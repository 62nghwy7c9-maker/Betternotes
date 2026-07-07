from pathlib import Path

import pytest

from betternotes.config import AppConfig, SubjectConfig


class FakeLLM:
    """Minimaler Ersatz für LLMClient in Tests.

    Zeichnet Aufrufe auf und liefert eine feste Antwort. `calls` enthält Tupel
    (kind, system, prompt, images) – images ist None bei complete().
    """

    def __init__(self, reply: str = "Antwort"):
        self.reply = reply
        self.calls: list[tuple] = []

    def complete(self, system: str, prompt: str, max_tokens: int = 2048) -> str:
        self.calls.append(("complete", system, prompt, None))
        return self.reply

    def transcribe(self, images, system: str, prompt: str, max_tokens: int = 4096) -> str:
        self.calls.append(("transcribe", system, prompt, images))
        return self.reply


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        recipient="test@example.org",
        subjects=[
            SubjectConfig(untis=["SW", "SOWI"], goodnotes=["Sowi*"], name="Sozialwissenschaften", news=True),
            SubjectConfig(untis=["M"], goodnotes=["Mathe*", "Mathematik*"], name="Mathematik"),
            SubjectConfig(untis=["D"], goodnotes=["Deutsch*"], name="Deutsch"),
        ],
        fallback_week={"mon": ["Mathematik", "Deutsch"], "tue": []},
    )


@pytest.fixture
def typed_pdf(tmp_path) -> Path:
    """Kleines PDF mit eingebettetem (getipptem) Text als Fixture."""
    import fitz

    path = tmp_path / "Mathe Analysis.pdf"
    pdf = fitz.open()
    for i in range(2):
        page = pdf.new_page()
        page.insert_text(
            (72, 100),
            f"Seite {i + 1}: Ableitungen. Die Ableitung beschreibt die momentane "
            "Steigung einer Funktion. Beispiel: f(x) = x^2, f'(x) = 2x. "
            "Hausaufgabe: Buch S. 42 Nr. 3.",
            fontsize=11,
        )
    pdf.save(path)
    pdf.close()
    return path
