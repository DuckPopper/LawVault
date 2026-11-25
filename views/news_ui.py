"""Current affairs: headlines in English and/or Bahasa Indonesia, filtered by each user's saved topics."""
import datetime as dt
import streamlit as st
import i18n, news, ui
from i18n import t


def _ago(ts: float) -> str:
    if not ts:
        return ""
    s = int(dt.datetime.now().timestamp() - ts)
    if s < 3600:
        return t("{n} min ago", n=max(1, s // 60))
    if s < 86400:
        return t("{n} h ago", n=s // 3600)
    return i18n.date_md(dt.datetime.fromtimestamp(ts))


def _card(n: dict) -> str:
    summary = f'<div class="lv-row-d">{ui.esc(n["summary"])}</div>' if n["summary"] else ""
    icon = {"law": "⚖️", "finance": "💼", "tech": "💻", "sports": "⚽", "world": "🌍"}.get(n["topic"], "📰")
    thumb = (f'<img src="{ui.esc(n["image"])}" alt="" loading="lazy" referrerpolicy="no-referrer" '
             f'onerror="this.remove()">' if n.get("image") else "")
    return (f'<div class="lv-card lv-news" style="margin-bottom:.7rem">'
            f'<div class="lv-thumb"><span class="lv-thumb-ico">{icon}</span>{thumb}</div>'
            f'<div class="lv-news-body">'
            f'<div class="lv-risk-h"><span class="lv-pill">{ui.esc(t(news.TOPICS[n["topic"]]))}</span>'
            f'<span class="lv-pill grey">{ui.esc(n["lang"].upper())}</span>'
            f'<span class="lv-item-sub" style="margin-left:auto">{ui.esc(n["source"])} · {ui.esc(_ago(n["ts"]))}</span></div>'
            f'<div class="lv-row-t" style="margin-top:.45rem"><a href="{ui.esc(n["link"])}" target="_blank" '
            f'rel="noopener noreferrer" style="text-decoration:none">{ui.esc(n["title"])}</a></div>{summary}</div></div>')


def render():
    u = st.session_state["user"]
    ui.page_header("News", "Current affairs in English and Bahasa Indonesia, filtered to the topics you follow.",
                   eyebrow="Workspace")
    prefs = news.get_prefs(u["id"])
    with st.expander(t("Choose what you see"), icon=":material/tune:", expanded=False):
        langs = st.pills(t("Languages"), list(news.LANGS), selection_mode="multi", default=prefs["langs"],
                         format_func=lambda c: news.LANG_LABEL[c], key="news_langs")
        topics = st.pills(t("Topics"), list(news.TOPICS), selection_mode="multi", default=prefs["topics"],
                          format_func=lambda k: t(news.TOPICS[k]), key="news_topics")
        if st.button(t("Save my choices"), type="primary", icon=":material/check:"):
            ok, msg = news.set_prefs(u["id"], langs or [], topics or [])
            (st.success if ok else st.error)(t(msg))
            if ok:
                st.rerun()
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.caption(t("Headlines from ANTARA, CNN Indonesia and BBC. Refreshed every 10 minutes. Tap a headline to read the full story on the publisher's site."))
    if c2.button(t("Refresh"), icon=":material/refresh:", use_container_width=True):
        news.clear_cache()
        st.rerun()
    with st.spinner(t("Loading headlines…")):
        items = news.headlines(prefs["langs"], prefs["topics"])
    if not items:
        st.info(t("No headlines right now. The publishers may be unreachable; try again in a minute."),
                icon=":material/cloud_off:")
        return
    left, right = st.columns(2)
    for i, n in enumerate(items):
        (left if i % 2 == 0 else right).markdown(_card(n), unsafe_allow_html=True)
