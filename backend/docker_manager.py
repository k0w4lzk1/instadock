import docker
import random
import os
import datetime
import subprocess
import psutil

from .db import save_instance, delete_instance

# ---------------------- CONFIG ----------------------

BASE_DOMAIN = os.getenv("BASE_DOMAIN", "localhost")
GHCR_USER = os.getenv("GHCR_USERNAME", "k0w4lzk1")  # your GitHub username
GHCR_REGISTRY = f"ghcr.io/{GHCR_USER}"

client = docker.from_env()


# ---------------------- HELPERS ----------------------

def docker_pull(image: str):
    """
    Pull an image from GHCR.
    """
    try:
        print(f"[docker_manager] Pulling image: {image}")
        subprocess.run(["docker", "pull", image], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Unable to pull image {image}: {e}")


def generate_subdomain(cid: str):
    """
    Generate subdomain like: <cid>.localhost
    """
    return f"{cid}.{BASE_DOMAIN}"


# ---------------------- SPAWN CONTAINER ----------------------

def spawn(image: str, user_id: str, submission_id: str = None, ttl_seconds: int = 600):
    """
    Spawns a Docker container using deterministic GHCR image naming.
    """
    # 1. Pull image
    docker_pull(image)

    # 2. Allocate fallback port (Traefik not required, but supported)
    host_port = random.randint(20000, 40000)

    # 3. Temporary subdomain until container ID is known
    temp_subdomain = f"temp.{BASE_DOMAIN}"

    # 4. Traefik labels (optional)
    labels = {
        "traefik.enable": "true",
        "traefik.http.routers.instadock.rule": f"Host(`{temp_subdomain}`)",
        "traefik.http.services.instadock.loadbalancer.server.port": "80",
    }

    # 5. Run container
    container = client.containers.run(
        image,
        detach=True,
        ports={"80/tcp": host_port},
        labels=labels,
        cap_drop=["ALL"],
        mem_limit="512m",
        nano_cpus=1_000_000_000,  # 1 CPU
        network="bridge",
    )

    # 6. Get real CID
    cid = container.id[:12]
    subdomain = generate_subdomain(cid)

    # 7. Update labels for Traefik routing
    try:
        subprocess.run([
            "docker", "container", "update",
            "--label-add", f"traefik.http.routers.instadock.rule=Host(`{subdomain}`)",
            cid
        ], check=True)
    except Exception:
        pass  # If Traefik not used, safe to ignore

    # 8. Compute expiry time
    expires = (datetime.datetime.utcnow() +
               datetime.timedelta(seconds=ttl_seconds)).isoformat()

    # 9. Save instance in DB
    save_instance(
        cid=cid,
        user_id=user_id,
        submission_id=submission_id,
        image=image,
        subdomain=subdomain,
        port=host_port,
        expires_at=expires,
    )

    print(f"[docker_manager] Spawned → {cid}")
    print(f"[docker_manager] URL → http://{subdomain}")
    print(f"[docker_manager] Expires → {expires}")

    return cid, f"http://{subdomain}", expires


# ---------------------- STOP / CLEANUP ----------------------

def stop(cid: str):
    """
    Stop and remove a container.
    """
    try:
        container = client.containers.get(cid)
        container.remove(force=True)
        print(f"[docker_manager] Removed {cid}")
    except Exception:
        print(f"[docker_manager] Could not remove {cid} (maybe already gone)")

    delete_instance(cid)


# ---------------------- LIST / STATS ----------------------

def list_containers():
    """
    List all running containers with stats.
    """
    out = []
    for c in client.containers.list():
        try:
            stats = c.stats(stream=False)
            out.append({
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else "<none>",
                "status": c.status,
                "cpu": round(stats["cpu_stats"]["cpu_usage"]["total_usage"] / 1e7, 2),
                "mem": round(stats["memory_stats"]["usage"] / (1024 * 1024), 2)
            })
        except Exception:
            continue

    return out


def system_stats():
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "total_memory": round(psutil.virtual_memory().total / (1024 ** 3), 1),
    }
