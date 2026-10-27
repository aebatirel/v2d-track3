"""Allow-listed inputs of the autokit mesh engine: observed points, our own tracks and the depth-camera intrinsics.

GT-free by construction. This is the only module of autokit that opens input files, and it opens only
  - our observed-point files written by scripts/obs_points.py (stereo depth along OUR tracks), with the keys in
    ALLOWED_KEYS; the 'pose' / mocap / scan data never enter (paths under /loc/ or /scan, *_align files, parquet and
    mocap paths raise ValueError, and so does any key outside ALLOWED_KEYS);
  - our own tracks (store run 20261025-sweep-a894083: world_T_cam, cam_T_<obj>), downloaded like prep_obs.sh;
  - the rig calibration (data/calib.json), reduced to the rectified-left intrinsics that obs_points.py used.
Object names appear only as file-name parts supplied by the caller.

Usage (library):
    from autokit.io_gt import load_obs, obs_path, load_poses, load_calib
    obs = load_obs(obs_path('white_pot', 41))              # dict pts, cam, frame, hits, free, lo, vox, args
    obs = load_obs(obs_path('white_pot', 41, refined=True))  # refine.py output
    P = load_poses(41)                                      # dict world_T_cam (T,4,4), cam_T_<obj> (T,4,4)
    K = load_calib()['K']                                   # 3x3 rectified-left intrinsics of the depth maps
CLI check: python io_gt.py OBJ EP   (prints the keys, shapes and the resolved paths)
"""
import json, os, subprocess, sys

import numpy as np

SCRATCH = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
OBS_DIRS = (f'{SCRATCH}/obs_all', f'{SCRATCH}/obs')           # preference order
REFINED_DIR = f'{SCRATCH}/auto/stage1/refined'
SWEEP_DIR = f'{SCRATCH}/data/sweep'
CALIB = f'{SCRATCH}/data/calib.json'
STORE = 'https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main'
SWEEP_RUN = 'runs/20261025-sweep-a894083/results/sweep/base'
PIPELINE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'pipeline'))

ALLOWED_KEYS = ('pts', 'cam', 'frame', 'hits', 'free', 'lo', 'vox', 'args')
FORBIDDEN = ('/loc/', '/scan', '_align', '.parquet', 'mocap')   # substrings of a path that hold or derive from GT


def check_path(path):
    """Raise ValueError if the path (as given or resolved through links) can hold ground truth."""
    for p in (str(path), os.path.realpath(str(path))):
        low = p.lower()
        for bad in FORBIDDEN:
            if bad in low:
                raise ValueError(f'integrity: refused path {p!r} (contains {bad!r})')
    return os.path.realpath(str(path))


def load_obs(path, keys=ALLOWED_KEYS):
    """Observed-point file -> dict of numpy arrays, only allow-listed keys (missing optional keys are skipped).
    pts (N,3) float object frame [m], cam (N,3) camera centre per point, frame (N,) frame index, and the 4 mm vote
    grids hits / free with their origin lo and cell size vox, args (JSON of obs_points.py's arguments)."""
    keys = tuple(keys)
    bad = [k for k in keys if k not in ALLOWED_KEYS]
    if bad:
        raise ValueError(f'integrity: keys {bad} are not in ALLOWED_KEYS {ALLOWED_KEYS}')
    rp = check_path(path)
    with np.load(rp, allow_pickle=False) as Z:
        out = {k: Z[k] for k in keys if k in Z.files}
    if 'pts' in keys and 'pts' not in out:
        raise ValueError(f'{rp}: no pts')
    return out


def obs_path(obj, ep, refined=False, must_exist=True):
    """Path of the observed points of object OBJ in public episode EP: refined copy (refine.py) when refined=True,
    else obs_all/ (current extraction) before obs/ (older extraction)."""
    name = f'ep{int(ep)}_{obj}.npz'
    cands = [f'{REFINED_DIR}/{name}'] if refined else [f'{d}/{name}' for d in OBS_DIRS]
    for c in cands:
        if os.path.isfile(c):
            return check_path(c)
    if must_exist:
        raise FileNotFoundError(f'no observed points for {name} in {cands}')
    return check_path(cands[0])


def _download(url, dest):
    """curl like prep_obs.sh (the agent proxy is pre-configured); HF_TOKEN, if set, goes in a header, never a URL."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    cmd = ['curl', '-sSLf', '-o', dest + '.part', url]
    tok = os.environ.get('HF_TOKEN')
    if tok:
        cmd[1:1] = ['-H', f'Authorization: Bearer {tok}']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        if os.path.exists(dest + '.part'):
            os.remove(dest + '.part')
        raise FileNotFoundError(f'download failed ({r.returncode}): {url}: {r.stderr.strip()}')
    os.replace(dest + '.part', dest)


def load_poses(ep, sweep_dir=SWEEP_DIR):
    """Our own tracks of public episode EP: dict world_T_cam (T,4,4) and cam_T_<obj> (T,4,4) for every tracked
    object (float64). Downloads poses.npz from the HF store run 20261025-sweep-a894083 if it is not cached."""
    path = f'{sweep_dir}/ep{int(ep)}/poses.npz'
    check_path(path)
    if not os.path.isfile(path):
        _download(f'{STORE}/{SWEEP_RUN}/ep{int(ep)}/poses.npz', path)
    with np.load(path, allow_pickle=False) as Z:
        out = {k: Z[k].astype(np.float64) for k in Z.files if k == 'world_T_cam' or k.startswith('cam_T_')}
    if 'world_T_cam' not in out:
        raise ValueError(f'{path}: no world_T_cam')
    return out


def load_calib(path=CALIB):
    """Intrinsics of the depth maps obs_points.py back-projects: the rectified LEFT camera of the ego stereo pair
    (pipeline/recon_mesh.rectified_K: cv2.stereoRectify of ego_cam_c / ego_cam_b, 1280x800 -> 1600x1000, alpha 0).
    Returns dict(K (3,3), size (W, H) of the rectified image, left, right camera names, baseline_m)."""
    rp = check_path(path)
    if PIPELINE not in sys.path:
        sys.path.insert(0, PIPELINE)
    from recon_mesh import rectified_K
    C = json.load(open(rp))
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    return dict(K=rectified_K(rp), size=(1600, 1000), left=sp['left'], right=sp['right'],
                baseline_m=float(sp['baseline_m']))


if __name__ == '__main__':
    obj, ep = sys.argv[1], int(sys.argv[2])
    p = obs_path(obj, ep)
    o = load_obs(p)
    print(p, {k: (v.shape, str(v.dtype)) for k, v in o.items()})
    P = load_poses(ep)
    print({k: v.shape for k, v in P.items()})
    print(np.round(load_calib()['K'], 2).tolist())
