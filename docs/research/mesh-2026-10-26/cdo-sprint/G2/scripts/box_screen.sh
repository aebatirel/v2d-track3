#!/bin/bash
# G2 stage-1 screen on the generation box's CPUs (PREREG s7). Run ONLY after the freeze commit that holds
# G2/results/SHA256SUMS, with the box's repo checked out at that commit.
#   1 the kit, the 4 public scans and their reference caches (runs/$RUN_ID/screen/screen_pkg.tar, uploaded after the
#     freeze) -> /content/scr (MESH_SCR layout: loc/kit/v2d_submission_kit, loc/t3/mesh, interact/v5/metric/cache)
#   2 a py3.13 venv pinned to the local scorer env (fallback: env A + pandas, logged)
#   3 manifest from the frozen SHA256SUMS (each file hash-checked) -> screen6.py, NP workers
# Output /content/results/screen/{manifest.tsv,screen6.jsonl,screen.log}; marker SCREEN-DONE.
set -u
O=/content/results/screen; mkdir -p $O; exec >> $O/screen.log 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
REPO=/content/v2d-track3; G2=$REPO/docs/research/mesh-2026-10-26/cdo-sprint/G2; NP=${NP:-24}
step "commit $(git -C $REPO rev-parse HEAD)"
if [ ! -d /content/scr/loc ]; then
  hf download $HF_STORE runs/$RUN_ID/screen/screen_pkg.tar --repo-type dataset --local-dir /content/scrdl > /dev/null 2>&1
  tar xf /content/scrdl/runs/$RUN_ID/screen/screen_pkg.tar -C /content && step "PKG-OK $(sha256sum /content/scrdl/runs/$RUN_ID/screen/screen_pkg.tar | cut -c1-16)" \
    || { step "PKG-FAIL"; exit 1; }
fi
export UV_CACHE_DIR=/content/uvcache UV_LINK_MODE=copy
PY=/content/scrvenv/bin/python
if [ ! -x $PY ]; then
  /venv/main/bin/python -m uv venv -q -p 3.13 /content/scrvenv && /venv/main/bin/python -m uv pip install -q -p $PY \
    numpy==2.5.4 scipy==1.18.1 trimesh==5.2.0 pandas==3.1.0 networkx==3.7 rtree==1.4.1 fast_simplification==0.2.0 \
    && step "VENV-OK py3.13 pinned" || { step "VENV-FAIL: fallback env A + pandas"; /venv/main/bin/python -m uv pip install -q \
    -p /content/genv/bin/python pandas fast_simplification; PY=/content/genv/bin/python; }
fi
$PY -c "import numpy, scipy, trimesh, pandas; print('versions', numpy.__version__, scipy.__version__, trimesh.__version__, pandas.__version__)"
$PY -I $G2/scripts/screen_manifest.py $G2/results/SHA256SUMS /content/results $O/manifest.tsv
MESH_SCR=/content/scr nice -n 5 $PY -I $REPO/docs/research/mesh-2026-10-26/cdo-sprint/C4-audit/scripts/screen6.py \
  $O/manifest.tsv $O/screen6.jsonl --workers $NP
step "SCREEN-DONE $(grep -c . $O/screen6.jsonl) records, $(grep -c '"error"' $O/screen6.jsonl) errors"
