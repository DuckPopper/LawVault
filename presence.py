"""Teams-style presence.

You pick one of six statuses; Idle and Offline are worked out automatically:

- online     Available        green   active in the last 10 minutes
- busy       Busy             red     you're working; notifications still pop up
- dnd        Do not disturb   red     no pop-ups (they are still collected in Notifications)
- brb        Be right back    amber
- away       Appear away      amber
- invisible  Appear offline   grey    others see you as offline
- idle       (automatic)      amber   tab open but no activity for 10 minutes
- offline    (automatic)      grey    no open tab for 90 seconds, or you chose Appear offline

A chosen status can expire ("Clear after 1 hour"): when it does you go back to Available.
You can also set a short status message ("In court until 3 pm"). It is encrypted at rest.
"""
from __future__ import annotations
import datetime as dt
from typing import Dict, List, Optional
import crypto
import db

CHOICES = ("online", "busy", "dnd", "brb", "away", "invisible")
# Menu names (Microsoft Teams wording)
MENU_LABEL = {"online": "Available", "busy": "Busy", "dnd": "Do not disturb", "brb": "Be right back",
              "away": "Appear away", "invisible": "Appear offline"}
# Older selectbox labels (Settings)
CHOICE_LABEL = {"online": "🟢 Available", "busy": "🔴 Busy", "dnd": "⛔ Do not disturb", "brb": "🟡 Be right back",
                "away": "🟡 Appear away", "invisible": "⚪ Appear offline"}
# What other people see
LABEL = {"online": "Available", "busy": "Busy", "dnd": "Do not disturb", "brb": "Be right back", "away": "Away",
         "idle": "Away", "offline": "Offline"}
DOT = {"online": "🟢", "busy": "🔴", "dnd": "⛔", "brb": "🟡", "away": "🟡", "idle": "🟡", "offline": "⚪"}
DOT_COLOR = {"online": "#3fbf6b", "busy": "#e5484d", "dnd": "#e5484d", "brb": "#f0a800", "away": "#f0a800",
             "idle": "#f0a800", "offline": "#8a8f98", "invisible": "#8a8f98"}

# "Clear status after" choices -> seconds from now (None = until I change it). "today" / "week" are computed.
DURATIONS = ("forever", "30m", "1h", "2h", "today", "week")
DURATION_LABEL = {"forever": "Until I change it", "30m": "30 minutes", "1h": "1 hour", "2h": "2 hours",
                  "today": "Today", "week": "This week"}
MESSAGE_MAX = 120
IDLE_AFTER = 10 * 60
OFFLINE_AFTER = 90


def until_for(duration: str, now: Optional[float] = None) -> Optional[float]:
    """Timestamp at which a status picked now with this duration should expire (None = never)."""
    now = db.now() if now is None else now
    base = dt.datetime.fromtimestamp(now)
    if duration == "30m":
        return now + 30 * 60
    if duration == "1h":
        return now + 3600
    if duration == "2h":
        return now + 7200
    if duration == "today":
        return dt.datetime.combine(base.date() + dt.timedelta(days=1), dt.time(0)).timestamp()
    if duration == "week":  # end of Sunday
        return dt.datetime.combine(base.date() + dt.timedelta(days=7 - base.weekday()), dt.time(0)).timestamp()
    return None


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


def set_choice(user_id: str, choice: str, duration: str = "forever") -> bool:
    if choice not in CHOICES or duration not in DURATIONS:
        return False
    until = None if choice == "online" else until_for(duration)
    with db.conn() as c:
        _ensure(c, user_id)
        c.execute("UPDATE presence SET status=?, status_until=? WHERE user_id=?", (choice, until, user_id))
    return True


def set_duration(user_id: str, duration: str) -> bool:
    """Changes only when the current status expires."""
    if duration not in DURATIONS:
        return False
    with db.conn() as c:
        _ensure(c, user_id)
        c.execute("UPDATE presence SET status_until=? WHERE user_id=? AND status<>'online'",
                  (until_for(duration), user_id))
    return True


def reset(user_id: str):
    """Teams' 'Reset status': back to Available, no expiry."""
    set_choice(user_id, "online")


def _effective(row, now: float) -> str:
    """The chosen status, after applying its expiry."""
    if not row:
        return "online"
    if row["status_until"] and now >= row["status_until"]:
        return "online"
    return row["status"] if row["status"] in CHOICES else "online"


def _row(c, user_id: str):
    return c.execute("SELECT * FROM presence WHERE user_id=?", (user_id,)).fetchone()


def get_choice(user_id: str) -> str:
    now = db.now()
    with db.conn() as c:
        r = _row(c, user_id)
        if r and r["status_until"] and now >= r["status_until"]:   # expired: tidy up
            c.execute("UPDATE presence SET status='online', status_until=NULL WHERE user_id=?", (user_id,))
    return _effective(r, now)


def get_until(user_id: str) -> Optional[float]:
    with db.conn() as c:
        r = _row(c, user_id)
    if not r or not r["status_until"] or db.now() >= r["status_until"]:
        return None
    return r["status_until"]


def set_message(user_id: str, text: str) -> bool:
    text = " ".join((text or "").split())[:MESSAGE_MAX]
    with db.conn() as c:
        _ensure(c, user_id)
        c.execute("UPDATE presence SET message_enc=? WHERE user_id=?", (crypto.encrypt(text) if text else None, user_id))
    return True


def get_message(user_id: str) -> str:
    return messages_of([user_id]).get(user_id, "")


def messages_of(user_ids: List[str]) -> Dict[str, str]:
    if not user_ids:
        return {}
    with db.conn() as c:
        rows = {u: _row(c, u) for u in set(user_ids)}
    return {u: (crypto.decrypt(rows[u]["message_enc"]) if rows.get(u) and rows[u]["message_enc"] else "")
            for u in user_ids}


def _compute(row, now: float) -> str:
    choice = _effective(row, now)
    if not row or choice == "invisible" or now - row["last_heartbeat"] > OFFLINE_AFTER:
        return "offline"
    if choice != "online":
        return choice
    return "idle" if now - row["last_active"] > IDLE_AFTER else "online"


def status_of(user_ids: List[str]) -> Dict[str, str]:
    """What OTHER people see. Appear offline shows as offline."""
    if not user_ids:
        return {}
    now = db.now()
    with db.conn() as c:
        rows = {u: _row(c, u) for u in set(user_ids)}
    return {u: _compute(rows.get(u), now) for u in user_ids}


def is_dnd(user_id: str) -> bool:
    return get_choice(user_id) == "dnd"
