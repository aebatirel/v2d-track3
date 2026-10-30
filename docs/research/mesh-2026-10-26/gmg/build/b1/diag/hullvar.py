"""Dev diagnostic (B1): HULL occupancy variants vs packability (watertight after fit_budget + kit decode). No GT."""
import sys, time, json, os
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import guard, bundle as B, complete, score as SC
from gmg.producers import hull as P
from gmg.bundle import STATE_FREE, STATE_OBSERVED
import numpy as np, trimesh
from scipy import ndimage
from autokit import program
ep, objs, run = int(sys.argv[1]), sys.argv[2].split(','), sys.argv[3]
guard.set_run(run)
b = B.from_obs_all(ep)
for obj in objs:
    obs = b.obs(obj); st = np.asarray(obs['state']); lo, vox = np.asarray(obs['lo'], float), float(obs['vox'])
    c = P.produce(dict(bundle=b, obj=obj, t0=0.005))[0]
    grow = c.params['grow']
    # rebuild the kept occupancy exactly as the producer does
    occ0 = st != STATE_FREE
    pl = b.rest_plane(obj)
    if pl is not None:
        idx = np.indices(st.shape).reshape(3, -1).T
        occ0 &= (((lo + (idx + 0.5) * vox) @ pl[0] + pl[1]) >= 0).reshape(st.shape)
    occ = complete.partner_clip(occ0, obs, grow=grow)
    lab, n = ndimage.label(occ)
    obs_lab = np.bincount(lab[(st == STATE_OBSERVED) & (lab > 0)], minlength=n + 1)
    occ = lab == int(obs_lab[1:].argmax()) + 1
    clipped = occ0 & ~complete.partner_clip(occ0, obs, grow=grow)
    far = SC.far_free_grid(obs)
    def test(tag, o, v=vox, l=lo):
        t = time.time()
        m = P._march(o, l, v)
        mm, info = program.fit_budget(m, [], 4000)
        mm = trimesh.Trimesh(np.asarray(mm.vertices), np.asarray(mm.faces), process=True)
        p = os.path.join(run, f'{obj}_{tag}.glb'); mm.export(p)
        v1 = SC.v1(p)
        chk = complete.clip_check_grid(o, obs, b, obj) if v == vox else None
        print(json.dumps(dict(obj=obj, tag=tag, vox_mm=v * 1e3, voxels=int(o.sum()), dense=len(m.faces), euler=int(m.euler_number),
              wt_dense=bool(m.is_watertight), packed=len(mm.faces), wt_packed=bool(mm.is_watertight), v1=v1['watertight'],
              agg=info.get('agg'), fsv=SC.fsv_far(mm, obs, far)['fsv_far'], deep=chk and chk['deep_total'], sec=round(time.time() - t, 1))), flush=True)
    test('base', occ)
    for it in (1, 2):
        o2 = ndimage.binary_closing(np.pad(occ, it + 1), iterations=it)[it + 1:-it - 1, it + 1:-it - 1, it + 1:-it - 1] & ~clipped
        lab2, n2 = ndimage.label(o2); o2 = lab2 == np.bincount(lab2[occ & (lab2 > 0)]).argmax()
        test(f'close{it}', o2)
    # fill enclosed cavities too
    test('base_fill', ndimage.binary_fill_holes(occ))
    # coarse 2x, any child occupied
    sh = [(s + 1) // 2 * 2 for s in occ.shape]; pad = np.zeros(sh, bool); pad[:occ.shape[0], :occ.shape[1], :occ.shape[2]] = occ
    co = pad.reshape(sh[0] // 2, 2, sh[1] // 2, 2, sh[2] // 2, 2).any(axis=(1, 3, 5))
    test('coarse2_any', co, 2 * vox, lo)
    cm = pad.reshape(sh[0] // 2, 2, sh[1] // 2, 2, sh[2] // 2, 2).sum(axis=(1, 3, 5)) >= 4
    lab3, n3 = ndimage.label(cm); test('coarse2_maj', lab3 == np.bincount(lab3.ravel())[1:].argmax() + 1, 2 * vox, lo)
