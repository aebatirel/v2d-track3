"""C2/P AUC guard: the base-run reuse check (C0b check_base_c0b.py's rule, restricted to twins 21 and 22) and the
single-swap mesh dir.
Reuse C0's base runs (SCR/cdo_c0/runs/base/ep21|22.json) only if all still equal C0's values:
  - every SCR/cdo_c0/base file's sha256 (C0 inputs/mesh_dirs_sha256.json 'base');
  - the ep21 / ep22 track npz sha256, source and converted (C0 inputs/tracks.json);
  - pipeline/score_registered.py sha256[:16] 6a4cd60a0d26e3f8; kit v2dlb/track3_pose.py b4b99f698eb4893a;
  - SCR/cdo_c0/runs/inputs_sha256.txt (every listed staged file re-hashed).
If all hold, the two base JSONs (+ logs) are copied to SCR/cdo_c2/P/auc/runs/base; else nothing is copied and
run_auc_guard_p.sh runs the base unchanged. Then builds SCR/cdo_c2/P/auc/single/water_pitcher (C0's base dir with
water_pitcher.glb replaced by the pick) with its sha256 list.
Usage: python -I check_base_p.py PICK.glb OUT.json
"""
import hashlib, json, os, shutil, sys

S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
R = '/home/user/v2d-track3'
C0 = f'{R}/docs/research/mesh-2026-10-26/cdo-sprint/C0'
D = f'{S}/cdo_c2/P/auc'
TW = [21, 22]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


pick, out = sys.argv[1], sys.argv[2]
res = dict(checks={})
md = json.load(open(f'{C0}/inputs/mesh_dirs_sha256.json'))['base']
cur = {f[:-4]: sha(f'{S}/cdo_c0/base/{f}') for f in sorted(os.listdir(f'{S}/cdo_c0/base')) if f.endswith('.glb')}
res['checks']['base_meshes'] = dict(ok=cur == md, n=len(cur), diff=[k for k in set(cur) | set(md) if cur.get(k) != md.get(k)])
tr = json.load(open(f'{C0}/inputs/tracks.json'))
bad = [e for e in map(str, TW) if sha(tr[e]['source']) != tr[e]['source_sha256'] or sha(tr[e]['out']) != tr[e]['out_sha256']]
res['checks']['tracks'] = dict(ok=not bad, bad=bad)
s16 = sha(f'{R}/pipeline/score_registered.py')[:16]
res['checks']['score_registered'] = dict(ok=s16 == '6a4cd60a0d26e3f8', sha16=s16)
k16 = sha(f'{S}/kit/v2d_submission_kit/v2dlb/track3_pose.py')[:16]
res['checks']['kit_track3_pose'] = dict(ok=k16 == 'b4b99f698eb4893a', sha16=k16)
bad = []
lines = [l.split(None, 1) for l in open(f'{S}/cdo_c0/runs/inputs_sha256.txt') if l.strip()]
for h, f in lines:
    f = f.strip()
    if not os.path.exists(f) or sha(f) != h:
        bad.append(f)
res['checks']['staged_inputs'] = dict(ok=not bad and len(lines) > 0, n=len(lines), bad=bad)
res['checks']['base_jsons'] = dict(ok=all(os.path.exists(f'{S}/cdo_c0/runs/base/ep{e}.json') for e in TW))
res['reuse_base'] = all(v['ok'] for v in res['checks'].values())
os.makedirs(f'{D}/runs/base', exist_ok=True)
if res['reuse_base']:
    for e in TW:
        for x in ('json', 'log'):
            shutil.copyfile(f'{S}/cdo_c0/runs/base/ep{e}.{x}', f'{D}/runs/base/ep{e}.{x}')
    res['base_copied'] = {e: sha(f'{D}/runs/base/ep{e}.json') for e in TW}
d = f'{D}/single/water_pitcher'
if os.path.exists(d):
    shutil.rmtree(d)
shutil.copytree(f'{S}/cdo_c0/base', d)
shutil.copyfile(pick, f'{d}/water_pitcher.glb')
res['mesh_dirs_sha256'] = {'single/water_pitcher': {f[:-4]: sha(f'{d}/{f}') for f in sorted(os.listdir(d))}, 'base': cur}
res['pick'] = dict(path=pick, sha256=sha(pick))
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(dict(reuse_base=res['reuse_base'], checks={k: v['ok'] for k, v in res['checks'].items()})))
