from betternotes.ingest import match_subject, scan_new_documents
from betternotes.state import FileState, State


def test_match_by_folder(config):
    subject = match_subject(config, "Mathe Q2/", "Kurvendiskussion.pdf")
    assert subject is not None and subject.name == "Mathematik"


def test_match_by_filename(config):
    subject = match_subject(config, "", "Sowi Klausurvorbereitung.pdf")
    assert subject is not None and subject.name == "Sozialwissenschaften"


def test_match_is_case_insensitive(config):
    subject = match_subject(config, "MATHE/", "notizen.pdf")
    assert subject is not None and subject.name == "Mathematik"


def test_no_match(config):
    assert match_subject(config, "Privat/", "Einkaufsliste.pdf") is None


class FakeFilesResource:
    def __init__(self, pages):
        self._pages = pages

    def list(self, q="", fields="", pageToken=None):
        return FakeRequest(self._pages, q)


class FakeRequest:
    def __init__(self, pages, q):
        self._pages = pages
        self._q = q

    def execute(self):
        # Ordner-Suche vs. Inhalts-Listing anhand der Query unterscheiden
        if "vnd.google-apps.folder" in self._q and "name =" in self._q:
            return {"files": [{"id": "root1", "name": "GoodNotes"}]}
        parent = self._q.split("'")[1]
        return {"files": self._pages.get(parent, [])}


class FakeDrive:
    def __init__(self, pages):
        self._files = FakeFilesResource(pages)

    def files(self):
        return self._files


def test_scan_skips_known_and_recurses(config):
    pages = {
        "root1": [
            {"id": "f-sub", "name": "Mathe Q2", "mimeType": "application/vnd.google-apps.folder", "modifiedTime": ""},
            {"id": "d-sowi", "name": "Sowi EU.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-07-05T10:00:00Z"},
            {"id": "d-old", "name": "Sowi Alt.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-07-01T10:00:00Z"},
            {"id": "d-txt", "name": "Notiz.txt", "mimeType": "text/plain", "modifiedTime": "2026-07-05T10:00:00Z"},
        ],
        "f-sub": [
            {"id": "d-mathe", "name": "Analysis.pdf", "mimeType": "application/pdf", "modifiedTime": "2026-07-05T09:00:00Z"},
        ],
    }
    state = State(files={"d-old": FileState(modified_time="2026-07-01T10:00:00Z", subject="Sozialwissenschaften")})
    docs = scan_new_documents(FakeDrive(pages), config, state)

    by_id = {d.file_id: d for d in docs}
    assert set(by_id) == {"d-sowi", "d-mathe"}
    assert by_id["d-sowi"].subject.name == "Sozialwissenschaften"
    assert by_id["d-mathe"].subject.name == "Mathematik"  # über Ordnernamen "Mathe Q2"
    assert by_id["d-mathe"].drive_path == "Mathe Q2/Analysis.pdf"
