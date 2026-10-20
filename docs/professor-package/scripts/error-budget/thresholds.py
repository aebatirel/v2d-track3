"""SP-SR / MP-SR breakpoints: fine sweeps of each error family + extra realism cases."""
import json
import numpy as np
from common import *
import budget as B
from budget import run, scale, anchor_rot, anchor_trans, lag, jitter, drift, body_offset, EPS, onset, first_motion_end, most_moving


def cam_rot_drift(deg, pivot_m=0.6):
    """World-frame rotational drift about a pivot (camera) pivot_m from slot-0 start."""
    def f(p, rng, e):
        o = p.copy(); T, N, _ = p.shape; ramp = np.linspace(0, 1, T)
        ax = B.rand_axis(rng); c = p[0, 0, :3] + B.rand_axis(rng) * pivot_m
        qd = qaxang(np.repeat(ax[None], T, 0), np.radians(deg) * ramp)
        for j in range(N):
            o[:, j, :3] = c + qrot(qd, p[:, j, :3] - c); o[:, j, 3:] = qmul(qd, p[:, j, 3:])
        return o
    return f


FAM = {
    "anchor/global trans (cm)": (lambda v: anchor_trans(v), [1, 2, 2.5, 3, 3.5, 4, 6, 8, 10, 12, 15], 8),
    "pos jitter (cm/axis)": (lambda v: jitter(v), [0.5, 1, 1.25, 1.5, 1.75, 2, 3, 4, 5, 6, 8], 4),
    "scale (%)": (lambda v: scale(v / 100), [5, 10, 15, 20, 25, 30, 40, 60, 80, 100], 1),
    "slot0 init rot (deg)": (lambda v: anchor_rot(v), [5, 8, 10, 12, 15, 20, 25, 30, 40, 60, 90], 8),
    "slot0 body rot (deg)": (lambda v: body_offset(rot_deg=v, slot=0), [5, 10, 15, 20, 25, 30, 40, 60, 90], 8),
    "slot1 body rot (deg) [multi]": (lambda v: body_offset(rot_deg=v), [15, 20, 25, 28, 30, 32, 35, 45, 60, 90, 180], 8),
    "slot1 body trans (cm) [multi]": (lambda v: body_offset(trans_cm=v), [1, 2, 2.5, 2.9, 3.1, 4, 6, 10, 15], 8),
    "lag (frames)": (lambda v: lag(int(v)), [3, 5, 8, 10, 15, 20, 30, 40], 1),
    "drift common (cm end)": (lambda v: drift(v), [3, 5, 6, 7, 8, 10, 15, 20, 30], 8),
    "cam rot drift, pivot 0.6 m (deg end)": (lambda v: cam_rot_drift(v), [1, 2, 3, 5, 8, 10, 15, 20], 8),
}

if __name__ == "__main__":
    out = {}
    for fam, (mk, grid, rep) in FAM.items():
        mo = "[multi]" in fam
        print(f"\n== {fam}" + ("  (13 multi-object eps)" if mo else "  (20 eps)"))
        print(f"{'val':>6} {'AUC':>6} {'SP-SR':>6} {'MP-SR':>6} {'RPE':>6} {'MPPE':>6}")
        rows = []
        for v in grid:
            m, per = run(mk(v), rep, mo)
            rows.append(dict(v=v, **m))
            print(f"{v:6g} {m['AUC']:6.3f} {m['SPSR']:6.2f} {m['MPSR']:6.2f} {m['RPE']:6.2f} {m['MPPE']:6.2f}", flush=True)
        out[fam] = rows
    # freeze fractions for the dropped-object variants
    fr = []
    for e in EPS:
        p = e["pose"]; j = most_moving(p); T = len(p); dt = np.median(np.diff(e["ts"]))
        o = onset(p, j); a = first_motion_end(p, j, dt)
        fr.append(((T - o) / T if o is not None else 0, (T - a) / T if a is not None else 0))
    fr = np.array(fr)
    print(f"\nfrozen fraction of frames, most-moving object: @onset mean {fr[:,0].mean():.2f}, after-1st-motion mean {fr[:,1].mean():.2f}")
    out["frozen_fraction"] = fr.tolist()
    json.dump(out, open("thresholds.json", "w"), indent=1)
