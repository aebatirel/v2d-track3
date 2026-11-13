"""Block-4 POST-HOC ORACLE DIAGNOSTIC (public episodes only; mocap/scans read only to score, via rdlib as diag_fix.py):
per object, on the same frames, track error vs marker-fix error, for b/c-only fixes (frozen census fix files) and for
a+b/c fixes (cama.py), split by the number of markers in the fix (2 / >= 3). Error = mean host-point distance (cm)
after one oracle rigid fit of the BASE track to mocap (rdlib.world_fit).
Usage: python -I diag_cama.py EP:OBJ[,EP:OBJ...] OUT_JSON
"""
import json, os, sys
import numpy as np
RDLIB = '/home/user/v2d-track3/docs/analysis/rpe-decomp-20261031'
S = os.environ.get('MK_SCRATCH', '/tmp/claude-0/-home-user-v2d-track3/6190fffb-f3a1-5d0e-84bd-7370ece99c2f/scratchpad')
sys.path.insert(0, RDLIB); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdlib as L, mlib

L.load_kit(f'{S}/dl/kit/v2d_submission_kit')
rows = {}
for spec in sys.argv[1].split(','):
    ep, obj = int(spec.split(':')[0]), spec.split(':')[1]; L.guard(ep)
    t3 = f'{S}/t3'; names = L.names_of(t3, ep); s = names.index(obj)
    P = np.load(mlib.poses_path('public', ep)); W = P['world_T_cam'].astype(float)
    base = {n: W @ P[f'cam_T_{n}'].astype(float) for n in names}; T = len(base[names[0]])
    F = np.load(f'{S}/mk/scan/fix_public{ep}_{obj}.npz'); A = np.load(f'{S}/mk/cama/public{ep}_{obj}.npz')
    H = [L.host_geometry(t3, n, k) for k, n in enumerate(names)]
    REG = [L.kit_reg('/home/user/v2d-track3/meshes/library_v3', n, H[k], ep, k) for k, n in enumerate(names)]
    G = L.ref_anchor(L.mocap7(t3, ep, names, T), H)                                   # GROUND TRUTH (scoring only)
    Pb = np.stack([L.to7(base[n]) for n in names], 1); Cb = L.convert(Pb, REG); Ws = L.world_fit(Cb, G, H)
    pts = H[s]['points']; R4 = L.to4(G[:, s])
    r_ = np.einsum('tij,kj->tki', R4[:, :3, :3], pts) + R4[:, None, :3, 3]
    def err(objw):
        Pv = Pb.copy(); Pv[:, s] = L.to7(objw); C = L.convert(Pv, REG)
        A4 = np.einsum('ij,tjk->tik', Ws, L.to4(C[:, s]))
        a = np.einsum('tij,kj->tki', A4[:, :3, :3], pts) + A4[:, None, :3, 3]
        return np.linalg.norm(a - r_, axis=2).mean(1) * 100
    nF = len(F['n']); nA = len(A['n_all']); m = min(T, nF, nA)
    bc = base[obj].copy(); okb = np.zeros(T, bool)
    for t in range(m):
        if F['n'][t] >= 2 and np.all(np.isfinite(F['fix'][t])):
            bc[t] = W[t] @ F['fix'][t]; okb[t] = True
    abc = base[obj].copy(); oka = np.zeros(T, bool)
    for t in range(m):
        if A['n_all'][t] >= 2 and np.all(np.isfinite(A['poses'][t])):
            abc[t] = W[t] @ A['poses'][t]; oka[t] = True
    eb, ebc, eabc = err(base[obj]), err(bc), err(abc)
    nb = np.zeros(T, int); nb[:m] = F['n'][:m]; na = np.zeros(T, int); na[:m] = A['n_all'][:m]
    rows[spec] = dict(obj=obj, eb=eb, ebc=ebc, eabc=eabc, okb=okb, oka=oka, nb=nb, na=na)
    print(spec, 'frames b/c', int(okb.sum()), 'a+b/c', int(oka.sum()), flush=True)

def med(x):
    return round(float(np.median(x)), 2) if len(x) else None

out = {}
for obj in sorted(set(r['obj'] for r in rows.values())):
    R = [r for r in rows.values() if r['obj'] == obj]
    cat = lambda k, mask: np.concatenate([r[k][mask(r)] for r in R])
    o = {}
    for lab, mk in (('2', lambda r, key, n: r[key] & (r[n] == 2)), ('3+', lambda r, key, n: r[key] & (r[n] >= 3))):
        mb = lambda r: mk(r, 'okb', 'nb'); ma = lambda r: mk(r, 'oka', 'na')
        o[f'bc_{lab}'] = dict(frames=int(sum(mb(r).sum() for r in R)), track_cm=med(cat('eb', mb)), fix_cm=med(cat('ebc', mb)),
                              fix_better_share=round(float((cat('ebc', mb) < cat('eb', mb)).mean()), 3) if sum(mb(r).sum() for r in R) else None)
        o[f'abc_{lab}'] = dict(frames=int(sum(ma(r).sum() for r in R)), track_cm=med(cat('eb', ma)), fix_cm=med(cat('eabc', ma)),
                               fix_better_share=round(float((cat('eabc', ma) < cat('eb', ma)).mean()), 3) if sum(ma(r).sum() for r in R) else None)
    a3 = o['abc_3+']
    o['abc3_beats_track'] = bool(a3['frames'] and a3['fix_cm'] < a3['track_cm'])
    out[obj] = o
    print(obj, json.dumps(o))
out['precondition_1'] = dict(objects_beating=[k for k, v in out.items() if isinstance(v, dict) and v.get('abc3_beats_track')],
                             passes=sum(1 for v in out.values() if isinstance(v, dict) and v.get('abc3_beats_track')) >= 2)
print(json.dumps(out['precondition_1']))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
