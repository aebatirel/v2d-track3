"""Diagnostic manifest.json for an ev10 sim dir (layout as tools/intrusion_tests/make_manifest.py: objects.<obj>.files
{file: sha256} + 8 OBB fiducials 1 mm inward). Written by ev10_intrusion/scripts, NOT by gmg; split = eval."""
import glob, hashlib, importlib.util, json, os, sys
import numpy as np, trimesh
spec = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py'); I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
sim, ep, src = sys.argv[1], int(sys.argv[2]), sys.argv[3]
man = dict(episode=ep, split='eval', round=0, source_of_pieces=src,
           note='DIAGNOSTIC manifest written by ev10_intrusion/scripts/make_manifest_ev10.py, not by gmg', objects={})
for d in sorted(glob.glob(f'{sim}/*/')):
    n = os.path.basename(d.rstrip('/'))
    if n.startswith('_'):
        continue
    fs = sorted(glob.glob(f'{sim}/{n}/piece_*.obj'))
    V = np.concatenate([np.asarray(trimesh.load(f, force='mesh', process=False).vertices) for f in fs])
    man['objects'][n] = dict(files={os.path.basename(f): hashlib.sha256(open(f, 'rb').read()).hexdigest() for f in fs},
                             fiducials=I.obb_fiducials(V).tolist())
json.dump(man, open(f'{sim}/manifest.json', 'w'), indent=1); print('wrote', f'{sim}/manifest.json', {k: len(v['files']) for k, v in man['objects'].items()})
