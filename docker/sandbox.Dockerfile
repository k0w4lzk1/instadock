# ===============================
# 🐍 InstaDock Universal Sandbox
# ===============================
FROM ubuntu:22.04

# --- Install base packages ---
RUN apt-get update && apt-get install -y \
    python3 python3-pip curl socat netcat git jq \
    && useradd -ms /bin/bash appuser \
    && rm -rf /var/lib/apt/lists/*

# --- Set working directory ---
WORKDIR /home/appuser

# --- Copy startup helper script ---
COPY docker/start.sh .
RUN chmod +x start.sh

# --- Copy all submission files into /app/submission ---
# (Works for both direct repo and nested submission folder layouts)
COPY . /app/submission

# --- Switch to non-root user ---
USER appuser
WORKDIR /app/submission

# --- Optional environment metadata (for logging / tracking) ---
ENV APP_ENV=sandbox \
    PYTHONUNBUFFERED=1

# --- Smart install: if instadocker.json exists, use it; else default ---
# The start.sh script will handle detecting entrypoint, installing deps, etc.
CMD ["bash", "/home/appuser/start.sh"]
