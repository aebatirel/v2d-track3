# 25 — Support-consistent meshes: a stability certificate for resting poses (2026-10-23)

Owner: "the brush is a weird shape; the 3-D mesh should be designed to physically support the starting position" and
"isn't there a mathematical requirement or some kind of boundary we can use to make sure it starts stable?"

## Measured problem
Public ep18 (sweeper + dust pan), frozen grasp-lock recipe, registered AUC 0.320 (previous best 0.889). Zero-action
replay: the brush moves 88.7 mm / 81.7° before any hand reaches it (`tools/rest_check.py` on the round-2 trace) and the
episode is lost from frame 4. Diagnostic with ground truth (after inference, reporting only): the real brush stands on
its bristles (contact patch 10.9 × 3.7 cm) and our perceived pose matches it (87.6° vs 86.2°). But our mesh touches
the table on 0.6 × 0.4 cm only, because the bristle underside is ragged and unobserved, so its centre of mass (COM) is
not over the support.

## The criterion (textbook statics of a rigid body on a plane)
- **Equilibrium:** a rigid body resting on a plane stands if and only if the vertical through its COM passes inside
  its support polygon, the convex hull of its points touching the plane.
- **Robustness:** the margin d is the distance from the COM's projection to the nearest polygon edge, and h is the COM
  height. The body then survives:
  - a tilt of up to atan(d / h);
  - a horizontal push of up to m g d / h;
  - a pose error of θ as long as d ≥ h tan θ.
- **Certificate used** (`pipeline/support_fill.py`):
  - COM inside, with d ≥ 3 mm and atan(d / h) ≥ 3°;
  - the COM is the URDF's inertial origin, i.e. the one the simulator uses;
  - our resting-pose jitter is 0.4–1.6 mm and 0.3–1.9° per frame, and the soft contact sinks about 1 mm.
- **Settling:** a perceived pose is tilted by 1–2°, so an object with a flat bottom first rocks onto it. The pose "as
  is" passes if quasi-static rocking reaches a certified stance within 3°:
  - rotate about the support point or edge on the COM's side, in the direction that lowers the COM, in 0.1° steps;
  - pick up each new contact within 1 mm;
  - stop as soon as the COM is inside the support polygon.
  - A first version took the contacts at the pose itself, with no rocking. It flagged the cup, rack and pot as
    unstable, although the simulator kept them standing. A second version looked for a single hull face within 3°,
    but our reconstructed bottoms are faceted, so no single face is large enough. Both were rejected.
- **Repair:** otherwise, fill the underside straight down to the table, using the smallest fill of 0.5 / 1 / 1.5 / 2 cm
  that certifies the pose:
  - the fill is a convex slab of the low surface points and their projections, joined to the mesh with a manifold
    union;
  - mass and COM stay the URDF's;
  - scoring keeps the library meshes.
- **Free space:** the fill must not change resting contacts with other objects along our reference. Surface samples of
  another object may lie inside the slab only briefly: ≤ 5 frames in a row and ≤ 15 frames in total. In ep18 the
  bristles go into the dust pan while sweeping (6 frames, ≤ 7.6 mm). In ep12 the cup sits in the rack 1 cm above the
  table for 53–66 frames, so those fills are blocked. A pose that no fill certifies is reported as UNSTABLE or BLOCKED
  and left as is.
- **Simulator check** (`tools/rest_check.py`): in the zero-action replay, every object stays within 5 mm and 2° of its
  simulated frame-0 pose until (its first hold start − 6 frames).

## Result on the public references (no ground truth used)
| ep | object | as is | decision |
|---|---|---|---|
| 18 | mini_sweeper f0 | still rocking past 3° from a 0.5 × 0.3 cm contact (it fell in the simulator) | **1 cm fill**: base 10.2 × 4.5 cm, d 4.3 mm, tips past 3.7° |
| 18 | mini_dust_pan f0, f189 | settles 2.2° / 1.3°; d 6.3 mm, 21° | unchanged (the simulator kept it: 2.8 mm / 1.6°) |
| 12 | blue_cup f0 | settles 1.6°, but d is only 1.2 mm | 0.5 cm fill: d 28.8 mm, 18° |
| 12 | plastic_dish_rack f0 | rocks past 3° | fill blocked (the cup rests in it from f128); unchanged |
| 24 | wooden_piece_2 f0 | settles 0.7°; d 3.6 mm, 19° | unchanged (ep24 needs no rerun) |
| 27 | plastic_dish_rack f0 | settles 2.8°; d 39.5 mm | unchanged |
| 27 | white_pot f0 | rocks past 3° | 1 cm fill: d 50.8 mm, 44° |

## Grip on the plates (checked before changing the grasp rule)
- Our MANO contacts show how the human holds both ep18 objects: a thumb against index/middle clamp.
  - The palm touches the dust pan in 13% of the hold and the brush in 8% and 0%.
  - The thumb distal link touches in 61–89% of the hold, the middle finger in 49–91%.
- The copied (snapped) clamp is therefore the right grasp type. Its failure in round 2 is confounded: the brush had
  already fallen, and the right hand followed the reference brush 10–18 cm away from the fallen one.
- The grasp rule is left unchanged for this test, so only one thing changes.

## Hypothesis and the experiment that falsifies it
**H1:** with support-consistent meshes and the frozen recipe otherwise unchanged:
- the rest check passes on ep18;
- ep18 reaches registered AUC ≥ 0.8 (previous best 0.889);
- ep12 and ep27 do not regress beyond their spread (0.910 ± 0.023, 0.972 ± 0.004).

It is falsified if:
- the brush still moves before it is grasped, which would point to contact parameters or a start overlap rather than
  geometry; or
- ep18 stays below 0.6 with the rest check passing, which would mean the plate grasp is the remaining blocker. The
  next step would then be a built palm-and-fingers clamp across the plate thickness.

Run: `ops/jobs/glock_public.sh` with SF=1 on public ep18, ep12 and ep27.
