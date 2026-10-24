# Why the low-scoring eval episodes scored low: 24 Oct submission

The submission: Track 3 AUC **0.575** (9th), MPPE 8.7 cm, CD-O 0.405 cm.

Sources:
- the 20 packed official rollouts, `results/submissions/20261024-track3/`;
- per-object diagnostics, `diagnostics.json` and `tools/eval_diagnostics.py`;
- the per-checkpoint curves, grasp-lock hold windows, grasp-search logs and perception logs in the store
  (`runs/20261024-pack-31ef267`).

No ground truth exists for eval episodes, so everything here compares the simulated objects with **our own
reference**, the perceived path (sim_vs_ref), or checks that reference for physical plausibility. Labels:
**[M]** measured on our outputs, **[I]** inferred, **[H]** hypothesis with the test that would falsify it.

## 1. Where the 0.425 of lost AUC goes

The score has two factors. The first is how well the robot follows our reference: the packed rollouts average
0.710 [M]. The second is how close our reference is to the truth: it turns 0.710 into 0.575 [M, Kaggle]. On the
public twins this second factor cost only 3–4 % [M].

| Loss | Size on the 20-episode mean | Main episodes |
|---|---|---|
| A. **Objects cannot stand at the start** (mesh or support) | ≈ 0.09 [I] | 10, 20, 30 |
| B. **Our reference moves an object with no detected hold, or is physically impossible** (perception and hold detection) | ≈ 0.06 [I] | 14, 33 cup, 8, 32 (and 30) |
| C. **Grasps that are never acquired, slip, or misplace** on hard shapes | ≈ 0.13 [I] | 25, 1, 19, 33 spoon, 28, 16, 3 |
| D. **Our reference vs the truth**, invisible in sim_vs_ref | ≈ 0.135 [M total], of which the spoon ≈ 0.12 [I] | the 10 spoon episodes |

Rows A–C are 1 − sim_vs_ref of the episodes in each class, summed over the classes and divided by 20. An episode
with several causes is split by object. Row D is 0.710 − 0.575. The spoon share comes from assuming the non-spoon
episodes lose 4 %, as their public twins did.

## 2. All 20 episodes

sim_vs_ref of the submitted rollout (packed), with the class of each loss.

| Eval | Objects | Score | Main cause |
|---|---|---|---|
| 38 | dust pan | 1.000 | — |
| 37 | spoon | 0.998 | — (D: spoon perception unknown) |
| 36 | spoon | 0.991 | — (D) |
| 35 | spoon | 0.983 | — (D) |
| 5 | pot + spoon | 0.974 | — (D); a bad mode exists, one of 5 earlier rollouts was at 0.39 |
| 6 | pot + spoon | 0.971 | — (D) |
| 15 | rack + spoon | 0.958 | — (D) |
| 3 | pot + spoon | 0.875 | pot slips during its hold (C), mild |
| 16 | rack + spoon | 0.850 | spoon left 12.7 cm off after its hold ends (C/B) |
| 32 | blue cup + spoon | 0.836 | cup reference jumpy and below its start (B), but held, so the robot follows |
| 8 | beige cup + pot | 0.823 | beige cup never held, low-confidence detection (B) |
| 28 | rack + pot | 0.751 | pot leaves the reference while it is placed; the rack is knocked at the end |
| 19 | sweeper + dust pan | 0.627 | dust pan grasp weak (C) |
| 14 | blue cup + rack | 0.557 | cup hold detected for 20 frames only; then the perceived cup sinks below the table (B) |
| 30 | sweeper + rack | 0.472 | sweeper topples and falls off the table at once (A); no hold ever detected (B) |
| 33 | blue cup + spoon | 0.421 | cup track flips after the hold (B); spoon grasp weak (C) |
| 10 | blue cup + beige cup | 0.342 | beige cup falls over at the start (A) |
| 20 | blue cup + pitcher | 0.336 | pitcher falls over at the start (A) |
| 25 | two boards | 0.232 | board grasps never acquired (C) |
| 1 | pot + lid | 0.205 | lid and pot lost right after their grasps (C) |

## 3. The low scorers, one by one

**Eval 1, pot + lid: 0.205.**
- [M] Both objects are in a hold most of the time (pot 214 of 335 frames, lid 262 of 335). The lid leaves the
  reference at f50, 12 frames after its hold starts at f38. The pot leaves at f96, the frame its hold starts.
- [M] The mean rotation error is 65–74°: the objects turn in the hand.
- [M] The grasp search improved the windows only partly: pot 0.39 → 0.56, lid 0.23 → 0.45.
- [M] No checkpoint lifts the pot to its reference height (3–9 cm against 12.8 cm).
- The public twin ep2 scored 0.31 against mocap with the older recipe.
- Cause: lid and pot grasps (C). The lid is a flat disc with a small knob, the pot is large and two-handled, and the
  lid sits on the pot, so each grasp disturbs the other object.

**Eval 25, two boards: 0.232.**
- [M] The copied human grasp on board 1 touches it with 1 finger (gap 23 mm); the grasp search ends with a median
  hold error of 60 cm, so the board is not held. Board 2 is lost at f44, 13 frames into its hold.
- [M] All 7 checkpoints score 0.14–0.27.
- The public twin ep24 scored 0.241 against mocap with this recipe.
- Cause: thin flat boards lying on the table cannot be picked up with a copied pinch (C). The planned "slide to the
  table edge, then grip" primitive (TODO #24) has not been built.

**Eval 20, blue cup + pitcher: 0.336.**
- [M] The pitcher tips over by itself before any hand arrives: tilt 11° at f4, 35° at f8. Its reference rises 36 cm;
  no checkpoint lifts it at all.
- [M, public audit] Our pitcher mesh lacks about half of its base, and its centre of mass is 2.8–4.1 cm outside its
  footprint.
- [M] The cup is lost from f2, held from f0, disturbed by the falling pitcher and the hand.
- Cause: mesh (A). A base completion that stands for 60 frames on CPU exists (8 convex sectors); it is not yet in the
  pipeline.

**Eval 10, blue cup + beige cup: 0.342.**
- [M] The beige cup falls over at the start: tilt 35° at f3, 84° at f10. Its reference rises 23 cm; no checkpoint
  lifts it.
- [M, mesh audit 22 Oct] Our beige cup mesh is 2 pieces with no bottom.
- [M] The blue cup slips during its hold: 27 % of frames within 3 cm.
- Cause: mesh (A), probably made worse by the cups starting nested.

**Eval 30, sweeper + rack: 0.472.**
- [M] Perception put the sweeper 7.1 cm under the table plane at frame 0, as for eval 8's beige cup. The automatic
  support fallback lifted it onto the plane.
- [M] In the simulator it then tips at once (tilt 17° at f2, 104° at f6) and falls **off the table**: z 3.8 cm by
  f20, 72 cm off its reference.
- [M] **No hold was detected for either object**, so the robot never tries to grasp the sweeper.
- [I] The public twin ep31's note ("sweeper standing in the rack dividers") suggests the sweeper starts inside the
  rack: supported by the rack, not the table, and partly occluded. That fits the wrong depth and the missing hand
  contacts.
- Cause: start or support (A) plus hold detection (B).

**Eval 33, blue cup + spoon: 0.421.**
- [M] The cup is held only from f17 to f48. After that our perceived cup moves 233 cm of path with no hand on it,
  tilts up to 144° and goes 14.6 cm below its start height.
- [I] The person holds the cup while working the spoon in it; our tracker loses or flips the partly hidden cup.
- [M] The spoon is lost at f110 during its hold; the search reached only 0.11 → 0.32 (median hold error 19 cm).
- Cause: cup perception and hold detection (B), plus a weak spoon grasp (C).
- [M] Its twin eval 32, also blue cup + spoon, scored 0.836: the cup was held there for 250 frames.

**Eval 14, blue cup + rack: 0.557.**
- [M] The cup is held f18–37 and followed well to f45 (error 1.5 cm). From there the perceived cup sinks to z 55 cm,
  **5 cm below the table top** (60 cm), and turns 90°, which cannot be real. No hold is detected after f37.
- [I] The cup is put into the rack, where the rack wires hide it and the track drifts.
- Cause: perception plus hold detection (B). The public twin ep12 scored 0.868 because its holds were detected.

**Eval 19, sweeper + dust pan: 0.627.**
- [M] The dust pan is lost at f26, during its hold.
- [M] The grasp search lifted its window only 0.18 → 0.36 (median hold error 14.6 cm); ep18's pan reached 0.50.
- [M] The fine-tune did not finish it this time. The 10M checkpoint was best (0.63) and later ones dropped to 0.27.
- [M] The sweeper is fine at 10M (83 % within 3 cm).
- Cause: dust pan grasp (C). This is the chaotic plate grasp seen on ep18, and this time the search did not find a
  good basin.

**Eval 28, rack + pot: 0.751.**
- [M] The pot follows its reference through the lift (2–5 cm off).
- [M] At the end it is placed 8.5 cm off, and the rack is knocked 15.8 cm at the last frames.
- Cause: placement into the rack, a pot–rack collision (mild).

**Eval 8, beige cup + pot: 0.823.**
- [M] The beige cup is never held. Its detection confidence is low (0.22, against 0.60 for the pot); it was placed
  7 cm under the table and lifted by the support fallback.
- [M] Its reference jitters: 121 cm of path while unheld, tilt up to 44°.
- [I] The cup is inside the pot.
- Mild in sim_vs_ref, because the simulated cup sits still while the jittering reference stays near it. Probably
  worse against the truth.

## 4. The perception gap (D) and the spoon

- [M] sim_vs_ref 0.710 vs Kaggle AUC 0.575; the public twins lost 3–4 %.
- [I] If the non-spoon episodes lose 4 %, the 10 spoon episodes average **≈ 0.64 AUC against a sim_vs_ref of
  0.886**. The spoon reference is then about 28 % off the truth: about 0.12 of the total, the largest single item.
- [H1] Our spoon mesh (a parametric template) registers to the hidden scan flipped or offset.
  - Falsified if it registers stably on ≥ 6 seeds against a measured stand-in.
- [H2] Our spoon pose track is poor; the spoon is thin and occluded by the hand.
  - Falsified if the reprojection residual of our spoon mesh on the eval frames is as small as for the other objects.
    No ground truth is needed for this check.
- [H3] Perception is worse on all objects in the eval set.
  - The MPPE board (8.7 cm) cannot separate H3 from the spoon, since the score is a single total. A second upload
    that changes only the spoon would.

## 5. What fixes what, by expected gain

All gains are estimates, on the 20-episode AUC.

1. **Spoon perception and mesh (D):** ≈ +0.05 to +0.12. Per-episode spoon fit, a flip and registration check, and
   reprojection QA. Part of v5 (D10) and TODO #13 / #16.
2. **Meshes that can stand (A):** ≈ +0.05 to +0.09.
   - Base completion for objects whose support check says UNSTABLE (pitcher, beige cup).
   - Multi-piece collision hulls.
   - No start inside another object (sweeper in the rack). The mesh v5 rebuild the owner asked for covers this.
3. **Hold detection and reference plausibility (B):** ≈ +0.03 to +0.06. These are generic rules for every episode:
   - an object that moves while no hold is detected gets a hold from the nearest hand, or its motion is frozen;
   - an object cannot go below the table, or flip while unsupported, so such frames are clamped;
   - an object perceived 7 cm under the table is a perception warning, not just a lift.
4. **Grasps on hard shapes (C):** ≈ +0.03 to +0.05.
   - Board edge primitive (TODO #24).
   - Lid knob pinch.
   - Plate grasp search with more seeds when the search window stays below 0.5 (eval 19 0.36, eval 38 0.35, eval 33
     spoon 0.32).

Each fix is tested on public twins against ground truth first. No change is made per episode on eval data.
