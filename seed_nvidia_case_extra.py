"""More material for nvidiaonly1's demo case so Case analysis has facts to work with. Run once per data dir."""
import cases, db
EMAIL = "nvidiaonly1@gmail.com"
db.init_db()
with db.conn() as c:
    u = c.execute("SELECT * FROM users WHERE email=?", (EMAIL,)).fetchone()
cs = [x for x in cases.list_cases(u["id"]) if x["title"].startswith("Demo: PT Sentosa")] if u else []
if not cs:
    raise SystemExit("demo case not found")
cid = cs[0]["id"]
if any(d["filename"] == "Witness_Statement_Budi.txt" for d in cases.list_documents(u["id"], cid)):
    raise SystemExit("already added")
cases.add_document(u, cid, "Witness_Statement_Budi.txt",
    "Statement of Mr. Budi Hartono, 20 Nov 2026: the tenant stopped paying after the flood of 3 January 2026. On 14 January the tenant "
    "told Ms. Rina (landlord) by phone about water damage and asked for a rent reduction; no written reply. On 12-13 February the landlord's "
    "guard padlocked the loading bay and trucks could not leave. Photographs were taken on both days.")
cases.add_document(u, cid, "Demand_Letter_2026-11-24.txt",
    "Demand letter of 24 Nov 2026: tenant owes IDR 170,000,000 for Jan-Feb 2026 plus 0.1% per day interest (clause 4). Pay by 1 December 2026 "
    "or the landlord terminates under clause 5, files with BANI and sets off the IDR 255,000,000 deposit.")
for body in ["Fact check: tenant says it paid 12 months upfront under Addendum 1 (1 July 2025); landlord's ledger shows nothing. Need bank proofs.",
             "Their best argument is the flood (force majeure, clause 9) plus the lockout on 12-13 Feb. Our best is no written notice and clause 5.",
             "Open question: is a reduction request by phone enough notice under clause 9? Prepare to argue it is not."]:
    cases.post_message(u["id"], cid, body)
print("added")
