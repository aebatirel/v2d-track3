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
{0.3, 0.5} x merge {off, on} x verify {off, on} x LAM_G {0, 0.1, 0.2, 0.4}; reach {none, 1.0, 0.8} m added
2026-10-23 after the public baseline (ep11 / ep22: both objects assigned to small blobs 1.0-1.4 m away at the image
edge while the real ones sat on the table ~0.5 m away; a proposal whose 3-D centroid is farther than REACH from the
head camera is barred: objects a person manipulates are within arm's reach).
SELECTION (fixed before replay): among variants with no regression (no public instance that R0 gets right turns
wrong), the most hits; ties go to the simplest (merge off, gate 0.3, smallest LAM_S, DZ 1, full extent). Ship only if
it beats R0 or equals it with more margin on the decoy check (spoon prompt on public pot/pitcher frames).

Usage: det_replay.py DUMPROOT OUT.json [LABDIR] [--g GDINO.json --t3 T3]   (DUMPROOT/ep<N>/det_f<k>.npz; with
       LABDIR: scores every variant; --g adds the grounding term, --t3 gives calib.json)
"""
import itertools, json, os, sys, glob
import numpy as np, cv2
from scipy.optimize import linear_sum_assignment
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pipeline'))
import det_rules as R  # noqa: E402  (the rules perc2 ships)

GRID = dict(lam_s=[0.0, 0.05, 0.1, 0.2], dz=[1.0, 1.5], ext_src=['full', 'eroded'], gate=[0.3, 0.5], merge=[False, True],
            verify=[False, True], lam_g=[0.0, 0.1, 0.2, 0.4], reach=[None, 1.0, 0.8])


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
        self.reprop = d['reprop'].astype(bool) if 'reprop' in d.files else np.zeros(len(self.masks), bool)   # DET_REPROP masks

    def ground(self, gdet, cam):
        """Grounding term from camera-a boxes (gdet: {name: {boxes, scores}}); cam: projection helper."""
        self.G, self.g_inside = R.ground_scores(self.masks, self.depth, self.Kh, self.names, gdet, cam)

    def extent_mask(self, m):
        """3-D extent of a half-resolution mask (as perc2's extent3d, on the half-resolution depth)."""
        v, u = np.nonzero(m & (self.depth > 0))
        if len(v) < 30: return 0.0
        z = self.depth[v, u]; fx, cx, cy = self.Kh[0, 0], self.Kh[0, 2], self.Kh[1, 2]
        X = np.stack([(u - cx) * z / fx, (v - cy) * z / fx, z], 1); X = X[::max(1, len(X) // 5000)]; X = X - np.median(X, 0)
        pr = X @ np.linalg.svd(X, full_matrices=False)[2].T
        return float((np.percentile(pr, 97, 0) - np.percentile(pr, 3, 0)).max())

    def scores(self, lam_s, dz, ext_src, gate, lam_g=0.0, reach=None, reprop=True):
        pext = self.ext[ext_src]; S = np.full(self.sim.shape, -10.0); near = R.reach_ok(self.cen, reach)
        if not reprop:                                           # as a run without DET_REPROP: those masks never existed
            near = near & ~self.reprop
        oks = []
        for a in range(len(self.names)):
            e = self.text[a]; ok = (self.ext['full'] > gate * e) & (self.ext['full'] < 1.3 * e) & near   # hard gate as perc2
            S[a] = np.where(ok, self.sim[a] - self.lam_i * np.abs(self.pint - self.tint[a]) / 255 - R.size_penalty(pext, e, lam_s, dz), -10.0)
            oks.append(ok)
        if lam_g > 0 and self.G is not None:
            S = np.where(S > -10, S + R.ground_term(self.G, self.g_inside, oks, lam_g), S)
        return S

    def assign(self, S):
        ri, ci = linear_sum_assignment(-S)
        if self.compact and len(self.names) == 2:              # vectorised form of the loop below (same choice)
            K = int(self.K_top); t0, t1 = np.argsort(-S[0])[:K], np.argsort(-S[1])[:K]
            P0, P1 = self.cen[t0], self.cen[t1]
            spread = np.linalg.norm(P0[:, None] - P1[None], axis=2)
            spread = np.where(np.isfinite(spread), spread, 0.0)
            cost = -(S[0, t0][:, None] + S[1, t1][None]) + self.lam_d * np.maximum(0.0, spread - self.D0)
            bad = (t0[:, None] == t1[None]) | (S[0, t0][:, None] <= -10) | (S[1, t1][None] <= -10)
            cost = np.where(bad, np.inf, cost)
            if np.isfinite(cost).any():
                i, j = np.unravel_index(np.argmin(cost), cost.shape)
                ri, ci = np.arange(2), np.array([t0[i], t1[j]])
        elif self.compact and len(self.names) > 2:
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
        """Is proposal q part of object a, whose chosen proposal is j? (cached: independent of the rule variant)"""
        key = (int(a), int(j), int(q)); cache = self.__dict__.setdefault('_part_cache', {})
        if key not in cache:
            cache[key] = self._part_of(a, j, q)
        return cache[key]

    def _part_of(self, a, j, q):
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

    def choose(self, lam_s=0.0, dz=1.0, ext_src='full', gate=0.3, merge=False, verify=False, lam_g=0.0, reach=None, reprop=True):
        S = self.scores(lam_s, dz, ext_src, gate, lam_g, reach, reprop)
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
            f"_{'verify' if v['verify'] else 'noverify'}_G{v['lam_g']}_reach{v['reach']}")


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
        _, (R1, P1, Kc, dc) = det_score.rect_K(opt['--t3']); cam = R.make_cam(f"{opt['--t3']}/calib.json", R1)
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
    if labdir:                                                    # diagnostic scoring (public): per-proposal truth once
        meta = json.load(open(f'{labdir}/labels_meta.json')); truth = {}
        for key, fr in frames.items():
            ep, k = key.split('_'); m = meta.get(ep[2:])
            lf = f'{labdir}/{key}_lab.npy'
            if m is None or m['fit_resid_cm_median'] > 2.0 or not os.path.exists(lf): continue
            lab = np.load(lf); area = fr.masks.reshape(len(fr.masks), -1).sum(1)
            for a in range(len(fr.names)):
                vis = int((lab == a + 1).sum())
                if vis < 50: continue
                inter = (fr.masks & (lab == a + 1)[None]).reshape(len(fr.masks), -1).sum(1)
                truth[(key, a)] = inter / np.maximum(area, 1) >= 0.5          # hit = purity >= 0.5
        base_key = vname(dict(lam_s=0.0, dz=1.0, ext_src='full', gate=0.3, merge=False, verify=False, lam_g=0.0, reach=None))
        for name, r in res.items():
            hits = {kk: (r['choices'][kk[0]][kk[1]] >= 0 and bool(t[r['choices'][kk[0]][kk[1]]])) for kk, t in truth.items()}
            r['hits'] = hits; r['n_hits'] = sum(hits.values())
            r['n_hits_f0'] = sum(v for kk, v in hits.items() if kk[0].endswith('_f0'))
        base = res[base_key]['hits']; n0 = sum(1 for kk in truth if kk[0].endswith('_f0'))
        for name, r in res.items():
            r['regressions'] = [f'{kk[0]} {frames[kk[0]].names[kk[1]]}' for kk, v in r['hits'].items() if base[kk] and not v]
            r['fixed'] = [f'{kk[0]} {frames[kk[0]].names[kk[1]]}' for kk, v in r['hits'].items() if v and not base[kk]]
        order = sorted(res, key=lambda nm: (-res[nm]['n_hits'], len(res[nm]['regressions'])))
        print(f'{len(truth)} scored instances ({n0} at frame 0); baseline {res[base_key]["n_hits"]} hits ({res[base_key]["n_hits_f0"]} at frame 0)')
        for nm in order[:25]:
            r = res[nm]; print(f"{nm:62s} hits {r['n_hits']:3d} f0 {r['n_hits_f0']:2d} fixed {len(r['fixed']):2d} regressions {len(r['regressions'])}")
        for r in res.values():
            r['hits'] = {f'{kk[0]}#{kk[1]}': v for kk, v in r['hits'].items()}
    json.dump(res, open(out, 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print('wrote', out)
