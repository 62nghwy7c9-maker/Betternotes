"""Google-Drive-Ingest: neue/geänderte Goodnotes-Backup-PDFs finden und laden."""

from __future__ import annotations

import fnmatch
import io
import json
import logging
from pathlib import Path

from .config import AppConfig, Secrets, SubjectConfig
from .models import NewDocument
from .state import State

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def build_drive_service(secrets: Secrets):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    info = json.loads(secrets.gdrive_service_account_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def match_subject(config: AppConfig, drive_path: str, name: str) -> SubjectConfig | None:
    """Ordnet eine Backup-Datei über die goodnotes-Muster einem Fach zu.

    Verglichen wird jede Pfadkomponente (Ordnernamen) und der Dateiname.
    """
    parts = [p for p in drive_path.split("/") if p] + [name, Path(name).stem]
    for subject in config.subjects:
        for pattern in subject.goodnotes:
            for part in parts:
                if fnmatch.fnmatch(part.casefold(), pattern.casefold()):
                    return subject
    return None


def _list_folder(service, folder_id: str):
    query = f"'{folder_id}' in parents and trashed = false"
    page_token = None
    while True:
        resp = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageToken=page_token,
            )
            .execute()
        )
        yield from resp.get("files", [])
        page_token = resp.get("nextPageToken")
        if not page_token:
            return


def _find_backup_folder(service, folder_name: str) -> str | None:
    resp = (
        service.files()
        .list(
            q=(
                "mimeType = 'application/vnd.google-apps.folder' "
                f"and name = '{folder_name}' and trashed = false"
            ),
            fields="files(id, name)",
        )
        .execute()
    )
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def scan_new_documents(service, config: AppConfig, state: State) -> list[NewDocument]:
    """Alle PDFs unterhalb des Backup-Ordners, die neuer sind als der letzte Lauf."""
    root_id = _find_backup_folder(service, config.drive.backup_folder)
    if root_id is None:
        log.warning(
            "Backup-Ordner '%s' nicht gefunden – ist er mit dem Service-Account geteilt?",
            config.drive.backup_folder,
        )
        return []

    new_docs: list[NewDocument] = []
    stack: list[tuple[str, str]] = [(root_id, "")]
    while stack:
        folder_id, prefix = stack.pop()
        for entry in _list_folder(service, folder_id):
            if entry["mimeType"] == "application/vnd.google-apps.folder":
                stack.append((entry["id"], f"{prefix}{entry['name']}/"))
                continue
            if not entry["name"].casefold().endswith(".pdf"):
                continue
            known = state.files.get(entry["id"])
            if known and known.modified_time >= entry["modifiedTime"]:
                continue
            new_docs.append(
                NewDocument(
                    file_id=entry["id"],
                    name=entry["name"],
                    drive_path=prefix + entry["name"],
                    modified_time=entry["modifiedTime"],
                    subject=match_subject(config, prefix, entry["name"]),
                )
            )
    return new_docs


def download_documents(service, docs: list[NewDocument], target_dir: str | Path) -> None:
    from googleapiclient.http import MediaIoBaseDownload

    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        request = service.files().get_media(fileId=doc.file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        local = target_dir / f"{doc.file_id}.pdf"
        local.write_bytes(buffer.getvalue())
        doc.local_path = local
        log.info("Heruntergeladen: %s (%s)", doc.drive_path, doc.subject.name if doc.subject else "ohne Fach")
