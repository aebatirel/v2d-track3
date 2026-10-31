# heldpose: held objects posed by our wrist x a per-hold grasp transform (refine step S10), 31 Oct 2026

Perception sprint, experiment "heldpose". Labels: [M] measured, [E] estimate, [H] hypothesis. CPU only on this VM, $0;
no GPU, Vast or Kaggle; nothing committed by this step (the orchestrator commits).

## 0. Pre-registration (written before any mocap was read for this experiment; not changed after scoring)

**Hypothesis [H-HP].** While an object is held, its pose is better given by our perceived wrist (palm frame of
`hands_refined.npz`) times a constant per-hold grasp transform G, estimated GT-free at hold onset from the tracker, than
by the tracker itself under occlusion.

**What was looked at before this section was frozen (GT-free only).** `scratchpad/heldpose/explore*.py` read our
tracks and hands on public ep18, 31, 39, 40 (no mocap): during hand-object contact the tracker's pose relative to the
palm frame varies by a median 10-50 deg and 1-6 cm; the palm frame's own frame-to-frame rotation step is median
1.3-3.9 deg, p90 2.9-15 deg; the palm frame flips by ~170 deg on single frames (ep40 f135, f225). So a grasp-rigid
prediction carries palm-orientation noise of the same order as the variation it is meant to remove.

**Method (pipeline/heldpose.py, called by `pipeline/refine.py --steps ...,S10`; opt-in, not in DEFAULT_STEPS).**
Inputs: our track (after every earlier step, so S10 runs after S2: the hands are not time-shifted), `hands_refined.npz`
(joints_<side>, measured_<side>, KR), `world_T_cam`, our meshes (library_v3). All paths pass
`refine.assert_inference_input`. Frame 0 is never changed.
1. Palm frame W(t) per hand: origin = mean of MediaPipe joints 0, 5, 9, 13, 17; x = 0 -> 9; z = normal of
   (5 - 0) x (17 - 0) orthogonalised; smoothed over a centred 5-frame window of measured frames (median position,
   chordal mean rotation with members > 20 deg off dropped).
2. Contact d(t): nearest of the 21 measured joints to our mesh surface (600 samples) at the tracked pose. A hold
   candidate is a run of frames with d < 2.0 cm, gaps <= 6 frames bridged, >= 10 frames long, with "co-motion": the
   palm origin and the object's tracked centroid each travel >= 2 cm (max distance from the run's first frame) within
   the run. Longest runs claim frames first; one hand per frame per object.
3. Visibility v(t) of the object against our hand (GT-free): the share of the 600 surface samples that project
   (KR, world_T_cam) outside the hand's image region (finger bones as 1.0 cm capsules, the palm polygon of joints
   0, 1, 5, 9, 13, 17) or in front of it. Self-occlusion and other objects are not modelled.
4. Grasp G per hold: chordal mean rotation / median translation of inv(W(t)) O(t) over the hold's first 15 measured
   frames with v(t) at the tracked pose >= 0.6 (fewer than 3 such frames: the 5 most visible of its first 30 measured
   frames). Prediction P(t) = W(t) G on measured frames of the hold.
5. Variants (declared now; all ramp in and out over 5 frames at the hold's ends; unmeasured frames keep the tracker):
   - **S10g (primary)**: blend O'(t) = O(t) (inv O(t) P(t))^w(t) (SE(3) screw), w(t) = clip((0.8 - v_P(t)) / 0.4, 0, 1),
     v_P = visibility at the predicted pose, 5-frame moving average of w. Fully visible objects keep the tracker; an
     object covered by >= 60 % takes the prediction.
   - **S10r (replace, ungated)**: w(t) = 1 on every measured hold frame. The direct test of [H-HP].
   - **S10t (translation lock, ungated)**: rotation from the tracker; translation such that the palm origin keeps its
     onset position in the object frame (the palm orientation is not used).

**Arms.** `Po` = Phase-1 P_o tracks (library_v3 templates, the eval-like arm, primary) and `refineP` = 25 Oct tracks
(`refine/in`), both with refine/in's hands and frame-0 depth, as in T1. Baseline = `--steps S2` (the adopted chain),
re-run with the new code and checked byte-identical against T1's S2 outputs.

**Scoring.** `tools/xstar_fit.py score_track` (the kit chain, ADD-AUC); lib = library_v3 at X_kit (leaderboard
convention), * = X*_geom. ΔR = R(S2,S10x) - R(S2). Mocap is read only by `scripts/hp_score.py`, after every refine
output exists.

**Pass rule (adoption of S10g; fixed by the sprint task):** on BOTH arms, mean ΔR_lib over the thin-object proxy
episodes {18, 31, 39, 40} >= +0.005, and no public episode (all 20) has ΔR_lib < -0.01. Otherwise not adopted.
S10r and S10t are mechanism readings: if one passes the rule while S10g fails, it is a candidate for a fresh test only,
not adopted on these data.

**Falsification of [H-HP] (diagnostic, scored after the runs):** per-frame symmetry-aware ADD vs mocap (after the
kit's scene alignment, * convention) of the tracker O(t) and of the prediction P(t) on hold frames, binned by v_P
(< 0.4, 0.4-0.8, >= 0.8). [H-HP] is falsified on the proxies if, in the lowest-visibility bin with >= 30 frames
(pooled over the sweeper and dust-pan holds), the prediction's median error is not below the tracker's; it is
supported if it is lower by >= 0.5 cm.

**Reported:** per episode and per object class (sweeper, dust pan, cups, pot/lid, pitcher, boards, rack); hold counts,
frames changed, mean / max change; on eval (GT-free) the frames and size of the change on each spoon track, without
writing or changing any eval reference.

## 1. Verdict

1. **S10g (primary) is NOT adopted: it fails both parts of the pre-registered rule on both arms [M].**
   - The proxy mean ΔR_lib over {18, 31, 39, 40} is **−0.0179** on Po and **−0.0181** on refineP. The bar was ≥ +0.005.
   - The worst episode is ep39 (dust pan) at **−0.054** on both arms. The bar was ≥ −0.01. ep22 (−0.023), ep44 (−0.023),
     ep45 (−0.019) and ep18 (−0.012 / −0.013) also break the no-drop bar.
   - Over all 20 episodes the mean is −0.0064, with 3 better and 12 worse episodes (lib).
2. **The ungated readings are much worse [M].** S10r (replace) averages −0.234 on the proxies and −0.248 over 20
   episodes; 18 of 20 episodes are worse. S10t (translation lock) averages −0.091 and −0.097; 19 of 20 are worse.
3. **[H-HP] is falsified on the public proxies [M].**
   - The < 0.4 visibility bin has only 15 frames, below the 30-frame floor. The lowest bin that qualifies is
     0.4–0.8 (sweeper and dust-pan holds, 403 frames, Po).
   - In that bin the tracker's median per-frame ADD is **0.47 cm** and the prediction's is **2.95 cm**. The prediction
     is better on only 6.5 % of frames.
   - The pre-registered falsification condition is "the prediction's median is not below the tracker's". It holds by a
     wide margin.
4. **Why (post hoc, oracle diagnostic `hp_floor.py`) [M]:** see §4. Even a grasp transform fitted to mocap, one per
   hold, does worse than the tracker on our palm frame. So the limit is the palm frame of our hand fit plus real in-hand
   motion, not how G is estimated at onset.
5. **Eval: nothing changes.** S10 is not adopted, so no eval reference is touched. The GT-free estimate of what S10g
   *would* change is in §5: 53 of 2769 spoon frames by ≥ 2 cm across the 10 spoon evals.
6. **One positive outlier, post hoc [M on public, H as a lever]:** ep11, the eval-10 twin (cup nest).
   - The hand lock removes part of the blue cup's track lift while the left hand holds it (f60–100).
   - ΔR_lib is +0.0185 (S10g) and +0.035 (S10r). The blue cup's own gain is +0.037 / +0.078.
   - This is one episode and was not a pre-registered target.
   - On eval 10, S10r would move the blue cup by up to 3.4 cm, and by ≥ 2 cm only in f90–120. The lift that stays after the hands leave
     (f120–160, `../../leak-decomp-20261030/tracker-fix/SCREEN.md`) is outside any hold, so S10 cannot reach it.
   - This is a lead for the eval-10 nest experiment, not a result of this one.

## 2. Commands, machine, code

- **Machine:** this Claude cloud VM (4 cores, shared with other sprint sessions), CPU only, $0.
- **Code:** `pipeline/heldpose.py` (new) and the S10 hook in `pipeline/refine.py`. At run time HEAD was b74ef87 plus an
  uncommitted working tree. The S11 session's lines were also in `refine.py`; S11 is opt-in and was not used here.
  - The exact bytes that ran (refine `3b353b5f…`, heldpose `9a5b9c0e…`, plus `tests/test_refine_s10.py`) were later
    committed by the orchestrator in the WIP commit 48d1fbd (checked by sha256).
  - sha256 of every run: `results/code_version_public.txt` and `results/code_version_eval.txt` (refine
    `3b353b5f…`, heldpose `9a5b9c0e…`).
  - The first public run was made before the per-frame aux arrays were added. Its 160 outputs are byte-identical to the
    final run (checked).
- **One deviation from the §0 text**, decided while implementing and before any scoring:
  - §0 says unmeasured frames inside a hold keep the tracker. The code instead screw-interpolates the palm frame between
    the measured neighbours, and interpolates v_P linearly, so that w does not jump to 0 and back.
  - This affects 204 of the 4372 hold frames (4.7 %, Po).
  - [E] It is too small to change the verdict: the rule is missed by 0.023 on the proxy mean and by 0.044 on the worst
    episode.
- **Tests:**
  - `python tests/test_refine_s10.py`: 5/5 pass. They cover:
    - S10 is opt-in and runs after S2;
    - the visibility geometry;
    - a mid-hold tracker failure is restored by replace, and frame 0 is unchanged;
    - an untouched object is byte-identical in every mode;
    - end to end through `refine.main`, with every input passing `assert_inference_input`.
  - `tests/test_refine_s6.py` still passes 3/3.
- **Inference, public** (`scripts/hp_run.sh`, 160 refine runs, about 3 min):
  - Arms: `refineP` (`refine/in`) and `Po` (`leak/t1/in_Po`, the T1 links).
  - Variants:
    - S2: `--steps S2`
    - S10g: `--steps S2,S10 --s10_mode gate`
    - S10r: `--s10_mode replace`
    - S10t: `--s10_mode trans`
  - Outputs: `scratchpad/heldpose/runs/<arm>/<variant>/ep<N>/`.
  - The S2 baseline is byte-identical to T1's S2 outputs on all 40 (arm, episode) pairs.
- **Oracle scoring:**
  - `scripts/hp_score.py` (public mocap, after inference; about 25 min under load). Slim copy:
    `results/hp_scores_slim.json`; log: `results/hp_score.log`. The full file with per-frame arrays is
    `scratchpad/heldpose/hp_scores.json`.
  - `scripts/hp_floor.py`: post-hoc oracle floor, Po arm. Output: `results/hp_floor.json`.
  - `scripts/hp_where.py`: post-hoc location of the thin objects' tracker errors > 3 cm. Output:
    `results/hp_where.json`.
  - Both use the scoring venv: `$S/map/scoring/venv/bin/python -I scripts/<name>.py ...`, with
    S = `/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad`.
- **Eval, GT-free:**
  - `scripts/hp_eval.sh` ran S2 and S10 g/r/t on the stored eval perception behind packs 6/7. Sources are as in the eval
    screen; input sha256 in `results/eval_inputs_sha256.txt`.
  - `scripts/hp_eval_summary.py` wrote `results/eval_change.json`.
  - Outputs went to the scratchpad only. No eval reference was written.
- **Integrity:** every inference input passed `refine.assert_inference_input`. Mocap was read only by `hp_score.py` and
  `hp_floor.py`, on public episodes, after all refine outputs existed. The pre-registration in §0 was written before
  any mocap read for this experiment. The only earlier looks were GT-free (`scratchpad/heldpose/explore*.py`).

## 3. Per-episode results [M] (Po arm unless noted; Δ = S2,S10x − S2; lib = leaderboard convention)

| ep | objects | S2 lib | Δlib S10g Po / refineP | Δ\* S10g | Δlib S10r | Δlib S10t | S10g holds, frames changed |
|---|---|---|---|---|---|---|---|
| 0 | pot, lid | 0.9669 | +0.0003 / +0.0004 | −0.0019 | −0.2004 | −0.0334 | 4, 105 |
| 2 | pot, lid | 0.9911 | −0.0013 / −0.0013 | −0.0001 | −0.1481 | −0.0159 | 3, 242 |
| 11 | blue cup, beige cup | 0.9012 | **+0.0185 / +0.0185** | +0.0223 | +0.0349 | −0.0513 | 2, 93 |
| 12 | blue cup, rack | 0.9763 | −0.0017 / −0.0017 | −0.0017 | −0.1899 | −0.1660 | 2, 13 |
| 13 | blue cup, rack | 0.9623 | −0.0001 / −0.0002 | −0.0012 | −0.0685 | −0.0557 | 2, 50 |
| **18** | sweeper, dust pan | 0.9162 | **−0.0123 / −0.0133** | −0.0112 | −0.2538 | −0.1238 | 3, 262 |
| 21 | blue cup, pitcher | 0.8389 | −0.0002 / −0.0002 | −0.0006 | −0.1205 | −0.0111 | 3, 35 |
| 22 | blue cup, pitcher | 0.8704 | **−0.0228 / −0.0230** | −0.0266 | −0.2165 | −0.0412 | 3, 134 |
| 23 | boards (identity swap) | 0.0425 | 0 / 0 | 0 | 0 | 0 | 2, 0 |
| 24 | boards | 0.8091 | +0.0002 / +0.0002 | 0.0000 | −0.2240 | −0.1040 | 4, 30 |
| 26 | rack, pot | 0.9717 | 0 / 0 | 0 | −0.1216 | −0.0253 | 1, 0 |
| 27 | rack, pot | 0.9634 | 0 / 0 | 0 | −0.1541 | −0.0688 | 1, 0 |
| **31** | sweeper, rack | 0.8239 | −0.0006 / −0.0007 | −0.0014 | −0.0223 | −0.0122 | 1, 135 |
| **39** | dust pan | 0.9759 | **−0.0537 / −0.0537** | −0.0568 | −0.2921 | −0.0821 | 5, 79 |
| **40** | dust pan | 0.9584 | −0.0048 / −0.0048 | −0.0046 | −0.3678 | −0.1471 | 1, 56 |
| 41 | pot | 0.9927 | −0.0080 / −0.0080 | −0.0077 | −0.4083 | −0.1066 | 5, 57 |
| 42 | pot | 0.9990 | 0 / 0 | 0 | −0.7162 | −0.4209 | 1, 0 |
| 43 | pot | 0.9486 | 0 / 0 | 0 | −0.5370 | −0.2113 | 4, 0 |
| 44 | pot | 0.9970 | **−0.0229 / −0.0229** | −0.0203 | −0.5517 | −0.2227 | 1, 126 |
| 45 | pot | 0.9823 | **−0.0185 / −0.0185** | −0.0136 | −0.3995 | −0.0478 | 2, 232 |

Proxy episodes in bold in the ep column; failing values in bold. ep23's score is pinned near 0 by the known board
identity swap, so no pose change there moves it.

**Rule readings [M]:**

| arm | variant | proxy Δlib (18 / 31 / 39 / 40) | proxy mean | worst Δlib (ep) | mean of 20 | better / worse | pass |
|---|---|---|---|---|---|---|---|
| Po | S10g | −0.0123 / −0.0006 / −0.0537 / −0.0048 | −0.0179 | −0.0537 (39) | −0.0064 | 3 / 12 | **no** |
| refineP | S10g | −0.0133 / −0.0007 / −0.0537 / −0.0048 | −0.0181 | −0.0537 (39) | −0.0065 | 3 / 12 | **no** |
| Po | S10r | −0.254 / −0.022 / −0.292 / −0.368 | −0.234 | −0.716 (42) | −0.248 | 1 / 18 | no |
| Po | S10t | −0.124 / −0.012 / −0.082 / −0.147 | −0.091 | −0.421 (42) | −0.097 | 0 / 19 | no |

**Per object class [M]** (mean per-object ΔAUC lib over the episodes that have the class, Po; n = object instances;
per-object AUCs depend on slot 0 through the kit's scene alignment, so these are indicative):

| class | n | S10g | S10r | S10t | reading |
|---|---|---|---|---|---|
| sweeper | 2 | −0.013 | −0.131 | −0.039 | ep18 −0.025, ep31 −0.001 |
| dust pan | 3 | −0.020 | −0.317 | −0.141 | ep39 −0.054 |
| cups | 6 | −0.002 | −0.148 | −0.100 | ep11 blue +0.037 (nest), ep22 blue −0.046 |
| pot / lid | 11 | −0.005 | −0.351 | −0.118 | per pot hold, the median residual of the tracker to the prediction is 2–11 cm |
| pitcher | 2 | 0.000 | −0.118 | −0.025 | the gate never opens (v_P ≥ 0.97) |
| boards | 4 | +0.000 | −0.112 | −0.052 | |
| rack | 5 | 0.000 | 0.000 | 0.000 | never held with co-motion (S10 finds no hold) |

**[H-HP] diagnostic** (`hp_score.py`; per-frame symmetry-aware ADD vs mocap, \* convention, after the kit's scene
alignment, on S10 hold frames; v_P = GT-free visibility at the prediction) [M]:

| arm, objects | v_P bin | frames | tracker median (cm) | prediction median (cm) | prediction better on |
|---|---|---|---|---|---|
| Po, sweeper + dust pan | < 0.4 | 15 | 0.63 | 8.48 | 0 % |
| | 0.4–0.8 | 403 | **0.47** | **2.95** | 6.5 % |
| | ≥ 0.8 | 673 | 0.93 | 4.67 | 5.8 % |
| Po, cups | 0.4–0.8 | 211 | 0.75 | 3.03 | 31.8 % |
| | ≥ 0.8 | 392 | 0.73 | 3.03 | 12.2 % |
| Po, pot / lid | 0.4–0.8 | 266 | 0.69 | 2.56 | 8.6 % |
| | ≥ 0.8 | 1670 | 0.82 | 6.89 | 0.7 % |
| Po, all | all | 4372 | 0.96 | 5.40 | 6.8 % |

refineP is the same to within 0.07 cm. The tracker is accurate during holds on the public data (median < 1 cm). The
hand-based prediction is 3–7× worse in every visibility bin.

## 4. Mechanism: the constant-grasp floor on our palm frame (post hoc, oracle; `scripts/hp_floor.py`) [M]

**What it computes.**
- For every S10 hold on the Po arm, per hold frame, after the kit's conversion and scene alignment (\* convention):
  - the tracker's error;
  - the error of S10's onset-G prediction P;
  - the error of the oracle-G floor P\* = A W(t) G\*.
- G\* is ONE grasp transform per hold fitted to mocap (chordal mean rotation, mean translation of inv(A W) M). A is the
  kit's scene alignment.
- P\* is the best any constant-grasp lock on our palm frame could do. Its error is palm-frame noise plus real in-hand
  motion.
- rel spread = median deviation of inv(A W(t)) M(t) from its hold mean: how far the true object moves relative to our
  palm frame.
- Summary values are frame-weighted means of per-hold medians (`results/hp_floor.json`).

| holds (Po) | holds / frames | tracker (cm) | onset-G P (cm) | oracle-G floor P\* (cm) | P\* better than tracker | rel spread (deg / cm) |
|---|---|---|---|---|---|---|
| sweeper + dust pan | 10 / 1053 | **0.88** | 4.50 | **3.13** | 10.5 % of frames | 19.0 / 2.9 |
| cups | 8 / 576 | 0.89 | 3.69 | 3.34 | 23.4 % | 20.4 / 2.8 |
| pot / lid | 19 / 1818 | 0.95 | 7.00 | 4.43 | 6.0 % | 16.1 / 4.1 |

Per hold, thin objects and cups:

| ep, object | tracker | P | P\* | rel spread |
|---|---|---|---|---|
| ep18 sweeper | 0.64 / 0.28 | 3.2 / 3.1 | 2.5 / 2.3 | 15–17° |
| ep31 sweeper | 1.40 | 1.87 | 1.60 | 10.4° |
| ep18 / 39 / 40 dust pan | 0.5–1.2 | 3.9–14.6 | 2.9–9.4 | 13–50° |
| ep12, 13, 21, 22 blue cup | 0.45–0.91 | 3.0–8.5 | 2.2–12.5 | 18–53° |
| **ep11 blue cup** | 1.00 | **0.92** | **0.41** | **2.8°, 0.37 cm** |
| **ep11 beige cup** | 1.93 | **1.44** | **1.16** | **4.2°, 1.1 cm** |

Readings:
1. Even with the grasp fitted to mocap, a constant grasp on our palm frame is 2.5–4.7× worse than the tracker on the
   thin objects. So [H-HP] fails because of the palm frame and in-hand motion, not because of the onset estimate.
   - The true object turns by a median of 10–50° relative to our palm frame within a hold.
   - That includes MediaPipe/hand-fit orientation noise: GT-free, the palm frame steps p90 3–15° per frame and flips on
     single frames.
   - It also includes real regrasps: the dust pan's handle is shifted between both hands, and the sweeper rolls in the
     fist while sweeping.
2. The only holds where the lock wins are ep11's two cups, where the true grasp is rigid in our palm frame (2.8° /
   4.2° spread). This is the cup nest of the eval-10 twin, where the tracker is known to lift the static-looking cup
   (tracker-fix ep11 DIAG).
3. A GT-free gate that found such rigid holds (for example, low tracker-vs-palm residual) is a post-hoc idea [H]. Its
   only public positive is one episode, so it is not a candidate on these data. See §6.

## 5. Eval (GT-free estimate only; no eval reference changed) [M on our tracks]

S10 run on the stored eval tracks behind packs 6/7 (`results/eval_change.json`). Because S10 is not adopted, it changes
**no** eval episode. If S10g had passed, it would have touched the following:

| spoon eval | holds (frames held / T) | S10g frames changed ≥ 1 cm / ≥ 2 cm | S10g max change (cm) | S10r frames ≥ 2 cm | median v_P per hold |
|---|---|---|---|---|---|
| 3 | 6 (200 / 313) | 0 / 0 | 0.32 | 122 | 0.84–0.99 |
| 5 | 3 (90 / 288) | 7 / 2 | 2.51 | 37 | 0.68–0.86 |
| 6 | 3 (95 / 243) | 0 / 0 | 0.88 | 49 | 0.74–0.81 |
| 15 | 2 (85 / 166) | 36 / 31 | 4.22 | 61 | 0.70–0.72 |
| 16 | 1 (107 / 173) | 6 / 0 | 1.52 | 87 | 0.88 |
| 32 | 4 (156 / 259) | 16 / 6 | 2.81 | 67 | 0.66–0.78 |
| 33 | 4 (232 / 348) | 11 / 0 | 1.32 | 111 | 0.72–0.86 |
| 35 | 7 (314 / 421) | 10 / 2 | 2.07 | 215 | 0.72–1.00 |
| 36 | 5 (321 / 407) | 44 / 12 | 2.74 | 236 | 0.70–0.83 |
| 37 | 1 (85 / 151) | 1 / 0 | 1.16 | 20 | 0.72 |
| **all 10** | **1685 / 2769 frames held** | **131 / 53** | – | **1005** | – |

- S10g would have changed 1022 spoon frames, most by < 1 cm. On ten spoon evals, 53 frames would move by ≥ 2 cm.
- S10r would move 1005 frames by ≥ 2 cm. On public data that size of change cost −0.23 per episode.
- The spoon's visibility on eval (median v_P 0.66–1.0 per hold) lies in the same range as the public sweeper
  (0.69–0.82) and dust pan (0.77–0.97). So the public proxies cover the eval spoon's occlusion range [M]. The < 0.4
  regime is rare on both.
- Other evals S10g would touch by ≥ 2 cm:
  - 38 (dust pan): 106 frames, max 15.3 cm, residual median 14.3 cm. The track and the hand disagree strongly there.
  - 19 (dust pan): 15 frames.
  - 30 (sweeper): 9 frames.
  - 33 (blue cup): 7 frames.
  - 14 (blue cup): 2 frames.
- Cost of the eval estimate: $0, CPU, about 2.5 min.

## 6. What this rules out, and what is left [E/H]

- **Ruled out [M]:** posing a held object as palm frame × a constant grasp, in any of the three forms tested.
  - This holds whether G is estimated at onset or fitted to mocap (§4), gated by visibility or not, and with full pose
    or translation only.
  - On the public thin-object proxies, the tracker's median error inside holds is already 0.34–1.41 cm per object.
    Our palm frame is not good enough to beat it.
  - LB value of S10 as built: negative. Do not spend a rollout gate or eval retrains on it.
- **Where the proxies' large tracker errors are (post hoc, oracle; `scripts/hp_where.py`, `results/hp_where.json`)
  [M]:**
  - On the four proxy episodes (Po, S2), only 50 thin-object frames exceed 3 cm.
  - 38 of them are ep18's sweeper over f117–160, all outside S10's holds. Over f124–148 the right hand, which holds
    the sweeper before and after, is not measured. GT-free, the track drifts up and rotates by more than 100° there,
    then jumps back by 15.6 cm at f155.
  - The other 12 are ep40's dust pan over f100–120, inside a hold.
  - ep31 and ep39 have none. Inside S10's holds the tracker's median error is 0.34–1.41 cm.
- **Not tested, and the reason [H]:**
  - A hand prior cannot reach most of the large errors, because the holding hand is unmeasured there.
  - Inside holds there is little to gain, because the tracker is already good.
  - A "tracker-jump repair" gated on a measured hand and a one-frame discontinuity is therefore not supported by these
    data either.
  - Falsifier for any future hand-based variant: the oracle floor of §4 must first beat the tracker on the low-visibility
    hold frames.
  - A residual-gated "rigid hold only" lock (apply only when the tracker stays within about 1 cm / 5° of palm x G over
    the hold) is the one form the floor does not rule out: ep11's cups have a 2.8–4.2° true spread.
    - Its public support is a single episode, and these data are now seen, so it is not proposed here.
    - Falsifier: on a fresh pre-registration it opens on fewer than 2 public holds outside ep11, or harms any episode by
      more than 0.005.
- **Lead for the eval-10 experiment [H]:**
  - On ep11, locking the held blue cup to the hand gave +0.0185 (gated) and +0.035 (replace) lib. It suppressed the
    cup's lift while the left hand holds it during the nest.
  - On eval 10, the comparable change is 2–3.4 cm at f90–120. The lift that is held after the hands leave (f120–160)
    stays.
  - Falsifier: an ep11-only, hold-restricted S10r (blue cup, frames where the beige cup is within 3 cm above it)
    gives < +0.01 on ep11 or harms any other cup episode by > 0.005.
  - This must be pre-registered fresh, since ep11 was seen here.
