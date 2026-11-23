"""Create demo accounts for local testing / exam demo. Run: python seed_demo.py
Demo login password for all accounts: DemoPassw0rd!2026  (local demo only - never use in production)"""
import sys
import auth, cases, config, db

if not config.DEV_MODE:
    sys.exit("Refusing to create demo accounts with DEV_MODE=0: their password is public in this file.")

DEMO_PW = "DemoPassw0rd!2026"
USERS = ["admin@lawvault.test", "partner@lawvault.test", "associate@lawvault.test"]

db.init_db()
for e in USERS:
    print(e, auth.signup(e, DEMO_PW, True)[1])
with db.conn() as c:
    admin = c.execute("SELECT * FROM users WHERE email=?", (USERS[0],)).fetchone()
cid, msg = cases.create_case(admin, "Smith v. Acme Corp", "Breach of contract – supplier dispute")
if cid:
    cases.add_member(admin, cid, USERS[1])
    with db.conn() as c:
        p = c.execute("SELECT id FROM users WHERE email=?", (USERS[1],)).fetchone()
    cases.post_message(p["id"], cid, "I've reviewed the supply agreement - clause 9 looks like our strongest argument.")
print("case:", msg)

# ---- demo calendar ----
import datetime as dt
import cal

if cid:
    with db.conn() as c:
        users = {r["email"]: r for r in c.execute("SELECT * FROM users")}
    admin, partner, assoc = (users[e] for e in USERS)
    cases.add_member(admin, cid, USERS[2], role="viewer")  # read-only, e.g. a trainee
    monday = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())

    def at(day_offset, h, m=0):
        return dt.datetime.combine(monday + dt.timedelta(days=day_offset), dt.time(h, m)).timestamp()

    for d in range(0, 14, 7):  # this week and next
        cal.add_event(admin, "Court: Smith v. Acme hearing", at(d + 1, 9), at(d + 1, 11), notes="Courtroom 4B", case_id=cid)
        cal.add_event(admin, "Client lunch", at(d + 3, 12), at(d + 3, 13, 30))
        cal.add_event(partner, "Deposition – Acme CFO", at(d + 2, 10), at(d + 2, 13), notes="Confidential")
        cal.add_event(partner, "Mediation", at(d + 4, 14), at(d + 4, 17))
        cal.add_event(assoc, "Research block", at(d + 0, 13), at(d + 0, 16))
    cal.set_visibility(partner["id"], "busy")      # partner shares free/busy with teammates
    cal.set_visibility(assoc["id"], "details")     # associate shares titles
    cal.add_event(partner, "Prep: clause 9 memo", at(7 + 0, 15), at(7 + 0, 16), invitee_ids=[admin["id"]])
    cal.request_access(assoc["id"], admin["id"], "details")  # admin sees a pending request
    print("calendar: demo events, sharing and requests created")

    # ---- demo deadlines & tasks ----
    import time
    now = time.time()
    cases.add_task(admin["id"], cid, "deadline", "File statement of defence", now + 3 * 86400, partner["id"])
    cases.add_task(admin["id"], cid, "deadline", "Mediation brief due", now + 10 * 86400)
    cases.add_task(partner["id"], cid, "task", "Draft clause 9 memo", now + 2 * 86400, admin["id"])
    print("tasks: demo deadlines and tasks created")

# ---- demo matter for the Case analysis page ----
import seed_analysis_demo
seed_analysis_demo.main()
