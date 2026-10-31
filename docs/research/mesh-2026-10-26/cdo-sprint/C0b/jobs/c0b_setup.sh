#!/bin/bash
# C0b box environment: one uv venv pinned to the local CPU venv (E0's req_main.txt: Python 3.13). CPU only.
# Usage: bash c0b_setup.sh WORKDIR LOG     (prints C0B-SETUP-OK / C0B-SETUP-FAIL into LOG)
W=$1; L=$2; D=$(cd "$(dirname "$0")" && pwd); REQ=$D/../../E0/jobs/req_main.txt
mkdir -p $W
{
  command -v uv > /dev/null || python3 -m pip install -q uv==0.11.32 || curl -LsSf https://astral.sh/uv/0.11.32/install.sh | sh
  export PATH=$HOME/.local/bin:$PATH
  uv --version
  ( uv venv -q --python 3.13 $W/venv && uv pip install -q --python $W/venv/bin/python -r $REQ ) \
    && $W/venv/bin/python -c "import numpy, scipy, trimesh, cv2, manifold3d, skimage, fast_simplification, rtree, huggingface_hub; print('main ok', numpy.__version__, trimesh.__version__)" \
    && echo C0B-SETUP-OK || echo C0B-SETUP-FAIL
  $W/venv/bin/python -V
  uv pip freeze --python $W/venv/bin/python > $W/freeze_main.txt 2>&1
} >> $L 2>&1
grep -q C0B-SETUP-OK $L
