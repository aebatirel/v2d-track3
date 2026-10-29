import sys, json, glob, os
import numpy as np, trimesh
out = {}
for f in sorted(glob.glob(os.path.join(sys.argv[1], '*.glb'))):
    name = os.path.basename(f)[:-4]
    s = trimesh.load(f, force='mesh')
    v = np.asarray(s.vertices)
    c = v - v.mean(0)
    w, V = np.linalg.eigh(np.cov(c.T))
    V = V[:, ::-1]
    p = c @ V
    ext = p.max(0) - p.min(0)
    aabb = v.max(0) - v.min(0)
    out[name] = dict(aabb_cm=[round(x*100, 2) for x in aabb], pca_extent_cm=[round(x*100, 2) for x in ext],
                     watertight=bool(s.is_watertight), faces=len(s.faces))
    # thickness distribution along smallest PCA axis on a grid (for plates/boards)
    if ext[2] < 0.6*ext[1]:
        xs = p[:, 0]; ys = p[:, 1]; zs = p[:, 2]
        bins = 12
        H = {}
        ix = np.clip(((xs - xs.min())/(np.ptp(xs)+1e-9)*bins).astype(int), 0, bins-1)
        iy = np.clip(((ys - ys.min())/(np.ptp(ys)+1e-9)*bins).astype(int), 0, bins-1)
        th = []
        for a in range(bins):
            for b in range(bins):
                m = (ix == a) & (iy == b)
                if m.sum() > 3:
                    th.append(np.ptp(zs[m]))
        th = np.array(th)
        out[name]['local_thickness_cm_p10_p50_p90'] = [round(float(np.percentile(th, q))*100, 2) for q in (10, 50, 90)]
print(json.dumps(out, indent=1))
