import sys, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/cdo-sprint/C1/T3-gen-fit/scripts')
import fit
m = trimesh.creation.icosphere(subdivisions=4, radius=0.05)
V, F = np.asarray(m.vertices), np.asarray(m.faces)
P = trimesh.creation.icosphere(subdivisions=6, radius=0.053).vertices
P = P[P[:, 2] > -0.01]                                  # partial: upper part only
U = P / np.linalg.norm(P, axis=1, keepdims=True)        # camera outside along the radial direction
cfg = dict(fit.DEFAULT); cfg['alphas'] = [100, 25, 6]; cfg['cap_m'] = 0.01
c = V.mean(0); s = np.linalg.norm(V.max(0) - V.min(0))
cfg['cap_m'] /= s
st = fit.nicp((V - c) / s, F, (P - c) / s, U, cfg, lambda x: None)
for k, Vn in enumerate(st):
    Vm = Vn * s + c; r = np.linalg.norm(Vm, axis=1)
    print(k, 'radius top', r[Vm[:, 2] > 0].mean().round(5), 'bottom', r[Vm[:, 2] < -0.02].mean().round(5))
