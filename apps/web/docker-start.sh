#!/bin/sh
set -eu

cd /app

STAMP_FILE="node_modules/.perturvia-deps-hash"

CURRENT_HASH=$(
  sha256sum package.json package-lock.json |
    sha256sum |
    cut -d ' ' -f 1
)

if [ ! -x node_modules/.bin/next ] ||
   [ ! -f "$STAMP_FILE" ] ||
   [ "$(cat "$STAMP_FILE")" != "$CURRENT_HASH" ]; then

  echo "Installing/synchronizing frontend dependencies..."
  npm ci
  echo "$CURRENT_HASH" > "$STAMP_FILE"

else
  echo "Frontend dependencies are up to date."
fi

exec npm run dev -- -H 0.0.0.0
