from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.database import DBSession
from app.models.models import Stock

router = APIRouter()


@router.get("/")
async def list_stocks(db: DBSession):
    result = await db.execute(select(Stock).order_by(Stock.ticker))
    return result.scalars().all()


@router.get("/{ticker}")
async def get_stock(ticker: str, db: DBSession):
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.strip().upper()))
    stock = result.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock
