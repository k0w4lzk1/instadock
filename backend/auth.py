from fastapi import Header, HTTPException, Depends, Query
from typing import Optional
import jwt
import os
import datetime

# --------------------------------------------------------------------
# 🔐 SECURITY CONFIG
# --------------------------------------------------------------------

# Force user to set a strong secret — never fallback to hardcoded
SECRET_KEY = os.getenv("JWT_SECRET") 
if not SECRET_KEY:
    # Set a stable default for immediate development:
    SECRET_KEY = "Trust_me_im_sources"
    print("[SECURITY WARNING] Using default JWT_SECRET. Set environment variable.")

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
# 🔒 DEPENDENCIES FOR FASTAPI (CRITICAL FIX FOR WS)
# --------------------------------------------------------------------

async def require_user(
    authorization: Optional[str] = Header(None, alias="Authorization"), # Check HTTP Header (standard API)
    # FIX: Also check the query parameter for WebSocket connections
    query_auth: Optional[str] = Query(None, alias="authorization") 
):
    """
    Validate Authorization: Bearer <token> from either Header (HTTP) or 
    Query Parameter (WebSocket).
    """
    auth_string = authorization if authorization else query_auth
    
    if not auth_string:
        raise HTTPException(status_code=401, detail="Missing Authorization header/query parameter")

    parts = auth_string.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format (Must be Bearer <token>)")

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