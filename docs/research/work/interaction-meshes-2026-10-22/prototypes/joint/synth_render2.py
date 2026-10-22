# Synthetic testbed for the joint (multi-object) reconstruction design. Copy of interact/codemap/synth_render.py
# (slotted 9 mm box boards posed by OUR ep23 tracks + OUR ep23 table plane, ideal z-depth, every 2nd frame) with two
# outputs: the ideal depth, and a 'bled' depth where every far gap narrower than BLEED px is filled with the near depth
# (grey opening = max(min(D)) with a BLEED x BLEED kernel): the worst case of stereo interpolating across a thin slot.
# Usage: synth_render2.py W_MM BLEED_PX
import sys, numpy as np, trimesh, cv2
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from recon_mesh import rectified_K
SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
O = f'{SP}/interact/joint/synth'
import os; os.makedirs(O, exist_ok=True)
W = float(sys.argv[1]) / 1000; BL = int(sys.argv[2])
T, H, L = 0.009, 0.139, 0.227
C = {'wooden_piece_1': 0.001, 'wooden_piece_2': 0.0}
def boxes(c):
    return [((-T / 2, -H / 2, -L / 2), (T / 2, H / 2, c - W / 2)), ((-T / 2, -H / 2, c + W / 2), (T / 2, H / 2, L / 2)),
            ((-T / 2, -H / 2, c - W / 2), (T / 2, 0.0, c + W / 2))]
for n, c in C.items():
    trimesh.util.concatenate([trimesh.creation.box(bounds=np.array(b)) for b in boxes(c)]).export(f'{O}/synth_{n}_w{int(W * 1000)}.glb')
P = np.load(f'{SP}/loc/perc/ep23/poses.npz'); Wc = P['world_T_cam'][::2]; Tc = {n: P[f'cam_T_{n}'][::2] for n in C}
np.savez(f'{O}/poses_ep23_s2.npz', world_T_cam=Wc, **{f'cam_T_{n}': Tc[n] for n in C})
K = rectified_K(f'{SP}/loc/t3/calib.json'); Hh, Ww = 1000, 1600
vv, uu = np.mgrid[0:Hh, 0:Ww]
d = np.stack([(uu - K[0, 2]) / K[0, 0], (vv - K[1, 2]) / K[1, 1], np.ones_like(uu, dtype=float)], -1).reshape(-1, 3)
nW, cW = np.array([-0.075, -0.719, -0.691]), 0.531
tag = f'w{int(W * 1000)}'
out = np.lib.format.open_memmap(f'{O}/depth_{tag}.npy', 'w+', np.float32, (len(Wc), Hh, Ww))
outb = np.lib.format.open_memmap(f'{O}/depth_{tag}_bleed{BL}.npy', 'w+', np.float32, (len(Wc), Hh, Ww))
kb = np.ones((BL, BL), np.uint8)
for t in range(len(Wc)):
    z = np.full(len(d), np.inf)
    Cw = np.linalg.inv(Wc[t]); nc = Cw[:3, :3] @ nW; cc = cW - nc @ Cw[:3, 3]
    den = d @ nc; zt = -cc / np.where(np.abs(den) > 1e-9, den, np.nan); z = np.where(zt > 0, zt, z)
    for n, c in C.items():
        Ti = np.linalg.inv(Tc[n][t]); o = Ti[:3, 3]; r = d @ Ti[:3, :3].T
        for lo, hi in boxes(c):
            lo, hi = np.array(lo), np.array(hi)
            with np.errstate(divide='ignore', invalid='ignore'):
                t1 = (lo - o) / r; t2 = (hi - o) / r
            tn = np.nanmax(np.minimum(t1, t2), 1); tf = np.nanmin(np.maximum(t1, t2), 1)
            hit = (tn <= tf) & (tf > 0)
            z = np.where(hit & (tn < z), tn, z)
    z = np.where(np.isfinite(z), z, np.nan).astype(np.float32).reshape(Hh, Ww)
    out[t] = z
    zf = np.where(np.isfinite(z), z, 9.0).astype(np.float32)
    zb = cv2.dilate(cv2.erode(zf, kb), kb)                     # grey opening: thin far gaps take the near depth
    outb[t] = np.where(zb < 8.9, zb, np.nan)
out.flush(); outb.flush(); print('rendered', len(Wc), 'frames', tag, 'bleed', BL)
