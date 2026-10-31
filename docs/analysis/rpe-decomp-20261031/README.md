# What drives our Track 3 RPE and MPPE (and AUC)? Public-episode decomposition, 31 Oct 2026

CPU only (this cloud VM, 4 cores), $0. Public episodes only; nothing was run on eval episodes. Labels: [M] measured
here, [E] estimate, [H] hypothesis. Ground truth (public mocap, the `pose` field of `observation.objects`, the public
scans) is read only by scoring and diagnostics. The two pre-registered candidates (K1, K2) transform our tracks from
inference-side inputs only (`cand.py`, `rest_hold`).

## Answer first

1. **On the leaderboard, RPE and MPPE come from rollout failures, not from the reference [M, public twins].**
   - Per draw, the reference adds 1.2–2.1 cm RPE. A successful draw scores 1.4–3.5 cm in total.
   - A failed draw scores 10–77 cm, because the metric is an unbounded mean in cm:
     - ep2 and ep11 failures: 10–19 cm, about the do-nothing floor (15–17 cm there); ep11's objects are never moved;
     - a cup flung off: 20–77 cm on ep13.
   - Over the 7 P-arm cells (the eval recipe; 70 official draws), mean RPE is 13.7 cm, of which the reference is
     1.4 cm (≈ 10 %). Mean MPPE is 8.4 cm, of which the reference is 1.3 cm (≈ 16 %).
   - Total RPE and the GT-free sim-vs-our-reference RPE agree draw by draw: r = 0.9998 over the 70 draws.
2. **This explains our RPE/MPPE ratio [E].**
   - RPE counts the full relative displacement when one object of a pair fails. MPPE averages it over both objects.
     Single-object episodes count 0 in RPE but not in MPPE.
   - So failures in two-object episodes push RPE/MPPE above 1. Ours is 1.35; the top six are at 0.88–1.03.
   - One benign failure (≈ 15 cm) in one of the 20 eval episodes adds ≈ 0.75 cm to the board RPE; a flung object
     adds 1–4 cm.
   - With no failures, our eval RPE would be ≈ 16 × (2–3 cm) / 20 ≈ 1.6–2.4 cm [E], close to the top six (1.10–1.73).
3. **At the reference level, our P_o tracks are already near the top teams' leaderboard values [M].**
   - Over the 20 public episodes (kit convention): RPE 1.66, MPPE 1.90, AUC 0.890.
   - Without ep23, a board identity swap: RPE 1.00, MPPE 1.18, AUC 0.935.
   - ep23 alone carries 43 % of the summed RPE. The worst 3 episodes carry 61 % of RPE, 53 % of MPPE and 61 % of the
     AUC loss.
4. **Within the reference, GT substitution (diagnostic only) shows constant offsets dominate MPPE/AUC [M]:**
   - (b) one constant body offset per object: MPPE −0.60, AUC +0.050 (19/20 better), RPE −0.22.
   - (a0) the frame-0 scene alignment replaced by the best whole-track fit: MPPE −0.71, AUC +0.040.
     - The misalignment is mostly tilt: 0.4–5° on most episodes. ep31 is 10.5°, of which 7.5° tilt and 7.3° yaw
       [M, `tiltcheck`].
     - RPE is invariant to it by construction.
   - RPE has no single dominant type. Without ep23 it splits about evenly: constant offset −0.22 of 1.00, rest-phase
     error −0.24, and ≈ 0.77 varying.
     - The exception is ep18: the sweeper (slot 0) at ≈ 10° rotation error × a 22 cm lever while moving, 4.9 cm.
5. **Both pre-registered reference-level candidates FAIL their rule [M].**
   - K1 rest-hold: ΔRPE +0.005, ΔAUC +0.001. K2 initial-hold: ΔRPE +0.000, ΔAUC +0.001.
   - Both are a GT-free way to remove jitter. The gain the oracle shows sits in rest-pose bias, which jitter removal
     cannot reach.
   - Post hoc, not pre-registered: choosing among a checkpoint's official draws by the GT-free sim-vs-reference MPPE
     cuts total RPE 13.7 → 6.4 and MPPE 8.4 → 3.8 at AUC 0.829. Choosing by sim_vs_ref gives 9.2 / 6.1 / 0.827.
     This is a pack-time lever, not a retrain fix; see "What this hands on".

## The kit's definitions

Source: the participant kit `v2d_submission_kit.zip` (organiser URL in `pipeline/setup.sh`; KIT_MANIFEST evaluator
commit 8c778f9). The metric files are `metric_code/track_3/{RPE,MPPE,AUC}.py`; their sha256 are 3ec593c0…, 15d05004…
and 243f8009…. The three files are identical except for `_METRIC` (line 594). All line numbers below are `RPE.py`.
- **Scoring chain** (`_score_registered_track3`, 824–877):
  - The submitted mesh is registered to the host scan (`_register_object_body`, 444; seed `1_000_003*ep + 101*slot`,
    867).
  - Poses are converted to the scan anchor (`_convert_object_body`, 458).
  - The scene is aligned once per world at frame 0 (`_align_registered_scene`, 476–498, called at 875):
    - rotation from the first object without a symmetry axis (480–487); translation from slot 0 (495: `offset =
      reference[0, 0, 0, :3] - rotation @ achieved[0, world, 0, :3]`);
    - if every object has a symmetry axis, slot 0's axis and the direction to slot 1 instead (488–493).
  - `return float(np.mean(scores))` (877): a plain mean over episodes.
- **RPE** (`_symmetry_relative_position_cm`, 543–566; dispatched at 585–586):
  - For each pair (first < second), the second's position relative to the first, in the first's body frame:
    `la = R_a(first)^T (p_a(second) - p_a(first))`, `lr` likewise for the reference (549–552).
  - The error is `|la - lr|` (564).
    - If the first object has an axis (cups), `hypot(Δaxial, Δradial)` (558–562): spin ignored, tilt counted.
    - If the first object is the lid, the minimum over the 180° flip (554–557).
  - `return float(np.mean(errors) * 100) if errors else 0.0` (566): **a single-object episode scores 0**.
  - Consequences:
    - invariant to the scene alignment;
    - slot 0's orientation error multiplies the separation between the objects (the lever arm).
- **MPPE** (580–584): six keypoints at ±5 cm along the body axes (`_MPPE_KEYPOINT_RADIUS_M = 0.05`, 213; directions
  217–219).
  - `_symmetry_point_errors` (510) gives the mean keypoint distance per frame, minimised over the symmetry (cups: 360
    spin steps; lid: 2).
  - `return float(np.mean(errors) * 100)`: the mean over bodies, frames and worlds, in cm, unbounded.
- **AUC** (570–573, `_add_auc` 270–278): the share of frames with symmetric ADD below 1…9 cm, trapezoid, mean per body.
  It is bounded: a failed frame costs at most its share.
- Note: the organiser repo's flash_chord README (`robotic_grounding/flash_chord/README.md:176`, clone 7eb9721) describes
  an MPPE with a max across bodies per frame. The kit's Kaggle metric above takes the mean, and only the kit is scored.

## Table 1: P_o tracks vs mocap, kit convention (lib), 20 public episodes [M]

Our P_o tracks (`20261030-orcP1{a,b,c}-87fc869`, library_v3 templates), library_v3 submitted, the public scan as the
host stand-in. The AUC reproduces phase-1 `xstar_trk_Po.json` "lib" exactly (checked on ep2, 11, 31; all 20 recomputed).

| ep | objects | AUC | MPPE cm | RPE cm | ep | objects | AUC | MPPE cm | RPE cm |
|---|---|---|---|---|---|---|---|---|---|
| 0 | pot, lid | 0.962 | 1.07 | 1.38 | 24 | boards | 0.812 | 2.36 | 0.98 |
| 2 | pot, lid | 0.987 | 0.71 | 1.44 | 26 | rack, pot | 0.972 | 0.84 | 1.29 |
| 11 | blue cup, beige cup | 0.898 | 1.64 | 1.74 | 27 | rack, pot | 0.961 | 0.79 | 1.16 |
| 12 | blue cup, rack | 0.966 | 0.96 | 1.14 | 31 | sweeper, rack | 0.800 | 2.03 | 1.91 |
| 13 | blue cup, rack | 0.960 | 1.07 | 1.39 | 39 | dust pan | 0.960 | 1.03 | 0 |
| 18 | sweeper, dust pan | 0.914 | 1.63 | **4.07** | 40 | dust pan | 0.957 | 0.90 | 0 |
| 21 | blue cup, pitcher | 0.833 | 2.15 | 1.25 | 41 | pot | 0.991 | 0.60 | 0 |
| 22 | blue cup, pitcher | 0.871 | 1.81 | 1.22 | 42 | pot | 0.990 | 0.59 | 0 |
| 23 | boards (identity swap) | **0.041** | **15.58** | **14.18** | 43 | pot | 0.948 | 1.05 | 0 |
| | | | | | 44 / 45 | pot | 0.997 / 0.980 | 0.47 / 0.72 | 0 / 0 |

- **Mean over 20** (RPE: single-object episodes count 0, as the kit does): AUC 0.8899, MPPE 1.900, RPE 1.658.
- **Without ep23:** 0.935, 1.18, 1.00.
- **Over the 13 multi-object episodes:** RPE 2.55; RPE/MPPE 1.02. Over 20: 0.87.
- **Worst 3:**
  - RPE: ep23, ep18, ep31 carry 61 % of the summed RPE (mean without them 0.76);
  - MPPE: ep23, ep24, ep21 carry 53 %;
  - AUC loss: ep23, ep31, ep24 carry 61 %.

## Table 2: ablations by GT substitution (diagnostics only), Δ vs base, means over 20 episodes [M, oracle]

**How substitutions are done.** Every substitution is made on the converted host-anchor poses in our world. The truth
is put into our world by one of two maps:
- **W_kit:** the kit's own frame-0 alignment. This is the primary map for c, c_rest, d and cd (rows marked k).
- **W\*:** a robust whole-track rigid fit onto mocap (`rdlib.world_fit`).

The kit's alignment and metrics then run unchanged.

| variant | what is replaced by truth | ΔRPE (20) [13 multi] | ΔMPPE | ΔAUC | AUC better / worse |
|---|---|---|---|---|---|
| (a) a0 | scene alignment from W\* instead of the frame-0 anchor pose | 0.000 [0.000] (invariant) | **−0.712** | **+0.040** | 17 / 2 |
| (a) a_rot | rotation anchor's frame-0 orientation (via W\*), our deltas kept | 0.000 | −0.346 | +0.026 | 15 / 4 |
| (a) a | + slot 0's frame-0 position (via W\*) | +0.341 ⚠ | −0.599 | +0.036 | 17 / 2 |
| **(b)** | one constant body offset per (episode, object), X\*_trk (phase-1 fits; an AUC upper bound) | **−0.215 [−0.331]** | −0.597 | **+0.050** | 19 / 0 |
| (c) c_k | objects no hand touches (true travel < 2 cm, < 5°: 6 objects in 6 eps) held at truth | −0.051 [−0.078] | −0.161 | +0.012 | 4 / 0 |
| c_rest_k | every object at truth in the frames where mocap says it is still | −0.117 [−0.181] | −0.869 | +0.055 | 15 / 0 |
| (d) d_k | every object's frame-0 pose, our world-frame motion deltas kept | +0.051 [+0.079] | −0.302 | +0.024 | 11 / 1 |
| cd_k | c then d | −0.048 | −0.396 | +0.028 | 11 / 1 |
| c, c_rest, d, cd via W\* | same, truth mapped by W\* | −0.125, −0.423, +0.391 ⚠, +0.296 ⚠ | −0.12, −1.22, −0.56, −0.66 | +0.008, +0.073, +0.036, +0.040 | – |
| **(e) remainder** | left after (b) / after cd_k | RPE 1.44 / 1.61 (no ep23: 0.77 / 0.88) | MPPE 1.30 / 1.50 (0.55 / 0.83) | AUC 0.940 / 0.918 (0.988 / 0.961) | – |

Without ep23 (19 episodes) [M]:

| variant | RPE | MPPE | AUC |
|---|---|---|---|
| base | 1.00 | 1.18 | 0.935 |
| a0 | 1.00 | 0.69 | 0.979 |
| b | 0.77 | 0.55 | 0.988 |
| c_rest_k | 0.76 | 0.67 | 0.964 |
| d_k | 0.98 | 0.93 | 0.957 |
| cd_k | 0.88 | 0.83 | 0.961 |

Readings:
- **MPPE and AUC.** At the reference level they are driven by constant offsets.
  - The anchor object's frame-0 orientation, after the kit registration of our mesh, rotates the whole scene: (a0)
    +0.040 AUC. It is mostly tilt (ep31: half yaw) [M].
  - Per-object body offsets: (b) +0.050.
- **This is not frame-0 noise.** A multi-frame frame-0 estimate does not help:
  - A-f0 earlier: +0.001;
  - K2 here: +0.001;
  - refine S4, a pre-contact hold: +0.0003.
- **It is a constant body or registration bias.** The refine stage's GT-free tilt-to-plane anchor (S3) was already
  rejected (−0.0013, `docs/research/work/refine/RESULTS.md`).
- ⚠ **The W\* versions of a, d and cd make mean RPE worse** (d: 9 better / 4 worse of 13, but ep23 +7.6 and ep24
  +2.3 cm). A whole-track world fit misplaces
  frame-0 truth when our VO world is not rigidly tied to mocap over the episode [H]. W\* differs from the kit's map by
  0.4–5° (10.5° on ep31). Use the kit-world rows for RPE.
- **RPE anatomy (`anatomy_Po.json`).** RPE is similar in "both still" and "something moving" frames
  (≈ 0.8–2.0 cm; moving frames typically 0.1–0.7 cm higher).
  - The exceptions are ep18 (sweeper moving 4.9 vs still 1.3) and ep23.
  - The slot-0 rotation × lever term and the translation term partly cancel on ep21/22/31: a world-consistent tilt
    leaves the relative vector right. So the RPE floor is a relative offset between objects, roughly constant over
    time.

## Table 3: rollout level, reference error vs policy error [M]

The kit chain, lib convention, 10 official draws per cell.
- **Data:** orcB `20261030-orcB-38234d1` (seed 42, grasp lock; P = our reference, O = mocap reference) and the mass
  check control arm `20261031-mass-2ed46ea` (mass0 = our 0.3 kg recipe, seeds 42 and 43).
- **Columns:**
  - reference: the reference parquet vs mocap;
  - total: sim vs mocap (what the board scores);
  - policy: sim vs our reference, GT-free (library_v3 as host, identity registration).

| cell | reference RPE / MPPE / AUC | total (mean of 10) | policy (mean of 10) | total RPE per draw |
|---|---|---|---|---|
| P ep11 | 1.66 / 1.63 / 0.896 | **14.57 / 7.82 / 0.595** | 14.58 / 8.34 / 0.534 | 14.5–14.7 (objects never moved: do-nothing floor 14.55) |
| P ep13 | 1.24 / 1.21 / 0.940 | **52.15 / 32.50 / 0.543** | 53.01 / 32.06 / 0.574 | 20.1–76.8 (cup flung; AUC 0.54 in every draw) |
| P ep12 s42 | 1.18 / 1.43 / 0.935 | 2.07 / 1.32 / 0.928 | 1.90 / 1.14 / 0.947 | 1.6–2.8 |
| P ep12 s43 | 1.18 / 1.43 / 0.935 | 2.18 / 1.42 / 0.920 | 1.97 / 1.10 / 0.950 | 1.4–3.5 |
| P ep31 | 2.07 / 2.13 / 0.822 | 2.81 / 2.29 / 0.783 | 3.44 / 2.84 / 0.723 | 2.3–3.4 |
| P ep2 s42 | 1.24 / 0.73 / 0.980 | **11.20 / 6.94 / 0.552** | 11.46 / 7.00 / 0.548 | bimodal: 1.8–2.9 (4 draws) or 12.9–18.9 (6) |
| P ep2 s43 | 1.24 / 0.73 / 0.980 | **10.90 / 6.53 / 0.581** | 11.04 / 6.58 / 0.579 | bimodal: 1.8–2.8 (3) or 10.1–18.4 (7) |
| O ep11 | 1.25 / 0.65 / 0.969 | 1.55 / 1.05 / 0.940 | 1.06 / 0.81 / 0.967 | 1.1–2.7 |
| O ep13 | 1.07 / 0.75 / 0.964 | 21.32 / 13.53 / 0.544 | 21.22 / 12.84 / 0.573 | 15.0–48.2 |
| O ep31 | 0.92 / 0.46 / 0.993 | 2.72 / 1.76 / 0.869 | 2.96 / 1.79 / 0.865 | 2.1–4.5 |

**Do-nothing floor [M, `floor_static.json`].** Every object is held at its true frame-0 pose. Mean over 20:
RPE 9.6 (multi-object episodes 7.6–29 cm), MPPE 9.3, AUC 0.45.
- A benign failure (nothing moved) costs about this much.
- A flung object costs 2–5× more in RPE/MPPE at the same AUC (ep13: AUC 0.543 in every draw, RPE 20–77).

## Candidates (pre-registered in `PREREG.md`, block 1, 15:46:46 UTC, before scoring) [M]

| candidate | ΔAUC | ΔRPE | ΔMPPE | AUC improved / worse (of 20) | worst ΔAUC | verdict |
|---|---|---|---|---|---|---|
| K1 rest-hold (no perceived hand within 4 cm and no non-free support → hold the run at its robust mean) | +0.0012 | +0.005 | −0.039 | 11 / 7 | −0.007 (ep24) | **FAIL** (rules 1, 2, 3) |
| K2 initial-hold (only the run from frame 0) | +0.0013 | +0.000 | −0.039 | 9 / 6 | −0.006 (ep40) | **FAIL** (rules 1, 2, 3) |

- The numbers without ep23 are the same.
- Both would have touched every eval episode, since every one starts at rest. Neither goes forward.
- **Disclosure.** After registering K2 I found that refine stage S4 (pre-contact hold) is close to it and was already
  "no effect" (+0.0003). K2 is a near-repeat, and its failure agrees with S4.
- **Reason both fail [M].** The oracle gain of rest phases (c_rest_k) comes from the rest-pose bias. Our rest jitter is
  small: the held runs deviate 0.1–0.8 cm from their mean on most objects.

**Post-hoc analysis (NOT pre-registered; data seen before the rule):** draw selection among a checkpoint's 10 official
draws, over the 7 P-arm cells.

| how the draw is chosen | total RPE | total MPPE | total AUC |
|---|---|---|---|
| expected value of one draw (mean) | 13.70 | 8.40 | 0.700 |
| max qa sim_vs_ref (AUC-like, GT-free) | 9.21 | 6.13 | 0.827 |
| **min policy MPPE (sim vs our reference, GT-free)** | **6.40** | **3.84** | 0.829 |

- The gain over sim_vs_ref selection comes almost entirely from ep13, where every draw has the same AUC but RPE spans
  20–77 cm.
- This is not a retrain fix, and drawing more and picking is the owner's call.
- Before any use it needs its own pre-registered test on fresh draws, for example the "Masses v2" rollouts (4 public
  episodes × 2 seeds × 10 draws).

## What this hands on (each item needs its own gate and the owner's go-ahead)

1. **The RPE/MPPE boards are failure boards [M].** For the combined retrain, the lever is fewer failures and
   gentler ones (objects left in place, not flung), not reference accuracy. Reference-level fixes (K1, K2, S3, S4, A-f0)
   move RPE by ≤ 0.01 cm.
2. **GT-free eval audit, not run here (instructions).** For each eval episode of the current pack, compute RPE and MPPE
   of sim vs our reference with `roll.py`'s policy path (no ground truth needed).
   - On public draws this matches the scored error to r = 0.9998.
   - It names the eval episodes that carry our 3.93 / 2.92. Expectation [E]: 2–4 failure episodes at 10–50 cm.
   - One is already visible without running anything. Eval 10's packed draw has sim_vs_ref 0.456
     (`docs/analysis/h5-20261029/h5_summary.json`). Its public twin, ep11 P, has 0.52 and scores RPE 14.6 / MPPE 7.8
     with the objects never moved. So eval 10 alone is plausibly ≈ 0.7 cm of the board RPE and ≈ 0.4 cm of MPPE [E].
   - The other 15 multi-object evals would then average ≈ 4 cm RPE, above our public successes (2–3 cm) [E]. Either
     more failures or eval-only reference error (spoon) is hidden there; the audit above tells which.
3. **Retrain-side hypotheses, untested here:**
   - **[H-sel] Checkpoint choice.** Choose the checkpoint by sim_vs_ref with a penalty on policy MPPE (or on the max
     object displacement from the reference). This lowers LB RPE/MPPE at equal AUC.
     - Falsifier: on public twins' curve rollouts (`curve/policy_*/r*/`, r1 copied up by `ckpt_curve.sh`; not fetched
       here), the checkpoint chosen with the penalty does not have lower total RPE than the one chosen by sim_vs_ref.
   - **[H-gentle] A deviation-bounded failure mode.** Example: terminate or penalise in training when an object leaves
     the reference by > 10 cm. This turns flings (20–77 cm) into near-static failures (≈ 10–15 cm).
     - Falsifier: on ep13 / eval-14-type twins, total RPE of failed draws does not drop below the do-nothing floor.
4. **Reference side, if it is still worked on:**
   - the frame-0 anchor tilt and per-object body offsets carry the MPPE/AUC loss (a0, b);
   - ep23-type identity swaps carry the largest single share (eval 25's twin; the eval-side swap was reported fixed
     earlier);
   - none of these has a GT-free fix that passed here.

## Caveats

- Public scans stand in for the hidden host scans. Host anchor and point count are guesses, as in
  `score_registered.py`.
- Rollout cells are the grasp-lock learner on public twins, three of which (ep2, 11, 13) are known hard. They show the
  mechanism; the eval mix has fewer failures (pack AUC 0.81).
- (b) X\*_trk was fitted to maximise AUC, not RPE, so its RPE delta is not an upper bound. On ep11, 13 and 24 it
  raises RPE.
- Two candidates were tested; no multiplicity correction was applied to a deterministic reading.

## Files (this folder) and commands

Scripts:
- `rdlib.py`: kit chain helpers;
- `decomp.py`: table 1 and the ablations, giving `decomp_Po.json`;
- `anatomy.py`: gives `anatomy_Po.json`;
- `roll.py`: gives `roll_rollouts.json`;
- `floor.py`: gives `floor_static.json`;
- `cand.py`: gives `cand_K12.json`, with `--dry` for a GT-free transform-only run;
- `gate.py`: gives `cand_K12_gate.json`;
- `tables.py`: gives `tables.md`, all tables in full;
- `tiltcheck.py`: the a0 tilt/yaw split, printed only;
- `PREREG.md`.

Inputs, under scratch `S=/tmp/claude-0/-home-user-v2d-track3/6190fffb-f3a1-5d0e-84bd-7370ece99c2f/scratchpad`:
- kit zip: `$S/dl/kit`;
- public parquets and scans: HF `nvidia/video_to_data_challenge` `track_3/public/*`, in `$S/t3`;
- P_o tracks and hands: single `hf_hub_download` calls from `aebatirel/v2d-store`. No listing and no 429; the hands
  md5 match `phase1/inputs.tsv` (0 mismatches);
- rollouts: `drawdiv-20261031/fetch.sh` (orcB) and the same pattern for `mass0s{42,43}_glock_public/ep{2,12}/best/r*`.

Commands (`cd $S`; `D=` this folder):
```
python3 -I $D/decomp.py $D $S $S/fp/docs/research/work/leak-decomp-20261030/phase1/scores/xstar_trk_Po.json $D/decomp_Po.json --jobs 4   # ~8 min
python3 -I $D/anatomy.py $D $S $D/anatomy_Po.json
python3 -I $D/roll.py $D $S $D/roll_rollouts.json $S/roll/orcB:glock_public:{11,13,31} $S/roll/orcB:oracle_glock_public:{11,13,31} $S/roll/mass:mass0s{42,43}_glock_public:{2,12}   # ~8 min
python3 -I $D/floor.py $D $S $D/floor_static.json
python3 -I $D/cand.py $D $S $S/fp/docs/research/work/leak-decomp-20261030/phase1/inputs.tsv $D/cand_K12.json --jobs 2
python3 -I $D/gate.py $D/cand_K12.json K1 K2 ; python3 -I $D/tables.py $D > $D/tables.md
```

Code version: working tree on `claude/standings-20261031` @ 168b62c, plus this folder (uncommitted; the coordinating
session commits). `$S/fp` is a read-only worktree of `origin/claude/focused-pascal-2nz9s1` @ 874565a.
