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
    obs = load_obs(obs_path(OBJ, EP))                      # dict pts, cam, frame, hits, free, lo, vox, args
    obs = load_obs(obs_path(OBJ, EP, refined=True))        # refine.py output
    P = load_poses(EP)                                      # dict world_T_cam (T,4,4), cam_T_<obj> (T,4,4)
    K = load_calib()['K']                                   # 3x3 rectified-left intrinsics of the depth maps
    m = load_mesh(path)                                     # candidate / library / earlier-round mesh (allow-listed roots)
    rp = mesh_input(path)                                   # checked real path for code that opens the file itself (kit)
    inputs_log()                                            # every input opened through this module, with sha256
CLI check: python io_gt.py OBJ EP   (prints the keys, shapes and the resolved paths)

Guard (stage 1b, 2026-10-29, after the stage-1 integrity audit): every input is checked twice before it is opened,
  1. deny-list: FORBIDDEN substrings of the path as given and as resolved through links (scan, loc, align, parquet,
     mocap), and regular files with more than one hard link (a hard link can give a GT file an innocent name);
  2. allow-list: the resolved path must sit under the roots of its kind (ROOTS: obs, corr, poses, calib, mesh).
Every input that passes is logged with its sha256 (INPUTS; inputs_log()), so a renamed copy is traceable against a
manifest of the extracted observation files.

gmg build step B0 (2026-10-30, SPEC v1 rev 1 sections 2 and 24): ROOTS['mesh'] no longer lists meshes/library_v3,
scratchpad/auto, results/prim/meshes, scratchpad/prim or scratchpad/lathe (library_v3 is deny-listed and the others
hold library-seeded or scan-informed meshes); its only root is the gmg run folder. Every check now also calls the
deny-list (ops/provenance/denylist.json through pipeline/provenance.py: path globs on the given and the resolved path,
and the sha256 of the file, so a renamed copy of a scan, a library_v1-v4 mesh or a scan-templated track is refused).
While the gmg guard is loaded in the process (sys.modules['gmg.guard']), every io_gt input must also pass it
(gmg.guard.check_io_gt): an io_gt root that is not on the gmg allow-list of the current GMG_MODE is refused (in clean
mode that includes obs_all/, obs/ and auto/stage1/refined/).
"""
import hashlib, json, os, subprocess, sys

import numpy as np

SCRATCH = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
OBS_DIRS = (f'{SCRATCH}/obs_all', f'{SCRATCH}/obs')           # preference order
REFINED_DIR = f'{SCRATCH}/auto/stage1/refined'
SWEEP_DIR = f'{SCRATCH}/data/sweep'
CALIB = f'{SCRATCH}/data/calib.json'
STORE = 'https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main'
SWEEP_RUN = 'runs/20261025-sweep-a894083/results/sweep/base'
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
PIPELINE = f'{REPO}/pipeline'
GMG_RUNS = os.path.join(os.path.realpath(os.environ.get('GMG_DATA_ROOT', SCRATCH)), 'gmg', 'runs')   # gmg run folders
GMG_RUNS_DEV = GMG_RUNS + '-dev'          # gmg dev-mode run folders (B0 round 2); the gmg guard admits them in dev only

ALLOWED_KEYS = ('pts', 'cam', 'frame', 'hits', 'free', 'lo', 'vox', 'args')
FORBIDDEN = ('/loc/', '/scan', '_align', '.parquet', 'mocap')   # substrings of a path that hold or derive from GT
# allow-listed roots per input kind (a directory root admits everything below it; a file root admits that file only)
# B0 (2026-10-30): the five mesh roots (scratchpad/auto, meshes/library_v3, results/prim/meshes, scratchpad/prim,
# scratchpad/lathe) are dropped; meshes come only from gmg run folders. obs gains the gmg run folders (bundles).
ROOTS = dict(
    obs=(f'{SCRATCH}/obs_all', f'{SCRATCH}/obs', REFINED_DIR, GMG_RUNS, GMG_RUNS_DEV),
    corr=(REFINED_DIR,),
    poses=(SWEEP_DIR,),
    calib=(CALIB,),
    mesh=(GMG_RUNS, GMG_RUNS_DEV),
)
DROPPED_MESH_ROOTS = (f'{SCRATCH}/auto', f'{REPO}/meshes/library_v3',
                      f'{REPO}/docs/research/mesh-2026-10-26/results/prim/meshes', f'{SCRATCH}/prim', f'{SCRATCH}/lathe')
INPUTS = {}                    # real path -> dict(kind, sha256, bytes, mtime) of every input that passed the guard
_PROV = {}
_SHA = {}                      # (real path, size, mtime_ns, inode) -> sha256


def _provenance():
    """pipeline/provenance.py, loaded from its file (no sys.path change), and the deny-lists it and the repo hold."""
    if 'mod' not in _PROV:
        import importlib.util
        spec = importlib.util.spec_from_file_location('io_gt_v2d_provenance', f'{PIPELINE}/provenance.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        lists = [mod.denylist()]
        repo_dl = f'{REPO}/ops/provenance/denylist.json'
        if os.path.abspath(mod.DENYLIST) != os.path.abspath(repo_dl):      # V2D_DENYLIST can add, never remove
            d = json.load(open(repo_dl))
            lists.append(dict(globs=list(d.get('globs', [])), sha256=dict(d.get('sha256', {}))))
        _PROV.update(mod=mod, lists=lists)
    return _PROV['mod'], _PROV['lists']


def _file_sha(rp):
    st = os.stat(rp)
    key = (rp, st.st_size, st.st_mtime_ns, st.st_ino)
    if key not in _SHA:
        h = hashlib.sha256()
        with open(rp, 'rb') as f:
            for b in iter(lambda: f.read(1 << 22), b''):
                h.update(b)
        _SHA[key] = h.hexdigest()
    return _SHA[key]


def deny_glob(path):
    """The deny-list glob (pipeline/provenance.py semantics) a path matches, as given or resolved, or None."""
    mod, lists = _provenance()
    import fnmatch
    for p in dict.fromkeys((os.path.abspath(str(path)), os.path.realpath(str(path)))):
        g = mod._glob_hit(p)
        if g:
            return g
        rel = os.path.relpath(p, REPO) if p.startswith(REPO + os.sep) else None
        for d in lists[1:]:
            for g in d['globs']:
                if fnmatch.fnmatch(p, g) or (rel is not None and fnmatch.fnmatch(rel, g)):
                    return g
    return None


def deny_sha(rp):
    """The deny-list entry whose sha256 the file RP has (a renamed copy of a denied file), or None."""
    if not os.path.isfile(rp):
        return None
    s = _file_sha(rp)
    for d in _provenance()[1]:
        if s in d['sha256']:
            return d['sha256'][s]
    return None


def check_path(path, sha=True):
    """Deny-list: raise ValueError if the path (as given or resolved through links) can hold ground truth (FORBIDDEN
    substrings, deny-list globs), if it is a regular file with more than one hard link, or (sha=True) if its sha256 is
    on the deny-list. Returns the resolved path. Path checks come first, so a refused path is never opened."""
    for p in (str(path), os.path.realpath(str(path))):
        low = p.lower()
        for bad in FORBIDDEN:
            if bad in low:
                raise ValueError(f'integrity: refused path {p!r} (contains {bad!r})')
    g = deny_glob(path)
    if g:
        raise ValueError(f'integrity: refused path {str(path)!r} (deny-list glob {g!r})')
    rp = os.path.realpath(str(path))
    if os.path.isfile(rp) and os.stat(rp).st_nlink > 1:
        raise ValueError(f'integrity: refused path {rp!r} (regular file with {os.stat(rp).st_nlink} hard links)')
    if sha:
        d = deny_sha(rp)
        if d:
            raise ValueError(f'integrity: refused path {rp!r} (sha256 on the deny-list: {d})')
    return rp


def _under(rp, root):
    r = os.path.realpath(root)
    return rp == r or rp.startswith(r.rstrip('/') + '/')


def check_input(path, kind):
    """Deny-list (check_path) + allow-list: the resolved path must lie under ROOTS[kind]; while the gmg guard is
    loaded it must also pass gmg.guard.check_io_gt; last, the sha256 deny check. Returns the resolved path."""
    rp = check_path(path, sha=False)
    if kind not in ROOTS:
        raise ValueError(f'integrity: unknown input kind {kind!r}')
    if not any(_under(rp, r) for r in ROOTS[kind]):
        raise ValueError(f'integrity: refused {kind} path {rp!r}: not under the allow-listed roots {ROOTS[kind]}')
    g = sys.modules.get('gmg.guard')
    if g is not None and hasattr(g, 'check_io_gt'):
        g.check_io_gt(rp, kind, exists=os.path.isfile(rp))
    d = deny_sha(rp)
    if d:
        raise ValueError(f'integrity: refused {kind} path {rp!r} (sha256 on the deny-list: {d})')
    return rp


def _sha256(rp):
    st = os.stat(rp)
    old = INPUTS.get(rp)
    if old and old['bytes'] == st.st_size and old['mtime'] == st.st_mtime:
        return old['sha256']
    return _file_sha(rp)                                     # shared with the deny-list sha256 check (cached)


def log_input(rp, kind):
    """Record the sha256 of an input that passed the guard (cached on size + mtime)."""
    st = os.stat(rp)
    INPUTS[rp] = dict(kind=kind, sha256=_sha256(rp), bytes=int(st.st_size), mtime=st.st_mtime)
    return INPUTS[rp]['sha256']


def inputs_log(reset=False):
    """[dict(path, kind, sha256, bytes)] of every input opened through this module since the last reset."""
    out = [dict(path=p, kind=v['kind'], sha256=v['sha256'], bytes=v['bytes']) for p, v in sorted(INPUTS.items())]
    if reset:
        INPUTS.clear()
    return out


def mesh_input(path):
    """Checked real path of a mesh file (deny-list + mesh roots), sha256 logged, for code that opens the file itself
    (the kit's budget_mesh, pipeline/mesh_gates.flip_check). Raises FileNotFoundError if it does not exist."""
    rp = check_input(path, 'mesh')
    if not os.path.isfile(rp):
        raise FileNotFoundError(rp)
    log_input(rp, 'mesh')
    return rp


def load_mesh(path, **kw):
    """Mesh through the guard: deny-list + allow-listed mesh roots (ROOTS['mesh']: the gmg run folders only, since
    B0), sha256 logged, then trimesh.load(force='mesh', **kw)."""
    import trimesh
    rp = mesh_input(path)
    return trimesh.load(rp, force='mesh', **kw)


def load_corr(path):
    """refine.py per-frame correction file (OUT.corr.npz next to a refined copy): dict frame, R, t, c0."""
    rp = check_input(path, 'corr')
    log_input(rp, 'corr')
    with np.load(rp, allow_pickle=False) as C:
        return {k: C[k] for k in ('frame', 'R', 't', 'c0')}


def load_obs(path, keys=ALLOWED_KEYS):
    """Observed-point file -> dict of numpy arrays, only allow-listed keys (missing optional keys are skipped).
    pts (N,3) float object frame [m], cam (N,3) camera centre per point, frame (N,) frame index, and the 4 mm vote
    grids hits / free with their origin lo and cell size vox, args (JSON of obs_points.py's arguments)."""
    keys = tuple(keys)
    bad = [k for k in keys if k not in ALLOWED_KEYS]
    if bad:
        raise ValueError(f'integrity: keys {bad} are not in ALLOWED_KEYS {ALLOWED_KEYS}')
    rp = check_input(path, 'obs')
    log_input(rp, 'obs')
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
            return check_input(c, 'obs')
    if must_exist:
        raise FileNotFoundError(f'no observed points for {name} in {cands}')
    return check_input(cands[0], 'obs')


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
    check_input(path, 'poses')
    if not os.path.isfile(path):
        _download(f'{STORE}/{SWEEP_RUN}/ep{int(ep)}/poses.npz', path)
    path = check_input(path, 'poses')
    log_input(path, 'poses')
    with np.load(path, allow_pickle=False) as Z:
        out = {k: Z[k].astype(np.float64) for k in Z.files if k == 'world_T_cam' or k.startswith('cam_T_')}
    if 'world_T_cam' not in out:
        raise ValueError(f'{path}: no world_T_cam')
    return out


def load_calib(path=CALIB):
    """Intrinsics of the depth maps obs_points.py back-projects: the rectified LEFT camera of the ego stereo pair
    (pipeline/recon_mesh.rectified_K: cv2.stereoRectify of ego_cam_c / ego_cam_b, 1280x800 -> 1600x1000, alpha 0).
    Returns dict(K (3,3), size (W, H) of the rectified image, left, right camera names, baseline_m)."""
    rp = check_input(path, 'calib')
    log_input(rp, 'calib')
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
