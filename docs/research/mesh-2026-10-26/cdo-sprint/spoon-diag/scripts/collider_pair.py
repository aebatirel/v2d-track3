"""Collider vs collider: the spoon's own CoACD pieces (union, sampled at 1.5 mm) posed by our reference in the container
frame, tested against the container's visual solid, its CoACD pieces and (cup) the C0 lathe solid. Also the part of the
spoon's pieces outside the spoon's visual solid (what CoACD adds to the spoon, e.g. a filled bowl).
Usage: collider_pair.py SCRIPTS CONFIG OUT SPOON_HULLS_32 SPOON_HULLS_33 SPOON_HULLS_16"""
import json, sys
import numpy as np
sys.path.insert(0, sys.argv[1]); import vox  # noqa: E402
SH = dict(zip(('32', '33', '16'), sys.argv[4:7]))
exec(open(f'{sys.argv[1]}/analyze.py').read().split('def main():')[0])
res = {}
for ep, c in cfg['episodes'].items():
    names, T = ref_poses(c['ref']); ci = names.index(c['container']); si = names.index('wooden_spoon')
    g = vox.voxelize(vox.load(c['container_mesh']), PITCH); H, eqs, boxes = load_hulls(c['hulls'])
    sp = vox.load(c['spoon_mesh']); gs = vox.voxelize(sp, SPOON_PITCH, pad=0.01)
    Hs, eqs_s, boxes_s = load_hulls(SH[ep])
    n = np.array(gs.occ.shape); G = gs.lo + (np.argwhere(np.ones(n, bool)) + 0.5) * SPOON_PITCH
    ins, _ = hull_test(eqs_s, boxes_s, G); Sh = G[ins]; added = ~gs.lookup(Sh)
    lathe = Lathe(cfg['lathe_json']) if c['container'] == 'blue_cup' else None
    rows = []
    for f in range(len(T)):
        M = np.linalg.inv(T[f, ci]) @ T[f, si]; X = Sh @ M[:3, :3].T + M[:3, 3]
        lo, hi = g.lo - 0.02, g.lo + np.array(g.occ.shape) * PITCH + 0.02; near = np.all((X > lo) & (X < hi), 1)
        Xn = X[near]; an = added[near]
        iv = g.lookup(Xn) if len(Xn) else np.zeros(0, bool); ih, _ = hull_test(eqs, boxes, Xn) if len(Xn) else (np.zeros(0, bool), None)
        row = dict(f=f, spoonhull_in_vis=cm3(iv.sum(), SPOON_PITCH), spoonhull_in_hull=cm3(ih.sum(), SPOON_PITCH),
                   spoonadded_in_vis=cm3((iv & an).sum(), SPOON_PITCH), spoonadded_in_hull=cm3((ih & an).sum(), SPOON_PITCH))
        if lathe is not None:
            row['spoonhull_in_lathe'] = cm3(lathe.inside(Xn).sum(), SPOON_PITCH) if len(Xn) else 0.0
        rows.append({k: round(v, 3) if isinstance(v, float) else v for k, v in row.items()})
    summ = {k: dict(max=round(max(r[k] for r in rows), 2), argmax=int(np.argmax([r[k] for r in rows])), frames_gt_1=sum(r[k] > 1 for r in rows))
            for k in rows[0] if k != 'f'}
    res[ep] = dict(spoon_hulls=SH[ep].split('/')[-1], spoon_pieces=len(Hs), spoon_hull_union_cm3=round(cm3(len(Sh), SPOON_PITCH), 1),
                   spoon_added_by_coacd_cm3=round(cm3(added.sum(), SPOON_PITCH), 1), summary=summ, per_frame=rows)
    print(ep, json.dumps({k: v for k, v in res[ep].items() if k != 'per_frame'}), flush=True)
json.dump(res, open(f'{sys.argv[3]}/collider_pair.json', 'w'), indent=1)
