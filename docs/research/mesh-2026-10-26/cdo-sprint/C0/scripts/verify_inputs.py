"""C0 stage 2: re-check the frozen mesh-dir and track hashes (inputs/*.json) before stage 0. No GT read.
Usage: python -I verify_inputs.py REPO SCRATCH"""
import hashlib, json, os, sys
R, S = sys.argv[1], sys.argv[2]
D = f'{S}/cdo_c0'
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
M = json.load(open(f'{R}/docs/research/mesh-2026-10-26/cdo-sprint/C0/inputs/mesh_dirs_sha256.json'))
bad = 0; n = 0
for cfg, objs in M.items():
    if not isinstance(objs, dict): continue
    for o, s in objs.items():
        if not isinstance(s, str) or len(s) != 64: continue
        p = f'{D}/{cfg}/{o}.glb'
        n += 1
        if not os.path.exists(p) or h(p) != s: bad += 1; print('MISMATCH', cfg, o)
print('mesh files checked', n, 'mismatches', bad, 'top keys', list(M.keys()))
TR = json.load(open(f'{R}/docs/research/mesh-2026-10-26/cdo-sprint/C0/inputs/tracks.json'))
tb = 0
for e, v in TR.items():
    if h(v['out']) != v['out_sha256'] or h(v['source']) != v['source_sha256']: tb += 1; print('TRACK MISMATCH', e)
print('tracks checked', len(TR), 'mismatches', tb)
