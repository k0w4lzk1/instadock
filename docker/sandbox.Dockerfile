# docker/sandbox.Dockerfile
FROM ubuntu:22.04

# --- System setup ---
RUN apt-get update && apt-get install -y \
    python3 python3-pip curl socat netcat git \
    && useradd -ms /bin/bash appuser \
    && rm -rf /var/lib/apt/lists/*

USER appuser
WORKDIR /home/appuser

# --- Copy trusted scripts ---
COPY docker/start.sh .
RUN chmod +x start.sh

# --- Copy submission code safely ---
# Backend ensures submissions/<user>/<sub_id> exists before merge
COPY submission /app/submission

# --- Add environment variables (for identification) ---
ARG SUBMISSION_TAG
ENV SUBMISSION_TAG=$SUBMISSION_TAG

# --- Launch sandbox ---
CMD ["./start.sh"]
