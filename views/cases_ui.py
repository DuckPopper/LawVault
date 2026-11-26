import datetime as dt
import streamlit as st
import ai, auth, cases, config, contacts, docutil, i18n, presence, ui
from i18n import t

ROLE_LABEL = {"owner": "Owner", "editor": "Editor", "viewer": "Viewer (read-only)"}


def _role_label(role: str) -> str:
    return t(ROLE_LABEL.get(role, role))


def _who_is_here(user_id: str, case_id: str):
    mem = cases.members(user_id, case_id)
    st_ = presence.status_of([m["id"] for m in mem])
    parts = [f"{presence.DOT[st_[m['id']]]} {t('You') if m['id'] == user_id else m['email'].split('@')[0]}" for m in mem]
    st.caption("  ·  ".join(parts))


@st.fragment(run_every=3)
def chat_feed(user_id: str, case_id: str):
    """Auto-refreshing group chat. Re-checks the session and membership on every refresh."""
    if not auth.peek_session(st.session_state.get("token")):
        st.warning(t("Your session ended. Refresh the page to log in again."))
        return
    _who_is_here(user_id, case_id)
    msgs = cases.get_messages(user_id, case_id)
    box = st.container(height=420, border=True)
    with box:
        if not msgs:
            st.caption(t("No messages yet. Start the discussion below. Tip: type “@ai” and a question to ask the AI."))
        for m in msgs:
            when = i18n.fmt(dt.datetime.fromtimestamp(m["ts"]), "%b %d %H:%M")
            if m["kind"] == "ai":
                with st.chat_message("assistant", avatar=":material/balance:"):
                    asker = t("you") if m["user_id"] == user_id else m["email"].split("@")[0]
                    st.caption(t("LawVault AI · answering {who} · {when}", who=asker, when=when))
                    st.markdown(m["body"])
                    st.caption(ai.DISCLAIMER)
                continue
            mine = m["user_id"] == user_id
            with st.chat_message("user" if mine else "human"):
                st.caption(f"{t('You') if mine else m['email']} · {when}")
                st.text(m["body"])


def _chat_tab(u, case):
    cid = case["id"]
    c1, c2 = st.columns([2, 3])
    if c1.button(t("Brief me on this case"), icon=":material/auto_awesome:",
                 help=t("AI briefing from the chat, documents and deadlines")):
        with st.spinner(t("Reading the case…")):
            text, err = ai.summarize_case(u, cid)
        st.session_state[f"summary_{cid}"] = (text, err)
    res = st.session_state.get(f"summary_{cid}")
    if res:
        text, err = res
        if err:
            st.error(i18n.tm(err))
        else:
            with st.expander(t("Case briefing"), expanded=True):
                st.markdown(text)
                st.caption(ai.DISCLAIMER)
                a, b = st.columns(2)
                if case["role"] != "viewer" and a.button(t("Post briefing to team chat")):
                    cases.post_message(u["id"], cid, "**" + t("Case briefing") + "**\n\n" + text, kind="ai")
                    st.session_state.pop(f"summary_{cid}")
                    st.rerun()
                if b.button(t("Dismiss")):
                    st.session_state.pop(f"summary_{cid}")
                    st.rerun()

    chat_feed(u["id"], cid)
    if case["role"] == "viewer":
        st.caption(t("👁️ You have view-only access to this case."))
        return
    flash = st.session_state.pop("chat_flash", None)
    if flash:
        st.error(i18n.tm(flash))
    text = st.chat_input(t("Message your team… (start with @ai to ask the AI, @email to mention someone)"))
    if text:
        cases.post_message(u["id"], cid, text)
        if ai.AI_TRIGGER.match(text):
            with st.spinner(t("LawVault AI is thinking…")):
                ok, err = ai.answer_in_chat(u, cid, text)
            if not ok:
                st.session_state["chat_flash"] = err
        st.rerun()


def _docs_tab(u, case):
    cid = case["id"]
    editor = case["role"] != "viewer"
    if editor:
        up = st.file_uploader(t("Upload PDF, Word or TXT to this case (up to {mb} MB)", mb=config.MAX_UPLOAD_MB),
                              type=list(docutil.ALLOWED), key=f"up_{cid}")
        if up and st.button(t("Save to case")):
            text, err = docutil.extract_text(up.name, up.getvalue())
            if err:
                st.error(i18n.tm(err))
            else:
                did, msg = cases.add_document(u, cid, up.name, text)
                (st.success if did else st.error)(i18n.tm(msg))
    docs = cases.list_documents(u["id"], cid)
    if not docs:
        st.caption(t("No documents yet."))
    for d in docs:
        with st.expander(d["filename"], icon=":material/description:"):
            full = cases.get_document(u["id"], d["id"])
            if full and full["analysis"]:
                st.markdown(full["analysis"])
                st.caption(ai.DISCLAIMER)
            if not editor:
                continue
            a, b = st.columns(2)
            if a.button(t("Analyze with AI"), key=f"an_{d['id']}"):
                with st.spinner(t("Analyzing…")):
                    res, err = ai.analyze_document(u, full["text"])
                if err:
                    st.error(i18n.tm(err))
                else:
                    cases.save_analysis(u["id"], d["id"], res)
                    st.rerun()
            if b.button(t("📅 Find deadlines"), key=f"dl_{d['id']}", help=t("AI pulls out dates you must act on")):
                with st.spinner(t("Looking for deadlines…")):
                    found, err = ai.extract_deadlines(u, full["text"])
                st.session_state[f"dl_{d['id']}"] = (found, err)
            res = st.session_state.get(f"dl_{d['id']}")
            if res:
                found, err = res
                if err:
                    st.error(i18n.tm(err))
                elif not found:
                    st.info(t("No dated deadlines found."))
                else:
                    picks = [i for i, f in enumerate(found)
                             if st.checkbox(f"{i18n.date_wmdy(f['date'])} — {f['title']}", value=True,
                                            key=f"dlc_{d['id']}_{i}")]
                    if st.button(t("Add selected to case deadlines"), key=f"dla_{d['id']}", type="primary"):
                        for i in picks:
                            due = dt.datetime.combine(found[i]["date"], dt.time(9, 0)).timestamp()
                            cases.add_task(u["id"], cid, "deadline", found[i]["title"], due)
                        st.session_state.pop(f"dl_{d['id']}")
                        st.success(t("Added {n} deadline(s). They also appear on everyone's calendar.", n=len(picks)))


def _tasks_tab(u, case):
    cid = case["id"]
    members = cases.members(u["id"], cid)
    editor = case["role"] != "viewer"
    if editor:
        with st.expander(t("➕ Add a deadline or task")):
            with st.form(f"task_{cid}", clear_on_submit=True):
                kind = st.radio(t("Type"), cases.TASK_KINDS, horizontal=True,
                                format_func=lambda k: t({"deadline": "⚖️ Deadline (court/filing date)",
                                                         "task": "✅ Task"}[k]))
                title = st.text_input(t("What"), placeholder=t("File statement of defence"))
                c1, c2, c3 = st.columns(3)
                has_due = c1.checkbox(t("Has a due date"), value=True)
                day = c2.date_input(t("Due date"), value=dt.date.today() + dt.timedelta(days=7))
                at = c3.time_input(t("Time"), value=dt.time(17, 0), step=900)
                who = st.selectbox(t("Assign to"), [None] + [m["id"] for m in members],
                                   format_func=lambda i: t("Nobody") if i is None else next(
                                       m["email"] for m in members if m["id"] == i))
                if st.form_submit_button(t("Add"), type="primary"):
                    due = dt.datetime.combine(day, at).timestamp() if has_due or kind == "deadline" else None
                    tid, msg = cases.add_task(u["id"], cid, kind, title, due, who)
                    (st.success if tid else st.error)(i18n.tm(msg))
    tasks = cases.list_tasks(u["id"], cid)
    if not tasks:
        st.caption(t("No deadlines or tasks yet."))
    now = dt.datetime.now().timestamp()
    for tk in tasks:
        c1, c2, c3 = st.columns([6, 3, 1])
        icon = "⚖️" if tk["kind"] == "deadline" else "✅"
        can_tick = editor or tk["assignee_id"] == u["id"]
        due_txt = ""
        if tk["due"]:
            overdue = not tk["done"] and tk["due"] < now
            due_txt = f"{t('🔴 overdue · ') if overdue else ''}{i18n.date_time(dt.datetime.fromtimestamp(tk['due']))}"
        done = c1.checkbox(f"{icon} {tk['title']}", value=tk["done"], key=f"td_{tk['id']}", disabled=not can_tick)
        if done != tk["done"]:
            cases.set_task_done(u["id"], tk["id"], done)
            st.rerun()
        c2.caption(f"{due_txt}{' · ' if due_txt and tk['assignee'] else ''}{tk['assignee'] or ''}")
        if editor and c3.button("🗑️", key=f"tx_{tk['id']}", help=t("Delete")):
            cases.delete_task(u["id"], tk["id"])
            st.rerun()


def _team_tab(u, case):
    cid = case["id"]
    mem = cases.members(u["id"], cid)
    pres = presence.status_of([m["id"] for m in mem])
    notes = presence.messages_of([m["id"] for m in mem])
    for m in mem:
        c1, c2, c3 = st.columns([4, 2, 1])
        dot = presence.DOT[pres[m["id"]]]
        c1.write(f"{dot} {m['email']}{t('  (you)') if m['id'] == u['id'] else ''}")
        c1.caption(t(presence.LABEL[pres[m["id"]]]) + (f" · “{notes[m['id']]}”" if notes[m["id"]] else ""))
        if case["role"] == "owner" and m["role"] != "owner":
            new = c2.selectbox(t("Role"), cases.ASSIGNABLE_ROLES, index=cases.ASSIGNABLE_ROLES.index(m["role"]),
                               format_func=_role_label, key=f"role_{m['id']}", label_visibility="collapsed")
            if new != m["role"]:
                cases.set_role(u["id"], cid, m["id"], new)
                st.rerun()
            if c3.button(t("Remove"), key=f"rm_{m['id']}"):
                cases.remove_member(u["id"], cid, m["id"])
                st.rerun()
        else:
            c2.write(_role_label(m["role"]))
    if case["role"] == "owner":
        for inv in cases.pending_invites(u["id"], cid):
            p1, p2, p3 = st.columns([4, 2, 1])
            p1.write(f"✉️ {inv['email']}")
            p1.caption(t("Invited, not signed up yet"))
            p2.write(_role_label(inv["role"]))
            if p3.button(t("Cancel"), key=f"ci_{inv['email']}"):
                cases.cancel_invite(u["id"], cid, inv["email"])
                st.rerun()
        member_emails = {m["email"] for m in mem} | {i["email"] for i in cases.pending_invites(u["id"], cid)}
        pick = [ct for ct in contacts.listing(u["id"]) if ct["email"] not in member_emails]
        if pick:
            p1, p2, p3 = st.columns([3, 2, 1])
            who = p1.selectbox(t("Add from contacts"), [ct["email"] for ct in pick], key=f"pick_{cid}")
            prole = p2.selectbox(t("As"), cases.ASSIGNABLE_ROLES, format_func=_role_label, key=f"pickrole_{cid}")
            p3.write("")
            if p3.button(t("Add"), key=f"pickadd_{cid}"):
                ok, msg = cases.add_member(u, cid, who, prole)
                (st.success if ok else st.error)(i18n.tm(msg))
                if ok:
                    st.rerun()
        with st.form("addm", clear_on_submit=True):
            a, b = st.columns([3, 2])
            em = a.text_input(t("Invite a lawyer by email"))
            role = b.selectbox(t("As"), cases.ASSIGNABLE_ROLES, format_func=_role_label)
            if st.form_submit_button(t("Add to case")):
                ok, msg = cases.add_member(u, cid, em, role)
                (st.success if ok else st.error)(i18n.tm(msg))
        with st.expander(t("⚠️ Danger zone")):
            if st.checkbox(t("I understand this permanently deletes the case, chat, documents and deadlines"),
                           key=f"cf_{cid}"):
                if st.button(t("Delete case"), type="primary"):
                    cases.delete_case(u["id"], cid)
                    st.session_state.pop("case_id", None)
                    st.rerun()
    elif st.button(t("Leave case")):
        cases.remove_member(u["id"], cid, u["id"])
        st.session_state.pop("case_id", None)
        st.rerun()


def _contacts_panel(u):
    st.caption(t("Coworkers and friends you work with. Only you can see this list."))
    for ct in contacts.listing(u["id"]):
        a, b = st.columns([5, 1])
        a.write(f"{ct['name']} · {ct['email']}" if ct["name"] else ct["email"])
        if b.button(t("Remove"), key=f"ctrm_{ct['email']}"):
            contacts.remove(u["id"], ct["email"])
            st.rerun()
    with st.form("addcontact", clear_on_submit=True):
        a, b = st.columns([3, 2])
        em = a.text_input(t("Email"))
        nm = b.text_input(t("Name (optional)"))
        if st.form_submit_button(t("Save contact")):
            ok, msg = contacts.add(u["id"], em, nm)
            (st.success if ok else st.error)(i18n.tm(msg))


def render():
    u = st.session_state["user"]
    ui.page_header("Cases", "Encrypted team chat, documents, deadlines and members for each matter.",
                   eyebrow="Workspace")
    with st.expander(t("New case"), icon=":material/add:"):
        with st.form("newcase", clear_on_submit=True):
            title = st.text_input(t("Case title"))
            desc = st.text_area(t("Short description (optional)"))
            if st.form_submit_button(t("Create")):
                cid, msg = cases.create_case(u, title, desc)
                (st.success if cid else st.error)(i18n.tm(msg))
                if cid:
                    st.session_state["case_id"] = cid
                    st.rerun()

    with st.expander(t("My contacts"), icon=":material/group:"):
        _contacts_panel(u)

    my = cases.list_cases(u["id"])
    if not my:
        st.info(t("Create your first case to start collaborating."))
        return
    ids = [c["id"] for c in my]
    cur = st.session_state.get("case_id") if st.session_state.get("case_id") in ids else ids[0]
    label = {c["id"]: f"{c['title']}  ({_role_label(c['role']).split(' ')[0].lower()})" for c in my}
    cid = st.selectbox(t("Open case"), ids, index=ids.index(cur), format_func=label.get)
    st.session_state["case_id"] = cid
    case = cases.get_case(u["id"], cid)
    if not case:
        st.error(t("You no longer have access to this case."))
        return
    if case["desc"]:
        st.caption(case["desc"])
    pages = st.session_state.get("_pages", {})
    if "analysis" in pages:
        st.page_link(pages["analysis"], label=t("Analyse this case: timeline, legal basis, risks, drafting, strategy"),
                     icon=":material/troubleshoot:")
    n_open = sum(1 for t in cases.list_tasks(u["id"], cid) if not t["done"])
    t_chat, t_docs, t_tasks, t_team = st.tabs(
        [t("Team chat"), t("Documents"), f"{t('Deadlines & tasks')} · {n_open}" if n_open else t("Deadlines & tasks"),
         t("Team")])
    with t_chat:
        _chat_tab(u, case)
    with t_docs:
        _docs_tab(u, case)
    with t_tasks:
        _tasks_tab(u, case)
    with t_team:
        _team_tab(u, case)
