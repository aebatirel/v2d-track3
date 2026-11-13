"""ORACLE DIAGNOSTIC ep0: ceiling of a lid-on-pot seat constraint on P_o, and a GT-free seat from our meshes."""
import sys, json
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, '/home/user/v2d-track3/tools')
import xstar_fit as XF
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
LIB = '/home/user/v2d-track3/meshes/library_v3'
XF.kit(S + '/map/scoring/kit/v2d_submission_kit'); T3D = S + '/map/scoring/t3'
names, gt = XF.mocap(T3D, 0); N = len(gt[names[0]])
H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
XG = json.load(open('/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
X = {n: np.array(XG[n]['X_scan_T_lib']) for n in names}
REG_ID = [XF.reg_of_X(np.eye(4), h['anchor']) for h in H]
REG_KIT = [XF.reg_of_X(XF.kit_X(f'{LIB}/{n}.glb', H[s], 0, s)[0], H[s]['anchor']) for s, n in enumerate(names)]
R = S + '/leak/p1/oracle_roots'
Po = {n: np.load(f'{R}/Po/ep0/poses_world_vo.npz')[n].astype(float) for n in names}   # lib frames
d = np.load(f'{S}/leak/diag_ep0/out/perframe.npz')
rel = d['lid_rel_d']; onpot = rel < 1.0                                                  # mocap on-pot frames (oracle phase)
star = lambda T: {n: T[n] @ np.linalg.inv(X[n]) for n in names}
def both(T):
    a = XF.score_track(names, T, gt, H, REG_KIT); b = XF.score_track(names, star(T), gt, H, REG_ID)
    return dict(lib=a, star=b)
out = {'as_is': both(Po), 'onpot_frames_mocap': int(onpot.sum())}
# oracle ceiling: lid on-pot frames = P_o pot @ mocap lid-in-pot (lib frames via X*_geom)
L = {n: Po[n].copy() for n in names}
for i in np.nonzero(onpot)[0]:
    rel_scan = np.linalg.inv(gt['white_pot'][i]) @ gt['white_pot_lid'][i]                 # scan frames
    rel_lib = X['white_pot'] @ np.linalg.inv(X['white_pot']) @ rel_scan                   # pot_lib^-1 lid_lib = X_pot^-1... see below
    # lib pose = scan pose @ X  =>  pot_lib^-1 lid_lib = X_pot^-1 rel_scan X_lid
    rel_lib = np.linalg.inv(X['white_pot']) @ rel_scan @ X['white_pot_lid']
    L['white_pot_lid'][i] = Po['white_pot'][i] @ rel_lib
out['oracle_seat_onpot'] = both(L)
# GT-free seat from our meshes: lid axis = pot opening axis, lid centred on it, lowered to first contact with the pot rim
pot = trimesh.load(f'{LIB}/white_pot.glb', force='mesh'); lid = trimesh.load(f'{LIB}/white_pot_lid.glb', force='mesh')
def pca(m):
    P = m.sample(20000, return_index=False) if hasattr(m, 'sample') else m.vertices
    c = P.mean(0); w, U = np.linalg.eigh(np.cov((P - c).T)); return c, w, U
# P_o's own relative pose at the start rest (frames 0..40, GT-free: the perceived lid-in-pot) as the initial guess
rel0 = np.stack([np.linalg.inv(Po['white_pot'][i]) @ Po['white_pot_lid'][i] for i in range(0, 40)])
R0 = Rot.from_matrix(rel0[:, :3, :3]).mean().as_matrix(); t0 = rel0[:, :3, 3].mean(0)
# pot rim: top ring of the pot body (points within 1 cm of the max along the pot up axis, excluding the handle)
pv = pot.sample(60000); lv = lid.sample(30000)
lid_in_pot = (lv @ R0.T) + t0
# pot up axis: direction from pot centroid to lid centroid in the pot frame, snapped to the pot's smallest-variance PCA axis
cp, wp, Up = pca(pot); up = Up[:, 0]; up = up if (lid_in_pot.mean(0) - cp) @ up > 0 else -up
h_p = pv @ up; rimz = np.percentile(h_p, 99.5)
body = pv[np.abs((pv - cp) - np.outer((pv - cp) @ up, up)).max(1) < 0.13]  # crude handle exclusion (radius < 13 cm)
rim = body[(body @ up) > rimz - 0.01]
rim_c = rim.mean(0); rim_c = rim_c - up * (rim_c @ up) + up * ((cp @ up))  # axis through rim centre
# lid: its normal = its smallest-variance PCA axis, oriented to the pot up
cl, wl, Ul = pca(lid); nl = Ul[:, 0]; nl = nl if (R0 @ nl) @ up > 0 else -nl
# align lid normal to pot up (minimal rotation from the perceived R0), centre lid centroid on the rim axis
a = R0 @ nl; v = np.cross(a, up); s = np.linalg.norm(v); cth = a @ up
Rfix = np.eye(3) if s < 1e-9 else Rot.from_rotvec(v / s * np.arctan2(s, cth)).as_matrix()
Rs = Rfix @ R0
lid_c_pot = Rs @ cl
off_plane = (rim_c - lid_c_pot) - up * ((rim_c - lid_c_pot) @ up)
tree = cKDTree(body)
def penetr(tz):
    q = lv @ Rs.T + (t0 + off_plane) * 0 + 0  # placeholder
    return q
t_xy = (lid_c_pot + off_plane)  # lid centroid target in the plane
best = None
for dz in np.arange(-0.04, 0.06, 0.0005):
    t = off_plane + up * dz - lid_c_pot + lid_c_pot  # translation applied after Rs (lid centroid moves by t)
    q = lv @ Rs.T + t + (t0 - t0)
    # translation so that lid centroid = Rs cl + t sits centred over rim axis; vertical position set by dz relative to rim
    dmin = tree.query(q, k=1)[0]
    # contact: closest approach >= 1 mm and lid's lowest points above the rim's lowest inner ring
    if best is None and dmin.min() > 0.001 and (q @ up).min() > rimz - 0.03:
        best = (dz, t)
# simpler and robust: lower the lid along up from high above until it first comes within 1 mm of the pot surface
q0 = lv @ Rs.T + off_plane + (t0 @ up) * 0
dz_list = np.arange(0.15, -0.05, -0.0005); seat = None
for dz in dz_list:
    t = off_plane + up * dz
    dmin = tree.query(lv @ Rs.T + t, k=1)[0].min()
    if dmin < 0.0015:
        seat = t; break
Rel_seat = np.eye(4); Rel_seat[:3, :3] = Rs; Rel_seat[:3, 3] = seat
# compare with the perceived and the mocap relative poses (lib frames)
rel_m = np.linalg.inv(X['white_pot']) @ (np.linalg.inv(gt['white_pot'][0]) @ gt['white_pot_lid'][0]) @ X['white_pot_lid']
def dpose(A, B):
    return dict(lid_centroid_cm=np.round(((A[:3, :3] @ cl + A[:3, 3]) - (B[:3, :3] @ cl + B[:3, 3])) * 100, 2).tolist(),
                along_up_cm=round(float((((A[:3, :3] @ cl + A[:3, 3]) - (B[:3, :3] @ cl + B[:3, 3])) @ up) * 100), 2),
                rot_deg=round(float(np.degrees(Rot.from_matrix(A[:3, :3].T @ B[:3, :3]).magnitude())), 2))
rel_p = np.eye(4); rel_p[:3, :3] = R0; rel_p[:3, 3] = t0
out['seat_vs_mocap_f0(lib frames)'] = dpose(Rel_seat, rel_m)
out['perceived_vs_mocap_f0(lib frames)'] = dpose(rel_p, rel_m)
# GT-free on-pot detection: perceived lid-in-pot within 3 cm / 15 deg of the seat
relP = np.stack([np.linalg.inv(Po['white_pot'][i]) @ Po['white_pot_lid'][i] for i in range(N)])
dc = np.linalg.norm((relP[:, :3, :3] @ cl + relP[:, :3, 3]) - (Rs @ cl + seat), axis=1) * 100
dr = np.degrees(np.arccos(np.clip((relP[:, :3, :3] @ nl) @ up, -1, 1)))
det = (dc < 3) & (dr < 15)
out['gtfree_onpot_detect'] = dict(n=int(det.sum()), agree_with_mocap=int((det == onpot).sum()), false_pos=int((det & ~onpot).sum()), false_neg=int((~det & onpot).sum()))
L2 = {n: Po[n].copy() for n in names}
for i in np.nonzero(det)[0]:
    # keep the perceived spin of the lid about the axis: project the perceived relative rotation onto rotations about up
    Rp = relP[i, :3, :3]; a = Rp @ nl; v = np.cross(a, up); s = np.linalg.norm(v)
    Rf = np.eye(3) if s < 1e-9 else Rot.from_rotvec(v / s * np.arctan2(s, a @ up)).as_matrix()
    Rn = Rf @ Rp; M = np.eye(4); M[:3, :3] = Rn; M[:3, 3] = seat + Rs @ cl - Rn @ cl
    L2['white_pot_lid'][i] = Po['white_pot'][i] @ M
out['gtfree_seat'] = both(L2)
json.dump(out, open(f'{S}/leak/diag_ep0/out/seat.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
