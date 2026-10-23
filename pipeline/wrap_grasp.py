"""Wrap (power) grasp on a handle for the Sharpa hand (2026-10-23; owner: "the grasps all pinch; wrap the hand around the
handle, that is the strongest grasp"; security first, the human's grasp position and angle second).
Used by pipeline/grasp_lock.py --wrap for elongated objects. All geometry is FlashCHORD's own (Newton FK of the scene,
the object's collision hulls), so what is built is what the simulator collides.

Hand frame (C_MC body = wrist target; measured with FK at zero finger angles): +z along the fingers (knuckles at
z 9-10 cm, fingertips 17 cm), y across the knuckles (right hand: index +3 cm, pinky -3 cm), +x the palm side (fingers
curl towards +x; palm surface at x ~ +2.2 cm); the thumb sits on the index side.

Construction for one hold (object at its reference pose at frame g):
  1. handle: the object's long axis (PCA of its collision hull vertices); radius = 90th percentile distance of the hull
     vertices to the axis within +-1.5 cm of the grip point; the grip point along the axis = the human hand's knuckle
     centre projected on the axis, kept HAND_HALF away from the ends of the narrow part (cross-section <= MAX_WIDTH);
  2. orientation: hand y parallel to the axis (sign as the human hand's y), hand x (palm normal) perpendicular to the
     axis and as close as possible to the human palm normal, z = x cross y;
  3. position: the handle axis lies in the palm at x = PALM_X + radius + CLEAR, z = GRIP_Z, y = GRIP_Y (hand frame);
  4. fingers: each finger curls (MCP_FE, PIP, DIP proportionally to their upper limits) until one of its links touches
     the hulls (signed distance <= 1 mm); the thumb closes (CMC_FE, MCP_FE, IP) the same way; targets = contact + SQUEEZE.
No ground truth is read; the human hand comes from our own reference.
"""
import numpy as np
from scipy.spatial.transform import Rotation as Rot

PALM_X, CLEAR, GRIP_Z, GRIP_Y = 0.022, 0.002, 0.080, 0.0
HAND_HALF, MAX_WIDTH = 0.045, 0.035
FINGERS = ('index', 'middle', 'ring', 'pinky')


def handle_geometry(V, ref_point):
    """V: hull vertices (object frame). Returns (centre c on the axis, axis a, radius r, narrow range [lo, hi] along a)."""
    c0 = V.mean(0); a = np.linalg.svd(V - c0, full_matrices=False)[2][0]
    s = (V - c0) @ a; radial = np.linalg.norm((V - c0) - np.outer(s, a), axis=1)
    bins = np.linspace(s.min(), s.max(), 41); width = np.zeros(40)
    for i in range(40):
        m = (s >= bins[i]) & (s < bins[i + 1])
        width[i] = 2 * np.percentile(radial[m], 90) if m.sum() > 3 else np.inf
    narrow = np.nonzero(width <= MAX_WIDTH)[0]
    lo, hi = (bins[narrow.min()], bins[narrow.max() + 1]) if len(narrow) else (s.min(), s.max())
    t = float(np.dot(ref_point - c0, a))
    t = float(np.clip(t, lo + HAND_HALF, hi - HAND_HALF)) if hi - lo > 2 * HAND_HALF else 0.5 * (lo + hi)
    m = np.abs(s - t) < 0.015; r = float(np.percentile(radial[m], 90)) if m.sum() > 3 else float(np.percentile(radial, 50))
    # the axis may not pass through the handle's local centre: re-centre on the slab's centroid
    c = c0 + a * t; sl = V[m] if m.sum() > 3 else V; off = sl.mean(0) - c; c = c + off - a * np.dot(off, a)
    return c, a, r, (lo, hi), t


def wrap_pose(R_human, c, a, r):
    """Hand orientation / position (object frame) for a wrap on the axis (c, a) of radius r, closest to the human hand."""
    yh, xh = R_human.apply([0, 1.0, 0]), R_human.apply([1.0, 0, 0])
    y = a * (1.0 if np.dot(yh, a) >= 0 else -1.0)
    x = xh - np.dot(xh, y) * y
    x = x / np.linalg.norm(x) if np.linalg.norm(x) > 1e-6 else np.cross(y, [0, 0, 1.0]) / max(np.linalg.norm(np.cross(y, [0, 0, 1.0])), 1e-9)
    z = np.cross(x, y); R = Rot.from_matrix(np.stack([x, y, z], 1))
    p = c - R.apply([PALM_X + r + CLEAR, GRIP_Y, GRIP_Z])
    return R, p


def close_fingers(fk, q, o, side, names, lo, hi, bodies, pb, pl, sdf, to_obj, squeeze, steps=40):
    """Curl each finger (and the thumb) of hand offset o from its open pose until a link touches the object hulls.
    Returns (q_contact fingers, q_squeezed fingers, {finger: contact fraction or None})."""
    qf = q[o + 7:o + 29].copy(); qc = qf.copy(); report = {}
    groups = {f: [i for i, n in enumerate(names) if f'_{f}_' in n and any(k in n for k in ('_FE', '_PIP', '_DIP'))] for f in FINGERS}
    groups['thumb'] = [i for i, n in enumerate(names) if '_thumb_' in n and any(k in n for k in ('CMC_FE', 'MCP_FE', '_IP'))]
    links = {f: [bodies[k] for k in bodies if k.startswith(f'{side}_{f}_') and k.split('_')[-1] in ('PP', 'MP', 'DP')] for f in FINGERS}
    links['thumb'] = [bodies[k] for k in bodies if k.startswith(f'{side}_thumb_') and k.split('_')[-1] in ('MC', 'PP', 'DP')]
    for f, idx in groups.items():
        sel = np.isin(pb, links[f]); hit = None
        for k in range(1, steps + 1):
            s = k / steps; qq = q.copy(); qq[o + 7:o + 29] = qc
            qq[o + 7 + np.array(idx)] = qf[idx] + s * (hi[idx] - qf[idx])
            X = to_obj(cr_world_points(fk(qq), pb[sel], pl[sel]))
            if sdf(X).min() <= 0.001:
                hit = s; break
        s = hit if hit is not None else 1.0
        qc[idx] = qf[idx] + s * (hi[idx] - qf[idx]); report[f] = None if hit is None else round(hit, 3)
    flex = np.zeros(len(names)); [flex.__setitem__(i, 1.0) for idx in groups.values() for i in idx]
    return qc, np.clip(qc + squeeze * flex, lo, hi), report


def cr_world_points(bq, body_ids, local):
    R = Rot.from_quat(bq[body_ids, 3:7]); return R.apply(local) + bq[body_ids, :3]
