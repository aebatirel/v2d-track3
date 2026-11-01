"""Dev check (B1): coarse-surface rules for the HULL (any / majority; partner blocks dropped). No GT."""
import sys, time, json, os
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import guard, bundle as B, pack as PK, score as SC, complete
from gmg.bundle import STATE_OBSERVED
from gmg.producers import hull as P
import numpy as np
from scipy import ndimage
ep, objs, run = int(sys.argv[1]), sys.argv[2].split(','), sys.argv[3]
guard.set_run(run)
b = B.from_obs_all(ep)

def make(rule, part):
    def _coarsen(occ, clipped, observed, k):
        if k == 1:
            return occ
        sh = [-(-n // k) * k for n in occ.shape]
        def red(a, how):
            pad = np.zeros(sh, bool); pad[:a.shape[0], :a.shape[1], :a.shape[2]] = a
            r = pad.reshape(sh[0] // k, k, sh[1] // k, k, sh[2] // k, k)
            return r.any(axis=(1, 3, 5)) if how == 'any' else r.sum(axis=(1, 3, 5)) >= (k ** 3 + 1) // 2
        co = red(occ, rule)
        if part == 'clip':
            co &= ~(red(clipped, 'any') & ~red(observed, 'any'))
        else:
            pf = ndimage.binary_dilation(np.asarray(obs['pocc']) > 0, iterations=max(grow, 0)) if grow else np.asarray(obs['pocc']) > 0
            co &= ~red(pf & ~observed, 'any')
        lab, n = ndimage.label(co)
        if n == 0: return co
        ob = np.bincount(lab[red(observed & occ, 'any') & (lab > 0)], minlength=n + 1)
        keep = int(ob[1:].argmax()) + 1 if ob[1:].any() else int(np.bincount(lab.ravel())[1:].argmax()) + 1
        return lab == keep
    return _coarsen

for obj in objs:
    obs = b.obs(obj)
    for rule in ('any', 'maj'):
        for part in ('clip', 'partner'):
            grow = 2
            P._coarsen = make(rule, part)
            P.MAX_COARSEN = 3
            t = time.time()
            # force k >= 2 by making k = 1 unpackable
            orig = P._packable
            P._packable = lambda m, bud, _o=orig: (False, -1) if len(m.faces) > 9000 else _o(m, bud)
            c = P.produce(dict(bundle=b, obj=obj, t0=0.005))[0]
            P._packable = orig
            grow = c.params['grow']
            m, info = PK.pack(c.mesh, os.path.join(run, f'{obj}_{rule}_{part}.glb'))
            v2 = SC.v2(m, b, obj)
            print(json.dumps(dict(obj=obj, rule=rule, part=part, k=c.params['coarsen_k'], tries=[(t_['k'], t_['faces_dense'], t_['packed_watertight']) for t_ in c.report['coarsen_tries']],
                                  v1=info['v1']['watertight'], v2=v2['veto'], v2_detail={k: v for k, v in v2.items() if k != 'partners'},
                                  clip_mesh=complete.clip_check(m, b, obj)['deep_total'], vol=info['v1'].get('volume_cm3'),
                                  fsv=SC.fsv_far(m, obs)['fsv_far'], sec=round(time.time() - t, 1))), flush=True)
