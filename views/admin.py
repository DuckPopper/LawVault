import datetime as dt
import streamlit as st
import db, twofa, ui
from i18n import t


def render():
    u = st.session_state["user"]
    if u["role"] != "admin":  # server-side check, not just hiding the menu
        st.error(t("Admins only."))
        return
    ui.page_header("Admin", "Account metadata and audit events only. Case and document content is never shown here.")
    with db.conn() as c:
        users = c.execute("SELECT id,email,role,plan,failed_attempts,locked_until,created_at FROM users ORDER BY created_at DESC").fetchall()
        logs = c.execute("SELECT ts,user_id,event,detail FROM audit_log ORDER BY id DESC LIMIT 100").fetchall()
        n_cases = c.execute("SELECT COUNT(*) n FROM cases").fetchone()["n"]
    a, b = st.columns(2)
    a.metric(t("Users"), len(users))
    b.metric(t("Cases"), n_cases)
    st.subheader(t("Users"))
    ui.table([t("Email"), t("Role"), t("Plan"), t("Locked"), t("Joined")],
             [[r["email"], r["role"], r["plan"], "🔒" if r["locked_until"] > db.now() else "",
               dt.datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d")] for r in users])
    locked = [r for r in users if r["locked_until"] > db.now()]
    for r in locked:
        if st.button(t("Unlock {email}", email=r["email"])):
            with db.conn() as c:
                c.execute("UPDATE users SET locked_until=0, failed_attempts=0 WHERE id=?", (r["id"],))
            db.audit("admin_unlock", u["id"], r["id"])
            st.rerun()
    with st.expander(t("Reset a user's authenticator app (lost phone)")):
        with db.conn() as c:
            has = c.execute("SELECT u.id, u.email FROM user_totp t JOIN users u ON u.id=t.user_id "
                            "WHERE t.enabled=1").fetchall()
        if not has:
            st.caption(t("Nobody has an authenticator app turned on."))
        else:
            who = st.selectbox(t("User"), [r["id"] for r in has],
                               format_func=lambda i: next(r["email"] for r in has if r["id"] == i))
            ok = st.checkbox(t("I verified this person's identity outside the app"))
            if st.button(t("Reset authenticator"), disabled=not ok):
                twofa.admin_reset(u["id"], who)
                st.success(t("Reset. They'll get email codes at their next login."))
    st.subheader(t("Audit log (latest 100)"))
    ui.table([t("Time"), t("User"), t("Event"), t("Detail")],
             [[dt.datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d %H:%M:%S"), (r["user_id"] or "")[:8],
               r["event"], r["detail"] or ""] for r in logs], scroll=True)
