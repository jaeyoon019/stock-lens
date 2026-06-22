from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import reports, stocks

app = FastAPI(title="stock-lens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["stocks"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])


@app.get("/health")
async def health():
    return {"status": "ok"}
