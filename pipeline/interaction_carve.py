"""Collision-copy interaction carve (2026-10-25; owner: "if we had the ridge this would have been perfect"; approach 1 of
docs/research/approaches-2026-10-25/approach1-motion-constrained-meshes.md, sections 2.3-2.5). GT-free: our meshes and
our own reference parquet (the poses the policy tracks), nothing else.

FlashCHORD replaces every collision mesh by CoACD hulls (threshold 0.05). On the boards they fill the notches, so the
simulated cross-lap joint cannot close: in the CPU proxy board 2 ends ~100 deg out of the joint (eval 25 and ep24).
This tool changes only the SIMULATOR collision copy, never the submitted mesh (CD-O and registration are untouched):

  slot MESH_A MESH_B REF.parquet OUT_DIR [--names A B]
    1. solid samples of each mesh (1.5 mm grid, winding number); along the reference, every sample counts the frames in
       which it lies inside the partner mesh (its "claim");
    2. hulls = FlashCHORD's own convex_decompose of each mesh (same function, same parameters), i.e. the hulls the
       simulator builds today;
    3. the joint: frames with B's origin within 2 cm of A's and still (assembled); the insertion window starts 40 frames
       before the first frame with > 0.5 cm3 overlap; the entry direction is B's path from there to the assembled pose,
       perpendicular to B's thickness axis (smallest principal axis of B's solid);
    4. A removes the slab {claim's 1-99 % extent along B's thickness axis + 1 mm} on the entry side of ONE plane through
       the claim's centre normal to the entry direction; B removes its slab (along A's thickness axis) on the other side
       of the same physical plane, so the two half-notches meet. One shared plane matters: splitting each board at its
       own claim median left a 1.3 cm uncut band in the prototype (1.4 cm / 8.4 deg lag);
    5. a hull that meets the removed region is replaced by its (at most 3, disjoint) convex parts outside it; the other
       hulls are kept whole;
    6. writes OUT_DIR/<name>/piece_XX.obj (one convex piece each: make_assets.py --pieces turns them into one
       <collision> element each, which FlashCHORD's CoACD keeps unchanged) and OUT_DIR/carve.json: claim, slab, plane,
       pieces, removed hull volume, and the collision-hull overlap at the assembled frames before and after;
    --proxy adds the CPU MuJoCo insertion check of the prototype (A fixed, B welded to a target that follows the
       reference's relative path; lag at the assembled frames for default hulls, cut pieces and contact off).

Prototype: approach1-scripts/insert_test.py (same cut; this version keeps untouched hulls whole and takes the thickness
axes from the solids instead of assuming the mesh x axis). Needs NVIDIA Warp and FlashCHORD (+ MuJoCo for --proxy): run
in the FlashCHORD venv, CPU.
"""
import argparse, json, os, sys, time

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.optimize import linprog
from scipy.spatial import ConvexHull, HalfspaceIntersection
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collision_decomp import SignedDistance, inside  # noqa: E402

PITCH, ASM_M, STILL_MM, PRE, OVL_CM3 = 0.0015, 0.02, 2.0, 40, 0.5
K, MARGIN, PCT = 5, 0.001, 1.0                    # claim = inside the partner in >= K frames; 1 mm clearance; 1-99 %


def load_mesh(path):
    """Geometry exactly as make_assets.py writes the simulator copy (colours dropped, merged vertices)."""
    m = trimesh.load(path, force='mesh')
    return trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)


def fc_hulls(m):
    """The hulls FlashCHORD builds for this mesh (flash_chord.scene.objects._decompose_object_collision)."""
    from flash_chord.assets.mesh import convex_decompose
    return [np.asarray(h.vertices, float) for h in convex_decompose(np.asarray(m.vertices), np.asarray(m.faces))]


def solid(m, sd):
    lo = m.bounds[0] - 2 * PITCH; hi = m.bounds[1] + 2 * PITCH
    n = np.ceil((hi - lo) / PITCH).astype(int) + 1
    G = np.stack(np.meshgrid(*[lo[k] + PITCH * np.arange(n[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    return G[sd(G) < 0]


def ref_poses(ref, names):
    row = pq.read_table(ref).to_pylist()[0]
    nb = list(row['object_body_names']); pos = np.array(row['object_body_position'], float)
    q = np.array(row['object_body_wxyz'], float); out = []
    for n in names:
        k = nb.index(n); T = np.tile(np.eye(4), (len(pos), 1, 1))
        T[:, :3, :3] = R.from_quat(q[:, k][:, [1, 2, 3, 0]]).as_matrix(); T[:, :3, 3] = pos[:, k]
        out.append(T)
    return out


def thin_axis(S):
    """Smallest principal axis of a solid (a board's thickness direction), in its own frame."""
    w, U = np.linalg.eigh(np.cov((S - S.mean(0)).T))
    return U[:, 0], np.sqrt(w)


def clip(V, planes):
    """Convex hull of V intersected with half-spaces n.x + d <= 0 (list of (n, d)); None if empty or thinner than a
    0.2 mm inscribed ball."""
    eq = ConvexHull(V).equations
    H = np.vstack([eq] + [np.r_[n, d][None] for n, d in planes])
    A, b = H[:, :3], -H[:, 3]; nrm = np.linalg.norm(A, axis=1)
    res = linprog(np.r_[0, 0, 0, -1.0], A_ub=np.c_[A, nrm], b_ub=b, bounds=[(None, None)] * 3 + [(0, None)])
    if not res.success or res.x[3] < 2e-4:
        return None
    P = HalfspaceIntersection(H, res.x[:3]).intersections
    try:
        return P[ConvexHull(P).vertices]
    except Exception:
        return None


def region_cut(hulls, a, lo, hi, n, c):
    """Remove {lo < a.x < hi} & {n.x > c} from every hull; hulls that miss the region stay whole."""
    out, touched = [], 0
    for V in hulls:
        if clip(V, [(-a, lo), (a, -hi), (-n, c)]) is None:
            out.append(V); continue
        touched += 1
        for pl in ([(a, -lo)], [(-a, hi)], [(-a, lo), (a, -hi), (n, -c)]):
            P = clip(V, pl)
            if P is not None:
                out.append(P)
    return out, touched


def hull_volume(hulls):
    return float(sum(ConvexHull(V).volume for V in hulls))


def union_grid(hulls):
    """Grid points (PITCH) inside the union of hulls: the collision solid."""
    P = np.vstack(hulls); lo = P.min(0) - PITCH; hi = P.max(0) + PITCH
    n = np.ceil((hi - lo) / PITCH).astype(int) + 1
    G = np.stack(np.meshgrid(*[lo[k] + PITCH * np.arange(n[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    keep = np.zeros(len(G), bool)
    for V in hulls:
        keep |= inside(ConvexHull(V).equations, G)
    return G[keep]


def hull_overlap_cm3(hA, hB, rel, frames):
    """Volume of B's collision solid inside A's collision hulls (B posed in A by rel), per frame, cm3."""
    GB = union_grid(hB); eqA = [ConvexHull(V).equations for V in hA]; v = PITCH ** 3 * 1e6; out = []
    for t in frames:
        Q = GB @ rel[t, :3, :3].T + rel[t, :3, 3]; hit = np.zeros(len(Q), bool)
        for eq in eqA:
            hit |= inside(eq, Q)
        out.append(hit.sum() * v)
    return np.array(out)


def slot(a):
    t_start = time.time()
    mA, mB = load_mesh(a.mesh_a), load_mesh(a.mesh_b)
    sdA, sdB = SignedDistance(mA), SignedDistance(mB); SA, SB = solid(mA, sdA), solid(mB, sdB)
    TA, TB = ref_poses(a.ref, a.names); nF = len(TA); v = PITCH ** 3 * 1e6
    rel = np.linalg.inv(TA) @ TB                                     # B in A, per frame
    cntA = np.zeros(len(SA), np.int32); cntB = np.zeros(len(SB), np.int32); ovl = np.zeros(nF)
    for t in range(nF):
        Ti = np.linalg.inv(rel[t])                                   # A in B
        inA = sdB(SA @ Ti[:3, :3].T + Ti[:3, 3]) < 0; inB = sdA(SB @ rel[t, :3, :3].T + rel[t, :3, 3]) < 0
        cntA += inA; cntB += inB; ovl[t] = (inA.sum() + inB.sum()) / 2 * v
    tr = rel[:, :3, 3]
    still = np.r_[np.inf, np.linalg.norm(np.diff(tr, axis=0), axis=1) * 1e3] < STILL_MM
    asm = (np.linalg.norm(tr, axis=1) < ASM_M) & still; idx = np.flatnonzero(asm)
    first = np.flatnonzero(ovl > OVL_CM3)
    rep = dict(tool='interaction_carve slot', mesh_a=a.mesh_a, mesh_b=a.mesh_b, ref=a.ref, names=a.names, frames=nF,
               solid_cm3=[round(len(SA) * v, 1), round(len(SB) * v, 1)], n_assembled=int(len(idx)),
               mesh_overlap_cm3_median_assembled=round(float(np.median(ovl[idx])), 2) if len(idx) else None)
    if not len(idx) or not len(first):
        rep['carved'] = False; rep['reason'] = 'no assembled frames' if not len(idx) else 'no overlap'
        return rep, None
    t0 = max(0, int(first[0]) - PRE)
    Ra = R.from_matrix(rel[idx, :3, :3]).mean().as_matrix(); tB = tr[idx].mean(0)      # B in A at assembly
    thA, sgA = thin_axis(SA); thB, sgB = thin_axis(SB)
    hA, hB = fc_hulls(mA), fc_hulls(mB)

    def claim_slab(S, cnt, ax):
        C = S[cnt >= K]; s = C @ ax
        return C, np.percentile(s, PCT) - MARGIN, np.percentile(s, 100 - PCT) + MARGIN

    # A: slab along B's thickness axis, on the entry side of the plane through its claim's centre
    aA = Ra @ thB; CA, loA, hiA = claim_slab(SA, cntA, aA)
    ins = tr[t0] - tB; ins -= aA * (ins @ aA); ins /= np.linalg.norm(ins)              # assembled -> entry, in A
    p = CA @ ins; cA = float((np.percentile(p, PCT) + np.percentile(p, 100 - PCT)) / 2)
    # B: slab along A's thickness axis, on the other side of the same plane (A frame: ins.x = cA)
    aB = Ra.T @ thA; CB, loB, hiB = claim_slab(SB, cntB, aB)
    nB = -Ra.T @ ins; cB = float(ins @ tB - cA)                                         # B carves where nB.x > cB
    cutA, touchA = region_cut(hA, aA, loA, hiA, ins, cA)
    cutB, touchB = region_cut(hB, aB, loB, hiB, nB, cB)
    ov_def = hull_overlap_cm3(hA, hB, rel, idx); ov_cut = hull_overlap_cm3(cutA, cutB, rel, idx)

    def info(C, lo, hi, ax, n, c, h, cut, touched, sg):
        return dict(claim_cm3=round(len(C) * v, 2), slab_mm=[round(lo * 1e3, 1), round(hi * 1e3, 1)],
                    slab_width_mm=round((hi - lo) * 1e3, 1), slab_axis=np.round(ax, 4).tolist(),
                    plane_normal=np.round(n, 4).tolist(), plane_offset_mm=round(c * 1e3, 2),
                    own_thickness_sigma_mm=round(float(sg[0]) * 1e3, 1), hulls_before=len(h), hulls_touched=touched,
                    pieces=len(cut), hull_cm3_before=round(hull_volume(h) * 1e6, 1),
                    hull_cm3_after=round(hull_volume(cut) * 1e6, 1))
    rep.update(carved=True, insertion_window=[t0, nF - 1], first_overlap_frame=int(first[0]),
               assembled_frames=[int(idx[0]), int(idx[-1])], entry_dir_A=np.round(ins, 4).tolist(),
               rel_rot_assembled_B_axes_in_A=np.round(Ra, 3).tolist(),
               a=info(CA, loA, hiA, aA, ins, cA, hA, cutA, touchA, sgA),
               b=info(CB, loB, hiB, aB, nB, cB, hB, cutB, touchB, sgB),
               hull_overlap_cm3_assembled=dict(default_median=round(float(np.median(ov_def)), 2),
                                               default_max=round(float(ov_def.max()), 2),
                                               cut_median=round(float(np.median(ov_cut)), 2),
                                               cut_max=round(float(ov_cut.max()), 2)))
    os.makedirs(a.out, exist_ok=True)
    for name, cut in zip(a.names, (cutA, cutB)):
        d = f'{a.out}/{name}'; os.makedirs(d, exist_ok=True)
        for k, V in enumerate(cut):
            trimesh.convex.convex_hull(V).export(f'{d}/piece_{k:02d}.obj')
    if a.proxy:
        rep['proxy'] = proxy(hA, hB, cutA, cutB, rel, t0, nF, idx)
    rep['sec'] = round(time.time() - t_start, 1)
    return rep, (hA, hB, cutA, cutB, rel, t0, idx)


# --- CPU MuJoCo insertion proxy (approach1-scripts/insert_test.py) ---------------------------------------------------
FPS, SUB = 20.0, 25                                                   # dt = 1/(FPS*SUB) = 2 ms


def mjcf(hA, hB, collide=True):
    def geoms(hs, tag, ct, ca):
        assets = ''.join(f'<mesh name="{tag}{i}" vertex="{" ".join(map(str, np.round(V.ravel(), 6)))}"/>' for i, V in enumerate(hs))
        g = ''.join(f'<geom type="mesh" mesh="{tag}{i}" contype="{ct}" conaffinity="{ca}" density="0" condim="3" friction="0.5"/>'
                    for i in range(len(hs)))
        return assets, g
    aA, gA = geoms(hA, 'a', 1, 1)
    aB, gB = geoms(hB, 'b', 1 if collide else 2, 1 if collide else 2)
    return f'''<mujoco><option timestep="{1 / (FPS * SUB)}" gravity="0 0 0"/><asset>{aA}{aB}</asset><worldbody>
<body name="A">{gA}</body>
<body name="tgt" mocap="true"/>
<body name="B"><freejoint/><inertial pos="0 0 0" mass="0.3" diaginertia="0.002 0.002 0.0005"/>{gB}</body>
</worldbody><equality><weld body1="tgt" body2="B" solref="0.02 1"/></equality></mujoco>'''


def drive(xml, rel, t0, t1):
    import mujoco
    m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m)
    bid = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, 'B')
    q0 = R.from_matrix(rel[t0, :3, :3]).as_quat()[[3, 0, 1, 2]]
    d.qpos[:3] = rel[t0, :3, 3]; d.qpos[3:7] = q0; d.mocap_pos[0] = rel[t0, :3, 3]; d.mocap_quat[0] = q0
    mujoco.mj_forward(m, d)
    lt, lr, pen = [], [], []
    for t in range(t0, t1):
        d.mocap_pos[0] = rel[t, :3, 3]; d.mocap_quat[0] = R.from_matrix(rel[t, :3, :3]).as_quat()[[3, 0, 1, 2]]
        for _ in range(SUB):
            mujoco.mj_step(m, d)
        lt.append(np.linalg.norm(d.xpos[bid] - rel[t, :3, 3]) * 100)
        lr.append(R.from_matrix(rel[t, :3, :3].T @ d.xmat[bid].reshape(3, 3)).magnitude() * 180 / np.pi)
        pen.append(max([-d.contact[i].dist for i in range(d.ncon)] + [0.0]) * 1e3)
    return np.array(lt), np.array(lr), np.array(pen)


def proxy(hA, hB, cutA, cutB, rel, t0, t1, idx):
    out = {}; loc = idx[(idx >= t0) & (idx < t1)] - t0
    for name, xml in (('default', mjcf(hA, hB)), ('cut', mjcf(cutA, cutB)), ('nocollide', mjcf(hA, hB, collide=False))):
        lt, lr, pe = drive(xml, rel, t0, t1)
        out[name] = dict(lag_cm_asm_median=round(float(np.median(lt[loc])), 2), lag_deg_asm_median=round(float(np.median(lr[loc])), 1),
                         lag_cm_max=round(float(lt.max()), 2), lag_cm_end=round(float(lt[-1]), 2),
                         pen_mm_max=round(float(pe.max()), 1))
        print('proxy', name, out[name], flush=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='mode', required=True)
    s = sub.add_parser('slot'); s.add_argument('mesh_a'); s.add_argument('mesh_b'); s.add_argument('ref'); s.add_argument('out')
    s.add_argument('--names', nargs=2, default=['wooden_piece_1', 'wooden_piece_2'])
    s.add_argument('--proxy', action='store_true')
    a = ap.parse_args()
    rep, _ = slot(a)
    os.makedirs(a.out, exist_ok=True)
    json.dump(rep, open(f'{a.out}/carve.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ('rel_rot_assembled_B_axes_in_A',)}))


if __name__ == '__main__':
    main()
