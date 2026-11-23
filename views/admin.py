import datetime as dt
import streamlit as st
import db, twofa, ui


def render():
    u = st.session_state["user"]
    if u["role"] != "admin":  # server-side check, not just hiding the menu
        st.error("Admins only.")
        return
    ui.page_header("Admin", "Account metadata and audit events only. Case and document content is never shown here.")
    with db.conn() as c:
        users = c.execute("SELECT id,email,role,plan,failed_attempts,locked_until,created_at FROM users ORDER BY created_at DESC").fetchall()
        logs = c.execute("SELECT ts,user_id,event,detail FROM audit_log ORDER BY id DESC LIMIT 100").fetchall()
        n_cases = c.execute("SELECT COUNT(*) n FROM cases").fetchone()["n"]
    a, b = st.columns(2)
    a.metric("Users", len(users))
    b.metric("Cases", n_cases)
    st.subheader("Users")
    st.dataframe([dict(email=r["email"], role=r["role"], plan=r["plan"],
                       locked=r["locked_until"] > db.now(),
                       joined=dt.datetime.fromtimestamp(r["created_at"]).strftime("%Y-%m-%d")) for r in users],
                 use_container_width=True)
    locked = [r for r in users if r["locked_until"] > db.now()]
    for r in locked:
        if st.button(f"Unlock {r['email']}"):
            with db.conn() as c:
                c.execute("UPDATE users SET locked_until=0, failed_attempts=0 WHERE id=?", (r["id"],))
            db.audit("admin_unlock", u["id"], r["id"])
            st.rerun()
    with st.expander("Reset a user's authenticator app (lost phone)"):
        with db.conn() as c:
            has = c.execute("SELECT u.id, u.email FROM user_totp t JOIN users u ON u.id=t.user_id "
                            "WHERE t.enabled=1").fetchall()
        if not has:
            st.caption("Nobody has an authenticator app turned on.")
        else:
            who = st.selectbox("User", [r["id"] for r in has],
                               format_func=lambda i: next(r["email"] for r in has if r["id"] == i))
            ok = st.checkbox("I verified this person's identity outside the app")
            if st.button("Reset authenticator", disabled=not ok):
                twofa.admin_reset(u["id"], who)
                st.success("Reset. They'll get email codes at their next login.")
    st.subheader("Audit log (latest 100)")
    st.dataframe([dict(time=dt.datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d %H:%M:%S"),
                       user=(r["user_id"] or "")[:8], event=r["event"], detail=r["detail"]) for r in logs],
                 use_container_width=True)
