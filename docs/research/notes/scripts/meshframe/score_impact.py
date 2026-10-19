"""Score impact of a spoon mesh-frame mismatch, using the kit's Track 3 scorer functions.

Achieved poses are synthesised from public GT: achieved_b(t) = GT_b(t) o M_b, with M = ref_T_ours
(our frame expressed in the reference scan frame) applied only to the body playing the spoon.
Optional smooth tracking noise is added to all bodies (paired across perturbations).

Settings
  slot1 : 2-object public episodes; slot-1 body = spoon proxy (eval: 7 spoon episodes)
  slot0 : slot-0 body of every public episode, scored alone (eval: 3 single-spoon episodes 35-37)
AUC vertices: public-scan surface samples for real bodies; a canonicalised parametric spoon for
the spoon proxy (organisers' AUC vertex payload is not public).
"""
import glob, importlib.util, io, base64, json, os, sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import trimesh
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "..")
KIT = os.path.join(SCR, "kit_v2", "v2d_submission_kit", "metric_code", "track_3")
sys.path.insert(0, HERE)
from canon import spoon_mesh, canonical_frame, apply, sample_surface  # noqa: E402


def load_metric(fname):
    spec = importlib.util.spec_from_file_location(fname.replace("-", "_"), os.path.join(KIT, fname + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


MODS = {k: load_metric(k) for k in ["AUC", "SP-SR", "MP-SR", "RPE", "MPPE"]}
S = MODS["MPPE"]  # shared helpers are identical across files (verified by diff)

# ---------------------------------------------------------------- data
MESH = os.path.join(SCR, "t3", "public", "mesh")


def mesh_samples(name, n=1000):
    p = f"{MESH}/{name}/{name}.glb"
    if not os.path.exists(p):
        p = f"{MESH}/{name}/{name}_visual.glb"
    m = trimesh.load(p, force="mesh", process=False)
    return sample_surface(np.asarray(m.vertices, float), np.asarray(m.faces), n, seed=0)


V0, F0 = spoon_mesh()
R0, c0, _ = canonical_frame(V0, F0, "skew_x")
SPOON_V = sample_surface(apply(V0, R0, c0), F0, 1000, seed=0)


def load_episode(f):
    t = pq.read_table(f).to_pandas().sort_values("frame_index")
    names = [o["name"] for o in t["observation.objects"].iloc[0]]
    P = np.array([[np.asarray(o["pose"], float) for o in objs] for objs in t["observation.objects"]])  # T,B,7 wxyz
    vis = np.array([[bool(o["visible"]) for o in objs] for objs in t["observation.objects"]])
    assert vis.all()
    out = np.concatenate([P[..., :3], P[..., 4:7], P[..., 3:4]], -1)  # -> x y z qx qy qz qw
    return names, out


EPIS = {int(os.path.basename(f)[8:14]): load_episode(f)
        for f in sorted(glob.glob(os.path.join(SCR, "t3", "public", "data", "chunk-000", "*.parquet")))}

# ---------------------------------------------------------------- perturbations


def perturb(pose, Rm, tm):
    """pose (T,7) xyzw -> pose o M."""
    R = Rot.from_quat(pose[:, 3:])
    p = pose[:, :3] + R.apply(tm)
    q = (R * Rot.from_matrix(Rm)).as_quat()
    return np.concatenate([p, q], 1)


def noise(pose, sp, sr_deg, seed):
    if sp == 0 and sr_deg == 0:
        return pose
    rng = np.random.default_rng(seed)
    T = len(pose)
    def smooth(n):
        x = gaussian_filter1d(rng.normal(size=(T, 3)), 20, axis=0, mode="nearest")
        return x / x.std(0, keepdims=True)
    dp = smooth(T) * sp / np.sqrt(3)
    dr = smooth(T) * np.radians(sr_deg) / np.sqrt(3)
    R = Rot.from_quat(pose[:, 3:]) * Rot.from_rotvec(dr)
    return np.concatenate([pose[:, :3] + dp, R.as_quat()], 1)


def metrics(ach, ref, verts, ids):
    """ach/ref (T,1,B,7) xyzw. Mirrors score(): normalise, warp, metric."""
    ach = S._normalise_quaternions(ach, "submission", ValueError)
    ref = S._normalise_quaternions(ref, "solution", ValueError)
    w = S._warp_to_reference_start(ach, ref)
    return dict(
        AUC=MODS["AUC"]._add_auc(MODS["AUC"]._object_add(w, ref, verts)),
        SPSR=float(np.mean(MODS["SP-SR"]._spider_success(w, ref))),
        MPSR=float(np.mean(MODS["MP-SR"]._maniptrans_success(w, ref, ids))),
        RPE=MODS["RPE"]._relative_position_error_cm(w, ref),
        MPPE=MODS["MPPE"]._mean_per_point_error_cm(w, ref),
        spoon_pos_cm=float(np.linalg.norm(w[:, 0, -1, :3] - ref[:, 0, -1, :3], axis=-1).mean() * 100),
        spoon_rot_deg=float(np.degrees(S._quaternion_geodesic_angle(w[:, 0, -1, 3:], ref[:, 0, -1, 3:]).mean())),
    )


def rx(d): return Rot.from_euler("x", d, degrees=True).as_matrix()
def ry(d): return Rot.from_euler("y", d, degrees=True).as_matrix()
def rz(d): return Rot.from_euler("z", d, degrees=True).as_matrix()


I3, Z3 = np.eye(3), np.zeros(3)
PERTS = {"none": (I3, Z3)}
for ax, f in zip("xyz", (rx, ry, rz)):
    PERTS[f"flip180_{ax}"] = (f(180), Z3)
for deg in (2, 5, 10, 20):
    for ax, f in zip("xyz", (rx, ry, rz)):
        PERTS[f"rot{deg}_{ax}"] = (f(deg), Z3)
for cm in (0.5, 1.0, 2.0):
    for i, ax in enumerate("xyz"):
        t = np.zeros(3); t[i] = cm / 100
        PERTS[f"off{cm}cm_{ax}"] = (I3, t)
PERTS["flip180_z+off1cm_z"] = (rz(180), np.array([0, 0, 0.01]))
PERTS["rot5_x+off1cm_z"] = (rx(5), np.array([0, 0, 0.01]))
PERTS["rot90_z"] = (rz(90), Z3)


def run(setting, noise_cfg):
    rows = []
    for ep, (names, P) in EPIS.items():
        if setting == "slot1":
            if len(names) < 2:
                continue
            bodies = [0, 1]
        else:
            bodies = [0]
        ref = P[:, bodies]  # T,B,7
        verts = np.stack([mesh_samples(names[b]) for b in bodies[:-1]] + [SPOON_V])
        ids = np.arange(len(bodies))
        # spoon proxy's motion statistic
        Rr = Rot.from_quat(ref[:, -1, 3:])
        maxrot = float(np.degrees((Rr[0].inv() * Rr).magnitude()).max())
        maxdisp = float(np.linalg.norm(ref[:, -1, :3] - ref[0, -1, :3], axis=1).max())
        for pname, (Rm, tm) in PERTS.items():
            ach = ref.copy()
            for j, b in enumerate(bodies):
                ach[:, j] = noise(ach[:, j], *noise_cfg, seed=1000 * ep + b)
            ach[:, -1] = perturb(ach[:, -1], Rm, tm)
            m = metrics(ach[:, None], ref[:, None], verts, ids)
            rows.append(dict(setting=setting, noise=f"{noise_cfg[0]*100:.0f}cm/{noise_cfg[1]:.0f}deg", ep=ep,
                             host=names[bodies[-1]], host_maxrot_deg=maxrot, host_maxdisp_m=maxdisp, pert=pname, **m))
    return rows


def check_full_score():
    """Cross-check the in-process path against the kit's score() on one episode."""
    names, P = EPIS[0]
    ref = P[:, :2]
    ach = ref.copy(); ach[:, 1] = perturb(ach[:, 1], rz(180), np.array([0, 0, 0.01]))
    T = len(ref)
    rows = []
    for t in range(T):
        for b in range(2):
            r = dict(row_id=f"r{t}_{b}", episode_index=0, world_index=0, frame_index=t, object_slot=b, object_name=names[b])
            for k, v in zip(S._POSE_COLUMNS, ref[t, b]): r["ref_" + k] = v
            for k, v in zip(S._POSE_COLUMNS, ach[t, b]): r[k] = v
            rows.append(r)
    df = pd.DataFrame(rows)
    buf = io.BytesIO(); np.savez(buf, **{names[0]: mesh_samples(names[0]), names[1]: SPOON_V})
    sol = df[["row_id", "episode_index", "world_index", "frame_index", "object_slot", "object_name"] + S._REF_COLUMNS].copy()
    sol["auc_vertex_samples_b64"] = ""; sol.loc[0, "auc_vertex_samples_b64"] = base64.b64encode(buf.getvalue()).decode()
    sub = df[["row_id"] + S._POSE_COLUMNS].copy()
    for c in S._PROVENANCE_COLUMNS: sub[c] = "x"
    sub["code_commit_url"] = "https://github.com/a/b/commit/abcdef1"
    full = {k: MODS[k].score(sol, sub, "row_id") for k in MODS}
    verts = np.stack([mesh_samples(names[0]), SPOON_V])
    mine = metrics(ach[:, None], ref[:, None], verts, np.arange(2))
    print("score() check:", {k: round(v, 6) for k, v in full.items()})
    print("in-process   :", {k: round(v, 6) for k, v in mine.items()})


if __name__ == "__main__":
    check_full_score()
    rows = []
    for setting in ("slot1", "slot0"):
        for ncfg in ((0.0, 0.0), (0.01, 5.0), (0.02, 10.0)):
            rows += run(setting, ncfg)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(HERE, "score_impact_rows.csv"), index=False)
    print("rows:", len(df))
