"""V6 (verify_systematics): my own in-process copy of pipeline/score_registered.py's AUC (kit functions, same host
geometry / seeds / mesh budget), validated against score_registered.py JSONs written by v4_score.sh, then used for
interpolation-free integer time shifts (+1 / -1 frame) and linear-vs-cubic half-frame advances on all public paths.
Usage: python -I v6_inproc.py OUT.json"""
import glob, json, os, sys
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation as R, Slerp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
import v2_scale_lag_tilt as V
from v2dlb import track3_pose as K
from v2dlb.object_mesh import _surface_moments
from v2dlb.mesh_common import _sample_mesh_surface

_H = {}


def host(n, slot):
    if (n, slot) not in _H:
        v, f = V.vf(V.scanp(n)); c, _ = _surface_moments(v, f)
        pts = _sample_mesh_surface(v, f, 1000, 7 + slot) - c
        axis, order = np.zeros(3), 0
        if n in ('beige_cup', 'blue_cup', 'white_pot_lid'):
            w, U = np.linalg.eigh(np.cov(pts.T))
            if n == 'white_pot_lid':
                axis, order = U[:, 0], 2
            else:
                k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
        _H[(n, slot)] = dict(anchor=c, points=pts, axis=axis, order=order)
    return _H[(n, slot)]


def auc(ep, names, ours, gt, lib):
    B = len(names)
    H = [host(n, s) for s, n in enumerate(names)]
    regs = [V.reg(ep, s, n, lib) for s, n in enumerate(names)]
    a = np.stack([np.c_[ours[n][:, :3, 3], R.from_matrix(ours[n][:, :3, :3]).as_quat()] for n in names], 1)[:, None].copy()
    r = np.stack([np.c_[gt[n][:, :3, 3], R.from_matrix(gt[n][:, :3, :3]).as_quat()] for n in names], 1)[:, None].copy()
    for s in range(B):
        a[:, :, s] = K._convert_object_body(a[:, :, s], regs[s][0], regs[s][1])
        r[:, :, s, :3] += np.einsum('...ij,j->...i', K._rotation_matrix(r[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
    a = K._align_registered_scene(a, r, axes)
    return round(float(K._registered_pose_metric('add_auc', a, r, pts, axes, orders)), 4)


def shift(M, tau, kind):
    T = len(M); t = np.arange(T)
    if float(tau).is_integer():
        return M[np.clip(t + int(tau), 0, T - 1)].copy()
    tq = np.clip(t + tau, 0, T - 1); out = np.tile(np.eye(4), (T, 1, 1))
    if kind == 'cubic':
        out[:, :3, 3] = CubicSpline(t, M[:, :3, 3], axis=0)(tq)
    else:
        out[:, :3, 3] = np.stack([np.interp(tq, t, M[:, k, 3]) for k in range(3)], 1)
    out[:, :3, :3] = Slerp(t, R.from_matrix(M[:, :3, :3]))(tq).as_matrix()
    return out


def main():
    W = f'{WORK}'
    # parity with score_registered.py
    par = {}
    for f in sorted(glob.glob(f'{W}/scores/*.json')):
        b = os.path.basename(f)[:-5]; ep = int(b.split('_')[0][2:])
        names, gt, _ = mocap(ep)
        z = np.load(f'{W}/npz/{b}.npz'); ours = {n: z[n] for n in names}
        lib = V.LIB_REF[ep] if '_ref_' in b or '_pre_' in b else V.LIB_PERC[ep]
        mine = auc(ep, names, ours, gt, lib); theirs = json.load(open(f))['perception']['AUC']
        par[b] = [mine, theirs]
    print('parity', par, flush=True)
    out = {'parity_with_score_registered': par, 'shifts': {}}
    for ep in sorted(CE):
        names, gt, _ = mocap(ep)
        d = ref_dir(ep); tfp = f'{d}/table_frame.npz' if d else f'{ST}/{V.STALE_TF.format(ep)}'
        Tt = np.load(tfp)['T_table_from_world']; P = perc(ep)
        srcs = {'perc': ({n: np.einsum('ij,tjk->tik', Tt, P[n]) for n in names}, V.LIB_PERC[ep])}
        if d:
            srcs['ref'] = (refparq(ref_final(ep)), V.LIB_REF[ep])
        out['shifts'][ep] = {}
        for k, (ours, lib) in srcs.items():
            row = {'0': auc(ep, names, ours, gt, lib)}
            for lab, tau, kind in (('+1', 1, None), ('-1', -1, None), ('+0.5lin', 0.5, 'lin'), ('+0.5cub', 0.5, 'cubic'),
                                   ('-0.5lin', -0.5, 'lin'), ('+0.5lin_from1', 0.5, 'lin1')):
                if kind == 'lin1':        # shift only frames >= 1: frame 0 (the kit's alignment frame) kept as is
                    o = {n: shift(ours[n], tau, 'lin') for n in names}
                    for n in names:
                        o[n][0] = ours[n][0]
                else:
                    o = {n: shift(ours[n], tau, kind) for n in names}
                row[lab] = auc(ep, names, o, gt, lib)
            out['shifts'][ep][k] = row
        print(ep, out['shifts'][ep], flush=True)
        json.dump(out, open(sys.argv[1], 'w'), indent=1)
    for k in ('perc', 'ref'):
        rows = [v[k] for e, v in out['shifts'].items() if k in v and e != 23]
        print(k, len(rows), {L: (round(float(np.mean([r[L] - r['0'] for r in rows])), 4), sum(r[L] > r['0'] for r in rows)) for L in rows[0] if L != '0'})
    json.dump(out, open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
