#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python3"
LOG_FILE="$PROJECT_DIR/logs/cron.log"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "No venv found at $PROJECT_DIR/venv. Run:"
    echo "  python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

mkdir -p "$PROJECT_DIR/logs" "$PROJECT_DIR/auth"

MARKER="# youtube-shorts-automation"
CRON_MORNING="0 10 * * * cd $PROJECT_DIR && $PYTHON_BIN main.py >> $LOG_FILE 2>&1 $MARKER"
CRON_EVENING="0 18 * * * cd $PROJECT_DIR && $PYTHON_BIN main.py >> $LOG_FILE 2>&1 $MARKER"

( crontab -l 2>/dev/null | grep -vF "$MARKER" ; echo "$CRON_MORNING" ; echo "$CRON_EVENING" ) | crontab -

echo "Installed cron entries (10:00 and 18:00 local server time):"
crontab -l | grep -F "$MARKER"
echo
echo "Uploads/output will be logged to $LOG_FILE"
echo "To remove later: crontab -l | grep -vF '$MARKER' | crontab -"
