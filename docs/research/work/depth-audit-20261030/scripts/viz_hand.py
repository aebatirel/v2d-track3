"""Debug overlay (inference side): depth image, our rendered silhouettes, our hand mask. Usage: viz_hand.py IN_EP DEPTHK.npy f0,f1 OUT.png"""
import sys
sys.path.insert(0, '/home/user/v2d-track3/pipeline'); sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/daudit/pylib')
import numpy as np, cv2, trimesh, depth_audit as DA
inp, dp, frames, outp = sys.argv[1:5]
frames = [int(x) for x in frames.split(',')]
P = np.load(f'{inp}/poses.npz'); names = [k[6:] for k in P.files if k.startswith('cam_T_')]
W_C = P['world_T_cam'].astype(float); Hh = np.load(f'{inp}/hands_refined.npz'); K = Hh['KR'].astype(float)
hands = DA.load_hands(f'{inp}/hands_refined.npz', len(W_C))
Dk = np.load(dp)
rends = [DA.Renderer(trimesh.load(f'/home/user/v2d-track3/meshes/library_v3/{n}.glb', force='mesh'), K, 1000, 1600) for n in names]
tiles = []
for i, t in enumerate(frames):
    d = Dk[i]; img = np.clip((d - 0.25) / 0.6, 0, 1); img = (255 * (1 - img)).astype(np.uint8); img[d == 0] = 0
    rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    hm = DA.hand_mask(hands, t, np.linalg.inv(W_C[t]), K, 1000, 1600, 0.012)
    rgb[hm] = (0.5 * rgb[hm] + [0, 0, 127]).astype(np.uint8)
    for b, n in enumerate(names):
        r = rends[b].render(P[f'cam_T_{n}'][t].astype(float))
        if r is None: continue
        u0, v0, z = r; m = np.zeros((1000, 1600), np.uint8); m[v0:v0 + z.shape[0], u0:u0 + z.shape[1]] = np.isfinite(z)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(rgb, cs, -1, [(0, 255, 0), (255, 128, 0)][b], 2)
    cv2.putText(rgb, f'frame {t}', (20, 40), 0, 1.2, (255, 255, 255), 2)
    tiles.append(rgb[150:900, 300:1400])
cv2.imwrite(outp, cv2.resize(np.concatenate(tiles, 1), None, fx=0.6, fy=0.6))
