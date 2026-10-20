"""GT object kinematics (public, 20 fps) and the wrist-residual demand of the default
FlashCHORD Sharpa controller at motion_speed 1.0 vs 0.5. Object motion is used as a proxy for
the grasping wrist while the object moves. Research only."""
import numpy as np
from scipy.signal import savgol_filter
from common14 import *

KP, KD = 25.0, 6.0          # wrist PD (sharpa_hands.py:56-60), N/m, N s/m ; Nm/rad, Nm s/rad
M_HAND, M_OBJ, G = 1.243, 0.3, 9.81
CLIP_P, CLIP_R = 0.20, 1.0  # residual clamps (m, rad)
dt = 1 / FPS


def rotvel(q):
    """angular speed rad/s from consecutive xyzw quats."""
    return np.r_[0, qangle(q[1:], q[:-1])] / dt


rows = []
for e in all_episodes():
    p = fill_gaps(e["pose"], e["vis"])
    for j, nm in enumerate(e["names"]):
        x = p[:, j, :3]
        if len(x) < 15:
            continue
        xs = savgol_filter(x, 9, 2, axis=0)
        v = savgol_filter(x, 9, 2, deriv=1, delta=dt, axis=0)
        a = savgol_filter(x, 9, 2, deriv=2, delta=dt, axis=0)
        w = savgol_filter(rotvel(p[:, j, 3:]), 9, 2)
        sp = np.linalg.norm(v, axis=1)
        mov = (sp > 0.05) | (w > np.radians(30))  # moving frames (likely held)
        if mov.sum() < 5:
            continue
        for s in (1.0, 0.5):
            vv, aa, ww = v * s, a * s * s, w * s
            # force the wrist PD must supply while carrying the object
            F = (M_HAND + M_OBJ) * aa + KD * vv + np.array([0, 0, M_OBJ * G])
            dpos = np.linalg.norm(F, axis=1) / KP
            drot = KD * np.abs(ww) / KP
            rows.append(dict(ep=e["ep"], obj=nm, s=s, nmov=int(mov.sum()),
                             v95=np.percentile(sp[mov], 95), vmax=sp[mov].max(),
                             a95=np.percentile(np.linalg.norm(a, axis=1)[mov], 95),
                             w95=np.degrees(np.percentile(w[mov], 95)), wmax=np.degrees(w[mov].max()),
                             dpos95=np.percentile(dpos[mov], 95), dposmax=dpos[mov].max(),
                             satp=float(np.mean(dpos[mov] > CLIP_P)),
                             drot95=np.percentile(drot[mov], 95), satr=float(np.mean(drot[mov] > CLIP_R)),
                             step_cm95=100 * np.percentile(sp[mov], 95) * dt))

import pandas as pd
df = pd.DataFrame(rows)
pd.set_option("display.width", 220)
print(df[df.s == 1.0].drop(columns="s").round(3).to_string(index=False))
print()
g = df.groupby("s")[["v95", "vmax", "a95", "w95", "wmax", "dpos95", "dposmax", "satp", "drot95", "satr", "step_cm95"]]
print("median over moving objects:\n", g.median().round(3).to_string())
print("max over moving objects:\n", g.max().round(3).to_string())
print("objects with any pos saturation (s=1, s=0.5):",
      int((df[df.s == 1].satp > 0).sum()), int((df[df.s == 0.5].satp > 0).sum()), "of", int((df.s == 1).sum()))
print("objects with any rot saturation (s=1, s=0.5):",
      int((df[df.s == 1].satr > 0).sum()), int((df[df.s == 0.5].satr > 0).sum()))
print("frame-weighted saturation fraction pos (s=1, 0.5):",
      round(float(np.average(df[df.s == 1].satp, weights=df[df.s == 1].nmov)), 4),
      round(float(np.average(df[df.s == .5].satp, weights=df[df.s == .5].nmov)), 4))
print("frame-weighted saturation fraction rot (s=1, 0.5):",
      round(float(np.average(df[df.s == 1].satr, weights=df[df.s == 1].nmov)), 4),
      round(float(np.average(df[df.s == .5].satr, weights=df[df.s == .5].nmov)), 4))
df.to_csv("kin.csv", index=False)
