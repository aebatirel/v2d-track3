"""b4_roi_swap: PREREG B.3 (ROI swap, prediction P3) for one public episode. Validation only (GMG_MODE=dev).

For every obs_all file of the episode (the old extraction: library_v3 ROI box + --others; dev read, keys lo, hi, vox,
hits, free, args only; the deny-listed mesh is never opened), compare with the CLEAN extraction of this build step:
  - Jaccard of OBSERVED voxels inside the old box, at the voxel level: the clean ownership labels (RUN/aux owners.npz:
    the final owner of every sample) are re-voted on the OLD lattice with the same voxel-centric rule as the clean
    grid (hits from the object's owned samples only, free from every valid depth ray; obs_points.py rule) and the A.2
    state rule; old OBSERVED = the A.2 rule on obs_all hits/free;
  - new OBSERVED voxels outside the old box: OBSERVED voxels of the clean bundle grid (its own lattice) whose centre
    lies outside [lo, hi] of the obs_all file, as a share of all OBSERVED voxels of the clean grid.
Pass (B.3): Jaccard >= 0.95 on >= 23 of the 25 files that had hands, and outside share <= 5 % on >= 23 of 25 (the 8
hands-null files are reported apart). This tool writes one record per file; tools/b4_report.py applies the counts.
Reads: the clean run's bundle and aux (dev role clean_run), the depth (role depth), tracks, calib, obs_all (dev).
Usage: GMG_MODE=dev python gmg/tools/b4_roi_swap.py --clean-run <DATA>/gmg/runs/<clean run> --run <DATA>/gmg/runs-dev/
       <yyyymmdd>-b4roi-<commit7> --ep 2
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.dirname(os.path.dirname(HERE))
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--clean-run', required=True)
    ap.add_argument('--run', required=True)
    ap.add_argument('--split', default='public', choices=['public'])
    ap.add_argument('--ep', type=int, required=True)
    a = ap.parse_args()
    if guard.mode() != 'dev':
        raise SystemExit('b4_roi_swap runs in GMG_MODE=dev only (it reads obs_all)')
    import numpy as np
    from gmg import extract_joint as EJ, bundle as BU
    run = guard.set_run(a.run)
    D = guard.CFG['data']
    ep, split = a.ep, a.split
    t0 = time.time()
    bdir = os.path.join(os.path.realpath(a.clean_run), 'bundle', split, f'ep{ep}')
    meta = guard.load_json(os.path.join(bdir, 'episode.json'), 'clean_run')
    objs = meta['objects']
    c = EJ.consts(meta['vox'], 0.30, meta['stride'])
    own = guard.load_npz(os.path.join(os.path.realpath(a.clean_run), 'aux', split, f'ep{ep}', 'owners.npz'),
                         'clean_run', keys=['frame', 'pix', 'code', 'objects', 'W'])
    if list(np.asarray(own['objects'])) != objs:
        raise ValueError('owners.npz objects differ from the bundle')
    ofr, opix, ocode = np.asarray(own['frame']), np.asarray(own['pix']), np.asarray(own['code'])
    W = int(own['W'])
    tracks = os.path.join(D, 'data', 'sweep', f'ep{ep}', 'poses.npz')
    P = guard.load_npz(tracks, 'tracks')
    if guard._INPUTS[os.path.realpath(tracks)]['sha256'] != meta['tracks']['sha256']:
        raise ValueError('tracks differ from the clean bundle')
    depth = guard.open_input(os.path.join(D, 'cache', 'depth', split, f'ep{ep}', 'depths_fs0.5.npy'), 'depth')
    if guard._INPUTS[os.path.realpath(depth)]['sha256'] != meta['depth']['sha256']:
        raise ValueError('depth differs from the clean bundle')
    Dm = np.load(depth, mmap_mode='r')
    K = np.asarray(meta['K'], np.float64)
    frames = list(range(0, int(meta['T']), int(meta['stride'])))
    recs = []
    old = {}
    for k, o in enumerate(objs):
        p = os.path.join(D, 'obs_all', f'ep{ep}_{o}.npz')
        if not os.path.exists(p):
            continue
        z = guard.load_npz(p, 'obs_all', keys=['lo', 'hi', 'vox', 'hits', 'free', 'args'])
        args = json.loads(str(z['args']))
        lo, hi, vx = np.asarray(z['lo'], np.float64), np.asarray(z['hi'], np.float64), float(z['vox'])
        shp = tuple(np.asarray(z['hits']).shape)
        axes = tuple(lo[d] + (np.arange(shp[d]) + 0.5) * vx for d in range(3))
        old[o] = dict(k=k, lo=lo, hi=hi, vox=vx, shape=shp, axes=axes,
                      st=BU.state_grid(np.asarray(z['hits']), np.asarray(z['free'])),
                      hands=bool(args.get('hands')), hits=np.zeros(int(np.prod(shp)), np.int32),
                      free=np.zeros(int(np.prod(shp)), np.int32))
    # re-vote the clean labels on the old lattices
    order = np.argsort(ofr, kind='stable')
    ofr, opix, ocode = ofr[order], opix[order], ocode[order]
    starts = np.searchsorted(ofr, frames)
    ends = np.searchsorted(ofr, frames, side='right')
    for i, t in enumerate(frames):
        Dt = EJ.filtered_depth(Dm[t], c['edge'])
        pix, code = opix[starts[i]:ends[i]], ocode[starts[i]:ends[i]]
        pv, pu = np.divmod(pix.astype(np.int64), W)
        for o, r in old.items():
            lab = np.zeros(Dt.shape, np.int8)
            sel = code == r['k']
            lab[pv[sel], pu[sel]] = 1
            fl, (hl,) = EJ.vote(Dt, lab, P[f'cam_T_{o}'][t].astype(np.float64), r['axes'], K, c)
            r['free'][fl] += 1
            r['hits'][hl] += 1
    for o, r in old.items():
        new_st = BU.state_grid(r['hits'].reshape(r['shape']), r['free'].reshape(r['shape']))
        A, B = r['st'] == 2, new_st == 2
        inter, union = int((A & B).sum()), int((A | B).sum())
        jac = inter / union if union else float('nan')
        z = guard.load_npz(os.path.join(bdir, f'{o}.npz'), 'clean_run', keys=['state', 'lo', 'vox'])
        st = np.asarray(z['state'])
        ijk = np.argwhere(st == 2)
        ctr = np.asarray(z['lo'], np.float64) + (ijk + 0.5) * float(z['vox'])
        out = ~np.all((ctr >= r['lo']) & (ctr <= r['hi']), axis=1)
        rec = dict(ep=ep, obj=o, hands_in_obs_all=r['hands'], jaccard=round(jac, 4), old_observed=int(A.sum()),
                   new_observed_on_old_lattice=int(B.sum()), intersection=inter,
                   clean_observed=int(len(ctr)), clean_observed_outside_old_box=int(out.sum()),
                   outside_share=round(float(out.mean()) if len(out) else float('nan'), 4),
                   old_only=int((A & ~B).sum()), new_only=int((B & ~A).sum()),
                   pass_jaccard=bool(jac >= 0.95), pass_outside=bool(len(out) and out.mean() <= 0.05))
        recs.append(rec)
        print(json.dumps(rec), flush=True)
    os.makedirs(os.path.join(run, 'b3'), exist_ok=True)
    with open(os.path.join(run, 'b3', f'{split}-ep{ep}.json'), 'w') as f:
        json.dump(dict(ep=ep, clean_run=os.path.basename(os.path.realpath(a.clean_run)), records=recs,
                       sec=round(time.time() - t0, 1)), f, indent=1)
    guard.write_manifest(os.path.join(run, 'b3', f'{split}-ep{ep}.manifest.json'), extra=dict(step='B4', prereg='B.3'))


if __name__ == '__main__':
    main()
