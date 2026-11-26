"""Plans, limits, daily AI quota, monthly voice quota. Checkout is MOCKED (no card data is ever collected).

Fixed plans: free / pro / firm.

"Pick your own" plan (key "custom"): a flat $15 a month that already includes CUSTOM_INCLUDED. The buyer can
  * switch features off  -> the price does NOT drop (it never goes under $15), and
  * buy extra units of any quota -> every unit has its own price (ADDONS).

How the add-on prices were worked out (monthly, worst case = the buyer uses the whole allowance):
  unit cost ............ UNIT_COST_CENTS below, from these assumptions
        AI request       ~$0.002   (about 5k tokens in + 1k out on a Gemini flash-lite model, rounded up)
        Whisper minute   ~$0.006   (OpenAI whisper-1 list price)
        document         ~$0.0005  (encrypted text + backups)     case ~$0.01 (chat, tasks)
        member per case  ~$0.40    (notifications, presence, support share)
        meeting person   ~$0.05
  price ................ at least 2x the worst-case cost, never below $0.50 a unit, rounded to $0.50.
The $15 base then costs about $6.40 in the worst case (AI $3.00, three members per case $1.20, hosting $1.00, card fee
$0.74, the rest $0.46), a margin of about 57%, and about 75% for a typical user who uses a third of the AI allowance.
tests/test_pricing.py keeps these promises true.
"""
from __future__ import annotations
import datetime as dt
import json
import db

PLANS = {
    "free": dict(name="Free", price=0, daily_ai=5, max_cases=2, max_docs=3, max_members=3, max_meeting_people=3,
                 voice_minutes=10, features={"calendar_sync": False}),   # sync starts at Pro
    "pro": dict(name="Pro", price=19, daily_ai=200, max_cases=50, max_docs=200, max_members=10, max_meeting_people=10,
                voice_minutes=120),
    "firm": dict(name="Firm", price=99, daily_ai=2000, max_cases=500, max_docs=2000, max_members=50,
                 max_meeting_people=50, voice_minutes=600),
}

# ---------- the pick-your-own plan ----------
FEATURES = ("calendar_ai", "voice", "case_analysis", "doc_review", "calendar_sync")
FEATURE_LABEL = {"calendar_ai": "Calendar assistant", "voice": "Voice input", "case_analysis": "Case analysis",
                 "doc_review": "Document review",
                 "calendar_sync": "Google and Apple calendar sync"}
CUSTOM_BASE_CENTS = 1500                       # flat, non-negotiable
CUSTOM_INCLUDED = dict(daily_ai=50, max_cases=10, max_docs=50, max_members=3, max_meeting_people=3,
                       voice_minutes=30)
# key -> what one "unit" adds, its price in cents, and the most units that can be bought
ADDONS = {
    "daily_ai":           dict(label="AI requests a day",   step=10, cents=150, max_units=50),
    "max_cases":          dict(label="Cases",               step=10, cents=100, max_units=20),
    "max_docs":           dict(label="Documents",           step=50, cents=100, max_units=40),
    "max_members":        dict(label="Members per case",    step=1,  cents=200, max_units=47),
    "max_meeting_people": dict(label="People per meeting",  step=1,  cents=50,  max_units=47),
    "voice_minutes":      dict(label="Voice minutes a month", step=60, cents=100, max_units=20),
}
# What one unit costs us at full use, in cents (see the assumptions above). Used only by the margin test.
UNIT_COST_CENTS = dict(daily_ai=60, max_cases=10, max_docs=2.5, max_members=40, max_meeting_people=5,
                       voice_minutes=36)


def money(amount) -> str:
    """15 -> '15', 16.5 -> '16.50'."""
    return f"{amount:.0f}" if abs(amount - round(amount)) < 1e-9 else f"{amount:.2f}"


def default_custom() -> dict:
    return dict(units={k: 0 for k in ADDONS}, features={f: True for f in FEATURES})


def normalize_custom(units: dict | None, features: dict | None):
    """Validate a buyer's choices. Returns (config, error). Unknown keys are rejected, not ignored."""
    cfg = default_custom()
    for k, v in (units or {}).items():
        if k not in ADDONS:
            return None, "Unknown option in the plan."
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= ADDONS[k]["max_units"]:
            return None, f"Choose between 0 and {ADDONS[k]['max_units']} packs for each option."
        cfg["units"][k] = v
    for k, v in (features or {}).items():
        if k not in FEATURES or not isinstance(v, bool):
            return None, "Unknown option in the plan."
        cfg["features"][k] = v
    return cfg, None


def quote(cfg: dict) -> dict:
    """Price breakdown in cents: {'base', 'lines': [(key, units, cents)], 'total'}."""
    lines = [(k, n, n * ADDONS[k]["cents"]) for k, n in cfg["units"].items() if n]
    return dict(base=CUSTOM_BASE_CENTS, lines=lines, total=CUSTOM_BASE_CENTS + sum(c for _, _, c in lines))


def custom_plan(cfg: dict) -> dict:
    """The same shape as a PLANS entry, built from a buyer's choices."""
    plan = {k: CUSTOM_INCLUDED[k] + cfg["units"].get(k, 0) * ADDONS[k]["step"] for k in CUSTOM_INCLUDED}
    plan.update(name="Custom", price=quote(cfg)["total"] / 100, features=dict(cfg["features"]), custom=True)
    return plan


def custom_config(user) -> dict:
    """The user's saved choices, or the plain $15 bundle. Anything unreadable falls back to the default."""
    try:
        raw = json.loads(user["plan_config"] or "{}")
        cfg, err = normalize_custom(raw.get("units"), raw.get("features"))
        return cfg if cfg and not err else default_custom()
    except (ValueError, KeyError, IndexError, AttributeError, TypeError):
        return default_custom()


# ---------- reading a user's plan ----------
def effective_plan(user) -> str:
    if user["plan"] != "free" and user["plan_expires"] and user["plan_expires"] < db.now():
        return "free"
    return user["plan"]


def plan_info(user) -> dict:
    key = effective_plan(user)
    return custom_plan(custom_config(user)) if key == "custom" else PLANS[key]


def limits(user) -> dict:
    return plan_info(user)


def has_feature(user, feature: str) -> bool:
    return plan_info(user).get("features", {}).get(feature, True)


def can_customize_theme(user) -> bool:
    """The accent colour wheel is a paid perk: Pro, Firm (enterprise) and pick-your-own plans."""
    return effective_plan(user) != "free"


def accent_hue(user):
    """The hue to paint the app with: the saved one, but only while the plan still includes the customizer."""
    try:
        return user["accent_hue"] if can_customize_theme(user) else None
    except (KeyError, IndexError):
        return None


def can_pick_own(user) -> bool:
    """Pick-your-own is unlocked by buying Pro (or Firm) once. After that it can be chosen any time."""
    try:
        return user["paid_pro_at"] is not None
    except (KeyError, IndexError):
        return False


# ---------- buying ----------
def mock_checkout(user_id: str, plan: str, days: int = 30, custom: dict | None = None):
    with db.conn() as c:
        row = c.execute("SELECT paid_pro_at FROM users WHERE id=?", (user_id,)).fetchone()
    if row is None:
        raise ValueError("bad user")
    if plan == "custom":
        if row["paid_pro_at"] is None:
            raise ValueError("Pick your own is available after your first Pro month. Subscribe to Pro first.")
        cfg, err = normalize_custom((custom or {}).get("units"), (custom or {}).get("features"))
        if err:
            raise ValueError(err)
        blob = json.dumps(cfg)
    elif plan in PLANS and plan != "free":
        blob = None
    else:
        raise ValueError("bad plan")
    with db.conn() as c:
        c.execute("UPDATE users SET plan=?, plan_expires=?, plan_config=?, "
                  "paid_pro_at=CASE WHEN ? IN ('pro','firm') THEN COALESCE(paid_pro_at, ?) ELSE paid_pro_at END "
                  "WHERE id=?", (plan, db.now() + days * 86400, blob, plan, db.now(), user_id))
    db.audit("plan_change", user_id, plan if plan != "custom" else f"custom ${quote(cfg)['total'] / 100:.2f}")


def cancel(user_id: str):
    with db.conn() as c:
        c.execute("UPDATE users SET plan='free', plan_expires=NULL, plan_config=NULL WHERE id=?", (user_id,))
    db.audit("plan_cancel", user_id)


# ---------- daily AI quota ----------
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


# ---------- monthly voice quota (seconds) ----------
def _month() -> str:
    return dt.date.today().strftime("%Y-%m")


def voice_seconds_used(user_id: str) -> int:
    with db.conn() as c:
        r = c.execute("SELECT seconds FROM voice_usage WHERE user_id=? AND month=?", (user_id, _month())).fetchone()
    return r["seconds"] if r else 0


def consume_voice(user, seconds: int) -> bool:
    """Atomically reserve `seconds` of this month's voice allowance. False = it would go over."""
    cap = limits(user)["voice_minutes"] * 60
    with db.conn() as c:
        c.execute("INSERT OR IGNORE INTO voice_usage(user_id,month,seconds) VALUES(?,?,0)", (user["id"], _month()))
        cur = c.execute("UPDATE voice_usage SET seconds=seconds+? WHERE user_id=? AND month=? AND seconds+?<=?",
                        (seconds, user["id"], _month(), seconds, cap))
        return cur.rowcount == 1


def refund_voice(user_id: str, seconds: int):
    with db.conn() as c:
        c.execute("UPDATE voice_usage SET seconds=MAX(0, seconds-?) WHERE user_id=? AND month=?",
                  (seconds, user_id, _month()))
