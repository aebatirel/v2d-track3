"""Summarise a recorded trace: errors, Joint6/7_R, wrist orientation errors, gate activity, phase landmarks.
Usage: python -I summarize.py WORKSHOP_DIR TRACE_NPZ ACTOR_NPZ [frames...]"""
import sys, os, json
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net
C, trace, actor = sys.argv[1:4]
fsel = [int(x) for x in sys.argv[4:]] or [100, 200, 250, 290, 300, 305, 310, 315, 320, 330, 340, 352, 370, 385, 400, 450, 500, 600, 700, 800, 870, 900, 950, 1000, 1022]
t = np.load(trace); ref = np.load(f'{C}/assets/reference.npz'); RT = ref['robot_target']
obs, fr, e, qp, cf = t['obs'], t['frames'], t['err'], t['qpos'], t['cforce']
w = net.load(actor); _, A = net.forward(w, obs, acts=True)
ang = lambda q: 2 * np.arccos(np.clip(abs(q[0]), 0, 1))
lim = lambda j6: max(0, min(np.pi / 2, np.deg2rad(110.5) - 1.025 * abs(j6)) - np.deg2rad(1.5))
meta = json.loads(str(t['meta'])); print(json.dumps(meta))
print('frame  obj_err  obj_ang  wrist | J6R off  J7R q/ref/lim | J6L off J7L q/ref/lim | Rw_ang Lw_ang | F_R F_L | rms | z5')
for f in fsel:
    k = np.flatnonzero(fr == f)
    if not len(k): continue
    i = k[0]; o = obs[min(i, len(obs) - 1)]; ii = min(i, len(obs) - 1)
    print(f'{f:5d} {e[i][0]:.3f} {e[i][1]:.3f} {e[i][2]:.3f} | {qp[i,5]-RT[f,5]:+.2f} {qp[i,6]:+.2f}/{RT[f,6]:+.2f}/{lim(qp[i,5]):.2f} | '
          f'{qp[i,34]-RT[f,34]:+.2f} {qp[i,35]:+.2f}/{RT[f,35]:+.2f}/{lim(qp[i,34]):.2f} | {ang(o[154:158]):.2f} {ang(o[161:165]):.2f} | '
          f'{cf[i-1][0] if i>0 else 0:5.0f} {cf[i-1][1] if i>0 else 0:5.0f} | {A["rms"][ii,0]:.2f} | {A["mean"][ii,5]:.2f}')
