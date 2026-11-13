#!/usr/bin/env python
"""C2/R scoring (PREREG section 6): ONE mesh_metric.py run of the committed pick, unless its sha1[:16] already has a
score record (then that record is reported and nothing is scored). Then the WIN rule.
Usage: python -I score_c2r.py MESH.glb LABEL OUT.jsonl
"""
import glob, hashlib, json, os, subprocess, sys

MESH, LABEL, OUT = sys.argv[1:4]
MR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
SCR = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
OBJ = 'plastic_dish_rack'
C0_CDO, LIB_ADD = 0.45604, 5.79
sha16 = hashlib.sha1(open(MESH, 'rb').read()).hexdigest()[:16]
prior = []
for f in glob.glob(f'{MR}/results/**/*.jsonl', recursive=True) + glob.glob(f'{MR}/cdo-sprint/**/*.jsonl', recursive=True):
    if os.path.abspath(f) == os.path.abspath(OUT):
        continue
    for l in open(f, errors='replace'):
        if f'"{sha16}"' in l:
            try:
                r = json.loads(l)
            except Exception:  # noqa: BLE001
                continue
            if r.get('sha') == sha16 and 'cdo_eval' in r:
                prior.append((f, r))
if prior:
    f, rec = prior[0]
    print(json.dumps(dict(note='existing record used, nothing scored', file=f, label=rec['label'])))
else:
    if os.path.exists(OUT) and any(f'"{sha16}"' in l for l in open(OUT)):
        sys.exit(f'{sha16} already scored in {OUT}: refusing a second scoring')
    cmd = [f'{SCR}/venv/bin/python', '-I', f'{MR}/scripts/mesh_metric.py', 'run', '--out', OUT, '--workers', '2',
           f'{LABEL}={OBJ}={os.path.abspath(MESH)}']
    print(' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    rec = [json.loads(l) for l in open(OUT) if f'"{sha16}"' in l][-1]
win = dict(cdo=rec['cdo_eval'] <= C0_CDO - 0.02 + 1e-9, add=rec['add_med'] <= LIB_ADD + 2.0 + 1e-9,
           flips=rec['flips_all'] == 0)
res = dict(label=rec['label'], sha1_16=sha16, cdo_eval=rec['cdo_eval'], cdo_all=rec.get('cdo_all'),
           add_med=rec['add_med'], add_eval=rec.get('add_eval'), add_max=rec.get('add_max'), flips_all=rec['flips_all'],
           amb_mm=rec.get('amb_mm'), thresholds=dict(cdo_le=round(C0_CDO - 0.02, 5), add_med_le=LIB_ADD + 2.0, flips_all=0),
           checks=win, WIN=all(win.values()), H_R_strong=rec['cdo_eval'] <= 0.40)
json.dump(res, open(OUT.replace('.jsonl', '_verdict.json'), 'w'), indent=1)
print(json.dumps(res))
