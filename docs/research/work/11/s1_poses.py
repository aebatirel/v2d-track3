from c11 import *
import pandas as pd
rows = []
for ep in PUBLIC:
    e = load_episode(ep); p = e['pose']; T = len(p)
    for j, nm in enumerate(e['names']):
        v = np.where(e['vis'][:, j] & np.isfinite(p[:, j, 0]))[0]
        f0, f1 = v[0], v[-1]
        R = R_of(p[[f0, f1], j, 3:])
        # empirical up body axis (signed) at f0 and f1
        ups = []
        for k in range(2):
            c = R[k][2, :]  # world z expressed in body coords = row 2
            a = np.argmax(np.abs(c)); ups.append(("+" if c[a] > 0 else "-") + "xyz"[a] + f"({abs(c[a]):.3f})")
        y0, t0 = yaw_tilt(p[f0, j, 3:], nm); y1, t1 = yaw_tilt(p[f1, j, 3:], nm)
        # path length
        x = p[v, j, :3]; L = np.sum(np.linalg.norm(np.diff(x, axis=0), axis=1))
        rows.append(dict(ep=ep, task=e['task'], obj=nm, slot=j, T=T, nvis=len(v), f0=f0, f1=f1,
                         up0=ups[0], up1=ups[1], yaw0=round(float(y0), 1), tilt0=round(float(t0), 1),
                         yaw1=round(float(y1), 1), tilt1=round(float(t1), 1),
                         x0=round(p[f0, j, 0], 3), y0=round(p[f0, j, 1], 3), z0=round(p[f0, j, 2], 3),
                         x1=round(p[f1, j, 0], 3), y1=round(p[f1, j, 1], 3), z1=round(p[f1, j, 2], 3), path=round(L, 2)))
df = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)
print(df.to_string(index=False))
df.to_csv('s1_poses.csv', index=False)
