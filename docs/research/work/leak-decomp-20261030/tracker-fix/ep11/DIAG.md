# ep11 tracker diagnosis: what goes wrong, and GT-free fixes (30 Oct 2026, ~22:45 UTC)

ep11 is the public twin of eval 10: two cups, the beige cup is stacked into the blue one. This is a public-episode oracle diagnostic. Mocap and scans are
read only to score and diagnose. Every proposed fix is GT-free. CPU only on this VM, $0, no GPU, no Kaggle, no commit.
Labels: [M] measured, [E] estimate, [H] hypothesis.

## Verdict
- **The starting hypothesis is refuted [M].** It said the inner (beige) cup drifts or sinks while it sits inside the outer
  one. In fact the inner cup is tracked well while nested: with the scans its median error is 0.66 cm and its AUC is 0.997
  over the 97 nested frames. With our mesh its error is a constant ~2 cm, and that error is already there at frame 0
  (1.94 cm before the nest, 1.96 cm during it).
- **The failure is the outer blue cup.** In mocap it never moves (0.5 cm over the whole episode). A left fist holds it
  from about frame 20, and the beige cup is lowered into it over frames 40–71. During that time the blue cup's track
  **rises along its own axis**:
  - peak lift +5.3 cm with our mesh (P_o) and +7.9 cm with the scans (P_s), at frames 60–69;
  - still about +3.7 cm while the hands stay on (frames 72–101);
  - and it **stays about 2.5 cm high** after the hands leave (frames 102–136).
- The lift is almost pure height: translation ≈ dz, and axis tilt stays ≤ 6°. It happens with both templates and is
  bit-identical in the repeat run, so neither the template nor GPU noise causes it. The fist alone does not cause it:
  over frames 20–39 the fist is already on the cup and the error stays ≤ 0.65 cm.
- **Error source:** a jump at an event (the nest), then a held offset. It is not a frame-0 initialisation error, not
  slow drift and not an identity swap. Cup spin is free and unscored, so it plays no part.
- **P_o has a second, separate error [M]:** a constant beige offset from frame 0.
  - The beige cup sits +1.5 cm too high relative to the blue cup and tilts 4° more than it should.
  - Our beige mesh's base extends **1.8 cm beyond the scan's base** (measured with X\*_geom). The tracker rests that
    base on the table, so the real cup body ends up too high.
  - This is the template-shape leak (L2): P_s beige 0.994 vs P_o 0.886.
- **The lift explains the "impossible nest" in eval 10's reference [M on ep11, H for eval 10].** On 26 Oct the
  reference was read as having the beige cup nested deeper than the shapes allow (113 cm³ overlap, beige shrunk 8 mm as
  a workaround). That reading is now explained:
  - It is the blue cup that is too high. Beige minus blue height at f130: P_s +0.28 cm, P_o +1.93 cm, mocap +3.16 cm.
  - After rule F1 (below), the gap is +2.79 cm with P_s and +4.28 cm with P_o: no overlap.
- **Fix F1, a GT-free static hold, tested on CPU [M].** Rule: freeze any object whose own perceived horizontal travel
  stays under 2 cm.
  - ep11 P_o: 0.874 → 0.943 in the \* convention, 0.898 → 0.967 in lib.
  - ep11 P_s: 0.908 → 0.997.
  - On all 20 public episodes it freezes exactly the objects that are static in mocap, with no false positives and no
    episode worse.
  - It still needs the rollout gate below before any eval use.

## Inputs and commands (this VM, repo a960523 + the scripts in `scripts/`)
- Tracks: `runs/20261030-orcP1b-87fc869/results/leak_p1/ep11/{perc2,perc2rep,perc2scan}/poses_world_vo.npz`.
  - They were already in `$S/leak/p1/runs/...` (`S` = the session scratchpad); nothing was downloaded.
  - `perc2` and `perc2rep` are bit-identical (md5 6e2c2ff5…), so the repeat noise is 0 on ep11.
  - `perc2scan` md5 e1512668….
- X\*_geom: `../../tierA/xstar_geom.json`.
- Hands: `$S/refine/in/ep11/hands_refined.npz`, used only as an occlusion proxy.
- Mocap: `$S/map/scoring/t3/ep11.parquet`.
- Video: cam a, `$S/hfds/.../episode_000011.mp4`.
- Scoring: the kit chain of `tools/xstar_fit.py` (`score_track`): \* = X\*_geom, lib = X_kit.
  - ADD is symmetry-aware: cups modulo spin, at 1°.
  - dz is along mocap +z (up).
  - Everything is computed after the kit's frame-0 scene alignment: slot 0 = blue cup, pinned by its frame-0 centre and
    axis plus the direction from blue to beige.
- Commands (`PY=$S/map/scoring/venv/bin/python`, run from `$S/leak/diag_11`):
  1. `$PY -I scripts/diag11.py diag11.json`: per-frame errors, phases, hands, nest geometry.
  2. `$PY -I scripts/f0geom.py`: frame-0 heights and tilts against our own table plane.
  3. `$PY -I scripts/static_hold_test.py static_hold_test.json`: rule F1 on all 20 episodes, P_o and P_s, \*.
  4. `$PY -I scripts/f1_lib_and_upright.py f1_lib_upright.json`: F1 in lib, plus the cup-upright test U1/U2.
  5. `$PY -I scripts/overlay11.py png/`: overlays.
- Copies of the scripts and JSON outputs are in this folder.
- Score check: P_o \* 0.8739 and P_s \* 0.9081 reproduce `tierA/FRAMES.md` and `p1_check_oracle.json`.
  - The 0.863 quoted for P_s is perc2's own unregistered scan-frame AUC, a different scorer.

## 1. Error per object and phase [M]
What happens, from mocap and the cam-a video (`ep11_raw_cam_a_grid.png`):
- The blue cup never moves.
- The beige cup is lifted from f23, carried over the blue cup, entered at f40, lowered into it by f71, and rests nested
  from f72 (its centre 3.2 cm above the blue cup's).
- The left hand holds the blue cup on the table from about f20 to f101. Both hands are away from f102.

Table cells are median / max ADD in cm, then AUC. Hand distance is the nearest hand joint to the cup centre in cm (the
occlusion proxy; about 4 cm means touching).

| phase | hand blue / beige | beige vs blue: height, radial cm | blue P_o | blue P_s | beige P_o | beige P_s |
|---|---|---|---|---|---|---|
| A f0–19 rest, hands approach | 5.4 / 14.3 | 0.2, 17.4 | 0.19 / 0.53, 1.000 | 0.11 / 0.33, 1.000 | 2.00 / 2.27, 0.881 | 0.63 / 0.89, 1.000 |
| B f20–39 fist on blue, beige lifted | 4.3 / 7.8 | 11.7, 15.6 | 0.28 / 0.65, 1.000 | 0.31 / 0.64, 1.000 | 1.75 / 2.96, 0.903 | 0.86 / 2.00, 0.972 |
| C f40–59 beige enters blue rim | 3.8 / 8.0 | 15.0, 1.2 | 0.92 / 1.36, 0.981 | 1.38 / 2.03, 0.944 | 2.15 / 2.40, 0.825 | 0.89 / 1.17, 0.984 |
| **D f60–71 beige lowered into nest** | 4.2 / 4.4 | 5.5, 0.7 | **2.10 / 5.33, 0.760** | **5.59 / 7.93, 0.406** | 2.01 / 2.16, 0.865 | 0.70 / 0.91, 1.000 |
| E f72–101 nested, hands on | 4.3 / 3.7 | 3.3, 0.7 | 3.76 / 4.39, 0.662 | 3.61 / 4.22, 0.688 | 2.03 / 2.20, 0.867 | 0.70 / 0.83, 1.000 |
| F f102–136 nested, hands off | 27.5 / 27.5 | 3.2, 0.6 | 2.41 / 2.54, 0.841 | 2.69 / 3.08, 0.809 | 1.52 / 1.83, 0.938 | 0.38 / 0.54, 1.000 |
| whole episode | | | 1.75 / 5.33, **0.862** | 2.58 / 7.93, **0.823** | 1.94 / 2.96, **0.886** | 0.65 / 2.00, **0.994** |

Blue-cup height error dz in cm (median, max):

| phase | P_o | P_s |
|---|---|---|
| A | −0.03, 0.15 | 0.04, 0.25 |
| B | 0.01, 0.36 | 0.20, 0.45 |
| C | 0.53, 1.28 | 1.29, 1.96 |
| D | 2.02, 5.28 | 5.56, 7.91 |
| E | 3.75, 4.37 | 3.59, 4.19 |
| F | 2.38, 2.51 | 2.66, 3.07 |

Axis tilt stays ≤ 6.3°. Blue's horizontal travel in the track is ≤ 1.0 cm (P_o) and ≤ 0.8 cm (P_s).
Per-frame values are in `diag11.json`.

Where the error comes from:
- **Blue: a jump at the nest, then a held offset.**
  - Error stays ≤ 0.65 cm over the 40 frames before the nest, in both arms, fist included: blue AUC 1.000 un-nested
    vs 0.805 (P_o) and 0.749 (P_s) nested.
  - Frame 0 is exact by construction, because slot 0 is pinned by the scorer's alignment.
- **Beige with P_o: a frame-0 initialisation error carried as a constant body offset.**
  - At frame 0: dz +1.93 cm and 5.0° tilt. A rigid best fit over all frames would recover beige 0.996 (oracle check).
  - A world-frame re-anchor at frame 0 is meaningless for a free-spin cup, so it was replaced by the best fit.
  - Our-plane geometry at frame 0: P_o beige axis 5.7° from our table normal (mocap 1.7°); beige sits +1.69 cm above
    blue along the normal (mocap +0.19 cm).
  - Our v3 beige mesh, in scan frame by X\*_geom, spans −6.74 … +10.62 cm along the cup axis against the scan's
    −8.37 … +8.84 cm: the base protrudes 1.78 cm beyond the scan's base. The v5 beige in `library_v3x` has the same
    protrusion (+1.96 cm).
- **Beige with P_s:** fine everywhere (≤ 2.0 cm max, while being carried).
- **No identity swap.** Hungarian assignment at frame 0 is blue → proposal 1, beige → 2. Both tracks follow the right
  cup: the beige track stays within 3 cm while the cup travels 25 cm.
- **No guard event.** `track_guard.json` shows 0 for every counter. TRACK_GUARD tests only "below the table", and here
  the cup goes up.

## 2. The hypothesis, against the evidence
- *"The inner cup is hidden inside the outer cup and drifts or sinks"*: **refuted.**
  - The inner beige cup's P_s error while nested (phases D–F) is 0.38–0.70 cm median, AUC 1.000.
  - Its P_o error is the same constant as before the nest.
- *"Cups are axisymmetric, so spin is free"*: true but irrelevant. The scorer and the analysis are spin-free.
  - The blue track's rotation span of 33–41° (spin included) has no effect on the score.
- **What does happen [M]:** the outer cup's track climbs toward the top of the stack.
  - It starts when the beige cup enters the blue rim (C), peaks while the beige is pushed down (D), and keeps about
    2.5 cm once things settle (F).
  - At F the blue cup's tracked centre is only 0.28 cm (P_s) below the beige centre; the truth is 3.16 cm.
- **Mechanism [H].** With the beige cup inside it and the fist around it, the blue cup shows FoundationPose only a band
  of wall:
  - its rim and interior are replaced by the beige cup's surfaces, which sit higher;
  - its lower wall is behind the fist.
  - So the cup's position along its own axis is nearly unobservable (the aperture problem of a cylinder seen without
    its ends). The refiner, which starts from the previous pose and fits depth, slides it up toward the stack's top
    surface. When the hands leave, the base reappears and pulls it only part of the way back (3.7 → 2.5 cm), because
    the rim is still covered.
  - Fix 2 is the experiment that falsifies this mechanism.
- Overlays (blue cup: green = mocap, magenta = P_s, red = P_o; yellow = mocap beige; mocap is placed in the camera by a
  rigid fit to P_s over f0–39, residual median 0.41 cm, for display only):
  - `ep11_blue_lift_overlay_grid.png`: f0/30/45/63/69/90/130.
  - `ep11_f063_blue_overlay.png`: the peak.
  - `ep11_f130_blue_overlay.png`: the held offset after release.
  - `ep11_raw_cam_a_grid.png`: raw frames showing the fist on the blue cup and the insertion.

## 3. Fixes (GT-free), tests that would falsify them, eval exposure, value

### Fix 1 — static hold F1 (post-processing; primary) [M at reference level]
**Rule** (inference side; uses only our tracks, our mesh, our frame-0 depth; no mocap):
- Fit the table plane with `det_rules.table_plane` on our frame-0 depth, as perc2's TRACK_GUARD does.
- Per object, take c(t) = our mesh's vertex centroid in world coordinates.
- Freeze the object when both hold:
  - its horizontal travel max_t |c(t) − c(0)| projected on the plane is under 2 cm;
  - for objects that are not axisymmetric, its rotation stays under 10° (the cups skip this test).
- A frozen object takes its frame-0 pose on every frame.

**Where:**
- A new step S6 in `pipeline/refine.py`, run before S2. It is whole-episode and offline, so it cannot be done inside
  perc2's online loop.
- Log the frozen objects in `pose_opt.json`.
- mkref is unchanged (`--snap per_object`).

**Measured, CPU, Phase-1 tracks, all 20 public episodes** (`static_hold_test.json`, `f1_lib_upright.json`):
- It freezes exactly the objects that are static in mocap (≤ 1 cm), at every threshold from 1 to 3 cm:
  - ep11 blue cup;
  - the rack in ep12, 13, 26, 27 and 31.
- Margin: static objects' perceived horizontal travel is ≤ 1.0 cm. The smallest for any moving object is 4.3 cm
  (ep40 dust pan, ep44 pot, both lifted mostly straight up).
- Gains:

| arm | ep11 | ep31 | ep12 | ep13 | ep26 | other 15 eps | mean over 20 | better / worse |
|---|---|---|---|---|---|---|---|---|
| P_o \* | **+0.069** | +0.034 | +0.005 | 0 | +0.002 | 0 | +0.0055 | 4 / 0 |
| P_o lib | **+0.069** | 0.000 | +0.0001 | +0.007 | +0.002 | 0 | +0.0039 | 4 / 0 |
| P_s \* | **+0.089** | +0.005 | 0 | +0.0001 | +0.001 | 0 | – | – |

- The oracle upper bound ("freeze what mocap says is static") equals the rule's result exactly.
- Mean lib +0.0039 is below the refine study's generic +0.005 gate. The gain sits on one episode, and no episode drops.

**Public test that would falsify it** (pre-register before running; GPU, needs the owner's go-ahead):
- Twin: ep11, eval 10's recipe as Phase-2 cell c1:
  - grasp lock gl10A2: SF=0 REPLAN=1 EVOLVE=0, ev10 pieces;
  - the Phase-1 P_o bundle, then refine S2 + S6, then mkref;
  - seeds 42 and 43; NREP 10.
- Compare with the same recipe without S6 on the same bundle (c1 itself).
- Falsified if the seed mean of the rollout ADD-AUC vs mocap rises by less than +0.05, or if sim_vs_ref of the S6 arm is
  < 0.70. For reference: P 0.595, O 0.940, orcB.
- Optional third arm: the same reference with the unshrunk ev10 beige pieces. It tests [H] that the 8 mm shrink is no
  longer needed once the blue cup stays on the table.
- Reference-level guard, re-run with the committed code on both `refine/in` and Phase-1 P_o/P_s:
  - the frozen set equals the mocap-static set on 20/20 episodes;
  - no episode Δ < −0.002 in lib or \*.
- Cost [E]: about $1.3 per grasp-lock training (orcB's $7.80 for 6). So about $2.6 if c1 already runs in Phase 2, about
  $5.2 if not.

**Before eval use:**
- Run S6 on the eval tracks (GT-free) and list what it freezes, with each frozen object's vertical excursion.
- Check every frozen object visually with `pipeline/track_overlay.py`.
- Retrain eval 10 with 2 seeds (about $2.6) and swap only under the multi-draw rule.

**Risk [H]:**
- An object lifted straight up with less than 2 cm of sideways travel would be frozen wrongly. Eval 5's pot, lifted with
  the spoon inside, is the candidate. The overlay QA, and a rule that the frozen object's vertical excursion must coincide
  with another roster object above its footprint, guard against it.
- If eval 10's blue cup is actually lifted (note 15 says "blue then held"), F1 does not trigger and nothing changes.

**Eval exposure (roster + note 15):**

| group | evals | twin evidence |
|---|---|---|
| static container receives an object | **10** | ep11 (this file) |
| | 30 (sweeper scrubbing in the rack) | ep31: \* +0.034, lib 0 |
| | 14 (cup onto rack) | ep12/13 |
| | 28 (pot onto rack) | ep26/27 |
| | 15, 16 (spoon into the rack tower; rack static all clip) | no twin |
| | 3 (pot held on the table while stirring), if its travel stays < 2 cm | – |
| not covered (the container moves) | 32, 33 (hand-held cup), 5 (pot lifted), 1 (pot dragged) | see Fix 2 |

**LB value [E]:**
- Eval 10 dominates:
  - The twin's P→O rollout gap is 0.345 [M, orcB].
  - With F1 the reference's lib R is 0.967, and the nest is physically consistent.
  - If 30–70 % of the gap is recovered, eval 10 gives (0.74–1.0)/20 × (0.10–0.24) = **+0.004 to +0.012 LB, central
    ≈ +0.007**; the upper bound is +0.017.
- Evals 14, 28, 30, 15 and 16 together add ≤ +0.001: their twins gain ≤ 0.007 in lib, and S is below 0.8 or no twin
  exists.

### Fix 2 — mask the other objects out of the tracker's input (`pipeline/perc2.py`) [H]
- **What:**
  - Track all objects frame by frame instead of one object for the whole episode (the `for a, n in enumerate(names)`
    loop around `est.track_one`).
  - Before each `track_one` on frame i, render the other objects at their latest poses with nvdiffrast (already loaded).
    Set depth to 0 (invalid) and grey out RGB wherever another object lies in front of this object's rendered surface
    or inside its silhouette.
  - Optionally also mask the MediaPipe hand pixels (`hands_refined.npz` uv_a mapped to rectified c).
- **Why beside F1:** it removes the cause, so it also covers moving containers, where F1 cannot act: 32 and 33 (spoon
  into a hand-held cup), 5, and 1. It also covers static containers whose drift moves sideways.
- **Public test that would falsify it** (one GPU perception box with the depth caches reused; about 30–40 min, about $1
  [E]):
  - Re-track all 20 episodes with masking. F1 is off, P_o templates are used.
  - Pass if ep11 blue \* ≥ 0.95 (now 0.862), no episode drops by more than 0.01 \*, and the repeat run is identical.
  - Falsified if ep11 blue \* < 0.90. The lift would then not come from the inner cup's surfaces; the fist/aperture
    mechanism would remain, and Fix 2 would be dropped.
- **LB [E]:**
  - On static-container evals it duplicates F1.
  - Its own extra on 32, 33, 5 and 1 is unknown, ≤ +0.003 [E]. Their losses were attributed to grasp and carry
    (hull census, 26 Oct).

### Fix 3 — beige template base (mesh session) [H]; the P_o-only constant offset
- **What:** a GT-free flat-base rule for our cup reconstructions. Cut the base where the lathe radius profile ends
  (approach-2 profile, `pipeline/lathe_collision.py`), so the template no longer stands on a 1.8 cm protrusion. Rebuild
  `beige_cup.glb` for tracking.
- **Already tested here and falsified as a post-hoc fix [M]:** a frame-0 "cup upright" body correction on P_o (U1 = axis
  onto the table normal, U2 = U1 + base snap; `f1_lib_upright.json`):
  - It cannot act on the beige cup: the PCA axis of our v3 beige mesh is 30° off.
  - It is mixed on the blue-cup episodes: ep12 U2 −0.015, ep22 U2 +0.013, ep21 U1 −0.005 and U2 +0.001.
- **Public test that would falsify it:** re-track ep11 P_o with the new beige template (one perception run, about $0.5
  [E]).
  - Pass if beige \* ≥ 0.95 (now 0.886) and the frame-0 beige-minus-blue height error ≤ 0.5 cm (now +1.5 cm).
  - Falsified if beige \* < 0.92.
  - Only one public beige episode exists, so this is weak evidence. Report it as such.
- **Eval exposure:** 10 (beige in slot 1) and 8 (beige in slot 0, where the scorer's frame-0 alignment absorbs a
  constant offset).
- **LB [E]:** ≤ +0.002. In the rollout a beige cup that is too high settles into the seat.

## 4. Not done / caveats
- Eval tracks were not inspected: this is a public-only diagnostic. The eval-side F1 check is listed under Fix 1.
- No rollout was run. The value of F1 to the leaderboard rests on the eval-10 twin gap (one seed in orcB) and on [E]
  recovery fractions.
- The mechanism of the lift is [H] until Fix 2's test.
- The F1 thresholds (2 cm, 10°) were chosen after seeing these 20 episodes. On public data every threshold from 1 to 3 cm
  gives identical results, but no fresh public holdout exists. The rollout gate above is the real test.
