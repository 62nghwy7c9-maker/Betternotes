"""Sowi-Nachrichten: tagesschau-API + RSS-Fallbacks, Top-Auswahl durch Claude."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

from .config import AppConfig
from . import prompts

log = logging.getLogger(__name__)

TAGESSCHAU_URL = "https://www.tagesschau.de/api2u/news"


@dataclass
class NewsItem:
    title: str
    teaser: str
    published: datetime
    source: str


def fetch_tagesschau(client: httpx.Client) -> list[NewsItem]:
    items: list[NewsItem] = []
    resp = client.get(TAGESSCHAU_URL, timeout=20)
    resp.raise_for_status()
    for entry in resp.json().get("news", []):
        try:
            published = datetime.fromisoformat(entry["date"])
        except (KeyError, ValueError):
            continue
        items.append(
            NewsItem(
                title=entry.get("title", ""),
                teaser=entry.get("firstSentence", "") or entry.get("topline", ""),
                published=published,
                source="tagesschau",
            )
        )
    return items


def fetch_rss(url: str) -> list[NewsItem]:
    import feedparser

    items: list[NewsItem] = []
    feed = feedparser.parse(url)
    for entry in feed.entries:
        parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        if parsed is None:
            continue
        published = datetime(*parsed[:6], tzinfo=timezone.utc)
        items.append(
            NewsItem(
                title=getattr(entry, "title", ""),
                teaser=getattr(entry, "summary", ""),
                published=published,
                source=url,
            )
        )
    return items


def collect_items(config: AppConfig, today: date) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        with httpx.Client() as client:
            items = fetch_tagesschau(client)
    except Exception as exc:  # noqa: BLE001 - API weg => RSS-Fallback
        log.warning("tagesschau-API nicht erreichbar (%s), nutze RSS-Fallbacks.", exc)

    if len(items) < config.news.count:
        for url in config.news.rss_fallbacks:
            try:
                items.extend(fetch_rss(url))
            except Exception as exc:  # noqa: BLE001
                log.warning("RSS-Feed %s nicht lesbar: %s", url, exc)

    cutoff = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) - timedelta(
        days=config.news.days_back
    )
    fresh = [i for i in items if i.published >= cutoff and i.title]
    fresh.sort(key=lambda i: i.published, reverse=True)
    return fresh


def top_news_markdown(anthropic_client, config: AppConfig, today: date) -> str:
    """Die N wichtigsten Sowi-Meldungen der letzten Tage als Markdown."""
    items = collect_items(config, today)
    if not items:
        return "_Es konnten keine aktuellen Nachrichten abgerufen werden._"

    listing = "\n".join(
        f"- [{item.published:%d.%m.%Y}] {item.title} — {item.teaser}" for item in items[:120]
    )
    prompt = prompts.NEWS_TEMPLATE.format(
        date=today.strftime("%d.%m.%Y"),
        days=config.news.days_back,
        count=config.news.count,
        items=listing,
    )
    response = anthropic_client.messages.create(
        model=config.model,
        max_tokens=2048,
        system=prompts.NEWS_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()
