"""Support-consistent object meshes for the simulator (2026-10-23; owner: "the mesh should physically support the starting
position"; docs/research/notes/25). Our perception can get a resting pose right while our mesh cannot hold it: on public
ep18 the brush stands on its bristles (mocap: contact patch 10.9 x 3.7 cm, stable); our reconstruction has the same pose
(87.6 vs 86.2 deg) but our mesh touches the table on 0.9 x 0.6 cm only (ragged, unobserved bristle underside), so it
tips over in the first frames and the whole episode is lost.
Rule (every object, every episode; our own reference only, no ground truth):
  1. resting poses = the first and the last frame (the simulator starts from frame 0 exactly) plus the first frame of
     every window of MIN_REST frames whose poses stay within STILL_MM / STILL_DEG of the window mean, kept when the
     lowest point is within NEAR of the table top (support usda); near-identical poses are processed once;
  2. stability certificate (statics of a rigid body on a plane): a rigid body stands if its centre of mass (the URDF's,
     which the simulator uses) projects inside its support polygon (convex hull of the points touching the table, within
     BAND). The margin d (COM to the nearest edge) sets the tilt it survives, atan(d / h_com), and the push,
     m g d / h_com. Required: d >= MARGIN_MIN and atan(d / h_com) >= TIP_MIN_DEG. The pose as is passes if it gets
     there by quasi-static rocking (rotate about the support point / edge on the COM's side, the way the COM goes down,
     picking up each new contact) within SETTLE_DEG (our resting-pose error is 1-2 deg; a faceted flat bottom settles);
  3. a pose that the mesh as is does not certify is filled straight down to the table where the underside is within
     FILL of it (convex slab of the low surface points and their projection on the table plane, mapped back to the
     object frame, manifold boolean union; concatenation if the union fails), the smallest FILL in FILLS that
     certifies it and stays in free space along our reference (surface samples of the other objects inside the slab
     in at most OV_RUN consecutive / OV_TOTAL frames: a brief contact, never another object resting in the fill; public
     ep12's cup sits in the rack 1 cm above the table). If none does, nothing is added and the pose is reported
     UNSTABLE / BLOCKED.
     (Leaning on other objects would need the friction-cone equilibrium LP of grasp_force.py with the table and the
     other objects as contacts; not needed for poses resting on the table.)
Writes a per-episode asset folder (urdf/ + mesh/, filled meshes only where needed) and a copy of the reference parquet
whose object_urdf_paths point there. Scoring keeps the original library meshes (the fill is simulator geometry).
Usage: support_fill.py REF.parquet USDA OUT_ASSETS OUT_REF.parquet [--fill 0 (auto)] [--asset_map /content/assets=LOCAL]
"""
import argparse, json, os, re, shutil

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import trimesh
from scipy.spatial import ConvexHull, Delaunay
from scipy.spatial.transform import Rotation as R

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hold_phases import hold_phases  # noqa: E402

STILL_MM, STILL_DEG, MIN_REST, NEAR = 3.0, 2.0, 10, 0.015   # perception jitters 0.4-1.6 mm, 0.3-1.9 deg / frame at rest
FILLS = (0.005, 0.01, 0.015, 0.02)   # tried in order; the smallest that certifies the pose is used
MARGIN_MIN, TIP_MIN_DEG = 0.003, 3.0  # stability certificate: COM >= 3 mm inside the support polygon and >= 3 deg to tip
OV_RUN, OV_TOTAL = 5, 15             # free space: a fill may touch another object briefly (<= OV_RUN frames in a row,
                                      # <= OV_TOTAL in all: ep18 brush into the dust pan while sweeping, 6 frames <= 7.6 mm),
                                      # never persistently (another object resting in it: ep12 cup in the rack)
SETTLE_DEG, BAND = 3.0, 0.001        # the pose as is may rock by up to SETTLE_DEG (our pose error 1-2 deg); contact band
                                      # = the soft contact's sink (~1 mm)


def table_top(usda):
    """Top height of the support from our reconstructed_stage usda (as contact_retarget.parse_support)."""
    txt = open(usda).read()
    c = [float(x) for x in re.search(r'xformOp:translate\s*=\s*\(([^)]*)\)', txt).group(1).split(',')]
    h = float(re.search(r'double height\s*=\s*([0-9.eE+-]+)', txt).group(1))
    return c[2] + h / 2


def rest_frames(P, Q, held):
    """Frame 0, the last frame, and the first frame of each still window (MIN_REST frames within STILL_MM / STILL_DEG
    of the window mean; windows do not overlap); frames where a hand holds the object (HELD mask) are not resting."""
    out, k = [0], 1
    while k + MIN_REST <= len(P):
        w = slice(k, k + MIN_REST); m = P[w].mean(0); qm = R.from_quat(Q[w]).mean()
        if not held[w].any() and np.linalg.norm(P[w] - m, axis=1).max() * 1000 < STILL_MM and \
                np.degrees((R.from_quat(Q[w]) * qm.inv()).magnitude()).max() < STILL_DEG:
            out.append(k); k += MIN_REST
        else:
            k += 1
    return [f for f in sorted(set(out + [len(P) - 1])) if not held[f]]


def certify(pts2, com2, h):
    """(COM inside, margin d, tipping angle deg) of the support polygon of the 2-D contact points PTS2 under the COM
    (in-plane COM2, height H above the plane)."""
    sp = ConvexHull(pts2); poly = pts2[sp.vertices]
    inside = bool(Delaunay(poly).find_simplex(com2) >= 0)
    e = np.roll(poly, -1, 0) - poly; nrm = np.c_[e[:, 1], -e[:, 0]] / np.linalg.norm(e, axis=1, keepdims=True)
    d = float(np.min(np.abs(((com2 - poly) * nrm).sum(1)))) if inside else 0.0
    return inside, d, float(np.degrees(np.arctan2(d, max(h, 1e-6))))


def _rot(X, p, k, th):
    return R.from_rotvec(k * th).apply(X - p) + p


def settle_check(X, com, step=np.radians(0.1)):
    """Quasi-static rocking of the hull points X (world) with centre of mass COM on a plane, up to SETTLE_DEG.
    Returns dict(settle_deg, contacts_cm, inside, margin_mm, tip_deg, ok)."""
    X, com, total, r = X.copy(), com.copy(), 0.0, {}
    while True:
        z0 = X[:, 2].min(); C = X[X[:, 2] < z0 + BAND]; c2 = com[:2]
        flat = len(C) >= 3 and np.linalg.matrix_rank(C[:, :2] - C[0, :2], tol=1e-4) == 2
        if flat:
            ins, d, tip = certify(C[:, :2], c2, com[2] - z0)
            r = dict(settle_deg=round(np.degrees(total), 1), contacts_cm=[round(100 * float(np.ptp(C[:, 0])), 1), round(100 * float(np.ptp(C[:, 1])), 1)],
                     inside=ins, margin_mm=round(1000 * d, 1), tip_deg=round(tip, 1), ok=ins and d >= MARGIN_MIN and tip >= TIP_MIN_DEG)
            if ins:                                                # stands (certified or not): no further rocking
                return r
            poly = C[ConvexHull(C[:, :2]).vertices]; best = None   # pivot: the edge the COM lies beyond, nearest it
            for a_, b_ in zip(poly, np.roll(poly, -1, 0)):
                e = (b_ - a_)[:2]; n2 = np.array([e[1], -e[0]]) / max(np.linalg.norm(e), 1e-12); dist = (c2 - a_[:2]) @ n2
                if dist > 0 and (best is None or dist < best[0]):
                    best = (dist, a_, b_)
            p, k = best[1], np.r_[(best[2] - best[1])[:2], 0.0]
        elif len(C) >= 2:                                          # collinear contacts: rock about their line
            i, j = np.unravel_index(np.argmax(np.linalg.norm(C[:, None, :2] - C[None, :, :2], axis=2)), (len(C), len(C)))
            p, k = C[i], np.r_[(C[j] - C[i])[:2], 0.0]
        else:                                                      # one contact point: tip towards the COM
            p = C[0]; k = np.cross([0, 0, 1.0], np.r_[c2 - p[:2], 0.0])
        if np.linalg.norm(k) < 1e-9:
            return dict(r, ok=False, settle_deg=round(np.degrees(total), 1), note='COM above a single point')
        k = k / np.linalg.norm(k)
        if np.cross(k, com - p)[2] > 0:                            # rotate the way the COM goes down
            k = -k
        n0 = len(C)
        while True:                                                # rock until a new point touches
            X, com = _rot(X, p, k, step), _rot(com[None], p, k, step)[0]; total += step
            if total > np.radians(SETTLE_DEG):
                return dict(r, ok=False, settle_deg=f'> {SETTLE_DEG}', note='still rocking')
            if (X[:, 2] < X[:, 2].min() + BAND).sum() > n0:
                break


def blocked(slab_pts, own, others):
    """Overlap of the convex slab (object frame) with the other objects along the reference: None if at most a brief
    contact (OV_RUN / OV_TOTAL), else (other, first frame, frames). OWN = (P, Q); OTHERS = [(name, samples, P, Q)]."""
    D = Delaunay(slab_pts); lo, hi = slab_pts.min(0) - 0.002, slab_pts.max(0) + 0.002; P, Q = own
    for n, S, Pk, Qk in others:
        hit = np.zeros(len(P), bool)
        for f in range(len(P)):
            Y = R.from_quat(Q[f]).inv().apply(R.from_quat(Qk[f]).apply(S) + Pk[f] - P[f]); Y = Y[np.all((Y > lo) & (Y < hi), axis=1)]
            hit[f] = len(Y) > 0 and bool((D.find_simplex(Y) >= 0).any())
        e = np.flatnonzero(np.diff(np.r_[0, hit.astype(int), 0])).reshape(-1, 2); runs = e[:, 1] - e[:, 0]
        if hit.sum() > OV_TOTAL or (len(runs) and runs.max() > OV_RUN):
            return n, int(np.argmax(hit)), int(hit.sum())
    return None


def fill_one(mesh, poses, ztop, fill=None, com_obj=None, own=None, others=()):
    """Returns (filled mesh or None, per-pose report). COM_OBJ: the centre of mass the simulator uses (URDF inertial);
    OWN / OTHERS: trajectories for the free-space test (see blocked)."""
    com_obj = mesh.center_mass if com_obj is None else com_obj; HV = np.asarray(mesh.convex_hull.vertices, float)
    V = np.asarray(mesh.vertices, float); slabs, rep, done = [], [], []
    for f, p, q in poses:
        Rq = R.from_quat(q)
        if any(np.linalg.norm(p - p2) < 0.01 and (Rq * R.from_quat(q2).inv()).magnitude() < np.radians(3) for p2, q2 in done):
            continue
        done.append((p, q)); X = Rq.apply(V) + p; zmin = X[:, 2].min()
        if zmin - ztop > NEAR:
            rep.append(dict(frame=int(f), skipped=f'lowest point {100 * (zmin - ztop):.1f} cm above the table (resting on something else)'))
            continue
        com = Rq.apply(com_obj) + p; r = dict(frame=int(f), lowest_above_table_mm=round(1000 * (zmin - ztop), 1))
        r['as_is'] = settle_check(Rq.apply(HV) + p, com)           # as it is: does it settle and stand?
        if r['as_is']['ok']:
            r['status'] = 'STABLE AS IS'; rep.append(r); continue
        for fl in ((fill,) if fill else FILLS):
            base = X[X[:, 2] < ztop + fl]; proj = base.copy(); proj[:, 2] = ztop
            if len(base) < 4 or np.ptp(proj[:, 0]) < 1e-3 or np.ptp(proj[:, 1]) < 1e-3:
                continue
            ins, d, tip = certify(proj[:, :2], com[:2], com[2] - ztop)
            r.update(fill_cm=round(100 * fl, 1), patch_cm=[round(100 * float(np.ptp(proj[:, 0])), 1), round(100 * float(np.ptp(proj[:, 1])), 1)],
                     inside=ins, margin_mm=round(1000 * d, 1), tip_deg=round(tip, 1))
            if ins and d >= MARGIN_MIN and tip >= TIP_MIN_DEG:
                pts = np.vstack([base, proj]); hull = ConvexHull(pts)
                hit = blocked(Rq.inv().apply(pts - p), own, others) if own is not None else None
                if hit:
                    r['blocked'] = f'{hit[0]} from frame {hit[1]} ({hit[2]} frames)'; continue
                slab = trimesh.Trimesh(Rq.inv().apply(pts - p), hull.simplices, process=True); trimesh.repair.fix_normals(slab)
                r.update(slab_cm3=round(1e6 * float(hull.volume), 1), status='CERTIFIED BY FILL'); slabs.append(slab); break
        else:
            r['status'] = 'BLOCKED' if 'blocked' in r else f'UNSTABLE (no fill up to {100 * FILLS[-1]:.1f} cm certifies it)'
        rep.append(r)
    if not slabs:
        return None, rep
    try:
        out = trimesh.boolean.union([mesh] + slabs, engine='manifold')
        how = 'union'
    except Exception as e:  # noqa: BLE001
        out = trimesh.util.concatenate([mesh] + slabs); how = f'concatenated ({str(e)[:60]})'
    for r in rep:
        r.setdefault('merge', how)
    return out, rep


def main():
    ap = argparse.ArgumentParser(); [ap.add_argument(x) for x in ('ref', 'usda', 'out_assets', 'out_ref')]
    ap.add_argument('--fill', type=float, default=0.0, help='fixed fill (m); 0 = the smallest certifying one of FILLS')
    ap.add_argument('--asset_map', default='')
    a = ap.parse_args()
    t = pq.read_table(a.ref); names = t.column('object_body_names')[0].as_py(); urdfs = t.column('object_urdf_paths')[0].as_py()
    T = len(np.array(t.column('robot_left_wrist_position')[0].as_py()).reshape(-1, 3))
    OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
    phases = hold_phases(a.ref)[0]['phases']
    ztop = table_top(a.usda); src_map = dict(x.split('=') for x in a.asset_map.split(',') if '=' in x)
    os.makedirs(f'{a.out_assets}/urdf', exist_ok=True); new_urdfs, report = [], dict(table_top=round(ztop, 4), fills_m=[a.fill] if a.fill else list(FILLS),
                                                                 margin_min_m=MARGIN_MIN, tip_min_deg=TIP_MIN_DEG, objects={})
    srcs, meshes, samples = [], [], []
    for u in urdfs:
        src = u
        for k, v in src_map.items():
            src = src.replace(k, v)
        mesh_rel = re.search(r'filename="([^"]+)"', open(src).read()).group(1)          # ../mesh/<n>/<n>.glb
        srcs.append((src, mesh_rel)); meshes.append(trimesh.load(os.path.normpath(os.path.join(os.path.dirname(src), mesh_rel)), force='mesh'))
        try:
            samples.append(trimesh.sample.sample_surface(meshes[-1], 4000, seed=0)[0])
        except TypeError:                                            # older trimesh: no seed argument
            np.random.seed(0); samples.append(trimesh.sample.sample_surface(meshes[-1], 4000)[0])
    for j, (n, (src, mesh_rel), mesh) in enumerate(zip(names, srcs, meshes)):
        ci = re.search(r'<inertial>\s*<origin xyz="([^"]+)"', open(src).read())     # the simulator's COM (the fill keeps it)
        mesh_dst = os.path.normpath(os.path.join(f'{a.out_assets}/urdf', mesh_rel)); os.makedirs(os.path.dirname(mesh_dst), exist_ok=True)
        held = np.zeros(T, bool)
        for ph in phases:
            if ph['object'] == n:
                held[max(0, ph['start'] - 4):min(T, ph['end'] + 2)] = True
        poses = [(f, OP[f, j], OQ[f, j]) for f in rest_frames(OP[:, j], OQ[:, j], held)]
        filled, rep = fill_one(mesh, poses, ztop, a.fill or None, np.array(ci.group(1).split(), float) if ci else None,
                               (OP[:, j], OQ[:, j]), [(names[k], samples[k], OP[:, k], OQ[:, k]) for k in range(len(names)) if k != j])
        if filled is not None:
            filled.export(mesh_dst)
        else:                                                      # untouched: the original file, bit for bit
            shutil.copy(os.path.normpath(os.path.join(os.path.dirname(src), mesh_rel)), mesh_dst)
        shutil.copy(src, f'{a.out_assets}/urdf/{os.path.basename(src)}'); new_urdfs.append(os.path.abspath(f'{a.out_assets}/urdf/{os.path.basename(src)}'))
        report['objects'][n] = dict(rest_frames=[int(p[0]) for p in poses], fills=rep, filled=filled is not None,
                                    volume_cm3=[round(1e6 * mesh.volume, 1), round(1e6 * (filled if filled is not None else mesh).volume, 1)])
    i = t.column_names.index('object_urdf_paths')
    t = t.set_column(i, 'object_urdf_paths', pa.array([new_urdfs], type=t.schema.field('object_urdf_paths').type))
    os.makedirs(os.path.dirname(os.path.abspath(a.out_ref)), exist_ok=True); pq.write_table(t, a.out_ref)
    json.dump(report, open(os.path.splitext(a.out_ref)[0] + '_support_fill.json', 'w'), indent=1)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
