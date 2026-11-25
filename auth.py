"""Signup, login (password + OTP), lockout, sessions, password reset."""
from __future__ import annotations
import re
from typing import Optional, Tuple
import hashlib
import config, crypto, db, i18n, notify, otp, security_checks

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
COMMON = {"password", "password1", "123456789", "1234567890", "qwertyuiop", "letmein123", "iloveyou12",
          "admin12345", "welcome123", "password123", "passw0rd123", "abc1234567"}


def norm_email(e: str) -> str:
    return (e or "").strip().lower()


def password_error(pw: str) -> Optional[str]:
    if len(pw) < 10:
        return "Password must be at least 10 characters."
    if pw.lower() in COMMON:
        return "That password is too common."
    if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
        return "Password needs at least one letter and one number."
    return None


def full_password_error(pw: str) -> Optional[str]:
    """Local rules first (instant), then the breached-password check."""
    return password_error(pw) or security_checks.breach_error(pw)


def password_strength(pw: str) -> int:
    """0-4 score for the strength meter."""
    s = sum([len(pw) >= 10, len(pw) >= 14, bool(re.search(r"[a-z]", pw) and re.search(r"[A-Z]", pw)),
             bool(re.search(r"\d", pw)) and bool(re.search(r"[^A-Za-z0-9]", pw))])
    return s


def signup(email: str, password: str, consent: bool, lang: str = "en") -> Tuple[bool, str]:
    email = norm_email(email)
    if not EMAIL_RE.match(email):
        return False, "Enter a valid email address."
    if not consent:
        return False, "You must accept the privacy policy."
    err = full_password_error(password)
    if err:
        return False, err
    role = "admin" if config.ADMIN_EMAIL and email == config.ADMIN_EMAIL else "user"
    try:
        with db.conn() as c:
            uid = db.uid()
            c.execute("INSERT INTO users(id,email,pw_hash,role,created_at,consent_at,lang) VALUES(?,?,?,?,?,?,?)",
                      (uid, email, crypto.hash_password(password), role, db.now(), db.now(),
                       lang if lang in i18n.LANGS else i18n.DEFAULT))
    except Exception:
        # Same message whether or not the email exists (no account enumeration).
        return False, "Could not create account. If you already have one, log in or reset your password."
    db.audit("signup", uid)
    return True, "Account created. Please log in."


def login_step1(email: str, password: str):
    """Check password. Returns (status, user_id, message). status: ok | locked | invalid."""
    email = norm_email(email)
    with db.conn() as c:
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if u and u["locked_until"] > db.now():
        db.audit("login_blocked_locked", u["id"])
        return "locked", None, "Too many failed attempts. Try again in a few minutes."
    # bcrypt runs outside any DB transaction so it never holds a write lock.
    ok = crypto.verify_password(password, u["pw_hash"] if u else None)
    if not ok:
        if u:
            with db.conn() as c:
                c.execute("UPDATE users SET failed_attempts=failed_attempts+1 WHERE id=?", (u["id"],))
                fails = c.execute("SELECT failed_attempts f FROM users WHERE id=?", (u["id"],)).fetchone()["f"]
                locked = fails >= config.MAX_FAILED_LOGINS
                if locked:
                    c.execute("UPDATE users SET failed_attempts=0, locked_until=? WHERE id=?",
                              (db.now() + config.LOCKOUT_SECONDS, u["id"]))
            db.audit("login_failed" + ("_lockout" if locked else ""), u["id"])
        return "invalid", None, "Invalid email or password."
    with db.conn() as c:
        c.execute("UPDATE users SET failed_attempts=0 WHERE id=?", (u["id"],))
    return "ok", u["id"], "Password accepted."


def start_login_otp(user_id: str, email: str):
    return otp.issue(user_id, norm_email(email), "login")


def create_session(user_id: str, user_agent: str = "", ip: str = "") -> str:
    token = crypto.new_token()
    t = db.now()
    with db.conn() as c:
        c.execute("INSERT INTO sessions(token_hash,user_id,created_at,last_seen,user_agent,ip) VALUES(?,?,?,?,?,?)",
                  (crypto.token_hash(token), user_id, t, t, user_agent[:300], ip[:64]))
    db.audit("login_success", user_id)
    return token


def _device_hash(user_id: str, user_agent: str) -> str:
    return hashlib.sha256(f"{user_id}|{user_agent}".encode()).hexdigest()


def register_device(user_id: str, user_agent: str) -> bool:
    """Remember this browser. True = a NEW device for an account that has logged in before."""
    h = _device_hash(user_id, user_agent)
    with db.conn() as c:
        seen_any = c.execute("SELECT 1 FROM known_devices WHERE user_id=? LIMIT 1", (user_id,)).fetchone()
        cur = c.execute("INSERT OR IGNORE INTO known_devices(user_id,device_hash,first_seen) VALUES(?,?,?)",
                        (user_id, h, db.now()))
    return bool(seen_any) and cur.rowcount == 1


def finish_login(user_id: str, user_agent: str = "", ip: str = "", device_label: str = "") -> str:
    """Called after BOTH factors pass. Creates the session and raises a new-device alert if needed."""
    token = create_session(user_id, user_agent, ip)
    if register_device(user_id, user_agent):
        msg = f"New sign-in to your account from {device_label or 'a new device'}" + (f" ({ip})" if ip else "") + \
              ". If this wasn't you, change your password and log out all devices."
        notify.notify(user_id, "security", msg, link="account")
        db.audit("new_device_login", user_id)
        if not config.DEV_MODE:
            try:
                with db.conn() as c:
                    email = c.execute("SELECT email FROM users WHERE id=?", (user_id,)).fetchone()["email"]
                otp.send_plain_email(email, "New sign-in to your LawVault account", msg)
            except Exception:
                db.audit("new_device_email_failed", user_id)
    return token


def peek_session(token: Optional[str]):
    """Like validate_session but does NOT refresh the idle timer (used by background refreshes)."""
    if not token:
        return None
    t = db.now()
    with db.conn() as c:
        s = c.execute("SELECT * FROM sessions WHERE token_hash=?", (crypto.token_hash(token),)).fetchone()
        if not s or t - s["last_seen"] > config.SESSION_IDLE_SECONDS or t - s["created_at"] > config.SESSION_MAX_SECONDS:
            return None
        return c.execute("SELECT * FROM users WHERE id=?", (s["user_id"],)).fetchone()


def list_sessions(user_id: str):
    t = db.now()
    with db.conn() as c:
        rows = c.execute("SELECT * FROM sessions WHERE user_id=? ORDER BY last_seen DESC", (user_id,)).fetchall()
    return [dict(token_hash=r["token_hash"], user_agent=r["user_agent"] or "", ip=r["ip"] or "",
                 created_at=r["created_at"], last_seen=r["last_seen"]) for r in rows
            if t - r["last_seen"] <= config.SESSION_IDLE_SECONDS and t - r["created_at"] <= config.SESSION_MAX_SECONDS]


def logout_session(user_id: str, token_hash: str) -> bool:
    """Log out ONE device. user_id check stops you from killing someone else's session."""
    with db.conn() as c:
        cur = c.execute("DELETE FROM sessions WHERE user_id=? AND token_hash=?", (user_id, token_hash))
    if cur.rowcount:
        db.audit("logout_device", user_id)
    return cur.rowcount == 1


def validate_session(token: Optional[str]):
    """Returns user row or None. Enforces idle + absolute timeouts."""
    if not token:
        return None
    h = crypto.token_hash(token)
    t = db.now()
    with db.conn() as c:
        s = c.execute("SELECT * FROM sessions WHERE token_hash=?", (h,)).fetchone()
        if not s:
            return None
        if t - s["last_seen"] > config.SESSION_IDLE_SECONDS or t - s["created_at"] > config.SESSION_MAX_SECONDS:
            c.execute("DELETE FROM sessions WHERE token_hash=?", (h,))
            return None
        c.execute("UPDATE sessions SET last_seen=? WHERE token_hash=?", (t, h))
        return c.execute("SELECT * FROM users WHERE id=?", (s["user_id"],)).fetchone()


def set_language(user_id: str, lang: str) -> bool:
    if lang not in i18n.LANGS:
        return False
    with db.conn() as c:
        c.execute("UPDATE users SET lang=? WHERE id=?", (lang, user_id))
    return True


def set_theme(user_id: str, theme: str) -> bool:
    if theme not in ("dark", "light"):
        return False
    with db.conn() as c:
        c.execute("UPDATE users SET theme=? WHERE id=?", (theme, user_id))
    return True


def update_profile(user_id: str, display_name: str, job_title: str, organization: str) -> bool:
    """Saves the profile fields (plain text, trimmed and capped)."""
    with db.conn() as c:
        c.execute("UPDATE users SET display_name=?, job_title=?, organization=? WHERE id=?",
                  (display_name.strip()[:80], job_title.strip()[:80], organization.strip()[:120], user_id))
    return True


def logout(token: Optional[str]):
    if token:
        with db.conn() as c:
            c.execute("DELETE FROM sessions WHERE token_hash=?", (crypto.token_hash(token),))


def logout_all(user_id: str):
    with db.conn() as c:
        c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    db.audit("logout_all", user_id)


def start_reset(email: str):
    """Always returns the same public message. dev_code only in DEV_MODE."""
    email = norm_email(email)
    with db.conn() as c:
        u = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    dev = None
    if u:
        _, _, dev = otp.issue(u["id"], email, "reset")
    return "If that email is registered, a reset code was sent.", dev


def finish_reset(email: str, code: str, new_password: str) -> Tuple[bool, str]:
    err = full_password_error(new_password)
    if err:
        return False, err
    with db.conn() as c:
        u = c.execute("SELECT id FROM users WHERE email=?", (norm_email(email),)).fetchone()
    if not u or not otp.verify(u["id"], "reset", code):
        return False, "Invalid or expired code."
    with db.conn() as c:
        c.execute("UPDATE users SET pw_hash=?, failed_attempts=0, locked_until=0 WHERE id=?",
                  (crypto.hash_password(new_password), u["id"]))
    logout_all(u["id"])  # kill any attacker sessions
    db.audit("password_reset", u["id"])
    return True, "Password updated. Please log in."


def change_password(user_id: str, current: str, new: str) -> Tuple[bool, str]:
    err = full_password_error(new)
    if err:
        return False, err
    with db.conn() as c:
        u = c.execute("SELECT pw_hash FROM users WHERE id=?", (user_id,)).fetchone()
    if not u or not crypto.verify_password(current, u["pw_hash"]):
        return False, "Current password is incorrect."
    with db.conn() as c:
        c.execute("UPDATE users SET pw_hash=? WHERE id=?", (crypto.hash_password(new), user_id))
    logout_all(user_id)
    db.audit("password_changed", user_id)
    return True, "Password changed. Please log in again."


def is_locked(user_id: str) -> bool:
    with db.conn() as c:
        r = c.execute("SELECT locked_until FROM users WHERE id=?", (user_id,)).fetchone()
    return bool(r and r["locked_until"] > db.now())


def second_factor_failed(user_id: str):
    """Wrong authenticator code: counts toward the same 5-strike lockout as wrong passwords."""
    with db.conn() as c:
        c.execute("UPDATE users SET failed_attempts=failed_attempts+1 WHERE id=?", (user_id,))
        fails = c.execute("SELECT failed_attempts f FROM users WHERE id=?", (user_id,)).fetchone()["f"]
        if fails >= config.MAX_FAILED_LOGINS:
            c.execute("UPDATE users SET failed_attempts=0, locked_until=? WHERE id=?",
                      (db.now() + config.LOCKOUT_SECONDS, user_id))
    db.audit("2fa_failed", user_id)
