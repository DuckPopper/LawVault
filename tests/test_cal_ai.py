import datetime as dt
import json
import ai, cal, cal_ai, cases, db, subscription as sub
from conftest import make_user

TOMORROW = dt.date.today() + dt.timedelta(days=1)


def fresh(uid):
    with db.conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def say(monkeypatch, *replies, seen=None):
    """The model answers with these JSON objects, one per call."""
    it = iter(replies)

    def fake(contents, system=ai.SYSTEM):
        if seen is not None:
            seen.append(contents[0]["parts"][0]["text"])
        r = next(it)
        return (json.dumps(r) if isinstance(r, dict) else r), True
    monkeypatch.setattr(ai, "_call", fake)


def meeting(**kw):
    base = dict(intent="create", title="Meeting", date=TOMORROW.isoformat(), start_time="12:00", duration_min=None,
                people=[], place=None, no_people=False, no_place=False)
    return dict(base, **kw)


def events(u):
    return cal.my_events(u["id"], 0, 4102444800)


def team():
    a, b = make_user("a@x.com"), make_user("budi.santoso@x.com")
    cid, _ = cases.create_case(a, "Shared")
    cases.add_member(a, cid, "budi.santoso@x.com")
    return fresh(a["id"]), b


def test_besok_jam_12_adds_the_meeting_then_asks_who_and_where(monkeypatch):
    a = make_user("a@x.com")
    say(monkeypatch, meeting())
    state = {}
    r = cal_ai.handle(a, "besok jam 12 saya ada meeting", state)
    assert r["code"] == "created" and r["ask"] and r["ask_who"] and r["ask_where"]
    (e,) = events(a)
    assert e["title"] == "Meeting" and dt.datetime.fromtimestamp(e["start"]) == dt.datetime.combine(
        TOMORROW, dt.time(12))
    assert e["end"] - e["start"] == 3600                         # default one hour
    assert state["event"]["id"] == e["id"]


def test_the_answer_updates_the_same_meeting_with_teammate_place_and_outsider(monkeypatch):
    a, b = team()
    say(monkeypatch, meeting(), dict(intent="update", people=["Pak Budi", "Bu Ratna dari PT Maju"],
                                     place="kantor klien di Sudirman"))
    state = {}
    cal_ai.handle(a, "besok jam 12 saya ada meeting", state)
    r = cal_ai.handle(a, "sama Pak Budi dan Bu Ratna dari PT Maju di kantor klien di Sudirman", state)
    assert r["code"] == "updated" and r["invited"] == ["budi.santoso@x.com"]
    assert r["others"] == ["Bu Ratna dari PT Maju"] and not state
    (e,) = events(a)                                             # still ONE event
    assert e["location"] == "kantor klien di Sudirman"
    assert [x["email"] for x in e["attendees"]] == ["budi.santoso@x.com"]
    assert "Bu Ratna dari PT Maju" in e["notes"]
    assert [i["title"] for i in cal.pending_invites(b["id"])] == ["Meeting"]   # the teammate got the invitation


def test_everything_in_one_sentence_means_no_question(monkeypatch):
    a, _ = team()
    say(monkeypatch, meeting(title="Client call", start_time="15:30", duration_min=45, people=["budi"], place="Zoom"))
    state = {}
    r = cal_ai.handle(a, "besok jam setengah 4 sore call klien 45 menit sama budi lewat Zoom", state)
    assert r["code"] == "created" and not r["ask"] and not state
    (e,) = events(a)
    assert e["location"] == "Zoom" and e["end"] - e["start"] == 45 * 60 and len(e["attendees"]) == 1


def test_missing_time_is_asked_and_merged_with_the_next_answer(monkeypatch):
    a = make_user("a@x.com")
    say(monkeypatch, meeting(start_time=None), dict(intent="update", start_time="09:00", date=None, title=None))
    state = {}
    r = cal_ai.handle(a, "besok saya ada meeting", state)
    assert r["code"] == "need_when" and r["has_date"] and not r["has_time"] and not events(a)
    r = cal_ai.handle(a, "jam 9 pagi", state)
    assert r["code"] == "created"
    assert dt.datetime.fromtimestamp(events(a)[0]["start"]).time() == dt.time(9)


def test_saying_no_one_and_nowhere_ends_the_questions(monkeypatch):
    a = make_user("a@x.com")
    say(monkeypatch, meeting(), dict(intent="update", no_people=True, no_place=True))
    state = {}
    cal_ai.handle(a, "besok jam 12 meeting", state)
    r = cal_ai.handle(a, "sendirian saja, tidak ada tempat khusus", state)
    assert r["code"] == "nothing_new" and not state and len(events(a)) == 1


def test_a_second_new_meeting_is_not_mistaken_for_an_answer(monkeypatch):
    a = make_user("a@x.com")
    say(monkeypatch, meeting(), meeting(title="Sidang", start_time="14:00"))
    state = {}
    cal_ai.handle(a, "besok jam 12 meeting", state)
    r = cal_ai.handle(a, "besok jam 2 siang saya ada sidang", state)
    assert r["code"] == "created" and len(events(a)) == 2


def test_overlap_is_flagged_not_blocked(monkeypatch):
    a = make_user("a@x.com")
    say(monkeypatch, meeting(), meeting(title="Other"))
    cal_ai.handle(a, "x", {})
    r = cal_ai.handle(a, "y", {})
    assert r["code"] == "created" and r["clash"] == "Meeting"


def test_not_about_scheduling_and_past_times_add_nothing(monkeypatch):
    a = make_user("a@x.com")
    say(monkeypatch, dict(intent="none"), meeting(date=(dt.date.today() - dt.timedelta(days=2)).isoformat()),
        "sorry I cannot do that")
    assert cal_ai.handle(a, "apa itu wanprestasi?", {})["code"] == "not_scheduling"
    assert cal_ai.handle(a, "kemarin jam 12 meeting", {})["code"] == "past"
    assert cal_ai.handle(a, "???", {})["code"] == "not_scheduling"
    assert events(a) == []


def test_teammates_are_matched_here_so_their_names_never_reach_the_model(monkeypatch):
    a, _ = team()
    seen = []
    say(monkeypatch, meeting(people=["Budi"]), seen=seen)
    cal_ai.handle(a, "besok jam 12 meeting sama Budi, email saya a@x.com", {})
    assert "budi.santoso" not in seen[0] and "a@x.com" not in seen[0]      # emails are masked too
    assert events(a)[0]["attendees"][0]["email"] == "budi.santoso@x.com"


def test_ambiguous_names_are_noted_not_guessed(monkeypatch):
    a, _ = team()
    c = make_user("budi.hartono@x.com")
    cid, _ = cases.create_case(a, "Other")
    cases.add_member(a, cid, "budi.hartono@x.com")
    say(monkeypatch, meeting(people=["Budi"], place="Zoom"))
    r = cal_ai.handle(a, "besok jam 12 meeting sama Budi di Zoom", {})
    assert r["invited"] == [] and r["unsure"] == ["Budi"] and events(a)[0]["attendees"] == []


def test_prompt_injection_in_the_reply_cannot_do_more_than_fill_fields(monkeypatch):
    a = make_user("a@x.com")
    say(monkeypatch, meeting(title="x" * 500, people=["<script>"] + ["p"] * 50, place="y" * 900, duration_min=99999,
                             start_time="25:99"))
    assert cal_ai.handle(a, "besok meeting", {})["code"] == "need_when"
    say(monkeypatch, meeting(title="x" * 500, people=["p"] * 50, place="y" * 900, duration_min=99999))
    cal_ai.handle(a, "besok jam 12 meeting", {})
    (e,) = events(a)
    assert len(e["title"]) == 150 and len(e["location"]) == 200 and e["end"] - e["start"] == 3600


def test_parse_survives_garbage():
    for raw in ("", "no json", "{", "[1,2]", '{"intent": 5, "date": 7, "people": "x", "start_time": []}'):
        p = cal_ai.parse(raw)
        assert p["intent"] == "none" and p["date"] is None and p["people"] == []


def test_ai_failure_refunds_the_request_and_adds_nothing(monkeypatch):
    a = make_user("a@x.com")
    monkeypatch.setattr(ai, "_call", lambda contents, system=ai.SYSTEM: ("down", False))
    assert cal_ai.handle(a, "besok jam 12 meeting", {}) == dict(code="error", error="down")
    assert sub.ai_used_today(a["id"]) == 0 and events(a) == []


def test_uses_one_ai_request_per_message_and_respects_the_daily_cap(monkeypatch):
    a = make_user("a@x.com")                                    # free: 5 a day
    say(monkeypatch, *[meeting(start_time=f"{9 + i}:00") for i in range(6)])
    codes = [cal_ai.handle(a, "besok meeting", {})["code"] for _ in range(6)]
    assert codes[:5] == ["created"] * 5 and codes[5] == "error" and sub.ai_used_today(a["id"]) == 5


def test_switched_off_in_a_custom_plan(monkeypatch):
    a = make_user("a@x.com")
    sub.mock_checkout(a["id"], "pro")
    sub.mock_checkout(a["id"], "custom", custom=dict(units={}, features={"calendar_ai": False}))
    say(monkeypatch, meeting())
    r = cal_ai.handle(fresh(a["id"]), "besok jam 12 meeting", {})
    assert r["code"] == "error" and sub.ai_used_today(a["id"]) == 0


def test_only_the_organizer_can_update_an_event(monkeypatch):
    a, b = team()
    cal.add_event(a, "Mine", dt.datetime.now().timestamp() + 3600, dt.datetime.now().timestamp() + 7200)
    eid = events(a)[0]["id"]
    assert cal.update_event(fresh(b["id"]), eid, location="Hacked")[0] is False
    assert cal.update_event(a, eid, location="Room 1")[0] is True


def test_location_is_private_to_people_with_full_view():
    a, b = team()
    cal.set_visibility(a["id"], "details")
    cal.add_event(a, "Hearing", dt.datetime.now().timestamp() + 3600, dt.datetime.now().timestamp() + 7200,
                  location="Secret courtroom")
    lvl, evs = cal.view_calendar(b["id"], a["id"], 0, 4102444800)
    assert lvl == "details" and evs[0]["title"] == "Hearing" and evs[0]["location"] == ""
    with db.conn() as c:
        raw = c.execute("SELECT location_enc FROM events").fetchone()["location_enc"]
    assert "courtroom" not in raw                               # encrypted at rest


def test_a_teammate_the_model_forgot_is_still_invited(monkeypatch):
    a, _ = team()
    say(monkeypatch, meeting(), dict(intent="update", people=["Pak Ratna"], place="Zoom"))
    state = {}
    cal_ai.handle(a, "besok jam 12 meeting", state)
    r = cal_ai.handle(a, "sama budi dan Pak Ratna lewat Zoom", state)         # model only returned Pak Ratna
    assert r["invited"] == ["budi.santoso@x.com"] and r["others"] == ["Pak Ratna"]
    assert len(events(a)[0]["attendees"]) == 1


def test_a_shared_first_name_is_never_guessed_from_the_sentence(monkeypatch):
    a, _ = team()
    make_user("budi.hartono@x.com")
    cid, _ = cases.create_case(a, "Other")
    cases.add_member(a, cid, "budi.hartono@x.com")
    say(monkeypatch, meeting(place="Zoom"))
    r = cal_ai.handle(a, "besok jam 12 meeting sama budi lewat Zoom", {})      # model returned no people at all
    assert r["invited"] == [] and events(a)[0]["attendees"] == []


def test_titles_start_with_a_capital():
    assert cal_ai.parse('{"intent":"create","title":"meeting dengan klien"}')["title"] == "Meeting dengan klien"
