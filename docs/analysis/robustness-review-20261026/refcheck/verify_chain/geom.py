"""Scorer-free geometry checks of the reference chain (refcheck/verify_chain, 27 Oct 2026).

Part 1 (no ground truth): for each canonical episode with a reference,
  M_t^i = E_t^i inv(P_t^i)   E = e2s_reference.parquet body pose (table frame), P = perception poses_world_vo.npz.
  If mkref only applies one rigid world->table transform A plus a constant per-object shift dz_i along the table normal,
  M_t^i = Tz(dz_i) A for every t: constant in t, the same rotation for every object, and translations that differ only
  in z (table frame). Reports the deviations and the relative z shifts (object i minus slot 0), and compares with
  table_frame.npz object_z_shift and with poses.npz (world_T_cam @ cam_T_obj, what mkref actually reads).
  The same decomposition for proc (after contact retarget) vs e2s, and for the evaluator reference columns vs proc.
Part 2 (DIAGNOSTIC, reads public mocap after inference): frame-0 lowest point of every public scan at its mocap pose
  (all 20 public episodes), to get the table height and the ep26 pot-above-table height, and the xy overlap of
  pot / rack footprints in ep26 and ep27.
Usage: python -I geom.py OUT.json
"""
import json, os, sys, glob
import numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
ST = f'{SP}/store'; T3 = f'{SP}/t3'
C = json.load(open(f'{SP}/work/canonical_refs.json'))['episodes']
PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]


def H(pos, wxyz):
    M = np.tile(np.eye(4), pos.shape[:2] + (1, 1))
    q = wxyz / np.linalg.norm(wxyz, axis=-1, keepdims=True)
    M[..., :3, :3] = Rot.from_quat(q[..., [1, 2, 3, 0]].reshape(-1, 4)).as_matrix().reshape(pos.shape[:2] + (3, 3))
    M[..., :3, 3] = pos
    return M


def refpq(path, names):
    t = pq.read_table(path, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    bn = t.column('object_body_names')[0].as_py(); idx = [bn.index(n) for n in names]
    return H(np.array(t.column('object_body_position')[0].as_py())[:, idx], np.array(t.column('object_body_wxyz')[0].as_py())[:, idx])


def resref(d, names):
    f = glob.glob(f'{d}/episode_*.parquet')[0]
    x = pq.read_table(f).to_pandas(); x = x[x.environment_id == x.environment_id.min()].sort_values(['reference_frame', 'object_body_id'])
    T = x.reference_frame.nunique(); B = len(names)
    pos = x[[f'reference_position_{c}' for c in 'xyz']].values.reshape(T, B, 3)
    q = x[[f'reference_quaternion_{c}' for c in 'xyzw']].values.reshape(T, B, 4)
    assert list(x.object_body_name.values[:B]) == names
    return H(pos, q[..., [3, 0, 1, 2]]), np.sort(x.reference_frame.unique())


def rel(A, Bm):
    """M_t^i = A_t^i inv(B_t^i); returns stats of constancy and per-object relative shift in A's frame"""
    M = np.einsum('tbij,tbjk->tbik', A, np.linalg.inv(Bm))
    T, B = M.shape[:2]
    out = {}
    M0 = M[0]
    for b in range(B):
        dR = np.einsum('tji,jk->tik', M[:, b, :3, :3], M0[b, :3, :3])
        out_b = dict(max_rot_change_over_t_deg=float(np.degrees(Rot.from_matrix(dR).magnitude()).max()),
                     max_trans_change_over_t_mm=float(np.linalg.norm(M[:, b, :3, 3] - M0[b, :3, 3], axis=-1).max() * 1000))
        Rrel = M0[b, :3, :3].T @ M0[0, :3, :3]
        out_b['rot_vs_slot0_deg'] = float(np.degrees(Rot.from_matrix(Rrel).magnitude()))
        out_b['trans_vs_slot0_mm_xyz'] = ((M0[b, :3, 3] - M0[0, :3, 3]) * 1000).round(2).tolist()
        out[b] = out_b
    return M, out


def per_frame_change(A, Bm):
    """for path A vs path B both in the SAME frame: per object max position change (mm) and rotation change (deg)"""
    d = np.linalg.norm(A[..., :3, 3] - Bm[..., :3, 3], axis=-1) * 1000
    R = np.einsum('tbji,tbjk->tbik', A[..., :3, :3], Bm[..., :3, :3])
    ang = np.degrees(Rot.from_matrix(R.reshape(-1, 3, 3)).magnitude()).reshape(R.shape[:2])
    return d, ang


res = {'part1': {}, 'part2': {}}
for e in C:
    if not e['ref_path']:
        continue
    ep = e['ep']
    objs = pq.read_table(f'{T3}/ep{ep}.parquet', columns=['observation.objects']).column(0)[0].as_py()
    names = [o['name'] for o in objs]
    P = np.load(f"{ST}/{e['perception_path']}"); Pm = np.stack([P[n] for n in names], 1)
    r = dict(names=names)
    pp = os.path.join(os.path.dirname(f"{ST}/{e['perception_path']}"), 'poses.npz')
    if os.path.exists(pp):
        Q = np.load(pp); W = Q['world_T_cam']
        Pc = np.stack([np.einsum('tij,tjk->tik', W, Q[f'cam_T_{n}']) for n in names], 1)
        d, ang = per_frame_change(Pc, Pm)
        r['poses_npz_vs_world_vo'] = dict(max_mm=round(float(d.max()), 4), max_deg=round(float(ang.max()), 4))
    E = refpq(f"{ST}/{e['ref_pre_contact_retarget']}", names)
    M, st = rel(E, Pm)
    r['mkref'] = {names[b]: v for b, v in st.items()}
    tf = os.path.join(f"{ST}/{e['ref_path']}", 'table_frame.npz')
    if os.path.exists(tf):
        z = np.load(tf); zn = [str(x) for x in z['names']]
        sh = np.array([float(z['object_z_shift'][zn.index(n)]) for n in names])
        r['table_frame_object_z_shift_cm'] = dict(zip(names, (sh * 100).round(3).tolist()))
        r['table_frame_rel_shift_cm'] = dict(zip(names, ((sh - sh[0]) * 100).round(3).tolist()))
        A = z['T_table_from_world']
        r['A_vs_M0_slot0'] = dict(rot_deg=float(np.degrees(Rot.from_matrix(A[:3, :3].T @ M[0, 0, :3, :3]).magnitude())),
                                   trans_mm=float(np.linalg.norm(A[:3, 3] - M[0, 0, :3, 3]) * 1000), z_mm=float((M[0, 0, 2, 3] - A[2, 3]) * 1000))
    else:
        r['table_frame'] = 'missing in ref_path'
    Pr = refpq(f"{ST}/{e['ref_parquet']}", names)
    d, ang = per_frame_change(Pr, E)
    r['contact_retarget_change'] = {n: dict(max_mm=round(float(d[:, b].max()), 3), mean_mm=round(float(d[:, b].mean()), 3),
                                            max_deg=round(float(ang[:, b].max()), 3), frames_over_1mm=int((d[:, b] > 1).sum()))
                                    for b, n in enumerate(names)}
    if e['results_dir']:
        Rr, fr = resref(f"{ST}/{e['results_dir']}/r1", names)
        G, st2 = rel(Rr, Pr[fr])
        r['evaluator_ref_vs_proc'] = {names[b]: v for b, v in st2.items()}
        r['evaluator_frames'] = [int(fr.min()), int(fr.max()), int(len(fr))]
    res['part1'][ep] = r
    print(ep, json.dumps(r)[:1500], flush=True)

# part 2: mocap bottoms (diagnostic)
scan = {}
for ep in PUBLIC:
    objs = pq.read_table(f'{T3}/ep{ep}.parquet', columns=['observation.objects']).column(0)[0].as_py()
    rr = {}
    for o in objs:
        n = o['name']
        if n not in scan:
            q = f'{T3}/mesh/{n}/{n}.glb'
            scan[n] = np.asarray(trimesh.load(q if os.path.exists(q) else f'{T3}/mesh/{n}/{n}_visual.glb', force='mesh').vertices)
        p = np.asarray(o['pose'], float)
        Rm = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix()
        V = scan[n] @ Rm.T + p[:3]
        rr[n] = dict(bottom_z_m=round(float(V[:, 2].min()), 5), xy_min=V[:, :2].min(0).round(4).tolist(),
                     xy_max=V[:, :2].max(0).round(4).tolist(), top_z_m=round(float(V[:, 2].max()), 4))
    res['part2'][ep] = rr
json.dump(res, open(sys.argv[1], 'w'), indent=1, default=lambda x: x if not isinstance(x, np.generic) else x.item())
for ep, rr in res['part2'].items():
    print(ep, {n: v['bottom_z_m'] for n, v in rr.items()})
