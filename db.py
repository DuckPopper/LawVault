"""SQLite storage. Every query is parameterised (no SQL injection)."""
from __future__ import annotations
import sqlite3, time, uuid
from contextlib import contextmanager
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user', plan TEXT NOT NULL DEFAULT 'free', plan_expires REAL,
  failed_attempts INTEGER NOT NULL DEFAULT 0, locked_until REAL NOT NULL DEFAULT 0,
  created_at REAL NOT NULL, consent_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS otps(
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  purpose TEXT NOT NULL, code_hash TEXT NOT NULL, salt TEXT NOT NULL,
  expires_at REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, used INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
  token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at REAL NOT NULL, last_seen REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, user_id TEXT, event TEXT NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS cases(
  id TEXT PRIMARY KEY, title_enc TEXT NOT NULL, desc_enc TEXT, owner_id TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS case_members(
  case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member', added_at REAL NOT NULL, PRIMARY KEY(case_id, user_id));
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, body_enc TEXT NOT NULL, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS documents(
  id TEXT PRIMARY KEY, case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  filename_enc TEXT NOT NULL, text_enc TEXT NOT NULL, analysis_enc TEXT, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS usage(
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, day TEXT NOT NULL,
  ai_calls INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, day));
CREATE TABLE IF NOT EXISTS ai_chats(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL, content_enc TEXT NOT NULL, ts REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_msg_case ON messages(case_id, id);
CREATE TABLE IF NOT EXISTS calendar_settings(
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  visibility TEXT NOT NULL DEFAULT 'private');
CREATE TABLE IF NOT EXISTS calendar_access(
  owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  viewer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  level TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL, PRIMARY KEY(owner_id, viewer_id));
CREATE TABLE IF NOT EXISTS events(
  id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title_enc TEXT NOT NULL, notes_enc TEXT, start_ts REAL NOT NULL, end_ts REAL NOT NULL,
  case_id TEXT REFERENCES cases(id) ON DELETE SET NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS event_attendees(
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pending', PRIMARY KEY(event_id, user_id));
CREATE INDEX IF NOT EXISTS idx_events_owner ON events(owner_id, start_ts);
CREATE TABLE IF NOT EXISTS presence(
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'online', last_active REAL NOT NULL DEFAULT 0, last_heartbeat REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, text_enc TEXT NOT NULL, link TEXT, ref TEXT, count INTEGER NOT NULL DEFAULT 1,
  read INTEGER NOT NULL DEFAULT 0, toasted INTEGER NOT NULL DEFAULT 0, ts REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, read, id);
CREATE TABLE IF NOT EXISTS case_tasks(
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, title_enc TEXT NOT NULL, due_ts REAL,
  assignee_id TEXT REFERENCES users(id) ON DELETE SET NULL, done INTEGER NOT NULL DEFAULT 0,
  created_by TEXT REFERENCES users(id) ON DELETE SET NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS user_totp(
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  secret_enc TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0, last_step INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS known_devices(
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, device_hash TEXT NOT NULL,
  first_seen REAL NOT NULL, PRIMARY KEY(user_id, device_hash));
CREATE TABLE IF NOT EXISTS legal_work(
  id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  case_id TEXT REFERENCES cases(id) ON DELETE CASCADE, tool TEXT NOT NULL,
  matter TEXT, title_enc TEXT NOT NULL, result_enc TEXT NOT NULL, created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_legal_case ON legal_work(case_id, created_at);
CREATE INDEX IF NOT EXISTS idx_legal_owner ON legal_work(owner_id, created_at);
"""

# Columns added after the first version. Added in place so existing databases keep working.
MIGRATIONS = [
    ("messages", "kind", "TEXT NOT NULL DEFAULT 'user'"),
    ("sessions", "user_agent", "TEXT"),
    ("sessions", "ip", "TEXT"),
    ("legal_work", "matter", "TEXT"),
]


@contextmanager
def conn():
    c = sqlite3.connect(config.DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(SCHEMA)
        for table, col, decl in MIGRATIONS:
            cols = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        c.execute("UPDATE case_members SET role='editor' WHERE role='member'")  # roles v2


def uid() -> str:
    return uuid.uuid4().hex


def now() -> float:
    return time.time()


def audit(event: str, user_id=None, detail: str = ""):
    """Events only - never passwords, OTPs, or document contents."""
    with conn() as c:
        c.execute("INSERT INTO audit_log(ts,user_id,event,detail) VALUES(?,?,?,?)",
                  (now(), user_id, event, detail[:200]))
