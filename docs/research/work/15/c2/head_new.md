# 15 — Eval video survey: risks and design needs for the 20 eval episodes (agent 15) — COMPLETE (2026-10-06)

Stages A (eval 1-16), B (eval 19-38) and C (risk table, action segments, grasp-synthesis flags, collision-asset checks)
are done. The 2026-10-06 workflow re-ran all three stages: section 12 holds the Stage B re-run, section 13 the Stage C
re-run log. Sections 1-6 were rewritten in that re-run and fold in the verifier (section 11) and both re-runs.
Labels: [V] verified (seen in frames, computed, or read in code or data), [E] estimate, [H] hypothesis.
Rules kept: research only. Eval videos were viewed for method design only; no per-episode labels for inference.
Public GT was used only for analysis and priors. No leaderboard probing, no evaluator or physics changes, no SlamDunk
code read. Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/15/ (stage A/B sheets in up/, Stage B re-run in
b2/, Stage C in c/, Stage C re-run in c2/, verifier in ../15-verify/). Earlier versions of this note:
work/15/c/notes_before_rewrite.md (before the first Stage C) and work/15/c2/notes_before_stageC_rerun.md.
Section 12 supersedes section 8 on these points: eval 35 has 5 hand-overs and ends yawed ~60 deg (not 120-150); eval 36
has 2 hand-overs and no in-hand twirls; eval 38 ends yawed ~65 deg (not ~90); eval 20 is probably not a trimmed twin.

## 1. Summary (most important first)

1. [V] Do NOT rotate ego_cam_a by 180 deg. The stored eval and public colour and mono videos are already upright, and
   camera_calibration.json matches the stored frames (section 9; reproduced independently in section 11).
2. [E] Robot grasp synthesis (rigid grasp-and-carry per segment, note 10 P9) likely FAILS on 7/20 eval episodes:
   14, 15, 16, 20, 25, 28, 35. Eval 36 is borderline (2 hand-overs and end-on views). On 8 more (3, 5, 6, 10, 19, 30, 32,
   33) the grasps are feasible, but a tool-contact, insertion or asset segment likely breaks in simulation. Only 1, 8, 37
   and 38 look like plain grasp-and-carry. Reasons per episode: section 3.
3. [V] The evaluator's collision model does not match the scans where contact matters. FlashCHORD runs CoACD
   (threshold 0.05, unlimited hulls, coacd==1.0.11 pinned; section 11). With the pinned version the public GT contact
   states sit 4-15 mm inside the hulls: lid on pot 7.7-8.4 mm, cup on rack 6.0-8.4 mm, pot on rack 7.2-9.8 mm, sweeper
   between the rack dividers 10.5-15.3 mm, nest 4.1-4.3 mm. Scan-vs-scan controls give 1-4 mm, so the hulls fill free
   space by 6-14 mm. Eval 1's lid and (by twin 31 inference) eval 30's anchor sweeper start inside the collision model
   at reset. [E, approximate MuJoCo, not the evaluator] the push-out is 1-4 cm and 3-33 deg for the sweeper, and a pure
   vertical projection leaves it ~2 cm above GT. Its timing (absorbed into the scorer's alignment at step 1 or not)
   depends on contact softness.
4. [V GT] No movable anchor is static up to its 1 cm motion onset. In all 20 public episodes slot 0 is first perturbed
   (>1 mm or >1 deg) at f3-64, and before the 1 cm onset it has already rotated 1.0-8.6 deg (median ~3.6 deg; section
   13). Only the rack anchors stay within ~1 deg for the whole clip. [E] The scorer applies the anchor's frame-0 pose to
   every object, so each 2 deg of anchor error moves an object 0.25 m away by ~0.9 cm. The frame-0 anchor must come
   from the frames BEFORE first hand contact. In the eval clips that window is: none in 20 (cup in mid-air) and 32 (hand
   on the resting cup); ~15 frames in 5, 6, 10, 14, 19, 33, 35 and 37; ~22-48 frames in 1, 3, 8, 25, 30, 36 and 38; the
   whole clip for the rack anchors 15, 16 and 28.
5. [V] Eval 20 starts with the slot-0 cup held in mid-air. The evaluator resets to the exact reference fingers with
   VOC 0 and no settling hold, and a free cup falls 12-15 mm in the first 50 ms step (section 11). [E] So the frame-0
   reference grasp in 20 must already hold the cup, against note 10 P10's "contact-free frame 0". Eval 32 starts with
   the hand on the cup, but the cup still rests on the table, so the support prior holds at f0.
6. [V] The same seated second person (office chair, jeans, white sneakers) is in the colour view of 19-20/20 eval clips,
   at the left edge. His arms or hands are visible in at least 8, 14, 15, 16, 19, 25, 28 and 30; in eval 8 his bare forearm
   with a dark watch enters the top-left corner. A standing person is also in 25. [E] Non-ego hand and arm rejection is a
   default pipeline stage. The ego cue is the WHITE smartwatch on the wearer's left wrist plus arm continuity from the
   bottom border; "a watch" alone is ambiguous.
7. [V] Hand switches per clip: eval 35 has 5 hand-overs (two-hand phases ~45 % of frames), 36 has 2, 14, 15 and 28 have
   1 each, 16 has a two-hand regrasp and 25 a two-hand placement. Pot handle geometry (section 13): ~157 mm free length,
   ~18 x 31 mm section, so two ~90 mm Sharpa palms do not fit on it side by side [E] (eval 28's two-hand hand-over).
8. [V] The public twins contain long on-table moving segments (slides and pivots): boards 23/24 (piece_1: 68 of 87
   moving frames), sweeper 18 (64/154, 13.5 cm run), dustpans 18 and 39 (18.6 cm slide). Sim friction is 1.0 everywhere
   (note 01). [E physics] "Press on top and drag" cannot move an object in sim. A slide needs a lateral edge push or a
   full grasp, and the soft wrist needs ~12 cm of residual to supply the 2.9 N table friction of a 0.3 kg object.
9. [V] Cavity geometry under CoACD: the rack's utensil tower survives but narrows to ~18-24 mm [E] (scan ~30 mm), vs a
   ~2 cm round spoon handle (note 13) in eval 15/16. The pot basin floor rises 5-25 mm and the cup walls bulge 10-25 mm
   inward at some rim azimuths (stirring in 3/5/6/32/33). The board halving slot survives (16 mm in the hulls vs 9.1 mm
   plate), so the eval 25 cross is not blocked.
10. [V] The spoon is in 10/20 eval episodes and is the only object, and so the anchor, in 35/36/37. It has no scan, URDF
   or GT; its sim asset (collision and inertia) is entirely ours, and its roll sign is ~50/50 (notes 07/13).
11. [V] Visibility: objects cut by the colour border in 20 (pitcher) and 28 (pot, during a ~140 deg/s roll about the
   handle axis); the mono pair sees more. Edge-on or end-on views in 25 (boards), 35 and 36 (spoon) and the eval 19
   dustpan dump (visible area 0.14-0.5x for ~12 frames); eval 38's edge-on moment keeps >=0.79x of its area. Head
   motion in every eval clip lies inside the range of the public twins, and whole-frame blur is rare (0-5 % of frames),
   so the blur seen is object motion.

## 2. Per-episode risk table, mapped to pipeline components

Ratings: H = high risk of a score-relevant failure, M = medium, L = low, - = not applicable. All ratings are [E]; the
evidence is in sections 8 and 11-13. Components: SEG = segmentation, identity and non-ego rejection (NE = the second
person's arms or hands are in view); TRK = 6-DoF tracking through grasps, occlusion, blur and truncation; STEREO = metric
depth needs; SMOOTH = world-frame smoother and slot-0 anchor (clean pre-contact window, static end, support and contact
constraints); GRASP = robot grasp synthesis vs non-prehensile, two-hand or tool-contact actions; SIM = collision assets
and contact-critical states under CoACD; SPOON = spoon mesh, roll and markers; SYM = symmetric or ambiguous anchor
(notes 11/12). "Window" = slot-0 frames before the first hand contact.

| ep | slot0 / slot1 | SEG | TRK | STEREO | SMOOTH (anchor) | GRASP | SIM | SPOON | SYM | grasp synthesis |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | pot / lid | M white-on-white, lid merges with pot | M handle in fist f28-300; pot waved with blur f132-182 | L | M window ~f0-22 (handle grip f24-32); twins 0/2 rotate 2.6-4.5 deg while held before the lift | M handle power grasp (18x31 mm); lid bar pinch; pot dragged on the table while held f60-125 | H lid starts 7.7-8.4 mm inside the pot hulls; a hull-cleared lid settles ~9 mm high | - | L pot unique; lid 2-fold broken by markers | FEASIBLE if the lid states are hull-aware |
| 3 | pot / spoon | M thin spoon at the pot rim | H spoon bowl inside pot, fast strokes | M thin spoon: marker triangulation | L window ~f0-48; pot held on the table | M spoon pick from flat (~2 cm round handle); stirring = tool contact | H basin floor +5-25 mm in hulls; spoon-pot contact pushes a 0.3 kg pot | H slot 1 | L | PARTIAL (stir contact) |
| 5 | pot / spoon | M-H pot fills 1/3 of the image, defocus | H both objects move together, blur f88-104 | H pot close to camera | H window ~f0-14 | H pot lifted with the spoon inside while stirring; pot turned on the table f24-40 | H as 3 | H | L | PARTIAL, worst of the stirring set |
| 6 | pot / spoon | M | H spoon hidden in pot most of f48-176 | M | H window ~f0-14 | M-H as 3, plus a 20-30 deg on-table turn f24-32 and small lifts | H as 3 | H | L | PARTIAL |
| 8 | beige cup / pot | M beige vs table and skin; NE forearm top-left f60-160 | M cup in fist, turned upside down | M cup high above the table | M window ~f0-40 | M cylinder wrap + inversion; pot handle lift/tilt and an early on-table turn | L | - | H beige near-3-fold markers (note 12: 21-31/40 flips if only 2 found) | FEASIBLE (spin identity is the risk) |
| 10 | blue cup / beige cup | H nested cylinders; blue cup behind fist and beige | M-H | M | M window ~f0-14; blue then held (twin 11: 4.7 deg before any 1 cm motion) | M-H beige held only by its top ~2-3 cm band to finish the nest, or release-and-drop | M nest 4.1-4.9 mm inside the blue hulls; wall bulges | - | H blue anchor spin from markers; beige near-3-fold | PARTIAL (insertion) |
| 14 | blue cup / rack | M white rack; NE at the edge | M-H mid-air hand-over, 180 deg flip, blur f80 | M | H window ~f0-14 (rack-relative yaw prior LOO 1.9 deg, note 11) | H L->R hand-over of a horizontal cup + flip + inverted placement | M-H cup on rack 6.0-8.4 mm inside hulls | - | M | LIKELY FAILS |
| 15 | rack / spoon | H NE fills the left third; spoon crosses his arm | M-H hand-over; spoon end hidden in the tower | M | L rack static all clip (public racks <=4.3 mm, 1.3 deg) | H spoon pick from flat + R->L hand-over + handle-first insertion (grasp must sit on bowl/upper handle) | H tower opening ~18-24 mm in hulls vs ~2 cm handle | H slot 1 | M rack anchor needs geometry or a world link (note 11) | LIKELY FAILS |
| 16 | rack / spoon | H NE larger, hands in lap | M-H two-hand regrasp | M | L rack static all clip | H as 15 (right hand inserts after a two-hand regrasp) | H as 15 | H | M | LIKELY FAILS |
| 19 | sweeper / dustpan | M tiny sweeper in fist; NE forearm and shoe at the left edge | H anchor barely visible during strokes; dustpan dump f144-156 (0.14-0.5x area) | M | H window ~f0-14 (touch ~f16-18); no static end (sweeper still held at f234) | M-H sweeping strokes on table and dustpan (twin 18: 64/154 on-table moving frames); dustpan yawed ~45 deg on the table while held | L sweeper vs dustpan <=3.4 mm | - | M 2-fold, resolved world-free (note 11) | PARTIAL (drag strokes) |
| 20 | blue cup / pitcher | M pitcher cut by border; NE in the mono views | H pitcher truncated f48-96 in cam a; cup moving in hand | H pitcher near camera: use the mono pair, which sees the gripping hand | H no window (cup in mid-air at f0); static end ~f160-201 | H frame-0 grasp must hold the cup at reset (12-15 mm free fall per step); pitcher lift 32 cm / 92 deg | L | - | H blue cup spin from markers, cup partly in fist | LIKELY FAILS (frame-0 grasp) |
| 25 | board 1 / board 2 | H identical-looking boards: identity from marker layout and numerals; standing and seated people | H thin boards edge-on; fine two-hand adjustment | H edge-on 7.5-9 mm plates | M window ~f0-30; end-snap prior (note 11) | H flat-plate pick-up by slide to the table edge + pivot (twin 23: 68/87 on-table moving frames), stand on edge, slot together | L slot survives (16 vs 9.1 mm); cross 1.7-3.0 mm, own-hull inflation only | - | M 2-fold + identity | LIKELY FAILS (non-prehensile pre-grasp) |
| 28 | rack / pot | H white pot on white rack; NE forearm every frame | H ~180 deg roll about the handle axis (~140 deg/s) at the top border f88-133; hand-over | M-H pot near camera f24-40: mono views keep it in frame | L rack static all clip | H both hands on one 18x31 mm handle with ~157 mm free length during the hand-over; roll under ~0.6 N m handle torque | M-H inverted pot on rack 7.2-9.8 mm inside hulls | - | L | LIKELY FAILS |
| 30 | sweeper / rack | M sweeper among white fins; NE forearm and shoe at the left edge | M-H sweeper in fist while scrubbing; hidden by fins at start and end | M | H window ~f0-22 (twin 31: first GT shift f24-26, 8.4 deg before its lift) | M ring grasp easy; scrubbing presses on a 0.3 kg rack held by the other hand | H anchor starts inside the rack hulls (twin 31 f0: 10.5 mm; eval depth not measured); approx push-out 1-4 cm, 3-33 deg; end state 13-15 mm | - | M 2-fold, resolved world-free | PARTIAL (anchor asset) |
| 32 | blue cup / spoon | M | H spoon bowl inside cup; blur | M | H no clean window (hand on the resting cup at f0; lift ~f10-16); static end ~f190-258 | M-H f0 hand contact must neither penetrate nor slip; cup held tilted in mid-air ~170 f; spoon pick; stir in cup | M-H cup wall bulges 10-25 mm in hulls | H | H blue cup, no GT prior | PARTIAL (stir contact, f0 contact) |
| 33 | blue cup / spoon | M | H many fast strokes | M | M-H window ~f0-14; static end ~f315-347 | M-H as 32 without the f0 contact | M-H | H | H | PARTIAL (stir contact) |
| 35 | spoon / - | M colour fails on skin, mono on floor: fuse | H end-on views; fists over markers | H axis depth when end-on | M window ~f0-14; static end ~f396-420 | H 5 hand-overs, two-hand phases ~45 % of frames, single-hand only ~35 % | M own thin hulls | H anchor; roll ~50/50 | H roll | LIKELY FAILS (switch count) |
| 36 | spoon / - | M | H three end-on phases (f72-84, f120, f156) | H | M window ~f0-22; static end ~f384-406 | M-H 2 hand-overs (f192-204, f276-288) + one-hand lift-and-point-away cycles; bowl may touch the table f96/132/168 | M | H anchor | H roll | AT RISK (borderline) |
| 37 | spoon / - | L | M blur at lift | M lift height | M window ~f0-14; static end ~f112-150 | L-M pick from flat, lift, lay back with a small slide | M own asset | H anchor | H roll | FEASIBLE (sanity case) |
| 38 | dustpan / - | L bright yellow-green (blob seed; reject the tape stripes) | M plate edge-on f76-82, but >=0.79x of its area stays visible | M thin plate | M window ~f0-30; static end ~f240-262 | L-M ring-handle grasp, one hand; possible on-table slide f96-120 | L | - | L handle breaks symmetry | FEASIBLE |

Component load (H count, M-H in brackets): TRK 11 (3, 5, 6, 19, 20, 25, 28, 32, 33, 35, 36) [+10, 14, 15, 16, 30];
SPOON 10 (3, 5, 6, 15, 16, 32, 33, 35, 36, 37); GRASP 8 (5, 14, 15, 16, 20, 25, 28, 35) [+6, 10, 19, 32, 33, 36]; SYM 8
(8, 10, 20, 32, 33, 35, 36, 37); SIM 7 (1, 3, 5, 6, 15, 16, 30) [+14, 28, 32, 33]; SMOOTH 7 (5, 6, 14, 19, 20, 30, 32)
[+33]; SEG 5 (10, 15, 16, 25, 28) [+5], with the non-ego stage needed in all 20; STEREO 5 (5, 20, 25, 35, 36) [+28].
Eval 5 has GRASP H but is not on the "likely fails" list: its grasps exist, and the risk is the spoon-pot contact while
the pot is lifted.

## 3. Grasp-synthesis flags (rigid grasp-and-carry per segment, note 10 P9)

### 3.1 Action segments per episode (from sections 8 and 12; frame numbers [E] +-4-8 f)
"Switches" = hand-overs or two-hand regrasps of one object. "Held drag" = object gripped while it slides or turns on the
table (mu = 1, so the hand must supply the table friction). "Tool contact" = a held object pushing on another object.

| ep | f0 state | slot-0 window | switches | two hands on one object | held drag / non-prehensile | tool contact or insertion | contact-critical end |
|---|---|---|---|---|---|---|---|
| 1 | hands open | f0-22 | 0 | - | pot dragged f60-125 | lid off f44, lid on f273 | lid on pot (hull 8 mm) |
| 3 | hands open | f0-48 | 0 | - | pot held on table | stir f96-255 | - |
| 5 | hands open | f0-14 | 0 | - | pot turned f24-40 | stir f56-209, pot lifted f80-112 and again | pot back on table |
| 6 | hands open | f0-14 | 0 | - | pot turned f24-32 | stir f48-176 | - |
| 8 | hands open | f0-40 | 0 | - | pot turned early | pours f64-80, ~f139 | cup set down |
| 10 | hands open | f0-14 | 0 | - | - | nesting f56-88 | nest (hull 4-5 mm) |
| 14 | hands open | f0-14 | 1 (L->R f40-56) | f40-48 | - | - | inverted cup on rack (hull 6-8 mm) |
| 15 | hands open | all (rack) | 1 (R->L ~f45) | ~f45 | spoon pick from flat | handle into tower f75-105 | spoon in tower |
| 16 | hands open | all (rack) | 1 regrasp | f47-63 | spoon pick from flat | handle into tower f94-125 | spoon in tower |
| 19 | hands reaching | f0-14 | 0 | - | dustpan turned ~45 deg f16-32 | sweeping f40-106 | sweeper still in hand |
| 20 | cup in mid-air | none | 0 | - | - | - (pour, no contact) | cup set down f150-160 |
| 25 | hands open | f0-30 | 0 | board 1 f72-129; boards f226-323 | board slid to the edge f48-56 + pivot | interlock f226-323 | standing cross |
| 28 | L hand moving in | all (rack) | 1 (L->R f48-64) | handle f48-64 | - | - | inverted pot on rack (hull 7-10 mm) |
| 30 | hands open | f0-22 | 0 | - | - | scrubbing f64-170 | sweeper between dividers (hull 13-15 mm) |
| 32 | hand on resting cup | none | 0 | - | spoon pick from flat | stir f80-160 | cup back on table |
| 33 | hands open | f0-14 | 0 | - | spoon pick from flat | stir f72-252 | cup back on table |
| 35 | hands open | f0-14 | 5 | ~45 % of frames | spoon pick from flat | - | spoon down, yaw ~60 deg |
| 36 | hands open | f0-22 | 2 | f192-204, f276-288 | spoon pick from flat; bowl near table f96/132/168 | - | spoon down, yaw ~45 deg |
| 37 | hands open | f0-14 | 0 | - | pick from flat; slide at placement f88-104 | - | spoon back near start |
| 38 | hands open | f0-30 | 0 | - | possible slide f96-120 | - | dustpan flat, yaw ~65 deg |

### 3.2 Verdicts
LIKELY FAILS (7): the key segment is not a rigid grasp-and-carry, or it needs a start state the sampler rules out.
- 20: the frame-0 cup is already in mid-air in the left hand. Reset = exact reference fingers, VOC 0, no hold; a free
  cup falls 12-15 mm in one 50 ms step. [H] Fix: a deliberately pre-loaded (slightly penetrating) frame-0 grasp,
  verified by a frame-0 drop test in the evaluator physics. Any slip in step 1 is absorbed by the scorer alignment and
  misaligns the pitcher for the whole clip.
- 25: boards are 7.5-9 mm plates lying flat. The human slides board 1 to the table edge, pivots it on edge, then slots
  the two boards together with both hands. At mu = 1.0 everywhere a top-press drag is impossible [E]; a lateral edge push
  or pivot primitive (non-prehensile) is needed, followed by an edge pinch.
- 28: L->R hand-over with both hands on one ~157 mm, 18 x 31 mm stick handle, then a ~180 deg wrist roll at ~140 deg/s
  with ~0.6 N m of gravity torque at the grip [E]. Two ~90 mm Sharpa palms do not fit side by side on the free handle
  [E], so the hands collide or one must grip the root or the pot wall.
- 14: mid-air hand-over of a horizontal cup, then a 180 deg flip and an inverted placement on a rack whose hulls the GT
  end pose penetrates by 6-8 mm.
- 15, 16: spoon pick from flat, a hand-over or two-hand regrasp, then a handle-first insertion into a tower whose hull
  opening (~18-24 mm) barely clears a ~2 cm handle. The insertion grasp must sit on the bowl or upper handle.
- 35: 5 hand-overs, each through a 1-1.5 s two-hand phase. Each switch is a discrete failure chance (note 14: one drop
  costs 0.18-0.45 AUC and kills MP-SR). [E] At a 90 % per-switch success rate, 5 switches succeed together only ~59 %.
AT RISK, borderline (1):
- 36: 2 hand-overs on a ~30 cm spoon (room for both palms), one-hand lift-and-point-away cycles in which the bowl may
  touch the table, and three end-on phases that make the reference itself uncertain. The earlier "in-hand twirls" was
  a misreading (section 12).
PARTIAL (8): the grasps are feasible, but a contact segment likely breaks in simulation.
- 3, 5, 6 (stirring in the pot), 32, 33 (stirring in a hand-held cup): the spoon bowl works inside a cavity whose hull
  floor or walls are 5-25 mm off. Every reference error becomes a contact force on a 0.3 kg container. 5 is the worst,
  because the pot is lifted with the spoon inside. In 32 the hand is already on the cup at f0.
- 10: insertion works only with a rim-band grasp (top ~2-3 cm of the beige cup) or a release-and-drop. The nest state
  overlaps the hulls by ~4-5 mm.
- 19: sweeping strokes drag the held sweeper over the table and dustpan, and the dustpan is turned on the table while
  held. Hands are already moving at f0, and slot 0 is still in hand at the end.
- 30: the grasp is easy, but the slot-0 sweeper starts inside the rack hulls (twin 31: 10.5 mm) and the scrub presses
  on a 0.3 kg rack.
FEASIBLE (4): 1 (pot handle + lid bar; the lid states must be hull-aware), 8 (cup wrap and pot handle; the beige spin
is the real risk), 37 (pick, lift, lay back), 38 (one-hand ring handle).

## 4. Stage C measurements (details in sections 7, 11 and 13)
- [V] Collision assets: the public URDFs reuse the visual GLB as the collision mesh (separate *_collision.glb only for
  the sweeper and the boards), mass 0.3 kg as a placeholder. FlashCHORD calls coacd.run_coacd(threshold=0.05,
  max_convex_hull=-1, preprocess_mode="auto") with coacd==1.0.11 pinned (section 11). There is no spoon URDF or mesh.
- [V] CoACD (1.0.14 in section 7, re-run with the pinned 1.0.11 in section 11; hull counts differ, penetrations agree):
  cups keep their cavity, but the walls bulge 10-25+ mm inward at some rim azimuths; the pot basin floor rises 5-25 mm;
  in the rack 57/37/10 % of plan cells rise >5/>10/>25 mm and the tower narrows; the boards' slot survives (16 vs
  19 mm); dustpan, lid and sweeper change by <=10 mm on >90 % of cells.
- [V] GT contact states inside the pinned hulls: lid/pot 7.7-8.4 mm (eps 0, 2); nest 4.1-4.3 mm (11); cup/rack 6.0-8.4
  mm (12, 13); pot/rack 7.2-9.8 mm (26, 27); sweeper/rack 10.5-15.3 mm (31); boards 1.7-3.0 mm, from piece_1's own hull
  inflation only (23, 24); sweeper/dustpan <=3.4 mm (18); separated pairs 0.0 mm. Scan-vs-scan controls 1.0-3.8 mm.
- [E, approximate MuJoCo, section 11] Reset push-out: twin 31 sweeper 4.5-5.4 mm in the first step, 1-4 cm and 3-33 deg
  by 1 s; twin 0 lid 1.7-12.7 mm in the first step, then 9-34 mm. A vertical lift clears the sweeper only at +54 mm and
  it settles ~2 cm above GT, tilted 13-15 deg; the lid settles ~9 mm above GT.
- [V GT] Slot-0 pre-onset perturbation (section 13): first >1 mm or >1 deg at f3-64; 1.0-8.6 deg of rotation before
  the 1 cm onset; racks <=1.3 deg over 155-191 frames.
- [V] On-table moving frames in public GT (lowest scan vertex within 1 cm of the table, >2 cm/s): summary item 8.
  Cups, the pitcher and most pot motions are airborne.
- [V] Sizes: cups rim ~88 mm, 100-111 mm max width incl. markers, 170 mm tall; pot body ~186 mm, free handle ~157 mm, ~18 x 31 mm
  (section 13); pitcher 141x272x415 mm; lid 190 mm; rack 117x175x510 mm; sweeper 48x114x142 mm; dustpan plate ~3-4 mm
  [E]; boards 139x227 mm, 7.5/9.1 mm thick; spoon ~30 cm, ~2 cm round handle (note 13).

## 5. Design needs (consolidated across stages A, B and C; method only, no per-episode labels)
1. Rig: no 180-degree re-rotation. Use the calibration as given (stereo left = ego_cam_c, right = ego_cam_b; the colour
   extrinsic targets cam_b, section 11). Track in the mono pair whenever the colour view truncates an object (20, 28).
2. Non-ego rejection by default, in colour and mono: accept only arms that enter from the bottom border and stay
   connected to it; use the white smartwatch on the left wrist as a left-hand cue [H]. The second person also wears a
   watch, so the cue must be colour-specific.
3. Anchor: estimate the slot-0 frame-0 pose only from frames before first hand contact, detected automatically (hand
   mask touching the object mask). Where that window is empty (20) or contact is already present (32), use the static
   END segment propagated backward through the track, plus support and stable-face priors (note 11). Never average up
   to the 1 cm onset (1-8.6 deg bias in public GT).
4. Hull-aware references: reproduce FlashCHORD's convex_decompose (coacd 1.0.11, threshold 0.05) offline, project every
   reference pose to non-penetration against those hulls, and run a frame-0 settle or drop test in the evaluator physics
   before any RL spend. Ask the organisers whether we may supply collision meshes (note 10 Q4). Without this, eval 30's
   anchor, 1, 10, 14, 28 and the stirring clips start or end in interpenetration.
5. Per-segment action typing from object kinematics, hand contact and support contact: static / carry / held drag /
   on-table slide or pivot / hand-over / tool contact (stir, sweep, scrub) / insertion / in-hand reorientation. Carry
   goes to grasp synthesis; slides to a lateral push or pivot primitive (mu = 1); hand-overs and tool contact to the
   repaired human-hand fallback with extra seeds.
6. Task-constrained grasp locations: rim band for nesting (10), bowl or upper handle for handle-first insertion (15/16),
   handle root plus pot wall for the second hand in the pot hand-over (28), frame-0 pre-loaded grasps (20; contact at f0
   in 32).
7. Spoon: our own mesh, collision hulls and inertia, a marker-based pose (note 13) and a roll sign rule. Also a
   collision-aware smoother against the container hulls in 3/5/6/32/33 and the tower in 15/16.
8. Symmetric anchors: blue cup (10, 14, 20, 32, 33) and beige cup (8) need the marker-layout spin with a sphere detector
   that finds silhouette spheres (note 12); rack (15, 16) needs geometry or a world link (note 11); board identity (25)
   from the marker layout, never image position.
9. Budget: the 7 "likely fails" episodes plus 36 are where extra seeds (note 14 best-of-N) and per-segment fallbacks pay
   most; 35 alone has 5 switch points.

## 6. Development cases with public GT for each risk (falsification tests)
| risk | public dev case | test that could falsify the fix |
|---|---|---|
| anchor window before first contact (all) | all 20 public eps (c2/preonset.out); 31 and 22 for small anchors | "pre-contact only" vs "up to 1 cm onset" anchors against GT frame 0: the fix fails if pre-contact is not better by >=1 deg |
| frame-0 in-hand anchor (20) | 21/22 trimmed to start after the cup grasp (~f17-35) | back-propagated anchor error vs GT; frame-0 drop test of the pre-loaded grasp in sim |
| hull interpenetration at reset (30, 1) | 31 f0 (sweeper in dividers), 0/2 f0 (lid on pot) | the hull-aware projected start must settle <2 mm / <1 deg in 1 s at VOC 0 |
| placement on the inflated rack (14, 28) | 12/13 end, 27 end | end pose after settling vs GT; the policy must not knock the rack |
| flat-plate pick-up by slide or pivot (25) | 23/24 piece_1 (68/87 on-table frames) | a push primitive reproduces a 7 cm slide and the pivot in sim within 1 cm / 5 deg |
| sweeping drags (19), dustpan dump visibility | 18 (dump dip f140-152 matches eval 19 f144-156) | sweeper and dustpan tracking error during on-table runs and the dip |
| nesting insertion (10) | 11 | beige final height within 5 mm of GT in sim with a rim-band grasp |
| hand-over on a handle (28) | 27 is single-handed; 26 has the left hand on the tower | no public two-hand handle hand-over: sim-only feasibility test with two Sharpa hands on the pot handle |
| stirring / tool contact (3/5/6/32/33) | none with GT (no spoon) | proxy: sweeper-in-dustpan contact (18) |
| spoon hand-overs (35/36) | none (dustpan hand-over in 39 as a proxy) | count of discrete drops over 3 seeds |
| non-ego rejection (all) | 22, 23, 27 (second people) | a small hand-audited sample of public frames (development only): zero ego-hand detections on the second person |

