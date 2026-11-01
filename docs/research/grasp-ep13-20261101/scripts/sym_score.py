"""Report-only (1 Nov 2026): sim_vs_ref of each ep13 arm's jitter copies with the kit's SYMMETRIC point errors
(AUC.py _symmetry_point_errors: blue_cup = any rotation about its central axis, as the kit's Track 3 README declares;
plastic_dish_rack = no symmetry) next to the plain-ADD value (pipeline/qa.py, the pre-registered metric). Same 500 points
on a 5 cm sphere, same warp to the reference start. The cup axis is our mesh's symmetry axis in its body frame (PCA,
the eigenvector whose variance differs from the other two). Our references only (no ground truth).
Usage: python -I sym_score.py S/ep13 S/inputs S/gl2 CUP_MESH.glb OUT.json"""
import glob, importlib, json, os, sys
import numpy as np, pyarrow.parquet as pq, trimesh

E, INP, GL2, MESH, OUT = sys.argv[1:6]
kit = os.environ['KIT']; sys.path.insert(0, kit); sys.path.insert(0, f'{kit}/metric_code/track_3'); AU = importlib.import_module('AUC')
m = trimesh.load(MESH, force='mesh'); v = m.vertices - m.vertices.mean(0); w, V = np.linalg.eigh(np.cov(v.T))
ax = V[:, int(np.argmax([abs(w[k] - np.mean(np.delete(w, k))) for k in range(3)]))]; ax = ax / np.linalg.norm(ax)
r0 = np.random.default_rng(0); P_ = r0.normal(size=(500, 3)); P_ = 0.05 * P_ / np.linalg.norm(P_, axis=1, keepdims=True)
res = {'cup_axis_body': np.round(ax, 3).tolist()}
for d in sorted(glob.glob(f'{E}/*_*/jitter.npz')):
    arm = os.path.basename(os.path.dirname(d)); ref = arm.split('_')[0]
    src = glob.glob(f'{INP}/ep13_{ref}/processed/*/*/ref_in.parquet') if len(ref) == 1 else glob.glob(f'{GL2}/ep13_{ref[0]}/processed/*/*/ref_gl_ilc.parquet')
    t = pq.read_table(src[0]); names = t.column('object_body_names')[0].as_py(); B = len(names); T = len(t.column('robot_left_wrist_position')[0].as_py())
    OP = np.array(t.column('object_body_position')[0].as_py()).reshape(T, B, 3)
    OQ = np.array(t.column('object_body_wxyz')[0].as_py()).reshape(T, B, 4)[..., [1, 2, 3, 0]]
    refa = np.concatenate([OP, OQ], 2)[:, None]; Q = np.load(d)['q'].astype(np.float64)       # (T, K, B, 7)
    axes = [ax if n == 'blue_cup' else np.zeros(3) for n in names]
    plain, sym = [], []
    for k in range(Q.shape[1]):
        sim = AU._warp_to_reference_start(Q[:, k][:, None], refa)
        plain.append(float(AU._add_auc(AU._object_add(sim, refa, np.repeat(P_[None], B, 0)))))
        errs = np.stack([AU._symmetry_point_errors(sim[:, :, b], refa[:, :, b], P_, axes[b], 360) for b in range(B)], -1)
        sym.append(float(AU._add_auc(errs)))
    plain, sym = np.array(plain), np.array(sym)
    res[arm] = dict(plain_nominal=round(plain[0], 4), plain_jit=round(float(plain[1:].mean()), 4),
                    sym_nominal=round(sym[0], 4), sym_jit=round(float(sym[1:].mean()), 4), sym_jit_sd=round(float(sym[1:].std()), 4))
    print(f"{arm:10s} plain ADD: nominal {plain[0]:.4f} jittered {plain[1:].mean():.4f} | symmetric: nominal {sym[0]:.4f} jittered {sym[1:].mean():.4f} ± {sym[1:].std():.4f}", flush=True)
# floors with the symmetric metric (the static first frame), per reference
for ref, src in (('P', f'{INP}/ep13_P'), ('O', f'{INP}/ep13_O')):
    t = pq.read_table(glob.glob(f'{src}/processed/*/*/ref_in.parquet')[0]); names = t.column('object_body_names')[0].as_py(); B = len(names)
    T = len(t.column('robot_left_wrist_position')[0].as_py())
    OP = np.array(t.column('object_body_position')[0].as_py()).reshape(T, B, 3); OQ = np.array(t.column('object_body_wxyz')[0].as_py()).reshape(T, B, 4)[..., [1, 2, 3, 0]]
    refa = np.concatenate([OP, OQ], 2)[:, None]; st = np.repeat(refa[:1], T, 0); axes = [ax if n == 'blue_cup' else np.zeros(3) for n in names]
    errs = np.stack([AU._symmetry_point_errors(st[:, :, b], refa[:, :, b], P_, axes[b], 360) for b in range(B)], -1)
    res[f'floor_{ref}'] = dict(sym=round(float(AU._add_auc(errs)), 4)); print(f'floor {ref} (P2/O2 share it): symmetric {res[f"floor_{ref}"]["sym"]:.4f}')
json.dump(res, open(OUT, 'w'), indent=1)
