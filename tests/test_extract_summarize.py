from betternotes.extract import extract_text
from betternotes.models import NewDocument
from betternotes.summarize import prep_only, summarize_subject


def _doc(path):
    return NewDocument(
        file_id="x", name=path.name, drive_path=path.name,
        modified_time="2026-07-05T10:00:00Z", local_path=path,
    )


def test_typed_pdf_uses_embedded_text(config, fake_claude, typed_pdf):
    text = extract_text(fake_claude, config, _doc(typed_pdf))
    assert "Ableitung" in text
    assert fake_claude.messages.calls == []  # kein Vision-Call nötig


def test_scanned_pdf_goes_to_vision(config, fake_claude, tmp_path):
    import fitz

    path = tmp_path / "handschrift.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.draw_line((72, 100), (300, 140))  # nur Striche, kein Text
    pdf.save(path)
    pdf.close()

    fake_claude.messages.reply = "Transkribierter Text (unleserlich?)"
    text = extract_text(fake_claude, config, _doc(path))
    assert text == "Transkribierter Text (unleserlich?)"
    (call,) = fake_claude.messages.calls
    assert any(part["type"] == "image" for part in call["messages"][0]["content"])


def test_summarize_passes_previous_summary(config, fake_claude):
    subject = config.subjects[1]  # Mathematik
    summarize_subject(fake_claude, config, subject, ["Neue Notizen"], "Alter Stand")
    (call,) = fake_claude.messages.calls
    prompt = call["messages"][0]["content"]
    assert "Alter Stand" in prompt
    assert "Neue Notizen" in prompt
    assert "Fachbegriff" in prompt  # Klammer-Erklärungen sind Teil des Prompts


def test_prep_only_without_history_needs_no_api(config, fake_claude):
    subject = config.subjects[1]
    text = prep_only(fake_claude, config, subject, "")
    assert "keine Notizen" in text
    assert fake_claude.messages.calls == []
