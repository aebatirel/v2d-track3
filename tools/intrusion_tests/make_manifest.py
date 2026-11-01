"""Write a test manifest.json (assumed gmg layout: objects.<obj>.files {file: sha256} + 8 OBB fiducials, 1 mm inward)."""
import glob, hashlib, importlib.util, json, os, shutil, sys
import numpy as np, trimesh
spec = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py'); I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
sim, ep, glbdir = sys.argv[1], int(sys.argv[2]), sys.argv[3]
man = dict(episode=ep, split='public', round=0, note='TEST manifest written by intrusion_test/make_manifest.py, not by gmg', objects={})
for d in sorted(glob.glob(f'{sim}/*/')):
    n = os.path.basename(d.rstrip('/'))
    if n.startswith('_'):
        continue
    shutil.copy(f'{glbdir}/{n}/{n}.glb', f'{sim}/{n}/{n}.glb')
    fs = sorted(glob.glob(f'{sim}/{n}/piece_*.obj')) + [f'{sim}/{n}/{n}.glb']
    V = np.concatenate([np.asarray(trimesh.load(f, force='mesh', process=False).vertices) for f in fs if f.endswith('.obj')])
    man['objects'][n] = dict(files={os.path.basename(f): hashlib.sha256(open(f, 'rb').read()).hexdigest() for f in fs},
                             fiducials=I.obb_fiducials(V).tolist())
json.dump(man, open(f'{sim}/manifest.json', 'w'), indent=1); print('wrote', f'{sim}/manifest.json')
