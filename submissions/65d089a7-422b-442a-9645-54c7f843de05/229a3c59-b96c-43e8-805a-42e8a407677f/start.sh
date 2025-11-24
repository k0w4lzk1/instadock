#!/bin/bash
set -e

echo "Running Shell/Socat Listener on port 8080..."

# HTTP response payload: 200 OK header + JSON body
RESPONSE="HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\": \"success\", \"language\": \"Bash/Socat\", \"message\": \"Sandbox Liveness Confirmed\"}"

# Start socat:
# - TCP-LISTEN:8080: Listen on port 8080
# - fork: Handle multiple simultaneous requests
# - reuseaddr: Allow immediate restart
# - EXEC: Executes /bin/echo -e "$RESPONSE" for each connection
socat TCP-LISTEN:8080,fork,reuseaddr EXEC:"/bin/echo -e '$RESPONSE'"
