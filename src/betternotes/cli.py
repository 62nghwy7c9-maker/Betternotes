"""CLI und Pipeline-Orchestrierung.

Ablauf jeden Morgen (vor dem Versand):
  1. Prüfen, ob jetzt gesendet werden soll (Zeitfenster + noch nicht gesendet).
  2. Stundenplan des Tages aus WebUntis holen -> nur die heutigen Fächer.
  3. Für diese Fächer die seit dem letzten Digest neuen Goodnotes-Dokumente
     aus dem Drive-Backup einsammeln und auswerten.
  4. Dokument bauen (inkl. Sowi-Nachrichten, falls Sowi heute) und mailen.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import extract, ingest, mailer, news, render, summarize
from .config import AppConfig, Secrets, load_config
from .guard import should_run
from .models import Digest, SubjectSection
from .state import FileState, State, load_state, save_state
from .timetable import get_todays_lessons, unique_subjects

log = logging.getLogger("betternotes")

_WEEKDAYS_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def build_digest(
    config: AppConfig,
    secrets: Secrets,
    state: State,
    day: date,
    workdir: Path,
) -> Digest | None:
    """Kernpipeline; None, wenn heute kein Unterricht ist."""
    lessons, timetable_note = get_todays_lessons(config, secrets, day)
    if not lessons:
        log.info("Heute (%s) kein Unterricht laut Stundenplan – kein Digest.", day)
        return None
    subjects_today = unique_subjects(lessons)
    log.info("Fächer heute: %s", ", ".join(s.name for s in subjects_today))

    # Neue Goodnotes-Dokumente einsammeln (nur für heutige Fächer herunterladen;
    # Notizen anderer Fächer bleiben bis zu deren Tag unangetastet im State).
    drive = ingest.build_drive_service(secrets)
    all_new = ingest.scan_new_documents(drive, config, state)
    today_names = {s.name for s in subjects_today}
    relevant = [d for d in all_new if d.subject and d.subject.name in today_names]
    unmatched = [d for d in all_new if d.subject is None]
    ingest.download_documents(drive, relevant, workdir / "pdf")

    import anthropic

    client = anthropic.Anthropic(api_key=secrets.anthropic_api_key)

    sections: list[SubjectSection] = []
    for subject in subjects_today:
        subject_docs = [d for d in relevant if d.subject is subject or (d.subject and d.subject.name == subject.name)]
        previous = state.subject_summaries.get(subject.name, "")
        if subject_docs:
            texts = []
            for doc in subject_docs:
                doc.text = extract.extract_text(client, config, doc)
                texts.append(f"[Dokument: {doc.drive_path}]\n{doc.text}")
            summary = summarize.summarize_subject(client, config, subject, texts, previous)
            had_new = True
        else:
            summary = summarize.prep_only(client, config, subject, previous)
            had_new = False

        news_md = ""
        if subject.news:
            log.info("%s ist heute – hole die Top-%d-Nachrichten.", subject.name, config.news.count)
            news_md = news.top_news_markdown(client, config, day)

        sections.append(
            SubjectSection(subject=subject, summary_md=summary, news_md=news_md, had_new_notes=had_new)
        )

        # State fortschreiben (wird nur bei echtem Versand gespeichert).
        if had_new:
            state.subject_summaries[subject.name] = summary
            for doc in subject_docs:
                state.files[doc.file_id] = FileState(
                    modified_time=doc.modified_time, subject=subject.name
                )

    misc_md = ""
    if unmatched:
        lines = [
            "Diese neuen Dateien konnten keinem Fach zugeordnet werden "
            "(Muster in config.yaml prüfen):",
            "",
        ]
        lines += [f"- {d.drive_path}" for d in unmatched]
        misc_md = "\n".join(lines)
        for doc in unmatched:
            state.files[doc.file_id] = FileState(modified_time=doc.modified_time, subject="")

    notes = [timetable_note] if timetable_note else []
    return Digest(
        date=datetime.combine(day, datetime.min.time()),
        lessons=lessons,
        sections=sections,
        misc_md=misc_md,
        notes=notes,
    )


def run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    secrets = Secrets.from_env()
    state = load_state(args.state)

    now_utc = datetime.now(timezone.utc)
    force = args.force or args.dry_run or bool(args.date)
    ok, reason = should_run(now_utc, config, state, force=force)
    log.info("Guard: %s", reason)
    if not ok:
        return 0

    day = date.fromisoformat(args.date) if args.date else now_utc.astimezone(
        ZoneInfo(config.timezone)
    ).date()

    try:
        with tempfile.TemporaryDirectory(prefix="betternotes-") as tmp:
            digest = build_digest(config, secrets, state, day, Path(tmp))
            if digest is None:
                return 0

            html = render.render_html(digest)
            out_dir = Path(args.output) if args.output else Path(tmp)
            out_dir.mkdir(parents=True, exist_ok=True)
            html_path = out_dir / f"digest-{day.isoformat()}.html"
            html_path.write_text(html, encoding="utf-8")
            pdf_path = render.html_to_pdf(html, out_dir / f"Tagesvorbereitung-{day.isoformat()}.pdf")

            if args.dry_run:
                log.info("Dry-Run: HTML unter %s, PDF unter %s – keine Mail, kein State-Update.", html_path, pdf_path)
                return 0

            subject_line = (
                f"📚 Tagesvorbereitung {_WEEKDAYS_SHORT[day.weekday()]} {day:%d.%m.} – "
                + render.subject_list(digest)
            )
            mailer.send_digest(secrets, config.recipient, subject_line, html, pdf_path)

            local_today = now_utc.astimezone(ZoneInfo(config.timezone)).date()
            state.last_sent_date = local_today.isoformat()
            save_state(state, args.state)
            return 0
    except Exception as exc:  # noqa: BLE001 - ein stiller Ausfall wäre schlimmer
        log.exception("Pipeline fehlgeschlagen.")
        if not args.dry_run:
            mailer.send_error(secrets, config.recipient, f"{type(exc).__name__}: {exc}")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="betternotes", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="Tages-Digest erstellen und versenden")
    run_parser.add_argument("--config", default="config.yaml")
    run_parser.add_argument("--state", default="state/state.json")
    run_parser.add_argument("--date", help="Stichtag YYYY-MM-DD (Standard: heute)")
    run_parser.add_argument("--dry-run", action="store_true", help="keine Mail, kein State-Update")
    run_parser.add_argument("--output", help="Ausgabeverzeichnis für HTML/PDF")
    run_parser.add_argument("--force", action="store_true", help="Zeitfenster/Dedupe ignorieren")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.command == "run":
        return run(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
