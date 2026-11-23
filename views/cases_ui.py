import datetime as dt
import streamlit as st
import ai, auth, cases, config, docutil, presence, ui

ROLE_LABEL = {"owner": "Owner", "editor": "Editor", "viewer": "Viewer (read-only)"}


def _who_is_here(user_id: str, case_id: str):
    mem = cases.members(user_id, case_id)
    st_ = presence.status_of([m["id"] for m in mem])
    parts = [f"{presence.DOT[st_[m['id']]]} {'You' if m['id'] == user_id else m['email'].split('@')[0]}" for m in mem]
    st.caption("  ·  ".join(parts))


@st.fragment(run_every=3)
def chat_feed(user_id: str, case_id: str):
    """Auto-refreshing group chat. Re-checks the session and membership on every refresh."""
    if not auth.peek_session(st.session_state.get("token")):
        st.warning("Your session ended. Refresh the page to log in again.")
        return
    _who_is_here(user_id, case_id)
    msgs = cases.get_messages(user_id, case_id)
    box = st.container(height=420, border=True)
    with box:
        if not msgs:
            st.caption("No messages yet. Start the discussion below. Tip: type “@ai” and a question to ask the AI.")
        for m in msgs:
            when = dt.datetime.fromtimestamp(m["ts"]).strftime("%b %d %H:%M")
            if m["kind"] == "ai":
                with st.chat_message("assistant", avatar=":material/balance:"):
                    asker = "you" if m["user_id"] == user_id else m["email"].split("@")[0]
                    st.caption(f"LawVault AI · answering {asker} · {when}")
                    st.markdown(m["body"])
                    st.caption(ai.DISCLAIMER)
                continue
            mine = m["user_id"] == user_id
            with st.chat_message("user" if mine else "human"):
                st.caption(f"{'You' if mine else m['email']} · {when}")
                st.text(m["body"])


def _chat_tab(u, case):
    cid = case["id"]
    c1, c2 = st.columns([1, 3])
    if c1.button("Brief me on this case", icon=":material/auto_awesome:", help="AI briefing from the chat, documents and deadlines"):
        with st.spinner("Reading the case…"):
            text, err = ai.summarize_case(u, cid)
        st.session_state[f"summary_{cid}"] = (text, err)
    res = st.session_state.get(f"summary_{cid}")
    if res:
        text, err = res
        if err:
            st.error(err)
        else:
            with st.expander("Case briefing", expanded=True):
                st.markdown(text)
                st.caption(ai.DISCLAIMER)
                a, b = st.columns(2)
                if case["role"] != "viewer" and a.button("Post briefing to team chat"):
                    cases.post_message(u["id"], cid, "**Case briefing**\n\n" + text, kind="ai")
                    st.session_state.pop(f"summary_{cid}")
                    st.rerun()
                if b.button("Dismiss"):
                    st.session_state.pop(f"summary_{cid}")
                    st.rerun()

    chat_feed(u["id"], cid)
    if case["role"] == "viewer":
        st.caption("👁️ You have view-only access to this case.")
        return
    flash = st.session_state.pop("chat_flash", None)
    if flash:
        st.error(flash)
    text = st.chat_input("Message your team… (start with @ai to ask the AI, @email to mention someone)")
    if text:
        cases.post_message(u["id"], cid, text)
        if ai.AI_TRIGGER.match(text):
            with st.spinner("LawVault AI is thinking…"):
                ok, err = ai.answer_in_chat(u, cid, text)
            if not ok:
                st.session_state["chat_flash"] = err
        st.rerun()


def _docs_tab(u, case):
    cid = case["id"]
    editor = case["role"] != "viewer"
    if editor:
        up = st.file_uploader(f"Upload PDF or TXT to this case (up to {config.MAX_UPLOAD_MB} MB)",
                              type=["pdf", "txt"], key=f"up_{cid}")
        if up and st.button("Save to case"):
            text, err = docutil.extract_text(up.name, up.getvalue())
            if err:
                st.error(err)
            else:
                did, msg = cases.add_document(u, cid, up.name, text)
                (st.success if did else st.error)(msg)
    docs = cases.list_documents(u["id"], cid)
    if not docs:
        st.caption("No documents yet.")
    for d in docs:
        with st.expander(d["filename"], icon=":material/description:"):
            full = cases.get_document(u["id"], d["id"])
            if full and full["analysis"]:
                st.markdown(full["analysis"])
                st.caption(ai.DISCLAIMER)
            if not editor:
                continue
            a, b = st.columns(2)
            if a.button("Analyze with AI", key=f"an_{d['id']}"):
                with st.spinner("Analyzing…"):
                    res, err = ai.analyze_document(u, full["text"])
                if err:
                    st.error(err)
                else:
                    cases.save_analysis(u["id"], d["id"], res)
                    st.rerun()
            if b.button("📅 Find deadlines", key=f"dl_{d['id']}", help="AI pulls out dates you must act on"):
                with st.spinner("Looking for deadlines…"):
                    found, err = ai.extract_deadlines(u, full["text"])
                st.session_state[f"dl_{d['id']}"] = (found, err)
            res = st.session_state.get(f"dl_{d['id']}")
            if res:
                found, err = res
                if err:
                    st.error(err)
                elif not found:
                    st.info("No dated deadlines found.")
                else:
                    picks = [i for i, f in enumerate(found)
                             if st.checkbox(f"{f['date']:%a %b %d, %Y} — {f['title']}", value=True,
                                            key=f"dlc_{d['id']}_{i}")]
                    if st.button("Add selected to case deadlines", key=f"dla_{d['id']}", type="primary"):
                        for i in picks:
                            due = dt.datetime.combine(found[i]["date"], dt.time(9, 0)).timestamp()
                            cases.add_task(u["id"], cid, "deadline", found[i]["title"], due)
                        st.session_state.pop(f"dl_{d['id']}")
                        st.success(f"Added {len(picks)} deadline(s). They also appear on everyone's calendar.")


def _tasks_tab(u, case):
    cid = case["id"]
    members = cases.members(u["id"], cid)
    editor = case["role"] != "viewer"
    if editor:
        with st.expander("➕ Add a deadline or task"):
            with st.form(f"task_{cid}", clear_on_submit=True):
                kind = st.radio("Type", cases.TASK_KINDS, horizontal=True,
                                format_func={"deadline": "⚖️ Deadline (court/filing date)", "task": "✅ Task"}.get)
                title = st.text_input("What", placeholder="File statement of defence")
                c1, c2, c3 = st.columns(3)
                has_due = c1.checkbox("Has a due date", value=True)
                day = c2.date_input("Due date", value=dt.date.today() + dt.timedelta(days=7))
                t = c3.time_input("Time", value=dt.time(17, 0), step=900)
                who = st.selectbox("Assign to", [None] + [m["id"] for m in members],
                                   format_func=lambda i: "Nobody" if i is None else next(
                                       m["email"] for m in members if m["id"] == i))
                if st.form_submit_button("Add", type="primary"):
                    due = dt.datetime.combine(day, t).timestamp() if has_due or kind == "deadline" else None
                    tid, msg = cases.add_task(u["id"], cid, kind, title, due, who)
                    (st.success if tid else st.error)(msg)
    tasks = cases.list_tasks(u["id"], cid)
    if not tasks:
        st.caption("No deadlines or tasks yet.")
    now = dt.datetime.now().timestamp()
    for t in tasks:
        c1, c2, c3 = st.columns([6, 3, 1])
        icon = "⚖️" if t["kind"] == "deadline" else "✅"
        can_tick = editor or t["assignee_id"] == u["id"]
        due_txt = ""
        if t["due"]:
            overdue = not t["done"] and t["due"] < now
            due_txt = f"{'🔴 overdue · ' if overdue else ''}{dt.datetime.fromtimestamp(t['due']):%a %b %d, %H:%M}"
        done = c1.checkbox(f"{icon} {t['title']}", value=t["done"], key=f"td_{t['id']}", disabled=not can_tick)
        if done != t["done"]:
            cases.set_task_done(u["id"], t["id"], done)
            st.rerun()
        c2.caption(f"{due_txt}{' · ' if due_txt and t['assignee'] else ''}{t['assignee'] or ''}")
        if editor and c3.button("🗑️", key=f"tx_{t['id']}", help="Delete"):
            cases.delete_task(u["id"], t["id"])
            st.rerun()


def _team_tab(u, case):
    cid = case["id"]
    mem = cases.members(u["id"], cid)
    pres = presence.status_of([m["id"] for m in mem])
    for m in mem:
        c1, c2, c3 = st.columns([4, 2, 1])
        dot = presence.DOT[pres[m["id"]]]
        c1.write(f"{dot} {m['email']}{'  (you)' if m['id'] == u['id'] else ''}")
        c1.caption(presence.LABEL[pres[m["id"]]])
        if case["role"] == "owner" and m["role"] != "owner":
            new = c2.selectbox("Role", cases.ASSIGNABLE_ROLES, index=cases.ASSIGNABLE_ROLES.index(m["role"]),
                               format_func=ROLE_LABEL.get, key=f"role_{m['id']}", label_visibility="collapsed")
            if new != m["role"]:
                cases.set_role(u["id"], cid, m["id"], new)
                st.rerun()
            if c3.button("Remove", key=f"rm_{m['id']}"):
                cases.remove_member(u["id"], cid, m["id"])
                st.rerun()
        else:
            c2.write(ROLE_LABEL.get(m["role"], m["role"]))
    if case["role"] == "owner":
        with st.form("addm", clear_on_submit=True):
            a, b = st.columns([3, 2])
            em = a.text_input("Invite a lawyer by email")
            role = b.selectbox("As", cases.ASSIGNABLE_ROLES, format_func=ROLE_LABEL.get)
            if st.form_submit_button("Add to case"):
                ok, msg = cases.add_member(u, cid, em, role)
                (st.success if ok else st.error)(msg)
        with st.expander("⚠️ Danger zone"):
            if st.checkbox("I understand this permanently deletes the case, chat, documents and deadlines",
                           key=f"cf_{cid}"):
                if st.button("Delete case", type="primary"):
                    cases.delete_case(u["id"], cid)
                    st.session_state.pop("case_id", None)
                    st.rerun()
    elif st.button("Leave case"):
        cases.remove_member(u["id"], cid, u["id"])
        st.session_state.pop("case_id", None)
        st.rerun()


def render():
    u = st.session_state["user"]
    ui.page_header("Cases", "Encrypted team chat, documents, deadlines and members for each matter.",
                   eyebrow="Workspace")
    with st.expander("New case", icon=":material/add:"):
        with st.form("newcase", clear_on_submit=True):
            title = st.text_input("Case title")
            desc = st.text_area("Short description (optional)")
            if st.form_submit_button("Create"):
                cid, msg = cases.create_case(u, title, desc)
                (st.success if cid else st.error)(msg)
                if cid:
                    st.session_state["case_id"] = cid
                    st.rerun()

    my = cases.list_cases(u["id"])
    if not my:
        st.info("Create your first case to start collaborating.")
        return
    ids = [c["id"] for c in my]
    cur = st.session_state.get("case_id") if st.session_state.get("case_id") in ids else ids[0]
    label = {c["id"]: f"{c['title']}  ({ROLE_LABEL.get(c['role'], c['role']).split(' ')[0].lower()})" for c in my}
    cid = st.selectbox("Open case", ids, index=ids.index(cur), format_func=label.get)
    st.session_state["case_id"] = cid
    case = cases.get_case(u["id"], cid)
    if not case:
        st.error("You no longer have access to this case.")
        return
    if case["desc"]:
        st.caption(case["desc"])
    pages = st.session_state.get("_pages", {})
    if "analysis" in pages:
        st.page_link(pages["analysis"], label="Analyse this case: timeline, legal basis, risks, drafting, strategy",
                     icon=":material/troubleshoot:")
    n_open = sum(1 for t in cases.list_tasks(u["id"], cid) if not t["done"])
    t_chat, t_docs, t_tasks, t_team = st.tabs(
        ["Team chat", "Documents", f"Deadlines & tasks · {n_open}" if n_open else "Deadlines & tasks", "Team"])
    with t_chat:
        _chat_tab(u, case)
    with t_docs:
        _docs_tab(u, case)
    with t_tasks:
        _tasks_tab(u, case)
    with t_team:
        _team_tab(u, case)
