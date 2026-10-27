"""Total mass, COM and inertia about the root link origin of a URDF at zero joint pose."""
import sys, numpy as np, xml.etree.ElementTree as ET
from scipy.spatial.transform import Rotation as R
root = ET.parse(sys.argv[1]).getroot()
links = {l.get('name'): l for l in root.findall('link')}
joints = root.findall('joint')
child_of = {j.find('child').get('link'): j for j in joints}
parents = {j.find('parent').get('link') for j in joints}
base = [n for n in links if n not in child_of][0]
def T_of(origin):
    T = np.eye(4)
    if origin is None: return T
    xyz = np.array([float(v) for v in origin.get('xyz', '0 0 0').split()])
    rpy = np.array([float(v) for v in origin.get('rpy', '0 0 0').split()])
    T[:3, :3] = R.from_euler('xyz', rpy).as_matrix(); T[:3, 3] = xyz
    return T
cache = {base: np.eye(4)}
def world(n):
    if n in cache: return cache[n]
    j = child_of[n]; T = world(j.find('parent').get('link')) @ T_of(j.find('origin')); cache[n] = T; return T
mt, c, items = 0.0, np.zeros(3), []
for n, l in links.items():
    ine = l.find('inertial')
    if ine is None: continue
    m = float(ine.find('mass').get('value'))
    Tl = world(n) @ T_of(ine.find('origin'))
    i = ine.find('inertia'); g = {k: float(i.get(k)) for k in ['ixx','iyy','izz','ixy','ixz','iyz']}
    Ic = np.array([[g['ixx'], g['ixy'], g['ixz']], [g['ixy'], g['iyy'], g['iyz']], [g['ixz'], g['iyz'], g['izz']]])
    Iw = Tl[:3, :3] @ Ic @ Tl[:3, :3].T
    p = Tl[:3, 3]; items.append((m, p, Iw)); mt += m; c += m * p
c /= mt
Io = np.zeros((3, 3))
for m, p, Iw in items:
    Io += Iw + m * (np.dot(p, p) * np.eye(3) - np.outer(p, p))
print(f"base link {base}; links with inertial {len(items)}; total mass {mt:.4f} kg; COM in base frame {np.round(c,4)} (|c|={np.linalg.norm(c):.4f} m)")
print("inertia about base origin (kg m^2):\n", np.round(Io, 5))
print("principal moments about base origin:", np.round(np.linalg.eigvalsh(Io), 5))
