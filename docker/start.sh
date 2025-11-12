#!/bin/bash
set -e

echo "🚀 InstaDock Sandbox Starting..."
cd /app/submission

# --- Detect and install requirements ---
if [ -f "instadocker.json" ]; then
    echo "📄 Using instadocker.json configuration..."
    ENTRYPOINT=$(jq -r '.entrypoint // "src/main.py"' instadocker.json)
    REQS=$(jq -r '.requirements // "requirements.txt"' instadocker.json)
    PORT=$(jq -r '.port // 8000' instadocker.json)
else
    echo "⚙️ No instadocker.json found, using defaults."
    ENTRYPOINT="src/main.py"
    REQS="requirements.txt"
    PORT=8000
fi

# --- Install dependencies if requirements exist ---
if [ -f "$REQS" ]; then
    echo "📦 Installing dependencies from $REQS..."
    pip install --no-cache-dir -r "$REQS"
else
    echo "⚠️ No $REQS found, skipping dependency install."
fi

# --- Run the application ---
echo "🏁 Running application: python3 $ENTRYPOINT"
exec python3 "$ENTRYPOINT"
