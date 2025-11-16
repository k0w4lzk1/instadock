import time
import datetime
import sqlite3
from pathlib import Path

from .db import DB_PATH, get_instance, delete_instance
from .docker_manager import stop as stop_container

CHECK_INTERVAL = 30   # seconds between cleanup cycles


# ---------------------------------------------------------
# CLEANUP EXPIRED INSTANCES
# ---------------------------------------------------------

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
            print(f"[cleanup] Invalid timestamp for {cid} — deleting entry.")
            stop_container(cid)
            continue

        if exp_dt <= now:
            print(f"[cleanup] TTL expired → removing instance {cid}")
            stop_container(cid)


# ---------------------------------------------------------
# BACKGROUND WORKER LOOP
# ---------------------------------------------------------

def start_cleanup_worker():
    """
    Background loop.  
    Safe to run as a thread.  
    Will never crash the main app.
    """
    print("[cleanup] Worker started.")

    while True:
        try:
            cleanup_expired_instances()
        except Exception as e:
            print(f"[cleanup] Error: {e}")

        time.sleep(CHECK_INTERVAL)
