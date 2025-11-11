#!/bin/bash
echo "🚀 Starting sandbox container for: ${SUBMISSION_TAG:-unknown}"
echo "📁 Listing /app/submission:"
ls -R /app/submission

cd /app/submission || exit 1

# Run main.py if it exists, else just sleep
if [ -f main.py ]; then
    echo "🐍 Running main.py..."
    python3 main.py
else
    echo "😴 No main.py found. Sleeping for 30 seconds..."
    sleep 30
fi
