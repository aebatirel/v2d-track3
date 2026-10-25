"""Can the cross be assembled in a simulator with our collision geometry? CPU MuJoCo proxy (approach-1 study, 2026-10-25).

GT-free: our meshes, the convex hulls FlashCHORD would build from them (flash_chord.assets.mesh.convex_decompose, CoACD
threshold 0.05, cached), and the relative path of board B in board A's frame taken from OUR reference parquet.
Board A is fixed at the origin; board B is a free body (0.3 kg, gravity off) pulled by a weld equality to a mocap
target that follows the reference relative path frame by frame (20 fps). Reported per variant: the lag of B behind the
target (translation / rotation) at the assembled frames and at the end, and the deepest contact penetration.
This is a geometric feasibility proxy, not FlashCHORD's solver configuration (Newton / MuJoCo Warp, dt 0.01).

Variants:
  default   : CoACD hulls of each mesh (what the eval-25 simulation had);
  cut       : collision copy only: every hull clipped by planes so that the region our reference sweeps B through A
              (and A through B) is empty. Slot = claim region (partner inside in >= K frames) bounding slab, widened by
              MARGIN, on the entry half only (split at the column centre along the insertion axis). Convex pieces only,
              so FlashCHORD's CoACD keeps them (note 19: a convex piece comes back unchanged);
  nocollide : A-B contact disabled (the drive's own tracking floor).
Usage (fcvenv, FLASH_CHORD_CACHE_DIR set): insert_test.py MESH_A MESH_B REF.parquet CLAIMS.npz START END OUT.json"""
import json, sys

import mujoco
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.optimize import linprog
from scipy.spatial import ConvexHull, HalfspaceIntersection
from scipy.spatial.transform import Rotation as R
from flash_chord.assets.mesh import convex_decompose

MARGIN, K, FPS, SUB = 0.001, 5, 20.0, 25          # 1 mm clearance; dt = 1/(FPS*SUB) = 2 ms


def hulls_of(path):
    m = trimesh.load(path, force='mesh'); m = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
    return [np.asarray(h.vertices, float) for h in convex_decompose(np.asarray(m.vertices), np.asarray(m.faces))]


def clip(V, planes):
    """Convex hull of V intersected with half-spaces n.x + d <= 0 (list of (n, d)); None if empty / degenerate."""
    eq = ConvexHull(V).equations
    H = np.vstack([eq] + [np.r_[n, d][None] for n, d in planes])
    A, b = H[:, :3], -H[:, 3]; nrm = np.linalg.norm(A, axis=1)
    res = linprog(np.r_[0, 0, 0, -1.0], A_ub=np.c_[A, nrm], b_ub=b, bounds=[(None, None)] * 3 + [(0, None)])
    if not res.success or res.x[3] < 2e-4:                     # needs an inscribed ball of >= 0.2 mm
        return None
    P = HalfspaceIntersection(H, res.x[:3]).intersections
    try:
        return P[ConvexHull(P).vertices]
    except Exception:
        return None


def slot_cut(hulls, S, cnt, axis_dir, rel_pts, plane=None):
    """Remove from every hull the slab (claim samples' 1-99 % extent along the partner's thickness axis, + MARGIN) on one
    side of a split plane. S, cnt: own solid samples and frames-inside-partner counts. axis_dir: partner thickness axis in
    own frame. rel_pts: partner origin positions in own frame along the path (insertion axis and entry side).
    plane = (n, c): carve where n.x > c (given for B so that A's and B's carves meet at one physical plane);
    default: the entry side of the claim's midpoint along the insertion axis."""
    C = S[cnt >= K]
    if len(C) < 20:
        return hulls, {}
    a = axis_dir / np.linalg.norm(axis_dir)
    s = C @ a; lo, hi = np.percentile(s, 1) - MARGIN, np.percentile(s, 99) + MARGIN
    if plane is None:
        ins = rel_pts[0] - rel_pts[-1]; ins -= a * (ins @ a); ins /= np.linalg.norm(ins)   # from the column to the entry side
        p = C @ ins; split = float((np.percentile(p, 1) + np.percentile(p, 99)) / 2)       # column midpoint along the insertion axis
    else:
        ins, split = plane
    out = []
    for V in hulls:
        # region to remove: lo < a.x < hi AND ins.x > split ; keep its complement = 3 convex pieces
        for pl in ([(a, -lo)], [(-a, hi)], [(ins, -split)]):
            P = clip(V, pl)
            if P is not None:
                out.append(P)
    return out, dict(slab_mm=[round(lo * 1e3, 1), round(hi * 1e3, 1)], split_mm=round(split * 1e3, 2), entry_axis=np.round(ins, 4).tolist(),
                     claim_cm3=round(len(C) * 1.5 ** 3 / 1000, 2), pieces=len(out))


def mjcf(hA, hB, collide=True):
    def geoms(hs, tag, ct, ca):
        assets = ''.join(f'<mesh name="{tag}{i}" vertex="{" ".join(map(str, np.round(V.ravel(), 6)))}"/>' for i, V in enumerate(hs))
        g = ''.join(f'<geom type="mesh" mesh="{tag}{i}" contype="{ct}" conaffinity="{ca}" density="0" condim="3" friction="0.5"/>' for i in range(len(hs)))
        return assets, g
    aA, gA = geoms(hA, 'a', 1, 1)
    aB, gB = geoms(hB, 'b', 1 if collide else 2, 1 if collide else 2)
    return f'''<mujoco><option timestep="{1 / (FPS * SUB)}" gravity="0 0 0"/><asset>{aA}{aB}</asset><worldbody>
<body name="A">{gA}</body>
<body name="tgt" mocap="true"/>
<body name="B"><freejoint/><inertial pos="0 0 0" mass="0.3" diaginertia="0.002 0.002 0.0005"/>{gB}</body>
</worldbody><equality><weld body1="tgt" body2="B" solref="0.02 1"/></equality></mujoco>'''


def run(xml, rel, t0, t1):
    m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m)
    bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'B')
    q0 = R.from_matrix(rel[t0, :3, :3]).as_quat()[[3, 0, 1, 2]]
    d.qpos[:3] = rel[t0, :3, 3]; d.qpos[3:7] = q0; d.mocap_pos[0] = rel[t0, :3, 3]; d.mocap_quat[0] = q0
    mujoco.mj_forward(m, d)
    lag_t, lag_r, pen = [], [], []
    for t in range(t0, t1):
        d.mocap_pos[0] = rel[t, :3, 3]; d.mocap_quat[0] = R.from_matrix(rel[t, :3, :3]).as_quat()[[3, 0, 1, 2]]
        for _ in range(SUB):
            mujoco.mj_step(m, d)
        p = d.xpos[bid].copy(); Rb = d.xmat[bid].reshape(3, 3)
        lag_t.append(np.linalg.norm(p - rel[t, :3, 3]) * 100)
        lag_r.append(R.from_matrix(rel[t, :3, :3].T @ Rb).magnitude() * 180 / np.pi)
        pen.append(max([-d.contact[i].dist for i in range(d.ncon)] + [0.0]) * 1e3)
    return np.array(lag_t), np.array(lag_r), np.array(pen)


def main():
    ma, mb, ref, claims, s0, s1, out = sys.argv[1:8]
    t0, t1 = int(s0), int(s1)
    row = pq.read_table(ref).to_pylist()[0]
    names = list(row['object_body_names']); pos = np.array(row['object_body_position'], float); q = np.array(row['object_body_wxyz'], float)
    T = {}
    for n in names:
        k = names.index(n); M = np.tile(np.eye(4), (len(pos), 1, 1))
        M[:, :3, :3] = R.from_quat(q[:, k, [1, 2, 3, 0]]).as_matrix(); M[:, :3, 3] = pos[:, k]; T[n] = M
    rel = np.linalg.inv(T[names[0]]) @ T[names[1]]                      # B in A
    z = np.load(claims); asm = z['asm']; F = z['frames']
    hA, hB = hulls_of(ma), hulls_of(mb)
    Ra = R.from_matrix(rel[F[asm], :3, :3]).mean().as_matrix()        # B axes in A at assembly
    cutA, infoA = slot_cut(hA, z['SA'], z['cntA'], Ra[:, 0], rel[t0:t1, :3, 3])            # B's thickness axis (x) in A
    relBA = np.linalg.inv(rel)                                                              # A in B
    nA, cA = np.array(infoA['entry_axis']), infoA['split_mm'] / 1e3                        # A carves where nA.x > cA (A frame)
    tB = rel[F[asm], :3, 3].mean(0)                                                         # B's origin in A at assembly
    plane_B = (-Ra.T @ nA, float(nA @ tB - cA))                                             # B carves the other side of the same plane
    cutB, infoB = slot_cut(hB, z["SB"], z["cntB"], Ra.T[:, 0], relBA[t0:t1, :3, 3], plane=plane_B)   # A's thickness axis (x) in B
    res = dict(frames=[t0, t1], hulls=[len(hA), len(hB)], cutA=infoA, cutB=infoB)
    asm_idx = np.flatnonzero(asm & (F >= t0) & (F < t1)) ; asm_local = F[asm_idx] - t0
    for name, xml in [('default', mjcf(hA, hB)), ('cut', mjcf(cutA, cutB)), ('nocollide', mjcf(hA, hB, collide=False))]:
        lt, lr, pe = run(xml, rel, t0, t1)
        res[name] = dict(lag_cm_asm_median=round(float(np.median(lt[asm_local])), 2), lag_cm_end=round(float(lt[-1]), 2),
                         lag_deg_asm_median=round(float(np.median(lr[asm_local])), 1), lag_cm_max=round(float(lt.max()), 2),
                         pen_mm_max=round(float(pe.max()), 1), pen_mm_asm_median=round(float(np.median(pe[asm_local])), 1),
                         lag_cm_every10=np.round(lt[::10], 2).tolist())
        print(name, {k: v for k, v in res[name].items() if k != 'lag_cm_every10'}, flush=True)
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps({k: res[k] for k in ('hulls', 'cutA', 'cutB')}))


if __name__ == '__main__':
    main()
