"""Zusammenfassung je Fach: Rückblick + Vorbereitung auf die nächste Stunde."""

from __future__ import annotations

import logging

from .config import AppConfig, SubjectConfig
from . import prompts

log = logging.getLogger(__name__)


def _ask(client, config: AppConfig, system: str, prompt: str) -> str:
    response = client.messages.create(
        model=config.model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()


def summarize_subject(
    client,
    config: AppConfig,
    subject: SubjectConfig,
    note_texts: list[str],
    previous_summary: str,
) -> str:
    """Markdown mit '### Rückblick' + '### Wichtig für die nächste Stunde'."""
    previous_block = (
        prompts.SUMMARIZE_PREVIOUS_BLOCK.format(previous=previous_summary)
        if previous_summary
        else ""
    )
    prompt = prompts.SUMMARIZE_TEMPLATE.format(
        subject=subject.name,
        previous_block=previous_block,
        notes="\n\n---\n\n".join(note_texts),
    )
    return _ask(client, config, prompts.SUMMARIZE_SYSTEM, prompt)


def prep_only(client, config: AppConfig, subject: SubjectConfig, previous_summary: str) -> str:
    """Nur Vorbereitung, wenn es keine neuen Notizen gibt, aber alter Stand existiert."""
    if not previous_summary:
        return (
            "_Für dieses Fach liegen noch keine Notizen im Goodnotes-Backup – "
            "sobald welche vorhanden sind, erscheint hier die Vorbereitung._"
        )
    prompt = prompts.PREP_ONLY_TEMPLATE.format(subject=subject.name, previous=previous_summary)
    return _ask(client, config, prompts.SUMMARIZE_SYSTEM, prompt)
