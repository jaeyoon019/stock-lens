"""Crawler entrypoint — run manually or via GitHub Actions."""
import asyncio
import logging
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.models.models import Article, Stock
from collectors.yahoo import RawArticle, fetch_yahoo_rss

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TICKERS = os.getenv("CRAWL_TICKERS", "AAPL,NVDA").split(",")


async def upsert_articles(ticker: str, articles: list[RawArticle]) -> int:
    """Persist articles to DB. Returns the count of newly inserted rows."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Ensure a Stock row exists for this ticker (name/market filled as
            # placeholders — real metadata can be enriched separately).
            await session.execute(
                pg_insert(Stock)
                .values(id=uuid.uuid4(), ticker=ticker, name=ticker, market="US")
                .on_conflict_do_nothing(index_elements=["ticker"])
            )

            stock_id: uuid.UUID = (
                await session.execute(select(Stock.id).where(Stock.ticker == ticker))
            ).scalar_one()

            if not articles:
                return 0

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
        ticker = ticker.strip()
        log.info(f"Crawling {ticker}...")
        articles = fetch_yahoo_rss(ticker)
        log.info(f"  {len(articles)} articles fetched")
        inserted = await upsert_articles(ticker, articles)
        log.info(f"  {inserted} new articles saved (duplicates skipped)")


if __name__ == "__main__":
    asyncio.run(run())
