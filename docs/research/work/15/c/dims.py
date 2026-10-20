# Stage C: object extents, thin dims, hull/volume ratio, handle lever arm (public scans; analysis only)
import glob, os, numpy as np, trimesh
R='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh'
for d in sorted(os.listdir(R)):
    fs=sorted(glob.glob(f'{R}/{d}/*.glb'))
    for f in fs:
        m=trimesh.load(f,force='mesh')
        v=m.vertices; ext=v.max(0)-v.min(0)
        c=m.center_mass if m.is_volume else m.centroid
        r=np.linalg.norm(v-c,axis=1).max()
        try: hv=m.convex_hull.volume
        except Exception: hv=float('nan')
        vol=abs(m.volume) if m.is_volume else float('nan')
        # thin-ness: 5th pct of OBB-thickness along min axis is just ext.min
        print(f'{os.path.basename(f):32s} ext_mm={np.round(ext*1000).astype(int)} min={ext.min()*1000:5.0f} '
              f'maxR_from_com={r*1000:4.0f} vol_cm3={vol*1e6:7.1f} hull_cm3={hv*1e6:7.1f} '
              f'fill={vol/hv if hv==hv and vol==vol else float("nan"):.2f} watertight={m.is_watertight} faces={len(m.faces)}')
