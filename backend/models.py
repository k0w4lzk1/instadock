from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class SubmitRepoReq(BaseModel):
    repo_url: HttpUrl
    ref: Optional[str] = None

class SubmitZipResp(BaseModel):
    submission_id: str
    branch: str
    status: str = "pending"

class SpawnReq(BaseModel):
    image: Optional[str] = None
    submission_id: Optional[str] = None
    ttl_seconds: int = 600

class SpawnResp(BaseModel):
    cid: str
    url: str
    expires_at: datetime
