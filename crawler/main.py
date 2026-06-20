"""Crawler entrypoint — run manually or via GitHub Actions."""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from collectors.yahoo import fetch_yahoo_rss

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TICKERS = os.getenv("CRAWL_TICKERS", "AAPL,NVDA").split(",")


async def run():
    for ticker in TICKERS:
        ticker = ticker.strip()
        log.info(f"Crawling {ticker}...")
        articles = fetch_yahoo_rss(ticker)
        log.info(f"  {len(articles)} articles fetched for {ticker}")
        # TODO: upsert into DB (Phase 1 Week 1)


if __name__ == "__main__":
    asyncio.run(run())
