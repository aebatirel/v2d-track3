"""Flatten the underside of a reconstructed mesh where the object rests on the table (2026-10-22).

Evidence (ep18): our sweeper's underside is rounded (the table hides it from the cameras; TSDF closing fills it in):
0.3 cm^2 within 2 mm of the lowest point at its perceived resting pose, centre of mass 3 cm outside that footprint, so
with the object assist off (as in the official evaluation) it falls over in 5 steps while mocap has it standing. An
object perception sees resting on a flat table touches it with a flat patch: vertices within DEPTH of the lowest point
along UP (the world up in the mesh frame at a resting frame of our own reference) are moved onto one plane DEPTH/2
above the lowest point (cut DEPTH/2, fill DEPTH/2). Only our perception is used (no scan, no ground truth).
Usage: python flatten_base.py IN.glb OUT.glb --up ux uy uz [--depth 0.008]
       python flatten_base.py IN.glb OUT.glb --from_ref REF.parquet --object NAME [--frame 0]
"""
import argparse, json, os
import numpy as np, trimesh


def flatten(m, up, depth):
    up = np.asarray(up, float); up /= np.linalg.norm(up)
    V = np.asarray(m.vertices, float).copy(); h = V @ up; h0 = h.min(); sel = h < h0 + depth
    V[sel] += np.outer((h0 + depth / 2) - h[sel], up)
    out = m.copy(); out.vertices = V
    return out, int(sel.sum())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('inp'); p.add_argument('out'); p.add_argument('--up', type=float, nargs=3)
    p.add_argument('--from_ref'); p.add_argument('--object'); p.add_argument('--frame', type=int, default=0)
    p.add_argument('--depth', type=float, default=0.008)
    a = p.parse_args()
    if a.up is None:
        import pyarrow.parquet as pq
        from scipy.spatial.transform import Rotation as Rot
        t = pq.read_table(a.from_ref); names = t.column('object_body_names')[0].as_py(); j = names.index(a.object)
        q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(-1, len(names), 4)[a.frame, j]
        a.up = Rot.from_quat(q[[1, 2, 3, 0]]).inv().apply([0, 0, 1]).tolist()
    scene = trimesh.load(a.inp)                                     # keep colours / materials: flatten every geometry
    geoms = scene.geometry if isinstance(scene, trimesh.Scene) else {'mesh': scene}
    moved = 0
    for k, g in list(geoms.items()):
        g2, n = flatten(g, a.up, a.depth); moved += n
        if isinstance(scene, trimesh.Scene):
            scene.geometry[k] = g2
        else:
            scene = g2
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True); scene.export(a.out)
    info = dict(inp=a.inp, up=np.round(a.up, 4).tolist(), depth=a.depth, vertices_moved=moved)
    json.dump(info, open(os.path.splitext(a.out)[0] + '.flatten.json', 'w'), indent=1); print(json.dumps(info))


if __name__ == '__main__':
    main()
