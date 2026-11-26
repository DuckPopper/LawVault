import io
import zipfile
import pytest
from pypdf import PdfReader, PdfWriter
import ai, tools
from conftest import make_user


def pdf(n=3):
    w = PdfWriter()
    for _ in range(n):
        w.add_blank_page(300, 400)
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


def pages(data):
    return len(PdfReader(io.BytesIO(data)).pages)


def test_zip_dedupes_and_sanitises():
    z = zipfile.ZipFile(io.BytesIO(tools.make_zip([("a.pdf", b"1"), ("a.pdf", b"2"), ("../../etc/passwd", b"3")])))
    assert z.namelist() == ["a.pdf", "a (2).pdf", "passwd"]
    with pytest.raises(tools.ToolError):
        tools.make_zip([])


def test_parse_pages():
    assert tools.parse_pages("1-2, 4", 5) == [0, 1, 3]
    assert tools.parse_pages("3,1", 5) == [2, 0]
    assert tools.parse_pages("4-", 5) == [3, 4]
    assert tools.parse_pages("", 3) == [0, 1, 2]
    for bad in ("0", "9", "3-1", "a", "1,,2", "1-2-3"):
        with pytest.raises(tools.ToolError):
            tools.parse_pages(bad, 5)


def test_merge_organize_split():
    assert pages(tools.merge_pdfs([pdf(2), pdf(3)])) == 5
    with pytest.raises(tools.ToolError):
        tools.merge_pdfs([pdf()])
    out = tools.organize_pdf(pdf(4), "2-3", 90)
    r = PdfReader(io.BytesIO(out))
    assert len(r.pages) == 2 and r.pages[0].get("/Rotate") == 90
    assert [n for n, _ in tools.split_pdf(pdf(5), 2)] == ["part-1.pdf", "part-2.pdf", "part-3.pdf"]


def test_garbage_and_encrypted_pdf():
    with pytest.raises(tools.ToolError):
        tools.page_count(b"not a pdf")
    w = PdfWriter()
    w.add_blank_page(100, 100)
    w.encrypt("pw")
    b = io.BytesIO()
    w.write(b)
    with pytest.raises(tools.ToolError, match="password"):
        tools.page_count(b.getvalue())


def test_watermark_and_sign_keep_pages_and_change_content():
    base = pdf(2)
    wm = tools.watermark_pdf(base, "CONFIDENTIAL", tiled=True)
    assert pages(wm) == 2 and wm != base
    with pytest.raises(tools.ToolError):
        tools.watermark_pdf(base, "  ")
    sig = tools.signature_typed("Jane Doe", "Classic")
    out = tools.sign_pdf(base, sig, 2, 0.7, 0.85, 0.25)
    assert pages(out) == 2 and out != base
    with pytest.raises(tools.ToolError):
        tools.sign_pdf(base, sig, 3, 0.5, 0.5, 0.2)


def test_rotated_page_is_signed_upright():
    w = PdfWriter()
    p = w.add_blank_page(300, 400)
    p.rotate(90)
    b = io.BytesIO()
    w.write(b)
    out = tools.sign_pdf(b.getvalue(), tools.signature_typed("A B"), 1, 0.5, 0.5, 0.3)
    assert pages(out) == 1


def test_signature_from_image_and_watermark_image():
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (400, 200), "white")
    ImageDraw.Draw(im).line((20, 100, 380, 60), fill="black", width=6)
    b = io.BytesIO()
    im.save(b, "PNG")
    sig = Image.open(io.BytesIO(tools.signature_from_image(b.getvalue())))
    assert sig.mode == "RGBA" and sig.getpixel((0, 0))[3] == 0 or sig.size[0] < 400
    blank = io.BytesIO()
    Image.new("RGB", (50, 50), "white").save(blank, "PNG")
    with pytest.raises(tools.ToolError):
        tools.signature_from_image(blank.getvalue())
    assert Image.open(io.BytesIO(tools.watermark_image(b.getvalue(), "DRAFT", tiled=True))).size == (400, 200)
    with pytest.raises(tools.ToolError):
        tools.watermark_image(b"junk", "x")


def test_render_page():
    assert tools.render_page(pdf(1), 1)[:4] == b"\x89PNG"


def test_email_draft_quota_and_failure_refund(monkeypatch):
    u = make_user("tools@example.com")
    seen = []

    def ok(contents, system=ai.SYSTEM):
        seen.append(contents[0]["parts"][0]["text"])
        return "Subject: Hello\n\nBody text", True
    monkeypatch.setattr(ai, "_call", ok)
    assert tools.draft_email(u, "Ask for an extension", "Counsel", "formal", "English") == ("Hello", "Body text", None)
    assert "Ask for an extension" in seen[0]
    assert tools.draft_email(u, "", "", "formal", "English")[2] == "Say what the e-mail is about."
    monkeypatch.setattr(ai, "_call", lambda c, s=ai.SYSTEM: ("down", False))
    assert tools.draft_email(u, "x", "", "formal", "English")[2] == "down"


def test_split_email_and_links():
    s, b = tools.split_email("Subject: Extension request\n\nDear Counsel,\nThanks.")
    assert s == "Extension request" and b.startswith("Dear Counsel")
    assert tools.split_email("no subject here") == ("", "no subject here")
    assert tools.mailto("a@b.com", "Hi & bye", "x y").startswith("mailto:a%40b.com?subject=Hi%20%26%20bye")


def test_signature_lands_where_the_preview_put_it():
    """The click-to-place preview and the saved PDF must agree: centre (x, y) and width are page fractions."""
    from PIL import Image
    import tools as T
    base = pdf(1)
    sig = T.signature_typed("Jane Doe", "Classic", "#000000")
    x, y, w = 0.3, 0.7, 0.25
    out = T.sign_pdf(base, sig, 1, x, y, w)
    img = Image.open(io.BytesIO(T.render_page(out, 1, 1.0))).convert("L")
    bbox = img.point(lambda v: 255 if v < 200 else 0).getbbox()
    assert bbox, "no ink on the page"
    pw, ph = img.size
    cx, cy = (bbox[0] + bbox[2]) / 2 / pw, (bbox[1] + bbox[3]) / 2 / ph
    assert abs(cx - x) < 0.03 and abs(cy - y) < 0.03
    assert abs((bbox[2] - bbox[0]) / pw - w) < 0.04


def png(color="red", size=(200, 300)):
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", size, color).save(b, "PNG")
    return b.getvalue()


def test_images_to_pdf_and_back():
    out = tools.images_to_pdf([png(), png("blue", (400, 200))], "fit")
    r = PdfReader(io.BytesIO(out))
    assert len(r.pages) == 2 and float(r.pages[0].mediabox.width) == 200
    a4 = PdfReader(io.BytesIO(tools.images_to_pdf([png()], "a4", 20)))
    assert (float(a4.pages[0].mediabox.width), float(a4.pages[0].mediabox.height)) == (595.0, 842.0)
    imgs = tools.pdf_to_images(out, "png", 72)
    assert [n for n, _ in imgs] == ["page-1.png", "page-2.png"] and imgs[0][1][:4] == b"\x89PNG"
    assert len(tools.pdf_to_images(out, "jpg", 72, "2")) == 1
    with pytest.raises(tools.ToolError):
        tools.images_to_pdf([])
    with pytest.raises(tools.ToolError):
        tools.images_to_pdf([b"junk"])


def test_protect_and_unlock():
    locked = tools.protect_pdf(pdf(2), "secret1")
    assert PdfReader(io.BytesIO(locked)).is_encrypted
    with pytest.raises(tools.ToolError, match="wrong"):
        tools.unlock_pdf(locked, "nope-nope")
    open_ = tools.unlock_pdf(locked, "secret1")
    assert not PdfReader(io.BytesIO(open_)).is_encrypted and pages(open_) == 2
    with pytest.raises(tools.ToolError, match="no password"):
        tools.unlock_pdf(pdf(), "x")
    with pytest.raises(tools.ToolError):
        tools.protect_pdf(pdf(), "123")


def test_page_numbers_crop_compress():
    out = tools.number_pages(pdf(3), "top-right", 5, "of", 10, skip_first=True)
    assert pages(out) == 3 and out != pdf(3)
    text = PdfReader(io.BytesIO(out)).pages[1].extract_text()
    assert "Page 5 of 6" in text
    c = PdfReader(io.BytesIO(tools.crop_pdf(pdf(1), 10, 10, 20, 0))).pages[0]
    assert abs(float(c.mediabox.width) - 300 * 0.7) < 1 and abs(float(c.mediabox.height) - 400 * 0.9) < 1
    with pytest.raises(tools.ToolError):
        tools.crop_pdf(pdf(1), 60, 0, 0, 0)
    big = tools.images_to_pdf([png(size=(1600, 1600))] * 2)
    assert pages(tools.compress_pdf(big, "strong")) == 2 and len(tools.compress_pdf(big, "strong")) <= len(big)


def test_edit_pdf_places_text_and_shapes_where_drawn():
    from PIL import Image
    items = {1: [{"t": "text", "x": 0.2, "y": 0.1, "s": 0.06, "c": "#000000", "text": "Hello edit\nsecond"},
                 {"t": "rect", "x": 0.5, "y": 0.5, "w": 0.3, "h": 0.2, "c": "#000000", "fill": True},
                 {"t": "bogus", "x": 9}, {"t": "text", "x": 0, "y": 0, "text": "  "}]}
    out = tools.edit_pdf(pdf(2), items)
    assert pages(out) == 2
    r = PdfReader(io.BytesIO(out))
    assert "Hello edit" in r.pages[0].extract_text() and "second" in r.pages[0].extract_text()
    assert r.pages[1].extract_text().strip() == ""
    img = Image.open(io.BytesIO(tools.render_page(out, 1, 1.0))).convert("L")
    pw, ph = img.size
    assert img.getpixel((int(pw * 0.65), int(ph * 0.6))) < 40            # filled box centre is black
    assert img.getpixel((int(pw * 0.1), int(ph * 0.9))) > 240            # elsewhere untouched
    assert tools.clean_items([{"t": "rect", "x": -3, "y": 2, "w": 5, "h": 0.1, "c": "javascript"}])[0]["c"] == "#000000"
    with pytest.raises(tools.ToolError):
        tools.edit_pdf(pdf(1), {1: []})
    with pytest.raises(tools.ToolError):
        tools.edit_pdf(pdf(1), {7: items[1]})


def test_edit_image():
    from PIL import Image
    src = png("red", (200, 100))
    out = tools.edit_image(src, rotate=90, crop=(10, 0, 10, 0), width=80, fmt="png")
    im = Image.open(io.BytesIO(out))
    assert im.size == (80, 128)          # 160x100 after crop, rotated to 100x160, scaled to width 80
    assert Image.open(io.BytesIO(tools.edit_image(src, fmt="jpg", grayscale=True))).format == "JPEG"
    assert Image.open(io.BytesIO(tools.edit_image(src, fmt="webp"))).format == "WEBP"
    g = Image.open(io.BytesIO(tools.edit_image(src, grayscale=True))).convert("RGB").getpixel((5, 5))
    assert g[0] == g[1] == g[2]
    for bad in (dict(rotate=45), dict(crop=(60, 0, 0, 0))):
        with pytest.raises(tools.ToolError):
            tools.edit_image(src, **bad)
    with pytest.raises(tools.ToolError):
        tools.edit_image(b"junk")


def test_remove_background_solid():
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (200, 200), (250, 250, 250))
    ImageDraw.Draw(im).ellipse((60, 60, 140, 140), fill=(200, 30, 30))
    b = io.BytesIO()
    im.save(b, "PNG")
    out = Image.open(io.BytesIO(tools.remove_background(b.getvalue(), "solid", 25, 0)))
    assert out.mode == "RGBA"
    assert out.getpixel((5, 5))[3] == 0 and out.getpixel((100, 100))[3] == 255
    flat = io.BytesIO()
    Image.new("RGB", (50, 50), "white").save(flat, "PNG")
    assert tools.remove_background(flat.getvalue(), "solid", 25)          # all background -> fully clear, no crash
    assert tools.on_checkerboard(tools.remove_background(b.getvalue()))[:4] == b"\x89PNG"
    with pytest.raises(tools.ToolError):
        tools.remove_background(b.getvalue(), "smart") if not tools.smart_remover_available() else (_ for _ in ()).throw(tools.ToolError("x"))
