"""Task loads of the boards from OUR reference (no GT): |a| p95/max (m/s^2, 3-frame smoothing), gravity moment for an
edge grip at lever l (half length - 1.5 cm), required normal force for a parallel-extension couple arm d, and the
friction-only normal force for a vertical board (notes 24 rule: SF 1.5, mu_d = 1/(sqrt2*1.5) = 0.47)."""
import sys, numpy as np
from scipy.ndimage import uniform_filter1d
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from refload import load_ref
d = load_ref(sys.argv[1]); fps = 20.0; m = 0.3; g = 9.81
for j, o in enumerate(d['names']):
    p = uniform_filter1d(d['OP'][:, j], 3, axis=0); v = np.gradient(p, 1 / fps, axis=0); a = np.gradient(v, 1 / fps, axis=0)
    an = np.linalg.norm(a, axis=1); F = m * np.linalg.norm(a - [0, 0, -g], axis=1)
    print(f'{o}: |a| p95 {np.percentile(an, 95):.2f} max {an.max():.2f} m/s2; |F|=m|a-g| p95 {np.percentile(F, 95):.2f} max {F.max():.2f} N (weight {m*g:.2f} N); speed max {np.linalg.norm(v,axis=1).max():.2f} m/s')
for name, l in (('short-end grip (lever 9.9 cm)', 0.099), ('long-edge grip (lever 5.4 cm)', 0.054)):
    M = m * g * l * 1.5
    print(f'{name}: gravity moment x SF1.5 = {M:.3f} N m; couple arm 3 cm -> {M/0.03:.1f} N per side, 5 cm -> {M/0.05:.1f} N; finger torque at 5 cm lever for 3 cm arm {M/0.03*0.05:.2f} N m -> {M/0.03*0.05/1.7:.2f} rad squeeze at kp 1.7')
print(f'vertical board, friction only: N >= m g SF / (2 mu_d) = {m*g*1.5/(2*0.47):.1f} N per side')
