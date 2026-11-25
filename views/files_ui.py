"""Files: every document you can open (yours and your cases'), with search, bulk upload, Google Docs import,
rename / move, and export as Word, PDF or text."""
import datetime as dt
import streamlit as st
import cases, config, docutil, export, gdocs, i18n, ui
from i18n import t

PAGE_SIZE = 25


def _editable_cases(uid: str):
    return [c for c in cases.list_cases(uid) if c["role"] in ("owner", "editor")]


def _save(u, name: str, text: str, case_id):
    did, msg = cases.add_document(u, case_id, name, text)
    (st.success if did else st.error)(f"{name}: {i18n.tm(msg)}")
    return bool(did)


def _add_panel(u):
    mine = _editable_cases(u["id"])
    dest = st.selectbox(t("Save to"), [None] + [c["id"] for c in mine], key="files_dest",
                        format_func=lambda cid: t("My files (private)") if cid is None
                        else next(c["title"] for c in mine if c["id"] == cid))
    tab_up, tab_g = st.tabs([t("Upload files"), t("Import from Google Docs")])
    with tab_up:
        ups = st.file_uploader(t("PDF, Word, TXT or MD, up to {mb} MB each", mb=config.MAX_UPLOAD_MB),
                               type=list(docutil.ALLOWED), accept_multiple_files=True, key="files_up")
        if ups and st.button(t("Save {n} file(s)", n=len(ups)), type="primary", icon=":material/upload:"):
            saved = 0
            for f in ups:
                text, err = docutil.extract_text(f.name, f.getvalue())
                if err:
                    st.error(f"{f.name}: {i18n.tm(err)}")
                else:
                    saved += _save(u, f.name, text, dest)
            if saved:
                st.toast(t("Saved {n} file(s).", n=saved), icon=":material/task_alt:")
    with tab_g:
        st.caption(t("Paste the link of a Google Doc. It must be shared as “Anyone with the link can view”. "
                     "LawVault never asks for your Google password."))
        link = st.text_input(t("Google Docs link"), placeholder="https://docs.google.com/document/d/…", key="gdoc_link")
        if st.button(t("Import"), icon=":material/cloud_download:", disabled=not link.strip(), key="gdoc_go"):
            with st.spinner(t("Fetching the document…")):
                name, text, err = gdocs.fetch(link)
            if err:
                st.error(i18n.tm(err))
            elif _save(u, name, text, dest):
                st.session_state["gdoc_link"] = ""


def _detail(u, row):
    d = cases.get_document(u["id"], row["id"])
    if not d:
        st.warning(t("That file is no longer available."))
        return
    base = d["filename"].rsplit(".", 1)[0]
    st.markdown(f"#### {d['filename']}")
    place = row["case"] or t("My files (private)")
    st.caption(t("{where} · uploaded by {who} · {n} characters", where=place,
                 who=t("you") if row["mine"] else row["owner"], n=f"{row['chars']:,}"))
    st.text_area(t("Preview"), d["text"][:4000] + ("…" if len(d["text"]) > 4000 else ""), height=200,
                 disabled=True, key=f"pv_{d['id']}")
    st.markdown(f"**{t('Download')}**")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Word (.docx)", export.to_docx(base, d["text"], plain=True), f"{base}.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       icon=":material/description:", use_container_width=True, key=f"dw_{d['id']}")
    c2.download_button("PDF", export.to_pdf(base, d["text"], plain=True), f"{base}.pdf", "application/pdf",
                       icon=":material/picture_as_pdf:", use_container_width=True, key=f"dp_{d['id']}")
    c3.download_button("TXT", d["text"].encode("utf-8"), f"{base}.txt", "text/plain",
                       icon=":material/article:", use_container_width=True, key=f"dt_{d['id']}")
    if d["analysis"]:
        st.markdown(f"**{t('AI review')}**")
        a1, a2 = st.columns(2)
        note = "AI-generated. Verify before relying on it."
        a1.download_button(t("Review as Word"), export.to_docx(f"{base} – review", d["analysis"], note),
                           f"{base}-review.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           icon=":material/description:", use_container_width=True, key=f"rw_{d['id']}")
        a2.download_button(t("Review as PDF"), export.to_pdf(f"{base} – review", d["analysis"], note),
                           f"{base}-review.pdf", "application/pdf", icon=":material/picture_as_pdf:",
                           use_container_width=True, key=f"rp_{d['id']}")
    if st.button(t("Check for AI-written text"), icon=":material/fingerprint:", key=f"det_{d['id']}"):
        st.session_state["detector_doc"] = d["id"]
        st.switch_page(st.session_state["_pages"]["detector"])
    if not row["can_edit"]:
        return
    with st.expander(t("Rename or move"), icon=":material/drive_file_rename_outline:"):
        new = st.text_input(t("Name"), d["filename"], key=f"rn_{d['id']}")
        if st.button(t("Rename"), key=f"rnb_{d['id']}", disabled=not new.strip() or new == d["filename"]):
            if cases.rename_document(u["id"], d["id"], new):
                st.rerun()
        if row["mine"]:
            mine = _editable_cases(u["id"])
            opts = [None] + [c["id"] for c in mine]
            cur = opts.index(row["case_id"]) if row["case_id"] in opts else 0
            to = st.selectbox(t("Move to"), opts, index=cur, key=f"mv_{d['id']}",
                              format_func=lambda cid: t("My files (private)") if cid is None
                              else next(c["title"] for c in mine if c["id"] == cid))
            if st.button(t("Move"), key=f"mvb_{d['id']}", disabled=to == row["case_id"]):
                ok, msg = cases.move_document(u["id"], d["id"], to)
                if ok:
                    st.rerun()
                st.error(i18n.tm(msg))
    if row["mine"]:
        if st.button(t("Delete"), key=f"del_{d['id']}", icon=":material/delete:"):
            cases.delete_document(u["id"], d["id"])
            st.rerun()


def render():
    u = st.session_state["user"]
    ui.page_header("Files", "Every document you can open, in one place: search, upload, import and export.",
                   eyebrow="Workspace")
    with st.expander(t("Add files"), icon=":material/upload_file:"):
        _add_panel(u)
    c1, c2, c3 = st.columns([3, 2, 2])
    q = c1.text_input(t("Search"), placeholder=t("Search names and contents…"), label_visibility="collapsed")
    scope = c2.selectbox(t("Show"), ["all", "mine", "personal"], label_visibility="collapsed",
                         format_func=lambda s: {"all": t("All files"), "mine": t("Uploaded by me"),
                                                "personal": t("Private (not in a case)")}[s])
    all_cases = cases.list_cases(u["id"])
    case_id = c3.selectbox(t("Case"), [None] + [c["id"] for c in all_cases], label_visibility="collapsed",
                           format_func=lambda cid: t("Any case") if cid is None
                           else next(c["title"] for c in all_cases if c["id"] == cid))
    rows = cases.list_accessible_documents(u["id"], q, case_id, scope)
    if not rows:
        st.info(t("No files match."), icon=":material/folder_off:")
        return
    shown = rows[:PAGE_SIZE]
    table = [{t("Name"): r["filename"], t("Case"): r["case"] or "—", t("Owner"): t("you") if r["mine"] else r["owner"],
              t("Added"): i18n.date_md(dt.datetime.fromtimestamp(r["created_at"])),
              t("Reviewed"): "✓" if r["has_analysis"] else ""} for r in shown]
    if q.strip():
        for tr, r in zip(table, shown):
            tr[t("Match")] = r["snippet"]
    sel = st.dataframe(table, hide_index=True, use_container_width=True, on_select="rerun",
                       selection_mode="single-row", key="files_table")
    if len(rows) > PAGE_SIZE:
        st.caption(t("Showing the newest {n} of {total}. Narrow the search to see others.", n=PAGE_SIZE, total=len(rows)))
    idx = (sel.selection.rows or [None])[0]
    if idx is None:
        st.caption(t("Select a row to preview, download, rename or move a file."))
        return
    with st.container(border=True):
        _detail(u, shown[idx])
