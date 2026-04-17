import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas.research import NewsItem
from app.storage.news_cache import load_cached_news, save_cached_news

COINDESK_RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml"
NEWS_CACHE_KEY = "btc-major-news"
NEWS_CACHE_SECONDS = 60 * 60 * 3
MAX_NEWS_ITEMS = 8


def _fallback_btc_news() -> list[NewsItem]:
    return [
        NewsItem(
            title="ETF flows and macro liquidity remain key BTC drivers",
            source="Mock Research Feed",
            summary="ETF flow direction, dollar liquidity, and macro rate expectations remain the core BTC research inputs.",
            sentiment="positive",
            data_source="Local fallback",
        ),
        NewsItem(
            title="Volatility expected around upcoming economic data",
            source="Mock Macro Feed",
            summary="Macro releases can raise intraday volatility, so scenario notes should separate signal from noise.",
            sentiment="neutral",
            data_source="Local fallback",
        ),
    ]


def _sentiment_for_title(title: str) -> str:
    lower_title = title.lower()
    positive_terms = ("rally", "surge", "gain", "bull", "etf inflow", "record")
    negative_terms = ("drop", "fall", "slump", "bear", "outflow", "hack", "lawsuit")

    if any(term in lower_title for term in positive_terms):
        return "positive"
    if any(term in lower_title for term in negative_terms):
        return "negative"
    return "neutral"


def _clean_summary(text: str | None) -> str | None:
    if not text:
        return None

    without_tags = re.sub(r"<[^>]+>", " ", text)
    normalized = re.sub(r"\s+", " ", unescape(without_tags)).strip()
    if not normalized:
        return None

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    summary = " ".join(sentences[:2]).strip()
    return summary[:360]


def _published_at(item: ET.Element) -> str | None:
    value = item.findtext("pubDate")
    if not value:
        return None

    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError):
        return value.strip()


def get_btc_news() -> list[NewsItem]:
    cached_items = load_cached_news(NEWS_CACHE_KEY, NEWS_CACHE_SECONDS)
    if cached_items:
        return cached_items

    request = Request(
        COINDESK_RSS_URL,
        headers={
            "Accept": "application/rss+xml, application/xml",
            "User-Agent": "btc-research-ai/0.1",
        },
    )

    try:
        with urlopen(request, timeout=10.0) as response:
            root = ET.fromstring(response.read())

        items = []
        for item in root.findall("./channel/item"):
            title = item.findtext("title")
            link = item.findtext("link")
            description = item.findtext("description")
            title_text = title.lower() if title else ""

            if not title or ("bitcoin" not in title_text and "btc" not in title_text):
                continue

            items.append(
                NewsItem(
                    title=title.strip(),
                    source="CoinDesk RSS",
                    url=link.strip() if link else None,
                    summary=_clean_summary(description),
                    published_at=_published_at(item),
                    sentiment=_sentiment_for_title(title),
                    data_source="CoinDesk RSS cached for 3h",
                )
            )

            if len(items) >= MAX_NEWS_ITEMS:
                break

        final_items = items or _fallback_btc_news()
        if items:
            save_cached_news(NEWS_CACHE_KEY, final_items)
        return final_items
    except (ET.ParseError, HTTPError, URLError, TimeoutError, ValueError):
        return load_cached_news(NEWS_CACHE_KEY, max_age_seconds=NEWS_CACHE_SECONDS * 8) or _fallback_btc_news()
