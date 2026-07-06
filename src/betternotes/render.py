"""Digest → HTML (Jinja2) → PDF (WeasyPrint)."""

from __future__ import annotations

import logging
from pathlib import Path

import markdown as md
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from .models import Digest

log = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

_WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def _md(text: str) -> Markup:
    return Markup(md.markdown(text, extensions=["tables", "sane_lists"]))


def render_html(digest: Digest) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["md"] = _md
    template = env.get_template("digest.html.j2")
    css = (TEMPLATE_DIR / "digest.css").read_text(encoding="utf-8")
    weekday = _WEEKDAYS[digest.date.weekday()]
    return template.render(
        digest=digest,
        css=css,
        weekday=weekday,
        date_str=digest.date.strftime("%d.%m.%Y"),
    )


def html_to_pdf(html: str, out_path: str | Path) -> Path | None:
    """PDF schreiben; gibt None zurück, wenn WeasyPrint (Systemlibs) fehlt."""
    try:
        from weasyprint import HTML
    except Exception as exc:  # noqa: BLE001 - fehlende Systemlibs (pango etc.)
        log.warning("WeasyPrint nicht verfügbar (%s) – es wird kein PDF erzeugt.", exc)
        return None
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(out_path)
    return out_path


def subject_list(digest: Digest) -> str:
    return ", ".join(s.subject.name for s in digest.sections)
