"""Fills nvidiaonly1@gmail.com with demo content (Files page, a case with chat/docs/tasks, contacts).
Run once per data dir:  LAWVAULT_DATA_DIR=data-demo DEV_MODE=1 .venv/bin/python seed_nvidia_demo.py"""
import datetime as dt
import cases, contacts, db
from pathlib import Path

EMAIL = "nvidiaonly1@gmail.com"
db.init_db()
with db.conn() as c:
    u = c.execute("SELECT * FROM users WHERE email=?", (EMAIL,)).fetchone()
if not u:
    raise SystemExit(f"{EMAIL} does not exist in this data dir")
if any(d["filename"] == "Lease_Agreement.txt" for d in cases.list_documents(u["id"])):
    raise SystemExit("already seeded")

lease = ("COMMERCIAL LEASE AGREEMENT between PT Sentosa Abadi (Landlord) and PT Maju Logistik (Tenant). Warehouse Unit 7, "
         "Jakarta Utara. Term: 1 Jan 2025 to 31 Dec 2029. Rent IDR 85,000,000 per month in advance. Late payment: 0.1% per day "
         "after a 7-day grace period. Default: 30 days' non-payment allows termination notice. Deposit IDR 255,000,000. "
         "Early termination: 6 months' notice plus 3 months' rent. Governing law: Indonesia. Disputes: mediation, then BANI arbitration.")
cid, _ = cases.create_case(u, "Demo: PT Sentosa Abadi v. PT Maju Logistik", "Rent arrears and early termination dispute over Warehouse Unit 7")
for name, text in [("Lease_Agreement.txt", lease),
                   ("Addendum_1.txt", "Addendum 1: rent reduced to IDR 78,000,000 from 1 July 2025 to 30 June 2026 against twelve months paid upfront."),
                   ("Client_Email_Notes.txt", "Client PT Maju Logistik is 45 days late on rent (Jan-Feb). Remind them of clause 4 late interest (0.1%/day) and clause 5 termination notice after 30 days. Offer a payment plan if they pay half by Friday.")]:
    cases.add_document(u, cid, name, text)
cases.add_document(u, None, "Personal_Note_Hearing_Prep.txt", "Prep list: bring original lease, payment ledger, demand letters of 3 Feb and 17 Feb.")
cases.post_message(u["id"], cid, "Kickoff: the tenant is 45 days late. Plan: demand letter this week, then mediation.")
cases.post_message(u["id"], cid, "Checking clause 4 (late interest) and clause 5 (30-day termination notice).")
now = dt.datetime.now()
def ts(days, h=10): return dt.datetime.combine((now + dt.timedelta(days=days)).date(), dt.time(h)).timestamp()
cases.add_task(u["id"], cid, "deadline", "Send demand letter", ts(2))
cases.add_task(u["id"], cid, "deadline", "Mediation session", ts(14, 9))
cases.add_task(u["id"], cid, "task", "Collect payment ledger from client")
for em, nm in [("partner@lawvault.test", "Senior partner"), ("associate@lawvault.test", "Associate")]:
    contacts.add(u["id"], em, nm)
print("seeded", EMAIL)
