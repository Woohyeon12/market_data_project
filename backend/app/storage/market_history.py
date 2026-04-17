import os
import sqlite3
from pathlib import Path

from app.schemas.research import IndexChartPoint

DB_PATH = Path(os.getenv("MARKET_HISTORY_DB_PATH", "data/market_history.sqlite"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS market_ohlc (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            source TEXT NOT NULL,
            PRIMARY KEY (symbol, date)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_market_ohlc_symbol_date
        ON market_ohlc (symbol, date)
        """
    )
    return connection


def load_ohlc_points(symbol: str) -> list[IndexChartPoint]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT date, open, high, low, close
            FROM market_ohlc
            WHERE symbol = ?
            ORDER BY date
            """,
            (symbol,),
        ).fetchall()

    return [
        IndexChartPoint(
            date=row[0],
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
        )
        for row in rows
    ]


def save_ohlc_points(
    symbol: str,
    points: list[IndexChartPoint],
    source: str,
) -> None:
    with _connect() as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO market_ohlc
                (symbol, date, open, high, low, close, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    symbol,
                    point.date,
                    point.open,
                    point.high,
                    point.low,
                    point.close,
                    source,
                )
                for point in points
            ],
        )


def count_ohlc_points(symbol: str) -> int:
    with _connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM market_ohlc WHERE symbol = ?",
            (symbol,),
        ).fetchone()

    return int(row[0]) if row else 0


def latest_ohlc_source(symbol: str) -> str | None:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT source
            FROM market_ohlc
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()

    return str(row[0]) if row else None
