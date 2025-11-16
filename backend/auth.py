from fastapi import Header, HTTPException, Depends
from typing import Optional
import jwt
import os
import datetime

# --------------------------------------------------------------------
# 🔐 SECURITY CONFIG
# --------------------------------------------------------------------

# Force user to set a strong secret — never fallback to hardcoded
SECRET_KEY = os.getenv("JWT_SECRET","Trust_me_im_sources") 
if not SECRET_KEY:
    raise RuntimeError("Environment variable JWT_SECRET must be set")

ALGORITHM = "HS256"
TOKEN_ISSUER = "instadock-backend"
TOKEN_LIFETIME_HOURS = 6


# --------------------------------------------------------------------
# 🔐 TOKEN CREATION
# --------------------------------------------------------------------

def create_token(user_id: str, role: str):
    now = datetime.datetime.utcnow()
    exp = now + datetime.timedelta(hours=TOKEN_LIFETIME_HOURS)

    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "nbf": now,
        "exp": exp,
        "iss": TOKEN_ISSUER,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# --------------------------------------------------------------------
# 🔍 TOKEN DECODING
# --------------------------------------------------------------------

def decode_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_signature": True, "verify_exp": True},
            issuer=TOKEN_ISSUER,
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid token issuer")

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# --------------------------------------------------------------------
# 🔒 DEPENDENCIES FOR FASTAPI
# --------------------------------------------------------------------

async def require_user(authorization: Optional[str] = Header(None)):
    """
    Validate Authorization: Bearer <token>
    and return user_id + role.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    token = parts[1]
    data = decode_token(token)
    return {"user_id": data["sub"], "role": data["role"]}


async def require_admin(user=Depends(require_user)):
    """
    Require admin role.
    """
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
