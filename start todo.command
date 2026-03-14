#!/bin/bash

set -euo pipefail

APP_DIR="/Users/geoffstanley/projects/job search"
PYTHON_BIN="/opt/homebrew/bin/python3"
SERVER_SCRIPT="$APP_DIR/todo_web.py"
URL="http://127.0.0.1:8421"

if ! lsof -nP -iTCP:8421 -sTCP:LISTEN >/dev/null 2>&1; then
  (
    sleep 1
    open "$URL"
  ) &
  exec "$PYTHON_BIN" "$SERVER_SCRIPT"
fi

open "$URL"
