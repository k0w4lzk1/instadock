from pydantic import BaseModel, HttpUrl, validator, root_validator
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

    # FIX: Replaced problematic @validator('image', always=True) with a root validator (Pydantic v1) 
    # to reliably check the presence of cross-field dependencies.
    @root_validator(pre=True)
    def validate_mode(cls, values):
        # Check if keys are explicitly present and have a non-None value
        has_image = 'image' in values and values['image'] is not None
        has_submission = 'submission_id' in values and values['submission_id'] is not None
        
        if has_image and has_submission:
            raise ValueError("Provide only ONE: 'image' OR 'submission_id'.")
        if not has_image and not has_submission:
            raise ValueError("Either 'image' or 'submission_id' must be provided.")
        
        return values


class SpawnResp(BaseModel):
    cid: str
    url: str
    expires_at: datetime


# ---------------------- ADMIN SUBMISSION IMAGE CHECK ----------------------

class SubmissionImageResp(BaseModel):
    submission_id: str
    image_tag: Optional[str]
    status: Optional[str] = None