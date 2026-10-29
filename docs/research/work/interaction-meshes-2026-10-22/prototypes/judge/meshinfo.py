import sys, trimesh, numpy as np
for p in sys.argv[1:]:
    m = trimesh.load(p, force='mesh')
    print(p[-70:], 'wt', m.is_watertight, 'vol', round(m.volume*1e6,1), 'area', round(m.area*1e4,1), 'ext', np.round(m.extents*100,1), 'bodies', len(m.split(only_watertight=False)), flush=True)
