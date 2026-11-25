import io, wave
import pytest
import config, db, subscription as sub, voice
from conftest import make_user


def wav(seconds=2, rate=16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(b"\x00\x00" * rate * seconds)
    return buf.getvalue()


def fresh(uid):
    with db.conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


@pytest.fixture
def api(monkeypatch):
    """A fake Whisper API that records what it was asked."""
    calls = []
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(config, "WHISPER_BACKEND", "openai")
    monkeypatch.setattr(voice, "_openai", lambda audio, name, lang: (calls.append(lang) or "besok jam 12 meeting"))
    return calls


def test_clip_length_is_read_from_the_wav_and_rounded_up():
    assert voice.clip_seconds(wav(3)) == 3
    assert voice.clip_seconds(b"not a wav" * 3200) == 1


def test_transcribes_and_meters_the_seconds(api):
    u = make_user("a@x.com")
    text, err = voice.transcribe(u, wav(4))
    assert (text, err) == ("besok jam 12 meeting", None)
    assert sub.voice_seconds_used(u["id"]) == 4


def test_language_from_settings_is_passed_to_whisper(api):
    u = make_user("a@x.com")
    voice.transcribe(u, wav(1))
    assert voice.set_lang(u["id"], "id") and not voice.set_lang(u["id"], "klingon")
    voice.transcribe(fresh(u["id"]), wav(1))
    assert api == ["auto", "id"]
    assert voice.get_lang(fresh(u["id"])) == "id"


def test_a_failed_call_costs_nothing(monkeypatch, api):
    u = make_user("a@x.com")
    monkeypatch.setattr(voice, "_openai", lambda *a: (_ for _ in ()).throw(RuntimeError("down")))
    text, err = voice.transcribe(u, wav(5))
    assert text is None and "unavailable" in err and sub.voice_seconds_used(u["id"]) == 0
    monkeypatch.setattr(voice, "_openai", lambda *a: "  ")
    assert voice.transcribe(u, wav(5))[0] is None and sub.voice_seconds_used(u["id"]) == 0


def test_limits_and_guards(api, monkeypatch):
    u = make_user("a@x.com")                                    # free plan: 10 minutes
    assert "at most 2 minutes" in voice.transcribe(u, wav(121))[1]
    assert "empty or too large" in voice.transcribe(u, b"")[1]
    monkeypatch.setattr(config, "MAX_VOICE_BYTES", 100)
    assert "empty or too large" in voice.transcribe(u, wav(1))[1]
    monkeypatch.setattr(config, "MAX_VOICE_BYTES", 10 ** 7)
    for _ in range(5):
        assert voice.transcribe(u, wav(120))[1] is None
    assert "Monthly voice limit" in voice.transcribe(u, wav(1))[1]


def test_voice_can_be_switched_off_in_a_custom_plan(api):
    u = make_user("a@x.com")
    sub.mock_checkout(u["id"], "pro")
    sub.mock_checkout(u["id"], "custom", custom=dict(units={}, features={"voice": False}))
    assert voice.transcribe(fresh(u["id"]), wav(1))[1] == "Voice input is not part of your plan."
    assert sub.voice_seconds_used(u["id"]) == 0


def test_not_configured_is_reported_before_any_quota_is_used(monkeypatch):
    u = make_user("a@x.com")
    monkeypatch.setattr(config, "WHISPER_BACKEND", "openai")
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    assert "OPENAI_API_KEY" in voice.transcribe(u, wav(1))[1]
    assert sub.voice_seconds_used(u["id"]) == 0


def test_the_openai_request_is_built_correctly(monkeypatch):
    seen = {}

    class R:
        def raise_for_status(self): pass
        def json(self): return {"text": " halo dunia "}

    def post(url, **kw):
        seen.update(url=url, **kw)
        return R()
    monkeypatch.setattr(config, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(voice.requests, "post", post)
    assert voice._openai(b"abc", "v.wav", "id") == "halo dunia"
    assert seen["url"].endswith("/v1/audio/transcriptions") and seen["data"]["language"] == "id"
    assert seen["headers"]["Authorization"] == "Bearer sk-test" and "file" in seen["files"]
    voice._openai(b"abc", "v.wav", "auto")
    assert "language" not in seen["data"]


def test_audio_is_never_written_to_the_database(api):
    u = make_user("a@x.com")
    voice.transcribe(u, wav(2))
    with db.conn() as c:
        events = [r["event"] for r in c.execute("SELECT event, detail FROM audit_log")]
        detail = c.execute("SELECT detail FROM audit_log WHERE event='voice_transcribed'").fetchone()["detail"]
    assert "voice_transcribed" in events and detail == "2s"      # only the length, never the words
