from datetime import date

from betternotes.config import Secrets
from betternotes.models import Lesson
from betternotes.timetable import fallback_lessons, get_todays_lessons, unique_subjects


def test_fallback_week(config):
    lessons = fallback_lessons(config, date(2026, 7, 6))  # Montag
    assert [l.subject.name for l in lessons] == ["Mathematik", "Deutsch"]
    assert fallback_lessons(config, date(2026, 7, 7)) == []  # Dienstag leer


def test_fallback_ignores_unknown_subject(config):
    config.fallback_week["even"]["mon"] = ["Mathematik", "Unbekanntes Fach"]
    lessons = fallback_lessons(config, date(2026, 7, 6))
    assert [l.subject.name for l in lessons] == ["Mathematik"]


def test_fallback_two_week_rotation(config):
    config.fallback_week = {
        "even": {"mon": ["Mathematik"]},
        "odd": {"mon": ["Deutsch"]},
    }
    even_monday = date(2026, 7, 6)   # KW 28
    odd_monday = date(2026, 7, 13)   # KW 29
    assert [l.subject.name for l in fallback_lessons(config, even_monday)] == ["Mathematik"]
    assert [l.subject.name for l in fallback_lessons(config, odd_monday)] == ["Deutsch"]


def test_missing_credentials_fall_back(config):
    lessons, note = get_todays_lessons(config, Secrets(), date(2026, 7, 6))
    assert [l.subject.name for l in lessons] == ["Mathematik", "Deutsch"]
    assert "WebUntis" in note


def test_unique_subjects_keeps_order(config):
    mathe = config.subjects[1]
    sowi = config.subjects[0]
    lessons = [Lesson(subject=mathe), Lesson(subject=sowi), Lesson(subject=mathe)]
    assert [s.name for s in unique_subjects(lessons)] == ["Mathematik", "Sozialwissenschaften"]


def test_untis_code_matching(config):
    assert config.subject_by_untis("sw").name == "Sozialwissenschaften"
    assert config.subject_by_untis("SOWI").name == "Sozialwissenschaften"
    assert config.subject_by_untis("PH") is None
