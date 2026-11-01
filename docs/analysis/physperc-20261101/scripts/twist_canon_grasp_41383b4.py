"""Twist canonicalisation of rotationally symmetric objects in a reference parquet (2026-11-01, GT-free).

Why: a camera cannot observe a symmetric object's rotation about its own symmetry axis (a plain cup), so perception
writes noise there. On public ep13 our blue-cup track twists 12° by f8, 54° by f18, 140° by f30 about its axis while it
rests (mocap: 0–9° until f24). The leaderboard ignores this twist (kit Track 3 README: beige_cup / blue_cup are
symmetric about their central axis; AUC.py minimises over it), but our plain-ADD proxy sim_vs_ref charges it, training
rewards that track full orientation chase it, and grasp_lock.py fixes held hands in the object frame, so a spurious twist
can drag a locked hand around the object.

What: for each named object, the symmetry axis a (body frame) is our mesh's PCA axis whose variance differs from the
other two (or --axis). The world axis u_t = R_t a (observable: tilt) is kept exactly. The twist is rebuilt:
  - parallel transport: R'_t = S(u'_(t-1) -> u_t) R'_(t-1), S = the minimal rotation between the two axis directions,
    so an object whose axis does not move gets no rotation at all (a resting cup stays put);
  - while the object is held (it moves more than MOVE_MM in the frame and a hand's frames are within HOLD_CM of its
    bounding sphere), the twist follows that hand: R'_t <- Rot(u_t, w . u_t) R'_t, w = the wrist's rotation vector over
    the frame (robot_<side>_wrist_wxyz).
R'_0 = R_0. Positions, hands and every other column are untouched. Only our own reference is read (no ground truth).
Usage: python twist_canon.py IN.parquet OUT.parquet [--objects blue_cup,beige_cup] [--hold_cm 2] [--move_mm 1]
       [--axis x,y,z]   (writes OUT_twist_canon.json: per object the axis, the twist removed per frame, max tilt change)
"""
import argparse, json, os

import numpy as np


def quat_wxyz_to_R(q):
    from scipy.spatial.transform import Rotation as R
    return R.from_quat(np.asarray(q, float)[..., [1, 2, 3, 0]])


def mesh_axis(path):
    import trimesh
    m = trimesh.load(path, force='mesh'); v = np.asarray(m.vertices, float); v = v - v.mean(0)
    w, V = np.linalg.eigh(np.cov(v.T)); i = int(np.argmax([abs(w[k] - np.mean(np.delete(w, k))) for k in range(3)]))
    others = np.delete(w, i); iso = float(abs(others[0] - others[1]) / max(others.max(), 1e-12))
    return V[:, i] / np.linalg.norm(V[:, i]), w.tolist(), iso


def min_rot(u0, u1):
    """Minimal rotation (scipy Rotation) taking unit vector u0 to u1."""
    from scipy.spatial.transform import Rotation as R
    c = np.cross(u0, u1); s = np.linalg.norm(c); d = float(np.clip(np.dot(u0, u1), -1.0, 1.0))
    if s < 1e-12:
        if d > 0:
            return R.identity()
        p = np.cross(u0, [1.0, 0, 0]); p = p if np.linalg.norm(p) > 1e-6 else np.cross(u0, [0, 1.0, 0])
        return R.from_rotvec(np.pi * p / np.linalg.norm(p))
    return R.from_rotvec(c / s * np.arctan2(s, d))


def canonicalise(OQ, OP, axis, radius, hands, hold_cm=2.0, move_mm=1.0):
    """OQ (T, 4) wxyz, OP (T, 3); hands: {side: (frames (T, F, 3), wrist_wxyz (T, 4))}. Returns (OQ' wxyz, info)."""
    from scipy.spatial.transform import Rotation as R
    Rin = quat_wxyz_to_R(OQ); T = len(OQ); u = Rin.apply(axis)
    out = [Rin[0]]; held = np.zeros(T, bool); by = [''] * T; follow = np.zeros(T)
    for t in range(1, T):
        prev = out[-1]; r = min_rot(prev.apply(axis), u[t]) * prev
        moving = np.linalg.norm(OP[t] - OP[t - 1]) > move_mm * 1e-3
        best, side = np.inf, ''
        for s, (fr, _) in hands.items():
            d = float(np.min(np.linalg.norm(fr[t] - OP[t], axis=-1)) - radius)
            if d < best:
                best, side = d, s
        if moving and best < hold_cm * 1e-2:
            Wq = hands[side][1]; w = (quat_wxyz_to_R(Wq[t]) * quat_wxyz_to_R(Wq[t - 1]).inv()).as_rotvec()
            tw = float(np.dot(w, u[t])); r = R.from_rotvec(u[t] * tw) * r; held[t], by[t], follow[t] = True, side, tw
        out.append(r)
    Rc = R.concatenate(out); q = Rc.as_quat()[:, [3, 0, 1, 2]]
    q[np.sum(q * np.asarray(OQ, float), 1) < 0] *= -1.0                         # keep the input's quaternion hemisphere
    removed = np.degrees((Rc * Rin.inv()).magnitude())
    tilt_change = np.degrees(np.arccos(np.clip(np.sum(Rc.apply(axis) * u, 1), -1, 1)))
    return q, dict(held_frames=int(held.sum()), held_by={s: int(sum(1 for b in by if b == s)) for s in hands},
                   twist_followed_deg=round(float(np.degrees(np.abs(follow).sum())), 1),
                   removed_deg_max=round(float(removed.max()), 1), removed_deg_every10=np.round(removed[::10], 1).tolist(),
                   tilt_change_deg_max=float(tilt_change.max()))


def main():
    import pyarrow as pa, pyarrow.parquet as pq
    p = argparse.ArgumentParser(); p.add_argument('inp'); p.add_argument('out')
    p.add_argument('--objects', default='blue_cup,beige_cup', help='objects symmetric about one axis (the kit declares '
                   'blue_cup and beige_cup; white_pot_lid is 2-fold, not handled here)')
    p.add_argument('--hold_cm', type=float, default=2.0); p.add_argument('--move_mm', type=float, default=1.0)
    p.add_argument('--axis', default='', help='body-frame axis x,y,z for all named objects (default: mesh PCA)')
    a = p.parse_args()
    t = pq.read_table(a.inp); g = lambda c: t.column(c)[0].as_py()  # noqa: E731
    names = g('object_body_names'); B = len(names); T = len(g('robot_left_wrist_position'))
    OP = np.array(g('object_body_position'), float).reshape(T, B, 3); OQ = np.array(g('object_body_wxyz'), float).reshape(T, B, 4)
    radius = np.array(g('object_mesh_radius'), float); meshes = g('object_mesh_paths')
    hands = {s: (np.array(g(f'robot_{s}_frames'), float).reshape(T, -1, 7)[:, :, :3],
                 np.array(g(f'robot_{s}_wrist_wxyz'), float).reshape(T, 4)) for s in ('left', 'right')}
    want = [x for x in a.objects.split(',') if x]; info = dict(inp=os.path.abspath(a.inp), args=vars(a), objects={})
    Q2 = OQ.copy()
    for j, n in enumerate(names):
        if n not in want:
            continue
        if a.axis:
            ax = np.array([float(x) for x in a.axis.split(',')]); ax /= np.linalg.norm(ax); pca, iso = None, None
        else:
            mp = meshes[j]
            if not os.path.exists(mp):                    # box paths (/content/...): the mesh beside the URDF's asset tree
                mp = os.path.join(os.path.dirname(g('object_urdf_paths')[j]), '..', 'mesh', n, os.path.basename(mp))
            ax, pca, iso = mesh_axis(mp)
        Q2[:, j], inf = canonicalise(OQ[:, j], OP[:, j], ax, radius[j], hands, a.hold_cm, a.move_mm)
        info['objects'][n] = dict(axis_body=np.round(ax, 4).tolist(), pca_var=pca, other_axes_rel_diff=iso, **inf)
    i = t.column_names.index('object_body_wxyz')
    shape = np.array(g('object_body_wxyz')).shape                    # keep the column's own nesting
    t2 = t.set_column(i, 'object_body_wxyz', pa.array([Q2.reshape(shape).tolist()], type=t.schema.field(i).type))
    pq.write_table(t2, a.out)
    json.dump(info, open(os.path.splitext(a.out)[0] + '_twist_canon.json', 'w'), indent=1)
    for n, d in info['objects'].items():
        print(f"{n}: axis {d['axis_body']}, twist removed max {d['removed_deg_max']}°, held {d['held_frames']} frames "
              f"{d['held_by']}, followed {d['twist_followed_deg']}°, tilt change max {d['tilt_change_deg_max']:.2e}°")
    if not info['objects']:
        print('no named symmetric object in', names)


if __name__ == '__main__':
    main()
