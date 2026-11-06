"""POST-HOC ORACLE DIAGNOSTIC (public episodes, after the pre-registered scoring): how accurate are the raw marker
fixes themselves, compared with our track, on the frames where a fix exists? Reads public mocap and scans through
rdlib. The poses of both are expressed in the mocap world by one oracle rigid fit of the BASE track (rdlib.world_fit),
so the comparison does not depend on the kit's frame-0 alignment. Error = mean distance of the host-scan surface
points (kit registration of our library_v3 mesh), cm.
Usage: python -I diag_fix.py EP:OBJ[,EP:OBJ...] OUT_JSON
"""
import json, os, sys
import numpy as np
RDLIB = '/home/user/v2d-track3/docs/analysis/rpe-decomp-20261031'
S = os.environ.get('MK_SCRATCH', '/tmp/claude-0/-home-user-v2d-track3/6190fffb-f3a1-5d0e-84bd-7370ece99c2f/scratchpad')
sys.path.insert(0, RDLIB); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdlib as L, mlib

L.load_kit(f'{S}/dl/kit/v2d_submission_kit')
out = {}
for spec in sys.argv[1].split(','):
    ep, obj = int(spec.split(':')[0]), spec.split(':')[1]; L.guard(ep)
    t3 = f'{S}/t3'; names = L.names_of(t3, ep); s = names.index(obj)
    P = np.load(mlib.poses_path('public', ep)); W = P['world_T_cam'].astype(float)
    base = {n: W @ P[f'cam_T_{n}'].astype(float) for n in names}
    F = np.load(f'{S}/mk/scan/fix_public{ep}_{obj}.npz'); n_ = F['n']; fx = F['fix']
    T = len(base[names[0]])
    H = [L.host_geometry(t3, n, k) for k, n in enumerate(names)]
    REG = [L.kit_reg('/home/user/v2d-track3/meshes/library_v3', n, H[k], ep, k) for k, n in enumerate(names)]
    G = L.ref_anchor(L.mocap7(t3, ep, names, T), H)                                   # GROUND TRUTH
    Pb = np.stack([L.to7(base[n]) for n in names], 1)
    fixw = base[obj].copy(); ok = np.zeros(T, bool)
    for t in range(min(T, len(n_))):
        if n_[t] >= 2 and np.all(np.isfinite(fx[t])):
            fixw[t] = W[t] @ fx[t]; ok[t] = True
    Pf = Pb.copy(); Pf[:, s] = L.to7(fixw)
    Cb, Cf = L.convert(Pb, REG), L.convert(Pf, REG)
    Ws = L.world_fit(Cb, G, H)
    pts = H[s]['points']
    def err(C):
        A = np.einsum('ij,tjk->tik', Ws, L.to4(C[:, s])); R = L.to4(G[:, s])
        a = np.einsum('tij,kj->tki', A[:, :3, :3], pts) + A[:, None, :3, 3]
        r = np.einsum('tij,kj->tki', R[:, :3, :3], pts) + R[:, None, :3, 3]
        return np.linalg.norm(a - r, axis=2).mean(1) * 100
    eb, ef = err(Cb), err(Cf)
    m3 = ok & (n_[:T] >= 3); m2 = ok & (n_[:T] == 2)
    out[spec] = dict(fix_frames=int(ok.sum()), full=int(m3.sum()),
                     base_cm_at_fix=round(float(np.median(eb[ok])), 2) if ok.any() else None,
                     fix_cm=round(float(np.median(ef[ok])), 2) if ok.any() else None,
                     base_cm_at_full=round(float(np.median(eb[m3])), 2) if m3.any() else None,
                     fix_cm_full=round(float(np.median(ef[m3])), 2) if m3.any() else None,
                     base_cm_at_2=round(float(np.median(eb[m2])), 2) if m2.any() else None,
                     fix_cm_2=round(float(np.median(ef[m2])), 2) if m2.any() else None,
                     fix_better_share=round(float((ef[ok] < eb[ok]).mean()), 3) if ok.any() else None)
    print(spec, json.dumps(out[spec]), flush=True)
json.dump(out, open(sys.argv[2], 'w'), indent=1)
