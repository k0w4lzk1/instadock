from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models import SubmitRepoReq, SubmitZipResp, SpawnReq, SpawnResp
from backend.repo_manager import create_branch_from_zip, create_branch_from_repo, approve_submission, reject_submission
from backend.docker_manager import spawn, stop, list_containers, system_stats
from backend.auth import require_user, require_admin
from backend.users import router as user_router
from backend.users import ensure_default_admin
from backend.db import list_pending_submissions

app = FastAPI(title="InstaDock API")

# Enable CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register /register and /login routes
app.include_router(user_router, prefix="/user")
ensure_default_admin()

@app.post("/submit/repo")
async def submit_repo(req: SubmitRepoReq, user=Depends(require_user)):
    try:
        sub_id, branch = create_branch_from_repo(user["user_id"], str(req.repo_url), req.ref)
        return SubmitZipResp(submission_id=sub_id, branch=branch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/submit/zip")
async def submit_zip(file: UploadFile = File(...), user=Depends(require_user)):
    try:
        sub_id, branch = create_branch_from_zip(user["user_id"], file)
        return SubmitZipResp(submission_id=sub_id, branch=branch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/approve/{sub_id}")
async def approve(sub_id: str, user=Depends(require_admin)):
    try:
        approve_submission(sub_id)
        return {"status": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/reject/{sub_id}")
async def reject(sub_id: str, user=Depends(require_admin)):
    try:
        reject_submission(sub_id)
        return {"status": "rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/spawn", response_model=SpawnResp)
async def spawn_container(req: SpawnReq, user=Depends(require_user)):
    try:
        cid, url, expires_at = spawn(req.image, req.ttl_seconds)
        return SpawnResp(cid=cid, url=url, expires_at=expires_at)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop/{cid}")
async def stop_container(cid: str, user=Depends(require_user)):
    stop(cid)
    return {"stopped": cid}

@app.get("/admin/containers", dependencies=[Depends(require_admin)])
def list_all_containers():
    return list_containers()

@app.get("/system/stats", dependencies=[Depends(require_user)])
def get_stats():
    return system_stats()

@app.get("/admin/submissions", dependencies=[Depends(require_admin)])
def get_pending_submissions():
    """List all pending submissions for the admin panel."""
    return list_pending_submissions()

@app.get("/")
def root():
    return {"msg": "InstaDock backend active!"}
