"""Write DIR/episode_XXXXXX/<all 13p meshes> with one object's mesh transformed by a given 4x4 Delta (vertices v ->
Delta v). Usage: python -I apply_delta.py BASE_MESH_DIR OUT_DIR EP OBJ DELTA_JSON_LIST"""
import sys, os, glob, shutil, json, numpy as np, trimesh
base, out, ep, obj, D = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], np.array(json.loads(sys.argv[5]))
ed = f'{out}/episode_{ep:06d}'; os.makedirs(ed, exist_ok=True)
for f in glob.glob(f'{base}/*.glb'):
    if not os.path.exists(f'{out}/{os.path.basename(f)}'): shutil.copy(f, out)
    shutil.copy(f, ed)
m = trimesh.load(f'{base}/{obj}.glb', force='mesh'); m.apply_transform(D); m.export(f'{ed}/{obj}.glb')
