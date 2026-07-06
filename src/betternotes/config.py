"""Konfiguration: config.yaml (Einstellungen) + Umgebungsvariablen (Geheimnisse)."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class SubjectConfig(BaseModel):
    untis: list[str]
    goodnotes: list[str]
    name: str
    news: bool = False

    def matches_untis(self, code: str) -> bool:
        return code.strip().casefold() in (u.casefold() for u in self.untis)


class DriveConfig(BaseModel):
    backup_folder: str = "GoodNotes"


class NewsConfig(BaseModel):
    days_back: int = 7
    count: int = 5
    rss_fallbacks: list[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    timezone: str = "Europe/Berlin"
    send_hour: int = 6
    recipient: str
    subjects: list[SubjectConfig]
    fallback_week: dict[str, list[str]] = Field(default_factory=dict)
    drive: DriveConfig = Field(default_factory=DriveConfig)
    news: NewsConfig = Field(default_factory=NewsConfig)
    max_pages_per_file: int = 12
    model: str = "claude-sonnet-5"

    def subject_by_name(self, name: str) -> SubjectConfig | None:
        for s in self.subjects:
            if s.name.casefold() == name.strip().casefold():
                return s
        return None

    def subject_by_untis(self, code: str) -> SubjectConfig | None:
        for s in self.subjects:
            if s.matches_untis(code):
                return s
        return None


class Secrets(BaseModel):
    anthropic_api_key: str = ""
    gdrive_service_account_json: str = ""
    webuntis_server: str = ""
    webuntis_school: str = ""
    webuntis_user: str = ""
    webuntis_password: str = ""
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""

    @classmethod
    def from_env(cls) -> "Secrets":
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            gdrive_service_account_json=os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON", ""),
            webuntis_server=os.environ.get("WEBUNTIS_SERVER", ""),
            webuntis_school=os.environ.get("WEBUNTIS_SCHOOL", ""),
            webuntis_user=os.environ.get("WEBUNTIS_USER", ""),
            webuntis_password=os.environ.get("WEBUNTIS_PASSWORD", ""),
            smtp_host=os.environ.get("SMTP_HOST", ""),
            smtp_port=int(os.environ.get("SMTP_PORT", "465")),
            smtp_user=os.environ.get("SMTP_USER", ""),
            smtp_password=os.environ.get("SMTP_PASSWORD", ""),
        )


def load_config(path: str | Path = "config.yaml") -> AppConfig:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return AppConfig.model_validate(data)
