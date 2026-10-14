import { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import {
  Search,
  TrendingUp,
  TrendingDown,
  Activity,
  Newspaper,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import "./App.css";

const API_BASE_URL =
  import.meta.env.API_BASE_URL || "http://127.0.0.1:8000";

const PERIODS = [
  { label: "1 Week", value: "1wk" },
  { label: "1 Month", value: "1mo" },
  { label: "3 Months", value: "3mo" },
  { label: "6 Months", value: "6mo" },
  { label: "1 Year", value: "1y" },
];

const money = (value, currency = "USD") => {
  if (value == null || !Number.isFinite(Number(value))) return "N/A";

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
};

const number = (value) => {
  if (value == null || !Number.isFinite(Number(value))) return "N/A";

  return Number(value).toLocaleString("en-US", {
    maximumFractionDigits: 2,
  });
};

const percent = (value) =>
  value == null ? "N/A" : `${Number(value).toFixed(2)}%`;

const dateLabel = (value) => {
  if (!value) return "";

  const date = new Date(value.length === 10 ? `${value}T12:00:00` : value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
};

function MetricCard({ label, value, detail, icon: Icon }) {
  return (
    <div className="metric-card">
      <div className="metric-heading">
        <span>{label}</span>
        {Icon && <Icon size={18} />}
      </div>
      <div className="metric-value">{value}</div>
      {detail && <div className="metric-detail">{detail}</div>}
    </div>
  );
}

function SectionHeading({ title, subtitle }) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
    </div>
  );
}

function App() {
  const [symbol, setSymbol] = useState("AAPL");
  const [companyName, setCompanyName] = useState("Apple Inc.");
  const [period, setPeriod] = useState("1mo");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function researchStock(event) {
    event.preventDefault();

    const normalizedSymbol = symbol.trim().toUpperCase();

    if (!normalizedSymbol) {
      setError("Enter a stock ticker.");
      return;
    }

    setLoading(true);
    setError("");
    setData(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/stocks/research`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            symbol: normalizedSymbol,
            company_name: companyName.trim() || null,
            period,
          }),
        }
      );

      const result = await response.json().catch(() => null);

      if (!response.ok) {
        const detail =
          typeof result?.detail === "string"
            ? result.detail
            : "The stock research request failed.";

        throw new Error(detail);
      }

      if (!result?.stock || !result?.quote) {
        throw new Error("The API returned an incomplete research response.");
      }

      setData(result);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot connect to the backend. Check that FastAPI is running and CORS is configured."
          : err.message || "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  }

  const stock = data?.stock;
  const quote = data?.quote;
  const indicators = data?.technical_indicators;
  const analysis = data?.analysis;

  const history = Array.isArray(data?.history) ? data.history : [];
  const news = Array.isArray(data?.news) ? data.news : [];

  const currency = stock?.currency || "USD";
  const priceChange = Number(quote?.change ?? 0);
  const isPositive = priceChange >= 0;

  const chartData = history.map((item) => ({
    date: item.datetime,
    close: Number(item.close),
  }));

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#">
          <span className="brand-icon">
            <Activity size={23} />
          </span>
          <span>Stock<span className="brand-accent">Scope</span></span>
        </a>

        <span className="topbar-label">AI STOCK RESEARCH</span>
      </header>

      <section className="page-content">
        <div className="hero">
          <div className="eyebrow">MARKET INTELLIGENCE</div>
          <h1>Research the market.<br />Understand the signals.</h1>
          <p className="hero-subtitle">
            Explore historical prices, technical indicators, market news, and AI-generated stock research in one place.
          </p>
        </div>

        <form className="search-panel" onSubmit={researchStock}>
          <label className="field">
            <span>Stock ticker</span>
            <input
              value={symbol}
              onChange={(event) => setSymbol(event.target.value)}
              placeholder="AAPL"
              maxLength={20}
              required
            />
          </label>

          <label className="field company-field">
            <span>Company name</span>
            <input
              value={companyName}
              onChange={(event) => setCompanyName(event.target.value)}
              placeholder="Apple Inc."
            />
          </label>

          <label className="field period-field">
            <span>History</span>
            <select
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
            >
              {PERIODS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <button className="research-button" type="submit" disabled={loading}>
            {loading ? (
              <RefreshCw className="spin" size={18} />
            ) : (
              <Search size={18} />
            )}
            {loading ? "Researching..." : "Analyze stock"}
          </button>
        </form>

        {error && (
          <div className="error-banner" role="alert">
            <AlertTriangle size={19} />
            <span>{error}</span>
          </div>
        )}

        {loading && (
          <div className="loading-panel">
            <div className="loading-spinner" />
            <h3>Researching the stock</h3>
            <p>Fetching market data, news, and AI analysis...</p>
          </div>
        )}

        {!data && !loading && !error && (
          <div className="empty-state">
            <Activity size={34} />
            <h2>Your research workspace</h2>
            <p>
              Search for a ticker to load its market data and research report.
            </p>
          </div>
        )}

        {data && (
          <>
            <section className="stock-overview">
              <div className="stock-identity">
                <div className="stock-symbol">{stock.symbol}</div>
                <div>
                  <h2>{stock.name || stock.symbol}</h2>
                  <p>
                    {stock.exchange || "Exchange unavailable"} · {currency}
                  </p>
                </div>
              </div>

              <div className="stock-price">
                <div className="current-price">
                  {money(quote.price, currency)}
                </div>
                <div className={isPositive ? "positive" : "negative"}>
                  {isPositive ? "+" : ""}
                  {money(quote.change, currency)}
                  {" "}({percent(quote.percent_change)})
                </div>
              </div>
            </section>

            <section className="metric-grid">
              <MetricCard
                label="Daily high"
                value={money(quote.high, currency)}
                icon={TrendingUp}
              />
              <MetricCard
                label="Daily low"
                value={money(quote.low, currency)}
                icon={TrendingDown}
              />
              <MetricCard
                label="Previous close"
                value={money(quote.previous_close, currency)}
                icon={Activity}
              />
              <MetricCard
                label="Volume"
                value={number(quote.volume)}
                detail="Reported trading volume"
                icon={Activity}
              />
            </section>

            <section className="content-card chart-card">
              <SectionHeading
                title="Price history"
                subtitle={`${history.length} observations · Latest date: ${
                  indicators?.latest_history_date || "Unavailable"
                }`}
              />

              {chartData.length > 0 ? (
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={chartData}
                      margin={{ top: 12, right: 12, left: 8, bottom: 4 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="var(--border)"
                      />
                      <XAxis
                        dataKey="date"
                        tickFormatter={dateLabel}
                        tick={{ fill: "var(--muted)", fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                        minTickGap={25}
                      />
                      <YAxis
                        domain={["auto", "auto"]}
                        tickFormatter={(value) => number(value)}
                        tick={{ fill: "var(--muted)", fontSize: 12 }}
                        axisLine={false}
                        tickLine={false}
                        width={68}
                      />
                      <Tooltip
                        labelFormatter={(value) => dateLabel(value)}
                        formatter={(value) => [
                          money(value, currency),
                          "Closing price",
                        ]}
                        contentStyle={{
                          background: "var(--surface)",
                          border: "1px solid var(--border)",
                          borderRadius: 10,
                        }}
                      />
                      {indicators?.sma_20 != null && (
                        <ReferenceLine
                          y={Number(indicators.sma_20)}
                          stroke="#e6a23c"
                          strokeDasharray="5 5"
                          label={{
                            value: "SMA20",
                            fill: "#e6a23c",
                            fontSize: 11,
                          }}
                        />
                      )}
                      <Line
                        type="monotone"
                        dataKey="close"
                        name="Closing price"
                        stroke="#64a6f7"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 5 }}
                        connectNulls={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="muted-message">No historical prices available.</p>
              )}

              <div className="chart-legend">
                <span><i className="legend-dot price-dot" /> Closing price</span>
                <span><i className="legend-dot sma-dot" /> SMA20</span>
              </div>
            </section>

            <section className="content-card">
              <SectionHeading
                title="Technical indicators"
                subtitle="Calculated from historical market prices"
              />

              <div className="indicator-grid">
                <MetricCard
                  label="SMA 20"
                  value={money(indicators?.sma_20, currency)}
                  detail="20-session average"
                />
                <MetricCard
                  label="SMA 50"
                  value={money(indicators?.sma_50, currency)}
                  detail="50-session average"
                />
                <MetricCard
                  label="RSI 14"
                  value={number(indicators?.rsi_14)}
                  detail="Relative strength index"
                />
                <MetricCard
                  label="20-session return"
                  value={percent(indicators?.return_20_sessions_pct)}
                  detail="Historical return"
                />
                <MetricCard
                  label="Annualized volatility"
                  value={percent(
                    indicators?.annualized_volatility_20_sessions_pct
                  )}
                  detail="Historical estimate"
                />
                <MetricCard
                  label="Price vs SMA20"
                  value={indicators?.price_vs_sma20 || "N/A"}
                  detail="Relative price position"
                />
              </div>

              <p className="disclaimer">
                Historical indicators describe past behavior and do not
                guarantee future returns.
              </p>
            </section>

            <section className="content-card analysis-card">
              <SectionHeading
                title="AI research assessment"
                subtitle="Generated from the supplied market data and news"
              />

              {analysis ? (
                <>
                  <div className="analysis-top">
                    <div
                      className={`recommendation recommendation-${String(
                        analysis.recommendation || "HOLD"
                      ).toLowerCase()}`}
                    >
                      {analysis.recommendation || "UNAVAILABLE"}
                    </div>

                    <div className="confidence">
                      <span>Analysis confidence</span>
                      <strong>
                        {analysis.confidence == null
                          ? "N/A"
                          : `${analysis.confidence}%`}
                      </strong>
                    </div>
                  </div>

                  <p className="analysis-summary">{analysis.summary}</p>

                  <div className="analysis-tags">
                    <span>
                      Technical: {analysis.technical_outlook || "N/A"}
                    </span>
                    <span>
                      News: {analysis.news_sentiment || "N/A"}
                    </span>
                    <span>
                      Horizon: {analysis.investment_horizon || "N/A"}
                    </span>
                  </div>

                  <div className="analysis-columns">
                    <div>
                      <h3 className="positive-heading">Supporting evidence</h3>
                      {analysis.reasons?.length ? (
                        <ul>
                          {analysis.reasons.map((reason, index) => (
                            <li key={index}>{reason}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="muted-message">No reasons supplied.</p>
                      )}
                    </div>

                    <div>
                      <h3 className="negative-heading">Risks to consider</h3>
                      {analysis.risks?.length ? (
                        <ul>
                          {analysis.risks.map((risk, index) => (
                            <li key={index}>{risk}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="muted-message">No risks supplied.</p>
                      )}
                    </div>
                  </div>

                  {analysis.evidence?.length > 0 && (
                    <div className="evidence-section">
                      <h3>Evidence sources</h3>
                      <ul>
                        {analysis.evidence.map((item, index) => (
                          <li key={index}>
                            <span>{item.claim}</span>
                            {" "}
                            <span className="evidence-source">
                              ({item.source})
                            </span>
                            {item.url && (
                              <>
                                {" "}
                                <a
                                  href={item.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  View source
                                </a>
                              </>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {analysis.data_limitations?.length > 0 && (
                    <div className="limitations">
                      <h3>Data limitations</h3>
                      <ul>
                        {analysis.data_limitations.map((item, index) => (
                          <li key={index}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <p className="muted-message">
                  AI analysis was not included in the response.
                </p>
              )}
            </section>

            <section className="content-card news-card">
              <SectionHeading
                title="Latest news"
                subtitle={`${news.length} articles returned by the backend`}
              />

              {news.length > 0 ? (
                <div className="news-list">
                  {news.map((article, index) => (
                    <article className="news-item" key={article.url || index}>
                      <div className="news-icon">
                        <Newspaper size={20} />
                      </div>
                      <div className="news-content">
                        <div className="news-meta">
                          <span>{article.source || "Unknown source"}</span>
                          <span>{dateLabel(article.published_at)}</span>
                        </div>
                        <h3>{article.title}</h3>
                        {article.description && (
                          <p>{article.description}</p>
                        )}
                        {article.url && (
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Read original article ↗
                          </a>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="muted-message">
                  No relevant news articles were returned for this search.
                </p>
              )}
            </section>

            <footer className="report-footer">
              <span>
                Report generated:{" "}
                {data.data_timestamp
                  ? new Date(data.data_timestamp).toLocaleString()
                  : "Timestamp unavailable"}
              </span>
              <p>
                AI-generated research is informational only, not personalized
                financial advice. Verify data and sources independently.
              </p>
            </footer>
          </>
        )}
      </section>
    </main>
  );
}

export default App;