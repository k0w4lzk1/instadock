import uuid
import shutil
import subprocess
import os
import zipfile
from pathlib import Path
from .db import record_submission
import json
import docker
from datetime import datetime

# --- CONFIG ---
WORKDIR = Path("/tmp/instadock_submissions")
REPO_URL = os.getenv("MAIN_REPO_URL", "https://github.com/k0w4lzk1/instaDock.git")
WORKDIR.mkdir(parents=True, exist_ok=True)

# --- HELPERS ---
def _git(*args, cwd=None):
    """Run a git command safely, with error logging."""
    print(f"[GIT] {' '.join(args)}")
    subprocess.run(["git", *args], cwd=cwd, check=True)


def _safe_copy(src: Path, dest: Path):
    """Recursively copy files, skipping git folders."""
    for item in src.iterdir():
        if item.name == ".git":
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)

def ensure_manifest(submission_path: Path):
    manifest_path = submission_path / "instadock.json"
    if not manifest_path.exists():
        default_manifest = {
            "dockerfile": "Dockerfile",
            "context": ".",
            "entrypoint": "python3 app/main.py",
            "ports": [8080]
        }
        with open(manifest_path, "w") as f:
            json.dump(default_manifest, f, indent=2)



def build_submission_image(sub_id: str, user_id: str, branch: str):
    """
    Build the submission's Docker image using its instadock.json manifest.
    """
    client = docker.from_env()
    tmp_path = WORKDIR / sub_id
    tmp_path.mkdir(parents=True, exist_ok=True)

    subprocess.run([
        "git", "clone", "--branch", branch, "--depth", "1", REPO_URL, str(tmp_path)
    ], check=True)

    submission_path = tmp_path / "submissions" / user_id / sub_id

    manifest_path = submission_path / "instadock.json"
    dockerfile = submission_path / "Dockerfile"
    context = submission_path
    ports = [8080]
    entrypoint = None

    # Load manifest if available
    if manifest_path.exists():
        with open(manifest_path) as f:
            meta = json.load(f)
            dockerfile = submission_path / meta.get("dockerfile", "Dockerfile")
            context = submission_path / meta.get("context", ".")
            ports = meta.get("ports", [8080])
            entrypoint = meta.get("entrypoint")

    if not dockerfile.exists():
        raise RuntimeError("Dockerfile not found in submission folder")

    image_tag = f"instadock/{user_id[:8]}-{sub_id[:8]}:latest"
    print(f"[BUILD] Building {image_tag} from {context}")

    image, logs = client.images.build(
        path=str(context),
        dockerfile=str(dockerfile),
        tag=image_tag
    )
    for log in logs:
        print(log.get("stream", ""), end="")

    print(f"[BUILD] Image {image_tag} built successfully")

    from .db import update_submission_status
    update_submission_status(sub_id, "built")

    return image_tag, ports, entrypoint

    
# --- SUBMISSION FROM REPO ---
def create_branch_from_repo(user_id: str, repo_url: str, ref: str = None):
    """
    Clone the user repository, copy its content safely under
    submissions/<user_id>/<submission_id>/ and push to a new isolated branch.
    """
    sub_id = str(uuid.uuid4())
    branch = f"submission/{user_id[:8]}/{sub_id[:8]}"
    repo_dir = WORKDIR / sub_id
    canon_dir = WORKDIR / f"canon_{sub_id}"

    try:
        # Clone user repo
        _git("clone", "--depth", "1", repo_url, str(repo_dir))
        if ref:
            _git("checkout", ref, cwd=repo_dir)

        # Clone your main repo fresh
        _git("clone", "--depth", "1", REPO_URL, str(canon_dir))
        _git("checkout", "-b", branch, cwd=canon_dir)

        # ✅ Place submission in safe directory
        submissions_path = canon_dir / "submissions" / user_id / sub_id
        submissions_path.mkdir(parents=True, exist_ok=True)
        ensure_manifest(submissions_path)
        _safe_copy(repo_dir, submissions_path)

        # Commit and push
        _git("add", str(submissions_path), cwd=canon_dir)
        _git("commit", "-m", f"Add submission from repo {repo_url}", cwd=canon_dir)
        _git("push", "origin", branch, cwd=canon_dir)

        record_submission(sub_id, user_id, branch, "pending", repo_url)
        return sub_id, branch

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git operation failed: {e}")
    finally:
        shutil.rmtree(repo_dir, ignore_errors=True)
        shutil.rmtree(canon_dir, ignore_errors=True)


# --- SUBMISSION FROM ZIP ---
def create_branch_from_zip(user_id: str, file):
    """
    Extract uploaded ZIP and copy safely into submissions/<user_id>/<submission_id>/.
    """
    sub_id = str(uuid.uuid4())
    branch = f"submission/{user_id[:8]}/{sub_id[:8]}"
    zip_dir = WORKDIR / sub_id
    canon_dir = WORKDIR / f"canon_{sub_id}"

    try:
        zip_dir.mkdir(parents=True, exist_ok=True)

        # ✅ Extract zip safely
        with zipfile.ZipFile(file.file, "r") as zip_ref:
            zip_ref.extractall(zip_dir)

        # Optional: security check to avoid malicious uploads
        for item in zip_dir.rglob("*"):
            rel_path = item.relative_to(zip_dir)
            if rel_path.parts and rel_path.parts[0] in (".github", "backend", "venv", ".env"):
                raise ValueError(f"Forbidden file/folder in ZIP: {rel_path}")

        # Clone main repo
        _git("clone", "--depth", "1", REPO_URL, str(canon_dir))
        _git("checkout", "-b", branch, cwd=canon_dir)

        # Copy submission into isolated folder
        submissions_path = canon_dir / "submissions" / user_id / sub_id
        submissions_path.mkdir(parents=True, exist_ok=True)
        ensure_manifest(submissions_path)
        _safe_copy(zip_dir, submissions_path)

        # Commit and push
        _git("add", str(submissions_path), cwd=canon_dir)
        _git("commit", "-m", f"Add submission ZIP from {user_id}", cwd=canon_dir)
        _git("push", "origin", branch, cwd=canon_dir)

        record_submission(sub_id, user_id, branch, "pending", "uploaded_zip")
        return sub_id, branch

    except zipfile.BadZipFile:
        raise RuntimeError("Invalid ZIP file provided")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git operation failed: {e}")
    finally:
        shutil.rmtree(zip_dir, ignore_errors=True)
        shutil.rmtree(canon_dir, ignore_errors=True)


# --- ADMIN ACTIONS ---
from .docker_manager import build_image

def approve_submission(sub_id: str):
    """Mark submission as approved and trigger build via GitHub."""
    from .db import get_submission, update_submission_status

    sub = get_submission(sub_id)
    if not sub:
        raise RuntimeError("Submission not found")

    branch = sub["branch"]
    tmp_repo = WORKDIR / f"approve_{sub_id}"

    try:
        _git("clone", REPO_URL, str(tmp_repo))
        _git("fetch", "origin", branch, cwd=tmp_repo)

        # Checkout the branch safely
        result = subprocess.run(
            ["git", "checkout", branch],
            cwd=tmp_repo,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Branch {branch} not found: {result.stderr}")

        # Add approval marker
        marker_file = tmp_repo / "APPROVED"
        marker_file.write_text("approved=true\n")

        _git("add", "APPROVED", cwd=tmp_repo)
        _git("commit", "-m", f"Approve submission {sub_id}", cwd=tmp_repo)
        _git("push", "origin", branch, cwd=tmp_repo)

        update_submission_status(sub_id, "approved")
        print(f"[✅] Submission {sub_id} approved and branch {branch} updated")

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git operation failed: {e.stderr or e}")
    finally:
        shutil.rmtree(tmp_repo, ignore_errors=True)
        

def reject_submission(sub_id: str):
    """Reject submission and remove its branch from remote if it exists."""
    from .db import get_submission, update_submission_status

    sub = get_submission(sub_id)
    if not sub:
        raise RuntimeError("Submission not found")

    branch = sub["branch"]
    tmp_repo = WORKDIR / f"reject_{sub_id}"

    try:
        _git("clone", REPO_URL, str(tmp_repo))
        _git("fetch", "origin", "--all", cwd=tmp_repo)

        # Check if branch exists on remote before deleting
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch],
            cwd=tmp_repo,
            capture_output=True,
            text=True
        )

        if result.returncode != 0 or not result.stdout.strip():
            print(f"[⚠️] Branch {branch} does not exist on remote, skipping deletion.")
        else:
            _git("push", "origin", "--delete", branch, cwd=tmp_repo)
            print(f"[❌] Deleted remote branch {branch}")

        update_submission_status(sub_id, "rejected")

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git operation failed: {e.stderr or e}")
    finally:
        shutil.rmtree(tmp_repo, ignore_errors=True)
