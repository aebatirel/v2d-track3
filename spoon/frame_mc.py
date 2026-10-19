#!/usr/bin/env python3
"""Monte Carlo of the R1 frame bits over the template's parameter uncertainty (CPU, ~2 min for N=300).

Each sample perturbs the template parameters within the measurement brackets of notes 13/20 (table below), rebuilds the
watertight template (markers unioned) and applies R1. Reports the share of samples whose skew along the middle axis
points to M2 (frame B under the exact mid-axis rule), the mean noisy-rule P(B) (organisers' sign estimated from n surface
points, n from the note-13 c_noisy posterior), the x-rule share, and z flips. Writes frame_mc.json next to this file.
This is a model of OUR uncertainty about the physical spoon; it says nothing about how the organisers' scan was made
(markers in or out, decimation, sign-rule noise beyond the n model).
Usage: python frame_mc.py [N] [seed]
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spoon_template as st  # noqa: E402

# (kind, a, b): 'n' = normal(mean a, sd b); 'u' = uniform(a, b). Metres unless noted; m_* entries are note-20 mm priors
# whose MEAN is resampled (their sd stays) before the template's weighted least squares with the triangle.
SPEC = {
    "bowl_bend": ("n", 0.0013, 0.0008),          # note 20 re-run +1.3 +- 0.8 mm
    "bowl_length": ("n", 0.095, 0.004),
    "bowl_width": ("n", 0.052, 0.002),
    "bowl_widest_frac": ("u", 0.42, 0.58),
    "bowl_depth": ("u", 0.006, 0.014),           # [H] ~1 cm
    "bowl_thickness": ("u", 0.004, 0.006),       # note 13: 4-6 mm
    "rim_height": ("u", 0.0, 0.004),             # note 20: 0-4 mm
    "bowl_pitch_deg": ("n", 0.0, 2.0),
    "neck_width": ("n", 0.016, 0.001),
    "handle_d_start": ("n", 0.0188, 0.0006),
    "handle_d_max": ("n", 0.0213, 0.0006),
    "handle_d_end": ("n", 0.0188, 0.0006),
    "m_lat1": ("n", 18.9, 0.6), "m_up1": ("n", 6.0, 1.5),
    "m_lat2": ("n", 15.5, 0.8), "m_up2": ("n", 10.0, 2.0),
    "m_lat3": ("n", 1.9, 1.2), "m_up3": ("n", 11.0, 1.5),
    "m_station1": ("n", 120.5, 3.0), "m_dz12": ("n", 41.5, 1.5),
}


def draw(rng):
    u = {}
    for k, (kind, a, b) in SPEC.items():
        v = rng.normal(a, b) if kind == "n" else rng.uniform(a, b)
        u[k] = [float(v), st.DEFAULTS[k][1]] if k.startswith("m_") else float(v)
    return u


def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(N):
        u = draw(rng)
        try:
            b = st.build_spoon(st.resolve_params(u))
            fr = st.frame_report(b["V"], b["F"], b["markers"])
            rows.append(dict(i=i, skew_x=fr["skew_toward_concave_x"], skew_y=fr["skew_toward_M2_y"], skew_z=fr["skew_toward_handle_z"],
                             label_mid=fr["mid"]["label"], label_x=fr["x"]["label"],
                             P_B_noisy=fr["noisy_mid_axis"].get("P_B_noisy_posterior"), params=u))
        except Exception as e:
            rows.append(dict(i=i, error=f"{type(e).__name__}: {e}", params=u))
        if i % 50 == 0:
            print(i, rows[-1].get("skew_y"), rows[-1].get("label_mid"), rows[-1].get("error", ""), flush=True)
    ok = [r for r in rows if "error" not in r]
    sy = np.array([r["skew_y"] for r in ok]); sx = np.array([r["skew_x"] for r in ok]); sz = np.array([r["skew_z"] for r in ok])
    pb = np.array([r["P_B_noisy"] for r in ok], float)
    # regression of skew_y on the main drivers (per unit: mm, deg)
    X = np.array([[1.0, r["params"]["bowl_bend"] * 1e3, r["params"]["m_lat1"][0] - r["params"]["m_lat2"][0], r["params"]["m_up1"][0],
                   r["params"]["m_up2"][0], r["params"]["m_lat3"][0]] for r in ok])
    coef, *_ = np.linalg.lstsq(X, sy, rcond=None)
    resid = sy - X @ coef
    summ = dict(
        N=N, seed=seed, built=len(ok), errors=len(rows) - len(ok),
        P_skew_y_toward_M2=float((sy > 0).mean()), skew_y_mean=float(sy.mean()), skew_y_sd=float(sy.std()),
        skew_y_p10_p90=[float(np.percentile(sy, 10)), float(np.percentile(sy, 90))],
        P_B_noisy_mid_axis_mean=float(np.nanmean(pb)),
        share_B_exact_mid_rule=float(np.mean([r["label_mid"] == "B" for r in ok])),
        share_B_x_rule=float(np.mean([r["label_x"] == "B" for r in ok])),
        P_skew_x_toward_concave=float((sx > 0).mean()), skew_x_mean=float(sx.mean()), skew_x_sd=float(sx.std()),
        z_bowl_to_handle=float((sz > 0).mean()), skew_z_min=float(sz.min()),
        skew_y_regression=dict(terms=["const", "bend_mm", "lat1_minus_lat2_mm", "up1_mm", "up2_mm", "lat3_mm"],
                               coef=[round(float(c), 5) for c in coef], r2=float(1 - resid.var() / sy.var()), resid_sd=float(resid.std())),
        spec=SPEC,
    )
    print(json.dumps({k: v for k, v in summ.items() if k != "spec"}, indent=1))
    with open(os.path.join(HERE, "frame_mc.json"), "w") as f:
        json.dump(dict(summary=summ, rows=rows), f, indent=1)


if __name__ == "__main__":
    main()
