"""Privacy policy text. Shown at sign-up and under Settings → Privacy."""
import i18n

POLICY = """
#### What we store
Your email address, a bcrypt hash of your password (never the password itself), and the cases, chat messages,
documents, deadlines and calendar entries you create. All case content is **encrypted at rest**.

#### Who can see it
Only you and the members of cases you share. Administrators can see account metadata and audit events,
**never** case or document content.

#### AI processing
When you use an AI feature, the text is first stripped of email addresses, phone numbers, card and ID numbers, then
sent to a third-party AI provider. Free AI tiers may retain prompts. **Do not upload highly privileged material
unless you run a local or private model.** AI output is general information, not legal advice.

#### Voice input
When you dictate, the recording is sent to a speech-to-text service (OpenAI Whisper), or processed on our own
server if the local option is on. LawVault never stores the audio; only the text is used, and it is masked like
any other AI input.

#### Calendar sync
If you connect Google or Apple Calendar (Pro plan and up), event titles, notes, locations and times are exchanged
with that service in both directions. Attendees are never sent. Sign-in tokens and app-specific passwords are stored
**encrypted**, and you can disconnect at any time from **Calendar → Sync**.

#### Your rights
You can export all of your data or permanently delete your account at any time from **Settings → Privacy** and
**Settings → Account**.
"""

POLICY_ID = """
#### Data yang kami simpan
Alamat email Anda, hash bcrypt dari kata sandi Anda (bukan kata sandi itu sendiri), serta kasus, pesan obrolan,
dokumen, tenggat, dan agenda kalender yang Anda buat. Seluruh isi kasus **dienkripsi saat disimpan**.

#### Siapa yang dapat melihatnya
Hanya Anda dan anggota kasus yang Anda bagikan. Administrator dapat melihat metadata akun dan catatan audit,
**tidak pernah** isi kasus atau dokumen.

#### Pemrosesan AI
Saat Anda menggunakan fitur AI, teks terlebih dahulu dibersihkan dari alamat email, nomor telepon, nomor kartu, dan
nomor identitas, lalu dikirim ke penyedia AI pihak ketiga. Layanan AI gratis dapat menyimpan perintah (prompt) Anda.
**Jangan mengunggah materi yang sangat rahasia (privileged) kecuali Anda menjalankan model lokal atau privat.**
Keluaran AI merupakan informasi umum, bukan nasihat hukum.

#### Input suara
Saat Anda mendikte, rekaman dikirim ke layanan speech-to-text (OpenAI Whisper), atau diproses di server kami
sendiri jika opsi lokal aktif. LawVault tidak pernah menyimpan audionya; hanya teksnya yang dipakai, dan teks itu
disamarkan seperti masukan AI lainnya.

#### Sinkronisasi kalender
Jika Anda menghubungkan Google atau Apple Calendar (paket Pro ke atas), judul, catatan, lokasi, dan waktu acara
dipertukarkan dengan layanan itu secara dua arah. Peserta tidak pernah dikirim. Token masuk dan kata sandi khusus
aplikasi disimpan **terenkripsi**, dan Anda dapat memutuskan koneksi kapan saja dari **Kalender → Sinkron**.

#### Hak Anda
Anda dapat mengekspor seluruh data Anda atau menghapus akun Anda secara permanen kapan saja melalui
**Pengaturan → Privasi** dan **Pengaturan → Akun**.
"""


def policy() -> str:
    return POLICY_ID if i18n.lang() == "id" else POLICY
