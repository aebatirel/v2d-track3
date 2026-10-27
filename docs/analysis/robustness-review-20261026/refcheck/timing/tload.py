"""Shared loaders for refcheck/timing (26 Oct 2026; CPU; PUBLIC episodes only; mocap is read only for diagnostics).

Reuses refcheck/systematics (sysload.py, systematics.py: kit registration and in-process kit AUC) READ-ONLY; the
registration cache is redirected to this check's own work dir (a copy of systematics' cache, same kit seeds).
Sources per episode (refcheck/resolve/canonical_refs.json):
  perc   canonical perception poses_world_vo.npz (camera-0 frame; tracking mesh = PERC_LIB)
  pre    e2s_reference.parquet (mkref output, before contact retarget; table frame; REF_LIB meshes)
  ref    final reference parquet (what grasp lock / the policy start from)
  glockt the grasp-lock training reference the rollouts name in their metadata (object path checked == ref)
  stale  20 Oct refsweep reference (perception templated on the PUBLIC scans; only used where no canonical ref exists)
  sim_rK achieved object poses of rollout rK of the canonical results dir
"""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
from scipy.ndimage import gaussian_filter1d

SYSDIR = '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/systematics'
sys.path.insert(0, SYSDIR)
from sysload import *                                                     # noqa: E402,F401,F403
import systematics as S                                                   # noqa: E402

WORK = f'{RC}/work/timing'
S.WORK = WORK                                                             # own registration cache
FPS = 1.0 / 0.049373                                                      # video / mocap rate (timestamp grid), Hz
MS = 1000.0 / FPS                                                         # ms per frame
STALE = 'runs/20261020-refsweep-ea14fdf/refs/perc2/ep{}'
PROBE_SITES = ['thumb_tip_site', 'index_tip_site', 'middle_tip_site', 'ring_tip_site', 'pinky_tip_site',
               'thumb_DP_site', 'index_DP_site', 'middle_DP_site', 'ring_DP_site', 'pinky_DP_site',
               'thumb_MCP_VL_site', 'index_MP_site', 'middle_MP_site', 'ring_MP_site', 'pinky_MP_site']
PALM_FRAMES = ['hand_C_MC', 'index_MCP_VL_site', 'middle_MCP_VL_site', 'ring_MCP_VL_site', 'pinky_MC_site']
TIPS, PALM = [4, 8, 12, 16, 20], [0, 5, 9, 13, 17]                        # MediaPipe joint ids (mkref)


def host_anchor(n, slot):
    return S.host_geometry(n, slot)['anchor']


def our_anchor(ep, slot, n, lib):
    if lib == 'scan':
        return host_anchor(n, slot)
    return S.registration(ep, slot, n, our_mesh_path(lib, n))['anchor']


def mesh_for(lib, n):
    return scan_path(n) if lib == 'scan' else our_mesh_path(lib, n)


def glockt_file(e):
    if not e.get('results_dir'):
        return None
    run = e['results_dir'].split('/results/')[0]
    g = sorted(glob.glob(f"{STORE}/{run}/refs/glockt/ep{e['ep']}/processed/*/*/*.parquet"))
    return g[0] if g else None


def rollout_files(e):
    if not e.get('results_dir'):
        return []
    return sorted(glob.glob(f"{STORE}/{e['results_dir']}/r*/episode_*.parquet"))


def load_rollout(f, names):
    t = pq.read_table(f).to_pandas()
    t = t[t.environment_id == t.environment_id.min()]
    out = {}
    for n in names:
        g = t[t.object_body_name == n].sort_values('step')
        pos = g[['achieved_position_x', 'achieved_position_y', 'achieved_position_z']].values.astype(float)
        q = g[['achieved_quaternion_x', 'achieved_quaternion_y', 'achieved_quaternion_z', 'achieved_quaternion_w']].values.astype(float)
        out[n] = mats(pos, q / np.linalg.norm(q, axis=1, keepdims=True))
    return out


def sources(ep, e, with_sim=True, with_stale=True):
    names = [str(x) for x in e['objects']]
    out = {}
    pl = PERC_LIB[ep]
    out['perc'] = dict(poses=load_npz(f"{STORE}/{e['perception_path']}"), lib=pl, path=e['perception_path'])
    fin, pre, _ = ref_files(e)
    if fin:
        rl = REF_LIB[ep]
        if pre:
            out['pre'] = dict(poses=load_ref_parquet(pre), lib=rl, path=pre[len(STORE) + 1:])
        out['ref'] = dict(poses=load_ref_parquet(fin), lib=rl, path=fin[len(STORE) + 1:])
        if with_sim:
            for f in rollout_files(e):
                k = 'sim_' + os.path.basename(os.path.dirname(f))
                out[k] = dict(poses=load_rollout(f, names), lib=rl, path=f[len(STORE) + 1:])
    elif with_stale:
        sf = sorted(glob.glob(f"{STORE}/{STALE.format(ep)}/processed/*/*/*.parquet"))
        if sf:
            out['stale'] = dict(poses=load_ref_parquet(sf[0]), lib='scan', path=sf[0][len(STORE) + 1:])
    for k, v in out.items():
        v['anchor'] = [our_anchor(ep, s, n, v['lib']) for s, n in enumerate(names)]
    return out


def signals(M, c):
    P = M[:, :3, :3] @ c + M[:, :3, 3]
    return P, Rot.from_matrix(M[:, :3, :3])


def speed_cms(P, sigma=1.0):
    return S.speed(P, sigma) * 100.0 * FPS                                 # central difference of the smoothed path


def rate_degs(R, sigma=1.0):
    T = len(R); w = np.zeros(T)
    if T < 3:
        return w
    w[1:-1] = np.degrees((R[2:] * R[:-2].inv()).magnitude()) / 2.0 * FPS
    w[0], w[-1] = w[1], w[-2]
    return gaussian_filter1d(w, sigma, mode='nearest') if sigma else w
