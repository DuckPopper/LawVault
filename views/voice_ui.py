"""A small microphone widget shared by the calendar assistant and the legal assistant."""
import hashlib
import streamlit as st
import i18n, subscription, voice
from i18n import t


def mic(u, key: str):
    """Record, then transcribe once. Returns the text the moment a new recording has been transcribed, else None.
    Shows nothing if the plan has no voice input."""
    if not subscription.has_feature(u, "voice"):
        return None
    n = st.session_state.get(f"{key}_n", 0)
    with st.expander(t("Speak instead of typing"), icon=":material/mic:"):
        used = subscription.voice_seconds_used(u["id"]) // 60
        cap = subscription.limits(u)["voice_minutes"]
        st.caption(t("Language: {lang} (change it in Settings). {used} of {cap} voice minutes used this month. "
                     "Audio is not stored.", lang=t(voice.LANGS[voice.get_lang(u)]), used=used, cap=cap))
        clip = st.audio_input(t("Record"), key=f"{key}_{n}", label_visibility="collapsed")
        if clip is None:
            return None
        data = clip.getvalue()
        if st.session_state.get(f"{key}_last") == hashlib.sha256(data).hexdigest():
            return None
        with st.spinner(t("Transcribing…")):
            text, err = voice.transcribe(u, data)
        st.session_state[f"{key}_last"] = hashlib.sha256(data).hexdigest()
        if err:
            st.error(i18n.tm(err))
            return None
        st.session_state[f"{key}_n"] = n + 1       # a fresh, empty recorder next time
        return text
