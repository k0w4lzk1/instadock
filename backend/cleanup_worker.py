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

def cleanup_old_images():
    try:
        result = subprocess.run(["docker", "images", "-q", "ghcr.io/k0w4lzk1/*"], capture_output=True, text=True)
        for img in result.stdout.strip().split("\n"):
            if img:
                subprocess.run(["docker", "rmi", "-f", img])
                print(f"[🧹 Removed local GHCR image {img}]")
    except Exception as e:
        print(f"[⚠️ Cleanup failed: {e}]")