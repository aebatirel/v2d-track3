# Physically valid object meshes: how robust our fixes are, and a robust plan (2026-10-22)

**Labels used below**
- **[M]** We measured it: the repo, the work log or today's object audit. Mocap was used only as a stand-in for diagnostics, after inference.
- **[P]** A paper's own number. We have not reproduced it.
- **[H]** Our hypothesis. Each one comes with a test.
- **[est]** An estimate.
- **checked / unchecked:** "checked" means the fact-check read the paper's full text. "Unchecked" means the sweep found the paper but nobody verified it.

## 0. Short answer

- **The current fixes are not robust as they stand.**
  - All three use the right physics.
  - Each was tuned by hand on one object in one episode.
  - On the eval episodes they will either not run at all (no one applies them to the pitcher), use the wrong settings (a different resting pose), or do damage (settle an object onto the wrong face, or carve a hole in the object it sits in).
- **Other researchers solve the same problem with the same loop.** The field calls it "simulation-ready" or "physically plausible" reconstruction. The loop is:
  1. Reconstruct.
  2. Test the physics in a simulator.
  3. Fix poses: gravity, no penetration, settle onto supports.
  4. Change the shape only where nobody saw it.
  5. Test again.
- **We have to write the code ourselves.**
  - SPARCS, S2MDF and PhysPose have no code.
  - SimuScene's repo is an empty placeholder.
  - Vysics has research-only code that needs the robot's own joint readings, which we do not have.
  - Their constraints are each a few hundred lines of numpy, trimesh and MuJoCo on our own voxel grids, collision pieces and CPU simulator.
- **The robust version is one automatic stage between reconstruction and reference building.** It runs the same way on public and eval episodes:
  - a voxel grid that records what was actually seen;
  - a physics check that needs no ground truth;
  - a pose-or-shape decision before any repair;
  - shape repairs limited to voxels nobody observed;
  - collision pieces we build ourselves;
  - a final re-check, plus a guard so we never ship a policy that scores below doing nothing.

  Cost [est]: about 6–7 days of CPU work to build, and about $40 of GPU time to validate on public episodes.
- **ep18 and ep24 are not the biggest exposure.** They are the twins of eval episodes 19 and 25. The audit found objects we have never simulated with our own meshes that cannot stand or cannot hold anything:
  - water pitcher (eval 20);
  - beige cup (eval 8 and 10);
  - dish rack with no tower floor and holes in its basket (eval 14, 15, 16, 28, 30);
  - blue cup with its cavity floor 5.5 cm too high (eval 10, 14, 32, 33);
  - lid starting 9 mm inside the pot (eval 1).

  **12 of the 20 eval episodes contain an object the audit rates critical or high.**
- **Rule point.** A fix chosen by hand for one eval object (for example, flattening the pitcher because we looked at it) is the per-episode manual edit the novelty review flagged. Every fix must be triggered by the physics check and applied by code, with one global setting.

## 1. Verdict on the three current fixes

### 1a. Flatten the underside along one episode's up direction (`flatten_base.py`, library_v3/v4)

**Measured result [M].** ep18 went from 0.345 to 0.715 (6 evaluations, 5 of 6 rollouts about 0.82). Three caveats:
- one training seed;
- the run also switched rest settling from height-only to stable-pose, so the mesh's share of the gain is not isolated;
- **leaving the objects where they start already scores 0.637 on ep18**, so the gain over doing nothing is about +0.08.

**What is principled.** This is the support constraint. If an object is seen resting on the table, the table plane bounds it from below and it must touch the plane over a real area:
- Vysics' "physible" support points plus its hyperplane bound (checked);
- PhyRecon's "seen resting means stable" (checked).

**What is a hack.**
1. **One up direction from one frame (ep18 f0).** At the resting ups of ep18 and ep31 the flat face is 4.2–6.2° off, with only about 3.5 mm of centre-of-mass margin [M].
2. **A fixed 8 mm band, and it only moves vertices that already exist.** It cannot create a base where the band has nothing to flatten. Atlas3D's bottom Laplacian has the same limit (checked).
3. **Applied by hand, per object.**
4. **Applied blindly, it would flatten a real foot ring or concave base** (cups, pot).
5. **It also edits observed geometry inside the band.** The scan registration uses that geometry.

**Where it fails on eval.**

| Eval | Object | Problem [M] |
|---|---|---|
| 30 | sweeper | Stands between the rack fins at a different up from ep18 f0 |
| 20 | pitcher | Never fixed. Footprint 1.2–1.5 cm², centre of mass 18–26 mm outside it, nearest stable face 62° away |
| 8, 10 | beige cup | 0.5 cm² footprint. Two loose fragments and no bottom: there is nothing for the band to flatten |
| 25 | board 1 | Stands with a +0.4 mm margin after v4 |

### 1b. Carve the slots from the overlap at the assembled pose (ep24)

**What is principled.** This is hard non-penetration between objects that share space:
- S2MDF's constraint "smallest plus second-smallest signed distance ≥ 0" (checked);
- HoloScene's penetration energy (checked).

**What is a hack.**
1. **It uses one frame (the final assembled pose) and one pair.**
2. **It treats all overlap as a shape error.** Some of it is pose error. We have not yet measured how much of the 13.5 cm³ lies outside the column where the boards cross. That part must be fixed by moving the boards, not carving them.
3. **The carved slot copies our own errors.**
   - Our board 2 is 12 mm thick (real: 9 mm).
   - The real slot is about 19 mm wide (note 15).
   - Splitting the shared volume equally gives a diagonal pinch the full height of the board. A real cross-halving joint has two half-depth notches.
4. **A carve in the mesh alone does not reach the simulator.**
   - CoACD (the convex decomposition the simulator uses, threshold 0.05) refills slots, even on the scan's own visual mesh.
   - Decomposed the same way, **the scan's visual meshes also overlap 13.4–13.5 cm³** [M]. The collision step alone makes the X impossible.
   - Note 19 showed that closed convex pieces we build ourselves come back from CoACD unchanged [M].

**The danger of applying this rule generally.** At other object pairs that share space it would cut holes in the host objects, whose surfaces we did see. There the faults are mostly thick walls, missing cavities or pose:

| Pair (eval) | Overlap at frame 0 or the contact frames [M] |
|---|---|
| Lid in pot (1) | 42–43 cm³, 9.2–9.4 mm |
| Cup nest (10) | 60 cm³, 8 mm |
| Sweeper in rack (30) | 7.7 cm³, 13.7 mm |
| Cup on rack peg (14) | Needs a 2.3–2.6 cm lift |

### 1c. Settle resting objects to the nearest stable pose (`contact_retarget --rest_settle`)

**What is principled.** Physics-aware pose refinement and settling: PhysPose and SimuScene (both checked).

**Measured [M].**
- It fixes the rack's float (median gap 0.0 cm on ep27).
- It is needed where the object cannot stand (ep18).
- On ep12, where the objects could already stand, it **lowered** the score: 0.740 vs 0.790 without it (one seed).

**What is a hack.**
1. **It snaps to the nearest stable face of a wrong mesh, with no limit on how far it moves the object.** It would tip the pitcher 62° and the beige cup 46°.
2. **It settles each object on its own, with no support order.** The ep12 cup was settled on a rack that is missing its floor and pegs.
3. **It cannot tell a pose error from a shape error.** SimuScene argues that hovering and sinking often need a shape fix (checked).
4. **It moves seated objects the wrong way.** The lid seated in the pot would be lifted 1.7–1.9 cm onto the rim. The sweeper in the rack would be lifted 3.1 cm.

**What it needs.** Allow only small changes (about 3 mm and 3°). Anything larger goes to the shape-repair branch.

**Bottom line.** The physics is right, but the fixes are not general. The robust version derives the same three constraints automatically from our own tracks, applies them only where we have no observations, and decides between a pose fix and a shape fix from the evidence.

## 2. Ways an object can be invalid in the simulator

| # | Failure | Our evidence [M] | Eval episodes exposed | Cheap check (no ground truth) |
|---|---|---|---|---|
| F1 | Cannot stand at its perceived resting pose (rounded or missing underside or edge) | ep18 sweeper 0.3 cm², centre of mass 3 cm outside. Pitcher 1.2–1.5 cm², 18–26 mm outside, 62°. Beige cup 0.5 cm², 29 mm, 46°. Marginal: board 2 flat +2 mm; board 1 standing +0.4 mm; sweeper at other ups 4–6°; blue cup +0.8 mm and rocks 1–2°; spoon on its back +2–4 mm | 8, 10, 19, 20, 25, 30, spoon episodes | Stable face within 5° of our up, centre-of-mass margin, 1–2 s drop test with the assist off |
| F2 | Floats or sinks at rest | 1–4 cm (ep12/27 rack about 1 cm; ep24 boards 2–4 cm). Objects drop at the start | all | Gap between the mesh and the table plane at each resting segment |
| F3 | A host is missing a thin support (floor, peg, fin) | Rack: tower has no floor, 36% of the basket is holes, fins 2 cm low. Pot bottom 56–61% solid. ep12 cup tips 23° (the rack is the suspected cause [H]) | 14, 15, 16, 28, 30, 3, 5, 6 | Height map of the host vs our stereo depth; drop the placed object and measure how high it ends up |
| F4 | Missing concavity (slot, cavity, basin depth) | Board slots absent. Blue cup's cavity floor 5.5 cm too high | 25, 10, 14, 32, 33 | Notch visible in the plan view (mesh and collision pieces); cavity depth on the cup's axis |
| F5 | Thin parts too thick | Dust pan 11–13 mm (real 3–5), lid 12–13 (2–7), pot walls 15–20 (4), board 2 12 (9). 1 cm step at the dust pan lip | 1, 3, 5, 6, 19, 25 | Thickness map vs observed depth |
| F6 | Overlap at shared contacts caused by pose error | ep0 lid track flipped 180° gives 156 cm³; part of the ep24 overlap is probably pose [H] | 1, 10, 25, 30 | Split the overlap into the crossing or contact region vs elsewhere |
| F7 | Collision geometry inflated by CoACD | Even the scan's hulls start inside each other: lid–pot 7.3–7.8 mm, cup–rack 6.9–7.7, sweeper–rack 9.7–12.4, boards 5.4–5.5 (slot filled), nest 3.9–4.8 | every seated, nested or inserted pair | Hull volume vs mesh volume near contacts; overlap above the measured floor |
| F8 | Topology defects | Beige cup in 2 bodies; rack in 5. Board 1 has 4 spurious holes. 19% of the pitcher's plan view is see-through holes, and its interior is 24–43% solid | 8, 10, 20, rack episodes | Number of pieces, share of see-through holes, interior fill |
| F9 | Wrong mass or centre of mass | Uniform shell density; filled interiors move the centre of mass; the spoon uses a 0.3 kg placeholder [est: a real one is far lighter] | 20 (tall pitcher), spoon episodes | Centre-of-mass shift vs a hollow model; flag only |
| F10 | Objects pop at reset (any of the above at frame 0, assist off) | Lid starts 9 mm inside the pot. The sweeper falls in 5 frames | 1, 19, 20, 25, 30 | Frame-0 test with no policy (`frame_quality_probe`, VOC=0) |
| F11 | Object rests off the simulated table | ep27 rack reaches r = 0.312 m; the table disc is 0.276 m | rack episodes (predicted) | Footprint inside the table disc |
| F12 | Robot hand inside the object | Fixed by contact retargeting (p95 now 2.7–6 mm) | all | Already gated |
| F13 | Damage caused by a repair: stable but wrong shape, or a shifted scan registration | PhyRecon reports bulges in rarely seen regions [P] | any repaired object | Change budget: only unobserved voxels may change; registered score on public episodes |

**Rule note (not physics).** The spoon is a parametric template, not reconstructed from our video. It appears in 10 eval episodes. Confirm with the organisers.

**Probable common cause [H, from reading `recon_mesh.py`].**
- Depth samples within 15 mm of the table never count as surface (`--table_band`).
- For thin objects the hole-closing step grows 12 mm from each wall.

So:
- the bottom 1–1.5 cm of resting objects is never observed;
- a board lying flat (7.5–9 mm thick) gets no surface votes in any frame where it lies flat;
- the 19 mm slot is closed by the closing step.

Experiment X3 tests this.

## 3. Robust staged pipeline

How the literature does it, and what we take:
- SimuScene, RoboSnap and phi-Scene: depenetrate, then settle objects in support order.
- PhysPose: refine poses with gravity and collision costs.
- Vysics and ARM: complete the unseen underside from support constraints.
- S2MDF: hard non-penetration between objects.
- PhyRecon: drop-test stability as a gate.

From each we take the formulation only, not the method: the full methods are either slow or start from a generative prior.

Each stage below runs on CPU, with one global setting, on every object and every episode, and writes its results to a QA file.

### Stage A: record what was seen, and fuse thin objects properly
- **Check:** share of unobserved voxels per object; plate thickness vs observed depth; number of pieces.
- **Repair:**
  1. Keep three voxel states: observed surface, observed empty, never observed. Keep the observation count per voxel.
  2. Keep samples near the table whenever the object is lifted more than 3 cm.
  3. Shrink the table band to about 6 mm in resting frames.
  4. Use 2 mm voxels and 4–5 mm truncation for objects detected as plates (thickness under 15 mm).
  5. Never close holes next to voxels seen empty.
- **Rests on:**
  - Directional TSDF (unchecked, https://arxiv.org/abs/1908.05146) and RoutedFusion (unchecked, https://arxiv.org/abs/2001.04388): plain TSDF fusion thickens thin structures.
  - Scalable Real2Sim (unchecked, https://arxiv.org/abs/2503.00370): accurate undersides come from views where the underside is actually seen.
- **Effort:** about 1 day. **Rule risk:** none.

### Stage B: physics check with no ground truth (the most valuable piece)
- **Resting segments come from our own tracks.** A segment is resting when speed is under 5 mm/s for at least 0.5 s, no hand is within 3 cm, and the object is near the table or another object.
- **Tests:**
  - **(a) Stability.** On the collision-piece union at our perceived up, a stable face within 5° and a centre-of-mass margin of at least 5 mm. This is the same as Atlas3D's tilt test, so we implement one check, not two.
  - **(b) Support gap** within ±2 mm.
  - **(c) Overlap.** At shared contacts, at most 1 cm³ and at most 2 mm beyond the collision floor.
  - **(d) Drop test.** 1–2 s of MuJoCo with the assist off; drift at most 3 mm and 3°. PhyRecon's 5° / 5 cm is too lenient for ADD scoring.
  - **(e) Topology:** number of pieces, see-through holes, minimum thickness.
  - **(f) Frame-0 pop test** with no policy.
- **Objects that support each other are tested together.** A lone real board standing on edge is marginal too (+0.4 mm on the scan [M]); the real X stays up because the boards interlock.
- **Result per object and segment:** pass, pose fix, shape fix, or flag.
- **Rests on:**
  - PhyRecon (checked, https://arxiv.org/abs/2404.16666);
  - Atlas3D (checked, https://arxiv.org/abs/2405.18515);
  - the support-gap and centre-of-mass scores of arXiv 2602.12633 (unchecked, https://arxiv.org/abs/2602.12633).
- **Effort:** about 1 day. Most of it exists: `stand_check.py`, `stab.py`, `pairs.py`, `lift.py`, `frame_quality_probe`. **Rule risk:** none.

### Stage C: decide between a pose fix and a shape fix [H, our own rule]
- **Gap below an object:** if depth rays passed through the gap (observed empty), it is a pose error. If the gap was never observed, it is a shape error.
- **Overlap:** if the overlapping voxels are well-observed surface on both objects, it is a pose error. If they are unobserved or closed voxels, it is a shape error.
- **Note:** SimuScene's rho does **not** make this choice. Both of its branches are shape edits, and it only tests translation, so it misses toppling (checked).
- **Effort:** half a day.

### Stage D: shape repair, only in voxels nobody observed
- **D1. Support-plane completion** (replaces `flatten_base`).
  1. For each resting segment, put the table plane in the object frame.
  2. Remove everything beyond the plane. This half already exists: `--below_carve`.
  3. Fill the unobserved voxels between the plane and the observed surface, inside the object's silhouette hull, and only where the column below was never seen empty.
  4. Each distinct resting orientation adds a plane. For example, the boards' standing frames give flat edges.
  - **Rests on:** Vysics (checked, https://arxiv.org/abs/2504.18719). Take its support-point and hyperplane terms only, not its convexity bias, which would fill slots, cavities and rack gaps. ARM (unchecked, https://arxiv.org/abs/2009.13146) reports that stability reasoning beats plain extrusion [P].
  - **Effort:** 1–2 days.
- **D2. Minimal stability fill.** If an object still fails, grow unobserved voxels at the support plane, inside the footprint's convex hull, until the centre-of-mass margin reaches 5 mm. If that is impossible, flag the object; never change the inertia to hide it.
  - **Rests on:** Make It Stand (unchecked, https://dl.acm.org/doi/10.1145/2461912.2461957); PhysComp's criterion (checked, https://arxiv.org/abs/2405.20510).
  - **Keep the edits to this narrow family.** PhyRecon reports that free-form stability edits grow bulges [P].
  - **Effort:** half a day.
- **D3. Silhouette carving for narrow gaps** (slots, cavities, gaps between fins).
  - Voxels that project outside confident masks in at least k frames become empty.
  - Needs masks in every frame: SAM2 video propagation (a few GPU minutes per episode), or masks seeded from the rendered mesh.
  - **Rests on:** Yemez & Wetherilt 2007 (unchecked); Picasso's free-space constraint (unchecked, https://arxiv.org/abs/2602.08058).
  - **Effort:** 1–1.5 days.
- **D4. Hard non-penetration at shared contacts, with an owner for the shared volume.**
  1. Remove the pose-error part first (Stage C).
  2. On full, untruncated SDFs resampled into one grid, enforce d_A + d_B ≥ 0 (S2MDF).
  3. Give the contested voxels to the object with observation evidence for them. Break ties by insertion direction: the board lowered from above keeps its upper half [H; no paper covers joinery].
  4. Each object must stay one piece. The stage does nothing to objects that never share space.
  - **Rests on:** S2MDF (checked, https://arxiv.org/abs/2605.29761).
  - **Effort:** 1 day.
- **D5. Simple shape families, kept only if they fit better.**
  - A flat slab (an outline extruded to a fixed thickness) for plates: boards, perhaps the dust pan.
  - A surface of revolution for the cup, pot and lid bodies, and the pitcher body with its observed handle kept.
  - Mirror symmetry, checked against observed free space, for the sweeper, dust pan and rack: Bohg 2011 (unchecked, https://doi.org/10.1109/ICRA.2011.5980354).
  - Keep a family only if it fits our depth and masks at least as well as the TSDF and passes Stage B. This is the most likely fix for the beige cup (fragments, no bottom) and the blue cup's cavity.
  - **Effort:** about 1 day per family. **Rule risk:** low (geometric priors on our own data), but ask the organisers.

### Stage E: build the collision pieces ourselves
- **Repair:**
  - Welded, watertight input.
  - Several closed convex `<collision>` pieces per object, using note 19's recommended set: rack and pot split into parts of at most 120 mm, the blue cup in 2 parts. Pieces come back from CoACD unchanged, so slots and cavities survive.
  - Screen each piece on Linux for debris hulls, which crash the MuJoCo build.
- **Check:** the notch is present in the union of collision pieces; overlap at shared contacts within about 1 mm of the floor.
- **Rests on:** note 19 [M]. Our measured result on the public scan assets: the recommended set leaves +0.5 / +1.0 mm above the floor, vs +5.4 / +2.3 mm for the provided assets.
- **Effort:** about 1 day.
- **Rule risk:** note 19's question (a) to the organisers ("may we ship our own collision geometry?") must be answered.

### Stage F: pose repair and settling in support order
1. **Refine poses PhysPose-style.** Keep each pose close to our visual track; penalise collision; add gravity only for unsupported objects.
2. **Settle in support order:** lowest object first (table, then rack, then cup), with objects already placed frozen as static colliders, and stop at first contact.
3. **One final joint settle.** Revert any object that moves more than 1 cm or 5° and flag it for shape repair.
4. **Blend** the settled pose into the motion.

- **Rests on:**
  - PhysPose (checked, https://arxiv.org/abs/2503.23587). Realistic gain is the estimated-scene one, 0.620→0.650 [P], not 0.620→0.707.
  - SimuScene's protocol (checked, https://arxiv.org/abs/2606.03994). Its prior-free stages reach a mean displacement of 0.197, from 0.395 [P].
  - RoboSnap's alternating depenetration and physics (unchecked, https://arxiv.org/abs/2607.06699).
- **Effort:** about 1 day, extending `rest_settle`. **Rule risk:** none (our own meshes, poses and table plane).

### Stage G: check again, and limit how much a repair may change
- Run Stage B again.
- Mask IoU and depth residual against our observations must not get worse.
- Report the volume changed in voxels that were observed (target: zero).
- On public episodes only, after inference: compare the bottom region with the scans, the footprint area, and the mesh-to-scan registered score (a drop above 0.01 rejects the change).

### Stage H: never ship a policy below doing nothing
- Per episode, compare the policy's rollout and a "hold still" rollout against **our** reference (sim-vs-reference, no ground truth). Submit the better one.
- **Why:** on ep18 the base policy scored 0.345 while doing nothing scored 0.637 [M]. `auto_ep.sh` currently has no such guard.
- **Validity of this guard [H]:** experiment X2.

## 4. Experiments, in order of value per cost (13 days to the 4 Nov freeze)

GPU costs: about $2 per 250M-step training, about $3–4 per episode including 6 evaluations.

| # | Question | Falsified if | Cost | Decides |
|---|---|---|---|---|
| X1 | Does the Stage B check catch every failure we know about? Run it on all public episodes and all 11 objects (current libraries), then on eval perception output (no scores) | It misses ep18's sweeper fall, ep24's boards not standing, ep12's 23° cup tip, or the 1–4 cm floats; or it flags more than 20% of objects in good episodes (ep27, 0.94) | 1 CPU day, $0 | Which objects and eval episodes get repair work; the eval risk list |
| X2 | Does sim-vs-reference rank "policy vs do nothing" the same way the registered score does? Uses existing rollouts | Ranking agrees on fewer than 3 of the 4 hard public episodes | Hours, about $0 | Whether Stage H can be used on eval |
| X3 | Cause of rounded undersides, floats and the missing notch. Rebuild with a 6 mm table band and lifted-frame samples. Label the scan's notch voxels as seen empty, seen inside, or closed (diagnostic only) | Gap and contact area unchanged (then floats are pose or table-plane errors); more than 50% of notch voxels "seen inside" (then stereo smears across the slot and silhouette carving is required) | Half a CPU day, $0 | Whether to fix fusion settings (cheap) or add D3 |
| X4 | Stages D1+D2 with one global setting on all objects | Drop-test failure rate not below library_v3; sweeper footprint under 5 cm² (real 11.7); pitcher or beige cup still unstable; objects with concave bottoms get worse; registered score drops more than 0.01 on any object | 1.5–2 CPU days, $0 | Replace `flatten_base` |
| X5 | ep12 cup: rack or cup? Replace the rack with an ideal plane at the cup's observed contact height; compare collision-hull vs mesh volume near the contact | The cup still tips on the ideal plane (then the cup's underside or its pose is at fault) | Half a CPU day, $0 | Rack repair (D1 on the host, finer collision pieces) vs cup repair |
| X6 | Stages C+F (pose-or-shape decision and settling in support order). On public episodes, split each rest gap into pose error (track vs mocap) and shape error (mesh vs scan), diagnostics only | The rule picks correctly less than 80% of the time; floats not under 2 mm; ep12 cup still tips more than 5°; ADD vs mocap on static segments gets worse | 1 CPU day, $0 | Adopt the settle protocol and its limits |
| X7 | Boards: slab fit + silhouette-carved notch + D4 owner rule + our own collision pieces | Overlap not under 1 cm³ (now 13.5); the X does not stand for 2 s with the assist off; notch more than 2 mm off the scan (diagnostic); a board splits into two pieces | 1.5 CPU days + about $1 GPU (SAM2) | Whether eval 25 deserves GPU time |
| X8 | One GPU batch on public twins of the eval risks: ep18, ep24, ep12, ep27 (library_v5 from stages A–F vs current, 6 evaluations each), plus first simulations of pitcher (ep21/22), beige cup (ep11), lid seated (ep0/ep2) and sweeper in rack (ep31) | ep18 under 0.70 without the manual patch; ep24 not above 0.36; ep12 or ep27 drop more than 0.02; any twin below its do-nothing floor | about 8 episodes × $3–4 ≈ $30 | Freeze the pipeline for eval |
| X9 | Second seed on ep18 and ep24 with v5; separate the mesh's share of the gain from the settle mode on ep18 | The gain is inside the spread between seeds | about $10–15 | Confidence in the ep18 and ep24 gains |
| X10 | Generative candidate (Hunyuan3D-Omni or SAM 3D) for unobserved voxels only, and only if X4/D5 fail on the beige cup | Fails Stage B, or residual to observed points above 3 mm | 1 day, about $5 | Low priority; the literature predicts failure |

**Schedule [est]**

| Dates | Work |
|---|---|
| 22–23 Oct | X1, X2, X3, X5. Send the organiser questions (Section 6) |
| 24–27 Oct | Build stages A, C, D, E, F; run X4, X6, X7 |
| 27–28 Oct | X8 |
| 29–30 Oct | Fixes, then X9 |
| 31 Oct–3 Nov | Run the unchanged pipeline on all 20 eval episodes, write the check report, train and evaluate: about $60–80 per seed, plus a second seed where flagged |
| 4 Nov | Pack, commit the exact code, buffer |

GPU total [est]: about $45 for development plus $80–160 for production.

## 5. What not to do

- **Do not port the heavy joint optimisers.**
  - SPARCS: 46–540 CPU-minutes per scene, no code.
  - HoloScene: about 8.3 GPU-hours per scene, plus generative priors.
  - PhyRecon: 12.56 A100-hours per scene [P].
- **Do not use Vysics' convexity loss.** It fills slots, cavities and rack gaps.
- **Do not use Vysics' dynamics inference.** It needs a known pusher geometry and the robot's joint readings; ours are estimated MANO hands.
- **Do not treat Atlas3D's bottom Laplacian as the principled flatten.** It cannot create a footprint.
- **Do not use SimuScene's rho to choose between a pose fix and a shape fix,** and do not use its whole-mesh stretch along gravity. The stretch distorts observed geometry that the scan registration uses, and the test misses toppling.
- **Do not make a generative model the fix.**
  - Real-object completion reaches only about 0.48 IoU (SceneComplete, unchecked [P]).
  - TRELLIS and Hunyuan3D produce 15–30% unstable assets (DSO, checked).
  - It is a rules grey zone.
  - Licence clash: the SAM licence, and Tencent's licence that excludes the EU, UK and South Korea, vs the required Apache-2.0 release.
  - Blackwell build risk.
- **Do not edit the centre of mass or inertia to make a bad mesh stand.** A 0.3 cm² point contact has no stable centre of mass. Use it only as a disclosed fallback for real mass distribution.
- **Do not let stability optimisation change unobserved voxels freely.** It grows bulges.
- **Do not settle every object blindly.** ep12 dropped from 0.790 to 0.740 [M].
- **Do not carve overlaps into hosts or into observed surfaces.**
- **Do not count on a slot carved only in the mesh.** CoACD refills it.
- **Do not tune thresholds on ep18 and ep24 alone,** do not tune on eval results, and do not hand-edit eval meshes guided by public scans (risk under the no-hand-labelling rule).
- **Do not expect PhysPose's known-scene gains.**

## 6. Open uncertainties and questions for the owner

- **For the organisers:**
  1. May we ship our own collision pieces (note 19 question (a))?
  2. Does physics-constrained completion of unseen geometry (support-plane fill, simple shape families) count as "own reconstruction"?
  3. Does the parametric spoon template count?
- **Scan registration.** We do not know how the hidden-scan registration weighs the regions we change. Stage G measures this on public episodes only.
- **Evaluator setup.** Not confirmed that the evaluator runs CoACD on the same platform and with the same contact settings as our check.
- **Mass distribution** of the real objects is unknown.
- **Joinery.** No paper reconstructs interlocking joints from video. The owner rule in D4 is untested.
- **Input coverage.** The research input to this report contained 2 of the 7 angles (physics-aware reconstruction and unseen-geometry completion, with their fact-checks). The object audit was cut off at its collision-inflation point. Conclusions drawn from the missing angles are not reflected here.