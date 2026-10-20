# Stage C: cost of many collision shapes per object under FlashCHORD's world replication (newton 1.2.0, CPU).
# newton adds a collision-filter pair for every pair of shapes on one body (builder.add_shape, "no contacts between
# shapes of the same body"); FlashCHORD's decomposition adds the same pairs for its hulls; builder.replicate copies the
# list per world (add_builder: shape_collision_filter_pairs.extend); finalize turns it into one Python set and runs
# find_shape_contact_pairs, a Python double loop over every pair of colliding shapes in each world.
# Template: 2 free object bodies with H box shapes each + 40 one-shape "hand" bodies + nothing else.
# usage: c_scale.py H N   -> time (s) and peak RSS (MB) of replicate + finalize, filter-pair and contact-pair counts.
import sys, time, resource, numpy as np
import warp as wp
wp.config.quiet = True
import newton
H, N = int(sys.argv[1]), int(sys.argv[2])
t = newton.ModelBuilder()
rng = np.random.default_rng(0)
for o in range(2):
    b = t.add_body(xform=wp.transform((0.3 * o, 0, 0.1), wp.quat_identity()))
    t.add_joint_free(b)
    for i in range(H):
        p = rng.uniform(-0.05, 0.05, 3)
        t.add_shape_box(b, xform=wp.transform(tuple(p), wp.quat_identity()), hx=0.005, hy=0.005, hz=0.005)
for k in range(40):
    b = t.add_body(xform=wp.transform((0, 0.3, 0.02 * k), wp.quat_identity())); t.add_joint_free(b)
    t.add_shape_capsule(b, radius=0.008, half_height=0.02)
fp1 = len(t.shape_collision_filter_pairs)
r0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
t0 = time.time(); s = newton.ModelBuilder(); s.replicate(t, N); t1 = time.time()
m = s.finalize(device='cpu'); t2 = time.time()
r1 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6   # macOS: bytes
print(f'H={H:4d} N={N:5d}: filter pairs/world {fp1:7d} total {len(s.shape_collision_filter_pairs):10d} | '
      f'contact pairs total {m.shape_contact_pair_count:10d} ({m.shape_contact_pair_count//N}/world) | '
      f'replicate {t1-t0:6.1f}s finalize {t2-t1:6.1f}s | peak RSS {r1:7.0f} MB (template {r0:.0f})', flush=True)
