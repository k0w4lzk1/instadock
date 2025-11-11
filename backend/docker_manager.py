import docker,random,os,datetime,sqlite3
from .db import DB_PATH
import psutil
import subprocess
from pathlib import Path

client = docker.from_env()
PROXY_HOST = os.getenv("PROXY_HOST", "localhost")


def spawn(image, ttl_seconds=600):
    port = random.randint(20000, 40000)
    container = client.containers.run(
        image,
        detach=True,
        ports={"80/tcp": port},
        cap_drop=["ALL"],
        mem_limit="512m",
        nano_cpus=1_000_000_000
    )
    cid = container.id[:12]
    expires = (datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl_seconds)).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO instances (cid, image, port, expires_at) VALUES (?,?,?,?)",
            (cid, image, port, expires),
        )
        conn.commit()

    return cid, f"http://{PROXY_HOST}:{port}", expires



def stop(cid: str):
    try:
        container = client.containers.get(cid)
        container.remove(force=True)
    except Exception:
        pass
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM instances WHERE cid=?", (cid,))
        conn.commit()

def list_containers():
    containers = []
    for c in client.containers.list():
        stats = c.stats(stream=False)
        containers.append({
            "id": c.short_id,
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else "<none>",
            "status": c.status,
            "cpu": round(stats["cpu_stats"]["cpu_usage"]["total_usage"]/1e7, 2),
            "mem": round(stats["memory_stats"]["usage"] / (1024*1024), 2)
        })
    return containers

def system_stats():
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "total_memory": round(psutil.virtual_memory().total / (1024*1024*1024), 1)
    }

GHCR_USER = os.getenv("GHCR_USERNAME", "k0w4lzk1")  # change to your GH username
GHCR_REGISTRY = f"ghcr.io/{GHCR_USER}"
WORKDIR = Path("/tmp/instadock_submissions")
WORKDIR.mkdir(parents=True, exist_ok=True)

def build_image(sub_id: str):
    """
    Build and push Docker image for an approved submission to GHCR.
    """
    submissions_root = WORKDIR / "submissions"

    # Find submission folder with Dockerfile
    submission_path = None
    for user_dir in submissions_root.rglob(sub_id):
        dockerfile = user_dir / "Dockerfile"
        if dockerfile.exists():
            submission_path = user_dir
            break

    if not submission_path:
        print(f"[⚠️ No Dockerfile found for {sub_id}, skipping build]")
        return None

    local_tag = f"instadock_{sub_id}"
    remote_tag = f"{GHCR_REGISTRY}/{local_tag}:latest"

    print(f"[🐳 Building Docker image for {sub_id}]")
    try:
        subprocess.run(["docker", "build", "-t", local_tag, str(submission_path)], check=True)
        subprocess.run(["docker", "tag", local_tag, remote_tag], check=True)

        # Push to GHCR
        print(f"[🚀 Pushing to {remote_tag}]")
        subprocess.run(["docker", "push", remote_tag], check=True)

        # Optional: remove local image to save space
        subprocess.run(["docker", "rmi", "-f", local_tag], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f"[✅ Built and pushed: {remote_tag}]")
        return remote_tag

    except subprocess.CalledProcessError as e:
        print(f"[❌ Docker build/push failed for {sub_id}]\n{e}")
        return None
