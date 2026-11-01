"""GT-FREE QA image: the pixel sets S11 uses on one public frame (our depth, our tracks, our hands, our meshes).
Colours on the half-res depth image: object j's used pixels green, other objects' front pixels blue, our hand mask red.
Usage: python -I qa_pixels.py IN_DIR DEPTH_GRID_NPZ FRAME OBJ OUT.png [DET_F0 for frame 0 det mask]"""
import sys, types
import numpy as np, cv2
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import refine, offsetfix as OF  # noqa: E402
inp, grid, t, obj, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
for p in (inp, grid):
    refine.assert_inference_input(p)
P = np.load(f'{inp}/poses.npz'); W = P['world_T_cam'].astype(float)
names = [k[6:] for k in P.files if k.startswith('cam_T_')]
O = [np.einsum('tij,tjk->tik', W, P[f'cam_T_{n}'].astype(float)) for n in names]
objs = [refine.Obj(n, f'/home/user/v2d-track3/meshes/library_v3/{n}.glb') for n in names]
H = np.load(f'{inp}/hands_refined.npz', allow_pickle=True)
K2 = np.diag([0.5, 0.5, 1.0]) @ H['KR']
a = types.SimpleNamespace(s11_hand_cm=2.0, s11_dil=2)
ds = OF.DepthSource(grid, len(W), np.load(f'{inp}/depth0.npy'))
dep = ds.get(t)
ctx = OF.frame_context(t, objs, O, W[t], dep.shape, K2, H, a)
j = names.index(obj); lab = ctx['lab']
own = cv2.dilate((lab == j).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
if len(sys.argv) > 6:                                                 # f0 mode: the chosen det_f0 mask instead
    refine.assert_inference_input(sys.argv[6])
    det = np.load(sys.argv[6], allow_pickle=True); dn = [str(x) for x in det['names']]
    own = np.unpackbits(det['masks'], axis=-1)[:, :, :int(det['mask_shape'][2])].astype(bool)[int(det['chosen'][dn.index(obj)])]
other = (lab >= 0) & (lab != j)
use = own & ~other & ~ctx['hm'] & (dep > 0)
g = np.clip((dep - 0.3) / 1.2, 0, 1); img = (np.dstack([g, g, g]) * 200).astype(np.uint8)
img[other] = (img[other] * 0.4 + np.array([255, 0, 0]) * 0.6).astype(np.uint8)
img[ctx['hm']] = (img[ctx['hm']] * 0.4 + np.array([0, 0, 255]) * 0.6).astype(np.uint8)
img[use] = (img[use] * 0.4 + np.array([0, 255, 0]) * 0.6).astype(np.uint8)
cv2.imwrite(out, img)
print(obj, 'frame', t, 'used px', int(use.sum()), 'hand px', int(ctx['hm'].sum()), 'other px', int(other.sum()))
