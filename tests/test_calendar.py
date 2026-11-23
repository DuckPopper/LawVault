import datetime as dt
import cal, cases, config, db, privacy, subscription
from conftest import make_user


def _next_weekday(n=1) -> dt.date:
    d = dt.date.today() + dt.timedelta(days=n)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def _ts(day, h, m=0):
    return dt.datetime.combine(day, dt.time(h, m)).timestamp()


def _team():
    """a and b share a case; c is a stranger."""
    a, b, c = make_user("a@x.com"), make_user("b@x.com"), make_user("c@x.com")
    cid, _ = cases.create_case(a, "Shared")
    cases.add_member(a, cid, "b@x.com")
    return a, b, c


DAY = None


def setup_function():
    global DAY
    DAY = _next_weekday()


WEEK = lambda: (_ts(DAY, 0), _ts(DAY, 0) + 7 * 86400)


# ---------- visibility toggle ----------
def test_calendar_private_by_default():
    a, b, _ = _team()
    cal.add_event(b, "Divorce hearing", _ts(DAY, 10), _ts(DAY, 11))
    assert cal.access_level(a["id"], b["id"]) is None
    assert cal.view_calendar(a["id"], b["id"], *WEEK()) == (None, [])


def test_busy_mode_hides_titles_and_notes():
    a, b, _ = _team()
    cal.add_event(b, "Divorce hearing", _ts(DAY, 10), _ts(DAY, 11), notes="client is nervous")
    cal.set_visibility(b["id"], "busy")
    lvl, evs = cal.view_calendar(a["id"], b["id"], *WEEK())
    assert lvl == "busy" and len(evs) == 1
    assert evs[0]["title"] == "Busy" and evs[0]["notes"] == "" and evs[0]["id"] is None


def test_details_mode_shows_titles_but_never_notes():
    a, b, _ = _team()
    cal.add_event(b, "Divorce hearing", _ts(DAY, 10), _ts(DAY, 11), notes="client is nervous")
    cal.set_visibility(b["id"], "details")
    _, evs = cal.view_calendar(a["id"], b["id"], *WEEK())
    assert evs[0]["title"] == "Divorce hearing" and evs[0]["notes"] == ""


def test_visibility_only_applies_to_teammates():
    a, b, c = _team()
    cal.set_visibility(b["id"], "details")
    assert cal.access_level(c["id"], b["id"]) is None
    assert cal.view_calendar(c["id"], b["id"], *WEEK()) == (None, [])


def test_invalid_visibility_rejected():
    a = make_user("a@x.com")
    assert not cal.set_visibility(a["id"], "public")
    assert cal.get_visibility(a["id"]) == "private"


def test_leaving_case_removes_toggle_access():
    a, b, _ = _team()
    cal.set_visibility(b["id"], "details")
    cid = cases.list_cases(a["id"])[0]["id"]
    cases.remove_member(a["id"], cid, b["id"])
    assert cal.access_level(a["id"], b["id"]) is None


# ---------- access requests ----------
def test_request_approve_then_revoke():
    a, b, _ = _team()
    ok, _ = cal.request_access(a["id"], b["id"], "details")
    assert ok and cal.access_level(a["id"], b["id"]) is None  # pending != access
    assert [r["email"] for r in cal.incoming_requests(b["id"])] == ["a@x.com"]
    assert cal.respond_request(b["id"], a["id"], True)
    assert cal.access_level(a["id"], b["id"]) == "details"
    cal.revoke(b["id"], a["id"])
    assert cal.access_level(a["id"], b["id"]) is None


def test_owner_can_downgrade_request_to_busy():
    a, b, _ = _team()
    cal.request_access(a["id"], b["id"], "details")
    cal.respond_request(b["id"], a["id"], True, "busy")
    assert cal.access_level(a["id"], b["id"]) == "busy"


def test_deny_request():
    a, b, _ = _team()
    cal.request_access(a["id"], b["id"], "busy")
    assert cal.respond_request(b["id"], a["id"], False)
    assert cal.access_level(a["id"], b["id"]) is None and cal.incoming_requests(b["id"]) == []


def test_requester_cannot_approve_own_request():
    a, b, _ = _team()
    cal.request_access(a["id"], b["id"], "details")
    # a tries to approve as if a were the owner of b's calendar
    assert not cal.respond_request(a["id"], a["id"], True)
    assert not cal.respond_request(a["id"], b["id"], True)
    assert cal.access_level(a["id"], b["id"]) is None


def test_strangers_cannot_request():
    a, b, c = _team()
    ok, msg = cal.request_access(c["id"], b["id"], "busy")
    assert not ok and cal.incoming_requests(b["id"]) == []


def test_bad_level_or_self_request_rejected():
    a, b, _ = _team()
    assert not cal.request_access(a["id"], b["id"], "full")[0]
    assert not cal.request_access(a["id"], a["id"], "busy")[0]


# ---------- events & invites ----------
def test_event_validation():
    a = make_user("a@x.com")
    assert cal.add_event(a, "", _ts(DAY, 10), _ts(DAY, 11))[0] is None
    assert cal.add_event(a, "x", _ts(DAY, 11), _ts(DAY, 10))[0] is None
    assert cal.add_event(a, "x", _ts(DAY, 10), _ts(DAY, 10) + 8 * 86400)[0] is None


def test_can_only_invite_teammates():
    a, b, c = _team()
    assert cal.add_event(a, "Meet", _ts(DAY, 10), _ts(DAY, 11), invitee_ids=[c["id"]])[0] is None
    assert cal.add_event(a, "Meet", _ts(DAY, 10), _ts(DAY, 11), invitee_ids=[b["id"]])[0]


def test_invite_accept_flow_and_visibility():
    a, b, _ = _team()
    eid, _ = cal.add_event(a, "Strategy", _ts(DAY, 14), _ts(DAY, 15), notes="bring exhibits", invitee_ids=[b["id"]])
    inv = cal.pending_invites(b["id"])
    assert len(inv) == 1 and inv[0]["notes"] == "bring exhibits" and inv[0]["organizer"] == "a@x.com"
    assert [e["my_status"] for e in cal.my_events(b["id"], *WEEK())] == ["pending"]
    assert cal.respond_invite(b["id"], eid, True)
    assert cal.pending_invites(b["id"]) == []
    assert [e["my_status"] for e in cal.my_events(b["id"], *WEEK())] == ["accepted"]


def test_declined_invite_disappears():
    a, b, _ = _team()
    eid, _ = cal.add_event(a, "Strategy", _ts(DAY, 14), _ts(DAY, 15), invitee_ids=[b["id"]])
    cal.respond_invite(b["id"], eid, False)
    assert cal.my_events(b["id"], *WEEK()) == []


def test_non_invitee_cannot_respond_or_delete():
    a, b, c = _team()
    eid, _ = cal.add_event(a, "Private", _ts(DAY, 9), _ts(DAY, 10))
    assert not cal.respond_invite(c["id"], eid, True)
    assert not cal.delete_event(c["id"], eid)
    assert not cal.delete_event(b["id"], eid)
    assert len(cal.my_events(a["id"], *WEEK())) == 1


def test_owner_delete_removes_for_everyone():
    a, b, _ = _team()
    eid, _ = cal.add_event(a, "Strategy", _ts(DAY, 14), _ts(DAY, 15), invitee_ids=[b["id"]])
    cal.respond_invite(b["id"], eid, True)
    assert cal.delete_event(a["id"], eid)
    assert cal.my_events(b["id"], *WEEK()) == []


def test_meeting_size_limited_by_plan():
    a = make_user("a@x.com")
    cid, _ = cases.create_case(a, "Big")
    others = []
    for i in range(3):
        o = make_user(f"o{i}@x.com")
        cases.add_member(a, cid, o["email"]) if i < 2 else None
        others.append(o)
    subscription.mock_checkout(a["id"], "pro")  # raise member cap so 3rd can join
    with db.conn() as c:
        a = c.execute("SELECT * FROM users WHERE id=?", (a["id"],)).fetchone()
    cases.add_member(a, cid, "o2@x.com")
    subscription.cancel(a["id"])
    with db.conn() as c:
        a = c.execute("SELECT * FROM users WHERE id=?", (a["id"],)).fetchone()
    ids = [o["id"] for o in others]
    assert cal.add_event(a, "Big meeting", _ts(DAY, 10), _ts(DAY, 11), invitee_ids=ids)[0] is None  # 4 > 3


def test_event_text_encrypted_at_rest():
    a = make_user("a@x.com")
    cal.add_event(a, "SecretHearingTitle", _ts(DAY, 10), _ts(DAY, 11), notes="SecretNotesHere")
    raw = config.DB_PATH.read_bytes()
    assert b"SecretHearingTitle" not in raw and b"SecretNotesHere" not in raw


# ---------- find a time ----------
def test_find_slots_avoids_everyones_busy_time():
    a, b, _ = _team()
    cal.set_visibility(b["id"], "busy")
    cal.add_event(a, "A busy", _ts(DAY, 9), _ts(DAY, 12))
    cal.add_event(b, "B busy", _ts(DAY, 12), _ts(DAY, 15))
    slots, err = cal.find_slots(a, [b["id"]], DAY, 1, 60, limit=50)
    assert err is None and slots
    assert slots[0][0] == _ts(DAY, 15)
    for s, e in slots:
        assert s >= _ts(DAY, 15) and e <= _ts(DAY, 18)


def test_find_slots_requires_calendar_access():
    a, b, c = _team()
    slots, err = cal.find_slots(a, [b["id"]], DAY, 1, 60)   # b is private
    assert err and not slots
    slots, err = cal.find_slots(a, [c["id"]], DAY, 1, 60)   # stranger
    assert err and not slots


def test_find_slots_skips_weekends_and_ignores_declined():
    a, b, _ = _team()
    cal.set_visibility(b["id"], "busy")
    eid, _ = cal.add_event(a, "All day", _ts(DAY, 9), _ts(DAY, 18), invitee_ids=[b["id"]])
    cal.respond_invite(b["id"], eid, False)
    cal.delete_event(a["id"], eid)
    sat = DAY + dt.timedelta(days=(5 - DAY.weekday()) % 7)
    slots, _ = cal.find_slots(a, [b["id"]], sat, 2, 60, limit=50)
    assert slots == []  # Saturday + Sunday


def test_find_slots_input_validation():
    a = make_user("a@x.com")
    assert cal.find_slots(a, [], DAY, 30, 60)[1]
    assert cal.find_slots(a, [], DAY, 1, 5)[1]


# ---------- privacy ----------
def test_export_and_delete_include_calendar():
    a, b, _ = _team()
    cal.add_event(a, "Mine", _ts(DAY, 10), _ts(DAY, 11))
    cal.request_access(b["id"], a["id"], "busy")
    assert [e["title"] for e in privacy.export_user_data(a["id"])["calendar_events"]] == ["Mine"]
    privacy.delete_account(a["id"])
    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) n FROM events").fetchone()["n"] == 0
        assert c.execute("SELECT COUNT(*) n FROM calendar_access").fetchone()["n"] == 0
