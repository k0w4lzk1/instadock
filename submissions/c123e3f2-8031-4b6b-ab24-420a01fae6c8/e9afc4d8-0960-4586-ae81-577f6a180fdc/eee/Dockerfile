# Dockerfile
# This file is a temporary measure to satisfy the CI/CD requirement for a Dockerfile.

FROM ubuntu:22.04

# Install tools used by the start.sh script
RUN apt-get update && apt-get install -y socat bash

# Set working directory to the container's standard application path
WORKDIR /app/submission

# The platform's CI/CD usually injects user files here.

# Execute the user's start script
CMD ["bash", "./start.sh"]
