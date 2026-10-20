# Build a probe URDF exercising every collision-geometry path newton 1.2.0 + FlashCHORD would see.
import os, numpy as np, trimesh
D = '/Users/aebatirel/Documents/Code/v2d-research/work/19/a_urdf'; os.makedirs(D, exist_ok=True)
trimesh.creation.box(extents=(0.04, 0.02, 0.06)).export(f'{D}/piece_box.stl')
trimesh.creation.cylinder(radius=0.02, height=0.05, sections=24).export(f'{D}/piece_cyl.stl')
sc = trimesh.Scene(); sc.add_geometry(trimesh.creation.box(extents=(0.02,)*3, transform=trimesh.transformations.translation_matrix((0.1,0,0))), geom_name='g1')
sc.add_geometry(trimesh.creation.box(extents=(0.02,)*3, transform=trimesh.transformations.translation_matrix((0.15,0,0))), geom_name='g2'); sc.export(f'{D}/two_geoms.glb')
cb = trimesh.creation.box(extents=(0.03,)*3); fc = np.tile([200, 30, 30, 255], (len(cb.faces), 1)); fc[:6] = [30, 30, 200, 255]
cb.visual.face_colors = fc; cb.apply_translation((0, 0.1, 0)); cb.export(f'{D}/colored.ply')
soup = trimesh.creation.cylinder(radius=0.02, height=0.05, sections=24); v = soup.vertices[soup.faces].reshape(-1, 3)
trimesh.Trimesh(v, np.arange(len(v)).reshape(-1, 3), process=False).export(f'{D}/piece_cyl_soup.obj')
open(f'{D}/probe.urdf', 'w').write('''<?xml version="1.0"?>
<robot name="probe">
  <link name="object">
    <inertial><origin xyz="0 0 0" rpy="0 0 0"/><mass value="0.3"/><inertia ixx="1e-3" ixy="0" ixz="0" iyy="1e-3" iyz="0" izz="1e-3"/></inertial>
    <collision><origin xyz="0 0 0.1" rpy="0 0 0"/><geometry><mesh filename="piece_box.stl"/></geometry></collision>
    <collision><origin xyz="0 0 0" rpy="0 0 0"/><geometry><mesh filename="piece_cyl.stl"/></geometry></collision>
    <collision><origin xyz="0 0 0" rpy="0 0 0"/><geometry><mesh filename="piece_cyl_soup.obj"/></geometry></collision>
    <collision><origin xyz="0.2 0 0" rpy="0 0 0"/><geometry><box size="0.01 0.02 0.03"/></geometry></collision>
    <collision><origin xyz="0.3 0 0" rpy="0 0 0"/><geometry><cylinder radius="0.01" length="0.04"/></geometry></collision>
    <collision><origin xyz="0 0 0" rpy="0 0 0"/><geometry><mesh filename="two_geoms.glb"/></geometry></collision>
    <collision><origin xyz="0 0 0" rpy="0 0 0"/><geometry><mesh filename="colored.ply"/></geometry></collision>
  </link>
  <link name="extra">
    <collision><origin xyz="0 0 0" rpy="0 0 0"/><geometry><sphere radius="0.01"/></geometry></collision>
    <collision><origin xyz="0 0 0" rpy="0 0 0"/><geometry><mesh filename="piece_box.stl" scale="0.5 0.5 0.5"/></geometry></collision>
  </link>
  <joint name="fix" type="fixed"><parent link="object"/><child link="extra"/><origin xyz="0 -0.2 0" rpy="0 0 0"/></joint>
</robot>
''')
print('ok')
