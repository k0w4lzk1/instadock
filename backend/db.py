import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "instadock.db"

def init_db():
    """Initialize database tables if they don't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        # Users table
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
        )
        """)
        # Submissions table
        c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            branch TEXT NOT NULL,
            status TEXT NOT NULL,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        conn.commit()


def record_submission(sub_id: str, user_id: str, branch: str, status: str, source: str):
    """Insert new submission into DB."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        INSERT INTO submissions (id, user_id, branch, status, source)
        VALUES (?, ?, ?, ?, ?)
        """, (sub_id, user_id, branch, status, source))
        conn.commit()


def get_submission(sub_id: str):
    """Fetch submission by ID."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, user_id, branch, status, source FROM submissions WHERE id=?", (sub_id,))
        row = c.fetchone()
        if not row:
            return None
        keys = ["id", "user_id", "branch", "status", "source"]
        return dict(zip(keys, row))


def update_submission_status(sub_id: str, new_status: str):
    """Update submission status."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE submissions SET status=? WHERE id=?", (new_status, sub_id))
        conn.commit()

def set_image_for_submission(sub_id: str, image_tag: str):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE submissions SET image_tag=? WHERE id=?", (image_tag, sub_id))
        conn.commit()

def list_pending_submissions():
    """Return all submissions with status 'pending'."""
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM submissions WHERE status='pending'")
        rows = [dict(row) for row in c.fetchall()]
    return rows

# Initialize DB at import
init_db()
