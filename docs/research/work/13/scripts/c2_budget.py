"""Stage C retry: does the kit's 4,096-face / 4,096-vertex mesh budget hurt a thin spoon template?
The packer (v2dlb/mesh_budget.py) decimates only when the welded mesh has > 4,096 faces, so we test a template
emitted NATIVELY under budget (no decimation on our side). The organisers' reference is decimated with
fast_simplification (not installed here); its proxy is the true spoon uniformly re-tessellated at the budget
(pessimistic: quadric decimation keeps shape better per face).
Usage: c2_budget.py N seed  -> out/c2_budget_<seed>.jsonl"""
import sys, json, importlib.util, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import spoon_model as sm
import c_cdo as cc

N, seed = int(sys.argv[1]), int(sys.argv[2])
cc.rng = np.random.default_rng(seed)
OUT = f"/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c2_budget_{seed}.jsonl"
HI = dict(ns=300, nphi=48, ns_sph=24, n_cyl=24)
LO = dict(ns=64, nphi=24, ns_sph=8, n_cyl=12)


def build(p, res, markers=True):
    cc.sphere = lambda *a, **k: sm.sphere(*a, n=res["ns_sph"], **k)
    cc.cylinder = lambda *a, **k: sm.cylinder(*a, n=res["n_cyl"], **k)
    V, F = cc.spoon(p, markers, ns=res["ns"], nphi=res["nphi"])
    T = V[F]; ar = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    return V, F[ar > 1e-14]


for i in range(N):
    p = cc.draw(); q = cc.fitted(p); sd = int(cc.rng.integers(1 << 30))
    th, tl = build(p, HI), build(p, LO)
    oh, ol = build(q, HI), build(q, LO)
    fth, ftl, foh, fol = (cc.frame(*m) for m in (th, tl, oh, ol))
    rec = dict(i=i, nF_lo=int(len(ol[1])), nV_lo=int(len(ol[0])), nF_hi=int(len(oh[1])),
               sk_true=np.round(fth[2], 4).tolist(),
               cdo=dict(truthlo_vs_truthhi=cc.cdo._object_chamfer_cm(th, tl, sd),
                        ourhi_vs_truthhi=cc.cdo._object_chamfer_cm(th, oh, sd),
                        ourlo_vs_truthhi=cc.cdo._object_chamfer_cm(th, ol, sd),
                        ourlo_vs_truthlo=cc.cdo._object_chamfer_cm(tl, ol, sd)),
               frame=dict(truthlo_vs_truthhi=cc.compare(fth, ftl), ourlo_vs_ourhi=cc.compare(foh, fol),
                          ourlo_vs_truthhi=cc.compare(fth, fol)))
    rec["cdo"] = {k: round(float(v), 4) for k, v in rec["cdo"].items()}
    with open(OUT, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(i, rec["nF_lo"], rec["nV_lo"], rec["cdo"], rec["frame"]["ourlo_vs_ourhi"]["dc_mm"], flush=True)
