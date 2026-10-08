#!/usr/bin/env bash
# agent_cron.sh — put Sarathi on a schedule without thinking about it again.
#
#   bash scripts/agent_cron.sh install     # add the cron job (weekly, Mon 08:00)
#   bash scripts/agent_cron.sh run         # run the queue right now
#   bash scripts/agent_cron.sh queue "goal"  # add a task
#   bash scripts/agent_cron.sh log         # tail the run log
#   bash scripts/agent_cron.sh remove      # remove the cron job
#
# The agent works the queue, archives each run to ~/.sarrathi/logs/, and exits.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${SARRATHI_HOME:-$HOME/.sarrathi}"
LOG="$HOME_DIR/logs/cron.log"
MARKER="# sarathi-agent (added by scripts/agent_cron.sh)"

mkdir -p "$HOME_DIR/logs"

case "${1:-help}" in
  queue)
    shift
    python3 "$ROOT/agent.py" --queue "${*:-unnamed task}"
    ;;
  run)
    cd "$ROOT"
    python3 agent.py --watch
    ;;
  log)
    tail -n "${2:-60}" "$LOG"
    ;;
  install)
    LINE="0 8 * * 1 cd $ROOT && python3 agent.py --watch >> $LOG 2>&1 $MARKER"
    if crontab -l 2>/dev/null | grep -qF "$MARKER"; then
      echo "Already installed. Current entry:"
      crontab -l | grep -F "$MARKER"
    else
      (crontab -l 2>/dev/null || true; echo "$LINE") | crontab -
      echo "Installed. Sarathi will work the queue every Monday at 08:00."
      echo "Queue a task:   bash scripts/agent_cron.sh queue \"research X\""
      echo "Run it now:     bash scripts/agent_cron.sh run"
    fi
    ;;
  remove)
    crontab -l 2>/dev/null | grep -vF "$MARKER" | crontab - || true
    echo "Removed."
    ;;
  *)
    sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
    ;;
esac
