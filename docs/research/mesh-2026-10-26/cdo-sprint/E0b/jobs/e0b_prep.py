"""E0b GT-free helpers (C0b PREREG section 9, 10). Every C0b command of ../../C0b/jobs/c0b_prep.py, unchanged, with the
markers bundle stand-in labelled split='eval', tier='E0b' (a label only: detect_episode's settings and arithmetic are
the frozen A.6 ones, sha asserted by c0b_prep), plus:

  fthr OUT.json PLAN.json FREF_DIR                frame-check thresholds (PREREG 9 (c)): per object with a C0b public
                                                  pick, 3 x the maximum of each statistic (centroid offset, median
                                                  symmetric surface distance, PCA axis angles) over the reference
                                                  candidates (eligible C0b public candidates from other public
                                                  episodes, each measured against the pick by C0's frame_check.py);
                                                  an axis is not checked when the pick's PCA eigenvalue is within a
                                                  ratio >= 0.8 of a neighbour (E0 / C0 frame_check rule)
Reads only our own files (frame_check outputs of our meshes, the plan).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'C0b', 'jobs')))
import c0b_prep as P  # noqa: E402


class _EvalBundle(P._Bundle):
    def __init__(self, ep, objects, obs, T):
        super().__init__(ep, objects, obs, T)
        self.meta.update(split='eval', tier='E0b')


P._Bundle = _EvalBundle
FACTOR = 3.0
SHORT = {'white_pot': 'pot', 'white_pot_lid': 'lid', 'plastic_dish_rack': 'rack', 'blue_cup': 'cup', 'beige_cup': 'beige'}
DEGEN = 0.8


def cmd_fthr(out, plan, fref):
    plan = json.load(open(plan))
    res = dict(rule='PREREG C0b 9 (c): threshold = 3 x max over the reference candidates of each statistic, measured '
                    'against the C0b public pick (C0 frame_check.py, no registration); axis not checked when the '
                    "pick's PCA eigenvalue is within a ratio >= 0.8 of a neighbour", factor=FACTOR, objects={})
    for o, fr in plan['frame_refs'].items():
        rows = []
        for r in fr['references']:
            f = os.path.join(fref, SHORT[o], r['label'].replace('/', '__') + '.json')
            k = json.load(open(f))['results'][o]
            rows.append(dict(label=r['label'], centroid_offset_mm=k['centroid_offset_mm'],
                             surf_symmetric_median_mm=k['surf_symmetric_median_mm'], axis_angle_deg=k['axis_angle_deg'],
                             pick_pca_sd_mm=k['lib']['pca_sd_mm']))
        if not rows:
            res['objects'][o] = dict(pick=fr['pick'], n_references=0, excludes=False,
                                     note='no reference candidate from another public episode: frame check reported only')
            continue
        sd = rows[0]['pick_pca_sd_mm']
        ev = [s * s for s in sd]
        checked = []
        for i in range(3):
            nb = [j for j in (i - 1, i + 1) if 0 <= j < 3]
            checked.append(not any(min(ev[i], ev[j]) / max(ev[i], ev[j]) >= DEGEN for j in nb))
        mx_c = max(r['centroid_offset_mm'] for r in rows)
        mx_s = max(r['surf_symmetric_median_mm'] for r in rows)
        mx_a = [max(r['axis_angle_deg'][i] for r in rows) for i in range(3)]
        res['objects'][o] = dict(
            pick=fr['pick'], n_references=len(rows), excludes=True, pick_pca_sd_mm=sd,
            eigen_ratios_neighbour=[min(ev[0], ev[1]) / max(ev[0], ev[1]), min(ev[1], ev[2]) / max(ev[1], ev[2])],
            axis_checked=checked, ref_max_centroid_offset_mm=mx_c, ref_max_surf_symmetric_median_mm=mx_s,
            ref_max_axis_angle_deg=mx_a, max_centroid_offset_mm=FACTOR * mx_c,
            max_surf_symmetric_median_mm=FACTOR * mx_s,
            max_axis_angle_deg=[FACTOR * a if c else None for a, c in zip(mx_a, checked)], references=rows)
    json.dump(res, open(out, 'w'), indent=1)
    for o, v in res['objects'].items():
        print(o, json.dumps({k: v.get(k) for k in ('pick', 'n_references', 'max_centroid_offset_mm',
                                                   'max_surf_symmetric_median_mm', 'max_axis_angle_deg', 'axis_checked')}))


if __name__ == '__main__':
    if sys.argv[1] == 'fthr':
        cmd_fthr(*sys.argv[2:5])
    else:
        P.main()
