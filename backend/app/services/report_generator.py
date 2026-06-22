"""Daily bull/bear report generator — one OpenAI call per ticker."""
import asyncio
import logging
from datetime import date

from openai import AsyncOpenAI
from sqlalchemy import func, select

from app.ai.prompts import REPORT_SYSTEM_PROMPT
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Article, Report, Stock
from app.schemas.report import ReportOutput

log = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_for_stock(stock: Stock, today: date) -> None:
    """Generate and persist one report for *stock* on *today*."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            existing = (
                await session.execute(
                    select(Report.id)
                    .where(Report.stock_id == stock.id)
                    .where(Report.report_date == today)
                )
            ).scalar_one_or_none()
            if existing:
                log.info("%s: report already exists for %s, skipping", stock.ticker, today)
                return

            articles = (
                await session.execute(
                    select(Article)
                    .where(Article.stock_id == stock.id)
                    .where(func.date(Article.created_at) == today)
                    .order_by(Article.published_at.desc().nulls_last())
                )
            ).scalars().all()

            if not articles:
                log.info("%s: no articles for %s, skipping", stock.ticker, today)
                return

            articles_text = "\n\n".join(
                f"[{i + 1}] {a.title}\n{a.content or ''}"
                for i, a in enumerate(articles)
            )
            user_msg = f"Ticker: {stock.ticker}\n\nNews articles:\n{articles_text}"

            response = await client.beta.chat.completions.parse(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format=ReportOutput,
            )
            output: ReportOutput = response.choices[0].message.parsed

            session.add(
                Report(
                    stock_id=stock.id,
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
                stock.ticker,
                len(output.bull_points),
                len(output.bear_points),
                output.confidence_score,
            )


async def run() -> None:
    today = date.today()
    log.info("Report generator — %s", today)

    async with AsyncSessionLocal() as session:
        stocks = (await session.execute(select(Stock))).scalars().all()

    for stock in stocks:
        try:
            await generate_for_stock(stock, today)
        except Exception:
            log.exception("%s: failed to generate report — skipping", stock.ticker)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())
