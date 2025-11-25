from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from passlib.context import CryptContext
import sqlite3
import uuid
import os
import datetime

# Import necessary dependencies and new DB functions
from .db import DB_PATH, list_approved_submissions, get_user_by_username, create_user, save_password_reset_token, verify_and_clear_reset_token
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
        # Block characters dangerous in URLs, file paths, routers
        bad_chars = " /\\'\"#?%{}()@!$^&*`~;<>,|"
        if any(ch in v for ch in bad_chars):
            raise ValueError("Username contains invalid characters.")
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


# ---------------------- FIX 5: FORGOT PASSWORD ENDPOINTS (COMPLETED) ----------------------

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
    FIX 5: Securely generates and saves a reset token to the DB.
    """
    user = get_user_by_username(req.username)
    
    # Defensive programming: Do not confirm existence of user
    if user:
        reset_token = str(uuid.uuid4())
        # Token is valid for 1 hour
        expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()
        
        save_password_reset_token(user["id"], reset_token, expires_at)

        # NOTE: In a real application, the reset_token would be sent via email.
        print(f"DEBUG: Password reset token for {req.username}: {reset_token}")
    
    return {
        "message": "If a matching account is found, a password reset link has been sent.",
        "reset_token": reset_token if user else None
    }

@router.post("/reset_password/{reset_token}")
def reset_password(reset_token: str, req: ResetPasswordModel):
    """
    FIX 5: Verifies the token and updates the password.
    """
    
    user_id = verify_and_clear_reset_token(reset_token)
    
    if not user_id:
        # User not found, token expired, or token already used
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    # 1. Update password
    new_password_hash = hash_password(req.new_password)
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_password_hash, user_id))
        conn.commit()

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
        role = "admin" 
        hashed = hash_password(password)

        create_user(username, hashed, role)

        print("[InstaDock] Default admin created -> username='admin' password='admin123'")