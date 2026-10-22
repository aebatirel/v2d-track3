"""DIAGNOSTIC ONLY (public episodes, after inference): our meshes vs the public scan solid of the same object
(interact/defects/<obj>_vox.npz, 2 mm grid in the scan frame; our track body frame = scan frame, no ICP here).
Also: lowest point above our own frame-0 table plane at given frames (our tracks). fcvenv (warp).
Usage: diag_scan.py OBJ EP FRAMES(a:b) MESH [MESH...]"""
import json, sys
import numpy as np, trimesh
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact')
import vox2
SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
obj, ep, fr = sys.argv[1], sys.argv[2], sys.argv[3]; meshes = sys.argv[4:]
z = np.load(f'{SP}/interact/defects/{obj}_vox.npz'); sh = z['shape']; lo = z['lo']; pitch = float(z['pitch'])
import os
ss = f'{SP}/interact/defects/{obj}_scan_solid.npz'   # visibility-repaired scan solid (cups, pot) when present
scan = np.unpackbits(np.load(ss)['final'] if os.path.exists(ss) else z['scan'])[:int(np.prod(sh))].reshape(sh).astype(bool)
P = np.load(f'{SP}/loc/perc/ep{ep}/poses.npz'); W = P['world_T_cam']; T = P[f'cam_T_{obj}']
tabs = json.load(open(f'{SP}/interact/census/table_support.json'))['own_depth_plane']
n, c = (np.array(tabs[ep]['plane0']['n']), tabs[ep]['plane0']['c']) if ep in tabs else (np.array([0, 0, 1.0]), 0.0)
slots = json.load(open(f'{SP}/interact/defects/boards_slot.json'))
a, b = map(int, fr.split(':'))
out = {}
for mp in meshes:
    m = trimesh.load(mp, force='mesh'); m.merge_vertices()
    lo2 = np.minimum(lo, m.bounds[0] - 2 * pitch); hi2 = np.maximum(lo + sh * pitch, m.bounds[1] + 2 * pitch)
    n2 = np.ceil((hi2 - lo2) / pitch).astype(int)
    G = np.stack(np.meshgrid(*[lo2[k] + pitch * (np.arange(n2[k]) + 0.5) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    ours = vox2.SD(m, 'winding')(G) < 0
    ii = np.floor((G - lo) / pitch).astype(int); ok = np.all((ii >= 0) & (ii < sh), 1)
    sc = np.zeros(len(G), bool); sc[ok] = scan[tuple(ii[ok].T)]
    v3 = pitch ** 3 * 1e6
    V = np.asarray(m.vertices); hmin = [float(((V @ (W[t] @ T[t])[:3, :3].T + (W[t] @ T[t])[:3, 3]) @ n + c).min()) for t in range(a, b)]
    out[mp] = dict(ours_cm3=round(ours.sum() * v3, 1), scan_cm3=round(sc.sum() * v3, 1), excess_cm3=round((ours & ~sc).sum() * v3, 1),
                   missing_cm3=round((sc & ~ours).sum() * v3, 1), iou=round((ours & sc).sum() / max((ours | sc).sum(), 1), 3),
                   lowest_above_plane_cm_median=round(float(np.median(hmin)) * 100, 2) if ep in tabs else None, extents_cm=np.round(m.extents * 100, 1).tolist())
    if obj in slots:                       # scan slot box (defects/boards_slot.json), 1 mm samples
        s_ = slots[obj]; rx, ry, rz = [np.array(s_[k]) / 100 for k in ('plate_x_range_cm', 'slot_y_range_cm', 'slot_z_range_cm')]
        g = np.stack(np.meshgrid(*[np.arange(r[0] + 5e-4, r[1], 1e-3) for r in (rx, ry, rz)], indexing='ij'), -1).reshape(-1, 3)
        out[mp]['slot_filled_frac'] = round(float((vox2.SD(m, 'winding')(g) < 0).mean()), 3)
    print(mp.split('/')[-1], json.dumps(out[mp]))
