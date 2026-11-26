"""Central configuration. Secrets come from environment / .env, never from code."""
from __future__ import annotations
import hashlib, os
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")

DATA_DIR = Path(os.getenv("LAWVAULT_DATA_DIR", str(BASE / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "lawvault.db"

DEV_MODE = os.getenv("DEV_MODE", "1") == "1"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
LEGAL_ENTITY = os.getenv("LEGAL_ENTITY", "LawVault").strip()          # name of the company running the service (shown in the Terms)
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "").strip() or ADMIN_EMAIL    # where users send legal / privacy requests
GOVERNING_LAW = os.getenv("GOVERNING_LAW", "the Republic of Indonesia").strip()
HIBP_CHECK = os.getenv("HIBP_CHECK", "1") == "1"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")  # fast; "thinking" models can take ~50 s
# Tried in order when the main model is busy (503), rate-limited (429), retired (404) or too slow
GEMINI_FALLBACK_MODELS = [m.strip() for m in os.getenv(
    "GEMINI_FALLBACK_MODELS", "gemini-flash-lite-latest,gemini-3.5-flash").split(",") if m.strip()]
# Backup AI (Groq, OpenAI-compatible): used automatically when Gemini is down, busy, rate-limited or out of quota.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_FALLBACK_MODELS = [m.strip() for m in os.getenv(
    "GROQ_FALLBACK_MODELS", "openai/gpt-oss-20b,qwen/qwen3.8-27b").split(",") if m.strip()]
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", "30"))  # seconds per model before trying the next
# Voice to text (Whisper). "openai" sends the clip to OpenAI's API; "local" runs faster-whisper on this machine so
# audio never leaves it (pip install faster-whisper).
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WHISPER_BACKEND = os.getenv("WHISPER_BACKEND", "openai").strip().lower()
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")        # model name for the API
WHISPER_LOCAL_SIZE = os.getenv("WHISPER_LOCAL_SIZE", "small")   # tiny / base / small / medium for local
WHISPER_TIMEOUT = int(os.getenv("WHISPER_TIMEOUT", "60"))
MAX_VOICE_SECONDS = 120          # longest single recording
MAX_VOICE_BYTES = 10 * 1024 * 1024
# Calendar sync. Google needs an OAuth client (Google Cloud Console > APIs > Credentials > Web application) whose
# redirect URI is exactly GOOGLE_REDIRECT_URI. Apple needs nothing here: each user brings an app-specific password.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8502/calendar")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "300"))          # seconds between background syncs
SYNC_HTTP_TIMEOUT = int(os.getenv("SYNC_HTTP_TIMEOUT", "30"))
SMTP = dict(
    host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
    port=int(os.getenv("SMTP_PORT", "587")),
    user=os.getenv("SMTP_USER", ""),
    password=os.getenv("SMTP_PASSWORD", ""),
)

# Security parameters (one place so they are easy to explain in the exam)
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60
OTP_TTL_SECONDS = 5 * 60
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN = 30
OTP_MAX_PER_HOUR = 5
SESSION_IDLE_SECONDS = 30 * 60
SESSION_MAX_SECONDS = 12 * 3600
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))  # keep .streamlit/config.toml maxUploadSize in step
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "500"))
MAX_AI_INPUT_CHARS = 150_000  # ~40k tokens: fits Gemini comfortably, keeps free-tier calls quick


def _load_key() -> bytes:
    env = os.getenv("APP_ENCRYPTION_KEY")
    if env:
        return env.encode()
    p = DATA_DIR / "app.key"
    if p.exists():
        return p.read_bytes().strip()
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    p.write_bytes(key)
    os.chmod(p, 0o600)
    return key


APP_KEY = _load_key()
HMAC_KEY = hashlib.sha256(b"lawvault-hmac|" + APP_KEY).digest()
