"""Episode bundle (module M2d of SPEC section 7; formats of SPEC section 6; build step B1).

  load_bundle(path) -> Bundle            read RUN/bundle/<split>/ep<N>/ (episode.json + <obj>.npz) through the guard
                                         (role own) and the tracks it names (role tracks, sha256 checked)
  from_obs_all(ep, objects=None) -> Bundle
                                         DEV ONLY (GMG_MODE=dev, tier DEV): obs_all points and grids (library_v3 ROI
                                         box and --others, so dev contact numbers overstate separation), own = 0 for
                                         every point, shared = 0, contact from the tracks, the old box from obs_all
                                         lo/hi; table plane by RANSAC (pipeline/recon_mesh.table_plane) on the frame-0
                                         depth of the det dump (mask-key filter: keys depth and K only); sigma by the
                                         even/odd split floor (PREREG A.2)
  save_bundle(b, out_dir) -> dir         write episode.json and <obj>.npz (inside the run folder)

Bundle: .objects (names in slot order), .obs(obj) (dict with the obs_all-compatible keys pts, cam, frame, own, lo, hi,
vox, hits, free, state, shared, pocc, args), .poses (world_T_cam, cam_T_<obj>), .meta (episode.json dict),
.samples(obj) (contact.observed_samples, cached), .partners(obj) (other tracked objects), .sigma(obj) (m).

Grid rule (PREREG A.2, A.6): OBSERVED if hits >= 3 and hits / (hits + free) >= 0.5; FREE if free >= 3 and
hits / (hits + free) < 0.2; else UNKNOWN. Frames: the extraction sequence range(0, T, stride) of the tracks.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

from gmg import guard, contact as CT

SPLITS = ('public', 'eval')
STATE_UNKNOWN, STATE_FREE, STATE_OBSERVED = 0, 1, 2
OBS_KEYS = ('pts', 'cam', 'frame', 'lo', 'hi', 'vox', 'hits', 'free', 'args')
BUNDLE_KEYS = ('pts', 'cam', 'frame', 'own', 'lo', 'hi', 'vox', 'hits', 'free', 'state', 'shared', 'pocc', 'args')
SIGMA_SAMPLE = 50000                # odd-frame points used for the median distance (numerical estimate of a median)


def _paths():
    D = guard.CFG['data']
    return dict(obs_all=os.path.join(D, 'obs_all', 'ep{ep}_{obj}.npz'),
                tracks=os.path.join(D, 'data', 'sweep', 'ep{ep}', 'poses.npz'),
                calib=os.path.join(D, 'data', 'calib.json'),
                det=os.path.join(D, 'data', 'store', 'ep{ep}', 'det_f0.npz'),
                roster=os.path.join(guard.CFG['gmg'], 'roster_public.json'))


def _pipeline():
    pp = os.path.join(guard.CFG['repo'], 'pipeline')
    if pp not in sys.path:
        sys.path.insert(0, pp)
    import recon_mesh
    return recon_mesh


def grid_consts():
    return dict(
        obs_hits=guard.constant('observed_min_hits', 3, 'generic:PREREG A.6 keep / OBSERVED (obs_points.py default)'),
        obs_ratio=guard.constant('observed_min_ratio', 0.5, 'generic:PREREG A.6 keep / OBSERVED'),
        free_min=guard.constant('free_min_count', 3, 'generic:PREREG A.6 FREE'),
        free_ratio=guard.constant('free_max_ratio', 0.2, 'generic:PREREG A.6 FREE'),
    )


def state_grid(hits, free):
    c = grid_consts()
    h = np.asarray(hits, np.float64); f = np.asarray(free, np.float64)
    r = np.where(h + f > 0, h / np.maximum(h + f, 1), 0.0)
    st = np.zeros(h.shape, np.uint8)
    st[(f >= c['free_min']) & (r < c['free_ratio'])] = STATE_FREE
    st[(h >= c['obs_hits']) & (r >= c['obs_ratio'])] = STATE_OBSERVED
    return st


class Bundle:
    def __init__(self, meta, obs, poses, path=None):
        self.meta, self._obs, self.poses, self.path = meta, obs, poses, path
        self._samples = {}

    @property
    def objects(self):
        return list(self.meta['objects'])

    def obs(self, obj):
        return self._obs[obj]

    def partners(self, obj):
        return [p for p in self.objects if p != obj]

    def sigma(self, obj):
        return float(self.meta['sigma_mm'][obj]) * 1e-3

    def samples(self, obj):
        if obj not in self._samples:
            self._samples[obj] = CT.observed_samples(self._obs[obj])
        return self._samples[obj]

    def frames(self):
        return list(range(0, int(self.meta['T']), int(self.meta['stride'])))

    def good_frames(self, obj):
        g = self.meta['good'][obj]
        return [f for f in self.frames() if g[f]]

    def contact(self, o, p):
        return self.meta['contact'][f'{o}|{p}']

    def band(self, o, p):
        """V2 band b = min(8 mm, 3 sqrt(sigma_o^2 + sigma_p^2 + j^2)) in m (PREREG A.2)."""
        cap = guard.constant('v2_band_cap_m', 0.008, 'generic:PREREG A.6 V2 cap 8 mm = two voxels')
        k = guard.constant('v2_band_k', 3.0, 'generic:PREREG A.6 V2 band 3 sigma')
        j = float(self.contact(o, p).get('j_mm') or 0.0) * 1e-3
        return float(min(cap, k * np.sqrt(self.sigma(o) ** 2 + self.sigma(p) ** 2 + j ** 2)))

    def table_in_obj(self, obj, f):
        """(n, d) of the table plane in OBJ's frame at track frame f (height = n.x + d), or None."""
        tb = self.meta.get('table')
        if not tb:
            return None
        nw, cw = np.asarray(tb['n'], np.float64), float(tb['d'])
        C_W = np.linalg.inv(self.poses['world_T_cam'][f].astype(np.float64))
        nc = C_W[:3, :3] @ nw
        cc = cw - nc @ C_W[:3, 3]
        T = self.poses[f'cam_T_{obj}'][f].astype(np.float64)
        return T[:3, :3].T @ nc, float(nc @ T[:3, 3] + cc)

    def rest_plane(self, obj):
        r = (self.meta.get('rest') or {}).get(obj)
        if not r or r.get('n_obj') is None:
            return None
        return np.asarray(r['n_obj'], np.float64), float(r['d_obj'])


# ------------------------------------------------------------------------------------------------ dev bundle
def _sigma(obs, frames_seq):
    """PREREG A.2: route-A sheet (autokit.shell.shell_sheet) from the even frames of the extraction sequence; sigma
    = median distance of odd-frame owned points to it (SIGMA_SAMPLE of them at random, seed 0), clamped to
    [0.5, 3] mm. Returns (sigma_m, info)."""
    from autokit import shell as SH
    from gmg import geom
    lo_c = guard.constant('sigma_clamp_lo_m', 0.0005, 'sensor:PREREG A.6 sigma clamp')
    hi_c = guard.constant('sigma_clamp_hi_m', 0.003, 'sensor:PREREG A.6 sigma clamp')
    guard.constant('sigma_odd_sample_n', SIGMA_SAMPLE, 'generic:numerical estimate of the A.2 median')
    rank = {f: i for i, f in enumerate(frames_seq)}
    fr = np.asarray(obs['frame'])
    par = np.array([rank.get(int(f), -1) for f in np.unique(fr)])
    even_f = set(np.unique(fr)[(par >= 0) & (par % 2 == 0)].tolist())
    ev = np.isin(fr, list(even_f)) & (np.asarray(obs['own']) == 0)
    od = (~np.isin(fr, list(even_f))) & (np.asarray(obs['own']) == 0)
    sub = {k: np.asarray(obs[k])[ev] for k in ('pts', 'cam', 'frame')}
    sh = SH.shell_sheet(sub)
    sheet = sh['sheet']
    info = dict(even_points=int(ev.sum()), odd_points=int(od.sum()), sheet_faces=int(len(sheet.faces)))
    if len(sheet.faces) == 0 or od.sum() == 0:
        info['fallback'] = 'no sheet or no odd points: sigma = upper clamp'
        return hi_c, info
    idx = np.nonzero(od)[0]
    rng = np.random.default_rng(0)
    if len(idx) > SIGMA_SAMPLE:
        idx = rng.choice(idx, SIGMA_SAMPLE, replace=False)
    d, _, _ = geom.Closest(sheet).query(np.asarray(obs['pts'], np.float64)[idx])
    med = float(np.median(d))
    info.update(raw_median_mm=round(med * 1e3, 3), n=int(len(idx)))
    return float(np.clip(med, lo_c, hi_c)), info


def _table_from_det(ep, poses, obj0):
    """Frame-0 table plane in world coordinates (= frame-0 camera) from the det dump's depth (half resolution of the
    1600 x 1000 rectified image) with the half-resolution camera matrix; None if no det dump exists."""
    P = _paths()
    p = P['det'].format(ep=ep)
    if not os.path.exists(p):
        return None
    d = guard.load_npz(p, 'det', keys=['depth', 'K'])
    D0 = np.asarray(d['depth'], np.float32)
    K = np.asarray(d['K'], np.float64)
    s = D0.shape[1] / CT.IMG_W
    Kh = K.copy()
    Kh[0, 0] *= s; Kh[1, 1] *= s
    Kh[0, 2] = (K[0, 2] + 0.5) * s - 0.5; Kh[1, 2] = (K[1, 2] + 0.5) * s - 0.5
    o0 = (poses['world_T_cam'][0].astype(np.float64) @ poses[f'cam_T_{obj0}'][0].astype(np.float64))[:3, 3]
    n, c, frac = _pipeline().table_plane(D0, Kh, o0)
    return dict(n=[float(x) for x in n], d=float(c), inlier_frac=round(float(frac), 4), source='det_f0 depth (frame 0, '
                f'half resolution x{s:g}), recon_mesh.table_plane RANSAC; no per-frame refit (dev)', obj_pos=obj0)


def _rest(b, obj, band):
    """PREREG A.3 V4: rest frames = speed below 2 mm per frame and the lowest owned points (1st percentile of the
    frame's heights) within 5 mm of the table; the 8 mm table band (obs_points.py) removed every point within 8 mm of
    the plane, so 'within 5 mm' is measured from the top of the band (DEVIATIONS, B1). Returns the rest record."""
    v_max = guard.constant('rest_speed_max_m_per_frame', 0.002, 'generic:PREREG A.6 V4 rest < 2 mm/frame')
    near = guard.constant('rest_near_table_m', 0.005, 'generic:PREREG A.6 V4 rest within 5 mm')
    share_min = guard.constant('rest_share_min', 0.10, 'generic:PREREG A.6 V4 rest >= 10 % of good frames')
    W = b.poses['world_T_cam'].astype(np.float64)
    T = b.poses[f'cam_T_{obj}'].astype(np.float64)
    xw = np.einsum('fij,fj->fi', W[:, :3, :3], T[:, :3, 3]) + W[:, :3, 3]
    sp = np.linalg.norm(np.diff(xw, axis=0), axis=1)
    sp = np.concatenate([sp, sp[-1:]])
    obs = b.obs(obj)
    P = np.asarray(obs['pts'], np.float64); fr = np.asarray(obs['frame']); own = np.asarray(obs['own'])
    good = b.good_frames(obj)
    rest, ns, ds, low = [], [], [], {}
    for f in good:
        pl = b.table_in_obj(obj, f)
        if pl is None:
            break
        m = (fr == f) & (own == 0)
        if not m.any():
            continue
        h = P[m] @ pl[0] + pl[1]
        lw = float(np.percentile(h, 1))
        low[f] = lw
        if sp[f] < v_max and lw <= band + near:
            rest.append(f); ns.append(pl[0]); ds.append(pl[1])
    rec = dict(frames=rest, share=round(len(rest) / max(len(good), 1), 4), applies=False, n_obj=None, d_obj=None,
               low1_mm_median=round(float(np.median(list(low.values()))) * 1e3, 2) if low else None)
    if ns:
        n = np.mean(ns, 0); n /= np.linalg.norm(n)
        rec.update(n_obj=[float(x) for x in n], d_obj=float(np.median(ds)))
    rec['applies'] = bool(rec['share'] >= share_min and ns)
    return rec


def from_obs_all(ep, objects=None, split='public'):
    """Dev bundle of episode EP from obs_all (SPEC section 7, M2d). Tier DEV. objects: all tracked objects of the
    episode in slot order (from gmg/roster_public.json); a subset is refused (contact needs every object)."""
    if guard.mode() != 'dev':
        raise guard.GuardError('gmg bundle.from_obs_all is dev only (GMG_MODE=dev)')
    if split != 'public':
        raise ValueError('from_obs_all: obs_all holds public episodes only')
    P = _paths()
    roster = guard.load_json(P['roster'], 'roster')
    slot = list(roster['episodes'][str(ep)])
    if objects is not None and list(objects) != slot:
        raise ValueError(f'from_obs_all ep{ep}: objects must be every tracked object in slot order {slot}')
    tp = P['tracks'].format(ep=ep)
    poses = guard.load_npz(tp, 'tracks')
    missing = [o for o in slot if f'cam_T_{o}' not in poses]
    if missing:
        raise ValueError(f'ep{ep}: tracks lack {missing}')
    T = int(min(len(poses['world_T_cam']), *[len(poses[f'cam_T_{o}']) for o in slot]))
    guard.constant('vote_voxel_m', 0.004, 'generic:PREREG A.6 vote voxel 4 mm')
    obs, args = {}, {}
    for o in slot:
        z = guard.load_npz(P['obs_all'].format(ep=ep, obj=o), 'obs_all', keys=list(OBS_KEYS))
        a = json.loads(str(z['args']))
        args[o] = a
        if abs(float(z['vox']) - 0.004) > 1e-9:
            raise ValueError(f'{o}: obs_all voxel {float(z["vox"])} != 4 mm')
        n = len(z['pts'])
        obs[o] = dict(pts=np.asarray(z['pts'], np.float32), cam=np.asarray(z['cam'], np.float32),
                      frame=np.asarray(z['frame'], np.int32), own=np.zeros(n, np.uint8),
                      lo=np.asarray(z['lo'], np.float64), hi=np.asarray(z['hi'], np.float64), vox=float(z['vox']),
                      hits=np.clip(z['hits'], 0, 65535).astype(np.uint16),
                      free=np.clip(z['free'], 0, 65535).astype(np.uint16))
        obs[o]['state'] = state_grid(obs[o]['hits'], obs[o]['free'])
        obs[o]['shared'] = np.zeros(obs[o]['hits'].shape, np.uint16)
    stride = {int(a['stride']) for a in args.values()}
    band = {float(a['table_band']) for a in args.values()}
    if len(stride) != 1 or len(band) != 1:
        raise ValueError(f'ep{ep}: obs_all files disagree on stride/table band {stride} {band}')
    stride, band = stride.pop(), band.pop()
    guard.constant('extraction_stride', stride, 'generic:SPEC section 7 M2 stride 2')
    guard.constant('table_band_m', band, 'generic:PREREG A.6 crop / SPEC M2 table band 8 mm (obs_points.py)')
    frames = list(range(0, T, stride))
    calib = guard.open_input(P['calib'], 'calib')
    K = _pipeline().rectified_K(calib)
    meta = dict(schema='gmg-episode/1', split=split, ep=int(ep), objects=slot, tier='DEV',
                source='dev: bundle.from_obs_all (obs_all = library_v3 ROI box and --others; contact overstates '
                       'separation; never evidence for the pot-and-lid rule)',
                roster=dict(path=P['roster'], sha256=guard._INPUTS[os.path.realpath(P['roster'])]['sha256']),
                T=T, stride=stride, vox=0.004,
                tracks=dict(path=tp, sha256=guard._INPUTS[os.path.realpath(tp)]['sha256']),
                K=K.tolist(), table_band_m=band)
    b = Bundle(meta, obs, poses)
    # good frames (track sanity is B4): every extraction frame with owned points
    meta['good'] = {}
    for o in slot:
        has = set(np.unique(obs[o]['frame']).tolist())
        meta['good'][o] = [f in has for f in range(T)]
    meta['sanity'] = {o: dict(flags=['sanity_not_run_B1']) for o in slot}
    # contact census from the tracks (2 mm centroids of owned points; footprints on the rectified image)
    cen = {o: CT.centroids(obs[o]['pts']) for o in slot}
    meta['contact'] = CT.census(cen, poses, frames, K) if len(slot) > 1 else {}
    # sigma per object (A.2), then jitter and the band per pair, then pocc
    meta['sigma_mm'], meta['sigma_info'] = {}, {}
    for o in slot:
        s, info = _sigma(obs[o], frames)
        meta['sigma_mm'][o] = round(s * 1e3, 4)
        meta['sigma_info'][o] = info
    for o in slot:
        for p in b.partners(o):
            rec = meta['contact'][f'{o}|{p}']
            Xp = b.samples(p)[0]
            j, npairs = CT.jitter(poses, o, p, Xp, rec['contact'], stride)
            rec.update(j_mm=round(j * 1e3, 4), j_pairs=npairs, co_moving=False, tie_break='none')
            rec['band_mm'] = round(b.band(o, p) * 1e3, 4)
    for o in slot:
        ob = obs[o]
        pocc = np.zeros(ob['hits'].shape, np.uint16)
        for p in b.partners(o):
            X, _, fid, _ = CT.partner_samples(b, o, p, meta['contact'][f'{o}|{p}']['contact'])
            vi, ok = CT._vox_index(X, ob['lo'], ob['vox'], pocc.shape)
            if ok.any():
                key = np.unique(np.stack([np.ravel_multi_index(vi[ok].T, pocc.shape), fid[ok]], 1), axis=0)
                np.add.at(pocc.reshape(-1), key[:, 0], 1)
        ob['pocc'] = pocc
        ob['args'] = json.dumps(dict(source='obs_all', obs_all_args=args[o]))
    meta['census_change'] = {}
    # table plane (frame 0, world) and at-rest planes
    meta['table'] = _table_from_det(ep, poses, slot[0])
    meta['rest'] = {o: _rest(b, o, band) for o in slot} if meta['table'] else {}
    meta['flags'] = ['dev_bundle', 'no_hands_rerun', 'contact_from_tracks']
    return b


# ------------------------------------------------------------------------------------------------ save / load
def bundle_dir(run, split, ep):
    return os.path.join(run, 'bundle', split, f'ep{int(ep)}')


def save_bundle(b, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for o in b.objects:
        ob = b.obs(o)
        np.savez_compressed(os.path.join(out_dir, f'{o}.npz'),
                            **{k: (np.asarray(ob[k]) if k != 'args' else np.asarray(ob[k])) for k in BUNDLE_KEYS})
    meta = dict(b.meta)
    meta['constants'] = guard.constants()
    meta['inputs'] = [dict(role=r['role'], path=r['realpath'], sha256=r['sha256'], tier=r['tier'])
                      for r in guard.inputs()]
    meta['commit'] = guard._git('rev-parse', 'HEAD')
    with open(os.path.join(out_dir, 'episode.json'), 'w') as f:
        json.dump(meta, f)
    b.path = out_dir
    return out_dir


def load_bundle(path):
    meta = guard.load_json(os.path.join(path, 'episode.json'), 'own')
    tp = meta['tracks']['path']
    guard.open_input(tp, 'tracks', expect_sha256=meta['tracks']['sha256'])
    poses = guard.load_npz(tp, 'tracks')
    obs = {}
    for o in meta['objects']:
        z = guard.load_npz(os.path.join(path, f'{o}.npz'), 'own', keys=list(BUNDLE_KEYS))
        d = {k: z[k] for k in BUNDLE_KEYS}
        d['vox'] = float(d['vox']); d['args'] = str(d['args'])
        obs[o] = d
    return Bundle(meta, obs, poses, path=path)
