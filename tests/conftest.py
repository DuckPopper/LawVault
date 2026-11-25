import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["LAWVAULT_DATA_DIR"] = tempfile.mkdtemp()
os.environ["DEV_MODE"] = "1"
os.environ["GEMINI_API_KEY"] = ""
os.environ["HIBP_CHECK"] = "0"
import pytest


@pytest.fixture(autouse=True)
def fresh_db():
    import calsync, config, db
    calsync.ASYNC = False          # a change syncs inline, so tests never race a background thread
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    db.init_db()


def make_user(email, pw="Str0ngPassw0rd!"):
    import auth, db
    ok, msg = auth.signup(email, pw, True)
    assert ok, msg
    with db.conn() as c:
        return c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
