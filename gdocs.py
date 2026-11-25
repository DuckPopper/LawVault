"""Import a Google Doc by link. The doc must be shared as "Anyone with the link can view": LawVault never asks for a
Google password. Only docs.google.com export URLs built from a validated document ID are ever requested, so a pasted
link can't be used to make the server call some other address (SSRF).
"""
from __future__ import annotations
import re
from urllib.parse import urlparse
import requests
import config

_URL = re.compile(r"^https://docs\.google\.com/document/(?:u/\d+/)?d/([A-Za-z0-9_-]{20,128})(?:[/?#].*)?$")
_HOSTS = ("docs.google.com", "googleusercontent.com")      # redirects may only stay on these
MAX_BYTES = 5 * 1024 * 1024
NOT_SHARED = ("Couldn't open that document. In Google Docs choose Share, set General access to “Anyone with the link” "
              "(Viewer) and try again, or download it as .docx and upload it instead.")


def doc_id(link: str) -> str | None:
    m = _URL.match((link or "").strip())
    return m.group(1) if m else None


def _allowed(url: str) -> bool:
    p = urlparse(url)
    h = (p.hostname or "").lower()
    return p.scheme == "https" and any(h == d or h.endswith("." + d) for d in _HOSTS)


def fetch(link: str):
    """Returns (title, text, error)."""
    did = doc_id(link)
    if not did:
        return None, None, "That doesn't look like a Google Docs link (docs.google.com/document/d/…)."
    url = f"https://docs.google.com/document/d/{did}/export?format=txt"
    try:
        r = None
        for _ in range(4):                       # follow redirects by hand, staying on Google's own hosts
            r = requests.get(url, timeout=15, allow_redirects=False, stream=True,
                             headers={"User-Agent": "LawVault/1.0"})
            if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
                url = requests.compat.urljoin(url, r.headers.get("Location", ""))
                r.close()
                if not _allowed(url) or "ServiceLogin" in url:
                    return None, None, NOT_SHARED
                continue
            break
        if r is None or r.status_code != 200 or "text/plain" not in r.headers.get("Content-Type", ""):
            return None, None, NOT_SHARED
        body = b""
        for chunk in r.iter_content(65536):
            body += chunk
            if len(body) > MAX_BYTES:
                break
        r.close()
    except requests.RequestException:
        return None, None, "Couldn't reach Google Docs. Check your connection and try again."
    if len(body) > MAX_BYTES:
        return None, None, f"That document is too large (max {MAX_BYTES // 1024 // 1024} MB of text)."
    text = body.decode("utf-8", errors="replace").lstrip("﻿").replace("\r\n", "\n")
    if not text.strip():
        return None, None, "That document is empty."
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "Google Doc")
    return f"{first[:80]}.gdoc.txt".replace("/", "-"), text[:config.MAX_AI_INPUT_CHARS * 4], None
