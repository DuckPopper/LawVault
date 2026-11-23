"""Email one-time passwords: hashed at rest, 5-min expiry, single use, attempt + resend limits."""
from __future__ import annotations
import hmac, secrets, smtplib
from email.message import EmailMessage
import config, crypto, db


def _send_email(to: str, code: str, purpose: str):
    msg = EmailMessage()
    msg["Subject"] = "Your LawVault verification code"
    msg["From"] = config.SMTP["user"]
    msg["To"] = to
    msg.set_content(f"Your {purpose} code is {code}. It expires in 5 minutes. "
                    "If you did not request it, ignore this email.")
    with smtplib.SMTP(config.SMTP["host"], config.SMTP["port"], timeout=15) as s:
        s.starttls()
        s.login(config.SMTP["user"], config.SMTP["password"])
        s.send_message(msg)


def send_plain_email(to: str, subject: str, body: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.SMTP["user"]
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP(config.SMTP["host"], config.SMTP["port"], timeout=15) as s:
        s.starttls()
        s.login(config.SMTP["user"], config.SMTP["password"])
        s.send_message(msg)


def issue(user_id: str, email: str, purpose: str):
    """Returns (ok, message, dev_code). dev_code is only set in DEV_MODE."""
    t = db.now()
    with db.conn() as c:
        last = c.execute("SELECT created_at FROM otps WHERE user_id=? AND purpose=? AND used=0 "
                         "ORDER BY created_at DESC LIMIT 1",
                         (user_id, purpose)).fetchone()
        if last and t - last["created_at"] < config.OTP_RESEND_COOLDOWN:
            return False, "Please wait a few seconds before requesting another code.", None
        n = c.execute("SELECT COUNT(*) n FROM otps WHERE user_id=? AND created_at>?", (user_id, t - 3600)).fetchone()["n"]
        if n >= config.OTP_MAX_PER_HOUR:
            return False, "Too many codes requested. Try again later.", None
        c.execute("UPDATE otps SET used=1 WHERE user_id=? AND purpose=?", (user_id, purpose))  # invalidate old
        code = f"{secrets.randbelow(10**6):06d}"
        salt = secrets.token_hex(8)
        c.execute("INSERT INTO otps(id,user_id,purpose,code_hash,salt,expires_at,created_at) VALUES(?,?,?,?,?,?,?)",
                  (db.uid(), user_id, purpose, crypto.hmac_code(code, salt), salt, t + config.OTP_TTL_SECONDS, t))
    if config.DEV_MODE:
        db.audit("otp_issued_dev", user_id, purpose)
        return True, "Code generated (dev mode).", code
    try:
        _send_email(email, code, purpose)
    except Exception:
        db.audit("otp_email_failed", user_id, purpose)
        return False, "Could not send email. Contact support.", None
    db.audit("otp_issued", user_id, purpose)
    return True, "We sent a 6-digit code to your email.", None


def verify(user_id: str, purpose: str, code: str) -> bool:
    t = db.now()
    with db.conn() as c:
        row = c.execute("SELECT * FROM otps WHERE user_id=? AND purpose=? AND used=0 ORDER BY created_at DESC LIMIT 1",
                        (user_id, purpose)).fetchone()
        if not row or row["expires_at"] < t or row["attempts"] >= config.OTP_MAX_ATTEMPTS:
            return False
        c.execute("UPDATE otps SET attempts=attempts+1 WHERE id=?", (row["id"],))
        if hmac.compare_digest(row["code_hash"], crypto.hmac_code(code.strip(), row["salt"])):
            c.execute("UPDATE otps SET used=1 WHERE id=?", (row["id"],))
            return True
        return False
