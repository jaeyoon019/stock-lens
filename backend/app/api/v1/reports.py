from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Report, Stock

router = APIRouter()


@router.get("/")
async def list_reports(
    ticker: str | None = Query(None),
    from_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Report).order_by(Report.report_date.desc())

    if ticker:
        q = q.join(Stock).where(Stock.ticker == ticker.upper())

    if from_date:
        q = q.where(Report.report_date >= from_date)

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{report_id}")
async def get_report(report_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
