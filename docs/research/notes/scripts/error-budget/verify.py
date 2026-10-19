"""Check that budget.metrics() reproduces the official score() end to end on DataFrames."""
import base64, io
import numpy as np, pandas as pd
import budget as B
from budget import EPS, VERTS, MODS, metrics, jitter, body_offset, lag


def frames(pert, seed=0):
    sol, sub = [], []
    for e in EPS:
        p = e["pose"]; a = pert(p, np.random.default_rng(seed + e["ep"]), e)
        T, N, _ = p.shape
        for t in range(T):
            for j in range(N):
                rid = f"{e['ep']}_0_{t}_{j}"
                sol.append(dict(id=rid, episode_index=e["ep"], world_index=0, frame_index=t, object_slot=j,
                                object_name=e["names"][j], **{"ref_" + c: p[t, j, k] for k, c in enumerate(B.A._POSE_COLUMNS)}))
                sub.append(dict(id=rid, **{c: a[t, j, k] for k, c in enumerate(B.A._POSE_COLUMNS)},
                                eval_script_sha256="x", eval_code_sha256="x", checkpoint_sha256="x",
                                packer_script_sha256="x", uploader_script_sha256="x",
                                code_commit_url="https://github.com/a/b/commit/abcdef1"))
    sol, sub = pd.DataFrame(sol), pd.DataFrame(sub)
    buf = io.BytesIO(); np.savez(buf, **VERTS)
    sol["auc_vertex_samples_b64"] = ""; sol.loc[0, "auc_vertex_samples_b64"] = base64.b64encode(buf.getvalue()).decode()
    return sol, sub


def combo(p, rng, e):
    return body_offset(rot_deg=15, trans_cm=2)(jitter(1.0, rot_deg=2)(lag(2)(p, rng, e), rng, e), rng, e)


for name, pert in [("GT", lag(0)), ("combo", combo)]:
    sol, sub = frames(pert)
    off = {k: MODS[k].score(sol, sub, "id") for k in MODS}
    mine = {k: [] for k in ["AUC", "SPSR", "MPSR", "RPE", "MPPE"]}
    for e in EPS:
        m = metrics(pert(e["pose"], np.random.default_rng(0 + e["ep"]), e), e["pose"], e["names"])
        for k in mine: mine[k].append(m[k])
    print(name, "official:", {k: round(v, 6) for k, v in off.items()})
    print(name, "mine    :", {k: round(float(np.mean(v)), 6) for k, v in mine.items()})
