"""Lathe body (lathe_obs.py --appendages 0, with its .lathe.json) + the faces of another mesh lying outside it by
more than MARGIN (handle, markers): inside/outside by point-in-polygon of (r, h) against the revolved profile."""
import sys, json, numpy as np, trimesh
lat = trimesh.load(sys.argv[1], force='mesh'); J = json.load(open(sys.argv[1].rsplit('.', 1)[0] + '.lathe.json'))
src = trimesh.load(sys.argv[2], force='mesh'); margin = float(sys.argv[4])
c, d = np.array(J['centre']), np.array(J['axis']); prof = np.array(J['profile'])
X = src.triangles_center - c; h = X @ d; r = np.linalg.norm(X - h[:, None] * d, axis=1)
def inside(rr, hh, poly):
    x, y = poly[:, 0], poly[:, 1]; x2, y2 = np.roll(x, -1), np.roll(y, -1); res = np.zeros(len(rr), bool)
    for xa, ya, xb, yb in zip(x, y, x2, y2):
        cross = ((ya > hh) != (yb > hh)) & (rr < (xb - xa) * (hh - ya) / (yb - ya + 1e-15) + xa)
        res ^= cross
    return res
# grow the profile outward by MARGIN: test the point moved MARGIN towards the axis / the body
near = inside(np.maximum(r - margin, 0), h, prof) | inside(r, h - margin, prof) | inside(r, h + margin, prof)
keep = ~near
app = src.submesh([np.nonzero(keep)[0]], append=True)
trimesh.util.concatenate([lat, app]).export(sys.argv[3])
print(sys.argv[3], 'kept', int(keep.sum()), 'of', len(keep), 'faces of', sys.argv[2].split('/')[-2])
