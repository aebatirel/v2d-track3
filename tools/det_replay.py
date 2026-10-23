"""Offline replay of perc2's frame-k detection rules on its dumps (det_f<k>.npz; 2026-10-23). No ground truth is
read here; tools/det_score.py scores the choices on public episodes (diagnostic).

Motivation: eval ep3 (2026-10-22) gave the spoon a SAM2 proposal that was the pot's handle (a separate mask from the
pot body; 0.14 m against the 0.32 m spoon template passed the 0.3-1.3x size gate) - a general failure mode (a part of
one roster object taken for another), so the candidate rules are general and are chosen on public episodes only,
with the grid and the selection rule fixed here before any replay (owner, 2026-10-22: generalised rules are fine).

Rules (applied to the dump's stored features; R0 reproduces the pipeline's own choice):
  size   S - LAM_S * max(0, |log(extent / template extent)| - log(DZ))  (DZ = dead zone factor; 1 = none);
         extent = the proposal's 3-D extent on its full or eroded mask (EXT_SRC)
  gate   lower bound of the hard size gate (pipeline 0.3)
  merge  part-of rule: a proposal q is part of object a's chosen mask M_a when q lies >= 50 % inside M_a, or q touches
         M_a with continuous depth across the contact (median depths within 3 cm) and adding q brings M_a's 3-D extent
         closer to a's template extent; q is then barred for every other object; assignment repeats (<= 3 rounds)
  then the pipeline's compact prior (joint choice over the top-K, centroid spread beyond D0 penalised).
  verify (if the dump has it, DET_VERIFY): pipeline/perc.py's render-and-compare check; C = v + 0.5 S on the checked
         proposals with >= 200 matched pixels, others barred; plain Hungarian on C (as perc.py)
  ground LAM_G * G: Grounding DINO tiny on the colour camera a (frame k+1), prompt = the roster name with underscores
         as spaces and trailing digits dropped, top-5 boxes; G[a, j] = max over a's boxes of IoU(box, proposal j
         projected into camera a) x score / best score of that prompt; off for an object when any of its gated
         proposals is < 80 % inside camera a (critique 2026-10-22 C15)
GRID (fixed 2026-10-23 before any replay): LAM_S {0, 0.05, 0.1, 0.2} x DZ {1, 1.5} x EXT_SRC {full, eroded} x gate
{0.3, 0.5} x merge {off, on} x verify {off, on} x LAM_G {0, 0.1, 0.2, 0.4}.
SELECTION (fixed before replay): among variants with no regression (no public instance that R0 gets right turns
wrong), the most hits; ties go to the simplest (merge off, gate 0.3, smallest LAM_S, DZ 1, full extent). Ship only if
it beats R0 or equals it with more margin on the decoy check (spoon prompt on public pot/pitcher frames).

Usage: det_replay.py DUMPROOT OUT.json [LABDIR] [--g GDINO.json --t3 T3]   (DUMPROOT/ep<N>/det_f<k>.npz; with
       LABDIR: scores every variant; --g adds the grounding term, --t3 gives calib.json)
"""
import itertools, json, os, sys, glob
import numpy as np, cv2
from scipy.optimize import linear_sum_assignment

GRID = dict(lam_s=[0.0, 0.05, 0.1, 0.2], dz=[1.0, 1.5], ext_src=['full', 'eroded'], gate=[0.3, 0.5], merge=[False, True],
            verify=[False, True], lam_g=[0.0, 0.1, 0.2, 0.4])


def unpack(d):
    shp = tuple(d['mask_shape']); return np.unpackbits(d['masks'], axis=-1)[..., :shp[2]].astype(bool)


class Frame:
    def __init__(self, path):
        d = np.load(path); self.path = path
        self.names = [str(x) for x in d['names']]; self.masks = unpack(d)
        self.sim, self.score0, self.pint = d['sim'], d['score'], d['intensity']
        self.ext = {'full': d['extent'], 'eroded': d['extent_eroded']}
        self.cen, self.tint, self.text = d['centroid'], d['template_intensity'], d['template_extent']
        self.chosen0 = d['chosen']; self.depth = d['depth'].astype(np.float32); self.K = d['K'].copy()
        self.lam_i, self.K_top, self.D0, self.lam_d, self.compact = d['params'].tolist()
        self.Kh = self.K.copy(); self.Kh[:2] *= 0.5
        self.V = d['verify'] if 'verify' in d.files else None; self.Vm = d['verify_matched'] if 'verify_matched' in d.files else None
        self.G = None                                            # (n_obj, n_props) grounding agreement, set by ground()

    def ground(self, gdet, cam):
        """Grounding term from camera-a boxes (gdet: {name: {boxes, scores}}); cam: projection helper."""
        P = len(self.masks); self.G = np.zeros((len(self.names), P)); inside = np.zeros(P); bb = np.zeros((P, 4))
        fx, cx, cy = self.Kh[0, 0], self.Kh[0, 2], self.Kh[1, 2]
        for j, m in enumerate(self.masks):
            v, u = np.nonzero(m & (self.depth > 0))
            if len(v) < 20: continue
            sel = np.linspace(0, len(v) - 1, min(len(v), 400)).astype(int); v, u = v[sel], u[sel]; z = self.depth[v, u]
            X = np.stack([(u - cx) * z / fx, (v - cy) * z / fx, z], 1)
            uv, ok = cam(X); inside[j] = ok.mean()
            if ok.sum() >= 10: bb[j] = [*uv[ok].min(0), *uv[ok].max(0)]
        self.g_inside = inside
        for a, n in enumerate(self.names):
            g = gdet.get(n)
            if not g or not g['scores']: continue
            best = max(g['scores'])
            for box, sc in zip(g['boxes'], g['scores']):
                ix = np.clip(np.minimum(bb[:, 2], box[2]) - np.maximum(bb[:, 0], box[0]), 0, None)
                iy = np.clip(np.minimum(bb[:, 3], box[3]) - np.maximum(bb[:, 1], box[1]), 0, None)
                inter = ix * iy; uni = (bb[:, 2] - bb[:, 0]) * (bb[:, 3] - bb[:, 1]) + (box[2] - box[0]) * (box[3] - box[1]) - inter
                self.G[a] = np.maximum(self.G[a], np.where(uni > 0, inter / np.maximum(uni, 1e-9), 0) * sc / best)

    def extent_mask(self, m):
        """3-D extent of a half-resolution mask (as perc2's extent3d, on the half-resolution depth)."""
        v, u = np.nonzero(m & (self.depth > 0))
        if len(v) < 30: return 0.0
        z = self.depth[v, u]; fx, cx, cy = self.Kh[0, 0], self.Kh[0, 2], self.Kh[1, 2]
        X = np.stack([(u - cx) * z / fx, (v - cy) * z / fx, z], 1); X = X[::max(1, len(X) // 5000)]; X = X - np.median(X, 0)
        pr = X @ np.linalg.svd(X, full_matrices=False)[2].T
        return float((np.percentile(pr, 97, 0) - np.percentile(pr, 3, 0)).max())

    def scores(self, lam_s, dz, ext_src, gate, lam_g=0.0):
        pext = self.ext[ext_src]; S = np.full(self.sim.shape, -10.0)
        for a in range(len(self.names)):
            e = self.text[a]; ok = (self.ext['full'] > gate * e) & (self.ext['full'] < 1.3 * e)   # hard gate as perc2
            pen = lam_s * np.maximum(0.0, np.abs(np.log(np.maximum(pext, 1e-3) / e)) - np.log(dz))
            g = 0.0
            if lam_g > 0 and self.G is not None and (self.g_inside[ok] >= 0.8).all():
                g = lam_g * self.G[a]
            S[a] = np.where(ok, self.sim[a] - self.lam_i * np.abs(self.pint - self.tint[a]) / 255 - pen + g, -10.0)
        return S

    def assign(self, S):
        ri, ci = linear_sum_assignment(-S)
        if self.compact and len(self.names) > 1:
            top = [list(np.argsort(-S[a])[:int(self.K_top)]) for a in range(len(self.names))]
            best = None
            for combo in itertools.product(*top):
                if len(set(combo)) < len(combo) or any(S[a, k] <= -10 for a, k in enumerate(combo)): continue
                P_ = self.cen[list(combo)]; spread = 0.0
                if np.isfinite(P_).all():
                    spread = max(np.linalg.norm(P_[i] - P_[j]) for i in range(len(P_)) for j in range(i + 1, len(P_)))
                cost = -sum(S[a, k] for a, k in enumerate(combo)) + self.lam_d * max(0.0, spread - self.D0)
                if best is None or cost < best[0]: best = (cost, combo)
            if best is not None:
                ri, ci = np.arange(len(self.names)), np.array(best[1])
        ch = np.full(len(self.names), -1); ch[ri] = ci; return ch

    def part_of(self, a, j, q):
        """Is proposal q part of object a, whose chosen proposal is j?"""
        Ma, Mq = self.masks[j], self.masks[q]
        if Mq.sum() == 0: return False
        if (Ma & Mq).sum() >= 0.5 * Mq.sum(): return True
        ring_a = cv2.dilate(Ma.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        contact_q = ring_a & Mq & ~Ma
        if contact_q.sum() < 5: return False
        ring_q = cv2.dilate(Mq.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        contact_a = ring_q & Ma & ~Mq
        za, zq = self.depth[contact_a & (self.depth > 0)], self.depth[contact_q & (self.depth > 0)]
        if len(za) < 5 or len(zq) < 5 or abs(np.median(za) - np.median(zq)) > 0.03: return False
        e = self.text[a]; before = abs(np.log(max(self.extent_mask(Ma), 1e-3) / e))
        after = abs(np.log(max(self.extent_mask(Ma | Mq), 1e-3) / e))
        return after < before

    def choose(self, lam_s=0.0, dz=1.0, ext_src='full', gate=0.3, merge=False, verify=False, lam_g=0.0):
        S = self.scores(lam_s, dz, ext_src, gate, lam_g)
        if verify and self.V is not None and np.isfinite(self.V).any():
            C = np.where(np.isfinite(self.V) & (self.Vm >= 200) & (S > -10), np.nan_to_num(self.V) + 0.5 * S, -10.0)
            if (C > -10).any(axis=1).all():
                ri, ci = linear_sum_assignment(-C); ch = np.full(len(self.names), -1); ch[ri] = ci; S = np.where(C > -10, S, -10.0)
            else:
                ch = self.assign(S)
        else:
            ch = self.assign(S)
        if merge:
            # most confident choice first; a choice already confirmed this round cannot be absorbed by a later object
            # (synthetic test 2026-10-23: without this the spoon, sitting on the pot handle, absorbed the pot body)
            n = len(self.names)
            for _ in range(3):
                barred = False; protected = set()
                for a in sorted(range(n), key=lambda a: -(S[a, ch[a]] if ch[a] >= 0 else -99.0)):
                    j = ch[a]
                    if j < 0 or S[a, j] <= -10: continue                 # its choice was barred earlier this round
                    protected.add(int(j))
                    for q in np.nonzero((S > -10).any(0))[0]:
                        if q == j or int(q) in protected or all(S[b, q] <= -10 for b in range(n) if b != a): continue
                        if self.part_of(a, j, q):
                            for b in range(n):
                                if b != a and S[b, q] > -10: S[b, q] = -10; barred = True
                if not barred:
                    break
                ch = self.assign(S)
        return ch


HAVE = dict(verify=False, ground=False)


def variants():
    keys = list(GRID)
    for vals in itertools.product(*GRID.values()):
        v = dict(zip(keys, vals))
        if v['lam_s'] == 0 and (v['dz'] != 1.0 or v['ext_src'] != 'full'): continue   # no size term: dz/ext unused
        if (v['verify'] and not HAVE['verify']) or (v['lam_g'] > 0 and not HAVE['ground']): continue
        yield v


def vname(v):
    return (f"s{v['lam_s']}_dz{v['dz']}_{v['ext_src']}_g{v['gate']}_{'merge' if v['merge'] else 'nomerge'}"
            f"_{'verify' if v['verify'] else 'noverify'}_G{v['lam_g']}")


if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(__doc__)
    args = [x for x in sys.argv[1:]]; opt = {}
    for flag in ('--g', '--t3'):
        if flag in args:
            i = args.index(flag); opt[flag] = args[i + 1]; del args[i:i + 2]
    root, out = args[0], args[1]; labdir = args[2] if len(args) > 2 else None
    frames = {}
    for f in sorted(glob.glob(f'{root}/ep*/det_f*.npz')):
        key = f"{f.split('/')[-2]}_{os.path.basename(f)[4:-4]}"; frames[key] = Frame(f)
    print(len(frames), 'dumped frames')
    HAVE['verify'] = any(fr.V is not None and np.isfinite(fr.V).any() for fr in frames.values())
    if '--g' in opt:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import det_score
        _, (R1, P1, Kc, dc) = det_score.rect_K(opt['--t3'])
        C = json.load(open(f"{opt['--t3']}/calib.json"))['cameras']
        ext = lambda n: np.array(C[n]['extrinsics_to_stereo_left'], float)
        T_a_c = np.linalg.inv(ext('ego_cam_a')) @ ext('ego_cam_c')
        Ka, Da = np.array(C['ego_cam_a']['intrinsic_matrix'], float), np.array(C['ego_cam_a']['distortion_coefficients'], float)
        def cam(X):                                              # rectified-left c -> raw c (R1^T) -> camera a pixels
            Xa = (X @ R1) @ T_a_c[:3, :3].T + T_a_c[:3, 3]; ok = Xa[:, 2] > 0.05
            uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da); uv = uv.reshape(-1, 2)
            ok &= (uv[:, 0] >= 0) & (uv[:, 0] < 2028) & (uv[:, 1] >= 0) & (uv[:, 1] < 1520); return uv, ok
        G = json.load(open(opt['--g']))['jobs']
        for key, fr in frames.items():
            if key in G: fr.ground(G[key]['det'], cam)
        HAVE['ground'] = any(fr.G is not None for fr in frames.values())
    print('signals:', HAVE)
    for key, fr in frames.items():                           # sanity: stored score and choice are reproduced
        S = fr.scores(0.0, 1.0, 'full', 0.3)
        if not np.allclose(S, fr.score0, atol=1e-4) or not (fr.choose() == fr.chosen0).all():
            print('WARNING: R0 does not reproduce the pipeline on', key)
    res = {}
    for v in variants():
        res[vname(v)] = dict(params=v, choices={k: fr.choose(**v).tolist() for k, fr in frames.items()})
    if labdir:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import det_score
        import tempfile
        base = None
        for name, r in res.items():
            with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as t:
                json.dump(r['choices'], t)
            summ, rows = det_score.score(labdir, root, t.name, quiet=True); os.unlink(t.name)
            r['score'] = summ; r['rows'] = rows
            if name == vname(dict(lam_s=0.0, dz=1.0, ext_src='full', gate=0.3, merge=False, verify=False, lam_g=0.0)): base = rows
        for name, r in res.items():
            right0 = {(x['ep'], x['frame'], x['obj']) for x in base if x['hit']}
            r['regressions'] = [f"ep{x['ep']} f{x['frame']} {x['obj']}" for x in r['rows'] if x['hit'] is False and (x['ep'], x['frame'], x['obj']) in right0]
            print(f"{name:40s} hits {r['score']['hits']}/{r['score']['instances']} good {r['score']['good']} regressions {len(r['regressions'])}")
    json.dump(res, open(out, 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print('wrote', out)
