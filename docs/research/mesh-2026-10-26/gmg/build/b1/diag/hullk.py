"""Dev check (B1): HULL producer with adaptive surface coarsening; pack + V1 + construction report. No GT."""
import sys, time, json, os
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import guard, bundle as B, pack as PK, score as SC, complete
from gmg.producers import hull as P
ep, objs, run = int(sys.argv[1]), sys.argv[2].split(','), sys.argv[3]
guard.set_run(run)
b = B.from_obs_all(ep)
for obj in objs:
    t = time.time()
    c = P.produce(dict(bundle=b, obj=obj, t0=0.005))[0]
    m, info = PK.pack(c.mesh, os.path.join(run, f'{obj}_hull.glb'))
    v2 = SC.v2(m, b, obj)
    print(json.dumps(dict(obj=obj, flags=c.flags, params=c.params, tries=c.report['coarsen_tries'], v1=info['v1'],
                          v2=v2['veto'], clip_mesh=complete.clip_check(m, b, obj)['deep_total'],
                          fsv=SC.fsv_far(m, b.obs(obj))['fsv_far'], sec=round(time.time() - t, 1))), flush=True)
