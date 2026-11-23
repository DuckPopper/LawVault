"""Background AI jobs.

Streamlit stops a page's script as soon as the user switches tabs, which used to kill any AI call in flight.
Calls started through here run on a process-wide thread pool instead, so they finish whichever page the user
is on. Jobs are keyed by (user_id, kind, key); the worker function must not touch `st` and must return
(value, error) like the functions in ai.py.
"""
from __future__ import annotations
import threading, time
from concurrent.futures import ThreadPoolExecutor

# Which page shows each kind of job (url_path in app.py), and how to describe it in the sidebar.
PAGE = {"chat": "qa", "review": "docs", "deadlines": "docs", "legal": "analysis"}

_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="lawvault-ai")
_lock = threading.Lock()
_jobs: dict = {}


def _safe(fn, args):
    try:
        return fn(*args)
    except Exception:
        return None, "Something went wrong while talking to the AI. Please try again."


def start(user_id: str, kind: str, key: str, fn, *args, label: str = "", meta: dict | None = None) -> bool:
    """Start fn(*args) in the background. Returns False if the same job is already running."""
    k = (user_id, kind, key)
    with _lock:
        old = _jobs.get(k)
        if old and not old["future"].done():
            return False
        _jobs[k] = dict(kind=kind, key=key, label=label, meta=meta or {}, started=time.time(),
                        notified=False, future=_pool.submit(_safe, fn, args))
    return True


def get(user_id: str, kind: str, key: str = ""):
    """The job as a dict with `running`, and once finished `value` and `error`; None if there is none."""
    with _lock:
        j = _jobs.get((user_id, kind, key))
    if not j:
        return None
    out = {k: v for k, v in j.items() if k != "future"}
    out["running"] = not j["future"].done()
    out["value"], out["error"] = (None, None) if out["running"] else j["future"].result()
    return out


def pop(user_id: str, kind: str, key: str = ""):
    with _lock:
        _jobs.pop((user_id, kind, key), None)


def mark_seen(user_id: str, kind: str, key: str = ""):
    with _lock:
        j = _jobs.get((user_id, kind, key))
        if j:
            j["notified"] = True


def for_user(user_id: str):
    """All of this user's jobs (running or finished but not yet seen), oldest first."""
    with _lock:
        keys = [k for k in _jobs if k[0] == user_id]
    jobs = [get(*k) for k in keys]
    return sorted((j for j in jobs if j and (j["running"] or not j["notified"])), key=lambda j: j["started"])


def running_keys(user_id: str, kinds) -> set:
    with _lock:
        return {k for k, j in _jobs.items() if k[0] == user_id and k[1] in kinds and not j["future"].done()}
