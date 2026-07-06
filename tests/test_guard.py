from datetime import datetime, timezone

from betternotes.guard import should_run
from betternotes.state import State


def test_summer_early_run_is_in_window(config):
    # 03:45 UTC im Juli = 05:45 CEST -> senden
    now = datetime(2026, 7, 6, 3, 45, tzinfo=timezone.utc)
    ok, _ = should_run(now, config, State())
    assert ok


def test_winter_early_run_is_too_early(config):
    # 03:45 UTC im Januar = 04:45 CET -> zu früh, der 04:45-Lauf übernimmt
    now = datetime(2026, 1, 12, 3, 45, tzinfo=timezone.utc)
    ok, reason = should_run(now, config, State())
    assert not ok
    assert "früh" in reason


def test_winter_late_run_is_in_window(config):
    # 04:45 UTC im Januar = 05:45 CET -> senden
    now = datetime(2026, 1, 12, 4, 45, tzinfo=timezone.utc)
    ok, _ = should_run(now, config, State())
    assert ok


def test_already_sent_today_dedupes(config):
    now = datetime(2026, 7, 6, 4, 45, tzinfo=timezone.utc)  # 06:45 lokal
    state = State(last_sent_date="2026-07-06")
    ok, reason = should_run(now, config, state)
    assert not ok
    assert "bereits" in reason


def test_force_overrides_window_and_dedupe(config):
    now = datetime(2026, 1, 12, 3, 45, tzinfo=timezone.utc)
    ok, _ = should_run(now, config, State(), force=True)
    assert ok
    # force ist ein bewusster manueller Lauf: auch erneuter Versand ist erlaubt
    state = State(last_sent_date="2026-01-12")
    ok, _ = should_run(now, config, state, force=True)
    assert ok
