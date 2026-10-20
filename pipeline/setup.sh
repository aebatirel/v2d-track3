#!/bin/bash
# One-shot setup for V2D Track 3 on a fresh GPU box (Colab G4, or Vast.ai with /content -> /workspace).
# Usage: bash /content/setup.sh > /content/setup.log 2>&1 &   (then: grep -aE '[A-Z0-9]+-OK|FAIL|DONE' /content/setup.log)
# Validated on Colab (2026-10); the Vast additions (/venv/main, CUDA dev headers, HF weight mirror, hand venvs) are
# written but not yet run.
# Optional: HF_STORE=<owner>/<repo> (private HF dataset repo) to pull the FoundationStereo/FoundationPose weights from
# our mirror instead of Google Drive.
cd /content
REPO_DIR=${REPO_DIR:-/content/v2d-track3}
[ -f /venv/main/bin/activate ] && . /venv/main/bin/activate      # Vast's vastai/pytorch images keep python here
export CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=12.0 MAX_JOBS=40 UV_LINK_MODE=copy
apt-get -qq update > /dev/null 2>&1
apt-get -qq install -y git-lfs libeigen3-dev libboost-all-dev cmake > /dev/null 2>&1
# Vast "mini" CUDA images ship nvcc but not the library headers that torch extensions include (cublas_v2.h etc.)
if [ ! -f $CUDA_HOME/include/cublas_v2.h ]; then
  CV=$(ls -d /usr/local/cuda-1* 2> /dev/null | sort -V | tail -1 | sed 's/.*cuda-//; s/\./-/')
  [ -n "$CV" ] && apt-get -qq install -y cuda-libraries-dev-$CV > /dev/null 2>&1
  [ -f $CUDA_HOME/include/cublas_v2.h ] && echo CUDADEV-OK || echo "CUDADEV-FAIL (version '$CV')"
fi
pip install -q uv

# --- FlashCHORD (NVIDIA evaluator pin) in its own uv venv, in the background ---
(
  if [ ! -d v2d ]; then
    git init -q v2d && cd v2d && git remote add origin https://github.com/nvidia-isaac/video_to_data.git &&
    GIT_LFS_SKIP_SMUDGE=1 git fetch -q --depth 1 origin 8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef &&
    GIT_LFS_SKIP_SMUDGE=1 git checkout -q FETCH_HEAD &&
    git lfs pull --include 'robotic_grounding/flash_chord/src/flash_chord/assets/**,robotic_grounding/source/robotic_grounding/robotic_grounding/assets/human_motion_data/ego_recon/**'
    cd /content
  fi
  cd /content/v2d/robotic_grounding/flash_chord && uv python install 3.11 > /dev/null &&
  uv venv -q --python 3.11 .venv && uv sync -q --frozen --extra train && echo FLASHCHORD-OK
) > /content/setup_flashchord.log 2>&1 &

# --- Track 3 dataset (all public + eval episodes, 1.5 GB), in the background ---
(bash $REPO_DIR/pipeline/fetch_data.sh) > /content/setup_data.log 2>&1 &

# --- hand venvs (CPU): MediaPipe, and NVIDIA's retargeter (see pipeline/README_ref.md), in the background ---
(
  uv venv -q --python 3.11 /content/mpvenv &&
  uv pip install -q --python /content/mpvenv/bin/python mediapipe==0.10.14 opencv-python-headless numpy scipy pyarrow &&
  echo MPVENV-OK
  uv venv -q --python 3.11 /content/rtvenv &&
  uv pip install -q --python /content/rtvenv/bin/python pin pin-pink daqp qpsolvers "viser>=0.2.11,<0.3" \
      loop-rate-limiters trimesh rtree "scipy>=1.14" pyarrow pandas tqdm opencv-python-headless &&
  uv pip install -q --python /content/rtvenv/bin/python torch --index-url https://download.pytorch.org/whl/cpu &&
  /content/rtvenv/bin/python -c "import qpsolvers; assert 'daqp' in qpsolvers.available_solvers" && echo RTVENV-OK
) > /content/setup_hands.log 2>&1 &
mkdir -p /content/ckpt
[ -s /content/ckpt/hand_landmarker.task ] || curl -fsSL -o /content/ckpt/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task

# --- submission kit (metric code, packer, evaluator runner) ---
mkdir -p /content/kit && cd /content/kit && [ -d v2d_submission_kit ] || (curl -sSL -o kit.zip https://nvidia-isaac.github.io/video_to_data/v2d_challenge/assets/v2d_submission_kit.zip && unzip -q -o kit.zip) ; cd /content && echo KIT-OK

# --- perception python deps (Colab: system Python 3.13 + torch 2.11+cu130; Vast: same versions in /venv/main) ---
# Colab preinstalls pandas, scipy, cv2, PIL, matplotlib, sklearn and yaml; the Vast mini image does not (box 1, 2026-10-20).
pip install -q open3d trimesh omegaconf timm einops imageio gdown scikit-image ruamel.yaml imgaug albumentations joblib h5py transformations pyrender PyOpenGL kornia psutil pybind11 ninja pyarrow warp-lang \
  pandas scipy opencv-python-headless pillow matplotlib scikit-learn pyyaml && echo PYDEPS-OK

# SAM2 (+ DINOv2-L into the torch hub cache, so the perception run does not fetch it)
SAM2_BUILD_CUDA=0 pip install -q 'git+https://github.com/facebookresearch/sam2.git' && echo SAM2-OK
[ -s /content/ckpt/sam2.1_hiera_large.pt ] || curl -sSL -o /content/ckpt/sam2.1_hiera_large.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt
python -c "import torch; torch.hub.load('facebookresearch/dinov2', 'dinov2_vitl14')" > /dev/null 2>&1 && echo DINOV2-OK

# FoundationStereo / FoundationPose weights: our HF mirror if available, else the authors' Google Drive folders
if [ -n "${HF_STORE:-}" ]; then
  hf download $HF_STORE --repo-type dataset --include 'weights/*' --local-dir /content/hfstore > /dev/null 2>&1   # an empty match also exits 0
  [ -n "$(ls -A /content/hfstore/weights 2> /dev/null)" ] && echo WEIGHTS-MIRROR-OK
fi

# FoundationStereo (ViT-L 23-51-11)
[ -d FoundationStereo ] || git clone -q https://github.com/NVlabs/FoundationStereo.git
[ -d /content/hfstore/weights/FoundationStereo/23-51-11 ] && mkdir -p FoundationStereo/pretrained_models && cp -rn /content/hfstore/weights/FoundationStereo/23-51-11 FoundationStereo/pretrained_models/
[ -d FoundationStereo/pretrained_models/23-51-11 ] || (cd FoundationStereo && gdown -q --folder https://drive.google.com/drive/folders/1VhPebc_mMxWKccrv7pdQLTvXYVcLYpsf -O pretrained_models)
ls FoundationStereo/pretrained_models/23-51-11 && echo FSTEREO-OK

# FoundationPose
[ -d FoundationPose ] || git clone -q https://github.com/NVlabs/FoundationPose.git
pip install -q --no-build-isolation 'git+https://github.com/NVlabs/nvdiffrast.git' && echo NVDIFFRAST-OK
pip install -q --no-build-isolation 'git+https://github.com/facebookresearch/pytorch3d.git' && echo PYTORCH3D-OK
(cd FoundationPose/mycpp && rm -rf build && mkdir build && cd build &&
 cmake .. -DPYTHON_EXECUTABLE=$(which python) -Dpybind11_DIR=$(python -m pybind11 --cmakedir) > /dev/null && make -j40 > /dev/null) && echo MYCPP-OK
[ -d /content/hfstore/weights/FoundationPose ] && mkdir -p FoundationPose/weights && cp -rn /content/hfstore/weights/FoundationPose/. FoundationPose/weights/
[ -d FoundationPose/weights/2023-10-28-18-33-37 ] || (cd FoundationPose && gdown -q --folder https://drive.google.com/drive/folders/1DFezOAD0oD1BblsXVxqDsl8fj0qzB82i -O weights)
ls FoundationPose/weights && echo FPOSE-OK

# Import what perception really imports, so a missing package fails here and not in the job
python -c 'import pandas, scipy, cv2, PIL, matplotlib, sklearn, yaml, torchvision, trimesh, pyarrow, omegaconf, sam2, open3d, kornia, warp, nvdiffrast.torch, pytorch3d' \
  && (cd FoundationPose && python -c 'import estimater') && (cd FoundationStereo && python -c 'import core.foundation_stereo') \
  && echo IMPORTS-OK || echo "IMPORTS-FAIL (see the traceback above)"

wait
for m in FLASHCHORD MPVENV RTVENV DATA; do grep -aq "$m-OK" /content/setup_*.log || echo "$m-FAIL (see /content/setup_*.log)"; done
echo SETUP-DONE
