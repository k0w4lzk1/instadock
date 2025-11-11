import time, datetime, sqlite3
from .db import DB_PATH
from .docker_manager import stop

while True:
    now = datetime.datetime.utcnow()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT cid, expires_at FROM instances").fetchall()
    for cid, exp in rows:
        if datetime.datetime.fromisoformat(exp) <= now:
            stop(cid)
    time.sleep(60)
