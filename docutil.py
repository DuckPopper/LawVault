"""Safe upload handling: size cap, real file-type check (magic bytes), page cap."""
from __future__ import annotations
import io
import config


def extract_text(filename: str, data: bytes):
    """Returns (text, error)."""
    if len(data) > config.MAX_UPLOAD_BYTES:
        return None, f"File too large (max {config.MAX_UPLOAD_MB} MB)."
    name = filename.lower()
    if name.endswith(".pdf"):
        if not data.startswith(b"%PDF"):
            return None, "That file is not a real PDF."
        try:
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(data))
            if r.is_encrypted:
                return None, "Encrypted PDFs are not supported."
            if len(r.pages) > config.MAX_PDF_PAGES:
                return None, f"PDF too long (max {config.MAX_PDF_PAGES} pages)."
            text = "\n".join((p.extract_text() or "") for p in r.pages)
        except Exception:
            return None, "Could not read that PDF."
    elif name.endswith(".txt"):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return None, "Text files must be UTF-8."
    else:
        return None, "Only PDF and TXT files are allowed."
    if not text.strip():
        return None, "No readable text found (scanned PDFs are not supported)."
    return text, None
