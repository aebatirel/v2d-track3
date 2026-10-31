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
                         'clean_run', keys=['frame', 'pix', 'code', 'tied', 'objects', 'W'])
    if list(np.asarray(own['objects'])) != objs:
        raise ValueError('owners.npz objects differ from the bundle')
    ofr, opix, ocode = np.asarray(own['frame']), np.asarray(own['pix']), np.asarray(own['code'])
    otied = np.asarray(own['tied'])
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
                      free=np.zeros(int(np.prod(shp)), np.int32), old_hits=np.asarray(z['hits']).ravel(),
                      cat=np.zeros((4, int(np.prod(shp))), np.int32))
    # re-vote the clean labels on the old lattices
    order = np.argsort(ofr, kind='stable')
    ofr, opix, ocode, otied = ofr[order], opix[order], ocode[order], otied[order]
    starts = np.searchsorted(ofr, frames)
    ends = np.searchsorted(ofr, frames, side='right')
    for i, t in enumerate(frames):
        Dt = EJ.filtered_depth(Dm[t], c['edge'])
        pix, code = opix[starts[i]:ends[i]], ocode[starts[i]:ends[i]]
        tied = otied[starts[i]:ends[i]]
        pv, pu = np.divmod(pix.astype(np.int64), W)
        for o, r in old.items():
            # label categories (the B.3 pass rule uses 1 only; 2-4 feed the diagnostic, DEVIATIONS 100):
            # 1 owned by o, 2 shared with o in the tie set, 3 owned by another object or shared without o,
            # 4 unowned (no object's keep rule passes at the sample's voxel, or outside every seeded component)
            k = r['k']
            ink = ((tied >> k) & 1).astype(bool)
            cat = np.where(code == k, 1, np.where(code == EJ.NONE, 4,
                                                  np.where((code == EJ.SHARED) & ink, 2, 3))).astype(np.int8)
            lab = np.zeros(Dt.shape, np.int8)
            lab[pv, pu] = cat
            fl, hl = EJ.vote(Dt, lab, P[f'cam_T_{o}'][t].astype(np.float64), r['axes'], K, c, nlab=4)
            r['free'][fl] += 1
            r['hits'][hl[0]] += 1
            for q in range(4):
                r['cat'][q][hl[q]] += 1
    for o, r in old.items():
        new_st = BU.state_grid(r['hits'].reshape(r['shape']), r['free'].reshape(r['shape']))
        A, B = r['st'] == 2, new_st == 2
        inter, union = int((A & B).sum()), int((A | B).sum())
        jac = inter / union if union else float('nan')
        z = guard.load_npz(os.path.join(bdir, f'{o}.npz'), 'clean_run', keys=['state', 'lo', 'vox', 'pocc', 'shared'])
        st = np.asarray(z['state'])
        # diagnostic (not the B.3 pass condition): the Jaccard over old-lattice voxels whose clean voxel (the one holding
        # the old centre) has no partner evidence (pocc == 0 and shared == 0). obs_points.py never removed partner
        # surfaces from its hit votes (--others filtered the points only), so old OBSERVED includes partner voxels.
        oi = np.argwhere(np.ones(r['shape'], bool))
        oc = r['lo'] + (oi + 0.5) * r['vox']
        vi = np.floor((oc - np.asarray(z['lo'], np.float64)) / float(z['vox'])).astype(np.int64)
        ins = np.all((vi >= 0) & (vi < np.asarray(st.shape)), axis=1)
        part = np.zeros(len(oc), bool)
        pg = (np.asarray(z['pocc']) > 0) | (np.asarray(z['shared']) > 0)
        part[ins] = pg[tuple(vi[ins].T)]
        part = part.reshape(r['shape'])
        A2, B2 = A & ~part, B & ~part
        u2 = int((A2 | B2).sum())
        jac_np = int((A2 & B2).sum()) / u2 if u2 else float('nan')
        ijk = np.argwhere(st == 2)
        ctr = np.asarray(z['lo'], np.float64) + (ijk + 0.5) * float(z['vox'])
        out = ~np.all((ctr >= r['lo']) & (ctr <= r['hi']), axis=1)
        # diagnostic (DEVIATIONS 100): where the old hits of the lost voxels went, and the Jaccard if other sample
        # categories counted as hits (all in-cube samples = the obs_points.py vote with the clean filters)
        lost = (A & ~B).ravel()
        cat = r['cat']
        fr_ = r['free'].reshape(r['shape'])

        def jac_with(qs):
            Bq = BU.state_grid(np.clip(cat[list(qs)].sum(0), 0, 65535).reshape(r['shape']).astype(np.uint16),
                               np.clip(fr_, 0, 65535).astype(np.uint16)) == 2
            uq = int((A | Bq).sum())
            return round(int((A & Bq).sum()) / uq, 4) if uq else float('nan')
        diag = dict(lost_hits_old=int(r['old_hits'][lost].sum()),
                    lost_hits_revote={nm: int(cat[q][lost].sum()) for q, nm in
                                      enumerate(('owned', 'shared_with_o', 'other_object', 'unowned'))},
                    lost_median_old_hits=float(np.median(r['old_hits'][lost])) if lost.any() else None,
                    kept_median_old_hits=float(np.median(r['old_hits'][(A & B).ravel()])) if (A & B).any() else None,
                    jaccard_all_samples_diag=jac_with((0, 1, 2, 3)),
                    jaccard_owned_unowned_diag=jac_with((0, 3)),
                    jaccard_owned_shared_unowned_diag=jac_with((0, 1, 3)))
        rec = dict(ep=ep, obj=o, hands_in_obs_all=r['hands'], jaccard=round(jac, 4), old_observed=int(A.sum()),
                   new_observed_on_old_lattice=int(B.sum()), intersection=inter,
                   clean_observed=int(len(ctr)), clean_observed_outside_old_box=int(out.sum()),
                   outside_share=round(float(out.mean()) if len(out) else float('nan'), 4),
                   old_only=int((A & ~B).sum()), new_only=int((B & ~A).sum()),
                   old_only_partner_evidence=int((A & ~B & part).sum()),
                   jaccard_no_partner_evidence_diag=round(jac_np, 4),
                   pass_jaccard=bool(jac >= 0.95), pass_outside=bool(len(out) and out.mean() <= 0.05),
                   attribution_diag=diag)
        recs.append(rec)
        print(json.dumps(rec), flush=True)
    os.makedirs(os.path.join(run, 'b3'), exist_ok=True)
    with open(os.path.join(run, 'b3', f'{split}-ep{ep}.json'), 'w') as f:
        json.dump(dict(ep=ep, clean_run=os.path.basename(os.path.realpath(a.clean_run)), records=recs,
                       sec=round(time.time() - t0, 1)), f, indent=1)
    guard.write_manifest(os.path.join(run, 'b3', f'{split}-ep{ep}.manifest.json'), extra=dict(step='B4', prereg='B.3'))


if __name__ == '__main__':
    main()
