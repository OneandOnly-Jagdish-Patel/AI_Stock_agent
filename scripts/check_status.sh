#!/bin/bash
# Report trading-agent and dashboard service health and recent logs on the VM.

set -euo pipefail

USER_NAME="${USER_NAME:-kali}"
AGENT_UNIT="trading-agent@${USER_NAME}.service"
DASH_UNIT="trading-dashboard@${USER_NAME}.service"

echo "==> Host: $(hostname) | User: $(whoami) | Time: $(date -Is)"
echo "==> TZ=America/Chicago: $(TZ=America/Chicago date)"

echo ""
echo "==> Service status"
systemctl is-active "$AGENT_UNIT" || true
systemctl is-active "$DASH_UNIT" || true
systemctl --no-pager -l status "$AGENT_UNIT" || true
echo "---"
systemctl --no-pager -l status "$DASH_UNIT" || true

APP_DIRS=(
  "/home/${USER_NAME}/AIportfolio/AI_Stock_agent"
  "/home/${USER_NAME}/AI_Stock_portfolio"
)

LOG_FILE=""
for dir in "${APP_DIRS[@]}"; do
  if [ -f "${dir}/logs/agent.log" ]; then
    LOG_FILE="${dir}/logs/agent.log"
    break
  fi
done

echo ""
echo "==> Agent log file: ${LOG_FILE:-not found}"
if [ -n "$LOG_FILE" ]; then
  echo "--- Last 80 lines ---"
  tail -n 80 "$LOG_FILE" || true
  echo ""
  echo "--- Recent errors/warnings (last 200 lines) ---"
  tail -n 200 "$LOG_FILE" | grep -Ei 'error|exception|traceback|critical|failed|kill switch' || echo "(none)"
fi

echo ""
echo "==> journalctl agent (last 40 lines)"
journalctl -u "$AGENT_UNIT" -n 40 --no-pager 2>/dev/null || true

echo ""
echo "==> journalctl dashboard (last 20 lines)"
journalctl -u "$DASH_UNIT" -n 20 --no-pager 2>/dev/null || true
