"""Interface language: every string the code passes to t() must have an Indonesian translation."""
import ast
import datetime as dt
import pathlib
import re
import pytest
import ai, auth, cases, db, detector, i18n, i18n_id, legal, news, notify, presence, subscription, voice
import views.detector_ui as detector_ui
from conftest import make_user

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = sorted([*ROOT.glob("*.py"), *ROOT.glob("views/*.py")])
HELPERS_TRANSLATING_ARGS = {"page_header", "section", "stat", "_row", "_h", "_group"}
BACKEND = ["auth.py", "otp.py", "twofa.py", "cal.py", "cases.py", "docutil.py", "ai.py", "legal.py",
           "subscription.py", "security_checks.py", "voice.py", "cal_ai.py", "calsync.py", "calproviders.py", "gdocs.py", "news.py"]


def _literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _literal(node.left), _literal(node.right)
        return a + b if a is not None and b is not None else None
    return None


def _call_name(call):
    fn = call.func
    return fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else None


def _used_keys():
    keys = {}
    for f in SOURCES:
        if f.name in ("i18n_id.py", "i18n.py"):
            continue
        for n in ast.walk(ast.parse(f.read_text())):
            if not isinstance(n, ast.Call):
                continue
            name = _call_name(n)
            args = []
            if name == "t" and n.args:
                args = n.args[:1]
            elif name == "plural" and len(n.args) >= 3:
                args = n.args[1:3]
            elif name in HELPERS_TRANSLATING_ARGS:
                args = n.args[:1] if name in ("section", "_h", "_group") else n.args[:3]
                args += [k.value for k in n.keywords if k.arg == "eyebrow"]
            for a in args:
                s = _literal(a)
                if s:
                    keys[s] = f.name
    return keys


def _placeholders(s):
    return set(re.findall(r"\{(\w+)\}", s))


def test_every_ui_string_is_translated():
    missing = {k: f for k, f in _used_keys().items() if k not in i18n_id.ID}
    assert not missing, "Add these to i18n_id.ID:\n" + "\n".join(f"  {f}: {k!r}" for k, f in missing.items())


def detector_texts():
    r = detector.analyze("word " * 20 + ". ".join(["A short one here today", "Another quite different sentence follows this one"] * 20))
    return [detector_ui.DISCLAIMER, *(x for s in r.get("signals", []) for x in (s["name"], s["note"]))]


def test_strings_kept_in_data_tables_are_translated():
    import views.calendar_ui as cal_ui
    import views.cases_ui as cases_ui
    import views.calendar_grid as grid
    import views.legal_ui as legal_ui
    import views.ai_ui as ai_ui
    strings = [*presence.CHOICE_LABEL.values(), *presence.LABEL.values(), *cal_ui.LEVEL_LABEL.values(),
               *cal_ui.VIS_HELP.values(), *cal_ui.VIEWS, *cases_ui.ROLE_LABEL.values(), *legal_ui._KIND_LABEL.values(),
               *(lbl for _, lbl in grid.LEGEND), grid.BUSY, ai.DISCLAIMER, ai_ui.BACKGROUND_NOTE,
               legal_ui.BACKGROUND_NOTE, *legal.JURISDICTIONS, *legal.DRAFT_TYPES,
               *(p["name"] for p in subscription.PLANS.values()), "Custom",
               *(a["label"] for a in subscription.ADDONS.values()), *subscription.FEATURE_LABEL.values(),
               *voice.LANGS.values(), *cal_ui.SYNC_STATUS.values(), *cal_ui.PROVIDER_LABEL.values(), "High", "Medium", "Low", "Owner", "Viewer",
               *news.TOPICS.values(), "Likely AI-written", "Possibly AI-assisted", "Likely human-written",
               *(s for s in detector_texts())]
    for m in legal.TOOLS.values():
        strings += [m["label"], m["blurb"]]
    missing = [s for s in strings if s not in i18n_id.ID]
    assert not missing, missing


def _return_messages(path):
    """Capitalised sentences that backend functions return to the UI as the last tuple element or alone."""
    out = []
    for n in ast.walk(ast.parse((ROOT / path).read_text())):
        if isinstance(n, ast.Return) and n.value is not None:
            vals = n.value.elts if isinstance(n.value, ast.Tuple) else [n.value]
            for v in vals:
                s = _literal(v)
                if s and re.match(r"[A-Z]", s) and " " in s and len(s) > 12:
                    out.append(s)
    return out


@pytest.mark.parametrize("path", BACKEND)
def test_backend_messages_are_translated(path):
    unknown = []
    for s in _return_messages(path):
        i18n_id_hit = s in i18n_id.ID or any(rx.fullmatch(s) for rx, _ in i18n_id.PATTERNS)
        if not i18n_id_hit:
            unknown.append(s)
    assert not unknown, unknown


def test_translations_keep_their_placeholders():
    bad = [k for k, v in i18n_id.ID.items() if _placeholders(k) != _placeholders(v)]
    assert not bad, bad
    for k, v in i18n_id.ID.items():  # every translation must survive str.format with its own placeholders
        v.format(**{p: "x" for p in _placeholders(k)})


# ---------- behaviour ----------
@pytest.fixture
def lang(monkeypatch):
    holder = {"code": "id"}
    monkeypatch.setattr(i18n, "lang", lambda: holder["code"])
    return holder


def test_t_translates_formats_and_falls_back(lang):
    assert i18n.t("Cases") == "Kasus"
    assert i18n.t("Added {n} deadline(s). They also appear on everyone's calendar.", n=3).startswith("3 tenggat")
    assert i18n.t("A string nobody translated {x}", x=1) == "A string nobody translated 1"
    lang["code"] = "en"
    assert i18n.t("Cases") == "Cases"
    assert i18n.t("{n} cases", n=2) == "2 cases"


def test_plural_and_tm(lang):
    assert i18n.plural(1, "{n} invitation waiting in Invites.", "{n} invitations waiting in Invites.") == \
        "1 undangan menunggu di Undangan."
    assert i18n.tm("This password has appeared in 1,234 known data breaches. Please choose a different one.") == \
        "Kata sandi ini muncul dalam 1,234 kebocoran data yang diketahui. Silakan pilih yang lain."
    assert i18n.tm("Totally new text") == "Totally new text"
    lang["code"] = "en"
    assert i18n.tm("Case created.") == "Case created."


def test_dates_are_localised():
    d = dt.date(2026, 11, 23)  # a Monday
    assert i18n.fmt(d, "%A, %B %-d", "id") == "Senin, November 23"
    assert i18n.fmt(d, "%a %b %d", "id") == "Sen Nov 23"
    assert i18n.fmt(dt.date(2026, 8, 3), "%B %b", "id") == "Agustus Agu"
    assert i18n.fmt(d, "%A %B", "en") == "Monday November"
    assert i18n.fmt(d, "%d/%m/%Y", "id") == "23/11/2026"


def test_every_notification_template_translates(lang):
    """Messages the backend stores (in English) must be matched by a pattern so they show in Indonesian."""
    a, b = make_user("a@x.com"), make_user("b@x.com")
    cid, _ = cases.create_case(a, "Sentosa v Maju")
    cases.add_member(a, cid, "b@x.com", "viewer")
    cases.post_message(a["id"], cid, "hello @b@x.com")
    cases.post_message(a["id"], cid, "another")
    cases.add_task(a["id"], cid, "deadline", "File reply", dt.datetime(2030, 1, 1).timestamp(), b["id"])
    import cal
    cal.add_event(a, "Strategy call", dt.datetime(2030, 1, 2, 10).timestamp(), dt.datetime(2030, 1, 2, 11).timestamp(),
                  "", cid, [b["id"]])
    cal.request_access(b["id"], a["id"], "details")
    cal.respond_request(a["id"], b["id"], True)
    with db.conn() as c:
        ev = c.execute("SELECT id FROM events").fetchone()
    cal.respond_invite(b["id"], ev["id"], True)
    auth.finish_login(b["id"], "Mozilla/5.0 (Macintosh)", "1.2.3.4", "Safari on Mac")
    auth.finish_login(b["id"], "Other Agent", "", "Chrome on Windows")
    untranslated = []
    for uid in (a["id"], b["id"]):
        for n in notify.recent(uid):
            if i18n.tm(n["text"]) == n["text"]:
                untranslated.append(n["text"])
    assert not untranslated, untranslated


def test_language_is_saved_per_user_and_chosen_at_signup():
    ok, _ = auth.signup("indo@x.com", "Str0ngPassw0rd!", True, "id")
    assert ok
    with db.conn() as c:
        row = c.execute("SELECT * FROM users WHERE email='indo@x.com'").fetchone()
    assert row["lang"] == "id"
    assert make_user("en@x.com")["lang"] == "en"
    assert auth.set_language(row["id"], "en") and not auth.set_language(row["id"], "xx")
    with db.conn() as c:
        assert c.execute("SELECT lang FROM users WHERE id=?", (row["id"],)).fetchone()["lang"] == "en"
    ok, _ = auth.signup("weird@x.com", "Str0ngPassw0rd!", True, "klingon")
    with db.conn() as c:
        assert c.execute("SELECT lang FROM users WHERE email='weird@x.com'").fetchone()["lang"] == "en"


def test_ai_replies_in_the_users_language(monkeypatch):
    seen = []
    monkeypatch.setattr(ai, "_call", lambda contents, system=ai.SYSTEM: (seen.append(system) or "ok", True))
    a = make_user("a@x.com")
    ai.ask(a, "What is wanprestasi?", [])
    assert "Bahasa Indonesia" not in seen[-1]
    auth.set_language(a["id"], "id")
    with db.conn() as c:
        a = c.execute("SELECT * FROM users WHERE id=?", (a["id"],)).fetchone()
    ai.ask(a, "Apa itu wanprestasi?", [])
    assert "Bahasa Indonesia" in seen[-1]
    # the case-analysis tools pick their own output language, whatever the interface language is
    legal.run(a, "analysis", None, "PT A signed a contract with PT B and PT B did not deliver the goods on time.",
              "Indonesia", "en")
    assert "Bahasa Indonesia" not in seen[-1]
