"""In-app notifications (the 🔔). Text is encrypted at rest. Repeated chat activity is grouped."""
from __future__ import annotations
from typing import Optional
import crypto, db

ICONS = {"chat": "💬", "mention": "📣", "invite": "📅", "cal_request": "🔑", "cal_reply": "🔑",
         "case_added": "📁", "task": "✅", "security": "🛡️", "ai": "🤖"}


def notify(user_id: str, kind: str, text: str, link: Optional[str] = None, ref: Optional[str] = None):
    """ref groups repeats: a second unread notification with the same ref bumps a counter instead."""
    with db.conn() as c:
        if ref:
            row = c.execute("SELECT id FROM notifications WHERE user_id=? AND ref=? AND read=0",
                            (user_id, ref)).fetchone()
            if row:
                c.execute("UPDATE notifications SET count=count+1, text_enc=?, ts=?, toasted=0 WHERE id=?",
                          (crypto.encrypt(text), db.now(), row["id"]))
                return
        c.execute("INSERT INTO notifications(user_id,kind,text_enc,link,ref,ts) VALUES(?,?,?,?,?,?)",
                  (user_id, kind, crypto.encrypt(text), link, ref, db.now()))


_Q_ALL = "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT ?"
_Q_TOAST = "SELECT * FROM notifications WHERE user_id=? AND read=0 AND toasted=0 ORDER BY id DESC LIMIT ?"


def _rows(user_id: str, query: str = _Q_ALL, limit: int = 50):
    with db.conn() as c:
        rows = c.execute(query, (user_id, limit)).fetchall()
    return [dict(id=r["id"], kind=r["kind"], text=crypto.decrypt(r["text_enc"]), link=r["link"], count=r["count"],
                 read=bool(r["read"]), ts=r["ts"], icon=ICONS.get(r["kind"], "🔔")) for r in rows]


def recent(user_id: str, limit: int = 50):
    return _rows(user_id, _Q_ALL, limit)


def unread_count(user_id: str) -> int:
    with db.conn() as c:
        return c.execute("SELECT COUNT(*) n FROM notifications WHERE user_id=? AND read=0", (user_id,)).fetchone()["n"]


def take_toasts(user_id: str):
    """Notifications not yet shown as a pop-up. Marks them as shown."""
    out = _rows(user_id, _Q_TOAST, 5)
    with db.conn() as c:
        c.execute("UPDATE notifications SET toasted=1 WHERE user_id=? AND toasted=0", (user_id,))
    return out


def mark_read(user_id: str, notif_id: Optional[int] = None):
    with db.conn() as c:
        if notif_id is None:
            c.execute("UPDATE notifications SET read=1, toasted=1 WHERE user_id=?", (user_id,))
        else:
            c.execute("UPDATE notifications SET read=1, toasted=1 WHERE user_id=? AND id=?", (user_id, notif_id))


def clear(user_id: str):
    with db.conn() as c:
        c.execute("DELETE FROM notifications WHERE user_id=?", (user_id,))
