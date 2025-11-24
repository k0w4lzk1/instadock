# Dockerfile
# This file is provided to satisfy the external CI/CD build process's requirement
# to find a Dockerfile in the submission's root.

FROM python:3.11-slim

# Install necessary runtime dependencies (Git is essential for other platform features)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app/submission

# CMD will be overridden by platform's start.sh
CMD ["echo", "Starting application..."]
