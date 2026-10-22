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
| k + rest settle + stable pose (kr) | 0.740 ± 0.032 | | | |
| **kri + flattened sweeper, stable pose (kfi)** | | | **0.715 ± 0.240; 5 of 6 rollouts 0.79–0.84, SP/MP 1** | |

Four-episode mean: base 0.577; retargeting 0.587 (two-seed means on the hard episodes). **ep18 rose from 0.345 to
0.715 (median 0.82) once our sweeper could stand; ep24 stays at ~0.32; the leaders' mean is 0.83–0.85.**

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
   CPU, assist off, no policy: sweeper 17.6° by step 4 → ≤ 0.7° for 9 steps. **GPU (box K): ep18 0.345 → 0.715
   mean, 5 of 6 rollouts 0.79–0.84 with SP and MP success** (one rollout drops the sweeper at f88).
4. **Objects float above the table in our references** (ep24 boards 2–4 cm, ep12 and ep27 dish rack ~1 cm). With the
   assist off they drop at the start; ep12's cup tips 23° within 4 steps. `--rest_settle 1` seats them (ep12 cup
   0.4 cm / 3.5°, all steps; ep27 rack drop 1.05 → 0.03 cm). **But it does not raise the score where no object
   falls over by itself:** ep12 kr 0.740 ± 0.032 (0.671–0.762) vs k 0.790 ± 0.023 (one seed, −0.05; `sim_vs_ref`
   ranks them the same way, 0.763 vs 0.791); ep24 0.312 vs 0.318. It paid off on ep18 only together with a sweeper
   that can stand. So the drop-test flag alone is not a rule to apply it: keep it as a candidate chosen by `sim_vs_ref`.
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

- **Pipeline for the submission:** build candidate references (E2S; contact-retargeted; retargeted + rest settling),
  train each, keep the best by `sim_vs_ref` (no ground truth; it ranked the variants like the true score on all
  four episodes tonight, one tie). Cost ≈ 2–3 trainings per episode; use the mean of several evaluations, a single
  one is noisy.
- **Physical-feasibility gate on every reference** (CPU, minutes): assist-off drop test from frame 0 and at rest
  segments; it found three of four episodes with objects that drop or fall with no hand near them. Where an object
  cannot stand on its own (no stable pose near its perceived resting pose) the mesh must be fixed (ep18: 0.345 →
  0.715). Floating alone (ep12) is not worth a fix by itself (kr −0.05 on ep12).
- **Mesh validity is the main lever found tonight**, and per-object hand patches (flattening one object along one
  episode's up) do not scale to the 20 evaluation episodes. Owner's direction (09:00): build the meshes from how the
  objects interact (no overlap at co-located frames, swept volumes are empty, resting objects touch the table with a
  flat patch, fingertip contacts lie on the surface). Research and design for that: in progress (two research
  workflows, plan to follow).
- Not adopting: keypoint scale, primitive hand, start fix (no measurable effect; patches stay opt-in).
- **Hard-episode ceiling** (ep24 stand-up, ep18 tool use): ep18 was mostly the mesh; ep24 needs the boards' slots and
  standing edges first (`meshes/library_v4` is a hand patch for the edges, no slots yet), then possibly a different
  way to produce feasible hand motion (physics search / sampling MPC as in Do as I Do).

## 4. Spend and runs

**Vast credit $52.69 at 01:00 TRT → $2.93 at 09:15 TRT: $49.76 spent overnight**, 13 RTX PRO 6000 boxes (WS, S and
Max-Q, $1.30–1.91/h), all self-destroyed; none running. Per-box instance, $/h, job and commit: the box tables in
`docs/work-log.md` (2026-10-22 entries). Run ids and what each measured:

| run id | variant(s) | result |
|---|---|---|
| `20261022-r1a-65c5a52` (A) | ep24 k s42, ep12 k s42 + base re-evaluations | ep24 0.307, ep12 0.790; base 0.297 / 0.725 |
| `20261022-r1b-65c5a52` (B) | ep18 k s42, ep27 k s42 + base re-evaluations | ep18 0.319, ep27 0.911; base 0.345 / 0.942 |
| `20261022-r1c-65c5a52` (C) | seed 43 | lost to the `hard_ab.sh` copy bug (≈ $0.5) |
| `20261022-r1c2-d4ac331` (C′) | ep24 k s43, ep18 k s43 | 0.306, 0.361 |
| `20261022-r2p-d4ac331` (D) | primitive hand ep18, ep24 | 0.377, 0.282 |
| `20261022-r2q-d4ac331` (E) | keypoints 0.15 m ep18, ep24 | 0.381, 0.313 |
| `20261022-r3ki-342d72c` (F) | start fix ep24, ep18 | 0.318, 0.342 |
| `20261022-r3kpi-342d72c` (G) | primitive + start fix | stopped while training (≈ $1.5) |
| `20261022-r3kie-342d72c` (H) | start fix ep12, ep27 | 0.763, 0.897 |
| `20261022-r3kri-764afba` (I) | rest settle (height) + start fix ep24, ep18 | 0.312, 0.368 |
| `20261022-r3i-1fc3dc9` (J) | start fix alone ep18 | 0.351 |
| `20261022-r4kfi-a30ac72` (K) | flattened sweeper + stable-pose settling ep18 | **0.715** |
| `20261022-r4kr-28e4883` (L) | rest settle + stable pose ep12 | 0.740 |
