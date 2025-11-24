#!/bin/bash
set -e

echo "🚀 InstaDock Sandbox Starting..."
cd /app/submission

# --- Detect configuration and set defaults ---
PORT=8080 # Default port if instadock.json is missing or doesn't specify a port.
ENTRYPOINT_CMD=""
REQS="requirements.txt"

if [ -f "instadock.json" ]; then
    echo "📄 Using instadock.json configuration..."
    
    # Read the first port from the "ports" array, defaulting to 8080
    CONFIG_PORT=$(jq -r '.ports[0]' instadock.json)
    if [ "$CONFIG_PORT" != "null" ]; then
        PORT="$CONFIG_PORT"
    fi
    
    # Read the custom entrypoint command
    CONFIG_ENTRYPOINT=$(jq -r '.entrypoint' instadock.json)
    if [ "$CONFIG_ENTRYPOINT" != "null" ]; then
        ENTRYPOINT_CMD="$CONFIG_ENTRYPOINT"
    fi
    
    # Read requirements file name
    REQS_NAME=$(jq -r '.requirements // "requirements.txt"' instadock.json)
    if [ "$REQS_NAME" != "null" ]; then
        REQS="$REQS_NAME"
    fi
else
    echo "⚙️ No instadock.json found, using defaults: PORT 8080, standard uvicorn entrypoint."
fi

# --- Install dependencies ---
if [ -f "$REQS" ]; then
    echo "📦 Installing dependencies from $REQS..."
    pip install --no-cache-dir -r "$REQS"
    # Ensure uvicorn is available for standard Python web apps
    pip install uvicorn gunicorn > /dev/null 2>&1 
else
    echo "⚠️ No $REQS found, skipping dependency install."
    pip install uvicorn gunicorn > /dev/null 2>&1 
fi


# --- Run the application ---
echo "🏁 Running application on http://0.0.0.0:$PORT"

if [ -n "$ENTRYPOINT_CMD" ]; then
    # Option 1: Execute the explicit entrypoint command provided by the user (e.g., "uvicorn src.main:app --host 0.0.0.0 --port 8080")
    echo "   -> Executing custom command: $ENTRYPOINT_CMD"
    # The 'exec' command replaces the shell process with the application process
    exec $ENTRYPOINT_CMD 
elif [ -f "src/main.py" ]; then
    # Option 2: Default to standard uvicorn execution if no command is specified but src/main.py exists
    echo "   -> Executing standard Uvicorn entrypoint: src.main:app"
    exec uvicorn --host 0.0.0.0 --port "$PORT" src.main:app
else
    echo "❌ ERROR: No instadock.json entrypoint defined and no default src/main.py found."
    exit 1
fi