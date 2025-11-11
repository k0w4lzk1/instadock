from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
import sqlite3, uuid, os, jwt, datetime
from .db import DB_PATH

router = APIRouter()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key")


# --- Utility: create access token ---
def create_access_token(data: dict):
    data["exp"] = datetime.datetime.utcnow() + datetime.timedelta(hours=6)
    return jwt.encode(data, SECRET_KEY, algorithm="HS256")


# --- Request Models ---
class RegisterReq(BaseModel):
    username: str
    password: str
    role: str = "user"


class LoginReq(BaseModel):
    username: str
    password: str


# --- Register Endpoint ---
@router.post("/register")
def register(req: RegisterReq):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        try:
            user_id = str(uuid.uuid4())
            hash_ = pwd_context.hash(req.password)
            c.execute(
                "INSERT INTO users (id, username, password_hash, role) VALUES (?,?,?,?)",
                (user_id, req.username, hash_, req.role),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Username taken")

    # Optionally issue a token immediately after register
    token = create_access_token({"sub": user_id, "role": req.role})
    return {
        "msg": "User created",
        "access_token": token,
        "token_type": "bearer",
    }


# --- Login Endpoint ---
@router.post("/login")
def login(req: LoginReq):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, password_hash, role FROM users WHERE username=?", (req.username,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        uid, hash_, role = row
        if not pwd_context.verify(req.password, hash_):
            raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": uid, "role": role})
    return {"access_token": token, "token_type": "bearer"}


###---- Helper Module -----
def ensure_default_admin():
    """Create a default admin user if none exists."""
    from passlib.context import CryptContext
    import uuid

    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE role='admin'")
        exists = c.fetchone()
        if not exists:
            user_id = str(uuid.uuid4())
            username = "admin"
            password = "admin123"  # default password; change it immediately after login
            hashed = pwd_context.hash(password)
            c.execute(
                "INSERT INTO users (id, username, password_hash, role) VALUES (?,?,?,?)",
                (user_id, username, hashed, "admin"),
            )
            conn.commit()
            print(f"[⚙️ InstaDock] Default admin created → username='admin' password='admin123'")
        else:
            print("[⚙️ InstaDock] Admin user already exists.")