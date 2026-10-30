#!/bin/bash
# Batch-2 generative probe (2026-10-29): environments, code and weights on an H100 (sm_90) box.
# Started in the background through `ops/vast.sh exec`; log /content/results/gen/setup.log, markers <NAME>-OK/-FAIL.
#   env A /content/genv  : py3.10, torch 2.6.0+cu124 and the prebuilt Hopper wheels of the Pixal3D HF Space
#                          (cumesh, o_voxel, flex_gemm, nvdiffrast, nvdiffrec_render, natten, flash_attn_3; compiled for
#                          compute_90 only, so this env needs an H100/H200) -> Pixal3D (main) and TRELLIS.2
#   env B /content/genv2 : py3.10, torch 2.6.0+cu124 -> TripoSG and Hunyuan3D-2.1 (shape only)
# Weights: public, ungated HF repos only, into /content/w. The configs name two gated repos (facebook/dinov3...,
# briaai/RMBG-2.0); the run scripts replace them with public mirrors (camenduru/dinov3-vitl16-pretrain-lvd1689m,
# ZhengPeng7/BiRefNet). Third-party code is pinned to the commits below. Downloads run without the box's HF_TOKEN.
set -u
O=/content/results/gen; mkdir -p $O /content/w /content/ext
exec >> $O/setup.log 2>&1
step() { echo "[$(date -u +%FT%TZ)] $*"; }
export HF_HOME=/content/hfcache UV_CACHE_DIR=/content/uvcache UV_LINK_MODE=copy
unset HF_TOKEN GH_TOKEN
PY=/venv/main/bin/python
$PY -m pip install -q uv "huggingface_hub>=0.34" && step "UV-OK" || step "UV-FAIL"
UV="$PY -m uv"
TORCH="torch==2.6.0 torchvision==0.21.0 triton==3.2.0 --index-url https://download.pytorch.org/whl/cu124"
W1=https://github.com/JeffreyXiang/Storages/releases/download/Space_Wheels_251210
W2=https://github.com/LDYang694/Storages/releases/download/20260430

# ---- code (pinned) ----
clone() {  # $1 repo, $2 dir, $3 commit
  [ -d /content/ext/$2/.git ] || git clone -q --filter=blob:limit=20m https://github.com/$1 /content/ext/$2
  git -C /content/ext/$2 checkout -q $3 && step "CODE-$2-OK $3" || step "CODE-$2-FAIL"
}
clone TencentARC/Pixal3D Pixal3D f7cf38429b0bd264f1995f0f8743a88b1c728b94
clone microsoft/TRELLIS.2 TRELLIS.2 75fbf0183001ed9876c8dbb35de6b68552ee08bd
clone VAST-AI-Research/TripoSG TripoSG fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c
clone Tencent-Hunyuan/Hunyuan3D-2.1 Hunyuan3D-2.1 82920d643c0dc2f7bfd7255f45f62d386edfe60c

# ---- weights (background, in parallel with the installs) ----
(
  dl() { hf download "$@" > /dev/null 2>&1; }
  dl TencentARC/Pixal3D --local-dir /content/w/Pixal3D --include pipeline_mv.json LICENSE \
     "ckpts/ss_dec_conv3d_16l8_fp16.*" "ckpts/ss_flow_img_dit_1_3B_64_bf16_mv.*" \
     "ckpts/slat_flow_img2shape_dit_1_3B_512_bf16_mv.*" "ckpts/slat_flow_img2shape_dit_1_3B_1024_bf16_mv.*" \
     "ckpts/shape_dec_next_dc_f16c32_fp16.*" && step "W-PIXAL3D-OK" || step "W-PIXAL3D-FAIL"
  dl camenduru/dinov3-vitl16-pretrain-lvd1689m && dl ZhengPeng7/BiRefNet && step "W-DINO-BIREF-OK" || step "W-DINO-BIREF-FAIL"
  dl microsoft/TRELLIS.2-4B --local-dir /content/w/TRELLIS.2-4B --include pipeline.json \
     "ckpts/ss_flow_img_dit_1_3B_64_bf16.*" "ckpts/slat_flow_img2shape_dit_1_3B_512_bf16.*" \
     "ckpts/slat_flow_img2shape_dit_1_3B_1024_bf16.*" "ckpts/shape_dec_next_dc_f16c32_fp16.*" \
     && dl microsoft/TRELLIS-image-large --include "ckpts/ss_dec_conv3d_16l8_fp16.*" \
     && step "W-TRELLIS2-OK" || step "W-TRELLIS2-FAIL"
  dl VAST-AI/TripoSG --local-dir /content/w/TripoSG && step "W-TRIPOSG-OK" || step "W-TRIPOSG-FAIL"
  dl tencent/Hunyuan3D-2.1 --local-dir /content/w/hy3dgen/tencent/Hunyuan3D-2.1 \
     --include "hunyuan3d-dit-v2-1/*" "hunyuan3d-vae-v2-1/*" && step "W-HY21-OK" || step "W-HY21-FAIL"
  step "WEIGHTS-DONE $(du -sh /content/w | cut -f1)"
) &

# ---- env A: Pixal3D + TRELLIS.2 ----
$UV venv -q -p $PY /content/genv && $UV pip install -q -p /content/genv/bin/python $TORCH && step "A-TORCH-OK" || step "A-TORCH-FAIL"
$UV pip install -q -p /content/genv/bin/python setuptools wheel && $UV pip install -q -p /content/genv/bin/python pillow==12.0.0 imageio==2.37.2 imageio-ffmpeg==0.6.0 tqdm==4.67.1 \
  easydict==1.13 opencv-python-headless==4.12.0.88 trimesh==4.10.1 transformers==4.57.3 zstandard==0.25.0 \
  kornia==0.8.2 timm==1.0.22 diffusers==0.37.1 accelerate==1.13.0 plyfile==1.1.3 safetensors scipy ninja einops \
  "huggingface_hub<1.0" && step "A-BASIC-OK" || step "A-BASIC-FAIL"
# MoGe (single-view camera estimation, unused by the multi-view path) needs trimesh>=4.11: no deps, after the pins
$UV pip install -q -p /content/genv/bin/python --no-deps git+https://github.com/microsoft/MoGe.git && step "A-MOGE-OK" || step "A-MOGE-FAIL"
$UV pip install -q -p /content/genv/bin/python --no-deps $W2/natten-0.21.0+torch2.6cu124-cp310-cp310-linux_x86_64.whl \
  $W1/flash_attn_3-3.0.0b1-cp39-abi3-linux_x86_64.whl $W1/cumesh-0.0.1-cp310-cp310-linux_x86_64.whl \
  $W1/flex_gemm-0.0.1-cp310-cp310-linux_x86_64.whl $W1/o_voxel-0.0.1-cp310-cp310-linux_x86_64.whl \
  $W1/nvdiffrast-0.4.0-cp310-cp310-linux_x86_64.whl $W1/nvdiffrec_render-0.0.0-cp310-cp310-linux_x86_64.whl \
  $W2/utils3d-0.0.2-py3-none-any.whl && step "A-WHEELS-OK" || step "A-WHEELS-FAIL"
/content/genv/bin/python -c "import torch, flash_attn_interface, cumesh, o_voxel, flex_gemm, natten, nvdiffrast.torch; print(torch.__version__, torch.cuda.get_device_name(0))" \
  && step "A-IMPORT-OK" || step "A-IMPORT-FAIL"

# ---- env B: TripoSG + Hunyuan3D-2.1 shape ----
$UV venv -q -p $PY /content/genv2 && $UV pip install -q -p /content/genv2/bin/python $TORCH && step "B-TORCH-OK" || step "B-TORCH-FAIL"
$UV pip install -q -p /content/genv2/bin/python setuptools wheel && $UV pip install -q -p /content/genv2/bin/python diffusers transformers einops "huggingface_hub<1.0" opencv-python-headless \
  trimesh omegaconf scikit-image "numpy<2" peft jaxtyping typeguard pymeshlab pyyaml accelerate safetensors tqdm \
  pygltflib scipy ninja pybind11 fast_simplification timm && step "B-BASIC-OK" || step "B-BASIC-FAIL"
$UV pip install -q -p /content/genv2/bin/python --no-build-isolation diso && step "B-DISO-OK" || step "B-DISO-FAIL (TripoSG falls back to the skimage extractor)"
/content/genv2/bin/python -c "import torch, diffusers, trimesh; print(torch.__version__)" && step "B-IMPORT-OK" || step "B-IMPORT-FAIL"
wait
step "SETUP-DONE"
