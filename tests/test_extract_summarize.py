from betternotes.extract import extract_text
from betternotes.models import NewDocument
from betternotes.summarize import prep_only, summarize_subject


def _doc(path):
    return NewDocument(
        file_id="x", name=path.name, drive_path=path.name,
        modified_time="2026-07-05T10:00:00Z", local_path=path,
    )


def test_typed_pdf_uses_embedded_text(config, fake_llm, typed_pdf):
    text = extract_text(fake_llm, config, _doc(typed_pdf))
    assert "Ableitung" in text
    assert fake_llm.calls == []  # kein Vision-Call nötig


def test_scanned_pdf_goes_to_vision(config, fake_llm, tmp_path):
    import fitz

    path = tmp_path / "handschrift.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.draw_line((72, 100), (300, 140))  # nur Striche, kein Text
    pdf.save(path)
    pdf.close()

    fake_llm.reply = "Transkribierter Text (unleserlich?)"
    text = extract_text(fake_llm, config, _doc(path))
    assert text == "Transkribierter Text (unleserlich?)"
    (kind, _system, _prompt, images) = fake_llm.calls[0]
    assert kind == "transcribe"
    assert images and all(isinstance(img, (bytes, bytearray)) for img in images)


def test_summarize_passes_previous_summary(config, fake_llm):
    subject = config.subjects[1]  # Mathematik
    summarize_subject(fake_llm, config, subject, ["Neue Notizen"], "Alter Stand")
    (kind, _system, prompt, _images) = fake_llm.calls[0]
    assert kind == "complete"
    assert "Alter Stand" in prompt
    assert "Neue Notizen" in prompt
    assert "Fachbegriff" in prompt  # Klammer-Erklärungen sind Teil des Prompts


def test_prep_only_without_history_needs_no_api(config, fake_llm):
    subject = config.subjects[1]
    text = prep_only(fake_llm, config, subject, "")
    assert "keine Notizen" in text
    assert fake_llm.calls == []
