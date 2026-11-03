"""Rack round R: hashes of every already-measured (scored [D] or audited) plastic_dish_rack file, so that no R candidate
re-uses one (PREREG s14: "new files, never measured"). Sources:
  review/library_index.json rack items with a CD-O record (sha = sha1[:16] of the file, as mesh_metric.sha);
  results/prim/rack/scores.jsonl (sha1[:16]); C2/R-rack/results/score.jsonl (sha1[:16]);
  every rack entry of C4-audit/candidates*.json (md5; audited or queued for the audit), with sha1[:16] when the file exists;
  the 13h / 13i rack files in C4-audit/meshes_13h, meshes_13i, meshes_outer.
Reads hashes and our meshes only (no scan). Usage: measured_rack.py OUT.json
"""
import glob, hashlib, json, os, sys

REPO = '/home/user/v2d-track3'
M = f'{REPO}/docs/research/mesh-2026-10-26'
sha1, md5, src = set(), set(), {}


def fh(p):
    b = open(p, 'rb').read()
    return hashlib.sha1(b).hexdigest()[:16], hashlib.md5(b).hexdigest()


lib = json.load(open(f'{M}/review/library_index.json'))['plastic_dish_rack']['items']
for it in lib:
    if it.get('cdo') is not None:
        sha1.add(it['sha']); src[it['sha']] = 'library_index:' + it['label']
for f in (f'{M}/results/prim/rack/scores.jsonl', f'{M}/cdo-sprint/C2/R-rack/results/score.jsonl'):
    for l in open(f):
        r = json.loads(l)
        sha1.add(r['sha']); src[r['sha']] = os.path.basename(f) + ':' + r['label']
for f in sorted(glob.glob(f'{M}/cdo-sprint/C4-audit/candidates*.json')):
    for c in json.load(open(f)):
        if c.get('object') != 'plastic_dish_rack':
            continue
        if c.get('md5'):
            md5.add(c['md5']); src[c['md5']] = os.path.basename(f) + ':' + c['label']
        p = c['path'] if os.path.isabs(c['path']) else os.path.join(REPO, c['path'])
        if os.path.exists(p):
            s, m = fh(p); sha1.add(s); md5.add(m); src[s] = src[m] = os.path.basename(f) + ':' + c['label']
for p in glob.glob(f'{M}/cdo-sprint/C4-audit/meshes_1*/plastic_dish_rack*') + glob.glob(f'{M}/cdo-sprint/C4-audit/meshes_outer/plastic_dish_rack*'):
    if p.endswith('.glb'):
        s, m = fh(p); sha1.add(s); md5.add(m); src[s] = src[m] = os.path.relpath(p, M)
json.dump(dict(sha1_16=sorted(sha1), md5=sorted(md5), src=src), open(sys.argv[1], 'w'), indent=1)
print(f'{len(sha1)} sha1[:16], {len(md5)} md5 of already-measured rack files -> {sys.argv[1]}')
