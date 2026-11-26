"""Builds demo-files/: one ready-to-use sample per Tools card. Run: .venv/bin/python make_demo_files.py"""
from pathlib import Path
import io, random
import fitz
from PIL import Image, ImageDraw, ImageFilter
import tools

OUT = Path.home() / "Desktop" / "LawVault demo files"
OUT.mkdir(exist_ok=True)

LEASE = [
    ("COMMERCIAL LEASE AGREEMENT", ["Between PT Sentosa Abadi (Landlord) and PT Maju Logistik (Tenant).",
        "1. Premises. Warehouse Unit 7, Jl. Industri Raya 12, Jakarta Utara, 2,400 m2.",
        "2. Term. Five (5) years from 1 January 2025 to 31 December 2029.",
        "3. Rent. IDR 85,000,000 per month, payable on the 1st, in advance."]),
    ("PAYMENT AND DEFAULT", ["4. Late payment. Interest of 0.1% per day applies after a 7-day grace period.",
        "5. Default. Non-payment for 30 days entitles the Landlord to give notice of termination.",
        "6. Security deposit. IDR 255,000,000, refundable within 30 days of handover in good condition.",
        "7. Indemnity. The Tenant indemnifies the Landlord against third-party claims from its operations."]),
    ("TERMINATION AND DISPUTES", ["8. Early termination. The Tenant may terminate with 6 months' written notice and a fee of 3 months' rent.",
        "9. Force majeure. Neither party is liable for delays beyond reasonable control, with prompt notice.",
        "10. Governing law. The laws of the Republic of Indonesia.",
        "11. Disputes. First mediation; failing that, BANI arbitration in Jakarta."]),
]
ADDENDUM = [("ADDENDUM NO. 1", ["The parties agree to amend clause 3 of the Lease:",
        "Rent is reduced to IDR 78,000,000 per month for the period 1 July 2025 to 30 June 2026,",
        "in exchange for the Tenant paying twelve months' rent upfront.", "All other terms remain unchanged."])]
SETTLE = [("SETTLEMENT AGREEMENT", ["The parties settle all claims arising from the Lease dated 1 January 2025.",
        "The Tenant shall pay IDR 120,000,000 within 14 days of signing.",
        "The Landlord releases the Tenant from further liability for the period before this date.",
        "", "", "Signed for the Tenant:  ________________________        Date: ______________"])]


def make_pdf(pages, footer=""):
    doc = fitz.open()
    for title, lines in pages:
        p = doc.new_page()
        p.insert_text((72, 90), title, fontsize=18, fontname="hebo")
        y = 135
        for ln in lines:
            p.insert_textbox(fitz.Rect(72, y, 523, y + 60), ln, fontsize=11.5, fontname="helv")
            y += 52 if len(ln) > 85 else 34
        if footer:
            p.insert_text((72, 800), footer, fontsize=8, fontname="helv")
    b = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return b


def w(name, data, sub=""):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_bytes(data if isinstance(data, bytes) else data.encode())


lease = make_pdf(LEASE, "Demo document - fictional parties")
w("TEST Split, Organize, Rotate, Watermark, Page numbers, Crop, Compress, Edit PDF, Protect, PDF to JPG, Merge (with Addendum) - Lease Agreement 3 pages.pdf", lease)             # split, organize, rotate, watermark, numbers, crop, compress, edit, protect, pdf-to-jpg
w("TEST Merge PDF (add to the Lease) - Addendum.pdf", make_pdf(ADDENDUM))             # merge with the lease
w("TEST Sign PDF - Settlement to sign.pdf", make_pdf(SETTLE))       # sign
w("TEST Unlock PDF (password demo123) - Locked contract.pdf", tools.protect_pdf(make_pdf(ADDENDUM), "demo123"))  # unlock

w("TEST Sign PDF (upload as signature) - Signature.png", tools.signature_typed("Demo Lawyer", "Classic"))   # upload as your own signature

rnd = random.Random(7)
def scan(n):
    im = Image.new("RGB", (1240, 1754), (250, 248, 242))
    d = ImageDraw.Draw(im)
    d.text((120, 140), f"SCANNED PAGE {n} - Witness statement", fill=(30, 30, 30))
    for i in range(22):
        d.line((120, 220 + i * 56, 1120 - rnd.randint(0, 260), 220 + i * 56), fill=(70, 70, 70), width=5)
    return im.filter(ImageFilter.GaussianBlur(0.6))
for n in (1, 2):
    b = io.BytesIO(); scan(n).save(b, "JPEG", quality=85); w(f"TEST JPG to PDF (select both) - Scan page {n}.jpg", b.getvalue())   # JPG to PDF

# Background remover: simple subject on a plain white backdrop
im = Image.new("RGB", (900, 900), "white"); d = ImageDraw.Draw(im)
d.ellipse((330, 120, 570, 380), fill=(224, 172, 140)); d.rounded_rectangle((250, 400, 650, 860), 60, fill=(36, 63, 112))
d.rectangle((420, 380, 480, 420), fill=(224, 172, 140))
b = io.BytesIO(); im.save(b, "PNG"); w("TEST Background remover - Portrait on white.png", b.getvalue())

# Image editor: a colourful, slightly dark photo-like image
im = Image.new("RGB", (1200, 800)); px = im.load()
for x in range(1200):
    for y in range(800):
        px[x, y] = (int(60 + 120 * x / 1200), int(70 + 90 * y / 800), int(110 + 60 * (1 - x / 1200)))
d = ImageDraw.Draw(im); d.ellipse((800, 120, 1000, 320), fill=(235, 200, 90)); d.rectangle((0, 560, 1200, 800), fill=(40, 70, 60))
b = io.BytesIO(); im.save(b, "JPEG", quality=88); w("TEST Image editor and Watermark on image - Photo.jpg", b.getvalue())

w("TEST E-mail draft (paste the text in) - Client notes.txt", "Client PT Maju Logistik is 45 days late on rent (Jan-Feb). Remind them of clause 4 late interest "
  "(0.1%/day) and clause 5 termination notice after 30 days. Offer a payment plan if they pay half by Friday.")
w("TEST AI detector (human-written, should score low) - Sample.txt", "Honestly, I wasn't sure the tenant would show up. They'd missed two calls, and the landlord was "
  "already muttering about locks. Then Pak Budi walks in at 4:55 with a bag of cash and an excuse about a flooded road. "
  "We counted it twice, the second time because I lost my place. Not elegant, but it settled the arrears.")
w("TEST AI detector (AI-style, should score high) - Sample.txt", "In conclusion, it is important to note that the lease agreement serves as a comprehensive framework. "
  "Furthermore, it is essential to consider that timely payment plays a crucial role in maintaining a harmonious landlord-tenant "
  "relationship. Moreover, both parties should carefully review the terms to ensure compliance and mitigate potential risks. "
  "Ultimately, clear communication is key to fostering a mutually beneficial outcome.")
w("README.txt", "Every file name starts with TEST and says which Tools card it is for.\nZip files: select any files.\nNot live yet: PDF to Word, Transcribe audio.\nPassword for the locked PDF: demo123\n")
print("ok", len(list(OUT.iterdir())),"files")
