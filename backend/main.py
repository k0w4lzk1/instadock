from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models import (
    SubmitRepoReq,
    SubmitZipResp,
    SpawnReq,
    SpawnResp
)

# Submission management
from backend.repo_manager import (
    create_branch_from_zip,
    create_branch_from_repo,
    approve_submission,
    reject_submission
)

# Container lifecycle
from backend.docker_manager import (
    spawn,
    stop as stop_container,
    list_containers,
    system_stats,
)

# Auth system
from backend.auth import require_user, require_admin

# Users router
from backend.users import router as user_router
from backend.users import ensure_default_admin

# DB helpers
from backend.db import (
    get_submission,
    list_pending_submissions,
    list_instances_for_user,
    get_instance,
)

app = FastAPI(title="InstaDock API (Patched)")

import threading
from backend.cleanup_worker import start_cleanup_worker
threading.Thread(target=start_cleanup_worker, daemon=True).start()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount user login/register
app.include_router(user_router, prefix="/user")

# Ensure admin exists
ensure_default_admin()

# ---------------------------------------------------------
# 🟩 SUBMISSION ENDPOINTS
# ---------------------------------------------------------

@app.post("/submit/repo")
async def submit_repo(req: SubmitRepoReq, user=Depends(require_user)):
    """User submits a Git repo to be built."""
    try:
        sub_id, branch = create_branch_from_repo(
            user["user_id"], str(req.repo_url), req.ref
        )
        return SubmitZipResp(submission_id=sub_id, branch=branch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/submit/zip")
async def submit_zip(file: UploadFile = File(...), user=Depends(require_user)):
    """User uploads a ZIP folder submission."""
    try:
        sub_id, branch = create_branch_from_zip(user["user_id"], file)
        return SubmitZipResp(submission_id=sub_id, branch=branch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# 🟩 ADMIN SUBMISSION APPROVAL
# ---------------------------------------------------------

@app.post("/admin/approve/{sub_id}")
async def approve(sub_id: str, user=Depends(require_admin)):
    """
    Admin marks submission approved.
    GitHub Actions workflow will build & push to GHCR.
    """
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


@app.get("/admin/submissions", dependencies=[Depends(require_admin)])
def get_pending():
    return list_pending_submissions()


# ---------------------------------------------------------
# 🟩 INSTANCE SPAWNING
# ---------------------------------------------------------

@app.post("/spawn", response_model=SpawnResp)
async def spawn_container(req: SpawnReq, user=Depends(require_user)):
    """
    Spawn an instance either from:
    - a submission_id (GHCR-built image)
    - OR a raw image string
    """
    submission_id = None
    image_to_use = req.image

    # If submission ID provided → use GHCR image stored in DB
    if req.submission_id:
        submission = get_submission(req.submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        if not submission.get("image_tag"):
            raise HTTPException(
                status_code=400,
                detail="Image for this submission not available. Wait for GitHub Actions."
            )

        image_to_use = submission["image_tag"]
        submission_id = req.submission_id

    if not image_to_use:
        raise HTTPException(400, "No image or submission_id provided")

    try:
        cid, url, expires_at = spawn(
            image=image_to_use,
            user_id=user["user_id"],
            submission_id=submission_id,
            ttl_seconds=req.ttl_seconds
        )
        return SpawnResp(cid=cid, url=url, expires_at=expires_at)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# 🟩 INSTANCE MANAGEMENT
# ---------------------------------------------------------

@app.post("/stop/{cid}")
async def stop_instance(cid: str, user=Depends(require_user)):
    """
    Stop a container. Users can only stop their own.
    """
    instance = get_instance(cid)
    if not instance:
        raise HTTPException(404, "Instance not found")

    if instance["user_id"] != user["user_id"] and user["role"] != "admin":
        raise HTTPException(403, "You cannot stop another user's instance")

    stop_container(cid)
    return {"stopped": cid}


@app.get("/instance/me", dependencies=[Depends(require_user)])
async def list_user_instances(user=Depends(require_user)):
    """List all instances owned by the current user."""
    return list_instances_for_user(user["user_id"])


@app.get("/instance/{cid}", dependencies=[Depends(require_user)])
async def instance_details(cid: str, user=Depends(require_user)):
    """Get a single instance's info."""
    inst = get_instance(cid)
    if not inst:
        raise HTTPException(404, "Instance not found")

    if inst["user_id"] != user["user_id"] and user["role"] != "admin":
        raise HTTPException(403, "Forbidden")

    return inst


# ---------------------------------------------------------
# 🟩 SYSTEM ADMIN
# ---------------------------------------------------------

@app.get("/admin/containers", dependencies=[Depends(require_admin)])
def admin_list_containers():
    return list_containers()


@app.get("/system/stats", dependencies=[Depends(require_user)])
def stats():
    return system_stats()


# ---------------------------------------------------------
# 🟩 ROOT
# ---------------------------------------------------------

@app.get("/")
def root():
    return {"msg": "InstaDock backend patched & active!"}
