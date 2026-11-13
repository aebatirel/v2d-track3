#!/usr/bin/env python
"""T3: collect the build (GT-free diagnostics of every fitted mesh), copy the fitted meshes into the repo folder,
write build_manifest.json and score_manifest.tsv. Reads only our own build outputs.
Usage: python -I manifest.py BUILD_DIR REPO_T3_DIR
"""
import hashlib, json, os, shutil, sys

B, T = sys.argv[1], sys.argv[2]
os.makedirs(f'{T}/meshes', exist_ok=True)
rows, man = [], []
for l in open(f'{B}/picks.jsonl') if os.path.exists(f'{B}/picks.jsonl') else []:
    pass
picks = {}
for f in sorted(os.listdir(B)):
    if f.startswith('picks') and f.endswith('.jsonl'):
        for l in open(f'{B}/{f}'):
            p = json.loads(l); picks[p['object']] = p
for o, p in picks.items():
    d = f'{B}/{o}/diag.json'
    if not os.path.exists(d) or not os.path.exists(f'{B}/{o}/fit.glb'):
        rows.append(dict(object=o, error='no fit.glb')); continue
    g = json.load(open(d))
    st = {s['tag']: s for s in g['stages']}
    fin = g['final']
    dst = f'{T}/meshes/{o}_t3fit.glb'
    shutil.copyfile(f'{B}/{o}/fit.glb', dst)
    sha = hashlib.sha256(open(dst, 'rb').read()).hexdigest()
    assert sha == fin['sha256'], o
    i0, s0 = st['input'], st['stage_0']
    rows.append(dict(object=o, pick=p['pick'], placed=p['placed'], obs=p['obs'], mesh=os.path.relpath(dst, T),
                     sha256=sha, faces=fin['faces'], verts=fin['verts'], watertight=fin['watertight'],
                     bodies=fin['bodies'], budget_faces=fin['budget_faces'],
                     held_tmean90_in=i0['held_o2m']['tmean90_mm'], held_tmean90_fit=s0['held_o2m']['tmean90_mm'],
                     held_tmean90_packed=fin['held_o2m']['tmean90_mm'],
                     train_tmean90_in=i0['train_o2m']['tmean90_mm'], train_tmean90_fit=s0['train_o2m']['tmean90_mm'],
                     held_med_in=i0['held_o2m']['med_mm'], held_med_fit=s0['held_o2m']['med_mm'],
                     m2o_in=i0['m2o']['tmean90_mm'], m2o_fit=s0['m2o']['tmean90_mm'],
                     free_in=i0['free_frac'], free_fit=s0['free_frac'], area_ratio=s0['area_ratio'],
                     rms_ratio=s0['rms_ratio'], flip_frac=s0['flip_frac'], selfint_in=i0['selfint_faces'],
                     selfint_fit=s0['selfint_faces'], disp_med_mm=s0['disp_med_mm'], disp_p95_mm=s0['disp_p95_mm'],
                     obs_train=g['obs_train'], obs_held=g['obs_held'], secs=g.get('secs')))
    man.append(f't3fit/{o}\t{o}\t{os.path.abspath(dst)}')
json.dump(rows, open(f'{T}/build_manifest.json', 'w'), indent=1)
open(f'{T}/score_manifest.tsv', 'w').write('\n'.join(man) + '\n')
for r in rows:
    if 'error' in r:
        print(r['object'], r['error']); continue
    print(f"{r['object']:18s} {r['sha256'][:16]} f{r['faces']} wt {r['watertight']} b{r['bodies']} held {r['held_tmean90_in']:.2f}->"
          f"{r['held_tmean90_fit']:.2f} (packed {r['held_tmean90_packed']:.2f}) train {r['train_tmean90_in']:.2f}->{r['train_tmean90_fit']:.2f} "
          f"free {r['free_in']:.3f}->{r['free_fit']:.3f} area {r['area_ratio']:.3f} rms {r['rms_ratio']:.4f} si {r['selfint_in']}->{r['selfint_fit']} disp {r['disp_med_mm']:.1f}")
