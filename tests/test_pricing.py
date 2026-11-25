"""The pick-your-own plan: $15 flat, features can be switched off for free, extra units each have a price."""
import pytest
import db, subscription as sub
from conftest import make_user


def fresh(uid):
    with db.conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def buy(u, units=None, features=None):
    if fresh(u["id"])["paid_pro_at"] is None:
        sub.mock_checkout(u["id"], "pro")                  # Pick-your-own opens after a first Pro month
    sub.mock_checkout(u["id"], "custom", custom=dict(units=units or {}, features=features or {}))
    return fresh(u["id"])


def test_base_is_fifteen_dollars_flat_with_the_included_amounts():
    u = buy(make_user("a@x.com"))
    info = sub.plan_info(u)
    assert info["price"] == 15 and info["name"] == "Custom"
    for k, v in sub.CUSTOM_INCLUDED.items():
        assert info[k] == v
    assert sub.limits(u)["daily_ai"] == 50 and all(sub.has_feature(u, f) for f in sub.FEATURES)


def test_each_extra_unit_has_its_own_price():
    u = buy(make_user("a@x.com"), dict(daily_ai=2, max_docs=1, max_members=3, voice_minutes=1))
    info = sub.plan_info(u)
    assert info["daily_ai"] == 70 and info["max_docs"] == 100 and info["max_members"] == 6
    assert info["voice_minutes"] == 90
    # 15 + 2*1.50 + 1*1.00 + 3*2.00 + 1*1.00
    assert info["price"] == pytest.approx(26.0)
    assert sub.quote(sub.custom_config(u))["total"] == 2600


def test_switching_features_off_never_lowers_the_price():
    u = buy(make_user("a@x.com"), features={f: False for f in sub.FEATURES})
    assert sub.plan_info(u)["price"] == 15
    assert not any(sub.has_feature(u, f) for f in sub.FEATURES)
    u = buy(u, dict(daily_ai=3), {"voice": False})
    assert sub.plan_info(u)["price"] == 19.5 and not sub.has_feature(u, "voice") and sub.has_feature(u, "calendar_ai")


def test_price_can_never_go_below_the_base_or_beyond_the_caps():
    for bad in (dict(daily_ai=-1), dict(daily_ai=10 ** 6), dict(daily_ai=True), dict(daily_ai="3"),
                dict(daily_ai=1.5), dict(nonsense=1)):
        cfg, err = sub.normalize_custom(bad, None)
        assert cfg is None and err, bad
    assert sub.normalize_custom(None, {"voice": "no"})[1] and sub.normalize_custom(None, {"x": True})[1]
    u = make_user("a@x.com")
    sub.mock_checkout(u["id"], "pro")
    with pytest.raises(ValueError):
        sub.mock_checkout(u["id"], "custom", custom=dict(units=dict(daily_ai=-5)))
    with pytest.raises(ValueError):
        sub.mock_checkout(u["id"], "enterprise")
    assert fresh(u["id"])["plan"] == "pro"


def test_a_corrupt_saved_config_falls_back_to_the_plain_bundle():
    u = buy(make_user("a@x.com"), dict(daily_ai=5))
    for junk in ("{not json", '{"units": {"daily_ai": -9}}', "[]", '{"units": 3}'):
        with db.conn() as c:
            c.execute("UPDATE users SET plan_config=? WHERE id=?", (junk, u["id"]))
        assert sub.plan_info(fresh(u["id"]))["price"] == 15


def test_pick_your_own_needs_a_first_pro_month():
    u = make_user("a@x.com")
    assert not sub.can_pick_own(u)
    with pytest.raises(ValueError, match="Pro"):
        sub.mock_checkout(u["id"], "custom", custom=dict(units={}, features={}))
    assert fresh(u["id"])["plan"] == "free"
    sub.mock_checkout(u["id"], "pro")
    assert sub.can_pick_own(fresh(u["id"]))
    sub.mock_checkout(u["id"], "custom", custom=dict(units={}, features={}))
    sub.cancel(u["id"])                                       # the unlock is not lost when a plan ends
    assert sub.can_pick_own(fresh(u["id"]))
    sub.mock_checkout(u["id"], "custom", custom=dict(units={}, features={}))
    assert fresh(u["id"])["plan"] == "custom"


def test_firm_also_unlocks_pick_your_own_and_old_pro_users_are_backfilled():
    u = make_user("a@x.com")
    sub.mock_checkout(u["id"], "firm")
    assert sub.can_pick_own(fresh(u["id"]))
    v = make_user("b@x.com")
    with db.conn() as c:
        c.execute("UPDATE users SET plan='pro', paid_pro_at=NULL WHERE id=?", (v["id"],))
    db.init_db()                                              # what happens when the app starts
    assert sub.can_pick_own(fresh(v["id"]))


def test_calendar_sync_starts_at_pro():
    u = make_user("a@x.com")
    assert not sub.has_feature(u, "calendar_sync")
    sub.mock_checkout(u["id"], "pro")
    assert sub.has_feature(fresh(u["id"]), "calendar_sync")
    sub.mock_checkout(u["id"], "custom", custom=dict(units={}, features={"calendar_sync": False}))
    assert not sub.has_feature(fresh(u["id"]), "calendar_sync") and sub.plan_info(fresh(u["id"]))["price"] == 15


def test_custom_limits_are_enforced_by_the_existing_checks():
    import cases
    u = buy(make_user("a@x.com"), dict(max_cases=1))
    for i in range(20):
        cid, err = cases.create_case(fresh(u["id"]), f"Case {i}")
        assert cid, err
    assert cases.create_case(fresh(u["id"]), "One too many")[0] is None


def test_expiry_and_cancel_return_to_free():
    u = buy(make_user("a@x.com"), dict(daily_ai=1))
    with db.conn() as c:
        c.execute("UPDATE users SET plan_expires=? WHERE id=?", (db.now() - 5, u["id"]))
    assert sub.effective_plan(fresh(u["id"])) == "free" and sub.limits(fresh(u["id"]))["daily_ai"] == 5
    u = buy(u)
    sub.cancel(u["id"])
    assert fresh(u["id"])["plan"] == "free" and fresh(u["id"])["plan_config"] is None


def test_switching_from_custom_to_a_fixed_plan_forgets_the_custom_choices():
    u = buy(make_user("a@x.com"), dict(daily_ai=5), {"voice": False})
    sub.mock_checkout(u["id"], "pro")
    u = fresh(u["id"])
    assert sub.plan_info(u)["name"] == "Pro" and sub.has_feature(u, "voice")


def test_voice_allowance_is_metered_in_seconds_and_refundable():
    u = make_user("a@x.com")                      # free: 10 minutes = 600 s
    assert sub.consume_voice(u, 590)
    assert not sub.consume_voice(u, 11) and sub.voice_seconds_used(u["id"]) == 590
    assert sub.consume_voice(u, 10)
    sub.refund_voice(u["id"], 600)
    assert sub.voice_seconds_used(u["id"]) == 0
    sub.refund_voice(u["id"], 99)                 # never goes negative
    assert sub.voice_seconds_used(u["id"]) == 0


def test_voice_race_cannot_overspend():
    import concurrent.futures as cf
    u = make_user("a@x.com")
    with cf.ThreadPoolExecutor(8) as ex:
        got = sum(ex.map(lambda _: sub.consume_voice(u, 100), range(20)))
    assert got == 6 and sub.voice_seconds_used(u["id"]) == 600


# ---------- the numbers behind the prices ----------
def test_every_addon_is_priced_at_least_double_its_cost_and_at_least_fifty_cents():
    for k, a in sub.ADDONS.items():
        assert a["cents"] >= 2 * sub.UNIT_COST_CENTS[k], k     # UNIT_COST_CENTS is per pack
        assert a["cents"] >= 50 and a["cents"] % 50 == 0, k


def test_the_fifteen_dollar_base_keeps_a_healthy_margin():
    worst = sum(sub.UNIT_COST_CENTS[k] * sub.CUSTOM_INCLUDED[k] / sub.ADDONS[k]["step"] for k in sub.CUSTOM_INCLUDED)
    worst += 100 + 0.029 * 1500 + 30                              # hosting + card fee
    assert worst / 1500 <= 0.45                                   # at least 55% margin even if all is used
    assert sub.CUSTOM_BASE_CENTS == 1500


def test_the_biggest_possible_plan_is_still_profitable():
    cfg = sub.default_custom()
    cfg["units"] = {k: a["max_units"] for k, a in sub.ADDONS.items()}
    cost = sum(sub.UNIT_COST_CENTS[k] * (sub.CUSTOM_INCLUDED[k] / sub.ADDONS[k]["step"] + n)
               for k, n in cfg["units"].items()) + 100 + 30
    price = sub.quote(cfg)["total"]
    assert cost / (price * (1 - 0.029)) < 0.5
