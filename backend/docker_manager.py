import docker
import random
import os
import datetime
import sqlite3
import subprocess
import psutil
from pathlib import Path

from .db import (
    DB_PATH,
    save_instance,
    delete_instance,
    get_submission,
    set_submission_image,
)

client = docker.from_env()

# Localhost routing for now — later becomes *.instadock.app
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "localhost")

# For GitHub registry pulling
GHCR_USER = os.getenv("GHCR_USERNAME", "k0w4lzk1")
GHCR_PAT = os.getenv("GHCR_TOKEN", None)  # optional - if pulling private images
GHCR_REGISTRY = f"ghcr.io/{GHCR_USER}"


# ---------------------------------------------------------------------------------------
# 🔹 HELPERS
# ---------------------------------------------------------------------------------------

def docker_pull(image: str):
    """Pull image from GHCR (or any registry)."""
    try:
        print(f"[🐳] Pulling image → {image}")

        # If registry is private and PAT available
        if GHCR_PAT:
            client.login(username=GHCR_USER, password=GHCR_PAT, registry="ghcr.io")

        subprocess.run(["docker", "pull", image], check=True)
        print(f"[✔] Image pulled successfully → {image}")

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to pull Docker image: {image}\nError: {e}")


def generate_subdomain(cid: str):
    """Return subdomain such as: cid123.localhost"""
    return f"{cid}.{BASE_DOMAIN}"


# ---------------------------------------------------------------------------------------
# 🔹 SPAWN CONTAINER
# ---------------------------------------------------------------------------------------

def spawn(image: str, user_id: str, submission_id: str = None, ttl_seconds: int = 600):
    """
    Spawn a container, Traefik-compatible, localhost subdomain-based.
    """
    print(f"[⚙] Spawning container for image → {image}")

    # Pull image from GHCR
    docker_pull(image)

    # Use random host port as fallback (Traefik may not need it)
    host_port = random.randint(20000, 40000)

    # Subdomain for routing
    cid_placeholder = "temp"
    subdomain = generate_subdomain(cid_placeholder)

    # Docker labels for Traefik auto-routing (if user adds Traefik later)
    labels = {
        "traefik.enable": "true",
        "traefik.http.routers.instaDock.rule": f"Host(`{subdomain}`)",
        "traefik.http.services.instaDock.loadbalancer.server.port": "80",
    }

    # Run container (no dangerous caps)
    container = client.containers.run(
        image,
        detach=True,
        ports={"80/tcp": host_port},
        labels=labels,
        cap_drop=["ALL"],
        mem_limit="512m",
        nano_cpus=1_000_000_000,  # 1 CPU
        network="bridge"
    )

    cid = container.id[:12]
    subdomain = generate_subdomain(cid)
    expires = (datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl_seconds)).isoformat()

    # Update labels after CID is known
    container.reload()
    container.attrs["Config"]["Labels"].update({
        "traefik.http.routers.instaDock.rule": f"Host(`{subdomain}`)"
    })
    container.commit()

    print(f"[🚀] Container spawned → {cid}")
    print(f"[🌐] URL → http://{subdomain}")
    print(f"[⏳] Expires at → {expires}")

    # Save instance to DB
    save_instance(
        cid=cid,
        user_id=user_id,
        submission_id=submission_id,
        image=image,
        subdomain=subdomain,
        port=host_port,
        expires_at=expires,
    )

    return cid, f"http://{subdomain}", expires


# ---------------------------------------------------------------------------------------
# 🔹 STOP/REMOVE CONTAINER
# ---------------------------------------------------------------------------------------

def stop(cid: str):
    """Stop & remove a container, then delete DB row."""
    try:
        container = client.containers.get(cid)
        container.remove(force=True)
        print(f"[🛑] Removed container {cid}")
    except Exception:
        print(f"[⚠] Could not remove container {cid} (might already be gone)")
    delete_instance(cid)


# ---------------------------------------------------------------------------------------
# 🔹 LIST & STATS
# ---------------------------------------------------------------------------------------

def list_containers():
    """Return all running containers with CPU/MEM stats."""
    containers = []
    for c in client.containers.list():
        try:
            stats = c.stats(stream=False)
            containers.append({
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else "<none>",
                "status": c.status,
                "cpu": round(stats["cpu_stats"]["cpu_usage"]["total_usage"] / 1e7, 2),
                "mem": round(stats["memory_stats"]["usage"] / (1024 * 1024), 2)
            })
        except Exception:
            continue
    return containers


def system_stats():
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "total_memory": round(psutil.virtual_memory().total / (1024 * 1024 * 1024), 1)
    }
