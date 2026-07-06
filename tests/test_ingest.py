from datetime import datetime
from types import SimpleNamespace

from dropbox.files import FileMetadata, FolderMetadata

from betternotes.ingest import match_subject, scan_new_documents
from betternotes.state import FileState, State


def test_match_by_folder(config):
    subject = match_subject(config, "Mathe Q2/Kurvendiskussion.pdf", "Kurvendiskussion.pdf")
    assert subject is not None and subject.name == "Mathematik"


def test_match_by_filename(config):
    subject = match_subject(config, "Sowi Klausurvorbereitung.pdf", "Sowi Klausurvorbereitung.pdf")
    assert subject is not None and subject.name == "Sozialwissenschaften"


def test_match_is_case_insensitive(config):
    subject = match_subject(config, "MATHE/notizen.pdf", "notizen.pdf")
    assert subject is not None and subject.name == "Mathematik"


def test_no_match(config):
    assert match_subject(config, "Privat/Einkaufsliste.pdf", "Einkaufsliste.pdf") is None


def _file(entry_id, path, modified):
    return FileMetadata(
        name=path.rsplit("/", 1)[-1],
        id=entry_id,
        path_display=path,
        server_modified=modified,
    )


class FakeDropbox:
    def __init__(self, entries):
        self._entries = entries

    def files_list_folder(self, path, recursive=False):
        assert path == "/GoodNotes" and recursive
        return SimpleNamespace(entries=self._entries, has_more=False, cursor="c")


def test_scan_skips_known_and_maps_subjects(config):
    entries = [
        FolderMetadata(name="Mathe Q2", id="id:folder", path_display="/GoodNotes/Mathe Q2"),
        _file("id:sowi", "/GoodNotes/Sowi EU.pdf", datetime(2026, 7, 5, 10, 0)),
        _file("id:old", "/GoodNotes/Sowi Alt.pdf", datetime(2026, 7, 1, 10, 0)),
        _file("id:mathe", "/GoodNotes/Mathe Q2/Analysis.pdf", datetime(2026, 7, 5, 9, 0)),
        _file("id:txt", "/GoodNotes/Notiz.txt", datetime(2026, 7, 5, 10, 0)),
    ]
    state = State(
        files={"id:old": FileState(modified_time="2026-07-01T10:00:00+00:00", subject="Sozialwissenschaften")}
    )
    docs = scan_new_documents(FakeDropbox(entries), config, state)

    by_id = {d.file_id: d for d in docs}
    assert set(by_id) == {"id:sowi", "id:mathe"}
    assert by_id["id:sowi"].subject.name == "Sozialwissenschaften"
    assert by_id["id:mathe"].subject.name == "Mathematik"  # über Ordnernamen "Mathe Q2"
    assert by_id["id:mathe"].drive_path == "Mathe Q2/Analysis.pdf"
