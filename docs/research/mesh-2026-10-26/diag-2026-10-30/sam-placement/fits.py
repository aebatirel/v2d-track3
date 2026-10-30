"""GT-free placement fits of a generated (canonical-frame) mesh into OUR object frame. No scan, mocap, align or
parquet pose is read here. Inputs: the raw generated mesh, our observed points + free/hit voxel grid (obs_all, our
stereo along our tracks), and our library_v3 mesh (fused from our own depth, same frame).

Variants (each multi-start: 24 cube rotations after PCA alignment, best start by the variant's own objective):
  base      sim3_fit.py replica: obs->mesh (best 90 %) + mesh->obs (best 70 % of ALL mesh samples), scale free
  vis       visibility-aware: mesh->obs only for mesh samples that lie in space our cameras observed (voxel with a
            surface hit (dilated 2 voxels) or carved free); unseen (back / bottom / inside) surfaces are not pulled
  vis_slib  vis with the scale FIXED from our library_v3 mesh: s = RMS radius(lib) / RMS radius(raw) (kit moments)
  lib       Sim(3) symmetric trimmed ICP of the raw mesh to our library_v3 mesh surface (both complete shapes)
  lib_vis   lib, then a local vis refinement of R, t with the lib scale fixed
Usage: fits.py --objs ... --seeds 42,7 --variants base,vis,vis_slib,lib,lib_vis --out fits.jsonl
"""
import argparse, json, sys, time
import numpy as np
from scipy.ndimage import binary_dilation
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/diag/sam-placement')
from common import *  # noqa

N = 8000
ITERS = 30


class Known:
    """Space our cameras observed: surface-hit voxels (dilated) or carved free space. GT-free."""
    def __init__(self, obs, dil=2, free_min=3):
        h, f = obs['hits'], obs['free']
        self.k = binary_dilation(h > 0, iterations=dil) | (f >= free_min)
        self.lo, self.vox = obs['lo'], obs['vox']

    def __call__(self, X):
        ijk = np.floor((X - self.lo) / self.vox).astype(int)
        ok = np.all((ijk >= 0) & (ijk < np.array(self.k.shape)), 1)
        out = np.zeros(len(X), bool)
        out[ok] = self.k[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]]
        return out


def objective(T, M, O, tO, variant, known):
    X = apply(T, M)
    do = cKDTree(X).query(O)[0]
    dm = tO.query(X)[0]
    jo = np.sort(do)[:int(0.9 * len(do))].mean()
    if variant == 'base':
        jm = np.sort(dm)[:int(0.7 * len(dm))].mean()
    elif variant in ('vis', 'vis_slib', 'lib_vis'):
        k = known(X)
        jm = np.sort(dm[k])[:int(0.9 * k.sum())].mean() if k.sum() > 50 else 1.0
    else:
        raise ValueError(variant)
    return float(jo + jm)


def icp(T, M, O, tO, variant, known, iters=ITERS, fix_scale=None):
    for _ in range(iters):
        X = apply(T, M)
        do, io = cKDTree(X).query(O)
        dm, im = tO.query(X)
        ko = do <= np.quantile(do, 0.9)
        if variant == 'base':
            km = dm <= np.quantile(dm, 0.7)
        elif variant == 'obs_only':
            km = np.zeros(len(M), bool)
        else:
            k = known(X)
            km = np.zeros(len(M), bool)
            if k.sum() > 50:
                km[k] = dm[k] <= np.quantile(dm[k], 0.9)
        src = np.r_[M[io[ko]], M[km]]; dst = np.r_[O[ko], O[im[km]]]
        if fix_scale is None:
            T = umeyama(src, dst)
        else:
            _, R, t = umeyama(fix_scale * src, dst, with_scale=False)
            T = (fix_scale, R, t)
    return T


def starts(M, Y, s0=None):
    cm, Vm, sm = pca(M); cy, Vy, sy = pca(Y)
    if s0 is None:
        s0 = float(np.median(sy / sm))
    out = []
    for Rs in rotations24():
        R = Vy @ Rs @ Vm.T
        out.append((s0, R, cy - s0 * R @ cm))
    return out


def fit_variant(variant, M, O, tO, known, raw, lib, Mlib=None):
    if variant in ('base', 'vis'):
        best = None
        for T0 in starts(M, O):
            T = icp(T0, M, O, tO, variant, known)
            j = objective(T, M, O, tO, variant, known)
            if best is None or j < best[0]:
                best = (j, T)
        return best[1], best[0], {}
    if variant == 'vis_slib':
        s = moments(lib)[1] / moments(raw)[1]
        best = None
        for T0 in starts(M, O, s0=s):
            T = icp(T0, M, O, tO, 'vis', known, fix_scale=s)
            j = objective(T, M, O, tO, 'vis', known)
            if best is None or j < best[0]:
                best = (j, T)
        return best[1], best[0], dict(s_lib=s)
    if variant in ('lib', 'lib_vis'):
        T, res = best_sim3(M, Mlib, keep=0.9, iters=ITERS)
        jl = res[0][0]
        info = dict(lib_symdist_mm=jl * 1e3, lib_second_mm=next((r[0] * 1e3 for r in res
                                                                 if angle_deg(r[1][1] @ T[1].T) > 30), None))
        if variant == 'lib':
            return T, objective(T, M, O, tO, 'vis', known), info
        T2 = icp(T, M, O, tO, 'vis', known, fix_scale=T[0])
        return T2, objective(T2, M, O, tO, 'vis', known), info
    raise ValueError(variant)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--objs', default=','.join(OBJS)); ap.add_argument('--seeds', default='42,7')
    ap.add_argument('--model', default='sam3d')
    ap.add_argument('--variants', default='base,vis,vis_slib,lib,lib_vis'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    fo = open(a.out, 'a')
    for obj in a.objs.split(','):
        obs = load_obs(obj, n=N)
        O = obs['pts']; tO = cKDTree(O); known = Known(obs)
        lib = load_mesh(f'{LIB}/{obj}.glb')
        Mlib, _ = surf(lib, N, seed=3)
        for seed in a.seeds.split(','):
            m2 = 'trellis2_1024' if (a.model == 'trellis2' and obj == 'blue_cup') else a.model
            rp, pp = gen_paths(m2, obj, seed)
            raw = load_mesh(rp)
            M, _ = surf(raw, N, seed=0)
            Tfit, res = recover_T(raw, load_mesh(pp))
            j_before = dict(base=objective(Tfit, M, O, tO, 'base', known), vis=objective(Tfit, M, O, tO, 'vis', known))
            cache = {}
            for v in a.variants.split(','):
                t0 = time.time()
                if v == 'lib_vis' and 'lib' in cache:            # reuse the lib fit, refine R, t locally
                    Tl, info = cache['lib']
                    T = icp(Tl, M, O, tO, 'vis', known, fix_scale=Tl[0]); j = objective(T, M, O, tO, 'vis', known)
                else:
                    T, j, info = fit_variant(v, M, O, tO, known, raw, lib, Mlib)
                    cache[v] = (T, info)
                out = f'{OUT}/fits/{a.model}_{v}/{obj}_{TAG[obj]}_s{seed}.ply'
                os.makedirs(os.path.dirname(out), exist_ok=True)
                trimesh.Trimesh(apply(T, np.asarray(raw.vertices)), raw.faces, process=False).export(out)
                rec = dict(model=a.model, obj=obj, seed=int(seed), variant=v, out=out, s=T[0], s_before=Tfit[0],
                           j=j, j_before=j_before, recover_res=float(res), secs=round(time.time() - t0, 1),
                           R=T[1].round(6).tolist(), t=np.round(T[2], 6).tolist(), **info)
                print(json.dumps({k: (round(x, 4) if isinstance(x, float) else x) for k, x in rec.items()
                                  if k not in ('R', 't', 'out')}), flush=True)
                fo.write(json.dumps(rec) + '\n'); fo.flush()


if __name__ == '__main__':
    main()
