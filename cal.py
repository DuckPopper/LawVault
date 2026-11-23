"""Personal calendars: sharing (visibility toggle + access requests), meeting invites, and find-a-time.

Privacy model
- Your calendar is PRIVATE by default.
- Visibility toggle applies only to teammates (people you share at least one case with):
    private  -> teammates see nothing
    busy     -> teammates see when you are busy, never what
    details  -> teammates see event titles (never private notes)
- Anyone on a shared case can REQUEST access; you approve (as busy or details), deny, or revoke later.
- Event titles and notes are encrypted at rest. Start/end times are stored in plain form so
  free/busy can be computed (documented limitation).
"""
from __future__ import annotations
import datetime as dt
from typing import List, Optional
import crypto, db, notify, subscription

VISIBILITY = ("private", "busy", "details")
_RANK = {None: 0, "busy": 1, "details": 2, "full": 3}
WORK_START, WORK_END = 9, 18          # working hours used by find-a-time
SLOT_STEP_MIN = 30
MAX_EVENT_SECONDS = 7 * 86400


# ---------- relationships ----------
def _is_teammate(c, a: str, b: str) -> bool:
    if a == b:
        return False
    r = c.execute("""SELECT 1 FROM case_members m1 JOIN case_members m2 ON m1.case_id=m2.case_id
                     WHERE m1.user_id=? AND m2.user_id=? LIMIT 1""", (a, b)).fetchone()
    return r is not None


def teammates(user_id: str) -> List[dict]:
    with db.conn() as c:
        rows = c.execute("""SELECT DISTINCT u.id, u.email FROM case_members m1
                            JOIN case_members m2 ON m1.case_id=m2.case_id
                            JOIN users u ON u.id=m2.user_id
                            WHERE m1.user_id=? AND m2.user_id<>? ORDER BY u.email""", (user_id, user_id)).fetchall()
    return [dict(r) for r in rows]


# ---------- visibility & access ----------
def _visibility(c, user_id: str) -> str:
    r = c.execute("SELECT visibility FROM calendar_settings WHERE user_id=?", (user_id,)).fetchone()
    return r["visibility"] if r else "private"


def get_visibility(user_id: str) -> str:
    with db.conn() as c:
        return _visibility(c, user_id)


def set_visibility(user_id: str, visibility: str) -> bool:
    if visibility not in VISIBILITY:
        return False
    with db.conn() as c:
        c.execute("INSERT INTO calendar_settings(user_id,visibility) VALUES(?,?) "
                  "ON CONFLICT(user_id) DO UPDATE SET visibility=excluded.visibility", (user_id, visibility))
    db.audit("calendar_visibility", user_id, visibility)
    return True


def _level(c, viewer_id: str, owner_id: str) -> Optional[str]:
    if viewer_id == owner_id:
        return "full"
    best = None
    g = c.execute("SELECT level FROM calendar_access WHERE owner_id=? AND viewer_id=? AND status='approved'",
                  (owner_id, viewer_id)).fetchone()
    if g:
        best = g["level"]
    vis = _visibility(c, owner_id)
    if vis != "private" and _RANK[vis] > _RANK[best] and _is_teammate(c, viewer_id, owner_id):
        best = vis
    return best


def access_level(viewer_id: str, owner_id: str) -> Optional[str]:
    """None = no access, 'busy', 'details', or 'full' (it's your own calendar)."""
    with db.conn() as c:
        return _level(c, viewer_id, owner_id)


def request_access(viewer_id: str, owner_id: str, level: str):
    if level not in ("busy", "details") or viewer_id == owner_id:
        return False, "Invalid request."
    with db.conn() as c:
        if not _is_teammate(c, viewer_id, owner_id):
            return False, "You can only request calendars of lawyers you share a case with."
        if _RANK[_level(c, viewer_id, owner_id)] >= _RANK[level]:
            return False, "You already have that level of access."
        c.execute("""INSERT INTO calendar_access(owner_id,viewer_id,level,status,created_at) VALUES(?,?,?,'pending',?)
                     ON CONFLICT(owner_id,viewer_id) DO UPDATE SET level=excluded.level, status='pending',
                     created_at=excluded.created_at""", (owner_id, viewer_id, level, db.now()))
    with db.conn() as c:
        who = c.execute("SELECT email FROM users WHERE id=?", (viewer_id,)).fetchone()["email"]
    notify.notify(owner_id, "cal_request", f"{who} asked to see your calendar ({level}).", link="calendar")
    db.audit("calendar_access_requested", viewer_id, level)
    return True, "Request sent. They'll see it under Calendar → Sharing."


_SELECT_ACCESS = "SELECT a.owner_id, a.viewer_id, a.level, a.status, a.created_at, u.email FROM calendar_access a "
_Q_INCOMING = _SELECT_ACCESS + ("JOIN users u ON u.id=a.viewer_id WHERE a.owner_id=? AND a.status='pending' "
                                "ORDER BY a.created_at DESC")
_Q_GRANTED = _SELECT_ACCESS + ("JOIN users u ON u.id=a.viewer_id WHERE a.owner_id=? AND a.status='approved' "
                               "ORDER BY a.created_at DESC")
_Q_MINE = _SELECT_ACCESS + "JOIN users u ON u.id=a.owner_id WHERE a.viewer_id=? ORDER BY a.created_at DESC"


def _requests(query: str, uid: str):
    with db.conn() as c:
        return [dict(r) for r in c.execute(query, (uid,)).fetchall()]


def incoming_requests(owner_id: str):
    return _requests(_Q_INCOMING, owner_id)


def granted_viewers(owner_id: str):
    return _requests(_Q_GRANTED, owner_id)


def my_requests(viewer_id: str):
    return _requests(_Q_MINE, viewer_id)


def respond_request(owner_id: str, viewer_id: str, approve: bool, level: Optional[str] = None) -> bool:
    """Only the calendar OWNER can answer (owner_id comes from the logged-in session)."""
    with db.conn() as c:
        if approve:
            row = c.execute("SELECT level FROM calendar_access WHERE owner_id=? AND viewer_id=? AND status='pending'",
                            (owner_id, viewer_id)).fetchone()
            if not row:
                return False
            lvl = level if level in ("busy", "details") else row["level"]
            c.execute("UPDATE calendar_access SET status='approved', level=? WHERE owner_id=? AND viewer_id=?",
                      (lvl, owner_id, viewer_id))
        else:
            cur = c.execute("DELETE FROM calendar_access WHERE owner_id=? AND viewer_id=? AND status='pending'",
                            (owner_id, viewer_id))
            if cur.rowcount != 1:
                return False
    with db.conn() as c:
        who = c.execute("SELECT email FROM users WHERE id=?", (owner_id,)).fetchone()["email"]
    notify.notify(viewer_id, "cal_reply", f"{who} {'approved' if approve else 'declined'} your calendar request.",
                  link="calendar")
    db.audit("calendar_access_" + ("approved" if approve else "denied"), owner_id)
    return True


def revoke(owner_id: str, viewer_id: str):
    with db.conn() as c:
        c.execute("DELETE FROM calendar_access WHERE owner_id=? AND viewer_id=?", (owner_id, viewer_id))
    db.audit("calendar_access_revoked", owner_id)


def cancel_request(viewer_id: str, owner_id: str):
    with db.conn() as c:
        c.execute("DELETE FROM calendar_access WHERE owner_id=? AND viewer_id=?", (owner_id, viewer_id))


def viewable_calendars(viewer_id: str) -> List[dict]:
    """Other people whose calendar this user can currently see, with the level."""
    with db.conn() as c:
        cands = {r["id"]: r["email"] for r in c.execute(
            """SELECT DISTINCT u.id, u.email FROM case_members m1 JOIN case_members m2 ON m1.case_id=m2.case_id
               JOIN users u ON u.id=m2.user_id WHERE m1.user_id=? AND m2.user_id<>?""", (viewer_id, viewer_id))}
        for r in c.execute("""SELECT u.id, u.email FROM calendar_access a JOIN users u ON u.id=a.owner_id
                              WHERE a.viewer_id=? AND a.status='approved'""", (viewer_id,)):
            cands[r["id"]] = r["email"]
        out = []
        for uid, email in sorted(cands.items(), key=lambda kv: kv[1]):
            lvl = _level(c, viewer_id, uid)
            if lvl:
                out.append(dict(id=uid, email=email, level=lvl))
    return out


# ---------- events & invites ----------
def add_event(user, title: str, start_ts: float, end_ts: float, notes: str = "",
              case_id: Optional[str] = None, invitee_ids: Optional[List[str]] = None):
    title = (title or "").strip()[:150]
    invitee_ids = [i for i in dict.fromkeys(invitee_ids or []) if i != user["id"]]
    if not title:
        return None, "Title is required."
    if end_ts <= start_ts:
        return None, "End time must be after start time."
    if end_ts - start_ts > MAX_EVENT_SECONDS:
        return None, "Events can be at most 7 days long."
    if len(invitee_ids) + 1 > subscription.limits(user)["max_meeting_people"]:
        return None, "Too many people for your plan. Upgrade to invite more."
    with db.conn() as c:
        if case_id and not c.execute("SELECT 1 FROM case_members WHERE case_id=? AND user_id=?",
                                     (case_id, user["id"])).fetchone():
            return None, "No access to that case."
        if any(not _is_teammate(c, user["id"], i) for i in invitee_ids):
            return None, "You can only invite lawyers you share a case with."
        eid = db.uid()
        c.execute("INSERT INTO events(id,owner_id,title_enc,notes_enc,start_ts,end_ts,case_id,created_at) "
                  "VALUES(?,?,?,?,?,?,?,?)", (eid, user["id"], crypto.encrypt(title),
                                              crypto.encrypt((notes or "").strip()[:2000]), start_ts, end_ts,
                                              case_id, db.now()))
        for i in invitee_ids:
            c.execute("INSERT INTO event_attendees(event_id,user_id,status) VALUES(?,?,'pending')", (eid, i))
    when = dt.datetime.fromtimestamp(start_ts).strftime("%a %b %d, %H:%M")
    for i in invitee_ids:
        notify.notify(i, "invite", f"{user['email']} invited you to “{title}” on {when}.", link="calendar")
    db.audit("event_created", user["id"], f"{len(invitee_ids)} invitees")
    return eid, "Meeting proposed - invitees can accept or decline." if invitee_ids else "Event added."


def delete_event(user_id: str, event_id: str) -> bool:
    """Owner deletes the event for everyone. An attendee 'deleting' just declines it."""
    with db.conn() as c:
        cur = c.execute("DELETE FROM events WHERE id=? AND owner_id=?", (event_id, user_id))
        if cur.rowcount:
            db_ok = True
        else:
            db_ok = c.execute("UPDATE event_attendees SET status='declined' WHERE event_id=? AND user_id=?",
                              (event_id, user_id)).rowcount == 1
    return db_ok


def respond_invite(user_id: str, event_id: str, accept: bool) -> bool:
    with db.conn() as c:
        cur = c.execute("UPDATE event_attendees SET status=? WHERE event_id=? AND user_id=?",
                        ("accepted" if accept else "declined", event_id, user_id))
        ev = c.execute("SELECT owner_id, title_enc FROM events WHERE id=?", (event_id,)).fetchone()
        who = c.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()
    if cur.rowcount == 1 and ev and who:
        notify.notify(ev["owner_id"], "invite",
                      f"{who['email']} {'accepted' if accept else 'declined'} “{crypto.decrypt(ev['title_enc'])}”.",
                      link="calendar")
    return cur.rowcount == 1


def _attendees(c, event_id: str):
    return [dict(r) for r in c.execute("""SELECT u.id, u.email, a.status FROM event_attendees a
                                          JOIN users u ON u.id=a.user_id WHERE a.event_id=?""", (event_id,))]


def _event_dict(c, r, viewer_id: str, level: str):
    att = _attendees(c, r["id"])
    involved = r["owner_id"] == viewer_id or any(a["id"] == viewer_id and a["status"] != "declined" for a in att)
    if level == "full" or involved:
        organizer = c.execute("SELECT email FROM users WHERE id=?", (r["owner_id"],)).fetchone()["email"]
        my_status = "organizer" if r["owner_id"] == viewer_id else next(
            (a["status"] for a in att if a["id"] == viewer_id), "organizer")
        return dict(id=r["id"], title=crypto.decrypt(r["title_enc"]), notes=crypto.decrypt(r["notes_enc"]),
                    start=r["start_ts"], end=r["end_ts"], organizer=organizer, attendees=att,
                    my_status=my_status, mine=r["owner_id"] == viewer_id, case_id=r["case_id"])
    if level == "details":
        return dict(id=r["id"], title=crypto.decrypt(r["title_enc"]), notes="", start=r["start_ts"],
                    end=r["end_ts"], organizer=None, attendees=[], my_status=None, mine=False, case_id=None)
    return dict(id=None, title="Busy", notes="", start=r["start_ts"], end=r["end_ts"], organizer=None,
                attendees=[], my_status=None, mine=False, case_id=None)


def _rows_for(c, owner_id: str, start: float, end: float, include_pending: bool):
    # 'pending' is passed twice when tentative invites should be excluded, so the SQL text never changes.
    second = "pending" if include_pending else "accepted"
    return c.execute("""SELECT * FROM events e WHERE e.start_ts<? AND e.end_ts>? AND (e.owner_id=? OR e.id IN
                        (SELECT event_id FROM event_attendees WHERE user_id=? AND status IN ('accepted', ?)))
                        ORDER BY e.start_ts""", (end, start, owner_id, owner_id, second)).fetchall()


def my_events(user_id: str, start: float, end: float):
    """Own events + accepted invites + pending invites (shown as tentative)."""
    with db.conn() as c:
        return [_event_dict(c, r, user_id, "full") for r in _rows_for(c, user_id, start, end, True)]


def view_calendar(viewer_id: str, owner_id: str, start: float, end: float):
    """Returns (level, events) with titles hidden according to the level. (None, []) if no access."""
    with db.conn() as c:
        lvl = _level(c, viewer_id, owner_id)
        if not lvl:
            return None, []
        return lvl, [_event_dict(c, r, viewer_id, lvl) for r in _rows_for(c, owner_id, start, end, False)]


def pending_invites(user_id: str):
    with db.conn() as c:
        rows = c.execute("""SELECT e.* FROM events e JOIN event_attendees a ON a.event_id=e.id
                            WHERE a.user_id=? AND a.status='pending' AND e.end_ts>? ORDER BY e.start_ts""",
                         (user_id, db.now())).fetchall()
        return [_event_dict(c, r, user_id, "full") for r in rows]


# ---------- find a time ----------
def find_slots(user, participant_ids: List[str], first_day: dt.date, days: int, duration_min: int, limit: int = 12):
    """Free slots (Mon-Fri, working hours) where EVERYONE is free. Requires calendar access to each person."""
    people = list(dict.fromkeys([user["id"]] + list(participant_ids)))
    if len(people) > subscription.limits(user)["max_meeting_people"]:
        return [], "Too many people for your plan."
    if not (15 <= duration_min <= 480) or not (1 <= days <= 14):
        return [], "Invalid duration or date range."
    start = dt.datetime.combine(first_day, dt.time(0)).timestamp()
    end = start + days * 86400 + 3600
    busy = []
    with db.conn() as c:
        for p in people:
            if not _level(c, user["id"], p):
                return [], "You don't have calendar access to one of the selected people."
            busy += [(r["start_ts"], r["end_ts"]) for r in _rows_for(c, p, start, end, False)]
    now, dur, out = db.now(), duration_min * 60, []
    for d in range(days):
        day = first_day + dt.timedelta(days=d)
        if day.weekday() >= 5:
            continue
        t = dt.datetime.combine(day, dt.time(WORK_START))
        day_end = dt.datetime.combine(day, dt.time(WORK_END)).timestamp()
        while t.timestamp() + dur <= day_end:
            s = t.timestamp()
            if s >= now and all(not (s < b_end and s + dur > b_start) for b_start, b_end in busy):
                out.append((s, s + dur))
                if len(out) >= limit:
                    return out, None
            t += dt.timedelta(minutes=SLOT_STEP_MIN)
    return out, None


def export_events(user_id: str):
    with db.conn() as c:
        rows = c.execute("SELECT * FROM events WHERE owner_id=?", (user_id,)).fetchall()
    return [dict(title=crypto.decrypt(r["title_enc"]), notes=crypto.decrypt(r["notes_enc"]),
                 start=r["start_ts"], end=r["end_ts"]) for r in rows]
