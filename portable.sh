#!/usr/bin/env bash
# Rev 1.2.0 - Distro
# Portable launcher for AssetForge.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

export ASSETFORGE_PORTABLE=1
export ASSETFORGE_DATA_DIR="${SCRIPT_DIR}/portable-data"
export ASSETFORGE_STATE_DIR="${SCRIPT_DIR}/portable-state"

mkdir -p "$ASSETFORGE_DATA_DIR" "$ASSETFORGE_STATE_DIR"

if [[ -x "${SCRIPT_DIR}/AssetForge" ]]; then
  exec "${SCRIPT_DIR}/AssetForge" "$@"
elif [[ -x "${SCRIPT_DIR}/run.sh" ]]; then
  exec "${SCRIPT_DIR}/run.sh" --portable "$@"
else
  echo "Unable to locate AssetForge binary or run.sh in ${SCRIPT_DIR}" >&2
  exit 1
fi
