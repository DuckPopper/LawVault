"""Discord-style presence. You choose Online / Do Not Disturb / Invisible; Idle and Offline are automatic.

- online     green  - active in the last 10 minutes
- idle       yellow - tab open but no activity for 10 minutes
- dnd        red    - you chose Do Not Disturb: no pop-ups, others see you're busy
- offline    grey   - no open tab for 90 seconds, OR you chose Invisible
"""
from __future__ import annotations
from typing import Dict, List
import db

CHOICES = ("online", "dnd", "invisible")
CHOICE_LABEL = {"online": "🟢 Online", "dnd": "🔴 Do Not Disturb", "invisible": "⚫ Invisible"}
DOT = {"online": "🟢", "idle": "🟡", "dnd": "🔴", "offline": "⚫"}
LABEL = {"online": "Online", "idle": "Idle", "dnd": "Do Not Disturb", "offline": "Offline"}
IDLE_AFTER = 10 * 60
OFFLINE_AFTER = 90


def _ensure(c, user_id: str):
    c.execute("INSERT OR IGNORE INTO presence(user_id,status,last_active,last_heartbeat) VALUES(?,?,0,0)",
              (user_id, "online"))


def touch(user_id: str):
    """Real user activity (a click, a page load, a message)."""
    with db.conn() as c:
        _ensure(c, user_id)
        c.execute("UPDATE presence SET last_active=?, last_heartbeat=? WHERE user_id=?", (db.now(), db.now(), user_id))


def heartbeat(user_id: str):
    """The tab is still open (sent automatically every 30 s). Does NOT count as activity."""
    with db.conn() as c:
        _ensure(c, user_id)
        c.execute("UPDATE presence SET last_heartbeat=? WHERE user_id=?", (db.now(), user_id))


def set_choice(user_id: str, choice: str) -> bool:
    if choice not in CHOICES:
        return False
    with db.conn() as c:
        _ensure(c, user_id)
        c.execute("UPDATE presence SET status=? WHERE user_id=?", (choice, user_id))
    return True


def get_choice(user_id: str) -> str:
    with db.conn() as c:
        r = c.execute("SELECT status FROM presence WHERE user_id=?", (user_id,)).fetchone()
    return r["status"] if r else "online"


def _compute(row, now: float) -> str:
    if not row or row["status"] == "invisible" or now - row["last_heartbeat"] > OFFLINE_AFTER:
        return "offline"
    if row["status"] == "dnd":
        return "dnd"
    return "idle" if now - row["last_active"] > IDLE_AFTER else "online"


def status_of(user_ids: List[str]) -> Dict[str, str]:
    """What OTHER people see. Invisible users show as offline."""
    if not user_ids:
        return {}
    now = db.now()
    with db.conn() as c:
        rows = {u: c.execute("SELECT * FROM presence WHERE user_id=?", (u,)).fetchone() for u in set(user_ids)}
    return {u: _compute(rows.get(u), now) for u in user_ids}


def is_dnd(user_id: str) -> bool:
    return get_choice(user_id) == "dnd"
