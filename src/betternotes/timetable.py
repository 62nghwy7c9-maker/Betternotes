"""Stundenplan des Tages: WebUntis, mit Fallback auf den konfigurierten Wochenplan."""

from __future__ import annotations

import logging
from datetime import date

from .config import AppConfig, Secrets
from .models import Lesson

log = logging.getLogger(__name__)

_WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class TimetableError(Exception):
    pass


def fetch_untis_lessons(config: AppConfig, secrets: Secrets, day: date) -> list[Lesson]:
    """Heutige, nicht entfallene Stunden aus WebUntis (wirft TimetableError bei Problemen)."""
    if not (secrets.webuntis_server and secrets.webuntis_school and secrets.webuntis_user):
        raise TimetableError("WebUntis-Zugangsdaten unvollständig.")

    import webuntis  # lazy: erleichtert Tests/Teilbetrieb ohne die Lib

    try:
        session = webuntis.Session(
            server=secrets.webuntis_server,
            school=secrets.webuntis_school,
            username=secrets.webuntis_user,
            password=secrets.webuntis_password,
            useragent="Betternotes",
        ).login()
    except Exception as exc:  # noqa: BLE001 - jede Login-Störung => Fallback
        raise TimetableError(f"WebUntis-Login fehlgeschlagen: {exc}") from exc

    try:
        periods = session.my_timetable(start=day, end=day)
    except Exception as exc:  # noqa: BLE001
        raise TimetableError(f"WebUntis-Stundenplanabruf fehlgeschlagen: {exc}") from exc
    finally:
        try:
            session.logout()
        except Exception:  # noqa: BLE001 - Logout-Fehler sind egal
            pass

    lessons: list[Lesson] = []
    for period in sorted(periods, key=lambda p: getattr(p, "start", None) or 0):
        if getattr(period, "code", None) == "cancelled":
            continue
        for subj in getattr(period, "subjects", []) or []:
            code = getattr(subj, "name", "") or ""
            subject = config.subject_by_untis(code)
            if subject is None:
                log.info("Untis-Fach '%s' ist keinem Betternotes-Fach zugeordnet.", code)
                continue
            lessons.append(Lesson(subject=subject, start=getattr(period, "start", None), end=getattr(period, "end", None)))
    return lessons


def fallback_lessons(config: AppConfig, day: date) -> list[Lesson]:
    week_key = "even" if day.isocalendar().week % 2 == 0 else "odd"
    plan = config.fallback_week.get(week_key, {})
    names = plan.get(_WEEKDAY_KEYS[day.weekday()], [])
    lessons = []
    for name in names:
        subject = config.subject_by_name(name)
        if subject is None:
            log.warning("Fallback-Wochenplan nennt unbekanntes Fach '%s'.", name)
            continue
        lessons.append(Lesson(subject=subject))
    return lessons


def _untis_configured(secrets: Secrets) -> bool:
    return bool(
        secrets.webuntis_server and secrets.webuntis_school and secrets.webuntis_user
    )


def get_todays_lessons(config: AppConfig, secrets: Secrets, day: date) -> tuple[list[Lesson], str]:
    """Liefert (Stunden, Hinweistext). Hinweistext ist leer, wenn Untis funktioniert hat."""
    if not _untis_configured(secrets):
        # WebUntis wurde bewusst nicht eingerichtet -> fester Wochenplan, dezenter Hinweis.
        log.info("WebUntis nicht eingerichtet – nutze festen Wochenplan.")
        return fallback_lessons(config, day), (
            "Stundenplan aus dem festen Wochenplan (WebUntis ist nicht eingerichtet, "
            "daher keine Vertretungen/Ausfälle)."
        )
    try:
        return fetch_untis_lessons(config, secrets, day), ""
    except TimetableError as exc:
        log.warning("WebUntis nicht nutzbar (%s) – nutze Fallback-Wochenplan.", exc)
        return fallback_lessons(config, day), (
            "WebUntis war nicht erreichbar – der Stundenplan stammt aus dem "
            "hinterlegten Wochenplan und enthält keine Vertretungen/Ausfälle."
        )


def unique_subjects(lessons: list[Lesson]):
    """Fächer in Reihenfolge der ersten Stunde, ohne Duplikate."""
    seen: set[str] = set()
    result = []
    for lesson in lessons:
        if lesson.subject.name not in seen:
            seen.add(lesson.subject.name)
            result.append(lesson.subject)
    return result
