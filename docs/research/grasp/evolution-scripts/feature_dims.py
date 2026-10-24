# usage: feature_dims.py LIBDIR -> lid knob size, pot handle cross-section, pitcher handle (rough, PCA frames, our meshes)
import sys, os, json, numpy as np, trimesh
L = sys.argv[1]
def pca(m):
    v = np.asarray(m.vertices); c = v.mean(0); w, V = np.linalg.eigh(np.cov((v - c).T)); V = V[:, ::-1]
    return (v - c) @ V
out = {}
# lid: knob = top band along the thinnest axis (sign chosen so the knob is the smaller-area end)
m = trimesh.load(os.path.join(L, 'white_pot_lid.glb'), force='mesh'); p = pca(m)
for s in (1, -1):
    z = s * p[:, 2]; top = z > z.max() - 0.015
    ext = np.ptp(p[top, :2], axis=0) * 100
    out['lid_top15mm_extent_cm_sign%+d' % s] = [round(float(x), 2) for x in ext]
out['lid_extent_cm'] = [round(float(x), 2) for x in np.ptp(p, axis=0) * 100]
# pot: handles along the long axis beyond the body radius; cross-section of the handle at its mid-length
m = trimesh.load(os.path.join(L, 'white_pot.glb'), force='mesh'); p = pca(m)
r_body = np.ptp(p[:, 1]) / 2
for s in (1, -1):
    x = s * p[:, 0]; sel = x > r_body + 0.01
    if sel.sum() < 10: continue
    xm = (x[sel].min() + x[sel].max()) / 2
    band = sel & (np.abs(x - xm) < 0.01)
    out['pot_handle%+d' % s] = dict(protrusion_cm=round(float((x[sel].max() - r_body) * 100), 2),
        cross_section_cm=[round(float(v), 2) for v in np.ptp(p[band][:, 1:], axis=0) * 100])
out['pot_extent_cm'] = [round(float(x), 2) for x in np.ptp(p, axis=0) * 100]
print(json.dumps(out, indent=1))
