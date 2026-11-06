"""Mass properties of our object meshes (2026-10-30, owner: "find the centre of gravity").

For every LIBRARY/<obj>.glb: surface area, the thin-shell centre of mass and inertia (what make_assets.py writes today),
and the solid ones from a filled voxel grid (pitch 2 mm). No ground truth is read: only our own meshes.
Usage: python object_physics.py LIBRARY_DIR OUT_JSON [--pitch 0.002] [--materials materials.json]
With --materials (per object: {"model": "solid"|"shell"|"prior", "density": kg/m3, "wall": m, "area_factor": f,
"mass_kg": m}) it also writes the mass, COM and inertia of that physical model: solid = density x filled volume
(watertight meshes only); shell = density x wall x area_factor x surface area (thin-wall limit; area_factor 0.5 when the
mesh carries both faces of a plate or lattice); prior = a stated mass on the shell COM and shell inertia shape.
"""
import argparse, glob, json, os
import numpy as np, trimesh


def shell_props(m, n=400000, seed=0):
    """Area-weighted surface samples: COM and inertia per unit mass about the COM (thin uniform shell)."""
    p = trimesh.sample.sample_surface_even(m, n, seed=seed)[0] if hasattr(trimesh.sample, 'sample_surface_even') else None
    if p is None or len(p) < n // 2:
        p = trimesh.sample.sample_surface(m, n, seed=seed)[0]
    c = p.mean(0); d = p - c
    I = np.eye(3) * (d ** 2).sum(1).mean() - (d[:, :, None] * d[:, None, :]).mean(0)
    return c, I


def solid_props(m, pitch):
    """Filled voxel occupancy: volume, COM, inertia per unit mass about the COM."""
    v = m.voxelized(pitch).fill()
    pts = v.points
    c = pts.mean(0); d = pts - c
    I = np.eye(3) * (d ** 2).sum(1).mean() - (d[:, :, None] * d[:, None, :]).mean(0) + np.eye(3) * pitch ** 2 / 6
    return len(pts) * pitch ** 3, c, I


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('library'); ap.add_argument('out')
    ap.add_argument('--pitch', type=float, default=0.002); ap.add_argument('--materials')
    a = ap.parse_args()
    mats = json.load(open(a.materials)) if a.materials else {}
    res = {}
    for f in sorted(glob.glob(os.path.join(a.library, '*.glb'))):
        n = os.path.basename(f)[:-4]
        m = trimesh.load(f, force='mesh')
        cs, Is = shell_props(m)
        vol, cv, Iv = solid_props(m, a.pitch)
        hull = m.convex_hull.volume
        r = dict(extents_cm=(m.bounding_box.extents * 100).round(2).tolist(), watertight=bool(m.is_watertight),
                 area_cm2=round(m.area * 1e4, 1), filled_volume_cm3=round(vol * 1e6, 1), hull_volume_cm3=round(hull * 1e6, 1),
                 fill_ratio=round(vol / hull, 3), shell_com_m=cs.round(5).tolist(), solid_com_m=cv.round(5).tolist(),
                 com_shift_mm=round(float(np.linalg.norm(cv - cs)) * 1000, 1),
                 shell_gyration_cm=(np.sqrt(np.linalg.eigvalsh(Is)) * 100).round(2).tolist(),
                 solid_gyration_cm=(np.sqrt(np.linalg.eigvalsh(Iv)) * 100).round(2).tolist())
        if n in mats:
            mt = mats[n]
            if mt['model'] == 'solid':
                mass, c, I = mt['density'] * vol, cv, Iv
            elif mt['model'] == 'shell':
                mass, c, I = mt['density'] * mt['wall'] * mt.get('area_factor', 1.0) * m.area, cs, Is
            else:
                mass, c, I = mt['mass_kg'], cs, Is
            r['physics'] = dict(model=mt['model'], material=mt.get('material'), mass_kg=round(float(mass), 4),
                                com_m=c.round(5).tolist(), inertia_kgm2=(I * mass).round(9).tolist(), note=mt.get('note'))
        res[n] = r
        print(f"{n:20s} ext {r['extents_cm']} wt {r['watertight']} area {r['area_cm2']:7.1f} cm2 filled {r['filled_volume_cm3']:7.1f} "
              f"hull {r['hull_volume_cm3']:7.1f} fill {r['fill_ratio']:.2f} COM shift solid-vs-shell {r['com_shift_mm']:5.1f} mm"
              + (f"  -> {r['physics']['mass_kg'] * 1000:.0f} g ({r['physics']['model']})" if 'physics' in r else ''), flush=True)
    json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
