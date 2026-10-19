#!/bin/bash
# One-shot Colab (G4 / RTX PRO 6000 Blackwell) setup for V2D Track 3 experiments.
# Usage: bash /content/setup.sh > /content/setup.log 2>&1 &   (then: grep -E 'OK|DONE|rror' /content/setup.log)
cd /content
export CUDA_HOME=/usr/local/cuda TORCH_CUDA_ARCH_LIST=12.0 MAX_JOBS=40
apt-get -qq install -y git-lfs libeigen3-dev libboost-all-dev > /dev/null 2>&1

# --- FlashCHORD (NVIDIA evaluator pin) in its own uv venv, in the background ---
(
  if [ ! -d v2d ]; then
    git init -q v2d && cd v2d && git remote add origin https://github.com/nvidia-isaac/video_to_data.git &&
    GIT_LFS_SKIP_SMUDGE=1 git fetch -q --depth 1 origin 8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef &&
    GIT_LFS_SKIP_SMUDGE=1 git checkout -q FETCH_HEAD &&
    git lfs pull --include 'robotic_grounding/flash_chord/src/flash_chord/assets/**,robotic_grounding/source/robotic_grounding/robotic_grounding/assets/human_motion_data/ego_recon/**'
    cd /content
  fi
  pip install -q uv
  cd /content/v2d/robotic_grounding/flash_chord && uv python install 3.11 > /dev/null &&
  uv venv -q --python 3.11 .venv && UV_LINK_MODE=copy uv sync -q --frozen --extra train && echo FLASHCHORD-OK
) > /content/setup_flashchord.log 2>&1 &

# --- Track 3 public episode data ---
EP=${EP:-12}
B=https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3/public
mkdir -p /content/t3/v /content/t3/mesh
for c in a b c; do f=/content/t3/v/ep${EP}_$c.mp4; [ -s $f ] || curl -sSL -o $f $B/videos/chunk-000/observation.images.ego_cam_$c/episode_$(printf %06d $EP).mp4; done
[ -s /content/t3/ep${EP}.parquet ] || curl -sSL -o /content/t3/ep${EP}.parquet $B/data/chunk-000/episode_$(printf %06d $EP).parquet
[ -s /content/t3/calib.json ] || curl -sSL -o /content/t3/calib.json $B/meta/camera_calibration.json
for o in blue_cup plastic_dish_rack; do mkdir -p /content/t3/mesh/$o; f=/content/t3/mesh/$o/$o.glb; [ -s $f ] || curl -sSL -o $f $B/mesh/$o/$o.glb; done
echo DATA-OK

# --- submission kit (metric code) ---
mkdir -p /content/kit && cd /content/kit && [ -d v2d_submission_kit ] || (curl -sSL -o kit.zip https://nvidia-isaac.github.io/video_to_data/v2d_challenge/assets/v2d_submission_kit.zip && unzip -q -o kit.zip) ; cd /content && echo KIT-OK

# --- perception python deps (system Python 3.13, torch 2.11+cu130) ---
pip install -q open3d trimesh omegaconf timm einops imageio gdown scikit-image ruamel.yaml imgaug albumentations joblib h5py transformations pyrender PyOpenGL kornia psutil pybind11 ninja pyarrow warp-lang && echo PYDEPS-OK

# SAM2
SAM2_BUILD_CUDA=0 pip install -q 'git+https://github.com/facebookresearch/sam2.git' && echo SAM2-OK
mkdir -p /content/ckpt && [ -s /content/ckpt/sam2.1_hiera_large.pt ] || curl -sSL -o /content/ckpt/sam2.1_hiera_large.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt

# FoundationStereo (ViT-L 23-51-11)
[ -d FoundationStereo ] || git clone -q https://github.com/NVlabs/FoundationStereo.git
[ -d FoundationStereo/pretrained_models/23-51-11 ] || (cd FoundationStereo && gdown -q --folder https://drive.google.com/drive/folders/1VhPebc_mMxWKccrv7pdQLTvXYVcLYpsf -O pretrained_models)
ls FoundationStereo/pretrained_models/23-51-11 && echo FSTEREO-OK

# FoundationPose
[ -d FoundationPose ] || git clone -q https://github.com/NVlabs/FoundationPose.git
pip install -q --no-build-isolation 'git+https://github.com/NVlabs/nvdiffrast.git' && echo NVDIFFRAST-OK
pip install -q --no-build-isolation 'git+https://github.com/facebookresearch/pytorch3d.git' && echo PYTORCH3D-OK
(cd FoundationPose/mycpp && rm -rf build && mkdir build && cd build &&
 cmake .. -DPYTHON_EXECUTABLE=$(which python) -Dpybind11_DIR=$(python -m pybind11 --cmakedir) > /dev/null && make -j40 > /dev/null) && echo MYCPP-OK
[ -d FoundationPose/weights/2023-10-28-18-33-37 ] || (cd FoundationPose && gdown -q --folder https://drive.google.com/drive/folders/1DFezOAD0oD1BblsXVxqDsl8fj0qzB82i -O weights)
ls FoundationPose/weights && echo FPOSE-OK

wait
echo SETUP-DONE
