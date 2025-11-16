from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
from passlib.context import CryptContext
import sqlite3
import uuid

from .db import DB_PATH
from .auth import create_token

router = APIRouter()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ---------------------- REQUEST MODELS ----------------------

class RegisterReq(BaseModel):
    username: str
    password: str

    @validator("username")
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        # Block characters dangerous in URLs, file paths, routers
        bad_chars = " /\\'\"#?%{}()@!$^&*`~;<>,|"
        if any(ch in v for ch in bad_chars):
            raise ValueError("Username contains invalid characters.")
        return v

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


class LoginReq(BaseModel):
    username: str
    password: str


# ---------------------- REGISTER ----------------------

@router.post("/register")
def register(req: RegisterReq):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        user_id = str(uuid.uuid4())
        hashed = pwd_context.hash(req.password)

        try:
            cur.execute("""
                INSERT INTO users (id, username, password_hash, role)
                VALUES (?, ?, ?, 'user')
            """, (user_id, req.username, hashed))
        except sqlite3.IntegrityError:
            raise HTTPException(400, "Username already exists")

        conn.commit()

    token = create_token(user_id, "user")
    return {
        "msg": "User registered",
        "access_token": token,
        "token_type": "bearer"
    }


# ---------------------- LOGIN ----------------------

@router.post("/login")
def login(req: LoginReq):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, password_hash, role FROM users
            WHERE username=?
        """, (req.username,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(401, "Invalid username or password")

    user_id, password_hash, role = row

    if not pwd_context.verify(req.password, password_hash):
        raise HTTPException(401, "Invalid username or password")

    token = create_token(user_id, role)
    return {
        "access_token": token,
        "token_type": "bearer"
    }


# ---------------------- DEFAULT ADMIN CREATION ----------------------

def ensure_default_admin():
    """
    Creates a default admin if none exists.
    This is the ONLY path to admin privileges.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE role='admin'")
        admin = cur.fetchone()

        if admin:
            print("[InstaDock] Admin already exists.")
            return

        user_id = str(uuid.uuid4())
        username = "admin"
        password = "admin123"  # User should change this manually after first login

        hashed = pwd_context.hash(password)

        cur.execute("""
            INSERT INTO users (id, username, password_hash, role)
            VALUES (?, ?, ?, 'admin')
        """, (user_id, username, hashed))

        conn.commit()

        print("[InstaDock] Default admin created -> username='admin' password='admin123'")
