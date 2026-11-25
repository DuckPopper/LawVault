# ⚖️ LawVault

A secure, multi-user Streamlit workspace for lawyers. Teams discuss cases in encrypted group chats, share
documents, track deadlines and tasks, and schedule meetings through permission-based shared calendars. A built-in
AI (Google Gemini free tier) answers legal questions, analyses contracts, summarizes whole cases, answers `@ai`
in the team chat and pulls deadlines out of documents. The **Case analysis** page runs a full matter workup:
case analysis (*analisis kasus*), a visual timeline (*pembuatan timeline*), the legal basis (*dasar hukum*), a
risk register with a severity × likelihood matrix (*risiko hukum*), legal drafting (somasi, gugatan, legal opinion,
surat kuasa, …) and a strategy recommendation (*rekomendasi strategi*), in Bahasa Indonesia or English, with
Indonesian law as the default jurisdiction.
The whole interface is available in **English and Bahasa Indonesia** (login page, sidebar and Settings → General),
including dates, notifications and the privacy policy; AI answers follow the chosen language. Login uses a password plus a one-time code (email or
authenticator app), with Discord-style presence, live notifications and subscription plans.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit: set ADMIN_EMAIL, add GEMINI_API_KEY for the AI
python seed_demo.py           # optional demo accounts, cases (incl. an Indonesian matter), calendar, deadlines
streamlit run app.py          # run from this folder so .streamlit/config.toml (theme) is used
```

**Demo accounts** (from `seed_demo.py`, local demo only): `admin@lawvault.test` (case owner),
`partner@lawvault.test` (editor), `associate@lawvault.test` (viewer), all with the password in `seed_demo.py`.
With `DEV_MODE=1` the email code is shown on screen; set `DEV_MODE=0` plus SMTP settings to email it for real.

**Tests:** `python -m pytest tests -q` → 137 security and feature tests.
**Static scan:** `bandit -r . -x ./tests,./.venv -ll` → no issues.
**CI:** `.github/workflows/ci.yml` runs both on every push once the project is on GitHub.

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for a 3-minute presentation walkthrough.

## Files

| File | Purpose |
|---|---|
| `app.py` | Entry point: session gate (tab or cookie) → navigation, status picker, live notification bell |
| `config.py` | All settings and security limits in one place; loads secrets from `.env` |
| `db.py` | SQLite schema, in-place migrations, parameterised queries, audit log |
| `crypto.py` | Fernet encryption at rest, bcrypt passwords, token hashing |
| `auth.py` | Signup, login, lockout, sessions, device list, new-device alerts, password reset/change |
| `otp.py` | Email one-time codes: generate, hash, expire, rate-limit, send |
| `twofa.py` | Optional authenticator-app 2FA (TOTP) with replay protection |
| `security_checks.py` | Breached-password check (Have I Been Pwned, k-anonymity) |
| `session_cookie.py` | Keeps you logged in across refreshes; device labels |
| `presence.py` | Online / Idle / Do Not Disturb / Invisible |
| `notify.py` | In-app notifications (encrypted, grouped) |
| `cases.py` | Cases, roles (owner/editor/viewer), group chat, documents, deadlines & tasks |
| `cal.py` | Calendars: visibility, access requests, meeting invites, find-a-time |
| `subscription.py` | Plans, limits, daily AI quota, mock checkout |
| `ai.py` | Gemini client, Q&A, contract analysis, case summary, `@ai` in chat, deadline extraction |
| `cal_ai.py` | Calendar assistant: "besok jam 12 saya ada meeting" adds the event, then asks who and where |
| `calsync.py`, `calproviders.py` | Two-way Google and Apple (iCloud CalDAV) calendar sync, Pro plan and up |
| `voice.py` | Whisper voice to text (OpenAI API or local faster-whisper), language chosen in Settings, metered per month |
| `i18n.py`, `i18n_id.py` | Interface language: `t()` helper, localised dates, per-user setting; the Indonesian strings |
| `legal.py` | Case analysis toolkit: six tools, prompts per jurisdiction, validated timeline / risk output, encrypted results |
| `seed_analysis_demo.py` | Demo matter *PT Sentosa Abadi v. PT Maju Logistik* for the Case analysis page |
| `privacy.py` | PII redaction, data export, account deletion |
| `docutil.py` | Safe upload parsing (size, magic bytes, page limit) |
| `ui.py` | Shared stylesheet and layout helpers (page header, stat cards, list rows) |
| `views/` | Streamlit pages; `settings.py` holds General, Account, Privacy and Billing; `calendar_grid.py` renders the Day/Week/Month calendar |
| `tests/` | 137 tests |
| `.streamlit/config.toml` | Theme (Inter font), 50 MB upload cap, XSRF protection, hides developer menu |

## Security & data protection

| Threat | Defence |
|---|---|
| Stolen database | Passwords bcrypt-hashed; OTPs & session tokens hashed; case content, chat, documents, tasks, calendar titles, notifications, AI history, case analyses and 2FA secrets Fernet-encrypted |
| Password guessing | 10+ char policy, common-password list, breached-password check, lockout after 5 failures for 15 min |
| Stolen password | Second factor: email code (5-min expiry, single use, attempt + resend limits) or optional authenticator app (replay-protected, counts toward lockout) |
| Someone else logging in | New-device alert (in-app, and email when SMTP is on); device list with per-device logout; "log out all devices" |
| Account enumeration | Identical messages for wrong email / wrong password / reset / invites; constant-time bcrypt check |
| Session hijack | Random 256-bit tokens stored hashed; 30-min idle + 12-h absolute timeout; SameSite=Strict cookie; background refreshes don't extend the idle timer |
| Seeing other users' data (IDOR) | Random UUID ids; every read/write checks case membership and role server-side |
| Over-privileged members | Case roles: owner / editor / viewer (read-only); only the owner manages members and roles |
| Snooping on schedules | Calendars private by default; sharing only with case teammates; owner-approved requests (busy-only or titles), revocable; private notes never shared |
| Spam from strangers | Invites, mentions and calendar requests only between people who share a case; chat notifications grouped |
| SQL injection | Parameterised queries only, with fixed SQL text (bandit-clean) |
| Malicious uploads | Extension + magic-byte check, 50 MB / 500 page caps (also enforced by Streamlit), encrypted PDFs rejected |
| Prompt injection via documents/chat | Untrusted text wrapped in `<document>` tags; system prompt forbids following it; AI output parsed defensively |
| PII leaking to the AI provider | Emails, phones, SSNs, card numbers redacted before sending |
| Nosy admins | Admin page shows metadata and audit events only, never content |
| Secrets in git | `.env`, keys and database are git-ignored |
| GDPR-style rights | Consent at signup, JSON export, permanent account deletion (cascades to all personal data) |

## Known limitations (be honest in the write-up)

- One app-wide encryption key: whoever holds the server key can decrypt. Upgrade path: per-user keys derived from passwords.
- Free AI tiers may retain prompts. For privileged material use a paid no-training tier or a local model (Ollama).
- The login cookie can't be HttpOnly: Streamlit can't set those itself (it needs a reverse proxy). It is SameSite=Strict and the token is useless once the session ends.
- On localhost Streamlit doesn't report the visitor's IP, so the device list shows "unknown IP" until deployed.
- Presence and chat update by polling (every 3–30 s), not true push.
- Checkout is mocked; production would use Stripe Checkout + webhooks.
- SQLite suits a demo; production would use Postgres.
- Event titles are encrypted but times are not (needed for free/busy); all times use the server's time zone.
- If the breached-password service is unreachable, signup is allowed (fail-open) with the other rules still applied.

## Languages

Strings in the code are written in English and wrapped in `t("…")`; the English text is the key into
`i18n_id.ID`, so an untranslated string falls back to English instead of breaking. `tests/test_i18n.py` fails if a
string passed to `t()` (or a backend message shown to users) has no Indonesian entry. The language is saved per user
(`users.lang`), chosen at sign-up from the login-page switch, and can be changed in the sidebar or Settings → General.
To add another language, add a `LANGS` entry, day and month names in `i18n.py`, and a dictionary like `i18n_id.py`.

## Files, Google Docs, AI detector and News (added 2026-11-25)
- **Files** (`views/files_ui.py`): one list of every document you can open (yours + your cases'), search by name or text, multi-file upload (PDF, Word, TXT, MD), rename / move, download as Word, PDF or TXT (and the AI review as Word/PDF).
- **Google Docs import**: paste a link to a doc shared as "Anyone with the link can view" (`gdocs.py`). Private docs: download as .docx and upload.
- **AI detector** (`detector.py`): offline statistical check plus an optional AI second opinion. A prompt for judgement, not proof.
- **News** (`news.py`): public RSS from ANTARA, CNN Indonesia and BBC (no API key), per-user language and topic choices.
- Extra dependencies: `python-docx`, `reportlab` (<4.3 for Python 3.9), `defusedxml`.
