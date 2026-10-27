"""Sensitivity reruns of carry_model.py (copy). Diagnostics on public GT only."""
import importlib.util, glob, sys, itertools
import numpy as np, pandas as pd
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation as Rot
spec = importlib.util.spec_from_file_location("cm", sys.argv[1]); cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)
DATA = sys.argv[2]
G, dt = 9.81, cm.dt

def tracks():
    out = []
    for f in sorted(glob.glob(f"{DATA}/episode_*.parquet")):
        ep, names, pos, quat = cm.load(f)
        for j, nm in enumerate(names):
            x = cm.fill(pos[:, j]); q = cm.fill(quat[:, j])
            if not np.all(np.isfinite(x)) or len(x) < 15: continue
            out.append(dict(ep=ep, obj=nm, x=x, q=q, nvis=int(np.isfinite(pos[:, j, 0]).sum()), T=len(x)))
    return out
TR = tracks()

def resid(x, v, a, carried, kp, kd, mh, mo, adv=False, gof=False):
    M = mh + mo * carried[:, None]
    F = M * a; F[:, 2] += mo * G * carried
    r = (F + kd * v) / kp
    gap = np.zeros_like(x)
    if adv:
        tau = kd / kp; t = np.arange(len(x)) * dt
        xa = np.stack([np.interp(t + tau, t, x[:, k]) for k in range(3)], 1)
        r = r - (xa - x); gap = gap + (xa - x)
    if gof:
        r[:, 2] -= mo * G * carried / kp; gap[:, 2] += mo * G * carried / kp
    return r, gap

def run(win=9, vth=0.05, wth=30.0, mh=1.243, mo=0.3, clip=0.20, kd_mode="zeta", I=0.011, offset=None, seed=0,
        lift_gate=False, detail=False):
    zeta0 = 6.0 / (2 * np.sqrt(25.0 * (mh + mo)))
    rows, grip, rot = [], [], []
    rng = np.random.default_rng(seed)
    for tr in TR:
        x, q = tr["x"].copy(), tr["q"]
        if offset is not None:                       # wrist rigidly offset from the object frame origin
            d = rng.normal(size=3); d *= offset / np.linalg.norm(d)
            qn = q / np.linalg.norm(q, axis=1, keepdims=True)
            Rm = Rot.from_quat(np.concatenate([qn[:, 1:], qn[:, :1]], 1))
            x = x + Rm.apply(d)
        v = savgol_filter(x, win, 2, deriv=1, delta=dt, axis=0)
        a = savgol_filter(x, win, 2, deriv=2, delta=dt, axis=0)
        w = savgol_filter(cm.ang_vel(q.copy()), win, 2, axis=0)
        wd = savgol_filter(w, win, 2, deriv=1, delta=dt, axis=0)
        sp = np.linalg.norm(v, axis=1)
        mov = (sp > vth) | (np.linalg.norm(w, axis=1) > np.radians(wth))
        if mov.sum() < 5: continue
        carried = mov.astype(float)
        if lift_gate:                                # weight only when lifted >1 cm above the track's rest height
            zr = np.percentile(x[:, 2], 5)
            carried = (mov & (x[:, 2] > zr + 0.01)).astype(float)
        lf = np.linalg.norm(a + np.array([0, 0, G]), axis=1)[mov] / G
        grip.append(dict(ep=tr["ep"], obj=tr["obj"], p05=np.percentile(lf, 5), p95=np.percentile(lf, 95), mx=lf.max(), mn=lf.min()))
        for label, kp in [("default", 25), ("adv", 25), ("grav", 25), ("adv+grav", 25), ("kp50", 50), ("kp100", 100), ("kp200", 200)]:
            if kp == 25: kd = 6.0
            elif kd_mode == "zeta": kd = zeta0 * 2 * np.sqrt(kp * (mh + mo))
            else: kd = float(kd_mode)
            r, gap = resid(x, v, a, carried, kp, kd, mh, mo, "adv" in label, "grav" in label)
            r, gap = r[mov], gap[mov]
            ra = np.abs(r); s = ra.max(1) > clip
            gn = np.linalg.norm(gap, axis=1)
            rows.append(dict(ep=tr["ep"], obj=tr["obj"], variant=label, nmov=int(mov.sum()), sat=s.mean(), nsat=int(s.sum()),
                             z_p95=np.percentile(ra[:, 2], 95), gap_p95=np.percentile(gn, 95), gap_max=gn.max(),
                             gap_over15=float(np.mean(gn > 0.15)), F_net_max=np.abs((mh + mo) * a[mov]).max() + mo * G))
        for label, k, dd in [("rot25", 25, 6.0), ("rot100", 100, 12.0), ("rot1200", 1200, 60.0)]:
            rr = (I * wd + dd * w) / k
            rr = rr[mov]
            rot.append(dict(ep=tr["ep"], obj=tr["obj"], variant=label, nmov=int(mov.sum()),
                            sat_axis=float(np.mean(np.abs(rr).max(1) > 1.0)), sat_norm=float(np.mean(np.linalg.norm(rr, axis=1) > 1.0)),
                            p95_axis=np.percentile(np.abs(rr).max(1), 95), p95_norm=np.percentile(np.linalg.norm(rr, axis=1), 95),
                            Iterm_p95=np.percentile(np.linalg.norm(I * wd[mov], axis=1) / k, 95),
                            Dterm_p95=np.percentile(np.linalg.norm(dd * w[mov], axis=1) / k, 95)))
    df, gr, ro = pd.DataFrame(rows), pd.DataFrame(grip), pd.DataFrame(rot)
    summ = {}
    for v_, g in df.groupby("variant", sort=False):
        summ[v_] = dict(n=len(g), tracks=int((g.sat > 0).sum()), tracks3=int((g.nsat >= 3).sum()),
                        frame_pct=100 * np.average(g.sat, weights=g.nmov), med_z_p95=g.z_p95.median(),
                        gap_p95_med=g.gap_p95.median(), gap_p95_max=g.gap_p95.max(), gap_max=g.gap_max.max(),
                        gap_over15_pct=100 * np.average(g.gap_over15, weights=g.nmov), Fmax=g.F_net_max.max())
    rsum = {}
    for v_, g in ro.groupby("variant", sort=False):
        rsum[v_] = dict(tracks_axis=int((g.sat_axis > 0).sum()), tracks_norm=int((g.sat_norm > 0).sum()),
                        med_p95_axis=g.p95_axis.median(), med_p95_norm=g.p95_norm.median(),
                        Iterm_med=g.Iterm_p95.median(), Dterm_med=g.Dterm_p95.median(),
                        sat_eps=",".join(f"{a}:{b}" for a, b in g[g.sat_axis > 0][["ep", "obj"]].values))
    load = dict(min_p05=gr.p05.min(), max_p95=gr.p95.max(), min=gr.mn.min(), max=gr.mx.max(),
                med_p05=gr.p05.median(), med_p95=gr.p95.median())
    if detail: return summ, rsum, load, df, ro, gr
    return summ, rsum, load

def line(tag, s, r, l):
    d = s["default"]
    print(f"{tag:34s} n={d['n']:2d} | default {d['tracks']:2d}/{d['n']} ({d['tracks3']:2d} w>=3fr) {d['frame_pct']:5.2f}% z95 {100*d['med_z_p95']:4.1f}cm"
          f" | adv {s['adv']['tracks']:2d} {s['adv']['frame_pct']:.2f}% | grav {s['grav']['tracks']:2d} {s['grav']['frame_pct']:.2f}%"
          f" | adv+grav {s['adv+grav']['tracks']:2d} {s['adv+grav']['frame_pct']:.2f}% z95 {100*s['adv+grav']['med_z_p95']:.1f}"
          f" | kp50 {s['kp50']['tracks']:2d} ({s['kp50']['frame_pct']:.2f}%) kp100 {s['kp100']['tracks']:2d}"
          f" | rot25 {r['rot25']['tracks_axis']}/{r['rot25']['tracks_norm']} p95 {r['rot25']['med_p95_axis']:.2f} rot100 {r['rot100']['tracks_axis']}/{r['rot100']['tracks_norm']}"
          f" | load {l['min_p05']:.2f}-{l['max_p95']:.2f} (abs {l['min']:.2f}-{l['max']:.2f})")

if __name__ == "__main__":
    mode = sys.argv[3] if len(sys.argv) > 3 else "sweep"
    if mode == "sweep":
        line("baseline (win9 v.05 mh1.243)", *run())
        for w in (5, 7, 11, 13): line(f"SG window {w}", *run(win=w))
        for vt in (0.03, 0.08): line(f"speed thr {vt}", *run(vth=vt))
        for wt in (20, 45): line(f"ang thr {wt} deg/s", *run(wth=wt))
        line("speed .03 + ang 20", *run(vth=0.03, wth=20))
        line("speed .08 + ang 45", *run(vth=0.08, wth=45))
        for mh in (0.87, 1.616): line(f"hand mass {mh}", *run(mh=mh))
        line("kd fixed 6 in sweep", *run(kd_mode=6.0))
        for c in (0.18, 0.15): line(f"effective clip {c}", *run(clip=c))
        line("weight only when lifted >1cm", *run(lift_gate=True))
        line("win7 + v.03 + mh1.616 (worst?)", *run(win=7, vth=0.03, mh=1.616))
        line("win11 + v.08 + mh0.87 (best?)", *run(win=11, vth=0.08, mh=0.87))
