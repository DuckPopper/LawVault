"""Adds an Indonesian demo matter for the Case analysis page. Safe to run more than once.
Run after seed_demo.py:  python seed_analysis_demo.py   (DEV_MODE=1 only; uses the demo accounts)"""
import sys
import time
import cases, config, db

TITLE = "PT Sentosa Abadi v. PT Maju Logistik"
DESC = "Wanprestasi perjanjian pengadaan forklift – Pengadilan Negeri Jakarta Selatan"

AGREEMENT = """PERJANJIAN JUAL BELI DAN PENGADAAN BARANG
No. 014/SA-ML/III/2026

Pada hari Senin, tanggal 2 Maret 2026, telah dibuat perjanjian antara:
1. PT Sentosa Abadi, berkedudukan di Jakarta Selatan ("Pembeli"); dan
2. PT Maju Logistik, berkedudukan di Bekasi ("Penjual").

Pasal 1 – Objek. Penjual menjual dan menyerahkan 20 (dua puluh) unit forklift listrik kapasitas 3 ton beserta
pemasangan dan pelatihan operator kepada Pembeli.

Pasal 2 – Harga. Harga keseluruhan Rp 4.000.000.000 (empat miliar rupiah), termasuk PPN.

Pasal 3 – Pembayaran. Uang muka 50% (Rp 2.000.000.000) dibayar paling lambat 9 Maret 2026. Sisa 50% dibayar
dalam 14 hari setelah berita acara serah terima seluruh unit ditandatangani.

Pasal 5 – Penyerahan. Seluruh unit diserahkan di gudang Pembeli di Cikarang paling lambat 30 April 2026.

Pasal 7 – Denda keterlambatan. Atas keterlambatan penyerahan, Penjual dikenakan denda 0,1% dari harga per hari
keterlambatan, paling banyak 5% dari harga.

Pasal 9 – Pemutusan. Apabila Penjual lalai menyerahkan unit lebih dari 30 hari sejak tanggal penyerahan, Pembeli
berhak memutus perjanjian ini dengan pemberitahuan tertulis, dan Penjual wajib mengembalikan seluruh pembayaran
yang telah diterima dalam 14 hari ditambah denda sesuai Pasal 7. Para pihak sepakat mengesampingkan Pasal 1266
dan 1267 KUHPerdata sepanjang mengenai keharusan putusan pengadilan untuk pemutusan.

Pasal 11 – Keadaan memaksa. Penjual dibebaskan dari tanggung jawab atas keterlambatan karena bencana alam, perang,
atau kebijakan pemerintah, dengan syarat memberitahukan Pembeli secara tertulis dalam 7 hari sejak kejadian.

Pasal 13 – Penyelesaian sengketa. Sengketa diselesaikan secara musyawarah dalam 30 hari; jika gagal, melalui
Pengadilan Negeri Jakarta Selatan.

Pasal 14 – Hukum yang berlaku. Perjanjian ini tunduk pada hukum Republik Indonesia.
"""

CHAT = [
    ("partner", "Klien sudah transfer DP Rp 2 miliar tanggal 6 Maret 2026, bukti transfer BCA ada di saya."),
    ("admin", "Per hari ini baru 8 unit forklift yang diserahkan (berita acara 28 April 2026). 12 unit belum datang."),
    ("partner", "PT Maju Logistik kirim email 20 Mei 2026, katanya unit tertahan di pelabuhan karena aturan impor baru. "
                "Mereka tidak pernah kirim pemberitahuan keadaan memaksa dalam 7 hari seperti Pasal 11."),
    ("admin", "Klien juga harus sewa forklift pengganti Rp 85 juta per bulan sejak Mei 2026. Invoice sewa ada."),
    ("partner", "Kita sudah kirim somasi pertama 10 Juni 2026, tidak dijawab. Somasi kedua 1 Juli 2026, dijawab "
                "bahwa mereka 'sedang mengusahakan'. Klien ingin pilih: putus kontrak dan uang kembali, atau unit "
                "datang plus ganti rugi."),
    ("admin", "Info dari klien: PT Maju Logistik sedang digugat PKPU oleh kreditur lain di PN Niaga Jakarta Pusat, "
              "sidang pertama 8 Desember 2026. Kita perlu bergerak cepat."),
]


def main():
    if not config.DEV_MODE:
        sys.exit("Refusing to seed demo data with DEV_MODE=0.")
    db.init_db()
    with db.conn() as c:
        users = {r["email"].split("@")[0]: r for r in c.execute(
            "SELECT * FROM users WHERE email IN ('admin@lawvault.test','partner@lawvault.test','associate@lawvault.test')")}
    if "admin" not in users:
        sys.exit("Run seed_demo.py first.")
    admin = users["admin"]
    if any(c["title"] == TITLE for c in cases.list_cases(admin["id"])):
        print("analysis demo: already there")
        return
    with db.conn() as c:  # the demo shouldn't trip over the free plan's case limit
        c.execute("UPDATE users SET plan='pro', plan_expires=? WHERE id=?", (time.time() + 365 * 86400, admin["id"]))
        admin = c.execute("SELECT * FROM users WHERE id=?", (admin["id"],)).fetchone()
    cid, msg = cases.create_case(admin, TITLE, DESC)
    if not cid:
        sys.exit(msg)
    if "partner" in users:
        cases.add_member(admin, cid, "partner@lawvault.test", "editor")
    if "associate" in users:
        cases.add_member(admin, cid, "associate@lawvault.test", "viewer")
    cases.add_document(admin, cid, "Perjanjian-014-SA-ML-2026.txt", AGREEMENT)
    for who, text in CHAT:
        cases.post_message(users.get(who, admin)["id"], cid, text)
    cases.add_task(admin["id"], cid, "deadline", "Ajukan tagihan sebagai kreditur dalam PKPU (cek jadwal)",
                   time.mktime((2026, 12, 8, 9, 0, 0, 0, 0, -1)))
    print("analysis demo:", TITLE)


if __name__ == "__main__":
    main()
