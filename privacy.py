"""PII redaction before AI calls, data export, and right-to-erasure."""
from __future__ import annotations
import re
import cal, crypto, db

_PATTERNS = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[CARD]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"(?<!\w)(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}\b"), "[PHONE]"),
]


def redact(text: str) -> str:
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text


def export_user_data(user_id: str) -> dict:
    import legal  # local import: legal -> ai -> privacy
    with db.conn() as c:
        u = c.execute("SELECT id,email,role,plan,plan_expires,created_at,consent_at FROM users WHERE id=?",
                      (user_id,)).fetchone()
        cases = c.execute("SELECT c.* FROM cases c JOIN case_members m ON m.case_id=c.id WHERE m.user_id=?",
                          (user_id,)).fetchall()
        msgs = c.execute("SELECT case_id,body_enc,ts FROM messages WHERE user_id=?", (user_id,)).fetchall()
        docs = c.execute("SELECT id,case_id,filename_enc,created_at FROM documents WHERE owner_id=?", (user_id,)).fetchall()
        chats = c.execute("SELECT role,content_enc,ts FROM ai_chats WHERE user_id=?", (user_id,)).fetchall()
    return dict(
        account=dict(u),
        cases=[dict(id=r["id"], title=crypto.decrypt(r["title_enc"]), created_at=r["created_at"]) for r in cases],
        my_messages=[dict(case_id=r["case_id"], text=crypto.decrypt(r["body_enc"]), ts=r["ts"]) for r in msgs],
        my_documents=[dict(id=r["id"], filename=crypto.decrypt(r["filename_enc"]), created_at=r["created_at"]) for r in docs],
        calendar_events=cal.export_events(user_id),
        ai_chat_history=[dict(role=r["role"], text=crypto.decrypt(r["content_enc"]), ts=r["ts"]) for r in chats],
        legal_work=legal.export_rows(user_id),
    )


def delete_account(user_id: str):
    """Hard delete. Cases with other members are handed to the longest-standing member."""
    with db.conn() as c:
        owned = c.execute("SELECT id FROM cases WHERE owner_id=?", (user_id,)).fetchall()
        for cs in owned:
            heir = c.execute("SELECT user_id FROM case_members WHERE case_id=? AND user_id<>? ORDER BY added_at LIMIT 1",
                             (cs["id"], user_id)).fetchone()
            if heir:
                c.execute("UPDATE cases SET owner_id=? WHERE id=?", (heir["user_id"], cs["id"]))
                c.execute("UPDATE case_members SET role='owner' WHERE case_id=? AND user_id=?", (cs["id"], heir["user_id"]))
            else:
                c.execute("DELETE FROM cases WHERE id=?", (cs["id"],))  # cascades msgs/docs/members
        c.execute("DELETE FROM users WHERE id=?", (user_id,))  # cascades sessions, otps, usage, chats, messages, docs
    db.audit("account_deleted", None, "user removed")
