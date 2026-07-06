from pathlib import Path

import pytest

from betternotes.config import AppConfig, SubjectConfig


class FakeTextBlock:
    type = "text"

    def __init__(self, text: str):
        self.text = text


class FakeResponse:
    def __init__(self, text: str):
        self.content = [FakeTextBlock(text)]


class FakeMessages:
    def __init__(self, reply: str):
        self.reply = reply
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.reply)


class FakeAnthropic:
    """Minimaler Ersatz für anthropic.Anthropic in Tests."""

    def __init__(self, reply: str = "Antwort"):
        self.messages = FakeMessages(reply)


@pytest.fixture
def fake_claude():
    return FakeAnthropic()


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
