#!/bin/bash
set -euo pipefail

PROJECT_ROOT="/Users/Bryce/Desktop/hurricane_project_clean"
VENV_PY="/path/to/venv/bin/python"   # <-- Change this to your venv python path

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"

cd "$PROJECT_ROOT"

mkdir -p "$PROJECT_ROOT/logs"

"$VENV_PY" "$PROJECT_ROOT/manage.py" fetch_storms \
  --timeout=600 \
  >> "$PROJECT_ROOT/logs/fetch_storms.log" 2>&1

