"""Official-scorer wrapper for agent 11 stage B. Calls the kit's own score() of AUC/SP-SR/MP-SR/RPE/MPPE on synthetic
solution/submission frames built from public GT (reference) and a modelled 'achieved' trajectory. Research only."""
from c11 import *
import base64, io
import pandas as pd

MET = {m: load_metric(m) for m in ["AUC", "SP-SR", "MP-SR", "RPE", "MPPE"]}
_V = {}


def verts(nm):
    if nm not in _V:
        _V[nm] = surface_points(nm, 500, 0)
    return _V[nm]


def _payload(names):
    buf = io.BytesIO(); np.savez(buf, **{n: verts(n) for n in names}); return base64.b64encode(buf.getvalue()).decode()


PROV = dict(eval_script_sha256="0" * 64, eval_code_sha256="0" * 64, checkpoint_sha256="0" * 64,
            packer_script_sha256="0" * 64, uploader_script_sha256="0" * 64,
            code_commit_url="https://github.com/local/research/commit/0000000")
COLS = ["pos_x", "pos_y", "pos_z", "quat_x", "quat_y", "quat_z", "quat_w"]


def frames(ach, ref, names, ep=0):
    """ach/ref: (T,B,7) xyz + quat xyzw.  Returns (solution, submission) DataFrames for one episode, one world."""
    T, B, _ = ref.shape
    f = np.repeat(np.arange(T), B); s = np.tile(np.arange(B), T)
    rid = [f"{ep}_0_{a}_{b}" for a, b in zip(f, s)]
    sol = pd.DataFrame({"id": rid, "episode_index": ep, "world_index": 0, "frame_index": f, "object_slot": s,
                        "object_name": [names[b] for b in s]})
    for k, c in enumerate(COLS):
        sol["ref_" + c] = ref[:, :, k].reshape(-1)
    sol["auc_vertex_samples_b64"] = ""; sol.loc[0, "auc_vertex_samples_b64"] = _payload(sorted(set(names)))
    sub = pd.DataFrame({"id": rid})
    for k, c in enumerate(COLS):
        sub[c] = ach[:, :, k].reshape(-1)
    for k, v in PROV.items():
        sub[k] = v
    return sol, sub


def score_all(ach, ref, names, ep=0):
    sol, sub = frames(ach, ref, names, ep)
    out = {}
    for m, mod in MET.items():
        out[m] = float(mod.score(sol, sub, "id"))
    return out


def spin(p, j, deg, axis):
    """constant body-frame rotation of object j by deg about body axis, every frame."""
    o = p.copy(); q = Rot.from_rotvec(np.radians(deg) * np.asarray(axis, float)).as_quat()
    o[:, j, 3:] = (Rot.from_quat(p[:, j, 3:]) * Rot.from_quat(q)).as_quat(); return o


def mean_metrics(L):
    return {k: float(np.mean([d[k] for d in L])) for k in L[0]}
