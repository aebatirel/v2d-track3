# Stage C: package split W2 parts as a FlashCHORD-ready asset (one untextured binary STL per <collision>, all on the
# root link, explicit <inertial> copied from the public URDF, original GLB kept as <visual>), then reload every STL the
# way newton 1.2.0 does (trimesh 4.12.2 load(force="mesh"), default processing) and check it survived the round trip.
# usage: c_export.py <name> <parts_dir> <outdir>
import sys, os, re, glob, numpy as np, trimesh
name, pdir, od = sys.argv[1], sys.argv[2], sys.argv[3]
P = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public'
os.makedirs(f'{od}/{name}/collision', exist_ok=True); os.makedirs(f'{od}/reloaded', exist_ok=True)
parts = sorted(glob.glob(f'{pdir}/{name}*.npz'))
pub = open(f'{P}/urdf/{name}_rigid.urdf').read()
inertial = re.search(r'<inertial>.*?</inertial>', pub, re.S).group(0)
vis = os.path.relpath(f'{P}/mesh/{name}/{name}.glb', f'{od}/{name}')
cols = []
for i, p in enumerate(parts):
    d = np.load(p); m = trimesh.Trimesh(d['v'], d['f'], process=False)
    fn = f'collision/{name}_c{i:03d}.stl'; m.export(f'{od}/{name}/{fn}')
    r = trimesh.load(f'{od}/{name}/{fn}', force='mesh')       # newton's call
    dv = np.abs(np.sort(np.asarray(r.vertices), 0) - np.sort(m.vertices, 0)).max() * 1e3 if len(r.vertices) == len(m.vertices) else np.nan
    np.savez(f'{od}/reloaded/{name}_c{i:03d}.npz', v=np.asarray(r.vertices, np.float64), f=np.asarray(r.faces, np.int64))
    print(f'{fn}: V {len(m.vertices)}->{len(r.vertices)} F {len(m.faces)}->{len(r.faces)} watertight {r.is_watertight} '
          f'winding_consistent {r.is_winding_consistent} vol {r.volume*1e6:.2f} cm3 L {np.ptp(r.vertices,0).max()*1e3:.1f} mm '
          f'max|dv| {dv:.2e} mm size {os.path.getsize(f"{od}/{name}/{fn}")/1e6:.1f} MB', flush=True)
    cols.append(f'    <collision>\n      <origin xyz="0 0 0" rpy="0 0 0"/>\n      <geometry><mesh filename="{fn}"/></geometry>\n    </collision>')
urdf = f'''<?xml version="1.0"?>
<robot name="{name}_split">
  <link name="object">
    {inertial}
    <visual>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <geometry><mesh filename="{vis}" scale="1 1 1"/></geometry>
    </visual>
{chr(10).join(cols)}
  </link>
</robot>
'''
open(f'{od}/{name}/{name}_split.urdf', 'w').write(urdf); print('wrote', f'{od}/{name}/{name}_split.urdf', len(cols), 'collision elements')
