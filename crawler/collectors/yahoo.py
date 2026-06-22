"""Yahoo Finance RSS collector."""
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import httpx


@dataclass
class RawArticle:
    ticker: str
    title: str
    url: str
    url_hash: str
    source: str
    published_at: datetime | None
    content: str


def fetch_yahoo_rss(ticker: str) -> list[RawArticle]:
    """Fetch articles from Yahoo Finance RSS for a given ticker."""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote(ticker, safe='')}&region=US&lang=en-US"
    response = httpx.get(url, timeout=10, follow_redirects=True)
    response.raise_for_status()
    feed = feedparser.parse(response.content)

    articles = []
    for entry in feed.entries:
        raw_url = entry.get("link", "")
        if not raw_url:
            continue
        url_hash = hashlib.sha256(raw_url.encode()).hexdigest()

        title = entry.get("title", "").strip()
        if not title:
            continue

        published = None
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            published = datetime(*published_parsed[:6], tzinfo=timezone.utc)

        articles.append(
            RawArticle(
                ticker=ticker,
                title=title,
                url=raw_url,
                url_hash=url_hash,
                source="yahoo",
                published_at=published,
                content=entry.get("summary", ""),
            )
        )

    return articles
