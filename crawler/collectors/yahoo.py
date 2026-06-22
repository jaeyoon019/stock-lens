"""Yahoo Finance RSS collector."""
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser


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
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    feed = feedparser.parse(url)

    articles = []
    for entry in feed.entries:
        raw_url = entry.get("link", "")
        if not raw_url:
            continue
        url_hash = hashlib.sha256(raw_url.encode()).hexdigest()

        published = None
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            published = datetime(*published_parsed[:6], tzinfo=timezone.utc)

        articles.append(
            RawArticle(
                ticker=ticker,
                title=entry.get("title", ""),
                url=raw_url,
                url_hash=url_hash,
                source="yahoo",
                published_at=published,
                content=entry.get("summary", ""),
            )
        )

    return articles
