import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas.research import NewsItem

COINDESK_RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml"
MAX_NEWS_ITEMS = 5


def _fallback_btc_news() -> list[NewsItem]:
    return [
        NewsItem(
            title="ETF flows and macro liquidity remain key BTC drivers",
            source="Mock Research Feed",
            sentiment="positive",
            data_source="Local fallback",
        ),
        NewsItem(
            title="Volatility expected around upcoming economic data",
            source="Mock Macro Feed",
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


def get_btc_news() -> list[NewsItem]:
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
            title_text = title.lower() if title else ""

            if not title or ("bitcoin" not in title_text and "btc" not in title_text):
                continue

            items.append(
                NewsItem(
                    title=title.strip(),
                    source="CoinDesk RSS",
                    url=link.strip() if link else None,
                    sentiment=_sentiment_for_title(title),
                    data_source="CoinDesk RSS",
                )
            )

            if len(items) >= MAX_NEWS_ITEMS:
                break

        return items or _fallback_btc_news()
    except (ET.ParseError, HTTPError, URLError, TimeoutError, ValueError):
        return _fallback_btc_news()
