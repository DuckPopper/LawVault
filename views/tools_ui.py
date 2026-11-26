"""Tools: small utilities lawyers reach for every day. Zip, PDF pages, watermark, sign, and an AI e-mail draft."""
import streamlit as st
import cases, config, i18n, pdfedit, sigplace, tools, ui
from i18n import t

PDF_MIME = "application/pdf"
IMG_TYPES = ["png", "jpg", "jpeg"]


def _guard(fn, *a, **kw):
    """Run a tool; show its error (translated) and return None instead of crashing the page."""
    try:
        return fn(*a, **kw)
    except tools.ToolError as e:
        st.error(i18n.tm(str(e)))
    except Exception:  # a malformed upload should never take the page down
        st.error(t("Something went wrong with that file. Please try another."))
    return None


def _too_big(files) -> bool:
    big = [f.name for f in files if f.size > config.MAX_UPLOAD_BYTES]
    if big:
        st.error(t("Too large (max {mb} MB): {names}", mb=config.MAX_UPLOAD_MB, names=", ".join(big)))
    return bool(big)


def _stem(name: str) -> str:
    return name.rsplit(".", 1)[0] if "." in name else name


# ---------- zipper ----------
def _zip_tool():
    st.caption(t("Drop any files and get one .zip. Everything stays on this server and is not saved."))
    files = st.file_uploader(t("Files to zip"), accept_multiple_files=True, key="tl_zip_up")
    name = st.text_input(t("Zip name"), "documents", key="tl_zip_name")
    if not files or _too_big(files):
        return
    total = sum(f.size for f in files)
    if total > config.MAX_UPLOAD_BYTES * 2:
        st.error(t("That is too much to zip at once."))
        return
    out = _guard(tools.make_zip, [(f.name, f.getvalue()) for f in files])
    if out:
        st.caption(t("{n} file(s), {kb} KB in, {zkb} KB zipped", n=len(files), kb=f"{total // 1024:,}",
                     zkb=f"{len(out) // 1024:,}"))
        st.download_button(t("Download zip"), out, f"{tools._safe_name(name) or 'documents'}.zip", "application/zip",
                           type="primary", icon=":material/folder_zip:", key="tl_zip_dl")


# ---------- PDF tools ----------
def _merge_tool():
    ups = st.file_uploader(t("PDFs to merge, in order"), type=["pdf"], accept_multiple_files=True, key="tl_mg_up")
    if not ups or _too_big(ups):
        return
    st.caption(" → ".join(f.name for f in ups))
    if len(ups) < 2:
        st.info(t("Add at least two PDFs to merge."))
        return
    out = _guard(tools.merge_pdfs, [f.getvalue() for f in ups])
    if out:
        st.download_button(t("Download merged PDF"), out, "merged.pdf", PDF_MIME, type="primary",
                           icon=":material/download:", key="tl_mg_dl")


def _organize_tool():
    up = st.file_uploader(t("PDF"), type=["pdf"], key="tl_pg_up")
    if not up or _too_big([up]):
        return
    data = up.getvalue()
    n = _guard(tools.page_count, data)
    if not n:
        return
    st.caption(t("{n} pages.", n=n))
    spec = st.text_input(t("Pages to keep, in the order you want them"), placeholder="1-3, 5, 8-",
                         help=t("Leave empty to keep all. 3,1,2 puts page 3 first. Leave a page out to delete it."),
                         key="tl_pg_spec")
    out = _guard(tools.organize_pdf, data, spec, 0)
    if out:
        st.download_button(t("Download PDF"), out, f"{_stem(up.name)}-organized.pdf", PDF_MIME,
                           type="primary", icon=":material/download:", key="tl_pg_dl")


def _rotate_tool():
    up = st.file_uploader(t("PDF"), type=["pdf"], key="tl_ro_up")
    if not up or _too_big([up]):
        return
    rot = st.segmented_control(t("Rotate"), [90, 180, 270], default=90, key="tl_ro_rot", format_func=lambda d: f"{d}°")
    out = _guard(tools.organize_pdf, up.getvalue(), "", rot or 90)
    if out:
        st.download_button(t("Download PDF"), out, f"{_stem(up.name)}-rotated.pdf", PDF_MIME,
                           type="primary", icon=":material/download:", key="tl_ro_dl")


def _split_tool():
    up = st.file_uploader(t("PDF"), type=["pdf"], key="tl_sp_up")
    if not up or _too_big([up]):
        return
    n = _guard(tools.page_count, up.getvalue())
    if not n:
        return
    every = st.number_input(t("Pages per file"), 1, max(n, 1), 1, key="tl_sp_n")
    parts = _guard(tools.split_pdf, up.getvalue(), every)
    if parts:
        st.caption(t("This makes {n} file(s), delivered as one zip.", n=len(parts)))
        base = _stem(up.name)
        z = _guard(tools.make_zip, [(f"{base}-{nm}", d) for nm, d in parts])
        if z:
            st.download_button(t("Download split pages (zip)"), z, f"{base}-split.zip", "application/zip",
                               type="primary", icon=":material/folder_zip:", key="tl_sp_dl")


# ---------- watermark ----------
def _wm_tool():
    up = st.file_uploader(t("PDF or image"), type=["pdf"] + IMG_TYPES, key="tl_wm_up")
    c1, c2 = st.columns([2, 1])
    text = c1.text_input(t("Watermark text"), "CONFIDENTIAL", max_chars=80, key="tl_wm_text")
    color = c2.color_picker(t("Colour"), "#888888", key="tl_wm_col")
    c3, c4, c5 = st.columns(3)
    opacity = c3.slider(t("Opacity"), 5, 100, 25, key="tl_wm_op") / 100
    size = c4.slider(t("Text size"), 16, 140, 60, key="tl_wm_sz")
    angle = c5.slider(t("Angle"), 0, 90, 45, key="tl_wm_an")
    tiled = st.toggle(t("Repeat across the page"), key="tl_wm_tile")
    if not up or _too_big([up]):
        return
    data, ext = up.getvalue(), up.name.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        out = _guard(tools.watermark_pdf, data, text, opacity, angle, size, tiled, color)
        if out:
            _preview_pdf(out, "tl_wm_pv")
            st.download_button(t("Download watermarked PDF"), out, f"{_stem(up.name)}-watermarked.pdf", PDF_MIME,
                               type="primary", icon=":material/download:", key="tl_wm_dl")
    else:
        out = _guard(tools.watermark_image, data, text, opacity, tiled)
        if out:
            st.image(out, use_container_width=True)
            st.download_button(t("Download watermarked image"), out, f"{_stem(up.name)}-watermarked.png", "image/png",
                               type="primary", icon=":material/download:", key="tl_wm_dl_i")


def _preview_pdf(data: bytes, key: str, page: int = 1):
    png = None
    try:
        png = tools.render_page(data, page)
    except tools.ToolError:
        pass
    if png:
        st.image(png, caption=t("Preview, page {n}", n=page), use_container_width=True)


# ---------- sign ----------
def _sign_tool():
    st.caption(t("For a legally binding e-signature with an audit trail, use a signing service."))
    up = st.file_uploader(t("PDF to sign"), type=["pdf"], key="tl_sg_up")
    how = st.segmented_control(t("Signature"), ["type", "upload"], default="type", key="tl_sg_how",
                               format_func=lambda k: {"type": t("Type it"), "upload": t("Upload a picture")}.get(k, k))
    sig = None
    if how == "upload":
        pic = st.file_uploader(t("A photo or scan of your signature on white paper"), type=IMG_TYPES, key="tl_sg_pic")
        if pic and not _too_big([pic]):
            sig = _guard(tools.signature_from_image, pic.getvalue())
    else:
        c1, c2, c3 = st.columns([3, 2, 1])
        name = c1.text_input(t("Your name"), st.session_state["user"]["display_name"] or "",
                             max_chars=60, key="tl_sg_name")
        style = c2.selectbox(t("Style"), list(tools.SIG_FONTS), key="tl_sg_style", format_func=t)
        ink = c3.color_picker(t("Ink"), "#12306b", key="tl_sg_ink")
        if name.strip():
            sig = _guard(tools.signature_typed, name, style, ink)
    if sig:
        st.image(tools.on_white(sig), width=220)
    if not up or _too_big([up]):
        return
    data = up.getvalue()
    n = _guard(tools.page_count, data)
    if not n:
        return
    if not sig:
        st.info(t("Create a signature above, then place it."))
        return
    page = int(st.number_input(t("Page"), 1, n, n, key="tl_sg_pg")) if n > 1 else 1
    png = _guard(tools.render_page, data, page, 1.6)
    if not png:
        return
    pos = sigplace.place(png, sig, key=f"tl_sg_place_{page}",
                         hint=t("Click the page to place your signature. Drag to move, pull the dot to resize."))
    out = _guard(tools.sign_pdf, data, sig, page, pos["x"], pos["y"], pos["w"])
    if out:
        st.download_button(t("Download signed PDF"), out, f"{_stem(up.name)}-signed.pdf", PDF_MIME, type="primary",
                           icon=":material/download:", key="tl_sg_dl")


# ---------- e-mail ----------
def _email_tool():
    u = st.session_state["user"]
    st.caption(t("Tell the AI what the e-mail is about and it drafts the subject and body. You send it from your own "
                 "mail app, so nothing is sent from here. Names, numbers and other personal details are masked before the AI sees them."))
    notes = st.text_area(t("What should the e-mail say?"), height=120, max_chars=4000, key="tl_em_notes",
                         placeholder=t("e.g. Ask opposing counsel to extend the filing deadline by two weeks because our expert is travelling."))
    c1, c2, c3 = st.columns([2, 1.3, 1.3])
    to = c1.text_input(t("To (name or address)"), key="tl_em_to")
    tone = c2.selectbox(t("Tone"), list(tools.TONES), key="tl_em_tone",
                        format_func=lambda k: {"formal": t("Formal"), "friendly": t("Friendly"), "firm": t("Firm"),
                                               "brief": t("Brief")}[k])
    lang = c3.selectbox(t("Write in"), ["English", "Bahasa Indonesia"], key="tl_em_lang",
                        index=1 if i18n.lang() == "id" else 0)
    docs = cases.list_accessible_documents(u["id"], "", None, "all")[:50]
    pick = st.selectbox(t("Attach context from a file (optional)"), [None] + [d["id"] for d in docs], key="tl_em_doc",
                        format_func=lambda i: t("None") if i is None else next(d["filename"] for d in docs if d["id"] == i))
    if st.button(t("Draft e-mail"), type="primary", icon=":material/auto_awesome:", key="tl_em_go",
                 disabled=not notes.strip() and not pick):
        text = ""
        if pick:
            d = cases.get_document(u["id"], pick)
            text = d["text"] if d else ""
        with st.spinner(t("Drafting…")):
            subj, body, err = tools.draft_email(u, notes, to, tone, lang, text)
        if err:
            st.error(i18n.tm(err))
        else:
            st.session_state["tl_em_out"] = {"subject": subj, "body": body}
            st.session_state["tl_em_subj"], st.session_state["tl_em_body"] = subj, body
    if "tl_em_out" in st.session_state:
        subj = st.text_input(t("Subject"), key="tl_em_subj")
        body = st.text_area(t("Body"), height=300, key="tl_em_body")
        st.caption(t("AI-generated. Read it and fill in anything in [brackets] before sending."))
        a, b, c = st.columns(3)
        a.link_button(t("Open in mail app"), tools.mailto(to, subj, body), icon=":material/mail:",
                      use_container_width=True)
        b.link_button(t("Open in Gmail"), tools.gmail_link(to, subj, body), icon=":material/open_in_new:",
                      use_container_width=True)
        c.download_button(t("Download .txt"), f"Subject: {subj}\n\n{body}".encode("utf-8"), "email-draft.txt",
                          "text/plain", icon=":material/download:", use_container_width=True, key="tl_em_dl")


# ---------- more PDF tools ----------
def _img_to_pdf_tool():
    ups = st.file_uploader(t("Images, in page order"), type=IMG_TYPES, accept_multiple_files=True, key="tl_i2p_up")
    c1, c2 = st.columns(2)
    page = c1.segmented_control(t("Page size"), ["fit", "a4"], default="fit", key="tl_i2p_pg",
                                format_func=lambda k: {"fit": t("Same as image"), "a4": "A4"}.get(k, k))
    margin = c2.slider(t("Margin"), 0, 60, 24, key="tl_i2p_m", disabled=page != "a4")
    if not ups or _too_big(ups):
        return
    out = _guard(tools.images_to_pdf, [f.getvalue() for f in ups], page or "fit", margin)
    if out:
        st.download_button(t("Download PDF"), out, "images.pdf", PDF_MIME, type="primary",
                           icon=":material/download:", key="tl_i2p_dl")


def _pdf_to_img_tool():
    up = st.file_uploader(t("PDF"), type=["pdf"], key="tl_p2i_up")
    c1, c2, c3 = st.columns(3)
    fmt = c1.segmented_control(t("Format"), ["jpg", "png"], default="jpg", key="tl_p2i_f", format_func=str.upper)
    dpi = c2.select_slider(t("Quality"), [72, 100, 130, 200, 300], 130, key="tl_p2i_d", format_func=lambda d: f"{d} dpi")
    spec = c3.text_input(t("Pages (optional)"), placeholder="1-3, 5", key="tl_p2i_s")
    if not up or _too_big([up]):
        return
    imgs = _guard(tools.pdf_to_images, up.getvalue(), fmt or "jpg", dpi, spec)
    if imgs:
        base = _stem(up.name)
        if len(imgs) == 1:
            nm, d = imgs[0]
            st.image(d, use_container_width=True)
            st.download_button(t("Download image"), d, f"{base}-{nm}", f"image/{'png' if nm.endswith('png') else 'jpeg'}",
                               type="primary", icon=":material/download:", key="tl_p2i_dl1")
            return
        z = _guard(tools.make_zip, [(f"{base}-{nm}", d) for nm, d in imgs])
        if z:
            st.caption(t("{n} images, delivered as one zip.", n=len(imgs)))
            st.download_button(t("Download images (zip)"), z, f"{base}-images.zip", "application/zip", type="primary",
                               icon=":material/folder_zip:", key="tl_p2i_dl")


def _protect_tool():
    up = st.file_uploader(t("PDF"), type=["pdf"], key="tl_pr_up")
    pw = st.text_input(t("Password"), type="password", key="tl_pr_pw", help=t("At least 6 characters. If you lose it, nobody can recover the file."))
    if not up or _too_big([up]) or not pw:
        return
    out = _guard(tools.protect_pdf, up.getvalue(), pw)
    if out:
        st.download_button(t("Download protected PDF"), out, f"{_stem(up.name)}-protected.pdf", PDF_MIME, type="primary",
                           icon=":material/lock:", key="tl_pr_dl")


def _unlock_tool():
    st.caption(t("You need the password. This removes it so the PDF opens freely."))
    up = st.file_uploader(t("Password-protected PDF"), type=["pdf"], key="tl_un_up")
    pw = st.text_input(t("Password"), type="password", key="tl_un_pw")
    if not up or _too_big([up]):
        return
    out = _guard(tools.unlock_pdf, up.getvalue(), pw)
    if out:
        st.download_button(t("Download unlocked PDF"), out, f"{_stem(up.name)}-unlocked.pdf", PDF_MIME, type="primary",
                           icon=":material/lock_open:", key="tl_un_dl")


def _numbers_tool():
    up = st.file_uploader(t("PDF"), type=["pdf"], key="tl_pn_up")
    c1, c2, c3 = st.columns(3)
    pos = c1.selectbox(t("Position"), tools.POSITIONS, key="tl_pn_pos", format_func=lambda p: t(p.replace("-", " ").capitalize()))
    style = c2.selectbox(t("Style"), ["n", "page", "of"], key="tl_pn_st",
                         format_func=lambda k: {"n": "3", "page": t("Page 3"), "of": t("Page 3 of 12")}[k])
    start = c3.number_input(t("Start at"), 1, 9999, 1, key="tl_pn_start")
    skip = st.toggle(t("Don't number the first page"), key="tl_pn_skip")
    if not up or _too_big([up]):
        return
    out = _guard(tools.number_pages, up.getvalue(), pos, int(start), style, 10, skip)
    if out:
        _preview_pdf(out, "tl_pn_pv", 1)
        st.download_button(t("Download numbered PDF"), out, f"{_stem(up.name)}-numbered.pdf", PDF_MIME, type="primary",
                           icon=":material/download:", key="tl_pn_dl")


def _crop_tool():
    up = st.file_uploader(t("PDF"), type=["pdf"], key="tl_cr_up")
    c1, c2, c3, c4 = st.columns(4)
    top = c1.slider(t("Top (%)"), 0, 45, 0, key="tl_cr_t")
    bottom = c2.slider(t("Bottom (%)"), 0, 45, 0, key="tl_cr_b")
    left = c3.slider(t("Left (%)"), 0, 45, 0, key="tl_cr_l")
    right = c4.slider(t("Right (%)"), 0, 45, 0, key="tl_cr_r")
    if not up or _too_big([up]):
        return
    out = _guard(tools.crop_pdf, up.getvalue(), left, top, right, bottom)
    if out:
        _preview_pdf(out, "tl_cr_pv", 1)
        st.download_button(t("Download cropped PDF"), out, f"{_stem(up.name)}-cropped.pdf", PDF_MIME, type="primary",
                           icon=":material/download:", key="tl_cr_dl")


def _compress_tool():
    up = st.file_uploader(t("PDF"), type=["pdf"], key="tl_cp_up")
    level = st.segmented_control(t("Compression"), ["light", "balanced", "strong"], default="balanced", key="tl_cp_lv",
                                 format_func=lambda k: {"light": t("Light"), "balanced": t("Balanced"), "strong": t("Strong")}.get(k, k))
    if not up or _too_big([up]):
        return
    data = up.getvalue()
    out = _guard(tools.compress_pdf, data, level or "balanced")
    if out:
        saved = 100 - round(len(out) * 100 / len(data))
        st.caption(t("{a} KB to {b} KB ({p}% smaller)", a=f"{len(data) // 1024:,}", b=f"{len(out) // 1024:,}", p=saved)
                   if saved > 0 else t("This PDF is already as small as this tool can make it."))
        st.download_button(t("Download compressed PDF"), out, f"{_stem(up.name)}-compressed.pdf", PDF_MIME, type="primary",
                           icon=":material/download:", key="tl_cp_dl")


def _edit_tool():
    st.caption(t("Whiteout covers what is underneath; it does not remove the text. For sensitive data, redact instead."))
    up = st.file_uploader(t("PDF to edit"), type=["pdf"], key="tl_ed_up")
    if not up or _too_big([up]):
        return
    data = up.getvalue()
    n = _guard(tools.page_count, data)
    if not n:
        return
    file_id = f"{up.name}:{up.size}"
    if st.session_state.get("tl_ed_file") != file_id:   # a new file starts with a clean slate
        st.session_state["tl_ed_file"], st.session_state["tl_ed_items"] = file_id, {}
    store = st.session_state["tl_ed_items"]
    page = int(st.number_input(t("Page"), 1, n, 1, key="tl_ed_pg")) if n > 1 else 1
    png = _guard(tools.render_page, data, page, 1.6)
    if not png:
        return
    store[page] = pdfedit.edit(png, store.get(page, []), key=f"tl_ed_{file_id}_{page}",
                               hint=t("Pick a tool, then click or drag on the page. Drag to move, pull the dot to resize."))
    marked = sorted(p for p, v in store.items() if v)
    if marked:
        st.caption(t("Edits on page(s): {pages}", pages=", ".join(map(str, marked))))
    out = None
    if marked:
        out = _guard(tools.edit_pdf, data, store)
    if out:
        st.download_button(t("Download edited PDF"), out, f"{_stem(up.name)}-edited.pdf", PDF_MIME, type="primary",
                           icon=":material/download:", key="tl_ed_dl")


def _image_editor_tool():
    up = st.file_uploader(t("Image"), type=IMG_TYPES + ["webp"], key="tl_im_up")
    if not up or _too_big([up]):
        return
    c1, c2, c3 = st.columns(3)
    rot = c1.segmented_control(t("Rotate"), [0, 90, 180, 270], default=0, key="tl_im_rot", format_func=lambda d: f"{d}°")
    flips = c2.pills(t("Flip"), ["h", "v"], selection_mode="multi", key="tl_im_flip",
                     format_func=lambda k: {"h": t("Left-right"), "v": t("Up-down")}[k])
    fmt = c3.segmented_control(t("Save as"), ["png", "jpg", "webp"], default="png", key="tl_im_fmt", format_func=str.upper)
    with st.expander(t("Crop and resize"), icon=":material/crop:"):
        k1, k2, k3, k4 = st.columns(4)
        top = k1.slider(t("Top (%)"), 0, 45, 0, key="tl_im_t")
        bottom = k2.slider(t("Bottom (%)"), 0, 45, 0, key="tl_im_b")
        left = k3.slider(t("Left (%)"), 0, 45, 0, key="tl_im_l")
        right = k4.slider(t("Right (%)"), 0, 45, 0, key="tl_im_r")
        resize = st.toggle(t("Set the width (pixels)"), key="tl_im_rs")
        width = st.number_input(t("Width"), 16, tools.MAX_SIDE, 1200, step=50, key="tl_im_w", disabled=not resize)
    with st.expander(t("Adjust"), icon=":material/tune:"):
        a1, a2, a3 = st.columns(3)
        br = a1.slider(t("Brightness"), 0.2, 2.0, 1.0, 0.05, key="tl_im_br")
        co = a2.slider(t("Contrast"), 0.2, 2.0, 1.0, 0.05, key="tl_im_co")
        sa = a3.slider(t("Colour"), 0.0, 2.0, 1.0, 0.05, key="tl_im_sa")
        gray = st.toggle(t("Black and white"), key="tl_im_gray")
    out = _guard(tools.edit_image, up.getvalue(), rot or 0, "h" in (flips or []), "v" in (flips or []),
                 (left, top, right, bottom), int(width) if resize else None, br, co, sa, gray, fmt or "png")
    if out:
        st.image(out, use_container_width=True)
        f = fmt or "png"
        st.download_button(t("Download image"), out, f"{_stem(up.name)}-edited.{f}", tools.IMG_FORMATS[f][1],
                           type="primary", icon=":material/download:", key="tl_im_dl")


def _bg_tool():
    up = st.file_uploader(t("Image"), type=IMG_TYPES + ["webp"], key="tl_bg_up")
    smart = tools.smart_remover_available()
    modes = ["solid"] + (["smart"] if smart else [])
    mode = st.segmented_control(t("Method"), modes, default="solid", key="tl_bg_mode",
                                format_func=lambda m: {"solid": t("Plain background"), "smart": t("Smart (AI)")}.get(m, m))
    if not smart:
        st.caption(t("Works best on a plain background (white paper, studio backdrop). For busy photos the smart AI method "
                     "is available once an administrator installs it (pip install rembg onnxruntime)."))
    tol = st.slider(t("Tolerance"), 1, 100, 30, key="tl_bg_tol", disabled=mode == "smart",
                    help=t("Higher removes more colours that are close to the background."))
    soft = st.slider(t("Edge softness"), 0, 4, 1, key="tl_bg_soft", disabled=mode == "smart")
    if not up or _too_big([up]):
        return
    out = _guard(tools.remove_background, up.getvalue(), mode or "solid", tol, soft)
    if out:
        st.image(tools.on_checkerboard(out), caption=t("Preview (the checkerboard is transparent)"),
                 use_container_width=True)
        st.download_button(t("Download PNG"), out, f"{_stem(up.name)}-no-background.png", "image/png", type="primary",
                           icon=":material/download:", key="tl_bg_dl")


# (key, material icon, tile colour, title, description, function). function=None means "coming soon".
TOOLS = [
    ("merge", "call_merge", "#d9532f", "Merge PDF", "Combine PDFs in the order you want.", _merge_tool),
    ("split", "call_split", "#e0702f", "Split PDF", "Separate a PDF into single pages or equal parts.", _split_tool),
    ("organize", "swap_vert", "#c2476e", "Organize PDF", "Sort, delete or pull out pages, in any order.", _organize_tool),
    ("rotate", "rotate_right", "#a8579c", "Rotate PDF", "Turn every page the way you need it.", _rotate_tool),
    ("watermark", "approval", "#b0589c", "Watermark", "Stamp text over a PDF or image. Choose colour, opacity and position.", _wm_tool),
    ("sign", "draw", "#4b87c9", "Sign PDF", "Place your signature: click the page, drag it, resize it.", _sign_tool),
    ("zip", "folder_zip", "#6aa84f", "Zip files", "Put a bunch of files in, get one zip out.", _zip_tool),
    ("email", "mail", "#7a5af5", "E-mail draft", "AI writes the subject and body, you send it from your own mail app.", _email_tool),
    ("compress", "compress", "#7aa63a", "Compress PDF", "Reduce file size while keeping quality.", _compress_tool),
    ("img2pdf", "image", "#d4a72c", "JPG to PDF", "Turn photos and scans into one PDF.", _img_to_pdf_tool),
    ("pdf2img", "photo_library", "#c9a227", "PDF to JPG", "Save each page as an image.", _pdf_to_img_tool),
    ("numbers", "format_list_numbered", "#a8579c", "Page numbers", "Add page numbers: position, style, start.", _numbers_tool),
    ("crop", "crop", "#c2476e", "Crop PDF", "Trim the margins of every page.", _crop_tool),
    ("protect", "shield_lock", "#4b87c9", "Protect PDF", "Lock a PDF with a password (AES-256).", _protect_tool),
    ("unlock", "lock_open", "#4b87c9", "Unlock PDF", "Remove a password you know from a PDF.", _unlock_tool),
    ("topword", "description", "#3f6fc7", "PDF to Word", "Turn a PDF into an editable document.", None),
    ("edit", "edit_document", "#b0589c", "Edit PDF", "Add text, boxes, highlights and whiteouts on the page itself.", _edit_tool),
    ("bg", "background_replace", "#2f9e8f", "Background remover", "Cut the background out of a photo.", _bg_tool),
    ("image", "tune", "#8a6fd6", "Image editor", "Crop, rotate, resize and adjust images.", _image_editor_tool),
    ("transcribe", "mic", "#5a6fd6", "Transcribe audio", "Speech to text. Video subtitles later.", None),
]
_CSS = """<style>
[class*="st-key-toolcard_"]{ position:relative; min-height:11.5rem; transition:transform .12s ease, box-shadow .12s ease; }
[class*="st-key-toolcard_"] [data-testid="stElementContainer"]:has(.stButton){ position:absolute !important; inset:0; width:100% !important; height:100% !important; z-index:3; margin:0; }
[class*="st-key-toolcard_"] .stButton, [class*="st-key-toolcard_"] .stButton button{ width:100% !important; height:100% !important; }
[class*="st-key-toolcard_"] .stButton button{ opacity:0; cursor:pointer; }
[class*="st-key-toolcard_"]:has(.stButton button:not(:disabled)):hover{ transform:translateY(-2px); }
[class*="st-key-toolcard_"]:has(.stButton button:not(:disabled)):hover [data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-toolcard_"]:has(.stButton button:not(:disabled)):hover{ border-color: var(--lv-accent) !important; }
[class*="st-key-toolcard_"]:has(.stButton button:disabled){ opacity:.55; }
[class*="st-key-toolcard_"] .stButton button:disabled{ cursor:default; }
.lv-tool-ico{ width:46px; height:46px; border-radius:11px; display:flex; align-items:center; justify-content:center; margin-bottom:.9rem; }
.lv-tool-ico span{ font-family:"Material Symbols Rounded"; font-size:27px; color:#fff; font-feature-settings:"liga"; line-height:1; }
.lv-tool-t{ font-family:'Newsreader',Georgia,serif; font-size:1.3rem; font-weight:500; color:var(--lv-text); margin-bottom:.35rem; }
.lv-tool-d{ font-size:.9rem; color:var(--lv-muted); line-height:1.45; }
.lv-tool-soon{ position:absolute; top:-.2rem; right:0; font-size:.72rem; font-weight:600; padding:.12rem .55rem; border-radius:999px;
  background: var(--lv-pill); color: var(--lv-muted); }
</style>"""


def _pick(key: str):
    st.session_state["tool"] = key


def _grid():
    st.markdown(_CSS, unsafe_allow_html=True)
    for row in range(0, len(TOOLS), 4):
        cols = st.columns(4)
        for col, (key, icon, color, title, desc, fn) in zip(cols, TOOLS[row:row + 4]):
            with col, st.container(key=f"toolcard_{key}", border=True):
                soon = '' if fn else f'<span class="lv-tool-soon">{ui.esc(t("Soon"))}</span>'
                ui.html_block(f'''<div style="position:relative">{soon}
                    <div class="lv-tool-ico" style="background:{color}"><span>{icon}</span></div>
                    <div class="lv-tool-t">{ui.esc(t(title))}</div>
                    <div class="lv-tool-d">{ui.esc(t(desc))}</div></div>''')
                st.button(t(title), key=f"toolbtn_{key}", disabled=fn is None, on_click=_pick, args=(key,))


def render():
    ui.page_header("Tools", "Everyday utilities for documents: zip, merge, watermark, sign and draft e-mails.",
                   eyebrow="Workspace")
    cur = st.session_state.get("tool")
    entry = next((x for x in TOOLS if x[0] == cur and x[5]), None)
    if not entry:
        _grid()
        return
    key, icon, color, title, desc, fn = entry
    if st.button(t("All tools"), icon=":material/arrow_back:", key="tool_back"):
        st.session_state.pop("tool", None)
        st.rerun()
    st.markdown(f"### {t(title)}")
    st.caption(t(desc))
    fn()
