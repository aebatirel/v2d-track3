"""Clean, closed (watertight) object meshes for the showcase renders (owner 2026-11-06: "replace the mesh with a better
fully covered holeless mesh"). The official public scans have open patches (white_pot: 11 holes, two of ~16 cm inside
the pot; plastic_dish_rack: 23, largest ~9 cm). Automatic hole filling (MeshFix) caps the pot's opening, so instead
our own kit-of-parts meshes (meshes/library_c0: watertight, hollow, fitted to our stereo points; public-scan CD-O pot
0.342 cm, rack 0.456 cm, lid 0.220 cm) are rigidly aligned onto each official scan (ICP, the scan's own frame, so the
recorded body poses apply unchanged) and written with URDF copies (same inertial as the official URDF).
  clean_meshes.py SRC_LIB OUT_DIR name...    -> OUT_DIR/mesh/<name>/<name>.glb, OUT_DIR/urdf/<name>_rigid.urdf, report.json
Rendering only: the physics of the trained policies used FlashCHORD's convex pieces of the official scans.
"""
import json, os, sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree


def load(p):
    s = trimesh.load(p); g = trimesh.util.concatenate(list(s.geometry.values())) if hasattr(s, 'geometry') else s
    m = trimesh.Trimesh(g.vertices, g.faces, process=False); m.merge_vertices(merge_tex=True, merge_norm=True)
    return m


def icp(src, dst, iters=60):
    """Rigid point-to-point ICP of src vertices onto dst surface samples (both meshes), trimmed at the 90th percentile."""
    P = src.sample(30000); Q = dst.sample(120000); tree = cKDTree(Q); T = np.eye(4)
    P0 = P.copy()
    for _ in range(iters):
        Pc = P0 @ T[:3, :3].T + T[:3, 3]; d, j = tree.query(Pc); keep = d <= np.percentile(d, 90)
        A, B = Pc[keep], Q[j[keep]]; ca, cb = A.mean(0), B.mean(0); U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
        D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); R = Vt.T @ D @ U.T
        dT = np.eye(4); dT[:3, :3] = R; dT[:3, 3] = cb - R @ ca; T = dT @ T
    return T


def main():
    src_lib, out = sys.argv[1], sys.argv[2]; names = sys.argv[3:]
    rep = {}
    for n in names:
        scan = load(f'/content/t3/mesh/{n}/{n}.glb'); clean = load(os.path.join(src_lib, f'{n}.glb'))
        T = icp(clean, scan); al = clean.copy(); al.apply_transform(T)
        d_s2c, _ = cKDTree(al.sample(200000)).query(scan.sample(30000))   # scan surface -> clean surface
        d_c2s, _ = cKDTree(scan.sample(200000)).query(al.sample(30000))
        rot = np.degrees(np.arccos(np.clip((np.trace(T[:3, :3]) - 1) / 2, -1, 1)))
        os.makedirs(f'{out}/mesh/{n}', exist_ok=True); os.makedirs(f'{out}/urdf', exist_ok=True)
        trimesh.Trimesh(al.vertices, al.faces).export(f'{out}/mesh/{n}/{n}.glb')   # no colours: the renderer's shape colour applies
        u = open(f'/content/t3/urdf/{n}_rigid.urdf').read()
        u = u.replace(f'../mesh/{n}/{n}.glb', os.path.abspath(f'{out}/mesh/{n}/{n}.glb'))
        open(f'{out}/urdf/{n}_rigid.urdf', 'w').write(u)
        rep[n] = dict(source=os.path.join(src_lib, f'{n}.glb'), faces=len(al.faces), watertight=bool(al.is_watertight),
                      icp_translation_mm=float(np.linalg.norm(T[:3, 3]) * 1000), icp_rotation_deg=float(rot),
                      scan_to_clean_mm_median=float(np.median(d_s2c) * 1000), scan_to_clean_mm_p90=float(np.percentile(d_s2c, 90) * 1000),
                      clean_to_scan_mm_median=float(np.median(d_c2s) * 1000), clean_to_scan_mm_p90=float(np.percentile(d_c2s, 90) * 1000))
        print(n, json.dumps(rep[n]), flush=True)
    json.dump(rep, open(f'{out}/report.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
