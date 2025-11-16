import time
import datetime
import sqlite3
import subprocess
from pathlib import Path

from backend.db import DB_PATH, get_instance, delete_instance
from backend.docker_manager import stop as stop_container


CHECK_INTERVAL = 30  # seconds — how often to check expiring instances


# -------------------------------------------------------------------
# 🟩 CLEANUP EXPIRED INSTANCES
# -------------------------------------------------------------------

def cleanup_expired_instances():
    """
    Remove containers whose TTL has expired.
    """
    now = datetime.datetime.utcnow()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT cid, expires_at FROM instances").fetchall()

    for row in rows:
        cid = row["cid"]
        exp = row["expires_at"]

        try:
            exp_dt = datetime.datetime.fromisoformat(exp)
        except Exception:
            print(f"[⚠] Invalid timestamp for {cid}, deleting entry.")
            stop_container(cid)
            continue

        if exp_dt <= now:
            print(f"[⏳] TTL expired → removing instance {cid}")
            stop_container(cid)


# -------------------------------------------------------------------
# 🟩 CLEANUP OLD LOCAL IMAGES (optional)
# -------------------------------------------------------------------

def cleanup_old_images():
    """
    Remove old GHCR images stored locally to free space.
    Only removes images in ghcr.io/<user>/*
    """
    try:
        result = subprocess.run(
            ["docker", "images", "-q", "ghcr.io/*"],
            capture_output=True,
            text=True
        )

        imgs = result.stdout.strip().split("\n")

        for img in imgs:
            if img:
                subprocess.run(["docker", "rmi", "-f", img])
                print(f"[🧹] Removed local GHCR image: {img}")

    except Exception as e:
        print(f"[⚠] GHCR cleanup failed: {e}")


# -------------------------------------------------------------------
# 🟩 MAIN WORKER LOOP
# -------------------------------------------------------------------

def start_cleanup_worker():
    """
    Main cleanup loop.
    Run this in a separate background process or thread.
    """
    print("[🧼 InstaDock Cleanup Worker] Started.")

    while True:
        try:
            cleanup_expired_instances()
        except Exception as e:
            print(f"[⚠] Instance cleanup error: {e}")

        # Optional: run less frequently
        # cleanup_old_images()

        time.sleep(CHECK_INTERVAL)
