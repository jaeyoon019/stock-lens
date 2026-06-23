"""LLM-as-judge evaluator — one OpenAI call per report."""
import asyncio
import logging
import uuid
from datetime import date

from openai import AsyncOpenAI
from sqlalchemy import select

from app.ai.prompts import EVAL_SYSTEM_PROMPT
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Evaluation, Report, Stock
from app.schemas.report import EvalOutput

log = logging.getLogger(__name__)


async def evaluate_report(
    client: AsyncOpenAI,
    report_id: uuid.UUID,
    report_date: date,
    bull_points: list[str],
    bear_points: list[str],
    overall_summary: str,
    confidence_score: float,
    article_count: int,
    ticker: str,
) -> None:
    """Score one report with the LLM judge and persist the result."""
    # Idempotency check — read-only, no transaction needed.
    async with AsyncSessionLocal() as session:
        existing = (
            await session.execute(
                select(Evaluation.id).where(Evaluation.report_id == report_id)
            )
        ).scalar_one_or_none()
    if existing:
        log.info("%s %s: already evaluated, skipping", ticker, report_date)
        return

    # Build prompt and call API outside any DB session.
    bull = "\n".join(f"- {p}" for p in bull_points)
    bear = "\n".join(f"- {p}" for p in bear_points)
    user_msg = (
        f"Ticker: {ticker}\nReport Date: {report_date}\n\n"
        f"Bull Points:\n{bull}\n\n"
        f"Bear Points:\n{bear}\n\n"
        f"Overall Summary: {overall_summary}\n"
        f"Confidence Score: {confidence_score}\n"
        f"Articles Analyzed: {article_count}"
    )

    response = await client.beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format=EvalOutput,
    )
    if not response.choices:
        raise RuntimeError(f"OpenAI returned empty choices for {ticker!r} {report_date}")
    output = response.choices[0].message.parsed
    if output is None:
        raise RuntimeError(
            f"Structured output returned None for {ticker!r} {report_date} "
            f"(finish_reason={response.choices[0].finish_reason!r})"
        )

    # Short write transaction — API call is already done.
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Re-check inside the transaction — prevents duplicate evaluations
            # if two concurrent process invocations both passed the initial read check.
            if (
                await session.execute(
                    select(Evaluation.id).where(Evaluation.report_id == report_id)
                )
            ).scalar_one_or_none():
                log.info("%s %s: evaluation appeared between check and insert (concurrent run), skipping", ticker, report_date)
                return
            session.add(
                Evaluation(
                    report_id=report_id,
                    judge_score=output.judge_score,
                    judge_feedback=output.judge_feedback,
                    model_used=settings.openai_model,
                )
            )
    log.info(
        "%s %s: judge_score=%.2f — %s",
        ticker,
        report_date,
        output.judge_score,
        output.judge_feedback,
    )


async def run() -> None:
    today = date.today()
    log.info("Evaluator — %s", today)
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async with AsyncSessionLocal() as session:
        # Select scalars only; avoids detached-instance access on ORM objects.
        # Pre-filter already-evaluated reports at the DB level to avoid one session per report.
        rows = (
            await session.execute(
                select(
                    Report.id,
                    Report.report_date,
                    Report.bull_points,
                    Report.bear_points,
                    Report.overall_summary,
                    Report.confidence_score,
                    Report.article_count,
                    Stock.ticker,
                )
                .join(Stock)
                .where(Report.report_date == today)
                .where(
                    ~select(Evaluation.id)
                    .where(Evaluation.report_id == Report.id)
                    .correlate(Report)
                    .exists()
                )
            )
        ).all()

    for row in rows:
        try:
            await evaluate_report(
                client,
                report_id=row.id,
                report_date=row.report_date,
                bull_points=row.bull_points,
                bear_points=row.bear_points,
                overall_summary=row.overall_summary,
                confidence_score=row.confidence_score,
                article_count=row.article_count,
                ticker=row.ticker,
            )
        except Exception:
            log.exception("%s: failed to evaluate report — skipping", row.ticker)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())
