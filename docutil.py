"""Safe upload handling: size cap, real file-type check (magic bytes), page cap. Reads PDF, Word (.docx), TXT and MD."""
from __future__ import annotations
import io, zipfile
import config

ALLOWED = ("pdf", "docx", "txt", "md")
MAX_UNZIPPED_BYTES = 120 * 1024 * 1024   # a .docx is a zip; refuse "zip bombs"


def _docx_text(data: bytes):
    if not data.startswith(b"PK"):
        return None, "That file is not a real Word document."
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_UNZIPPED_BYTES or "word/document.xml" not in z.namelist():
                return None, "Could not read that Word document."
        from docx import Document
        d = Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for tbl in d.tables:
            for row in tbl.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        return "\n".join(parts), None
    except Exception:
        return None, "Could not read that Word document."


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
    elif name.endswith(".docx"):
        text, err = _docx_text(data)
        if err:
            return None, err
    elif name.endswith((".txt", ".md")):
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return None, "Text files must be UTF-8."
    else:
        return None, "Only PDF, Word (.docx), TXT and MD files are allowed."
    if not text.strip():
        return None, "No readable text found (scanned PDFs are not supported)."
    return text, None
