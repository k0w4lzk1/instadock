from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import docker.errors
import sqlite3 
from backend.db import DB_PATH 
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
    reject_submission,
    delete_submission, 
)

# Container lifecycle
from backend.docker_manager import (
    spawn,
    stop as stop_container,
    start as start_container, 
    restart as restart_container,
    remove as remove_container, 
    list_containers,
    system_stats,
    client as docker_client, 
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
    list_all_instances,
    update_instance_status,
)

# FIX 4: Add dependencies to all API tools
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

# Mount user login/register/password reset (unprotected endpoints handled in users.py)
app.include_router(user_router, prefix="/user")

# Ensure admin exists
ensure_default_admin()

# ---------------------------------------------------------
# 🟩 SUBMISSION ENDPOINTS (FIX 4: PROTECTED)
# ---------------------------------------------------------

@app.post("/submit/repo", dependencies=[Depends(require_user)])
async def submit_repo(req: SubmitRepoReq, user=Depends(require_user)):
    """User submits a Git repo to be built."""
    try:
        sub_id, branch = create_branch_from_repo(
            user["user_id"], str(req.repo_url), req.ref
        )
        return SubmitZipResp(submission_id=sub_id, branch=branch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/submit/zip", dependencies=[Depends(require_user)])
async def submit_zip(file: UploadFile = File(...), user=Depends(require_user)):
    """User uploads a ZIP folder submission."""
    try:
        sub_id, branch = create_branch_from_zip(user["user_id"], file)
        return SubmitZipResp(submission_id=sub_id, branch=branch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# 🟩 ADMIN SUBMISSION APPROVAL (FIX 4: ADMIN ONLY)
# ---------------------------------------------------------

@app.post("/admin/approve/{sub_id}", dependencies=[Depends(require_admin)])
async def approve(sub_id: str):
    """Admin marks submission approved."""
    try:
        approve_submission(sub_id)
        return {"status": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/reject/{sub_id}", dependencies=[Depends(require_admin)])
async def reject(sub_id: str):
    try:
        reject_submission(sub_id)
        return {"status": "rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.delete("/admin/submission/{sub_id}", dependencies=[Depends(require_admin)])
async def admin_delete_submission(sub_id: str):
    """FIX 2: Admin permanently deletes a submission record and associated git branch."""
    try:
        delete_submission(sub_id) 
        return {"status": "permanently deleted", "sub_id": sub_id}
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/submissions", dependencies=[Depends(require_admin)])
def get_pending():
    """FIX 2: List pending submissions."""
    return list_pending_submissions()


# ---------------------------------------------------------
# 🟩 INSTANCE SPAWNING (FIX 4: PROTECTED)
# ---------------------------------------------------------

MAX_INSTANCES_PER_USER = 5

@app.post("/spawn", response_model=SpawnResp, dependencies=[Depends(require_user)])
async def spawn_container(req: SpawnReq, user=Depends(require_user)):
    """Spawn an instance."""
    user_id = user["user_id"]
    
    # NFR-1.2: Check instance quota (only count running instances towards quota)
    running_instances = [inst for inst in list_instances_for_user(user_id) if inst.get('status') == 'running']
    
    if len(running_instances) >= MAX_INSTANCES_PER_USER:
        raise HTTPException(
            status_code=429,
            detail=f"Quota exceeded. You are limited to {MAX_INSTANCES_PER_USER} active instances. Please stop an existing instance."
        )

    submission_id = None
    image_to_use = req.image

    # If submission ID provided → use GHCR image stored in DB
    if req.submission_id:
        submission = get_submission(req.submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Check if approved
        if submission.get("status") != 'approved':
             raise HTTPException(status_code=400, detail="Submission must be approved before spawning.")

        # Ensure image tag is available (CI/CD finished)
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
# 🟩 INSTANCE MANAGEMENT (FIX 4: PROTECTED)
# ---------------------------------------------------------

def check_instance_ownership(cid: str, user_data: dict):
    """Helper to check existence and ownership/admin role."""
    instance = get_instance(cid)
    if not instance:
        raise HTTPException(404, "Instance not found")
    
    # Allow only owner or admin to control the instance
    if instance["user_id"] != user_data["user_id"] and user_data["role"] != "admin":
        raise HTTPException(403, "You cannot control another user's instance")
    
    return instance


@app.post("/stop/{cid}", dependencies=[Depends(require_user)])
async def stop_instance(cid: str, user=Depends(require_user)):
    try:
        check_instance_ownership(cid, user)
        stop_container(cid)
        return {"status": "stopped", "cid": cid}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise e


@app.post("/start/{cid}", dependencies=[Depends(require_user)])
async def start_instance(cid: str, user=Depends(require_user)):
    try:
        instance = check_instance_ownership(cid, user)
        if instance["status"] == 'running':
             return {"status": "already running", "cid": cid}
             
        start_container(cid)
        return {"status": "started", "cid": cid}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise e


@app.post("/restart/{cid}", dependencies=[Depends(require_user)])
async def restart_instance(cid: str, user=Depends(require_user)):
    try:
        check_instance_ownership(cid, user)
        restart_container(cid)
        return {"status": "restarted", "cid": cid}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise e

@app.delete("/delete/{cid}", dependencies=[Depends(require_user)])
async def delete_instance(cid: str, user=Depends(require_user)):
    try:
        check_instance_ownership(cid, user)
        remove_container(cid)
        return {"status": "deleted", "cid": cid}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise e


@app.get("/instance/me", dependencies=[Depends(require_user)])
async def list_user_instances(user=Depends(require_user)):
    """FIX 4: Protected endpoint."""
    return list_instances_for_user(user["user_id"])


@app.get("/instance/{cid}", dependencies=[Depends(require_user)])
async def instance_details(cid: str, user=Depends(require_user)):
    """FIX 4: Protected endpoint."""
    return check_instance_ownership(cid, user)


# ---------------------------------------------------------
# 🟩 ADMIN/SYSTEM ENDPOINTS (FIX 2: ADMIN ONLY)
# ---------------------------------------------------------

@app.get("/admin/submissions/approved", dependencies=[Depends(require_admin)])
def admin_list_all_approved_submissions():
    """FIX 2: Admin views all approved submissions across all users."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, user_id, branch, status, image_tag, created_at, source FROM submissions 
            WHERE status='approved' AND image_tag IS NOT NULL
            ORDER BY created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

@app.get("/admin/instances/all", dependencies=[Depends(require_admin)])
def admin_list_all_instances():
    """FIX 2: Admin views all spawned instances (running, stopped, expired)."""
    return list_all_instances()

@app.get("/admin/stats", dependencies=[Depends(require_admin)])
def admin_stats():
    """Admin-level stats for system health check."""
    return system_stats()


# ---------------------------------------------------------
# 🟩 ROOT (FIX 4: PROTECTED)
# ---------------------------------------------------------

@app.get("/", dependencies=[Depends(require_user)])
def root():
    return {"msg": "InstaDock backend patched & active!"}