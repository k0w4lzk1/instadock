import uuid
import shutil
import subprocess
import os
import zipfile
from pathlib import Path
import json

from .db import (
    record_submission,
    update_submission_status,
    get_submission,
)

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

WORKDIR = Path("/tmp/instadock_submissions")
WORKDIR.mkdir(parents=True, exist_ok=True)

# Main monorepo where /submissions/ gets updated
MAIN_REPO_URL = os.getenv("MAIN_REPO_URL", "https://github.com/k0w4lzk1/instaDock.git")


# -------------------------------------------------------------------
# SHELL HELPERS
# -------------------------------------------------------------------

def _git(*args, cwd=None):
    """
    Run a git command and throw errors cleanly.
    """
    print(f"[GIT] {' '.join(args)}")
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Git error: {result.stderr}")

    return result.stdout.strip()


# -------------------------------------------------------------------
# ZIP SAFETY
# -------------------------------------------------------------------

def validate_zip_safe(path: Path):
    """
    Prevent symlink escapes and unsafe paths.
    """
    for p in path.rglob("*"):
        if p.is_symlink():
            raise RuntimeError("ZIP contains unsafe symlink")
        if ".." in p.parts:
            raise RuntimeError("ZIP contains unsafe path traversal")


# -------------------------------------------------------------------
# MANIFEST
# -------------------------------------------------------------------

def ensure_manifest(path: Path):
    """
    Ensure instadock.json exists.
    """
    manifest_path = path / "instadock.json"
    if not manifest_path.exists():
        data = {
            "dockerfile": "Dockerfile",
            "context": ".",
            "ports": [8080]
        }
        with open(manifest_path, "w") as f:
            json.dump(data, f, indent=2)


# -------------------------------------------------------------------
# CREATE FROM REPO
# -------------------------------------------------------------------

def create_branch_from_repo(user_id: str, repo_url: str, ref: str = None):
    """
    Clone user repo, copy its contents into:
    submissions/<full_user_uuid>/<full_submission_uuid>/
    inside the main monorepo.
    """
    sub_id = str(uuid.uuid4())
    branch = f"submission/{user_id[:8]}/{sub_id[:8]}"

    # Temp paths
    user_clone = WORKDIR / f"user_{sub_id}"
    mono_clone = WORKDIR / f"mono_{sub_id}"

    try:
        # Clone user repo
        _git("clone", "--depth", "1", repo_url, str(user_clone))
        if ref:
            _git("checkout", ref, cwd=user_clone)

        # Clone monorepo
        _git("clone", "--depth", "1", MAIN_REPO_URL, str(mono_clone))
        _git("checkout", "-b", branch, cwd=mono_clone)

        # Build target path
        target = mono_clone / "submissions" / user_id / sub_id
        target.mkdir(parents=True, exist_ok=True)

        ensure_manifest(target)

        # Copy user repo contents
        for item in user_clone.iterdir():
            if item.name == ".git":
                continue
            dest = target / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        # Commit and push
        _git("add", ".", cwd=mono_clone)
        _git("commit", "-m", f"Add submission repo ({repo_url})", cwd=mono_clone)
        _git("push", "origin", branch, cwd=mono_clone)

        # Record in DB
        record_submission(sub_id, user_id, branch, "pending", repo_url)

        return sub_id, branch

    finally:
        shutil.rmtree(user_clone, ignore_errors=True)
        shutil.rmtree(mono_clone, ignore_errors=True)


# -------------------------------------------------------------------
# CREATE FROM ZIP
# -------------------------------------------------------------------

def create_branch_from_zip(user_id: str, file):
    """
    Extract uploaded ZIP and insert into:
    submissions/<user_id>/<submission_id>
    inside monorepo.
    """
    sub_id = str(uuid.uuid4())
    branch = f"submission/{user_id[:8]}/{sub_id[:8]}"

    zip_extract_dir = WORKDIR / f"zip_{sub_id}"
    mono_clone = WORKDIR / f"mono_{sub_id}"

    try:
        zip_extract_dir.mkdir(parents=True, exist_ok=True)

        # Extract ZIP
        with zipfile.ZipFile(file.file, "r") as z:
            z.extractall(zip_extract_dir)

        validate_zip_safe(zip_extract_dir)

        # Clone monorepo
        _git("clone", "--depth", "1", MAIN_REPO_URL, str(mono_clone))
        _git("checkout", "-b", branch, cwd=mono_clone)

        target = mono_clone / "submissions" / user_id / sub_id
        target.mkdir(parents=True, exist_ok=True)

        ensure_manifest(target)

        # Copy zip contents
        for item in zip_extract_dir.iterdir():
            dest = target / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        # Commit and push
        _git("add", ".", cwd=mono_clone)
        _git("commit", "-m", f"Add ZIP submission ({user_id})", cwd=mono_clone)
        _git("push", "origin", branch, cwd=mono_clone)

        record_submission(sub_id, user_id, branch, "pending", "zip_upload")

        return sub_id, branch

    finally:
        shutil.rmtree(zip_extract_dir, ignore_errors=True)
        shutil.rmtree(mono_clone, ignore_errors=True)


# -------------------------------------------------------------------
# APPROVE SUBMISSION
# -------------------------------------------------------------------

def approve_submission(sub_id: str):
    """
    Approve submission:
    - Adds APPROVED file to branch
    - GitHub Actions workflow does the build
    - Backend uses deterministic GHCR tag; no callback needed
    """
    sub = get_submission(sub_id)
    if not sub:
        raise RuntimeError("Submission not found")

    branch = sub["branch"]
    approve_clone = WORKDIR / f"approve_{sub_id}"

    try:
        _git("clone", MAIN_REPO_URL, str(approve_clone))
        _git("fetch", "origin", branch, cwd=approve_clone)
        _git("checkout", branch, cwd=approve_clone)

        # Add APPROVED marker
        (approve_clone / "APPROVED").write_text("approved=true\n")

        _git("add", "APPROVED", cwd=approve_clone)
        _git("commit", "-m", f"Approve submission {sub_id}", cwd=approve_clone)
        _git("push", "origin", branch, cwd=approve_clone)

        update_submission_status(sub_id, "approved")

    finally:
        shutil.rmtree(approve_clone, ignore_errors=True)


# -------------------------------------------------------------------
# REJECT SUBMISSION
# -------------------------------------------------------------------

def reject_submission(sub_id: str):
    sub = get_submission(sub_id)
    if not sub:
        raise RuntimeError("Submission not found")

    branch = sub["branch"]
    reject_clone = WORKDIR / f"reject_{sub_id}"

    try:
        _git("clone", MAIN_REPO_URL, str(reject_clone))
        _git("fetch", "origin", "--all", cwd=reject_clone)

        # Delete branch if it exists
        exists = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch],
            cwd=reject_clone,
            capture_output=True,
            text=True
        )

        if exists.stdout.strip():
            _git("push", "origin", "--delete", branch, cwd=reject_clone)

        update_submission_status(sub_id, "rejected")

    finally:
        shutil.rmtree(reject_clone, ignore_errors=True)

# FIX 2: New endpoint for permanent deletion of a submission
# -------------------------------------------------------------------
# PERMANENTLY DELETE SUBMISSION (New - Calls reject logic + removes DB entry)
# -------------------------------------------------------------------

def delete_submission(sub_id: str):
    """
    Permanently delete a submission. This includes deleting the git branch
    and removing the record from the database.
    """
    sub = get_submission(sub_id)
    if not sub:
        raise RuntimeError("Submission not found")

    # Rejecting the submission handles the deletion of the remote git branch.
    reject_submission(sub_id)

    # Delete the record from the database
    from .db import delete_submission as db_delete_submission
    db_delete_submission(sub_id)

    return True