# 15 — Eval video survey: risks and design needs for the 20 eval episodes (agent 15, 2026-10-05) — COMPLETE

Stages A (eval 1-16), B (eval 19-38) and C (risk table, grasp-synthesis flags, collision-asset checks) are done.
Labels: [V] verified (seen in frames, computed or read in code/data), [E] estimate, [H] hypothesis.
Rules kept: research only; eval videos viewed for method design only (no per-episode labels for inference);
public GT used only for analysis/priors; no leaderboard probing; no evaluator/physics changes; no SlamDunk code read.
Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/15/ (stage A/B sheets in up/, stage C scripts and
outputs in c/). The pre-rewrite version of this note is at work/15/c/notes_before_rewrite.md.

## 1. Summary (most important first)

1. [V] Do NOT rotate ego_cam_a by 180 deg. The stored eval and public colour and mono videos are already upright,
   and camera_calibration.json matches the stored frames (stereo rectification test, section 9).
2. [V] The evaluator's collision model does not match the scans where contact matters. FlashCHORD replaces every
   collision mesh with CoACD hulls (threshold 0.05; note 01 C.8). With CoACD 1.0.14 at that threshold, the public GT
   contact states sit 5-15 mm inside the hulls: lid on pot 7.6-8.4 mm, cup on rack 6-8 mm, pot on rack 7-10 mm,
   sweeper between the rack dividers 10-15 mm. For the rack pairs a scan-vs-scan control gives only 0-1.3 mm, so the
   overlap comes from the hulls themselves. Eval 30's anchor (the sweeper between the dividers) and eval 1's lid
   therefore start inside the collision model at frame 0, and the evaluator resets with no VOC.
   [E] Expect the object to be ejected at step 1 and a slot-0 settle error in eval 30.
3. [E] Robot grasp synthesis (rigid grasp-and-carry, note 10 P9) likely FAILS on 8/20 eval episodes:
   14, 15, 16, 20, 25, 28, 35, 36. On 8 more (3, 5, 6, 10, 19, 30, 32, 33) the grasps themselves are feasible, but a
   tool-contact, insertion or asset segment likely fails in simulation. Only 1, 8, 37 and 38 look like plain
   grasp-and-carry. Section 3 gives the reason for each episode.
4. [V] Eval 20 starts with the slot-0 cup already held in mid-air, and eval 32 starts with the hand already on the cup.
   The evaluator starts from the exact reference fingers with VOC 0 and no hold (note 01 C.7/C.10). [E] So the frame-0
   reference grasp in 20 must hold the cup from step 0, against note 10's "contact-free frame 0" rule.
5. [V] The public twins contain long on-table moving segments (slides and pivots): boards 23/24 (piece_1: 68 of 87
   moving frames), sweeper 18 (64/154, 13.5 cm run), dustpans 18 and 39 (18.6 cm slide). Sim friction is 1.0 everywhere
   (note 01). [E physics] So "press on top and drag" cannot move an object in sim. A slide needs a lateral push on an
   edge or a full grasp, and the soft wrist needs ~12 cm of residual to overcome the 2.9 N table friction of a
   0.3 kg object.
6. [V] The rack's utensil tower survives CoACD but is narrowed: walls ~6 mm thicker inward, opening ~18-24 mm [E] vs
   ~30 mm, floor 0.5-1 cm higher. Eval 15/16 put a spoon handle (~16-20 mm) into it. The pot basin floor is raised 5-25 mm,
   and the cup walls bulge 10-25 mm inward at some rim azimuths, which affects stirring in 3/5/6/32/33. The board halving
   slot survives (16 mm in the hulls vs 9.1 mm plate), so the eval 25 cross is NOT blocked by the hulls.
7. [V] The spoon is in 10/20 eval episodes and is the only object, and so the anchor, in 35/36/37. It has no scan, URDF or
   GT, so its sim asset (collision and inertia) is entirely ours. Its roll sign is ~50/50 (notes 07/13).
8. [V] Anchor timing: the slot-0 static start is 0 frames in 20 and 32, <=1 s in 5, 6, 14, 19, 33 and 35, and the whole
   clip for the rack anchors (15, 16, 28). The frame-0 anchor pose must come from the tracked trajectory (a static end
   segment, back-propagated), not from an assumed resting start.
9. [V] Distractors and visibility: second people in 14, 15, 16 and 25 (and in the mono views of 20); identical-looking
   boards in 25 (identity from the marker layout); objects cut by the colour border in 20 and 28 (the mono pair sees more);
   edge-on or end-on views in 25, 38, 35 and 36; heavy blur on spoon strokes and lifted objects.

## 2. Stage C: per-episode risk table, mapped to pipeline components

Ratings: H = high risk of a score-relevant failure, M = medium, L = low, - = not applicable. Components:
SEG = segmentation and identity; TRK = 6-DoF tracking through grasps, occlusion, blur and truncation; STEREO = metric
depth needs; SMOOTH = world-frame smoother and slot-0 anchor (static windows, support and contact constraints);
GRASP = robot grasp synthesis vs non-prehensile or dexterous actions; SIM = collision assets and contact-critical states
under CoACD (stage C measurements, section 4); SPOON = spoon mesh, roll and markers; SYM = symmetric or ambiguous anchor
(notes 11/12). Evidence: per-episode descriptions (section 8) and section 4; ratings are [E] unless stated otherwise.

| ep | slot0 / slot1 | SEG | TRK | STEREO | SMOOTH (anchor) | GRASP | SIM | SPOON | SYM | grasp synthesis |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | pot / lid | M white-on-white, lid merges with pot | M handle in fist f28-300; pot waved with blur f132-182 | L | L static ~45-125 f | M handle power grasp (0.3 kg x ~0.2 m lever = ~0.6 N m); lid bar pinch; drags while held | H lid starts 7.6-7.9 mm inside pot hulls at f0; re-seat 8 mm | - | L pot unique; lid 2-fold broken by markers | FEASIBLE if the lid states are hull-aware |
| 3 | pot / spoon | M thin spoon at the pot rim | H spoon bowl inside pot, fast strokes | M thin spoon: marker triangulation | L pot ~static | M spoon pinch from flat (~16-20 mm handle on table); stirring = tool contact | H basin floor +5-25 mm in hulls; spoon-pot contact pushes a 0.3 kg pot | H slot 1 | L | PARTIAL (stir contact) |
| 5 | pot / spoon | M-H pot fills 1/3 of the image, defocus | H both objects move together, blur f88-104 | H pot close to camera | H static 16-20 f | H pot lifted with spoon inside while stirring (coupled contact, both hands busy) | H as 3 | H | L | PARTIAL, worst of the stirring set |
| 6 | pot / spoon | M | H spoon hidden in pot most of f48-176 | M | H static 16-20 f | M-H as 3 plus small pot lifts and tilts | H as 3 | H | L | PARTIAL |
| 8 | beige cup / pot | M beige cup vs table/skin [H] | M cup in fist, turned upside down | M cup high above table | M static 44-50 f | M cylinder wrap (88 mm) + inversion; pot handle lift/tilt | L | - | H beige near-3-fold spin, no GT prior | FEASIBLE (spin is the risk) |
| 10 | blue cup / beige cup | H nested cylinders, blue cup behind fist + beige | M-H | M | L-M blue cup near-static | M-H beige held only by its top ~2-3 cm band to finish the nest (twin 11: beige ends 30 mm above blue) | M nest 4.6-4.9 mm inside blue hulls; wall bulges | - | H blue cup spin from markers; beige near-3-fold | PARTIAL (insertion) |
| 14 | blue cup / rack | M white rack; 2nd person at edge | M-H hand-over mid-air, 180 deg flip, blur f80 | M | H static ~16 f (rack-relative yaw prior LOO 1.9 deg, note 11) | H L->R hand-over of a horizontal cup + flip + inverted placement | M-H cup on rack 6-8 mm inside hulls | - | M | LIKELY FAILS |
| 15 | rack / spoon | H 2nd person fills left third; spoon crosses his arm | M-H hand-over; spoon end hidden in tower | M | L rack static all clip | H spoon pinch from flat + R->L hand-over + handle-first insertion (grasp must be at bowl/upper handle) | H tower opening ~18-24 mm in hulls vs ~16-20 mm handle | H slot 1 | M rack anchor needs world link/geometry (note 11) | LIKELY FAILS |
| 16 | rack / spoon | H 2nd person larger, hands in lap | M-H two-hand regrasp | M | L rack static all clip | H as 15 (right hand inserts) | H as 15 | H | M | LIKELY FAILS |
| 19 | sweeper / dustpan | M tiny sweeper in fist | H anchor barely visible during strokes | M | H static ~10-15 f; no static end (sweeper still held) | M-H sweeping drags on table/dustpan (twin 18: 64/154 on-table moving frames); dustpan slid then tilted | L sweeper vs dustpan <=3.4 mm | - | M 2-fold, resolved world-free (note 11) | PARTIAL (drag strokes) |
| 20 | blue cup / pitcher | M pitcher cut by border; 2nd person in mono | H pitcher truncated f48-96 in cam a; cup moving in hand | H pitcher near camera: use mono pair | H static start 0 f; only static end ~40 f | H f0 cup in hand mid-air at reset (VOC 0); pitcher lift 32 cm / 92 deg | L | - | H blue cup; bearing prior LOO 6 deg | LIKELY FAILS (frame-0 grasp) |
| 25 | board 1 / board 2 | H identical boards: identity from marker layout; 2 people | H thin boards edge-on; fine two-hand adjustment | H edge-on 7.5-9 mm plates | M static ~30 f; end-snap prior (note 11) | H flat plate pick-up by slide/pivot to the table edge (twin 23: 68/87 on-table frames), stand on edge, slot together | L slot survives (16 mm vs 9.1 mm); cross 1.3-2.9 mm | - | M 2-fold + identity | LIKELY FAILS (non-prehensile pre-grasp) |
| 28 | rack / pot | H white pot on white rack | H 180 deg mid-air flip; top-border cut f96-120; hand-over | M-H pot near camera f24-40: use mono views | L rack static all clip | H both hands on a 24x33 mm stick handle during the hand-over; flip under ~0.6 N m handle torque (twin 26 rotation saturation, note 14) | M-H pot on rack 7 mm inside hulls | - | L | LIKELY FAILS |
| 30 | sweeper / rack | M sweeper among white fins | M-H sweeper in fist while scrubbing; hidden by fins at start/end | M | H anchor starts in divider comb; static 28-32 f | M ring grasp easy; scrubbing presses on a 0.3 kg rack held by the other hand | H anchor 10 mm inside rack hulls at f0 (twin 31), 13-15 mm at end | - | M 2-fold, resolved world-free | PARTIAL (asset/anchor) |
| 32 | blue cup / spoon | M | H spoon bowl inside cup; blur | M | H static start 0 f; static end ~f190-258 | M-H f0 hand already on cup (must not penetrate); cup held tilted mid-air ~170 f; spoon pinch; stir in cup | M-H cup wall bulges 10-25 mm in hulls | H | H blue cup, no GT prior | PARTIAL (stir contact) |
| 33 | blue cup / spoon | M | H many fast strokes | M | M-H static 12-16 f | M-H as 32 without f0 contact | M-H | H | H | PARTIAL (stir contact) |
| 35 | spoon / - | M colour fails on skin, mono on floor -> fuse | H end-on views; fists over markers | H axis depth when end-on | M static 16 f; static end 20-35 f | H >=4 hand-overs + in-hand reorientation (each switch is a chance of a discrete failure) | M own thin hulls (bowl/handle) | H anchor; roll ~50/50 | H roll | LIKELY FAILS |
| 36 | spoon / - | M | H twirls, blur, end-on | H | M static 20-24 f | H in-hand twirls + R->L hand-over | M | H anchor | H roll | LIKELY FAILS |
| 37 | spoon / - | L | M blur at lift | M lift height | M static 16-24 f; static end ~40 f | L-M pinch from flat, lift, place back | M own asset | H anchor | H roll | FEASIBLE (sanity case) |
| 38 | dustpan / - | L bright yellow-green | M plate edge-on f80 | M thin plate | M static 32-36 f | L-M ring-handle grasp; one hand; possible table slides | L | - | L handle breaks symmetry | FEASIBLE |

Component load (counts of H in the table, with M-H in brackets): TRK 11 (3, 5, 6, 19, 20, 25, 28, 32, 33, 35, 36)
[+10, 14, 15, 16, 30]; SPOON 10; GRASP 9 (5, 14, 15, 16, 20, 25, 28, 35, 36) [+6, 10, 19, 32, 33]; SYM 8 (8, 10, 20, 32,
33, 35, 36, 37); SIM 7 (1, 3, 5, 6, 15, 16, 30) [+14, 28, 32, 33]; SMOOTH 7 (5, 6, 14, 19, 20, 30, 32) [+33]; SEG 5
(10, 15, 16, 25, 28); STEREO 5 (5, 20, 25, 35, 36) [+28]. Eval 5 has GRASP H but is not in the grasp-synthesis
"likely fails" list: its grasps exist, and the risk is the spoon-pot contact while the pot is lifted.

## 3. Grasp-synthesis flags (rigid grasp-and-carry per segment, note 10 P9)

LIKELY FAILS (8): the key segment is not a rigid grasp-and-carry, or it needs a start state the sampler rules out.
- 20: frame-0 cup is already in mid-air in the left hand. Reset = exact reference fingers, VOC 0, no hold. In one 50 ms
  control step a free cup falls ~1.2 cm [E], so the frame-0 grasp must already squeeze. [H] Fix: a deliberately
  pre-loaded (slightly penetrating) frame-0 grasp, verified by a frame-0 drop test in the evaluator physics.
- 25: boards are 7.5-9 mm plates lying flat. The human slides board 1 to the table edge, pivots it on edge, then slots
  the two boards together with both hands. At mu = 1.0 everywhere, a top-press drag is impossible [E]. A lateral edge push
  or a pivot primitive is needed (non-prehensile), followed by an edge pinch.
- 28: L->R hand-over with both hands on one 24x33 mm stick handle, plus a 180 deg mid-air flip with ~0.6 N m of
  gravity torque at the grip [E]. Two human-sized Sharpa hands (208x90x50 mm) on a ~15 cm handle are likely to collide.
- 14: mid-air hand-over of a horizontal cup, then a 180 deg flip and an inverted placement on a rack whose hulls the GT
  end pose penetrates by 6-8 mm.
- 15, 16: spoon pinch from flat, then a hand-over or two-hand regrasp, then a handle-first insertion into a tower
  whose hull opening (~18-24 mm) barely clears the handle. The grasp must sit on the bowl/upper handle.
- 35: >=4 hand-to-hand passes and in-hand reorientations. Each switch is a discrete failure opportunity (note 14: one
  drop costs 0.18-0.45 AUC and kills MP-SR).
- 36: in-hand twirls (dexterous rotation inside one hand), then a hand-over.
PARTIAL (8): the grasps are feasible, but a contact segment likely breaks in simulation.
- 3, 5, 6 (stirring in the pot), 32, 33 (stirring in a hand-held cup): the spoon bowl works inside a cavity whose hull
  floor or walls are 5-25 mm off. Every reference error turns into contact forces on a 0.3 kg container. 5 is the worst,
  because the pot is lifted with the spoon inside. In 32 the hand is already on the cup at f0.
- 10: insertion is only possible with a rim-band grasp (top ~2-3 cm of the beige cup) or a release-and-drop. The nest
  state overlaps the hulls by ~5 mm.
- 19: sweeping strokes drag the held sweeper over the table and dustpan, and the dustpan is slid and yawed on the table.
  Hands are already moving at f0.
- 30: the grasp is easy, but the slot-0 sweeper starts 10 mm inside the rack hulls, and the scrub presses on a 0.3 kg
  rack.
FEASIBLE (4): 1 (pot handle + lid bar; the lid states must be hull-aware), 8 (cup wrap and pot handle; the beige spin
is the real risk), 37 (pick-lift-place), 38 (one-hand ring handle).

## 4. Stage C measurements (details in the log, section 7)
- [V] Collision assets: the public URDFs reuse the visual GLB as the collision mesh (separate *_collision.glb only for
  the sweeper and the boards), mass 0.3 kg as a placeholder. FlashCHORD's CoACD runs at threshold 0.05 with unlimited
  hulls (note 01). There is no spoon URDF or mesh.
- [V] CoACD 1.0.14 (seed 0, threshold 0.05, other params default; [E] FlashCHORD's wrapper assets/mesh.py was not
  fetched, so its other params may differ) gives 9-73 hulls per object. Top-down height maps (scan vs hulls): cups keep
  their cavity, but the walls bulge 10-25+ mm inward at some rim azimuths. The pot basin floor rises 5-25 mm. In the rack,
  57/37/10 % of plan cells rise >5/>10/>25 mm, and the tower narrows. The boards' slot is kept (16 vs 19 mm). The
  dustpan, lid and sweeper change by <=10 mm on >90 % of cells.
- [V] GT contact states inside the hulls (hull-of-A samples in the hulls of B): lid/pot 7.6-8.4 mm (eps 0, 2);
  beige/blue nest 4.6-4.9 mm (11); cup/rack 6.0-8.4 mm (12, 13); pot/rack 7.1-9.6 mm (26, 27); sweeper/rack 10-15 mm (31);
  boards 1.3-2.9 mm (23, 24); sweeper/dustpan <=3.4 mm (18); separated pairs 0.0 mm. In the rack-pair control, scan
  vs scan gives 1.0-1.3 mm max (p99 0.0-0.6), so the rack overlap comes from CoACD.
- [V] On-table moving frames in public GT (lowest scan vertex within 1 cm of the table, >2 cm/s): listed in summary
  item 5. Cups, the pitcher and most pot motions are airborne.
- [V] Sizes: cups rim ~88 mm, 170 mm tall; pot stick handle reaches 242 mm from the body centroid, end cross-section ~24x33
  mm; pitcher 141x272x415 mm; lid 190 mm; rack 117x175x510 mm; sweeper 48x114x142 mm; dustpan plate ~3-4 mm [E];
  boards 139x227 mm, 7.5/9.1 mm thick.

## 5. Design needs (consolidated across stages A, B and C; method only, no per-episode labels)
1. Rig: no 180-degree re-rotation. Use the calibration as given (left = ego_cam_c, right = ego_cam_b). Add mono-pair
   tracking as a fallback whenever the colour view truncates an object (20, 28), and reject non-ego hands in the colour
   and mono streams (14, 15, 16, 20, 25).
2. Anchor: estimate the slot-0 frame-0 pose from the whole track (best-observed or static END segment, propagated
   backward), with support and stable-face priors (note 11). Detect the static start automatically (hands open or
   first contact) and allow it to be zero (20, 32).
3. Hull-aware references (new): reproduce FlashCHORD's exact convex_decompose call offline (fetch assets/mesh.py at the
   pinned commit), project every reference pose to non-penetration against those hulls, and run a frame-0 settle/drop
   test in the evaluator physics before any RL spend. Ask the organisers whether we may supply collision meshes (note 10
   Q4). Without this, eval 30 (anchor), 1, 10, 14, 28 and the stirring clips start or end in interpenetration.
4. Per-segment action typing from object kinematics plus support contact: static / carry / on-table slide-or-pivot /
   hand-over / tool contact (stir, sweep, scrub) / insertion / in-hand reorientation. Each type then goes to grasp
   synthesis (carry), to a push/pivot primitive (slides; lateral edge pushes, since mu = 1 everywhere), or to the
   repaired human-hand fallback (in-hand, hand-over windows).
5. Task-constrained grasp locations: rim band for nesting (10), bowl/upper handle for handle-first insertion (15/16),
   one hand per handle end for the pot hand-over (28), and frame-0 pre-loaded grasps (20, 32 contact at f0).
6. Spoon: our own mesh, collision hulls and inertia, a marker-based pose (notes 13) and a roll sign rule. Also a
   collision-aware smoother against the container hulls in 3/5/6/32/33 and the tower in 15/16.
7. Symmetric anchors: blue cup (10, 14, 20, 32, 33) and beige cup (8) need the marker-layout spin (note 12); rack (15, 16)
   needs geometry or a world link (note 11); board identity (25) from the marker layout.
8. Budget: the 8 "likely fails" episodes are where extra seeds (note 14 best-of-N) and per-segment fallbacks pay most.

## 6. Development cases with public GT for each risk (falsification tests)
| risk | public dev case | test that could falsify the fix |
|---|---|---|
| frame-0 in-hand anchor (20) | 21/22 trimmed to start at the cup lift (~f33-40) | back-propagated anchor error vs GT; frame-0 drop test of the pre-loaded grasp in sim |
| hull interpenetration at reset (30, 1) | 31 f0 (sweeper in dividers), 0/2 f0 (lid on pot) | the hull-aware projected start must settle <2 mm / <1 deg in 1 s at VOC 0 |
| placement on inflated rack (14, 28) | 12/13 end, 27 end | end pose after settling vs GT; the policy must not knock the rack |
| flat-plate pick-up by slide/pivot (25) | 23/24 piece_1 (68/87 on-table frames) | push primitive reproduces a 7 cm slide and the pivot in sim within 1 cm / 5 deg |
| sweeping drags (19) | 18 | sweeper/dustpan tracking error during on-table runs |
| nesting insertion (10) | 11 | beige final height within 5 mm of GT in sim with a rim-band grasp |
| hand-over on a handle (28) | 27 is single-handed; 26 has the left hand on the tower | no public two-hand handle hand-over -> sim-only feasibility test |
| stirring/tool contact (3/5/6/32/33) | none with GT (no spoon) | proxy: sweeper-in-dustpan contact (18) |
| spoon in-hand/hand-overs (35/36) | none (dustpan hand-over in 39 as a proxy) | count of discrete drops over 3 seeds |
