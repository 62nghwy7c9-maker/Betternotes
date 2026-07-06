from datetime import datetime
from email.message import EmailMessage

import pytest

import betternotes.mailer as mailer_mod
from betternotes.config import Secrets
from betternotes.mailer import send_digest
from betternotes.models import Digest, Lesson, SubjectSection
from betternotes.render import html_to_pdf, render_html, subject_list


@pytest.fixture
def digest(config):
    sowi, mathe = config.subjects[0], config.subjects[1]
    return Digest(
        date=datetime(2026, 7, 6),
        lessons=[Lesson(subject=mathe), Lesson(subject=sowi)],
        sections=[
            SubjectSection(
                subject=mathe,
                summary_md="### Rückblick: letzte Stunde\n- Ableitung (momentane Steigung einer Funktion)",
                had_new_notes=True,
            ),
            SubjectSection(
                subject=sowi,
                summary_md="### Wichtig für die nächste Stunde\n- EU-Gipfel nachlesen",
                news_md="#### Meldung (05.07.2026)\nInflation (allgemeiner Anstieg der Preise) sinkt.",
                had_new_notes=False,
            ),
        ],
        misc_md="- Privat/Skizze.pdf",
        notes=["WebUntis war nicht erreichbar."],
    )


def test_render_html(digest):
    html = render_html(digest)
    assert "Tagesvorbereitung – Montag, 06.07.2026" in html
    assert "Mathematik" in html and "Sozialwissenschaften" in html
    assert "momentane Steigung" in html
    assert "Nachrichten der Woche" in html
    assert "Keine neuen Notizen" in html          # Hinweis für Sowi ohne neue Notizen
    assert "WebUntis war nicht erreichbar" in html


def test_subject_list(digest):
    assert subject_list(digest) == "Mathematik, Sozialwissenschaften"


def test_html_to_pdf(digest, tmp_path):
    pytest.importorskip("weasyprint")
    try:
        result = html_to_pdf(render_html(digest), tmp_path / "out.pdf")
    except OSError as exc:  # fehlende Systembibliotheken (pango) in der CI
        pytest.skip(f"WeasyPrint-Systemlibs fehlen: {exc}")
    if result is None:
        pytest.skip("WeasyPrint nicht verfügbar")
    assert result.read_bytes()[:5] == b"%PDF-"


def test_send_digest_builds_multipart_mail(monkeypatch, tmp_path):
    sent: list[EmailMessage] = []
    monkeypatch.setattr(mailer_mod, "_send", lambda secrets, msg: sent.append(msg))

    pdf = tmp_path / "anhang.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    secrets = Secrets(smtp_user="absender@gmx.de")
    send_digest(secrets, "empfaenger@gmail.com", "Betreff", "<p>Hallo</p>", pdf)

    (msg,) = sent
    assert msg["To"] == "empfaenger@gmail.com"
    assert msg["Subject"] == "Betreff"
    parts = [p.get_content_type() for p in msg.walk()]
    assert "text/html" in parts
    assert "application/pdf" in parts
