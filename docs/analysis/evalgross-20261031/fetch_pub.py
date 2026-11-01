#!/usr/bin/env python3
"""Fetch public calibration inputs (inference side only) and the ego_cam_c videos, single-file hf_hub_download.
Public perception = the 25 Oct tracks the 30 Oct depth audit scored (docs/research/work/refine/README_inputs.md §2),
so the per-frame depth-audit table calib_gt/v2/per_frame.csv lines up with them frame by frame.
No dataset parquet, no mocap, no scan, no score file is requested.
Usage: python3 -I fetch_pub.py OUT_DIR [poses|video_pub|video_eval]"""
import sys, time
from huggingface_hub import hf_hub_download

OUT, MODE = sys.argv[1], sys.argv[2]
GUARD = [0, 11, 12, 18, 21, 23, 24, 31]
PUB = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
EVAL = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]


def get(repo, path):
    for k in range(4):
        try:
            return hf_hub_download(repo, path, repo_type='dataset', local_dir=OUT, token='x')
        except Exception as ex:  # noqa: BLE001
            if '404' in str(ex) or 'NotFound' in type(ex).__name__:
                return None
            time.sleep(5 * (k + 1))


if MODE == 'poses':
    for e in PUB:
        d = f'runs/20261025-guard-fe3f407/results/sweep/guard/ep{e}' if e in GUARD else \
            f'runs/20261025-sweep-a894083/results/sweep/base/ep{e}'
        print(e, get('aebatirel/v2d-store', f'{d}/poses.npz'), flush=True)
else:
    split, eps = ('public', PUB) if MODE == 'video_pub' else ('evaluation', EVAL)
    for e in eps:
        print(e, get('nvidia/video_to_data_challenge',
                     f'track_3/{split}/videos/chunk-000/observation.images.ego_cam_c/episode_{e:06d}.mp4'), flush=True)
