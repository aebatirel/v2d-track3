"""Diagnostic (dev, GT-free): full-resolution crop of one view's image, projected mask, SAM2 mask and final mask."""
import sys, numpy as np, cv2
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import guard, bundle as BU, gen_inputs as GI
from gmg.tools import b11_views as BV
S = guard.CFG['data']
ep, obj, k = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
BU._sigma = lambda obs, fr: (0.001, {'stub': True})
b = BU.from_obs_all(ep)
geo = GI.camera_geometry(f'{S}/data/calib.json')
H = guard.load_npz(f'{S}/data/sweep/ep{ep}/hands.npz', 'dev_hands')
D = np.load(guard.open_input(f'{S}/cache/depth/public/ep{ep}/depths_fs0.5.npy', 'depth'), mmap_mode='r')
fr, _ = BV.read_frames(f'{S}/data/store/ep{ep}_a.mp4', {k + 1})
img = fr[k + 1]
ref = GI.Sam2Refiner(f'{S}/weights/sam2.1-hiera-tiny', geo)
holder = {}
def refine(im, pos, neg, M):
    R = ref(im, pos, neg, M); holder['R'] = R; return R
v = GI.View(obj=obj, k=k, j=k + 1, mode='separated', dir=[0, 0, 1], area=0, hand_share=0, depth_share=0, partner_share=0)
F, res = GI.masks(v, b, img, geo=geo, hands=H, depth=D, refine=refine)
M = res['projected']; R = holder['R']
x0, y0, x1, y1 = GI.crop_box(M, geo, pad=0.1)
def show(m, col):
    o = img.copy(); o[m] = (0.5 * o[m] + 0.5 * np.array(col)).astype(np.uint8); return o[y0:y1, x0:x1]
row = np.concatenate([img[y0:y1, x0:x1], show(M, (255, 255, 0)), show(R, (0, 255, 255)), show(F, (0, 255, 0))], 1)
cv2.imwrite(f'{S}/gmg/b2/diag/zoom_ep{ep}_{obj}_{k}.jpg', row)
from scipy.ndimage import label
lab, n = label(F); sz = np.bincount(lab.ravel())[1:]
print('F components', n, 'sizes', sorted(sz.tolist(), reverse=True)[:12], 'M', M.sum(), 'R', R.sum(), 'F', F.sum())
