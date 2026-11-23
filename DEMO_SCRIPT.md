# LawVault — 3-minute demo script

**Before you present**
- Run `python seed_demo.py` on a fresh database (delete `data/lawvault.db` first) and start the app.
- Have a Gemini key in `.env`, or skip the AI steps.
- Open two browser windows: a normal one and a private one, side by side.
- Have a terminal ready with `python -m pytest tests -q`.

---

### 1. Secure login (30 s)
- **Window 1:** sign up a new account with the password `password123`. *"Weak and common passwords are rejected, and so are passwords found in real data breaches; only the first 5 characters of a hash leave the server."*
- Log in as `admin@lawvault.test`. *"Password, then a one-time code. In production the code is emailed; dev mode shows it on screen."*
- Refresh the page. *"Still logged in: the session survives a refresh, but it's a hashed token with idle and absolute timeouts."*

### 2. Multi-user collaboration (60 s)
- **Window 2 (private):** log in as `partner@lawvault.test`.
- Both windows: **Cases & Team Chat**. Send a message from each. *"Live team chat, encrypted at rest. The dots show who's online."*
- Partner: set the status to **🔴 Do Not Disturb**. Admin's window shows partner in red. *"Discord-style presence, and DND stops pop-ups."*
- Admin: **Team** tab. *"Roles: the associate is a viewer, so it's read-only. Only the owner manages members."*
- Admin: **Deadlines & tasks**. Tick the task. *"Deadlines also appear on everyone's calendar and dashboard."*

### 3. AI for the team (40 s)
- In the chat: `@ai what is the limitation period for breach of contract?` *"The answer is posted for the whole team. Personal data is masked first, and text inside documents can't hijack the AI."*
- Click **Brief me on this case**. *"A briefing from the whole chat, documents and deadlines."*
- **Documents** → **Find deadlines**. *"The AI pulls dates out of a contract. Its output is validated before anything is saved."*

### 3b. Case analysis (60 s)
- **AI → Case analysis**, case **PT Sentosa Abadi v. PT Maju Logistik**, jurisdiction Indonesia, Bahasa Indonesia.
- **Run full analysis**. *"Five steps, each building on the last: analisis kasus, timeline, dasar hukum, risiko hukum, strategi. It keeps running if I switch pages."*
- **Timeline**: *"Built from the chat and the contract; upcoming dates go straight into the case deadlines."*
- **Legal risks**: the matrix. *"Severity times likelihood, each risk with its legal basis and a mitigation."*
- **Legal drafting** → Somasi → **Draft it**. *"A complete first draft in the Indonesian format, with placeholders for missing facts."*
- *"Results are encrypted and shared with the case team; a viewer can read them but not run new ones."*

### 3c. Two languages (20 s)
- Sidebar → language picker → **Bahasa Indonesia**. *"The whole interface switches, including dates, notifications and the privacy policy; the AI now answers in Indonesian too. The choice is saved per user and offered on the login page."*

### 4. Calendar (30 s)
- **Calendar → Team calendars**: the partner shows only "Busy". *"Private by default. You choose busy-only or titles, and only for case teammates."*
- **Find a time** → pick both people → **Book**. *"Finds a slot where everyone is free and sends invites."*
- **Sharing**: approve the associate's request as busy-only.

### 5. Security controls (20 s)
- **Settings → Account**: the device list. *"Log out a single device, or all of them. A login from a new device sends an alert."* Show the **authenticator QR** (optional 2FA).
- **Admin** page: *"Admins see account data and the audit log, never case content."*
- Terminal: run the tests. *"95 tests, including proof that users can't see each other's data, plus a clean Bandit security scan in CI."*

### Close (10 s)
*"Known limitations are listed in the README: one server key, free AI tier retention, and a cookie that can't be HttpOnly without a proxy. Each one has an upgrade path."*
