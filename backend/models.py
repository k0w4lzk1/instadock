from pydantic import BaseModel, HttpUrl, validator
from typing import Optional
from datetime import datetime


# ---------------------- SUBMISSION API MODELS ----------------------

class SubmitRepoReq(BaseModel):
    repo_url: HttpUrl
    ref: Optional[str] = None


class SubmitZipResp(BaseModel):
    submission_id: str
    branch: str
    status: str = "pending"


# ---------------------- SPAWN API MODELS ----------------------

class SpawnReq(BaseModel):
    image: Optional[str] = None
    submission_id: Optional[str] = None
    ttl_seconds: int = 600

    @validator("ttl_seconds")
    def validate_ttl(cls, v):
        if v < 60:
            raise ValueError("TTL must be >= 60 seconds")
        if v > 86400:
            raise ValueError("TTL must be <= 86400 seconds (24h)")
        return v

    @validator("image", always=True)
    def validate_mode(cls, v, values):
        sub = values.get("submission_id")
        if not v and not sub:
            raise ValueError("Either 'image' or 'submission_id' must be provided.")
        if v and sub:
            raise ValueError("Provide only ONE: 'image' OR 'submission_id'.")
        return v


class SpawnResp(BaseModel):
    cid: str
    url: str
    expires_at: datetime


# ---------------------- ADMIN SUBMISSION IMAGE CHECK ----------------------

class SubmissionImageResp(BaseModel):
    submission_id: str
    image_tag: Optional[str]
    status: Optional[str] = None
