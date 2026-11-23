"""Interface language: English (default) and Bahasa Indonesia.

Strings in the code are written in English and wrapped in t(). The English text is the lookup key, so a string
nobody has translated yet simply shows in English instead of breaking. Placeholders use str.format names:

    t("Added {n} deadline(s).", n=3)

Which language is used:
  1. a signed-in user's saved choice (users.lang), copied into the session by app.py
  2. otherwise the session / ?lang= link choice made on the login page
  3. otherwise English

Dates: strftime() always gives English day and month names, so use fmt() for anything shown to people.
"""
from __future__ import annotations
import datetime as dt

LANGS = {"en": "English", "id": "Bahasa Indonesia"}
DEFAULT = "en"

_DAYS = {
    "id": ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"),
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
}
_DAYS_SHORT = {
    "id": ("Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"),
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
}
_MONTHS = {
    "id": ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
           "November", "Desember"),
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"),
}
_MONTHS_SHORT = {
    "id": ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"),
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
}


def valid(code) -> str:
    return code if code in LANGS else DEFAULT


def lang() -> str:
    """The language for the current Streamlit session."""
    import streamlit as st
    code = st.session_state.get("lang")
    if code in LANGS:
        return code
    try:  # a shared link or a refresh on the login page: ?lang=id
        code = st.query_params.get("lang")
    except Exception:
        code = None
    return valid(code)


def set_lang(code: str):
    """Remember the choice for this session (and in the URL while signed out, so a refresh keeps it)."""
    import streamlit as st
    code = valid(code)
    st.session_state["lang"] = code
    if not st.session_state.get("token"):
        try:
            st.query_params["lang"] = code
        except Exception:
            pass


def t(text: str, **kw) -> str:
    """Translate an English UI string into the session language, then fill in {placeholders}."""
    out = text
    if lang() != "en":
        from i18n_id import ID
        out = ID.get(text, text)
    return out.format(**kw) if kw else out


def tm(text: str) -> str:
    """Translate a message whose English text was built from data (backend errors, notifications).
    Exact matches first, then the patterns in i18n_id.PATTERNS. Unknown text is returned unchanged."""
    if not text or lang() == "en":
        return text
    from i18n_id import ID, PATTERNS
    if text in ID:
        return ID[text]
    for rx, tpl in PATTERNS:
        m = rx.fullmatch(text)
        if m:
            return tpl.format(**m.groupdict())
    return text


def tl(code: str, text: str, **kw) -> str:
    """Translate into an explicit language (for code that has no Streamlit session, e.g. notifications)."""
    out = text
    if code != "en":
        from i18n_id import ID
        out = ID.get(text, text)
    return out.format(**kw) if kw else out


def plural(n: int, one: str, many: str, **kw) -> str:
    """Pick the singular or plural English string; Indonesian reuses the same translation for both."""
    return t(one if n == 1 else many, n=n, **kw)


# ---------- dates ----------
def fmt(d, pattern: str, code: str | None = None) -> str:
    """strftime with localised %A %a %B %b. Works on date and datetime."""
    code = valid(code) if code else lang()
    wd, mo = d.weekday(), d.month - 1
    pattern = (pattern.replace("%A", _DAYS[code][wd]).replace("%a", _DAYS_SHORT[code][wd])
               .replace("%B", _MONTHS[code][mo]).replace("%b", _MONTHS_SHORT[code][mo]))
    return d.strftime(pattern)


def _by_lang(en: str, idn: str) -> str:
    return idn if lang() == "id" else en


def date_long(d) -> str:      # November 23, 2026  /  23 November 2026
    return fmt(d, _by_lang("%B %-d, %Y", "%-d %B %Y"))


def date_md(d) -> str:        # Nov 23  /  23 Nov
    return fmt(d, _by_lang("%b %-d", "%-d %b"))


def date_wmd(d) -> str:       # Mon Nov 23  /  Sen 23 Nov
    return fmt(d, _by_lang("%a %b %d", "%a %d %b"))


def date_wmdy(d) -> str:      # Mon Nov 23, 2026  /  Sen 23 Nov 2026
    return fmt(d, _by_lang("%a %b %d, %Y", "%a %d %b %Y"))


def date_full(d) -> str:      # Monday, November 23  /  Senin, 23 November
    return fmt(d, _by_lang("%A, %B %-d", "%A, %-d %B"))


def date_time(d) -> str:      # Mon Nov 23, 09:00  /  Sen 23 Nov, 09:00
    return fmt(d, _by_lang("%a %b %d, %H:%M", "%a %d %b, %H:%M"))


def day_short(weekday: int) -> str:
    return _DAYS_SHORT[lang()][weekday]


def month_name(month: int) -> str:
    return _MONTHS[lang()][month - 1]


def weekday_initials() -> str:
    return "SSRKJSM" if lang() == "id" else "MTWTFSS"  # Senin Selasa Rabu Kamis Jumat Sabtu Minggu


# ---------- AI ----------
_AI_NOTE = {
    "id": ("\n\nLANGUAGE\nWrite every answer in Bahasa Indonesia (formal, as used by Indonesian legal practitioners) "
           "unless the user writes in another language. Keep statute and article names in their original form."),
    "en": "",
}


def ai_note(code: str | None) -> str:
    return _AI_NOTE.get(valid(code), "")
