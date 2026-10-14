
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router


app = FastAPI(
    title="Stock Research Analyst Agent",
    description=(
        "Stock market data and recent news research API."
    ),
    version="1.0.0",
)

# Allows a React development server to access this API.
# Restrict origins to your real frontend URL before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Stock Research Analyst API is running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
