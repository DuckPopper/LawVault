"""Quick stress + attack test against a throwaway LawVault database (never the real data folder)."""
import os, sys, tempfile, time, secrets, statistics
from concurrent.futures import ThreadPoolExecutor

APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)
os.environ["LAWVAULT_DATA_DIR"] = tempfile.mkdtemp()
os.environ["DEV_MODE"] = "1"
os.environ["GEMINI_API_KEY"] = ""
os.environ["HIBP_CHECK"] = "0"

import config, db, auth, cases, otp  # noqa: E402

db.init_db()
PW = "Str0ngPassw0rd!"
R = {}


def user(email):
    ok, msg = auth.signup(email, PW, True)
    assert ok, msg
    with db.conn() as c:
        c.execute("UPDATE users SET plan='firm', plan_expires=? WHERE email=?", (db.now() + 86400, email))
        return c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()


# ---------- 1. Load: 25 team members chatting in one case at the same time ----------
owner = user("owner@t.test")
team = [user(f"m{i}@t.test") for i in range(24)]
cid, _ = cases.create_case(owner, "Stress case")
for m in team:
    cases.add_member(owner, cid, m["email"], "editor")
everyone = [owner] + team
lat, errors = [], []


def chat(u):
    for i in range(40):
        t = time.perf_counter()
        try:
            cases.post_message(u["id"], cid, f"msg {i} from {u['email']}")
            cases.get_messages(u["id"], cid, limit=50)
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))
        lat.append((time.perf_counter() - t) * 1000)


t0 = time.perf_counter()
with ThreadPoolExecutor(25) as ex:
    list(ex.map(chat, everyone))
dur = time.perf_counter() - t0
lat.sort()
R["load"] = dict(users=25, ops=len(lat) * 2, seconds=round(dur, 1), ops_per_s=round(len(lat) * 2 / dur),
                 p50_ms=round(statistics.median(lat), 1), p95_ms=round(lat[int(len(lat) * .95)], 1),
                 errors=len(errors), sample_error=errors[:1])
with db.conn() as c:
    R["load"]["messages_saved"] = c.execute("SELECT COUNT(*) n FROM messages WHERE case_id=?", (cid,)).fetchone()["n"]

# ---------- 2. Brute force password, one at a time ----------
victim = user("victim@t.test")
seq = [auth.login_step1("victim@t.test", f"guess{i}xxxxxx")[0] for i in range(200)]
R["bruteforce_sequential"] = dict(attempts=200, evaluated=seq.count("invalid"), blocked=seq.count("locked"),
                                  correct_pw_after=auth.login_step1("victim@t.test", PW)[0])

# ---------- 3. Brute force password, 50 guesses in parallel ----------
victim2 = user("victim2@t.test")
with ThreadPoolExecutor(50) as ex:
    par = list(ex.map(lambda i: auth.login_step1("victim2@t.test", f"guess{i}xxxxxx")[0], range(50)))
R["bruteforce_parallel"] = dict(attempts=50, evaluated=par.count("invalid"), blocked=par.count("locked"))

# ---------- 4. OTP guessing ----------
_, _, code = otp.issue(victim["id"], "victim@t.test", "login")
hits = sum(otp.verify(victim["id"], "login", f"{i:06d}") for i in range(1000) if f"{i:06d}" != code)
R["otp_guessing"] = dict(guesses=1000, accepted=hits, real_code_after=otp.verify(victim["id"], "login", code))

# ---------- 5. Session token guessing ----------
R["session_guessing"] = dict(guesses=10000,
                             accepted=sum(bool(auth.validate_session(secrets.token_urlsafe(32))) for _ in range(10000)))

# ---------- 6. IDOR: 20 outsiders try to reach the case ----------
outs = [user(f"out{i}@t.test") for i in range(20)]
leaks = 0
for o in outs:
    leaks += bool(cases.get_case(o["id"], cid)) + bool(cases.get_messages(o["id"], cid)) + bool(cases.members(o["id"], cid))
    leaks += bool(cases.post_message(o["id"], cid, "hi") not in (None, False) and cases.get_messages(owner["id"], cid, 1)[-1]["body"] == "hi")
R["idor"] = dict(attempts=80, leaks=leaks)

# ---------- 7. SQL injection payloads ----------
payloads = ["' OR '1'='1", "admin'--", "x'; DROP TABLE users;--", "\" OR 1=1 --", "' UNION SELECT * FROM sessions--"]
bad = 0
for p in payloads:
    bad += auth.login_step1(p, p)[0] == "ok"
    bad += auth.login_step1("owner@t.test", p)[0] == "ok"
with db.conn() as c:
    users_left = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
R["sqli"] = dict(payloads=len(payloads) * 2, logins_bypassed=bad, users_table_intact=users_left > 0)

# ---------- 8. Encryption at rest ----------
raw = open(config.DB_PATH, "rb").read()
R["db_plaintext_leak"] = dict(case_title_found=b"Stress case" in raw, chat_text_found=b"msg 1 from" in raw)

import json
print(json.dumps(R, indent=1))
