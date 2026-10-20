# Stage C cavity metrics (object-only, no GT): how much free space inside the pot basin, the blue-cup interior and the
# rack's utensil tower each collider set removes, vs the exact W2 solid (scan + 0.3 mm; field grids b/FG, 1 mm).
#  (1) floor rise: per column (2 mm cells) along the cavity axis, first solid from the mouth side, hulls vs W2.
#  (2) free opening: slices across the axis (1 mm pixels); free component containing the cavity centre;
#      inscribed-circle diameter (2 x max distance transform) and free area, hulls vs W2.
#  (3) air filled: air (W2 field > 0.5 mm) inside the object's own region that the hull union covers, and how far
#      into the air it reaches (W2 field value at covered air points), for the whole object.
# usage: c_cavity.py <obj> LABEL=hulldir ...
import sys, numpy as np
from scipy.spatial import ConvexHull
from scipy import ndimage
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls
FG = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/FG'
# cavity spec (object scan frame, metres): axis index, mouth sign (+1: mouth at high coordinate), region box for the
# columns/slices (None = whole object), slice positions measured from the cavity floor of W2 (mm), centre (2 of 3 coords)
SPEC = {
 'white_pot': dict(ax=0, sgn=+1, box=None, c=(0.0013, -0.0073), r=0.085, slices=[10, 30, 60, 90], note='basin (stirring 3/5/6; lid seat 1)'),
 'blue_cup':  dict(ax=2, sgn=-1, box=None, c=(-0.003, -0.003), r=0.040, slices=[10, 40, 80, 120, 150], note='cup interior (stirring 32/33; nest 10)'),
 'beige_cup': dict(ax=2, sgn=-1, box=None, c=(0.003, 0.006), r=0.040, slices=[10, 40, 80, 120, 150], note='cup interior (nest 10, outer)'),
 'plastic_dish_rack': dict(ax=0, sgn=+1, box=((-1, 1), (-0.08, 0.07), (-0.212, -0.118)), c=(-0.006, -0.165), r=1.0, slices=[5, 15, 30, 45],
                           note='utensil tower (spoon insertion 15/16)'),
}
def hull_eqs(hv):
    out = []
    for v in hv:
        e = ConvexHull(v).equations; out.append((v.min(0), v.max(0), e))
    return out
def occ(pts, H, pad=0.0):
    o = np.zeros(len(pts), bool)
    for lo, hi, e in H:
        k = np.where(np.all((pts >= lo - pad) & (pts <= hi + pad), 1))[0]
        if len(k) == 0: continue
        k = k[~o[k]]
        if len(k) == 0: continue
        o[k] |= (pts[k] @ e[:, :3].T + e[:, 3]).max(1) <= pad
    return o
def main():
    n = sys.argv[1]; sp = SPEC[n]; ax, sgn = sp['ax'], sp['sgn']
    d = np.load(f'{FG}/{n}.npz'); f, lo, h = d['f'], d['lo'], float(d['h'])
    X = [lo[i] + h * np.arange(f.shape[i]) for i in range(3)]
    sel = [np.ones(len(X[i]), bool) if sp['box'] is None else (X[i] >= sp['box'][i][0]) & (X[i] <= sp['box'][i][1]) for i in range(3)]
    sets = [(a.split('=')[0], hull_eqs(load_hulls(f"{a.split('=')[1]}/{n}.npz"))) for a in sys.argv[2:]]
    # ---- (1) columns, 2 mm cells, 1 mm steps along the axis
    oth = [i for i in range(3) if i != ax]
    ci = [np.where(sel[i])[0][::2] for i in oth]; ai = np.where(sel[ax])[0]
    if sgn > 0: ai = ai[::-1]                         # scan from the mouth inward
    grid = np.stack(np.meshgrid(ci[0], ci[1], indexing='ij'), -1).reshape(-1, 2)
    idx = np.zeros((len(grid), len(ai), 3), int)
    idx[:, :, oth[0]] = grid[:, 0, None]; idx[:, :, oth[1]] = grid[:, 1, None]; idx[:, :, ax] = ai[None, :]
    solid = f[idx[..., 0], idx[..., 1], idx[..., 2]] < 0
    has = solid.any(1); first = np.where(has, solid.argmax(1), -1)        # steps (mm) from the mouth plane
    # cavity columns: connected set of columns whose W2 first hit is >= 20 mm below the region top, containing the centre
    rr = np.hypot(X[oth[0]][grid[:, 0]] - sp['c'][0], X[oth[1]][grid[:, 1]] - sp['c'][1]) <= sp['r']
    rim = first[has].min(); deep = (has & rr & (first >= rim + 20)).reshape(len(ci[0]), len(ci[1]))
    lbl, _ = ndimage.label(deep)
    cij = (int(np.argmin(np.abs(X[oth[0]][ci[0]] - sp['c'][0]))), int(np.argmin(np.abs(X[oth[1]][ci[1]] - sp['c'][1]))))
    cav = (lbl == lbl[cij]).reshape(-1) & (lbl[cij] > 0)
    e0 = X[oth[0]][grid[cav, 0]]; e1 = X[oth[1]][grid[cav, 1]]
    print(f'   cavity component extent mm: axis{oth[0]} {e0.min()*1e3:.0f}..{e0.max()*1e3:.0f}, axis{oth[1]} {e1.min()*1e3:.0f}..{e1.max()*1e3:.0f}', flush=True)
    pts_all = np.stack([X[0][idx[..., 0]], X[1][idx[..., 1]], X[2][idx[..., 2]]], -1)
    print(f'== {n}: {sp["note"]}; region columns {has.sum()}, cavity columns {cav.sum()} (W2 floor depth below rim '
          f'median {np.median(first[cav]-rim):.0f} mm)', flush=True)
    floor_w2 = first[cav]
    for lab, H in sets:
        P = pts_all[cav].reshape(-1, 3); o = occ(P, H, pad=2e-6).reshape(cav.sum(), len(ai))
        fh = np.where(o.any(1), o.argmax(1), len(ai)); rise = floor_w2 - fh            # mm, + = hull floor higher
        cen = np.hypot(X[oth[0]][grid[cav, 0]] - sp['c'][0], X[oth[1]][grid[cav, 1]] - sp['c'][1]) <= 0.6 * min(sp['r'], 0.06)
        rc = rise[cen]
        print(f'  {lab:8s} floor rise mm, all cavity cells: median {np.median(rise):5.1f} p90 {np.percentile(rise,90):5.1f} max {rise.max():5.1f} | '
              f'>5 mm {np.mean(rise>5)*100:4.1f}% >10 mm {np.mean(rise>10)*100:4.1f}% >20 mm {np.mean(rise>20)*100:4.1f}% | '
              f'central cells (n {cen.sum()}): median {np.median(rc):4.1f} p90 {np.percentile(rc,90):4.1f} max {rc.max():4.1f}', flush=True)
    # ---- (2) slices across the axis at fixed heights above the W2 cavity floor (deepest cavity column)
    floor_step = int(np.median(floor_w2)); fl_mm = floor_step       # median floor depth below the mouth plane
    ia = np.where(sel[ax])[0]; mouth_i = ia[-1] if sgn > 0 else ia[0]
    for hs in sp['slices']:
        k = mouth_i - sgn * (fl_mm - hs)                            # axis index of the slice
        sl = [np.where(sel[i])[0] for i in range(3)]; sl[ax] = np.array([k])
        G = np.stack(np.meshgrid(*[X[i][sl[i]] for i in range(3)], indexing='ij'), -1)
        sh = G.shape[:3]; G2 = G.reshape(-1, 3)
        w2s = (f[np.ix_(sl[0], sl[1], sl[2])] < 0).reshape(-1)
        res = []
        for lab, H in [('W2', None)] + sets:
            s = w2s if H is None else occ(G2, H, pad=2e-6)
            free = (~s).reshape(sh).squeeze(ax)
            lbl, nl = ndimage.label(free)
            # centre component = free component that contains the cavity columns' centroid, else the largest interior one
            c2 = sp['c']
            ij = [int(np.argmin(np.abs(X[oth[0]][sl[oth[0]]] - c2[0]))), int(np.argmin(np.abs(X[oth[1]][sl[oth[1]]] - c2[1])))]
            lab_c = lbl[ij[0], ij[1]]
            if lab_c == 0: res.append(f'{lab} blocked'); continue
            comp = lbl == lab_c
            border = comp[0].any() or comp[-1].any() or comp[:, 0].any() or comp[:, -1].any()
            dtf = ndimage.distance_transform_edt(np.pad(comp, 1))     # 1 mm pixels
            res.append(f'{lab} D {2*dtf.max():5.1f} A {comp.sum()/100:6.1f}cm2{"*" if border else ""}')
        print(f'  slice {hs:3d} mm above floor: ' + ' | '.join(res), flush=True)
    # ---- (3) air filled inside the object's own region (2 mm grid, inside the convex hull of the W2 solid)
    s2 = [np.where(sel[i])[0][::2] for i in range(3)]
    G = np.stack(np.meshgrid(*[X[i][s2[i]] for i in range(3)], indexing='ij'), -1).reshape(-1, 3)
    fv = f[np.ix_(*s2)].reshape(-1); sol = G[fv < 0]
    ch = ConvexHull(sol[np.random.default_rng(0).choice(len(sol), min(len(sol), 200000), replace=False)])
    inside = (G @ ch.equations[:, :3].T + ch.equations[:, 3]).max(1) <= 0
    air = inside & (fv > 0.5e-3); A = G[air]; fa = fv[air] * 1e3
    print(f'  air inside the region hull: {air.sum()*8e-3:.0f} cm3', flush=True)
    for lab, H in sets:
        o = occ(A, H, pad=2e-6); dd = fa[o]
        print(f'  {lab:8s} air filled {o.sum()*8e-3:6.1f} cm3 ({o.mean()*100:4.1f}%); reach into air mm p50 {np.median(dd) if len(dd) else 0:4.1f} '
              f'p99 {np.percentile(dd,99) if len(dd) else 0:5.1f} max {dd.max() if len(dd) else 0:5.1f}', flush=True)
main()
