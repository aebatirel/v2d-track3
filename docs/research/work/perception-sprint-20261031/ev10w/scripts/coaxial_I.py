"""POST HOC (not in PREREG): intrusion of the beige cup after removing ONLY its relative tilt and lateral offset from the
blue lathe axis (the beige's own axis put on the blue axis, same axial position, same spin), per frame, with a carve's
pieces. Separates the track's offset/tilt from the cavity geometry. I = max of the two ordered pairs (intrusion.py
definition: 2 mm lattices of each union, > 1 um inside the other's pieces), cm3. DIAGNOSTIC, GT-free.
Usage: coaxial_I.py REF CARVE_DIR BLUE_PROFILE.npz BEIGE_PROFILE.npz FRAMES(a:b:step) OUT.json"""
import sys, glob, json, importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location('intrusion', '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w/tree/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
ref, carve, pb, pg, frs, outp = sys.argv[1:7]; a_, b_, s_ = (int(x) for x in frs.split(':'))
B, G = np.load(pb), np.load(pg); c0b, db = np.asarray(B['c0'], float), np.asarray(B['d'], float); c0g, dg = np.asarray(G['c0'], float), np.asarray(G['d'], float)
names, O, P, Q, fps = I.load_ref(ref); ib, ig = names.index('blue_cup'), names.index('beige_cup')
Oi = I.inv_pose(O); REL = np.einsum('tij,tjk->tik', Oi[:, ib], O[:, ig])
UB = I.Union(sorted(glob.glob(f'{carve}/blue_cup/piece_*.obj'))); UG = I.Union(sorted(glob.glob(f'{carve}/beige_cup/piece_*.obj')))
SB, SG = UB.lattice(0.002), UG.lattice(0.002)


def Ival(R, t):
    nb = int((UB.depth_lb(SG @ R.T + t) > I.EPS).sum()); Ri = R.T; ng = int((UG.depth_lb(SB @ Ri.T - Ri @ t) > I.EPS).sum())
    return max(nb, ng) * 8e-3


rows = []
for f in range(a_, b_ + 1, s_):
    R, t = REL[f, :3, :3], REL[f, :3, 3]
    a = R @ dg; v = np.cross(a, db); sn = np.linalg.norm(v); cs = a @ db
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    Rc = np.eye(3) + K + K @ K * ((1 - cs) / sn ** 2) if sn > 1e-12 else np.eye(3)
    p = R @ c0g + t; foot = c0b + ((p - c0b) @ db) * db
    R2 = Rc @ R; t2 = foot - R2 @ c0g
    rows.append(dict(frame=f, I_tracked=round(Ival(R, t), 3), I_coaxial=round(Ival(R2, t2), 3)))
    print(json.dumps(rows[-1]), flush=True)
summ = {}
for lab, lo, hi in (('f100-117', 100, 117), ('f118-160', 118, 160), ('f100-160', 100, 160)):
    rr = [r for r in rows if lo <= r['frame'] <= hi]
    summ[lab] = dict(frames=len(rr), coaxial_le2=int(sum(r['I_coaxial'] <= 2.0 for r in rr)), coaxial_median=float(np.median([r['I_coaxial'] for r in rr])),
                     coaxial_max=float(max(r['I_coaxial'] for r in rr)), tracked_median=float(np.median([r['I_tracked'] for r in rr])))
json.dump(dict(DIAGNOSTIC='POST HOC coaxial-projection intrusion (ev10w/scripts/coaxial_I.py); not a PREREG gate', ref=ref, carve=carve,
               summary=summ, rows=rows), open(outp, 'w'), indent=1)
print(json.dumps(summ))
