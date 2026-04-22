#!/usr/bin/env bash
# Ghostline daily run wrapper
# Activates venv, runs the tool, logs output

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Create logs directory if needed
mkdir -p logs

# Date for log filename
DATE=$(date +%Y-%m-%d)
LOG_FILE="logs/run_${DATE}.log"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the tool, tee to both stdout and log file
python run.py 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}
echo "" >> "$LOG_FILE"
echo "Exit code: $EXIT_CODE" >> "$LOG_FILE"
exit $EXIT_CODE
