"""Dropbox-Ingest: neue/geänderte Goodnotes-Backup-PDFs finden und laden.

Goodnotes' Auto-Backup legt PDFs unter /<backup_folder> in Dropbox ab.
Einmalige Autorisierung über `betternotes dropbox-auth` (Refresh-Token).
"""

from __future__ import annotations

import fnmatch
import logging
from datetime import timezone
from pathlib import Path

from .config import AppConfig, Secrets, SubjectConfig
from .models import NewDocument
from .state import State

log = logging.getLogger(__name__)


def build_dropbox_client(secrets: Secrets):
    import dropbox

    return dropbox.Dropbox(
        app_key=secrets.dropbox_app_key,
        app_secret=secrets.dropbox_app_secret,
        oauth2_refresh_token=secrets.dropbox_refresh_token,
    )


def match_subject(config: AppConfig, rel_path: str, name: str) -> SubjectConfig | None:
    """Ordnet eine Backup-Datei über die goodnotes-Muster einem Fach zu.

    Verglichen wird jede Pfadkomponente (Ordnernamen), der Dateiname und der
    Dateiname ohne Endung.
    """
    parts = [p for p in rel_path.split("/") if p] + [name, Path(name).stem]
    for subject in config.subjects:
        for pattern in subject.goodnotes:
            for part in parts:
                if fnmatch.fnmatch(part.casefold(), pattern.casefold()):
                    return subject
    return None


def _iter_entries(dbx, root: str):
    result = dbx.files_list_folder(root, recursive=True)
    while True:
        yield from result.entries
        if not result.has_more:
            return
        result = dbx.files_list_folder_continue(result.cursor)


def scan_new_documents(dbx, config: AppConfig, state: State) -> list[NewDocument]:
    """Alle PDFs unterhalb des Backup-Ordners, die neuer sind als der letzte Lauf."""
    from dropbox.exceptions import ApiError
    from dropbox.files import FileMetadata

    root = "/" + config.storage.backup_folder.strip("/")
    try:
        entries = list(_iter_entries(dbx, root))
    except ApiError as exc:
        log.warning(
            "Backup-Ordner '%s' nicht lesbar (%s) – ist das Goodnotes-Auto-Backup "
            "nach Dropbox aktiv?",
            root,
            exc,
        )
        return []

    new_docs: list[NewDocument] = []
    for entry in entries:
        if not isinstance(entry, FileMetadata):
            continue
        if not entry.name.casefold().endswith(".pdf"):
            continue
        modified = entry.server_modified.replace(tzinfo=timezone.utc).isoformat()
        known = state.files.get(entry.id)
        if known and known.modified_time >= modified:
            continue
        # Pfad relativ zum Backup-Ordner, z.B. "Mathe Q2/Analysis.pdf"
        rel_path = entry.path_display.lstrip("/").split("/", 1)
        rel_path = rel_path[1] if len(rel_path) > 1 else rel_path[0]
        new_docs.append(
            NewDocument(
                file_id=entry.id,
                name=entry.name,
                drive_path=rel_path,
                modified_time=modified,
                subject=match_subject(config, rel_path, entry.name),
            )
        )
    return new_docs


def download_documents(dbx, docs: list[NewDocument], target_dir: str | Path) -> None:
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        _, response = dbx.files_download(f"id:{doc.file_id}" if not doc.file_id.startswith("id:") else doc.file_id)
        local = target_dir / (doc.file_id.replace("id:", "") + ".pdf")
        local.write_bytes(response.content)
        doc.local_path = local
        log.info(
            "Heruntergeladen: %s (%s)",
            doc.drive_path,
            doc.subject.name if doc.subject else "ohne Fach",
        )


def run_auth_wizard() -> int:
    """Interaktive Einmal-Einrichtung: führt zum Dropbox-Refresh-Token.

    Voraussetzung: eine eigene Dropbox-App unter https://www.dropbox.com/developers/apps
    (Scoped access, Full Dropbox, Berechtigungen files.metadata.read + files.content.read).
    """
    from dropbox import Dropbox, DropboxOAuth2FlowNoRedirect

    print("Betternotes – Dropbox-Einrichtung")
    print("=" * 40)
    print("Falls noch nicht geschehen: unter https://www.dropbox.com/developers/apps")
    print('eine App anlegen ("Scoped access" + "Full Dropbox") und im Reiter')
    print('"Permissions" die Haken bei files.metadata.read und files.content.read setzen.')
    print()
    app_key = input("App key (aus der App-Übersicht): ").strip()
    app_secret = input("App secret ('Show' klicken): ").strip()

    flow = DropboxOAuth2FlowNoRedirect(app_key, consumer_secret=app_secret, token_access_type="offline")
    print()
    print("1. Öffne diesen Link im Browser und klicke auf 'Erlauben':")
    print("   " + flow.start())
    print("2. Kopiere den angezeigten Code hierher.")
    code = input("Code: ").strip()
    result = flow.finish(code)

    account = Dropbox(
        app_key=app_key, app_secret=app_secret, oauth2_refresh_token=result.refresh_token
    ).users_get_current_account()
    print()
    print(f"✅ Verbunden mit dem Dropbox-Konto von {account.name.display_name}.")
    print()
    print("Trage diese 3 Secrets in GitHub ein (Settings → Secrets → Actions):")
    print(f"  DROPBOX_APP_KEY       = {app_key}")
    print(f"  DROPBOX_APP_SECRET    = {app_secret}")
    print(f"  DROPBOX_REFRESH_TOKEN = {result.refresh_token}")
    return 0
