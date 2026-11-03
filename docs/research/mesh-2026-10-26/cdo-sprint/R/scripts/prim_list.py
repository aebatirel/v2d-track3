"""Rack round R: the R-prim list for stage 2 (PREREG s14). Collects the prim_rack.py outputs of the R runs (base = its
defaults; E / K / Q = one existing variant flag each), drops every file whose sha1[:16] or md5 equals an already-measured
rack file (scripts/measured_rack.py), keeps byte-identical outputs once (first in run / file order), and records per fit:
md5, sha1[:16], faces, watertight, bodies, the fit record (prim_rack.py's own candidate line: markers, pegs, fidelity) and
the t3fit episode (per-episode fits: their own episode; joint fits: the joint's reference episode = the joint episode
with the most voxel-deduplicated observed points, the rule in prim_rack.py joint()). GT-free (our meshes and points only).
Usage: prim_list.py PRIM_ROOT MEASURED.json OUT.json      (PRIM_ROOT/<run>/plastic_dish_rack/*.glb, PRIM_ROOT/<run>.log)
"""
import hashlib, json, os, sys
import numpy as np, trimesh

root, meas_p, out = sys.argv[1:4]
RUNS = ('base', 'E', 'K', 'Q')
FLAGS = dict(base='', E='--end_draft', K='--peg_kappa_free', Q='--cup_quad')
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
meas = json.load(open(meas_p))
VOX = 0.0015


def npts(e):                                     # prim_rack.load(): 1.5 mm voxel dedupe, then count
    P = np.load(f'{S}/obs_all/ep{e}_plastic_dish_rack.npz')['pts'].astype(np.float64)
    return len(np.unique(np.floor(P / VOX).astype(np.int64), axis=0))


rows, seen, dropped = [], {}, []
for run in RUNS:
    d = os.path.join(root, run, 'plastic_dish_rack')
    recs = {}
    for l in open(os.path.join(root, run + '.log')):
        if l.startswith('{"object"'):
            r = json.loads(l); recs[(r['episode'], r['variant'])] = r
        elif l.startswith('{"joint_episodes"'):
            jep = json.loads(l)['joint_episodes']
    ref = max(jep, key=npts)
    for f in sorted(os.listdir(d)):
        if not f.endswith('.glb'):
            continue
        p = os.path.join(d, f); b = open(p, 'rb').read()
        s1, m5 = hashlib.sha1(b).hexdigest()[:16], hashlib.md5(b).hexdigest()
        stem = f[:-4]
        ep, var = ('all', stem.split('_', 1)[1]) if stem.startswith('joint_') else tuple(stem[2:].split('_', 1))
        lab = f'{run}_{stem}'
        if s1 in meas['sha1_16'] or m5 in meas['md5']:
            dropped.append(dict(label=lab, why='equals an already-measured file: ' + meas['src'].get(s1, meas['src'].get(m5, '?'))))
            continue
        if m5 in seen:
            dropped.append(dict(label=lab, why='byte-identical to ' + seen[m5])); continue
        seen[m5] = lab
        m = trimesh.load(p, force='mesh')
        rec = recs.get((ep, var), {})
        rows.append(dict(label=lab, run=run, flag=FLAGS[run], episode=ep, variant=var, path=p, md5=m5, sha1_16=s1,
                         faces=int(len(m.faces)), watertight=bool(m.is_watertight), bodies=len(m.split(only_watertight=False)),
                         obs_episode=ref if ep == 'all' else ep, joint_episodes=jep if ep == 'all' else None,
                         fit_record={k: v for k, v in rec.items() if k not in ('object', 'path')}))
json.dump(rows, open(out, 'w'), indent=1)
json.dump(dropped, open(out.replace('.json', '_dropped.json'), 'w'), indent=1)
print(f'{len(rows)} R-prim fits, {len(dropped)} dropped -> {out}')
for r in dropped:
    print('dropped', r)
