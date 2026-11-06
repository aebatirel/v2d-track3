#!/bin/bash
# G0 box setup (build step B3): env C for SAM 3D Objects, as gen/sam3d_setup.sh of the 29 Oct probe (same pins), on
# the image vastai/pytorch:2.7.1-cu128-cuda-12.9-mini-py310-*: py3.10 venv with torch 2.6.0+cu124 (sdpa attention by
# default; the flash_attn 2.7.4.post1 wheel the pipeline forces on A100/H100/H200), spconv-cu124, pytorch3d built
# CPU-only (PYTORCH3D_FORCE_NO_CUDA=1: the mini image has nvcc but no CUDA library headers, which broke the probe's
# first build; the inference path uses its transforms/structures, and its renderer import needs the C extension),
# kaolin stubbed (flexicubes imports only kaolin.utils.testing.check_tensor). Weights: the gated SAM 3D checkpoints from
# the private store (runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints), with retries.
# Log: $1 (default /content/results/g0/setup.log); markers C-*-OK / C-*-FAIL; exit 1 if the import check fails.
set -u
L=${1:-/content/results/g0/setup.log}; mkdir -p "$(dirname "$L")"
exec >> "$L" 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
export UV_CACHE_DIR=/content/uvcache UV_LINK_MODE=copy HF_HUB_DISABLE_PROGRESS_BARS=1
PY=/venv/main/bin/python
$PY -m pip install -q uv "huggingface_hub>=0.34" && step "C-UV-OK" || step "C-UV-FAIL"
UV="$PY -m uv"; P="-p /content/genv3/bin/python"
[ -d /content/ext/sam-3d-objects/.git ] || git clone -q --filter=blob:limit=20m https://github.com/facebookresearch/sam-3d-objects /content/ext/sam-3d-objects
git -C /content/ext/sam-3d-objects checkout -q f91db411c50efee93d8db7aeb323885650f6f722 && step "C-CODE-OK" || step "C-CODE-FAIL"
# weights in the background while the env installs (12.4 GB)
W=/content/w/sam3d; C=$W/runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints
(
  for f in pipeline.yaml ss_generator.yaml slat_generator.yaml ss_decoder.yaml slat_decoder_gs.yaml slat_decoder_gs_4.yaml \
    slat_decoder_mesh.yaml ss_encoder.yaml slat_encoder.yaml ss_decoder.ckpt slat_decoder_gs.ckpt slat_decoder_gs_4.ckpt \
    slat_decoder_mesh.ckpt slat_generator.ckpt ss_generator.ckpt; do
    for i in 1 2 3 4; do
      [ -s $C/$f ] && break
      hf download $HF_STORE runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints/$f --repo-type dataset \
        --local-dir $W > /dev/null 2>&1 || { step "C-W-$f retry $i"; sleep $((i * 10)); }
    done
    [ -s $C/$f ] || step "C-W-$f-FAIL"
  done
  step "C-WEIGHTS-DONE $(ls $C | wc -l) files $(du -sh $C | cut -f1)"
) &
WPID=$!
$UV venv -q -p $PY /content/genv3 && $UV pip install -q $P setuptools wheel ninja \
  && $UV pip install -q $P torch==2.6.0 torchvision==0.21.0 triton==3.2.0 --index-url https://download.pytorch.org/whl/cu124 \
  && step "C-TORCH-OK" || step "C-TORCH-FAIL"
$UV pip install -q $P "numpy<2" scipy pillow opencv-python-headless trimesh "timm==0.9.16" einops easydict tqdm safetensors \
  "huggingface_hub<1.0" hydra-core omegaconf loguru roma seaborn matplotlib xatlas plyfile fast_simplification \
  spconv-cu124 "transformers<5" fvcore iopath igraph scikit-image lightning optree jsonlines pymeshfix \
  && step "C-BASIC-OK" || step "C-BASIC-FAIL"
# SAM 3D pins MoGe a8c3734 (requirements.txt), which pins utils3d 3913c65 (probe, 2026-10-29)
$UV pip install -q $P --no-deps "git+https://github.com/microsoft/MoGe.git@a8c37341bc0325ca99b9d57981cc3bb2bd3e255b" \
  "git+https://github.com/EasternJournalist/utils3d.git@3913c65d81e05e47b9f367250cf8c0f7462a0900" && step "C-MOGE-OK" || step "C-MOGE-FAIL"
CUDA_VISIBLE_DEVICES= PYTORCH3D_FORCE_NO_CUDA=1 FORCE_CUDA=0 MAX_JOBS=$(nproc) $UV pip install -q $P --no-build-isolation \
  "git+https://github.com/facebookresearch/pytorch3d.git@75ebeeaea0908c5527e7b1e305fbc7681382db47" && step "C-P3D-OK" || step "C-P3D-FAIL"
$UV pip install -q $P open3d astor gsplat pyvista && $UV pip install -q $P --no-deps \
  "https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl" \
  && step "C-EXTRA-OK" || step "C-EXTRA-FAIL"
SP=$(/content/genv3/bin/python -c "import site; print(site.getsitepackages()[0])")
mkdir -p $SP/kaolin/utils
printf '# stub (gen probe): SAM 3D flexicubes imports only check_tensor\n' > $SP/kaolin/__init__.py
: > $SP/kaolin/utils/__init__.py
printf 'def check_tensor(*a, **k):\n    return True\n' > $SP/kaolin/utils/testing.py
step "C-KAOLIN-STUB-OK"
/content/genv3/bin/python -m pip freeze > /content/results/g0/pip_freeze_genv3.txt 2> /dev/null \
  || $UV pip freeze $P > /content/results/g0/pip_freeze_genv3.txt 2> /dev/null
wait $WPID
cd /content/ext/sam-3d-objects && LIDRA_SKIP_INIT=1 /content/genv3/bin/python -c "
import sys; sys.path.insert(0, '.')
import torch, pytorch3d
from pytorch3d.renderer import look_at_view_transform
from sam3d_objects.pipeline.inference_pipeline_pointmap import InferencePipelinePointMap
print('import ok', torch.__version__, torch.cuda.get_device_name(0), pytorch3d.__version__)" && step "C-IMPORT-OK" || { step "C-IMPORT-FAIL"; exit 1; }
for f in $(ls $C); do [ -s $C/$f ] || { step "C-WEIGHTS-INCOMPLETE $f"; exit 1; }; done
[ $(ls $C | wc -l) -ge 15 ] || { step "C-WEIGHTS-INCOMPLETE"; exit 1; }
step "C-SETUP-DONE"
