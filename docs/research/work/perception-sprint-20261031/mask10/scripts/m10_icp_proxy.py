"""CPU mechanism proxy for option (a), masking re-track [H]: does the inner cup's depth drag the outer cup's fit upward,
and does masking it out stop that? GT-free (our depth grid, our track, our hands, our meshes; mocap is not read).
A depth-only stand-in for FoundationPose's track_one: on the depth-grid frames inside the S12 window, the outer (blue)
cup is fitted by trimmed point-to-plane ICP (pipeline/offsetfix.icp, no update about the cup axis), each frame starting
from the previous frame's result (a tracker), the first from the pre-nest pose P* (S12). The points are every valid depth
pixel in the tracker's crop (our render of the blue cup at its current pose, bounding box grown by 20 %, as
FoundationPose crops around the pose) within --band cm of the posed mesh. Three chains:
  raw      no masking (what perc2 feeds FoundationPose today)
  objmask  pixels whose front-most render is the other cup (at its tracked pose), dilated 3 px, removed (option a)
  objhand  objmask + our hand mask (offsetfix.hand_mask, 2 cm)
  raw_t, objmask_t   raw / objmask with the table removed (points within 0.8 cm above our frame-0 plane): a learned
           refiner is trained to ignore background, while point-to-plane ICP is pulled by table points near the base
An ICP update that moves the centroid by more than 3 cm in one frame is rejected (the pose is kept).
Reports the height of the blue cup's centroid along our table normal relative to P*, per frame and chain.
Usage: python -I m10_icp_proxy.py TRACK_DIR S12_POSE_OPT DEPTH_GRID_NPZ OUT_JSON [--band 3]"""
import json, sys
import numpy as np
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import refine, offsetfix as OF
import cv2

trk, popt, grid, out = sys.argv[1:5]
band = float(sys.argv[sys.argv.index('--band') + 1]) if '--band' in sys.argv else 3.0
for f in (trk, popt, grid):
    refine.assert_inference_input(f)
P = np.load(f'{trk}/poses.npz'); W = P['world_T_cam'].astype(float)
names = [k[6:] for k in P.files if k.startswith('cam_T_')]
O = {n: np.einsum('tij,tjk->tik', W, P[f'cam_T_{n}'].astype(float)) for n in names}
H = np.load(refine.checked(f'{trk}/hands_refined.npz'))
K2 = np.diag([0.5, 0.5, 1.0]) @ np.asarray(H['KR'], float)
s12 = json.load(open(popt))['steps']['S12']
n_, d_ = np.asarray(s12['plane']['n'], float), float(s12['plane']['d'])
w = [x for x in s12['windows'] if x.get('applied')][0]
jo, ji = names.index(w['outer']), names.index(w['inner'])
objs = [refine.Obj(n, f'/home/user/v2d-track3/meshes/library_v3/{n}.glb') for n in names]
for o in objs:
    OF.mesh_model(o)
ax = OF.body_axis(objs[jo])
c = objs[jo].V.mean(0)
Z = np.load(grid); frames = [int(x) for x in Z['frames']]
fr = [t for t in frames if w['start'] <= t < w.get('hold_end', w['end'])]
Pst = O[w['outer']][w['pre_frame']]
class A_: s11_hand_cm = 2.0
res = {}
for chain in ('raw', 'objmask', 'objhand', 'raw_t', 'objmask_t'):
    Tw = Pst.copy()
    rows = []
    for t in fr:
        dep = np.asarray(Z['depth'][frames.index(t)], np.float32)
        Wt = W[t]; Wi = np.linalg.inv(Wt)
        Tc = Wi @ Tw
        _, lab_self = OF.render([(0, Tc, OF.mesh_model(objs[jo])[0])], K2, dep.shape)
        v, u = np.nonzero(lab_self == 0)
        if len(v) == 0:
            rows.append(dict(f=t, points=0, skipped='not in view'))
            continue
        cy, cx = (v.min() + v.max()) / 2, (u.min() + u.max()) / 2
        hy, hx = (v.max() - v.min()) * 0.6, (u.max() - u.min()) * 0.6
        crop = np.zeros(dep.shape, bool)
        crop[max(0, int(cy - hy)):int(cy + hy) + 1, max(0, int(cx - hx)):int(cx + hx) + 1] = True
        pix = crop.copy()
        if chain in ('objmask', 'objhand', 'objmask_t'):
            _, lab = OF.render([(1, Wi @ O[w['inner']][t], OF.mesh_model(objs[ji])[0]), (0, Tc, OF.mesh_model(objs[jo])[0])], K2, dep.shape)
            m = cv2.dilate((lab == 1).astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
            pix &= ~m
        if chain == 'objhand':
            pix &= ~OF.hand_mask(H, t, Wi, K2, dep.shape, 2.0)
        cloud = OF.backproject(pix, dep, K2)
        if chain.endswith('_t') and len(cloud):
            Xw = cloud @ Wt[:3, :3].T + Wt[:3, 3]
            cloud = cloud[(Xw @ n_ + d_) > 0.008]
        from scipy.spatial import cKDTree
        Pm = OF.mesh_model(objs[jo])[0]
        Xm = Pm[::max(1, len(Pm) // 60000)] @ Tc[:3, :3].T + Tc[:3, 3]
        if len(cloud):
            cloud = cloud[cKDTree(Xm).query(cloud)[0] < band / 100]
        if len(cloud) < 150:
            rows.append(dict(f=t, points=int(len(cloud)), skipped=True))
            continue
        Ti, r0, r1 = OF.icp(Tc, cloud, OF.mesh_model(objs[jo]), 30, 0.8, ax)
        step = np.linalg.norm((Ti[:3, :3] @ c + Ti[:3, 3]) - (Tc[:3, :3] @ c + Tc[:3, 3])) * 100
        if r0 is not None and step <= 3.0:                        # a tracker step cap (as S11's 3 cm)
            Tw = Wt @ Ti
        cw = Tw[:3, :3] @ c + Tw[:3, 3]
        c0 = Pst[:3, :3] @ c + Pst[:3, 3]
        ct = O[w['outer']][t][:3, :3] @ c + O[w['outer']][t][:3, 3]
        e = cw - c0
        rows.append(dict(f=t, points=int(len(cloud)), v_cm=round(float(e @ n_ * 100), 2),
                         h_cm=round(float(np.linalg.norm(e - (e @ n_) * n_) * 100), 2),
                         track_v_cm=round(float((ct - c0) @ n_ * 100), 2),
                         res_mm=None if r1 is None else round(r1 * 1000, 2), step_cm=round(float(step), 2),
                         rejected=bool(r0 is None or step > 3.0)))
    res[chain] = rows
    vs = [r['v_cm'] for r in rows if 'v_cm' in r]
    print(chain, 'frames', len(vs), 'v (cm) median', round(float(np.median(vs)), 2), 'max', round(float(np.max(vs)), 2), 'end', vs[-1])
json.dump(dict(note='GT-free ICP proxy of the masking re-track (option a); heights relative to the S12 pre-nest pose P*.',
               window=w, band_cm=band, chains=res), open(out, 'w'), indent=1)
CH = ('raw', 'objmask', 'objhand', 'raw_t', 'objmask_t')
print('frame  track_v | ' + ' | '.join(f'{ch} v' for ch in CH))
for k in range(len(res['raw'])):
    r = [res[ch][k] for ch in CH]
    print(f"f{r[0]['f']:3d}  {r[0].get('track_v_cm', float('nan')):+5.2f} | " + ' | '.join(f"{x.get('v_cm', float('nan')):+5.2f} ({x['points']})" for x in r))
