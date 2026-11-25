"""AI-writing detector page: paste text, pick a saved file or upload one."""
import streamlit as st
import cases, config, detector, docutil, i18n, subscription, ui
from i18n import t

DISCLAIMER = ("No AI detector is reliable. Formal legal drafting, non-native writing and edited AI text all give "
              "false results. Treat this as a prompt for your own judgement, never as proof.")


def _result(res: dict):
    if not res["ok"]:
        st.warning(t("Add at least {n} words for a meaningful result.", n=res["min_words"]))
        return
    colour = "red" if res["score"] >= 70 else "amber" if res["score"] >= 45 else "green"
    c1, c2 = st.columns([1, 3])
    c1.markdown(ui.stat("AI-writing score", f"{res['score']}%", t(res["label"]), res["score"] / 100), unsafe_allow_html=True)
    c2.markdown(f'<span class="lv-pill {colour}">{ui.esc(t(res["label"]))}</span>', unsafe_allow_html=True)
    c2.caption(t("Based on {n} words. {d}", n=f"{res['words']:,}", d=t(DISCLAIMER)))
    ui.section("What the check looked at")
    for s in res["signals"]:
        w = int(s["ai_like"] * 100)
        ui.html_block(f'<div class="lv-item"><div class="lv-item-main"><div class="lv-item-title">{ui.esc(t(s["name"]))}'
                      f' <span class="lv-item-sub">· {ui.esc(s["value"])}</span></div>'
                      f'<div class="lv-item-sub">{ui.esc(t(s["note"]))}</div>'
                      f'<div class="lv-bar"><i style="width:{w}%"></i></div></div>'
                      f'<div class="lv-item-side">{w}% {ui.esc(t("AI-like"))}</div></div>')
    if res["flagged"]:
        ui.section("Sentences with stock phrases")
        for s in res["flagged"]:
            st.markdown(f"> {s}")


def render():
    u = st.session_state["user"]
    ui.page_header("AI detector", "Check whether a text reads as written by an AI. A quick statistical check, plus an "
                   "optional second opinion from the AI.", eyebrow="AI")
    st.caption(t(DISCLAIMER))
    text, name = "", ""
    pre = st.session_state.pop("detector_doc", None)      # sent over from the Files page
    if pre and (d := cases.get_document(u["id"], pre)):
        text, name = d["text"], d["filename"]
        st.session_state["det_text"] = text
    tab_paste, tab_file = st.tabs([t("Paste text"), t("A file")])
    with tab_paste:
        pasted = st.text_area(t("Text to check"), key="det_text", height=240, max_chars=60_000,
                              placeholder=t("Paste the text here…"))
        if pasted.strip():
            text, name = pasted, ""
    with tab_file:
        docs = cases.list_accessible_documents(u["id"])
        pick = st.selectbox(t("A saved file"), [None] + [d["id"] for d in docs], key="det_pick",
                            format_func=lambda i: t("— choose —") if i is None else next(d["filename"] for d in docs if d["id"] == i))
        up = st.file_uploader(t("Or upload one"), type=list(docutil.ALLOWED), key="det_up")
        if pick and (d := cases.get_document(u["id"], pick)):
            text, name = d["text"], d["filename"]
        if up:
            text, err = docutil.extract_text(up.name, up.getvalue())
            if err:
                st.error(i18n.tm(err))
            name = up.name
    text = (text or "")[:60_000]
    if not text.strip():
        st.info(t("Paste some text or choose a file to check."), icon=":material/fingerprint:")
        return
    if name:
        st.caption(t("Checking: {name}", name=name))
    _result(detector.analyze(text))

    ui.section("Second opinion")
    st.caption(t("Asks the AI to judge the text. Personal data is masked first. Uses 1 of your {cap} daily AI requests.",
                 cap=subscription.limits(u)["daily_ai"]))
    if st.button(t("Ask the AI"), icon=":material/auto_awesome:", key="det_ai"):
        with st.spinner(t("Reading…")):
            op, err = detector.ai_opinion(u, text)
        st.session_state["det_op"] = (op, err)
    op, err = st.session_state.get("det_op", (None, None))
    if err:
        st.error(i18n.tm(err))
    elif op:
        st.markdown(f"**{t('AI opinion')}: {op['score']}% — {t(op['label'])}**")
        for r in op["reasons"]:
            st.markdown(f"- {r}")
