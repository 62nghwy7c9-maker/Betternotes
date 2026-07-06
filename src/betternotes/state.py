"""Persistenter Zustand: was wurde schon verarbeitet, wann zuletzt gesendet."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_STATE_PATH = Path("state/state.json")


class FileState(BaseModel):
    modified_time: str = ""
    subject: str = ""
    last_summary: str = ""


class State(BaseModel):
    last_sent_date: str = ""                      # ISO-Datum des letzten Versands
    files: dict[str, FileState] = Field(default_factory=dict)
    subject_summaries: dict[str, str] = Field(default_factory=dict)


def load_state(path: str | Path = DEFAULT_STATE_PATH) -> State:
    path = Path(path)
    if not path.exists():
        return State()
    return State.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_state(state: State, path: str | Path = DEFAULT_STATE_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        state.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
