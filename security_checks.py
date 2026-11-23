"""Breached-password check using Have I Been Pwned's k-anonymity API.

Only the first 5 characters of the password's SHA-1 hash leave the server; the full password and full hash never do.
If the service can't be reached, signup is NOT blocked (fail-open) - the other password rules still apply.
"""
from __future__ import annotations
import hashlib
from typing import Optional
import requests
import config


def pwned_count(password: str) -> Optional[int]:
    """How many times this password appears in known breaches. None = couldn't check."""
    if not config.HIBP_CHECK:
        return None
    digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).hexdigest().upper()  # HIBP protocol
    prefix, suffix = digest[:5], digest[5:]
    try:
        r = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}",
                         headers={"Add-Padding": "true", "User-Agent": "LawVault-student-project"}, timeout=4)
        r.raise_for_status()
    except Exception:
        return None
    for line in r.text.splitlines():
        h, _, n = line.partition(":")
        if h == suffix:
            return int(n or 0)
    return 0


def breach_error(password: str) -> Optional[str]:
    n = pwned_count(password)
    if n:
        return f"This password has appeared in {n:,} known data breaches. Please choose a different one."
    return None
