# docker/sandbox.Dockerfile
FROM ubuntu:22.04

# --- Install dependencies ---
RUN apt-get update && apt-get install -y \
    python3 python3-pip curl socat netcat git \
    && useradd -ms /bin/bash appuser \
    && rm -rf /var/lib/apt/lists/*

USER appuser
WORKDIR /home/appuser

# --- Copy your trusted start script ---
COPY start.sh .
RUN chmod +x start.sh

# --- Copy only user submission safely ---
# The backend will put submissions inside submissions/<user>/<id>
# so we copy them all into /app/submissions in the container
COPY ../submission /app/submission

# Optional: copy backend/frontend if you want to test interactions
# COPY ../backend /app/backend

# --- Entrypoint ---
CMD ["./start.sh"]
