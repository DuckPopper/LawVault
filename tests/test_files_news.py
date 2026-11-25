"""Files, Google Docs import, Word/PDF export, AI detector, news feed and the per-user theme."""
import io, json
import pytest
import auth, cases, db, detector, docutil, export, gdocs, news
from conftest import make_user

HUMAN = ("I went to the registry on Monday and honestly the queue was a mess. The clerk didn't have the file, so we "
         "waited. Two hours later, nothing. My client was furious (fair enough!) and wanted to file a complaint right "
         "there. I talked him down. We'll try again Thursday with the original deed, which, if I'm right, sits in the "
         "partner's drawer. Short story: bad day. Then a tenant called about the lease, and that one was actually "
         "simple: the break clause needs six months' notice, no more, no less. I drafted a letter in ten minutes. "
         "Funny how the easy ones arrive after the hard ones. Anyway, tomorrow I read the whole bundle again.")
AI = ("It is important to note that contract law plays a crucial role in modern commerce. Furthermore, parties must "
      "ensure that obligations are clearly defined. Moreover, it is crucial to understand the remedies available. In "
      "addition, the court will consider the intention of the parties. Overall, a holistic approach is essential. It is "
      "worth noting that damages are the primary remedy. In conclusion, careful drafting ensures that disputes are "
      "minimised and the landscape of liability is navigated effectively. Furthermore, parties must ensure that every "
      "obligation is documented. Moreover, the parties must ensure that every remedy is understood. In addition, the "
      "parties should ensure that the contract is reviewed carefully.")


def U(email):
    return dict(make_user(email))


# ---------- theme ----------
def test_theme_is_saved_per_user():
    a, b = U("a@t.test"), U("b@t.test")
    assert a["theme"] == "dark"
    assert auth.set_theme(a["id"], "light") and not auth.set_theme(a["id"], "neon")
    with db.conn() as c:
        got = {r["email"]: r["theme"] for r in c.execute("SELECT email, theme FROM users")}
    assert got == {"a@t.test": "light", "b@t.test": "dark"}


# ---------- word / pdf / google docs ----------
def _docx(text):
    return export.to_docx("T", text, plain=True)


def test_docx_roundtrip_and_pdf_export():
    data = export.to_docx("Title", "### Heading\nHello **bold**.\n- one\n- two")
    text, err = docutil.extract_text("x.docx", data)
    assert not err and "Hello bold." in text and "one" in text
    pdf = export.to_pdf("Titel – “q”", "### Ringkasan\nIsi **penting** — ok.\n- satu", "AI-generated")
    assert pdf.startswith(b"%PDF")
    text, err = docutil.extract_text("x.pdf", pdf)
    assert not err and "penting" in text


def test_docx_validation():
    assert docutil.extract_text("x.docx", b"not a zip")[1]
    assert docutil.extract_text("x.exe", b"MZ")[1]


def test_gdocs_link_validation():
    ok = "https://docs.google.com/document/d/1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789/edit"
    assert gdocs.doc_id(ok) == "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
    for bad in ("http://docs.google.com/document/d/" + "a" * 30, "https://evil.com/?https://docs.google.com/document/d/" + "a" * 30,
                "https://docs.google.com.evil.com/document/d/" + "a" * 30, "https://docs.google.com/document/d/short", ""):
        assert gdocs.doc_id(bad) is None
    assert gdocs.fetch("https://evil.com/x")[2]


def test_gdocs_fetch_refuses_login_redirect(monkeypatch):
    class R:
        is_redirect, status_code, headers = True, 302, {"Location": "https://accounts.google.com/ServiceLogin?x=1"}
        def close(self): pass
    monkeypatch.setattr(gdocs.requests, "get", lambda *a, **k: R())
    name, text, err = gdocs.fetch("https://docs.google.com/document/d/" + "a" * 30 + "/edit")
    assert text is None and "Anyone with the link" in err


# ---------- files ----------
def test_file_list_search_rename_move():
    owner, other = U("o@t.test"), U("p@t.test")
    cid, _ = cases.create_case(owner, "Case One")
    cases.add_member(owner, cid, "p@t.test", "viewer")
    d1, _ = cases.add_document(owner, cid, "../../etc/lease.txt", "The break clause needs six months notice.")
    d2, _ = cases.add_document(owner, None, "private.txt", "secret memo")
    names = {r["filename"] for r in cases.list_accessible_documents(owner["id"])}
    assert names == {"lease.txt", "private.txt"}                      # path stripped
    seen = cases.list_accessible_documents(other["id"])
    assert [r["filename"] for r in seen] == ["lease.txt"] and not seen[0]["can_edit"]   # case doc yes, private no
    hit = cases.list_accessible_documents(owner["id"], "six months")
    assert len(hit) == 1 and "six months" in hit[0]["snippet"]
    assert not cases.rename_document(other["id"], d1, "hacked.txt")          # viewer cannot rename
    assert cases.rename_document(owner["id"], d1, "Lease v2.txt")
    assert cases.move_document(other["id"], d2, None)[0] is False               # not the uploader
    assert cases.move_document(owner["id"], d2, cid)[0]
    assert cases.list_accessible_documents(owner["id"], scope="personal") == []
    stranger_case, _ = cases.create_case(other, "Theirs")
    assert cases.move_document(owner["id"], d2, stranger_case)[0] is False     # no editor access there


# ---------- detector ----------
def test_detector_separates_formulaic_ai_from_casual_text():
    h, a = detector.analyze(HUMAN), detector.analyze(AI)
    assert h["ok"] and a["ok"] and a["score"] >= 70 > 45 > h["score"]
    assert a["flagged"] and not h["flagged"]
    assert detector.analyze("too short")["ok"] is False


def test_detector_parses_model_output_defensively():
    assert detector.parse_opinion('x {"ai_likelihood": 130, "reasons": ["a", "b"]} y')["score"] == 100
    for bad in ("", "no json", '{"ai_likelihood": "high"}', "[1,2]"):
        assert detector.parse_opinion(bad) is None


# ---------- news ----------
RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Good &amp; &lt;b&gt;bold&lt;/b&gt; story</title><link>https://example.com/a</link><description>&lt;p&gt;Hi there&lt;/p&gt;</description><pubDate>Wed, 25 Nov 2026 10:00:00 +0700</pubDate></item>
<item><title>Evil</title><link>javascript:alert(1)</link></item>
<item><title></title><link>https://example.com/b</link></item></channel></rss>"""


def test_feed_parsing_drops_unsafe_links_and_strips_html():
    items = news.parse_feed(RSS, "X")
    assert [i["title"] for i in items] == ["Good & bold story"] and items[0]["summary"] == "Hi there" and items[0]["ts"] > 0
    assert news.parse_feed(b"<<not xml", "X") == []
    bomb = b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]><rss><channel><item><title>&b;</title><link>https://e.com</link></item></channel></rss>'
    assert news.parse_feed(bomb, "X") == []                                 # entity declarations are refused


def test_news_preferences_and_filtering(monkeypatch):
    u = U("n@t.test")
    assert news.get_prefs(u["id"]) == news.DEFAULT_PREFS
    assert news.set_prefs(u["id"], ["en"], ["sports", "bogus"])[0]
    assert news.get_prefs(u["id"]) == dict(langs=["en"], topics=["sports"])
    assert not news.set_prefs(u["id"], [], ["sports"])[0] and not news.set_prefs(u["id"], ["en"], ["bogus"])[0]
    asked = []
    monkeypatch.setattr(news, "_fetch", lambda src, url: asked.append(url) or [dict(title=url, link="https://e.com", summary="", ts=1.0, source=src)])
    out = news.headlines(["id"], ["sports"])
    assert all("olahraga" in a or "sport" in a.lower() for a in asked) and {i["lang"] for i in out} == {"id"}
    assert all(i["topic"] == "sports" for i in out)


def test_every_language_topic_pair_has_a_feed():
    assert all(news.FEEDS.get((l, k)) for l in news.LANGS for k in news.TOPICS)
    assert all(url.startswith("https://") for fs in news.FEEDS.values() for _, url in fs)
