import sys, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/cdo-sprint/C1/T3-gen-fit/scripts')
import fit
rng = np.random.default_rng(0)
o = trimesh.creation.icosphere(subdivisions=4, radius=0.05); i = trimesh.creation.icosphere(subdivisions=4, radius=0.046)
i.invert()
m = trimesh.util.concatenate([o, i])                       # thin-walled shell, 4 mm wall, outward normals
V, F = np.asarray(m.vertices), np.asarray(m.faces)
P = trimesh.creation.icosphere(subdivisions=6, radius=0.053).vertices   # true outer surface 3 mm outside
P = P[P[:, 2] > -0.01]
P = P + rng.normal(0, 0.0015, P.shape)                    # stereo-like noise
cam = np.array([0.3, 0.0, 0.4])
U = cam - P; U /= np.linalg.norm(U, axis=1, keepdims=True)
vis_ok = np.einsum('ni,ni->n', P / np.linalg.norm(P, axis=1, keepdims=True), U) > 0
P, U = P[vis_ok], U[vis_ok]                               # only the side the camera sees
cfg = dict(fit.DEFAULT); cfg['alphas'] = [100, 25, 6]
c = V.mean(0); s = np.linalg.norm(V.max(0) - V.min(0)); cfg['cap_m'] /= s
st = fit.nicp((V - c) / s, F, (P - c) / s, U, cfg, print)
for k, Vn in enumerate(st):
    Vm = Vn * s + c; r = np.linalg.norm(Vm - Vm.mean(0), axis=1)
    print(k, 'outer r', r[:len(o.vertices)].mean().round(5), 'inner r', r[len(o.vertices):].mean().round(5), 'centre', (Vm.mean(0)*1e3).round(2))
