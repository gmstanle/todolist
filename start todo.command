#!/bin/bash

set -euo pipefail

APP_DIR="/Users/geoffstanley/projects/job search"
PYTHON_BIN="/opt/homebrew/bin/python3"
SERVER_SCRIPT="$APP_DIR/todo_web.py"
URL="http://127.0.0.1:8421"
LOG_FILE="/tmp/job-search-todo.log"

if ! lsof -nP -iTCP:8421 -sTCP:LISTEN >/dev/null 2>&1; then
  nohup "$PYTHON_BIN" "$SERVER_SCRIPT" >"$LOG_FILE" 2>&1 &
  sleep 1
fi

open "$URL"
