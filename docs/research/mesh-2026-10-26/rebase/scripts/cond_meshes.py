"""Report only: lowest point of other pot meshes (C0 = shipped visual, E0b = pack-10 candidate) at the same T-rest frames."""
import sys, json, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/rebase/scripts')
import rebase as rb
R0 = sys.argv[1]; out = {}
meshes = {k: rb.load_mesh(p) for k, p in dict(v3='/home/user/v2d-track3/meshes/library_v3/white_pot.glb', c0='/home/user/v2d-track3/meshes/library_c0/white_pot.glb', e0b='/home/user/v2d-track3/meshes/library_e0b/white_pot.glb').items()}
for s in sys.argv[2:]:
    cfg = json.load(open(f'{R0}/cfg/{s}.json')); fr = json.load(open(f'{R0}/out/{s}/frames.json'))
    R = rb.load_ref(cfg['ref']); io = R['names'].index('white_pot'); top = fr['support']['top_z']
    F = np.flatnonzero(rb.run_mask(fr['rest_runs'], R['nf']))
    if not len(F): continue
    out[s] = {k: rb.stats([(top - rb.tf(R['T'][f, io], m.vertices)[:, 2].min()) * 1e3 for f in F]) for k, m in meshes.items()}
    print(s, {k: (v['median'], v['max']) for k, v in out[s].items()})
json.dump(out, open(f'{R0}/out/cond_meshes.json', 'w'), indent=1)
