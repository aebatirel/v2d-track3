#!/bin/bash
# C0b public picks: C0's GT-free frame + kit budget check against library_v3 (REPORTED ONLY; the pick is already
# committed, nothing is decided here). Runs C0's scripts/frame_check.py unchanged. Reads mesh files only.
# Usage: bash report_frame_c0b.sh PICKS.json OUT.json
set -eu
S=/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad
R=/home/user/v2d-track3
P=$1; OUT=$2
specs=$(python3 -c "
import json,sys
p=json.load(open('$P'))['picks']
print(' '.join(f\"{o}:$R/{v['repo_path']}:$R/meshes/library_v3/{o}.glb\" for o,v in p.items() if v.get('pick')))")
$S/venv/bin/python -I $R/docs/research/mesh-2026-10-26/cdo-sprint/C0/scripts/frame_check.py $S/kit/v2d_submission_kit $OUT $specs
