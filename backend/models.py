from pydantic import BaseModel, HttpUrl, validator
from typing import Optional
from datetime import datetime


# ------------------------------------------------------------
# 🟩 SUBMISSION INPUT
# ------------------------------------------------------------

class SubmitRepoReq(BaseModel):
    repo_url: HttpUrl
    ref: Optional[str] = None


class SubmitZipResp(BaseModel):
    submission_id: str
    branch: str
    status: str = "pending"


# ------------------------------------------------------------
# 🟩 SPAWN INPUT
# ------------------------------------------------------------

class SpawnReq(BaseModel):
    # ONE of these must be provided
    image: Optional[str] = None
    submission_id: Optional[str] = None
    
    ttl_seconds: int = 600

    @validator("ttl_seconds")
    def validate_ttl(cls, v):
        if v < 60:
            raise ValueError("TTL must be at least 60 seconds")
        if v > 86400:  # 24 hours
            raise ValueError("TTL too large")
        return v

    @validator("image", always=True)
    def validate_spawn_mode(cls, v, values):
        """
        Ensure user sends *either* image or submission_id.
        """
        sub = values.get("submission_id")
        if not v and not sub:
            raise ValueError("Either 'image' or 'submission_id' must be provided.")
        if v and sub:
            raise ValueError("Provide only one: 'image' OR 'submission_id'.")
        return v


# ------------------------------------------------------------
# 🟩 SPAWN OUTPUT
# ------------------------------------------------------------

class SpawnResp(BaseModel):
    cid: str
    url: str
    expires_at: datetime   # Convert ISO string → datetime automatically


# ------------------------------------------------------------
# 🟩 SUBMISSION → IMAGE TAG RESPONSE
# ------------------------------------------------------------

class SubmissionImageResp(BaseModel):
    submission_id: str
    image_tag: Optional[str]
    status: str
