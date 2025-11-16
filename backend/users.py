from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
from passlib.context import CryptContext
import sqlite3
import uuid
from .db import DB_PATH
from .auth import create_token

router = APIRouter()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# --------------------------------------------------------------------
# 🟩 REQUEST MODELS
# --------------------------------------------------------------------

class RegisterReq(BaseModel):
    username: str
    password: str

    @validator("username")
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if any(ch in v for ch in " /\\'\"#?%{}()@!$^&*"):
            raise ValueError("Invalid characters in username")
        return v

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginReq(BaseModel):
    username: str
    password: str


# --------------------------------------------------------------------
# 🟩 REGISTER
# --------------------------------------------------------------------

@router.post("/register")
def register(req: RegisterReq):
    with sqlite3.connect(DB_PATH) as conn:
        try:
            c = conn.cursor()

            user_id = str(uuid.uuid4())
            password_hash = pwd_context.hash(req.password)

            # Force role=user. Admin cannot be self-created.
            c.execute("""
                INSERT INTO users (id, username, password_hash, role)
                VALUES (?, ?, ?, 'user')
            """, (user_id, req.username, password_hash))

            conn.commit()

        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Username already exists")

    # Create secure token
    token = create_token(user_id, "user")

    return {
        "msg": "User registered",
        "access_token": token,
        "token_type": "bearer",
    }


# --------------------------------------------------------------------
# 🟩 LOGIN
# --------------------------------------------------------------------

@router.post("/login")
def login(req: LoginReq):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, password_hash, role FROM users WHERE username=?",
            (req.username,)
        )
        row = c.fetchone()

        if not row:
            raise HTTPException(401, "Invalid username or password")

        user_id, password_hash, role = row

        if not pwd_context.verify(req.password, password_hash):
            raise HTTPException(401, "Invalid username or password")

    # Return signed token
    token = create_token(user_id, role)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# --------------------------------------------------------------------
# 🟩 ENSURE DEFAULT ADMIN (SAFE)
# --------------------------------------------------------------------

def ensure_default_admin():
    """
    Create a default admin if none exists.
    ONLY way admin can exist.
    """
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE role='admin'")
        exists = c.fetchone()

        if exists:
            print("[⚙️ InstaDock] Admin exists.")
            return

        user_id = str(uuid.uuid4())
        username = "admin"
        password = "admin123"

        hashed = pwd_context.hash(password)

        c.execute("""
            INSERT INTO users (id, username, password_hash, role)
            VALUES (?, ?, ?, 'admin')
        """, (user_id, username, hashed))

        conn.commit()

        print(f"[⚙️ InstaDock] Default admin created → username='admin' password='admin123' (CHANGE IT!)")
