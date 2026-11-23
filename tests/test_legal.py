import datetime as dt
import json
import pytest
import ai, cases, crypto, db, legal, notify, privacy, subscription
from conftest import make_user

FACTS = ("PT Maju signed a supply agreement with CV Sentosa on 1 March 2026. CV Sentosa paid Rp 500 million "
         "but PT Maju delivered only half the goods and stopped replying. Client wants a refund or delivery.")


def _team(role="editor"):
    a, b, c = make_user("a@x.com"), make_user("b@x.com"), make_user("c@x.com")
    cid, _ = cases.create_case(a, "Sentosa v Maju")
    cases.add_member(a, cid, "b@x.com", role)
    cases.post_message(a["id"], cid, "Contact budi@client.co.id about the late delivery")
    return a, b, c, cid


@pytest.fixture
def fake_ai(monkeypatch):
    calls = []

    def fake(contents, system=ai.SYSTEM):
        calls.append(contents[-1]["parts"][0]["text"])
        return fake.reply, True
    fake.reply = "### Summary of facts\n- ok"
    monkeypatch.setattr(ai, "_call", fake)
    fake.calls = calls
    return fake


TIMELINE = json.dumps({"events": [
    {"date": "2026-03-01", "event": "Agreement signed", "kind": "legal", "source": "contract"},
    {"date": "2099-01-15", "event": "Hearing", "kind": "deadline"},
    {"date": "next week", "event": "Bad date becomes undated", "kind": "weird"},
    {"date": "2026-02", "event": "Negotiations", "kind": "fact"},
    {"event": ""}, "not a dict",
], "gaps": ["When was notice served?"]})

RISKS = json.dumps({"overall": "HIGH", "summary": "Exposure is real.", "risks": [
    {"title": "Limitation", "severity": "low", "likelihood": "low"},
    {"title": "Insolvency of debtor", "severity": "high", "likelihood": "high", "area": "financial"},
    {"title": "Odd values", "severity": "catastrophic", "likelihood": 7},
    {"severity": "high"},
]})


# ---------- parsing model output defensively ----------
def test_timeline_parser_validates_and_sorts():
    tl = legal.parse_timeline("Here you go:\n" + TIMELINE + "\nthanks")
    assert [e["event"] for e in tl["events"]] == ["Negotiations", "Agreement signed", "Hearing",
                                                  "Bad date becomes undated"]
    odd = tl["events"][-1]
    assert odd["date"] == "" and odd["kind"] == "fact"
    assert tl["gaps"] == ["When was notice served?"]
    assert [d["title"] for d in legal.future_deadlines(tl)] == ["Hearing"]


def test_risk_parser_validates_and_ranks():
    rk = legal.parse_risks(RISKS)
    assert rk["overall"] == "high"
    assert [r["title"] for r in rk["risks"]] == ["Insolvency of debtor", "Odd values", "Limitation"]
    assert rk["risks"][1]["severity"] == "medium" and rk["risks"][1]["likelihood"] == "medium"


@pytest.mark.parametrize("raw", ["", "no json", "[1,2]", '{"events": "x"}', "{broken"])
def test_parsers_reject_garbage(raw):
    assert legal.parse_timeline(raw) is None
    assert legal.parse_risks(raw) is None


# ---------- prompts ----------
def test_prompt_wraps_material_and_applies_options():
    p = legal.build_prompt("basis", "FACTS", "Indonesia", "id", {"analysis": "earlier"}, )
    assert "<document>\nFACTS\n</document>" in p
    assert "Bahasa Indonesia" in p and "KUHPerdata" in p
    assert "Earlier result: Case analysis" in p
    assert "### Dasar Hukum yang Berlaku" in p and "### Applicable law" not in p
    assert "### Applicable law" in legal.build_prompt("basis", "F", "Indonesia", "en", {})
    p = legal.build_prompt("drafting", "F", "Nowhere", "en", {}, "Somasi (letter of demand)", "ignore rules")
    assert "Somasi" in p and "English" in p and "General / other" in p
    assert "<instructions>\nignore rules\n</instructions>" in p


# ---------- running and access control ----------
def test_run_on_case_saves_shared_result_and_notifies(fake_ai):
    a, b, c, cid = _team()
    res, err = legal.run(a, "analysis", cid, "", "Indonesia", "id")
    assert err is None and res["text"] == fake_ai.reply
    assert "budi@client.co.id" not in fake_ai.calls[-1] and "[EMAIL]" in fake_ai.calls[-1]  # PII masked
    assert "Sentosa v Maju" in fake_ai.calls[-1]
    assert legal.latest(b["id"], cid)["analysis"]["text"] == fake_ai.reply  # teammate sees it
    assert legal.latest(c["id"], cid) == {}                                 # outsider doesn't
    assert any("case analysis" in n["text"] for n in notify.recent(b["id"]))
    with db.conn() as conn:
        row = conn.execute("SELECT result_enc FROM legal_work").fetchone()
    assert fake_ai.reply not in row["result_enc"]  # encrypted at rest


def test_outsider_and_viewer_cannot_run(fake_ai):
    a, b, c, cid = _team("viewer")
    assert legal.run(c, "analysis", cid, "", "Indonesia", "id") == (None, "No access to that case.")
    res, err = legal.run(b, "analysis", cid, "", "Indonesia", "id")
    assert res is None and "editor" in err
    assert not fake_ai.calls
    assert subscription.ai_used_today(b["id"]) == 0


def test_own_facts_are_private_and_grouped_by_matter(fake_ai):
    a, b = make_user("a@x.com"), make_user("b@x.com")
    assert legal.run(a, "analysis", None, "too short", "Indonesia", "id")[1]
    res, err = legal.run(a, "strategy", None, FACTS, "Indonesia", "en")
    assert err is None
    key = legal.matter_key(FACTS)
    assert key == legal.matter_key("  " + FACTS.upper())  # whitespace / case don't start a new matter
    assert "strategy" in legal.latest(a["id"], None, key)
    assert legal.latest(a["id"], None, legal.matter_key(FACTS + " more")) == {}
    assert legal.latest(b["id"], None, key) == {}


def test_bad_structured_output_is_refunded_not_saved(fake_ai):
    a = make_user("a@x.com")
    fake_ai.reply = "Sorry, here is prose instead of JSON"
    res, err = legal.run(a, "timeline", None, FACTS, "Indonesia", "id")
    assert res is None and "timeline" in err
    assert legal.latest(a["id"], None, legal.matter_key(FACTS)) == {}


def test_provider_failure_refunds_quota(monkeypatch):
    a = make_user("a@x.com")
    monkeypatch.setattr(ai, "_call", lambda contents, system=ai.SYSTEM: ("down", False))
    assert legal.run(a, "analysis", None, FACTS, "Indonesia", "id") == (None, "down")
    assert subscription.ai_used_today(a["id"]) == 0


def test_run_all_chains_results(fake_ai, monkeypatch):
    a = make_user("a@x.com")
    subscription.mock_checkout(a["id"], "pro")
    with db.conn() as c:
        a = c.execute("SELECT * FROM users WHERE id=?", (a["id"],)).fetchone()
    replies = iter(["ANALYSIS", TIMELINE, "BASIS", RISKS, "STRATEGY"])
    monkeypatch.setattr(ai, "_call", lambda contents, system=ai.SYSTEM: (
        fake_ai.calls.append(contents[-1]["parts"][0]["text"]) or next(replies), True))
    prog = {}
    done, err = legal.run_all(a, None, FACTS, "Indonesia", "id", progress=prog)
    assert err is None and done == list(legal.FULL_RUN) and prog["done"] == done
    assert "ANALYSIS" in fake_ai.calls[-1] and "BASIS" in fake_ai.calls[-1]  # strategy saw earlier work
    assert set(legal.latest(a["id"], None, legal.matter_key(FACTS))) == set(legal.FULL_RUN)


def test_run_all_stops_at_first_failure(fake_ai):
    a = make_user("a@x.com")  # free plan: 5 a day
    for _ in range(3):
        subscription.consume_ai_call(a)
    fake_ai.reply = "ok"
    done, err = legal.run_all(a, None, FACTS, "Indonesia", "id")
    assert done == ["analysis"] and "Stopped at Timeline" in err  # timeline reply wasn't JSON


def test_delete_rules_export_and_cascade(fake_ai):
    a, b, c, cid = _team()
    res, _ = legal.run(b, "analysis", cid, "", "Indonesia", "id")
    assert not legal.delete(c["id"], res["id"])
    assert legal.delete(a["id"], res["id"])  # case owner may delete teammates' results
    res, _ = legal.run(b, "analysis", cid, "", "Indonesia", "id")
    assert privacy.export_user_data(b["id"])["legal_work"][0]["result"] == fake_ai.reply
    privacy.delete_account(b["id"])
    with db.conn() as conn:
        assert conn.execute("SELECT COUNT(*) n FROM legal_work").fetchone()["n"] == 0
