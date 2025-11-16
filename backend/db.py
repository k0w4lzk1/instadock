import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "instadock.db"

def init_db():
    """Initialize all required tables."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # --- Users ---
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """)

        # --- Submissions ---
        c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            branch TEXT NOT NULL,
            status TEXT NOT NULL,
            source TEXT,
            image_tag TEXT,               -- GHCR image URL/tag
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        # --- Instances ---
        c.execute("""
        CREATE TABLE IF NOT EXISTS instances (
            cid TEXT PRIMARY KEY,         -- Docker container ID (short)
            user_id TEXT NOT NULL,
            submission_id TEXT,           -- Optional: tie instance to submission
            image TEXT NOT NULL,
            subdomain TEXT NOT NULL,      -- e.g. cid123.localhost
            port INTEGER,                 -- only used if fallback to ports
            expires_at TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (submission_id) REFERENCES submissions (id)
        )
        """)

        conn.commit()


# --- Submission Helpers --------------------------------------------------

def record_submission(sub_id: str, user_id: str, branch: str, status: str, source: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO submissions (id, user_id, branch, status, source)
            VALUES (?, ?, ?, ?, ?)
        """, (sub_id, user_id, branch, status, source))
        conn.commit()


def update_submission_status(sub_id: str, new_status: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE submissions SET status=? WHERE id=?", (new_status, sub_id))
        conn.commit()


def set_submission_image(sub_id: str, image_tag: str):
    """Store GHCR image tag built by GitHub Actions."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE submissions SET image_tag=? WHERE id=?
        """, (image_tag, sub_id))
        conn.commit()


def get_submission(sub_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM submissions WHERE id=?", (sub_id,)).fetchone()
        return dict(row) if row else None


def list_pending_submissions():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM submissions WHERE status='pending'").fetchall()
        return [dict(r) for r in rows]


# --- Instance Helpers ------------------------------------------------------

def save_instance(cid: str, user_id: str, submission_id: str, image: str, subdomain: str, port: int, expires_at: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO instances (cid, user_id, submission_id, image, subdomain, port, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (cid, user_id, submission_id, image, subdomain, port, expires_at))
        conn.commit()


def delete_instance(cid: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM instances WHERE cid=?", (cid,))
        conn.commit()


def get_instance(cid: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM instances WHERE cid=?", (cid,)).fetchone()
        return dict(row) if row else None


def list_instances_for_user(user_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM instances WHERE user_id=? ORDER BY created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def list_all_instances():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM instances ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# Initialize database on import
init_db()
