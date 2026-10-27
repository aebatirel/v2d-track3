"""Was mkref's per-object table snap right? (refcheck/chain, 26 Oct 2026; DIAGNOSTIC: reads public mocap.)

mkref measures, at frame 0, each object's lowest point (OUR mesh at the perceived pose) above its fitted table plane
(h, mkref_log 'frame-0 object bottoms above the fitted table') and shifts objects with |h| <= 2 cm by -h along the table
normal. This script places the perceived frame-0 poses in the mocap world with the kit's own frame-0 scene alignment
(scored with the public scans, i.e. our mesh frame taken as the scan frame), and reports per object (cm):
  gt_bottom_above_table : the public scan's lowest point at the mocap pose minus the episode's table height (the
                          lowest mocap scan bottom among the episode's objects; > 1 cm = not resting on the table)
  ours_bottom_err       : our mesh's lowest point at the aligned perceived pose minus the scan's lowest point at the
                          mocap pose (perception vertical error + our-mesh bottom offset)
  mkref_h               : mkref's measured bottom above its fitted plane (from mkref_log.txt)
  plane_err             : mkref_h - (ours_bottom_err + gt_bottom_above_table): how far mkref's plane sits above the
                          mocap table at that object (relative values matter: object slot 0 is pinned by the alignment)
  needed_shift          : -(ours_bottom_err) relative to object 0 (what would put the bottoms where mocap has them),
                          vs the applied relative shift.
Usage: python -I snapcheck.py T3 KIT STORE CANONICAL.json OUT.json
"""
import json, os, re, sys
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

T3d, KIT, ST, CAN, OUT = sys.argv[1:6]
sys.path.insert(0, KIT)
from v2dlb import track3_pose as K
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments

REPO = '/home/user/v2d-track3'
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}


def scan_path(n):
    q = f'{T3d}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{T3d}/mesh/{n}/{n}_visual.glb'


def axis_of(n, v, f, slot):
    from v2dlb.mesh_common import _sample_mesh_surface
    c, _ = _surface_moments(v, f)
    pts = _sample_mesh_surface(v, f, 1000, 7 + slot) - c
    if n not in SYM:
        return c, np.zeros(3)
    w, U = np.linalg.eigh(np.cov(pts.T))
    if SYM[n] == 'half':
        return c, U[:, 0]
    k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
    return c, U[:, k]


out = {}
for e in json.load(open(CAN))['episodes']:
    if not e['ref_path']:
        continue
    ep = e['ep']; lib = f'{REPO}/meshes/library_v3x' if ep == 11 else f'{REPO}/meshes/library_v3'
    objs = pq.read_table(f'{T3d}/ep{ep}.parquet', columns=['observation.objects']).column(0)[0].as_py()
    names = [o['name'] for o in objs]; B = len(names)
    P = np.load(f"{ST}/{e['perception_path']}")
    log = open(f"{ST}/{e['ref_path']}/mkref_log.txt").read() if os.path.exists(f"{ST}/{e['ref_path']}/mkref_log.txt") else ''
    m = re.search(r"frame-0 object bottoms above the fitted table \(cm\): (\{[^}]*\})", log)
    if not m:   # mkref log of the reference this one was built from (contact retarget copies keep it in the mc dir)
        alt = {12: 'runs/20261021-auto18-966eb96/refs/perc2mc/ep12', 24: 'runs/20261021-auto24-966eb96/refs/perc2mcs/ep24',
               27: 'runs/20261021-auto18-966eb96/refs/perc2mc/ep27', 18: 'runs/20261021-auto18-966eb96/refs/perc2mc/ep18'}.get(ep)
        if alt and os.path.exists(f'{ST}/{alt}/mkref_log.txt'):
            m = re.search(r"frame-0 object bottoms above the fitted table \(cm\): (\{[^}]*\})", open(f'{ST}/{alt}/mkref_log.txt').read())
    h = json.loads(m.group(1).replace("'", '"')) if m else {}
    scans, ours, anchors, axes, REG, gt, ach = [], [], [], [], [], [], []
    for s, n in enumerate(names):
        sm = trimesh.load(scan_path(n), force='mesh'); sv, sf = np.asarray(sm.vertices, float), np.asarray(sm.faces, np.int64)
        c, ax = axis_of(n, sv, sf, s); anchors.append(c); axes.append(ax); scans.append(sv)
        ours.append(budget_mesh(f'{lib}/{n}.glb', 4096, 4096)[0])
        REG.append(K._register_object_body(budget_mesh(scan_path(n), 4096, 4096), (sv, sf), c, 1_000_003 * ep + 101 * s))
        q = np.array(objs[s]['pose'], float); gt.append(np.r_[q[:3], q[4:7], q[3]])
        M = P[n][0]; ach.append(np.r_[M[:3, 3], Rot.from_matrix(M[:3, :3]).as_quat()])
    gt = np.array(gt)[None, None]; ach = np.array(ach)[None, None]
    ref = gt.copy(); conv = ach.copy()
    for s in range(B):
        ref[..., s, :3] += Rot.from_quat(gt[0, 0, s, 3:]).apply(anchors[s])
        conv[:, :, s] = K._convert_object_body(ach[:, :, s], *REG[s])
    al = K._align_registered_scene(conv, ref, axes)
    Q = Rot.from_quat(al[0, 0, 0, 3:]) * Rot.from_quat(conv[0, 0, 0, 3:]).inv()
    o = al[0, 0, 0, :3] - Q.apply(conv[0, 0, 0, :3])
    gtb = np.array([(Rot.from_quat(gt[0, 0, s, 3:]).apply(scans[s]) + gt[0, 0, s, :3])[:, 2].min() for s in range(B)])
    table = gtb.min()
    row = {}
    for s, n in enumerate(names):
        Rp = Q * Rot.from_quat(ach[0, 0, s, 3:]); tp = Q.apply(ach[0, 0, s, :3]) + o       # aligned perceived body pose
        ob = (Rp.apply(ours[s]) + tp)[:, 2].min()
        row[n] = dict(gt_bottom_above_table_cm=round((gtb[s] - table) * 100, 2), ours_bottom_err_cm=round((ob - gtb[s]) * 100, 2),
                      mkref_h_cm=h.get(n))
    b0 = names[0]
    for n in names:
        r = row[n]
        r['needed_rel_shift_cm'] = round(-(r['ours_bottom_err_cm'] - row[b0]['ours_bottom_err_cm']), 2)
        if r['mkref_h_cm'] is not None and row[b0]['mkref_h_cm'] is not None:
            sh = lambda x: -x if abs(x) <= 2.0 else 0.0
            r['applied_rel_shift_cm'] = round(sh(r['mkref_h_cm']) - sh(row[b0]['mkref_h_cm']), 2)
            r['plane_err_cm'] = round(r['mkref_h_cm'] - (r['ours_bottom_err_cm'] + r['gt_bottom_above_table_cm']), 2)
    out[ep] = row
    print(ep, row, flush=True)
json.dump(out, open(OUT, 'w'), indent=1)
