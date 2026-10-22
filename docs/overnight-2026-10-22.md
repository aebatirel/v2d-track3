# Overnight 2026-10-21 → 22: how robust is contact-anchored retargeting, and what limits the hard episodes?

Owner's ask (01:00 TRT): redo the four validation episodes (ep12, ep27 good; ep18, ep24 bad) with the new approach,
test as much as possible, find what works and what does not, fix it, have a reliable setup by morning. Budget: the
$50 top-up (credit $52.69 at 01:00).

All scores: **registered ADD-AUC with our own meshes vs mocap (the kit's scorer, `pipeline/score_registered.py`), mean
± std (min–max) over 6 official evaluations (`reset_mode=explicit`, 1 world) of one trained policy.** The base of each
episode is the policy published on 2026-10-21, re-evaluated 6 times. Rows: `results/e2e/overnight_20261022/` (table:
`table.md`, tool `tools/ab_table.py`); commands and run ids: `docs/work-log.md` (2026-10-22 entries).

## 1. Results (6 evaluations each; seed 42 unless noted)

| | ep12 (easy) | ep27 (easy) | ep18 (hard) | ep24 (hard) |
|---|---|---|---|---|
| base (published policy) | 0.725 ± 0.067 | **0.942 ± 0.017** | 0.345 ± 0.046 | 0.297 ± 0.055 |
| k: contact retargeting | **0.790 ± 0.023** | 0.911 ± 0.017 | 0.319 ± 0.042; s43 0.361 ± 0.038 | 0.307 ± 0.002; s43 0.306 ± 0.018 |
| k + keypoints 0.15 m (kq) | | | **0.381 ± 0.012** | 0.313 ± 0.011 |
| k + start fix (ki) | 0.763 ± 0.025 | 0.897 ± 0.013 | 0.342 ± 0.096 | **0.318 ± 0.001** |
| k + rest settle (height only) + start fix (kri) | | | 0.368 ± 0.069 | 0.312 ± 0.003 |
| start fix alone (i) | | | 0.351 ± 0.056 | |
| primitive-collision hand (p) | | | 0.377 ± 0.021 | 0.282 ± 0.023 |
| k + rest settle + stable pose (kr) | pending (box L) | | | |
| kri + flattened sweeper, stable pose (kfi) | | | pending (box K) | |

Four-episode mean: base 0.577; retargeting 0.587 (two-seed means on the hard episodes). **No variant tonight lifts
the hard episodes above ~0.38 (ep18) / ~0.32 (ep24); the leaders' mean is 0.83–0.85.**

## 2. What we learned (measured)

1. **Contact retargeting** makes the reference physically clean (simulator: ep24 frames with a hand > 2 mm inside
   something 242 → 62 of 275; ep18 ~77 % → 11 %) and makes rollouts **consistent** (spread ep12 ±0.067 → ±0.023, ep24
   ±0.055 → ±0.002–0.018), but the mean moves little: ep12 +0.066, ep24 +0.01, ep18 ≈ 0, ep27 −0.031. Not a
   universal win. Our no-ground-truth `sim_vs_ref` (6-evaluation means) ranks base vs retargeting like the true score
   on all four episodes (one tie, ep24 s42), so
   choosing per episode by it (what `auto_ep.sh` already does) captures the gains without the losses.
2. **Noise:** evaluations of one policy spread ±0.01–0.10; two seeds differ by ≈ 0.04. The published single-rollout
   scores of 2026-10-21 were low draws (ep24 0.232 vs a 0.297 mean). Decisions need ≥ 2 seeds × 6 evaluations.
3. **ep18's real cause: our sweeper cannot stand.** In the first frames no hand is near it, yet it tips by f5 in every
   rollout. Our reconstruction's underside is rounded (the table hides it): at our frame-0 pose its footprint is 0.3 cm²
   with the centre of mass 3 cm outside; no stable upright pose exists for our mesh. With the object assist off (as in
   the official evaluation) it falls in 4–5 steps. (Diagnostic only: the public scan stands on a flat 11.7 cm² base.)
   Fix, from our own data only: `pipeline/flatten_base.py` (flat underside along our perceived up) →
   `meshes/library_v3`, plus `contact_retarget --rest_settle 1` turning resting objects onto their nearest stable pose.
   CPU, assist off, no policy: sweeper 17.6° by step 4 → ≤ 0.7° for 9 steps. GPU: pending (box K).
4. **Objects float above the table in our references** (ep24 boards 2–4 cm, ep12 and ep27 dish rack ~1 cm). With the
   assist off they drop at the start; ep12's cup tips 23° within 4 steps. `--rest_settle 1` seats them (ep12 cup
   0.4 cm / 3.5°, all steps; ep27 rack drop 1.05 → 0.03 cm). GPU on ep12: pending (box L). On ep24 it did not change
   the score (0.312 vs 0.318).
5. **ep24's ceiling is learning, not geometry:** every variant tracks the slide (board 1 within 1–2 cm to f68) and fails
   where a board is lifted and stood on its edge (board 1 ~f102, board 2 ~f117). Retargeting, rest settling, keypoint
   scale and the start fix all land at 0.306–0.318.
6. **Train/eval start mismatch** (FlashCHORD's Sharpa reset always opens the fingers and holds the frame with full
   object assist for 20 steps; the official evaluation starts exact and unassisted): patched (`FC_IMMEDIATE_FIRST_FRAME`,
   modelled on NVIDIA's humanoid recipe). It is real but not what limits these episodes: no effect on ep18, within
   noise elsewhere.
7. **Tooling correction:** my CPU probes ran with the object assist at 1.0 (a fresh training env starts at the first
   curriculum stage), which hid the falling sweeper. Probes now default to 0 like the evaluation.
8. Keypoint scale: best and tightest on both hard episodes but within noise. Primitive hand: +0.03 on ep18, −0.015 on
   ep24. Max-Q GPUs train at 76 % of the WS speed (worth it below ≈ $1.71/h).

## 3. Recommendation

(final after boxes K and L) Draft:
- **Pipeline for the submission:** build both references (E2S and contact-retargeted), train both, keep the better
  by `sim_vs_ref` (no ground truth; same ranking as the true score on all four episodes, one tie). Cost ≈ 2
  trainings per episode; use the mean of several evaluations, a single one is noisy.
- **Add a physical-feasibility gate to every reference** (CPU, minutes): assist-off drop test from frame 0 and at rest
  segments; settle floating/unstable resting objects (`--rest_settle 1`), flatten undersides of objects seen standing.
  It found three of four episodes with objects that fall or drop with no hand near them.
- Not adopting: keypoint scale, primitive hand, start fix (no measurable effect; patches stay opt-in).
- **Hard-episode ceiling** (ep24 lift-and-stand, ep18 tool use): needs a different way to produce feasible hand motion
  (physics search / sampling MPC as in Do as I Do), not more reference cleaning.

## 4. Spend and runs

(final after boxes K and L)
