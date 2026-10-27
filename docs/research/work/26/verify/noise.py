import sys, importlib.util, numpy as np
from scipy.signal import savgol_filter
spec = importlib.util.spec_from_file_location("sens", sys.argv[3]); S = importlib.util.module_from_spec(spec)
sys.argv = sys.argv[:3]; spec.loader.exec_module(S)
dt = S.dt
print("ep obj  T vis | static jitter rms(x - SG9) mm | dd-noise accel (m/s^2) | lift cm | max speed | max |w| deg/s | adv+grav max gap")
nz = []
for tr in S.TR:
    x = tr["x"]
    v = savgol_filter(x, 9, 2, deriv=1, delta=dt, axis=0)
    w = savgol_filter(S.cm.ang_vel(tr["q"].copy()), 9, 2, axis=0)
    sp = np.linalg.norm(v, axis=1); mov = (sp > 0.05) | (np.linalg.norm(w, axis=1) > np.radians(30))
    st = sp < 0.005
    jit = np.sqrt(np.mean((x - savgol_filter(x, 9, 2, axis=0))[st] ** 2)) * 1000 if st.sum() > 10 else np.nan
    dd = np.diff(x, 2, axis=0) / dt ** 2
    ddn = np.sqrt(np.mean(dd[st[1:-1]] ** 2)) if st.sum() > 10 else np.nan
    if mov.sum() < 5: continue
    nz.append(jit)
    lift = (x[mov, 2].max() - np.percentile(x[:, 2], 5)) * 100
    print(f"{tr['ep']:2d} {tr['obj']:15s} {tr['T']:3d} {tr['nvis']:3d} | {jit:6.3f} | {ddn:6.3f} | {lift:5.1f} | {sp.max():.2f} | {np.degrees(np.linalg.norm(w,axis=1)).max():5.0f}")
print("median static jitter (mm):", np.nanmedian(nz))
