"""Adds document-review and case-analysis samples to the Desktop demo folder."""
from pathlib import Path
import docx
import make_demo_files as m

OUT = m.OUT

SUPPLY = [
 ("SUPPLY AND SERVICES AGREEMENT", [
  "Between CV Nusantara Pangan (Supplier) and PT Maju Logistik (Customer), dated 15 September 2026.",
  "1. Supply. The Supplier delivers 40 tonnes of rice per month to the Customer's Surabaya depot.",
  "2. Price. IDR 13,500 per kg. The Supplier may change the price at any time by notice, effective immediately.",
  "3. Payment. The Customer pays within 7 days of invoice. Late payment bears 5% interest per month."]),
 ("RISK ALLOCATION", [
  "4. Liability. The Supplier's liability is excluded entirely, including for spoiled or late goods and for its own negligence.",
  "5. Indemnity. The Customer indemnifies the Supplier for all claims, without limit, whether or not caused by the Customer.",
  "6. Exclusivity. The Customer shall buy rice only from the Supplier for 5 years and may not resell outside East Java.",
  "7. Termination. The Supplier may terminate on 3 days' notice; the Customer only for proven material breach after 90 days' cure."]),
 ("DATES AND DISPUTES", [
  "8. First delivery on 5 January 2027. Customer to open a letter of credit by 15 December 2026.",
  "9. The Customer must give written notice of any defect within 24 hours of delivery or waive all claims.",
  "10. Automatic renewal for successive 5-year terms unless notice is given between 1 and 31 March 2031.",
  "11. Disputes are decided exclusively by the Supplier's chosen arbitrator in Medan. Governing law: Indonesia."]),
]
pdf = m.make_pdf(SUPPLY, "Demo document - fictional parties")
m.w("TEST Document review - one-sided supply contract (AI risks and Find deadlines).pdf", pdf)

d = docx.Document()
d.add_heading("Demand Letter (Somasi)", 1)
for t in ["Jakarta, 24 November 2026",
          "To: PT Maju Logistik. From: PT Sentosa Abadi, through its counsel.",
          "Under the Commercial Lease Agreement of 1 January 2025 you owe rent of IDR 170,000,000 for January and February 2026, "
          "plus late interest of 0.1% per day under clause 4.",
          "We require full payment within 7 days of this letter, that is by 1 December 2026. If you do not pay, we will terminate the Lease "
          "under clause 5 and file a claim with BANI without further notice, and seek the security deposit of IDR 255,000,000 as set-off."]:
    d.add_paragraph(t)
d.save(OUT / "TEST Document review - demand letter (Word file, Find deadlines).docx")

m.w("TEST Document review - witness statement (upload to the case Documents tab).txt",
 "Statement of Mr. Budi Hartono, warehouse supervisor, 20 November 2026. I confirm that PT Maju Logistik stopped paying rent after "
 "the flood of 3 January 2026. On 14 January I told Ms. Rina of PT Sentosa Abadi that Unit 7 had water damage and that rent should be "
 "reduced. She answered by phone that she would think about it. No written reply came. In February the landlord's guard "
 "padlocked the loading bay for two days (12-13 February), and our trucks could not leave. I took photographs on both days.")

m.w("TEST Case analysis - facts to type or upload on the Case analysis page.txt",
 "Parties: PT Sentosa Abadi (landlord) and PT Maju Logistik (tenant). Lease of Warehouse Unit 7 from 1 January 2025 for five years, rent IDR 85,000,000 "
 "per month. On 3 January 2026 a flood damaged Unit 7. On 14 January the tenant orally asked for a rent reduction; no written answer. The tenant paid nothing "
 "for January and February 2026. On 12-13 February the landlord locked the loading bay. On 3 February and 17 February the landlord sent demand letters. "
 "An addendum signed 1 July 2025 reduced rent to IDR 78,000,000 until 30 June 2026 against 12 months upfront; the tenant says it paid, the landlord says it did not. "
 "Question: can the landlord terminate and keep the IDR 255,000,000 deposit, and does the flood or the lockout help the tenant?")
print("review files added")
