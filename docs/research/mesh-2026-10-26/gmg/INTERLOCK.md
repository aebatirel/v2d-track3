# gmg INTERLOCK stage: slots, seats and cavities that let touching objects fit (design v2, built, round-1 fixes)

Date: 2026-10-31. v1 written at repo commit `de64bd3` and committed as `2eb8397`; this v2 answers the design review of
v1 (blocking items B1-B7 and the non-blocking items; section 16 lists each one and where it is resolved). Branch
`claude/bold-albattani-6qmxsv`. Status: **built** (BI1 code and synthetic tests, section 17; BI2 dev runs on ep24, ep2,
ep11, section 18) and **corrected after the verifier's review of the build** (round-1 fixes, PREREG F-I3, section
19). Outcome so far: on the dev runs the rule pushes every pair (no carve); the Embodiment contract now runs on their
real tool (section 19). This file adds a stage to the frozen gmg design
(`SPEC.md`, `PREREG.md`, freeze `fd814f6`). SPEC.md is not edited; the one SPEC rule this stage overrides is named in
section 8 and in PREREG F-I1.0. The selection-rule changes are pre-registered as PREREG section F entry **F-I1**
(dated 2026-10-31, revised the same day). If this file and PREREG F-I1 disagree, PREREG wins. Writing v1 and v2 used
**zero new scan scorings**; no gmg scoring round has run yet. It replaces the stopped placement-slot design
(`build/P.md`): the placement and physics checks are in sections 5 and 6.

Labels: [D] measured against a scan (older work), [M] measured without a scan, [E] estimate, [H] hypothesis,
[R] read from code or documents. "dev" = computed from `obs_all` points (library_v3 ROI and `--others`; partner
points near the library meshes removed), never evidence for a pre-registered rule. Probe code and outputs of this
design: `build/I/` (copied from the session scratchpad `interlock/` and, for the reviewer's probes, `review_I/`).

---

## 0. For the owner (one page)

**The problem.** The two wooden boards have a slot: a narrow notch from one edge to about the middle, so they slide
into each other and form a cross (ep24 public, eval 25). Our gmg meshes come from stereo depth, and stereo cannot see a
narrow gap: it paints wood across it. Without the slot the simulator cannot assemble the cross, whatever the policy
does. The same kind of problem appears wherever objects fit together: a lid seated in the pot rim, a cup stacked in a
cup, a cup or pot in the rack, the sweeper in the dust pan.

**What the dev measurements show** (CPU, no scan; v1 overstated two of them, corrected here):
- Along our ep24 track, board 2 slides into board 1 on a straight 12 cm path (straightness 0.91) during 56 frames.
  In board 1's own frame the space it passes through is a narrow band across the board's full width, centred
  10.5-12.9 mm from the middle of the long side. SAM 3D draws the slot at the middle (4 of 4 runs). So the motion and
  the image agree that a slot crosses the board there, but **disagree by about one slot width on where**; our tracks
  were measured in October to be off by about that much. [M, dev]
- Which half of that band is the slot (which edge it opens to) is **not** measured by the motion. The rule takes the
  half the partner comes from, because that is the only way the partner can get in. v1 presented this "one edge to
  the middle" result as a measurement; it is a consequence of the rule.
- Our depth grid marks that band as seen solid (stereo bridging; in the dev data partner points also leak in). A rule
  "never carve what the cameras saw" alone would never open a slot, so the camera silhouette, or a test of whether
  stereo could have resolved the gap at all, has to take part. [M, dev]
- The existing contact veto (V2) misses plate crossings: it looks for partner points deeper than 8 mm inside the
  candidate, and in a 1-2 cm board none is. [M, dev]

**Three independent witnesses, cross-checked.** (1) Shape from the image: SAM 3D sees the slot; its mesh is placed in
our frame from our metric depth. (2) Silhouette: in views where the boards are apart, background shows through the
slot. (3) Motion and physics: where the other piece passes through, again and again at the same place in this piece's
own frame, must be empty.

**What happens with the result.**
- **Simulator copy:** carved only where the pair passes every test, including physical ones run for **every** carved
  pair: a hands-free settle under gravity (16 jittered copies), a free-travel test (the guest must not be able to drop
  more than 4 mm: in October a carved rack let the sweeper fall through and a carved pot let the lid sink 0.6-1 cm), a
  cap on collision shapes per episode, and per-episode asset folders so one episode's carves never leak into another.
  The copy follows the poses the simulator will replay. **Both pieces of an interlocking pair are carved together or
  not at all.**
- **If the silhouette or SAM 3D sees the slot about 1 cm from where our track pushes the partner through,** the
  simulator copy gets the seen slot moved to where the replay needs it, the tracker gets the offset as a correction to
  check, and only the seen position can go into a submitted mesh.
- **Submitted mesh:** only when two witnesses agree and none disagrees. This reverses one line of the frozen SPEC
  (section 14, "never in the packed mesh"), declared in PREREG F-I1.0. The slotted mesh must still win the frozen
  selection. A one-time scan check at R1 reverts all submitted carves if together they make CD-O worse at all or add a
  flip; that check is the real guard against a repeat of October's board-2 flip (ADD +103 mm).

**The Embodiment session's frame-by-frame physics fix (your 08:50 request).** Their tool reports, frame by frame,
where two objects overlap inside our simulator pieces, in the pieces' own coordinates. One shared gmg rule then decides
per place: **carve** (entered at the same place for many frames while the other piece moves through it, not seen as
solid, small) or **push** (a track error, for example a cup that sinks through a cup bottom we saw). Their pose fit's
"cannot be pushed out within 1 cm / 3 degrees" number counts only if the fit ran on our delivered pieces with
ground-truth-free mass properties; their 30 Oct fit used the public scans and would be refused. A round is kept only
if it reduces overlap on frames the carve was not built from and passes the physical tests; at most 3 rounds.

**Checks for every candidate along the whole movement** (the placement and physics slot you asked for): does the mesh
stay on our depth in every frame (a constant offset is a placement error, a drift is a track error), does it overlap
a partner or the table in any phase (rest, contact, assembled), does it rest the way the video shows.

**Board 2's HULL pick** (6.8 cm thick in its oriented box) wins today only because the thin shell is flagged
flip-risky. With F-I1 a HULL no longer counts as the safe alternative (SPEC section 8 calls it "fallback only"; of the
4 dev objects picked so far only board 2 changes), slot-less candidates are vetoed when a slotted one overlaps the
partner by at least 1 cm3 less, and the R1 scan check also covers this change.

**What the built stage does (31 Oct, dev runs without a scan; sections 18-19).** It pushes the ep24 boards instead
of carving them: the place the partner passes through is 19-25 mm wide in our data (the partner's stereo thickness
plus track jitter), while the real slot looks about 6-8 mm wide in the video [E], so most of that place is wood our
cameras saw, and the rule treats that as a pose error, not a missing slot. A counterfactual slot (never delivered)
lets the simulated cross close to 0.33 cm, against 1.85 cm without it, so the slot itself works; the open problem is
measuring where and how wide it is. The cups and the pot+lid also push. Our own simulator pieces for the open
containers (pot, cups) fill their openings, so those deliveries are marked do-not-use until the splitter is fixed.

**Cost.** CPU only, no rental. The 16-copy physics checks take about 0.6-2.5 CPU-hours per carved pair on our 4 shared
cores [E]. mujoco and coacd are installed in the gmg venv; FlashCHORD's settle is run by the Embodiment session with
its own venv (jitter_check), not here. GPU: SAM 3D on board views added to G1/G2/G4, about +$0.5-1.5 in total [E].
**One owner decision (D-I1):** may
simulator copies and the physics fit use the adopted masses (`props_masses_only.json`, computed from the scans' surface
areas)? Until you say yes they use the 0.3 kg placeholder, on public and eval alike.

---

## 1. Evidence behind the design

| # | Fact | Label, source |
|---|---|---|
| E1 | ep24, board 1 <- board 2 along our tracks: 56 of 79 contact frames enter board 1's HULL (f164-274); partner origin travel 118.6 mm, straightness 0.91, along board 1's width axis | [M, dev] `build/I/probe_ep24b.json` |
| E2 | Board 1's region entered in >= 10 frames: 0.53-0.58 of the long axis (centre 10.5-12.9 mm from the middle of 233.9 mm), 12.5 mm wide (7.1 mm at >= 28 frames), spanning 0.01-1.00 of the width (a through-column). The "entry half 0.01-0.48" is produced by the centroid split in the probe (`s = (C - C.mean) @ d`), not measured. Entry-side share of frame counts: 0.57 (board 1), 0.54-0.56 (board 2), near chance. Board 2's region spans 0.38-0.57 of its long axis and 0.43-2.58 of its observed thickness extent. The two boards' PCA axes have independent signs, so "opposite edges" across boards is not defined by this probe | [M, dev] same; correction of v1 |
| E3 | 96-100 % of the entered voxels are OBSERVED in the dev depth grids (HULL 1.0; shells 0.96 / 0.98). Board 2's region reaching 2.58 x its thickness extent fits partner contamination of the dev grid; E3 is **not** evidence for GAP | [M, dev] `build/I/review_gapw_rerun.txt`; the clean share is P27c |
| E4 | V2 (a) finds 0 partner samples deeper than b (8.0 / 7.7 mm) in either board's shell or HULL; partner samples inside the HULLs reach only 6.0 mm (board 2) and 8.6 mm (board 1) deep; the B5 pool's V2 medians are 8 and 13 against thresholds 39 and 65 | [M, dev] `build/I/pairs_ep24.json`, `build/I/review_depth.py` (reviewer, not re-run), B5 pool |
| E5 | SAM 3D boards (4 runs): slot centred at 0.50-0.51 of the long axis, from one edge to 0.42-0.48 of the width, slot width 1.2-3.0 % of the length; Pixal3D-MV: shallower notch (0.27 of the width), and its ep23 board 2 copied the partner board | [M, dev, generator outputs of 29 Oct, crops seeded with library_v3: refused in clean mode] `build/I/sam_slot.json`, `build/look/sam_boards.png` |
| E6 | ep2 pot <- lid: HULL entered in 54 frames, travel 20.2 mm, straightness 0.61 (a seat), region 1.6 cm3, all OBSERVED, 6-7 mm deep (a pose push of < 1 cm removes it); shells 0 | [M, dev] `build/I/pairs_ep2.json` |
| E7 | ep11 cups: no partner sample deeper than b = 8 mm in either cup's shell or HULL | [M, dev; dev overstates separation] `build/I/pairs_ep11.json` |
| E8 | Stereo fills the slot; RGB silhouettes see 89 % of slot voxels as free against 1 % of wood | [M with a scan slot box as diagnostic, i.e. D] work log 22 Oct |
| E9 | FlashCHORD's CoACD refills a carved slot (hull overlap 16.9-17.0 cm3) unless the copy is delivered as our convex pieces | [M] work log 22 Oct |
| E10 | Collision-copy slot carve on library_v3 for eval 25: proxy lag 1.17 cm / 103.7 deg -> 0.06 cm / 0.5 deg; FlashCHORD CPU 7.47 cm / 47.9 deg -> 0.12 cm / 0.4 deg; hull overlap 11.8 -> 0.17 cm3 | [M] work log 26 Oct, `meshes/carve/ev25/` |
| E11 | Carving the submitted mesh: XCarve CD-O +0.006 / +0.007, board 2 new flip (ADD +103 mm), 1.3-1.5 cm3 real wood cut under 5-10 mm track bias; planar cut removes 36-47 % real wood; lid min-cut +0.14 to +0.18 | [D] ledger rows 20, 21, lessons |
| E12 | Board 2's S1 pick on the B5 dev pool is the HULL (6.8 cm: the thickness of its oriented bounding box) because V5 removes the flip-risk shell (amb 4.12 mm vs floor 2.34 mm). Of the 4 dev objects with an S1 pick (B5 pools ep11, ep24) it is the only one whose pick relies on a HULL being the non-flip-risk alternative | [M, dev] B5 pool traces, `build/look/ep24_candidates.png` |
| E13 | Collider overlap between objects along our reference drives the largest simulator spreads (evals 30, 14, 1, 10); the 0.219 lid lies 84 % inside the pot's convex hull | [M] keen-heisenberg `arda-feedback-20261031.md` section 7 |
| E14 | A single zero-action replay is chaotic (a 2 mm nudge flips results); judge with jittered means | [M] determined-wright physics README |
| E15 | Persistent region (n >= max(5, ceil(0.25 N)), N 55-57) on the B5 dev candidates: board 1 HULL 16.6 cm3, thinnest PCA extent 8.6 mm, inscribed width 11.3 mm; board 2 HULL 19.0 cm3, 23.8 mm, 16.0 mm; shells 8.9 mm (board 1) and 4.0 mm (board 2). Observed-point extents: board 1 233.9 x 128.2 x 41.8 mm, board 2 233.3 x 122.0 x 18.7 mm. Median camera range 0.514 / 0.504 m; fx 600.2 px at full resolution (about 300 at the half-resolution depth input), so 8 depth pixels are about 13.5 mm at the boards [E] | [M, dev] reviewer's probe, re-run: `build/I/review_gapw.py`, `review_gapw_rerun.txt` |
| E16 | Simulator-copy placement carves (30 Oct, library_v3): carved guests sink or fall. E1 lid: 6 mm free travel, sinks 0.6-1.0 cm below its reference in every carved draw; E14 cup 6 mm; E30 sweeper > 40 mm free travel, drops 2.5-3.5 cm and tilts 48 deg in 2 of 2 draws, loses 35 % of its hull volume (150 -> 98 cm3); guest removal was 4-13 x the claim; the v3 "ends" variant was falsified (P31 sweeper 72.8 deg) | [M] origin/main `docs/research/work/carve-20261030/BUILD.md`, `RETRAIN_PLAN.md` (d) |
| E17 | One settle is chaotic: the same frame re-run gives 1.08/8.1, 0.64/1.3, 1.29/8.1 cm/deg (E1 carved f305); "any later criterion should use at least 3 draws" | [M] RETRAIN_PLAN (b) |
| E18 | Shape budget S_A + S_B <= about 165 per episode at 4096 worlds (note 19 C4); carved E28 208, E14 204, E1 160 | [M, R] RETRAIN_PLAN (c) |
| E19 | `pack_eval.sh` builds one `/content/assets` for all standard-learner episodes and merges pieces "first wins": eval 1's carved pot would replace eval 28's, a rack carve would hit 28 and 30, ev30's sweeper would hit 19 | [R] RETRAIN_PLAN prerequisite 2 |
| E20 | phys_fit v1 ran with "geometry: the public scans" and `props_public_scans.json`; `pipeline/phys_fit.py` takes free `--meshes` / `--props`, loads `{meshes}/{name}.glb` and needs `com_m` and `inertia_kgm2`; v1 was not adopted (frame-0 control) | [R] determined-wright README "Physics fit v1", `pipeline/phys_fit.py` |
| E21 | `props_masses_only.json` masses come from `props_public_scans.json`: a shell model on NVIDIA's scans (density x wall x the scan's surface area), materials from the public videos | [R] its `_note`, `pipeline/object_physics.py` |
| E22 | The gmg venv has neither `mujoco` nor `coacd` (ModuleNotFoundError); `ep24_a.mp4` is in the scratch store; the FlashCHORD venv is not in this container | [M] 31 Oct 09:33 UTC |
| E23 | `make_assets.py` writes collision and visual origins as identity and the inertial origin at the COM, so a URDF link frame is the mesh file frame; MuJoCo re-centres mesh geoms to their inertial frame at compile time | [R] `pipeline/make_assets.py`; MuJoCo mesh compilation |

---

## 2. Scope: which contacts, which features

The stage is generic. It uses only the roster, our tracks, our grids, our images, the reference the simulator
replays, and (optionally) generator meshes. There is no board, lid or cup code. Each ordered pair (target o,
partner p) with contact frames (SPEC section 4) is classified per **engaged run**: a maximal run of contact frames in
which the partner's evidence occupancy (3.3) enters the target's candidate by at least 3 voxels (gaps of up to 2 stride
frames are bridged).

| Kind (per run) | Test | Public examples -> eval |
|---|---|---|
| INSERTION | partner origin path in o's frame over the run: travel >= 20 mm and straightness (largest singular value / sum) >= 0.7 | boards ep24 (118.6 mm, 0.91) -> eval 25; cup lowered into cup ep11 -> eval 10 |
| SEAT / REST | not INSERTION; the pair holds a relative pose (relative speed < 2 mm per frame) for >= 5 frames | lid on pot ep0/ep2 (20 mm, 0.61) -> eval 1; cup or pot in rack ep12/13/26/27 -> eval 14, 28 |
| SLIDE | not INSERTION, not static | sweeper in rack ep31 -> eval 30 |
| TRANSIENT | run shorter than 5 frames | sweeper + dust pan bristles ep18 -> eval 19 |

The spoon pairs (evals 3, 5, 6, 15, 16, 32, 33) were never measured; they run through the same tests.

### 2.1 Two pose sources
- **P_sel** = the gmg tracks of the episode's bundle. Everything that decides the **submitted** mesh uses P_sel:
  sources (a)-(c) for tiers, ICARVE, the features and vetoes of section 5.
- **P_sim** = the poses the simulator will replay for this episode: the reference that the packed policy is trained
  and evaluated against, or, inside the Embodiment loop (section 11), the reference of the current round. Everything
  that builds or judges the **simulator copy** uses P_sim: its regions, its carve positions, the OFFSET shift (4.4) and
  the physical acceptance (6.2). The simulator copy must fit the motion the simulator replays, not a different track.
- P_sim must pass the provenance check of 11.2 (a ground-truth-free perception chain). If no such reference exists,
  or it fails the check, P_sim = P_sel and the copy is flagged `sim_pose_fallback`.
- **eval 25:** P_sim = the reference of the packed eval-25 policy (at pack 3, run `20261025-ev25idfix-02de0c7`, built by
  perception plus `pipeline/identity_fix.py` [R, work log 25 Oct]), subject to the provenance check. Round 0 carves
  from it, so a misplaced round-0 carve cannot use up the cumulative budget.
- **Identity (SPEC section 7, reconciled).** On public episodes IDENTITY_SWAP routes like TRACK_FAIL: source (c) from
  P_sel is absent for that object. On eval the identity test only raises a flag and never changes an eval output, so
  (c) from P_sel stays on and the flag is reported; v1's "disable (c) on IDENTITY_SWAP" applies on public only. A swap
  in P_sel cannot misplace the eval simulator copy, which uses P_sim.

---

## 3. Where a slot, seat or cavity comes from (three sources and their cross-check)

All regions live in the **target's own frame**, on the target's 4 mm grid (the bundle grid), with a 2 mm refinement
inside the region for carving.

### 3.1 Source (a): generator shape placed in our frame
- **Input.** GEN meshes (SAM 3D with our metric pointmap; Pixal3D-MV) from separated, hand-free views only (SPEC
  section 4, mechanism 2), never contact frames (E5: Pixal3D-MV copied the partner board from a contact view).
- **Placement** (section 7): SAM 3D layout mapped by `inv(cam_T_obj[k])`, consensus over views and seeds, then M11.
  Near-symmetric flips are resolved by trusted marker balls (SPEC section 10), then by the depth residual. **The slot
  side is never used to resolve the flip** (v1 used it, which made the (a, c) side agreement circular). If neither
  markers nor the depth residual separates the flip members (margin below 1 sigma), the side of (a) is "unresolved"
  (flag `gen_side_unresolved`).
- **Concavity set C_a.** Voxelise the placed generator solid S_g at 2 mm. Notches: closing(S_g, r) minus S_g with
  r = max(6 mm, partner thickness at the crossing); cavities: convex hull of S_g minus S_g. Only the part within 2
  voxels of the motion region R_c (3.3), or within t_max = 20 mm of it for the OFFSET rule (4.4), is used.
- **What (a) is trusted for:** position along the target's long axis and depth of the feature (how far it reaches),
  and its side when the flip is resolved. **Not** its width: SAM's slot is 1.2-3.0 % of the board length (E5).
- **FUSE must not refill it.** FUSE keeps our shell wherever a voxel is OBSERVED; in the slot those voxels are
  OBSERVED by stereo bridging, so plain FUSE refills it. **FUSE-I** (B15): before the union, the observed shell is cut
  by the component's submitted carve solid (T2, T3 or T2o, 3.4); the generated emptiness is kept there. Plain FUSE
  stays in the pool.
- **Remesh check.** M10 (`remesh.watertight` + `fit_budget(4000)`) can close a 3-7 mm slot. For any GEN mesh with a
  concavity near R_c, at least 80 % of that concavity's volume must survive remesh and budget; otherwise (a) counts as
  absent (flag `gen_slot_lost_in_remesh`).

### 3.2 Source (b): RGB silhouette (sees what stereo bridges)
- **Frames:** good frames in which the target is 2-D separated from every partner (SPEC section 4), hands cover at most
  25 % of its mask and no hand pixel lies within 16 px of the projected region.
- **Per-pixel classifier, full resolution** (not SAM2's low-resolution masks, which would close a 10-pixel slot).
  Per object and episode: positives = pixels of projected OBSERVED target voxels at least 3 px from the projected
  outline; negatives = pixels whose depth lies more than 20 mm behind the target's projected surface. Features: Lab
  colour and a 5x5 local texture. Model: a two-class Gaussian mixture (3 components per class), fitted on that
  episode's own pixels.
- **Votes per voxel:** for each qualifying frame in which the voxel projects inside the image and is not occluded by
  the partner or a hand, NMV += 1; if its pixel is classified background with probability > 0.5, NMF += 1. A voxel is
  **see-through (SIL)** if NMF >= 3 and NMF >= 0.5 NMV.
- **Contrast gate (GT-free).** Used for an object only if (i) held-out pixel accuracy on a 20 % split is >= 0.9 and
  (ii) the false see-through share on strongly OBSERVED interior voxels (hits >= 10, >= 2 voxels from the outline) is
  <= 2 %. Otherwise (b) is "absent", not "disagrees". Whether the boards pass is measured first in BI2 (T-I2a; the ep24
  video is available [M]); v1's "white objects are expected to fail [H]" is kept only as a hypothesis for the cups.
- **Notch set N_b** = SIL components inside the target's candidate occupancy; **R_b** = the part of N_b within 2 voxels
  of R_c (or of C_a if R_c is empty).

### 3.3 Source (c): motion-required empty space (swept partner, robust to jitter)
- **Partner evidence occupancy.** The partner's OBSERVED and shared voxel centres (one sample per voxel, as V2's P_p,
  plus 2 mm sub-samples so that a 10 mm plate is 5 samples thick), **minus the partner's own carved region** (decided
  jointly with the target's, 4.3). For the Embodiment export the partner samples come from the partner's delivered
  pieces instead (11.2), which already exclude every accepted carve.
- **Build and check frames.** Each engaged run is cut into consecutive 10-frame blocks; even blocks are **build**
  frames, odd blocks are **check** frames. Regions and decisions use build frames only; check frames are held out for
  acceptance (6.2 P7, 11.5). Runs shorter than 20 frames use all frames for building and have no held-out check (flag
  `no_holdout`); the physical tests still apply.
- **Entered count.** In each build frame f, the samples are moved into o's frame through the two tracks
  (T_{o<-p}[f], from P_sel or P_sim per 2.1). Voxel v of o is *entered* in f if a sample lands in v and v lies inside
  the candidate. n_v = number of build frames in which v is entered.
- **Persistent:** n_v >= max(5, ceil(0.25 N_build)). Five frames is the Embodiment session's minimum; 25 % a quartile.
- **Swept:** the partner-local positions of the samples that entered v (mapped back by inv(T_{o<-p}[f])) span at least
  s_min = max(8 mm, 3 j) at their 90th-percentile extent (j = pair jitter, PREREG A.2). A partner resting with a pose
  error enters v with the same few partner points; a partner sliding in enters v with a moving part of itself.
- **Insertion direction and entry side.** d = the principal direction of the partner origin path in o's frame over the
  run, signed by the partner's mean velocity (from where it comes to where it goes). The entry side of o is the side
  the partner comes from. Taking the entry half is a **physical requirement** (the replayed partner can only get in if
  o is open toward where it comes from), not evidence; the two half-slots of a cross-lap end up on opposite edges by
  construction.
- **Insertion split, only for a true through-column.** A persistent component is split only if, along d, it exits the
  target at **both** ends: the voxels within 1 voxel beyond each end of the component along d are outside the
  candidate or FREE. (This happens when the partner's own slot is bridged in its evidence. A cup cavity that the outer
  cup's candidate fills from rim to floor ends at the floor, so it is not split.) The split plane is normal to d,
  through the component's centroid, or through the end of C_a when (a) agrees; o keeps the far side and loses the entry
  side. **One plane per linked pair** (4.3), computed once in o's frame at the median assembled relative pose and mapped
  into p's frame, so the two half-notches meet (the 26 Oct lesson: separate planes left a 1.3 cm uncut band).
- **Track health.** On public, (c) is absent if either object is TRACK_FAIL or IDENTITY_SWAP (PREREG B.15) or good in
  < 80 % of the run's frames; on eval, IDENTITY_SWAP is a flag only (2.1). For P_sim the same M3 per-frame residual test
  is applied with the P_sim poses (owned points against the pick).
- **Region R_c** = the persistent, swept voxels (after the split), 26-connected components, each handled separately.

### 3.4 Cross-check (d): agreement decides confidence and destination
Per component R of R_c (or of C_a or N_b when no motion exists):

| Pair of sources | Agree if |
|---|---|
| (a, c) | centroid distance <= 10 mm; angle between the two principal axes taken as unsigned lines (angle = arccos of the absolute dot product) <= 15 deg; >= 50 % of R inside C_a dilated by 1 voxel; C_a open toward the entry side, tested only when (a)'s side is resolved (3.1), else skipped and recorded |
| (b, c) | >= 50 % of R's silhouette-testable voxels (NMV >= 3) are SIL |
| (a, b) | >= 50 % of R_b (or of N_b) inside C_a dilated by 1 voxel |

10 mm and 15 deg reuse PREREG K-c; 50 % is a majority. A source is **absent** if it was not run, failed its own gate
(3.2 contrast gate, 3.1 remesh check, 3.3 track health) or covers too little (fewer than 3 testable voxels); it
**disagrees** if present and its agreement test with another present source fails.

**Rules.**
- **Any present source that disagrees blocks submitted candidates** for that component, whatever the other two say.
- A component that decide() (section 4) pushes or ignores never yields submitted candidates, except through the
  OFFSET rule (4.4), whose submitted candidate is built at the observed notch N, not at R. At T2o the position of (c)
  is excluded from the agreement tests (its offset is why OFFSET applies); (a) and (b) must both be present and agree
  on N, and neither may disagree.

| Tier | Sources | Simulator copy | Submitted mesh |
|---|---|---|---|
| **T3** | (a), (b), (c) present, all three pairs agree | carve if decide_pair says CARVE | ICARVE and FUSE-I candidates enter S1 |
| **T2** | exactly two present and agreeing, the third absent: (a, c), (b, c), or (a, b) | carve if (c) is one of the two and decide_pair says CARVE | ICARVE and FUSE-I candidates |
| **T2o** | OFFSET (4.4): (a) and (b) present and agreeing on the notch N, R pushed by class O | carve N + t (4.4) | ICARVE and FUSE-I at N |
| **T1** | (c) present, decide_pair says CARVE; (a), (b) absent or disagreeing | carve | no (flag `interlock_disagree` if a source disagrees) |
| **T0** | anything else | no | no |

The accepted region **R*** of a target is the union of its simulator carves (sim copy), and of its T2, T3 and T2o
carve solids (submitted candidates and the E exclusion of section 8). A testable silhouette that does **not** see
through a region is not "absent": its voxels are class O in section 4.

### 3.5 Widths across the feature
Let n be the across direction of a component (its thinnest principal axis, perpendicular to d).
- **Simulator width** w_sim = max(1-99 % extent along n of the partner samples that entered R at the assembled build
  frames, **the partner's simulator collider thickness at the crossing**) + 2 x 1 mm clearance. The partner's collider
  is its delivered pieces of the same round (round 0: the pieces of its pick); its thickness at the crossing is the
  1-99 % extent along n of its pieces' volume samples inside the target's candidate dilated by 2 voxels, at the median
  assembled relative pose. A HULL or thick GEN partner therefore gets a wide slot or none: if w_sim makes the carve
  exceed the budget of 4 (iv), the linked pair is pushed with flag `interlock_partner_too_thick`.
- **Submitted width** w_sub = the partner's measured two-sided thickness at the crossing from its own evidence (else its
  pick's thickness there), capped at w_sim. The real slot must be at least as wide as the partner; nothing supports
  more.
- **Position and end:** from (a) when it agrees, else from the split plane of (c); under OFFSET from N.

---

## 4. The carve rule (one implementation, used by the gmg and by the Embodiment session)

`gmg/interlock.py: decide_pair(pair, components, evidence) -> per component CARVE | PUSH | OFFSET | IGNORE`, applied to
the persistent components of both targets of a pair, whether the intrusions came from our tracks (3.3) or from the
Embodiment's export (section 11). The same region builder (3.3: build frames, persistence, sweep, through-column test,
shared split plane) runs on both inputs.

### 4.1 Voxel classes (from the target's bundle grids and source (b))
- **U** = FREE or UNKNOWN in the depth state grid (the cameras saw it empty, or never saw it);
- **SIL** = OBSERVED in depth but see-through in the silhouette (3.2): stereo bridging;
- **GAP** = OBSERVED, the silhouette is absent for it (gate failed or NMV < 3; a testable silhouette that says solid
  makes the voxel O), the component is **too narrow in the image for stereo to resolve**, and removing it keeps the
  target's topology (a notch, not a hole or a split). Image width: in every view k in which at least 3 of the
  component's voxels have depth hits (stereo saw the place and bridged it), project the component's 2 mm sub-samples
  into the depth image at the depth input's resolution, rasterise, and take 2 x the largest inscribed radius of the
  projected mask (distance transform), in pixels; the median over those views must be <= w_bridge = 8 depth pixels (two
  cells of a quarter-resolution stereo cost volume on the half-resolution depth input [H]; about 13.5 mm at the boards'
  0.50-0.51 m with fx about 300 at half resolution [E]; v1's "15 mm at 0.55 m" is corrected). v1 used the component's
  thinnest 3-D axis instead, which equals min(target thickness, partner thickness), so every thin-walled target passed
  (shells 4-9 mm, rack fins, cup walls, the lid); the image width tests stereo resolvability, not object thickness;
- **O** = every other OBSERVED voxel: surface our cameras saw as solid.

### 4.2 Decision for one component R (R_U = R in U, R_O = R in SIL, GAP or O)
1. **IGNORE** if the run is TRANSIENT (< 5 frames) or R has fewer than 3 voxels.
2. **PUSH** all of R if more than 25 % of R is class O (the cameras saw solid surface where the partner is placed:
   the pose is wrong, not the shape). Nothing of R is carved; the OFFSET rule (4.4) is then tried.
3. **R_U -> CARVE** (SPEC section 4 mechanism 4 with persistence) unless the topology guard fails: the carved solid
   must keep its number of components and its genus. A cup floor that the partner sinks through would open a hole:
   PUSH.
4. **R_O** is carved only if all of these hold:
   - (i) **swept**: at least 50 % of R_O's voxels pass the swept test, and the run is INSERTION or SLIDE;
   - (ii) **not pushable**: over the build frames in which R is entered, the median of the smallest pose correction
     that removes the intrusion exceeds the physics prior (10 mm, 3 deg). Our proxy: the smallest rigid translation of
     the partner, over 26 directions plus R's normal, that leaves fewer than 3 entered voxels. With the Embodiment's
     export: `pushed_residual_m` > b in at least half of those frames, **only if validate() accepted the fit's
     provenance** (11.2); otherwise the proxy decides;
   - (iii) **evidence class**: at least 75 % of R_O is SIL or GAP. Only SIL and GAP voxels are carved; class O voxels
     are never carved by this step, and they are listed in the report;
   - (iv) **budget**, measured **after** the split and with w_sim: the voxels carved for this target over all
     components and rounds add up to at most 10 % of its candidate's solid volume; R reaches at most 0.6 of the
     target's extent along d; the topology guard holds.
   If all hold: CARVE (the SIL and GAP voxels of R_O, at width w_sim) in the simulator copy, subject to 6.2. Otherwise
   PUSH R_O (if (ii) failed, a pose correction removes it; if (i), (iii) or (iv) failed and it is not pushable either,
   flag `interlock_unresolved`, handed to the Embodiment loop and the tracker).
5. Every decision is written with its reasons and numbers (frames, sweep, push distance, class mix, image width,
   budget, tier, OFFSET shift).

### 4.3 Pair-level decision (a cross-lap needs both half-slots)
- Two components R_o (in o) and R_p (in p) are **linked** if each lies, by at least 50 % of its voxels, inside the
  crossing volume X = o's candidate intersected with p's candidate at the median assembled relative pose (dilated by 1
  voxel), mapped into each object's frame.
- Linked components are decided **together**: both CARVE only if each passes 4.2 on its own side, with the pair's
  shared split plane and both widths of 3.5; otherwise **both PUSH** (each side's reasons recorded; flag
  `interlock_pair_fail`). No half-interlock is ever delivered. OFFSET (4.4) is applied to a linked pair jointly, with
  one relative-pose offset mapped into both frames.
- Unlinked components (one-sided features: cup in cup, cup or pot in rack, sweeper in dust pan, lid seat) are decided
  per target.
- [M, dev; reviewer's probe, re-run] With v1's rule the ep24 pair would have been split: board 2's region inside its
  HULL is 23.8 mm on its thinnest axis (GAP fails, class O, PUSH) while board 1's is 8.6 mm (carved): a half carve. The
  v2 decision on ep24 is not claimed here; T-I2b measures it.

### 4.4 OFFSET: an observed notch next to the motion region (track bias of about one slot width)
Applies to a component R (or linked pair) that step 2 pushes, when an observed notch N exists on the same target: a SIL
component of N_b (3.2), or a placed generator notch of C_a that survived remesh, within t_max = 20 mm of R.
- **Shift.** t = the translation on a 2 mm grid with |t| <= t_max and |t . d| <= 0.5 |t| (mostly lateral to the
  insertion direction) that maximises the overlap of N + t with R; OFFSET holds only if at least 50 % of R lies inside
  N + t dilated by 1 voxel and N passes the topology test. A shift along d means the partner went too deep or not deep
  enough: a pose error the fit or the tracker must fix, never OFFSET. This keeps the ep11 case ("our reference nests
  the cup deeper than the shapes allow") a PUSH.
- **Simulator copy** (poses P_sim): carve N + t, widened to w_sim, under the budget of 4.2 (iv) and the physical
  acceptance of 6.2. The removed shape is the gap the cameras saw (N), placed where the replayed partner passes. Class-O
  voxels inside N + t are listed as `o_displaced`. This is the only case in which a simulator copy removes voxels the
  depth grid holds as seen solid.
- **Tracker hand-off:** t and the frames, as a correction hypothesis ("partner offset t in the target frame over frames
  F"), in `push_list.json`.
- **Submitted candidates:** ICARVE at N (never at N + t), only at tier T2o: (a) and (b) both present and agreeing on N,
  and the run is INSERTION or SEAT. The position of (c) counts neither for nor against: its offset is the reason OFFSET
  exists.
- When the tracker or the Embodiment fit removes the offset (a new P_sim), the copy is rebuilt from the new poses: R
  moves onto N and OFFSET no longer applies.

Why this rule (the v1 deadlock): with the dev track off by 10.5-12.9 mm, a testable silhouette would see wood under
most of R (class O, PUSH) and see the slot at N, where the replayed partner never goes; v1 carved neither, so a better
silhouette made the simulator copy worse.

### 4.5 Worked cases [expected, H]
- **Board slot (ep24, eval 25):** INSERTION, swept, push distance about the slot length (6 cm) -> not pushable;
  voxels OBSERVED -> SIL if the silhouette passes its gate and sees through, else GAP if the image width is <= 8 px,
  else O. Linked pair. Possible outcomes: CARVE both (T1-T3); OFFSET (T2o if SAM 3D and the silhouette agree on N); or
  PUSH both. Which one happens on ep24 is measured in T-I2b.
- **Lid on pot rim (ep2, eval 1):** SEAT; the rim region is OBSERVED, 6-7 mm deep, pushable (E6) -> PUSH; the lid's
  unseen underside where the rim sits is U -> CARVE, subject to the free-travel test (the E1 lid sank with 6 mm of
  free travel, E16).
- **Cup in cup (ep11, eval 10):** INSERTION into a U cavity -> CARVE in the simulator copy (CoACD would fill it); an
  inner cup below the outer cup's seen floor enters class O -> PUSH (topology guard too); a shift along d is never
  OFFSET.
- **Two objects resting with a pose error:** not swept -> R_O PUSH; R_U carve only where the partner persistently sat
  in unseen space, and only if the settle and free-travel tests pass.
- **Wandering jitter:** never persistent at one place -> IGNORE.

---

## 5. Physics along our track, for every candidate (the placement and physics checks)

New module `gmg/physcheck.py`; features appended to each candidate's line in `RUN/feat/.../<obj>.jsonl` under key
`phys`. Everything uses P_sel, our grids and our table plane. Cost per candidate: seconds (an SDF grid at 2 mm, then
trilinear look-ups) [E].

### 5.1 Per-frame placement consistency with our depth (whole movement)
- For each good frame f: trimmed point-to-plane Gauss-Newton alignment (to convergence, at most 5 steps) of frame f's
  owned points to the candidate, giving a 6-DoF offset delta_f. Directions the frame cannot constrain (eigenvalue of
  the 6x6 information matrix below 1 % of the largest) are excluded per frame.
- **Constant part** delta_bar = robust median over good frames; **drift** = median absolute deviation around it, and
  the largest 10-frame block mean deviation (catches steps such as the ep11 outer cup lift).
- **Meaning.** A constant offset says the candidate sits off our observed surface (CPU candidates: about 0; GEN and
  FUSE: the placement error); the kit registers our mesh to the scan once, so it becomes a pose error of about its
  size in every frame [E]. A drift is a per-frame track error: no mesh can fix it; it goes to the tracker (section 12).
- **Flags:** `placement_offset` if |delta_bar_t| > max(3 sigma, 2 mm) or |delta_bar_r| > 2 deg; `placement_drift` if
  the drift MAD > 3 sigma or a block deviation > max(3 sigma, 5 mm). **Veto VP** (GEN, FUSE, FUSE-I only): on held-out
  frames |delta_bar_t| > 10 mm or |delta_bar_r| > 15 deg (the K-c tolerances); CPU candidates are never vetoed by it.

### 5.2 Interpenetration with each partner, per phase (volume, not depth)
- Phases per pair: **apart**, **contact** (outside engaged runs), **engaged**, with **assembled** = the last static
  stretch (relative speed < 2 mm per frame, >= 5 frames) of an INSERTION or SEAT run.
- I_f(c, p) = volume of the partner evidence occupancy (3.3) inside candidate c in frame f. Reported per phase:
  median, 90th percentile, max (cm3).
- **Veto VI (interlock), relative to the best candidate:** with I(c) = median of I_f over the assembled frames, c is
  vetoed if I(c) - min over the object's feasible candidates of I(c') > 1.0 cm3. The best candidate always passes, so
  the veto cannot remove the whole pool, and the quantisation floor cancels: an ICARVE candidate keeps a residual of
  about (2-6 mm) x 60 mm x 10 mm = 1.2-3.6 cm3 [E] (the submitted slot is the partner's width, measured against 4 mm
  evidence voxels with 2 mm sub-samples), which v1's absolute 1.0 cm3 would have vetoed. A slot-less board overlaps by
  about the whole crossing (the dev persistent crossing regions are 6.5-19.0 cm3 [M, E15]; indicative, not I itself)
  and is vetoed whenever an ICARVE exists. V2 stays as it is.
- For the simulator copy the same measure is computed on the convex pieces (**collider overlap** per phase,
  keen-heisenberg's suggestion, E13); reported, and part of 6.2.

### 5.3 Table penetration along the whole track
Per good frame: share of 20,000 volume samples more than max(3 sigma, 2 mm) below the table plane. **Veto V4t:**
share > 1 % in at least 25 % of good frames, applied only if at least one feasible candidate passes it (otherwise the
flag `track_below_table` goes to the tracker). Never a carve (the 22 Oct per-frame `below_carve` erased real wood).

### 5.4 Rest consistency at static segments
Static segment: object speed < 2 mm per frame for >= 15 frames, no hand keypoint within 30 mm. On the table: lowest
point within max(3 sigma, 2 mm) of the table, stable pose (`trimesh.poses.compute_stable_poses`) within 10 deg of the
observed up, centre of mass inside the support polygon. On a partner: the lowest contact region within b of the
partner occupancy and no penetration deeper than b. Flags only (`rest_mismatch`).

### 5.5 Hands (report only)
Hand keypoints inside the candidate during holds are reported (`hand_inside_mm3`). Never a veto or a carve.

---

## 6. Simulator copy and its physical acceptance

### 6.1 Convex pieces CoACD cannot refill (port to our meshes)
New module `gmg/simpieces.py`, a port of `pipeline/collision_decomp.py` (free-space-guided split) and of
`pipeline/interaction_carve.py region_cut` (planar half-cuts), using `gmg.geom`, applied to **our pick**, never to
library meshes.
1. Solid of the pick (full resolution before the 4096-face budget) at 1.5-2 mm; subtract the simulator carves (4.2,
   4.4) at width w_sim; topology guard.
2. Keep-out set = carved voxels + FREE voxels + SIL voxels + the partner's swept persistent occupancy (from P_sim),
   within 2 voxels of the surface.
3. Pieces: convex hulls split by the plane that minimises keep-out volume inside the children; planar slots use the
   exact half-cut; stop when every hull holds <= 0.3 cm3 of keep-out volume, cap 32 pieces (64 if the solid is above
   300 cm3), and the episode cap of 6.2 P5; each hull reduced to <= 64 vertices.
4. **Delivery layout** per episode and round, never overwritten: `RUN/sim/<split>/ep<N>/r<k>/`
   - `<obj>/<obj>.glb` (visual = the submitted mesh, colourless copy for Newton), `<obj>/piece_XX.obj` (the collision
     pieces; vertices in the same file coordinates as the GLB), `<obj>/inertia.json` (COM and inertia of the uniform
     solid of the pieces, which `make_assets.py --pieces` already reads), `<obj>/carve.json` (decisions, sources,
     widths, OFFSET shifts, physical results);
   - `_fit/<obj>.glb`: the union of the object's pieces as one watertight mesh in the same file coordinates, so
     `phys_fit.py --meshes r<k>/_fit` loads the collision geometry unchanged (it reads `{meshes}/{name}.glb`, E20);
   - `props_gmg.json`: per object `mass_kg` (the 0.3 kg placeholder unless the owner approves another mass table,
     D-I1), `com_m` and `inertia_kgm2` from the pieces (as `inertia.json`), `provenance` (inputs and sha256);
   - `manifest.json`: episode, split, round, P_sim (path, sha256, provenance), per object the sha256 of every delivered
     file, 8 fiducial points per object in file coordinates (the corners of the oriented box of the pieces' union,
     moved 1 mm inward), the gmg commit.
- **Masses.** v1 named `props_masses_only.json`. Its masses come from the public scans' surface areas (E21), so it is
  scan-derived for every object that has a scan. It is not used by this stage until the owner decides (D-I1); the
  placeholder is used on public and eval alike, so both run the same path.

### 6.2 Physical acceptance: for every carved pair, every kind and every voxel class
Run on the carved pieces and on the uncarved free-space pieces (the default) of the same pick, at poses P_sim.
Simulated statistics are means over **16 jittered copies** (0.5 mm / 0.005 rad, common random numbers;
`tools/physics_solve/jitter_check.py` settings), never single draws (E14, E17).
- **Frames.** INSERTION and SEAT: the median frame of the assembled stretch. SEAT, REST and SLIDE runs and every R_U
  carve: the middle frame of each static contact segment of the pair (at most 3, longest first). Frame 0 if the pair is
  in contact there.
- **P1 settle:** 2 s hands-free settle under gravity, hands parked, no drive (the `settle_at.py` recipe of
  carve-20261030, in the FlashCHORD scene; a plain-MuJoCo pre-check may run first but does not decide). Pass: guest
  and host mean drift <= 1 cm and mean tilt <= 5 deg at 2 s; mean relative sink (guest displacement relative to the
  host along gravity) <= 4 mm; no NaN in any copy; no copy in which the guest ends on the table or below the host's
  lowest point when P_sim has it on the host (fall-through).
- **P2 free travel (Monte Carlo, geometry only):** at each P1 frame the carved guest pieces are translated in 0.5 mm
  steps along gravity (in the host frame), along +d (deeper insertion) and along +n and -n (across the feature), until
  the Monte Carlo overlap with the host pieces (200,000 points in the guest's box) exceeds 0.05 cm3. Pass: travel <=
  max(4 mm, the default's travel + 1 mm) in each of these directions; 26 directions are reported. 4 mm = 2 x the 1 mm
  clearance + one 2 mm carve voxel. It catches the measured failures: E1 lid 6 mm (sank 0.6-1.0 cm), E14 cup 6 mm, E30
  sweeper > 40 mm (fell through) (E16).
- **P3 replay proxy** (INSERTION runs only; 6.3): the partner follows the replayed path through the carved pieces.
  Kinematic: it cannot detect sinking or falling, which is why P1 and P2 exist.
- **P4 over-removal:** per object, the removed collider volume (default pieces minus carved pieces, Monte Carlo) <= 1.5
  x the carved region's volume at width w_sim, and each object keeps >= 90 % of its default collider volume (E30's
  sweeper lost 35 %; guest removal was 4-13 x the claim, E16).
- **P5 shape budget:** total collision shapes of the episode (all objects' pieces) <= 165 (E18). Over the cap, adjacent
  hulls are merged, smallest keep-out increase first; if the cap cannot be met with every hull <= 0.3 cm3 of keep-out,
  the pair with the smallest P1 gain over its default gets its default pieces.
- **P6 no new overlap:** at every checked frame (stride 4 over P_sim plus all rest frames), carved overlap <= default
  overlap + 0.1 cm3 (carve-20261030 criterion 3).
- **P7 held-out intrusion** (when the run has check frames): on the check frames, the collider overlap of the carved
  pieces at engaged frames is at most half the default's. Carving removes the build frames' intrusions by
  construction; the check frames test whether the carve generalises to frames it was not built from.
- **Delivery:** carved pieces only if P1, P2, P4, P5, P6, P7 and (INSERTION) P3 pass. Otherwise the default pieces,
  and the pair goes on the hand-off list (`interlock_physics_fail`, with the failing test). v1's "deliver if it halves
  the lag" clause is removed.

### 6.3 Replay proxy (the v1 "interlock test")
The `interaction_carve.py` MuJoCo proxy, driven by P_sim's relative path: target fixed, partner welded to a mocap
target (a MuJoCo kinematic body, not motion capture) following T_{o<-p}[f] from 40 frames before the first engaged frame
to the end; default pieces vs carved pieces vs contact off; 16 jittered copies. Pass: at the assembled frames, carved
median lag <= 0.5 cm and <= 5 deg, collider overlap < 1.0 cm3, and the lag never exceeds 1.0 cm after the first
assembled frame. "Slot not limiting" if the default's lag < 1 cm and < 10 deg (then the carve is delivered only if all
other tests pass, flagged). These are the 26 Oct pre-registered thresholds. Confirmation in FlashCHORD's own physics
(`tools/carve_fc_test.py`) is public dev only.

### 6.4 One asset folder per episode
Carves are per episode and round (6.1 layout); `carve.json` and `manifest.json` name the episode, and
`interlock.load_sim(dir, episode)` refuses a folder whose manifest names another episode. The pack must build each
episode's assets in its own root (for example `/content/assets_ep<N>`, `make_assets.py --pieces`) and rewrite only that
episode's reference `object_urdf_paths` (RETRAIN_PLAN prerequisite 2; the pack code is owned by the pack session and
not yet written). CPU test before any launch: every packed episode's URDF collision counts equal its manifest, and
episodes without a carve show the default counts (E19).

---

## 7. Generator placement: layout consensus across frames, and what G0/G1 must record

- **Per view and seed** (k, s): SAM 3D layout (R, t, scale) in camera k, mapped to o's frame by `inv(cam_T_obj[k])`.
- **Consensus:** rotations by a chordal L1 mean (Weiszfeld on SO(3)) after aligning each to the consensus modulo the
  generated mesh's own flip set; translation by the geometric median; scale by the median. Views more than 15 deg or
  10 mm from the consensus are outliers (flag). The flip member is chosen by trusted markers, then by the depth
  residual; never by the slot side (3.1).
- **Whole-movement check:** the consensus-placed mesh goes through 5.1 on all good frames, not only the view frames.
- **Ties to PREREG.** K-c and K-d stay as they are; the consensus and 5.1 are reported next to them (K-c', report
  only). G0 (layout-only placement of the ep2 lid and pot) also reports 5.1 over all good ep2 frames.
- **G0, G1, G2, G4 must additionally record** per run: view frame k, `cam_T_obj[k]`, the mask PNG and its sha256, the
  pointmap sha256, the seed, the raw generated mesh (before remesh), the layout in camera and object frame, runtime.
- **Boards added (G1 and G2):** ep24 board 1 and board 2 on M9's separated, hand-free, face-on views (before the
  insertion, about f < 160 [M, dev]), 1 view x 4 seeds or up to 4 views x 2 seeds. ep23 boards only if they pass the
  identity tests. G4 (eval) uses the same rule on eval 25. Cost +$0.3-0.6 per batch [E].
- **K-f (report only):** in at least half of the board runs, the placed GEN mesh has a notch of length >= 0.3 of the
  board width from one edge that survives remesh [H].

---

## 8. How it enters selection (summary; exact text in PREREG F-I1)

- **SPEC section 14 override, named (F-I1.0).** SPEC section 14 says interaction carving goes "only in this copy, never
  in the packed mesh (carving the packed mesh hurt: lid +0.14 to +0.18 [D])". F-I1.4 overrides that sentence for two
  candidate types, ICARVE and FUSE-I, and for nothing else. Why the amendment is allowed: SPEC is frozen design text
  and PREREG section F records amendments made before any scoring round (none has run; zero gmg scan scorings exist);
  the override is declared in F-I1.0 instead of editing SPEC. Why it is justified: the October harm came from carving
  the packed mesh unconditionally from one source (the lid min-cut; XCarve on the boards from motion alone); here a
  carve enters only as one more candidate, needs two agreeing sources with none disagreeing, competes in the frozen S1
  selection, and is reverted globally at R1 unless it helps.
- **New candidates.** ICARVE(c): for every feasible candidate c of class STRUCT, FUSE, GEN or SHELL (never HULL), c
  minus the submitted carve solid (width w_sub) of its T2, T3 and T2o components, by a manifold boolean; class of c;
  flag `interlock_carved`. FUSE-I (3.1) when GEN meshes exist. A slotted plate from P-PROG's slab body (B11) is ICARVE
  of the slab.
- **Evidence score E:** held-out points whose voxel lies in the target's T2/T3/T2o carve solids are dropped for every
  candidate of that object (paired). Count reported.
- **Vetoes:** VI (5.2, relative to the best candidate), V4t (5.3), VP (5.1, GEN, FUSE and FUSE-I), VF (below).
- **Flip units.** In PREREG A.5 step 3.2, ICARVE(c) and FUSE-I are ranked with their **base's** flip units: a notch adds
  asymmetry by itself, and that must not buy a carve its win over the slot-less base.
- **VF, stated plainly:** ICARVE and FUSE-I are vetoed if their observed flip margin is smaller than the base's by more
  than 1 sigma. A notch usually adds ambiguity measures rather than removing them, so VF will rarely fire. **The guard
  against a repeat of October's board-2 flip is the R1 scan revert below,** not VF.
- **V5 clarification:** a HULL candidate does not count as the "feasible candidate that is not flip-risk" that lets V5
  apply (SPEC section 8: HULL is fallback only). Affected dev objects [M]: of the 4 dev objects with an S1 pick (B5 pools
  ep11 and ep24) only `wooden_piece_2` (HULL -> its flip-risk shell); the beige and blue cups are kit-symmetric (V5 not
  applied) and board 1's pool has no non-flip-risk candidate. Every pick the clarification changes is flagged
  `v5_hull_clarified` and its pre-clarification pick is scored at R1 (below), because no interlock test guards an
  object without ICARVE.
- **Flags:** `interlock_tier`, `interlock_unresolved`, `interlock_push`, `interlock_pair_fail`,
  `interlock_partner_too_thick`, `interlock_physics_fail`, `o_displaced`, `gen_side_unresolved`, `sim_pose_fallback`,
  `placement_offset`, `placement_drift`, `rest_mismatch`, `gen_slot_lost_in_remesh`, `v5_hull_clarified`, `no_holdout`,
  `fit_provenance_refused`.
- **R1 and adoption (global, not per object).** For every R1 anchor whose pick is ICARVE or FUSE-I, its base candidate
  is scored too, and for every anchor flagged `v5_hull_clarified`, its pre-clarification pick (R1 at most +10 in total,
  R2 at most +20; expected 2-4, the boards). Two global method choices, each applied once before D.1:
  - submitted carves are adopted only if, over all ICARVE / FUSE-I anchors, mean CD-O(pick) - CD-O(base) <= 0 and no
    pick flips more than its base; otherwise every ICARVE and FUSE-I pick reverts to its base (the simulator copy keeps
    its carve);
  - the V5 clarification is kept only if, over the `v5_hull_clarified` anchors, mean CD-O(new pick) - CD-O(old pick)
    <= 0 and no new pick flips more than its old pick; otherwise those picks revert.
  The tolerance is 0. v1's +0.005 cm was set from XCarve's scan results (+0.006 / +0.007) to make XCarve fail: a
  scan-derived constant, withdrawn. With 2-4 objects the mean is noisy; the per-object differences and their 30-seed
  spread are reported next to the decision.

### 8.1 The ep24 board-2 HULL pick, step by step [H, checked by T-I4]
Today (B5 dev pool): shell (flip-risk) and HULL; V5 removes the shell, so the HULL wins (E12). With F-I1:
1. the V5 clarification keeps the shell (flag `v5_hull_clarified`; the HULL is also scored at R1);
2. decide_pair runs on board 1 and board 2 together (4.3); its outcome on ep24 is measured in T-I2b, not assumed;
3. if a T2, T3 or T2o component exists, ICARVE(shell) is built;
4. VI vetoes the slot-less shell and HULL when ICARVE(shell) overlaps the partner by at least 1 cm3 less;
5. the pick is ICARVE(shell), a slotted STRUCT plate or FUSE-I when B11 or G2 have run, or otherwise the shell (flagged
   `flip_risk` unless trusted markers break the remaining face flip). The HULL is not picked while the shell is
   feasible. If both boards are pushed, the simulator copies are uncarved and the case goes to the tracker.

---

## 9. Per pair

| Pair (public -> eval) | Expected decisions [H] | Simulator (P_sim) | Submitted |
|---|---|---|---|
| boards ep24 -> eval 25 | INSERTION; linked pair; CARVE both, OFFSET, or PUSH both (T-I2b); eval 25 carves from the packed policy's reference | carved pieces only after 6.2 | ICARVE / FUSE-I at T2, T3 or T2o |
| boards ep23 | identity swap expected on public (B.15) -> no (c) from P_sel | uncarved unless P_sim gives (c) | no |
| lid + pot ep0/ep2 -> eval 1 | SEAT; rim region PUSH; lid underside U carved only if P2 holds (E1 sank with 6 mm travel); pot opening kept FREE in the pieces | pieces after 6.2 | no change |
| cups ep11 -> eval 10 | INSERTION into a U cavity -> CARVE; inner cup below the seen floor -> PUSH, never OFFSET | pieces with an open cavity after 6.2 | no change |
| cup / pot in rack ep12/13/26/27 -> eval 14, 28 | holder cavities U -> CARVE; rack fins O -> PUSH; P5 shape cap (E28 reached 208) | pieces after 6.2 | no change |
| sweeper in rack ep31 -> eval 30 | SLIDE; carve only U or SIL with sweep; **negative control** (T-I10): the earlier carve let the sweeper fall through | pieces only if P1/P2 hold, else default | no change |
| sweeper + dust pan ep18 -> eval 19 | TRANSIENT (7 of 177 frames) -> IGNORE | default pieces | no change |
| spoon pairs (7 evals) | measured at run time; spoon into U cavities -> CARVE | pieces after 6.2 | no change |

---

## 10. What failed before and how this design avoids it

| Earlier result | How this design avoids it |
|---|---|
| XCarve on the submitted board mesh: CD-O +0.006/+0.007, board 2 new flip ADD +103 mm; 1.3-1.5 cm3 real wood cut under track bias [D] | submitted carves only as candidates at T2/T3/T2o with no disagreeing source; width = the partner's thickness; flip units inherited from the base; the global R1 revert with tolerance 0 is the guard (VF rarely fires) |
| the planar cut removed 36-47 % real wood (track bias about one slot width) [D] | motion-only regions go to the simulator copy only; OFFSET puts the observed notch, not the motion band, into submitted candidates |
| CoACD refills slots and cavities (16.9-17.0 cm3) [M] | convex pieces of our own (6.1) through `make_assets.py --pieces` |
| two separate cut planes left a 1.3 cm uncut band [M] | one shared plane per linked pair (3.3, 4.3) |
| min-cut made the lid worse (+0.14 to +0.18) [D] | no repartition of the interface; seats are PUSH or U-carves |
| per-frame below-table carving erased real wood [D] | the table is a veto (V4t), never a carve |
| hand carving removed as much real material as excess [M] | hands are reported only |
| the old carve ran on library_v3 | inputs are gmg candidates and our own evidence only; the guard refuses library files |
| eval 25's board identity swap | the simulator copy uses P_sim (the identity-corrected reference); on public, (c) needs identity-clean tracks |
| V2 cannot see plate crossings (E4) | VI measures volume per phase, relative to the best candidate |
| Pixal3D-MV copied the partner board (E5) | generator inputs from separated views only; V2 (b) copy clause |
| single chaotic replays and settles misled earlier gates (E14, E17) | 16 jittered copies in every simulator judgement |
| simulator-copy placement carves made the E1 lid sink 0.6-1.0 cm and let the E30 sweeper fall through (E16) | P1 settle with a relative-sink bound and P2 free travel <= 4 mm for every carved pair, any kind or class; P4 over-removal bound |
| the "ends" variant (v3) was falsified on P31 (E16) | no segment-selection tuning; the physical tests decide; ep31 / eval 30 is a pre-registered negative control (T-I10) |
| 208 shapes on E28, over the about 165 budget (E18) | P5 episode cap |
| one shared `/content/assets` leaks carves across evals (E19) | per-episode delivery and manifest; per-episode asset roots required at pack time (6.4) |
| phys_fit v1 ran on the scans (E20) | validate() refuses its push numbers unless the fit ran on our delivered pieces and props (11.2) |

---

## 11. Contract with the Embodiment session (determined-wright) — please read this section

Their reply (31 Oct 08:46 UTC, `build/embodiment-reply-20261031.md`) is adopted: export as a standalone GT-free tool on
their reference poses, their field names, their simulator-copy layout, jittered-mean judging, a minimum frame count and
a relative-motion test in the rule. v2 adds what the review found missing: which geometry is sampled, in which
coordinates, and the provenance of the fit and of the reference.

### 11.1 Ownership
- **Embodiment owns** `tools/intrusion.py` (the export), `pipeline/phys_fit.py` and the solver/RL loop. The gmg never
  edits them.
- **gmg owns** `gmg/interlock.py` (file schema and validator, the region builder, decide_pair, the carve function),
  `gmg/simpieces.py`, `gmg/simphys.py` (the physical acceptance of 6.2) and the constants (PREREG F-I1). The
  Embodiment session never edits them. One implementation; both sessions call it.

### 11.2 Intrusion export `intrusions.npz` + `intrusions.json` (schema `gmg-intrusion/2`)
**Geometry (what is sampled).**
- Both the target's depth and the partner's samples come from the **union of the delivered collision pieces**
  (`<obj>/piece_XX.obj`) of the round named in the header, never from `<obj>.glb`. The GLB is the submitted, slot-less
  visual mesh; the simulator collides the pieces. Sampling the visual partner would put the partner's own bridged slot
  back in every round as a through-column, which no round could open.
- Partner solid samples: the points of a grid of pitch <= 2 mm inside the union of the partner's pieces ("inside" =
  inside at least one convex piece, an exact half-space test per piece). Target depth: distance to the surface of the
  union of the target's pieces (positive inside).

**Coordinates.**
- `pts_local` is in the target's **file coordinates**: the coordinates in which the vertices of its `piece_XX.obj` and
  `<obj>.glb` are written. `make_assets.py` writes identity collision and visual origins, so the URDF link (body) frame
  is the file frame (E23). MuJoCo re-centres mesh geoms to their inertial frame at compile time, so geom poses
  (`geom_xpos`, `geom_xmat`) must never be used; world -> file goes through the object's reference pose (or its body
  pose).
- **Fiducial round trip.** `manifest.json` gives 8 fiducials per object in file coordinates (6.1). The export carries
  `f_star` (one engaged frame), `fiducials_world` (per object, the fiducials mapped file -> world at `f_star` by the
  transform the tool used for that object's samples) and `fiducials_back` (the same points mapped back by the inverse
  the tool used for `pts_local`).

**Per sample** (N rows): `frame` int32; `target`, `partner` int16 (indices into `objects`); `pts_local` (N,3) float32
(metres, target file coordinates); `depth_m` float32 (informative only: in a plate crossing no sample is deeper than
half the plate, E4).

**Per frame-pair** (P rows): `fp_frame`, `fp_target`, `fp_partner`; `rel_T` (P,4,4) float64 (partner file frame ->
target file frame); `pushed_residual_m` float32 (after the fit's correction inside its 1 cm / 3 deg prior, the length of
the smallest further rigid translation of the partner that removes the remaining intrusion; 0 if none remains, NaN if
no fit ran); `intr_vol_m3` float32 (sample count x pitch^3 before the correction).

**Header `intrusions.json`.** `schema`, `objects` (names in slot order), `round`, `sim_dir`, `meshes` {name: {file:
sha256}} for every file the tool read, `pitch_m`, `tool`, `commit`, `argv`, and:
- `reference`: {path, sha256, `provenance`: the producer chain (tool, commit, run id per step) and every input file
  with its sha256, back to the perception outputs (`poses.npz`, `poses_world_vo.npz`, `hands_refined.npz`,
  `table_frame.npz`)};
- `fit` (required whenever any `pushed_residual_m` is not NaN): {tool, commit, argv, `meshes` {name: sha256 of the
  `--meshes` file}, `props` {path, sha256}, `prior` {sig_p, sig_r_deg, hold_f0}, `inputs` {file: sha256}};
- `pose_source`: "reference" or "phys_fit" (if the samples were computed on the fit's corrected poses, the fit block
  is also the provenance of the poses).

**`interlock.validate(path, sim_dir)`** (runs before any decision; identical on public and eval):
1. Refuse the file if: any mesh hash differs from the delivered round's `manifest.json`; frames are out of range;
   `rel_T` is not rigid; the fiducial round trip errs by > 0.5 mm; `fiducials_world` differs by > 0.5 mm from the
   reference pose at `f_star` applied to our file-coordinate fiducials (this catches a geom-frame or re-centred frame);
   fewer than 99 % of 10,000 random samples lie inside the union of the target's pieces, or fewer than 99 % of them,
   mapped back by inv(`rel_T`), lie inside the union of the partner's pieces.
2. Refuse the file if the reference provenance is missing or incomplete, or any path in its chain fails the gmg guard
   (`guard.py`, `ops/provenance/denylist.json`: mocap, the parquet `pose` field, `*_align.npz`, scans, library_v1..v4).
   Examples refused: a reference built from mocap object motion (the orcB "O" arm), a phys_fit output run on the scans.
3. Force `pushed_residual_m` = NaN for every row (flag `fit_provenance_refused`; the push proxy of 4.2 (ii) decides) if
   the fit block is missing or incomplete, its `meshes` are not exactly the delivered round's `_fit/<obj>.glb` files,
   its `props` is not the delivered round's `props_gmg.json` (no scan-derived geometry, COM, inertia or, until D-I1,
   mass), or its prior differs from 1 cm / 3 deg. phys_fit v1 as run on 30 Oct (scans, `props_public_scans.json`)
   falls here.
The fit therefore runs as `phys_fit.py IN OUT --meshes r<k>/_fit --props r<k>/props_gmg.json` on a reference that passes
step 2. Eval runs exactly this path: eval has no scans, and the same checks pass or fail by the same rules.

**How export input enters the rule.** The export's samples go through the same region builder as ours (3.3: build and
check frames, persistence, sweep, the true through-column test, the shared split plane of a linked pair) and the same
decide_pair (4.3), with the reach and volume budget measured after the split. The partner's own carved region needs no
separate subtraction: the partner's pieces already exclude every carve accepted in earlier rounds. At round 0 on an
uncarved copy, a through-column caused by the partner's uncarved slot is split by the pair's shared plane, exactly as in
our own path.

### 11.3 The carve function
```python
from gmg import interlock
res = interlock.carve_from_intrusions(
    pair=("wooden_piece_1", "wooden_piece_2"),   # both targets of a pair are decided together (4.3)
    intrusions="…/intrusions.npz",              # schema gmg-intrusion/2, validated first (11.2)
    evidence="RUN/bundle/public/ep24",           # our bundle: hits/free/state grids, sigma, j, census, tracks
    sim_dir="RUN/sim/public/ep24/r0",            # the round they ran on
    out_dir="RUN/sim/public/ep24/r1",            # new round; never overwrites
    round=1)
# res.pieces_dir  -> out_dir/<obj>/ (<obj>.glb, piece_XX.obj, inertia.json, carve.json), out_dir/_fit/, props_gmg.json
# res.decisions   -> [{region, voxels, cm3, kind, tier, decision: CARVE|PUSH|OFFSET|IGNORE, reasons, push_mm, frames, t}]
# res.physics     -> the 6.2 results per pair (P1-P7), and which pieces were delivered (carved or default)
```
CLI: `python -m gmg.interlock carve --pair A B --intrusions F --evidence BUNDLE --sim-in DIR --out DIR --round K`.
Single-object targets (one-sided features) use `--pair A B` too; the decision is then per target. The evidence is read
through the gmg guard. Their reference poses enter only through `rel_T` and the samples.

### 11.4 Rule (section 4, restated for them)
A place in the target's own frame is **carved** only if it is entered in at least max(5, 25 %) of the build frames,
and: either it is unseen or seen-empty space (class U) and carving it neither splits the target nor opens a hole; or it
is solid only to stereo (see-through in the silhouette, or narrower than 8 depth pixels in the views where stereo saw
it, where the silhouette cannot test), the partner **moves through it** (its entering points span >= max(8 mm, 3 j) of
the partner), it **cannot be pushed out** within 1 cm / 3 deg (our proxy, or your `pushed_residual_m` when your fit's
provenance validates), and the carve stays inside the budget (10 % of the volume, 0.6 of the depth, after the split).
Both halves of an interlocking pair are carved together or not at all. If our silhouette or the generator sees the
notch up to 2 cm to the side of where your reference puts the partner, the copy gets the seen notch at your reference's
position and the offset goes to the tracker (OFFSET). Surface that a testable silhouette shows as solid is otherwise
never carved. Every carve must then pass the physical tests of 6.2 before it is delivered. Everything else is **push**:
your fit, or the tracker, owns it.

### 11.5 Iteration
1. Round 0: the gmg delivers `r0` from P_sim = the reference you will replay (carves only where 6.2 passed).
2. You run phys_fit (optional) and the export on `r0` -> `intrusions_r0`.
3. The gmg validates and runs `carve_from_intrusions` per pair -> `r1` + decisions; PUSH and OFFSET lists go back to
   you and to the tracker session (frames, objects, needed correction).
4. You re-run on `r1`.
5. **Accept round k** only if all of these hold; otherwise round k is reverted (its budget released) and round k-1 is
   final:
   - **A1 held-out:** on the check frames (never used to build any region of any round), the persistent intrusion
     volume at engaged frames falls by >= 10 % against round k-1, and no other pair or phase gains more than 0.1 cm3;
   - **A2 push:** the number of check-frame pairs with `pushed_residual_m` > b does not increase (only when the fit
     block validated);
   - **A3 physical:** every carved pair of round k passes 6.2 (P1-P7), and its settle means are no worse than round
     k-1's by more than one standard error of the 16 copies;
   - **A4 over-carve:** the cumulative carve is within the budget of 4.2 (iv), no object keeps less than 90 % of its
     default collider volume, topology is kept, and the episode holds <= 165 shapes.
6. Stop at round 3, when a round adds no CARVE, or when A1 fails.
The build-frame intrusion reduction is reported but never decides: it falls by construction once the entered voxels
are carved. Zero-action `sim_vs_ref` is reported, never used to decide.

### 11.6 Same for public and eval
Identical code, constants frozen from public, no ground truth anywhere (their export reads only a validated reference
and our pieces; our rule reads our bundle and that export). On eval nothing is compared with public numbers.

### 11.7 What we ask them to change (their files, their decision)
`tools/intrusion.py` samples the union of `piece_XX.obj` (not the GLB), writes `pts_local` in file coordinates, adds the
fiducial fields and the `reference` / `fit` blocks; phys_fit runs with `--meshes r<k>/_fit --props r<k>/props_gmg.json`.

### 11.8 Resolutions (31 Oct 10:55 UTC, orchestrator; accepted by the Embodiment session 10:52; written here 31 Oct ~15:00 after the verifier's review, PREREG F-I3.9 / F-I3.10)
Their `tools/intrusion.py` (commit `759032e`, read here at `48cda9f`) raised five open points; the decisions and how
the code implements them:
1. **manifest layout.** Adopted: `manifest.json` schema `gmg-sim/2` carries `objects.<obj>.{files {basename: sha256},
   fiducials [8 x 3]}` (their reader's preferred layout) and keeps the `gmg-sim/1` top-level `files` / `fiducials`
   (`load_sim` reads both). **Fiducials, exactly:** the 8 corners of the oriented bounding box of ALL vertices of the
   object's pieces, box axes = the principal axes (SVD) of those vertices about their mean; each corner coordinate is
   moved 1 mm inward along each box axis (a corner moves 1.73 mm along the diagonal; every box face lies 1 mm inside
   the extreme vertex). Their `fiducial_box` check (margins 1 mm, symmetric) expects exactly this.
2. **Reference pose for validate step 1.** The header's own poses are never used (that compared the header with
   itself). Two independent sources (F-I3.10): (i) an independent reader of the reference's `object_body_*` columns
   (`validate(..., ref_poses=)`; for B10: a guard role for our reference parquets, since `guard.py` refuses every
   `.parquet` and belongs to build 1), or (ii) our tracks (role tracks) when their sha256 is the chain's
   `poses.npz`: one rigid transform common to all objects plus a per-object vertical shift (mkref's table snap) is
   fitted on the fiducials, and every object's fiducials and the export's `rel_T` at f_star must agree within 0.5 mm.
   Without either source the export is refused. Public dataset parquets stay refused everywhere.
3. **Provenance.** Their per-step chain is read (each step's `inputs`, `artifact`, `sha256`); a reconstructed chain
   (`--prov`, inferred, or marked reconstructed) is accepted with flag `prov_reconstructed` as long as it holds a
   perception `poses.npz` with a sha256 and no ground-truth or object-motion source (mocap, scans, `_align`,
   `oracle`, `/loc/`, deny-list, dataset episode parquets). library_v1..v4 meshes as simulator assets are allowed with
   flag `ref_sim_assets_library`; any other library_v file is refused. `poses_world_vo.npz` is not required.
4. **`--fit_commit`**: fine; the fit block must name a commit (else `pushed_residual_m` is forced to NaN).
5. **Approximate `pushed_residual_m`**: fine; it only feeds PUSH, and our push proxy remains the fallback.
**props_gmg.json** is now in phys_fit's layout `{obj: {physics: {mass_kg, com_m, inertia_kgm2, ...}}}` (the layout of
`props_masses_only.json`; the mass is still the 0.3 kg placeholder until D-I1). Section 19 records the run of their
real tool on our ep24 round 0 and our validator's verdict.

---

## 12. Modules, hooks and hand-offs

**New files (this stage; none of build 1's files is edited):**

| Module | Interface | Effort [E] |
|---|---|---|
| `gmg/interlock.py` | `engaged_runs`, `blocks(run) -> build, check`, `intrusions_from_tracks(bundle, o, p, poses)`, `regions(...) -> [Region]`, `image_width(region, bundle, views)`, `decide_pair(pair, components, evidence)`, `offset(region, notches)`, `agree(region, sources) -> tier`, `carve_from_intrusions(...)`, `validate(path, sim_dir)`, `load_sim(dir, episode)`, `icarve(cand, regions)` | 14 h |
| `gmg/silhouette.py` | `classifier(bundle, obj, video) -> model, gate`, `votes(bundle, obj, video, voxels) -> (nmv, nmf)`, `notches(...) -> N_b` | 6 h |
| `gmg/physcheck.py` | `features(mesh, bundle, obj, regions=None) -> dict` (5.1-5.5, VI) | 6 h |
| `gmg/simpieces.py` | `build(mesh, bundle, obj, carves, keepout, widths) -> (dir, report)`; `fit_mesh(pieces)` (the `_fit` union); `props(pieces, mass_table)`; `manifest(...)` | 9 h |
| `gmg/simphys.py` | `settle(pieces_o, pieces_p, pose, frames, jitter=16)`, `free_travel(pieces_o, pieces_p, pose, dirs)`, `replay_proxy(...)`, `over_removal(...)`, `shape_budget(...)`, `accept(pair, ...) -> P1-P7` | 10 h |
| `gmg/gen_slot.py` | `concavity(gen_mesh_placed, grid, r) -> C_a`; `layout_consensus(runs, bundle, obj)` | 5 h |
| `tests/test_interlock.py`, `tests/test_simphys.py` | T-I1 (synthetic plates, rendered images, controls) | 8 h |

**Installs (BI1):** `mujoco` (Apache-2.0) and `coacd` (MIT) into the gmg venv (both missing, E22); the FlashCHORD venv
rebuilt in this container for P1 (missing, E22) [E: 20-40 min].

**Hooks for build 1** (to be wired by the owners of those steps, B9/B10/B15):
- B9 `simcopy.py` calls `simpieces.build` and `simphys.accept` instead of plain CoACD.
- B10 `run_episode.py`: after the CPU producers, `interlock.regions` and `decide_pair` per pair; `interlock.icarve` adds
  ICARVE candidates; `physcheck.features` per candidate; select reads VI, V4t, VP, VF, the inherited flip units and the
  E exclusion.
- B15: `gen_slot.layout_consensus` before `place.fit`; FUSE-I in `producers/fuse.py`; the M10 slot-survival check.

**New build steps** (after B8, before B10): **BI1** modules + installs + T-I1 (CPU); **BI2** dev runs T-I2..T-I8 and
T-I10 on ep24, ep2, ep11, ep12, ep18, ep31 (CPU); **BI3** wiring at B10/B15; **BI4** the Embodiment loop (T-I9) once
their export exists.

**Hand-offs.**
- **Embodiment (determined-wright):** section 11 (with 11.7); the `r0` sim folders of ep24, ep2, ep11 (public dev)
  when BI2 is done.
- **Tracker (focused-pascal):** `RUN/interlock/<split>/ep<N>/push_list.json` (PUSH and OFFSET decisions with frames and
  corrections) and the `placement_drift` frames per object.
- **Pack session:** per-episode asset roots and the URDF-count check (6.4) before any launch that uses our pieces.
- **Analysis (keen-heisenberg):** collider overlap per phase for every delivered sim copy, and the 6.2 results.
- **GPU planning:** the board views and extra records of section 7 go into the G1 proposal.

---

## 13. Pre-registered tests and predictions (frozen in PREREG F-I1.12)

| ID | Test (data; cost) | Pass | Prediction and falsifier |
|---|---|---|---|
| T-I1 | **Synthetic** ($0, minutes). Main: two 230 x 125 x t mm plates with cross-lap half-slots of width t on opposite edges, **t swept over 6, 10, 13, 18, 25 mm**; slot voxels OBSERVED (bridged); depth camera at 0.5 m with fx 300 (w_bridge 13.3 mm); a straight 120 mm insertion over 60 frames plus 30 assembled frames; jitter 0.5 mm / 0.2 deg. **Rendered images:** a numpy ray caster renders textured plates on a textured table in 6 views, and the silhouette classifier, gate and votes run on those images. Cases: (s0) silhouette absent; (s1) rendered, see-through; (s2) rendered, low contrast (plate texture = table texture); (g) a slotted generator plate placed with 4 mm / 5 deg error; (o1) the track offset 11 mm laterally from the true slots, silhouette see-through; (o2) the same offset along d; (w) the partner's collider a 60 mm box; controls n1-n6 as in v1, n7 a thin tall guest (15 x 30 x 250 mm) in a holder slot whose carve removes the slot's bottom support, n8 one plate's region class O (testable silhouette says solid), n9 cup nesting with the outer candidate filling the cavity rim to floor | s0: GAP and CARVE (both plates) for t = 6, 10, 13 (projected 3.6, 6.0, 7.8 px); class O and PUSH (both plates) for t = 18, 25 (10.8, 15.0 px). s1: SIL and CARVE for every t; with (g): T3. s2: gate fails, (b) absent. o1: OFFSET, simulator carve at the replay position (shift within 2 mm of 11 mm), submitted ICARVE at the true slot only with (g). o2: PUSH, no OFFSET. w: PUSH, `interlock_partner_too_thick`. n7: P2 travel > 40 mm and P1 tilt > 5 deg detected, carve not delivered. n8: both plates PUSH (`interlock_pair_fail`). n9: no split, cavity carved as U. n2, n3, n6: PUSH; n4, n5: IGNORE. Carved slot width >= the partner's collider thickness + 2 mm in every carved case | [H] all pass; any miss is a code bug, fixed and logged before BI2 |
| T-I2a | ep24 silhouette gate (video in the scratch store) | reported: held-out pixel accuracy, false see-through share, SIL share of R_c and of the SAM 3D notch region | no prediction (v1's [H] "may fail" withdrawn); measured first in BI2 |
| T-I2b | decide_pair on the ep24 regions (dev now, clean when B4's bundle exists), on the B5 dev picks after the V5 clarification (shells) and on the HULLs: classes, image widths, decisions, OFFSET shifts, widths w_sim | reported | no claim that the ep24 simulator copies get carved until this runs |
| T-I2c | ep24 sources: (a, c) offset along the long axis; entry-side share of frame counts; OBSERVED share of R_c in the clean grid | reported | see P27a-c |
| T-I3 | 6.2 on ep24 (needs mujoco, coacd, the FlashCHORD venv): carved vs default pieces | 6.2 rules | P28 |
| T-I4 | ep24 pool with F-I1 (dev now, clean later) | VI vetoes the slot-less candidates whenever an ICARVE exists and overlaps by >= 1 cm3 less | P29 |
| T-I5 | ep2 lid + pot | no CARVE of class O on either object; lid-pot collider overlap at the seated frames <= 1 cm3; the lid's free travel <= 4 mm | [H]; falsified if any O voxel is carved or a carve with travel > 4 mm is delivered |
| T-I6 | ep11 cups | the outer cup's pieces keep the cavity (keep-out <= 0.3 cm3 per hull); any intrusion below the observed floor is PUSH, never OFFSET | [H]; falsified if an observed floor voxel is carved |
| T-I7 | Negative controls: ep18, the single-object episodes, ep12/13 cup in rack | ep18: no CARVE; single-object: no region; ep12/13: carves only in U voxels, episode shapes <= 165 | [H]; falsified by any O carve or a cap breach |
| T-I8 | 5.1 on the dev picks of the 10 anchor pairs | reported | P31 |
| T-I9 | Embodiment loop on ep24 and ep11 (needs their export) | 11.5 A1-A4 | P32 |
| T-I10 | **Negative control E30 / P31**: public ep31 (the eval-30 twin, sweeper in rack) with our meshes and our tracks; eval 30 runs the same guard at eval time, reported only, never used to change a rule | every delivered copy passes P1 and P2 | P34 |
| K-f | SAM 3D board runs in G1 | reported | P33 |

Predictions (each can fail):
- **P26** T-I1 passes as stated | any miss | [H].
- **P27a** clean ep24: the entry-side share of frame counts is >= 0.6 on both boards (a time-ordered insertion enters
  its entry half for longer than its far half) | < 0.6 on either board | [H; dev 0.54-0.57 points to a failure].
- **P27b** clean ep24: (a, c) offset along the long axis <= 10 mm on both boards | > 10 mm (then OFFSET decides the
  simulator copy) | [H; dev 10.5-12.9 mm on board 1 points to a failure].
- **P27c** clean ep24: >= 50 % of R_c is OBSERVED | < 20 % (then GAP and OFFSET are unused on the boards) | [H].
- **P28** T-I3: if T-I2b carves the boards, the carved pieces pass P1-P7 and P3, and the default pieces fail P3 | any
  carved failure | [H]; void (not passed) if T-I2b pushes the boards.
- **P29** T-I4: on clean ep24, if an ICARVE(shell) exists, its median assembled overlap is >= 1 cm3 below the slot-less
  shell's and VI removes the slot-less shell and HULL | otherwise | [H].
- **P30** T-I5 to T-I7: no class-O voxel carved on ep2, ep11, ep12, ep13, ep18 | any | [H].
- **P31** T-I8: CPU picks' constant placement offset <= 1 mm on >= 9 of 10 anchor pairs; `placement_drift` on the ep11
  blue cup | < 8 of 10, or no flag | [H].
- **P32** T-I9 on ep24: round 1 reduces the check-frame intrusion volume by >= 50 % and its carved copies pass P1-P7;
  on ep11 no observed floor voxel is carved | either fails | [H].
- **P33** K-f: >= half of the board runs show a notch that survives remesh | fewer | [H].
- **P34** T-I10: on ep31 the rack-sweeper pair delivers either its default pieces or a carve with gravity free travel
  <= 4 mm and mean tilt <= 5 deg | any delivered copy outside these bounds | [H].
These tests gate or fix steps; none is a failure criterion of the gmg (D.3).

Scan scorings: none in this stage. R1 and R2 gain the base candidates of ICARVE / FUSE-I anchor picks and the
pre-clarification picks of `v5_hull_clarified` anchors (section 8; caps in PREREG F-I1.11).

---

## 14. Cost

- **CPU [M where marked, else E]:** intrusions from our tracks per pair: under 1 min; silhouette per object: 1-2 min;
  regions, image widths and decisions: seconds to a minute; ICARVE booleans: seconds per candidate; physcheck: 5-30 s
  per candidate; pieces: 1-3 min per object. Physical acceptance per carved pair: the replay proxy took 248 s for one
  run on 26 Oct [M, quoted by the review], so 16 copies take about 16-64 min on 4 shared cores; settles (2 s simulated,
  16 copies, up to 4 frames, carved and default) about 20-80 min; free travel 1-3 min. **About 0.6-2.5 CPU-hours per
  carved pair**, about 4-15 h for a public batch with about 6 carved pairs, and about the same for eval. On this
  container it competes with build 1's runs. A rented CPU-only box would be a separate owner decision with its own cost
  (none proposed here).
- **Installs:** mujoco, coacd, the FlashCHORD venv (E22): 20-40 min once [E].
- **GPU [E]:** SAM 3D board views: +$0.3-0.6 in each of G1, G2 and G4. No new rental by itself.
- **People-time [E]:** about 58 build-hours (section 12).

## 15. Risks and open points

- **The boards may be pushed, not carved.** If the silhouette gate fails (T-I2a) and the gap is wider than 8 depth
  pixels in the views where stereo saw it, the region is class O; without an observed notch for OFFSET, both boards are
  pushed and stay slot-less in the simulator too. Stated plainly: v2 does not promise a carved eval-25 copy; T-I2b
  decides on public dev and the same rule runs on eval.
- **Dev contamination:** E3's OBSERVED share and board 2's 2.58 x thickness reach probably include partner points
  owned by the target in `obs_all`. P27c on the clean bundle decides.
- **OFFSET removes camera-solid voxels in the simulator copy** (only the observed gap's shape, moved by at most 2 cm
  sideways). A wrong shift would cut real material in the copy. Guards: lateral shifts only, >= 50 % overlap, the
  physical tests of 6.2, the tracker check of t, never in a submitted mesh.
- **The R1 revert is the only guard against a submitted-mesh flip** (VF rarely fires, section 8). With 2-4 objects the
  mean CD-O difference is noisy.
- **w_bridge is a hypothesis** (8 depth pixels); T-I1 tests the image-width code, not the stereo model behind it.
- **Masses (D-I1):** `props_masses_only.json` is scan-derived for scanned objects; until the owner decides, the
  placeholder is used in the simulator copies and in the fit, on public and eval.
- **P_sim provenance:** if the packed eval-25 reference's provenance chain cannot be shown GT-free, the copy falls back
  to P_sel (`sim_pose_fallback`), whose eval identity flag is report-only (2.1).
- **Cost:** the jittered physical checks dominate (section 14) and compete with build 1 for 4 cores.
- **One real insertion example** (ep24 public; eval 25 is the target): thresholds are generic or carried over from
  earlier pre-registrations; the ones chosen after seeing October results are labelled informed in F-I1.14.
- **The spoon** pairs are unmeasured; their regions are reported on eval only, never tuned.

---

## 16. Revision note (v2, 2026-10-31, after the design review of v1; still before any scoring round)

v1 = commit `2eb8397` (INTERLOCK.md and PREREG F-I1 as first written). No scan number was seen for this revision; the
only new measurements are dev re-runs without a scan (E15, E22) and documents read (E16-E21, E23).

| Review item | Resolution (where) |
|---|---|
| B1 GT path in the contract: phys_fit v1 ran on scans; nothing pinned the fit's meshes, props or the reference | header `fit` and `reference.provenance` blocks; validate() refuses a non-GT-free reference and forces `pushed_residual_m` = NaN unless the fit ran on the delivered `_fit` meshes and `props_gmg.json`; same path on eval (11.2; F-I1.13) |
| B2 export geometry undefined; visual partner re-inserts its bridged slot; split and R*_p not applied to export input | samples and depth from the union of the delivered pieces, in file coordinates; geom frames forbidden; fiducial round trip and containment checks; export input goes through the same region builder, true through-column split and pair decision; reach measured after the split (11.2, 3.3, 4.2; F-I1.13) |
| B3 carve history unread; no sinking or fall-through guard | carve-20261030 read (E16-E19); P1 settle (16 jittered copies, relative sink), P2 free travel <= 4 mm, P4 over-removal, P5 165-shape cap, P6, per-episode asset roots for every carved pair, any kind or class; E30/P31 negative control T-I10, n7 replica (6.2, 6.4, 13; F-I1.8, F-I1.12) |
| B4 deadlock between the silhouette and track bias; T2 (a, c) against a testable solid silhouette | P_sim for the simulator copy (2.1); OFFSET rule (4.4); any disagreeing present source blocks submission; a pushed component never yields submitted candidates except T2o at the observed notch (3.4) |
| B5 no pair-level decision; slot width not tied to the partner's collider | decide_pair with linked components, both or neither (4.3); w_sim >= the partner's simulator collider thickness + clearance, `interlock_partner_too_thick` (3.5); ep24 decision deferred to T-I2b, the v1 claim "simulator copies are still carved" withdrawn (0, 15) |
| B6 circular acceptance and tautological predictions | build/check frames (3.3); acceptance on held-out frames plus P1-P7 (6.2, 11.5); P27 and P32 replaced by predictions that can fail; flip resolution no longer uses the slot side; unsigned axis comparison; section 0 and E2 corrected |
| B7 undeclared reversal of SPEC section 14 | named and justified in section 8 and PREREG F-I1.0 |
| VI below the quantisation floor | VI relative to the best candidate (5.2) |
| VF probably vacuous | stated; flip units inherited from the base; the R1 revert named as the real guard (8) |
| V5 clarification without a guard | affected dev objects listed (only board 2 of 4); `v5_hull_clarified` picks scored at R1 with a global revert (8) |
| +0.005 cm tolerance scan-derived | tolerance 0; per-object differences reported (8) |
| GAP tests object thickness; 15 mm at 0.55 m | image-plane width in the views where stereo bridged; about 13.5 mm at 0.50-0.51 m [E] (4.1) |
| T-I1 single 10 mm plate, synthetic votes | thickness sweep 6-25 mm with pre-registered GAP outcomes; rendered-image silhouette cases (13) |
| eval identity vs SPEC section 7; which eval-25 poses carve the copy | public only for IDENTITY_SWAP -> no (c); eval flag only; eval-25 copy from the packed policy's reference; round 0 from P_sim (2.1) |
| split misfires on deep cup nesting | true through-column required (3.3); n9 (13) |
| masses from `props_masses_only.json` | scan-derived (E21); placeholder until owner decision D-I1 (6.1) |
| cost and feasibility | 248 s proxy run -> 16-64 min per pair; settles; 0.6-2.5 CPU-h per carved pair; mujoco and coacd missing, installs in BI1 (12, 14) |
| ep24 video available for the gate | T-I2a measured first in BI2; [H] "may fail" withdrawn (3.2, 13) |
| "6.8 cm HULL box" and E3 | OBB thickness; partner samples only 6.0 / 8.6 mm deep; E3 not cited for GAP (0, E3, E4, E12) |
| contract frame | `pts_local` in file coordinates with the fiducial round trip (11.2) |

Not done in this revision (stated, not hidden): the silhouette gate on ep24 and decide_pair on the ep24 dev regions
were not run (no code yet; they are T-I2a and T-I2b, first in BI2); `review_depth.py` was not re-run.

---

## 17. As built (BI1, 31 Oct) — interface for the gmg and for the Embodiment session

Code (new files only; none of build 1's files is edited): `gmg/interlock.py`, `gmg/silhouette.py`, `gmg/gen_slot.py`,
`gmg/physcheck.py`, `gmg/simpieces.py`, `gmg/simphys.py`, `gmg/tools/interlock_dev.py` (dev driver of one episode),
`gmg/tools/interlock_cands.py` (CPU candidates of a clean bundle through build 1's producers),
`gmg/tests/test_interlock.py` (T-I1). Build-time corrections and their reasons: PREREG **F-I2** (no F-I1.14 threshold
changed). Notes and commands: `build/I.md`.

### 17.1 For the Embodiment session (determined-wright): what to call, what to write (updated 31 Oct, F-I3)

```python
import sys; sys.path.insert(0, 'docs/research/mesh-2026-10-26')   # GMG_MODE=dev for public dev, clean otherwise
from gmg import interlock as IL
b = IL.load_bundle_any('…/bundle/public/ep24')                     # our evidence (tracks, grids, flags)
tracks = dict(path=b.meta['tracks']['path'], sha256=b.meta['tracks']['sha256'], poses=b.poses)
ok, rep = IL.validate('…/intrusions.npz', '…/sim/public/ep24/r0', tracks=tracks)   # 11.2 + F-I3.10; rep['refused']
res = IL.carve_from_intrusions(('wooden_piece_1', 'wooden_piece_2'), '…/intrusions.npz', evidence='…/bundle/public/ep24',
                               sim_dir='…/r0', out_dir='…/r1', round=1)   # physics_fn='default' (P2-P7 + P1 pre-check)
# res['decisions'] (per region: decision, tier, reasons, push_mm, widths, offset, budget, flags, push_list),
# res['pieces_dir'], res['validation'], res['physics']; carved pieces that cannot be delivered here (P1 = your
# jitter_check) go to r1/_carved_pending_p1/ and r1 delivers the previous pieces
acc = IL.round_accept('…/intr_r0.npz', '…/intr_r1.npz', '…/r0', '…/r1', tracks=tracks,
                      settle={'wooden_piece_1|wooden_piece_2': dict(pass_=True, ...)})   # 11.5 A1-A4, F-I3.3
sim = IL.load_sim('…/r0', episode=24)          # refuses another episode's folder and do-not-use folders (F-I3.8)
```
`physics_fn(b, o, p, carved, default, recs, rels=None, run=None) -> dict(deliver_carved, P2_P7_pass, ...)`; the default
(`IL.default_physics()`) runs `simphys.pair_physics` on the export's own `rel_T` (P_sim). Sources (a), (b) and the
observed notches come from `<sim_dir>/sources/<obj>.npz`, written by the gmg with round 0 and carried by every round
(F-I3.1), so the export path decides with the same inputs as ours.
CLI: `python -m gmg.interlock validate --intrusions F --sim-in DIR --evidence BUNDLE`,
`python -m gmg.interlock carve --pair A B --intrusions F --evidence BUNDLE --sim-in DIR --out DIR --round K
[--no-physics]`, `python -m gmg.interlock accept --prev F0 --new F1 --sim-prev D0 --sim-new D1 --evidence BUNDLE
[--settle JSON] [--band-m B]`.

**Export file (schema `gmg-intrusion/2`)**: exactly what `tools/intrusion.py` writes; `IL.write_export(path, bundle,
sim_dir, pair, reference, poses=None, frames=None, pitch=0.002, fit=None, pushed=None)` writes the same header layout
from a delivered round and a set of poses (tests).
- npz per sample: `frame` int32, `target`, `partner` int16 (indices into `objects`), `pts_local` (N,3) float32 in the
  TARGET's file coordinates (the coordinates of its `piece_XX.obj` / `<obj>.glb`), `depth_m` float32;
- npz per frame-pair: `fp_frame`, `fp_target`, `fp_partner`, `rel_T` (P,4,4) float64 (partner file -> target file),
  `pushed_residual_m` float32 (NaN if no fit), `intr_vol_m3` float32;
- json: `schema`, `objects`, `round`, `sim_dir`, `meshes` {obj: {"piece_XX.obj" (or "<obj>/piece_XX.obj"): sha256}},
  `pitch_m`, `tool`, `commit`, `argv`, `reference` {path, sha256, provenance {chain [{tool, commit, run_id, artifact,
  sha256, inputs {path: sha256}}], ...}}, `fit` (tool, commit, argv, meshes {obj: sha256 of r<k>/_fit/<obj>.glb}, props
  {path, sha256 of r<k>/props_gmg.json}, prior {sig_p: 0.01, sig_r_deg: 3, hold_f0}), `pose_source`, `frames` (or
  `T`), `f_star`, `fiducials_file`, `fiducials_world`, `fiducials_back`.
- Partner samples: points of a <= 2 mm grid inside the union of the partner's delivered pieces (not the GLB).

**Delivered round folder** (`simpieces.write_round`, never overwritten): `<obj>/<obj>.glb` (visual = submitted mesh),
`<obj>/piece_XX.obj` (collision; `make_assets.py --pieces`), `<obj>/inertia.json`, `<obj>/carve.json` (delivered,
decisions, physics, pieces gate), `_fit/<obj>.glb` (union of the pieces for `phys_fit.py --meshes r<k>/_fit`),
`props_gmg.json` {obj: {physics: {mass_kg 0.3 placeholder (D-I1 open), com_m, inertia_kgm2, volume_cm3}}} (phys_fit
`--props`), `sources/<obj>.npz`, `manifest.json` (schema gmg-sim/2: episode, split, round, p_sim, objects.<obj>.{files,
fiducials, gate}, files {path: sha256}, fiducials, code {commit, dirty, sha256 of the code files}, interlock {holdout,
carved_cm3, solid_ref_cm3, default_collider_cm3}, do_not_use), `interlock_regions.npz` (rounds >= 1) and, when the
pieces fail the keep-out gate, `DO_NOT_USE.json`. Carved pieces that passed P2-P7 but could not run P1 here are kept
in `<interlock out>/_carved_pending_p1/` (one name for both paths).

### 17.2 What the rule does, in one paragraph (for them)
A place in the target's own frame is carved in the simulator copy only if the partner enters it in at least
max(5, 25 %) of the build frames of an engaged run, the entered voxels are not seen as solid (unseen, or see-through
in our RGB silhouette, or narrower than 8 depth pixels where stereo saw it), the partner moves through it (sweep test)
and cannot be pushed out within 1 cm (our push proxy, or your validated `pushed_residual_m`), and the carve stays in
the budget; both halves of an interlocking pair are carved together or not at all; an observed notch (silhouette or
placed SAM 3D) within 2 cm to the side of where the reference puts the partner is moved there (OFFSET) and the offset
goes to the tracker. Everything else is PUSH: a pose correction for your fit or the tracker (`push_list.json`).

## 18. BI2 dev results (31 Oct, CPU, no scan) — what the built stage does on ep24, ep2, ep11

Runs: dev process (GMG_MODE=dev, tier DEV) on build 1's CLEAN B4 v4 bundles (`gmg/runs/20261031-b4ext4-b61e8aa`),
candidates from build 1's CPU producers (shell, HULL), our tracks (P_sel), the ep<N>_a.mp4 videos, the clean run's
hands, and the 29 Oct SAM 3D meshes (dev only; made from ep23 / ep2 / ep11 crops seeded with library_v3; placed by our
depth, F-I2.10). Run folder `<scratch>/gmg/runs-dev/20261031-i2probe-626ce13`, code `78570c3` (driver
`gmg/tools/interlock_dev.py`; commands in `build/I.md`). Results: `build/I/results/`, delivered r0 folders
`build/I/sim_r0/`, figures `build/I/png/`. Zero scan reads. Labels: [M] measured here, [H] hypothesis.

**Identity flags change the public outcome.** Build 1 wrote the B.15 cross identity test into the clean bundles at
11:36: ep24 BOTH boards and ep11's blue cup are IDENTITY_SWAP (the two boards are near-identical shells). On public
episodes F-I1.2 then makes source (c) absent: **public ep24 and ep11 get no region at all (IGNORE, uncarved
copies).** On eval the identity test only flags (SPEC section 7); the `evalsem` runs below apply that eval semantics to
the same public geometry, i.e. what the rule will do on eval 25 / 10 if the evidence looks the same.

### 18.1 ep24 boards (eval semantics; picks = the shells after the V5 clarification)
| | board 1 (wooden_piece_1) | board 2 (wooden_piece_2) |
|---|---|---|
| run (c) [M] | INSERTION f164-274, travel 122 mm, straightness 0.91, assembled f218-274 | f162-274, 128 mm, 0.92 |
| motion region [M] | 127 voxels, a 25 mm band across the FULL width (131 mm), through-column, split by the shared plane: carve side 67 voxels, edge to 10 mm past the centre line | 222 voxels, 19 mm band, full width (128 mm); carve side 118 voxels, edge to -6 mm |
| (a) SAM 3D, placed [M] | agrees: centroid 6.2 mm, axis 1.2 deg, 100 % of R in C_a; along the long axis 1.3-3.6 mm; flip unresolved (margin 0.00 sigma) | agrees: 9.0 mm, 2.2 deg, 73 %; along the long axis 7.1 mm; the SAM slot opens at the OTHER edge (side untestable: flip unresolved) |
| (b) silhouette [M] | absent: no qualifying frame (a hand within 16 px in 33 of 34 separated frames) | gate passes (accuracy 0.917, false see-through 0.27 %) but sees wood in the region: SIL share 0.008 -> disagrees |
| GAP image width [M] | 9.0 px median (p10 7.9) > 8 -> class O | n/a (testable silhouette says solid) |
| decision | **PUSH** (class O 97 %); OFFSET with the SAM notch fails its topology test (the placed concavity is a 63 x 117 mm block) | **PUSH** (class O 65 %); its OFFSET holds alone (t 8.9 mm) but the linked partner has none -> both PUSH (`interlock_pair_fail`) |
| simulator r0 | default pieces (32 + 32; CoACD 13-15) | |
| submitted | no ICARVE (no T2 / T3 / T2o) | |

Why no carve, in plain words (**corrected 31 Oct, PREREG F-I3.11**; the first version blamed the brown table): the
place the partner passes through is 19-25 mm wide in board 1's frame (the partner's stereo evidence thickness, 12-19 mm,
plus track jitter), while the real slot looks about 6-8 mm wide in the RGB video (cam_a frame 26, board 2: 10-12 px at
about 1.6 px/mm, inner wall included) [E, by eye]. So two thirds or more of that place is wood that the cameras saw,
and even a perfect silhouette that sees the true slot would leave most of R class O (> 25 %): step 2 pushes. The
wooden table may also hurt the colour model, but it is not why the boards push, and the earlier [H] that a depth-free
see-through test would separate the cases is withdrawn. The 12-19 mm figure quoted in F-I2.14 and the test docstring
is the evidence thickness, not the boards'; the t = 6 mm known miss of T-I1 is therefore the regime that matters on
ep24 and eval 25. [H, not used] The region must be measured against the partner's plate thickness, not its evidence
thickness (falsifiable on ep24, F-I3.11).

**DIAG counterfactual** (forced split at the shared plane, never delivered or submitted; `results/ep24-evalsem/
diag_*.json`): slotted shells packed watertight (3892 / 4000 faces), slot widths w_sub 12.6 / 14.6 mm, w_sim 21.7 /
14.6 mm. Partner evidence inside the candidate at the assembled frames 7.0 -> 3.4 cm3 (board 1), 9.0 -> 5.2 cm3
(board 2) (the rest is the partner's own unslotted half). Collider overlap at assembly (pieces) 6.9 -> 0.76 cm3,
check frames 6.8 -> 0.73 cm3 (P6, P7 pass); P4 passes (95 / 97 % of the collider kept). **Replay proxy (MuJoCo, 16
jittered copies): default 1.85 cm / 113 deg (the cross cannot close), carved 0.33 cm / 9.4 deg, contact off 0.03 cm /
0.1 deg.** P3 fails on rotation (> 5 deg) and P2 fails across the slot (+n 13 mm free travel: w_sim 21.7 mm on board 1
against a 12.6 mm evidence thickness; the partner-collider term of w_sim uses the partner's 1-99 % extent at the
crossing, 19.7 mm, which includes its marker bump). The P1 pre-check fails for default and carved alike (the cross is
held in the air at the assembled frame and drops about 2 cm with hands parked). So even a carve would not be delivered
as built: [H] the slot width needs the partner's plate thickness, not its extent near the crossing.

**P27 (clean geometry, dev process)** [M]: P27a entry-side share 0.646 / 0.580 -> **fails** (< 0.6 on board 2);
P27b (a, c) offset along the long axis 3.6 / 7.1 mm -> passes (the dev obs_all estimate of 10.5-12.9 mm does not
reproduce on the clean bundle); P27c observed share 0.93 / 0.61 -> passes. P28 is void (T-I2b pushed the boards).

**Placement along the whole movement (5.1)** [M]: board 2 shell constant offset 0.5 mm, drift MAD 0.9 mm (one block
of frames 130-140 at 230 mm, where its owned points are not its own); board 1 shell 87 mm constant, drift MAD 65 mm:
its owned points in frames ~72-240 lie 125 mm from its candidate (frames 250-270: 0.7 mm) - the same ownership /
identity problem that B.15 flags. Table (V4t) never applies (<= 5 % of frames over 1 %). VI: board 1's HULL is vetoed
(13.1 vs 7.0 cm3), board 2's HULL ties its shell (8.96 vs 8.97 cm3).

### 18.2 ep2 pot + lid (no identity flag; picks pot shell, lid HULL as in the B1 dev run)
SEAT runs f0-60 and f272-342 (travel 22-36 mm, straightness 0.58-0.70) [M]. Pot <- lid regions 916 / 273 voxels,
class O 68-74 % (the pot's silhouette gate passes, accuracy 0.985, and sees the rim solid) -> PUSH; lid <- pot (HULL)
O 93-95 % -> PUSH; two small GAP regions (4 and 7 voxels) are pushable (2 and 4 mm) -> PUSH. No carve: **T-I5 holds**
(no class-O carve). The lid's silhouette gate fails (false see-through 2.4 %). SAM 3D: the pot meshes lose their notch
in the remesh (`gen_slot_lost_in_remesh`), the lid meshes are pot+lid shapes (diag 30 Oct) -> (a) absent or noise.
**Collider overlap while seated: our default pieces up to 425 cm3 vs CoACD 98 cm3** [M] (`png/ep2_track.png`): the
F-I1.8 keep-out counts free space only within 2 voxels of the surface, so hulls may span the pot's opening; see 18.4.

### 18.3 ep11 cups (eval semantics; blue cup IDENTITY_SWAP on public)
INSERTION f42-136, travel 190 mm, straightness 0.92 [M]. Regions 1214 (blue) and 782 (beige) voxels, class O 52 /
62 % (testable-solid silhouette) -> PUSH both; (a) and (b) disagree. One 3-voxel U carve on the beige cup (T1,
0.33 cm3) whose pair has no carve: default pieces delivered. **T-I6 holds** (no observed floor voxel carved). The
partner occupancy includes SHARED voxels (F-I1.1), and on ep11 the cups share 2595 / 2256 voxels against 2390 / 2850
OBSERVED [M]: the contact interface itself counts as intrusion and inflates the regions. VI at the assembled frames
would veto both SHELLS (100.7 / 73.9 cm3) in favour of the partner-clipped HULLs (9.1 / 33.3 cm3) [M]: a HULL win
that B10 must not take at face value. Default pieces fill the cups' cavities (union 697 / 666 cm3 vs solid 172 /
169 cm3), collider overlap up to 544 cm3 vs CoACD about 300 cm3 [M].

### 18.4 What this means and what is open
- **The pre-registered rule carves nothing on these three public episodes** (and, by the B.15 flags, finds no region
  at all on public ep24 / ep11). With eval semantics it PUSHES the boards: the evidence it is allowed to trust says
  "solid" where the slot is. The physics of a slot is not the limit: a DIAG slot lets the cross close to 0.33 cm.
- **Open problems, measured here** (none fixed in this step; each needs a dated F entry before use):
  1. the motion region is 2-4 x wider than the slot (partner evidence thickness + jitter vs a 6-8 mm slot [E]), so
     class O dominates whatever the silhouette sees (corrected 31 Oct, F-I3.11; the "wooden table" reading and its
     [H] are withdrawn);
  2. w_sim uses the partner's extent near the crossing (19.7 mm with a marker bump vs 12.6 mm plate) -> P2 fails [M];
  3. F-I1.8 keep-out limited to 2 voxels from the surface lets our default pieces fill open containers (pot, cups):
     425 / 544 cm3 overlap vs CoACD 98 / ~300 cm3 [M]. A probe without the limit does not fix it [M]: ep11 overlap
     max 307 cm3 (union 453 / 793 cm3 vs solid 172 / 170), ep2 pot union 2776 cm3 after only 11 pieces: the port's
     split search freezes pieces whose best plane removes < 10 % of the weighted excess (collision_decomp.py's rule),
     and the partner-occupancy weight (x10) keeps the excess far above 0.3 cm3, so B9 needs a better splitter (or
     CoACD's pieces checked against our keep-out) before simulator copies of containers use our pieces;
  4. SHARED voxels in the partner occupancy count the contact interface (ep11, ep2) [M];
  5. the placed SAM 3D concavity at r = 12.4-20 mm is a large block, not a slot (63-71 mm long on board 1) [M];
  6. VI prefers partner-clipped HULLs where shells touch the partner (ep11, ep2 pot) [M];
  7. FlashCHORD's P1 settle is not in this container; the plain-MuJoCo pre-check is uninformative when the pair is
     held in the air at the assembled frame [M].
- **Pre-registered tests touched here:** T-I1 (16 OK, 1 expected failure = logged P26 miss; s2 and rendered-image
  silhouettes not run); T-I2a (board 1 absent, board 2 passes the gate but disagrees); T-I2b (PUSH both, eval
  semantics; IGNORE on public); T-I2c / P27 above; T-I3 / P28 void (no carve); T-I4 / P29 void (no ICARVE exists);
  T-I5 holds on ep2; T-I6 holds on ep11; T-I7 to T-I10 not run in this step.
- **Hand-off to the Embodiment session (corrected 31 Oct, F-I3.8):** the r0 folders `build/I/sim_r0/ep24-evalsem/`,
  `ep2-t3/`, `ep11-evalsem/` violate F-I1.8 (pieces hold up to 0.72 / 2.0 cm3 (boards), 945 / 533 cm3 (cups) and
  1250 cm3 (pot) of keep-out per hull, limit 0.3 cm3) and are now marked **do-not-use** (`DO_NOT_USE.json`;
  `load_sim` refuses them). Their props file is also in the wrong layout for phys_fit (fixed in F-I3.9). New
  deliveries go through the keep-out gate (section 19); the ep24 r0 of section 19 is the one to use.

## 19. Round-1 fixes after the verifier's review of the build (31 Oct, PREREG F-I3)

The review found eight blocking problems in the built stage. Each one, what was wrong, and what the code does now
(rule text in PREREG F-I3; labels [M] measured here without a scan, [E] estimate, [H] hypothesis):

| review item | what was wrong | fix (F-I3) |
|---|---|---|
| B1 contract vs their real tool | validate crashed on their header (no `reference_poses_f_star`), refused every export (basename mesh keys, per-step provenance inputs, chain parquets and library sim assets), had no frame range (`frames` vs `T`), compared the header's poses with themselves; props_gmg.json was not in phys_fit's layout | validate reads their header, never raises, takes the f_star pose from an independent source only (a reader of the reference, or our tracks when they are the chain's `poses.npz`: frame-free fit + rel_T at f_star), reads per-step provenance with `prov_reconstructed`, refuses ground truth and dataset parquets but not reference parquets or library sim assets; props_gmg.json `{obj: {physics: ...}}`; manifest `objects.<obj>.{files, fiducials}` (F-I3.9, F-I3.10, 11.8) |
| B2 export path not the same rule | no silhouette, generator, notches or identity gate on the export path; n axis fell back to the component's thinnest axis | one constructor `make_side` for both paths; sources saved with every round (`sources/<obj>.npz`); partner pieces as the export's partner samples (F-I3.1) |
| B3 iteration | budget not cumulative, A1 on invalid exports, A1 on all samples without the other-pair clause, check frames recomputed, A3 / A4 not wired | cumulative budget vs the round-0 solid, fixed hold-out, round_accept rewritten (F-I3.3) |
| B4 class O carved | submitted ICARVE ignored class O; OFFSET's N + t had no budget | both fixed (F-I3.2, F-I3.4) |
| B5 (a) could not fail | C_a cut to R's neighbourhood before the tests | whole touching components + reverse share (two-way), also (a, b) and OFFSET (F-I3.5) |
| B6 container pieces | r0 pieces of the pot and cups held up to 1250 cm3 of keep-out per hull (limit 0.3) and were offered to the Embodiment | keep-out gate (ours, else CoACD, else do-not-use; `load_sim` refuses); the three old r0 folders marked do-not-use (F-I3.8) |
| B7 tests | o2 never exercised its rule, n4 passed vacuously, the contract test never called carve_from_intrusions | o2a / o2b, n4 on its runs, contract through carve_from_intrusions, new tests (F-I3.6) |
| B8 wrong justification | "boards 12-19 mm thick" was the evidence thickness; the slot is about 6-8 mm in the video [E] | F-I2.14 / 18.1 corrected; the table explanation and its [H] withdrawn (F-I3.11) |

| (found while fixing) | the export path counted every frame, our bundle every second one (stride 2), so the gate saw a good share of 0.5 and made (c) absent; carves past a slot end opened pockets under seen faces | export frame-pairs on our frame grid (F-I3.1); column rule (F-I3.12) |

### 19.1 Their real tool on our ep24 round 0 (31 Oct 14:50-15:30, dev, no scan) [M]
- **Round 0** (`gmg/tools/interlock_dev.py --identity eval --tag r1evalsem`, run `20261031-i2probe-626ce13`, 897 s):
  decisions as in 18.1 (board 1 PUSH, U 2 / O 65, image width 9.0 px; board 2 PUSH, U 41 / O 77 testable solid),
  now with **(a) disagreeing on both boards** under the two-way test (board 1: the placed SAM 3D concavity near R is
  38.4 cm3 against R 4.3 cm3, reverse share 0.21, centroid 24.4 mm; board 2: 6.7 vs 7.6 cm3, reverse 0.35,
  centroid 19.3 mm). Board 2's OFFSET, which "held alone" in 18.1, now fails its budget (F-I3.4): reach 0.81 > 0.6
  and the N + t carve would cut the board in two (components 1 -> 2). The **pieces gate** marks this round
  do-not-use: our pieces hold 0.72 / 2.0 cm3 of keep-out per hull at most (13 / 21 of 32 hulls over 0.3), CoACD's
  52.9 / 77.3 cm3 (12 of 13 / 15). Collider overlap along the track: ours max 7.45 cm3, CoACD max 18.5 cm3.
- **Their tool, unmodified** (`origin/claude/determined-wright-3joens` at `48cda9f`: `tools/intrusion.py`,
  `pipeline/phys_fit.py`), run by `build/I/contract_ext.py` (not a gmg process) on that round 0 with a reference
  parquet built from OUR ep24 tracks in a table frame (a stand-in: their perceived ep24 reference is not in this
  container and there is no HF token here) and a `.prov.json` naming the tracks file:
  `intrusion.py` accepted our manifest and fiducials (fiducial box margins exactly 1.0 mm on every face, round trip
  and parquet check ~1e-13 mm, containment 1.0 / 1.0), 22 s, 227 of 482 frame-pairs with intrusion, 130,848
  samples, flag `reference_provenance_incomplete` (their perception list: no `poses_world_vo.npz`,
  `hands_refined.npz`, `table_frame.npz` in our chain). `phys_fit.py` read our `_fit/<obj>.glb` and
  `props_gmg.json` and ran to completion (max_nfev 3: a plumbing run, not a fit result; 691 s).
- **Our validator on their export** (`build/I/contract_gmg.py`, with the explicit do-not-use override, flagged):
  **valid**; independent pose from our tracks as the chain's `poses.npz` (frame-free fit residual 0.0 mm, rel_T at
  f_star 0.0 mm, rel_T over all 482 rows 0.0 mm, vertical shifts 0.0 mm); `pushed_residual` none.
- **carve_from_intrusions on their export** (eval semantics, sources from the round): **PUSH both boards, T0, (a)
  disagreeing** - the same decisions and tiers as our tracks path. The regions differ because the export samples
  the partner's pieces (solid) and ours its stereo evidence: board 1 U 3 / O 85 (tracks U 2 / O 65), board 2 U 36 /
  O 41 (tracks U 41 / O 77). Before the frame-grid fix the export path gave IGNORE (good share 0.5, see the table).
- **With their fit** (`intrusion.py --fit <phys_fit out> --fit_commit 48cda9f`, 2598 s, of which 2573 s for the push
  residuals): their own fit check passed (fit input = this reference, 0.0 mm / 0.0 deg); `pushed_residual_m` finite
  on 352 of 482 rows (130 beyond their 10 cm cap), non-zero on the 227 intruding rows, median 65 mm (on a 3-iteration
  plumbing fit, i.e. nearly uncorrected poses of two boards that cross). Our validator: **valid, `pushed_residual`
  kept** (the fit ran on the round's `_fit` meshes and `props_gmg.json` with the 1 cm / 3 deg prior and names a
  commit). Decisions unchanged (PUSH both, T0): step 2 (class O) decides before the push test.
- Files: `build/I/results/contract_ep24/` (their export headers, their phys_fit report, our validation and decision
  records, the reference `.prov.json`, sha256 of the exports and the reference parquet kept in the scratchpad).

### 19.2 Tests (T-I1 with the round-1 additions) [M]
Full suite with the final rule code (`<scratch>/interlock/r1fix/full.log`, 23 tests, 3152 s at load 9-14): 20 OK,
1 expected failure (s1 at t = 6 mm, F-I2.14 / F-I3.11), 2 failures that were test expectations, not rule defects,
both corrected and re-run (`rerun.log`): (1) the contract same-rule test without a silhouette (t = 10 mm): the
export path pushes where the tracks path carves at the GAP threshold (F-I3.13; now a logged expected failure; the
silhouette cases t = 10 / 18 mm give the same decisions and tiers on both paths); (2) the two-round test expected A1
to pass, but the export path's voxel carve is partly refilled by our splitter (persistent check-frame intrusion
435.3 -> 403.5 cm3, -7 %), so A1 rejects the round, as it should (F-I3.3); the test now checks that A1 is computed
from the fixed check frames and matches its definition, that A3 is pending without the settle, that the round is
not accepted, that an invalid export is not evaluated, and that round 2 counts round 1's carve in its budget.
New tests that pass: blob generator disagrees (centroid 31.8 mm, axis 89 deg, reverse share 0.03); OFFSET carries
budget (iv); the Embodiment header validates against an independent pose and 10 malformed or wrong variants are
refused without a crash (3 mm fiducial shift, 15 mm pts_local shift, frames out of range, no frame count, no
independent pose, mocap / dataset parquet / library_v3 poses / scan in the chain, no poses.npz); our tracks as the
chain's poses.npz with a table frame and +-2.5 mm vertical snaps validates, other tracks are refused, a 3 mm
re-centring is refused; the pieces gate marks a cup whose hull spans its cavity do-not-use and `load_sim` refuses
it; o2a PUSH; o2b CARVE on both plates, no OFFSET, A's carve within 1.5 mm of the slot end, o_residual_push on A;
n4 sees the 3-frame contact (TRANSIENT run) and carves nothing.

### 19.3 ep31 (sweeper in the rack, eval-30 twin; the orchestrator's priority case) [M]
Eval semantics (the sweeper is IDENTITY_SWAP on public), decisions only (`--no-physics`, 398 s), shells as picks:
sweeper <- rack has one SLIDE run (f18-40, 12 frames, 42.8 mm, straightness 0.55) with a 2-voxel region (IGNORE,
`one_sided_region`); rack <- sweeper has no engaged run. The shells overlap at most 0.32 cm3 along the track
(engaged frames; rack shell 0.0). No silhouette (the two are in contact in all 145 frames). So with our CPU shells
there is nothing to carve or push on ep31; the P34 free-travel test needs a delivered r0 for ep31 (not built in this
round; a rack's pieces will also meet the keep-out gate). ep13 (cup in the rack) was not run.

### 19.4 Still open after round 1
1. **The boards still push.** The motion region (19-25 mm, the partner's evidence thickness plus jitter) is 2-4 times
   the slot (about 6-8 mm in the video [E]); class O dominates whatever the silhouette sees. [H, F-I3.11, not used]
   measure the region against the partner's plate thickness.
2. **Every delivery so far is do-not-use** under the keep-out gate: our splitter reaches 0.72 / 2.0 cm3 per hull on the
   boards (limit 0.3) and fills the containers (up to 1250 cm3); CoACD is worse on the boards (53-77 cm3). B9 needs a
   better splitter (more pieces where the keep-out is, or CoACD pieces re-split against our keep-out).
3. **Independent reference pose for real references:** their perceived references are accepted only when our tracks
   are the chain's `poses.npz`, or when B10 adds the guard role for our reference parquets (`validate(ref_poses=)`).
   Known blind spot: a re-centring along the vertical at f_star (absorbed by the per-object vertical shift).
4. A3 needs their jitter_check settle report; without it no round is accepted.
5. Not run: phys_fit with the real prior to convergence on our pieces (only the plumbing run), ep13, the ep2 / ep11
   re-runs with the new code (their old r0 folders are marked do-not-use), CoACD pieces checked against the keep-out
   on the containers, the P34 free-travel test on ep31.
6. Non-blocking review items left: w_sub is not asserted in the tests (6.0 mm for a 10 mm partner in o2b: the
   voxel-centre extent); offset_asm (a track offset only at the assembled frames) is covered by the column rule for
   the half-thickness pocket but the misplaced slab centre is only caught by the P3 replay.
