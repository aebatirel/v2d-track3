"""Simulator assets from our own meshes (route A, 2026-10-21): the same layout as the public Track 3 assets.

For every LIBRARY/<obj>.glb writes OUT/mesh/<obj>/<obj>.glb (visual = collision, geometry only) and
OUT/urdf/<obj>_rigid.urdf with the public files' conventions: placeholder mass 0.3 kg, centre of mass and inertia
from a uniform triangle-surface estimate over the mesh (the public comment says the same), mesh frame = link frame.
mkref.py --assets OUT then writes these paths into the reference, so FlashCHORD trains and evaluates with our objects.
Usage: python make_assets.py LIBRARY_DIR OUT_DIR [--mass 0.3]

The simulator copy carries no colours. Newton's loader (newton/_src/utils/mesh.py, load_meshes_from_file) splits a mesh
with per-vertex or per-face colours into one shape per distinct face colour; FlashCHORD then runs CoACD on every
fragment. With our video-coloured meshes a board became 174 open fragments: CoACD ran > 10 min and the 4096-world
training build was killed for memory (2026-10-21, ep24 twice). Geometry only, the board loads as 1 watertight shape.
"""
import argparse, glob, os, shutil
import numpy as np, trimesh

URDF = """<?xml version="1.0"?>
<robot name="track3_{n}">
  <!-- Our reconstruction (pipeline/recon_mesh.py). Placeholder mass {m} kg as in the public assets; COM/inertia are a
       uniform triangle-surface estimate over this mesh. -->
  <mujoco><compiler balanceinertia="true" discardvisual="false"/></mujoco>
  <link name="object">
    <inertial>
      <origin xyz="{cx:.6f} {cy:.6f} {cz:.6f}" rpy="0 0 0"/>
      <mass value="{m}"/>
      <inertia ixx="{ixx:.9g}" ixy="{ixy:.9g}" ixz="{ixz:.9g}" iyy="{iyy:.9g}" iyz="{iyz:.9g}" izz="{izz:.9g}"/>
    </inertial>
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry><mesh filename="../mesh/{n}/{n}.glb" scale="1 1 1"/></geometry>
    </visual>
{collisions}
  </link>
</robot>
"""


COLLISION = """    <collision>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry><mesh filename="../mesh/{f}" scale="1 1 1"/></geometry>
    </collision>"""


def surface_inertia(m, mass):
    """COM and inertia (about the COM) of a thin uniform shell over the triangles, by sampling."""
    pts = trimesh.sample.sample_surface_even(m, 20000, seed=0)[0] if hasattr(trimesh.sample, 'sample_surface_even') \
        else trimesh.sample.sample_surface(m, 20000, seed=0)[0]
    c = pts.mean(0); d = pts - c
    I = mass * (np.eye(3) * (d ** 2).sum(1).mean() - (d[:, :, None] * d[:, None, :]).mean(0))
    return c, I


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('library'); p.add_argument('out'); p.add_argument('--mass', type=float, default=0.3)
    p.add_argument('--pieces', help='DIR/<obj>/piece_*.obj (pipeline/collision_decomp.py; mesh v5 spec 8.2): one '
                                    '<collision> element per convex piece for those objects, the visual stays the mesh')
    a = p.parse_args()
    os.makedirs(f'{a.out}/urdf', exist_ok=True)
    for f in sorted(os.listdir(a.library)):
        if not f.endswith('.glb'):
            continue
        n = f[:-4]
        m = trimesh.load(f'{a.library}/{f}', force='mesh')
        m = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)   # drop colours (see above)
        os.makedirs(f'{a.out}/mesh/{n}', exist_ok=True)
        m.export(f'{a.out}/mesh/{n}/{n}.glb')
        c, I = surface_inertia(m, a.mass)
        cols = [f'{n}/{n}.glb']
        pieces = sorted(glob.glob(f'{a.pieces}/{n}/piece_*.obj')) if a.pieces else []
        if pieces:                                       # FlashCHORD's CoACD keeps each convex piece as one hull
            cols = []
            for k, pc in enumerate(pieces):
                shutil.copy(pc, f'{a.out}/mesh/{n}/col_{k:02d}.obj'); cols.append(f'{n}/col_{k:02d}.obj')
        open(f'{a.out}/urdf/{n}_rigid.urdf', 'w').write(URDF.format(
            n=n, m=a.mass, cx=c[0], cy=c[1], cz=c[2], ixx=I[0, 0], ixy=I[0, 1], ixz=I[0, 2], iyy=I[1, 1], iyz=I[1, 2],
            izz=I[2, 2], collisions='\n'.join(COLLISION.format(f=f) for f in cols)))
        print(f'{n}: {len(m.vertices)} verts, watertight {m.is_watertight}, extents cm {np.round(m.extents * 100, 1)}, '
              f'com {np.round(c * 100, 2)} cm' + (f', {len(pieces)} collision pieces' if pieces else ''))


if __name__ == '__main__':
    main()
