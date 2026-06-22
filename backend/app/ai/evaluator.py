"""LLM-as-judge evaluator — one OpenAI call per report."""
import asyncio
import logging
from datetime import date

from openai import AsyncOpenAI
from sqlalchemy import select

from app.ai.prompts import EVAL_SYSTEM_PROMPT
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Evaluation, Report, Stock
from app.schemas.report import EvalOutput

log = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def evaluate_report(report: Report, ticker: str) -> None:
    """Score *report* with the LLM judge and persist the result."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            existing = (
                await session.execute(
                    select(Evaluation.id).where(Evaluation.report_id == report.id)
                )
            ).scalar_one_or_none()
            if existing:
                log.info("%s %s: already evaluated, skipping", ticker, report.report_date)
                return

            bull = "\n".join(f"- {p}" for p in report.bull_points)
            bear = "\n".join(f"- {p}" for p in report.bear_points)
            user_msg = (
                f"Ticker: {ticker}\nReport Date: {report.report_date}\n\n"
                f"Bull Points:\n{bull}\n\n"
                f"Bear Points:\n{bear}\n\n"
                f"Overall Summary: {report.overall_summary}\n"
                f"Confidence Score: {report.confidence_score}\n"
                f"Articles Analyzed: {report.article_count}"
            )

            response = await client.beta.chat.completions.parse(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": EVAL_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format=EvalOutput,
            )
            output: EvalOutput = response.choices[0].message.parsed

            session.add(
                Evaluation(
                    report_id=report.id,
                    judge_score=output.judge_score,
                    judge_feedback=output.judge_feedback,
                    model_used=settings.openai_model,
                )
            )
            log.info(
                "%s %s: judge_score=%.2f — %s",
                ticker,
                report.report_date,
                output.judge_score,
                output.judge_feedback,
            )


async def run() -> None:
    today = date.today()
    log.info("Evaluator — %s", today)

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(Report, Stock.ticker)
                .join(Stock)
                .where(Report.report_date == today)
            )
        ).all()

    for report, ticker in rows:
        try:
            await evaluate_report(report, ticker)
        except Exception:
            log.exception("%s: failed to evaluate report — skipping", ticker)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())
