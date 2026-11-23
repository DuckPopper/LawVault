"""Optional authenticator-app 2FA (TOTP, RFC 6238) - Google Authenticator, Authy, 1Password...

When enabled it REPLACES the email code at login (stronger: works offline, not exposed if email is hacked).
- secret encrypted at rest
- each 30-second code can be used only once (replay protection)
- disabling needs your password AND a current code
"""
from __future__ import annotations
import hmac, io, time
import pyotp
import crypto, db

ISSUER = "LawVault"


def _row(c, user_id):
    return c.execute("SELECT * FROM user_totp WHERE user_id=?", (user_id,)).fetchone()


def is_enabled(user_id: str) -> bool:
    with db.conn() as c:
        r = _row(c, user_id)
    return bool(r and r["enabled"])


def start_setup(user_id: str, email: str):
    """Creates a fresh (not yet active) secret. Returns (secret, otpauth_uri)."""
    secret = pyotp.random_base32()
    with db.conn() as c:
        c.execute("INSERT INTO user_totp(user_id,secret_enc,enabled,last_step) VALUES(?,?,0,0) "
                  "ON CONFLICT(user_id) DO UPDATE SET secret_enc=excluded.secret_enc, enabled=0, last_step=0",
                  (user_id, crypto.encrypt(secret)))
    return secret, pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER)


def qr_png(uri: str) -> bytes:
    import qrcode
    buf = io.BytesIO()
    qrcode.make(uri).save(buf, format="PNG")
    return buf.getvalue()


def _check(c, user_id: str, code: str, require_enabled: bool) -> bool:
    r = _row(c, user_id)
    code = (code or "").strip().replace(" ", "")
    if not r or (require_enabled and not r["enabled"]) or not code.isdigit() or len(code) != 6:
        return False
    totp = pyotp.TOTP(crypto.decrypt(r["secret_enc"]))
    now_step = int(time.time() // 30)
    for step in (now_step - 1, now_step, now_step + 1):  # allow 30 s clock drift
        if step > r["last_step"] and hmac.compare_digest(totp.at(step * 30), code):
            c.execute("UPDATE user_totp SET last_step=? WHERE user_id=?", (step, user_id))
            return True
    return False


def confirm_setup(user_id: str, code: str) -> bool:
    with db.conn() as c:
        ok = _check(c, user_id, code, require_enabled=False)
        if ok:
            c.execute("UPDATE user_totp SET enabled=1 WHERE user_id=?", (user_id,))
    if ok:
        db.audit("2fa_enabled", user_id)
    return ok


def verify(user_id: str, code: str) -> bool:
    with db.conn() as c:
        return _check(c, user_id, code, require_enabled=True)


def disable(user_id: str, password: str, code: str):
    with db.conn() as c:
        u = c.execute("SELECT pw_hash FROM users WHERE id=?", (user_id,)).fetchone()
    if not u or not crypto.verify_password(password, u["pw_hash"]):
        return False, "Password is incorrect."
    if not verify(user_id, code):
        return False, "Authenticator code is incorrect."
    with db.conn() as c:
        c.execute("DELETE FROM user_totp WHERE user_id=?", (user_id,))
    db.audit("2fa_disabled", user_id)
    return True, "Authenticator app removed. You'll get email codes again."


def admin_reset(admin_id: str, user_id: str):
    """For a user who lost their phone (identity checked outside the app)."""
    with db.conn() as c:
        c.execute("DELETE FROM user_totp WHERE user_id=?", (user_id,))
    db.audit("2fa_admin_reset", admin_id, user_id)
