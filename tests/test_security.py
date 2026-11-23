import time
import auth, cases, config, crypto, db, otp, privacy, subscription, ai
from conftest import make_user

PW = "Str0ngPassw0rd!"


# ---------- passwords & signup ----------
def test_weak_passwords_rejected():
    for bad in ["short1", "alllettersonly", "1234567890", "password123"]:
        ok, _ = auth.signup("a@x.com", bad, True)
        assert not ok

def test_consent_required():
    assert not auth.signup("a@x.com", PW, False)[0]

def test_password_stored_hashed():
    u = make_user("a@x.com")
    assert u["pw_hash"].startswith("$2") and PW not in u["pw_hash"]

def test_duplicate_signup_generic_message():
    make_user("a@x.com")
    ok, msg = auth.signup("a@x.com", PW, True)
    assert not ok and "already" in msg.lower() and "exists" not in msg.lower()


# ---------- login, lockout, enumeration ----------
def test_wrong_password_and_unknown_user_same_message():
    make_user("a@x.com")
    s1 = auth.login_step1("a@x.com", "WrongPass123")
    s2 = auth.login_step1("ghost@x.com", "WrongPass123")
    assert s1[0] == s2[0] == "invalid" and s1[2] == s2[2]

def test_lockout_after_5_failures():
    make_user("a@x.com")
    for _ in range(config.MAX_FAILED_LOGINS):
        auth.login_step1("a@x.com", "WrongPass123")
    status, _, _ = auth.login_step1("a@x.com", PW)  # even correct pw is blocked now
    assert status == "locked"

def test_success_resets_failed_counter():
    make_user("a@x.com")
    auth.login_step1("a@x.com", "bad")
    assert auth.login_step1("a@x.com", PW)[0] == "ok"
    with db.conn() as c:
        assert c.execute("SELECT failed_attempts f FROM users").fetchone()["f"] == 0


# ---------- OTP ----------
def test_otp_happy_path_single_use():
    u = make_user("a@x.com")
    ok, _, code = otp.issue(u["id"], "a@x.com", "login")
    assert ok and len(code) == 6
    assert otp.verify(u["id"], "login", code)
    assert not otp.verify(u["id"], "login", code)  # replay blocked

def test_otp_stored_hashed():
    u = make_user("a@x.com")
    _, _, code = otp.issue(u["id"], "a@x.com", "login")
    with db.conn() as c:
        row = c.execute("SELECT * FROM otps").fetchone()
    assert code not in row["code_hash"] and code not in str(dict(row).values())

def test_otp_expires():
    u = make_user("a@x.com")
    _, _, code = otp.issue(u["id"], "a@x.com", "login")
    with db.conn() as c:
        c.execute("UPDATE otps SET expires_at=?", (time.time() - 1,))
    assert not otp.verify(u["id"], "login", code)

def test_otp_attempt_limit():
    u = make_user("a@x.com")
    _, _, code = otp.issue(u["id"], "a@x.com", "login")
    for _ in range(config.OTP_MAX_ATTEMPTS):
        otp.verify(u["id"], "login", "000000" if code != "000000" else "111111")
    assert not otp.verify(u["id"], "login", code)  # correct code now rejected

def test_otp_resend_cooldown():
    u = make_user("a@x.com")
    assert otp.issue(u["id"], "a@x.com", "login")[0]
    assert not otp.issue(u["id"], "a@x.com", "login")[0]

def test_new_otp_invalidates_old():
    u = make_user("a@x.com")
    _, _, old = otp.issue(u["id"], "a@x.com", "login")
    with db.conn() as c:
        c.execute("UPDATE otps SET created_at=created_at-100")
    _, _, new = otp.issue(u["id"], "a@x.com", "login")
    assert not otp.verify(u["id"], "login", old) or old == new

def test_otp_purpose_bound():
    u = make_user("a@x.com")
    _, _, code = otp.issue(u["id"], "a@x.com", "reset")
    assert not otp.verify(u["id"], "login", code)


# ---------- sessions ----------
def test_session_valid_then_idle_timeout():
    u = make_user("a@x.com")
    t = auth.create_session(u["id"])
    assert auth.validate_session(t)["id"] == u["id"]
    with db.conn() as c:
        c.execute("UPDATE sessions SET last_seen=?", (time.time() - config.SESSION_IDLE_SECONDS - 5,))
    assert auth.validate_session(t) is None

def test_session_token_stored_hashed_and_garbage_rejected():
    u = make_user("a@x.com")
    t = auth.create_session(u["id"])
    with db.conn() as c:
        assert c.execute("SELECT token_hash h FROM sessions").fetchone()["h"] != t
    assert auth.validate_session("garbage") is None and auth.validate_session(None) is None

def test_logout_all_kills_sessions():
    u = make_user("a@x.com")
    t1, t2 = auth.create_session(u["id"]), auth.create_session(u["id"])
    auth.logout_all(u["id"])
    assert auth.validate_session(t1) is None and auth.validate_session(t2) is None

def test_password_reset_flow_and_kills_sessions():
    u = make_user("a@x.com")
    t = auth.create_session(u["id"])
    _, dev = auth.start_reset("a@x.com")
    ok, _ = auth.finish_reset("a@x.com", dev, "BrandNewPass99")
    assert ok and auth.validate_session(t) is None
    assert auth.login_step1("a@x.com", "BrandNewPass99")[0] == "ok"

def test_reset_unknown_email_same_message():
    m1, d1 = auth.start_reset("ghost@x.com")
    make_user("a@x.com")
    m2, _ = auth.start_reset("a@x.com")
    assert m1 == m2 and d1 is None


# ---------- MULTI-USER ISOLATION (core requirement) ----------
def test_user_cannot_read_other_users_case_or_chat():
    a, b = make_user("a@x.com"), make_user("b@x.com")
    cid, _ = cases.create_case(a, "Secret merger", "very private")
    cases.post_message(a["id"], cid, "confidential strategy")
    assert cases.get_case(b["id"], cid) is None
    assert cases.get_messages(b["id"], cid) == []
    assert cases.list_cases(b["id"]) == []
    assert cases.members(b["id"], cid) == []

def test_non_member_cannot_post_or_upload():
    a, b = make_user("a@x.com"), make_user("b@x.com")
    cid, _ = cases.create_case(a, "Case")
    assert not cases.post_message(b["id"], cid, "intrusion")
    did, _ = cases.add_document(b, cid, "x.txt", "hi")
    assert did is None

def test_document_idor_blocked():
    a, b = make_user("a@x.com"), make_user("b@x.com")
    did, _ = cases.add_document(a, None, "private.txt", "my secrets")
    assert cases.get_document(b["id"], did) is None
    assert not cases.save_analysis(b["id"], did, "tamper")
    cases.delete_document(b["id"], did)
    assert cases.get_document(a["id"], did) is not None

def test_group_chat_between_members():
    a, b = make_user("a@x.com"), make_user("b@x.com")
    cid, _ = cases.create_case(a, "Joint case")
    cases.add_member(a, cid, "b@x.com")
    cases.post_message(a["id"], cid, "hello counsel")
    cases.post_message(b["id"], cid, "hi, reviewing now")
    assert [m["body"] for m in cases.get_messages(b["id"], cid)] == ["hello counsel", "hi, reviewing now"]
    assert cases.get_document(b["id"], cases.add_document(a, cid, "f.txt", "shared")[0])  # shared doc visible

def test_removed_member_loses_access():
    a, b = make_user("a@x.com"), make_user("b@x.com")
    cid, _ = cases.create_case(a, "Case")
    cases.add_member(a, cid, "b@x.com")
    assert cases.remove_member(a["id"], cid, b["id"])
    assert cases.get_messages(b["id"], cid) == [] and cases.get_case(b["id"], cid) is None

def test_only_owner_can_add_remove_delete():
    a, b, c3 = make_user("a@x.com"), make_user("b@x.com"), make_user("c@x.com")
    cid, _ = cases.create_case(a, "Case")
    cases.add_member(a, cid, "b@x.com")
    assert not cases.add_member(b, cid, "c@x.com")[0]
    assert not cases.remove_member(b["id"], cid, a["id"])
    assert not cases.delete_case(b["id"], cid)
    assert cases.delete_case(a["id"], cid)

def test_add_member_unknown_email_same_reply():
    a = make_user("a@x.com"); make_user("b@x.com")
    cid, _ = cases.create_case(a, "Case")
    assert cases.add_member(a, cid, "ghost@x.com") == cases.add_member(a, cid, "b@x.com")

def test_sql_injection_attempts_are_inert():
    a = make_user("a@x.com")
    for evil in ["' OR '1'='1", "x'; DROP TABLE users;--"]:
        assert auth.login_step1(evil, evil)[0] == "invalid"
        cases.create_case(a, evil)
    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"] == 1


# ---------- encryption at rest ----------
def test_case_content_encrypted_in_db():
    a = make_user("a@x.com")
    cid, _ = cases.create_case(a, "TopSecretTitle", "TopSecretDesc")
    cases.post_message(a["id"], cid, "TopSecretMessage")
    did, _ = cases.add_document(a, cid, "TopSecretFile.pdf", "TopSecretBody")
    with db.conn() as c:
        blob = " ".join(str(tuple(r)) for t in ("cases", "messages", "documents")
                        for r in c.execute(f"SELECT * FROM {t}").fetchall())
    assert "TopSecret" not in blob
    raw = config.DB_PATH.read_bytes()
    assert b"TopSecret" not in raw
    assert cases.get_document(a["id"], did)["text"] == "TopSecretBody"  # but decrypts for the owner

def test_tampered_ciphertext_not_crashing():
    assert crypto.decrypt("not-a-valid-token") == "[unreadable]"


# ---------- subscription / quota ----------
def test_free_ai_quota_enforced_and_pro_raises_it():
    a = make_user("a@x.com")
    for _ in range(subscription.PLANS["free"]["daily_ai"]):
        assert subscription.consume_ai_call(a)
    assert not subscription.consume_ai_call(a)
    subscription.mock_checkout(a["id"], "pro")
    with db.conn() as c:
        a = c.execute("SELECT * FROM users WHERE id=?", (a["id"],)).fetchone()
    assert subscription.effective_plan(a) == "pro" and subscription.consume_ai_call(a)

def test_expired_plan_falls_back_to_free():
    a = make_user("a@x.com")
    subscription.mock_checkout(a["id"], "pro")
    with db.conn() as c:
        c.execute("UPDATE users SET plan_expires=?", (time.time() - 10,))
        a = c.execute("SELECT * FROM users").fetchone()
    assert subscription.effective_plan(a) == "free"

def test_free_case_limit():
    a = make_user("a@x.com")
    for i in range(subscription.PLANS["free"]["max_cases"]):
        assert cases.create_case(a, f"c{i}")[0]
    assert cases.create_case(a, "one too many")[0] is None

def test_bad_plan_rejected():
    a = make_user("a@x.com")
    for bad in ("admin", "free", "../x"):
        try:
            subscription.mock_checkout(a["id"], bad); assert False
        except ValueError:
            pass


# ---------- privacy ----------
def test_pii_redaction():
    t = privacy.redact("Mail john@firm.com or call 555-123-4567, SSN 123-45-6789, card 4111 1111 1111 1111")
    for leak in ("john@firm.com", "555-123-4567", "123-45-6789", "4111 1111 1111 1111"):
        assert leak not in t

def test_ai_failure_is_graceful_and_refunds_quota():
    a = make_user("a@x.com")
    ans, err = ai.ask(a, "What is a tort?", [])
    assert ans is None and "not configured" in err
    assert subscription.ai_used_today(a["id"]) == 0

def test_export_contains_own_data_only():
    a, b = make_user("a@x.com"), make_user("b@x.com")
    cases.add_document(a, None, "a.txt", "x"); cases.add_document(b, None, "b.txt", "y")
    ex = privacy.export_user_data(a["id"])
    assert [d["filename"] for d in ex["my_documents"]] == ["a.txt"]

def test_delete_account_erases_and_hands_over_shared_case():
    a, b = make_user("a@x.com"), make_user("b@x.com")
    shared, _ = cases.create_case(a, "Shared"); solo, _ = cases.create_case(a, "Solo")
    cases.add_member(a, shared, "b@x.com")
    cases.post_message(a["id"], shared, "from a")
    privacy.delete_account(a["id"])
    with db.conn() as c:
        assert c.execute("SELECT COUNT(*) n FROM users WHERE id=?", (a["id"],)).fetchone()["n"] == 0
        assert c.execute("SELECT COUNT(*) n FROM cases WHERE id=?", (solo,)).fetchone()["n"] == 0
        assert c.execute("SELECT owner_id o FROM cases WHERE id=?", (shared,)).fetchone()["o"] == b["id"]
        assert c.execute("SELECT COUNT(*) n FROM messages WHERE user_id=?", (a["id"],)).fetchone()["n"] == 0

def test_audit_log_never_contains_secrets():
    u = make_user("a@x.com")
    _, _, code = otp.issue(u["id"], "a@x.com", "login")
    auth.login_step1("a@x.com", "NeverLogThis123")
    with db.conn() as c:
        blob = str([tuple(r) for r in c.execute("SELECT * FROM audit_log").fetchall()])
    assert code not in blob and "NeverLogThis123" not in blob

def test_upload_validation():
    import docutil
    assert docutil.extract_text("evil.pdf", b"MZ not a pdf")[1]
    assert docutil.extract_text("a.exe", b"x")[1]
    assert docutil.extract_text("big.txt", b"a" * (config.MAX_UPLOAD_BYTES + 1))[1]
    assert docutil.extract_text("ok.txt", b"hello")[0] == "hello"
