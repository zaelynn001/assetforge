#!/usr/bin/env bash
# Rev 1.2.0 - Distro
# assetforge launcher – robust mode (Rev 0.1.2)

set -Eeuo pipefail
shopt -s lastpipe

# ---------- error handling ----------
err() {
  local ec=$?
  echo "❌ run.sh failed (exit $ec) at line ${BASH_LINENO[0]} in ${FUNCNAME[1]:-main}" >&2
  echo "    Command: ${BASH_COMMAND}" >&2
  exit "$ec"
}
trap err ERR

# ---------- options ----------
DEBUG=0
APP="main"   # or "app_launcher" if you prefer
PORTABLE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --debug) DEBUG=1; shift ;;
    --app)   APP="${2:-main}"; shift 2 ;;
    --portable) PORTABLE=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ "$DEBUG" == "1" ]] && set -x

# ---------- project root detection ----------
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Expect src/ to exist here
[[ -d "src" ]] || { echo "src/ not found in $(pwd) — are you in the project root?" >&2; exit 3; }

# ---------- logs ----------
APP_NAME="assetforge"

if [[ -f "$SCRIPT_DIR/.portable" ]]; then
  PORTABLE=1
fi

if [[ "${ASSETFORGE_PORTABLE:-0}" == "1" ]]; then
  PORTABLE=1
fi

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"

DEFAULT_DATA_DIR="$DATA_HOME/$APP_NAME"
DEFAULT_STATE_DIR="$STATE_HOME/$APP_NAME"

if [[ $PORTABLE -eq 1 ]]; then
  DEFAULT_DATA_DIR="$SCRIPT_DIR/portable-data"
  DEFAULT_STATE_DIR="$SCRIPT_DIR/portable-state"
fi

DATA_DIR="${ASSETFORGE_DATA_DIR:-$DEFAULT_DATA_DIR}"
STATE_DIR="${ASSETFORGE_STATE_DIR:-$DEFAULT_STATE_DIR}"
LOG_DIR="$STATE_DIR/logs"

mkdir -p "$DATA_DIR" "$LOG_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/run-$STAMP.log"

echo "📒 Logging to: $LOG_FILE"

# ---------- venv ----------
if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
  echo "🐍 Using venv: $(python -V 2>&1)" | tee -a "$LOG_FILE"
else
  echo "⚠️  .venv not found; using system Python: $(python3 -V 2>&1)" | tee -a "$LOG_FILE"
fi

# ---------- environment ----------
export PYTHONUNBUFFERED=1
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export ASSETFORGE_DATA_DIR="$DATA_DIR"
export ASSETFORGE_STATE_DIR="$STATE_DIR"

# ---------- quick sanity checks ----------
python -c "import sys; print('Python OK:', sys.version.split()[0])" 2>&1 | tee -a "$LOG_FILE"
python -c "import PySide6, sqlite3; print('Imports OK')" 2>&1 | tee -a "$LOG_FILE"

# ---------- choose entrypoint ----------
case "$APP" in
  main)         ENTRY="src.main" ;;
  app_launcher) ENTRY="src.app_launcher" ;;
  *) echo "Unknown --app value: $APP" >&2; exit 4 ;;
esac

echo "▶️  Starting: python -X dev -W default -m $ENTRY" | tee -a "$LOG_FILE"

# ---------- run ----------
# Use python from venv if active, else python3/python fallback
PYTHON_BIN="${PYTHON_BIN:-python}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || PYTHON_BIN="python3"

# Run and tee both stdout & stderr into the log
set +e
"$PYTHON_BIN" -X dev -W default -m "$ENTRY" 2>&1 | tee -a "$LOG_FILE"
APP_EC=${PIPESTATUS[0]}
set -e

if [[ $APP_EC -ne 0 ]]; then
  echo "❌ App exited with code $APP_EC" | tee -a "$LOG_FILE"
  exit "$APP_EC"
fi

echo "✅ assetforge exited cleanly" | tee -a "$LOG_FILE"
