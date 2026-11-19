#!/bin/bash
# Install NVIDIA ViPE + MetricTrail on a box, separately from our pipeline's venv (2026-11-19, camera-arms test,
# docs/analysis/camarms-20261119/PREREG.md). Follows ViPE's README/docs at the pinned commit: conda env cu128
# (nvcc 12.8) + uv sync, then the MetricTrail DPVO kernels (mono + stereo) and weights.
# Writes /content/vipe_ready on success; logs to stdout. Idempotent.
#   bash ops/box/vipe_setup.sh > /content/results/camarms/vipe_setup.log 2>&1
set -eo pipefail
VIPE_COMMIT=${VIPE_COMMIT:-ead2e008bc055310121736a49ff306bba50d10dc}
MF=/content/mf; VR=/content/vipe; export TORCH_HOME=${TORCH_HOME:-/content/torch_home}
t0=$(date +%s); say() { echo "[vipe_setup $(( $(date +%s) - t0 ))s] $*"; }
[ -f /content/vipe_ready ] && { say "already ready"; exit 0; }

if [ ! -x $MF/bin/conda ]; then
  say "miniforge"
  curl -fsSL -o /content/mf.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
  bash /content/mf.sh -b -p $MF > /dev/null
fi
if [ ! -d $VR/.git ]; then
  say "clone ViPE"
  git clone -q https://github.com/nv-tlabs/vipe $VR
fi
git -C $VR fetch -q origin $VIPE_COMMIT 2> /dev/null || true
git -C $VR checkout -q $VIPE_COMMIT
say "ViPE at $(git -C $VR rev-parse HEAD)"
if [ ! -d $MF/envs/cu128 ]; then
  say "conda env cu128"
  $MF/bin/conda env create -q -p $MF/envs/cu128 -f $VR/envs/cu128.yml > /dev/null
fi
source $MF/bin/activate $MF/envs/cu128
export CUDA_HOME=$CONDA_PREFIX TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-12.0} MAX_JOBS=${MAX_JOBS:-$(nproc)}
nvcc --version | tail -2
cd $VR
say "uv sync (builds ViPE's CUDA extensions for sm ${TORCH_CUDA_ARCH_LIST})"
uv sync 2>&1 | tail -5
source $VR/.venv/bin/activate
uv pip install -q yacs numba
uv pip install -q xformers==0.0.33.post1 || say "xformers install failed (MoGe-2 falls back to torch sdpa)"
python -c "import torch; print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
say "MetricTrail kernels"
python -m vipe.metrictrail.build 2>&1 | tail -3
python -m vipe.metrictrail.build --stereo 2>&1 | tail -3
uv pip install -q OpenEXR opencv-python-headless 2> /dev/null || true   # depth artifacts (vipe_cam.py depth mode)

say "weights"
mkdir -p $TORCH_HOME/hub/metrictrail $TORCH_HOME/hub/checkpoints
python - << 'PYEOF'
import os, hashlib, shutil
from huggingface_hub import hf_hub_download
th = os.environ['TORCH_HOME']
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
dst = f'{th}/hub/metrictrail/dino_dpvo_multidataset15k.pth'
if not os.path.exists(dst):
    shutil.copy(hf_hub_download('nvidia/MetricTrail', 'dino_dpvo.pth'), dst)
assert sha(dst) == 'd0aa57e165b159fc84bdb9d94918ad9b508c153acfb4c46f5058ab80421fb5f5', 'DINO-DPVO digest'
print('dino_dpvo ok')
# DINOv3 ViT-S/16 in Meta's original .pth form (the gated facebook/ HF repo holds only the transformers export).
# MetricTrail checks this file's full sha256 against the value its checkpoint recorded at training time.
dst = f'{th}/hub/checkpoints/dinov3_vits16_pretrain_lvd1689m-08c60483.pth'
if not os.path.exists(dst):
    shutil.copy(hf_hub_download('xysun917/dinov3-vits16', 'dinov3_vits16_pretrain_lvd1689m-08c60483.pth'), dst)
print('dinov3 sha256', sha(dst))
PYEOF
say "smoke: load the DINO-DPVO network with the DINOv3 weights (digest checks)"
python - << 'PYEOF'
from vipe.metrictrail.checkpoint import resolve_dino_dpvo_checkpoint, resolve_dinov3_weights, checkpoint_payload
v, dino = checkpoint_payload(resolve_dino_dpvo_checkpoint(None), dinov3_weights=resolve_dinov3_weights(None))
print('checkpoint ok; DINOv3 digest matches', dino.get('weights_sha256', '')[:16])
PYEOF
touch /content/vipe_ready
say "READY"
