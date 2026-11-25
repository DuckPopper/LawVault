"""Export text (plain or the light Markdown the AI writes) as Word (.docx) or PDF. No network, no temp files."""
from __future__ import annotations
import io, re
from xml.sax.saxutils import escape

_BOLD = re.compile(r"(\*\*[^*]+\*\*)")


def parse_blocks(md: str, plain: bool = False):
    """Markdown-lite -> [(kind, text)] with kind in h1/h2/h3/bullet/p.
    plain=True keeps a document's own line structure (every non-empty line is a paragraph, no Markdown)."""
    if plain:
        return [("p", ln.strip().replace("**", "")) for ln in (md or "").replace("\r\n", "\n").split("\n") if ln.strip()]
    blocks, para = [], []

    def flush():
        if para:
            blocks.append(("p", " ".join(para)))
            para.clear()
    for raw in (md or "").replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        b = re.match(r"^\s*[-*•]\s+(.*)$", line)
        if m:
            flush(); blocks.append((f"h{len(m.group(1))}", m.group(2).strip()))
        elif b:
            flush(); blocks.append(("bullet", b.group(1).strip()))
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
    flush()
    return blocks


def to_docx(title: str, body: str, footer: str = "", plain: bool = False) -> bytes:
    from docx import Document
    from docx.shared import Pt
    d = Document()
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(11)
    d.core_properties.title = title[:200]
    d.add_heading(title, level=0)
    for kind, text in parse_blocks(body, plain):
        if kind in ("h1", "h2", "h3"):
            d.add_heading(text.replace("**", ""), level=int(kind[1]))
            continue
        p = d.add_paragraph(style="List Bullet" if kind == "bullet" else None)
        for part in _BOLD.split(text):
            if part.startswith("**") and part.endswith("**") and len(part) > 4:
                p.add_run(part[2:-2]).bold = True
            elif part:
                p.add_run(part)
    if footer:
        d.add_paragraph().add_run(footer).italic = True
    out = io.BytesIO()
    d.save(out)
    return out.getvalue()


def _latin(s: str) -> str:
    """Built-in PDF fonts use WinAnsi (cp1252): keep what it can show, replace the rest."""
    return s.encode("cp1252", errors="replace").decode("cp1252")


def to_pdf(title: str, body: str, footer: str = "", plain: bool = False) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer
    ss = getSampleStyleSheet()
    body_s = ParagraphStyle("b", parent=ss["BodyText"], fontSize=10.5, leading=15, spaceAfter=6)
    heads = {"h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=16, spaceBefore=10),
             "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13.5, spaceBefore=8),
             "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontSize=11.5, spaceBefore=8)}

    def rich(text: str) -> str:
        return "".join(f"<b>{escape(_latin(p[2:-2]))}</b>" if p.startswith("**") and p.endswith("**") and len(p) > 4
                       else escape(_latin(p)) for p in _BOLD.split(text))

    story, bullets = [Paragraph(escape(_latin(title)), ParagraphStyle("t", parent=ss["Title"], fontSize=20)),
                      Spacer(1, 6)], []

    def flush():
        if bullets:
            story.append(ListFlowable([ListItem(Paragraph(rich(b), body_s)) for b in bullets], bulletType="bullet",
                                      start="•", leftIndent=14))
            bullets.clear()
    for kind, text in parse_blocks(body, plain):
        if kind == "bullet":
            bullets.append(text)
            continue
        flush()
        story.append(Paragraph(rich(text.replace("**", "")) if kind in heads else rich(text),
                               heads.get(kind, body_s)))
    flush()
    if footer:
        story.append(Paragraph(f"<i>{escape(_latin(footer))}</i>", body_s))

    def page_no(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{doc.page}")
    out = io.BytesIO()
    SimpleDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                      bottomMargin=18 * mm, title=title[:200]).build(story, onFirstPage=page_no, onLaterPages=page_no)
    return out.getvalue()
