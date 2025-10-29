#!/usr/bin/env bash
# Rev 1.2.0 - Distro
# Backup helper for AssetForge data/exports repositories.

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d .git ]]; then
  echo "backup: no git repository found at $ROOT_DIR" >&2
  exit 1
fi

git add data exports

if git diff --cached --quiet; then
  echo "backup: nothing to commit" >&2
  exit 0
fi

STAMP="$(date +%Y-%m-%dT%H:%M:%S)"
MESSAGE="Backup $STAMP"

git commit -m "$MESSAGE"

REMOTE="${1:-origin}"
BRANCH="${2:-main}"

git push "$REMOTE" "$BRANCH"

echo "backup: pushed commit '$MESSAGE' to $REMOTE/$BRANCH"
