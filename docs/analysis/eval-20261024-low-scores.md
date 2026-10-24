# Why the low-scoring eval episodes scored low: 24 Oct submission

The submission: Track 3 AUC **0.575** (9th), MPPE 8.7 cm, CD-O 0.405 cm.

Sources:
- the 20 packed official rollouts, `results/submissions/20261024-track3/`;
- per-object diagnostics, `diagnostics.json` and `tools/eval_diagnostics.py`;
- per-checkpoint curves, grasp-lock hold windows, grasp-search and perception logs (store,
  `runs/20261024-pack-31ef267`);
- **the 20 videos** (store, `runs/20261024-vid-7f31368/results/eval_videos/`). Each is real camera | simulated objects
  (filled) and robot hands (green / magenta lines) drawn on the camera, with our reference as a white outline | 3-D
  simulation. The policy is replayed the way the official evaluator plays it.

No ground truth exists for eval episodes. Everything here compares the simulation with **our own reference** (the
perceived path, sim_vs_ref), checks that reference for physical plausibility, or compares the white outline with
the real camera image in the videos. Labels: **[M]** measured, **[V]** seen in the video, **[I]** inferred,
**[H]** hypothesis with the test that would falsify it.

**Revised after watching the videos.** Eval 30 is a perception failure, not a support one, and evals 14 and 33 share
its pattern. The pitcher and board meshes are worse than the first draft said.

## 1. Where the 0.425 of lost AUC goes

There are two factors. The first is how well the robot follows our reference: the packed rollouts average 0.710 [M].
The second is how close that reference is to the truth: it takes 0.710 down to 0.575 [M, Kaggle]. On the public
twins the second factor cost only 3–4 % [M].

| Loss | Size on the 20-episode mean | Main episodes |
|---|---|---|
| A. **Broken or unstable meshes**: the object cannot stand, or the task is physically impossible with our shape | ≈ 0.08 [I] | 20 (pitcher is a twisted shell), 10 (beige cup open shell), 25 (boards lack their slots) |
| B. **Perception loses an object to the person's wrist** (white watch) or the track becomes impossible | ≈ 0.09 [I] | 30 (sweeper detected on the wrist from frame 0), 14 and 33 (cup jumps to the wrist when hidden), 8, 32 |
| C. **Grasps not acquired, slipping, or misplaced** | ≈ 0.11 [I] | 1 (lid never lifted), 19 (dust pan), 25 (boards), 33 spoon, 28, 16, 3 |
| D. **Our reference vs the truth**, invisible in sim_vs_ref | ≈ 0.135 [M total]; spoon ≈ 0.12 [I] | the 10 spoon episodes |

Rows A–C are 1 − sim_vs_ref of the episodes in each class, summed and divided by 20. Episodes with several causes
are split by object. Row D is 0.710 − 0.575. The spoon share assumes the non-spoon episodes lose 4 %, as their public
twins did.

## 2. All 20 episodes

sim_vs_ref of the submitted rollout (packed), with the main cause of each loss.

| Eval | Objects | Score | Main cause |
|---|---|---|---|
| 38 | dust pan | 1.000 | — |
| 37 | spoon | 0.998 | — (D: spoon accuracy against the truth unknown) |
| 36 | spoon | 0.991 | — (D) |
| 35 | spoon | 0.983 | — (D); the outline sits on the real spoon in the video [V] |
| 5 | pot + spoon | 0.974 | — (D); a bad mode exists, one of 5 earlier rollouts at 0.39 |
| 6 | pot + spoon | 0.971 | — (D) |
| 15 | rack + spoon | 0.958 | — (D) |
| 3 | pot + spoon | 0.875 | pot slips during its hold (C), mild |
| 16 | rack + spoon | 0.850 | spoon left 12.7 cm off after its hold (C) |
| 32 | blue cup + spoon | 0.836 | cup track jumpy and below its start (B), but held, so the robot follows |
| 8 | beige cup + pot | 0.823 | beige cup low-confidence detection (0.22), never held (B) |
| 28 | rack + pot | 0.751 | pot placed 8.5 cm off; the rack is knocked at the end (C) |
| 19 | sweeper + dust pan | 0.627 | dust pan grasp weak (C) |
| 14 | blue cup + rack | 0.557 | cup placed upside-down on the rack, then the track jumps to the wrist (B) |
| 30 | sweeper + rack | 0.472 | sweeper detected on the person's wrist, not in the rack (B) |
| 33 | blue cup + spoon | 0.421 | cup track jumps to the wrist (B); spoon grasp weak (C) |
| 10 | blue cup + beige cup | 0.342 | beige cup mesh is an open shell and falls over at the start (A) |
| 20 | blue cup + pitcher | 0.336 | pitcher mesh is a twisted shell and falls flat at the start (A) |
| 25 | two boards | 0.232 | boards must be slotted into a cross; our meshes have no slots (A), and the grasps fail (C) |
| 1 | pot + lid | 0.205 | the robot never lifts the lid off the pot; the pot turns in the hand (C) |

## 3. The low scorers, one by one

**Eval 1, pot + lid: 0.205 (grasp).**
- [V] The person lifts the lid off the pot, puts it on the table, then lifts and tilts the pot by its handle.
  The white outlines sit on the real pot and lid all the way, so **perception is good**.
- [V] In the simulation the lid stays on the pot all episode. The pot turns in the robot's hand, with its handle
  pointing the wrong way.
- [M] The lid leaves the reference 12 frames after its hold starts (f38 → f50), and the pot at the start of its
  hold (f96). The mean rotation error is 65–74°.
- [M] No checkpoint lifts the pot to its reference height (3–9 cm against 12.8 cm).
- Cause: the lid pick (a flat disc with a small knob, seated in the pot) and the pot handle grasp (C).

**Eval 25, two boards: 0.232 (mesh + grasp).**
- [V] The person stands board 1 up, picks up board 2 and **slots the two together into a cross**. Our outlines
  follow this correctly.
- [V] In the simulation board 1 is lifted and stands briefly (frame 120), then both boards end flat on the table,
  away from the cross.
- [M, mesh audit 22 Oct] Our board meshes lack the two slots: the "1.0 × 11.3 × 1.2 cm column" that overlaps
  between the boards is the missing notch. **With our meshes the cross cannot be assembled at all.**
- [M] The copied grasp on board 2 touches it with 1 finger (gap 23 mm). All 7 checkpoints score 0.14–0.27.
- The public twin ep24 scored 0.241 against mocap.
- Cause: mesh (A) plus grasp (C). Needed: the slots in the mesh, and the board edge primitive (TODO #24).

**Eval 20, blue cup + pitcher: 0.336 (mesh).**
- [V] The person holds the cup and lifts the pitcher to pour into it. The outlines follow both well, so
  **perception is good**.
- [V] In the 3-D view **our pitcher mesh is a thin, twisted shell**, not a closed watering can. It tips over by
  f8 (tilt 35° [M]) and lies flat for the rest of the episode. Its reference rises 36 cm; no checkpoint lifts it.
- Cause: a broken mesh (A). A base completion alone, as in the public audit, would not be enough; the body itself
  needs rebuilding.

**Eval 10, blue cup + beige cup: 0.342 (mesh).**
- [V] The person lifts the beige cup and stacks it into the blue cup. The outlines follow both cups, so
  **perception is good**.
- [V, M] In the simulation the beige cup falls over at the start (tilt 35° at f3, 84° at f10). In the 3-D view it
  is an open shell with no bottom, matching the 22 Oct audit: "2 pieces, no bottom".
- Cause: a broken mesh (A).

**Eval 30, sweeper + rack: 0.472 (perception).**
- [V] The real sweeper stands upright **inside the dish rack** at frame 0; the person lifts it out and uses it.
- [V] **Our detection put the sweeper at the person's left wrist**, next to a white watch, off the table. The white
  outline then follows the wrist, never the sweeper. Its detection score was the lowest of all 40 objects (0.20).
- [M] This explains every measured symptom: the sweeper started "7 cm under the table", the support fallback lifted
  it at the table edge, it fell to the floor (z 3.8 cm by f20), and no hold was detected because the real hand never
  touches the wrongly placed sweeper.
- [V] The rack is tracked well.
- Cause: detection (B). The support fallback did what it was designed to do on a wrong input.

**Eval 33, blue cup + spoon: 0.421 (perception + grasp).**
- [V] The person holds the cup up in the left hand and works the spoon in it with the right. The outline is right
  at first (f30). Once the hand covers the cup, **the outline jumps to the left wrist and watch** (f160, f250) while
  the real cup is held higher up.
- [M] The cup hold is detected only from f17 to f48. After that our reference moves the cup 233 cm of path with no
  hand on it, tilting up to 144° and dropping 14.6 cm.
- [M] The spoon grasp was weak: the search went only 0.11 → 0.32, and the spoon is lost at f110.
- Cause: perception (B) plus grasp (C). Its twin eval 32 scored 0.836 because the cup stayed tracked and held.

**Eval 14, blue cup + rack: 0.557 (perception).**
- [V] The person picks up the cup, turns it over and puts it upside-down on a rack peg.
- [V] The outline follows the cup until it reaches the rack. Then **it drops to the left wrist near the table
  edge**: our reference cup goes 5 cm below the table top [M], which is impossible.
- [V] The simulated cup ends near where the real cup goes, so the truth score is probably better than 0.557 here
  [I].
- [V] The simulated rack is knocked a few cm.
- Cause: perception (B). The public twin ep12 scored 0.868 because the cup stayed tracked.

**Eval 19, sweeper + dust pan: 0.627 (grasp).**
- [M] The dust pan is lost at f26, during its hold.
- [M] The grasp search reached only 0.18 → 0.36 (median hold error 14.6 cm); ep18's pan reached 0.50.
- [M] The 10M checkpoint was best (0.63); later ones dropped to 0.27.
- Cause: the chaotic plate grasp seen on ep18; this time the search found no good basin (C).

**Eval 28, rack + pot: 0.751.**
- [M] The pot follows its reference through the lift (2–5 cm off). It is placed 8.5 cm off at the end, and the
  rack is knocked 15.8 cm in the last frames.
- Cause: placing the pot into the rack (C), mild.

**Eval 8, beige cup + pot: 0.823.**
- [M] The beige cup is never held. Its detection confidence is low (0.22). It was placed 7 cm under the table and
  lifted by the fallback, and its reference jitters (121 cm of path while unheld).
- Cause: perception (B). Mild in sim_vs_ref, but probably worse against the truth.

## 4. Pattern: the person's wrist and white watch

- [V] The person wears a white watch on the left wrist in these eval videos (14, 20, 25, 30, 33, 35 at least).
- [V] In 30, 33 and 14 our object track ends on that wrist. In 30 the sweeper was detected there from frame 0. In 33
  and 14 the cup track jumped there when the hand or the rack hid the cup.
- [H] The detector and tracker accept wrist and watch pixels as the object when the object is hidden.
  - Test: run frame-0 detection and tracking with the hand and forearm pixels removed. MediaPipe already gives us the
    hands. If the outline still goes to the wrist in 30, 33 and 14, the hypothesis is wrong.
- Generic fixes, no per-episode choices:
  - remove hand and forearm pixels before detection and tracking;
  - reject a detection or track that sits on the wrist or moves with it while no hold is detected;
  - forbid object poses below the table;
  - hold the last good pose while the object is hidden.

## 5. The spoon and the perception gap (D)

- [M] sim_vs_ref 0.710 against a Kaggle AUC of 0.575; the public twins lost 3–4 %.
- [I] If the non-spoon episodes lose 4 %, the 10 spoon episodes average **≈ 0.64 AUC against a sim_vs_ref of
  0.886**. That is about 0.12 of the total, the largest single item.
- [V] In eval 35 the spoon outline sits on the real spoon throughout, at least in 2-D. Gross 2-D tracking failures
  are therefore not the explanation there. Depth along the camera ray, roll about the handle, and the mesh itself
  cannot be judged from this view.
- [H1] Our spoon mesh is a parametric template with fixed dimensions. Kaggle aligns it with the hidden scan, and if
  that alignment lands flipped or offset, all 10 episodes pay.
  - Test: our template's alignment against a stand-in on ≥ 6 seeds, including flips along the handle.
- [H2] Depth or roll errors of the spoon track.
  - Test: stereo depth of the spoon pixels against our track depth on eval frames. This needs no ground truth.

## 6. What fixes what, by expected gain

All gains are estimates, on the 20-episode AUC.

1. **Spoon mesh and pose:** ≈ +0.05 to +0.12.
   - Per-episode spoon fit from the eval video (v5 D10).
   - An alignment and flip check.
   - The stereo depth check.
2. **Meshes rebuilt for the simulation** (the owner's v5 directive): ≈ +0.05 to +0.08.
   - Closed, standing pitcher and beige cup.
   - Board slots.
   - Multi-piece collision shapes.
3. **Perception robust to the hand and wrist:** ≈ +0.04 to +0.08.
   - Hand and forearm masking in detection and tracking.
   - Rejecting tracks that sit on the wrist.
   - The below-table and plausibility guards from §4.
4. **Grasps:** ≈ +0.03 to +0.05.
   - Lid pick.
   - Board edge primitive.
   - More search seeds when a grasp window stays below 0.5 (eval 19 0.36, eval 38 0.35, eval 33 spoon 0.32).

Each fix is validated on public twins against ground truth before it is used. Nothing is changed per episode on
eval data.
