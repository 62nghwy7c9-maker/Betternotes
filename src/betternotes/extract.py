"""Text aus Goodnotes-Backup-PDFs holen.

Getippte Notizen enthalten echten PDF-Text; Handschrift besteht nur aus Strichen
und wird als Bild an Claude Vision gegeben.
"""

from __future__ import annotations

import base64
import logging

from .config import AppConfig
from .models import NewDocument
from . import prompts

log = logging.getLogger(__name__)

RENDER_DPI = 150
# Ab so vielen Zeichen pro Seite gilt die Seite als "getippt" (kein Vision nötig).
MIN_EMBEDDED_CHARS_PER_PAGE = 40


def extract_text(client, config: AppConfig, doc: NewDocument) -> str:
    """Text der letzten max_pages_per_file Seiten – eingebettet oder via Claude Vision."""
    import fitz  # PyMuPDF

    assert doc.local_path is not None, "Dokument wurde nicht heruntergeladen"
    pdf = fitz.open(doc.local_path)
    try:
        first = max(0, pdf.page_count - config.max_pages_per_file)
        pages = [pdf[i] for i in range(first, pdf.page_count)]

        embedded = [page.get_text().strip() for page in pages]
        if all(len(t) >= MIN_EMBEDDED_CHARS_PER_PAGE for t in embedded) and embedded:
            log.info("%s: eingebetteter Text genügt (%d Seiten).", doc.name, len(pages))
            return "\n\n".join(embedded)

        images = []
        zoom = RENDER_DPI / 72
        for page in pages:
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            images.append(pix.tobytes("png"))
    finally:
        pdf.close()

    log.info("%s: sende %d Seiten an Claude Vision.", doc.name, len(images))
    content: list[dict] = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.standard_b64encode(png).decode("ascii"),
            },
        }
        for png in images
    ]
    content.append({"type": "text", "text": "Transkribiere diese Notiz-Seiten."})

    response = client.messages.create(
        model=config.model,
        max_tokens=4096,
        system=prompts.TRANSCRIBE_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
