"""C4 addendum 8: GT-free outer-shell copy. Drops fragments (< 1% of total area) and components that lie inside another
component (>= 90% of 500 sampled vertices inside its volume; convex hull if that component is not watertight).
Usage: outer_shell.py IN.glb OUT.glb   -> writes OUT.glb only if something was dropped; prints a JSON report.
"""
import hashlib, json, sys
import numpy as np, trimesh

src, out = sys.argv[1:3]
m = trimesh.load(src, force='mesh')
comps = m.split(only_watertight=False)
tot = sum(c.area for c in comps)
rep = dict(src=src, n_components=len(comps), total_area_mm2=round(tot * 1e6, 1), components=[])
keep = []
big = [c for c in comps if c.area >= 0.01 * tot]
rng = np.random.default_rng(0)
for i, c in enumerate(comps):
    r = dict(i=i, area_mm2=round(c.area * 1e6, 1), extents_mm=np.round(c.extents * 1e3, 1).tolist(),
             watertight=bool(c.is_watertight))
    if c.area < 0.01 * tot:
        r['drop'] = 'fragment < 1% area'
        rep['components'].append(r); continue
    v = c.vertices[rng.choice(len(c.vertices), min(500, len(c.vertices)), replace=False)]
    inside_of = None
    for j, o in enumerate(big):
        if o is c or o.area <= c.area:
            continue
        vol = o if o.is_watertight else o.convex_hull
        frac = float(vol.contains(v).mean())
        if frac >= 0.9:
            inside_of = (j, round(frac, 3)); break
    if inside_of:
        r['drop'] = f'inside a larger component (frac {inside_of[1]})'
    else:
        keep.append(c)
    rep['components'].append(r)
dropped = len(comps) - len(keep)
rep['dropped'] = dropped
if dropped and keep:
    res = trimesh.util.concatenate(keep)
    res.export(out)
    rep.update(out=out, out_md5=hashlib.md5(open(out, 'rb').read()).hexdigest(), out_faces=int(len(res.faces)),
               out_area_mm2=round(res.area * 1e6, 1))
else:
    rep['out'] = None
print(json.dumps(rep))
