"""Two-way calendar sync between LawVault and Google / Apple calendars.

What syncs: the user's OWN events (title, notes, location, start, end), from 30 days back to a year ahead.
- LawVault -> Google/Apple: new and changed events are pushed, deleted ones removed.
- Google/Apple -> LawVault: new, changed and deleted events come in. Imported events are private to the user like any
  other event; nothing is shared with teammates unless the user's calendar visibility allows it.
- Both sides changed since the last sync: the more recently edited one wins.
- Never sent out: attendees (so Google/Apple can't e-mail anyone), other people's events, case deadlines.
- Recurring Apple events arrive as read-only occurrences. Deleting one here does not delete it at Apple.

Safety nets: sign-in secrets are encrypted at rest; a sync that would delete more than half of the user's mapped events
is refused; a failed sync changes nothing it hasn't finished and is retried; OAuth uses a single-use `state`.
Sync needs the plan feature `calendar_sync` (Pro and up). When it lapses, links pause and nothing is deleted.
"""
from __future__ import annotations
import datetime as dt
import json
import logging
import secrets
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import requests
import calproviders as prov
import config, crypto, db, subscription

log = logging.getLogger("lawvault.calsync")
WINDOW_PAST, WINDOW_FUTURE = 30 * 86400, 365 * 86400
MAX_EVENT_SECONDS = 7 * 86400
MAX_LINKS = 4
STATE_TTL = 600
ASYNC = True                     # tests switch this off so a change syncs inline
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lawvault-sync")
_locks: dict = {}
_locks_guard = threading.Lock()
_worker = {"started": False}


class SyncAbort(Exception):
    """Stop the sync on purpose and show this message."""


def _lock(link_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(link_id, threading.Lock())


# ---------------------------------------------------------------- links
def google_configured() -> bool:
    return bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET)


def list_links(user_id: str):
    with db.conn() as c:
        rows = c.execute("SELECT id, provider, account, status, last_sync, last_error FROM calendar_links "
                         "WHERE user_id=? ORDER BY created_at", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def _user(c, user_id: str):
    return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def add_link(user_id: str, provider: str, account: str, cred: dict):
    """Save (or refresh) a connection. Returns (link_id, error)."""
    with db.conn() as c:
        u = _user(c, user_id)
        if not u:
            return None, "No such user."
        if not subscription.has_feature(u, "calendar_sync"):
            return None, "Calendar sync is not part of your plan."
        old = c.execute("SELECT id FROM calendar_links WHERE user_id=? AND provider=? AND account=?",
                        (user_id, provider, account)).fetchone()
        if old:
            c.execute("UPDATE calendar_links SET cred_enc=?, status='ok', last_error=NULL WHERE id=?",
                      (crypto.encrypt(json.dumps(cred)), old["id"]))
            return old["id"], None
        if c.execute("SELECT COUNT(*) n FROM calendar_links WHERE user_id=?", (user_id,)).fetchone()["n"] >= MAX_LINKS:
            return None, "You can connect up to 4 calendars."
        lid = db.uid()
        c.execute("INSERT INTO calendar_links(id,user_id,provider,account,cred_enc,created_at) VALUES(?,?,?,?,?,?)",
                  (lid, user_id, provider, account[:200], crypto.encrypt(json.dumps(cred)), db.now()))
    db.audit("calendar_link_added", user_id, provider)
    return lid, None


def remove_link(user_id: str, link_id: str, delete_imported: bool = False) -> bool:
    """Disconnect. Events already in LawVault stay unless delete_imported is true (then only the ones that
    came from that calendar are removed)."""
    with db.conn() as c:
        link = c.execute("SELECT id FROM calendar_links WHERE id=? AND user_id=?", (link_id, user_id)).fetchone()
        if not link:
            return False
        if delete_imported:
            for m in c.execute("SELECT event_id FROM event_links WHERE link_id=? AND origin LIKE 'remote%'",
                               (link_id,)).fetchall():
                c.execute("DELETE FROM events WHERE id=? AND owner_id=?", (m["event_id"], user_id))
        c.execute("DELETE FROM calendar_links WHERE id=?", (link_id,))
    db.audit("calendar_link_removed", user_id)
    return True


def _set_status(link_id: str, status: str, error: Optional[str], synced: bool = False):
    with db.conn() as c:
        c.execute("UPDATE calendar_links SET status=?, last_error=?, last_sync=COALESCE(?, last_sync) WHERE id=?",
                  (status, error, db.now() if synced else None, link_id))


# ---------------------------------------------------------------- Google sign-in (OAuth)
def google_auth_url(user_id: str) -> Optional[str]:
    if not google_configured():
        return None
    state = secrets.token_urlsafe(24)
    with db.conn() as c:
        c.execute("DELETE FROM oauth_states WHERE expires_at<?", (db.now(),))
        c.execute("INSERT INTO oauth_states(state,user_id,provider,expires_at) VALUES(?,?,?,?)",
                  (state, user_id, "google", db.now() + STATE_TTL))
    q = urllib.parse.urlencode(dict(client_id=config.GOOGLE_CLIENT_ID, redirect_uri=config.GOOGLE_REDIRECT_URI,
                                    response_type="code", scope=prov.GOOGLE_SCOPE, access_type="offline",
                                    prompt="consent", state=state))
    return f"{prov.GOOGLE_AUTH_URL}?{q}"


def google_finish(user_id: str, code: str, state: str):
    """Called when Google sends the user back. Returns (ok, message). The state must be unused, unexpired and
    issued to THIS user, otherwise nothing is stored."""
    with db.conn() as c:
        row = c.execute("SELECT * FROM oauth_states WHERE state=?", (state or "",)).fetchone()
        c.execute("DELETE FROM oauth_states WHERE state=?", (state or "",))        # single use
    if not row or row["user_id"] != user_id or row["provider"] != "google" or row["expires_at"] < db.now():
        return False, "This sign-in link is no longer valid. Please start again."
    if not google_configured() or not code:
        return False, "Google sign-in is not configured."
    try:
        r = requests.post(prov.GOOGLE_TOKEN_URL, timeout=config.SYNC_HTTP_TIMEOUT, data=dict(
            code=code, client_id=config.GOOGLE_CLIENT_ID, client_secret=config.GOOGLE_CLIENT_SECRET,
            redirect_uri=config.GOOGLE_REDIRECT_URI, grant_type="authorization_code"))
        body = r.json() if r.status_code == 200 else {}
    except Exception:
        return False, "Could not reach Google. Please try again."
    if not body.get("refresh_token"):
        return False, "Google did not allow offline access. Remove LawVault from your Google account permissions and try again."
    cred = dict(access_token=body.get("access_token", ""), refresh_token=body["refresh_token"],
                expires_at=time.time() + int(body.get("expires_in", 3600)))
    lid, err = add_link(user_id, "google", "Google Calendar", cred)
    if err:
        return False, err
    sync_link(lid)
    return True, "Google Calendar connected."


def connect_apple(user_id: str, apple_id: str, app_password: str):
    """Sign in to iCloud with an app-specific password. Returns (ok, message)."""
    apple_id, app_password = (apple_id or "").strip(), (app_password or "").strip()
    if "@" not in apple_id or len(app_password) < 8:
        return False, "Enter your Apple ID and an app-specific password."
    try:
        cals = prov.Apple.discover(apple_id, app_password)
    except prov.AuthError as e:
        return False, str(e)
    except prov.ProviderError as e:
        return False, str(e)
    if not cals:
        return False, "No calendar that can hold events was found in that iCloud account."
    name, url = cals[0]
    lid, err = add_link(user_id, "apple", apple_id,
                        dict(username=apple_id, password=app_password, calendar_url=url, calendar_name=name))
    if err:
        return False, err
    sync_link(lid)
    return True, "Apple Calendar connected."


# ---------------------------------------------------------------- the sync itself
def _fp_row(r) -> str:
    return prov.fingerprint(crypto.decrypt(r["title_enc"]), crypto.decrypt(r["notes_enc"]),
                            crypto.decrypt(r["location_enc"]) if r["location_enc"] else "",
                            r["start_ts"], r["end_ts"])


def _clean(r: prov.RemoteEvent):
    start = r.start
    end = min(max(r.end, start + 900), start + MAX_EVENT_SECONDS)
    return (r.title.strip()[:150] or "(no title)", r.notes.strip()[:2000], r.location.strip()[:200], start, end)


def _local_fp(title, notes, loc, start, end) -> str:
    return prov.fingerprint(title, notes, loc, start, end)


def _provider(link):
    cred = json.loads(crypto.decrypt(link["cred_enc"]))

    def save(new):
        with db.conn() as c:
            c.execute("UPDATE calendar_links SET cred_enc=? WHERE id=?", (crypto.encrypt(json.dumps(new)), link["id"]))
    return prov.make(link["provider"], cred, save)


def sync_link(link_id: str):
    """Run one sync for a connection. Returns a stats dict (with `error` set if it failed), or None if unknown."""
    with _lock(link_id):
        with db.conn() as c:
            link = c.execute("SELECT * FROM calendar_links WHERE id=?", (link_id,)).fetchone()
            user = _user(c, link["user_id"]) if link else None
        if not link or not user:
            return None
        if not subscription.has_feature(user, "calendar_sync"):
            msg = "Calendar sync is not part of your current plan."
            _set_status(link_id, "paused", msg)
            return dict(error=msg)
        try:
            stats = _run(link, user, _provider(link))
        except prov.AuthError:
            msg = "Please connect this calendar again."
            _set_status(link_id, "reauth", msg)
            return dict(error=msg)
        except SyncAbort as e:
            _set_status(link_id, "error", str(e))
            return dict(error=str(e))
        except Exception:
            log.exception("calendar sync failed for link %s", link_id)
            msg = "The calendar service is unavailable right now. LawVault will retry."
            _set_status(link_id, "error", msg)
            return dict(error=msg)
        _set_status(link_id, "ok", None, synced=True)
        return stats


def _run(link, user, provider) -> dict:
    uid, lid = user["id"], link["id"]
    now = db.now()
    w0, w1 = now - WINDOW_PAST, now + WINDOW_FUTURE
    cursor = crypto.decrypt(link["cursor_enc"]) if link["cursor_enc"] else None
    remote, new_cursor, complete = provider.pull(cursor, w0, w1)
    stats = dict(imported=0, updated=0, removed_here=0, pushed=0, removed_there=0)

    with db.conn() as c:
        maps = {m["remote_id"]: dict(m) for m in c.execute("SELECT * FROM event_links WHERE link_id=?", (lid,))}
        local = {r["id"]: r for r in c.execute("SELECT * FROM events WHERE owner_id=?", (uid,))}
    seen = {r.id for r in remote}

    # ---- circuit breaker: a listing that makes most of our mapped events vanish is more likely a fault than a purge
    if complete:
        in_window = [m for m in maps.values() if m["event_id"] in local
                     and w0 <= local[m["event_id"]]["start_ts"] <= w1 and m["origin"] != "remote-ro"]
        gone = [m for m in in_window if m["remote_id"] not in seen]
        if len(in_window) >= 5 and len(gone) > len(in_window) / 2:
            raise SyncAbort("Sync stopped: the other calendar returned far fewer events than expected. "
                            "Nothing was deleted.")
    else:
        gone = []
    gone_ids = {m["remote_id"] for m in gone} | {
        m["remote_id"] for m in maps.values() if complete and m["origin"] == "remote-ro" and m["event_id"] in local
        and w0 <= local[m["event_id"]]["start_ts"] <= w1 and m["remote_id"] not in seen}

    # ---- remote -> local
    with db.conn() as c:
        for rid in gone_ids:                                   # deleted at the other end
            m = maps[rid]
            c.execute("DELETE FROM events WHERE id=? AND owner_id=?", (m["event_id"], uid))
            c.execute("DELETE FROM event_links WHERE link_id=? AND remote_id=?", (lid, rid))
            stats["removed_here"] += 1
        for r in remote:
            m = maps.get(r.id)
            if r.deleted:
                if m and m["event_id"] in local and m["remote_id"] not in gone_ids:
                    c.execute("DELETE FROM events WHERE id=? AND owner_id=?", (m["event_id"], uid))
                    stats["removed_here"] += 1
                if m:
                    c.execute("DELETE FROM event_links WHERE link_id=? AND remote_id=?", (lid, r.id))
                continue
            if not (w0 <= r.start <= w1):
                continue
            title, notes, loc, start, end = _clean(r)
            if m is None:
                eid = db.uid()
                c.execute("INSERT INTO events(id,owner_id,title_enc,notes_enc,start_ts,end_ts,case_id,created_at,"
                          "location_enc,updated_at) VALUES(?,?,?,?,?,?,NULL,?,?,?)",
                          (eid, uid, crypto.encrypt(title), crypto.encrypt(notes), start, end, now,
                           crypto.encrypt(loc), r.updated or now))
                c.execute("INSERT INTO event_links(link_id,event_id,remote_id,remote_version,local_hash,all_day,origin)"
                          " VALUES(?,?,?,?,?,?,?)", (lid, eid, r.id, r.version, _local_fp(title, notes, loc, start, end),
                                                     int(r.all_day), "remote-ro" if r.read_only else "remote"))
                stats["imported"] += 1
                continue
            row = local.get(m["event_id"])
            if row is None or m["remote_version"] == r.version:
                continue                                       # deleted here (handled below) or nothing new there
            local_changed = _fp_row(row) != m["local_hash"]
            local_when = row["updated_at"] or row["created_at"]
            if local_changed and m["origin"] != "remote-ro" and (r.updated or 0) < local_when:
                c.execute("UPDATE event_links SET remote_version=? WHERE link_id=? AND remote_id=?",
                          (r.version, lid, r.id))                # ours is newer: keep it, it is pushed below
                continue
            c.execute("UPDATE events SET title_enc=?, notes_enc=?, location_enc=?, start_ts=?, end_ts=?, updated_at=? "
                      "WHERE id=? AND owner_id=?", (crypto.encrypt(title), crypto.encrypt(notes), crypto.encrypt(loc),
                                                    start, end, r.updated or now, m["event_id"], uid))
            c.execute("UPDATE event_links SET remote_version=?, local_hash=?, all_day=? WHERE link_id=? AND remote_id=?",
                      (r.version, _local_fp(title, notes, loc, start, end), int(r.all_day), lid, r.id))
            stats["updated"] += 1
        local = {r["id"]: r for r in c.execute("SELECT * FROM events WHERE owner_id=?", (uid,))}
        maps = {m["remote_id"]: dict(m) for m in c.execute("SELECT * FROM event_links WHERE link_id=?", (lid,))}
    by_event = {m["event_id"]: m for m in maps.values()}

    # ---- local -> remote (no database connection is held while talking to the network)
    for eid, row in local.items():
        if row["end_ts"] <= w0 or row["start_ts"] >= w1:
            continue
        m = by_event.get(eid)
        if m and m["origin"] == "remote-ro":
            continue
        fp = _fp_row(row)
        if m and m["local_hash"] == fp:
            continue
        ev = dict(uid=eid, title=crypto.decrypt(row["title_enc"]), notes=crypto.decrypt(row["notes_enc"]),
                  location=crypto.decrypt(row["location_enc"]) if row["location_enc"] else "",
                  start=row["start_ts"], end=row["end_ts"])
        all_day = bool(m["all_day"]) if m else False
        rid, ver = provider.push(ev, m["remote_id"] if m else None, all_day)
        with db.conn() as c:
            if m and rid != m["remote_id"]:
                c.execute("DELETE FROM event_links WHERE link_id=? AND remote_id=?", (lid, m["remote_id"]))
            c.execute("INSERT OR REPLACE INTO event_links(link_id,event_id,remote_id,remote_version,local_hash,"
                      "all_day,origin) VALUES(?,?,?,?,?,?,?)",
                      (lid, eid, rid, ver, fp, int(all_day), m["origin"] if m else "local"))
        stats["pushed"] += 1
    for m in maps.values():
        if m["event_id"] in local or m["origin"] == "remote-ro":
            continue                                           # (read-only occurrences stay as tombstones)
        provider.delete(m["remote_id"])                        # deleted here: delete there too
        with db.conn() as c:
            c.execute("DELETE FROM event_links WHERE link_id=? AND remote_id=?", (lid, m["remote_id"]))
        stats["removed_there"] += 1

    with db.conn() as c:
        if new_cursor:
            c.execute("UPDATE calendar_links SET cursor_enc=? WHERE id=?", (crypto.encrypt(new_cursor), lid))
        acct = getattr(provider, "account", None)
        if acct and link["provider"] == "google":
            c.execute("UPDATE calendar_links SET account=? WHERE id=?", (acct[:200], lid))
    return stats


# ---------------------------------------------------------------- when syncs run
def sync_user(user_id: str):
    with db.conn() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM calendar_links WHERE user_id=? AND status<>'reauth'",
                                          (user_id,))]
    return [sync_link(i) for i in ids]


def kick(user_id: str):
    """A local event changed: push it out soon (in the background)."""
    try:
        with db.conn() as c:
            if not c.execute("SELECT 1 FROM calendar_links WHERE user_id=? LIMIT 1", (user_id,)).fetchone():
                return
        if ASYNC:
            _pool.submit(sync_user, user_id)
        else:
            sync_user(user_id)
    except Exception:
        log.exception("could not start a sync")


def sync_all():
    with db.conn() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM calendar_links WHERE status IN ('ok','error','paused')")]
    for i in ids:
        sync_link(i)


def start_worker():
    """Start the background thread that syncs every few minutes. Safe to call on every Streamlit rerun."""
    with _locks_guard:
        if _worker["started"]:
            return
        _worker["started"] = True

    def loop():
        while True:
            time.sleep(config.SYNC_INTERVAL)
            try:
                sync_all()
            except Exception:
                log.exception("scheduled sync failed")
    threading.Thread(target=loop, name="lawvault-sync-worker", daemon=True).start()
