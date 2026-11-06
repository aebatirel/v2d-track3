import sys, numpy as np, pyarrow.parquet as pq, trimesh, glob
t = pq.read_table(sys.argv[1])
for c in ('raw_motion_file', 'object_name', 'object_mesh_paths', 'object_urdf_paths', 'object_mesh_radius', 'object_articulation', 'sequence_id'):
    print(c, repr(t.column(c)[0].as_py())[:400])
for n in ('blue_cup', 'beige_cup'):
    m = trimesh.load(f'/home/user/v2d-track3/meshes/library_v3/{n}.glb', force='mesh', process=False)
    print(n, 'lib v3 bounds', m.bounds.round(4).tolist(), 'faces', len(m.faces), 'wt', m.is_watertight)
    V = np.concatenate([trimesh.load(f, force='mesh', process=False).vertices for f in sorted(glob.glob(f'/home/user/v2d-track3/meshes/carve/ev10/{n}/piece_*.obj'))])
    print(n, 'carve bounds', V.min(0).round(4).tolist(), V.max(0).round(4).tolist())
