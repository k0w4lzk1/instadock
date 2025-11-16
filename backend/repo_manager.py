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
    set_submission_image,
)

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

WORKDIR = Path("/tmp/instadock_submissions")
WORKDIR.mkdir(parents=True, exist_ok=True)

# Main Git repo containing /submissions folder & workflows
MAIN_REPO_URL = os.getenv("MAIN_REPO_URL", "https://github.com/k0w4lzk1/instaDock.git")

# GitHub username for GHCR images: ghcr.io/USER/
GHCR_USER = os.getenv("GHCR_USERNAME", "k0w4lzk1")
GHCR_REGISTRY = f"ghcr.io/{GHCR_USER}"


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def _git(*args, cwd=None):
    """Run git command with clear debugging."""
    print(f"[GIT] {' '.join(args)}")
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git failed: {result.stderr}")
    return result.stdout.strip()


def validate_zip_safe(path: Path):
    """Basic zip safety: block symlinks, traversals."""
    for item in path.rglob("*"):
        if item.is_symlink():
            raise RuntimeError("ZIP contains unsafe symlink")

        # Prevent ../../ escape attacks
        if ".." in item.parts:
            raise RuntimeError("ZIP contains unsafe path traversal")


def ensure_manifest(submission_path: Path):
    """Ensure instadock.json exists."""
    manifest_path = submission_path / "instadock.json"
    if not manifest_path.exists():
        meta = {
            "dockerfile": "Dockerfile",
            "context": ".",
            "entrypoint": None,
            "ports": [8080]
        }
        with open(manifest_path, "w") as f:
            json.dump(meta, f, indent=2)


# -------------------------------------------------------------------
# CREATE SUBMISSION FROM REPO
# -------------------------------------------------------------------

def create_branch_from_repo(user_id: str, repo_url: str, ref: str = None):
    """
    Clone user repo → copy into own repo's /submissions/<user>/<sub_id>.
    """
    sub_id = str(uuid.uuid4())
    branch = f"submission/{user_id[:8]}/{sub_id[:8]}"

    user_clone = WORKDIR / f"user_{sub_id}"
    canon_clone = WORKDIR / f"canon_{sub_id}"

    try:
        # Clone user repo
        _git("clone", "--depth", "1", repo_url, str(user_clone))
        if ref:
            _git("checkout", ref, cwd=user_clone)

        # Clone main repo
        _git("clone", "--depth", "1", MAIN_REPO_URL, str(canon_clone))
        _git("checkout", "-b", branch, cwd=canon_clone)

        # Prepare folder
        submissions_path = canon_clone / "submissions" / user_id / sub_id
        submissions_path.mkdir(parents=True, exist_ok=True)
        ensure_manifest(submissions_path)

        # Copy user repo contents
        for item in user_clone.iterdir():
            if item.name == ".git":
                continue
            target = submissions_path / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

        # Commit and push
        _git("add", ".", cwd=canon_clone)
        _git("commit", "-m", f"Add submission repo → {repo_url}", cwd=canon_clone)
        _git("push", "origin", branch, cwd=canon_clone)

        record_submission(sub_id, user_id, branch, "pending", repo_url)
        return sub_id, branch

    finally:
        shutil.rmtree(user_clone, ignore_errors=True)
        shutil.rmtree(canon_clone, ignore_errors=True)


# -------------------------------------------------------------------
# CREATE SUBMISSION FROM ZIP
# -------------------------------------------------------------------

def create_branch_from_zip(user_id: str, file):
    """
    Extract uploaded ZIP safely.
    Copy into our repo under /submissions/<user>/<sub_id>.
    """
    sub_id = str(uuid.uuid4())
    branch = f"submission/{user_id[:8]}/{sub_id[:8]}"

    zip_dir = WORKDIR / f"zip_{sub_id}"
    canon_clone = WORKDIR / f"canon_{sub_id}"

    try:
        zip_dir.mkdir(parents=True, exist_ok=True)

        # Extract ZIP
        with zipfile.ZipFile(file.file, 'r') as z:
            z.extractall(zip_dir)

        validate_zip_safe(zip_dir)

        # Clone main repo
        _git("clone", "--depth", "1", MAIN_REPO_URL, str(canon_clone))
        _git("checkout", "-b", branch, cwd=canon_clone)

        submissions_path = canon_clone / "submissions" / user_id / sub_id
        submissions_path.mkdir(parents=True, exist_ok=True)
        ensure_manifest(submissions_path)

        # Copy files
        for item in zip_dir.iterdir():
            target = submissions_path / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

        # Commit & push
        _git("add", ".", cwd=canon_clone)
        _git("commit", "-m", f"Add submission ZIP from {user_id}", cwd=canon_clone)
        _git("push", "origin", branch, cwd=canon_clone)

        record_submission(sub_id, user_id, branch, "pending", "uploaded_zip")
        return sub_id, branch

    finally:
        shutil.rmtree(zip_dir, ignore_errors=True)
        shutil.rmtree(canon_clone, ignore_errors=True)


# -------------------------------------------------------------------
# APPROVE SUBMISSION → BRANCH MARK
# -------------------------------------------------------------------

def approve_submission(sub_id: str):
    """
    Mark submission approved by adding APPROVED file to its branch.
    GitHub Actions will detect this and build to GHCR.
    """
    sub = get_submission(sub_id)
    if not sub:
        raise RuntimeError("Submission not found")

    branch = sub["branch"]
    clone_path = WORKDIR / f"approve_{sub_id}"

    try:
        _git("clone", MAIN_REPO_URL, str(clone_path))
        _git("fetch", "origin", branch, cwd=clone_path)
        _git("checkout", branch, cwd=clone_path)

        (clone_path / "APPROVED").write_text("approved=true\n")

        _git("add", "APPROVED", cwd=clone_path)
        _git("commit", "-m", f"Approve submission {sub_id}", cwd=clone_path)
        _git("push", "origin", branch, cwd=clone_path)

        update_submission_status(sub_id, "approved")

    finally:
        shutil.rmtree(clone_path, ignore_errors=True)


# -------------------------------------------------------------------
# REJECT SUBMISSION
# -------------------------------------------------------------------

def reject_submission(sub_id: str):
    sub = get_submission(sub_id)
    if not sub:
        raise RuntimeError("Submission not found")

    branch = sub["branch"]
    clone_path = WORKDIR / f"reject_{sub_id}"

    try:
        _git("clone", MAIN_REPO_URL, str(clone_path))
        _git("fetch", "origin", "--all", cwd=clone_path)

        # Check if branch exists
        exists = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch],
            cwd=clone_path,
            capture_output=True,
            text=True
        )
        if exists.stdout.strip():
            _git("push", "origin", "--delete", branch, cwd=clone_path)

        update_submission_status(sub_id, "rejected")

    finally:
        shutil.rmtree(clone_path, ignore_errors=True)


# -------------------------------------------------------------------
# RECEIVE FINAL IMAGE FROM GITHUB ACTIONS
# -------------------------------------------------------------------

def set_built_image(sub_id: str, image_tag: str):
    """
    Called by webhook: store GHCR image like:
    ghcr.io/user/instadock_<sub_id>:latest
    """
    full_tag = f"{GHCR_REGISTRY}/{image_tag}:latest"
    set_submission_image(sub_id, full_tag)
    update_submission_status(sub_id, "built")
