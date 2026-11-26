"""Personal address book of coworkers/friends. One-way and private: only the owner sees it.
It never reveals whether an email has a LawVault account (no account enumeration)."""
from __future__ import annotations
import re
import crypto, db

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
MAX_CONTACTS = 200


def add(user_id: str, email: str, name: str = ""):
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        return False, "Enter a valid email address."
    with db.conn() as c:
        me = c.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()
        if me and me["email"] == email:
            return False, "That is your own email."
        n = c.execute("SELECT COUNT(*) n FROM contacts WHERE user_id=?", (user_id,)).fetchone()["n"]
        if n >= MAX_CONTACTS and not c.execute("SELECT 1 FROM contacts WHERE user_id=? AND email=?",
                                               (user_id, email)).fetchone():
            return False, "Contact limit reached."
        c.execute("INSERT INTO contacts(user_id,email,name_enc,added_at) VALUES(?,?,?,?) "
                  "ON CONFLICT(user_id,email) DO UPDATE SET name_enc=CASE WHEN excluded.name_enc<>'' "
                  "THEN excluded.name_enc ELSE contacts.name_enc END",
                  (user_id, email, crypto.encrypt((name or "").strip()[:80]) if (name or "").strip() else "", db.now()))
    return True, "Contact saved."


def remove(user_id: str, email: str) -> bool:
    with db.conn() as c:
        cur = c.execute("DELETE FROM contacts WHERE user_id=? AND email=?", (user_id, (email or "").strip().lower()))
    return cur.rowcount == 1


def listing(user_id: str):
    with db.conn() as c:
        rows = c.execute("SELECT email,name_enc FROM contacts WHERE user_id=? ORDER BY email", (user_id,)).fetchall()
    return [dict(email=r["email"], name=crypto.decrypt(r["name_enc"]) if r["name_enc"] else "") for r in rows]
