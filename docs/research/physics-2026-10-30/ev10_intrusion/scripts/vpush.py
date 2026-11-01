"""DIAGNOSTIC: smallest purely vertical (world up) relative shift that separates the two cups on OUR reference poses.
  beige_up_mm   beige moves up relative to blue (= blue cup moves DOWN) until no sample of either lies inside the other
  beige_down_mm beige moves down relative to blue (= blue cup moves UP)
A (carved pieces) and B decomp pieces: exact per direction (intrusion.free_shift on the 2 mm lattices, both orders, max).
B mesh (plain library_v3 glb): winding-number SDF, shift stepped at 1 mm (beige lattice in blue, then blue lattice in beige).
Usage: vpush.py REF OUT.json"""
import sys, glob, json, importlib.util, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from collision_decomp import SignedDistance
spec = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py'); I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
ref, outp = sys.argv[1:3]
names, O, P, Q, fps = I.load_ref(ref); T = len(O); ib, ig = names.index('blue_cup'), names.index('beige_cup'); Oi = I.inv_pose(O)
REL = np.einsum('tij,tjk->tik', Oi[:, ib], O[:, ig]); RELi = I.inv_pose(REL)          # beige->blue, blue->beige
zw = np.array([0, 0, 1.0])
up_b = np.einsum('tji,j->ti', O[:, ib, :3, :3], zw); up_g = np.einsum('tji,j->ti', O[:, ig, :3, :3], zw)   # world up in each file frame
E_ = sys.argv[3] if len(sys.argv) > 3 else None
out = {}
def pieces_run(tag, sim):
    UB, UG = I.Union(sorted(glob.glob(f'{sim}/blue_cup/piece_*.obj'))), I.Union(sorted(glob.glob(f'{sim}/beige_cup/piece_*.obj')))
    SB, SG = UB.lattice(0.002), UG.lattice(0.002); rows = []
    for f in range(T):
        Xg = SG @ REL[f, :3, :3].T + REL[f, :3, 3]; Xb = SB @ RELi[f, :3, :3].T + RELi[f, :3, 3]
        if not ((UB.depth_lb(Xg) > I.EPS).any() or (UG.depth_lb(Xb) > I.EPS).any()):
            rows.append(dict(frame=f, beige_up_mm=0.0, beige_down_mm=0.0)); continue
        r = dict(frame=f)
        for key, sgn in (('beige_up_mm', 1), ('beige_down_mm', -1)):
            s1 = I.free_shift(UB, Xg, sgn * up_b[f], 0.2); s2 = I.free_shift(UG, Xb, -sgn * up_g[f], 0.2)
            r[key] = max(s1, s2) * 1e3
        rows.append(r)
    out[tag] = rows; print(tag, 'done', flush=True)
pieces_run('A_carve_ev10', sys.argv[3]); pieces_run('B_libv3_decomp', sys.argv[4])
bB = trimesh.load('/home/user/v2d-track3/meshes/library_v3/blue_cup.glb', force='mesh', process=False); bB = trimesh.Trimesh(bB.vertices, bB.faces, process=True)
gB = trimesh.load('/home/user/v2d-track3/meshes/library_v3/beige_cup.glb', force='mesh', process=False); gB = trimesh.Trimesh(gB.vertices, gB.faces, process=True)
sdB, sdG = SignedDistance(bB), SignedDistance(gB)
def lattice(m, sd, pitch=0.002):
    lo, hi = m.bounds; ax = [(np.arange(np.floor(a / pitch - .5), np.ceil(b / pitch - .5) + 1) + .5) * pitch for a, b in zip(lo, hi)]
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3); return G[sd(G, 1.0) < -1e-6]
LB, LG = lattice(bB, sdB), lattice(gB, sdG); rows = []
for f in range(T):
    Xg = LG @ REL[f, :3, :3].T + REL[f, :3, 3]; Xb = LB @ RELi[f, :3, :3].T + RELi[f, :3, 3]
    clash = lambda s, sgn: (sdB(Xg + s * sgn * up_b[f], 0.2) < -1e-6).any() or (sdG(Xb - s * sgn * up_g[f], 0.2) < -1e-6).any()
    if not clash(0.0, 1):
        rows.append(dict(frame=f, beige_up_mm=0.0, beige_down_mm=0.0)); continue
    r = dict(frame=f)
    for key, sgn in (('beige_up_mm', 1), ('beige_down_mm', -1)):
        s = next((k / 1000 for k in range(1, 201) if not clash(k / 1000, sgn)), np.inf); r[key] = s * 1e3
    rows.append(r)
out['B_libv3_mesh'] = rows
out['DIAGNOSTIC'] = __doc__
json.dump(out, open(outp, 'w'), indent=1, default=float); print('wrote', outp)
