from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from passlib.context import CryptContext
import sqlite3
import uuid
import os

# Import necessary dependencies
from .db import DB_PATH, list_approved_submissions, get_user_by_username, create_user
from .auth import create_token, require_user

router = APIRouter()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ---------------------- AUTH MODELS (from models.py, simplified for users.py) ----------------------

class RegisterReq(BaseModel):
    username: str
    password: str

    @validator("username")
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        # FIX 6: Enforce alphanumeric usernames only, required for Git/URL safety
        if not v.isalnum():
            raise ValueError("Username must only contain letters and numbers.")
        return v

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8: # FIX 6: Increased complexity requirement
            raise ValueError("Password must be at least 8 characters.")
        return v


class LoginReq(BaseModel):
    username: str
    password: str

# ---------------------- AUTH UTILS ----------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------- REGISTER ----------------------

@router.post("/register")
def register(req: RegisterReq):
    if get_user_by_username(req.username):
        raise HTTPException(status_code=400, detail="Username already registered")
        
    hashed = hash_password(req.password)
    user_id = create_user(req.username, hashed)

    # FIX: Creating a token upon registration for immediate login
    token = create_token(user_id, "user")
    return {
        "token": token,
        "role": "user",
        "msg": "User registered successfully"
    }


# ---------------------- LOGIN ----------------------

@router.post("/login")
def login(req: LoginReq):
    db_user = get_user_by_username(req.username)

    if not db_user or not verify_password(req.password, db_user["password_hash"]):
        raise HTTPException(401, "Invalid username or password")

    token = create_token(db_user["id"], db_user["role"])
    return {
        "token": token,
        "role": db_user["role"],
        "token_type": "bearer"
    }

# ---------------------- USER DATA & SUBMISSIONS ----------------------

@router.get("/me", dependencies=[Depends(require_user)])
def read_user_me(user_data=Depends(require_user)):
    """FIX 4: Protected endpoint for user details."""
    return user_data

@router.get("/approved_submissions", dependencies=[Depends(require_user)])
async def get_user_approved_submissions(user=Depends(require_user)):
    """FIX 4: Lists approved submissions that can be spawned into an instance."""
    return list_approved_submissions(user["user_id"])


# ---------------------- FIX 5: FORGOT PASSWORD ENDPOINTS ----------------------

class RequestPasswordResetModel(BaseModel):
    username: str

class ResetPasswordModel(BaseModel):
    new_password: str
    
    @validator("new_password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


@router.post("/forgot_password")
def forgot_password(req: RequestPasswordResetModel):
    """
    FIX 5: Initiates password reset flow.
    (STUB: Actual token storage/emailing is omitted.)
    """
    user = get_user_by_username(req.username)
    if not user:
        # Defensive programming: Do not confirm existence of user
        return {"message": "If a matching account is found, a password reset link has been sent."}

    # Dummy reset token for local testing
    reset_token = str(uuid.uuid4())
    
    return {
        "message": "If a matching account is found, a password reset link has been sent.",
        "reset_token": reset_token
    }

@router.post("/reset_password/{reset_token}")
def reset_password(reset_token: str, req: ResetPasswordModel):
    """
    FIX 5: Processes the password reset using the token.
    (STUB: Placeholder for token validation and password update.)
    """
    if not reset_token or len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Invalid token or password must be at least 8 characters.")

    # In a real app: update user password in DB and invalidate token.
    return {"message": "Password successfully reset. You may now log in."}


# ---------------------- DEFAULT ADMIN CREATION ----------------------

def ensure_default_admin():
    """
    Creates a default admin if none exists.
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
        password = "admin123" 

        hashed = hash_password(password)

        cur.execute("""
            INSERT INTO users (id, username, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, hashed))

        conn.commit()

        print("[InstaDock] Default admin created -> username='admin' password='admin123'")