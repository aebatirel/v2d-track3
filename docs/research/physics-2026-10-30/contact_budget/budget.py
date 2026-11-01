"""Per-world contact budget of a FlashCHORD scene under the training sim config (sim=rl), CPU: collision geoms per group
(hands, each object, support/table) and, over W sampled training resets + STEPS zero-action steps, the per-world
contact count by group pair and nefc (constraint rows). Our reference only; no ground truth."""
import collections, json, os, sys
sys.path.insert(0, os.path.join(os.environ['USE_COPY'], 'src')); sys.path.insert(1, '/home/user/v2d-track3/tools/physics_solve')
import numpy as np, warp as wp, mujoco
wp.config.log_level = wp.LOG_WARNING
import solve as S
from flash_chord.lifecycle import reset as _r  # noqa
W = int(os.environ.get('W', '8')); STEPS = int(os.environ.get('STEPS', '60'))
env, labels = S.build_env(sys.argv[1], W, planner=False); sol = env.solver; m = sol.mj_model; md = sol.mjw_data
bname = [mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b) or f'body{b}' for b in range(m.nbody)]
def group(b):
    n = bname[b].lower()
    if 'track3_' in n: return n.split('track3_')[1].split('/')[0]
    if 'left' in n: return 'left_hand'
    if 'right' in n: return 'right_hand'
    if b == 0: return 'world/table'
    return 'other:' + n
gb = [int(x) for x in m.geom_bodyid]; coll = [(int(m.geom_contype[g]) | int(m.geom_conaffinity[g])) != 0 for g in range(m.ngeom)]
geoms = collections.Counter(group(gb[g]) for g in range(m.ngeom) if coll[g])
per_pair = collections.defaultdict(list); tot, nefc, nacon_req = [], [], []
FRAMES = [int(x) for x in os.environ.get('FRAMES', '').split(',') if x.strip()]   # explicit (evaluator-style) resets at
with S.on(env):                                       # these frames instead of one sampled training reset
    for F in (FRAMES or [None]):
      env.reset() if F is None else env.reset(frame_id=F)
      for k in range(STEPS):
          env.step(None); n = min(int(md.nacon.numpy()[0]), int(getattr(md, 'naconmax', 10 ** 9)))
          g = md.contact.geom.numpy()[:n]; w = md.contact.worldid.numpy()[:n]
          cnt = collections.Counter(); wc = collections.Counter(int(x) for x in w)
          for (a, b), wi in zip(g, w):
              p = tuple(sorted((group(gb[int(a)]), group(gb[int(b)])))); cnt[(int(wi), p)] += 1
          for p in {p for _, p in cnt}:
              per_pair[p].append(max(cnt.get((wi, p), 0) for wi in range(W)))
          tot.append(max(wc.values()) if wc else 0); nefc.append(int(md.nefc.numpy().max()))
          nacon_req.append(int(md.nacon.numpy()[0]))
out = dict(ref=sys.argv[1], worlds=W, steps=STEPS, nconmax=int(getattr(md, 'naconmax', -1)), njmax=int(getattr(md, 'njmax', -1)),
           collision_geoms=dict(geoms), max_contacts_per_world=max(tot), median_contacts_per_world=float(np.median(tot)),
           max_nefc_per_world=max(nefc), median_nefc=float(np.median(nefc)), frames=FRAMES or 'sampled',
           max_total_contacts_requested=max(nacon_req), share_steps_nefc_over_njmax=float(np.mean(np.array(nefc) > int(getattr(md, 'njmax', 10 ** 9)))),
           max_contacts_per_world_by_pair={' / '.join(p): max(v) for p, v in sorted(per_pair.items(), key=lambda x: -max(x[1]))})
print(json.dumps(out, indent=1)); json.dump(out, open(sys.argv[2], 'w'), indent=1)
