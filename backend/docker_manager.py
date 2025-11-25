import docker
import random
import os
import datetime
import subprocess 
import psutil
import uuid # Needed for stable container name/subdomain
import time # IMPORT for delay

# FR-4.0: Import DB update function
from .db import save_instance, delete_instance, get_instance, update_instance_status

# ---------------------- CONFIG ----------------------

# FIX: Force BASE_DOMAIN to 'localhost' for direct port access in host mode
BASE_DOMAIN = os.getenv("PROXY_HOST", os.getenv("BASE_DOMAIN", "localhost"))
GHCR_USER = os.getenv("GHCR_USERNAME", "k0w4lzk1")
# SECURITY FIX: Token MUST be loaded from environment and NOT hardcoded.
GHCR_PULL_TOKEN = os.getenv("GHCR_PULL_TOKEN","") 
GHCR_REGISTRY = f"ghcr.io/{GHCR_USER}"

# Ensure we can connect to the Docker daemon (you need Docker running on your host)
client = docker.from_env()

# ---------------------- HELPERS ----------------------

def docker_pull(image: str):
    """
    Pulls an image from GHCR using authenticated access if a token is available.
    """
    try:
        print(f"[docker_manager] Pulling image: {image}")
        
        if GHCR_PULL_TOKEN and GHCR_USER:
            print("[docker_manager] Attempting authenticated pull...")
            
            # Use secure subprocess.run with input to pass password
            login_process = subprocess.run(
                ['docker', 'login', 'ghcr.io', '--username', GHCR_USER, '--password-stdin'],
                input=GHCR_PULL_TOKEN.encode('utf-8'),
                check=True, 
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            print("[docker_manager] Docker login successful.")
        
        # Execute the pull command, capturing output for better error reporting
        pull_process = subprocess.run(
            ["docker", "pull", image], 
            check=True,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        print(f"[docker_manager] Docker pull successful. Output: {pull_process.stdout.decode().strip()}")
        
    except subprocess.CalledProcessError as e: 
        detailed_error = e.stderr.decode('utf-8') if e.stderr else 'Unknown Docker command failure.'
        if e.cmd[0] == 'docker' and e.cmd[1] == 'login':
            login_error = e.stderr.decode('utf-8') if e.stderr else 'Unknown login failure.'
            raise RuntimeError(f"GHCR authentication failed (check GHCR_PULL_TOKEN): {login_error}")

        raise RuntimeError(f"Unable to pull image {image} (manifest unknown/permissions issue): {detailed_error.strip()}")

    except Exception as e:
        raise RuntimeError(f"Error during Docker pull process: {e}")


def generate_subdomain(cid: str):
    """
    Generate subdomain like: <cid>.localhost
    """
    return f"{cid}.{BASE_DOMAIN}"


# ---------------------- SPAWN CONTAINER ----------------------

def spawn(image: str, user_id: str, submission_id: str = None, ttl_seconds: int = 600):
    """
    Spawns a Docker container using a direct host port map for local testing.
    """
    
    # FIX: Add a short delay to allow the CI/CD pipeline (GitHub Actions) 
    # to finish building and pushing the image to GHCR.
    print("[docker_manager] Waiting 15 seconds for CI/CD image push to complete...")
    time.sleep(15) 
    print("[docker_manager] Delay finished. Attempting image pull.")

    # 1. Pull image
    docker_pull(image)

    # 2. Allocate fallback port (Traefik ignored)
    # The application port is 8080, which we map to a random host port.
    host_port = random.randint(20000, 40000)

    # 3. Generate a stable container name/subdomain from the start.
    container_uuid = str(uuid.uuid4())
    container_name = f"instadock-{container_uuid}"
    
    # 4. Traefik labels (included for compliance, but ignored when running this way)
    short_uuid_id = container_uuid[:8] 
    labels = {
        "traefik.enable": "true",
        "traefik.http.routers.instadock.rule": f"Host(`{short_uuid_id}.{BASE_DOMAIN}`)", 
        "traefik.http.services.instadock.loadbalancer.server.port": "8080", # FIX: Traefik target port is 8080
    }

    # 5. Run container
    # CRITICAL FIX: Map container port 8080 (the actual listening port) to the random host port.
    container = client.containers.run(
        image,
        detach=True,
        ports={"8080/tcp": host_port}, # Mapped 8080 to host port
        labels=labels,
        name=container_name, 
        cap_drop=["ALL"],
        mem_limit="512m",
        nano_cpus=1_000_000_000,  # 1 CPU
        network="bridge", # Default network since instadock-proxy won't exist
    )

    # 6. Get real CID (short ID)
    cid = container.id[:12]
    
    # 7. Compute expiry time
    expires = (datetime.datetime.utcnow() +
               datetime.timedelta(seconds=ttl_seconds)).isoformat()

    # 8. Determine the correct subdomain string to save in the DB
    # We force the simple localhost:<port> structure to the DB
    subdomain_to_save = f"localhost:{host_port}" 
    url_to_display = f"http://{subdomain_to_save}" 

    # 9. Save instance in DB 
    save_instance(
        cid=cid,
        user_id=user_id,
        submission_id=submission_id,
        image=image,
        subdomain=subdomain_to_save, 
        port=host_port,
        expires_at=expires,
    )

    print(f"[docker_manager] Spawned → {cid}")
    print(f"[docker_manager] URL → {url_to_display}")
    print(f"[docker_manager] Expires → {expires}")

    return cid, url_to_display, expires


# ---------------------- STOP / CLEANUP / START / RESTART ----------------------

def remove(cid: str):
    """
    Stop and permanently remove a container and its DB entry.
    Used by the cleanup worker.
    """
    try:
        container = client.containers.get(cid)
        container.remove(force=True)
        print(f"[docker_manager] Permanently removed {cid}")
    except Exception:
        print(f"[docker_manager] Could not remove {cid} (maybe already gone)")

    delete_instance(cid)

def stop(cid: str):
    """
    Stop a container instance and update its DB status.
    """
    try:
        container = client.containers.get(cid)
        container.stop()
        print(f"[docker_manager] Stopped {cid}")
        update_instance_status(cid, 'stopped')
        return True
    except docker.errors.NotFound:
        # If the container is already removed from Docker, update DB and proceed.
        delete_instance(cid)
        raise RuntimeError(f"Container {cid} not found on host. Removed DB entry.")
    except Exception as e:
        print(f"[docker_manager] Error stopping {cid}: {e}")
        raise RuntimeError(f"Error stopping container: {e}")

def start(cid: str):
    """
    Start a container instance that was previously stopped.
    """
    try:
        container = client.containers.get(cid)
        container.start()
        print(f"[docker_manager] Started {cid}")
        update_instance_status(cid, 'running')
        return True
    except docker.errors.NotFound:
        # If the container is gone, delete the DB record.
        delete_instance(cid)
        raise RuntimeError(f"Container {cid} not found on host. Removed DB entry.")
    except Exception as e:
        print(f"[docker_manager] Error starting {cid}: {e}")
        raise RuntimeError(f"Error starting container: {e}")

def restart(cid: str):
    """
    Restart a container instance.
    """
    try:
        container = client.containers.get(cid)
        container.restart()
        print(f"[docker_manager] Restarted {cid}")
        update_instance_status(cid, 'running')
        return True
    except docker.errors.NotFound:
        delete_instance(cid)
        raise RuntimeError(f"Container {cid} not found on host. Removed DB entry.")
    except Exception as e:
        print(f"[docker_manager] Error restarting {cid}: {e}")
        raise RuntimeError(f"Error restarting container: {e}")


# ---------------------- LIST / STATS ----------------------

def list_containers():
    """
    List all running and stopped containers with stats.
    """
    out = []
    # Use client.containers.list(all=True) to also get stopped containers for accurate status check
    for c in client.containers.list(all=True):
        try:
            stats = c.stats(stream=False)
            out.append({
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else "<none>",
                "status": c.status, # Docker status will show 'running', 'exited', 'created' etc.
                "cpu": round(stats["cpu_stats"]["cpu_usage"]["total_usage"] / 1e7, 2),
                "mem": round(stats["memory_stats"]["usage"] / (1024 * 1024), 2)
            })
        except Exception:
            continue

    return out


def system_stats():
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "total_memory_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
    }