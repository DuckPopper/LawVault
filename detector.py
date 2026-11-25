"""AI-writing detector. Two independent signals:

1. `analyze()` - a transparent, offline statistical check (sentence-length variation, vocabulary variety, stock
   phrases, repeated sentence openers). Free, instant, nothing leaves the machine.
2. `ai_opinion()` - an optional second opinion from the language model.

No detector is reliable. Formulaic legal drafting, non-native writing and heavily edited AI text all fool them, so the
result is a prompt for human judgement, never proof. The UI says so.
"""
from __future__ import annotations
import json, math, re
import ai, config, privacy

MIN_WORDS = 80

# Phrases language models overuse (English / Bahasa Indonesia). Legal boilerplate such as "hereinafter" is left out on purpose.
STOCK = [
    "it is important to note", "it is worth noting", "it's important to note", "in today's fast-paced",
    "in the ever-evolving", "plays a crucial role", "plays a vital role", "delve into", "tapestry", "a testament to",
    "in conclusion", "in summary", "overall,", "navigate the complexities", "landscape of", "shed light on",
    "multifaceted", "holistic approach", "it is crucial to", "ensuring that", "not only", "at the end of the day",
    "penting untuk dicatat", "perlu dicatat bahwa", "di era digital", "dalam era digital", "memainkan peran penting",
    "peran yang sangat penting", "kesimpulannya", "dapat disimpulkan bahwa", "secara keseluruhan", "dalam lanskap",
    "menyoroti pentingnya", "tidak hanya itu", "pada dasarnya",
]
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])|\n+")
_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text) if len(_WORD.findall(s)) >= 3]


def _label(score: int) -> str:
    return "Likely AI-written" if score >= 70 else "Possibly AI-assisted" if score >= 45 else "Likely human-written"


def analyze(text: str) -> dict:
    """Returns {ok, score 0-100, label, words, signals[{name, value, ai_like 0-1, note}], flagged[str]}."""
    words = [w.lower() for w in _WORD.findall(text)]
    sents = sentences(text)
    if len(words) < MIN_WORDS or len(sents) < 4:
        return dict(ok=False, words=len(words), min_words=MIN_WORDS)
    lens = [len(_WORD.findall(s)) for s in sents]
    mean = sum(lens) / len(lens)
    cv = math.sqrt(sum((x - mean) ** 2 for x in lens) / len(lens)) / mean          # burstiness
    ttr = len(set(words)) / len(words) if len(words) <= 400 else len(set(words[:400])) / 400
    low = text.lower()
    hits = [p for p in STOCK if p in low]
    openers = [" ".join(s.lower().split()[:2]) for s in sents]
    repeat = 1 - len(set(openers)) / len(openers)
    contractions = len(re.findall(r"\b\w+['’](?:t|s|re|ve|ll|d|m)\b", low)) / max(1, len(words))

    def ramp(x, lo, hi):          # 0 at lo, 1 at hi
        return max(0.0, min(1.0, (x - lo) / (hi - lo)))
    signals = [
        dict(name="Sentence rhythm", value=f"{cv:.2f}", ai_like=1 - ramp(cv, 0.30, 0.65), weight=0.30,
             note="People mix short and long sentences; models tend to keep them even."),
        dict(name="Vocabulary variety", value=f"{ttr:.2f}", ai_like=(1 - ramp(ttr, 0.45, 0.70)) * 0.6,
             weight=0.15, note="Unusually uniform or repetitive wording."),
        dict(name="Stock phrases", value=str(len(hits)), ai_like=ramp(len(hits), 0, 4), weight=0.30,
             note="Phrases such as “it is important to note” or “penting untuk dicatat”."),
        dict(name="Repeated sentence openers", value=f"{repeat:.0%}", ai_like=ramp(repeat, 0.10, 0.45),
             weight=0.10, note="Many sentences starting the same way."),
        dict(name="Informal markers", value=f"{contractions:.1%}", ai_like=1 - ramp(contractions, 0.0, 0.015),
             weight=0.15, note="Contractions and casual asides are rare in AI output (weak signal)."),
    ]
    score = round(100 * sum(s["ai_like"] * s["weight"] for s in signals))
    flagged = [s for s in sents if any(p in s.lower() for p in STOCK)][:8]
    for s in signals:
        s["ai_like"] = round(s["ai_like"], 2)
    return dict(ok=True, score=score, label=_label(score), words=len(words), signals=signals, flagged=flagged)


def parse_opinion(raw: str):
    """Defensive parse of the model's JSON reply (untrusted output). Returns dict or None."""
    a, b = (raw or "").find("{"), (raw or "").rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        d = json.loads(raw[a:b + 1])
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    try:
        likelihood = max(0, min(100, int(d.get("ai_likelihood"))))
    except (TypeError, ValueError):
        return None
    reasons = [str(r).strip()[:240] for r in (d.get("reasons") or []) if str(r).strip()][:5] \
        if isinstance(d.get("reasons"), list) else []
    return dict(score=likelihood, label=_label(likelihood), reasons=reasons)


def ai_opinion(user, text: str):
    """Second opinion from the language model. Returns (opinion, error); uses one AI call from the plan's quota."""
    sample = privacy.redact(text[:12_000])
    prompt = ("Judge whether the text inside the document tags was written by an AI language model or by a person. "
              "Consider rhythm, specificity, generic phrasing, hedging and structure. Be calibrated: formal legal "
              "drafting is often formulaic without being AI-written. Reply with ONLY JSON like "
              '{"ai_likelihood": 0-100, "reasons": ["short reason", "short reason"]} and nothing else.\n\n'
              f"<document>\n{sample}\n</document>")
    raw, err = ai._with_quota(user, [{"role": "user", "parts": [{"text": prompt}]}], "en")
    if err:
        return None, err
    op = parse_opinion(raw)
    return (op, None) if op else (None, "The AI's answer couldn't be read. Please try again.")
