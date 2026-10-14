import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings


logger = logging.getLogger(__name__)

NEWS_URL = "https://newsapi.org/v2/everything"
REQUEST_TIMEOUT = 15.0
DEFAULT_LIMIT = 5
MAX_LIMIT = 5


class NewsDataError(Exception):
    """Raised when news cannot be retrieved from NewsAPI."""


# Legal/business suffixes should not count as meaningful company-name tokens.
COMPANY_SUFFIXES = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "company",
    "co",
    "limited",
    "ltd",
    "plc",
    "llc",
    "group",
    "holdings",
}

# These terms help distinguish company-related news from incidental mentions.
BUSINESS_CONTEXT_TERMS = {
    "stock",
    "stocks",
    "share",
    "shares",
    "market",
    "markets",
    "earnings",
    "revenue",
    "profit",
    "profits",
    "investor",
    "investors",
    "analyst",
    "analysts",
    "forecast",
    "outlook",
    "valuation",
    "financial",
    "finance",
    "business",
    "company",
    "quarter",
    "quarterly",
    "growth",
    "sales",
    "demand",
    "production",
    "launch",
    "acquisition",
    "merger",
    "competition",
    "lawsuit",
    "regulation",
    "partnership",
    "guidance",
    "dividend",
    "buyback",
    "price",
    "target",
    "upgrade",
    "downgrade",
    "nasdaq",
    "nyse",
    "iphone",
    "ipad",
    "mac",
    "ios",
    "services",
}

# Broad words alone should not establish that an article is relevant.
GENERIC_WORDS = {
    "stock",
    "stocks",
    "share",
    "shares",
    "market",
    "markets",
    "company",
    "business",
    "financial",
    "finance",
    "news",
    "latest",
    "today",
    "report",
    "reports",
    "update",
    "updates",
}


def _normalize_text(value: str | None) -> str:
    """Normalize text for matching and duplicate detection."""
    if not value:
        return ""

    value = value.lower()
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _get_company_tokens(company_name: str | None) -> set[str]:
    """Return meaningful tokens from a company name."""
    normalized = _normalize_text(company_name)

    return {
        token
        for token in normalized.split()
        if len(token) > 2 and token not in COMPANY_SUFFIXES
    }


def _contains_exact_term(text: str, term: str) -> bool:
    """Match a term as a complete word or phrase."""
    if not text or not term:
        return False

    pattern = rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _article_relevance_score(
    article: dict[str, Any],
    company_name: str | None,
    symbol: str,
) -> int:
    """
    Estimate how relevant an article is to the requested company.

    Headlines receive more weight than descriptions because a company
    mentioned only incidentally in a description is often a false match.
    """
    title = _normalize_text(article.get("title"))
    description = _normalize_text(article.get("description"))
    combined_text = f"{title} {description}"

    company_tokens = _get_company_tokens(company_name)
    normalized_symbol = _normalize_text(symbol)

    title_company_matches = {
        token
        for token in company_tokens
        if _contains_exact_term(title, token)
    }

    description_company_matches = {
        token
        for token in company_tokens
        if _contains_exact_term(description, token)
    }

    symbol_in_title = _contains_exact_term(title, normalized_symbol)
    symbol_in_description = _contains_exact_term(
        description, normalized_symbol
    )

    score = 0

    # A ticker match is a strong signal when it appears as a complete term.
    if symbol_in_title:
        score += 6
    elif symbol_in_description:
        score += 4

    # Company-name matches are weighted by where they appear.
    if title_company_matches:
        score += 5

    if description_company_matches:
        score += 2

    # Give context a small boost, but never use context alone as proof.
    context_matches = sum(
        1
        for term in BUSINESS_CONTEXT_TERMS
        if _contains_exact_term(combined_text, term)
    )
    score += min(context_matches, 3)

    # A company name mentioned only in the description is weak evidence.
    if (
        not title_company_matches
        and not symbol_in_title
        and description_company_matches
    ):
        score -= 2

    # Generic finance wording cannot make an unrelated article relevant.
    meaningful_title_matches = title_company_matches or symbol_in_title
    if not meaningful_title_matches and not symbol_in_description:
        score -= 3

    return score


def _is_relevant_article(
    article: dict[str, Any],
    company_name: str | None,
    symbol: str,
) -> bool:
    """Keep English articles with a meaningful link to the company's business or stock."""

    title_raw = article.get("title") or ""
    description_raw = article.get("description") or ""

    title = _normalize_text(title_raw)
    description = _normalize_text(description_raw)
    combined = f"{title} {description}"

    if not title:
        return False

    # NewsAPI can occasionally return non-English content despite language=en.
    letters = [char for char in title_raw if char.isalpha()]
    english_letters = [char for char in letters if char.isascii()]
    if letters and len(english_letters) / len(letters) < 0.8:
        return False

    normalized_symbol = _normalize_text(symbol.strip())
    company_tokens = _get_company_tokens(company_name)

    symbol_in_title = _contains_exact_term(title, normalized_symbol)
    symbol_in_description = _contains_exact_term(
        description, normalized_symbol
    )

    company_in_title = any(
        _contains_exact_term(title, token)
        for token in company_tokens
    )
    company_in_description = any(
        _contains_exact_term(description, token)
        for token in company_tokens
    )

    # These terms indicate a possible investment or company-business catalyst.
    financial_terms = {
        "stock", "shares", "share price", "price target",
        "earnings", "revenue", "profit", "profits", "valuation",
        "analyst", "investors", "market share", "sales", "demand",
        "production cuts", "forecast", "guidance", "dividend",
        "buyback", "upgrade", "downgrade", "competition", "competitive",
        "lawsuit", "antitrust", "regulation", "acquisition", "merger",
        "supply chain", "margin", "growth", "wireless", "spectrum",
        "business risk", "financial results",
    }

    # Product/event terms can be useful catalysts, but require the company
    # to appear in the headline so generic product stories are less likely
    # to pass merely because the company is mentioned in passing.
    product_catalyst_terms = {
        "iphone", "ipad", "macbook", "mac", "app store",
        "ios", "apple tv", "homepod", "product launch",
        "product announcement", "product release",
    }

    has_financial_context = any(
        _contains_exact_term(combined, term)
        for term in financial_terms
    )

    has_product_catalyst = any(
        _contains_exact_term(title, term)
        for term in product_catalyst_terms
    )

    # Strongest case: the company/ticker appears in the headline and the
    # article discusses an investment, financial, or competitive issue.
    if (symbol_in_title or company_in_title) and has_financial_context:
        return True

    # Product news can be retained as a possible catalyst if the headline
    # identifies both the company and a specific product/event.
    if (symbol_in_title or company_in_title) and has_product_catalyst:
        return True

    # Allow articles whose headline focuses on a competitor or industry risk
    # when the target ticker/company is explicitly discussed in the body.
    # Require several meaningful contextual signals to reduce false matches.
    risk_terms = {
        "risk", "competition", "competitive", "demand",
        "revenue", "sales", "production", "earnings",
    }
    risk_context_count = sum(
        1 for term in risk_terms
        if _contains_exact_term(combined, term)
    )

    if (
        (symbol_in_description or company_in_description)
        and has_financial_context
        and risk_context_count >= 2
    ):
        return True

    return False


def _clean_article(article: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a NewsAPI article to the response shape used by the app."""
    title = (article.get("title") or "").strip()
    url = (article.get("url") or "").strip()

    if not title or not url:
        return None

    parsed_url = urlparse(url)

    # Ignore malformed or non-web URLs.
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return None

    source_data = article.get("source") or {}
    source_name = source_data.get("name")

    return {
        "title": title,
        "description": (article.get("description") or "").strip() or None,
        "source": source_name.strip() if isinstance(source_name, str) else None,
        "url": url,
        "image_url": article.get("urlToImage"),
        "published_at": article.get("publishedAt"),
    }


def _deduplicate_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove repeated articles by URL and normalized headline."""
    unique_articles: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for article in articles:
        url = (article.get("url") or "").strip().rstrip("/").lower()
        title = _normalize_text(article.get("title"))

        # Ignore tracking parameters when comparing URLs.
        parsed_url = urlparse(url)
        normalized_url = (
            f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            .rstrip("/")
        )

        if normalized_url in seen_urls or title in seen_titles:
            continue

        seen_urls.add(normalized_url)
        seen_titles.add(title)
        unique_articles.append(article)

    return unique_articles


def _build_search_query(
    symbol: str,
    company_name: str | None,
) -> str:
    """
    Build a focused NewsAPI query.

    Company name and ticker are searched together. Relevance filtering is
    still applied afterward because search providers can return false matches.
    """
    symbol = symbol.strip().upper()

    if company_name and company_name.strip():
        company_name = company_name.strip().replace('"', "")
        return f'"{company_name}" OR "{symbol}"'

    return f'"{symbol}" AND (stock OR shares OR earnings OR company)'


async def get_stock_news(
    symbol: str,
    company_name: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """
    Fetch recent, relevant company news from NewsAPI.

    Returns a list of dictionaries containing:
        title, description, source, url, image_url, published_at

    Raises:
        NewsDataError: If NewsAPI fails or returns an invalid response.
    """
    if not settings.news_api_key:
        raise NewsDataError("NEWS_API_KEY is not configured.")

    symbol = symbol.strip().upper()

    if not symbol:
        raise NewsDataError("A stock symbol is required.")

    if limit < 1:
        limit = DEFAULT_LIMIT

    limit = min(limit, MAX_LIMIT)

    # Use a rolling seven-day window in UTC.
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(days=7)

    params = {
        "q": _build_search_query(symbol, company_name),
        "from": from_date.strftime("%Y-%m-%dT%H:%M:%S"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": MAX_LIMIT,
        "page": 1,
        "apiKey": settings.news_api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(NEWS_URL, params=params)
            response.raise_for_status()
            payload = response.json()

    except httpx.TimeoutException as exc:
        logger.warning("NewsAPI request timed out for %s", symbol)
        raise NewsDataError("News provider request timed out.") from exc

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        logger.error(
            "NewsAPI returned HTTP %s for symbol %s",
            status_code,
            symbol,
        )
        raise NewsDataError(
            f"News provider returned HTTP {status_code}."
        ) from exc

    except httpx.RequestError as exc:
        logger.exception("Could not connect to NewsAPI for %s", symbol)
        raise NewsDataError(
            "Could not connect to the news provider."
        ) from exc

    except ValueError as exc:
        logger.exception("NewsAPI returned invalid JSON for %s", symbol)
        raise NewsDataError(
            "News provider returned an invalid response."
        ) from exc

    if not isinstance(payload, dict):
        raise NewsDataError("News provider returned an unexpected response.")

    if payload.get("status") != "ok":
        provider_message = payload.get("message") or "Unknown provider error"
        logger.error("NewsAPI error for %s: %s", symbol, provider_message)
        raise NewsDataError("News provider could not complete the request.")

    raw_articles = payload.get("articles")

    if not isinstance(raw_articles, list):
        raise NewsDataError("News provider returned an invalid articles list.")

    cleaned_articles: list[dict[str, Any]] = []

    for raw_article in raw_articles:
        if not isinstance(raw_article, dict):
            continue

        article = _clean_article(raw_article)

        if article is None:
            continue

        if not _is_relevant_article(
            article=article,
            company_name=company_name,
            symbol=symbol,
        ):
            continue

        cleaned_articles.append(article)

    # NewsAPI normally sorts by publication date, newest first. Sort locally
    # too, while safely placing articles without dates at the end.
    cleaned_articles.sort(
        key=lambda article: article.get("published_at") or "",
        reverse=True,
    )

    unique_articles = _deduplicate_articles(cleaned_articles)
    result = unique_articles[:limit]

    logger.info(
        "Retrieved %d relevant news articles for %s",
        len(result),
        symbol,
    )

    return result