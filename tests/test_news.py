from datetime import date, datetime, timedelta, timezone

import betternotes.news as news_mod
from betternotes.news import NewsItem, top_news_markdown


def test_top_news_filters_old_items(config, fake_llm, monkeypatch):
    now = datetime(2026, 7, 6, 8, 0, tzinfo=timezone.utc)
    items = [
        NewsItem(title="Frisch", teaser="EU-Gipfel", published=now - timedelta(days=1), source="t"),
        NewsItem(title="Alt", teaser="Vor drei Wochen", published=now - timedelta(days=21), source="t"),
    ]
    monkeypatch.setattr(news_mod, "fetch_tagesschau", lambda client: items)

    fake_llm.reply = "#### Frisch (05.07.2026)\nZusammenfassung."
    md = top_news_markdown(fake_llm, config, date(2026, 7, 6))

    assert md.startswith("#### Frisch")
    (kind, _system, prompt, _images) = fake_llm.calls[0]
    assert kind == "complete"
    assert "Frisch" in prompt
    assert "Alt" not in prompt


def test_no_items_gives_notice_without_api_call(config, fake_llm, monkeypatch):
    monkeypatch.setattr(news_mod, "fetch_tagesschau", lambda client: [])
    monkeypatch.setattr(news_mod, "fetch_rss", lambda url: [])
    md = top_news_markdown(fake_llm, config, date(2026, 7, 6))
    assert "keine aktuellen Nachrichten" in md
    assert fake_llm.calls == []
