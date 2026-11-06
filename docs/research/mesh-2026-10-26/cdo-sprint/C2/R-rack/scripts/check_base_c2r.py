"""C2/R AUC guard (PREREG C2/R-rack section 7): a copy of C0b's check_base_c0b.py (base-run reuse check, unchanged
conditions) that builds only SCR/cdo_c2r/single/plastic_dish_rack and copies the base runs to SCR/cdo_c2r/runs/base.
Original docstring follows (its C0b paths now read cdo_c2r; no joint dir is built).
C0b AUC guard: the base-run reuse check of PREREG C0b section 7, and the C0b mesh dirs.
Reuse C0's base runs (SCR/cdo_c0/runs/base/ep<e>.json) only if all still equal C0's values:
  - every SCR/cdo_c0/base file's sha256 (C0 inputs/mesh_dirs_sha256.json 'base');
  - the track npz sha256, source and converted (C0 inputs/tracks.json);
  - pipeline/score_registered.py sha256[:16] 6a4cd60a0d26e3f8; kit v2dlb/track3_pose.py b4b99f698eb4893a;
  - SCR/cdo_c0/runs/inputs_sha256.txt (every listed staged file re-hashed).
If all hold, the 15 base JSONs are copied to SCR/cdo_c2r/runs/base (else nothing is copied and all base runs are re-run
unchanged by run_auc_guard_c0b.sh). Then builds SCR/cdo_c2r/single/<o> (C0's base dir with o's file replaced by its
C0b pick) and SCR/cdo_c2r/c0b (all picks swapped), with mesh_dirs_sha256.json.
Usage: python -I check_base_c0b.py SELECTION.json OUT.json    (SELECTION: C0b/results/picks.json: {obj: path})
"""
import hashlib, json, os, shutil, sys

S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
R = '/home/user/v2d-track3'
C0 = f'{R}/docs/research/mesh-2026-10-26/cdo-sprint/C0'
TWINS = [0, 2, 11, 12, 13, 21, 22, 26, 27, 31, 41, 42, 43, 44, 45]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


picks, out = json.load(open(sys.argv[1])), sys.argv[2]
res = dict(checks={})
md = json.load(open(f'{C0}/inputs/mesh_dirs_sha256.json'))['base']
cur = {f[:-4]: sha(f'{S}/cdo_c0/base/{f}') for f in sorted(os.listdir(f'{S}/cdo_c0/base')) if f.endswith('.glb')}
res['checks']['base_meshes'] = dict(ok=cur == md, n=len(cur), diff=[k for k in set(cur) | set(md) if cur.get(k) != md.get(k)])
tr = json.load(open(f'{C0}/inputs/tracks.json'))
bad = []
for e, v in tr.items():
    if sha(v['source']) != v['source_sha256'] or sha(v['out']) != v['out_sha256']:
        bad.append(e)
res['checks']['tracks'] = dict(ok=not bad, n=len(tr), bad=bad)
res['checks']['score_registered'] = dict(ok=sha(f'{R}/pipeline/score_registered.py')[:16] == '6a4cd60a0d26e3f8',
                                         sha16=sha(f'{R}/pipeline/score_registered.py')[:16])
res['checks']['kit_track3_pose'] = dict(ok=sha(f'{S}/kit/v2d_submission_kit/v2dlb/track3_pose.py')[:16] == 'b4b99f698eb4893a',
                                        sha16=sha(f'{S}/kit/v2d_submission_kit/v2dlb/track3_pose.py')[:16])
bad = []
lines = [l.split(None, 1) for l in open(f'{S}/cdo_c0/runs/inputs_sha256.txt') if l.strip()]
for h, f in lines:
    f = f.strip()
    if not os.path.exists(f) or sha(f) != h:
        bad.append(f)
res['checks']['staged_inputs'] = dict(ok=not bad and len(lines) > 0, n=len(lines), bad=bad)
res['checks']['base_jsons'] = dict(ok=all(os.path.exists(f'{S}/cdo_c0/runs/base/ep{e}.json') for e in TWINS))
res['reuse_base'] = all(v['ok'] for v in res['checks'].values())
os.makedirs(f'{S}/cdo_c2r/runs/base', exist_ok=True)
if res['reuse_base']:
    for e in TWINS:
        for x in ('json', 'log'):
            shutil.copyfile(f'{S}/cdo_c0/runs/base/ep{e}.{x}', f'{S}/cdo_c2r/runs/base/ep{e}.{x}')
    res['base_copied'] = {e: sha(f'{S}/cdo_c2r/runs/base/ep{e}.json') for e in TWINS}
# mesh dirs
dirs = {}
for o, p in picks.items():
    d = f'{S}/cdo_c2r/single/{o}'
    if os.path.exists(d):
        shutil.rmtree(d)
    shutil.copytree(f'{S}/cdo_c0/base', d)
    shutil.copyfile(p, f'{d}/{o}.glb')
    dirs[f'single/{o}'] = {f[:-4]: sha(f'{d}/{f}') for f in sorted(os.listdir(d))}
dirs['base'] = cur
res['mesh_dirs_sha256'] = dirs
res['picks'] = {o: dict(path=p, sha256=sha(p)) for o, p in picks.items()}
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(dict(reuse_base=res['reuse_base'], checks={k: v['ok'] for k, v in res['checks'].items()})))
