"""Voice to text with Whisper.

Two backends, chosen with WHISPER_BACKEND in .env:
  openai - the clip is sent to OpenAI's transcription API (needs OPENAI_API_KEY).
  local  - faster-whisper runs on this machine, so the audio never leaves it (pip install faster-whisper).

Privacy: audio is held in memory only for the call. It is never written to disk or the database; only the
resulting text is used, and that text goes through the normal AI path (personal data masked) if it is sent on.
Usage is metered in seconds per month against the plan's `voice_minutes`; a failed call is refunded.
"""
from __future__ import annotations
import io
import math
import wave
import requests
import config, db, subscription

# Language hint for Whisper. "auto" lets it detect the language. More codes can be added here.
LANGS = {"auto": "Auto-detect", "id": "Bahasa Indonesia", "en": "English"}
_local_model = None


def valid_lang(code) -> str:
    return code if code in LANGS else "auto"


def get_lang(user) -> str:
    try:
        return valid_lang(user["voice_lang"])
    except (KeyError, IndexError):
        return "auto"


def set_lang(user_id: str, code: str) -> bool:
    if code not in LANGS:
        return False
    with db.conn() as c:
        c.execute("UPDATE users SET voice_lang=? WHERE id=?", (code, user_id))
    return True


def clip_seconds(audio: bytes) -> int:
    """Length of a WAV clip, rounded up. Anything that isn't a readable WAV is estimated at 16 kHz mono 16-bit."""
    try:
        with wave.open(io.BytesIO(audio)) as w:
            return max(1, math.ceil(w.getnframes() / max(1, w.getframerate())))
    except (wave.Error, EOFError):
        return max(1, math.ceil(len(audio) / 32000))


def _openai(audio: bytes, filename: str, lang: str) -> str:
    data = {"model": config.WHISPER_MODEL}
    if lang != "auto":
        data["language"] = lang
    r = requests.post("https://api.openai.com/v1/audio/transcriptions",
                      headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                      files={"file": (filename, audio, "audio/wav")}, data=data, timeout=config.WHISPER_TIMEOUT)
    r.raise_for_status()
    return str(r.json().get("text", "")).strip()


def _local(audio: bytes, lang: str) -> str:
    global _local_model
    if _local_model is None:
        from faster_whisper import WhisperModel
        _local_model = WhisperModel(config.WHISPER_LOCAL_SIZE, compute_type="int8")
    segments, _ = _local_model.transcribe(io.BytesIO(audio), language=None if lang == "auto" else lang)
    return " ".join(s.text.strip() for s in segments).strip()


def _backend_ready():
    """None if usable, else the message to show."""
    if config.WHISPER_BACKEND == "local":
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return "Local voice input needs faster-whisper. Run: pip install faster-whisper"
    elif not config.OPENAI_API_KEY:
        return "Voice input is not configured. Add OPENAI_API_KEY to your .env file, or set WHISPER_BACKEND=local."
    return None


def transcribe(user, audio: bytes, filename: str = "voice.wav"):
    """Returns (text, error). The user's voice language from Settings is used as the hint."""
    if not subscription.has_feature(user, "voice"):
        return None, "Voice input is not part of your plan."
    if not audio or len(audio) > config.MAX_VOICE_BYTES:
        return None, "That recording is empty or too large."
    secs = clip_seconds(audio)
    if secs > config.MAX_VOICE_SECONDS:
        return None, "Recordings can be at most 2 minutes. Please record a shorter one."
    problem = _backend_ready()
    if problem:
        return None, problem
    if not subscription.consume_voice(user, secs):
        return None, "Monthly voice limit reached for your plan. Upgrade for more voice minutes."
    try:
        text = _local(audio, get_lang(user)) if config.WHISPER_BACKEND == "local" else _openai(
            audio, filename, get_lang(user))
    except Exception:
        text = ""
        err = "The voice service is unavailable right now. Please try again."
    else:
        text = (text or "").strip()
        err = None if text else "No speech was detected. Please try again."
    if err:
        subscription.refund_voice(user["id"], secs)
        return None, err
    db.audit("voice_transcribed", user["id"], f"{secs}s")
    return text, None
