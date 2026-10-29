"""Spoon diagnosis, 2026-10-25 (owner: "carry on"; the spoon is in 10 of 20 eval episodes and its truth gap is the
largest loss, docs/analysis/eval-20261024-low-scores.md §5). GT-free: our references, our submitted spoon mesh and
the kit's own metric code; nothing reads mocap or a scan.

The kit (metric_code/track_3/AUC.py) registers our mesh to the hidden scan geometrically, then `_align_registered_scene`
rotates the whole achieved scene so that the ANCHOR object's frame-0 orientation matches the truth exactly (anchor = the
lowest slot without a symmetry axis). The spoon anchors evals 32, 33, 35, 36, 37. A frame-0 orientation error of the
anchor then rotates every later position of the scene about it.

1. Sensitivity [M, kit code]: truth := our reference with the spoon rotated in its body frame by EPS about each body
   axis for all frames (a constant orientation error of our track); achieved := our reference. Kit alignment +
   add_auc with points sampled on our spoon mesh. Also reported without the scene alignment, to separate the
   amplification from the spoon's own orientation error.
2. Plausibility at frame 0 [M]: a spoon resting on the table must rest on its convex hull in a statically stable
   facet orientation. For our reference spoon pose at the rest frames before its first motion, the angle between its
   body-frame "down" (R^T (0,0,-1)) and the nearest stable rest direction of the mesh.
Usage: python -I spoon_anchor.py KIT_DIR MESH.glb REF_ROOT [episodes...]
"""
import glob, importlib, json, os, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as R

kit, mesh_path, ref_root = sys.argv[1:4]; eps = [int(x) for x in sys.argv[4:]] or [3, 5, 6, 15, 16, 32, 33, 35, 36, 37]
sys.path.insert(0, f'{kit}/metric_code/track_3'); A = importlib.import_module('AUC')
roster = json.load(open(f'{kit}/data/track_3_evaluation_objects.json'))['episodes']
AXIAL = {'beige_cup', 'blue_cup'}; HALF = {'white_pot_lid'}
m = trimesh.load(mesh_path, force='mesh'); com = m.center_mass if m.is_watertight else m.centroid
rng = np.random.default_rng(0); P_spoon = m.sample(3000) - com                    # metric points (stand-in for the scan's)
ext = np.ptp(m.vertices, 0)

# stable resting directions of the mesh on a plane: convex hull facets whose centre-of-mass projection lies inside
hull = m.convex_hull; stable = []
for fi, n in enumerate(hull.facets_normal):
    pts = hull.vertices[np.unique(hull.faces[hull.facets[fi]])]
    d = n                                                                         # resting on this facet: its outward normal points down
    u = np.cross(n, [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0]); u /= np.linalg.norm(u); v = np.cross(n, u)
    q = np.c_[(pts - com) @ u, (pts - com) @ v]
    if len(q) < 3:
        continue
    from scipy.spatial import ConvexHull, Delaunay
    try:
        inside = Delaunay(q).find_simplex([[0.0, 0.0]])[0] >= 0
        hq = ConvexHull(q); margin = min(-(eq[:2] @ [0, 0] + eq[2]) for eq in hq.equations)
    except Exception:
        continue
    if inside:
        stable.append(dict(down=d, margin_mm=1000 * margin, area_cm2=1e4 * hull.area_faces[hull.facets[fi]].sum()))
stable.sort(key=lambda s: -s['margin_mm'])
print(json.dumps(dict(mesh=os.path.basename(mesh_path), extents_cm=(100 * ext).round(1).tolist(), stable_rests=[
    dict(down=np.round(s['down'], 3).tolist(), margin_mm=round(s['margin_mm'], 1), area_cm2=round(s['area_cm2'], 1)) for s in stable[:6]])))


def load(ep):
    f = glob.glob(f'{ref_root}/ep{ep}/processed/*/*/*.parquet')[0]; t = pq.read_table(f)
    names = t.column('object_body_names')[0].as_py(); T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
    P = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    Q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
    return names, P, Q


def score(ach, ref, names, align=True):
    verts, axes, orders = [], [], []
    for n in names:
        if n == 'wooden_spoon':
            verts.append(P_spoon)
        else:                                                                    # other objects: a 5 cm sphere stand-in
            s = rng.normal(size=(500, 3)); verts.append(0.05 * s / np.linalg.norm(s, axis=1, keepdims=True))
        ax = np.zeros(3); od = 1
        if n in AXIAL:
            ax = np.array([0, 0, 1.0]); od = A._SYMMETRY_ANGLES
        elif n in HALF:
            ax = np.array([0, 0, 1.0]); od = 2
        axes.append(ax); orders.append(od)
    a = A._align_registered_scene(ach, ref, axes) if align else ach
    return float(A._registered_pose_metric('add_auc', a, ref, verts, axes, orders))


out = {}
for ep in eps:
    names_r = roster[str(ep)]; names, P, Q = load(ep)
    order = [names.index(n) for n in names_r]; P, Q = P[:, order], Q[:, order]; names = names_r
    js = names.index('wooden_spoon'); T = len(P)
    fixed = [i for i, n in enumerate(names) if n not in AXIAL and n not in HALF]; anchor = names[fixed[0] if fixed else 0]
    ref = np.concatenate([P, Q], -1)[:, None]                                     # (T, 1, B, 7)
    # 1. sensitivity to a constant body-frame orientation error of the spoon
    sens = {}
    for axn, axv in (('x', [1, 0, 0]), ('y', [0, 1, 0]), ('z', [0, 0, 1])):
        for eps_deg in (5, 10, 20, 30):
            tru = ref.copy(); r = R.from_quat(tru[:, 0, js, 3:]) * R.from_rotvec(np.radians(eps_deg) * np.array(axv, float))
            tru[:, 0, js, 3:] = r.as_quat()
            sens[f'{axn}{eps_deg}'] = dict(aligned=round(score(ref, tru, names), 3), no_scene_align=round(score(ref, tru, names, align=False), 3))
    # 2. frame-0 plausibility: the spoon's body "down" vs the mesh's stable rest directions, over its first rest frames
    mv = np.nonzero(np.linalg.norm(P[:, js] - P[0, js], axis=1) > 0.01)[0]; f_on = int(mv[0]) if len(mv) else T
    downs = R.from_quat(Q[:max(1, min(f_on, 30)), js]).inv().apply([0, 0, -1.0])
    ang = [min(np.degrees(np.arccos(np.clip(d @ s['down'], -1, 1))) for s in stable) for d in downs]
    z0 = float(P[0, js, 2])
    out[ep] = dict(objects=names, anchor=anchor, spoon_anchors=anchor == 'wooden_spoon', motion_onset=f_on,
                   spoon_z0_cm=round(100 * z0, 1), f0_tilt_from_nearest_stable_rest_deg=dict(
                       f0=round(ang[0], 1), median=round(float(np.median(ang)), 1), max=round(float(np.max(ang)), 1)),
                   sensitivity_auc=sens)
    print(ep, json.dumps(out[ep]), flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spoon_anchor.json'), 'w'), indent=1)
