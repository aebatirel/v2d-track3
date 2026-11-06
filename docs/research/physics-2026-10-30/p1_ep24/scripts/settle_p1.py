"""P1 settle (INTERLOCK 6.2) for one asset set at one reference frame, 16 jittered copies in FlashCHORD's own physics.
Extends docs/research/work/carve-20261030/scripts/settle_at.py (copied recipe: scene from a copy of the reference tree
with its object URDFs rewritten to ASSETS, CoACD decomposition on, support on, CPU, actuator gains zeroed, hands parked
3 m away, objects placed at the frame-F reference pose with zero velocity, SolverMuJoCo stepped at the env's sim_dt with
gravity and NO drive for STEPS control frames of 1/fps s).

Changes against settle_at.py (2026-10-31, determined-wright, for bold-albattani's P1 on gmg r0):
- K+1 worlds in one env (worlds are independent in MuJoCo-Warp; tools/physics_solve/jitter_check.py): world 0 = the
  nominal pose (reported, not in the means), worlds 1..K = jittered copies. Jitter per copy and per object: position
  N(0, SIG_POS) per world axis, rotation exp(N(0, SIG_ROT) per world axis) applied about the object's mesh origin
  (left-multiplied in the world frame). Draws come from default_rng(SEED) as an array (K, B, 6) in object order, so two
  asset sets run with the same SEED/K get the same start poses (common random numbers).
- EMB override (FlashCHORD embodiment config), hands parked by joint label (left/right_wrist_[xyz]).
- Metrics per copy (spec 6.2 P1): drift = |p(2 s) - p(0)| of the mesh-frame origin from the copy's own start pose,
  tilt = rotation angle of R(0)^T R(2 s); relative sink = -[(dp_guest - dp_host) . up] (up = +z, gravity -z);
  NaN; lowest collision-vertex height of each object at start / end vs the table top; fall-through flags.
- --snap_mm X (diagnostic variant, NOT the spec's literal P1): after jitter, each copy's pair is moved rigidly along z
  so that the lowest vertex of SNAP_PIECES (both objects) sits X mm above the table top; the relative pose is unchanged.
Our reference only; no ground truth is read.
Usage (FlashCHORD venv, from the flash_chord dir, FC=<flash_chord root>):
  EMB=sharpa_hands_mid settle_p1.py --tree REF_TREE --assets ASSETS --frame F --out OUT.json [--k 16 --seed 0
    --sig_pos 0.0005 --sig_rot 0.005 --steps 40 --host wooden_piece_1 --guest wooden_piece_2 --snap_mm X
    --snap_pieces DIR]"""
import argparse, glob, json, os, shutil, time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--tree', required=True); ap.add_argument('--assets', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--frame', type=int, required=True); ap.add_argument('--steps', type=int, default=40)
ap.add_argument('--k', type=int, default=16); ap.add_argument('--seed', type=int, default=0)
ap.add_argument('--sig_pos', type=float, default=0.0005); ap.add_argument('--sig_rot', type=float, default=0.005)
ap.add_argument('--host', default='wooden_piece_1'); ap.add_argument('--guest', default='wooden_piece_2')
ap.add_argument('--snap_mm', type=float, default=None); ap.add_argument('--snap_pieces', default='')
ap.add_argument('--table_tol_mm', type=float, default=2.0)
ap.add_argument('--only_copy', type=int, default=0, help='1..K: run ONE world holding jitter draw #c of the K-draw array (as-is 1-world recipe, CRN with the K-world runs)')
ap.add_argument('--sim_over', default='', help='comma-separated hydra overrides, e.g. sim.nconmax=4096,sim.njmax=16384')
a = ap.parse_args()
FC = os.environ['FC']
import pyarrow as pa, pyarrow.parquet as pq, warp as wp
import trimesh
from scipy.spatial.transform import Rotation as Rot

tag = os.path.splitext(os.path.basename(a.out))[0]
root = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'trees', tag)
src_pq = next(os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(a.tree, 'processed')) for f in fs if f.endswith('.parquet'))
seq = next(p.split('=', 1)[1] for p in src_pq.split(os.sep) if p.startswith('sequence_id='))
dst = os.path.join(root, 'processed', f'sequence_id={seq}', 'robot_name=sharpa_wave'); os.makedirs(dst, exist_ok=True)
os.makedirs(os.path.join(root, 'reconstructed_stage'), exist_ok=True)
sup = os.path.join(a.tree, 'reconstructed_stage', f'{seq}_support.usda')
shutil.copy(sup, os.path.join(root, 'reconstructed_stage'))
t = pq.read_table(src_pq); row = t.to_pylist()[0]; names = list(row['object_body_names'])
rep = {'object_urdf_paths': [os.path.abspath(f'{a.assets}/urdf/{n}_rigid.urdf') for n in names],
       'object_mesh_paths': [os.path.abspath(f'{a.assets}/mesh/{n}/{n}.glb') for n in names]}
for k, v in rep.items():
    i = t.column_names.index(k); t = t.set_column(i, k, pa.array([v], type=t.schema.field(k).type))
parquet = os.path.join(dst, 'ref.parquet'); pq.write_table(t, parquet)
pos = np.array(row['object_body_position'], float); quat = np.array(row['object_body_wxyz'], float)[..., [1, 2, 3, 0]]
nF = len(pos); F = a.frame; assert 0 <= F < nF
B = len(names); hk, gk = names.index(a.host), names.index(a.guest)

# table top from the support stage (cylinder: translate z + height / 2)
txt = open(sup).read()
import re
tz = float(re.search(r'xformOp:translate = \(([-\d.e]+), ([-\d.e]+), ([-\d.e]+)\)', txt).group(3))
th = float(re.search(r'double height = ([-\d.e]+)', txt).group(1))
table_top = tz + th / 2

# collision vertices (mesh frame) of the asset set, for lowest-point heights
def piece_verts(d, n):
    fs = sorted(glob.glob(f'{d}/mesh/{n}/col_*.obj')) or sorted(glob.glob(f'{d}/{n}/piece_*.obj'))
    return np.vstack([np.asarray(trimesh.load(f, force='mesh').vertices) for f in fs]), len(fs)
CV = {}; npieces = {}
for n in names:
    CV[n], npieces[n] = piece_verts(a.assets, n)
SV = {n: piece_verts(a.snap_pieces, n)[0] for n in names} if a.snap_mm is not None else None

from hydra import compose, initialize_config_dir
from flash_chord.configuration import instantiate_typed
from flash_chord.embodiments.base import Embodiment
from flash_chord.envs.rl import RLEnv, RLEnvConfig
from flash_chord.scene.collision import CollisionPolicy
from flash_chord.scene.setup import setup_scene
import newton
ov = ['experiment=sharpa_flash_sac', f"task.parquet='{parquet}'"] + ([f"embodiment={os.environ['EMB']}"] if os.environ.get('EMB') else [])
ov += [x for x in a.sim_over.split(',') if x]
with initialize_config_dir(version_base='1.3', config_dir=f'{FC}/src/flash_chord/configs'):
    cfg = compose(config_name='train_flash_sac', overrides=ov)
env_config = instantiate_typed(cfg.env, RLEnvConfig); sc = env_config.sim
W = 1 if a.only_copy else a.k + 1
t0 = time.time()
with wp.ScopedDevice('cpu'):
    st = setup_scene(parquet=parquet, control_fps=sc.fps, motion_speed=1.0, embodiment=instantiate_typed(cfg.embodiment, Embodiment),
                     collision=instantiate_typed(cfg.collision, CollisionPolicy), world_count=W, include_support=True,
                     decompose_objects=True)
    env = RLEnv(st.scene, st.reference, config=env_config)
m = st.scene.model; sol = env.solver
labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
jlab = list(getattr(m, 'joint_label', None) or getattr(m, 'joint_key', []))
jworld = m.joint_world.numpy(); child = m.joint_child.numpy(); qs = m.joint_q_start.numpy()
# per world: object body ids and their free-joint q starts; hand wrist prismatic coords
obj_body = np.zeros((W, B), int); q0 = np.zeros((W, B), int); wrist = {}
for j, l in enumerate(jlab):
    w = int(jworld[j]); cl = labels[child[j]]
    for k, n in enumerate(names):
        if cl == f'track3_{n}/object':
            obj_body[w, k] = child[j]; q0[w, k] = qs[j]
    for side in ('left', 'right'):
        for ax, c in zip('xyz', range(3)):
            if l == f'{side}_wrist_{ax}':
                wrist[(w, side, ax)] = int(qs[j])
sb = m.shape_body.numpy(); sf = m.shape_flags.numpy(); collide = int(newton.ShapeFlags.COLLIDE_SHAPES)
coll = {}
for k, n in enumerate(names):
    ids = np.nonzero((sb == obj_body[0, k]) & ((sf & collide) != 0))[0]
    vols = sorted(abs(trimesh.Trimesh(np.asarray(m.shape_source[s].vertices, float),
                                      np.asarray(m.shape_source[s].indices).reshape(-1, 3), process=False).volume) for s in ids)
    pv = sorted(abs(trimesh.load(f, force='mesh').volume) for f in sorted(glob.glob(f'{a.assets}/mesh/{n}/col_*.obj')))
    coll[n] = dict(collide_shapes=int(len(ids)), urdf_pieces=npieces[n], hull_vol_cm3=round(sum(vols) * 1e6, 3),
                   piece_vol_cm3=round(sum(pv) * 1e6, 3),
                   max_abs_sorted_vol_diff_cm3=round(float(np.max(np.abs(np.array(vols) - np.array(pv)))) * 1e6, 4)
                   if len(vols) == len(pv) else None)
info = dict(tree=os.path.abspath(a.tree), ref_parquet=src_pq, assets=os.path.abspath(a.assets), names=names, host=a.host,
            guest=a.guest, frame=F, k=a.k, seed=a.seed, sig_pos=a.sig_pos, sig_rot=a.sig_rot, steps=a.steps,
            snap_mm=a.snap_mm, snap_pieces=a.snap_pieces or None, table_top=table_top, emb=os.environ.get('EMB'),
            build_sec=round(time.time() - t0, 1), collision=coll,
            sim=dict(fps=float(sc.fps), substeps=int(sc.substeps), sim_dt=float(sc.sim_dt), nconmax=int(sc.nconmax),
                     njmax=int(sc.njmax), solver=sc.solver, cone=sc.cone, integrator=sc.integrator, iterations=int(sc.iterations)),
            hydra_overrides=ov)
print(json.dumps(info), flush=True)
dt = float(sc.sim_dt); sub = int(sc.substeps)


def ref_T(k, f):
    T = np.eye(4); T[:3, :3] = Rot.from_quat(quat[f, k]).as_matrix(); T[:3, 3] = pos[f, k]; return T


def body_T(bq):
    T = np.eye(4); T[:3, :3] = Rot.from_quat(bq[3:7]).as_matrix(); T[:3, 3] = bq[:3]; return T


def lowest(V, T):
    return float((V @ T[:3, :3].T + T[:3, 3])[:, 2].min())


def ang(Ra, Rb):
    return float(np.degrees(Rot.from_matrix(Ra.T @ Rb).magnitude()))


# start poses: world 0 nominal, worlds 1..K jittered (common random numbers: same SEED and K -> same draws)
rng = np.random.default_rng(a.seed)
J = rng.normal(size=(a.k, B, 6)); J[..., :3] *= a.sig_pos; J[..., 3:] *= a.sig_rot
T_start = np.zeros((W, B, 4, 4)); snap_dz = np.zeros(W)
for w in range(W):
    jw = a.only_copy - 1 if a.only_copy else w - 1                       # index into J; -1 = nominal
    for k in range(B):
        T = ref_T(k, F)
        if jw >= 0:
            Tj = np.eye(4); Tj[:3, :3] = Rot.from_rotvec(J[jw, k, 3:]).as_matrix() @ T[:3, :3]
            Tj[:3, 3] = T[:3, 3] + J[jw, k, :3]; T = Tj
        T_start[w, k] = T
    if a.snap_mm is not None:
        low = min(lowest(SV[n], T_start[w, k]) for k, n in enumerate(names))
        snap_dz[w] = table_top + a.snap_mm * 1e-3 - low
        T_start[w, :, 2, 3] += snap_dz[w]

with wp.ScopedDevice('cpu'):
    for nm in ('actuator_gainprm', 'actuator_biasprm'):
        arr = getattr(sol.mjw_model, nm); v = arr.numpy(); v[...] = 0; arr.assign(v)
    env.reset(frame_id=F)
    s0, s1 = env.state_0, env.state_1
    q = s0.joint_q.numpy().copy()
    for (w, side, ax), i in wrist.items():                                  # park the wrists far away
        q[i] = {'x': (3.0 if side == 'left' else -3.0), 'y': 0.0, 'z': 0.3}[ax]
    for w in range(W):
        for k in range(B):
            T = T_start[w, k]; i = q0[w, k]
            q[i:i + 3] = T[:3, 3]; q[i + 3:i + 7] = Rot.from_matrix(T[:3, :3]).as_quat()
    s0.joint_q.assign(q.astype(np.float32)); s0.joint_qd.zero_(); newton.eval_fk(m, s0.joint_q, s0.joint_qd, s0)
    bq0 = s0.body_q.numpy()
    C = np.zeros((W, B, 4, 4))
    for w in range(W):
        for k in range(B):
            C[w, k] = np.linalg.inv(body_T(bq0[obj_body[w, k]])) @ T_start[w, k]       # body -> mesh frame
    # float32 start as actually placed (mesh frame)
    T0 = np.array([[body_T(bq0[obj_body[w, k]]) @ C[w, k] for k in range(B)] for w in range(W)])
    series = [T0]; nan_at = np.full(W, -1); t1 = time.time(); ncon = []; nefc = []
    md = sol.mjw_data
    for f in range(a.steps):
        for s in range(sub):
            s0.clear_forces()
            sol.step(s0, s1, env.control, env.contacts, dt); s0, s1 = s1, s0
            ncon.append(int(np.asarray(md.nacon.numpy()).sum())); nefc.append(int(np.asarray(md.nefc.numpy()).max()))
        bq = s0.body_q.numpy()
        Tf = np.full((W, B, 4, 4), np.nan)
        for w in range(W):
            x = bq[obj_body[w]]
            if not np.all(np.isfinite(x)):
                if nan_at[w] < 0:
                    nan_at[w] = f
                continue
            for k in range(B):
                Tf[w, k] = body_T(x[k]) @ C[w, k]
        series.append(Tf)
    sim_sec = round(time.time() - t1, 1)
S_ = np.array(series)                                                    # (steps+1, W, B, 4, 4)
up = np.array([0, 0, 1.0])


def copy_metrics(w):
    if nan_at[w] >= 0:
        return dict(nan=True, nan_at_step=int(nan_at[w]))
    r = dict(nan=False)
    Tend = S_[-1, w]; Tb = S_[0, w]
    i1s = min(int(round(1.0 * sc.fps)), a.steps)
    for k, n in enumerate(names):
        d = np.linalg.norm(S_[:, w, k, :3, 3] - Tb[k, :3, 3], axis=1)
        tl = np.array([ang(Tb[k, :3, :3], S_[i, w, k, :3, :3]) for i in range(len(S_))])
        Tr = ref_T(k, F).copy(); Tr[2, 3] += snap_dz[w]
        r[n] = dict(drift_cm=round(float(d[-1]) * 100, 3), tilt_deg=round(float(tl[-1]), 3),
                    drift_cm_1frame=round(float(d[1]) * 100, 3), drift_cm_1s=round(float(d[i1s]) * 100, 3),
                    tilt_deg_1s=round(float(tl[i1s]), 3), peak_drift_cm=round(float(d.max()) * 100, 3),
                    peak_tilt_deg=round(float(tl.max()), 3),
                    drift_vs_ref_cm=round(float(np.linalg.norm(Tend[k, :3, 3] - Tr[:3, 3])) * 100, 3),
                    tilt_vs_ref_deg=round(ang(Tr[:3, :3], Tend[k, :3, :3]), 3),
                    dz_mm=round(float(Tend[k, 2, 3] - Tb[k, 2, 3]) * 1e3, 3),
                    low_start_mm=round((lowest(CV[n], Tb[k]) - table_top) * 1e3, 3),
                    low_end_mm=round((lowest(CV[n], Tend[k]) - table_top) * 1e3, 3))
    dh = Tend[hk, :3, 3] - Tb[hk, :3, 3]; dg = Tend[gk, :3, 3] - Tb[gk, :3, 3]
    r['rel_sink_mm'] = round(float(-(dg - dh) @ up) * 1e3, 3)
    R0 = np.linalg.inv(Tb[hk]) @ Tb[gk]; R1 = np.linalg.inv(Tend[hk]) @ Tend[gk]
    r['rel_change'] = dict(cm=round(float(np.linalg.norm(R1[:3, 3] - R0[:3, 3])) * 100, 3), deg=round(ang(R0[:3, :3], R1[:3, :3]), 3),
                           in_host_frame_mm=np.round((R1[:3, 3] - R0[:3, 3]) * 1e3, 3).tolist())
    g_low = r[a.guest]['low_end_mm']; h_low = r[a.host]['low_end_mm']
    r['guest_on_table_end'] = bool(g_low <= a.table_tol_mm)
    r['guest_below_host_lowest_end'] = bool(g_low < h_low)
    r['guest_low_minus_host_low_start_mm'] = round(r[a.guest]['low_start_mm'] - r[a.host]['low_start_mm'], 3)
    r['guest_low_minus_host_low_end_mm'] = round(g_low - h_low, 3)
    return r


copies = [copy_metrics(w) for w in range(W)]
jit = copies if a.only_copy else [c for c in copies[1:]]
ok = [c for c in jit if not c['nan']]


def mean(key, n=None):
    v = [c[n][key] if n else c[key] for c in ok]
    return round(float(np.mean(v)), 3) if v else None


summary = dict(copies=len(jit), finite=len(ok), nan=len(jit) - len(ok),
               host=dict(drift_cm=mean('drift_cm', a.host), tilt_deg=mean('tilt_deg', a.host)),
               guest=dict(drift_cm=mean('drift_cm', a.guest), tilt_deg=mean('tilt_deg', a.guest)),
               rel_sink_mm=mean('rel_sink_mm'),
               rel_change_cm=round(float(np.mean([c['rel_change']['cm'] for c in ok])), 3) if ok else None,
               rel_change_deg=round(float(np.mean([c['rel_change']['deg'] for c in ok])), 3) if ok else None,
               guest_on_table_end=int(sum(c['guest_on_table_end'] for c in ok)),
               guest_below_host_lowest_end=int(sum(c['guest_below_host_lowest_end'] for c in ok)))
for n in (a.host, a.guest):
    for key in ('drift_cm_1s', 'peak_drift_cm', 'peak_tilt_deg', 'drift_vs_ref_cm', 'tilt_vs_ref_deg', 'low_start_mm', 'low_end_mm', 'dz_mm'):
        summary['host' if n == a.host else 'guest'][key] = mean(key, n)
    for key in ('drift_cm', 'tilt_deg'):
        v = [c[n][key] for c in ok]
        summary['host' if n == a.host else 'guest'][key + '_sd'] = round(float(np.std(v)), 3) if v else None
        summary['host' if n == a.host else 'guest'][key + '_max'] = round(float(np.max(v)), 3) if v else None
TH = dict(drift_cm=1.0, tilt_deg=5.0, rel_sink_mm=4.0)
crit = dict(host_drift=bool(ok) and summary['host']['drift_cm'] <= TH['drift_cm'],
            guest_drift=bool(ok) and summary['guest']['drift_cm'] <= TH['drift_cm'],
            host_tilt=bool(ok) and summary['host']['tilt_deg'] <= TH['tilt_deg'],
            guest_tilt=bool(ok) and summary['guest']['tilt_deg'] <= TH['tilt_deg'],
            rel_sink=bool(ok) and summary['rel_sink_mm'] <= TH['rel_sink_mm'],
            no_nan=summary['nan'] == 0)
buffers = dict(max_total_contacts=int(max(ncon)), naconmax=int(md.naconmax) if hasattr(md, 'naconmax') else None,
               max_nefc_any_world=int(max(nefc)), njmax=int(md.njmax) if hasattr(md, 'njmax') else None,
               contacts_series=ncon[::sub])
out = dict(info=info, sim_sec=sim_sec, buffers=buffers, snap_dz_mm=np.round(snap_dz * 1e3, 3).tolist(), summary=summary,
           criteria_excl_fallthrough=crit, nominal=None if a.only_copy else copies[0], copies=jit, only_copy=a.only_copy,
           jitter_draws=np.round(J, 7).tolist())
json.dump(out, open(a.out, 'w'), indent=1)
np.savez_compressed(os.path.splitext(a.out)[0] + '_series.npz', T=S_.astype(np.float32), nan_at=nan_at, J=J, snap_dz=snap_dz)
print(json.dumps(dict(sim_sec=sim_sec, buffers={k: v for k, v in buffers.items() if k != 'contacts_series'}, summary=summary, criteria_excl_fallthrough=crit, nominal=copies[0])), flush=True)
