"""Zeitfenster- und Dedupe-Prüfung.

Der Workflow läuft um 03:45 und 04:45 UTC. Je nach Sommer-/Winterzeit liegt
genau einer der beiden Läufe kurz vor 6:00 Europe/Berlin; der andere wird hier
leise beendet. Ein zweiter Versand am selben Tag wird über state.last_sent_date
verhindert.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .config import AppConfig
from .state import State

# So viele Minuten vor send_hour darf der Lauf starten (Actions-Cron ist unpünktlich).
EARLY_WINDOW_MINUTES = 45


def should_run(now_utc: datetime, config: AppConfig, state: State, force: bool = False) -> tuple[bool, str]:
    """Liefert (laufen?, Begründung). now_utc muss zeitzonenbewusst sein."""
    local = now_utc.astimezone(ZoneInfo(config.timezone))

    if not force and state.last_sent_date == local.date().isoformat():
        return False, f"Heute ({state.last_sent_date}) wurde bereits gesendet."

    if force:
        return True, "Erzwungener Lauf (--force)."

    target = local.replace(hour=config.send_hour, minute=0, second=0, microsecond=0)
    delta_min = (local - target).total_seconds() / 60

    if delta_min < -EARLY_WINDOW_MINUTES:
        return False, (
            f"Zu früh: lokale Zeit {local:%H:%M}, Ziel {config.send_hour}:00 "
            f"(dieser Cron-Lauf gehört zur anderen Jahreszeit)."
        )
    return True, f"Lokale Zeit {local:%H:%M}, Versandfenster erreicht."
