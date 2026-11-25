import streamlit as st
import datetime as dt
import ai, cal, cases, config, docutil, i18n, jobs, subscription, ui
from views import voice_ui
from i18n import t

BACKGROUND_NOTE = "This keeps running if you switch tabs. You'll get a notification when it's done."  # shown via t()


def _poll(user_id: str, kinds):
    """While any of these jobs run, check every 1.5 s and redraw the page as soon as one finishes."""
    watching = jobs.running_keys(user_id, kinds)
    if not watching:
        return

    @st.fragment(run_every=1.5)
    def _check():
        if not watching <= jobs.running_keys(user_id, kinds):
            st.rerun(scope="app")
    _check()


def qa():
    u = st.session_state["user"]
    ui.page_header("Legal assistant", "Research questions, statutes, procedure and drafting. Answers are concise "
                   "and to the point.", eyebrow="AI")
    st.caption(t("{disclaimer}  ·  {used} / {cap} requests used today  ·  Personal data is masked before it "
                 "leaves LawVault.", disclaimer=t(ai.DISCLAIMER), used=subscription.ai_used_today(u["id"]),
                 cap=subscription.limits(u)["daily_ai"]))
    hist = ai.chat_history(u["id"])
    for h in hist:
        with st.chat_message(h["role"], avatar=":material/person:" if h["role"] == "user" else ":material/balance:"):
            st.markdown(h["content"])

    job = jobs.get(u["id"], "chat")
    if job:
        if job["running"]:  # the question isn't saved until the answer arrives, so show it from the job
            with st.chat_message("user", avatar=":material/person:"):
                st.markdown(job["meta"]["q"])
            with st.chat_message("assistant", avatar=":material/balance:"):
                st.markdown("_" + t("Researching…") + "_")
                st.caption(t(BACKGROUND_NOTE))
        else:
            if job["error"]:
                with st.chat_message("user", avatar=":material/person:"):
                    st.markdown(job["meta"]["q"])
                st.error(i18n.tm(job["error"]))
            jobs.pop(u["id"], "chat")
    elif not hist:
        st.info(t("Ask about limitation periods, elements of a claim, procedural steps, or paste a clause to "
                  "have it explained."), icon=":material/lightbulb:")

    busy = bool(job and job["running"])
    spoken = None if busy else voice_ui.mic(u, "qa_mic")
    q = st.chat_input(t("Waiting for the answer…") if busy else t("Ask a legal question…"), disabled=busy) or spoken
    if q and not busy:
        jobs.start(u["id"], "chat", "", ai.ask, u, q, hist, label="Legal assistant", meta={"q": q})
        st.rerun()
    if hist and not busy and st.button(t("Clear conversation"), icon=":material/delete_sweep:"):
        ai.clear_history(u["id"])
        st.rerun()
    _poll(u["id"], {"chat"})


def _review_and_save(user, doc_id: str, text: str):
    """Runs in the background: the review is saved even if nobody is looking at the page when it finishes."""
    res, err = ai.analyze_document(user, text)
    if not err and not cases.save_analysis(user["id"], doc_id, res):
        err = "The review finished but couldn't be saved (the document may have been deleted)."
    return res, err


def analyzer():
    u = st.session_state["user"]
    ui.page_header("Document review", "Upload a contract for a structured review: parties, operative clauses, "
                   "risk flags and points to raise.", eyebrow="AI")
    if not subscription.has_feature(u, "doc_review"):
        st.info(t("Document review is switched off in your plan. You can turn it on under Settings → Billing."),
                icon=":material/lock:")
        return
    st.caption(ai.DISCLAIMER)
    up = st.file_uploader(t("Upload a contract (PDF or TXT, up to {mb} MB)", mb=config.MAX_UPLOAD_MB),
                          type=["pdf", "txt"])
    if up and st.button(t("Save document"), type="primary", icon=":material/upload:"):
        text, err = docutil.extract_text(up.name, up.getvalue())
        if err:
            st.error(i18n.tm(err))
        else:
            did, msg = cases.add_document(u, None, up.name, text)
            (st.success if did else st.error)(i18n.tm(msg))
    for d in cases.list_documents(u["id"]):
        review = jobs.get(u["id"], "review", d["id"])
        found_job = jobs.get(u["id"], "deadlines", d["id"])
        working = any(j and j["running"] for j in (review, found_job))
        with st.expander(d["filename"] + (t("  ·  working…") if working else ""), icon=":material/description:",
                         expanded=working):
            full = cases.get_document(u["id"], d["id"])
            if review:
                if review["running"]:
                    st.info(f"{t('Reviewing…')} {t(BACKGROUND_NOTE)}", icon=":material/hourglass_top:")
                else:
                    if review["error"]:
                        st.error(i18n.tm(review["error"]))
                    jobs.pop(u["id"], "review", d["id"])
            if full["analysis"]:
                st.markdown(full["analysis"])
            c1, c2 = st.columns(2)
            if c1.button(t("Review with AI"), key=f"a_{d['id']}", icon=":material/auto_awesome:",
                         use_container_width=True, disabled=bool(review and review["running"])):
                jobs.start(u["id"], "review", d["id"], _review_and_save, u, d["id"], full["text"],
                           label=f"Review of {d['filename']}", meta={"tpl": "Review of {name}", "name": d["filename"]})
                st.rerun()
            if c2.button(t("Delete"), key=f"d_{d['id']}", icon=":material/delete:", use_container_width=True):
                cases.delete_document(u["id"], d["id"])
                st.rerun()
            if st.button(t("Find deadlines and add to my calendar"), key=f"fd_{d['id']}", icon=":material/event:",
                         disabled=bool(found_job and found_job["running"])):
                jobs.start(u["id"], "deadlines", d["id"], ai.extract_deadlines, u, full["text"],
                           label=f"Deadlines in {d['filename']}",
                           meta={"tpl": "Deadlines in {name}", "name": d["filename"]})
                st.rerun()
            if found_job and found_job["running"]:
                st.info(f"{t('Looking for deadlines…')} {t(BACKGROUND_NOTE)}", icon=":material/hourglass_top:")
            elif found_job:
                jobs.mark_seen(u["id"], "deadlines", d["id"])
                found, err = found_job["value"], found_job["error"]
                if err:
                    st.error(i18n.tm(err))
                elif not found:
                    st.info(t("No dated deadlines found."))
                else:
                    picks = [i for i, f in enumerate(found)
                             if st.checkbox(f"{i18n.date_wmdy(f['date'])} — {f['title']}", value=True,
                                            key=f"pdc_{d['id']}_{i}")]
                    if st.button(t("Add selected to my calendar"), key=f"pda_{d['id']}", type="primary"):
                        for i in picks:
                            s = dt.datetime.combine(found[i]["date"], dt.time(9, 0)).timestamp()
                            cal.add_event(u, f"⚖️ {found[i]['title']}", s, s + 1800, f"From {d['filename']}")
                        jobs.pop(u["id"], "deadlines", d["id"])
                        st.success(t("Added {n} event(s) to your calendar.", n=len(picks)))
    _poll(u["id"], {"review", "deadlines"})
