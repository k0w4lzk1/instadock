# instadock/docker/backend.Dockerfile

# Stage 1: Build environment
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.11-slim

WORKDIR /app

# Copy installed dependencies and source code
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY backend/ /app/backend/

# Use uvicorn to run the FastAPI application on all interfaces
# This ensures external traffic can reach it.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]