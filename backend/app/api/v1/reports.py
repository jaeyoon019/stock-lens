from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.database import DBSession
from app.models.models import Report, Stock

router = APIRouter()


@router.get("/")
async def list_reports(
    ticker: str | None = Query(None),
    from_date: date | None = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
    db: DBSession,
):
    q = select(Report).order_by(Report.report_date.desc()).limit(limit)

    if ticker:
        q = q.join(Stock).where(Stock.ticker == ticker.strip().upper())

    if from_date:
        q = q.where(Report.report_date >= from_date)

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{report_id}")
async def get_report(report_id: UUID, db: DBSession):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
