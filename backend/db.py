import sqlite3
from pathlib import Path
import os 
import uuid 

DB_PATH = Path(__file__).resolve().parent / "instadock.db"

# FIX: Define the GHCR_USER constant locally to break the circular dependency.
GHCR_USER = os.getenv("GHCR_USERNAME", "k0w4lzk1")


def init_db():
    """Initialize database tables."""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        # Users (CRITICAL FIX: Added password reset fields)
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            reset_token TEXT,
            reset_expires_at TEXT
        )
        """)
        
        # Add password reset columns if they don't exist (for existing databases)
        try:
            c.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE users ADD COLUMN reset_expires_at TEXT")
        except sqlite3.OperationalError:
            pass


        # Submissions
        c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            branch TEXT NOT NULL,
            status TEXT NOT NULL,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        # Instances
        # FR-4.0: Added status column to track running/stopped state
        c.execute("""
        CREATE TABLE IF NOT EXISTS instances (
            cid TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            submission_id TEXT,
            image TEXT NOT NULL,
            subdomain TEXT NOT NULL,
            port INTEGER,
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running', 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (submission_id) REFERENCES submissions(id)
        )
        """)
        
        # Add 'image_tag' column to submissions if it doesn't exist (to simulate CI build result)
        try:
            c.execute("ALTER TABLE submissions ADD COLUMN image_tag TEXT")
        except sqlite3.OperationalError:
            pass 
        
        conn.commit()


# ---------------- SUBMISSIONS ----------------

def record_submission(sub_id, user_id, branch, status, source):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO submissions (id, user_id, branch, status, source)
            VALUES (?, ?, ?, ?, ?)
        """, (sub_id, user_id, branch, status, source))
        conn.commit()


def update_submission_status(sub_id, status):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE submissions SET status=? WHERE id=?", (status, sub_id))
        
        # Simulate CI/CD providing the image tag upon approval
        if status == 'approved':
             submission = get_submission(sub_id)
             submission_uuid = submission['id']
             
             # FIX: Reconstruct the image name exactly as observed in the successful manual pull.
             # The CI process is using the short ID (first 8 chars) as a suffix to the repository name.
             short_id = submission_uuid.split('-')[0]
             
             # The full repository name is 'instadock_' + short_id
             # The tag is implicitly ':latest'
             image_repo_name = f"instadock_{short_id}"
             image_tag = f"ghcr.io/{GHCR_USER}/{image_repo_name}:latest"
             
             conn.execute("UPDATE submissions SET image_tag=? WHERE id=?", (image_tag, sub_id))
        
        conn.commit()

def get_submission(sub_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM submissions WHERE id=?", (sub_id,)).fetchone()
        return dict(row) if row else None


def list_pending_submissions():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM submissions WHERE status='pending'").fetchall()
        return [dict(r) for r in rows]

def list_approved_submissions(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # Only list submissions that are 'approved' AND have a non-NULL image_tag
        rows = conn.execute("""
            SELECT * FROM submissions 
            WHERE user_id=? AND status='approved' AND image_tag IS NOT NULL
            ORDER BY created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]

def delete_submission(sub_id):
    """Admin function to permanently delete a submission record."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM submissions WHERE id=?", (sub_id,))
        conn.commit()

# ---------------- INSTANCES ----------------

def save_instance(cid, user_id, submission_id, image, subdomain, port, expires_at):
    with sqlite3.connect(DB_PATH) as conn:
        # FR-4.0: Insert with default status 'running'
        conn.execute("""
        INSERT INTO instances (cid, user_id, submission_id, image, subdomain, port, expires_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'running')
        """, (cid, user_id, submission_id, image, subdomain, port, expires_at))
        conn.commit()
        
def update_instance_status(cid, status):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE instances SET status=? WHERE cid=?", (status, cid))
        conn.commit()


def delete_instance(cid):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM instances WHERE cid=?", (cid,))
        conn.commit()


def get_instance(cid):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM instances WHERE cid=?", (cid,)).fetchone()
        return dict(row) if row else None


def list_instances_for_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # FR-4.0: List all instances for the user, regardless of status
        rows = conn.execute("""
            SELECT * FROM instances WHERE user_id=? ORDER BY created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def list_all_instances():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM instances ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

# ---------------- USER AUTH HELPERS ----------------

def get_user_by_username(username: str):
    """Retrieves user by username for login/registration checks."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return dict(row) if row else None
        
def create_user(username: str, password_hash: str, role: str = 'user'):
    """Creates a new user record."""
    user_id = str(uuid.uuid4())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO users (id, username, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, password_hash, role)) 
        conn.commit()
    return user_id

# FIX: New function to save the password reset token
def save_password_reset_token(user_id: str, token: str, expires_at: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE users SET reset_token=?, reset_expires_at=? WHERE id=?
        """, (token, expires_at, user_id))
        conn.commit()

# FIX: New function to verify and clear the token
def verify_and_clear_reset_token(token: str):
    now_iso = datetime.datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # Find user where token matches and has not expired
        user_row = conn.execute("""
            SELECT id, password_hash FROM users WHERE reset_token=? AND reset_expires_at > ?
        """, (token, now_iso)).fetchone()
        
        if user_row:
            user_data = dict(user_row)
            # Clear token immediately after successful verification
            conn.execute("UPDATE users SET reset_token=NULL, reset_expires_at=NULL WHERE id=?", (user_data["id"],))
            conn.commit()
            return user_data["id"]
        
        return None

# Initialize DB on import
init_db()