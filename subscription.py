"""Plans, limits, daily AI quota. Checkout is MOCKED (no card data is ever collected)."""
from __future__ import annotations
import datetime as dt
import db

PLANS = {
    "free": dict(name="Free", price=0, daily_ai=5, max_cases=2, max_docs=3, max_members=3, max_meeting_people=3),
    "pro": dict(name="Pro", price=19, daily_ai=200, max_cases=50, max_docs=200, max_members=10, max_meeting_people=10),
    "firm": dict(name="Firm", price=99, daily_ai=2000, max_cases=500, max_docs=2000, max_members=50,
                 max_meeting_people=50),
}


def effective_plan(user) -> str:
    if user["plan"] != "free" and user["plan_expires"] and user["plan_expires"] < db.now():
        return "free"
    return user["plan"]


def limits(user) -> dict:
    return PLANS[effective_plan(user)]


def mock_checkout(user_id: str, plan: str, days: int = 30):
    if plan not in PLANS or plan == "free":
        raise ValueError("bad plan")
    with db.conn() as c:
        c.execute("UPDATE users SET plan=?, plan_expires=? WHERE id=?", (plan, db.now() + days * 86400, user_id))
    db.audit("plan_change", user_id, plan)


def cancel(user_id: str):
    with db.conn() as c:
        c.execute("UPDATE users SET plan='free', plan_expires=NULL WHERE id=?", (user_id,))
    db.audit("plan_cancel", user_id)


def _today() -> str:
    return dt.date.today().isoformat()


def ai_used_today(user_id: str) -> int:
    with db.conn() as c:
        r = c.execute("SELECT ai_calls FROM usage WHERE user_id=? AND day=?", (user_id, _today())).fetchone()
    return r["ai_calls"] if r else 0


def consume_ai_call(user) -> bool:
    """Atomically take one AI call from today's quota. False = over quota."""
    cap = limits(user)["daily_ai"]
    with db.conn() as c:
        c.execute("INSERT OR IGNORE INTO usage(user_id,day,ai_calls) VALUES(?,?,0)", (user["id"], _today()))
        cur = c.execute("UPDATE usage SET ai_calls=ai_calls+1 WHERE user_id=? AND day=? AND ai_calls<?",
                        (user["id"], _today(), cap))
        return cur.rowcount == 1


def refund_ai_call(user_id: str):
    """Give the call back if the AI provider failed - users shouldn't pay for outages."""
    with db.conn() as c:
        c.execute("UPDATE usage SET ai_calls=ai_calls-1 WHERE user_id=? AND day=? AND ai_calls>0", (user_id, _today()))
