#!/bin/bash
echo "🚀 Starting sandbox container..."
cd /app/submission || exit 1

# Example: run Python if exists
if [ -f main.py ]; then
  echo "🐍 Running main.py..."
  python3 main.py
else
  echo "📁 Contents of submission:"
  ls -la
fi
