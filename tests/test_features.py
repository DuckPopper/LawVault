import datetime as dt
import hashlib
import time
import pyotp
import pytest
import ai, auth, cal, cases, config, crypto, db, notify, presence, privacy, security_checks, subscription, twofa
from conftest import make_user


def _team(role="editor"):
    a, b, c = make_user("a@x.com"), make_user("b@x.com"), make_user("c@x.com")
    cid, _ = cases.create_case(a, "Smith v Acme")
    cases.add_member(a, cid, "b@x.com", role)
    return a, b, c, cid


def _fresh(u):
    with db.conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone()


@pytest.fixture
def fake_ai(monkeypatch):
    calls = []

    def fake(contents, system=ai.SYSTEM):
        calls.append(contents[-1]["parts"][0]["text"])
        return fake.reply, True
    fake.reply = "AI says hi"
    monkeypatch.setattr(ai, "_call", fake)
    fake.calls = calls
    return fake


# ---------- case roles ----------
def test_viewer_is_read_only():
    a, b, _, cid = _team("viewer")
    cases.post_message(a["id"], cid, "hello")
    assert [m["body"] for m in cases.get_messages(b["id"], cid)] == ["hello"]  # can read
    assert not cases.post_message(b["id"], cid, "let me in")                  # can't write
    assert cases.add_document(b, cid, "x.txt", "y")[0] is None
    assert cases.add_task(b["id"], cid, "task", "do it")[0] is None
    did, _ = cases.add_document(a, cid, "f.txt", "text")
    assert cases.get_document(b["id"], did) and not cases.save_analysis(b["id"], did, "tamper")


def test_owner_changes_roles_others_cannot():
    a, b, c, cid = _team("viewer")
    cases.add_member(a, cid, "c@x.com", "editor")
    assert not cases.set_role(c["id"], cid, b["id"], "editor")   # editor can't promote
    assert not cases.set_role(a["id"], cid, a["id"], "viewer")   # owner can't demote self
    assert not cases.set_role(a["id"], cid, b["id"], "owner")    # can't hand out owner
    assert cases.set_role(a["id"], cid, b["id"], "editor")
    assert cases.post_message(b["id"], cid, "now I can talk")


def test_invalid_role_on_invite():
    a, b, _, cid = _team()
    assert not cases.add_member(a, cid, "c@x.com", "owner")[0]


def test_old_member_rows_migrate_to_editor():
    a, b, _, cid = _team()
    with db.conn() as c:
        c.execute("UPDATE case_members SET role='member' WHERE user_id=?", (b["id"],))
    db.init_db()
    assert cases.get_case(b["id"], cid)["role"] == "editor"


# ---------- deadlines & tasks ----------
def test_tasks_lifecycle_and_permissions():
    a, b, c, cid = _team("viewer")
    due = time.time() + 3 * 86400
    tid, _ = cases.add_task(a["id"], cid, "deadline", "File defence", due, assignee_id=b["id"])
    assert tid
    assert cases.list_tasks(c["id"], cid) == []                    # stranger sees nothing
    assert cases.set_task_done(b["id"], tid, True)                 # viewer CAN tick own assigned task
    assert not cases.delete_task(b["id"], tid)                     # but can't delete
    assert not cases.set_task_done(c["id"], tid, False)
    assert cases.list_tasks(a["id"], cid)[0]["done"]


def test_task_validation():
    a, b, c, cid = _team()
    assert cases.add_task(a["id"], cid, "deadline", "No date")[0] is None
    assert cases.add_task(a["id"], cid, "meeting", "x")[0] is None
    assert cases.add_task(a["id"], cid, "task", "x", assignee_id=c["id"])[0] is None  # not a member


def test_deadlines_show_for_all_members_only():
    a, b, c, cid = _team()
    due = time.time() + 86400
    cases.add_task(a["id"], cid, "deadline", "Hearing", due)
    win = (time.time(), time.time() + 7 * 86400)
    assert [d["title"] for d in cases.deadlines_between(b["id"], *win)] == ["Hearing"]
    assert cases.deadlines_between(c["id"], *win) == []


def test_task_title_encrypted():
    a, b, _, cid = _team()
    cases.add_task(a["id"], cid, "task", "SecretTaskTitle")
    assert b"SecretTaskTitle" not in config.DB_PATH.read_bytes()


# ---------- notifications ----------
def test_chat_notifications_group_and_mentions():
    a, b, c, cid = _team()
    cases.post_message(a["id"], cid, "one")
    cases.post_message(a["id"], cid, "two")
    n = notify.recent(b["id"])
    chat = [x for x in n if x["kind"] == "chat"]
    assert len(chat) == 1 and chat[0]["count"] == 2           # grouped, not spammy
    cases.post_message(a["id"], cid, "@b@x.com please review")
    assert any(x["kind"] == "mention" for x in notify.recent(b["id"]))
    assert notify.recent(a["id"]) == [] or all(x["kind"] != "chat" for x in notify.recent(a["id"]))
    assert notify.recent(c["id"]) == []                       # outsiders get nothing


def test_notifications_for_calendar_and_case_add():
    a, b, _, cid = _team()
    assert any(x["kind"] == "case_added" for x in notify.recent(b["id"]))
    cal.request_access(b["id"], a["id"], "busy")
    assert any(x["kind"] == "cal_request" for x in notify.recent(a["id"]))
    cal.respond_request(a["id"], b["id"], True)
    assert any(x["kind"] == "cal_reply" for x in notify.recent(b["id"]))
    day = dt.date.today() + dt.timedelta(days=2)
    s = dt.datetime.combine(day, dt.time(10)).timestamp()
    eid, _ = cal.add_event(a, "Strategy", s, s + 3600, invitee_ids=[b["id"]])
    assert any(x["kind"] == "invite" for x in notify.recent(b["id"]))
    cal.respond_invite(b["id"], eid, True)
    assert any("accepted" in x["text"] for x in notify.recent(a["id"]))


def test_notification_read_toast_and_privacy():
    a, b, _, cid = _team()
    assert notify.unread_count(b["id"]) == 1
    assert len(notify.take_toasts(b["id"])) == 1 and notify.take_toasts(b["id"]) == []
    notify.mark_read(a["id"])                       # a can't mark b's as read
    assert notify.unread_count(b["id"]) == 1
    notify.mark_read(b["id"])
    assert notify.unread_count(b["id"]) == 0
    assert b"added you" not in config.DB_PATH.read_bytes()  # encrypted


# ---------- presence ----------
def test_presence_states():
    a, b, _, _ = _team()
    assert presence.status_of([a["id"]])[a["id"]] == "offline"   # never connected
    presence.touch(a["id"])
    assert presence.status_of([a["id"]])[a["id"]] == "online"
    with db.conn() as c:
        c.execute("UPDATE presence SET last_active=? WHERE user_id=?", (time.time() - 700, a["id"]))
    presence.heartbeat(a["id"])                                   # tab open, no activity
    assert presence.status_of([a["id"]])[a["id"]] == "idle"
    presence.set_choice(a["id"], "dnd")
    assert presence.status_of([a["id"]])[a["id"]] == "dnd" and presence.is_dnd(a["id"])
    presence.set_choice(a["id"], "invisible")
    assert presence.status_of([a["id"]])[a["id"]] == "offline"    # others see offline
    with db.conn() as c:
        c.execute("UPDATE presence SET status='online', last_heartbeat=? WHERE user_id=?",
                  (time.time() - 200, a["id"]))
    assert presence.status_of([a["id"]])[a["id"]] == "offline"    # tab closed
    assert not presence.set_choice(a["id"], "sleeping")


def test_presence_teams_statuses_duration_and_message():
    a, _, _, _ = _team()
    presence.touch(a["id"])
    for choice in ("busy", "brb", "away", "dnd"):
        assert presence.set_choice(a["id"], choice)
        assert presence.status_of([a["id"]])[a["id"]] == choice
    assert presence.is_dnd(a["id"])                               # last one picked was Do not disturb
    presence.set_choice(a["id"], "busy", "1h")
    assert presence.get_until(a["id"]) and presence.get_until(a["id"]) > time.time() + 3500
    with db.conn() as c:                                           # the hour is up
        c.execute("UPDATE presence SET status_until=? WHERE user_id=?", (time.time() - 1, a["id"]))
    assert presence.get_choice(a["id"]) == "online" and presence.get_until(a["id"]) is None
    presence.set_choice(a["id"], "dnd", "today")
    presence.reset(a["id"])
    assert presence.get_choice(a["id"]) == "online"
    assert not presence.set_choice(a["id"], "busy", "forever-and-ever")
    presence.set_message(a["id"], "  In court   until 3 pm  ")
    assert presence.get_message(a["id"]) == "In court until 3 pm"
    assert b"In court" not in config.DB_PATH.read_bytes()          # encrypted at rest
    presence.set_message(a["id"], "x" * 500)
    assert len(presence.get_message(a["id"])) == presence.MESSAGE_MAX
    presence.set_message(a["id"], "")
    assert presence.get_message(a["id"]) == ""


# ---------- sessions & devices ----------
def test_session_list_and_single_logout():
    a, b = make_user("a@x.com"), make_user("b@x.com")
    t1 = auth.create_session(a["id"], "Mozilla/5.0 (Macintosh; Mac OS X) Chrome/120", "10.0.0.1")
    t2 = auth.create_session(a["id"], "Mozilla/5.0 (iPhone) Safari/604", "10.0.0.2")
    sess = auth.list_sessions(a["id"])
    assert len(sess) == 2 and {s["ip"] for s in sess} == {"10.0.0.1", "10.0.0.2"}
    h2 = crypto.token_hash(t2)
    assert not auth.logout_session(b["id"], h2)          # can't log out someone else's device
    assert auth.logout_session(a["id"], h2)
    assert auth.validate_session(t2) is None and auth.validate_session(t1)


def test_peek_does_not_extend_idle_timer():
    a = make_user("a@x.com")
    t = auth.create_session(a["id"])
    with db.conn() as c:
        c.execute("UPDATE sessions SET last_seen=?", (time.time() - 100,))
    assert auth.peek_session(t)
    with db.conn() as c:
        assert time.time() - c.execute("SELECT last_seen FROM sessions").fetchone()["last_seen"] >= 99


def test_new_device_alert_only_after_first_device():
    a = make_user("a@x.com")
    auth.finish_login(a["id"], "UA-laptop", "1.1.1.1", "Chrome on macOS")
    assert notify.recent(a["id"]) == []                              # first ever device: no alert
    auth.finish_login(a["id"], "UA-laptop", "1.1.1.1", "Chrome on macOS")
    assert notify.recent(a["id"]) == []                              # known device: no alert
    auth.finish_login(a["id"], "UA-phone", "2.2.2.2", "Safari on iPhone")
    n = notify.recent(a["id"])
    assert len(n) == 1 and n[0]["kind"] == "security" and "Safari on iPhone" in n[0]["text"]


def test_cookie_token_format_guard():
    import session_cookie
    assert session_cookie._TOKEN_RE.match(crypto.new_token())
    for evil in ["abc", "x'; alert(1);//aaaaaaaaaaaaaaaa", "a" * 200, "a b c d e f g h i j k l m n o p q"]:
        assert not session_cookie._TOKEN_RE.match(evil)
    assert session_cookie.describe_device("Mozilla/5.0 (Macintosh; Intel Mac OS X) Chrome/120 Safari/537") \
        == "Chrome on macOS"


# ---------- authenticator 2FA ----------
def _enable_totp(u):
    secret, uri = twofa.start_setup(u["id"], u["email"])
    assert "otpauth://totp/" in uri and "LawVault" in uri
    assert twofa.confirm_setup(u["id"], pyotp.TOTP(secret).now())
    return secret


def _wrong(secret):
    """A 6-digit code that is NOT valid in any accepted time window."""
    t = pyotp.TOTP(secret)
    valid = {t.at(time.time() + d) for d in (-30, 0, 30)}
    return next(f"{n:06d}" for n in range(1_000_000) if f"{n:06d}" not in valid)


def test_totp_setup_requires_valid_code():
    a = make_user("a@x.com")
    secret, _ = twofa.start_setup(a["id"], a["email"])
    assert not twofa.confirm_setup(a["id"], _wrong(secret))
    assert not twofa.is_enabled(a["id"])


def test_totp_login_and_replay_blocked():
    a = make_user("a@x.com")
    secret = _enable_totp(a)
    assert twofa.is_enabled(a["id"])
    with db.conn() as c:
        c.execute("UPDATE user_totp SET last_step=0")  # allow a fresh login code in the same 30 s
    code = pyotp.TOTP(secret).now()
    assert twofa.verify(a["id"], code)
    assert not twofa.verify(a["id"], code)          # same code can't be reused
    assert not twofa.verify(a["id"], "12345a")


def test_totp_secret_encrypted_and_disable_needs_both():
    a = make_user("a@x.com")
    secret = _enable_totp(a)
    assert secret.encode() not in config.DB_PATH.read_bytes()
    assert not twofa.disable(a["id"], "wrong-password1", pyotp.TOTP(secret).now())[0]
    assert not twofa.disable(a["id"], "Str0ngPassw0rd!", _wrong(secret))[0]
    with db.conn() as c:
        c.execute("UPDATE user_totp SET last_step=0")
    assert twofa.disable(a["id"], "Str0ngPassw0rd!", pyotp.TOTP(secret).now())[0]
    assert not twofa.is_enabled(a["id"])


def test_wrong_totp_codes_lock_account():
    a = make_user("a@x.com")
    _enable_totp(a)
    for _ in range(config.MAX_FAILED_LOGINS):
        auth.second_factor_failed(a["id"])
    assert auth.is_locked(a["id"])


def test_admin_reset_2fa():
    a, adm = make_user("a@x.com"), make_user("admin@x.com")
    _enable_totp(a)
    twofa.admin_reset(adm["id"], a["id"])
    assert not twofa.is_enabled(a["id"])


# ---------- breached passwords ----------
class _Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_breached_password_rejected(monkeypatch):
    pw = "Summer2024Holiday"
    sha = hashlib.sha1(pw.encode()).hexdigest().upper()  # nosec - mirrors the HIBP protocol
    sent = []

    def fake_get(url, headers=None, timeout=None):
        sent.append(url)
        return _Resp(f"0000000000000000000000000000000000A:1\n{sha[5:]}:4321\n")
    monkeypatch.setattr(config, "HIBP_CHECK", True)
    monkeypatch.setattr(security_checks.requests, "get", fake_get)
    ok, msg = auth.signup("a@x.com", pw, True)
    assert not ok and "4,321" in msg
    assert sent[0].endswith("/range/" + sha[:5]) and pw not in sent[0] and sha not in sent[0]  # k-anonymity


def test_breach_check_fails_open(monkeypatch):
    def boom(*a, **k):
        raise OSError("offline")
    monkeypatch.setattr(config, "HIBP_CHECK", True)
    monkeypatch.setattr(security_checks.requests, "get", boom)
    assert auth.signup("a@x.com", "Summer2024Holiday", True)[0]


# ---------- team AI ----------
def test_ai_in_chat_posts_answer_for_team(fake_ai):
    a, b, _, cid = _team()
    cases.post_message(b["id"], cid, "@ai what is consideration?")
    ok, err = ai.answer_in_chat(_fresh(b), cid, "@ai what is consideration?")
    assert ok and err is None
    msgs = cases.get_messages(a["id"], cid)
    assert msgs[-1]["kind"] == "ai" and msgs[-1]["body"] == "AI says hi"   # everyone sees it
    assert subscription.ai_used_today(b["id"]) == 1                        # asker's quota


def test_ai_in_chat_blocked_for_viewers_and_outsiders(fake_ai):
    a, b, c, cid = _team("viewer")
    assert not ai.answer_in_chat(_fresh(b), cid, "@ai hi")[0]
    assert not ai.answer_in_chat(_fresh(c), cid, "@ai hi")[0]
    assert fake_ai.calls == []


def test_ai_trigger_matching():
    assert ai.AI_TRIGGER.match("@ai what?") and ai.AI_TRIGGER.match("  @AI: hi")
    assert not ai.AI_TRIGGER.match("email @aidan about it") and not ai.AI_TRIGGER.match("hi @ai")


def test_case_summary_membership_and_redaction(fake_ai):
    a, b, c, cid = _team("viewer")
    cases.post_message(a["id"], cid, "Client phone is 555-123-4567")
    assert ai.summarize_case(_fresh(c), cid) == (None, "No access to that case.")
    text, err = ai.summarize_case(_fresh(b), cid)                  # viewers may read a summary
    assert text == "AI says hi" and err is None
    assert "555-123-4567" not in fake_ai.calls[-1] and "<document>" in fake_ai.calls[-1]


def test_deadline_extraction_parses_untrusted_output(fake_ai):
    a = make_user("a@x.com")
    fake_ai.reply = ('Here you go:\n[{"title": "Notice due", "date": "2027-03-01"}, '
                     '{"title": "", "date": "2027-01-01"}, {"title": "Bad", "date": "next week"}, "junk"]')
    found, err = ai.extract_deadlines(a, "contract text")
    assert err is None and found == [dict(title="Notice due", date=dt.date(2027, 3, 1))]
    assert ai.parse_deadlines("no json here") == [] and ai.parse_deadlines("[not json]") == []


def test_ai_failure_refunds_team_features(monkeypatch):
    a, b, _, cid = _team()
    monkeypatch.setattr(ai, "_call", lambda contents, system=ai.SYSTEM: ("down", False))
    assert ai.summarize_case(_fresh(a), cid) == (None, "down")
    assert subscription.ai_used_today(a["id"]) == 0


# ---------- privacy cascade ----------
def test_delete_account_removes_new_data():
    a, b, _, cid = _team()
    _enable_totp(a)
    presence.touch(a["id"])
    auth.finish_login(a["id"], "UA", "", "")
    cases.post_message(b["id"], cid, "hi")
    cases.add_task(b["id"], cid, "task", "assigned", assignee_id=a["id"])
    privacy.delete_account(a["id"])
    with db.conn() as c:
        for t in ("user_totp", "presence", "known_devices", "sessions"):
            assert c.execute(f"SELECT COUNT(*) n FROM {t} WHERE user_id=?", (a["id"],)).fetchone()["n"] == 0  # nosec
        assert c.execute("SELECT COUNT(*) n FROM notifications WHERE user_id=?", (a["id"],)).fetchone()["n"] == 0
        assert c.execute("SELECT assignee_id FROM case_tasks").fetchone()["assignee_id"] is None


def test_ai_falls_back_when_model_busy(monkeypatch):
    import ai, config

    class R:
        def __init__(self, code, text=""):
            self.status_code, self._text = code, text
        def raise_for_status(self):
            pass
        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": self._text}]}}]}

    calls = []
    def fake_post(url, **kw):
        calls.append(url)
        return R(503) if len(calls) == 1 else R(200, "fallback answer")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "busy-model")
    monkeypatch.setattr(config, "GEMINI_FALLBACK_MODELS", ["backup-model"])
    monkeypatch.setattr(ai.requests, "post", fake_post)
    assert ai._call([{"role": "user", "parts": [{"text": "hi"}]}]) == ("fallback answer", True)
    assert "busy-model" in calls[0] and "backup-model" in calls[1]
    # every model busy -> clear error, not ok (so quota is refunded)
    monkeypatch.setattr(ai.requests, "post", lambda url, **kw: R(503))
    text, ok = ai._call([{"role": "user", "parts": [{"text": "hi"}]}])
    assert not ok and "unavailable" in text
