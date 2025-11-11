import docker,random,os,datetime,sqlite3
from .db import DB_PATH
import psutil

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