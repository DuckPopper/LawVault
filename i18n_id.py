"""Bahasa Indonesia strings. Keys are the English UI text used in the code (see i18n.t).
tests/test_i18n.py fails if a string passed to t() has no entry here, so nothing is silently left in English."""
import re

ID = {
    # ---------- navigation and shell ----------
    "Workspace": "Ruang Kerja",
    "AI": "AI",
    "You": "Anda",
    "you": "Anda",
    "  (you)": "  (Anda)",
    "Dashboard": "Dasbor",
    "Cases": "Kasus",
    "Calendar": "Kalender",
    "Case analysis": "Analisis kasus",
    "Legal assistant": "Asisten hukum",
    "Document review": "Tinjauan dokumen",
    "Notifications": "Notifikasi",
    "Settings": "Pengaturan",
    "Admin": "Admin",
    "Status": "Status",
    "Language": "Bahasa",
    "Interface language": "Bahasa antarmuka",
    "Log out": "Keluar",
    "Light mode": "Mode terang",
    "Dark mode": "Mode gelap",
    "Invisible: you appear offline. Do Not Disturb: no pop-up notifications.":
        "Tak terlihat: Anda tampak offline. Jangan Ganggu: tanpa notifikasi pop-up.",
    "{plan} plan": "Paket {plan}",
    "Free": "Gratis",
    "Pro": "Pro",
    "Firm": "Firma",
    "{n} unread notification": "{n} notifikasi belum dibaca",
    "{n} unread notifications": "{n} notifikasi belum dibaca",
    "{job}: working…": "{job}: sedang diproses…",
    "{job} failed. Open {page} to see it.": "{job} gagal. Buka {page} untuk melihatnya.",
    "{job} is ready. Open {page} to see it.": "{job} sudah siap. Buka {page} untuk melihatnya.",
    "Full case analysis": "Analisis kasus lengkap",
    "Review of {name}": "Tinjauan {name}",
    "Deadlines in {name}": "Tenggat dalam {name}",

    # ---------- presence ----------
    "🟢 Online": "🟢 Online",
    "🔴 Do Not Disturb": "🔴 Jangan Ganggu",
    "⚫ Invisible": "⚫ Tak Terlihat",
    "Online": "Online",
    "Idle": "Tidak aktif",
    "Do Not Disturb": "Jangan Ganggu",
    "Offline": "Offline",
    "Status updated.": "Status diperbarui.",

    # ---------- login ----------
    "The secure workspace for legal teams": "Ruang kerja aman untuk tim hukum",
    "Case data encrypted at rest · Two-step sign-in": "Data kasus terenkripsi · Masuk dua langkah",
    "Log in": "Masuk",
    "Sign up": "Daftar",
    "Forgot password": "Lupa kata sandi",
    "Email": "Email",
    "Password": "Kata sandi",
    "Continue": "Lanjutkan",
    "Password (10+ chars, letter + number)": "Kata sandi (10+ karakter, huruf + angka)",
    "Privacy policy": "Kebijakan privasi",
    "I have read and accept the privacy policy": "Saya telah membaca dan menyetujui kebijakan privasi",
    "Create account": "Buat akun",
    "Checking password against known breaches…": "Memeriksa kata sandi terhadap kebocoran data yang diketahui…",
    "Very weak": "Sangat lemah",
    "Weak": "Lemah",
    "Fair": "Cukup",
    "Good": "Baik",
    "Strong": "Kuat",
    "Account email": "Email akun",
    "Send reset code": "Kirim kode reset",
    "6-digit code": "Kode 6 digit",
    "New password": "Kata sandi baru",
    "Reset password": "Atur ulang kata sandi",
    "DEV MODE – your code: **{code}**": "MODE DEV – kode Anda: **{code}**",
    "DEV MODE – your code: **{code}** (real email is used when DEV_MODE=0)":
        "MODE DEV – kode Anda: **{code}** (email asli digunakan jika DEV_MODE=0)",
    "Two-step verification": "Verifikasi dua langkah",
    "Enter your code.": "Masukkan kode Anda.",
    "Authenticator code": "Kode aplikasi autentikator",
    "6-digit code from your email": "Kode 6 digit dari email Anda",
    "Verify and log in": "Verifikasi dan masuk",
    "Resend code": "Kirim ulang kode",
    "Cancel": "Batal",
    "Lost your phone? Ask an administrator to reset your authenticator.":
        "Kehilangan ponsel? Minta administrator untuk mengatur ulang autentikator Anda.",
    "Too many failed attempts. Try again in a few minutes.": "Terlalu banyak percobaan gagal. Coba lagi beberapa menit lagi.",
    "Invalid or expired code.": "Kode tidak valid atau sudah kedaluwarsa.",
    "Open your authenticator app and enter the 6-digit code.":
        "Buka aplikasi autentikator Anda dan masukkan kode 6 digit.",
    "Authenticator app removed. You'll get email codes again.":
        "Aplikasi autentikator dihapus. Anda akan kembali menerima kode lewat email.",

    # ---------- backend messages ----------
    "Password must be at least 10 characters.": "Kata sandi minimal 10 karakter.",
    "That password is too common.": "Kata sandi itu terlalu umum.",
    "Password needs at least one letter and one number.": "Kata sandi harus memuat minimal satu huruf dan satu angka.",
    "Enter a valid email address.": "Masukkan alamat email yang valid.",
    "You must accept the privacy policy.": "Anda harus menyetujui kebijakan privasi.",
    "Could not create account. If you already have one, log in or reset your password.":
        "Tidak dapat membuat akun. Jika Anda sudah punya akun, silakan masuk atau atur ulang kata sandi.",
    "Account created. Please log in.": "Akun berhasil dibuat. Silakan masuk.",
    "Invalid email or password.": "Email atau kata sandi salah.",
    "Password accepted.": "Kata sandi diterima.",
    "If that email is registered, a reset code was sent.":
        "Jika email tersebut terdaftar, kode reset telah dikirim.",
    "Password updated. Please log in.": "Kata sandi diperbarui. Silakan masuk.",
    "Current password is incorrect.": "Kata sandi saat ini salah.",
    "Password changed. Please log in again.": "Kata sandi diubah. Silakan masuk kembali.",
    "Password is incorrect.": "Kata sandi salah.",
    "Authenticator code is incorrect.": "Kode autentikator salah.",
    "Please wait a few seconds before requesting another code.":
        "Harap tunggu beberapa detik sebelum meminta kode lagi.",
    "Too many codes requested. Try again later.": "Terlalu banyak permintaan kode. Coba lagi nanti.",
    "Code generated (dev mode).": "Kode dibuat (mode dev).",
    "Could not send email. Contact support.": "Tidak dapat mengirim email. Hubungi dukungan.",
    "We sent a 6-digit code to your email.": "Kami mengirim kode 6 digit ke email Anda.",
    "Invalid request.": "Permintaan tidak valid.",
    "You can only request calendars of lawyers you share a case with.":
        "Anda hanya dapat meminta kalender advokat yang berbagi kasus dengan Anda.",
    "You already have that level of access.": "Anda sudah memiliki tingkat akses tersebut.",
    "Request sent. They'll see it under Calendar → Sharing.":
        "Permintaan terkirim. Mereka akan melihatnya di Kalender → Berbagi.",
    "Title is required.": "Judul wajib diisi.",
    "End time must be after start time.": "Waktu selesai harus setelah waktu mulai.",
    "Events can be at most 7 days long.": "Acara paling lama 7 hari.",
    "Too many people for your plan. Upgrade to invite more.":
        "Terlalu banyak orang untuk paket Anda. Tingkatkan paket untuk mengundang lebih banyak.",
    "No access to that case.": "Tidak ada akses ke kasus tersebut.",
    "You can only invite lawyers you share a case with.":
        "Anda hanya dapat mengundang advokat yang berbagi kasus dengan Anda.",
    "Meeting proposed - invitees can accept or decline.":
        "Rapat diusulkan - undangan dapat diterima atau ditolak.",
    "Event added.": "Acara ditambahkan.",
    "Too many people for your plan.": "Terlalu banyak orang untuk paket Anda.",
    "Invalid duration or date range.": "Durasi atau rentang tanggal tidak valid.",
    "You don't have calendar access to one of the selected people.":
        "Anda tidak memiliki akses kalender ke salah satu orang yang dipilih.",
    "Case limit reached for your plan. Upgrade to create more.":
        "Batas kasus untuk paket Anda tercapai. Tingkatkan paket untuk membuat lebih banyak.",
    "Case created.": "Kasus berhasil dibuat.",
    "Invalid role.": "Peran tidak valid.",
    "Only the case owner can add members.": "Hanya pemilik kasus yang dapat menambah anggota.",
    "Member limit reached for your plan.": "Batas anggota untuk paket Anda tercapai.",
    "If that lawyer has a LawVault account, they now have access.":
        "Jika advokat tersebut memiliki akun LawVault, kini mereka memiliki akses.",
    "You need editor access to upload to this case.": "Anda memerlukan akses editor untuk mengunggah ke kasus ini.",
    "Document limit reached for your plan.": "Batas dokumen untuk paket Anda tercapai.",
    "Uploaded.": "Terunggah.",
    "Give it a title.": "Beri judul.",
    "A deadline needs a date.": "Tenggat memerlukan tanggal.",
    "You need editor access to add deadlines or tasks.": "Anda memerlukan akses editor untuk menambah tenggat atau tugas.",
    "The assignee must be a member of this case.": "Penerima tugas harus anggota kasus ini.",
    "Added.": "Ditambahkan.",
    "Daily AI limit reached for your plan. Upgrade for more.":
        "Batas harian AI untuk paket Anda tercapai. Tingkatkan paket untuk menambah.",
    "AI is not configured. Add GEMINI_API_KEY to your .env file (free key: aistudio.google.com).":
        "AI belum dikonfigurasi. Tambahkan GEMINI_API_KEY ke berkas .env Anda (kunci gratis: aistudio.google.com).",
    "The AI service is unavailable right now. Please try again later.":
        "Layanan AI sedang tidak tersedia. Silakan coba lagi nanti.",
    "The free AI tier is rate-limited right now. Please try again in a minute.":
        "Layanan AI gratis sedang dibatasi. Silakan coba lagi dalam semenit.",
    "No answer was produced.": "Tidak ada jawaban yang dihasilkan.",
    "Something went wrong while talking to the AI. Please try again.":
        "Terjadi kesalahan saat menghubungi AI. Silakan coba lagi.",
    "You need editor access to ask the AI in this chat.": "Anda memerlukan akses editor untuk bertanya kepada AI di obrolan ini.",
    "Type a question after @ai.": "Ketik pertanyaan setelah @ai.",
    "The review finished but couldn't be saved (the document may have been deleted).":
        "Tinjauan selesai tetapi tidak dapat disimpan (dokumen mungkin telah dihapus).",
    "That file is not a real PDF.": "Berkas itu bukan PDF yang sebenarnya.",
    "Encrypted PDFs are not supported.": "PDF terenkripsi tidak didukung.",
    "Could not read that PDF.": "Tidak dapat membaca PDF tersebut.",
    "Text files must be UTF-8.": "Berkas teks harus berformat UTF-8.",
    "Only PDF and TXT files are allowed.": "Hanya berkas PDF dan TXT yang diizinkan.",
    "No readable text found (scanned PDFs are not supported).":
        "Tidak ditemukan teks yang dapat dibaca (PDF hasil pindai tidak didukung).",
    "You need editor access to run analyses on this case.":
        "Anda memerlukan akses editor untuk menjalankan analisis pada kasus ini.",
    "Describe the facts first (at least a few sentences).": "Jelaskan faktanya terlebih dahulu (minimal beberapa kalimat).",
    "Unknown tool.": "Alat tidak dikenal.",
    "The AI's timeline couldn't be read. Please try again.": "Timeline dari AI tidak dapat dibaca. Silakan coba lagi.",
    "The AI's risk register couldn't be read. Please try again.":
        "Daftar risiko dari AI tidak dapat dibaca. Silakan coba lagi.",
    "The result couldn't be saved (your access to the case may have changed).":
        "Hasil tidak dapat disimpan (akses Anda ke kasus mungkin telah berubah).",
    "You have view-only access to this case, so you can read results but not run tools.":
        "Anda hanya memiliki akses baca untuk kasus ini, sehingga Anda dapat membaca hasil tetapi tidak menjalankan alat.",

    # ---------- dashboard ----------
    "Good morning": "Selamat pagi",
    "Good afternoon": "Selamat siang",
    "Good evening": "Selamat malam",
    "Active cases": "Kasus aktif",
    "of {max} on {plan}": "dari {max} pada paket {plan}",
    "Due in 14 days": "Jatuh tempo dalam 14 hari",
    "{n} overdue": "{n} terlambat",
    "Nothing overdue": "Tidak ada yang terlambat",
    "My open tasks": "Tugas saya yang terbuka",
    "Assigned to you": "Ditugaskan kepada Anda",
    "AI requests today": "Permintaan AI hari ini",
    "{inv} meeting invitation(s) and {req} calendar request(s) need a response.":
        "{inv} undangan rapat dan {req} permintaan kalender menunggu tanggapan.",
    "Open calendar": "Buka kalender",
    "Today": "Hari ini",
    "Nothing scheduled today.": "Tidak ada jadwal hari ini.",
    "Upcoming deadlines": "Tenggat mendatang",
    "Overdue": "Terlambat",
    "Tomorrow": "Besok",
    "In {n} days": "Dalam {n} hari",
    "No deadlines in the next 14 days.": "Tidak ada tenggat dalam 14 hari ke depan.",
    "Due {date}": "Jatuh tempo {date}",
    "Nothing assigned to you.": "Tidak ada yang ditugaskan kepada Anda.",
    "Recent cases": "Kasus terbaru",
    "No cases yet. Create one under Cases.": "Belum ada kasus. Buat satu di menu Kasus.",
    "Open cases": "Buka kasus",
    "Tentative": "Belum pasti",

    # ---------- cases ----------
    "Encrypted team chat, documents, deadlines and members for each matter.":
        "Obrolan tim terenkripsi, dokumen, tenggat, dan anggota untuk setiap perkara.",
    "Owner": "Pemilik",
    "Editor": "Editor",
    "Viewer": "Pengamat",
    "Viewer (read-only)": "Pengamat (hanya baca)",
    "New case": "Kasus baru",
    "Case title": "Judul kasus",
    "Short description (optional)": "Deskripsi singkat (opsional)",
    "Create": "Buat",
    "Create your first case to start collaborating.": "Buat kasus pertama Anda untuk mulai berkolaborasi.",
    "Open case": "Buka kasus",
    "You no longer have access to this case.": "Anda tidak lagi memiliki akses ke kasus ini.",
    "Analyse this case: timeline, legal basis, risks, drafting, strategy":
        "Analisis kasus ini: timeline, dasar hukum, risiko, drafting, strategi",
    "Team chat": "Obrolan tim",
    "Documents": "Dokumen",
    "Deadlines & tasks": "Tenggat & tugas",
    "Team": "Tim",
    "Your session ended. Refresh the page to log in again.": "Sesi Anda berakhir. Muat ulang halaman untuk masuk kembali.",
    "No messages yet. Start the discussion below. Tip: type “@ai” and a question to ask the AI.":
        "Belum ada pesan. Mulai diskusi di bawah. Tips: ketik “@ai” diikuti pertanyaan untuk bertanya kepada AI.",
    "LawVault AI · answering {who} · {when}": "AI LawVault · menjawab {who} · {when}",
    "Brief me on this case": "Ringkas kasus ini untuk saya",
    "AI briefing from the chat, documents and deadlines": "Ringkasan AI dari obrolan, dokumen, dan tenggat",
    "Reading the case…": "Membaca kasus…",
    "Case briefing": "Ringkasan kasus",
    "Post briefing to team chat": "Kirim ringkasan ke obrolan tim",
    "Dismiss": "Tutup",
    "👁️ You have view-only access to this case.": "👁️ Anda hanya memiliki akses baca untuk kasus ini.",
    "Message your team… (start with @ai to ask the AI, @email to mention someone)":
        "Kirim pesan ke tim Anda… (awali dengan @ai untuk bertanya kepada AI, @email untuk menyebut seseorang)",
    "LawVault AI is thinking…": "AI LawVault sedang berpikir…",
    "Upload PDF or TXT to this case (up to {mb} MB)": "Unggah PDF atau TXT ke kasus ini (hingga {mb} MB)",
    "Save to case": "Simpan ke kasus",
    "No documents yet.": "Belum ada dokumen.",
    "Analyze with AI": "Analisis dengan AI",
    "Analyzing…": "Menganalisis…",
    "📅 Find deadlines": "📅 Cari tenggat",
    "AI pulls out dates you must act on": "AI mengambil tanggal-tanggal yang harus Anda tindak lanjuti",
    "Looking for deadlines…": "Mencari tenggat…",
    "No dated deadlines found.": "Tidak ditemukan tenggat bertanggal.",
    "Add selected to case deadlines": "Tambahkan yang dipilih ke tenggat kasus",
    "Added {n} deadline(s). They also appear on everyone's calendar.":
        "{n} tenggat ditambahkan. Tenggat ini juga muncul di kalender semua orang.",
    "➕ Add a deadline or task": "➕ Tambah tenggat atau tugas",
    "Type": "Jenis",
    "⚖️ Deadline (court/filing date)": "⚖️ Tenggat (sidang/pengajuan)",
    "✅ Task": "✅ Tugas",
    "What": "Apa",
    "File statement of defence": "Ajukan jawaban gugatan",
    "Has a due date": "Memiliki batas waktu",
    "Due date": "Tanggal jatuh tempo",
    "Time": "Waktu",
    "Assign to": "Tugaskan kepada",
    "Nobody": "Tidak ada",
    "Add": "Tambah",
    "No deadlines or tasks yet.": "Belum ada tenggat atau tugas.",
    "🔴 overdue · ": "🔴 terlambat · ",
    "Delete": "Hapus",
    "Role": "Peran",
    "Remove": "Keluarkan",
    "Invite a lawyer by email": "Undang advokat lewat email",
    "As": "Sebagai",
    "Add to case": "Tambahkan ke kasus",
    "⚠️ Danger zone": "⚠️ Zona berbahaya",
    "I understand this permanently deletes the case, chat, documents and deadlines":
        "Saya mengerti ini menghapus kasus, obrolan, dokumen, dan tenggat secara permanen",
    "Delete case": "Hapus kasus",
    "Leave case": "Tinggalkan kasus",

    # ---------- calendar ----------
    "Previous": "Sebelumnya",
    "Next": "Berikutnya",
    "New": "Baru",
    "View": "Tampilan",
    "Day": "Hari",
    "Week": "Minggu",
    "Month": "Bulan",
    "this day": "hari ini",
    "this week": "minggu ini",
    "this month": "bulan ini",
    "Events {label} · {n}": "Acara {label} · {n}",
    "Calendars": "Kalender",
    "My events": "Acara saya",
    "Meetings": "Rapat",
    "Case deadlines": "Tenggat kasus",
    "Case tasks": "Tugas kasus",
    "Busy": "Sibuk",
    "{n} more": "{n} lagi",
    "New event": "Acara baru",
    "Title": "Judul",
    "Client call: Smith v. Acme": "Telepon klien: Smith lawan Acme",
    "Date": "Tanggal",
    "Starts": "Mulai",
    "Ends": "Selesai",
    "Invitees": "Undangan",
    "Add people you share a case with": "Tambahkan orang yang berbagi kasus dengan Anda",
    "Case": "Kasus",
    "None": "Tidak ada",
    "Notes": "Catatan",
    "Only you and invitees can see these": "Hanya Anda dan undangan yang dapat melihat ini",
    "Add event": "Tambah acara",
    "from {who}": "dari {who}",
    "Nothing scheduled in this range.": "Tidak ada jadwal pada rentang ini.",
    "Deadline": "Tenggat",
    "Organizer: {who}": "Penyelenggara: {who}",
    "Delete for everyone": "Hapus untuk semua orang",
    "Remove from my calendar": "Hapus dari kalender saya",
    "Accept": "Terima",
    "Decline": "Tolak",
    "{n} invitation waiting in Invites.": "{n} undangan menunggu di Undangan.",
    "{n} invitations waiting in Invites.": "{n} undangan menunggu di Undangan.",
    "Invites": "Undangan",
    "Team calendars": "Kalender tim",
    "Find a time": "Cari waktu",
    "Sharing": "Berbagi",
    "No pending invitations.": "Tidak ada undangan yang tertunda.",
    "You can't see anyone's calendar yet. Teammates can turn on sharing, or you can request access under Sharing.":
        "Anda belum dapat melihat kalender siapa pun. Rekan tim dapat mengaktifkan berbagi, atau Anda dapat meminta akses di Berbagi.",
    "This person shares free/busy only: you see when they're busy, not what.":
        "Orang ini hanya membagikan status luang/sibuk: Anda melihat kapan mereka sibuk, bukan untuk apa.",
    "Finds times when everyone is free, Monday to Friday, {start}:00–{end}:00. Only people whose calendar you can see are listed.":
        "Mencari waktu ketika semua orang luang, Senin sampai Jumat, pukul {start}:00–{end}:00. Hanya orang yang kalendernya dapat Anda lihat yang ditampilkan.",
    "Attendees": "Peserta",
    "Duration": "Durasi",
    "{n} min": "{n} menit",
    "From": "Dari",
    "Days to search": "Hari yang dicari",
    "Meeting title": "Judul rapat",
    "Case strategy meeting": "Rapat strategi kasus",
    "Find free slots": "Cari waktu luang",
    "No common free time in that range. Try more days or a shorter meeting.":
        "Tidak ada waktu luang bersama pada rentang itu. Coba tambah hari atau perpendek rapat.",
    "{n} slots where everyone is free.": "{n} slot ketika semua orang luang.",
    "Book": "Pesan",
    "Who can see my calendar": "Siapa yang dapat melihat kalender saya",
    "Visibility for case teammates": "Visibilitas untuk rekan satu kasus",
    "**Private.** Nobody sees your calendar unless you approve their request.":
        "**Pribadi.** Tidak ada yang melihat kalender Anda kecuali Anda menyetujui permintaan mereka.",
    "**Busy only.** Case teammates see *when* you're busy, never *what*.":
        "**Hanya sibuk.** Rekan satu kasus melihat *kapan* Anda sibuk, tidak pernah *untuk apa*.",
    "**Details.** Case teammates see event titles. Private notes stay hidden.":
        "**Rinci.** Rekan satu kasus melihat judul acara. Catatan pribadi tetap tersembunyi.",
    "Calendar visibility saved.": "Visibilitas kalender disimpan.",
    "Requests to see my calendar": "Permintaan untuk melihat kalender saya",
    "No pending requests.": "Tidak ada permintaan yang tertunda.",
    "**{email}** wants {level} access": "**{email}** meminta akses {level}",
    "Approve": "Setujui",
    "Busy only": "Hanya sibuk",
    "Titles visible": "Judul terlihat",
    "Full": "Penuh",
    "Deny": "Tolak",
    "People I approved": "Orang yang saya setujui",
    "Revoke": "Cabut",
    "Request a colleague's calendar": "Minta kalender rekan",
    "Share a case with someone first. You can only request calendars of case teammates.":
        "Bagikan kasus dengan seseorang terlebih dahulu. Anda hanya dapat meminta kalender rekan satu kasus.",
    "Colleague": "Rekan",
    "Access": "Akses",
    "Send request": "Kirim permintaan",
    "My requests": "Permintaan saya",
    "Withdraw": "Tarik kembali",
    "Stop viewing": "Berhenti melihat",
    "pending": "menunggu",
    "accepted": "diterima",
    "declined": "ditolak",
    "approved": "disetujui",
    "denied": "ditolak",
    "busy": "sibuk",
    "details": "rinci",

    # ---------- AI pages ----------
    "Research questions, statutes, procedure and drafting. Answers are concise and to the point.":
        "Pertanyaan hukum, peraturan, hukum acara, dan drafting. Jawaban ringkas dan langsung ke inti.",
    "General legal information, not legal advice. Verify before relying on it.":
        "Informasi hukum umum, bukan nasihat hukum. Verifikasi sebelum mengandalkannya.",
    "{disclaimer}  ·  {used} / {cap} requests used today  ·  Personal data is masked before it leaves LawVault.":
        "{disclaimer}  ·  {used} / {cap} permintaan digunakan hari ini  ·  Data pribadi disamarkan sebelum keluar dari LawVault.",
    "Researching…": "Meneliti…",
    "This keeps running if you switch tabs. You'll get a notification when it's done.":
        "Proses tetap berjalan jika Anda berpindah tab. Anda akan menerima notifikasi setelah selesai.",
    "Ask about limitation periods, elements of a claim, procedural steps, or paste a clause to have it explained.":
        "Tanyakan tentang daluwarsa, unsur gugatan, tahapan acara, atau tempel sebuah klausul untuk dijelaskan.",
    "Waiting for the answer…": "Menunggu jawaban…",
    "Ask a legal question…": "Ajukan pertanyaan hukum…",
    "Clear conversation": "Hapus percakapan",
    "Upload a contract for a structured review: parties, operative clauses, risk flags and points to raise.":
        "Unggah kontrak untuk tinjauan terstruktur: para pihak, klausul operatif, penanda risiko, dan hal yang perlu diangkat.",
    "Upload a contract (PDF or TXT, up to {mb} MB)": "Unggah kontrak (PDF atau TXT, hingga {mb} MB)",
    "Save document": "Simpan dokumen",
    "  ·  working…": "  ·  sedang diproses…",
    "Reviewing…": "Meninjau…",
    "Review with AI": "Tinjau dengan AI",
    "Find deadlines and add to my calendar": "Cari tenggat dan tambahkan ke kalender saya",
    "Add selected to my calendar": "Tambahkan yang dipilih ke kalender saya",
    "Added {n} event(s) to your calendar.": "{n} acara ditambahkan ke kalender Anda.",

    # ---------- case analysis ----------
    "Analyse a matter end to end: the issues, a timeline, the legal basis, the risks, a first draft and a recommended strategy.":
        "Analisis sebuah perkara dari awal hingga akhir: isu hukum, timeline, dasar hukum, risiko, draf awal, dan strategi yang direkomendasikan.",
    "Timeline": "Timeline",
    "Legal basis": "Dasar hukum",
    "Legal risks": "Risiko hukum",
    "Legal drafting": "Legal drafting",
    "Strategy": "Strategi",
    "Analisis kasus": "Analisis kasus",
    "Pembuatan timeline": "Pembuatan timeline",
    "Dasar hukum": "Dasar hukum",
    "Risiko hukum": "Risiko hukum",
    "Rekomendasi strategi": "Rekomendasi strategi",
    "Facts, parties, the legal issues and an issue-by-issue analysis.":
        "Fakta, para pihak, isu hukum, dan analisis per isu.",
    "A dated chronology of what happened and what is coming up.": "Kronologi bertanggal tentang apa yang terjadi dan apa yang akan datang.",
    "The statutes and articles that apply, with their elements tested against the facts.":
        "Undang-undang dan pasal yang berlaku, dengan unsur-unsurnya diuji terhadap fakta.",
    "A risk register ranked by severity and likelihood, with mitigations.":
        "Daftar risiko yang diurutkan berdasarkan tingkat keparahan dan kemungkinan, beserta mitigasinya.",
    "A complete first draft of the document you choose, ready for review.":
        "Draf awal lengkap dari dokumen yang Anda pilih, siap ditinjau.",
    "Litigation and non-litigation options, the recommended route and an action plan.":
        "Pilihan litigasi dan non-litigasi, jalur yang direkomendasikan, dan rencana tindakan.",
    "Indonesia": "Indonesia",
    "Singapore": "Singapura",
    "Malaysia": "Malaysia",
    "England & Wales": "Inggris & Wales",
    "United States": "Amerika Serikat",
    "General / other": "Umum / lainnya",
    "Somasi (letter of demand)": "Somasi (surat teguran)",
    "Surat gugatan (statement of claim)": "Surat gugatan",
    "Jawaban gugatan (statement of defence)": "Jawaban gugatan",
    "Legal opinion / memorandum hukum": "Legal opinion / memorandum hukum",
    "Surat kuasa khusus (special power of attorney)": "Surat kuasa khusus",
    "Perjanjian perdamaian (settlement agreement)": "Perjanjian perdamaian",
    "Laporan / pengaduan pidana (criminal complaint)": "Laporan / pengaduan pidana",
    "This keeps running if you switch pages. You'll get a notification when it's done.":
        "Proses tetap berjalan jika Anda berpindah halaman. Anda akan menerima notifikasi setelah selesai.",
    "Material": "Materi",
    "A LawVault case": "Kasus LawVault",
    "Facts I type or upload": "Fakta yang saya ketik atau unggah",
    "Uses the case's team chat ({msgs} messages), documents ({docs}) and deadlines ({tasks}). Results are shared with everyone on the case.":
        "Menggunakan obrolan tim kasus ({msgs} pesan), dokumen ({docs}), dan tenggat ({tasks}). Hasil dibagikan kepada semua anggota kasus.",
    "Additional facts (optional)": "Fakta tambahan (opsional)",
    "Anything the AI should know that isn't in the case yet.": "Apa pun yang perlu diketahui AI yang belum ada dalam kasus.",
    "👁️ View-only: you can read the results below but not run new ones.":
        "👁️ Hanya baca: Anda dapat membaca hasil di bawah tetapi tidak dapat menjalankan yang baru.",
    "Facts of the matter": "Fakta perkara",
    "Who the parties are, what was agreed, what went wrong and when, what the client wants. Bahasa Indonesia or English.":
        "Siapa para pihak, apa yang disepakati, apa yang salah dan kapan, apa yang diinginkan klien. Bahasa Indonesia atau Inggris.",
    "Attach a document (PDF or TXT, up to {mb} MB)": "Lampirkan dokumen (PDF atau TXT, hingga {mb} MB)",
    "{name}: {n} characters will be included.": "{name}: {n} karakter akan disertakan.",
    "Results on typed facts are private to you and kept for these exact facts.":
        "Hasil dari fakta yang diketik bersifat pribadi dan disimpan untuk fakta yang persis sama.",
    "{disclaimer}  ·  {used} / {cap} AI requests used today  ·  Personal data is masked before it leaves LawVault.":
        "{disclaimer}  ·  {used} / {cap} permintaan AI digunakan hari ini  ·  Data pribadi disamarkan sebelum keluar dari LawVault.",
    "Jurisdiction": "Yurisdiksi",
    "Output language": "Bahasa keluaran",
    "Run full analysis": "Jalankan analisis lengkap",
    "Analysis → timeline → legal basis → risks → strategy, each building on the last. Uses {n} AI requests. Drafting is run separately.":
        "Analisis → timeline → dasar hukum → risiko → strategi, masing-masing melanjutkan yang sebelumnya. Memakai {n} permintaan AI. Drafting dijalankan terpisah.",
    "Step {i} of {n}: {what}…": "Langkah {i} dari {n}: {what}…",
    "starting": "memulai",
    "Full analysis finished: {done} of {n} steps.": "Analisis lengkap selesai: {done} dari {n} langkah.",
    "A full run needs {n} AI requests; you have {left} left today.":
        "Analisis lengkap membutuhkan {n} permintaan AI; sisa Anda hari ini {left}.",
    "Run": "Jalankan",
    "Run again": "Jalankan lagi",
    "Draft it": "Buat draf",
    "Draft again": "Buat draf lagi",
    "Document": "Dokumen",
    "Instructions (optional)": "Instruksi (opsional)",
    "e.g. demand payment within 7 days; firm but courteous tone":
        "mis. menuntut pembayaran dalam 7 hari; nada tegas namun sopan",
    "Working on {what}…": "Sedang mengerjakan {what}…",
    "No {what} yet.": "Belum ada {what}.",
    "by {who}": "oleh {who}",
    "Download .md": "Unduh .md",
    "Undated": "Tanpa tanggal",
    "{events} events  ·  {legal} legal acts  ·  {deadlines} deadlines  ·  grey = fact, gold = legal act, red = deadline":
        "{events} peristiwa  ·  {legal} tindakan hukum  ·  {deadlines} tenggat  ·  abu-abu = fakta, emas = tindakan hukum, merah = tenggat",
    "Fact": "Fakta",
    "Legal act": "Tindakan hukum",
    "Source: {src}": "Sumber: {src}",
    "Gaps in the chronology": "Celah dalam kronologi",
    "Add {n} upcoming date(s) to the case deadlines": "Tambahkan {n} tanggal mendatang ke tenggat kasus",
    "Added {n} deadline(s). They also appear on the team's calendars.":
        "{n} tenggat ditambahkan. Tenggat ini juga muncul di kalender tim.",
    "Overall exposure": "Tingkat paparan keseluruhan",
    "Likelihood": "Kemungkinan",
    "Severity": "Keparahan",
    "High": "Tinggi",
    "Medium": "Sedang",
    "Low": "Rendah",
    "general": "umum",
    "Basis": "Dasar",
    "Mitigation": "Mitigasi",

    # ---------- notifications ----------
    "Just now": "Baru saja",
    "{n} min ago": "{n} menit lalu",
    "{n} h ago": "{n} jam lalu",
    "{n} unread": "{n} belum dibaca",
    "You're all caught up.": "Semua sudah terbaca.",
    "Mark all read": "Tandai semua dibaca",
    "Clear all": "Hapus semua",
    "Do Not Disturb is on. Notifications are collected here but won't pop up.":
        "Jangan Ganggu aktif. Notifikasi dikumpulkan di sini tetapi tidak muncul sebagai pop-up.",
    "Open": "Buka",

    # ---------- admin ----------
    "Account metadata and audit events only. Case and document content is never shown here.":
        "Hanya metadata akun dan catatan audit. Isi kasus dan dokumen tidak pernah ditampilkan di sini.",
    "Admins only.": "Khusus admin.",
    "Users": "Pengguna",
    "Audit log (latest 100)": "Log audit (100 terbaru)",
    "Unlock {email}": "Buka kunci {email}",
    "Reset a user's authenticator app (lost phone)": "Atur ulang aplikasi autentikator pengguna (ponsel hilang)",
    "Nobody has an authenticator app turned on.": "Tidak ada yang mengaktifkan aplikasi autentikator.",
    "User": "Pengguna",
    "I verified this person's identity outside the app": "Saya telah memverifikasi identitas orang ini di luar aplikasi",
    "Reset authenticator": "Atur ulang autentikator",
    "Reset. They'll get email codes at their next login.": "Selesai diatur ulang. Mereka akan menerima kode email saat masuk berikutnya.",

    # ---------- settings ----------
    "General": "Umum",
    "Account": "Akun",
    "Privacy": "Privasi",
    "Billing": "Tagihan",
    "Profile": "Profil",
    "Used to sign in and for security alerts.": "Digunakan untuk masuk dan peringatan keamanan.",
    "Administrators can see account metadata and audit events, never case content.":
        "Administrator dapat melihat metadata akun dan catatan audit, tidak pernah isi kasus.",
    "Administrator": "Administrator",
    "Member": "Anggota",
    "Member since": "Anggota sejak",
    "Menus, messages and dates. AI answers follow it too, unless you ask in another language.":
        "Menu, pesan, dan tanggal. Jawaban AI juga mengikuti bahasa ini, kecuali Anda bertanya dalam bahasa lain.",
    "Presence": "Kehadiran",
    "Invisible shows you as offline. Do Not Disturb collects notifications without pop-ups.":
        "Tak Terlihat menampilkan Anda sebagai offline. Jangan Ganggu mengumpulkan notifikasi tanpa pop-up.",
    "Assistant": "Asisten",
    "Conversation history": "Riwayat percakapan",
    "Your Legal Q&A history is encrypted and visible only to you.":
        "Riwayat Tanya Jawab Hukum Anda dienkripsi dan hanya terlihat oleh Anda.",
    "Clear history": "Hapus riwayat",
    "Assistant history cleared.": "Riwayat asisten dihapus.",
    "Active now": "Aktif sekarang",
    "Active {n} min ago": "Aktif {n} menit lalu",
    "Active {n} h ago": "Aktif {n} jam lalu",
    "This device": "Perangkat ini",
    "Unknown IP": "IP tidak diketahui",
    "signed in {when}": "masuk {when}",
    "That device was logged out.": "Perangkat itu telah dikeluarkan.",
    "Authenticator app": "Aplikasi autentikator",
    "On. You sign in with a code from your authenticator app.":
        "Aktif. Anda masuk dengan kode dari aplikasi autentikator Anda.",
    "Stronger than email codes: works offline and stays safe if your email is compromised. Google Authenticator, Microsoft Authenticator, Authy or 1Password.":
        "Lebih kuat daripada kode email: bekerja offline dan tetap aman jika email Anda diretas. Google Authenticator, Microsoft Authenticator, Authy, atau 1Password.",
    "Turn off": "Matikan",
    "Current authenticator code": "Kode autentikator saat ini",
    "Turn off authenticator": "Matikan autentikator",
    "Set up": "Siapkan",
    "Scan with your app": "Pindai dengan aplikasi Anda",
    "1. Scan the QR code with your authenticator app.\n2. Can't scan? Enter this key:":
        "1. Pindai kode QR dengan aplikasi autentikator Anda.\n2. Tidak bisa memindai? Masukkan kunci ini:",
    "3. Enter the 6-digit code it shows": "3. Masukkan kode 6 digit yang ditampilkan",
    "Turn on": "Aktifkan",
    "Authenticator app is on.": "Aplikasi autentikator aktif.",
    "That code didn't match. Check your phone's clock and try the next code.":
        "Kode itu tidak cocok. Periksa jam ponsel Anda dan coba kode berikutnya.",
    "Security": "Keamanan",
    "Changing it signs you out everywhere.": "Mengubahnya akan mengeluarkan Anda dari semua perangkat.",
    "Change password": "Ubah kata sandi",
    "Current password": "Kata sandi saat ini",
    "10+ characters, a letter and a number.": "10+ karakter, huruf, dan angka.",
    "Update password": "Perbarui kata sandi",
    "Active sessions": "Sesi aktif",
    "Log out of all devices": "Keluar dari semua perangkat",
    "Ends every session, including this one.": "Mengakhiri semua sesi, termasuk sesi ini.",
    "Log out everywhere": "Keluar di mana saja",
    "Delete account": "Hapus akun",
    "Permanently deletes your account, chats, documents, calendar and sessions. This cannot be undone.":
        "Menghapus akun, obrolan, dokumen, kalender, dan sesi Anda secara permanen. Tindakan ini tidak dapat dibatalkan.",
    "**This is permanent.** Export your data first from Privacy if you need it.":
        "**Ini permanen.** Ekspor data Anda terlebih dahulu dari Privasi jika diperlukan.",
    "Confirm password": "Konfirmasi kata sandi",
    "Type DELETE to confirm": "Ketik DELETE untuk konfirmasi",
    "Delete everything": "Hapus semuanya",
    "Password or confirmation incorrect.": "Kata sandi atau konfirmasi salah.",
    "Your data": "Data Anda",
    "Export data": "Ekspor data",
    "Download everything LawVault holds about you as a JSON file.":
        "Unduh semua data tentang Anda di LawVault sebagai berkas JSON.",
    "Export": "Ekspor",
    "Personal data in AI requests": "Data pribadi dalam permintaan AI",
    "Emails, phone, card and ID numbers are masked before any text leaves LawVault.":
        "Email, telepon, nomor kartu, dan nomor identitas disamarkan sebelum teks apa pun keluar dari LawVault.",
    "Always on": "Selalu aktif",
    "Encryption at rest": "Enkripsi saat disimpan",
    "Case content, chat, documents, calendar titles and notifications.":
        "Isi kasus, obrolan, dokumen, judul kalender, dan notifikasi.",
    "Current plan": "Paket saat ini",
    "${price}/month": "${price}/bulan",
    "Resets at midnight": "Direset tengah malam",
    "Renews {date}": "Diperpanjang {date}",
    "Plans": "Paket",
    "Current": "Saat ini",
    "${price} per month": "${price} per bulan",
    "{n} AI requests a day": "{n} permintaan AI per hari",
    "{n} cases": "{n} kasus",
    "{n} documents": "{n} dokumen",
    "{n} members per case": "{n} anggota per kasus",
    "{n} people per meeting": "{n} orang per rapat",
    "Upgrade to {plan}": "Tingkatkan ke {plan}",
    "Demo checkout: no payment details are collected. A production build would use Stripe Checkout.":
        "Checkout demo: tidak ada data pembayaran yang dikumpulkan. Versi produksi akan menggunakan Stripe Checkout.",
    "Cancel subscription": "Batalkan langganan",
    "You keep paid features until the end of the billing period.":
        "Anda tetap menikmati fitur berbayar hingga akhir periode tagihan.",
    "Cancel plan": "Batalkan paket",
}

# Messages built from data (notifications, counts). Captured values are translated too if they are known strings.
_Q = "[“\"]"
PATTERNS = [
    (re.compile(r"This password has appeared in (?P<n>[\d,.]+) known data breaches\. Please choose a different one\."),
     "Kata sandi ini muncul dalam {n} kebocoran data yang diketahui. Silakan pilih yang lain."),
    (re.compile(r"New sign-in to your account from (?P<device>.+?) \((?P<ip>[^)]*)\)\. If this wasn't you, change "
                r"your password and log out all devices\."),
     "Login baru ke akun Anda dari {device} ({ip}). Jika ini bukan Anda, ubah kata sandi dan keluar dari semua perangkat."),
    (re.compile(r"New sign-in to your account from (?P<device>.+?)\. If this wasn't you, change your password and "
                r"log out all devices\."),
     "Login baru ke akun Anda dari {device}. Jika ini bukan Anda, ubah kata sandi dan keluar dari semua perangkat."),
    (re.compile(r"New AI case analysis in “(?P<title>.+)”"), "Analisis kasus AI baru di “{title}”"),
    (re.compile(r"(?P<who>.+?) asked to see your calendar \((?P<level>\w+)\)\."),
     "{who} meminta untuk melihat kalender Anda ({level})."),
    (re.compile(r"(?P<who>.+?) approved your calendar request\."), "{who} menyetujui permintaan kalender Anda."),
    (re.compile(r"(?P<who>.+?) declined your calendar request\."), "{who} menolak permintaan kalender Anda."),
    (re.compile(r"(?P<who>.+?) invited you to “(?P<title>.+)” on (?P<when>.+)\."),
     "{who} mengundang Anda ke “{title}” pada {when}."),
    (re.compile(r"(?P<who>\S+@\S+) accepted “(?P<title>.+)”\."), "{who} menerima “{title}”."),
    (re.compile(r"(?P<who>\S+@\S+) declined “(?P<title>.+)”\."), "{who} menolak “{title}”."),
    (re.compile(r"File too large \(max (?P<mb>\d+) MB\)\."), "Berkas terlalu besar (maks. {mb} MB)."),
    (re.compile(r"PDF too long \(max (?P<n>\d+) pages\)\."), "PDF terlalu panjang (maks. {n} halaman)."),
    (re.compile(r"(?P<who>.+?) added you to “(?P<title>.+)” as (?P<role>\w+)\."),
     "{who} menambahkan Anda ke “{title}” sebagai {role}."),
    (re.compile(r"(?P<who>.+?) mentioned you in “(?P<title>.+)”"), "{who} menyebut Anda di “{title}”"),
    (re.compile(r"New messages in “(?P<title>.+)”"), "Pesan baru di “{title}”"),
    (re.compile(r"New (?P<kind>deadline|task) for you in “(?P<case>.+?)”: (?P<title>.+)"),
     "{kind} baru untuk Anda di “{case}”: {title}"),
    (re.compile(r"Stopped at (?P<label>.+?): (?P<err>.+)"), "Berhenti pada {label}: {err}"),
]

# Words that appear inside the patterns above (captured values are looked up here too)
ID.update({"deadline": "Tenggat", "task": "Tugas", "editor": "editor", "viewer": "pengamat"})

# ---------- calendar assistant, voice input, pick-your-own plan ----------
ID.update({
    "Custom": "Kustom",
    "Pick your own": "Pilih sendiri",
    "Build your plan": "Susun paket Anda",
    "Change your plan": "Ubah paket Anda",
    "From ${price} per month": "Mulai ${price} per bulan",
    "Add more of anything": "Tambah apa pun yang dibutuhkan",
    "{n} voice minutes a month": "{n} menit suara per bulan",
    "Voice minutes this month": "Menit suara bulan ini",
    "Resets monthly": "Direset tiap bulan",
    "The ${base} base price is flat and already includes everything marked “included”. Buying more of an option "
    "adds its price. Switching an option off does not lower the price.":
        "Harga dasar ${base} bersifat tetap dan sudah mencakup semua yang bertanda “termasuk”. Menambah suatu opsi "
        "menambah harganya. Mematikan suatu opsi tidak menurunkan harga.",
    "{inc} included · each +{step} costs ${price}": "{inc} termasuk · setiap +{step} seharga ${price}",
    "Extra packs (0 = none)": "Paket tambahan (0 = tidak ada)",
    "Total: {n}": "Total: {n}",
    "Features": "Fitur",
    "Your price": "Harga Anda",
    "Base plan": "Paket dasar",
    "Subscribe for ${price}/month": "Berlangganan ${price}/bulan",
    "AI requests a day": "Permintaan AI per hari",
    "Documents": "Dokumen",
    "Members per case": "Anggota per kasus",
    "People per meeting": "Peserta per rapat",
    "Voice minutes a month": "Menit suara per bulan",
    "Calendar assistant": "Asisten kalender",
    "Voice input": "Input suara",
    "Document review": "Tinjauan dokumen",
    "Auto-detect": "Deteksi otomatis",
    # settings
    "Voice input language": "Bahasa input suara",
    "The language you speak when you dictate. Auto-detect works for most recordings; pick one if names or short "
    "phrases are misheard.":
        "Bahasa yang Anda ucapkan saat mendikte. Deteksi otomatis cocok untuk kebanyakan rekaman; pilih satu bahasa "
        "jika nama atau frasa pendek salah dikenali.",
    "Voice language saved.": "Bahasa suara disimpan.",
    "{used} of {cap} voice minutes used this month.": "{used} dari {cap} menit suara terpakai bulan ini.",
    # microphone widget
    "Speak instead of typing": "Bicara, tidak perlu mengetik",
    "Language: {lang} (change it in Settings). {used} of {cap} voice minutes used this month. Audio is not stored.":
        "Bahasa: {lang} (ubah di Pengaturan). {used} dari {cap} menit suara terpakai bulan ini. Audio tidak disimpan.",
    "Record": "Rekam",
    "Transcribing…": "Menyalin ucapan…",
    # calendar assistant
    "Tell me about a meeting in your own words, in Bahasa Indonesia or English, for example “besok jam 12 saya ada "
    "meeting”. I add it, then ask who it is with and where. Each message uses one AI request.":
        "Ceritakan rapat Anda dengan kata-kata sendiri, dalam Bahasa Indonesia atau Inggris, misalnya “besok jam 12 "
        "saya ada meeting”. Saya menambahkannya, lalu menanyakan dengan siapa dan di mana. Setiap pesan memakai satu "
        "permintaan AI.",
    "Tell me about a meeting…": "Ceritakan tentang sebuah rapat…",
    "Adding to your calendar…": "Menambahkan ke kalender Anda…",
    "I couldn't find a meeting in that. Try: “Tomorrow at 12 I have a meeting.”":
        "Saya tidak menemukan rapat di pesan itu. Coba: “Besok jam 12 saya ada meeting.”",
    "That time has already passed. Which day and time did you mean?":
        "Waktu itu sudah lewat. Hari dan jam berapa maksud Anda?",
    "What time is it?": "Jam berapa?",
    "Which day is it?": "Hari apa?",
    "Which day and time is it?": "Hari dan jam berapa?",
    "OK, “{title}” stays as it is.": "Baik, “{title}” tidak diubah.",
    "Added “{title}” on {when}.": "“{title}” ditambahkan pada {when}.",
    "Updated “{title}”.": "“{title}” diperbarui.",
    "Invited: {who}.": "Diundang: {who}.",
    "Noted in the event: {who}. They aren't LawVault teammates, so no invitation was sent.":
        "Dicatat di acara: {who}. Mereka bukan rekan tim LawVault, jadi undangan tidak dikirim.",
    "Place: {place}.": "Tempat: {place}.",
    "Heads up: this overlaps with “{title}”.": "Perhatian: jadwal ini bertabrakan dengan “{title}”.",
    "Who is it with, and where?": "Dengan siapa, dan di mana?",
    "Who is it with?": "Dengan siapa?",
    "Where is it?": "Di mana?",
    "The calendar assistant is switched off in your plan. You can turn it on under Settings → Billing.":
        "Asisten kalender dimatikan di paket Anda. Anda dapat menyalakannya di Pengaturan → Tagihan.",
    "Document review is switched off in your plan. You can turn it on under Settings → Billing.":
        "Tinjauan dokumen dimatikan di paket Anda. Anda dapat menyalakannya di Pengaturan → Tagihan.",
    "Case analysis is switched off in your plan. You can turn it on under Settings → Billing.":
        "Analisis kasus dimatikan di paket Anda. Anda dapat menyalakannya di Pengaturan → Tagihan.",
    # messages returned by the backend
    "The calendar assistant is not part of your plan.": "Asisten kalender bukan bagian dari paket Anda.",
    "Voice input is not part of your plan.": "Input suara bukan bagian dari paket Anda.",
    "That recording is empty or too large.": "Rekaman itu kosong atau terlalu besar.",
    "Recordings can be at most 2 minutes. Please record a shorter one.":
        "Rekaman maksimal 2 menit. Silakan rekam yang lebih pendek.",
    "Local voice input needs faster-whisper. Run: pip install faster-whisper":
        "Input suara lokal memerlukan faster-whisper. Jalankan: pip install faster-whisper",
    "Voice input is not configured. Add OPENAI_API_KEY to your .env file, or set WHISPER_BACKEND=local.":
        "Input suara belum dikonfigurasi. Tambahkan OPENAI_API_KEY ke berkas .env, atau setel WHISPER_BACKEND=local.",
    "Monthly voice limit reached for your plan. Upgrade for more voice minutes.":
        "Batas suara bulanan paket Anda tercapai. Tingkatkan paket untuk menambah menit suara.",
    "The voice service is unavailable right now. Please try again.":
        "Layanan suara sedang tidak tersedia. Silakan coba lagi.",
    "No speech was detected. Please try again.": "Tidak ada ucapan terdeteksi. Silakan coba lagi.",
    "No access to that event.": "Tidak ada akses ke acara itu.",
    "Event updated.": "Acara diperbarui.",
    "Unknown option in the plan.": "Opsi paket tidak dikenal.",
})
ID.update({"English": "English", "Bahasa Indonesia": "Bahasa Indonesia"})  # language names stay in their own language

# ---------- Google / Apple calendar sync, Pro-first rule ----------
ID.update({
    "Sync": "Sinkron",
    "Google and Apple calendar sync": "Sinkronisasi kalender Google dan Apple",
    "Available after your first month on Pro.": "Tersedia setelah bulan pertama Anda di Pro.",
    "Up to date": "Sudah terbaru",
    "Will retry": "Akan dicoba lagi",
    "Reconnect needed": "Perlu disambungkan ulang",
    "Paused": "Dijeda",
    "Google Calendar": "Google Calendar",
    "Apple Calendar": "Apple Calendar",
    "Apple Calendar (iCloud)": "Apple Calendar (iCloud)",
    "never": "belum pernah",
    "Last synced: {when}": "Terakhir disinkronkan: {when}",
    "Sync now": "Sinkronkan sekarang",
    "Syncing…": "Menyinkronkan…",
    "Synced: {a} new, {b} updated, {c} sent.": "Tersinkron: {a} baru, {b} diperbarui, {c} terkirim.",
    "Disconnect": "Putuskan",
    "Also remove events that came from this calendar": "Hapus juga acara yang berasal dari kalender ini",
    "Connect a calendar": "Hubungkan kalender",
    "Connect Google Calendar": "Hubungkan Google Calendar",
    "Continue to Google": "Lanjut ke Google",
    "Connect Apple Calendar": "Hubungkan Apple Calendar",
    "Connecting…": "Menghubungkan…",
    "Apple ID": "Apple ID",
    "App-specific password": "Kata sandi khusus aplikasi",
    "See plans": "Lihat paket",
    "Calendar sync is switched off in your plan. You can turn it on under Settings → Billing.":
        "Sinkronisasi kalender dimatikan di paket Anda. Anda dapat menyalakannya di Pengaturan → Tagihan.",
    "Syncing with Google and Apple Calendar is included in the Pro plan.":
        "Sinkronisasi dengan Google dan Apple Calendar termasuk dalam paket Pro.",
    "Two-way sync: events you add here appear in Google or Apple Calendar, and events from there appear here. "
    "Titles, notes, locations and times are shared with that service; attendees are not, so nobody gets an e-mail "
    "from it. Case deadlines are not synced.":
        "Sinkronisasi dua arah: acara yang Anda tambahkan di sini muncul di Google atau Apple Calendar, dan acara dari "
        "sana muncul di sini. Judul, catatan, lokasi, dan waktu dibagikan ke layanan itu; peserta tidak, sehingga tidak "
        "ada yang menerima email darinya. Tenggat kasus tidak disinkronkan.",
    "Google sign-in is not set up on this server yet. An administrator needs to add GOOGLE_CLIENT_ID and "
    "GOOGLE_CLIENT_SECRET to the .env file.":
        "Masuk dengan Google belum disiapkan di server ini. Administrator perlu menambahkan GOOGLE_CLIENT_ID dan "
        "GOOGLE_CLIENT_SECRET ke berkas .env.",
    "You sign in on Google's own page. LawVault never sees your Google password.":
        "Anda masuk di halaman Google sendiri. LawVault tidak pernah melihat kata sandi Google Anda.",
    "Create an app-specific password at appleid.apple.com → Sign-In and Security → App-Specific Passwords. Your "
    "normal Apple ID password is never needed. It is stored encrypted.":
        "Buat kata sandi khusus aplikasi di appleid.apple.com → Masuk dan Keamanan → Kata Sandi Khusus Aplikasi. "
        "Kata sandi Apple ID biasa Anda tidak pernah diperlukan. Kata sandi ini disimpan terenkripsi.",
    # messages from the backend
    "Calendar sync is not part of your plan.": "Sinkronisasi kalender bukan bagian dari paket Anda.",
    "Calendar sync is not part of your current plan.": "Sinkronisasi kalender bukan bagian dari paket Anda saat ini.",
    "You can connect up to 4 calendars.": "Anda dapat menghubungkan hingga 4 kalender.",
    "No such user.": "Pengguna tidak ditemukan.",
    "This sign-in link is no longer valid. Please start again.":
        "Tautan masuk ini sudah tidak berlaku. Silakan mulai lagi.",
    "Google sign-in is not configured.": "Masuk dengan Google belum dikonfigurasi.",
    "Google sign-in was cancelled.": "Masuk dengan Google dibatalkan.",
    "Could not reach Google. Please try again.": "Tidak dapat menghubungi Google. Silakan coba lagi.",
    "Google did not allow offline access. Remove LawVault from your Google account permissions and try again.":
        "Google tidak mengizinkan akses offline. Hapus LawVault dari izin akun Google Anda lalu coba lagi.",
    "Google Calendar connected.": "Google Calendar terhubung.",
    "Apple Calendar connected.": "Apple Calendar terhubung.",
    "Enter your Apple ID and an app-specific password.": "Masukkan Apple ID dan kata sandi khusus aplikasi.",
    "No calendar that can hold events was found in that iCloud account.":
        "Tidak ditemukan kalender yang dapat menyimpan acara di akun iCloud itu.",
    "Apple did not accept that Apple ID or app-specific password.":
        "Apple tidak menerima Apple ID atau kata sandi khusus aplikasi itu.",
    "Apple did not accept the saved sign-in.": "Apple tidak menerima data masuk yang tersimpan.",
    "Could not reach iCloud.": "Tidak dapat menghubungi iCloud.",
    "iCloud is unavailable right now.": "iCloud sedang tidak tersedia.",
    "Google no longer accepts this connection.": "Google tidak lagi menerima koneksi ini.",
    "Google refused access to the calendar.": "Google menolak akses ke kalender.",
    "Please connect this calendar again.": "Silakan hubungkan kalender ini lagi.",
    "The calendar service is unavailable right now. LawVault will retry.":
        "Layanan kalender sedang tidak tersedia. LawVault akan mencoba lagi.",
    "Sync stopped: the other calendar returned far fewer events than expected. Nothing was deleted.":
        "Sinkronisasi dihentikan: kalender lain mengembalikan acara jauh lebih sedikit dari yang diharapkan. "
        "Tidak ada yang dihapus.",
    "Pick your own is available after your first Pro month. Subscribe to Pro first.":
        "Pilih sendiri tersedia setelah bulan Pro pertama Anda. Berlangganan Pro terlebih dahulu.",
})

# ---------- files, Google Docs, AI detector, news (2026-11-25) ----------
ID.update({
    "Files": "Berkas", "News": "Berita", "AI detector": "Detektor AI",
    # files
    "Every document you can open, in one place: search, upload, import and export.":
        "Semua dokumen yang dapat Anda buka, di satu tempat: cari, unggah, impor, dan ekspor.",
    "Save to": "Simpan ke", "My files (private)": "Berkas saya (pribadi)",
    "{where} · uploaded by {who} · {n} characters": "{where} · diunggah oleh {who} · {n} karakter",
    "Preview": "Pratinjau", "Download": "Unduh", "AI review": "Tinjauan AI",
    "Review as Word": "Tinjauan sebagai Word", "Review as PDF": "Tinjauan sebagai PDF",
    "Check for AI-written text": "Periksa teks buatan AI",
    "That file is no longer available.": "Berkas itu sudah tidak tersedia.",
    "Rename or move": "Ubah nama atau pindahkan", "Name": "Nama", "Rename": "Ubah nama",
    "Move to": "Pindahkan ke", "Move": "Pindahkan", "Add files": "Tambah berkas",
    "Upload files": "Unggah berkas", "Import from Google Docs": "Impor dari Google Docs",
    "PDF, Word, TXT or MD, up to {mb} MB each": "PDF, Word, TXT atau MD, hingga {mb} MB per berkas",
    "Save {n} file(s)": "Simpan {n} berkas", "Saved {n} file(s).": "{n} berkas disimpan.",
    "Paste the link of a Google Doc. It must be shared as “Anyone with the link can view”. LawVault never asks for your Google password.":
        "Tempel tautan Google Doc. Dokumen harus dibagikan sebagai “Siapa saja yang memiliki link dapat melihat”. "
        "LawVault tidak pernah meminta kata sandi Google Anda.",
    "Google Docs link": "Tautan Google Docs", "Import": "Impor", "Fetching the document…": "Mengambil dokumen…",
    "Search": "Cari", "Search names and contents…": "Cari nama dan isi…", "Show": "Tampilkan",
    "All files": "Semua berkas", "Uploaded by me": "Diunggah oleh saya",
    "Private (not in a case)": "Pribadi (bukan dalam kasus)", "Any case": "Kasus apa pun",
    "No files match.": "Tidak ada berkas yang cocok.", "Added": "Ditambahkan", "Reviewed": "Ditinjau",
    "Match": "Cocok",
    "Showing the newest {n} of {total}. Narrow the search to see others.":
        "Menampilkan {n} terbaru dari {total}. Persempit pencarian untuk melihat yang lain.",
    "Select a row to preview, download, rename or move a file.":
        "Pilih satu baris untuk melihat pratinjau, mengunduh, mengubah nama, atau memindahkan berkas.",
    "Only the person who uploaded a document can move it.": "Hanya pengunggah dokumen yang dapat memindahkannya.",
    "You need editor access to that case.": "Anda memerlukan akses editor ke kasus itu.",
    "Moved.": "Dipindahkan.",
    "That file is not a real Word document.": "Berkas itu bukan dokumen Word yang asli.",
    "Could not read that Word document.": "Tidak dapat membaca dokumen Word itu.",
    "Only PDF, Word (.docx), TXT and MD files are allowed.": "Hanya berkas PDF, Word (.docx), TXT, dan MD yang diizinkan.",
    "That doesn't look like a Google Docs link (docs.google.com/document/d/…).":
        "Itu tidak tampak seperti tautan Google Docs (docs.google.com/document/d/…).",
    "Couldn't open that document. In Google Docs choose Share, set General access to “Anyone with the link” (Viewer) and try again, or download it as .docx and upload it instead.":
        "Tidak dapat membuka dokumen itu. Di Google Docs pilih Bagikan, atur Akses umum ke “Siapa saja yang memiliki link” "
        "(Pelihat) lalu coba lagi, atau unduh sebagai .docx dan unggah.",
    "Couldn't reach Google Docs. Check your connection and try again.":
        "Tidak dapat menghubungi Google Docs. Periksa koneksi Anda dan coba lagi.",
    "That document is too large (max 5 MB of text).": "Dokumen itu terlalu besar (maks. 5 MB teks).",
    "That document is empty.": "Dokumen itu kosong.",
    # detector
    "Check whether a text reads as written by an AI. A quick statistical check, plus an optional second opinion from the AI.":
        "Periksa apakah suatu teks terbaca seperti ditulis AI. Pemeriksaan statistik cepat, ditambah pendapat kedua dari AI (opsional).",
    "No AI detector is reliable. Formal legal drafting, non-native writing and edited AI text all give false results. Treat this as a prompt for your own judgement, never as proof.":
        "Tidak ada detektor AI yang andal. Penyusunan dokumen hukum formal, tulisan non-penutur asli, dan teks AI yang disunting "
        "dapat memberi hasil keliru. Anggap ini sebagai bahan pertimbangan Anda, bukan bukti.",
    "Paste text": "Tempel teks", "A file": "Sebuah berkas", "Text to check": "Teks yang diperiksa",
    "Paste the text here…": "Tempel teks di sini…", "A saved file": "Berkas tersimpan", "— choose —": "— pilih —",
    "Or upload one": "Atau unggah satu", "Paste some text or choose a file to check.": "Tempel teks atau pilih berkas untuk diperiksa.",
    "Checking: {name}": "Memeriksa: {name}",
    "Add at least {n} words for a meaningful result.": "Tambahkan minimal {n} kata agar hasilnya bermakna.",
    "AI-writing score": "Skor tulisan AI", "Based on {n} words. {d}": "Berdasarkan {n} kata. {d}",
    "What the check looked at": "Yang diperiksa", "AI-like": "mirip AI",
    "Sentences with stock phrases": "Kalimat dengan frasa klise AI", "Second opinion": "Pendapat kedua",
    "Asks the AI to judge the text. Personal data is masked first. Uses 1 of your {cap} daily AI requests.":
        "Meminta AI menilai teks. Data pribadi disamarkan lebih dulu. Memakai 1 dari {cap} permintaan AI harian Anda.",
    "Ask the AI": "Tanya AI", "Reading…": "Membaca…", "AI opinion": "Pendapat AI",
    "Likely AI-written": "Kemungkinan besar ditulis AI", "Possibly AI-assisted": "Mungkin dibantu AI",
    "Likely human-written": "Kemungkinan besar ditulis manusia",
    "Sentence rhythm": "Irama kalimat", "Vocabulary variety": "Ragam kosakata",
    "Stock phrases": "Frasa klise", "Repeated sentence openers": "Pembuka kalimat berulang",
    "Informal markers": "Penanda informal",
    "People mix short and long sentences; models tend to keep them even.":
        "Manusia mencampur kalimat pendek dan panjang; model cenderung menjaganya seragam.",
    "Unusually uniform or repetitive wording.": "Pilihan kata yang tidak wajar seragam atau berulang.",
    "Phrases such as “it is important to note” or “penting untuk dicatat”.":
        "Frasa seperti “it is important to note” atau “penting untuk dicatat”.",
    "Many sentences starting the same way.": "Banyak kalimat yang dimulai dengan cara yang sama.",
    "Contractions and casual asides are rare in AI output (weak signal).":
        "Singkatan dan selingan kasual jarang muncul pada tulisan AI (sinyal lemah).",
    "The AI's answer couldn't be read. Please try again.": "Jawaban AI tidak dapat dibaca. Silakan coba lagi.",
    # news
    "Current affairs in English and Bahasa Indonesia, filtered to the topics you follow.":
        "Berita terkini dalam bahasa Inggris dan Indonesia, disaring sesuai topik yang Anda ikuti.",
    "Headlines from ANTARA, CNN Indonesia and BBC. Refreshed every 10 minutes. Tap a headline to read the full story on the publisher's site.":
        "Berita utama dari ANTARA, CNN Indonesia, dan BBC. Diperbarui setiap 10 menit. Ketuk judul untuk membaca berita lengkap di situs penerbit.",
    "Refresh": "Segarkan", "Choose what you see": "Pilih yang ingin Anda lihat", "Languages": "Bahasa",
    "Topics": "Topik", "Save my choices": "Simpan pilihan saya", "Loading headlines…": "Memuat berita utama…",
    "No headlines right now. The publishers may be unreachable; try again in a minute.":
        "Belum ada berita utama. Penerbit mungkin tidak dapat dijangkau; coba lagi sebentar lagi.",
    "Law & politics": "Hukum & politik", "Finance & business": "Keuangan & bisnis", "Technology": "Teknologi",
    "Sports": "Olahraga", "World": "Dunia", "Top stories": "Berita utama",
    "Preferences saved.": "Preferensi disimpan.",
    "Pick at least one language and one topic.": "Pilih setidaknya satu bahasa dan satu topik.",
})
ID.update({
    "Upload a contract (PDF, Word or TXT, up to {mb} MB)": "Unggah kontrak (PDF, Word atau TXT, hingga {mb} MB)",
    "Upload PDF, Word or TXT to this case (up to {mb} MB)": "Unggah PDF, Word atau TXT ke kasus ini (hingga {mb} MB)",
})
