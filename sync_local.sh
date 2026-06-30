#!/usr/bin/env bash
# sync_local.sh  —  PRIVATE, LOCAL USE ONLY
# Pulls the latest public report from GitHub, then appends Lucren content
# ideas to the local copy. The ideas section never touches GitHub or Discord.
#
# Called by cron — do not run manually unless you want to re-trigger ideas.
# Logs to: ~/Library/Logs/GlobalMarkets-investor-sync.log
# ---------------------------------------------------------------------------
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HOME/Library/Logs/GlobalMarkets-investor-sync.log"
PYTHON="/usr/local/bin/python3"
TYPE="${1:-open}"    # open | close | weekly | monthly
DATE=$(date +%Y-%m-%d)

echo ""                                                      >> "$LOG"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') | sync type=$TYPE ===" >> "$LOG"

cd "$DIR"

# 1. Pull the latest report from GitHub
echo "Pulling from GitHub..." >> "$LOG"
/usr/bin/git pull origin main >> "$LOG" 2>&1 || {
  echo "[ERROR] git pull failed" >> "$LOG"
  exit 1
}

# 2. Append Lucren content ideas to the local copy
echo "Appending content ideas (type=$TYPE)..." >> "$LOG"
case "$TYPE" in
  open)
    $PYTHON append_content_ideas.py --open  --date "$DATE" >> "$LOG" 2>&1 || \
      echo "  [WARN] content ideas failed — report saved without ideas" >> "$LOG"
    ;;
  close)
    $PYTHON append_content_ideas.py --close --date "$DATE" >> "$LOG" 2>&1 || \
      echo "  [WARN] content ideas failed — report saved without ideas" >> "$LOG"
    ;;
  weekly)
    $PYTHON append_content_ideas.py --weekly --date "$DATE" >> "$LOG" 2>&1 || \
      echo "  [WARN] content ideas failed — report saved without ideas" >> "$LOG"
    ;;
  monthly)
    $PYTHON append_content_ideas.py --monthly >> "$LOG" 2>&1 || \
      echo "  [WARN] content ideas failed — report saved without ideas" >> "$LOG"
    ;;
  *)
    echo "[ERROR] Unknown type: $TYPE. Use open|close|weekly|monthly" >> "$LOG"
    exit 1
    ;;
esac

echo "Done." >> "$LOG"
