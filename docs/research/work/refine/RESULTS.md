# Refine stage (`pipeline/refine.py`) on the 20 public episodes, 2026-10-30

- **Machine:** Claude cloud VM (CPU), $0.
- **Inputs:** the 25 Oct current-recipe perception tracks and hands from the HF store (`README_inputs.md`).
- **Scoring:** `pipeline/score_registered.py` against public mocap, with our meshes (lib) and the scan.
- **Baseline reproduced exactly:** lib 0.8921 (0.9369 without ep23), scan 0.9084.
- **Gates:** pre-registered in the session plan before any result: mean lib ≥ base + 0.005; no episode drop > 0.02 (S3 has its own rule); no new flips.
- **Raw results:** `results/gates.json`, `results/step_summary.json`, `results/frame0_check.json`.
- **Evaluation scripts:** `evalscripts/`, `score_arm.sh`, `compare.py`.

| Arm | Δ lib mean | better / worse | drops > 0.02 | Δ scan | Verdict |
|---|---|---|---|---|---|
| S1 support-gated snap | −0.0077 | 6 / 8 | 12, 13, 21, 22 | −0.0002 | **rejected** |
| **S2 0.545-frame advance** | **+0.0061** | **17 / 3** | none | **+0.0053** | **adopted** |
| S2, frame 0 held | +0.0030 | 20 / 0 | none | +0.0026 | below the +0.005 gate (kept as a fallback) |
| S3 tilt-to-plane anchor | −0.0013 | 10 / 8 | 24, 39, 40 | −0.0038 | **rejected** |
| S4 pre-contact hold | +0.0003 | 4 / 1 | none | +0.0004 | no effect, not adopted |

## Readings
- **S1 and S3 were falsified on public data.** The mocap-oracle versions in refcheck showed gains, but the GT-free gated
  versions do not reproduce them. S1 hurts the cup-into-rack and pitcher episodes; S3 hurts the dust-pan and board
  episodes.
- **S2 is the only adopted step.** It compensates the measured tracker/sync lag (refcheck R6). It reaches the
  leaderboard only through rebuilt references and retrained policies; the measured transfer is ≈ 0.74 of a
  sim_vs_ref gain.
- **Not done:** the adversarial verify stage was cut by a usage limit. Its two checks for S2 were done by hand: no GT
  read (`assert_inference_input`), and `world_T_cam` and the keys unchanged (`gates.json`).
