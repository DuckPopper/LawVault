"""Case workspaces + group chat + documents + deadlines/tasks.
EVERY function checks membership and role on the server (no cross-user access).

Roles:  owner  - everything, manages members and roles, deletes the case
        editor - chat, upload, analyse, add/complete tasks
        viewer - read-only (e.g. a client or trainee)
"""
from __future__ import annotations
import re
from typing import Optional
import contacts, crypto, db, notify, subscription

ROLES = ("owner", "editor", "viewer")
ASSIGNABLE_ROLES = ("editor", "viewer")


def _role(c, user_id: str, case_id: str) -> Optional[str]:
    r = c.execute("SELECT role FROM case_members WHERE case_id=? AND user_id=?", (case_id, user_id)).fetchone()
    return r["role"] if r else None


def _can_edit(c, user_id: str, case_id: str) -> bool:
    return _role(c, user_id, case_id) in ("owner", "editor")


def _title(c, case_id: str) -> str:
    r = c.execute("SELECT title_enc FROM cases WHERE id=?", (case_id,)).fetchone()
    return crypto.decrypt(r["title_enc"]) if r else "a case"


def can_edit(user_id: str, case_id: str) -> bool:
    with db.conn() as c:
        return _can_edit(c, user_id, case_id)


def create_case(user, title: str, desc: str = ""):
    title = title.strip()[:120]
    if not title:
        return None, "Title is required."
    with db.conn() as c:
        n = c.execute("SELECT COUNT(*) n FROM cases WHERE owner_id=?", (user["id"],)).fetchone()["n"]
        if n >= subscription.limits(user)["max_cases"]:
            return None, "Case limit reached for your plan. Upgrade to create more."
        cid = db.uid()
        c.execute("INSERT INTO cases(id,title_enc,desc_enc,owner_id,created_at) VALUES(?,?,?,?,?)",
                  (cid, crypto.encrypt(title), crypto.encrypt(desc.strip()[:2000]), user["id"], db.now()))
        c.execute("INSERT INTO case_members(case_id,user_id,role,added_at) VALUES(?,?,?,?)",
                  (cid, user["id"], "owner", db.now()))
    db.audit("case_created", user["id"], cid)
    return cid, "Case created."


def list_cases(user_id: str):
    with db.conn() as c:
        rows = c.execute("""SELECT c.id,c.title_enc,c.desc_enc,c.created_at,m.role FROM cases c
                            JOIN case_members m ON m.case_id=c.id WHERE m.user_id=? ORDER BY c.created_at DESC""",
                         (user_id,)).fetchall()
    return [dict(id=r["id"], title=crypto.decrypt(r["title_enc"]), desc=crypto.decrypt(r["desc_enc"]),
                 role=r["role"], created_at=r["created_at"]) for r in rows]


def get_case(user_id: str, case_id: str):
    with db.conn() as c:
        role = _role(c, user_id, case_id)
        if not role:
            return None
        r = c.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    return dict(id=r["id"], title=crypto.decrypt(r["title_enc"]), desc=crypto.decrypt(r["desc_enc"]), role=role)


def members(user_id: str, case_id: str):
    with db.conn() as c:
        if not _role(c, user_id, case_id):
            return []
        rows = c.execute("SELECT u.id,u.email,m.role FROM case_members m JOIN users u ON u.id=m.user_id "
                         "WHERE m.case_id=? ORDER BY m.added_at", (case_id,)).fetchall()
    return [dict(r) for r in rows]


def add_member(user, case_id: str, email: str, role: str = "editor"):
    email = (email or "").strip().lower()
    if role not in ASSIGNABLE_ROLES:
        return False, "Invalid role."
    added = None
    with db.conn() as c:
        if _role(c, user["id"], case_id) != "owner":
            return False, "Only the case owner can add members."
        n = c.execute("SELECT COUNT(*) n FROM case_members WHERE case_id=?", (case_id,)).fetchone()["n"]
        n += c.execute("SELECT COUNT(*) n FROM case_invites WHERE case_id=? AND email<>?", (case_id, email)).fetchone()["n"]
        if n >= subscription.limits(user)["max_members"]:
            return False, "Member limit reached for your plan."
        t = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if t:
            cur = c.execute("INSERT OR IGNORE INTO case_members(case_id,user_id,role,added_at) VALUES(?,?,?,?)",
                            (case_id, t["id"], role, db.now()))
            if cur.rowcount:
                added = (t["id"], _title(c, case_id))
        else:
            c.execute("INSERT OR REPLACE INTO case_invites(case_id,email,role,invited_by,created_at) VALUES(?,?,?,?,?)",
                      (case_id, email, role, user["id"], db.now()))
    if added:
        notify.notify(added[0], "case_added", f"{user['email']} added you to “{added[1]}” as {role}.", link="cases")
    db.audit("member_add_attempt", user["id"], case_id)
    contacts.add(user["id"], email)  # anyone you work with lands in your contacts
    # Same reply whether or not the email is registered (no account enumeration).
    return True, "If that lawyer has a LawVault account, they now have access. Otherwise they are invited and join the case when they sign up."


def pending_invites(user_id: str, case_id: str):
    """Owner only: emails invited to the case who haven't signed up yet."""
    with db.conn() as c:
        if _role(c, user_id, case_id) != "owner":
            return []
        rows = c.execute("SELECT email,role FROM case_invites WHERE case_id=? ORDER BY created_at", (case_id,)).fetchall()
    return [dict(email=r["email"], role=r["role"]) for r in rows]


def cancel_invite(user_id: str, case_id: str, email: str) -> bool:
    with db.conn() as c:
        if _role(c, user_id, case_id) != "owner":
            return False
        cur = c.execute("DELETE FROM case_invites WHERE case_id=? AND email=?", (case_id, (email or "").strip().lower()))
    return cur.rowcount == 1


def accept_pending(user_id: str, email: str) -> int:
    """Called after signup: turn invites for this email into memberships. Returns how many."""
    email = (email or "").strip().lower()
    joined = []
    with db.conn() as c:
        for r in c.execute("SELECT i.case_id,i.role,i.invited_by FROM case_invites i JOIN cases cs ON cs.id=i.case_id "
                           "WHERE i.email=?", (email,)).fetchall():
            c.execute("INSERT OR IGNORE INTO case_members(case_id,user_id,role,added_at) VALUES(?,?,?,?)",
                      (r["case_id"], user_id, r["role"], db.now()))
            joined.append((r["case_id"], r["role"], _title(c, r["case_id"])))
        c.execute("DELETE FROM case_invites WHERE email=?", (email,))
    for _cid, role, title in joined:
        notify.notify(user_id, "case_added", f"You were invited to “{title}” as {role}.", link="cases")
    return len(joined)


def set_role(user_id: str, case_id: str, target_id: str, role: str) -> bool:
    """Owner only. The owner's own role can't be changed here."""
    if role not in ASSIGNABLE_ROLES:
        return False
    with db.conn() as c:
        if _role(c, user_id, case_id) != "owner" or target_id == user_id:
            return False
        cur = c.execute("UPDATE case_members SET role=? WHERE case_id=? AND user_id=? AND role<>'owner'",
                        (role, case_id, target_id))
    db.audit("member_role_changed", user_id, f"{case_id}:{role}")
    return cur.rowcount == 1


def remove_member(user_id: str, case_id: str, target_id: str):
    with db.conn() as c:
        role = _role(c, user_id, case_id)
        if role != "owner" and user_id != target_id:
            return False
        if target_id == user_id and role == "owner":
            return False  # owner can't leave; delete the case or transfer instead
        c.execute("DELETE FROM case_members WHERE case_id=? AND user_id=?", (case_id, target_id))
    db.audit("member_removed", user_id, case_id)
    return True


def delete_case(user_id: str, case_id: str):
    with db.conn() as c:
        if _role(c, user_id, case_id) != "owner":
            return False
        c.execute("DELETE FROM cases WHERE id=?", (case_id,))
    db.audit("case_deleted", user_id, case_id)
    return True


def post_message(user_id: str, case_id: str, body: str, kind: str = "user"):
    """kind='ai' marks an answer from LawVault AI (posted on behalf of the member who asked)."""
    body = body.strip()[:8000]
    if not body or kind not in ("user", "ai"):
        return False
    with db.conn() as c:
        if not _can_edit(c, user_id, case_id):
            return False
        c.execute("INSERT INTO messages(case_id,user_id,body_enc,ts,kind) VALUES(?,?,?,?,?)",
                  (case_id, user_id, crypto.encrypt(body), db.now(), kind))
        others = c.execute("SELECT u.id, u.email FROM case_members m JOIN users u ON u.id=m.user_id "
                           "WHERE m.case_id=? AND m.user_id<>?", (case_id, user_id)).fetchall()
        title = _title(c, case_id)
        sender = c.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()["email"]
    mentioned = {m.lower() for m in re.findall(r"@([\w.+-]+@[\w-]+\.[\w.-]+)", body)}
    for o in others:
        if o["email"].lower() in mentioned:
            notify.notify(o["id"], "mention", f"{sender} mentioned you in “{title}”", link="cases")
        else:
            notify.notify(o["id"], "chat", f"New messages in “{title}”", link="cases", ref=f"chat:{case_id}")
    return True


def get_messages(user_id: str, case_id: str, limit: int = 200):
    with db.conn() as c:
        if not _role(c, user_id, case_id):
            return []
        rows = c.execute("""SELECT * FROM (SELECT m.id,m.user_id,u.email,m.body_enc,m.ts,m.kind FROM messages m
                            JOIN users u ON u.id=m.user_id WHERE m.case_id=? ORDER BY m.id DESC LIMIT ?)
                            ORDER BY id""", (case_id, limit)).fetchall()
    return [dict(id=r["id"], user_id=r["user_id"], email=r["email"], body=crypto.decrypt(r["body_enc"]), ts=r["ts"],
                 kind=r["kind"]) for r in rows]


def add_document(user, case_id: Optional[str], filename: str, text: str):
    with db.conn() as c:
        if case_id and not _can_edit(c, user["id"], case_id):
            return None, "You need editor access to upload to this case."
        n = c.execute("SELECT COUNT(*) n FROM documents WHERE owner_id=?", (user["id"],)).fetchone()["n"]
        if n >= subscription.limits(user)["max_docs"]:
            return None, "Document limit reached for your plan."
        did = db.uid()
        filename = clean_filename(filename)
        c.execute("INSERT INTO documents(id,case_id,owner_id,filename_enc,text_enc,created_at) VALUES(?,?,?,?,?,?)",
                  (did, case_id, user["id"], crypto.encrypt(filename[:200]), crypto.encrypt(text), db.now()))
    db.audit("document_uploaded", user["id"], did)
    return did, "Uploaded."


def _can_see_doc(c, user_id: str, d) -> bool:
    return d["owner_id"] == user_id or (d["case_id"] is not None and _role(c, user_id, d["case_id"]) is not None)


def list_documents(user_id: str, case_id: Optional[str] = None):
    with db.conn() as c:
        if case_id:
            if not _role(c, user_id, case_id):
                return []
            rows = c.execute("SELECT * FROM documents WHERE case_id=? ORDER BY created_at DESC", (case_id,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM documents WHERE owner_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [dict(id=r["id"], filename=crypto.decrypt(r["filename_enc"]), has_analysis=bool(r["analysis_enc"]),
                 created_at=r["created_at"], case_id=r["case_id"]) for r in rows]


def get_document(user_id: str, doc_id: str):
    with db.conn() as c:
        d = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not d or not _can_see_doc(c, user_id, d):
            return None
    return dict(id=d["id"], filename=crypto.decrypt(d["filename_enc"]), text=crypto.decrypt(d["text_enc"]),
                analysis=crypto.decrypt(d["analysis_enc"]), case_id=d["case_id"])


def save_analysis(user_id: str, doc_id: str, analysis: str):
    with db.conn() as c:
        d = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not d or not _can_see_doc(c, user_id, d):
            return False
        if d["case_id"] and not _can_edit(c, user_id, d["case_id"]):
            return False
        c.execute("UPDATE documents SET analysis_enc=? WHERE id=?", (crypto.encrypt(analysis), doc_id))
    return True


def delete_document(user_id: str, doc_id: str):
    with db.conn() as c:
        c.execute("DELETE FROM documents WHERE id=? AND owner_id=?", (doc_id, user_id))


def clean_filename(name: str) -> str:
    """A display name only: no folders, no control characters, never empty."""
    name = re.sub(r"[\x00-\x1f\x7f]", "", (name or "").replace("\\", "/").split("/")[-1]).strip()
    return name[:200] or "Untitled"


def list_accessible_documents(user_id: str, query: str = "", case_id: Optional[str] = None, scope: str = "all"):
    """Every document this user may open: their own plus those in cases they belong to.
    scope: all | mine | personal (not in any case). `query` matches the name or the text (case-insensitive)."""
    with db.conn() as c:
        rows = c.execute("""SELECT d.*, u.email AS owner_email, cs.title_enc AS case_title, m.role AS my_role
                            FROM documents d JOIN users u ON u.id=d.owner_id
                            LEFT JOIN cases cs ON cs.id=d.case_id
                            LEFT JOIN case_members m ON m.case_id=d.case_id AND m.user_id=?
                            WHERE d.owner_id=? OR m.user_id IS NOT NULL
                            ORDER BY d.created_at DESC""", (user_id, user_id)).fetchall()
    q, out = (query or "").strip().lower(), []
    for r in rows:
        if case_id and r["case_id"] != case_id:
            continue
        if scope == "mine" and r["owner_id"] != user_id:
            continue
        if scope == "personal" and r["case_id"]:
            continue
        name, text = crypto.decrypt(r["filename_enc"]), crypto.decrypt(r["text_enc"])
        snippet = ""
        if q:
            if q in name.lower():
                pass
            elif q in text.lower():
                i = text.lower().index(q)
                snippet = ("…" if i > 60 else "") + re.sub(r"\s+", " ", text[max(0, i - 60):i + len(q) + 80]).strip() + "…"
            else:
                continue
        mine = r["owner_id"] == user_id
        out.append(dict(id=r["id"], filename=name, case_id=r["case_id"],
                        case=crypto.decrypt(r["case_title"]) if r["case_title"] else None,
                        owner=r["owner_email"], mine=mine, has_analysis=bool(r["analysis_enc"]),
                        created_at=r["created_at"], chars=len(text), snippet=snippet,
                        can_edit=mine or r["my_role"] in ("owner", "editor")))
    return out


def rename_document(user_id: str, doc_id: str, new_name: str) -> bool:
    """The uploader, or an editor of the case the document is in."""
    name = clean_filename(new_name)
    with db.conn() as c:
        d = c.execute("SELECT owner_id, case_id FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not d or not (d["owner_id"] == user_id or (d["case_id"] and _can_edit(c, user_id, d["case_id"]))):
            return False
        c.execute("UPDATE documents SET filename_enc=? WHERE id=?", (crypto.encrypt(name), doc_id))
    return True


def move_document(user_id: str, doc_id: str, case_id: Optional[str]):
    """Only the uploader can move a document, and only into a case they can edit (or back to personal)."""
    with db.conn() as c:
        d = c.execute("SELECT owner_id FROM documents WHERE id=?", (doc_id,)).fetchone()
        if not d or d["owner_id"] != user_id:
            return False, "Only the person who uploaded a document can move it."
        if case_id and not _can_edit(c, user_id, case_id):
            return False, "You need editor access to that case."
        c.execute("UPDATE documents SET case_id=? WHERE id=?", (case_id, doc_id))
    db.audit("document_moved", user_id, doc_id)
    return True, "Moved."


# ---------- deadlines & tasks ----------
TASK_KINDS = ("deadline", "task")


def add_task(user_id: str, case_id: str, kind: str, title: str, due_ts: Optional[float] = None,
             assignee_id: Optional[str] = None):
    title = (title or "").strip()[:200]
    if kind not in TASK_KINDS or not title:
        return None, "Give it a title."
    if kind == "deadline" and not due_ts:
        return None, "A deadline needs a date."
    with db.conn() as c:
        if not _can_edit(c, user_id, case_id):
            return None, "You need editor access to add deadlines or tasks."
        if assignee_id and not _role(c, assignee_id, case_id):
            return None, "The assignee must be a member of this case."
        tid = db.uid()
        c.execute("INSERT INTO case_tasks(id,case_id,kind,title_enc,due_ts,assignee_id,created_by,created_at) "
                  "VALUES(?,?,?,?,?,?,?,?)", (tid, case_id, kind, crypto.encrypt(title), due_ts, assignee_id,
                                              user_id, db.now()))
        case_title = _title(c, case_id)
    if assignee_id and assignee_id != user_id:
        notify.notify(assignee_id, "task", f"New {kind} for you in “{case_title}”: {title}", link="cases")
    db.audit("task_added", user_id, case_id)
    return tid, "Added."


def list_tasks(user_id: str, case_id: str):
    with db.conn() as c:
        if not _role(c, user_id, case_id):
            return []
        rows = c.execute("""SELECT t.*, u.email AS assignee FROM case_tasks t LEFT JOIN users u ON u.id=t.assignee_id
                            WHERE t.case_id=? ORDER BY t.done, t.due_ts IS NULL, t.due_ts""", (case_id,)).fetchall()
    return [dict(id=r["id"], kind=r["kind"], title=crypto.decrypt(r["title_enc"]), due=r["due_ts"],
                 assignee=r["assignee"], assignee_id=r["assignee_id"], done=bool(r["done"])) for r in rows]


def set_task_done(user_id: str, task_id: str, done: bool) -> bool:
    """Editors, or the person the task is assigned to (even a viewer), can tick it off."""
    with db.conn() as c:
        t = c.execute("SELECT * FROM case_tasks WHERE id=?", (task_id,)).fetchone()
        if not t or not (_can_edit(c, user_id, t["case_id"]) or
                         (t["assignee_id"] == user_id and _role(c, user_id, t["case_id"]))):
            return False
        c.execute("UPDATE case_tasks SET done=? WHERE id=?", (1 if done else 0, task_id))
    return True


def delete_task(user_id: str, task_id: str) -> bool:
    with db.conn() as c:
        t = c.execute("SELECT case_id FROM case_tasks WHERE id=?", (task_id,)).fetchone()
        if not t or not _can_edit(c, user_id, t["case_id"]):
            return False
        c.execute("DELETE FROM case_tasks WHERE id=?", (task_id,))
    return True


def deadlines_between(user_id: str, start: float, end: float):
    """Open deadlines from all my cases in a time window (shown on my calendar and dashboard)."""
    with db.conn() as c:
        rows = c.execute("""SELECT t.*, c.title_enc AS case_title FROM case_tasks t
                            JOIN case_members m ON m.case_id=t.case_id AND m.user_id=?
                            JOIN cases c ON c.id=t.case_id
                            WHERE t.done=0 AND t.due_ts IS NOT NULL AND t.due_ts>=? AND t.due_ts<?
                            ORDER BY t.due_ts""", (user_id, start, end)).fetchall()
    return [dict(id=r["id"], kind=r["kind"], title=crypto.decrypt(r["title_enc"]), due=r["due_ts"],
                 case=crypto.decrypt(r["case_title"]), case_id=r["case_id"]) for r in rows]


def my_open_tasks(user_id: str):
    with db.conn() as c:
        rows = c.execute("""SELECT t.*, c.title_enc AS case_title FROM case_tasks t JOIN cases c ON c.id=t.case_id
                            JOIN case_members m ON m.case_id=t.case_id AND m.user_id=t.assignee_id
                            WHERE t.assignee_id=? AND t.done=0 ORDER BY t.due_ts IS NULL, t.due_ts""",
                         (user_id,)).fetchall()
    return [dict(id=r["id"], kind=r["kind"], title=crypto.decrypt(r["title_enc"]), due=r["due_ts"],
                 case=crypto.decrypt(r["case_title"])) for r in rows]
