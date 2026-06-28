#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run_reports.sh  —  GlobalMarkets-Investor report automation
#
# Usage:
#   ./run_reports.sh open          # run open report for today
#   ./run_reports.sh close         # run close report for today
#   ./run_reports.sh weekly        # run weekly recap (use on Fridays)
#   ./run_reports.sh all           # open + close + weekly (Friday)
#
# Called by cron — logs to run_reports.log
# ---------------------------------------------------------------------------
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$DIR/run_reports.log"
TYPE="${1:-open}"
DATE=$(date +%Y-%m-%d)
PYTHON="/usr/local/bin/python3"

echo "" >> "$LOG"
echo "=== $(date '+%Y-%m-%d %H:%M:%S') | type=$TYPE ===" >> "$LOG"

cd "$DIR"

# Cron schedule (add via: crontab -e)
# 30 9  * * 1-5  → 9:30 AM ET open   (Mon-Fri)
#  0 16 * * 1-5  → 4:00 PM ET close  (Mon-Fri)
#  0 17 * * 5    → 5:00 PM ET weekly (Friday)
# Note: update hours by +1 in Nov when EST (UTC-5) kicks in.

# Skip weekends
DAY=$(date +%u)   # 1=Mon … 7=Sun
if [[ "$DAY" -ge 6 ]]; then
  echo "Weekend — skipping." >> "$LOG"
  exit 0
fi

run_type() {
  local t="$1"
  echo "Running: generate_report.py --type $t --date $DATE" >> "$LOG"
  $PYTHON generate_report.py --type "$t" --date "$DATE" >> "$LOG" 2>&1
}

case "$TYPE" in
  open)   run_type open ;;
  close)  run_type close ;;
  weekly) run_type weekly ;;
  all)
    run_type open
    run_type close
    run_type weekly
    ;;
  *)
    echo "Unknown type: $TYPE. Use open|close|weekly|all" >> "$LOG"
    exit 1
    ;;
esac

# Fill narrative sections via Claude API
FILL_FLAG="--today"
[[ "$TYPE" == "weekly" ]] && FILL_FLAG="--weekly"
[[ "$TYPE" == "all" ]]    && FILL_FLAG="--all"

echo "Running fill_narratives.py $FILL_FLAG ..." >> "$LOG"
$PYTHON fill_narratives.py $FILL_FLAG --date "$DATE" >> "$LOG" 2>&1 || \
  echo "  [WARN] fill_narratives.py encountered an error — reports saved without narratives." >> "$LOG"

# Stage and commit new/changed report files
echo "Committing..." >> "$LOG"
git add Open/ Close/ Weekly/ 2>> "$LOG" || true

if git diff --cached --quiet; then
  echo "Nothing new to commit." >> "$LOG"
else
  git commit -m "Auto: $TYPE report for $DATE" >> "$LOG" 2>&1
  git push origin main >> "$LOG" 2>&1
  echo "Pushed to GitHub." >> "$LOG"
fi

echo "Done." >> "$LOG"
