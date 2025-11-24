from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import docker.errors

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
    delete_submission # NEW IMPORT for permanent deletion
)

# Container lifecycle
from backend.docker_manager import (
    spawn,
    stop as stop_container,
    start as start_container, 
    restart as restart_container,
    remove as remove_container, # NEW IMPORT for permanent deletion
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


# FIX 2: New endpoint for permanent deletion of submissions
@app.delete("/admin/submission/{sub_id}", dependencies=[Depends(require_admin)])
async def admin_delete_submission(sub_id: str):
    """
    Admin permanently deletes a submission record and associated git branch.
    Warning: Does not check for running instances.
    """
    try:
        delete_submission(sub_id)
        return {"status": "permanently deleted", "sub_id": sub_id}
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/submissions", dependencies=[Depends(require_admin)])
def get_pending():
    return list_pending_submissions()


# ---------------------------------------------------------
# 🟩 INSTANCE SPAWNING
# ---------------------------------------------------------

MAX_INSTANCES_PER_USER = 5 # NFR-1.2: Quota enforcement

@app.post("/spawn", response_model=SpawnResp)
async def spawn_container(req: SpawnReq, user=Depends(require_user)):
    """
    Spawn an instance either from:
    - a submission_id (GHCR-built image)
    - OR a raw image string
    """
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
# 🟩 INSTANCE MANAGEMENT (FR-4.0)
# ---------------------------------------------------------

def check_instance_ownership(cid: str, user_data: dict):
    """Helper to check existence and ownership/admin role."""
    instance = get_instance(cid)
    if not instance:
        raise HTTPException(404, "Instance not found")
    
    # FR-4.0: Allow only owner or admin to control the instance
    if instance["user_id"] != user_data["user_id"] and user_data["role"] != "admin":
        raise HTTPException(403, "You cannot control another user's instance")
    
    return instance


@app.post("/stop/{cid}")
async def stop_instance(cid: str, user=Depends(require_user)):
    """Stop a container instance."""
    try:
        check_instance_ownership(cid, user)
        stop_container(cid)
        return {"status": "stopped", "cid": cid}
    except RuntimeError as e:
        # Docker manager raises RuntimeError if container is permanently removed/missing
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise e


@app.post("/start/{cid}")
async def start_instance(cid: str, user=Depends(require_user)):
    """Start a previously stopped container instance."""
    try:
        instance = check_instance_ownership(cid, user)
        # FR-4.0: Only start if the last known status was 'stopped'
        if instance["status"] == 'running':
             return {"status": "already running", "cid": cid}
             
        start_container(cid)
        return {"status": "started", "cid": cid}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise e


@app.post("/restart/{cid}")
async def restart_instance(cid: str, user=Depends(require_user)):
    """Restart a running or stopped container instance."""
    try:
        check_instance_ownership(cid, user)
        restart_container(cid)
        return {"status": "restarted", "cid": cid}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise e

# FR-4.0: New endpoint for permanently deleting an instance
@app.delete("/delete/{cid}")
async def delete_instance(cid: str, user=Depends(require_user)):
    """
    Permanently stop, remove the container, and delete the DB record.
    """
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
    """List all instances owned by the current user."""
    return list_instances_for_user(user["user_id"])


@app.get("/instance/{cid}", dependencies=[Depends(require_user)])
async def instance_details(cid: str, user=Depends(require_user)):
    """Get a single instance's info."""
    return check_instance_ownership(cid, user)


@app.get("/user/approved_submissions")
async def get_user_approved_submissions(user=Depends(require_user)):
    """This endpoint is now defined in users.py to correctly mount under /user."""
    raise HTTPException(500, "This endpoint should be accessed via the /user router.")


# ---------------------------------------------------------
# 🟩 LIVE LOGS (FR-5.0)
# ---------------------------------------------------------

@app.websocket("/ws/logs/{cid}")
async def websocket_endpoint(websocket: WebSocket, cid: str, user_id: dict = Depends(require_user)):
    """
    FR-5.0: Stream live logs from a running container instance.
    """
    
    # Check ownership and existence before accepting the connection
    instance = get_instance(cid)
    if not instance:
        await websocket.close(code=1000, reason="Instance not found.")
        return

    # Check ownership (require_user returns dict {'user_id', 'role'})
    if instance["user_id"] != user_id["user_id"] and user_id["role"] != "admin":
        await websocket.close(code=1000, reason="Forbidden.")
        return
        
    await websocket.accept()
    
    print(f"[WebSocket] Logs requested for {cid} by {user_id['user_id']}")
    
    try:
        container = docker_client.containers.get(cid)
    except docker.errors.NotFound:
        await websocket.send_text("--- ERROR: Container not found on host. ---")
        await websocket.close(code=1000)
        return
    except Exception as e:
        await websocket.send_text(f"--- ERROR accessing container: {e} ---")
        await websocket.close(code=1011)
        return


    try:
        # Stream logs from the container
        await websocket.send_text(f"--- Streaming logs for {cid}... (Connecting to Docker Log Stream) ---")
        for line in container.logs(stream=True, follow=True, timestamps=True):
            await websocket.send_text(line.decode().strip())
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected from {cid} logs.")
    except Exception as e:
        print(f"[WebSocket] Error streaming logs for {cid}: {e}")
        try:
            await websocket.send_text(f"--- STREAMING ERROR: {e} ---")
            await websocket.close(code=1011)
        except:
            pass 


# ---------------------------------------------------------
# 🟩 SYSTEM ADMIN
# ---------------------------------------------------------

@app.get("/admin/containers", dependencies=[Depends(require_admin)])
def admin_list_containers():
    """
    List all known instances (from DB) and enrich with live Docker status. (FR-6.0)
    """
    db_instances = list_all_instances()
    live_containers = list_containers()
    live_map = {c["id"]: c for c in live_containers}

    for instance in db_instances:
        cid = instance["cid"]
        live_info = live_map.get(cid)
        
        # Use Docker's detailed status for better accuracy
        if live_info:
            instance["live_status"] = live_info["status"]
            instance["cpu"] = live_info["cpu"]
            instance["mem"] = live_info["mem"]
        else:
            # Container missing from Docker might mean it was manually removed or failed to start
            instance["live_status"] = "removed" 
            instance["cpu"] = 0
            instance["mem"] = 0
            # Also update the DB status if it was previously running
            if instance.get("status") == 'running':
                update_instance_status(cid, 'removed')
                instance["status"] = 'removed'

    return db_instances


@app.get("/system/stats", dependencies=[Depends(require_user)])
def stats():
    system_data = system_stats()
    return {
        "cpu_percent": system_data["cpu_percent"],
        "memory_percent": system_data["memory_percent"],
        "total_memory_gb": system_data["total_memory_gb"],
    }


# ---------------------------------------------------------
# 🟩 ROOT
# ---------------------------------------------------------

@app.get("/")
def root():
    return {"msg": "InstaDock backend patched & active!"}