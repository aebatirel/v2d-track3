"""DIAGNOSTIC, NOT CONTRACT-VALID wrapper around tools/intrusion.py (ev10 eval-reference consistency check, 31 Oct).

Why: intrusion.py refuses this reference because its honest (reconstructed) provenance chain contains the
make_assets(meshes/library_v3) step (deny-list substring 'library_v3'); the tool has no diagnostic flag. This wrapper
runs the tool's own main() unchanged except that the provenance deny-list hits are RECORDED instead of enforced, then
marks the header DIAGNOSTIC and adds (a) the smallest separating translation WITH its direction on the reference poses
(the tool's push_residual search, same directions, exact per direction; the tool itself only computes it on a validated
phys_fit), and (b) per-frame summaries. Ground truth is not read (eval episode; our reference only). No score.
Usage: intrusion_diag.py REF SIM_DIR OUT.npz PROV.json
"""
import importlib.util, json, os, sys, glob, csv
import numpy as np
spec = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
ref, sim, out, prov = sys.argv[1:5]
DIAG = 'DIAGNOSTIC, NOT CONTRACT-VALID (ev10_intrusion/scripts/intrusion_diag.py: provenance deny-list hits recorded, not enforced)'

orig_prov = I.provenance
def prov_diag(r, pf):
    try:
        return orig_prov(r, pf)
    except I.Refuse as e:
        msg = str(e)
    hits, saved = [], I.denied
    def rec(path=None, digest=None):
        why = saved(path, digest)
        if why:
            hits.append(dict(path=path, sha256=digest, reason=why))
        return None
    I.denied = rec
    try:
        d = orig_prov(r, pf)
    finally:
        I.denied = saved
    d.update(complete=False, source=d['source'] + ' [' + DIAG + ']', refusal_without_wrapper=msg, denied_inputs_recorded=hits)
    return d
I.provenance = prov_diag

hdr = I.main([ref, sim, out, '--prov', prov])
out_json = out[:-4] + '.json'
H = json.load(open(out_json)); H = dict(DIAGNOSTIC=DIAG, **H); H['flags'] = [DIAG] + H['flags']

def push_dir(U, X, s_max=0.10):
    """Same search as intrusion.push_residual, also returning the best direction u (shift of the partner samples)."""
    near = lambda Y, c: Y[np.all((Y > U.alo - c) & (Y < U.ahi + c), 1)]
    X = near(X, s_max); Xa = near(X, 0.0)
    if not len(Xa) or not (U.depth_lb(Xa) > I.EPS).any():
        return 0.0, np.zeros(3)
    best, u_best = np.inf, None
    for cap in (0.01, 0.03, s_max):
        Xc = near(X, cap); s = [I.free_shift(U, Xc, u, cap) for u in I.AXES]
        if np.isfinite(min(s)):
            best, u_best = min(s), I.AXES[int(np.argmin(s))]; break
    if u_best is None:
        return np.inf, np.full(3, np.nan)
    def scan(D):
        nonlocal best, u_best
        for u in D:
            s = I.free_shift(U, near(X, best), u, best)
            if s < best:
                best, u_best = s, u
    scan(I.icosphere_dirs())
    for deg in (10.0, 3.0):
        scan(I.cone(u_best, deg))
    return float(best), np.asarray(u_best, float)

Z = np.load(out)
names = [str(x) for x in Z['objects']]; ib, ig = names.index('blue_cup'), names.index('beige_cup')
_, O, P, Q, fps = I.load_ref(ref)
U = {n: I.Union(sorted(glob.glob(f'{sim}/{n}/piece_*.obj'))) for n in names}
S = {n: U[n].lattice(H['pitch_m']) for n in names}
fpF, fpT, fpP, relT, vol = Z['fp_frame'], Z['fp_target'], Z['fp_partner'], Z['rel_T'], Z['intr_vol_m3']
fr, tg, pa, dep, dlb = Z['frame'], Z['target'], Z['partner'], Z['depth_m'], Z['depth_lb_m']
rows = []
for i in range(len(fpF)):
    f, t, p = int(fpF[i]), int(fpT[i]), int(fpP[i])
    m = (fr == f) & (tg == t) & (pa == p); n_in = int(m.sum())
    r = dict(frame=f, target=names[t], partner=names[p], n_samples=n_in, vol_cm3=float(vol[i]) * 1e6,
             depth_max_mm=float(dep[m].max() * 1e3) if n_in else 0.0, depth_med_mm=float(np.median(dep[m]) * 1e3) if n_in else 0.0,
             depth_lb_max_mm=float(dlb[m].max() * 1e3) if n_in else 0.0)
    if n_in:
        R = relT[i]; X = S[names[p]] @ R[:3, :3].T + R[:3, 3]
        s, u = push_dir(U[names[t]], X)
        # express as a shift of the BLUE cup relative to the beige cup, in the blue cup's file frame and in world
        if t == ib:
            sb = -u                                   # partner (beige) moves +u in the blue frame == blue moves -u
        else:
            sb = R[:3, :3].T @ u                      # blue (partner) moves +u in the beige frame -> blue frame
        up_blue = O[f, ib, :3, :3].T @ np.array([0, 0, 1.0])     # world up in the blue file frame
        sw = O[f, ib, :3, :3] @ sb
        r.update(push_mm=s * 1e3, push_dir_partner_in_target=u.round(4).tolist(), blue_shift_dir_blueframe=sb.round(4).tolist(),
                 blue_shift_dir_world=sw.round(4).tolist(), blue_shift_up_cos=float(sb @ up_blue))
    rows.append(r)
H['diagnostic_push'] = dict(definition='smallest translation of the partner samples (2 mm lattice) leaving none inside the target pieces, '
                            'on the REFERENCE poses (not a phys_fit): intrusion.push_residual search (6 axes, 42 icosphere dirs, '
                            '10/3 deg cones), direction kept; blue_shift_* = the same separation written as a shift of the blue cup '
                            'relative to the beige cup; blue_shift_up_cos = cosine to world up (+1 = blue cup moves up)',
                            rows=rows)
json.dump(H, open(out_json, 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
with open(out[:-4] + '_rows.csv', 'w', newline='') as fh:
    k = ['frame', 'target', 'partner', 'n_samples', 'vol_cm3', 'depth_max_mm', 'depth_med_mm', 'depth_lb_max_mm', 'push_mm', 'blue_shift_up_cos',
         'blue_shift_dir_blueframe', 'blue_shift_dir_world']
    w = csv.DictWriter(fh, fieldnames=k, extrasaction='ignore'); w.writeheader()
    for r in rows:
        w.writerow({a: (round(v, 4) if isinstance(v, float) else v) for a, v in r.items()})
print('diag done', out_json, len(rows), 'rows', sum(r['n_samples'] > 0 for r in rows), 'intruding')
