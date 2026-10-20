# Verifier: build-RAM scaling with unequal objects (S_A, S_B shapes) + K one-shape hand bodies, N worlds.
# usage: v_scale.py SA SB K N
import sys, time, resource, numpy as np
import warp as wp
wp.config.quiet = True
import newton
SA, SB, K, N = map(int, sys.argv[1:5])
t = newton.ModelBuilder()
rng = np.random.default_rng(1)
for o, S in enumerate((SA, SB)):
    b = t.add_body(xform=wp.transform((0.3 * o, 0, 0.1), wp.quat_identity()))
    t.add_joint_free(b)
    for i in range(S):
        p = rng.uniform(-0.05, 0.05, 3)
        t.add_shape_box(b, xform=wp.transform(tuple(p), wp.quat_identity()), hx=0.004, hy=0.004, hz=0.004)
for k in range(K):
    b = t.add_body(xform=wp.transform((0, 0.3, 0.02 * k), wp.quat_identity())); t.add_joint_free(b)
    t.add_shape_capsule(b, radius=0.008, half_height=0.02)
fp1 = len(t.shape_collision_filter_pairs)
r0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
t0 = time.time(); s = newton.ModelBuilder(); s.replicate(t, N); t1 = time.time()
m = s.finalize(device='cpu'); t2 = time.time()
r1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
pairs = len(s.shape_collision_filter_pairs) + m.shape_contact_pair_count
pred = SA*(SA-1)//2 + SB*(SB-1)//2 + SA*SB + K*(SA+SB) + K*(K-1)//2
print(f'SA={SA} SB={SB} K={K} N={N}: filter/world {fp1} contact/world {m.shape_contact_pair_count//N} '
      f'pairs/world {pairs//N} (pred {pred}) | replicate {t1-t0:.1f}s finalize {t2-t1:.1f}s | '
      f'peak RSS {r1:.0f} MB (template {r0:.0f}) -> {(r1-r0)*1e6/max(pairs,1):.0f} B/pair', flush=True)
