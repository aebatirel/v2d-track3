# PREREG T2: revolution-axis tilt prior (written and pushed BEFORE any T2 transform or score)

Session physics-perception, 1 Nov 2026 ~20:55 UTC. CPU, $0. Public episodes only. Follows T1 (`results_T1.json`:
P1 +0.00156, 13 / 0, below the +0.003 gate).

## Evidence before this test (diagnostics; mocap read only there)
- D1: the stable facet of our mesh is a ~2 deg tilt prior. T1's fusion with it gives +0.0016.
- D2 (`diag/d2_axis.json`, `scripts/d2_axis.py`): physics prior "a surface of revolution resting upright on a flat
  table has a vertical axis". Axis fitted to OUR mesh by the line-complex method (normals meet the axis), IRLS
  keep 60 %. Fit rms: pot 0.85 mm, lid 0.08, beige cup 0.45, blue cup 3.25; pitcher 14.6 mm (handle / spout, failed:
  the 4 mm rms gate excludes it). Tilt error of 17 gated objects (8 anchors) vs the truth, W = 0 / 0.5 / 0.75 / 1:
  all 2.47 / 1.52 / 1.12 / 0.89 deg; anchors 1.66 / 1.18 / 1.04 / 1.01 deg. Facet prior on the same objects: best
  1.59 (all) / 1.46 (anchors).
- Disclosure: D2 is in-sample. W_AXIS = 0.75 is fixed now from the D1 / D2 error levels (inverse variance with
  tracker ~2.2 deg, axis ~1.0 deg gives ~0.8; 0.75 rounds toward the tracker). REV_RMS_MM = 4 was set after seeing
  the fits (pitcher 14.6 vs blue cup 3.25). Gates (hand, gap, match <= 6 deg) are unchanged from T1.

## Transform: `scripts/pp_tilt.py` with PP_PRIOR=axis (T1's default path verified byte-identical after the edit)
Per gated object: prior = +-revolution axis (W_AXIS 0.75) if fit rms <= 4 mm, else the T1 facet prior (W 0.5).
One body-frame correction for the whole track, pivot about the surface centroid, no translation.

## Arms
| arm | prior | objects | role |
|---|---|---|---|
| **Q1** | axis (W 0.75) else facet (W 0.5) | every gated object | **primary, gated** |
| Q2 | same | scorer anchor only | secondary, gated on its own |
| R2 | axis W 1.0 else facet W 0.5 | every gated object | report only |

## Gate (unchanged from T1), against `runs/before`
mean ΔAUC >= +0.003 over the 20 public episodes; no episode < −0.010; mean ΔMPPE <= 0 and mean ΔRPE <= 0. Scored
once each. Falsifier: Q1 mean ΔAUC <= P2's +0.00132 (the axis prior's tilt gain does not reach the score).

## Expected [E]
Q1 removes ~55 % of the tilt of 17 objects (2.47 -> 1.12 deg) plus T1's facet part on the rest: +0.003 to +0.006 [E].
