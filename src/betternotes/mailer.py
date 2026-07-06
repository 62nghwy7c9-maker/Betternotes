"""E-Mail-Versand über SMTP (SSL), inkl. Fehler-Mail bei Pipeline-Problemen."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from .config import Secrets

log = logging.getLogger(__name__)


def _send(secrets: Secrets, message: EmailMessage) -> None:
    with smtplib.SMTP_SSL(secrets.smtp_host, secrets.smtp_port) as smtp:
        smtp.login(secrets.smtp_user, secrets.smtp_password)
        smtp.send_message(message)


def send_digest(
    secrets: Secrets,
    recipient: str,
    subject: str,
    html_body: str,
    pdf_path: Path | None,
) -> None:
    message = EmailMessage()
    message["From"] = secrets.smtp_user
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(
        "Deine Tagesvorbereitung ist angehängt. Diese Mail ist als HTML formatiert – "
        "bitte in einem HTML-fähigen Mailprogramm öffnen."
    )
    message.add_alternative(html_body, subtype="html")
    if pdf_path is not None:
        message.add_attachment(
            pdf_path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=pdf_path.name,
        )
    _send(secrets, message)
    log.info("Digest-Mail an %s gesendet.", recipient)


def send_error(secrets: Secrets, recipient: str, error_text: str) -> None:
    """Kurze Fehler-Mail, damit ein Ausfall nicht unbemerkt bleibt."""
    try:
        message = EmailMessage()
        message["From"] = secrets.smtp_user
        message["To"] = recipient
        message["Subject"] = "⚠️ Betternotes: Tagesvorbereitung konnte nicht erstellt werden"
        message.set_content(
            "Beim Erstellen der heutigen Tagesvorbereitung ist ein Fehler aufgetreten:\n\n"
            f"{error_text}\n\n"
            "Details stehen im Log des GitHub-Actions-Laufs."
        )
        _send(secrets, message)
    except Exception:  # noqa: BLE001 - Fehler-Mail darf nie selbst crashen
        log.exception("Auch die Fehler-Mail konnte nicht gesendet werden.")
