"""C2/P GT-free pick (PREREG.md section 4 = C0b PREREG section 5 applied to the pitcher).
  1. exclusions: raw mesh not watertight (trimesh, process=True); kit budget_mesh(path, 4096, 4096) raises or leaves
     more than 4096 faces or vertices; no fidelity value;
  2. fidelity: obs_fidelity.py OBS_ep21,OBS_ep22 MESH with defaults (trim 0.9, 300k observed points, 200k mesh samples,
     seed 0, no ICP), one mesh per process, on the C0b pass-B points of BOTH public episodes (set ALL);
  3. pick: lowest sum_mm; ties (equal to 3 decimals) -> fewer raw faces -> label in byte order.
Reported only (never deciding): fidelity on each episode alone; library_v3 water_pitcher on the same points.
Usage: pick_p.py W OUT.json [REPORT_MESH ...] [--sets=ALL|ep21,ep22] [--cand=DIR]   (defaults: all three sets, cand)
"""
import json, os, subprocess, sys
import trimesh

args = [x for x in sys.argv[1:] if not x.startswith('--')]
CAND = next((x.split('=', 1)[1] for x in sys.argv[1:] if x.startswith('--cand=')), 'cand')   # A2: --cand=cand_a2
SETS = next((x.split('=', 1)[1].split(',') for x in sys.argv[1:] if x.startswith('--sets=')), ['ALL', 'ep21', 'ep22'])
W, out = args[0], args[1]
report = args[2:]
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
R = '/home/user/v2d-track3'
PY = f'{S}/venv/bin/python'
FID = f'{R}/docs/research/mesh-2026-10-26/scripts/obs_fidelity.py'
KIT = f'{S}/kit/v2d_submission_kit'
OBS = {'ALL': f'{W}/pts/B/ep21_water_pitcher.npz,{W}/pts/B/ep22_water_pitcher.npz',
       'ep21': f'{W}/pts/B/ep21_water_pitcher.npz', 'ep22': f'{W}/pts/B/ep22_water_pitcher.npz'}
OBS = {k: v for k, v in OBS.items() if k in SETS}      # --sets=ALL: the deciding set only (per-episode = report run)
LABELS = [f'{s}_{v}' for s in ('ep21', 'ep22', 'merged', 'ep21r', 'ep22r', 'mergedr') for v in ('g1', 'g0')]   # A1: +r


def fid(obs, mesh):
    r = subprocess.run([PY, '-I', FID, obs, mesh], capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.startswith('{')]
    return json.loads(lines[-1]) if r.returncode == 0 and lines else dict(error=r.stderr[-500:])


def budget_ok(path):
    code = ('import sys; sys.path.insert(0, %r); from v2dlb.mesh_budget import budget_mesh; import trimesh, json; '
            'm = budget_mesh(%r, 4096, 4096); m = m if isinstance(m, trimesh.Trimesh) else trimesh.Trimesh(*m); '
            'print(json.dumps(dict(v=len(m.vertices), f=len(m.faces))))') % (KIT, path)
    r = subprocess.run([PY, '-I', '-c', code], capture_output=True, text=True)
    if r.returncode != 0:
        return False, r.stderr[-300:]
    d = json.loads(r.stdout.strip().splitlines()[-1])
    return d['v'] <= 4096 and d['f'] <= 4096, d


from concurrent.futures import ThreadPoolExecutor   # fidelity processes run 3 at a time (same commands, one mesh each)
paths = {lab: f'{W}/{CAND}/{lab.split("_")[0]}_water_pitcher_{lab.split("_")[1]}.glb' for lab in LABELS}
jobs = [(lab, k) for lab in LABELS if os.path.exists(paths[lab]) for k in OBS] + [(p, k) for p in report for k in OBS]
with ThreadPoolExecutor(3) as ex:
    FID_RES = dict(zip(jobs, ex.map(lambda j: fid(OBS[j[1]], paths.get(j[0], j[0])), jobs)))
rows = []
for lab in LABELS:
    p = paths[lab]
    row = dict(label=lab, path=p, exists=os.path.exists(p))
    if not row['exists']:
        row['excluded'] = 'build failed / missing'
        rows.append(row); continue
    m = trimesh.load(p, force='mesh', process=True)
    row.update(faces=int(len(m.faces)), watertight=bool(m.is_watertight))
    ok, info = budget_ok(p)
    row['budget'] = info
    row['fid'] = {k: FID_RES[(lab, k)] for k in OBS}
    if not row['watertight']:
        row['excluded'] = 'not watertight'
    elif not ok:
        row['excluded'] = 'budget_mesh'
    elif 'ALL' in OBS and 'sum_mm' not in row['fid']['ALL']:
        row['excluded'] = 'no fidelity'
    rows.append(row)
    print(json.dumps({k: row.get(k) for k in ('label', 'faces', 'watertight', 'excluded')}),
          {k: v.get('sum_mm') for k, v in row['fid'].items()}, flush=True)
ok = [r for r in rows if 'excluded' not in r]
pick = min(ok, key=lambda r: (round(r['fid']['ALL']['sum_mm'], 3), r['faces'], r['label'].encode())) if ok and 'ALL' in OBS else None
rep = []
for p in report:
    rep.append(dict(path=p, fid={k: FID_RES[(p, k)] for k in OBS}))
    print('report', p, {k: v.get('sum_mm') for k, v in rep[-1]['fid'].items()}, flush=True)
res = dict(rule='lowest obs_fidelity sum_mm on ALL (ep21+ep22 C0b pass-B points); ties: fewer faces, label',
           candidates=rows, pick=None if pick is None else dict(label=pick['label'], path=pick['path'],
                                                               sum_mm=pick['fid']['ALL']['sum_mm']),
           reported_only=rep)
json.dump(res, open(out, 'w'), indent=1)
print('PICK', json.dumps(res['pick']))
