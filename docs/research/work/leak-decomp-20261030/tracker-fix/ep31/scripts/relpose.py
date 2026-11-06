"""ORACLE: sweeper orientation relative to the rack at f0 (truth vs P_s vs P_o), decomposed about the rack's own axes,
and the angle between the sweeper's thin axis and the rack's long axis (slot alignment). Also the end-rest (f260)."""
import sys, numpy as np
sys.path.insert(0, sys.argv[1]); import diag31 as D
from scipy.spatial.transform import Rotation as Rot
names, gt, N, tr = D.load_tracks()
def rel(Ts, Tr): return np.linalg.inv(Tr) @ Ts
for f in (0, 20, 100, 260):
    Rt = rel(gt['mini_sweeper'][f], gt['plastic_dish_rack'][f])
    print('frame', f)
    for arm in ('truth', 'Po', 'Ps'):
        Rr = Rt if arm == 'truth' else rel(tr[arm]['mini_sweeper'][f], tr[arm]['plastic_dish_rack'][f])
        thin = Rr[:3, :3] @ np.array([1.0, 0, 0])   # sweeper thin axis (4.8 cm) in rack frame
        ang_long = np.degrees(np.arccos(abs(thin[2])))   # rack body z = long axis (51 cm)
        hz = Rr[:3, :3] @ np.array([0, 0, 1.0]); ang_vert = np.degrees(np.arccos(abs(hz[0])))  # sweeper handle vs rack vertical (body x)
        line = '  %-5s thin-axis vs rack long axis %.2f deg; handle vs rack vertical %.2f deg; pos in rack frame cm %s' % (arm, ang_long, ang_vert, np.round(Rr[:3, 3] * 100, 1))
        if arm != 'truth':
            E = Rr[:3, :3] @ Rt[:3, :3].T   # rack-frame rotation taking truth-relative to perceived-relative
            rv = np.degrees(Rot.from_matrix(E).as_rotvec())
            line += ' | rel err %.2f deg, about rack [vertical, across, long] = %s, dpos cm %s' % (np.linalg.norm(rv), np.round(rv, 2), np.round((Rr[:3, 3] - Rt[:3, 3]) * 100, 2))
        print(line)
