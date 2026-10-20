# Debris-hull origin: for every part mesh whose CoACD hulls (exact call, stored in <partsdir>/hulls/) contain a hull of
# volume < VMAX m^3, report the hull, the part's connected components (count, smallest volumes) and whether the debris
# hull lies on a part cap plane (axis-aligned cut faces) or inside/near a tiny input component.
# usage: c2_debris.py VMAX partsdir [partsdir ...]
import sys, glob, os, numpy as np, trimesh
from scipy.spatial import ConvexHull
VMAX = float(sys.argv[1])
def hvol(v):
    try: return ConvexHull(v).volume
    except Exception: return 0.0
for pd_ in sys.argv[2:]:
    for p in sorted(glob.glob(pd_ + '/*_p*.npz')):
        hp = pd_ + '/hulls/' + os.path.basename(p)
        if not os.path.exists(hp): continue
        dh = np.load(hp); n = int(dh['n'])
        vols = np.array([hvol(dh[f'v{i}']) for i in range(n)])
        bad = np.where(vols < VMAX)[0]
        if len(bad) == 0: continue
        d = np.load(p); m = trimesh.Trimesh(d['v'], d['f'], process=False)
        comps = m.split(only_watertight=False)
        cv = sorted([abs(c.volume) for c in comps])
        lo, hi = m.vertices.min(0), m.vertices.max(0)
        print(f'PART {p.split("work/19/")[-1]} hulls {n} faces {len(m.faces)} comps {len(comps)} smallest comp vol {cv[:3]}')
        for i in bad:
            hv = dh[f'v{i}']; c = hv.mean(0); ext = hv.max(0) - hv.min(0)
            # distance of debris centre to the part bbox faces (cap planes are at the bbox where the part was cut)
            dcap = np.min(np.abs(np.concatenate([c - lo, hi - c])))
            # nearest input vertex and the component containing it
            k = np.argmin(np.linalg.norm(m.vertices - c, axis=1)); dv = np.linalg.norm(m.vertices[k] - c)
            ci = [j for j, cc in enumerate(comps) if np.any(np.all(np.isclose(cc.vertices, m.vertices[k]), axis=1))]
            cvol = abs(comps[ci[0]].volume) if ci else float('nan')
            print(f'   hull {i} vol {vols[i]:.2e} m3 ext um {np.round(ext*1e6,1).tolist()} nverts {len(hv)} '
                  f'dist to bbox face {dcap*1e3:.3f} mm, nearest input vertex {dv*1e6:.1f} um, its comp vol {cvol:.2e}')
