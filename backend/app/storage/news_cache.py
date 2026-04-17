import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.research import NewsItem

DB_PATH = Path(os.getenv("MARKET_HISTORY_DB_PATH", "data/market_history.sqlite"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS news_cache (
            cache_key TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            summary TEXT,
            published_at TEXT,
            sentiment TEXT NOT NULL,
            data_source TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            PRIMARY KEY (cache_key, url)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_news_cache_key_fetched
        ON news_cache (cache_key, fetched_at)
        """
    )
    return connection


def load_cached_news(cache_key: str, max_age_seconds: int) -> list[NewsItem]:
    with _connect() as connection:
        latest_row = connection.execute(
            "SELECT MAX(fetched_at) FROM news_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()

        if not latest_row or not latest_row[0]:
            return []

        fetched_at = datetime.fromisoformat(str(latest_row[0]))
        age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        if age_seconds > max_age_seconds:
            return []

        rows = connection.execute(
            """
            SELECT title, source, url, summary, published_at, sentiment, data_source
            FROM news_cache
            WHERE cache_key = ? AND fetched_at = ?
            ORDER BY published_at DESC, title
            """,
            (cache_key, latest_row[0]),
        ).fetchall()

    return [
        NewsItem(
            title=str(row[0]),
            source=str(row[1]),
            url=str(row[2]) or None,
            summary=str(row[3]) if row[3] else None,
            published_at=str(row[4]) if row[4] else None,
            sentiment=str(row[5]),
            data_source=str(row[6]),
        )
        for row in rows
    ]


def save_cached_news(cache_key: str, items: list[NewsItem]) -> str:
    fetched_at = datetime.now(timezone.utc).isoformat()

    with _connect() as connection:
        connection.execute("DELETE FROM news_cache WHERE cache_key = ?", (cache_key,))
        connection.executemany(
            """
            INSERT OR REPLACE INTO news_cache
                (cache_key, url, title, source, summary, published_at, sentiment, data_source, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    cache_key,
                    item.url or item.title,
                    item.title,
                    item.source,
                    item.summary,
                    item.published_at,
                    item.sentiment,
                    item.data_source,
                    fetched_at,
                )
                for item in items
            ],
        )

    return fetched_at
