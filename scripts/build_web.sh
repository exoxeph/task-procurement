#!/bin/sh
# Build the static web page in a temporary folder, then copy only the finished files to web/out.
# Why: npm install creates a very large node_modules. If it sits inside the repo, Vercel packs it into
# the Python function and the bundle exceeds the 500 MB limit.
set -e
ROOT="$(pwd)"
WORK="$(mktemp -d)"
(cd web && tar --exclude=node_modules --exclude=.next --exclude=out -cf - .) | (cd "$WORK" && tar -xf -)
cd "$WORK"
npm ci
STATIC_EXPORT=1 API_MODE=live npm run build
mkdir -p "$ROOT/web/out"
cp -R out/. "$ROOT/web/out/"
echo "web/out ready: $(ls "$ROOT/web/out" | wc -l) entries"
