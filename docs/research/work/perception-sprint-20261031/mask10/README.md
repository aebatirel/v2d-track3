# mask10: a GT-free fix for the eval-10 cup nest (refine step S12, physics projection, masking re-track spec), 31 Oct 2026

Perception sprint, experiment "mask10". Labels: [M] measured, [E] estimate, [H] hypothesis. CPU only on this VM, $0;
no GPU, Vast or Kaggle; nothing committed by this step (the orchestrator commits).

## 0. Pre-registration (written before any mocap was read for this experiment; not changed after scoring)

**Failure [M, earlier work].** ep11 (eval 10's public twin, beige cup lowered into the blue cup):
- the outer blue cup's track rises along its axis while the beige cup goes in: +5.3 cm peak (P_o), +2.5 cm held after
  the hands leave (`../../leak-decomp-20261030/tracker-fix/ep11/DIAG.md`);
- the inner cup is tracked well while nested (P_s 0.66 cm median);
- the true-motion oracle scored 0.940 vs 0.595 for our perceived reference on the ep11 rollout (orcB);
- eval 10's stored track shows the same signature after a real 4.5 cm slide of the blue cup at f38–46, so S6 (whole-episode
  static hold) does not fire there (`../../leak-decomp-20261030/tracker-fix/SCREEN.md` §4, `T1/RESULTS.md` §3).

**Hypothesis [H-NEST].** The outer cup of a nest is the bottom of the stack. It cannot rise unless it is lifted, and a
lifted stack also moves sideways. So holding the outer cup at its pre-nest pose from the moment the inner cup enters it
until the stack moves sideways removes the lift, and keeps eval 10's earlier slide.

**What was looked at before this section was frozen (GT-free only).**
- `scratchpad/mask10/scripts/explore11.py` on ep11's P_o track (no mocap): per-frame horizontal distance and height between
  the cups' centroids, lowest/highest vertex heights, hand distances. The beige cup becomes coaxial (≤ 2.3 cm) at f42 and
  its lowest vertex passes the blue cup's top at f45. The blue cup's bottom is then 2.2–4.8 cm above our table plane, and
  2.4 cm at f102–136 with no hand within 17 cm.
- `scripts/meshgeo.py`, `scripts/piecegeo.py` (our meshes and the eval-10 collision pieces, no scans). Our blue mesh's
  cavity is filled up to 5.8 cm above its base; the ev10 collision pieces have an open cavity with the floor 0.4 cm
  above the base, and the beige pieces are shrunk 8 mm in radius (`meshes/carve/ev10/carve.json`).
- A GT-free smoke run of S12 V1 on ep11 P_o: window [42, 137), pre-nest frame 33, mean outer height change −2.37 cm.
  No score was computed.
- Eval 10's track profile in SCREEN.md / T1 (read earlier by those steps; no rule parameter here was set from it).
- The 20 public episodes are the same ones every earlier fix used (no fresh holdout). Only ep11 has two cups, so on
  the other 19 the cup rule cannot fire by construction; their no-change test checks the code, not the rule.

**Method (`pipeline/nest.py`, called by `pipeline/refine.py --steps S12,S2`; opt-in, not in DEFAULT_STEPS).**
Inputs: our track, our hands (`hands_refined.npz`), our frame-0 depth (table plane by `det_rules.table_plane`, as S6),
our meshes (library_v3), optional collision pieces (`meshes/carve/ev10`, the eval-10 simulator geometry) and an optional
depth grid for the veto (our stereo depth). Every path passes `refine.assert_inference_input`. Heights are along our
table normal n.
1. **Nest window.** For an ordered cup pair (outer j, inner i), a frame is nested when all three hold:
   - the inner's vertex centroid is above the outer's;
   - it is within 2.5 cm of it horizontally (coaxial; about the cup's rim radius minus its base radius);
   - the inner's lowest vertex is at most 2 cm above the outer's highest vertex (entering or inside).

   Runs are bridged over gaps of ≤ 5 frames; a run of ≥ 10 frames is a window [ts, te). Frame 0 is never in a window.
2. **Pre-nest pose.** P* is the outer's tracked pose at the frame of [ts − 10, ts) whose centroid height is the median
   of those frames.
3. **Guard G1.** At P* the outer's bottom must be within 2 cm of its frame-0 bottom height (it is still standing where it
   stood; a lifted, hand-held outer is left alone).
4. **Release.** The hold ends at the first window frame where the tracked outer is more than 2 cm from P* horizontally
   (the stack is carried), or at te. After a release before the last frame, the pose ramps back to the track over 5
   frames (SE(3) screw).
5. **Hold.** V1: the outer takes P* on every held frame. V1h: the tracked outer is moved along n to P*'s centroid height
   (sideways motion and rotation kept).
6. **Depth veto (V1d).** On the depth-grid frames in the window, the outer's visible pixels are back-projected. Those are
   our renders at the tracked and the held pose, with the others in front removed, our hands removed (2 cm), and points
   within 0.8 cm of the table removed. The median distance to our mesh is then computed at the held pose and at the
   tracked pose (points within 3 cm of either).

   The window is vetoed when, on more than half of the frames with ≥ 150 points, the held median exceeds the tracked
   one by more than 1.0 cm. Depth: the 48-frame grid of our ep11 cache (`scratchpad/offset/depth/ep11/depth_grid.npz`,
   fetched by the offset experiment). On eval 10, our stored frames 0/30/60/150.
7. **Inner, V2 (the task's literal option b).** On window frames where the inner rests (not moving by refine's labels
   and no measured hand within 5 cm), the inner's bottom is put on the outer's cavity floor. On the other window frames
   it is kept at or above that floor. Floor and inner bottom come from the ev10 collision pieces (`--s12_pieces
   meshes/carve/ev10`).

   **[H, stated before scoring]: V2 hurts the beige cup.** Real stacking cups jam on their walls above the floor, and
   the ev10 beige pieces are shrunk by 8 mm. So V2 puts the beige cup too deep.
8. **Inner, V3 (option c, physics projection; `tools/nest_physics.py`, fcvenv MuJoCo 3.8.1).** It starts from the S12 V1
   output before S2.

   On each held window frame where no measured hand is within 5 cm of the inner cup, the inner cup is settled:
   - the inner is a free body (ev10 pieces, 0.3 kg, `inertia.json`), started at its tracked pose with zero velocity;
   - the outer is static at its held pose (ev10 pieces), on our table plane;
   - gravity is along −n, timestep 2 ms, settle time 1.0 s, MuJoCo default contact parameters.

   The settled pose replaces the tracked one, with a 5-frame SE(3) ramp at the edges of each released run. S2 runs
   afterwards.

   V3p (physics only, no hold): on the same window frames (S12's detection) where neither cup has a measured hand within
   5 cm, both cups are settled as free bodies from their tracked poses, with the same parameters and ramp.

   [H] V3 has the same depth bias as V2 (shrunk pieces). V3p can remove only the hands-off part of the lift.

**Variants (declared now).**

| id | steps | what it tests |
|---|---|---|
| **V1 (primary)** | `--steps S12,S2` (hold) | [H-NEST] |
| V1h | `--steps S12,S2 --s12_mode height` | height-only hold |
| V1d | V1 + `--s12_depth <ep11 grid>` | the depth veto ("unless depth contradicts it") |
| V2 | V1 + `--s12_inner floor --s12_pieces meshes/carve/ev10` | literal (b): inner on the outer's floor |
| V3 | V1 (pre-S2) + `nest_physics.py --mode inner` + S2 | (c) with the hold |
| V3p | input + `nest_physics.py --mode both` + S2 | (c) alone |

**Arms.**
- `Po` (primary, eval-like): the Phase-1 P_o tracks (library_v3 templates).
- `refineP`: the 25 Oct tracks (`refine/in`).

Both arms use refine/in's frame-0 depth and hands, as in T1. Baseline is `--steps S2` (the adopted chain), re-run with
the current code and checked byte-identical against T1's S2 outputs. V1d, V3 and V3p need inputs that exist only for
ep11 (the depth grid) or a nest window, so on the other 19 episodes they equal V1 and S2 by construction.

**Scoring.** `tools/xstar_fit.py score_track` (the kit chain, ADD-AUC). lib = library_v3 at X_kit (leaderboard
convention, decisive); \* = X\*_geom (beside). ΔR = R(variant) − R(S2). Mocap is read only by `scripts/m10_score.py`,
after every inference output exists.

**Pass rule (fixed by the sprint task), per variant and arm:**
- ep11 ΔR_lib ≥ +0.05;
- on each of the other 19 public episodes, |ΔR_lib| ≤ 0.002 and |ΔR_\*| ≤ 0.002.

A variant passes when it passes on both arms. V1 is the primary reading: if it passes, S12 V1 is the candidate for the
ep11 rollout gate below. No eval reference changes on this result alone.

**Mechanism readings (scored after, not part of the rule):**
- per-object AUC on ep11;
- blue-cup height error by phase (the DIAG's phases);
- beige-minus-blue height at f130 against mocap's +3.16 cm.

**Eval 10 (GT-free, no reference changed):**
- run V1, V1h, V2 and V3 on eval 10's stored track (the perception behind packs 6–8);
- report the window, the pre-nest frame, the held height change and the depth-veto reading on our stored frames;
- draw an overlay PNG.

**Next gate if V1 passes [not run here; needs the owner's go-ahead]:** the ep11 rollout gate of the ep11 DIAG Fix 1
(grasp lock gl10A2, P_o bundle + refine S12,S2 + mkref, seeds 42 and 43, NREP 10, against the same recipe without S12).
Falsified if the seed mean ADD-AUC vs mocap rises by less than +0.05.

## 1. Verdict
Section 0 is unchanged since it was frozen. Its sha256 before scoring was `6d95ac9d…` (`results/README_prereg_sha256_before_scoring.txt`,
10:23 UTC). Everything below was added after scoring.

1. **The primary V1 passes the pre-registered rule on both arms [M].**
   - ep11 ΔR_lib is **+0.0676** (bar +0.05): 0.9012 → 0.9688. Δ\* is +0.0682.
   - Every other public episode is byte-identical to S2, so Δ = 0 exactly.
   - The blue cup's own AUC goes 0.865 → **1.000**. Its height error is ≤ 0.1 cm median in every phase; the track had
     +3.0 / +3.75 / +2.4 cm in phases D / E / F.
   - The beige cup is unchanged (lib 0.9375).
   - V1h and V1d give the same numbers (+0.0676).
2. **The best variant is V3, hold plus physics seat of the inner cup (option c with b) [M]: +0.0764 lib (+0.0782 \*).
   It passes.**
   - The beige cup improves 0.9375 → 0.9553 lib (\* 0.899 → 0.919). Its hands-off phase F goes 0.94 → 1.00.
   - On the hands-off frames the settled beige sits **+3.32 cm** over the blue cup (centres, scorer frame). Mocap says
     +3.17 cm. V1 leaves it at +4.35 cm (the beige template's offset).
   - The [H] I stated in §0, that the 8 mm-shrunk ev10 pieces would seat the beige too deep, is **falsified**: they seat
     it 0.15 cm from the mocap height.
3. **V2, the literal option (b) inner floor, gives +0.0676 lib, the same as V1 [M].** It lowers the beige by up to 2.6 cm
   on resting frames. Beige over blue is then +2.16 cm against mocap's +3.17, so it overshoots by about 1 cm in the other
   direction. The kit's 1 cm ADD steps do not register that change. Real stacking cups jam on their walls before the floor;
   the physics seat (V3) gets this right and the floor rule does not.
4. **V3p (physics alone, no hold) fails: +0.0126 [M].** It removes only the hands-off lift (phase F blue height error
   2.4 → −0.03 cm). While the fist holds the blue cup (phases D–E) physics cannot rule out a hand lift, so the +3–3.75 cm
   stays. The hold is the part that matters.
5. **The depth veto never fires, so it is untested [M].** On ep11, 6 of 25 usable grid frames call the held pose worse
   by more than 1 cm. That is below the majority needed for a veto. On eval 10 only f150 is usable: 0.23 vs 0.21 cm.
6. **Caveats on the pass.**
   - The two arms are the same track on ep11 (T1: identical), so "both arms" is one test.
   - No other public episode has two cups, so the no-change half of the rule tests the code, not the rule.
   - The detector's parameters come from ep11's GT-free geometry and are scored on ep11. There is no holdout.
   - This is reference level only. S6 also gave +0.0676 on ep11, so the reference-level ceiling for the outer cup was
     already known. The new information is that a nest-window rule reaches it without the whole-episode static condition
     (which fails on eval 10), and that physics fixes the inner cup.
7. **Eval 10, GT-free, no reference changed: the frozen V1 does little there; a post-hoc variant does what was intended**
   (§4) [M on our track; H that it is right].
   - Eval 10's window starts at f53, and the pre-nest frame is **f44, inside the real 4.5 cm slide (f38–46)**.
   - At f44 the track already sits +1.53 cm high and 0.8 cm short of the slid position.
   - V1 therefore holds the blue cup at +1.53 cm to the end: mean height change −0.17 cm, peak −2.2 cm at f105–117.
   - **V4 / V4p (post hoc, after seeing eval 10's track)** use the frame-0 support height with the tracked sideways
     motion, and in V4p the physics seat.
     - They put the blue cup back at +0.06 cm over f53–160 (track: +0.4 to +3.7 cm) and keep the 4.1 cm slide.
     - In V4p the beige sits +3.2 cm over the blue cup on the hands-off frames.
     - On ep11 they score +0.0676 (V4) and +0.0698 (V4p) lib. On ep11 V4 equals V1h, so ep11 cannot test what V4 changes
       on eval 10.
8. **Option (a), masking re-track: job spec and cost in §5. CPU mocks predict it fails alone with our templates
   [M on mock / proxy, H for FoundationPose].**
   - A depth-only ICP stand-in for the tracker reproduces the lift from the raw depth: +3.5 cm median, +5.3 cm peak; the
     track has +5.4 cm.
   - With the inner cup masked out, the fit has no axial anchor and runs 4–6 cm down.
   - With library_v3's partial beige template, the occluder masks also cover most of the blue cup's lower body at f130.
   - So any GPU test of (a) should be paired with S12.
9. **Recommendation (needs the owner's go-ahead; nothing launched).**
   - Take the eval-10 fix to the ep11 rollout gate (§0, last item) with **V3 as the arm that passed the pre-registered
     rule**, and V4p beside it. They differ on eval 10, not on ep11.
   - About $2.6–5.2 [E, orcB per-training cost]. If it passes, retrain eval 10 on the V4p (or V3) reference with 2
     seeds (about $2.6) and swap only under the multi-draw rule.
   - LB value unchanged from the ep11 DIAG [E]: +0.004 to +0.012, central +0.007, at most +0.017, if the twin gate
     recovers 30–70 % of ep11's 0.345 P→O rollout gap.

**Eval episodes it would change: eval 10 only.** It is the only roster with two cups (`--s12_cups blue_cup,beige_cup`).
Eval 8 (beige cup + pot) and 14, 20, 32, 33 (blue cup + rack / pitcher / spoon) have no cup pair, so S12 skips them.

## 2. What ran (commands, machine, code, provenance)
- **Machine:** this Claude cloud VM (4 cores, shared with other sprint sessions), CPU only, **$0**.
- **Run time:** 10:15–11:20 UTC.
- **Code:**
  - `pipeline/nest.py` (new, S12);
  - the S12 hook and args in `pipeline/refine.py` (opt-in; `STEP_ORDER` … S11, S12, S1 …);
  - `tools/nest_physics.py` (new, fcvenv MuJoCo 3.8.1);
  - `pipeline/occluder_mask.py` (new, for option a);
  - `tests/test_refine_s12.py` (new; 7/7 pass). `tests/test_refine_s6.py` and `tests/test_refine_s10.py` still pass.
  - HEAD at the public run was 3e1bdd0 plus the uncommitted files (`runs/code_sha256_at_public_run.txt`). Final hashes are
    in `results/code_sha256_final.txt`.
  - With the final code, V1, V1h and V2 on ep11 reproduce the scored outputs byte for byte.
  - S2 baselines are byte-identical to T1's on 40/40 (arm, episode).
- **Inference, GT-free:**
  - `scripts/m10_run.sh`: 20 episodes × 2 arms × variants, about 3 min. Job lines are in `runs/jobs_public.txt`.
    Outputs: `scratchpad/mask10/runs/<arm>/<variant>/ep<N>/`.
  - Eval 10: `scripts/m10_eval10.sh`; outputs in `scratchpad/mask10/eval10/`.
  - Every input path passes `refine.assert_inference_input`.
- **Oracle scoring (public mocap, after inference):**
  - `scripts/m10_score.py` (full run, 25 min): `scores/m10_scores_full.json`, `scores/m10_score_full.log`.
  - ep11 re-scores: `M10_EPS=11 M10_VARS=S2,V2` → `scores/m10_scores_ep11_V2fix.json`; `M10_VARS=S2,V4,V4p` →
    `scores/m10_scores_ep11_posthoc.json`.
  - `scripts/m10_verdict.py` merges them into `results/m10_verdict.json`.
- **GT-free readings:**
  - `scripts/m10_profile.py`: per-frame heights; `results/profile_ep11_Po.txt`, `eval10/profile_eval10.txt`.
  - `scripts/m10_penetration.py`: piece penetration; `eval10/penetration_eval10.json`, `results/penetration_ep11_Po.json`.
  - `scripts/m10_overlay.py`: `eval10/e10_s12_overlay.png`, `eval10/e10_s12_overlay_V4p.png`.
  - `scripts/m10_icp_proxy.py`: `results/icp_proxy_ep11.{json,txt}`.
  - `scripts/m10_perc2_mock.py`: `results/perc2_mask_mock_ep11_*`.
- **Two code defects were found and fixed during the run.** Both are recorded so nothing is hidden.
  1. **V3, first run: NaN.** S2's output on ep11 was non-finite on 3 (Po) and 2 (refineP) blue-cup frames.
     - Cause: the held pose went through a float32 `cam_T` round trip, which leaves about 1e-8 rad of frame-to-frame
       jitter. At θ ∈ [1e-8, 1.05e-8], `refine.se3_log` divides by `1 − cos θ = 0`. Its small-angle branch starts only
       below 1e-8.
     - refine flagged it (`finite: false`), but `m10_run.sh` grepped only for tracebacks. The NaN crashed the first
       scoring run before any ep11 score was written (`scores/m10_score_run1_crashed.log`).
     - Fix in `nest_physics.py`: restore one exact held pose and write `cam_T` in float64. The rule did not change.
     - The invalid outputs are kept in `scratchpad/mask10/runs/<arm>/V3_nan_invalid/`.
     - `refine.se3_log` itself is untouched, because other sessions compare S2 bytes. It is a latent issue for any
       multi-stage refine chain that holds a pose.
  2. **V2, first run: wrong cup orientation in `nest.CupGeom`.** The axis flip was inverted, so the "floor" was read at
     the rim end (16.6 cm above the base instead of 0.42).
     - I found it at about 10:44 UTC in the GT-free eval-10 record (`floor_above_base_cm`). The full-run scores printed
       at 10:48.
     - Fixed, V2 re-run (ep11 and eval 10; outputs elsewhere are byte-identical to S2) and re-scored.
     - The superseded run is kept as `runs/<arm>/V2_bug_orientation/`. Its log line reads V2 +0.0511 and is invalid.
       V1, V1h and V1d do not use the floor and are unaffected (checked byte for byte).
- **Integrity:**
  - Mocap was read only by `m10_score.py`, on public episodes, after inference.
  - The oracle-template diagnostic (S12 on the P_s track with the scan meshes, `scratchpad/mask10/oracle_Ps/`) was run
    only to check that the window holds with true templates. It was not scored and feeds nothing.
  - Eval 10: our stored track (inputs sha256 in `eval10/inputs_sha256.txt`, same as T1's), outputs in the scratchpad
    only. No eval reference was written or changed, and nothing was tuned on eval results (there are none).
  - V4 / V4p were designed after seeing eval 10's GT-free track and are labelled post hoc.

## 3. ep11 numbers (public, vs mocap) [M]
Po and refineP are the same track on ep11, so the numbers are identical. Δ is against S2 (0.9012 lib, 0.8814 \*). Phase
blue dz = the blue cup's height error, median cm, after the kit's scene alignment (\* convention). F beige−blue = the beige
cup's centre over the blue's on f102–136; mocap gives +3.17.

| variant | lib | Δ lib | Δ \* | blue / beige lib | blue dz D / E / F (cm) | F beige−blue (cm) | rule |
|---|---|---|---|---|---|---|---|
| input (no refine) | 0.8978 | −0.0034 | −0.0075 | 0.862 / 0.933 | 2.03 / 3.75 / 2.38 | +1.98 | – |
| S2 (baseline) | 0.9012 | 0 | 0 | 0.865 / 0.938 | 3.02 / 3.75 / 2.40 | +1.98 | – |
| **V1** hold (primary) | **0.9688** | **+0.0676** | +0.0682 | **1.000** / 0.938 | −0.02 / 0.03 / 0.05 | +4.35 | **pass** |
| V1h height hold | 0.9688 | +0.0676 | +0.0682 | 1.000 / 0.938 | −0.02 / 0.04 / 0.04 | +4.36 | pass |
| V1d V1 + depth veto (no veto) | 0.9688 | +0.0676 | +0.0682 | 1.000 / 0.938 | = V1 | +4.35 | pass |
| V2 inner on the floor (fixed run) | 0.9688 | +0.0676 | +0.0684 | 1.000 / 0.938 | −0.02 / 0.03 / 0.05 | +2.16 | pass |
| **V3** hold + physics seat | **0.9776** | **+0.0764** | **+0.0782** | 1.000 / **0.955** | −0.02 / 0.03 / 0.05 | **+3.32** | **pass** |
| V3p physics only | 0.9138 | +0.0126 | +0.0258 | 0.913 / 0.915 | 3.02 / 3.75 / **−0.03** | +2.11 | fail |
| V4 support height (post hoc) | 0.9688 | +0.0676 | +0.0682 | 1.000 / 0.938 | −0.05 / 0.01 / 0.01 | +4.39 | (not in the rule) |
| V4p V4 + physics seat (post hoc) | 0.9710 | +0.0698 | +0.0780 | 1.000 / 0.942 | −0.05 / 0.01 / 0.01 | +3.32 | (not in the rule) |

- **S12 on ep11:**
  - window [42, 137) (beige coaxial within 2.3 cm from f42, entering the rim), pre-nest frame f33, held to the end;
  - mean outer height change −2.37 cm (min −5.36);
  - V3 / V3p settled 36 hands-off frames (f101–136);
  - V3 moved the beige −1.07 cm (median); V3p moved the blue −2.42 and the beige −2.23 cm.
- **The other 19 public episodes:** every variant's output is byte-identical to S2 on both arms (no cup pair), so Δ = 0.

| ep | objects | S2 lib Po / refineP | S2 \* Po / refineP |
|---|---|---|---|
| 0 | white_pot, white_pot_lid | 0.9669 / 0.9672 | 0.9629 / 0.9657 |
| 2 | white_pot, white_pot_lid | 0.9911 / 0.9871 | 0.9824 / 0.9823 |
| 12 | blue_cup, plastic_dish_rack | 0.9763 / 0.9760 | 0.9739 / 0.9739 |
| 13 | blue_cup, plastic_dish_rack | 0.9623 / 0.9648 | 0.9051 / 0.9038 |
| 18 | mini_sweeper, mini_dust_pan | 0.9162 / 0.9680 | 0.9217 / 0.9718 |
| 21 | blue_cup, water_pitcher | 0.8389 / 0.8389 | 0.8438 / 0.8438 |
| 22 | blue_cup, water_pitcher | 0.8704 / 0.8704 | 0.8618 / 0.8598 |
| 23 | wooden_piece_1, wooden_piece_2 | 0.0425 / 0.0425 | 0.0429 / 0.0429 |
| 24 | wooden_piece_1, wooden_piece_2 | 0.8091 / 0.8091 | 0.8069 / 0.8069 |
| 26 | plastic_dish_rack, white_pot | 0.9717 / 0.9678 | 0.9652 / 0.9610 |
| 27 | plastic_dish_rack, white_pot | 0.9634 / 0.9627 | 0.9362 / 0.9339 |
| 31 | mini_sweeper, plastic_dish_rack | 0.8239 / 0.8550 | 0.8673 / 0.8723 |
| 39 | mini_dust_pan | 0.9759 / 0.9759 | 0.9914 / 0.9914 |
| 40 | mini_dust_pan | 0.9584 / 0.9584 | 0.9784 / 0.9784 |
| 41 | white_pot | 0.9927 / 0.9927 | 0.9893 / 0.9893 |
| 42 | white_pot | 0.9990 / 0.9993 | 0.9708 / 0.9784 |
| 43 | white_pot | 0.9486 / 0.9479 | 0.9465 / 0.9469 |
| 44 | white_pot | 0.9970 / 0.9970 | 0.9995 / 0.9995 |
| 45 | white_pot | 0.9823 / 0.9823 | 0.9843 / 0.9843 |

- Mean ΔR_lib over the 20 episodes: V1 +0.0034, V3 +0.0038 (all of it ep11).
- **Physical consistency with the ev10 simulator pieces (GT-free, last 40 frames) [M]:**
  - the blue cup's lowest collision point above our table plane: ep11 S2 +2.33 cm → V1/V3 +0.03 cm;
  - beige-into-blue penetration median 2.4 mm (S2) → 0.1 mm (V3);
  - frames with more than 2 mm penetration: 76 (S2) → 14 (V3), 9 (V4p).
  - Caveat: the measure is capped near the 3 mm wall thickness, so it counts contacts, not depth.

## 4. Eval 10, GT-free (our stored track behind packs 6–8; no reference changed) [M on the track, H that it is right]
- **S12 detection:**
  - window [53, 161): the beige comes coaxial over the blue at f53 and is held high until it is lowered at about f97;
  - pre-nest frame **f44**, inside the real slide f38–46;
  - G1 passes: the bottom is 1.34 cm above its frame-0 height, under the 2 cm guard;
  - no release; no depth veto (f150: 0.23 cm held vs 0.21 cm tracked; f60 has 26 points).
- **Height of the blue cup** (from frame 0, along our table normal, cm; `eval10/profile_eval10.txt`):

| frames | track (S2) | V1 / V3 | V4 / V4p (post hoc) | V3p |
|---|---|---|---|---|
| f55–95 (fist on, beige above) | +0.0 to +1.5 | +1.53 | +0.06 | = track |
| f100–117 (nest, hands on) | +3.1 to +3.7 | +1.53 | +0.06 | = track |
| f122–160 (hands off) | +1.6 to +2.2 | +1.53 | +0.06 | +0.05 |
| horizontal from f0 (end) | 4.10 | **3.71** (held f44 pose) | 4.10 (tracked) | 4.62 |

- **Beige over blue, f130–160:**
  - track +2.2 to +2.8 cm; V1 +2.85; V3 +3.2; V4 +4.3; **V4p +3.2**;
  - ep11 mocap +3.17 (another episode, given only as a scale).
- **Blue cup's lowest collision point vs our table** (last 40 frames): track +1.68 cm, V1/V3 +1.30, **V4/V4p −0.20** (its
  frame-0 value −0.11).
- **Pieces penetration, frames over 2 mm:** track 81, V1 84, V3 45, V4 39, V4p 23.
- **Overlays:**
  - `eval10/e10_s12_overlay.png` (track red, V1 cyan, V3p magenta, beige yellow; f0/44/53/90/105/117/130/160);
  - `eval10/e10_s12_overlay_V4p.png` (same with V4p).
  - The ego camera looks down, so the overlays show the horizontal effect (V1's 0.8 cm offset from f53) more than the
    height.
- **Reading:**
  - The pre-registered rule removes the eval-10 lift only partly, because the pre-nest pose falls in the slide.
  - V4p is the version that does what [H-NEST] intends on eval 10: on the table at its frame-0 height, slid by the track,
    beige seated by physics.
  - It differs from V1 only where ep11 cannot test it (a slide before the nest).
  - V4p needs its own pre-registered test before any eval use. The ep11 rollout gate can carry V4p as a second arm at no
    extra perception cost.
- **Known limit [M, synthetic, `tests/test_refine_s12.py`].** nested(t) is evaluated on the tracked outer. If the
  tracked lift exceeds the true centre offset (about 3 cm) for more than 5 frames, the window ends and the hold releases.
  - This did not happen on ep11 (P_o or the scan-template track) or on eval 10: their minimum beige-over-blue offsets
    were +1.0, +0.3 and +1.4 cm.
  - A hysteresis version (test against P* once a window has started) would remove the risk [H, untested].

## 5. Option (a), masking re-track: specification, CPU mocks, cost
**Change.** `perc2_mask_others.patch` against `pipeline/perc2.py` (sha256 7669e396…), not applied, uses
`pipeline/occluder_mask.py`. It compiles; GPU-untested.
- **Off by default.** `MASK_OTHERS=0` runs the existing object-major loop unchanged.
- **`MASK_OTHERS=1` (frame-major loop).**
  - Frame 0: registration and the guard's retry exactly as today.
  - For each frame i ≥ 1:
    - every roster object is rendered with nvdiffrast at its frame i−1 pose (`MASK_HULL=1`: its convex hull);
    - for object a, the pixels whose front-most render is another object (`MASK_MODE=render`) are hidden from
      `track_one`: depth 0, gray set to the frame's median, dilated `MASK_DIL`=3 px;
    - with the default `MASK_MODE=depth`, only those pixels where our measured depth matches the other object's render
      within `MASK_TOL`=1 cm, and better than object a's own render, are hidden.
  - TRACK_GUARD re-detection and registration use the raw frame.
  - Writes `mask_others.json` (masked pixel counts per frame).
- **CPU mock** (`scripts/m10_perc2_mock.py`): runs the patch's block verbatim with stubs (CPU splat renderer for
  nvdiffrast; a FoundationPose stub that returns the stored track) on ep11 frames 0/63/64/129/130.
  - Wiring is checked: the hidden pixels equal an independent recomputation of the masks on every call, in every mode.
  - Images: `results/perc2_mask_mock_ep11_hull{0_render,1_render,0_depth}.png`.
- **What the mock shows [M].** With library_v3's beige template, which is partial and lopsided (extents 5.1 × 7.1 ×
  16.5 cm, 42 % unknown voxels) and interpenetrates the blue cup at the tracked poses, the masks hide most of the blue cup:
  - mesh render: 80 % (f64), 83 % (f130) of its projected silhouette;
  - hull: 81 % / 89 %;
  - depth mode: 63 % / 77 %, including its lower wall at f130.
- **ICP proxy (`scripts/m10_icp_proxy.py`).** A depth-only stand-in for `track_one`: trimmed point-to-plane ICP of our
  blue mesh, chained over the 33 depth-grid frames in the window, started from P*, with a 3 cm step cap. Heights are
  relative to P* in cm; the track has +5.4 at f67 and +2.4 at the end.

| chain | median | peak | end | reading |
|---|---|---|---|---|
| raw (today's input) | +3.5 | +5.3 | +3.8 | reproduces the lift from depth alone [M, proxy] |
| table removed | +3.5 | +5.3 | +3.8 | the table is not the cause |
| inner cup masked | −6.1 (accepted steps) | +0.2 | −6.1 | no axial anchor: slides down; 13/33 steps over the cap |
| inner cup masked, table removed | −5.1 | +0.4 | −4.2 | same |
| inner + hands masked | – | – | +0.1 | no points under the fist (19 frames skipped); 12 of 14 later steps over the cap |

- **Prediction [H].** The masking re-track with library_v3 templates alone would not reach the pre-registered T2 bar
  (ep11 blue \* ≥ 0.95, falsified below 0.90). With the inner cup masked, the outer cup's height along its axis is
  unobservable, so TRACK_GUARD would end up holding it about 2 cm under the table rather than 2.5–5 cm above it.
  - FoundationPose also uses the gray image, so the rim and base edges may anchor it where depth does not. Only the GPU
    run can tell.
  - What would falsify the prediction: ep11 blue \* ≥ 0.95 with `MASK_OTHERS=1` alone.
- **Job (needs the owner's go-ahead; not launched).**
  - One perception box: RTX PRO 6000, on demand $1.45–1.65/h (`docs/runbook-vast.md`).
  - Phase-1 machinery (`ops/jobs/perc_leak.sh`) with one new arm `m` = P_o templates + `MASK_OTHERS=1 MASK_MODE=depth
    MASK_DIL=3`, output `perc2mask`.
  - Same depth caches and hands (`phase1/inputs.tsv`). Run id `<date>-orcM-<sha>` (refused by `tools/no_oracle.py` as
    the job requires).
  - Episodes: all 20 public (no-harm check), plus a repeat of ep11 (determinism). Then eval 10 with `SPLIT=eval`
    (cached `cache/depth/eval/ep10`) for a GT-free look only.
  - Scoring on this VM: `m10_score.py` with the new arm, and S12 V3 applied on top of the masked track as a second
    reading.
  - Cost: about 22 perc2 runs, comparable to one Phase-1 box (21–29 min, $0.65–0.85 actual) → **≈ $0.8–1.2 [E]**.
  - Code first: apply the patch, review, and a CPU syntax and mock check (above). Add the arm in `perc_leak.sh` and
    `tools/leak_p1.py` (outputs `perc2mask`).
  - Pass rule (T2, pre-registered in `../../leak-decomp-20261030/tracker-fix/PLAN.md`): ep11 blue \* ≥ 0.95, no episode
    −0.01, repeat identical.
- **Value [E].** On eval 10 it duplicates S12. Its own extra (moving containers: evals 32, 33, 5, 1) is ≤ +0.003 (ep11
  DIAG Fix 2). Given the mock, I rank it below the S12 rollout gate.

## 6. Not done / caveats
- No rollout. The LB value rests on orcB's twin gap (one seed) and [E] recovery fractions.
- No holdout. ep11 is the only public cup nest; V1 matches S6 on it.
- V4 / V4p are post hoc and untested where they differ from V1 (eval 10's slide).
- The depth veto was never triggered, so it has no measured value.
- `refine.se3_log`'s small-angle threshold (1e-8) can divide by zero on float32 round-trips of held poses. It is worked
  around in `nest_physics.py`; any future refine chain that holds a pose should do the same.
