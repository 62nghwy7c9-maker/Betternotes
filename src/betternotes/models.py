"""Gemeinsame Datentypen der Pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import SubjectConfig


@dataclass
class Lesson:
    subject: SubjectConfig
    start: datetime | None = None
    end: datetime | None = None


@dataclass
class NewDocument:
    file_id: str
    name: str
    drive_path: str
    modified_time: str
    subject: SubjectConfig | None = None
    local_path: Path | None = None
    text: str = ""


@dataclass
class SubjectSection:
    subject: SubjectConfig
    summary_md: str          # "Rückblick" + "Wichtig für die nächste Stunde"
    news_md: str = ""        # nur für News-Fächer (Sowi)
    had_new_notes: bool = False


@dataclass
class Digest:
    date: datetime
    lessons: list[Lesson]
    sections: list[SubjectSection]
    misc_md: str = ""        # nicht zuordenbare neue Notizen
    notes: list[str] = field(default_factory=list)  # Hinweise (z.B. Untis-Fallback aktiv)
