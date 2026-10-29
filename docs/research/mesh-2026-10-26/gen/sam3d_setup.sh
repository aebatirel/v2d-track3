#!/bin/bash
# Env C for SAM 3D Objects (batch-2 generative probe, 2026-10-29), on the probe box after box_setup.sh.
# py3.10 + torch 2.6.0+cu124 (not the repo's conda torch 2.5.1/cu121 env): sdpa attention (the repo default, no
# flash_attn), spconv-cu124, pytorch3d built CPU-only (the inference path uses its transforms/structures only),
# kaolin replaced by a stub (flexicubes imports only kaolin.utils.testing.check_tensor). Weights: the gated
# checkpoints come from the private store (runs/<run>/weights/sam-3d-objects), copied there by the agent session,
# because the box token cannot read gated repos. Log: /content/results/gen/sam3d_setup.log.
set -u
exec >> /content/results/gen/sam3d_setup.log 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
export UV_CACHE_DIR=/content/uvcache UV_LINK_MODE=copy
PY=/venv/main/bin/python; UV="$PY -m uv"; P="-p /content/genv3/bin/python"
[ -d /content/ext/sam-3d-objects/.git ] || git clone -q --filter=blob:limit=20m https://github.com/facebookresearch/sam-3d-objects /content/ext/sam-3d-objects
git -C /content/ext/sam-3d-objects checkout -q f91db411c50efee93d8db7aeb323885650f6f722 && step "C-CODE-OK" || step "C-CODE-FAIL"
$UV venv -q -p $PY /content/genv3 && $UV pip install -q $P setuptools wheel ninja \
  && $UV pip install -q $P torch==2.6.0 torchvision==0.21.0 triton==3.2.0 --index-url https://download.pytorch.org/whl/cu124 \
  && step "C-TORCH-OK" || step "C-TORCH-FAIL"
$UV pip install -q $P "numpy<2" scipy pillow opencv-python-headless trimesh "timm==0.9.16" einops easydict tqdm safetensors \
  "huggingface_hub<1.0" hydra-core omegaconf loguru roma seaborn matplotlib xatlas plyfile fast_simplification \
  spconv-cu124 "transformers<5" fvcore iopath igraph scikit-image lightning optree jsonlines pymeshfix \
  && step "C-BASIC-OK" || step "C-BASIC-FAIL"
$UV pip install -q $P --no-deps git+https://github.com/microsoft/MoGe.git \
  "git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8" && step "C-MOGE-OK" || step "C-MOGE-FAIL"
FORCE_CUDA=0 MAX_JOBS=64 $UV pip install -q $P --no-build-isolation \
  "git+https://github.com/facebookresearch/pytorch3d.git@75ebeeaea0908c5527e7b1e305fbc7681382db47" && step "C-P3D-OK" || step "C-P3D-FAIL"
SP=$(/content/genv3/bin/python -c "import site; print(site.getsitepackages()[0])")
mkdir -p $SP/kaolin/utils
printf '# stub (gen probe): SAM 3D flexicubes imports only check_tensor\n' > $SP/kaolin/__init__.py
: > $SP/kaolin/utils/__init__.py
printf 'def check_tensor(*a, **k):\n    return True\n' > $SP/kaolin/utils/testing.py
step "C-KAOLIN-STUB-OK"
mkdir -p /content/w/sam3d && cd /content/w/sam3d && for f in pipeline.yaml ss_generator.yaml slat_generator.yaml ss_decoder.yaml \
  slat_decoder_gs.yaml slat_decoder_gs_4.yaml slat_decoder_mesh.yaml ss_encoder.yaml slat_encoder.yaml ss_decoder.ckpt \
  slat_decoder_gs.ckpt slat_decoder_gs_4.ckpt slat_decoder_mesh.ckpt slat_generator.ckpt ss_generator.ckpt; do
  hf download $HF_STORE runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints/$f --repo-type dataset \
    --local-dir /content/w/sam3d > /dev/null 2>&1 || step "C-W-$f-FAIL"
done
ls -la /content/w/sam3d/runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/checkpoints && step "C-WEIGHTS-DONE"
cd /content/ext/sam-3d-objects && /content/genv3/bin/python -c "
import sys; sys.path.insert(0, '.')
from sam3d_objects.pipeline.inference_pipeline_pointmap import InferencePipelinePointMap; print('import ok')" && step "C-IMPORT-OK" || step "C-IMPORT-FAIL"
