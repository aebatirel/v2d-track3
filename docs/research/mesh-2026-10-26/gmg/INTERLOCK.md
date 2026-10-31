# gmg INTERLOCK stage: slots, seats and cavities that let touching objects fit (design v1)

Date: 2026-10-31. Written at repo commit `de64bd3` (branch `claude/bold-albattani-6qmxsv`). Status: **design, not built**.
This file adds a stage to the frozen gmg design (`SPEC.md`, `PREREG.md`, freeze `fd814f6`). SPEC.md is not edited.
The selection-rule changes are pre-registered as PREREG section F entry **F-I1** (dated 2026-10-31). If this file and
PREREG F-I1 disagree, PREREG wins. Writing it used **zero new scan scorings**; no gmg scoring round has run yet.
It replaces the stopped placement-slot design (`build/P.md`): the placement and physics checks are in section 5.

Labels: [D] measured against a scan (older work), [M] measured without a scan, [E] estimate, [H] hypothesis,
[R] read from code or documents. "dev" = computed from `obs_all` points (library_v3 ROI and `--others`; partner
points near the library meshes removed), never evidence for a pre-registered rule. Probe code and outputs of this
design: `build/I/` (copied from the session scratchpad `interlock/`).

---

## 0. For the owner (one page)

**The problem.** The two wooden boards have a slot: a narrow notch from one edge to about the middle, so they slide
into each other and form a cross (ep24 public, eval 25). Our gmg meshes come from stereo depth, and stereo cannot see a
1 cm gap: it paints wood across it. Without the slot the simulator cannot assemble the cross, whatever the policy does.
The same kind of problem appears wherever objects fit together: a lid seated in the pot rim, a cup stacked in a cup, a
cup or pot in the rack, the sweeper in the dust pan.

**What I measured today** (CPU, dev data, no scan):
- Along our own ep24 track, board 2 slides into board 1 on a straight 12 cm path (straightness 0.91) during 56 frames.
  In board 1's own frame the space it passes through sits at the middle of the board's long side, and the half it
  enters first runs from one edge to the middle. That is exactly where SAM 3D draws the slot (4 of 4 runs: centred on
  the long side, from one edge to 0.42-0.48 of the width). Board 2 shows the same from the opposite edge. [M, dev]
- Our depth grid marks 100 % of that space as "seen solid". So a rule "never carve what the cameras saw" would never
  open a slot; the camera silhouette (which does see through the slot, measured on 22 Oct) has to take part. [M, dev]
- The existing contact veto (V2) misses it completely: it looks for partner points deeper than 8 mm inside the
  candidate, and a 1-2 cm board is never that deep anywhere. The board-2 HULL (a 6.8 cm box) passes it. [M, dev]

**The idea: three independent witnesses, cross-checked.**
1. **Shape from the image:** SAM 3D sees the slot. Its mesh is placed in our frame from our metric depth.
2. **Silhouette:** in camera images where the boards are apart, background shows through the slot.
3. **Motion and physics:** the space the other piece passes through, again and again at the same place in this
   piece's own frame, while it slides in, must be empty. Two solid pieces cannot share space.

**What happens with the result.**
- **Simulator copy: always** when the motion witness passes its tests. The copy is delivered as our own convex
  pieces, which the simulator's decomposition (CoACD) cannot refill.
- **Submitted mesh: only** when two witnesses agree (at least one of them the silhouette or the motion), and the
  slotted mesh then wins the normal frozen selection with extra flip and registration guards. In October, carving the
  submitted board mesh without such agreement flipped its registration (ADD +103 mm) and made CD-O slightly worse; the
  simulator-only carve is what helped eval 25 (0.71 -> 0.79 [M]). A one-time scan check at round R1 reverts all
  submitted carves if, taken together, they make CD-O worse or add a flip.

**The Embodiment session's frame-by-frame physics fix (your 08:50 request).** Their fit tells us, frame by frame,
where it had to push two objects apart and could not do it within its small pose budget (1 cm, 3 degrees). One
shared gmg rule then decides per place: **carve** (a real slot or cavity: entered at the same place in the target's
frame for many frames, while the other piece moves through it, not seen as solid by our cameras, and small; a notch
too narrow for stereo, which stereo paints solid but the silhouette cannot check, counts as not seen) or
**push** (a track error: for example a cup that sinks through a cup bottom we saw). They re-run with the carved
simulator copies. At most 3 rounds; each round must reduce the leftover penetration and pushes, else it is undone.

**Checks for every candidate along the whole movement** (the placement and physics slot you asked for): does the mesh
stay on our depth in every frame (a constant offset is a placement error, a drift is a track error), does it overlap
a partner or the table in any phase (rest, contact, assembled), does it rest the way the video shows.

**Board 2's HULL pick** (the 6.8 cm box) is fixed three ways: slotted candidates exist (from the shell, from SAM 3D and
from a plate model), the new volume-based interlock check vetoes slot-less meshes when a slotted one passes, and a HULL
can no longer win just because the thin shell is flagged as flip-risky (the SPEC calls the HULL "fallback only").

**Cost.** CPU core $0, about 5-15 CPU-minutes per two-object episode [E]. GPU: SAM 3D on board views is added to the
planned G1/G2/G4 batches, about +$0.5-1.5 in total [E]. Nothing is rented by this design. No owner decision is needed
to build it; the GPU additions are stated with cost when G1 is proposed.

---

## 1. Evidence behind the design

| # | Fact | Label, source |
|---|---|---|
| E1 | ep24, board 1 <- board 2 along our tracks: 56 of 79 contact frames enter board 1's HULL (f164-274); partner origin travel 118.6 mm, straightness 0.91, along board 1's width axis | [M, dev] `build/I/probe_ep24b.json` |
| E2 | Region entered in >= 10 frames: at 0.53-0.58 of the long axis, 12.5 mm wide (7.1 mm at >= 28 frames), full width; its entry half spans 0.01-0.48 of the width. Board 2: entry half 0.49-1.05 (the opposite edge); entry side holds 54-57 % of the frame counts | [M, dev] same |
| E3 | 100 % of the entered voxels are OBSERVED in the dev depth grids of both boards | [M, dev]; dev grids may also hold partner points (obs_all ownership), so the clean share is a test (T-I2) |
| E4 | V2 (a) finds 0 partner samples deeper than b (8.0 / 7.7 mm) in either board's shell or HULL; the B5 pool's V2 medians are 8 and 13 against thresholds 39 and 65 | [M, dev] `build/I/pairs_ep24.json`, B5 pool |
| E5 | SAM 3D boards (4 runs): slot centred at 0.50 of the long axis, from one edge to 0.42-0.48 of the width, slot width 1.2-3.0 % of the length (narrower than a board); Pixal3D-MV: shallower notch (0.27 of the width), and its ep23 board 2 copied the partner board (a perpendicular plate) | [M, dev, generator outputs of 29 Oct, crops seeded with library_v3: refused in clean mode] `build/I/sam_slot.json`, `build/look/sam_boards.png` |
| E6 | ep2 pot <- lid: HULL entered in 54 frames, travel 20.2 mm, straightness 0.61 (a seat), region 1.6 cm3, all OBSERVED, 6-7 mm deep (a pose push of < 1 cm removes it); shells 0 | [M, dev] `build/I/pairs_ep2.json` |
| E7 | ep11 cups: no partner sample deeper than b = 8 mm in either cup's shell or HULL | [M, dev; dev overstates separation] `build/I/pairs_ep11.json` |
| E8 | Stereo fills the slot; RGB silhouettes see 89 % of slot voxels as free against 1 % of wood | [M with a scan slot box as diagnostic, i.e. D] work log 22 Oct |
| E9 | FlashCHORD's CoACD refills a carved slot (hull overlap 16.9-17.0 cm3) unless the copy is delivered as our convex pieces | [M] work log 22 Oct |
| E10 | Collision-copy slot carve on library_v3 for eval 25: proxy lag 1.17 cm / 103.7 deg -> 0.06 cm / 0.5 deg; FlashCHORD CPU 7.47 cm / 47.9 deg -> 0.12 cm / 0.4 deg; hull overlap 11.8 -> 0.17 cm3 | [M] work log 26 Oct, `meshes/carve/ev25/` |
| E11 | Carving the submitted mesh: XCarve CD-O +0.006 / +0.007, board 2 new flip (ADD +103 mm), 1.3-1.5 cm3 real wood cut under 5-10 mm track bias; planar cut removes 36-47 % real wood; lid min-cut +0.14 to +0.18 | [D] ledger rows 20, 21, lessons |
| E12 | Board 2's S1 pick on the B5 dev pool is the HULL (6.8 cm thick) because V5 removes the flip-risk shell (amb 4.12 mm vs floor 2.34 mm) | [M, dev] `build/look/ep24_candidates.png`, B5 pool |
| E13 | Collider overlap between objects along our reference drives the largest simulator spreads (evals 30, 14, 1, 10); the 0.219 lid lies 84 % inside the pot's convex hull | [M] keen-heisenberg `arda-feedback-20261031.md` section 7 |
| E14 | A single zero-action replay is chaotic (a 2 mm nudge flips results); judge with jittered means | [M] determined-wright physics README |

---

## 2. Scope: which contacts, which features

The stage is generic. It uses only the roster, our tracks, our grids, our images and (optionally) generator meshes.
There is no board, lid or cup code. Each ordered pair (target o, partner p) with contact frames (SPEC section 4) is
classified per **engaged run**: a maximal run of contact frames in which the partner's evidence occupancy (5.2)
enters the target's candidate by at least 3 voxels (gaps of up to 2 stride frames are bridged).

| Kind (per run) | Test | Public examples -> eval |
|---|---|---|
| INSERTION | partner origin path in o's frame over the run: travel >= 20 mm and straightness (largest singular value / sum) >= 0.7 | boards ep24 (118.6 mm, 0.91) -> eval 25; cup lowered into cup ep11 -> eval 10 |
| SEAT / REST | not INSERTION; the pair holds a relative pose (relative speed < 2 mm per frame) for >= 5 frames | lid on pot ep0/ep2 (20 mm, 0.61) -> eval 1; cup or pot in rack ep12/13/26/27 -> eval 14, 28 |
| SLIDE | not INSERTION, not static | sweeper in rack ep31 -> eval 30 |
| TRANSIENT | run shorter than 5 frames | sweeper + dust pan bristles ep18 -> eval 19 |

The spoon pairs (evals 3, 5, 6, 15, 16, 32, 33) were never measured; they run through the same tests.

---

## 3. Where a slot, seat or cavity comes from (three sources and their cross-check)

All regions live in the **target's own tracked frame**, on the target's 4 mm grid (the bundle grid), with a 2 mm
refinement inside the region for carving.

### 3.1 Source (a): generator shape placed in our frame
- **Input.** GEN meshes (SAM 3D with our metric pointmap; Pixal3D-MV) from separated, hand-free views only (SPEC
  section 4, mechanism 2), never contact frames (E5: Pixal3D-MV copied the partner board from a contact view).
- **Placement** (section 7): SAM 3D layout mapped by `inv(cam_T_obj[k])`, consensus over views and seeds, then M11.
  Near-symmetric flips are resolved in this order: trusted marker balls (the generated posts and balls matched to our
  detected balls, SPEC section 10), then the slot side against the motion region (3.3), then the depth residual.
- **Concavity set C_a.** Voxelise the placed generator solid S_g at 2 mm. Notches: closing(S_g, r) minus S_g with
  r = max(6 mm, partner thickness at the crossing); cavities: convex hull of S_g minus S_g. Only the part within 2
  voxels of the motion region R_c (3.3) is used for agreement; the rest of C_a is ignored by this stage.
- **What (a) is trusted for:** side, position and depth of the feature (where the slot is, which edge, how far it
  reaches). **Not** its width: SAM's slot is 1.2-3.0 % of the board length, narrower than the partner board (E5).
- **FUSE must not refill it.** The FUSE producer (SPEC section 8) keeps our shell wherever a voxel is OBSERVED. In the
  slot those voxels are OBSERVED by stereo bridging (E3), so plain FUSE would refill the slot. New variant **FUSE-I**
  (B15): before the union, the observed shell is cut by the accepted region R* (3.4) of tier T2 or T3; the
  generated emptiness is kept there. Plain FUSE stays in the pool; selection decides.
- **Remesh check.** M10 (`remesh.watertight` + `fit_budget(4000)`) can close a 3-7 mm slot. For any GEN mesh with a
  concavity in R_c's neighbourhood, at least 80 % of that concavity's volume must survive remesh and budget; otherwise
  the GEN mesh is kept, but source (a) counts as absent for that run (flag `gen_slot_lost_in_remesh`).

### 3.2 Source (b): RGB silhouette (sees what stereo bridges)
- **Frames:** good frames in which the target is 2-D separated from every partner (SPEC section 4), hands cover at most
  25 % of its mask and no hand pixel lies within 16 px of the projected region.
- **Per-pixel classifier, full resolution** (not SAM2's low-resolution masks, which would close a 10-pixel slot).
  Per object and episode: positives = pixels of projected OBSERVED target voxels at least 3 px from the projected
  outline; negatives = pixels whose depth lies more than 20 mm behind the target's projected surface. Features: colour
  (Lab) and a 5x5 local texture. Model: a two-class Gaussian mixture per class (3 components). Fitted on our own pixels
  of that episode only.
- **Votes per voxel** (as the 22 Oct S2 design): for each qualifying frame in which the voxel projects inside the
  image and is not occluded by the partner or a hand, NMV += 1; if its pixel is classified background with
  probability > 0.5, NMF += 1. A voxel is **see-through (SIL)** if NMF >= 3 and NMF >= 0.5 NMV.
- **Contrast gate (GT-free).** The silhouette is used for an object only if (i) the classifier's held-out accuracy on
  a 20 % pixel split is >= 0.9 and (ii) the false see-through share on strongly OBSERVED interior voxels (hits >= 10,
  at least 2 voxels from the outline) is <= 2 %. White objects on the light table are expected to fail the gate [H];
  then (b) is "absent", not "disagrees".
- **Region R_b** = SIL voxels inside the target's candidate occupancy, within 2 voxels of R_c (or of C_a if R_c is
  empty).

### 3.3 Source (c): motion-required empty space (swept partner, robust to jitter)
- **Partner evidence occupancy.** The partner's OBSERVED and shared voxel centres (one sample per voxel, as V2's P_p,
  plus 2 mm sub-samples so that a 10 mm plate is 5 samples thick), **minus the partner's own accepted region R*_p**
  (so the partner's own bridged slot does not count as its material). Computed for both objects first; then each
  side uses the other's R*.
- **Entered count.** In each frame of an engaged run, the samples are moved into o's frame through the two tracks
  (T_{o<-p}[f]). Voxel v of o is *entered* in frame f if a sample lands in v and v lies inside the candidate (for
  regions) or anywhere (for the carve rule on external meshes). n_v = number of run frames in which v is entered.
- **Persistent:** n_v >= max(5, ceil(0.25 N_run)). Five frames is the minimum count the Embodiment session asked for;
  25 % is a quartile. Single-frame jitter cannot make a voxel persistent.
- **Swept:** the partner-local positions of the samples that entered v (mapped back by inv(T_{o<-p}[f])) span at
  least s_min = max(8 mm, 3 j) at their 90th-percentile extent. j is the pair jitter (PREREG A.2). A partner merely
  resting with a pose error enters v with the same few partner points (spread about j); a partner sliding in enters v
  with a moving part of itself.
- **Insertion split** (XCarve R2, ported). If the persistent region spans >= 0.9 of o's extent along the insertion
  direction d (a through-column, which happens when the partner's own slot is bridged in its observation), it is split
  by one plane normal to d: o keeps the far side and loses the **entry side** (where the partner came from). The plane
  goes through the region's centroid, or through the end of C_a if (a) agrees (3.4). **One shared plane per pair**: it
  is computed once in o's frame at the median assembled relative pose and mapped into p's frame, so the two half
  notches meet (the 26 Oct lesson: two separate planes left a 1.3 cm uncut band). [M, dev] E2 shows the entry halves
  on opposite edges, as a cross-lap joint requires.
- **Track health.** Source (c) is used only if both objects are not TRACK_FAIL or IDENTITY_SWAP (PREREG B.15) and both
  are good in >= 80 % of the run's frames. eval 25's 22 Oct identity swap would otherwise carve the wrong board.
- **Region R_c** = the persistent, swept voxels (after the split), 26-connected components, each handled separately.

### 3.4 Cross-check (d): agreement decides confidence and destination
Per component R of R_c (or of C_a when no motion exists):

| Pair of sources | Agree if |
|---|---|
| (a, c) | centroid distance <= 10 mm; principal-axis angle <= 15 deg; >= 50 % of R inside C_a dilated by 1 voxel; C_a on the entry side |
| (b, c) | >= 50 % of R's silhouette-testable voxels (NMV >= 3) are SIL |
| (a, b) | >= 50 % of R_b inside C_a dilated by 1 voxel |

10 mm and 15 deg reuse PREREG K-c; 50 % is a majority. A source is **absent** if it was not run, failed its own
gate (3.2 contrast gate, 3.1 remesh check, 3.3 track health) or covers too little (fewer than 3 testable voxels); it
**disagrees** if present and its agreement test with (c) fails. Tiers:

| Tier | Sources | Simulator copy (section 4 decides per voxel class) | Submitted mesh |
|---|---|---|---|
| **T3** | (a), (b), (c) present, all three pairs agree | carve | ICARVE and FUSE-I candidates enter S1 |
| **T2** | exactly two agree: (a, c), (b, c), or (a, b) with (c) absent | carve if (c) is one of the two | ICARVE and FUSE-I candidates enter S1 |
| **T1** | (c) present; (a) and (b) absent or disagreeing | carve | no (flag `interlock_disagree` if a source disagrees) |
| **T0** | no (c), and not T2 | no | no (report; (b) alone is the 22 Oct silhouette free-space idea, out of this stage's scope) |

The accepted region **R*** of a target is the union of its carved components (simulator copy), and of its T2 and T3
components (submitted candidates and the E exclusion of section 8). A testable silhouette that does **not** see
through a region is not "absent": its voxels are class O in section 4 and the region is pushed, not carved.

**What each source is trusted for, in the carve.** Position and end of the feature: (a) when it agrees, else the
split plane of (c). Width in the simulator copy: the 1-99 % extent of the partner samples that entered R at the
assembled frames, across the feature, plus 1 mm clearance per side (as `interaction_carve.py`). Width in a submitted
ICARVE candidate: the partner's own measured two-sided thickness at the crossing (else its pick's thickness there),
never more than the simulator width: the real slot must be at least as wide as the partner, and nothing supports more.

---

## 4. The carve rule (one implementation, used by the gmg and by the Embodiment session)

`gmg/interlock.py: decide(region, evidence) -> CARVE | PUSH | IGNORE`, applied to each persistent component R of a
target, whether the intrusions came from our tracks (3.3) or from the Embodiment's export (section 11).

**Voxel classes** (from the target's bundle grids and source (b)):
- **U** = FREE or UNKNOWN in the depth state grid (the cameras saw it empty, or never saw it);
- **SIL** = OBSERVED in depth but see-through in the silhouette (3.2): stereo bridging;
- **GAP** = OBSERVED, the silhouette is absent for it (gate failed or fewer than 3 testable views; a testable
  silhouette that says solid makes the voxel O), the component is narrow across its thinnest axis (at most w_bridge =
  8 depth pixels at the region's median camera range: two cells of a quarter-resolution stereo cost volume on the
  half-resolution depth input [H]; about 15 mm at 0.55 m), and removing it keeps the target's topology (a notch, not
  a hole or a split). This is a gap stereo cannot resolve: "stereo-solid", not "camera-solid";
- **O** = every other OBSERVED voxel: surface our cameras saw as solid.

**Decision for one component R** (R_U = R in U, R_O = R in SIL, GAP or O):
1. **IGNORE** if the run is TRANSIENT (< 5 frames) or R has fewer than 3 voxels.
2. **PUSH all of R** if more than 25 % of R is class O (the cameras saw solid surface where the partner is placed:
   the pose is wrong, not the shape). Nothing of R is carved.
3. **R_U -> CARVE** (SPEC section 4 mechanism 4 with persistence: no completed volume where the partner persistently
   sat) unless the topology guard fails: the carved solid must keep its number of components and its genus (no
   through-hole). A cup floor that the partner sinks through would open a hole: PUSH. No motion test is needed for U:
   it is completion or seen-empty space, not observation.
4. **R_O** is carved only if all of these hold:
   - (i) **swept**: at least 50 % of R_O's voxels pass the swept test (3.3), and the run is INSERTION or SLIDE;
   - (ii) **not pushable**: over the frames in which R is entered, the median of the smallest pose correction that
     removes the intrusion exceeds the physics prior (10 mm, 3 deg). Our proxy: the smallest rigid translation of the
     partner, over 26 directions plus R's normal, that leaves fewer than 3 entered voxels. With the Embodiment's
     export: their `pushed_residual_m` above the band b in at least half of those frames;
   - (iii) **evidence class**: at least 75 % of R_O is SIL or GAP. Only SIL and GAP voxels are carved; class O voxels
     (surface our cameras saw as solid) never are, and they are listed in the report;
   - (iv) **budget**: the SIL and GAP voxels carved by all components of this target add up to at most 10 % of the
     target candidate's solid volume; R reaches at most 0.6 of the target's extent along the entry direction; the
     topology guard of step 3 holds.
   If all hold: **CARVE** (the SIL and GAP voxels of R_O) in the simulator copy; the tier of 3.4 decides whether
   submitted candidates are built. Otherwise **PUSH** R_O (if (ii) failed, a pose correction removes it; if (i), (iii)
   or (iv) failed and the intrusion is not pushable either, flag `interlock_unresolved`, handed to the Embodiment
   loop and the tracker).
5. Every decision is written with its reasons and numbers (persistent frames, sweep, push distance, class mix,
   budget, tier).

Worked cases [M, dev, and expected]:
- **Board slot (ep24, eval 25):** INSERTION, swept, push distance about the slot length (6 cm) -> not pushable; voxels
  OBSERVED (E3) -> SIL if the silhouette passes its gate and sees through, else GAP (narrow notch, topology kept) ->
  CARVE in the simulator copy; submitted candidates at T2 or T3 (SAM 3D or the silhouette agreeing with the motion).
- **Lid on pot rim (ep2, eval 1):** SEAT; the rim region is OBSERVED, 6-7 mm deep, pushable (E6) -> PUSH; the lid's
  unseen, thickened underside where the rim sits is U -> CARVE (already done by mechanism 4 for gmg candidates).
- **Cup in cup (ep11, eval 10):** the cavity is U (seen empty from above) -> CARVE in the simulator copy (CoACD would
  fill it); an inner cup that sinks below the outer cup's seen floor enters class O -> PUSH (the case where "our
  reference nests the cup deeper than the shapes allow"; topology guard too).
- **Two objects resting with a pose error:** not swept -> R_O PUSH; R_U carve only where the partner persistently sat
  in unseen space (the Embodiment's caveat is honoured for observed surface).
- **Wandering jitter:** never persistent at one place -> IGNORE.

---

## 5. Physics along our track, for every candidate (the placement and physics checks)

New module `gmg/physcheck.py`; features appended to each candidate's line in `RUN/feat/.../<obj>.jsonl` under key
`phys`. Everything uses our tracks, our grids and our table plane. Cost per candidate: seconds (an SDF grid of the
candidate at 2 mm, then trilinear look-ups) [E].

### 5.1 Per-frame placement consistency with our depth (whole movement)
- For each good frame f: one Gauss-Newton step (repeated to convergence, at most 5) of trimmed point-to-plane
  alignment of frame f's owned points to the candidate, giving a 6-DoF offset delta_f (translation, rotation vector).
  Directions the frame cannot constrain (eigenvalue of the 6x6 information matrix below 1 % of the largest; for
  example sliding along a plate seen face-on) are excluded per frame.
- **Constant part** delta_bar = robust median over good frames; **drift** = median absolute deviation around it, and
  the largest 10-frame block mean deviation (catches steps such as the ep11 outer cup lift).
- **Meaning.**
  - A constant offset says the candidate sits off our observed surface in the tracked frame. CPU candidates are built
    from these points, so for them it should be about 0; for GEN and FUSE it is the placement error. ADD: the kit
    registers our mesh to the scan once, so a constant mesh offset becomes a pose error of about its size in every
    frame [E]. Simulator: the collider sits off the seen surface, so grasps and object-object contacts happen at the
    wrong place.
  - A drift is a per-frame track error: no mesh can fix it. ADD carries it frame by frame. In the simulator it shows
    up as time-varying penetration that the physics fit has to push. It is handed to the tracker session (section 12).
- **Flags:** `placement_offset` if |delta_bar_t| > max(3 sigma, 2 mm) or |delta_bar_r| > 2 deg; `placement_drift` if
  the drift MAD > 3 sigma or a block deviation > max(3 sigma, 5 mm). **Veto VP** (GEN and FUSE only): on held-out
  frames |delta_bar_t| > 10 mm or |delta_bar_r| > 15 deg (the K-c tolerances); CPU candidates are never vetoed by it.

### 5.2 Interpenetration with each partner, per phase (volume, not depth)
- Phases per pair: **apart** (separated frames), **contact** (contact frames outside engaged runs), **engaged** (runs
  of 2), with **assembled** = the last static stretch (relative speed < 2 mm per frame) of an INSERTION or SEAT run.
- I_f(c, p) = volume of the partner evidence occupancy (3.3, minus R*_p) inside candidate c in frame f. Reported per
  phase: median, 90th percentile, max (cm3).
- **Veto VI (interlock):** median of I_f over the assembled frames > 1.0 cm3, applied only if at least one feasible
  candidate of the same target passes VI (as V5). V2 stays as it is; VI catches what V2's depth band cannot (E4).
- For the simulator copy the same measure is computed on the convex pieces (6.1): **collider overlap** per phase
  (keen-heisenberg's suggestion, E13); reported, and part of the interlock test (6.2).

### 5.3 Table penetration along the whole track
- Per good frame: share of 20,000 volume samples more than max(3 sigma, 2 mm) below the table plane. **Veto V4t:**
  share > 1 % in at least 25 % of good frames, applied only if at least one feasible candidate passes it (if none
  does, the track sinks the object and the pair is flagged `track_below_table` for the tracker). This is V4's test
  applied to every frame (a held object cannot be in the table either); 25 % persistence keeps short track dips from
  vetoing a good mesh. V4 (at rest) is unchanged.
  Never a carve (the 22 Oct per-frame `below_carve` erased real wood).

### 5.4 Rest consistency at static segments
- Static segment: object speed < 2 mm per frame for >= 15 frames, no hand keypoint within 30 mm of the candidate.
- On the table: lowest point within max(3 sigma, 2 mm) of the table (else `float_mm` or `sink_mm`), stable pose
  (`trimesh.poses.compute_stable_poses`) within 10 deg of the observed up, centre of mass inside the support polygon.
- On a partner (lid on pot, cup in rack): the candidate's lowest contact region within b of the partner occupancy and
  no penetration deeper than b (the lid seat check).
- Flags only (`rest_mismatch`); the simulator copy repairs the base as SPEC section 14 says.

### 5.5 Hands (report only)
Hand keypoints inside the candidate during holds are reported (`hand_inside_mm3`). Never a veto or a carve: hand
carving removed as much real material as excess (22 Oct, R5).

---

## 6. Simulator copy and the interlock test

### 6.1 Convex pieces CoACD cannot refill (port to our meshes)
New module `gmg/simpieces.py`, a port of `pipeline/collision_decomp.py` (free-space-guided split) and of
`pipeline/interaction_carve.py region_cut` (planar half-cuts), using `gmg.geom` instead of Warp, applied to **our
pick**, never to library meshes.
1. Solid of the pick (full resolution before the 4096-face budget) at 1.5-2 mm; subtract R* (simulator tiers) widened
   by the 1 mm clearance; topology guard.
2. Keep-out set = carved voxels + FREE voxels + SIL voxels + the partner's swept persistent occupancy, within 2
   voxels of the surface.
3. Pieces: convex hulls split by the plane that minimises keep-out volume inside the children (collision_decomp
   recipe); planar slots use the exact half-cut; stop when every hull holds <= 0.3 cm3 of keep-out volume, cap 32
   pieces (64 if the solid is above 300 cm3); each hull reduced to <= 64 vertices.
4. Layout for the Embodiment session and `make_assets.py --pieces`: `DIR/<obj>/<obj>.glb` (visual = the submitted
   mesh, colourless copy for Newton) plus `DIR/<obj>/piece_XX.obj` and `DIR/<obj>/carve.json`; one directory per round
   `RUN/sim/<split>/ep<N>/r<k>/`, never overwritten. Mass from `props_masses_only.json` (their adopted masses).

### 6.2 INTERLOCK TEST in a simulator (per pair with an INSERTION or SEAT run)
- **Proxy (gate, CPU, minutes):** the `interaction_carve.py` MuJoCo proxy, driven by **our tracks' relative path**
  (no reference needed): target fixed, partner welded to a mocap target following T_{o<-p}[f] from 40 frames before the
  first engaged frame to the end; default pieces (our pick, CoACD as FlashCHORD runs it) vs carved pieces vs contact
  off. 16 jittered copies (0.5 mm, 0.005 rad, common random numbers, as `jitter_check.py`); all statistics are means
  over copies.
- **Pass:** at the assembled frames, carved: median lag <= 0.5 cm and <= 5 deg, collider overlap < 1.0 cm3; and it is
  "not pushed apart": the partner's lag never exceeds 1.0 cm after the first assembled frame. **Slot not limiting:**
  default lag < 1 cm and < 10 deg (then carving is not needed for the simulator; the carve is still delivered if it
  passes, flagged). These are the 26 Oct pre-registered thresholds.
- **Delivery:** carved pieces are delivered if they pass, or if they cut the default lag by at least half (flag
  `interlock_test_fail`); else the uncarved free-space pieces are delivered and the pair is handed to the Embodiment
  loop.
- **Confirmation (public dev only, not a gate):** `tools/carve_fc_test.py` in FlashCHORD's own physics on CPU (needs
  the FlashCHORD venv rebuilt; the 26 Oct one is gone from this container [M]).

---

## 7. Generator placement: layout consensus across frames, and what G0/G1 must record

- **Per view and seed** (k, s): SAM 3D layout (R, t, scale) in camera k, mapped to o's frame by `inv(cam_T_obj[k])`.
- **Consensus:** rotations by a chordal L1 mean (Weiszfeld on SO(3)) after aligning each to the consensus modulo the
  generated mesh's own flip set (its self-ambiguity pairs); translation by the geometric median; scale by the median.
  Views more than 15 deg or 10 mm from the consensus are outliers (flag). The flip member is chosen by markers, then
  slot side vs R_c, then depth residual (3.1).
- **Whole-movement check:** the consensus-placed mesh goes through 5.1 on all good frames, not only the view frames.
  This is the GT-free form of "SAM placed it consistently with the movement".
- **Ties to PREREG.** K-c (layout within 10 mm / 15 deg per testable object) and K-d (agreement after `place.fit`)
  stay as they are; the consensus and 5.1 are reported next to them (K-c', report only). G0 (layout-only placement of
  the ep2 lid and pot) additionally reports 5.1 over all good ep2 frames.
- **G0, G1, G2, G4 must additionally record** per run: view frame k, `cam_T_obj[k]`, the mask PNG and its sha256, the
  pointmap sha256, the seed, the raw generated mesh (before remesh), the layout in camera and object frame, runtime.
- **Boards added (G1 and G2):** ep24 board 1 and board 2 on M9's separated, hand-free, face-on views (before the
  insertion, about f < 160 [M, dev]), 1 view x 4 seeds or up to 4 views x 2 seeds. ep23 boards only if they pass the
  identity tests (B.15 predicts ep23 board 2 fails). G4 (eval) uses the same rule on eval 25. Cost +$0.3-0.6 per batch
  [E, from the 29 Oct probe: 104 meshes, 5 generators, $4.36].
- **New probe K-f (report only, no kill rule):** in at least half of the board runs, the placed GEN mesh has a notch
  of length >= 0.3 of the board width from one edge, and it survives remesh (3.1). Prediction: yes (4 of 4 in the
  29 Oct probe) [H].

---

## 8. How it enters selection (summary; exact text in PREREG F-I1)

- **New candidates.**
  - **ICARVE(c)**: for every feasible candidate c of class STRUCT, FUSE, GEN or SHELL (never HULL), c minus the
    submitted carve solid of its T2/T3 components via a manifold boolean; same class as c, flag `interlock_carved`.
  - **FUSE-I** (3.1) when GEN meshes exist.
  - A slotted **plate** comes from P-PROG's slab body (B11) once R* exists: it is ICARVE of the slab, no new grammar.
- **Evidence score E:** held-out points whose voxel lies in the target's T2/T3 components of R* are dropped for
  every candidate of that object (paired), so a slot is not charged for stereo-bridged points. Count reported.
- **New vetoes:** VI (5.2), V4t (5.3), VP (5.1, GEN and FUSE only), and **VF** (flip guard for ICARVE and FUSE-I):
  vetoed if its flip units (PREREG A.5 step 3.2) are fewer than its base candidate's, or its observed flip margin is
  smaller than the base's by more than 1 sigma.
- **V5 clarification:** a HULL candidate does not count as the "feasible candidate that is not flip-risk" that lets V5
  apply. The HULL stays the fallback the SPEC (section 8) says it is.
- **Flags:** `interlock_tier`, `interlock_unresolved` (VI could not be satisfied), `interlock_push` (a PUSH decision,
  handed off), `placement_offset`, `placement_drift`, `rest_mismatch`, `gen_slot_lost_in_remesh`,
  `interlock_test_fail`.
- **R1 and adoption (global, not per object).** For every R1 anchor whose pick is ICARVE or FUSE-I with a carve, its
  base candidate is scored too (R1 at most +10, R2 at most +20; expected 2-4, the boards). The submitted-mesh carve is
  adopted as a **method** only if, over all such objects, mean CD-O(pick) - CD-O(base) <= +0.005 cm and no pick flips
  more than its base; otherwise every ICARVE and FUSE-I pick reverts to its base for submission, and the carve stays in
  the simulator copy only. Scans decide this method choice once; they never choose per object.

### 8.1 The ep24 board-2 HULL pick, step by step [H, to be checked by T-I4]
Today (B5 dev pool): shell (flip-risk) and HULL; V5 removes the shell, so the 6.8 cm HULL wins (E12). With F-I1:
1. the V5 clarification keeps the shell (the only non-flip-risk candidate is a HULL);
2. R* exists for board 2 (T2 or T3 with SAM 3D or a passing silhouette; T1 with motion only), so ICARVE(shell) is
   built when the tier is T2 or better;
3. VI vetoes the slot-less shell and the slot-less HULL when ICARVE(shell) passes VI;
4. the pick is ICARVE(shell), or a slotted STRUCT plate or FUSE-I when B11 or G2 have run; flagged `flip_risk`
   unless trusted markers break the remaining face flip (the slot breaks two of the plate's three 180 deg flips).
If only T1 exists, step 2 builds nothing: the pick is the shell (flag `interlock_unresolved` if VI fails for all),
and the simulator copy is carved anyway.

---

## 9. Per pair

| Pair (public -> eval) | Expected decisions [H] | Simulator | Submitted |
|---|---|---|---|
| boards ep24 -> eval 25 | INSERTION; slot CARVE on both boards, one shared plane | carved pieces; interlock test | ICARVE / FUSE-I if T2 or T3 |
| boards ep23 | identity swap expected (B.15) -> no source (c) | uncarved | no |
| lid + pot ep0/ep2 -> eval 1 | SEAT; rim region PUSH; lid underside U carved by mechanism 4; pot opening kept FREE in the pieces (no lid inside the pot's hull, E13) | pieces | no change |
| cups ep11 -> eval 10 | INSERTION into a U cavity -> CARVE (simulator); inner cup below the seen floor -> PUSH, handed off | pieces with an open cavity | no change |
| cup / pot in rack ep12/13/26/27 -> eval 14, 28 | holder and tray cavities U -> CARVE in the copy; rack fins O -> PUSH | pieces | no change |
| sweeper in rack ep31 -> eval 30 | SLIDE; carve only U or SIL with sweep; otherwise PUSH (the sweeper inside our rack mesh is the largest spread, E13) | pieces | no change |
| sweeper + dust pan ep18 -> eval 19 | TRANSIENT (7 of 177 frames) -> IGNORE | default pieces | no change |
| spoon pairs (7 evals) | measured at run time; spoon into U cavities -> CARVE in the copy | pieces | no change |

---

## 10. What failed before and how this design avoids it

| Earlier result | How this design avoids it |
|---|---|
| XCarve on the submitted board mesh: CD-O +0.006/+0.007, board 2 new flip ADD +103 mm; 1.3-1.5 cm3 real wood cut under track bias [D] | the submitted mesh changes only through ICARVE / FUSE-I candidates at T2/T3 (two agreeing sources, at least one the silhouette or the motion); width = the partner's thickness, not the swept band; VF flip guard; the global R1 adoption check reverts it if it hurts |
| the planar cut removed 36-47 % real wood (track bias about one slot width) [D] | motion-only regions go to the simulator copy only; the end comes from SAM 3D when it agrees; the silhouette bounds the width |
| CoACD refills slots and cavities (16.9-17.0 cm3) [M] | convex pieces of our own (6.1) through `make_assets.py --pieces` |
| two separate cut planes left a 1.3 cm uncut band [M] | one shared plane per pair (3.3) |
| min-cut made the lid worse (+0.14 to +0.18) [D] | no repartition of the interface; seats are PUSH or U-carves |
| per-frame below-table carving erased real wood [D] | the table is a veto (V4t), never a carve |
| hand carving removed as much real material as excess [M] | hands are reported only |
| the old carve ran on library_v3 | inputs are gmg candidates and our own evidence only; the guard refuses library files |
| eval 25's board identity swap | source (c) requires identity-clean, good tracks |
| V2 cannot see plate crossings (today, E4) | VI measures volume per phase |
| Pixal3D-MV copied the partner board (E5) | generator inputs from separated views only; V2 (b) copy clause |
| single chaotic replays misled earlier CPU gates (E14) | 16 jittered copies in every simulator judgement |

---

## 11. Contract with the Embodiment session (determined-wright) — please read this section

Their reply (31 Oct 08:46 UTC, `build/embodiment-reply-20261031.md`) is adopted: export as a standalone GT-free tool on
their reference poses, their field names, their simulator-copy layout, jittered-mean judging, a minimum frame count
and a relative-motion test in the rule.

### 11.1 Ownership
- **Embodiment owns** `tools/intrusion.py` (the export), `pipeline/phys_fit.py` and the solver/RL loop. The gmg never
  edits them.
- **gmg owns** `gmg/interlock.py` (file schema and validator, the carve rule of section 4, the carve function),
  `gmg/simpieces.py` (pieces) and the constants (PREREG F-I1). The Embodiment session never edits them. One
  implementation; both sessions call it.

### 11.2 Intrusion export `intrusions.npz` (schema `gmg-intrusion/1`)
Per **sample** (N rows), their proposed fields:
- `frame` (N,) int32: reference frame index; `target` (N,) int16 and `partner` (N,) int16: indices into `objects`;
- `pts_local` (N,3) float32: the sample's position in the **target's mesh frame** (the frame of the `<obj>.glb` they
  loaded from our sim directory; metres);
- `depth_m` (N,) float32: distance of the sample below the target surface (positive inside). Informative only: in a
  plate crossing no sample is deeper than half the plate (E4), so pushability comes from `pushed_residual_m`.

Per **frame-pair** (P rows, one per frame and ordered pair with any sample), added by us:
- `fp_frame`, `fp_target`, `fp_partner` (P,): keys; `rel_T` (P,4,4) float64: partner pose in the target frame (needed
  for the swept test); `pushed_residual_m` (P,) float32: after the fit's pose correction (inside its 1 cm / 3 deg
  prior), the length of the smallest further rigid translation of the partner that removes the remaining intrusion
  (0 if none remains, NaN if the fit did not run; the rule's "not pushable" is `pushed_residual_m` > b);
  `intr_vol_m3` (P,) float32: sample count x pitch^3 before the correction.

Header `intrusions.json`: `schema`, `objects` (names in slot order), `meshes` {name: {path, sha256}} (must equal the sim
copy we delivered), `reference` {path, sha256}, `pose_source` ("reference" or "phys_fit"), `T`, `fps`, `samples`:
"partner solid grid" with `pitch_m` <= 0.002 (solid samples by winding number, as `interaction_carve.py`; surface
samples under-count a plate crossing), `tool`, `commit`. Validation (`interlock.validate`) refuses a file whose mesh
hashes differ from our delivered round, whose frames are out of range, or whose `rel_T` is not rigid.

### 11.3 The carve function
```python
from gmg import interlock
res = interlock.carve_from_intrusions(
    target="wooden_piece_2",                    # name in the episode roster
    intrusions="…/intrusions.npz",             # schema gmg-intrusion/1 (or our own, from our tracks)
    evidence="RUN/bundle/public/ep24",          # our bundle: hits/free/state grids, sigma, j, census, tracks
    sim_dir="RUN/sim/public/ep24/r0",           # the round they ran on (DIR/<obj>/<obj>.glb + piece_*.obj)
    out_dir="RUN/sim/public/ep24/r1",           # new round; never overwrites
    round=1)
# res.pieces_dir  -> out_dir/<target>/   (<target>.glb, piece_XX.obj, carve.json)
# res.decisions   -> [{region, voxels, cm3, kind, tier, decision: CARVE|PUSH|IGNORE, reasons, push_mm, frames}]
# res.report      -> dict (also out_dir/<target>/carve.json)
```
CLI: `python -m gmg.interlock carve --target NAME --intrusions F --evidence BUNDLE --sim-in DIR --out DIR --round K`.
The evidence (bundle and, if built, the silhouette and generator regions in `RUN/interlock/`) is read through the gmg
guard (no ground truth, no library files). Their reference poses enter only through `rel_T` and the samples.

### 11.4 Rule (section 4, restated for them)
A place in the target's own frame is **carved** only if it is entered in at least max(5, 25 %) of the engaged frames,
and: either it is unseen or seen-empty space (class U) and carving it neither splits the target nor opens a hole; or
it is solid only to stereo (see-through in the silhouette, or a notch at most about 15 mm wide whose removal keeps the
topology, where the silhouette cannot test), the partner **moves through it** (its entering points span
>= max(8 mm, 3 j) of the partner), the fit **could not push** it out within 1 cm / 3 deg (`pushed_residual_m` > b in
>= 50 % of those frames), and the carve stays inside the budget (10 % of the volume, 0.6 of the depth). Surface that a
testable silhouette shows as solid is never carved. Everything else is **push**: their fit, or the tracker, owns it.

### 11.5 Iteration
1. Round 0: the gmg delivers `r0` (pieces with the carves from our own tracks, section 6).
2. They run phys_fit (and/or their loop) on `r0` and export `intrusions_r0`.
3. The gmg runs `carve_from_intrusions` for every target -> `r1` + decisions; PUSH decisions go back to them and to
   the tracker session as a list (frames, object, partner, needed correction).
4. They re-run on `r1`. **Accept round k** only if, as jittered means (`jitter_check.py`, 16 copies, 0.5 mm / 0.005 rad,
   common random numbers), the persistent intrusion volume at engaged frames and the number of frame-pairs with
   `pushed_residual_m` > b both fall relative to round k-1; otherwise round k-1 is final.
5. Stop at round 3, or when a round adds no CARVE decision, or when both measures fall by less than 10 %.
The carve budget is cumulative over rounds, and every round can only carve eligible voxels of the same evidence, so
the loop cannot erode an object. Zero-action `sim_vs_ref` is reported, never used to decide.

### 11.6 Same for public and eval
Identical code, constants frozen from public, no ground truth anywhere (their export reads only their reference and
our meshes; our rule reads our bundle). On eval nothing is compared with public numbers.

---

## 12. Modules, hooks and hand-offs

**New files (this stage; none of build 1's files is edited):**

| Module | Interface | Effort [E] |
|---|---|---|
| `gmg/interlock.py` | `engaged_runs(bundle, o, p)`, `intrusions_from_tracks(bundle, o, p, occ_o) -> IntrusionSet`, `regions(bundle, o, p, cands, sil=None, gen=None) -> [Region]`, `decide(region, evidence)`, `agree(region, sources) -> tier`, `carve_from_intrusions(...)`, `validate(path)`, `icarve(cand, regions) -> cand` | 10 h |
| `gmg/silhouette.py` | `classifier(bundle, obj, video) -> model, gate`, `votes(bundle, obj, video, voxels) -> (nmv, nmf)` | 6 h |
| `gmg/physcheck.py` | `features(mesh, bundle, obj, regions=None) -> dict` (5.1-5.5) | 6 h |
| `gmg/simpieces.py` | `build(mesh, bundle, obj, regions, keepout) -> (dir, report)`; `proxy_test(pieces_o, pieces_p, rel, frames, jitter=16) -> dict` | 8 h |
| `gmg/gen_slot.py` | `concavity(gen_mesh_placed, grid, r) -> C_a`; `layout_consensus(runs, bundle, obj) -> pose, spread, outliers` | 5 h |
| `tests/test_interlock.py` | synthetic plates and controls (T-I1) | 5 h |

**Hooks for build 1** (to be wired by the owners of those steps, B9/B10/B15):
- B9 `simcopy.py` calls `simpieces.build(pick, bundle, obj, regions, keepout)` instead of plain CoACD.
- B10 `run_episode.py`: after the CPU producers, `interlock.regions` per pair; `interlock.icarve` adds ICARVE
  candidates; `physcheck.features` per candidate; select reads VI, V4t, VP, VF and the E exclusion.
- B15: `gen_slot.layout_consensus` before `place.fit`; FUSE-I in `producers/fuse.py`; the M10 slot-survival check.

**New build steps** (after B8, before B10): **BI1** the modules above + T-I1 (CPU); **BI2** dev runs T-I2..T-I8 on
ep24, ep2, ep11, ep12, ep18 (CPU); **BI3** wiring at B10/B15; **BI4** the Embodiment loop (T-I9) once their export
exists.

**Hand-offs.**
- **Embodiment (determined-wright):** section 11; the `r0` sim copies of ep24, ep2, ep11 (public dev) when BI2 is done.
- **Tracker (focused-pascal):** `RUN/interlock/<split>/ep<N>/push_list.json` (PUSH decisions with frames and needed
  corrections) and the `placement_drift` frames per object (expected: the ep11 outer-cup lift, ep0 lid).
- **Analysis (keen-heisenberg):** collider overlap per phase along our tracks for every delivered sim copy (5.2/6.2),
  the census they asked for (evals 30, 14, 1, 10).
- **GPU planning:** the board views and extra records of section 7 go into the G1 proposal.

---

## 13. Pre-registered tests and predictions (frozen in PREREG F-I1)

| ID | Test (data; cost) | Pass | Prediction and falsifier |
|---|---|---|---|
| T-I1 | Synthetic cross-lap plates: two 230 x 125 x 10 mm plates, half-depth 10 mm slots on opposite edges; both slots bridged in the depth state (OBSERVED), see-through in 6 silhouette views; a straight 120 mm insertion over 60 frames plus 30 assembled frames; jitter 0.5 mm / 0.2 deg; a slotted generator plate placed with 4 mm / 5 deg error. Controls: (n1) no generator, no silhouette; (n2) a partner resting 6 mm inside an observed face for 40 frames; (n3) an inner cylinder 12 mm below an outer cup's observed floor (floor testable in the silhouette, not see-through); (n4) a 3-frame contact; (n5) random 3 mm intrusions at random places; (n6) as the main case but the silhouette testable and not see-through in the slots ($0, seconds) | slot centroid error <= 4 mm, slot end within 8 mm, width in [10 mm, 10 + 2j + 4 mm]; tier T3 on both plates; carved pieces' overlap at assembly <= 0.2 cm3; n1 -> T1, carved as GAP in the simulator copy only; n2, n3, n6 -> PUSH (no carve); n4, n5 -> IGNORE | [H] all pass; any miss is a code bug, fixed and logged before BI2 |
| T-I2 | ep24 (dev now, clean when B4's bundle exists): regions from (a) (if GEN exists), (b), (c) and their agreement in mm and deg | reported | [H] clean: (c) entry halves on opposite edges of the two boards; >= 50 % of R_c OBSERVED in the clean grid (bridging; falsified if < 20 %, then GAP is unnecessary); if (b) passes its gate, >= 50 % of R_c is SIL; with SAM 3D, centroid distance (a)-(c) <= 10 mm and angle <= 15 deg on both boards |
| T-I3 | Interlock test (6.2) on ep24 along our tracks, gmg picks, default vs carved pieces (CPU, minutes) | 6.2 pass rule | [H] carved passes (lag <= 0.5 cm / 5 deg, overlap < 1 cm3) and default fails (>= 2 cm or >= 20 deg), as on library_v3 (E10); falsified if carved fails |
| T-I4 | ep24 pool with F-I1 (dev now, clean later) | board 2's pick is not the HULL; VI vetoes the slot-less HULL whenever an ICARVE candidate passes VI | [H] pick = ICARVE(shell) or a slotted STRUCT/FUSE-I, flagged flip_risk unless trusted markers; falsified if the HULL is picked while a non-HULL candidate is feasible |
| T-I5 | ep2 lid + pot | no CARVE of class O on either object; pieces' lid-pot collider overlap at the seated frames <= 1 cm3 | [H] the rim region is PUSH (E6); falsified if any O voxel is carved |
| T-I6 | ep11 cups | the outer cup's pieces keep the cavity (keep-out volume inside hulls <= 0.3 cm3 each); any intrusion below the observed floor is PUSH | [H]; falsified if an observed floor voxel is carved |
| T-I7 | Negative controls: ep18 (sweeper + dust pan), the single-object episodes, ep12/13 cup in rack | ep18: no CARVE; single-object: no region; ep12/13: carves only in U voxels | [H]; falsified by any O carve |
| T-I8 | 5.1 on the dev picks of the 10 anchor pairs | reported | [H] CPU picks: constant offset <= 1 mm on >= 9 of 10; `placement_drift` raised on the ep11 blue cup (lift of 2-5 cm while nested, focused-pascal [M]) |
| T-I9 | Embodiment loop on ep24 and ep11 (needs their export) | 11.5 acceptance | [H] ep24: persistent intrusion volume at engaged frames falls by >= 80 % after round 1, frame-pairs with pushed_residual > b fall by >= 50 %; ep11: no CARVE of the observed floor |
| K-f | SAM 3D board runs in G1 | reported | [H] >= half show the notch and keep it after remesh |

Scan scorings: none in this stage. R1 and R2 gain the base candidates of ICARVE / FUSE-I anchor picks (section 8;
caps in PREREG F-I1.11).

---

## 14. Cost

- **CPU [E]:** intrusions from our tracks per pair (about 50-100k partner samples x 100-300 frames, voxel look-ups):
  under 1 min; silhouette per object: about 0.5 s per qualifying frame, 1-2 min; regions and decisions: seconds;
  ICARVE booleans: seconds per candidate; physcheck: 5-30 s per candidate; pieces: 1-3 min per object; proxy test with
  16 jittered copies: 5-15 min per pair (one copy took about 4 min including setup on 26 Oct [M]). About 5-15
  CPU-minutes per two-object episode, about 0.5-1.5 h added to a public batch, 1-2 h to the eval batch.
- **GPU [E]:** SAM 3D board views: +$0.3-0.6 in each of G1, G2 and G4. No new rental by itself.
- **People-time [E]:** about 40 build-hours (section 12).

## 15. Risks and open points

- **Dev contamination:** E3's 100 % OBSERVED may partly be partner points owned by the target in `obs_all`. T-I2 on
  the clean bundle decides; the rule works either way (U or SIL/GAP).
- **Silhouette gate may fail** on the boards' wood against the table; then the CPU path reaches only T1 (simulator
  copy carved as GAP) and a slotted submitted mesh needs SAM 3D (T2 with (a, c)). Stated plainly: **without G1/G2 and
  without a passing silhouette, the submitted board meshes stay slot-less; the simulator copies are still carved.**
- **GAP softens "never carve what the cameras saw"** for one case only: a narrow notch that stereo cannot resolve, that
  the partner slides through, that no small pose correction removes, and whose removal keeps the topology. A testable
  silhouette that says solid always wins (class O). If T-I2 finds the clean slot voxels mostly not OBSERVED, GAP is
  unused.
- **w_bridge is a hypothesis** (8 depth pixels). T-I2 measures it indirectly.
- **One real insertion example** (ep24 public; eval 25 is the target): thresholds are generic or carried over from
  earlier pre-registrations, not fitted.
- **Cross-lap assumption in the split:** a peg in a blind hole whose sides read solid would lose its tip under the
  split; the split runs only for through-columns, and no such object is in our data.
- **phys_fit v1 was not adopted** by its own gate (frame-0 control); `pushed_residual_m` may come from their v2 or be
  NaN, in which case our push proxy decides.
- **The spoon** pairs are unmeasured; their regions are reported on eval only, never tuned.
