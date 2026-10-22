# DIAGNOSTICS ONLY (public scans; never a method input). Compare one of our meshes with the object's scan on the
# defects grid (2 mm): ICP from identity, parity voxelisation, excess / missing / IoU, distance bands, outside-hull,
# concavity classes by width, board slot fill and plate thickness.  Usage: evalscan.py NAME MESH [MESH ...]
import sys, json, os
import numpy as np
from scipy import ndimage
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/code')
import vox
D = f'{vox.S}/interact/defects'
SLOT = json.load(open(f'{D}/boards_slot.json'))
n = sys.argv[1]
z = np.load(f'{D}/{n}_vox.npz'); sh = tuple(z['shape']); lo = z['lo']; p = float(z['pitch'])
U = lambda a: np.unpackbits(a)[:np.prod(sh)].reshape(sh).astype(bool)  # noqa: E731
S_ = U(np.load(f'{D}/{n}_scan_solid.npz')['final']) if os.path.exists(f'{D}/{n}_scan_solid.npz') else U(np.load(f'{D}/{n}_gwn.npz')['thr0.5'])
H = np.unpackbits(np.load(f'{D}/{n}_pockets.npz')['hull'])[:np.prod(sh)].reshape(sh).astype(bool)
sc = vox.load_merged(vox.scan_path(n)); g = vox.Grid(lo, lo + np.array(sh) * p, p); g.shape = sh
cm3 = lambda M: round(float(M.sum()) * p ** 3 * 1e6, 1)  # noqa: E731
dS = ndimage.distance_transform_edt(~S_) * p
pad = int(np.ceil(0.045 / p)) + 2; Sp = np.pad(S_, pad); dSp = ndimage.distance_transform_edt(~Sp) * p
prev = Sp.copy(); bands = []
for r in (0.006, 0.010, 0.020, 0.045):
    clo = ndimage.distance_transform_edt(dSp <= r) * p > r
    bands.append((f'w<{int(2 * r * 1000)}mm', clo & ~prev)); prev = prev | clo
out = {}
for path in sys.argv[2:]:
    ou = vox.load_merged(path); T, st = vox.trimmed_icp(ou, sc); ou.apply_transform(T)
    O = vox.parity_votes(ou, g) >= 4
    E = O & ~S_; M = S_ & ~O
    Op = np.pad(O, pad)
    r = dict(vol_ours=cm3(O), vol_scan=cm3(S_), excess=cm3(E), missing=cm3(M), iou=round(float((S_ & O).sum() / (S_ | O).sum()), 3),
             excess_le4mm=cm3(E & (dS <= 0.0041)), excess_gt4mm=cm3(E & (dS > 0.0041)), excess_out_hull=cm3(E & ~H),
             conc_fill={k: round(float((b & Op).sum() / max(b.sum(), 1)), 2) for k, b in bands},
             icp_mm=round(float(np.linalg.norm(T[:3, 3]) * 1e3), 1), o2s_med_p90=[round(st["ours_to_scan_mm"]["med"], 1), round(st["ours_to_scan_mm"]["p90"], 1)], s2o_med_p90=[round(st["scan_to_ours_mm"]["med"], 1), round(st["scan_to_ours_mm"]["p90"], 1)])
    if n in SLOT:
        s = SLOT[n]; X = lo + (np.argwhere(np.ones(sh, bool)) + 0.5) * p
        X = X.reshape(sh + (3,))
        box = ((X[..., 0] >= s['plate_x_range_cm'][0] / 100) & (X[..., 0] <= s['plate_x_range_cm'][1] / 100) &
               (X[..., 1] >= s['slot_y_range_cm'][0] / 100 + 0.004) & (X[..., 1] <= s['slot_y_range_cm'][1] / 100 - 0.004) &
               (X[..., 2] >= s['slot_z_range_cm'][0] / 100 + 0.001) & (X[..., 2] <= s['slot_z_range_cm'][1] / 100 - 0.001))
        r['slot_box_cm3'] = cm3(box); r['slot_filled_frac'] = round(float((box & O).sum() / max(box.sum(), 1)), 2)
        col = S_.sum(0) > 0; th = O.sum(0)[col & (O.sum(0) > 0)] * p * 1e3
        r['plate_thickness_mm_ours_med'] = round(float(np.median(th)), 1); r['plate_thickness_mm_scan_med'] = round(float(np.median(S_.sum(0)[col]) * p * 1e3), 1)
        r['footprint_ours_cm2'] = round(float((O.sum(0) > 0).sum() * p * p * 1e4), 1); r['footprint_scan_cm2'] = round(float(col.sum() * p * p * 1e4), 1)
    out[path] = r; print(os.path.basename(os.path.dirname(path)) + '/' + os.path.basename(path), json.dumps(r), flush=True)
