#!/bin/bash
# Extract the code PUBOWN runs, exactly as it was at the C0b public box's commit, into DEST (repo layout kept, so
# relative imports, the gmg guard's repo root and C0b's job paths work unchanged). Other sessions keep editing the
# shared scripts (e.g. C2/R adds prim_rack.py options); PUBOWN must build with C0b's frozen code, so it never runs the
# working tree's copies. Prints the tree hash of each extracted directory.
# Usage: pubown_freeze.sh REPO COMMIT DEST
set -euo pipefail
REPO=$1 C=$2 DEST=$3
MR=docs/research/mesh-2026-10-26
git -C "$REPO" cat-file -e "$C^{commit}" || { echo "commit $C not in $REPO" >&2; exit 2; }
DIRS=($MR/scripts $MR/autokit pipeline ops/provenance $MR/cdo-sprint/C0b/jobs)
FILES=$(git -C "$REPO" ls-tree -r --name-only "$C" -- "${DIRS[@]}"; \
        git -C "$REPO" ls-tree --name-only "$C" -- $MR/gmg/ | grep '\.py$'; \
        echo $MR/cdo-sprint/E0/jobs/req_main.txt; echo $MR/gmg/roster_public.json)
rm -rf "$DEST"; mkdir -p "$DEST"
git -C "$REPO" archive "$C" -- $FILES | tar -x -C "$DEST"
echo "{\"commit\": \"$(git -C "$REPO" rev-parse "$C")\", \"files\": $(echo "$FILES" | grep -c .), \"trees\": {$(for d in "${DIRS[@]}" $MR/gmg; do
  printf '"%s": "%s", ' "$d" "$(git -C "$REPO" rev-parse "$C:$d")"; done | sed 's/, $//')}}"
