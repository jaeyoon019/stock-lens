"""Crawler entrypoint — run manually or via GitHub Actions."""
import asyncio
import logging
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Article, Stock
from collectors.yahoo import RawArticle, fetch_yahoo_rss

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TICKERS = settings.ticker_list


async def upsert_articles(ticker: str, articles: list[RawArticle], market: str) -> int:
    """Persist articles to DB. Returns the count of newly inserted rows."""
    # Guard before opening any DB connection — avoids a pointless Stock commit.
    if not articles:
        return 0

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Ensure a Stock row exists. market is caller-supplied so KRX tickers
            # are not permanently mislabelled "US" by a default.
            await session.execute(
                pg_insert(Stock)
                .values(id=uuid.uuid4(), ticker=ticker, name=ticker, market=market)
                .on_conflict_do_nothing(index_elements=["ticker"])
            )

            stock_id: uuid.UUID | None = (
                await session.execute(select(Stock.id).where(Stock.ticker == ticker))
            ).scalar_one_or_none()

            if stock_id is None:
                raise RuntimeError(
                    f"Stock row missing for {ticker!r} after upsert — concurrent delete?"
                )

            result = await session.execute(
                pg_insert(Article)
                .values(
                    [
                        dict(
                            id=uuid.uuid4(),
                            stock_id=stock_id,
                            title=a.title,
                            source=a.source,
                            url=a.url,
                            url_hash=a.url_hash,
                            content=a.content,
                            published_at=a.published_at,
                        )
                        for a in articles
                    ]
                )
                .on_conflict_do_nothing(index_elements=["url_hash"])
                .returning(Article.id)
            )
            return len(result.fetchall())


async def run():
    for ticker in TICKERS:
        try:
            log.info("Crawling %s...", ticker)
            articles = await asyncio.to_thread(fetch_yahoo_rss, ticker)
            log.info("  %d articles fetched", len(articles))
            inserted = await upsert_articles(ticker, articles, market="US")
            log.info("  %d new articles saved (duplicates skipped)", inserted)
        except Exception:
            log.exception("  Failed to process %s — skipping", ticker)


if __name__ == "__main__":
    asyncio.run(run())
