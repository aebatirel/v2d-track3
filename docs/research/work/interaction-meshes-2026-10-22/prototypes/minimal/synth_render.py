# Synthetic-depth experiment (no ground truth used): two planter boards modelled as slotted boxes (thickness 9 mm,
# 13.9 x 22.7 cm, through-slot of width W from the slot edge to mid-height, the measured cross-halving layout) posed by
# OUR ep23 tracks, plus OUR ep23 table plane (recon log). Renders ideal z-depth (no stereo error, no hands) for every
# 2nd frame and writes a poses.npz with the same frames, so pipeline/recon_mesh.py can fuse it unchanged.
# Usage: synth_render.py W_MM [half]   (half: render at half resolution and upsample x2, nearest)
import sys, json, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from recon_mesh import rectified_K
SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
O = f'{SP}/interact/minimal/synth'
W = float(sys.argv[1]) / 1000; half = len(sys.argv) > 2 and sys.argv[2] == 'half'
T, H, L = 0.009, 0.139, 0.227
C = {'wooden_piece_1': 0.001, 'wooden_piece_2': 0.0}       # slot centre along axis 2 (from the assembled pose, our tracks)
def boxes(c):
    return [((-T / 2, -H / 2, -L / 2), (T / 2, H / 2, c - W / 2)), ((-T / 2, -H / 2, c + W / 2), (T / 2, H / 2, L / 2)),
            ((-T / 2, -H / 2, c - W / 2), (T / 2, 0.0, c + W / 2))]
def box_mesh(c):
    ms = [trimesh.creation.box(bounds=np.array(b)) for b in boxes(c)]
    m = trimesh.boolean.union(ms) if False else trimesh.util.concatenate(ms)
    return m
for n, c in C.items():   # mesh used as --others (the library build passed the other object's mesh there)
    box_mesh(c).export(f'{O}/synth_{n}_w{int(W * 1000)}.glb')
P = np.load(f'{SP}/loc/perc/ep23/poses.npz'); Wc = P['world_T_cam'][::2]; Tc = {n: P[f'cam_T_{n}'][::2] for n in C}
np.savez(f'{O}/poses_ep23_s2.npz', world_T_cam=Wc, **{f'cam_T_{n}': Tc[n] for n in C})
K = rectified_K(f'{SP}/loc/t3/calib.json'); Hh, Ww = 1000, 1600
s = 2 if half else 1
vv, uu = np.mgrid[0:Hh:s, 0:Ww:s]; uu = uu + (s - 1) / 2; vv = vv + (s - 1) / 2
d = np.stack([(uu - K[0, 2]) / K[0, 0], (vv - K[1, 2]) / K[1, 1], np.ones_like(uu)], -1).reshape(-1, 3)   # z = 1 rays
nW, cW = np.array([-0.075, -0.719, -0.691]), 0.531          # ep23 table plane in world (= frame-0 camera), recon log
out = np.lib.format.open_memmap(f'{O}/depth_w{int(W * 1000)}{"_half" if half else ""}.npy', 'w+', np.float32, (len(Wc), Hh, Ww))
for t in range(len(Wc)):
    z = np.full(len(d), np.inf)
    Cw = np.linalg.inv(Wc[t]); nc = Cw[:3, :3] @ nW; cc = cW - nc @ Cw[:3, 3]       # table plane in camera
    den = d @ nc; zt = -cc / np.where(np.abs(den) > 1e-9, den, np.nan); z = np.where(zt > 0, zt, z)
    for n, c in C.items():
        Ti = np.linalg.inv(Tc[n][t]); o = Ti[:3, 3]; r = d @ Ti[:3, :3].T            # rays in object frame (param = z)
        for lo, hi in boxes(c):
            lo, hi = np.array(lo), np.array(hi)
            with np.errstate(divide='ignore', invalid='ignore'):
                t1 = (lo - o) / r; t2 = (hi - o) / r
            tn = np.nanmax(np.minimum(t1, t2), 1); tf = np.nanmin(np.maximum(t1, t2), 1)
            hit = (tn <= tf) & (tf > 0)
            z = np.where(hit & (tn < z), tn, z)
    z = np.where(np.isfinite(z), z, np.nan).astype(np.float32).reshape(vv.shape)
    if half:
        z = np.repeat(np.repeat(z, 2, 0), 2, 1)
    out[t] = z
out.flush(); print('rendered', len(Wc), 'frames', 'half' if half else 'full', 'W', W)
