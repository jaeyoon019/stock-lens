"""Daily bull/bear report generator — one OpenAI call per ticker."""
import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta
from datetime import time as dt_time

from openai import AsyncOpenAI
from sqlalchemy import select

from app.ai.prompts import REPORT_SYSTEM_PROMPT
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Article, Report, Stock
from app.schemas.report import ReportOutput

log = logging.getLogger(__name__)

_MAX_CONTENT_CHARS = 800  # ~200 tokens per article; keeps total prompt within model context limits


async def generate_for_stock(
    client: AsyncOpenAI, stock_id: uuid.UUID, ticker: str, today: date
) -> None:
    """Generate and persist one report for *ticker* on *today*."""
    start = datetime.combine(today, dt_time.min)
    end = start + timedelta(days=1)

    # Read phase — no write transaction needed.
    async with AsyncSessionLocal() as session:
        existing = (
            await session.execute(
                select(Report.id)
                .where(Report.stock_id == stock_id)
                .where(Report.report_date == today)
            )
        ).scalar_one_or_none()
        if existing:
            log.info("%s: report already exists for %s, skipping", ticker, today)
            return

        articles = (
            await session.execute(
                select(Article)
                .where(Article.stock_id == stock_id)
                .where(Article.created_at >= start)
                .where(Article.created_at < end)
                .order_by(Article.published_at.desc().nulls_last())
            )
        ).scalars().all()

        if not articles:
            log.info("%s: no articles for %s, skipping", ticker, today)
            return

    # Build prompt and call API outside any DB session.
    # Article scalar columns (title, content) remain accessible on detached instances.
    articles_text = "\n\n".join(
        f"[{i + 1}] {a.title}\n{(a.content or '')[:_MAX_CONTENT_CHARS]}"
        for i, a in enumerate(articles)
    )
    user_msg = f"Ticker: {ticker}\n\nNews articles:\n{articles_text}"

    response = await client.beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format=ReportOutput,
    )
    output = response.choices[0].message.parsed
    if output is None:
        raise RuntimeError(
            f"Structured output returned None for {ticker!r} "
            f"(finish_reason={response.choices[0].finish_reason!r})"
        )

    # Short write transaction — API call is already done.
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Re-check inside the transaction — prevents a wasted duplicate API call
            # if two concurrent process invocations both passed the initial read check.
            if (
                await session.execute(
                    select(Report.id)
                    .where(Report.stock_id == stock_id)
                    .where(Report.report_date == today)
                )
            ).scalar_one_or_none():
                log.info("%s: report appeared between check and insert (concurrent run), skipping", ticker)
                return
            session.add(
                Report(
                    stock_id=stock_id,
                    report_date=today,
                    bull_points=output.bull_points,
                    bear_points=output.bear_points,
                    overall_summary=output.overall_summary,
                    confidence_score=output.confidence_score,
                    article_count=len(articles),  # authoritative count, not LLM's
                )
            )
    log.info(
        "%s: saved report — %d bull, %d bear, score=%.2f",
        ticker,
        len(output.bull_points),
        len(output.bear_points),
        output.confidence_score,
    )


async def run() -> None:
    today = date.today()
    log.info("Report generator — %s", today)
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    async with AsyncSessionLocal() as session:
        # Select scalars only; avoids detached-instance access on ORM objects.
        rows = (await session.execute(select(Stock.id, Stock.ticker))).all()

    for stock_id, ticker in rows:
        try:
            await generate_for_stock(client, stock_id, ticker, today)
        except Exception:
            log.exception("%s: failed to generate report — skipping", ticker)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())
