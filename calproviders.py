"""Talking to Google Calendar (REST + OAuth) and Apple iCloud Calendar (CalDAV).

Each provider offers the same three calls, so calsync.py never needs to know which one it is dealing with:
    pull(cursor, start, end) -> (events, new_cursor, complete)
    push(event, remote_id, all_day) -> (remote_id, version)
    delete(remote_id)

Only title, notes, location and times travel. Attendees are never sent, so Google or Apple can't e-mail anyone.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import urllib.parse
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
import requests
import config

GOOGLE_API = "https://www.googleapis.com/calendar/v3"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_SCOPE = "https://www.googleapis.com/auth/calendar.events"
ICLOUD_URL = "https://caldav.icloud.com/"          # fixed on purpose: no user-supplied server, so no SSRF


class AuthError(Exception):
    """The saved sign-in no longer works; the user must connect again."""


class ProviderError(Exception):
    """Anything else that went wrong talking to the provider."""


@dataclass
class RemoteEvent:
    id: str
    version: str = ""
    title: str = ""
    notes: str = ""
    location: str = ""
    start: float = 0.0
    end: float = 0.0
    all_day: bool = False
    updated: float = 0.0
    deleted: bool = False
    read_only: bool = False       # e.g. one occurrence of a recurring Apple event: shown here, never written back


def fingerprint(title: str, notes: str, location: str, start: float, end: float, all_day: bool = False) -> str:
    """A stable summary of an event's content. Used to tell 'changed' from 'same' on either side."""
    raw = json.dumps([title or "", notes or "", location or "", int(start), int(end), bool(all_day)],
                     ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _ts(d: dt.datetime) -> float:
    return d.timestamp()


def _day_ts(d: dt.date) -> float:
    return dt.datetime.combine(d, dt.time(0)).timestamp()


def _utc(ts: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)


def _parse_rfc3339(s: str) -> float:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


# =========================================================== Google
class Google:
    kind = "google"

    def __init__(self, cred: dict, save: Optional[Callable[[dict], None]] = None):
        self.cred, self._save, self.account = cred, save, None

    # --- tokens
    def _token(self) -> str:
        if self.cred.get("access_token") and self.cred.get("expires_at", 0) > dt.datetime.now().timestamp() + 60:
            return self.cred["access_token"]
        r = requests.post(GOOGLE_TOKEN_URL, timeout=config.SYNC_HTTP_TIMEOUT, data=dict(
            client_id=config.GOOGLE_CLIENT_ID, client_secret=config.GOOGLE_CLIENT_SECRET,
            refresh_token=self.cred.get("refresh_token", ""), grant_type="refresh_token"))
        if r.status_code in (400, 401):
            raise AuthError("Google no longer accepts this connection.")
        r.raise_for_status()
        body = r.json()
        self.cred["access_token"] = body["access_token"]
        self.cred["expires_at"] = dt.datetime.now().timestamp() + int(body.get("expires_in", 3600))
        if self._save:
            self._save(self.cred)
        return self.cred["access_token"]

    def _req(self, method: str, path: str, **kw):
        r = None
        for attempt in (0, 1):
            r = requests.request(method, GOOGLE_API + path, timeout=config.SYNC_HTTP_TIMEOUT,
                                 headers={"Authorization": f"Bearer {self._token()}"}, **kw)
            if r.status_code == 401 and attempt == 0:
                self.cred["expires_at"] = 0          # token revoked or stale: refresh once and retry
                continue
            break
        if r.status_code in (401, 403) and "rateLimit" not in r.text and "quota" not in r.text.lower():
            raise AuthError("Google refused access to the calendar.")
        return r

    # --- reading
    @staticmethod
    def _when(part: dict) -> Tuple[Optional[float], bool]:
        if "dateTime" in part:
            return _parse_rfc3339(part["dateTime"]), False
        if "date" in part:
            return _day_ts(dt.date.fromisoformat(part["date"])), True
        return None, False

    def _parse(self, it: dict) -> Optional[RemoteEvent]:
        if it.get("status") == "cancelled":
            return RemoteEvent(id=it["id"], deleted=True)
        if it.get("eventType") in ("workingLocation", "birthday", "fromGmail"):
            return None
        start, all_day = self._when(it.get("start", {}))
        end, _ = self._when(it.get("end", {}))
        if start is None:
            return None
        upd = _parse_rfc3339(it["updated"]) if it.get("updated") else 0.0
        return RemoteEvent(id=it["id"], version=it.get("etag", ""), title=it.get("summary") or "(no title)",
                           notes=it.get("description") or "", location=it.get("location") or "", start=start,
                           end=end if end is not None and end > start else start + 1800, all_day=all_day,
                           updated=upd)

    def pull(self, cursor: Optional[str], start: float, end: float):
        events: List[RemoteEvent] = []
        page, new_cursor = None, None
        for _ in range(40):
            params = dict(singleEvents="true", showDeleted="true", maxResults=250)
            if cursor:
                params["syncToken"] = cursor
            else:
                params.update(timeMin=_utc(start).isoformat(), timeMax=_utc(end).isoformat())
            if page:
                params["pageToken"] = page
            r = self._req("GET", "/calendars/primary/events", params=params)
            if r.status_code == 410:                 # the sync token expired: start again from a full listing
                return self.pull(None, start, end)
            r.raise_for_status()
            data = r.json()
            self.account = data.get("summary") or self.account
            events += [e for e in (self._parse(i) for i in data.get("items", [])) if e]
            page = data.get("nextPageToken")
            if not page:
                new_cursor = data.get("nextSyncToken")
                break
        return events, new_cursor, cursor is None

    # --- writing
    @staticmethod
    def _body(ev: dict, all_day: bool) -> dict:
        body = {"summary": ev["title"], "description": ev["notes"], "location": ev["location"],
                "reminders": {"useDefault": True}}
        if all_day:
            s = dt.date.fromtimestamp(ev["start"])
            e = max(dt.date.fromtimestamp(ev["end"]), s + dt.timedelta(days=1))
            body["start"], body["end"] = {"date": s.isoformat()}, {"date": e.isoformat()}
        else:
            body["start"] = {"dateTime": _utc(ev["start"]).isoformat(), "timeZone": "UTC"}
            body["end"] = {"dateTime": _utc(ev["end"]).isoformat(), "timeZone": "UTC"}
        return body

    def push(self, ev: dict, remote_id: Optional[str], all_day: bool = False):
        body = self._body(ev, all_day)
        if remote_id:
            r = self._req("PATCH", f"/calendars/primary/events/{urllib.parse.quote(remote_id, safe='')}",
                          params={"sendUpdates": "none"}, json=body)
            if r.status_code not in (404, 410):
                r.raise_for_status()
                return remote_id, r.json().get("etag", "")
        r = self._req("POST", "/calendars/primary/events", params={"sendUpdates": "none"}, json=body)
        r.raise_for_status()
        j = r.json()
        return j["id"], j.get("etag", "")

    def delete(self, remote_id: str):
        r = self._req("DELETE", f"/calendars/primary/events/{urllib.parse.quote(remote_id, safe='')}",
                      params={"sendUpdates": "none"})
        if r.status_code not in (404, 410):
            r.raise_for_status()


# =========================================================== Apple (CalDAV)
def _vevent_to_remote(comp, rid: str, read_only: bool) -> Optional[RemoteEvent]:
    """One VEVENT component -> RemoteEvent."""
    def val(name):
        v = comp.get(name)
        return v.dt if v is not None and hasattr(v, "dt") else None
    s = val("dtstart")
    if s is None:
        return None
    all_day = not isinstance(s, dt.datetime)
    start = _day_ts(s) if all_day else _ts(s)
    e = val("dtend")
    if e is not None:
        end = _day_ts(e) if not isinstance(e, dt.datetime) else _ts(e)
    elif val("duration") is not None:
        end = start + val("duration").total_seconds()
    else:
        end = start + (86400 if all_day else 1800)
    if end <= start:
        end = start + 1800
    mod = val("last-modified")
    title, notes, loc = str(comp.get("summary", "") or ""), str(comp.get("description", "") or ""), str(
        comp.get("location", "") or "")
    return RemoteEvent(id=rid, version=fingerprint(title, notes, loc, start, end, all_day),
                       title=title or "(no title)", notes=notes, location=loc, start=start, end=end,
                       all_day=all_day, updated=_ts(mod) if isinstance(mod, dt.datetime) else 0.0,
                       read_only=read_only)


def build_ics(ev: dict, uid: str, all_day: bool) -> str:
    import icalendar
    cal = icalendar.Calendar()
    cal.add("prodid", "-//LawVault//Calendar//EN")
    cal.add("version", "2.0")
    comp = icalendar.Event()
    comp.add("uid", uid)
    comp.add("dtstamp", dt.datetime.now(dt.timezone.utc))
    _fill(comp, ev, all_day)
    cal.add_component(comp)
    return cal.to_ical().decode()


def _fill(comp, ev: dict, all_day: bool):
    for k in ("summary", "description", "location", "dtstart", "dtend", "duration"):
        if k in comp:
            del comp[k]
    comp.add("summary", ev["title"])
    if ev["notes"]:
        comp.add("description", ev["notes"])
    if ev["location"]:
        comp.add("location", ev["location"])
    if all_day:
        s = dt.date.fromtimestamp(ev["start"])
        comp.add("dtstart", s)
        comp.add("dtend", max(dt.date.fromtimestamp(ev["end"]), s + dt.timedelta(days=1)))
    else:
        comp.add("dtstart", _utc(ev["start"]))
        comp.add("dtend", _utc(ev["end"]))


class Apple:
    kind = "apple"

    def __init__(self, cred: dict, save: Optional[Callable[[dict], None]] = None):
        self.cred, self._save, self.account = cred, save, cred.get("username")
        self._cal = None

    # --- connection (the seam tests replace)
    @staticmethod
    def _client(username: str, password: str):
        import caldav
        return caldav.DAVClient(url=ICLOUD_URL, username=username, password=password)

    @classmethod
    def discover(cls, username: str, password: str):
        """Sign in and list the calendars that can hold events: [(name, url)]. Raises AuthError on a bad login."""
        try:
            from caldav.lib import error as dav_error
            principal = cls._client(username, password).principal()
            out = []
            for c in principal.calendars():
                try:
                    kinds = c.get_supported_components()
                except Exception:
                    kinds = ["VEVENT"]
                if "VEVENT" in kinds:
                    out.append((str(c.name or "Calendar"), str(c.url)))
            return out
        except Exception as e:
            if e.__class__.__name__ in ("AuthorizationError", "PropfindError") or "401" in str(e):
                raise AuthError("Apple did not accept that Apple ID or app-specific password.")
            raise ProviderError("Could not reach iCloud.")

    def _calendar(self):
        if self._cal is None:
            import caldav
            client = self._client(self.cred["username"], self.cred["password"])
            self._cal = caldav.Calendar(client=client, url=self.cred["calendar_url"])
        return self._cal

    def _wrap(self, fn):
        try:
            return fn()
        except (AuthError, ProviderError):
            raise
        except Exception as e:
            if e.__class__.__name__ == "AuthorizationError":
                raise AuthError("Apple did not accept the saved sign-in.")
            raise ProviderError("iCloud is unavailable right now.")

    # --- reading
    def pull(self, cursor: Optional[str], start: float, end: float):
        def run():
            import recurring_ical_events
            out: List[RemoteEvent] = []
            objs = self._calendar().search(start=_utc(start), end=_utc(end), event=True, expand=False)
            for obj in objs:
                href = str(obj.url)
                cal = obj.icalendar_instance
                comps = [c for c in cal.walk("VEVENT")]
                recurring = any("rrule" in c or "recurrence-id" in c for c in comps)
                if recurring:
                    for inst in recurring_ical_events.of(cal).between(_utc(start), _utc(end)):
                        s = inst.get("dtstart").dt
                        stamp = (s.isoformat() if hasattr(s, "isoformat") else str(s))
                        r = _vevent_to_remote(inst, f"{href}#{stamp}", True)
                        if r:
                            out.append(r)
                elif comps:
                    r = _vevent_to_remote(comps[0], href, False)
                    if r:
                        out.append(r)
            return out, None, True            # a full listing every time: anything missing was deleted
        return self._wrap(run)

    # --- writing
    def push(self, ev: dict, remote_id: Optional[str], all_day: bool = False):
        def run():
            import caldav
            cal = self._calendar()
            if remote_id:
                try:
                    obj = caldav.Event(client=cal.client, url=remote_id)
                    obj.load()
                    comp = next(iter(obj.icalendar_instance.walk("VEVENT")))
                    _fill(comp, ev, all_day)
                    obj.save()
                    return remote_id, fingerprint(ev["title"], ev["notes"], ev["location"], ev["start"], ev["end"],
                                                  all_day)
                except Exception as e:
                    if e.__class__.__name__ != "NotFoundError":
                        raise                         # not "deleted meanwhile": treat as a real error
            uid = f"{ev.get('uid') or hashlib.sha256(json.dumps(ev, sort_keys=True).encode()).hexdigest()}@lawvault"
            obj = cal.save_event(build_ics(ev, uid, all_day))
            return str(obj.url), fingerprint(ev["title"], ev["notes"], ev["location"], ev["start"], ev["end"],
                                             all_day)
        return self._wrap(run)

    def delete(self, remote_id: str):
        def run():
            import caldav
            try:
                caldav.Event(client=self._calendar().client, url=remote_id.split("#")[0]).delete()
            except Exception as e:
                if e.__class__.__name__ != "NotFoundError":
                    raise
        return self._wrap(run)


def make(kind: str, cred: dict, save=None):
    if kind == "google":
        return Google(cred, save)
    if kind == "apple":
        return Apple(cred, save)
    raise ValueError("unknown provider")
