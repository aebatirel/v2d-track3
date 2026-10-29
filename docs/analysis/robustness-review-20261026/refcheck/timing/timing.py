"""refcheck/timing: WHEN things happen in our reference vs the public mocap (26 Oct 2026; CPU; diagnostics only).

Mocap is read here only to measure our timing after inference; nothing here feeds inference.
Per canonical episode (refcheck/resolve/canonical_refs.json) and object:
 A. Object motion events in mocap and in each of our sources (perc, pre, ref, stale, sim_rK; see tload.py), on the
    kit anchor of each mesh (the point that corresponds to the scan's surface centroid). Axis-symmetric cups: the
    rotation is the swing of the symmetry axis (the spin about it is unobservable).
      crossing onset  first frame of >= SUSTAIN frames with displacement from the start rest pose (median of the
                      first N_REST frames) > 1 / 2 cm, or rotation > ROT_TH deg; 'move' = the earlier of 1 cm / ROT_TH
      crossing offset last frame of such a run against the final rest pose (median of the last N_REST frames)
      physical onset  (mocap) walk back from the 'move' crossing while speed >= V_LO cm/s or rotation rate >= W_LO deg/s
                      (Gaussian sigma 1 frame); physical offset the same forward from the 'move' offset
      speed edges     rising / falling edges of speed >= V_EV cm/s sustained >= SUSTAIN frames (all bouts), matched
                      mocap -> ours within +-MATCH frames
    Lag = ours - mocap in frames (> 0: ours LATE); 1 frame = 49.37 ms at the 20.254 Hz video / mocap grid.
 B. Hand contact timing in each reference that has hands (pre = mkref/E2S output, ref = after contact retarget,
    glockt = the grasp-lock training reference the rollouts name, stale = 20 Oct refsweep), against the TRUE (mocap)
    physical onset / offset of each object and against the reference's own onset:
      robot sites   min distance of the 15 probe sites + palm centre (mkref's contact probes) of either robot hand to
                    the object's surface (our mesh, posed by THAT reference's object path) < 1 / 2 cm
      human         MediaPipe/MANO joint centres (5 tips + 5 palm joints) of the perceived human hand < 2 cm
      labels        the reference's own contact labels (mano_*_object_contact_part_ids == object)
    contact runs: gaps <= BRIDGE bridged, runs >= MINRUN kept. arrival = start of the run active at the onset, else
    of the first run starting after it (before the offset); lead = onset - arrival (> 0: hand there BEFORE motion).
    release = end of the run active at the offset, else of the last run ending before it; lag = release - offset.
    unheld = frames inside the true moving window (and inside the reference's own moving window) with no contact.
    Grasp-lock plan (ref_gl[_r1]_grasp_lock.json matching glockt): hold_from / end per phase vs the true events.
    mkref hand bookkeeping (ref_summary.json): first valid frame, lead-in, filled (held / attached) invalid runs and
    their overlap with the true moving windows.
 C. Track-guard interventions (perception guard arm, runs/20261025-guard-fe3f407): re-acquired frames (log) and held
    frames (world pose identical to the previous frame), per object.
Usage: python -I timing.py OUT.json
"""
import glob, json, os, re, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tload import *                                                        # noqa: E402,F401,F403

POS_TH, ROT_TH, SUSTAIN, N_REST = (1.0, 2.0), 10.0, 3, 5
V_LO, W_LO, V_EV, MATCH = 1.0, 10.0, 5.0, 10
CONTACT_TH, HUMAN_TH, BRIDGE, MINRUN = (1.0, 2.0), 2.0, 2, 3
GUARD = 'runs/20261025-guard-fe3f407/results/sweep/guard/ep{}'


# ------------------------------------------------------------------ object tracks and events
def sym_axis_body(ep, slot, n, lib):
    if SYM.get(n) != 'axis':
        return None
    a = S.host_geometry(n, slot)['axis']
    if lib in ('scan', 'mocap'):
        return a
    return S.registration(ep, slot, n, our_mesh_path(lib, n))['R'].T @ a       # converted R = R_ours @ Rreg^T


class Track:
    def __init__(self, M, c, axis=None):
        self.P = M[:, :3, :3] @ c + M[:, :3, 3]
        self.R = Rot.from_matrix(M[:, :3, :3])
        self.u = None if axis is None else M[:, :3, :3] @ axis
        self.T = len(M)

    def rest(self, idx):
        p = np.median(self.P[idx], 0)
        if self.u is not None:
            r = self.u[idx].mean(0); r = r / np.linalg.norm(r)
        else:
            r = self.R[idx].mean()
        return p, r

    def ang_to(self, r):
        if self.u is not None:
            return np.degrees(np.arccos(np.clip(self.u @ r, -1, 1)))
        return np.degrees((self.R * r.inv()).magnitude())

    def rate(self):
        w = np.zeros(self.T)
        if self.u is not None:
            w[1:-1] = np.degrees(np.arccos(np.clip(np.sum(self.u[2:] * self.u[:-2], 1), -1, 1))) / 2 * FPS
            w[0], w[-1] = w[1], w[-2]
            from scipy.ndimage import gaussian_filter1d
            return gaussian_filter1d(w, 1.0, mode='nearest')
        return rate_degs(self.R)


def first_run(mask, k=SUSTAIN):
    for t in range(len(mask) - k + 1):
        if mask[t:t + k].all():
            return int(t)
    return None


def last_run(mask, k=SUSTAIN):
    for t in range(len(mask) - 1, k - 2, -1):
        if mask[t - k + 1:t + 1].all():
            return int(t)
    return None


def runs(mask):
    m = np.concatenate([[0], mask.astype(int), [0]]); d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0].tolist(), np.nonzero(d == -1)[0].tolist()))


def clean_runs(mask, bridge=BRIDGE, minrun=MINRUN):
    m = mask.copy(); r = runs(m)
    for (a0, a1), (b0, _) in zip(r, r[1:]):
        if b0 - a1 <= bridge:
            m[a1:b0] = True
    return [(a, b) for a, b in runs(m) if b - a >= minrun]


def frac_on(x, t, th):
    """Sub-frame time at which x rises through th just before frame t (linear interpolation)."""
    if t is None:
        return None
    if t == 0 or x[t - 1] >= th or x[t] == x[t - 1]:
        return float(t)
    return float(t - 1 + (th - x[t - 1]) / (x[t] - x[t - 1]))


def frac_off(x, t, th):
    """Sub-frame time at which x falls through th just after frame t."""
    if t is None:
        return None
    if t + 1 >= len(x) or x[t + 1] >= th or x[t] == x[t + 1]:
        return float(t)
    return float(t + (x[t] - th) / (x[t] - x[t + 1]))


def events(tr):
    T = tr.T; idx0, idxL = np.arange(min(N_REST, T)), np.arange(max(0, T - N_REST), T)
    p0, r0 = tr.rest(idx0); pL, rL = tr.rest(idxL)
    d0 = np.linalg.norm(tr.P - p0, axis=1) * 100; a0 = tr.ang_to(r0)
    dL = np.linalg.norm(tr.P - pL, axis=1) * 100; aL = tr.ang_to(rL)
    ev = {}
    for th in POS_TH:
        ev[f'on_p{th:g}'] = first_run(d0 > th); ev[f'off_p{th:g}'] = last_run(dL > th)
        ev[f'on_p{th:g}_f'] = frac_on(d0, ev[f'on_p{th:g}'], th); ev[f'off_p{th:g}_f'] = frac_off(dL, ev[f'off_p{th:g}'], th)
    ev['on_r'] = first_run(a0 > ROT_TH); ev['off_r'] = last_run(aL > ROT_TH)
    ev['on_r_f'] = frac_on(a0, ev['on_r'], ROT_TH); ev['off_r_f'] = frac_off(aL, ev['off_r'], ROT_TH)
    c = [x for x in (ev['on_p1'], ev['on_r']) if x is not None]; ev['on_move'] = min(c) if c else None
    c = [x for x in (ev['off_p1'], ev['off_r']) if x is not None]; ev['off_move'] = max(c) if c else None
    ev['max_disp_cm'] = round(float(d0.max()), 2); ev['max_rot_deg'] = round(float(a0.max()), 1)
    v, w = speed_cms(tr.P), tr.rate()
    r5 = [(a, b) for a, b in runs(v >= V_EV) if b - a >= SUSTAIN]
    ev['v_starts'] = [int(a) for a, _ in r5]; ev['v_ends'] = [int(b - 1) for _, b in r5]
    return ev, v, w, (d0, a0, dL, aL)


def physical(ev, v, w):
    """Mocap physical onset / offset by hysteresis around the 'move' crossings; moving bouts."""
    mv = (v >= V_LO) | (w >= W_LO)
    out = dict(on_phys=None, off_phys=None, bouts=[])
    if ev['on_move'] is None:
        return out, mv
    t = ev['on_move']
    while t - 1 >= 0 and mv[t - 1]:
        t -= 1
    out['on_phys'] = int(t)
    t = ev['off_move'] if ev['off_move'] is not None else ev['on_move']
    while t + 1 < len(mv) and mv[t + 1]:
        t += 1
    out['off_phys'] = int(t)
    out['bouts'] = [[int(a), int(b - 1)] for a, b in clean_runs(mv, bridge=9, minrun=5)]
    return out, mv


def match_edges(g, o):
    return [int(min(o, key=lambda x: abs(x - t)) - t) for t in g if o and min(abs(x - t) for x in o) <= MATCH]


# ------------------------------------------------------------------ hands
_TREES = {}


def surface_tree(mesh_path):
    if mesh_path not in _TREES:
        m = trimesh.load(mesh_path, force='mesh')
        pts = np.concatenate([np.asarray(trimesh.sample.sample_surface(m, 30000, seed=0)[0]), np.asarray(m.vertices)])
        _TREES[mesh_path] = cKDTree(pts)
    return _TREES[mesh_path]


def load_hands(path):
    cols = ['object_body_names', 'object_body_position', 'object_body_wxyz']
    for s in ('right', 'left'):
        cols += [f'{s}_robot_frame_names', f'robot_{s}_frames', f'mano_{s}_joints', f'mano_{s}_object_contact_part_ids']
    t = pq.read_table(path, columns=cols)
    g = lambda c: t.column(c)[0].as_py()
    names = g('object_body_names')
    pos = np.array(g('object_body_position'), float); q = np.array(g('object_body_wxyz'), float)
    obj = {n: mats(pos[:, i], q[:, i][:, [1, 2, 3, 0]] / np.linalg.norm(q[:, i], axis=1, keepdims=True)) for i, n in enumerate(names)}
    H = {}
    for s in ('right', 'left'):
        fn = g(f'{s}_robot_frame_names'); fr = np.array(g(f'robot_{s}_frames'), float)[..., :3]
        ix = {n: i for i, n in enumerate(fn)}
        probes = [fr[:, ix[f'{s}_{p}']] for p in PROBE_SITES] + [np.mean([fr[:, ix[f'{s}_{p}']] for p in PALM_FRAMES], 0)]
        J = np.array(g(f'mano_{s}_joints'), float)
        H[s] = dict(robot=np.stack(probes, 1), human=J[:, TIPS + PALM], pid=np.array(g(f'mano_{s}_object_contact_part_ids')))
    return names, obj, H


def hand_dist(Pw, M, tree):
    """min distance (cm) over probes (T,K,3) to the surface of the object posed by M (T,4,4)."""
    R, t = M[:, :3, :3], M[:, :3, 3]
    Po = np.einsum('tji,tkj->tki', R, Pw - t[:, None])
    d, _ = tree.query(Po.reshape(-1, 3))
    return d.reshape(Po.shape[:2]).min(1) * 100


def contact_events(mask, on, off, own_on=None, own_off=None, mv_true=None):
    rr = clean_runs(mask)
    out = dict(runs=[[a, b - 1] for a, b in rr][:40], n_runs=len(rr), first=(rr[0][0] if rr else None),
               contact_frac=round(float(mask.mean()), 3))
    for tag, a, b in (('true', on, off), ('own', own_on, own_off)):
        if a is None:
            continue
        act = [r for r in rr if r[0] <= a < r[1]]
        later = [r for r in rr if a < r[0] <= (b if b is not None else len(mask))]
        arr = act[0][0] if act else (later[0][0] if later else None)
        out[f'arrival_vs_{tag}'] = None if arr is None else int(arr)
        out[f'lead_vs_{tag}'] = None if arr is None else int(a - arr)
        out[f'contact_at_{tag}_onset'] = bool(act)
        if b is not None:
            act = [r for r in rr if r[0] <= b < r[1]]
            before = [r for r in rr if a <= r[1] - 1 < b]
            rel = act[0][1] - 1 if act else (before[-1][1] - 1 if before else None)
            out[f'release_vs_{tag}'] = None if rel is None else int(rel)
            out[f'release_lag_vs_{tag}'] = None if rel is None else int(rel - b)
            cm = np.zeros(len(mask), bool)
            for r0, r1 in rr:
                cm[r0:r1] = True
            win = np.zeros(len(mask), bool); win[a:b + 1] = True
            if tag == 'true' and mv_true is not None:
                win &= mv_true
            out[f'unheld_frames_{tag}'] = int((win & ~cm).sum()); out[f'window_frames_{tag}'] = int(win.sum())
    return out


# ------------------------------------------------------------------ main
def main():
    out_path = sys.argv[1]
    C = canon(); res = {}
    for ep, e in sorted(C.items()):
        names, gt = load_gt(ep)
        assert names == [str(x) for x in e['objects']], (ep, names, e['objects'])
        T = len(gt[names[0]])
        src = sources(ep, e)
        R = dict(T=T, objects=names, sources={k: v['path'] for k, v in src.items()}, obj={})
        # glockt object path == ref?
        gtf = glockt_file(e)
        if gtf:
            G = load_ref_parquet(gtf)
            R['glockt'] = gtf[len(STORE) + 1:]
            R['glockt_obj_path_vs_ref_mm'] = round(float(max(np.abs(G[n][:, :3, 3] - src['ref']['poses'][n][:, :3, 3]).max() for n in names) * 1000), 4)
        true_ev = {}
        for s, n in enumerate(names):
            trg = Track(gt[n], host_anchor(n, s), sym_axis_body(ep, s, n, 'mocap'))
            evg, vg, wg, _ = events(trg); ph, mvg = physical(evg, vg, wg)
            evg.update(ph); true_ev[n] = (evg, mvg)
            row = dict(mocap=evg, static=evg['on_move'] is None, lags={}, edge_lags={}, src={})
            for k, v in src.items():
                M = v['poses'][n]
                if len(M) != T:
                    row['src'][k] = dict(error=f'{len(M)} frames vs {T}'); continue
                tro = Track(M, v['anchor'][s], sym_axis_body(ep, s, n, v['lib']))
                evo, vo, wo, _ = events(tro)
                row['src'][k] = {kk: vv for kk, vv in evo.items()}
                lg = {}
                for key in ('on_p1', 'on_p2', 'on_r', 'on_move', 'off_p1', 'off_p2', 'off_r', 'off_move'):
                    if evg.get(key) is not None and evo.get(key) is not None:
                        lg[key] = int(evo[key] - evg[key])
                for key in ('on_p1_f', 'on_p2_f', 'on_r_f', 'off_p1_f', 'off_p2_f', 'off_r_f'):
                    if evg.get(key) is not None and evo.get(key) is not None:
                        lg[key] = round(float(evo[key] - evg[key]), 3)
                row['lags'][k] = lg
                row['edge_lags'][k] = dict(starts=match_edges(evg['v_starts'], evo['v_starts']),
                                           ends=match_edges(evg['v_ends'], evo['v_ends']))
            R['obj'][n] = row
        # ---------------- hands
        hand_src = {}
        fin, pre, _ = ref_files(e)
        if fin:
            if pre:
                hand_src['pre'] = (pre, REF_LIB[ep])
            hand_src['ref'] = (fin, REF_LIB[ep])
            if gtf:
                hand_src['glockt'] = (gtf, REF_LIB[ep])
        else:
            sf = sorted(glob.glob(f"{STORE}/{STALE.format(ep)}/processed/*/*/*.parquet"))
            if sf:
                hand_src['stale'] = (sf[0], 'scan')
        R['hands'] = {}
        for hk, (path, lib) in hand_src.items():
            hn, obj, H = load_hands(path)
            own = {}
            if hk in src:
                for n in names:
                    own[n] = (src[hk]['poses'][n], None)
            hrow = {}
            for s, n in enumerate(hn):
                tree = surface_tree(mesh_for(lib, n))
                evg, mvg = true_ev[n]
                tro = Track(obj[n], our_anchor(ep, s, n, lib), sym_axis_body(ep, s, n, lib))
                evo, _, _, _ = events(tro)
                dist = {sd: dict(robot=hand_dist(H[sd]['robot'], obj[n], tree), human=hand_dist(H[sd]['human'], obj[n], tree))
                        for sd in ('right', 'left')}
                o = dict(own_on=evo['on_move'], own_off=evo['off_move'], true_on=evg.get('on_phys'), true_off=evg.get('off_phys'),
                         min_robot_dist_cm={sd: round(float(dist[sd]['robot'].min()), 2) for sd in dist})
                masks = {}
                for th in CONTACT_TH:
                    masks[f'robot<{th:g}cm'] = (dist['right']['robot'] < th) | (dist['left']['robot'] < th)
                    for sd in ('right', 'left'):
                        masks[f'robot_{sd}<{th:g}cm'] = dist[sd]['robot'] < th
                masks[f'human<{HUMAN_TH:g}cm'] = (dist['right']['human'] < HUMAN_TH) | (dist['left']['human'] < HUMAN_TH)
                masks['labels'] = (H['right']['pid'] == s + 1).any(1) | (H['left']['pid'] == s + 1).any(1)
                for mk, m in masks.items():
                    o[mk] = contact_events(m, evg.get('on_phys'), evg.get('off_phys'), evo['on_move'], evo['off_move'], mvg)
                hrow[n] = o
            R['hands'][hk] = hrow
        # ---------------- grasp-lock plan
        if gtf:
            d = os.path.dirname(gtf).replace('/glockt/', '/glock/')
            fr = lambda f: np.array(pq.read_table(f, columns=['robot_right_frames']).column(0)[0].as_py(), float)[..., :3]
            G0 = fr(gtf); best = None
            for stem in ('ref_gl', 'ref_gl_r1'):
                f = f'{d}/{stem}_ilc.parquet'
                if os.path.exists(f) and os.path.exists(f'{d}/{stem}_grasp_lock.json'):
                    dd = float(np.abs(fr(f) - G0).max())
                    if best is None or dd < best[0]:
                        best = (dd, stem)
            if best:
                J = json.load(open(f'{d}/{best[1]}_grasp_lock.json'))
                plan = []
                for ph in J.get('phases', []):
                    n = ph['object']; evg = true_ev[n][0]
                    x = {k: ph.get(k) for k in ('hand', 'object', 'start', 'end', 'contact_end', 'hold_from', 'grasp_frame', 'move_frame')}
                    x['onset_anchor'] = (ph.get('onset_anchor') or {}).get('onset')
                    x['approach_from'] = (ph.get('approach') or {}).get('from_frame')
                    x['replan'] = ph.get('replan') is not None
                    if evg.get('on_phys') is not None:
                        x['hold_from_minus_true_onset'] = int(ph['hold_from'] - evg['on_phys'])
                        x['end_minus_true_offset'] = int(ph['end'] - evg['off_phys'])
                    plan.append(x)
                R['grasp_lock_plan'] = dict(json=f'{d}/{best[1]}_grasp_lock.json'[len(STORE) + 1:], robot_frames_max_diff_m=round(best[0], 6),
                                            phases=plan, single_hand=J.get('args', {}).get('single_hand'),
                                            onset_anchor_arg=J.get('args', {}).get('onset_anchor'), close=J.get('args', {}).get('close'))
        # ---------------- mkref hand bookkeeping
        rs = None
        if fin:
            rs = f"{STORE}/{e['ref_path']}/ref_summary.json"
        elif os.path.exists(f"{STORE}/{STALE.format(ep)}/ref_summary.json"):
            rs = f"{STORE}/{STALE.format(ep)}/ref_summary.json"
        if rs and os.path.exists(rs):
            hs = json.load(open(rs)).get('hands', {})
            book = {}
            for sd, h in hs.items():
                fills = []
                seen = set()
                for f in h.get('fills', []):
                    s0, e0 = int(f[0]), int(f[1])
                    if (s0, e0) in seen:
                        continue
                    seen.add((s0, e0))
                    anchors = sorted({int(g[3]) for g in h['fills'] if int(g[0]) == s0 and g[3] is not None})
                    ov = {}
                    for n in names:
                        evg = true_ev[n][0]
                        if evg.get('on_phys') is not None:
                            ov[n] = int(max(0, min(e0, evg['off_phys'] + 1) - max(s0, evg['on_phys'])))
                    fills.append(dict(start=s0, end_excl=e0, frames=e0 - s0, attach_bodies=[names[a] for a in anchors],
                                      overlap_true_motion_frames=ov))
                sep = h.get('separation', {})
                book[sd] = dict(mode=h.get('mode'), valid_frames=h.get('valid_frames'), first_valid=sep.get('first_valid'),
                                lead_in_to=sep.get('lead_in'), lead_in_cm=sep.get('lead_in_cm'), fills=fills)
            # the hand track mkref read (raw_motion_file 'poses|hands'): measured / tracker-filled / invalid frames
            rp = pre if (fin and pre) else (fin if fin else None)
            if rp is None:
                sf = sorted(glob.glob(f"{STORE}/{STALE.format(ep)}/processed/*/*/*.parquet")); rp = sf[0] if sf else None
            hn_file = None
            if rp:
                raw = pq.read_table(rp, columns=['raw_motion_file']).column(0)[0].as_py()
                cand = os.path.join(os.path.dirname(rs), os.path.basename(raw.split('|')[-1]))
                hn_file = cand if os.path.exists(cand) else None
            if hn_file:
                Hn = np.load(hn_file)
                for sd in book:
                    meas = Hn[f'measured_{sd}'].astype(bool); val = Hn[f'valid_{sd}'].astype(bool)
                    x = dict(file=hn_file[len(STORE) + 1:], measured=int(meas.sum()), tracker_filled=int((val & ~meas).sum()),
                             invalid=int((~val).sum()), per_object={})
                    for n in names:
                        evg, mvg = true_ev[n]
                        if evg.get('on_phys') is None:
                            continue
                        w = np.zeros(T, bool); w[evg['on_phys']:evg['off_phys'] + 1] = True; w &= mvg
                        x['per_object'][n] = dict(true_moving_frames=int(w.sum()), of_which_measured=int((w & meas).sum()),
                                                  tracker_filled=int((w & val & ~meas).sum()), invalid=int((w & ~val).sum()))
                    book[sd]['hand_track'] = x
            R['mkref_hands'] = dict(summary=rs[len(STORE) + 1:], sides=book)
        # ---------------- track guard (perception guard arm)
        gd = f"{STORE}/{GUARD.format(ep)}"
        if os.path.exists(f'{gd}/track_guard.json'):
            tg = json.load(open(f'{gd}/track_guard.json'))
            P = load_npz(f'{gd}/poses_world_vo.npz')
            log = open(f'{gd}/log.txt').read()
            gr = {}
            for n in names:
                reac = [int(m) for m in re.findall(rf'track guard {re.escape(n)} f(\d+): re-acquired', log)]
                M = P[n]; same = np.where(np.abs(M[1:] - M[:-1]).max((1, 2)) < 1e-9)[0] + 1
                gr[n] = dict(counts=tg.get(n), reacquired_frames=reac, held_frames=same.tolist(),
                             true_moving_at_held=[bool(true_ev[n][1][t]) for t in same.tolist()])
            R['guard'] = gr
        res[ep] = R
        print(ep, {n: (R['obj'][n]['mocap']['on_phys'], R['obj'][n]['mocap']['off_phys'], R['obj'][n]['lags'].get('ref', R['obj'][n]['lags'].get('perc'))) for n in names}, flush=True)
        json.dump(res, open(out_path, 'w'), indent=1, default=int)


if __name__ == '__main__':
    main()
