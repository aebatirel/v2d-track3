"""Score the repair (b) gate (after gate_b.py). M1: registered AUC of the object track vs mocap (pipeline/score_registered.py,
kit functions, the episode's own meshes) for U and F. M2: jittered sim_vs_ref of the re-locked U and F (copies 1..8 of
jitter_check --k 9 --seed 0), symmetric kit errors (cups any spin about their axis; the pot lid 2-fold about its thinnest
axis, as score_registered's stand-in; others none) and plain ADD. Verdict by the pre-registered rule.
Usage: S=<scratchpad> python -I score_b.py RUN_DIR"""
import glob, importlib, json, os, subprocess, sys
import numpy as np, pyarrow.parquet as pq, trimesh

S = os.environ['S']; D = os.path.abspath(sys.argv[1]); R = '/home/user/v2d-track3'; KIT = f'{S}/kit/v2d_submission_kit'
sys.path.insert(0, KIT); sys.path.insert(0, f'{KIT}/metric_code/track_3'); AU = importlib.import_module('AUC')
P_ = np.random.default_rng(0).normal(size=(500, 3)); P_ = 0.05 * P_ / np.linalg.norm(P_, axis=1, keepdims=True)


def sym_axis(mesh, name):
    v = trimesh.load(mesh, force='mesh').vertices; v = v - v.mean(0); w, V = np.linalg.eigh(np.cov(v.T))
    if name in ('blue_cup', 'beige_cup'):
        return V[:, int(np.argmax([abs(w[k] - np.mean(np.delete(w, k))) for k in range(3)]))], 360
    if name == 'white_pot_lid':
        return V[:, 0], 2
    return np.zeros(3), 1


def m2(ref, npz, axes):
    t = pq.read_table(ref); names = t.column('object_body_names')[0].as_py(); B = len(names); T = len(t.column('robot_left_wrist_position')[0].as_py())
    OP = np.array(t.column('object_body_position')[0].as_py()).reshape(T, B, 3); OQ = np.array(t.column('object_body_wxyz')[0].as_py()).reshape(T, B, 4)[..., [1, 2, 3, 0]]
    refa = np.concatenate([OP, OQ], 2)[:, None]; Q = np.load(npz)['q'].astype(float); pl, sy = [], []
    for k in range(1, Q.shape[1]):
        sim = AU._warp_to_reference_start(Q[:, k][:, None], refa)
        pl.append(float(AU._add_auc(AU._object_add(sim, refa, np.repeat(P_[None], B, 0)))))
        e = np.stack([AU._symmetry_point_errors(sim[:, :, b], refa[:, :, b], P_, axes[names[b]][0], axes[names[b]][1]) for b in range(B)], -1)
        sy.append(float(AU._add_auc(e)))
    return float(np.mean(pl)), float(np.mean(sy))


res = {}
for d in sorted(glob.glob(f'{D}/ep*')):
    ep = int(os.path.basename(d)[2:]); inp = glob.glob(f'{d}/in/processed/*/*/ref_in.parquet')[0]; hf = inp.replace('ref_in.parquet', 'ref_hf.parquet')
    mdir = f'{d}/meshes'; os.makedirs(mdir, exist_ok=True)
    for m in glob.glob(f'{d}/in/assets/mesh/*/*.glb'):
        dst = f'{mdir}/{os.path.basename(m)}'
        if not os.path.exists(dst):
            os.symlink(m, dst)
    names = pq.read_table(inp).column('object_body_names')[0].as_py()
    axes = {n: sym_axis(f'{d}/in/assets/mesh/{n}/{n}.glb', n) for n in names}
    r = dict()
    for arm, ref in (('U', inp), ('F', hf)):
        npz = f'{d}/{arm}_track.npz'
        subprocess.run([f'{S}/venv/bin/python', '-I', f'{R}/docs/research/grasp-ep13-20261101/scripts/ref_to_npz.py', ref, npz], check=True)
        out = f'{d}/{arm}_registered.json'
        subprocess.run([f'{S}/venv/bin/python', f'{R}/pipeline/score_registered.py', str(ep), npz, '--meshes', mdir, '--t3', f'{S}/content/t3',
                        '--kit', KIT, '--out', out], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        auc = json.load(open(out))['perception']['AUC']
        g = glob.glob(f'{d}/{arm}/processed/*/*/ref_gl_ilc.parquet'); jz = f'{d}/{arm}/jitter.npz'
        pl, sy = m2(g[0], jz, axes) if g and os.path.exists(jz) else (None, None)
        r[arm] = dict(ref_auc_vs_mocap=auc, jit_plain=pl, jit_sym=sy)
    r['d_auc'] = round(r['F']['ref_auc_vs_mocap'] - r['U']['ref_auc_vs_mocap'], 4)
    r['d_sym'] = None if r['U']['jit_sym'] is None or r['F']['jit_sym'] is None else round(r['F']['jit_sym'] - r['U']['jit_sym'], 4)
    r['d_plain'] = None if r['U']['jit_plain'] is None or r['F']['jit_plain'] is None else round(r['F']['jit_plain'] - r['U']['jit_plain'], 4)
    res[f'ep{ep}'] = r; print(f'ep{ep}', json.dumps(r), flush=True)
da = [v['d_auc'] for v in res.values()]; ds = [v['d_sym'] for v in res.values()]
complete = all(x is not None for x in ds)
M1 = bool(np.mean(da) >= -0.002 and min(da) >= -0.010); M2 = bool(complete and np.mean(ds) >= 0.02)
res['summary'] = dict(mean_d_auc=round(float(np.mean(da)), 4), min_d_auc=round(float(min(da)), 4),
                      mean_d_sym=round(float(np.mean(ds)), 4) if complete else None, M1=M1, M2=M2, verdict='PASS' if (M1 and M2) else 'FAIL')
print(json.dumps(res['summary'])); json.dump(res, open(f'{D}/gate_b.json', 'w'), indent=1)
