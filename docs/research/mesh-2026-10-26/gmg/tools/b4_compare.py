"""b4_compare: v4 (pre-registered B4 run) against v5 (round-2 rerun) from their git summaries (build/b4/*.json and
build/b4/v5/*.json). Small JSON for git; reads only the summary files b4_report wrote (no bundle, no data).

Per object-episode: seed rule, seed points, guard, component voxels before / after the guard, OBSERVED voxels, sigma,
good frames, flags, B.3 Jaccard and outside share, cross-test verdict and distances. Per pair: B.2a leakage per
direction (and the v5 per-frame-gap diagnostic). Verdict lines of B.2a, B.3 and B.15 for both runs, plus the C.2
anchors.
Usage: python gmg/tools/b4_compare.py --v4 gmg/build/b4 --v5 gmg/build/b4/v5 --out gmg/build/b4/v5/compare_v4_v5.json
"""
import argparse
import json
import os


def load(d, name):
    p = os.path.join(d, name)
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--v4', required=True)
    ap.add_argument('--v5', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    S = {k: load(d, 'summary.json') for k, d in (('v4', a.v4), ('v5', a.v5))}
    B3 = {k: load(d, 'b3.json') for k, d in (('v4', a.v4), ('v5', a.v5))}
    B2 = {k: load(d, 'b2a.json') for k, d in (('v4', a.v4), ('v5', a.v5))}
    B15 = {k: load(d, 'b15.json') for k, d in (('v4', a.v4), ('v5', a.v5))}
    b3rec = {k: {(r['ep'], r['obj']): r for r in (v or {}).get('records', [])} for k, v in B3.items()}
    b15row = {k: {(r['ep'], r['obj']): r for r in (v or {}).get('rows', [])} for k, v in B15.items()}
    rows = []
    for ep in sorted(S['v4'], key=lambda e: int(e[2:])):
        for o in S['v4'][ep]['objects']:
            row = dict(ep=int(ep[2:]), obj=o)
            for k in ('v4', 'v5'):
                r = (S[k] or {}).get(ep, {}).get('obj', {}).get(o)
                if r is None:
                    row[k] = None
                    continue
                cr = r['crop']
                b3 = b3rec[k].get((int(ep[2:]), o), {})
                idr = b15row[k].get((int(ep[2:]), o), {})
                row[k] = dict(seed=cr.get('seed'), seed_points=cr.get('seed_points'), det_iou=cr.get('det_iou'),
                              seed_box_mm=cr.get('seed_box_mm'), comp_box_mm=cr.get('comp_box_mm'),
                              guard=cr.get('guard'), comp_vox=cr.get('component_voxels'),
                              comp_vox_after_guard=cr.get('component_voxels_after_guard'),
                              seed_unowned=cr.get('seed_unowned'), observed=r['observed'], owned=r['owned'],
                              sigma_mm=r['sigma_mm'], n_good=r['sanity']['n_good'], flags=r['sanity']['flags'],
                              b3_jaccard=b3.get('jaccard'), b3_outside=b3.get('outside_share'),
                              cross=(idr.get('cross') or {}).get('pass_'),
                              cross_d_own=(idr.get('cross') or {}).get('d_own_mm'),
                              cross_d_other=(idr.get('cross') or {}).get('d_other_mm'),
                              cross_nearest=(idr.get('cross') or {}).get('nearest'),
                              split={p: v for p, v in (idr.get('split') or {}).items()})
            rows.append(row)
    pairs = []
    for k in ('v4', 'v5'):
        for pr in (B2[k] or {}).get('pairs', []):
            rec = dict(run=k, ep=pr['ep'], pair=pr['pair'], included=pr['included'], pair_fail=pr.get('pair_fail'),
                       directions=[(d['target'], d.get('sep3d_frames'), d.get('leakage'))
                                   for d in pr.get('directions', [])])
            if pr.get('diag_frame_gap'):
                rec['diag_frame_gap'] = [(d['target'], d.get('sep3d_frames'), d.get('leakage'))
                                         for d in pr['diag_frame_gap']['directions']]
            pairs.append(rec)
    verd = {k: dict(B2a=(B2[k] or {}).get('verdict'), B2a_testable=(B2[k] or {}).get('testable_pairs'),
                    B2a_failing=(B2[k] or {}).get('failing_pairs'),
                    B3=(B3[k] or {}).get('verdict'), B3_jaccard_ge_095=(B3[k] or {}).get('jaccard_ge_095'),
                    B3_outside_le_5pct=(B3[k] or {}).get('outside_le_5pct'),
                    B15_cross_flagged=(B15[k] or {}).get('cross_flagged'),
                    B15_split_flagged=(B15[k] or {}).get('split_flagged'),
                    B15_seed0=(B15[k] or {}).get('seed0'), P22_supported=(B15[k] or {}).get('P22_supported'),
                    anchors={o: v['anchor'] for o, v in ((B15[k] or {}).get('anchors') or {}).items()})
            for k in ('v4', 'v5')}
    json.dump(dict(note='v4 = pre-registered B4 run (20261031-b4ext4-b61e8aa); v5 = round-2 rerun, post-hoc [M]',
                   verdicts=verd, objects=rows, b2a_pairs=pairs), open(a.out, 'w'), indent=1)
    print(json.dumps(verd, indent=1))


if __name__ == '__main__':
    main()
