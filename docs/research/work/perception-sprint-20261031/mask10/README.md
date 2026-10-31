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
(filled in after scoring)
