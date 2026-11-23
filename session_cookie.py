"""Keeps you logged in across page refreshes.

The browser stores only a random session token. The server stores a SHA-256 hash of it and still applies
the idle / absolute timeouts, so a copied cookie stops working when the session ends or you log out.
Limitation: Streamlit cannot set HttpOnly cookies itself (that needs a reverse proxy), so the cookie is set
from a tiny script with SameSite=Strict (and Secure on HTTPS).
"""
from __future__ import annotations
import re
from typing import Optional
import streamlit as st
import streamlit.components.v1 as components
import config

NAME = "lv_session"
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{20,100}$")


def read() -> Optional[str]:
    try:
        tok = st.context.cookies.get(NAME)
    except Exception:
        return None
    return tok if tok and _TOKEN_RE.match(tok) else None


def _https() -> bool:
    try:
        return (st.context.headers.get("X-Forwarded-Proto") == "https"
                or str(getattr(st.context, "url", "")).startswith("https"))
    except Exception:
        return False


def _set(value: str, max_age: int):
    secure = "; Secure" if _https() else ""
    components.html(
        f"<script>window.parent.document.cookie = "
        f"'{NAME}={value}; Max-Age={max_age}; Path=/; SameSite=Strict{secure}';</script>", height=0)


def write(token: str):
    if _TOKEN_RE.match(token):  # never inject anything that isn't a token into the script
        _set(token, config.SESSION_MAX_SECONDS)


def clear():
    _set("", 0)


def client_info():
    """(user_agent, ip) for the sessions list and new-device alerts."""
    try:
        ua = (st.context.headers.get("User-Agent") or "")[:300]
    except Exception:
        ua = ""
    try:
        ip = getattr(st.context, "ip_address", None) or ""
    except Exception:
        ip = ""
    return ua, ip


def describe_device(ua: str) -> str:
    """'Chrome on macOS' style label from a user agent."""
    ua = ua or ""
    browser = next((n for k, n in (("Edg/", "Edge"), ("OPR/", "Opera"), ("Firefox/", "Firefox"),
                                   ("Chrome/", "Chrome"), ("Safari/", "Safari")) if k in ua), "Browser")
    osname = next((n for k, n in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"),
                                  ("Mac OS X", "macOS"), ("Windows", "Windows"), ("Linux", "Linux")) if k in ua), "")
    return f"{browser} on {osname}" if osname else browser
