"""C0b pre-registered scoring [D] (PREREG C0b section 6): ONE mesh_metric evaluate() per picked mesh, default seeds (the
eval seeds of the object's pairs, plus extra seeds 11, 22, ... up to at least 6 seeds; no 30-seed flip set), then the
WIN rule. Public scans are stand-ins for the hidden scans (diagnostic). Run ONLY after the picks are committed and
pushed (PREREG 5.4 / 11.3).
  - refuses a mesh whose sha1[:16] results/score_c0b.jsonl already holds (one scoring per distinct mesh);
  - if the sha1[:16] equals a record in an existing repo score file (SCORED below), that record is used and nothing is
    scored (recorded as reused);
  - WIN: cdo_eval <= L - 0.02 and add_med <= A + 2.0 mm and (white_pot, plastic_dish_rack) flips_all = 0;
    beige: eval 10 CD-O (seed 10000131) <= 0.83625 and eval 8 CD-O (seed 8000024) <= 0.70995 and add_med <= 8.965.
    4-decimal seed values as written; a value exactly at a threshold passes.
Usage: score_c0b.py OBJECT MESH.glb OUT.jsonl
"""
import glob, json, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(MR, 'scripts'))
import mesh_metric as MM  # noqa: E402

LIB = {'white_pot': (0.43712, 6.69), 'white_pot_lid': (0.4211, 8.13), 'plastic_dish_rack': (0.55506, 5.79),
       'blue_cup': (0.52332, 10.14)}
FLIP_RULE = ('white_pot', 'plastic_dish_rack')
BEIGE = dict(ev10_seed=10000131, ev10_max=0.83625, ev8_seed=8000024, ev8_max=0.70995, add_max=8.965)
EPS = 1e-9
SCORED = [os.path.join(MR, 'results', '*.jsonl'), os.path.join(MR, 'results', 'prim', '**', '*.jsonl'),
          os.path.join(MR, 'cdo-sprint', '**', '*.jsonl')]


def rule(o, rec):
    if o == 'beige_cup':
        s = {r['seed']: r for r in rec['seeds']}
        c10, c8 = s[BEIGE['ev10_seed']]['cdo_cm'], s[BEIGE['ev8_seed']]['cdo_cm']
        G = dict(cdo_ev10=c10, cdo_ev8=c8, add_med=rec['add_med'], flips_all=rec['flips_all'],
                 ev10_ok=bool(c10 <= BEIGE['ev10_max'] + EPS), ev8_ok=bool(c8 <= BEIGE['ev8_max'] + EPS),
                 add_ok=bool(rec['add_med'] <= BEIGE['add_max'] + EPS), flip_rule='exempt (kit-symmetric)')
        G['win'] = bool(G['ev10_ok'] and G['ev8_ok'] and G['add_ok'])
        return G
    L, A = LIB[o]
    G = dict(L=L, A=A, cdo_eval=rec['cdo_eval'], add_med=rec['add_med'], flips_all=rec['flips_all'],
             cdo_ok=bool(rec['cdo_eval'] <= L - 0.02 + EPS), add_ok=bool(rec['add_med'] <= A + 2.0 + EPS))
    if o in FLIP_RULE:
        G['flip_ok'] = bool(rec['flips_all'] == 0)
    else:
        G['flip_ok'] = True; G['flip_rule'] = 'exempt (kit-symmetric)'
    G['win'] = bool(G['cdo_ok'] and G['add_ok'] and G['flip_ok'])
    return G


def main():
    o, path, out = sys.argv[1:4]
    sha = MM.sha(path)
    if os.path.exists(out) and any(json.loads(l).get('sha') == sha for l in open(out) if l.strip()):
        raise SystemExit(f'{path} (sha1 {sha}) already scored in {out}: refusing a second scoring')
    prior = None
    for pat in SCORED:
        for f in sorted(glob.glob(pat, recursive=True)):
            if os.path.abspath(f) == os.path.abspath(out):
                continue
            for l in open(f):
                if l.strip().startswith('{'):
                    try:
                        r = json.loads(l)
                    except ValueError:
                        continue
                    if r.get('sha') == sha and r.get('object') == o and 'cdo_eval' in r and 'seeds' in r:
                        prior = dict(r, reused_from=os.path.relpath(f, MR))
                        break
            if prior:
                break
        if prior:
            break
    if prior is not None:
        rec = prior
        rec['scoring'] = 'reused (identical sha1[:16]; nothing scored)'
    else:
        rec = MM.evaluate(f'C0b/{o}', o, path, group='cdo_c0b')
        rec['scoring'] = 'scored once (mesh_metric.evaluate defaults)'
    rec['gates_c0b'] = rule(o, rec)
    with open(out, 'a') as fh:
        fh.write(json.dumps(rec) + '\n')
    print(json.dumps({k: rec.get(k) for k in ('label', 'object', 'sha', 'scoring', 'cdo_eval', 'cdo_all', 'add_med',
                                               'add_max', 'flips_all', 'n_seeds', 'amb_mm', 'secs')}))
    print(json.dumps(rec['gates_c0b']))


if __name__ == '__main__':
    main()
