import datetime as dt
import json
import pytest
import cal, calproviders as prov, calsync, cases, config, crypto, db, subscription as sub
from calproviders import RemoteEvent
from conftest import make_user

H = 3600
NOW = lambda: dt.datetime.now().timestamp()


def fresh(uid):
    with db.conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def pro(email="a@x.com"):
    u = make_user(email)
    sub.mock_checkout(u["id"], "pro")
    return fresh(u["id"])


class Fake:
    """An in-memory calendar server that behaves like Google/Apple for the sync engine."""
    kind, account = "fake", None

    def __init__(self):
        self.events, self.n, self.pushed, self.deleted, self.hidden = {}, 0, [], [], False

    def put(self, title="Remote", start=None, end=None, notes="", loc="", updated=None, read_only=False, rid=None):
        self.n += 1
        rid = rid or f"r{self.n}"
        start = start if start is not None else NOW() + 2 * 86400
        self.events[rid] = dict(title=title, notes=notes, location=loc, start=start, end=end or start + H,
                                all_day=False, updated=updated or NOW(), read_only=read_only)
        return rid

    def pull(self, cursor, start, end):
        out = [] if self.hidden else [RemoteEvent(
            id=i, version=prov.fingerprint(e["title"], e["notes"], e["location"], e["start"], e["end"]),
            title=e["title"], notes=e["notes"], location=e["location"], start=e["start"], end=e["end"],
            updated=e["updated"], read_only=e["read_only"]) for i, e in self.events.items()]
        return out, None, True

    def push(self, ev, remote_id, all_day=False):
        self.pushed.append(dict(ev))
        rid = remote_id if remote_id in self.events else self.put(rid=None)
        self.events[rid] = dict(title=ev["title"], notes=ev["notes"], location=ev["location"], start=ev["start"],
                                end=ev["end"], all_day=False, updated=NOW(), read_only=False)
        return rid, prov.fingerprint(ev["title"], ev["notes"], ev["location"], ev["start"], ev["end"])

    def delete(self, rid):
        self.deleted.append(rid)
        self.events.pop(rid, None)


@pytest.fixture
def remote(monkeypatch):
    fake = Fake()
    monkeypatch.setattr(calsync, "_provider", lambda link: fake)
    return fake


def link(u):
    lid, err = calsync.add_link(u["id"], "google", "me@gmail.com", {"refresh_token": "SECRET-REFRESH"})
    assert lid, err
    return lid


def mine(u):
    return sorted(cal.my_events(u["id"], 0, 4102444800), key=lambda e: e["start"])


# ------------------------------------------------------------------ the engine
def test_remote_events_come_in_once(remote):
    a = pro()
    remote.put("Hearing", loc="Court 3", notes="bring file")
    lid = link(a)
    assert calsync.sync_link(lid)["imported"] == 1
    (e,) = mine(a)
    assert (e["title"], e["location"], e["notes"]) == ("Hearing", "Court 3", "bring file")
    assert calsync.sync_link(lid) == dict(imported=0, updated=0, removed_here=0, pushed=0, removed_there=0)
    assert len(mine(a)) == 1 and remote.pushed == []            # no echo back


def test_new_local_events_go_out_straight_away(remote):
    a = pro()
    link(a)
    cal.add_event(a, "Client call", NOW() + H, NOW() + 2 * H, "notes", None, None, "Zoom")
    (r,) = remote.events.values()
    assert (r["title"], r["location"], r["notes"]) == ("Client call", "Zoom", "notes")
    assert len(remote.pushed) == 1
    calsync.sync_user(a["id"])
    assert len(remote.pushed) == 1                              # unchanged events are not sent again


def test_local_edit_and_delete_reach_the_other_calendar(remote):
    a = pro()
    link(a)
    eid, _ = cal.add_event(a, "Call", NOW() + H, NOW() + 2 * H)
    cal.update_event(a, eid, location="Room 9")
    assert next(iter(remote.events.values()))["location"] == "Room 9" and len(remote.events) == 1
    cal.delete_event(a["id"], eid)
    assert remote.events == {} and len(remote.deleted) == 1


def test_remote_edit_and_delete_reach_lawvault(remote):
    a = pro()
    rid = remote.put("Old title")
    lid = link(a)
    calsync.sync_link(lid)
    remote.events[rid].update(title="New title", location="Zoom")
    assert calsync.sync_link(lid)["updated"] == 1
    assert (mine(a)[0]["title"], mine(a)[0]["location"]) == ("New title", "Zoom") and remote.pushed == []
    del remote.events[rid]
    assert calsync.sync_link(lid)["removed_here"] == 1 and mine(a) == []


def test_when_both_sides_changed_the_newer_edit_wins(remote):
    a = pro()
    rid = remote.put("Meeting")
    lid = link(a)
    calsync.sync_link(lid)
    eid = mine(a)[0]["id"]
    remote.events[rid].update(title="Remote edit", updated=NOW() + 50)
    with db.conn() as c:
        c.execute("UPDATE events SET title_enc=?, updated_at=? WHERE id=?", (crypto.encrypt("Local edit"), NOW(), eid))
    calsync.sync_link(lid)
    assert mine(a)[0]["title"] == "Remote edit"                  # remote was newer
    remote.events[rid].update(title="Remote again", updated=NOW() - 500)
    with db.conn() as c:
        c.execute("UPDATE events SET title_enc=?, updated_at=? WHERE id=?", (crypto.encrypt("Local wins"), NOW(), eid))
    calsync.sync_link(lid)
    assert mine(a)[0]["title"] == "Local wins" and remote.events[rid]["title"] == "Local wins"


def test_attendees_and_other_peoples_events_never_leave(remote):
    a = pro()
    b = make_user("b@x.com")
    cid, _ = cases.create_case(a, "Shared")
    cases.add_member(a, cid, "b@x.com")
    link(a)
    cal.add_event(b, "Bob private", NOW() + H, NOW() + 2 * H)
    cal.add_event(a, "Team call", NOW() + 3 * H, NOW() + 4 * H, "", None, [b["id"]])
    assert [p["title"] for p in remote.pushed] == ["Team call"]
    assert set(remote.pushed[0]) == {"uid", "title", "notes", "location", "start", "end"}   # no attendee data


def test_far_away_events_are_left_alone(remote):
    a = pro()
    remote.put("Ancient", start=NOW() - 400 * 86400)
    remote.put("Far future", start=NOW() + 800 * 86400)
    calsync.sync_link(link(a))
    assert mine(a) == []


def test_a_suspicious_empty_listing_deletes_nothing(remote):
    a = pro()
    for i in range(6):
        remote.put(f"E{i}", start=NOW() + (i + 1) * 86400)
    lid = link(a)
    calsync.sync_link(lid)
    remote.hidden = True                                        # the server "forgets" everything
    res = calsync.sync_link(lid)
    assert "Nothing was deleted" in res["error"] and len(mine(a)) == 6
    assert calsync.list_links(a["id"])[0]["status"] == "error"
    remote.hidden = False
    assert calsync.sync_link(lid)["removed_here"] == 0 and calsync.list_links(a["id"])[0]["status"] == "ok"


def test_read_only_occurrences_are_never_written_back_or_resurrected(remote):
    a = pro()
    remote.put("Weekly", rid="series#1", read_only=True)
    lid = link(a)
    calsync.sync_link(lid)
    eid = mine(a)[0]["id"]
    cal.delete_event(a["id"], eid)
    calsync.sync_link(lid)
    assert remote.deleted == [] and "series#1" in remote.events and mine(a) == []     # not deleted there, not back here


def test_two_calendars_mirror_each_other_through_lawvault_without_duplicates(monkeypatch):
    google_side, apple_side = Fake(), Fake()
    monkeypatch.setattr(calsync, "_provider", lambda l: google_side if l["provider"] == "google" else apple_side)
    a = pro()
    google_side.put("From Google")
    link(a)
    calsync.add_link(a["id"], "apple", "me@icloud.com", {})
    calsync.sync_user(a["id"])
    calsync.sync_user(a["id"])
    calsync.sync_user(a["id"])
    assert [e["title"] for e in mine(a)] == ["From Google"]
    assert [e["title"] for e in apple_side.events.values()] == ["From Google"]
    assert len(google_side.events) == 1                         # no echo, no copies


def test_sync_pauses_without_the_plan_and_deletes_nothing(remote):
    a = pro()
    remote.put("Keep me")
    lid = link(a)
    calsync.sync_link(lid)
    sub.cancel(a["id"])
    res = calsync.sync_link(lid)
    assert "not part of your current plan" in res["error"] and len(mine(a)) == 1
    assert calsync.list_links(a["id"])[0]["status"] == "paused"
    sub.mock_checkout(a["id"], "pro")
    assert calsync.sync_link(lid)["imported"] == 0 and calsync.list_links(a["id"])[0]["status"] == "ok"


def test_free_users_cannot_connect(remote):
    u = make_user("f@x.com")
    assert calsync.add_link(u["id"], "google", "x", {}) == (None, "Calendar sync is not part of your plan.")
    assert calsync.connect_apple(u["id"], "me@icloud.com", "abcd-efgh-ijkl-mnop")[0] is False


def test_credentials_are_encrypted_and_the_link_limit_holds(remote):
    a = pro()
    link(a)
    with db.conn() as c:
        raw = c.execute("SELECT cred_enc FROM calendar_links").fetchone()["cred_enc"]
    assert "SECRET-REFRESH" not in raw and "SECRET-REFRESH" in crypto.decrypt(raw)
    for i in range(3):
        assert calsync.add_link(a["id"], "apple", f"x{i}@icloud.com", {})[0]
    assert calsync.add_link(a["id"], "apple", "x9@icloud.com", {})[1] == "You can connect up to 4 calendars."
    assert calsync.add_link(a["id"], "google", "me@gmail.com", {"refresh_token": "NEW"})[0]   # same account: refresh
    assert len(calsync.list_links(a["id"])) == 4


def test_disconnect_keeps_events_unless_asked_to_purge(remote):
    a = pro()
    remote.put("Came from there")
    lid = link(a)
    calsync.sync_link(lid)
    cal.add_event(a, "Mine", NOW() + H, NOW() + 2 * H)
    b = make_user("b@x.com")
    assert calsync.remove_link(b["id"], lid) is False            # only the owner can disconnect
    assert calsync.remove_link(a["id"], lid, delete_imported=True)
    assert [e["title"] for e in mine(a)] == ["Mine"] and calsync.list_links(a["id"]) == []
    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) n FROM event_links").fetchone()["n"] == 0


def test_a_provider_crash_is_reported_not_raised(remote, monkeypatch):
    a = pro()
    lid = link(a)
    monkeypatch.setattr(remote, "pull", lambda *x: (_ for _ in ()).throw(RuntimeError("boom with secret-token")))
    res = calsync.sync_link(lid)
    assert "unavailable" in res["error"] and "secret-token" not in res["error"]
    monkeypatch.setattr(remote, "pull", lambda *x: (_ for _ in ()).throw(prov.AuthError("x")))
    assert calsync.sync_link(lid)["error"] == "Please connect this calendar again."
    assert calsync.list_links(a["id"])[0]["status"] == "reauth"


def test_the_background_worker_starts_only_once(monkeypatch):
    started = []
    monkeypatch.setattr(calsync.threading, "Thread", lambda **kw: type("T", (), {"start": lambda s: started.append(1)})())
    monkeypatch.setitem(calsync._worker, "started", False)
    calsync.start_worker()
    calsync.start_worker()
    assert started == [1]


# ------------------------------------------------------------------ Google sign-in
@pytest.fixture
def google(monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "csecret")
    monkeypatch.setattr(config, "GOOGLE_REDIRECT_URI", "http://localhost:8502/calendar")


class Resp:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._b, self.text = status, body or {}, text

    def json(self): return self._b
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_google_url_has_a_single_use_state_bound_to_the_user(google, remote, monkeypatch):
    a, other = pro(), pro("b@x.com")
    url = calsync.google_auth_url(a["id"])
    assert "access_type=offline" in url and "calendar.events" in url and "client_id=cid" in url
    state = url.split("state=")[1]
    monkeypatch.setattr(calsync.requests, "post", lambda *x, **k: Resp(200, dict(
        access_token="AT", refresh_token="RT", expires_in=3600)))
    assert calsync.google_finish(other["id"], "code", state)[0] is False         # someone else's state
    assert calsync.google_finish(a["id"], "code", state)[0] is False             # ...and it is now used up
    state = calsync.google_auth_url(a["id"]).split("state=")[1]
    assert calsync.google_finish(a["id"], "code", state) == (True, "Google Calendar connected.")
    assert calsync.google_finish(a["id"], "code", state)[0] is False             # single use
    (l,) = calsync.list_links(a["id"])
    assert l["provider"] == "google"


def test_google_state_expires_and_unknown_states_fail(google):
    a = pro()
    state = calsync.google_auth_url(a["id"]).split("state=")[1]
    with db.conn() as c:
        c.execute("UPDATE oauth_states SET expires_at=?", (db.now() - 1,))
    assert "no longer valid" in calsync.google_finish(a["id"], "code", state)[1]
    assert calsync.google_finish(a["id"], "code", "made-up")[0] is False
    assert calsync.google_finish(a["id"], "code", "")[0] is False


def test_google_without_a_refresh_token_or_config_is_refused(google, monkeypatch):
    a = pro()
    monkeypatch.setattr(calsync.requests, "post", lambda *x, **k: Resp(200, dict(access_token="AT")))
    state = calsync.google_auth_url(a["id"]).split("state=")[1]
    ok, msg = calsync.google_finish(a["id"], "code", state)
    assert not ok and "offline access" in msg and calsync.list_links(a["id"]) == []
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "")
    assert calsync.google_auth_url(a["id"]) is None and not calsync.google_configured()


def test_free_user_cannot_finish_google_sign_in(google, monkeypatch):
    u = make_user("f@x.com")
    state = calsync.google_auth_url(u["id"]).split("state=")[1]
    monkeypatch.setattr(calsync.requests, "post", lambda *x, **k: Resp(200, dict(refresh_token="RT")))
    assert calsync.google_finish(u["id"], "code", state) == (False, "Calendar sync is not part of your plan.")


def test_apple_connect(monkeypatch, remote):
    a = pro()
    assert calsync.connect_apple(a["id"], "not-an-email", "x")[0] is False
    monkeypatch.setattr(prov.Apple, "discover", classmethod(lambda cls, u, p: (_ for _ in ()).throw(
        prov.AuthError("Apple did not accept that Apple ID or app-specific password."))))
    assert "did not accept" in calsync.connect_apple(a["id"], "me@icloud.com", "abcd-efgh-ijkl-mnop")[1]
    monkeypatch.setattr(prov.Apple, "discover", classmethod(lambda cls, u, p: []))
    assert "No calendar" in calsync.connect_apple(a["id"], "me@icloud.com", "abcd-efgh-ijkl-mnop")[1]
    monkeypatch.setattr(prov.Apple, "discover", classmethod(lambda cls, u, p: [("Home", "https://p1.icloud.com/h/")]))
    assert calsync.connect_apple(a["id"], "me@icloud.com", "abcd-efgh-ijkl-mnop") == (True, "Apple Calendar connected.")
    with db.conn() as c:
        cred = json.loads(crypto.decrypt(c.execute("SELECT cred_enc FROM calendar_links").fetchone()["cred_enc"]))
    assert cred["calendar_url"] == "https://p1.icloud.com/h/" and cred["password"] == "abcd-efgh-ijkl-mnop"


# ------------------------------------------------------------------ the Google REST client
class Script:
    """Replaces requests.request/post for the Google client and records what was sent."""
    def __init__(self, monkeypatch, *responses):
        self.sent, self.queue = [], list(responses)
        monkeypatch.setattr(prov.requests, "request", self.request)
        monkeypatch.setattr(prov.requests, "post", self.post)

    def request(self, method, url, **kw):
        self.sent.append((method, url, kw))
        return self.queue.pop(0)

    def post(self, url, **kw):
        self.sent.append(("POST", url, kw))
        return Resp(200, dict(access_token="NEWTOKEN", expires_in=3600))


def g(monkeypatch, *responses, cred=None):
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "cid")
    saved = []
    s = Script(monkeypatch, *responses)
    client = prov.Google(cred or dict(access_token="AT", refresh_token="RT", expires_at=NOW() + 3000), saved.append)
    return client, s, saved


def test_google_pull_parses_timed_all_day_and_cancelled(monkeypatch):
    items = [dict(id="a", etag='"1"', summary="Timed", start=dict(dateTime="2030-01-02T10:00:00Z"),
                  end=dict(dateTime="2030-01-02T11:00:00Z"), location="Court", description="d",
                  updated="2030-01-01T00:00:00Z"),
             dict(id="b", start=dict(date="2030-01-05"), end=dict(date="2030-01-06"), summary="All day"),
             dict(id="c", status="cancelled"),
             dict(id="d", eventType="workingLocation", start=dict(date="2030-01-05"), end=dict(date="2030-01-06")),
             dict(id="e", summary="No time")]
    client, s, _ = g(monkeypatch, Resp(200, dict(items=items, nextSyncToken="TOK", summary="me@gmail.com")))
    events, cursor, complete = client.pull(None, NOW(), NOW() + 9)
    assert cursor == "TOK" and complete and client.account == "me@gmail.com"
    by = {e.id: e for e in events}
    assert set(by) == {"a", "b", "c"} and by["c"].deleted and by["b"].all_day and not by["a"].all_day
    assert by["a"].title == "Timed" and by["a"].end - by["a"].start == 3600 and by["a"].version == '"1"'
    params = s.sent[0][2]["params"]
    assert "timeMin" in params and "syncToken" not in params


def test_google_incremental_pull_uses_the_token_and_recovers_from_410(monkeypatch):
    client, s, _ = g(monkeypatch, Resp(200, dict(items=[], nextSyncToken="T2")))
    assert client.pull("T1", 0, 1)[2] is False and s.sent[0][2]["params"]["syncToken"] == "T1"
    client, s, _ = g(monkeypatch, Resp(410), Resp(200, dict(items=[], nextSyncToken="T3")))
    events, cursor, complete = client.pull("OLD", NOW(), NOW() + 9)
    assert cursor == "T3" and complete and "syncToken" not in s.sent[1][2]["params"]


def test_google_pages_are_followed(monkeypatch):
    one = dict(id="a", start=dict(date="2030-01-05"), end=dict(date="2030-01-06"))
    client, _, _ = g(monkeypatch, Resp(200, dict(items=[one], nextPageToken="P2")),
                     Resp(200, dict(items=[dict(one, id="b")], nextSyncToken="T")))
    assert [e.id for e in client.pull(None, 0, 1)[0]] == ["a", "b"]


def test_google_refreshes_an_expired_token_and_retries_once_on_401(monkeypatch):
    client, s, saved = g(monkeypatch, Resp(200, dict(items=[], nextSyncToken="T")),
                         cred=dict(access_token="OLD", refresh_token="RT", expires_at=0))
    client.pull(None, 0, 1)
    assert s.sent[0][1] == prov.GOOGLE_TOKEN_URL and s.sent[1][2]["headers"]["Authorization"] == "Bearer NEWTOKEN"
    assert saved and saved[-1]["access_token"] == "NEWTOKEN"
    client, s, _ = g(monkeypatch, Resp(401, text="x"), Resp(200, dict(items=[], nextSyncToken="T")))
    assert client.pull(None, 0, 1)[1] == "T"
    client, s, _ = g(monkeypatch, Resp(401, text="x"), Resp(401, text="x"))
    with pytest.raises(prov.AuthError):
        client.pull(None, 0, 1)


def test_google_push_sends_no_attendees_and_never_emails(monkeypatch):
    ev = dict(title="T", notes="N", location="L", start=1893456000.0, end=1893459600.0)
    client, s, _ = g(monkeypatch, Resp(200, dict(id="new1", etag='"9"')))
    assert client.push(ev, None) == ("new1", '"9"')
    method, url, kw = s.sent[0]
    assert method == "POST" and kw["params"] == {"sendUpdates": "none"} and "attendees" not in kw["json"]
    assert kw["json"]["summary"] == "T" and kw["json"]["start"]["timeZone"] == "UTC"
    client, s, _ = g(monkeypatch, Resp(200, dict(etag='"10"')))
    assert client.push(ev, "abc/def") == ("abc/def", '"10"') and s.sent[0][0] == "PATCH" and "abc%2Fdef" in s.sent[0][1]
    client, s, _ = g(monkeypatch, Resp(404), Resp(200, dict(id="fresh", etag='"1"')))       # deleted meanwhile
    assert client.push(ev, "gone")[0] == "fresh"
    client, s, _ = g(monkeypatch, Resp(200, dict(id="x", etag="1")))
    client.push(ev, None, all_day=True)
    assert "date" in s.sent[0][2]["json"]["start"] and "dateTime" not in s.sent[0][2]["json"]["start"]


def test_google_delete_ignores_already_gone(monkeypatch):
    client, s, _ = g(monkeypatch, Resp(404))
    client.delete("x")
    client, s, _ = g(monkeypatch, Resp(500))
    with pytest.raises(RuntimeError):
        client.delete("x")


# ------------------------------------------------------------------ Apple / iCalendar
def test_ics_round_trip_and_all_day():
    import icalendar
    ev = dict(title="Sidang, PN Jakarta; ruang 3", notes="Bawa berkas\nlengkap", location="PN Jakarta Pusat",
              start=1893456000.0, end=1893459600.0)
    ics = prov.build_ics(ev, "abc@lawvault", False)
    comp = next(iter(icalendar.Calendar.from_ical(ics).walk("VEVENT")))
    r = prov._vevent_to_remote(comp, "href", False)
    assert (r.title, r.notes, r.location, r.start, r.end) == (ev["title"], ev["notes"], ev["location"], ev["start"],
                                                            ev["end"])
    assert r.version == prov.fingerprint(ev["title"], ev["notes"], ev["location"], ev["start"], ev["end"], False)
    day = dt.datetime(2030, 3, 4).timestamp()
    ics = prov.build_ics(dict(title="Libur", notes="", location="", start=day, end=day + 86400), "u@lawvault", True)
    comp = next(iter(icalendar.Calendar.from_ical(ics).walk("VEVENT")))
    r = prov._vevent_to_remote(comp, "h", False)
    assert r.all_day and r.start == day and r.end == day + 86400 and "DESCRIPTION" not in ics


def test_apple_pull_reads_plain_and_recurring_events():
    import icalendar
    start = dt.datetime.now(dt.timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)

    def obj(url, body):
        return type("O", (), dict(url=url, icalendar_instance=icalendar.Calendar.from_ical(body)))()
    plain = ("BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:p1\nSUMMARY:Plain\nDTSTART:" + start.strftime(
        "%Y%m%dT%H%M%SZ") + "\nDURATION:PT30M\nEND:VEVENT\nEND:VCALENDAR\n")
    weekly = ("BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:w1\nSUMMARY:Weekly\nRRULE:FREQ=WEEKLY;COUNT=3\nDTSTART:"
              + start.strftime("%Y%m%dT%H%M%SZ") + "\nDTEND:" + (start + dt.timedelta(hours=1)).strftime(
                  "%Y%m%dT%H%M%SZ") + "\nEND:VEVENT\nEND:VCALENDAR\n")

    class Cal:
        def search(self, **kw):
            assert kw["event"] is True
            return [obj("https://c/1.ics", plain), obj("https://c/2.ics", weekly)]
    a = prov.Apple(dict(username="me@icloud.com", password="p", calendar_url="u"))
    a._cal = Cal()
    events, cursor, complete = a.pull(None, NOW(), NOW() + 30 * 86400)
    assert cursor is None and complete
    plain_ev = next(e for e in events if e.title == "Plain")
    assert plain_ev.id == "https://c/1.ics" and plain_ev.end - plain_ev.start == 1800 and not plain_ev.read_only
    weekly_ev = [e for e in events if e.title == "Weekly"]
    assert len(weekly_ev) == 3 and all(e.read_only and e.id.startswith("https://c/2.ics#") for e in weekly_ev)
    assert len({e.id for e in weekly_ev}) == 3


def test_apple_push_creates_then_updates():
    saved = {}

    class Obj:
        url = "https://c/new.ics"

    class Cal:
        client = object()

        def save_event(self, ics):
            saved["ics"] = ics
            return Obj()
    a = prov.Apple(dict(username="u", password="p", calendar_url="x"))
    a._cal = Cal()
    ev = dict(uid="local1", title="Call", notes="", location="Zoom", start=1893456000.0, end=1893459600.0)
    rid, ver = a.push(ev, None)
    assert rid == "https://c/new.ics" and "UID:local1@lawvault" in saved["ics"] and "attendee" not in saved["ics"].lower()
    assert ver == prov.fingerprint("Call", "", "Zoom", ev["start"], ev["end"], False)


def test_apple_login_failures_become_auth_errors(monkeypatch):
    class AuthorizationError(Exception):
        pass

    def boom(cls, u, p):
        raise AuthorizationError("401")
    monkeypatch.setattr(prov.Apple, "_client", classmethod(boom))
    with pytest.raises(prov.AuthError):
        prov.Apple.discover("me@icloud.com", "wrong-wrong-wrong")
    a = prov.Apple(dict(username="u", password="p", calendar_url="x"))
    monkeypatch.setattr(a, "_calendar", lambda: (_ for _ in ()).throw(AuthorizationError("401")))
    with pytest.raises(prov.AuthError):
        a.pull(None, 0, 1)
    monkeypatch.setattr(a, "_calendar", lambda: (_ for _ in ()).throw(OSError("down")))
    with pytest.raises(prov.ProviderError):
        a.pull(None, 0, 1)


def test_the_icloud_server_address_is_fixed():
    assert prov.ICLOUD_URL == "https://caldav.icloud.com/"
