#!/usr/bin/env bash
# Rebuild index.html from /workspace/mk-funds/holdings.sqlite and push to ivanovski/mk-funds (GitHub Pages).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"; SITE=/workspace/mk-funds-site
python3 "$SRC/build.py"
cp "$SRC/build.py" "$SRC/template.html" "$SRC/update.sh" "$SITE/src/"
cd "$SITE"; touch .nojekyll; git add -A
if git diff --cached --quiet; then echo "no changes"; exit 0; fi
git commit -qm "Update data $(date +%F)"; git push -q origin main; echo pushed
