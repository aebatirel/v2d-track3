"""Verifier's own settle + contact + hull-extraction run (scratch, 2026-10-30). Scene build follows settle_at2.py
(FlashCHORD setup_scene, CoACD on, support on, 1 world, CPU), but: assets from make_assets.py --pieces (training path),
collision hulls read back from the BUILT model (what the simulator really uses), contact counts (nacon/nefc) at reset and
max over the run, and the guest's vertical drift. Our reference only; no ground truth.
Usage: vsim.py --tree T --assets A --frames F1,F2 --steps 60 --out OUT.json  (writes OUT.npz with mesh-frame hulls)"""
import argparse, json, os, shutil, time
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--tree', required=True); ap.add_argument('--assets', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--frames', required=True); ap.add_argument('--steps', type=int, default=60)
a = ap.parse_args()
FC = os.environ['FC']
import pyarrow as pa, pyarrow.parquet as pq, warp as wp
from scipy.spatial.transform import Rotation as Rot

tag = os.path.splitext(os.path.basename(a.out))[0]
root = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'trees', tag)
src_pq = next(os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(a.tree, 'processed')) for f in fs if f.endswith('.parquet'))
seq = next(p.split('=', 1)[1] for p in src_pq.split(os.sep) if p.startswith('sequence_id='))
dst = os.path.join(root, 'processed', f'sequence_id={seq}', 'robot_name=sharpa_wave'); os.makedirs(dst, exist_ok=True)
os.makedirs(os.path.join(root, 'reconstructed_stage'), exist_ok=True)
shutil.copy(os.path.join(a.tree, 'reconstructed_stage', f'{seq}_support.usda'), os.path.join(root, 'reconstructed_stage'))
t = pq.read_table(src_pq); row = t.to_pylist()[0]; names = list(row['object_body_names'])
for k, v in {'object_urdf_paths': [os.path.abspath(f'{a.assets}/urdf/{n}_rigid.urdf') for n in names],
             'object_mesh_paths': [os.path.abspath(f'{a.assets}/mesh/{n}/{n}.glb') for n in names]}.items():
    i = t.column_names.index(k); t = t.set_column(i, k, pa.array([v], type=t.schema.field(k).type))
parquet = os.path.join(dst, 'ref.parquet'); pq.write_table(t, parquet)
pos = np.array(row['object_body_position'], float); quat = np.array(row['object_body_wxyz'], float)[..., [1, 2, 3, 0]]
nF = len(pos)

from hydra import compose, initialize_config_dir
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
import newton
with initialize_config_dir(version_base='1.3', config_dir=f'{FC}/src/flash_chord/configs'):
    cfg = compose(config_name='train_flash_sac', overrides=['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"])
env_config = instantiate_typed(cfg.env, RLEnvConfig); sc = env_config.sim
with wp.ScopedDevice('cpu'):
    st = setup_scene(parquet=parquet, control_fps=sc.fps, motion_speed=1.0, embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                     collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=1, include_support=True,
                     decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=env_config)
m = st.scene.model; sol = env.solver
labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
obj_body = [next(i for i, l in enumerate(labels) if l.startswith(f'track3_{n}/')) for n in names]
sb = m.shape_body.numpy(); sf = m.shape_flags.numpy(); collide = int(newton.ShapeFlags.COLLIDE_SHAPES)
info = dict(mjw_caps={k: int(getattr(sol.mjw_data, k)) for k in ('naconmax', 'njmax', 'nconmax') if hasattr(sol.mjw_data, k) and np.isscalar(getattr(sol.mjw_data, k))}, tree=a.tree, assets=a.assets, names=names, steps=a.steps, nconmax=int(sc.nconmax), njmax=int(sc.njmax),
            collide_shapes=[int(((sb == b) & ((sf & collide) != 0)).sum()) for b in obj_body], frames={})
child = m.joint_child.numpy(); qs = m.joint_q_start.numpy()
q0 = [int(qs[int(np.nonzero(child == b)[0][0])]) for b in obj_body]
dt = float(sc.sim_dt); sub = int(sc.substeps)
X = m.shape_transform.numpy(); SC = m.shape_scale.numpy()


def TT(p, qxyzw):
    T = np.eye(4); T[:3, :3] = Rot.from_quat(qxyzw).as_matrix(); T[:3, 3] = p; return T


def ref_T(k, f):
    return TT(pos[f, k], quat[f, k])


def body_T(state, k):
    bq = state.body_q.numpy()[obj_body[k]]; return TT(bq[:3], bq[3:7])


def bname(b):
    if b < 0:
        return 'world'
    l = labels[b]
    return next((n for n in names if l.startswith(f'track3_{n}/')), 'support' if 'support' in l else l.split('/')[0][:12])


def counts(detail=False):
    d = sol.mjw_data; out = {}
    for k in ('nacon', 'nefc'):
        v = getattr(d, k, None)
        if v is not None:
            out[k] = int(np.max(v.numpy() if hasattr(v, 'numpy') else v))
    try:
        n = out.get('nacon', 0); dist = d.contact.dist.numpy()[:n]
        out['min_dist_mm'] = round(float(dist.min()) * 1e3, 2) if n else None
        out['n_pen_gt2mm'] = int((dist < -0.002).sum())
        if detail and n:
            g = d.contact.geom.numpy()[:n]; g2s = sol.mjc_geom_to_newton_shape.numpy()[0]; pairs = {}
            for (ga, gb), dd in zip(g, dist):
                key = '-'.join(sorted([bname(int(sb[g2s[ga]])) if g2s[ga] >= 0 else 'mjgeom', bname(int(sb[g2s[gb]])) if g2s[gb] >= 0 else 'mjgeom']))
                c, mn = pairs.get(key, (0, 1.0)); pairs[key] = (c + 1, min(mn, float(dd)))
            out['pairs'] = {k: [c, round(mn * 1e3, 2)] for k, (c, mn) in pairs.items()}
    except Exception as e:  # noqa
        out['dist_err'] = str(e)[:80]
    return out


def err(Ta, Tb):
    return [round(float(np.linalg.norm(Ta[:3, 3] - Tb[:3, 3])) * 100, 2),
            round(float(np.degrees(Rot.from_matrix(Ta[:3, :3] @ Tb[:3, :3].T).magnitude())), 1)]


hulls_saved = False; npz = {}
with wp.ScopedDevice('cpu'):
    for nm in ('actuator_gainprm', 'actuator_biasprm'):
        arr = getattr(sol.mjw_model, nm); v = arr.numpy(); v[...] = 0; arr.assign(v)
    for F in [int(x) for x in a.frames.split(',')]:
        F = min(F, nF - 1)
        env.reset(frame_id=F); s0, s1 = env.state_0, env.state_1
        q = s0.joint_q.numpy().copy(); q[0:3] = [3.0, 0.0, 0.3]; q[29:32] = [-3.0, 0.0, 0.3]
        for k in range(len(names)):
            T = ref_T(k, F); q[q0[k]:q0[k] + 3] = T[:3, 3]; q[q0[k] + 3:q0[k] + 7] = Rot.from_matrix(T[:3, :3]).as_quat()
        s0.joint_q.assign(q.astype(np.float32)); s0.joint_qd.zero_(); newton.eval_fk(m, s0.joint_q, s0.joint_qd, s0)
        C = [np.linalg.inv(body_T(s0, k)) @ ref_T(k, F) for k in range(len(names))]
        if not hulls_saved:                                   # hulls as built, in each object's mesh frame
            for k, n in enumerate(names):
                hs = []
                for i in np.flatnonzero((sb == obj_body[k]) & ((sf & collide) != 0)):
                    src = m.shape_source[i]; V = np.asarray(src.vertices, float) * SC[i]
                    Tm = np.linalg.inv(C[k]) @ TT(X[i][:3], X[i][3:7])
                    hs.append(V @ Tm[:3, :3].T + Tm[:3, 3])
                npz[n + '_n'] = np.array([len(h) for h in hs]); npz[n] = np.vstack(hs)
            hulls_saved = True
        rows = []; nan = None; cmax = {}; c_reset = None
        for f in range(a.steps):
            for s in range(sub):
                s0.clear_forces(); sol.step(s0, s1, env.control, env.contacts, dt); s0, s1 = s1, s0
                c = counts(detail=c_reset is None)
                if c_reset is None:
                    c_reset = c
                for kk in ('nacon', 'nefc'):
                    cmax[kk] = max(cmax.get(kk, 0), c.get(kk, 0))
            if not np.all(np.isfinite(s0.body_q.numpy()[obj_body])):
                nan = f; break
            Tk = [body_T(s0, k) @ C[k] for k in range(len(names))]; Tr = [ref_T(k, F) for k in range(len(names))]
            r = dict(t=round((f + 1) * dt * sub, 2))
            for k, n in enumerate(names):
                r[n] = err(Tk[k], Tr[k]) + [round(float(Tk[k][2, 3] - Tr[k][2, 3]) * 100, 2)]   # cm, deg, dz world cm
            Ra = np.linalg.inv(Tk[0]) @ Tk[1]; Rr = np.linalg.inv(Tr[0]) @ Tr[1]
            # guest displacement in host frame, projected on the host-frame direction of world up at the reference
            up = Tr[0][:3, :3].T @ np.array([0, 0, 1.0])
            r['rel'] = err(Ra, Rr) + [round(float((Ra[:3, 3] - Rr[:3, 3]) @ up) * 100, 2)]
            rows.append(r)
        pick = lambda key, i: rows[min(i, len(rows) - 1)][key] if rows else None
        out = dict(nan_at_step=nan, contacts_reset=c_reset, contacts_max=cmax,
                   **{key: dict(at_2s=pick(key, 39), at_3s=pick(key, 59), min_dz_cm=min(x[key][2] for x in rows) if rows else None)
                      for key in names + ['rel']})
        info['frames'][str(F)] = out
        print(F, json.dumps(out), flush=True)
json.dump(info, open(a.out, 'w'), indent=1)
np.savez(a.out[:-5] + '.npz', **npz)
print('collide_shapes', info['collide_shapes'], 'nconmax', info['nconmax'], 'njmax', info['njmax'])
