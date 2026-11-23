import base64
from pathlib import Path
import streamlit as st
import auth, otp, session_cookie, twofa
from views.policy import POLICY

_PENDING = ("pending_uid", "pending_email", "pending_method", "dev_code", "otp_msg")


def _strength(pw: str):
    if pw:
        s = auth.password_strength(pw)
        st.progress((s + 1) / 5, text=["Very weak", "Weak", "Fair", "Good", "Strong"][s])


def _clear_pending():
    for k in _PENDING:
        st.session_state.pop(k, None)


_LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo.svg"
_CSS = """<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"]{ display:none; }
.st-key-auth_card{ background: var(--lv-surface); border:1px solid var(--lv-border); border-radius:18px;
  padding: 1.6rem 1.7rem 1.2rem; box-shadow: 0 30px 80px rgba(0,0,0,.35); }
.lv-auth-logo{ text-align:center; margin: 3.5rem 0 .4rem; }
.lv-auth-logo img{ height:44px; }
.lv-auth-sub{ text-align:center; color: var(--lv-muted); font-size:.92rem; margin-bottom:1.6rem; }
.lv-auth-foot{ text-align:center; color: var(--lv-muted); font-size:.75rem; margin-top:1.2rem; }
</style>"""


def render():
    st.markdown(_CSS, unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        logo = base64.b64encode(_LOGO.read_bytes()).decode()
        st.markdown(f'<div class="lv-auth-logo"><img src="data:image/svg+xml;base64,{logo}" alt="LawVault"></div>'
                    '<div class="lv-auth-sub">The secure workspace for legal teams</div>', unsafe_allow_html=True)
        with st.container(key="auth_card"):
            _render_forms()
        st.markdown('<div class="lv-auth-foot">Case data encrypted at rest · Two-step sign-in</div>',
                    unsafe_allow_html=True)


def _render_forms():
    if st.session_state.get("pending_uid"):
        return _second_factor()
    t_login, t_signup, t_reset = st.tabs(["Log in", "Sign up", "Forgot password"])

    with t_login:
        with st.form("login", border=False):
            email = st.text_input("Email")
            pw = st.text_input("Password", type="password")
            go = st.form_submit_button("Continue", type="primary", use_container_width=True)
        if go:
            status, uid, msg = auth.login_step1(email, pw)
            if status != "ok":
                st.error(msg)
            elif twofa.is_enabled(uid):
                st.session_state.update(pending_uid=uid, pending_email=email, pending_method="totp",
                                        otp_msg="Open your authenticator app and enter the 6-digit code.")
                st.rerun()
            else:
                ok, m, dev = auth.start_login_otp(uid, email)
                if ok:
                    st.session_state.update(pending_uid=uid, pending_email=email, pending_method="email",
                                            dev_code=dev, otp_msg=m)
                    st.rerun()
                else:
                    st.error(m)

    with t_signup:
        email = st.text_input("Email", key="su_email")
        pw = st.text_input("Password (10+ chars, letter + number)", type="password", key="su_pw")
        _strength(pw)
        with st.expander("Privacy policy"):
            st.markdown(POLICY)
        consent = st.checkbox("I have read and accept the privacy policy")
        if st.button("Create account", type="primary", use_container_width=True):
            with st.spinner("Checking password against known breaches…"):
                ok, msg = auth.signup(email, pw, consent)
            (st.success if ok else st.error)(msg)

    with t_reset:
        remail = st.text_input("Account email", key="rs_email")
        if st.button("Send reset code"):
            msg, dev = auth.start_reset(remail)
            st.info(msg)
            if dev:
                st.warning(f"DEV MODE – your code: **{dev}**")
        code = st.text_input("6-digit code", key="rs_code")
        newpw = st.text_input("New password", type="password", key="rs_new")
        if st.button("Reset password"):
            ok, msg = auth.finish_reset(remail, code, newpw)
            (st.success if ok else st.error)(msg)


def _second_factor():
    method = st.session_state.get("pending_method", "email")
    uid = st.session_state["pending_uid"]
    st.subheader("Two-step verification")
    st.info(st.session_state.get("otp_msg", "Enter your code."))
    if method == "email" and st.session_state.get("dev_code"):
        st.warning(f"DEV MODE – your code: **{st.session_state['dev_code']}** (real email is used when DEV_MODE=0)")
    with st.form("otp", border=False):
        label = "Authenticator code" if method == "totp" else "6-digit code from your email"
        code = st.text_input(label, max_chars=6)
        ok_btn = st.form_submit_button("Verify and log in", type="primary", use_container_width=True)
    if ok_btn:
        if auth.is_locked(uid):
            st.error("Too many failed attempts. Try again in a few minutes.")
            return
        if method == "totp":
            passed = twofa.verify(uid, code)
            if not passed:
                auth.second_factor_failed(uid)
        else:
            passed = otp.verify(uid, "login", code)
        if passed:
            ua, ip = session_cookie.client_info()
            st.session_state["token"] = auth.finish_login(uid, ua, ip, session_cookie.describe_device(ua))
            st.session_state["set_cookie"] = True
            _clear_pending()
            st.rerun()
        else:
            st.error("Invalid or expired code.")
    c1, c2 = st.columns(2)
    if method == "email" and c1.button("Resend code"):
        ok, m, dev = auth.start_login_otp(uid, st.session_state["pending_email"])
        st.session_state["dev_code"] = dev
        st.session_state["otp_msg"] = m
        st.rerun()
    if method == "totp":
        c1.caption("Lost your phone? Ask an administrator to reset your authenticator.")
    if c2.button("Cancel"):
        _clear_pending()
        st.rerun()
