#!/bin/bash
# E0 box environment: two uv venvs pinned to the local venvs (req_main.txt: Python 3.13; req_mp.txt: Python 3.12 with
# mediapipe 0.10.14 for pipeline/hands_mp.py, as pipeline/setup.sh builds /content/mpvenv). CPU only, no GPU code.
# Usage: bash e0_setup.sh WORKDIR LOG     (prints E0-SETUP-OK / E0-SETUP-FAIL lines into LOG)
W=$1; L=$2; D=$(cd "$(dirname "$0")" && pwd)
mkdir -p $W
{
  command -v uv > /dev/null || python3 -m pip install -q uv==0.11.32 || curl -LsSf https://astral.sh/uv/0.11.32/install.sh | sh
  export PATH=$HOME/.local/bin:$PATH
  uv --version
  ok=1
  ( uv venv -q --python 3.13 $W/venv && uv pip install -q --python $W/venv/bin/python -r $D/req_main.txt ) \
    && $W/venv/bin/python -c "import numpy, scipy, trimesh, cv2, manifold3d, skimage, fast_simplification, rtree, huggingface_hub; print('main ok', numpy.__version__, trimesh.__version__)" \
    && echo E0-SETUP-MAIN-OK || { echo E0-SETUP-MAIN-FAIL; ok=0; } &
  ( uv venv -q --python 3.12 $W/mpvenv && uv pip install -q --python $W/mpvenv/bin/python -r $D/req_mp.txt ) \
    && $W/mpvenv/bin/python -c "import mediapipe as mp, cv2, numpy; mp.solutions.hands.Hands; print('mp ok', mp.__version__)" \
    && echo E0-SETUP-MP-OK || echo E0-SETUP-MP-FAIL &
  wait
  $W/venv/bin/python -V; $W/mpvenv/bin/python -V
  uv pip freeze --python $W/venv/bin/python > $W/freeze_main.txt 2>&1
  uv pip freeze --python $W/mpvenv/bin/python > $W/freeze_mp.txt 2>&1
} >> $L 2>&1
grep -q E0-SETUP-MAIN-OK $L
