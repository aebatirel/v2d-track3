# Does the carved slot survive the simulator's convex decomposition? kit budget_mesh (4096) -> CoACD with FlashCHORD's
# parameters (threshold 0.05, max_convex_hull -1, preprocess auto; interact/codemap/slot_coacd.py) -> slot volume
# covered by the union of hulls (synthetic box truth), and hull-union overlap of the two boards at the assembled frames.
import sys, json, time, numpy as np, trimesh, coacd
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/kit/v2d_submission_kit')
from v2dlb.mesh_budget import budget_mesh
coacd.set_log_level('error')
d, poses = sys.argv[1], sys.argv[2]
T, H, W = 0.009, 0.139, 0.009; C = {'wooden_piece_1': 0.001, 'wooden_piece_2': 0.0}
def halfspaces(parts):
    hs = []
    for v, f in parts:
        hm = trimesh.Trimesh(v, f, process=True).convex_hull
        hs.append((hm.face_normals, np.einsum('ij,ij->i', hm.face_normals, hm.triangles[:, 0])))
    return hs
def inside(hs, P):
    ins = np.zeros(len(P), bool)
    for s in range(0, len(P), 20000):
        Q = P[s:s + 20000]
        for A, b in hs:
            ins[s:s + 20000] |= np.all(Q @ A.T - b <= 1e-6, axis=1)
    return ins
HS, out = {}, {}
for n, c in C.items():
    vb, fb = budget_mesh(f'{d}/{n}.glb', 4096, 4096); t0 = time.time()
    parts = coacd.run_coacd(coacd.Mesh(np.asarray(vb, float), np.asarray(fb, int)), threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
    HS[n] = halfspaces(parts); rng = np.random.default_rng(0)
    P = np.c_[rng.uniform(-T / 2 * 0.9, T / 2 * 0.9, 3000), rng.uniform(0.005, H / 2 - 0.005, 3000), rng.uniform(c - W / 2 * 0.8, c + W / 2 * 0.8, 3000)]
    out[n] = dict(hulls=len(parts), sec=round(time.time() - t0, 1), slot_free_in_hulls=round(float(1 - inside(HS[n], P).mean()), 3))
# hull-union overlap at assembled frames (126..162 of the stride-2 poses): grid samples inside A's hulls -> inside B's hulls
Pz = np.load(poses); TA, TB = Pz['cam_T_wooden_piece_1'], Pz['cam_T_wooden_piece_2']
g = np.arange(-0.13, 0.13, 0.002); gx = np.arange(-0.02, 0.02, 0.002)
G = np.stack(np.meshgrid(gx, np.arange(-0.08, 0.08, 0.002), g, indexing='ij'), -1).reshape(-1, 3)
GA = G[inside(HS['wooden_piece_1'], G)]
ov = []
for t in range(126, 163, 6):
    Tm = np.linalg.inv(TB[t]) @ TA[t]; Q = GA @ Tm[:3, :3].T + Tm[:3, 3]
    ov.append(inside(HS['wooden_piece_2'], Q).sum() * 8e-3)
out['hull_overlap_assembled_cm3'] = [round(float(x), 2) for x in ov]
print(json.dumps(out))
