# Stage A check: mimic newton 1.2.0 load_meshes_from_file branch decisions (utils/mesh.py:690-880) with the
# pinned trimesh 4.12.2 on each public URDF collision mesh; report how many Newton mesh shapes would result,
# their vertex/face counts and watertightness (what CoACD's preprocess_mode="auto" manifold check sees).
import re, os, sys, numpy as np, trimesh
R = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
print('trimesh', trimesh.__version__)
for u in (sys.argv[1:] or sorted(os.listdir(f'{R}/urdf'))):
    x = open(f'{R}/urdf/{u}').read()
    cols = re.findall(r'<collision>.*?</collision>', x, re.S)
    for c in cols:
        fn = re.search(r'filename="([^"]+)"', c).group(1)
        f = os.path.normpath(os.path.join(R, 'urdf', fn))
        raw = trimesh.load(f, process=False, force='mesh')
        tri = trimesh.load(f, force='mesh')
        metas = list(tri.geometry.values()) if hasattr(tri, 'geometry') else [tri]
        for m in metas:
            vis = getattr(m, 'visual', None)
            fm = getattr(vis, 'face_materials', None)
            mats = getattr(vis, 'materials', None)
            fc = getattr(vis, 'face_colors', None) if vis is not None else None
            vc = getattr(vis, 'vertex_colors', None) if vis is not None else None
            branch = 'single'
            n = 1
            if fm is not None and mats is not None:
                branch = 'face_materials'; n = len(np.unique(np.asarray(fm)))
            elif fc is not None and np.asarray(fc).shape[0] == len(m.faces):
                rgb = np.round((np.asarray(fc, dtype=np.float32) / (255.0 if np.max(fc) > 1 else 1.0))[:, :3], 4)
                branch = 'face_colors'; n = len(np.unique(rgb, axis=0))
            elif vc is not None:
                branch = 'vertex_colors'; n = -1
            print(f'{u:32s} {os.path.basename(f):28s} vis={type(vis).__name__:15s} branch={branch:14s} '
                  f'shapes={n} V={len(m.vertices)} F={len(m.faces)} rawV={len(raw.vertices)} '
                  f'watertight={m.is_watertight} winding={m.is_winding_consistent} '
                 , flush=True)
