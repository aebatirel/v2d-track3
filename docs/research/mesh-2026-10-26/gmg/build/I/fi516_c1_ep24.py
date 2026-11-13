"""T-I17 c1, the validity check of contact gate G1 (PREREG F-I5.16 (1)(h)); run 1 Nov in the collision-carve round-2
Eval-carves step to fix verify_cc2_0 B1 (c1 had been skipped on the false premise that the ep24 bundle was absent).

What the rule says: G1's engine and options (gmg/contactgate5.py: plain MuJoCo, the sim=rl options and limits from
docs/research/work/15-verify/cfg_sim_rl.yaml, sha256 checked, mesh geoms condim 3 friction 1.0, uniform-solid props
at 0.3 kg from simpieces.props, limits applied to the counts) on the round-2 ep24 board-slot r0
(build/I/results/slot2-ep24/fi4o/r0: carved 57 / 77 pieces, _default 50 / 71; read only) at f246 with both boards free
(the settle scene), poses = determined-wright's reference at f246 (our P_sel plus their constant world-z shifts),
a table plane at their table top, their 16 draws (default_rng(0).normal((16, 2, 6)), 0.5 mm and 0.005 rad per axis on
both objects, rotation left-multiplied in the world frame about the mesh origin), 2 s.
Pass iff the carved set overflows in >= 15 of 16 copies, the default in none, and max nefc carved / default >= 3
(theirs in MuJoCo-Warp with large buffers: 2027 / 416). Fail -> G1 (plain MuJoCo) is weaker than MuJoCo-Warp, and no
F-I5 delivery is called usable before G1 has run in MuJoCo-Warp.

Poses come from an npz written by <scratch>/cc2eval/scripts/ref24_pose.py (standalone, outside the gmg guard, which
refuses .parquet paths) from our own reference ref_gl_ilc.parquet (md5 699fe426..., columns object_body_names /
object_body_position / object_body_wxyz only) and its support stage (md5 debb7ad9..., table top z = 0.600 m).
No ground truth: our perception's reference, our pieces.

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/build/I/fi516_c1_ep24.py --pose <npz> --out <json>
"""
import argparse
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
if MR not in sys.path:
    sys.path.insert(0, MR)
R0 = os.path.join(HERE, 'results', 'slot2-ep24', 'fi4o', 'r0')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pose', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--copies', type=int, default=16); ap.add_argument('--secs', type=float, default=2.0)
    ap.add_argument('--sets', default='carved,default')
    a = ap.parse_args()
    import numpy as np
    import trimesh
    import mujoco
    from scipy.spatial.transform import Rotation as Rot
    from gmg import contactgate5 as CG, simpieces as SP

    cfg = CG.sim_rl()                      # raises if the sha256 or a value differs from PREREG F-I5.16
    opt = CG.options(cfg)
    P = np.load(a.pose)
    names = [str(x) for x in P['names']]
    host, guest = 'wooden_piece_1', 'wooden_piece_2'        # determined-wright RESULT section 3 (host board 1)
    pos, wxyz, top = np.asarray(P['pos'], float), np.asarray(P['wxyz'], float), float(P['table_top'])

    def T_ref(k):
        T = np.eye(4)
        T[:3, :3] = Rot.from_quat(wxyz[k][[1, 2, 3, 0]]).as_matrix()
        T[:3, 3] = pos[k]
        return T

    rng = np.random.default_rng(0)
    J = rng.normal(size=(a.copies, len(names), 6))
    J[..., :3] *= 0.0005
    J[..., 3:] *= 0.005
    starts = []
    for c in range(-1, a.copies):                             # -1 = the nominal pose (reported, not in the verdict)
        Ts = {}
        for k, n in enumerate(names):
            T = T_ref(k)
            if c >= 0:
                Tj = np.eye(4)
                Tj[:3, :3] = Rot.from_rotvec(J[c, k, 3:]).as_matrix() @ T[:3, :3]
                Tj[:3, 3] = T[:3, 3] + J[c, k, :3]
                T = Tj
            Ts[n] = T
        starts.append(Ts)
    table = (np.array([0.0, 0.0, 1.0]), -top)                 # plane z = table top, gravity -z
    steps = int(round(a.secs / opt['timestep']))
    sets = {'carved': R0, 'default': os.path.join(R0, '_default')}
    out = dict(check='T-I17 c1 (PREREG F-I5.16 (1)(h))', r0=os.path.relpath(R0, MR), pose_npz=a.pose,
               frame=int(P['frame']), names=names, host=host, guest=guest, table_top_m=top,
               sim_rl=dict(path=cfg['path'], sha256=cfg['sha256'], sha_matches_prereg=cfg['sha_matches_prereg']),
               options=opt, steps=steps, copies=a.copies, draws='default_rng(0).normal((16, 2, 6)), pos x 0.0005 m, '
               'rotvec x 0.005 rad, R_j @ R about the mesh origin, both objects (determined-wright settle_p1.py)',
               versions=dict(mujoco=mujoco.__version__, trimesh=trimesh.__version__), sets={})
    for name in a.sets.split(','):
        d0 = sets[name]
        pcs = {o: [np.asarray(trimesh.load(f, force='mesh').vertices, float)
                   for f in sorted(glob.glob(os.path.join(d0, o, 'piece_*.obj')))] for o in (host, guest)}
        hp, gp = SP.props(pcs[host], CG.k_('mass_kg')), SP.props(pcs[guest], CG.k_('mass_kg'))
        low = {o: round(float(min((V @ starts[0][o][:3, :3].T + starts[0][o][:3, 3])[:, 2].min()
                                  for V in pcs[o]) - top) * 1e3, 2) for o in (host, guest)}
        rows = []
        t0 = time.time()
        for ci, Ts in enumerate(starts):
            m = mujoco.MjModel.from_xml_string(CG.scene_xml('settle', pcs[host], pcs[guest], Ts[host], Ts[guest],
                                                            table, hp, gp, opt))
            d = mujoco.MjData(m)
            mujoco.mj_forward(m, d)
            n0 = dict(ncon=int(d.ncon), nefc=int(d.nefc))          # the start pose's collision pass (mj_forward)
            q_start = np.array(d.qpos, float).copy()
            r = CG.count_copy(m, d, steps, opt)
            r['copy'] = ci                                       # 0 = nominal, 1..16 = draws 0..15
            r['at_forward'] = n0
            q_end = np.array(d.qpos, float)                      # free joints: H qpos[0:7], G qpos[7:14]
            r['end'] = {o: dict(dz_mm=round(float(q_end[7 * i + 2] - q_start[7 * i + 2]) * 1e3, 2),
                                drift_mm=round(float(np.linalg.norm(q_end[7 * i:7 * i + 3] - q_start[7 * i:7 * i + 3]))
                                               * 1e3, 2))
                        for i, o in enumerate((host, guest))}
            r['end_ncon'], r['end_nefc'] = int(d.ncon), int(d.nefc)
            rows.append(r)
            print(name, ci, r['max_ncon'], r['max_nefc'], r['overflow'], round(time.time() - t0, 1), flush=True)
        jit = [r for r in rows if r['copy'] > 0]
        out['sets'][name] = dict(dir=os.path.relpath(d0, MR), pieces=[len(pcs[host]), len(pcs[guest])],
                                 lowest_vertex_above_table_mm_nominal=low,
                                 max_nefc=int(max(r['max_nefc'] for r in jit)),
                                 median_max_nefc=float(np.median([r['max_nefc'] for r in jit])),
                                 max_ncon=int(max(r['max_ncon'] for r in jit)),
                                 median_max_ncon=float(np.median([r['max_ncon'] for r in jit])),
                                 overflow_copies=int(sum(r['overflow'] for r in jit)),
                                 nan_copies=int(sum(r['nan'] for r in jit)), secs=round(time.time() - t0, 1),
                                 nominal=rows[0], per_copy=jit)
        json.dump(out, open(a.out, 'w'), indent=1)
    S = out['sets']
    if 'carved' in S and 'default' in S:
        c, dft = S['carved'], S['default']
        ratio = c['max_nefc'] / max(dft['max_nefc'], 1)
        legs = dict(carved_overflow_ge_15=bool(c['overflow_copies'] >= 15), default_overflow_none=bool(
            dft['overflow_copies'] == 0), ratio_ge_3=bool(ratio >= 3.0))
        out['verdict'] = dict(pass_=bool(all(legs.values())), legs=legs, ratio_carved_default=round(ratio, 3),
                              target_mujoco_warp=dict(carved_max_nefc=2027, default_max_nefc=416,
                                                      carved_overflow='16/16', default_overflow='0/16',
                                                      source='determined-wright p1_ep24 RESULT.md (3c7fd32)'))
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps(out.get('verdict')), flush=True)


if __name__ == '__main__':
    main()
