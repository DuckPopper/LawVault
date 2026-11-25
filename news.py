"""Current-affairs feed. Reads public RSS feeds (no API key, no quota) in English and Bahasa Indonesia and filters
them by the topics each user picked. Feeds are fetched over HTTPS only, size-capped and parsed with defusedxml
(a feed is untrusted input). Results are cached in memory for a few minutes so a page refresh never hammers a publisher.
"""
from __future__ import annotations
import email.utils, html, json, re, threading, time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import requests
from defusedxml import ElementTree as ET
import db

LANGS = ("id", "en")
LANG_LABEL = {"id": "Bahasa Indonesia", "en": "English"}
TOPICS = {"law": "Law & politics", "finance": "Finance & business", "tech": "Technology",
          "sports": "Sports", "world": "World", "top": "Top stories"}
DEFAULT_PREFS = dict(langs=["id", "en"], topics=["law", "finance", "tech"])

# (language, topic) -> [(publisher, feed url)]. All of these were checked live on 2026-11-25.
_ANTARA, _CNN, _BBC = "ANTARA", "CNN Indonesia", "BBC"
FEEDS = {
    ("id", "law"):     [(_ANTARA, "https://www.antaranews.com/rss/hukum.xml")],
    ("id", "finance"): [(_ANTARA, "https://www.antaranews.com/rss/ekonomi.xml"),
                        (_CNN, "https://www.cnnindonesia.com/ekonomi/rss")],
    ("id", "tech"):    [(_ANTARA, "https://www.antaranews.com/rss/tekno.xml"),
                        (_CNN, "https://www.cnnindonesia.com/teknologi/rss")],
    ("id", "sports"):  [(_ANTARA, "https://www.antaranews.com/rss/olahraga.xml"),
                        (_CNN, "https://www.cnnindonesia.com/olahraga/rss")],
    ("id", "world"):   [(_ANTARA, "https://www.antaranews.com/rss/dunia.xml")],
    ("id", "top"):     [(_ANTARA, "https://www.antaranews.com/rss/terkini.xml")],
    ("en", "law"):     [(_BBC, "https://feeds.bbci.co.uk/news/politics/rss.xml")],
    ("en", "finance"): [(_BBC, "https://feeds.bbci.co.uk/news/business/rss.xml")],
    ("en", "tech"):    [(_BBC, "https://feeds.bbci.co.uk/news/technology/rss.xml")],
    ("en", "sports"):  [(_BBC, "https://feeds.bbci.co.uk/sport/rss.xml")],
    ("en", "world"):   [(_BBC, "https://feeds.bbci.co.uk/news/world/rss.xml")],
    ("en", "top"):     [(_BBC, "https://feeds.bbci.co.uk/news/rss.xml")],
}

CACHE_SECONDS = 600
MAX_FEED_BYTES = 3 * 1024 * 1024
HTTP_TIMEOUT = 8
PER_FEED = 15
_cache: dict[str, tuple[float, list]] = {}
_lock = threading.Lock()
_TAGS = re.compile(r"<[^>]+>")


# ---------- preferences ----------
def get_prefs(user_id: str) -> dict:
    with db.conn() as c:
        r = c.execute("SELECT langs, topics FROM news_prefs WHERE user_id=?", (user_id,)).fetchone()
    if not r:
        return {k: list(v) for k, v in DEFAULT_PREFS.items()}
    return _clean(json.loads(r["langs"]), json.loads(r["topics"]))


def _clean(langs, topics) -> dict:
    langs = [l for l in LANGS if l in (langs or [])]      # also fixes the order and drops unknown values
    topics = [k for k in TOPICS if k in (topics or [])]
    return dict(langs=langs, topics=topics)


def set_prefs(user_id: str, langs, topics):
    p = _clean(langs, topics)
    if not p["langs"] or not p["topics"]:
        return False, "Pick at least one language and one topic."
    with db.conn() as c:
        c.execute("INSERT INTO news_prefs(user_id,langs,topics) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE "
                  "SET langs=excluded.langs, topics=excluded.topics",
                  (user_id, json.dumps(p["langs"]), json.dumps(p["topics"])))
    return True, "Preferences saved."


# ---------- fetching ----------
def _text(s: str | None, limit: int) -> str:
    s = html.unescape(_TAGS.sub(" ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"


def _safe_url(u: str | None) -> str | None:
    p = urlparse((u or "").strip())
    return p.geturl() if p.scheme in ("http", "https") and p.netloc else None   # never javascript: or data:


def _ts(s: str | None) -> float:
    try:
        return email.utils.parsedate_to_datetime((s or "").strip()).timestamp()
    except (TypeError, ValueError):
        return 0.0


def parse_feed(xml_bytes: bytes, source: str) -> list[dict]:
    """RSS 2.0 items -> [{title, link, summary, ts, source}]. Anything malformed is skipped."""
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return []
    out = []
    for it in root.iter("item"):
        title, link = _text(it.findtext("title"), 220), _safe_url(it.findtext("link"))
        if not title or not link:
            continue
        out.append(dict(title=title, link=link, summary=_text(it.findtext("description"), 260),
                        ts=_ts(it.findtext("pubDate")), source=source))
        if len(out) >= PER_FEED:
            break
    return out


def _fetch(source: str, url: str) -> list[dict]:
    now = time.time()
    with _lock:
        hit = _cache.get(url)
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    items = None
    try:
        if not url.startswith("https://"):
            raise ValueError("https only")
        with requests.get(url, timeout=HTTP_TIMEOUT, stream=True, headers={"User-Agent": "Mozilla/5.0 LawVault"}) as r:
            r.raise_for_status()
            body = r.raw.read(MAX_FEED_BYTES + 1, decode_content=True)
        if len(body) <= MAX_FEED_BYTES:
            items = parse_feed(body, source)
    except Exception:
        pass
    if items is None:                       # publisher down: keep showing the last good copy if we have one
        return hit[1] if hit else []
    with _lock:
        _cache[url] = (now, items)
    return items


def headlines(langs, topics, limit: int = 40) -> list[dict]:
    """Newest first, de-duplicated. Each item also carries its language and topic."""
    jobs = [(l, k, src, url) for l in langs for k in topics for src, url in FEEDS.get((l, k), [])]
    if not jobs:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as ex:
        results = list(ex.map(lambda j: _fetch(j[2], j[3]), jobs))
    seen, out = set(), []
    for (lang, topic, _, _), items in zip(jobs, results):
        for it in items:
            key = re.sub(r"\W+", "", it["title"].lower())
            if key not in seen:
                seen.add(key)
                out.append({**it, "lang": lang, "topic": topic})
    out.sort(key=lambda x: x["ts"], reverse=True)
    return out[:limit]


def clear_cache():
    with _lock:
        _cache.clear()
