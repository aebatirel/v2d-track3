"""Is a relative vertical error in the kit-aligned frame a table/height error or a tilt of the alignment?
(refcheck/verify_chain, 27 Oct 2026; DIAGNOSTIC: reads public mocap after inference.)

For a canonical episode, at frame 0, in scan mode (public scans as the candidate meshes, so our mesh frame is taken as
the scan frame, as in the chain's 'scan' scores):
  Ral          = the kit's scene rotation (from the first object without a symmetry axis, else slot 0's axis + the
                 direction to slot 1), re-derived here with rotation matrices;
  tilt_deg     = angle between Ral @ n (mkref's fitted table normal, perception world) and mocap +z (the mocap table is
                 level: scan bottoms of resting objects agree within ~0.3 cm across all public episodes, geom.json);
  lever_dz_cm  = vertical displacement that this tilt alone gives object i relative to slot 0 in the aligned frame,
                 ((Ral @ (p_i - p_0)) . z  -  (Ral_level @ (p_i - p_0)) . z), Ral_level = Ral corrected to level;
  bottoms      = lowest point of the PUBLIC SCAN at the perceived pose above mkref's plane (n.x + d), vs the scan's
                 lowest point above the mocap table at the mocap pose (table = 0.6010 m, the median on-table pot bottom);
                 and the same with OUR mesh (library), which is what mkref measured.
Usage: python -I tilt.py EP PERC.npz TABLE_FRAME.npz LIBDIR OUT.json
"""
import json, os, sys
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
KIT = f'{SP}/kit/v2d_submission_kit'; T3 = f'{SP}/t3'
sys.path.insert(0, KIT)
from v2dlb.mesh_budget import budget_mesh
from v2dlb.track3_pose import _register_object_body
from v2dlb.mesh_common import _sample_mesh_surface

ep, perc, tfp, lib, out = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
MODE = sys.argv[6] if len(sys.argv) > 6 else 'scan'   # scan: public scans as candidates; lib: our meshes (registration applied)
SYM = {'blue_cup': 360, 'beige_cup': 360, 'white_pot_lid': 2}
TABLE = 0.6010
objs = pq.read_table(f'{T3}/ep{ep}.parquet', columns=['observation.objects']).column(0)[0].as_py()
names = [o['name'] for o in objs]; B = len(names)
P = np.load(perc); tf = np.load(tfp); n_pl, d_pl = tf['plane_n'], float(tf['plane_d'])
res = dict(ep=ep, names=names, mode=MODE)
gp, gr, ap, ar, axes, scanV, libV, anch = [], [], [], [], [], [], [], []
for s, n in enumerate(names):
    q = f'{T3}/mesh/{n}/{n}.glb'; q = q if os.path.exists(q) else f'{T3}/mesh/{n}/{n}_visual.glb'
    m = trimesh.load(q, force='mesh'); v, f = np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)
    tri = v[f]; a = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    c = (tri.mean(1) * a[:, None]).sum(0) / a.sum(); anch.append(c)
    X = _sample_mesh_surface(v, f, 1000, 7 + s) - c
    ax = np.zeros(3)
    if n in SYM:
        w, U = np.linalg.eigh(np.cov(X.T)); k = 0 if SYM[n] == 2 else int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)]))
        ax = U[:, k]
    axes.append(ax); scanV.append(v); libV.append(np.asarray(trimesh.load(f'{lib}/{n}.glb', force='mesh').vertices, float))
    ca, Rb = _register_object_body(budget_mesh(q if MODE == 'scan' else f'{lib}/{n}.glb', 4096, 4096), (v, f), c, 1_000_003 * ep + 101 * s)
    po = np.asarray(objs[s]['pose'], float); Rg = Rot.from_quat([po[4], po[5], po[6], po[3]]).as_matrix()
    gp.append(po[:3] + Rg @ c); gr.append(Rg)
    M = P[n][0]; ap.append(M[:3, 3] + M[:3, :3] @ ca); ar.append(M[:3, :3] @ Rb.T)
    # bottoms
    Vp = (scanV[s] - c) @ ar[-1].T + ap[-1]; Vl = libV[s] @ M[:3, :3].T + M[:3, 3]; Vg = scanV[s] @ Rg.T + po[:3]
    res.setdefault('bottoms_cm', {})[n] = dict(scan_at_perc_above_mkref_plane=round(float((Vp @ n_pl + d_pl).min() * 100), 2),
                                             ours_at_perc_above_mkref_plane=round(float((Vl @ n_pl + d_pl).min() * 100), 2),
                                             scan_at_mocap_above_table=round(float((Vg[:, 2].min() - TABLE) * 100), 2))
fixed = [s for s in range(B) if not np.any(axes[s])]
if fixed or B == 1:
    k = fixed[0] if fixed else 0; Ral = gr[k] @ ar[k].T; res['rotation_anchor'] = names[k]
else:
    def basis(ax, d):
        p = d - ax * (ax @ d); p /= np.linalg.norm(p); return np.column_stack((p, np.cross(ax, p), ax))
    Ral = basis(gr[0] @ axes[0], gp[1] - gp[0]) @ basis(ar[0] @ axes[0], ap[1] - ap[0]).T; res['rotation_anchor'] = 'axis+direction'
nz = Ral @ n_pl
res['tilt_deg'] = round(float(np.degrees(np.arccos(np.clip(nz[2], -1, 1)))), 3)
fix = Rot.align_vectors([[0, 0, 1]], [nz])[0].as_matrix()                  # minimal rotation taking Ral n to +z
Rlev = fix @ Ral
res['lever_dz_cm'] = {}; res['aligned_dz_err_cm'] = {}; res['levelled_dz_err_cm'] = {}
off = gp[0] - Ral @ ap[0]; offl = gp[0] - Rlev @ ap[0]
for s, n in enumerate(names):
    d = ap[s] - ap[0]
    res['lever_dz_cm'][n] = round(float(((Ral @ d)[2] - (Rlev @ d)[2]) * 100), 2)
    res['aligned_dz_err_cm'][n] = round(float(((Ral @ ap[s] + off)[2] - gp[s][2]) * 100), 2)
    res['levelled_dz_err_cm'][n] = round(float(((Rlev @ ap[s] + offl)[2] - gp[s][2]) * 100), 2)
    res.setdefault('dist_to_slot0_cm', {})[n] = round(float(np.linalg.norm(d) * 100), 1)
# perception's own tilt of every non-symmetric object vs the mocap (after the levelled alignment), deg
res['frame0_orientation_err_after_levelled_alignment_deg'] = {
    n: round(float(np.degrees(Rot.from_matrix((Rlev @ ar[s]).T @ gr[s]).magnitude())), 2) if not np.any(axes[s]) else
    round(float(np.degrees(np.arccos(np.clip(abs((Rlev @ ar[s] @ axes[s]) @ (gr[s] @ axes[s])), -1, 1)))), 2)
    for s, n in enumerate(names)}
res['frame0_orientation_err_after_kit_alignment_deg'] = {
    n: round(float(np.degrees(Rot.from_matrix((Ral @ ar[s]).T @ gr[s]).magnitude())), 2) if not np.any(axes[s]) else
    round(float(np.degrees(np.arccos(np.clip(abs((Ral @ ar[s] @ axes[s]) @ (gr[s] @ axes[s])), -1, 1)))), 2)
    for s, n in enumerate(names)}
res['mocap_axis_tilt_from_vertical_deg'] = {n: round(float(np.degrees(np.arccos(np.clip(abs((gr[s] @ axes[s])[2]), -1, 1)))), 2)
                                            for s, n in enumerate(names) if np.any(axes[s])}
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res, indent=1))
