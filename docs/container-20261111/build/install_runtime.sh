#!/bin/bash
# Team Imitation.Tech, V2D Track 3: the evaluation runtime of the submission container, installed the way our
# evaluation boxes installed it (pipeline/setup.sh at commit 9610329e of github.com/aebatirel/v2d-track3, FlashCHORD
# block), on the same base image (vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16):
#   0. uv 0.13.4 into the base image's /venv/main (setup.sh: `pip install -q uv`; 0.13.4 is the version in our boxes'
#      environment snapshot pt2.11-cu130-py313-20261020);
#   1. FlashCHORD (github.com/nvidia-isaac/video_to_data) at the pinned evaluator commit, with the same git-lfs
#      includes, into $PREFIX/v2d (boxes: /content/v2d);
#   2. its own uv venv: Python 3.11 (the base image ships uv's CPython 3.11.17, the one our boxes used) and
#      `uv sync --frozen --extra train` (the repository's uv.lock);
#   3. the kit Python $PREFIX/kit-venv: the base image's Python 3.13 (/venv/main) with the library versions that packed
#      the counted submission (pandas 3.0.5, pyarrow 26.0.0, numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0,
#      fast_simplification 0.2.0) and the kit's remaining requirements (kaggle, kagglesdk, six).
# The same script prepared the GPU box that reproduced the submission before the container was sent.
# Usage: PREFIX=/opt bash install_runtime.sh
set -euxo pipefail
PREFIX=${PREFIX:-/opt}
PIN=8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef
INCLUDE='robotic_grounding/flash_chord/src/flash_chord/assets/**,robotic_grounding/source/robotic_grounding/robotic_grounding/assets/human_motion_data/ego_recon/**'
export UV_LINK_MODE=copy UV_NO_CACHE=1

/venv/main/bin/pip install -q --no-cache-dir uv==0.13.4
UV=/venv/main/bin/uv
$UV --version

cd "$PREFIX"
git init -q v2d
cd v2d
git remote add origin https://github.com/nvidia-isaac/video_to_data.git
GIT_LFS_SKIP_SMUDGE=1 git fetch -q --depth 1 origin $PIN
GIT_LFS_SKIP_SMUDGE=1 git checkout -q FETCH_HEAD
[ "$(git rev-parse HEAD)" = $PIN ]
if ! git lfs pull --include "$INCLUDE"; then
  # Fallback for a build network that does not serve Git LFS (our build host's proxy): the same LFS objects from
  # GitHub's media endpoint for this commit, each checked against its pointer's sha256, into the local LFS store;
  # then the same checkout `git lfs pull` would do.
  python3 - "$PIN" "$INCLUDE" <<'EOF'
import hashlib, os, subprocess, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor
pin, include = sys.argv[1], sys.argv[2]
rows = [l.split(' ', 2) for l in subprocess.check_output(['git', 'lfs', 'ls-files', '-l', '-I', include], text=True).splitlines()]
def fetch(row):
    oid, _, path = row
    dst = f'.git/lfs/objects/{oid[:2]}/{oid[2:4]}/{oid}'
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    url = f'https://media.githubusercontent.com/media/nvidia-isaac/video_to_data/{pin}/' + urllib.parse.quote(path)
    for attempt in range(4):
        subprocess.run(['curl', '-sSfL', '--retry', '3', '-o', dst + '.part', url], check=False)
        if os.path.exists(dst + '.part') and hashlib.sha256(open(dst + '.part', 'rb').read()).hexdigest() == oid:
            os.replace(dst + '.part', dst)
            return
    raise SystemExit(f'LFS object {oid} ({path}) failed')
with ThreadPoolExecutor(8) as ex:
    list(ex.map(fetch, rows))
print(f'fetched {len(rows)} LFS objects, sha256-checked')
EOF
  git lfs checkout
fi
# every included LFS file is present, and no tracked file differs from the pinned commit
! git lfs ls-files -I "$INCLUDE" | grep -q ' - '
[ -z "$(git status --porcelain --untracked-files=no)" ]

cd robotic_grounding/flash_chord
$UV python install 3.11
$UV venv -q --python 3.11 .venv
$UV sync -q --frozen --extra train
.venv/bin/python --version
$UV pip freeze --python .venv/bin/python > "$PREFIX/flash_chord.venv.freeze.txt"

/venv/main/bin/python -m venv "$PREFIX/kit-venv"
"$PREFIX/kit-venv/bin/pip" install -q --no-cache-dir pandas==3.0.5 pyarrow==26.0.0 numpy==2.5.4 scipy==1.18.1 \
    trimesh==5.2.0 fast_simplification==0.2.0 kaggle==2.2.5 kagglesdk==0.1.38 six==1.17.0
"$PREFIX/kit-venv/bin/pip" freeze > "$PREFIX/kit-venv.freeze.txt"

python3 - "$PREFIX/v2d/robotic_grounding/flash_chord/src/flash_chord/evaluation" <<'EOF'
import hashlib, sys
from pathlib import Path
p = Path(sys.argv[1]); h = hashlib.sha256()
for n in sorted(['__init__.py', 'harness.py', 'metrics.py', 'rollout.py']):
    h.update(n.encode()); h.update(b'\0'); h.update((p / n).read_bytes())
print('eval_code_sha256', h.hexdigest())
EOF
