#!/usr/bin/env bash
# Syncs find-book/ into the backend monorepo and pushes.
# Install as hook: ln -sf ../../backend/scripts/sync-frontend.sh .git/hooks/post-commit
set -e

# Resolve symlink so this works when called as a git hook
REAL_SCRIPT="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$REAL_SCRIPT")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_ROOT="$(cd "$BACKEND_ROOT/../find-book" && pwd)"

echo "[sync-frontend] Syncing $FRONTEND_ROOT → $BACKEND_ROOT/find-book/"

rsync -a --delete \
  --exclude='.git/' \
  --exclude='node_modules/' \
  --exclude='dist/' \
  --exclude='.env*' \
  "$FRONTEND_ROOT/" "$BACKEND_ROOT/find-book/"

cd "$BACKEND_ROOT"

if git diff --quiet HEAD -- find-book/ && git diff --cached --quiet -- find-book/; then
  echo "[sync-frontend] Nothing changed in backend repo — skip."
  exit 0
fi

FRONTEND_MSG=$(git -C "$FRONTEND_ROOT" log -1 --pretty=format:"%s")
FRONTEND_SHA=$(git -C "$FRONTEND_ROOT" log -1 --pretty=format:"%h")

git add find-book/
git commit -m "sync(frontend): $FRONTEND_MSG [$FRONTEND_SHA]"
git push origin develop

echo "[sync-frontend] Done — backend updated and pushed."
