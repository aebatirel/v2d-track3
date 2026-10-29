"""verify_timing: offset (settling) crossings, own code (27 Oct 2026). Offset = the time-reversed onset crossing
against the END rest pose (mean of the last 5 frames): the last time the tracked point is > thr from its end rest.
lag = ours - mocap (> 0: ours settles LATER). Usage: python -I vt_offset.py OUT.json"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vt_load as L
from vt_lag import cross


def off_cross(P, thr):
    d = np.linalg.norm(P - P[-5:].mean(0), axis=1)[::-1]
    t = cross(d, thr)
    return None if t is None else (len(d) - 1) - t


def main():
    C = L.canon(); out = []
    for ep in L.PUBLIC:
        if ep == 23:
            continue
        e = C[ep]; names, gt = L.load_mocap(ep); fin, pre = L.ref_paths(e)
        srcs = {'perc': (L.load_npz(f"{L.STORE}/{e['perception_path']}"), L.lib_of(e, 'perc'))}
        if fin:
            srcs['pre'] = (L.load_refpq(pre), L.lib_of(e, 'ref')); srcs['ref'] = (L.load_refpq(fin), L.lib_of(e, 'ref'))
        for n in names:
            Pg = L.point_path(gt[n], L.surf_centroid(L.scan_mesh(n)))
            if np.linalg.norm(Pg - Pg[:5].mean(0), axis=1).max() < 0.03:
                continue
            row = dict(ep=ep, obj=n, gt_1cm=off_cross(Pg, 0.01), gt_2cm=off_cross(Pg, 0.02))
            for s, (P, lib) in srcs.items():
                Po = L.point_path(P[n], L.surf_centroid(L.our_mesh(lib, n)))
                for thr, k in ((0.01, '1cm'), (0.02, '2cm')):
                    t = off_cross(Po, thr)
                    row[f'{s}_lag_{k}'] = None if t is None or row[f'gt_{k}'] is None else round(t - row[f'gt_{k}'], 2)
            out.append(row); print(row)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    for s in ('perc', 'pre', 'ref'):
        for k in ('1cm', '2cm'):
            v = np.array([r[f'{s}_lag_{k}'] for r in out if r.get(f'{s}_lag_{k}') is not None])
            print(s, k, 'n', len(v), 'median %.2f IQR %.2f..%.2f' % (np.median(v), *np.percentile(v, [25, 75])))


if __name__ == '__main__':
    main()
