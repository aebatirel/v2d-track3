# gmg INTERLOCK stage: slots, seats and cavities that let touching objects fit (design v2, built, round-1 fixes)

Date: 2026-10-31. v1 written at repo commit `de64bd3` and committed as `2eb8397`; this v2 answers the design review of
v1 (blocking items B1-B7 and the non-blocking items; section 16 lists each one and where it is resolved). Branch
`claude/bold-albattani-6qmxsv`. Status: **built** (BI1 code and synthetic tests, section 17; BI2 dev runs on ep24, ep2,
ep11, section 18) and **corrected after the verifier's review of the build** (round-1 fixes, PREREG F-I3, section
19). Outcome so far: on the dev runs the rule pushes every pair (no carve); the Embodiment contract now runs on their
real tool (section 19). **Amended 31 Oct ~16:20 UTC under the owner's waiver of the camera rule** for plate-plate
insertions, simulator copy only (PREREG F-I4, section 20; written and pushed before any run with it); **result (31 Oct
~18:00 UTC): no notch built on public ep24, eval 25 not run, nothing delivered (section 20.9)**. **Round 2 (31 Oct
~18:05 UTC, orchestrator decision): the plate body follows the observed outline (polygon prisms) and t comes from all
points** (PREREG F-I4.15, section 20.10; written and pushed before any run with it). **Round-2 result (31 Oct ~20:15 UTC): both ep24 boards slotted, P2-P7 pass, r0 delivered with P1 pending; not frozen for eval 25 (ep23 board 1 over the prism cap), section 20.11.** **Round-2 report (31 Oct ~21:15 UTC): two verifiers, no blocking item; board 2's slot about 3.5 mm off the observed slot; P1 handed to the Embodiment session; eval 25 not run; open decisions, section 20.12.** **Round 3 (31 Oct ~21:20 UTC, orchestrator decision, post hoc): a simplification ladder for the prism cap, a new synthetic freeze family w10, and slot-centre and coverage reports (PREREG F-I4.16, section 20.13; written and pushed before any run with it).** **Round 3 amended (31 Oct ~22:25 UTC, orchestrator decision 2, post hoc, after determined-wright's P1 and contact-budget results on the round-2 ep24 folder): a contact-budget gate for every delivery, a body of at most three rectangles cut into boxes, and a new freeze (PREREG F-I4.17, section 20.14; written and pushed before any run with it).** **Extended 31 Oct
~17:34 UTC to every pair whose simulator colliders collide persistently** (owner: "if 2 mesh collide we can carve it"; PREREG
F-I5, section 21; written and pushed before any code or run with it). **Collision-carve result and report (31 Oct ~20:57 and ~21:30 UTC): nothing carved or delivered on the five public episodes; eval twins not run (orchestrator); two verifiers: the ring pieces fail the gate on their own and our tracked poses fail the hands-off test even with faithful colliders, sections 21.11-21.12.** **Collision-carve round 2 (31 Oct ~21:50 UTC, orchestrator decision, post hoc): cavity-safe rings, CoACD below the cap, a pose precheck, a faithful reference and a physical delivery floor, then the five 21.10 decisions (PREREG F-I5.15, section 21.13; written and pushed before any code or run with it).** This file adds a stage to the frozen gmg design
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

**Your waiver (31 Oct ~16:00 UTC, section 20).** For two flat boards that slide into each other, "the cameras saw
wood there" no longer blocks the slot in the simulator copy. The simulator boards become thin plates at their own
measured thickness. The slot is drawn from measurements: width = the other board's thickness + 2 mm, centred where
it passes, deep enough to meet the other slot. Every other check stays, and the physics tests must pass. Submitted
meshes, cups, the pot and the lid are unchanged. This was written down (PREREG F-I4) before anything was run with it.
**Result (31 Oct ~18:00 UTC, section 20.9): no notch was built.** On public ep24 both boards are still pushed: the
first run found no plate on either board, and after one dated post-hoc fix the rectangle plate body failed, because the
boards are I-shaped (wider ends). Eval 25 was not run and nothing new was delivered. The next step is a plate body that
follows the outline, a new rule that you or the orchestrator decide on.

**Your extended waiver (31 Oct, section 21).** "if 2 mesh collide we can carve it": any pair whose simulator shapes
overlap again and again along our tracks may be carved (cups, pot and lid, cup or pot in the rack, sweeper), simulator
copy only. First every object gets pieces that keep its cavity empty (rings for cups, a finer CoACD with a repair, or
exact boxes); then the receiving object is cut by the other object's own pieces where they persistently go, with a
clearance computed from the slope it rests on (about 0.1 mm on a cup wall, so the inner cup cannot sink the way the
widened eval-10 cup did). A carve is delivered only if, among other tests, the guest stays within 4 mm and 5 degrees of
its tracked pose with the hands off. The pose correction that would remove the overlap instead is computed and shown,
not used to block. Written down (PREREG F-I5) before any code or run.
**Result on the public episodes (31 Oct ~20:57 UTC, section 21.11): nothing carved or delivered, and the copies these
runs wrote must not be used.** The step that builds hollow-keeping pieces failed on all ten real objects and fell back
to 6 mm boxes keeping 2-9 % of each object; on those pieces every hands-off test fails by 8-127 mm. The piece builder
needs a decision before any carve can be judged (21.11).
**Verified (31 Oct ~21:30 UTC, section 21.12).** Fixing the piece builder alone would not be enough: at the frames
tested our tracked poses are themselves impossible (the ep11 cups overlap by half a cup, a cup sits 15-23 mm inside the
table, the sweeper floats 45 mm above it), so even 2 mm copies of our shapes fail the hands-off test; and the ring
pieces fail the hollowness test on their own. The eval episodes were not run. Round 2 (F-I5.15) comes next, public
episodes first.
**Round 2, written down (31 Oct ~22:02 UTC, section 21.13, PREREG F-I5.15; before any code or run).** Ring pieces
whose faces cannot enter the cup's opening, with as much wall as the piece cap allows (room for 16 slices on a 20 cm
cup);
CoACD asked for half the cap so its repair can split; a check of every test frame for impossible poses (guest inside
the table, floating, or overlapping in a way no carve may fix), which go to the pose lanes; and a do-not-use marker on
any copy that keeps less than half of a shape or fails the hands-off test where faithful shapes pass it (round-1
copies included). Expected: the cup and pot pieces pass, the rack episodes stay do-not-use, no public carve. A true
cup-in-cup nest is tested on synthetic cups only; eval 10 is the only real one.

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

## 20. Board slot under the owner's waiver of the camera rule (31 Oct, PREREG F-I4; written before any run with it)

**In plain words.** You waived the camera rule ("Okay I waive that camera rule", 31 Oct ~16:00 UTC). Until now the
rule refused to cut the boards' slot because stereo paints wood across a gap of about 6-8 mm [E], and the RGB check
could not confirm it (a hand in the way on board 1; on board 2 the colour check called the slot wood). Under the
waiver, for two flat boards that slide into each other, "the cameras saw wood there" no longer stops the cut.
Everything else still has to hold: the other board must really pass through that place, again and again, along a
straight path; a small pose correction (up to 1 cm) must not be able to explain the overlap; the cut must stay small
(10 % of the board, at most 0.6 of its width); both boards are cut or neither; and the cut copy must pass the physics
checks. The change applies to the simulator copy only. The board meshes we submit for scoring are not touched. Cups,
the pot, the lid and every other object keep the old rule.

Two other changes come with it, both measured problems of sections 18-19:
- **The simulator board becomes a thin flat plate at its own measured thickness.** Today it is the stereo shell,
  which is thicker than the board and carries the marker bumps. That made the slot too wide (21.7 mm, against
  12.6 mm for the partner's evidence across the crossing), and our convex pieces could not stay out of the empty
  space around it (0.72 / 2.0 cm3 per piece; the limit is 0.3).
- **The slot is drawn from measurements, not from the band the other board's stereo points sweep.** That band is
  19-25 mm wide, two to four times the slot. Width = the other board's plate thickness + 2 mm. Centre = the middle of
  the place it passes through. Depth = from the edge it enters to where it stops + 2 mm. A check confirms that the two
  slots together span the crossing.

### 20.1 Scope (F-I4.0)
| | in scope (waiver applies) | outside (F-I1 to F-I3 unchanged) |
|---|---|---|
| objects | both targets plate-like (20.2) | any target not plate-like: cups, pot, lid, rack, sweeper, dust pan, spoon |
| run kind | INSERTION on both linked components (travel >= 20 mm, straightness >= 0.7) | SEAT, REST, SLIDE, TRANSIENT |
| class O, silhouette | no longer block the carve (step 2, step 4 (iii), column rule F-I3.12, "class O never carved") | as before |
| kept gates | engaged runs, persistence, sweep (partner moves through), push test > 10 mm, budget (iv) and topology, both-or-neither, identity / track gate, physics P2-P7, keep-out gate; P1 by the Embodiment | as before |
| destination | simulator copy only (tier T1, `owner_waiver_fi4`) | as before |
| submitted mesh | unchanged (no ICARVE / FUSE-I from the waiver) | as before |

If a pair in scope fails a kept gate, it gets the old decision (PUSH, or OFFSET as before) and the record names the
gate (`waiver_gate_fail:<gate>`).

### 20.2 Plate-like, thickness and the simulator body (F-I4.1, F-I4.2)
- **Plate-like** = the existing structure test (`structure.py`, build step B7) finds a plane pair: two parallel faces
  seen from opposite sides with material between them, 3-25 mm apart, footprints overlapping by at least half. It runs
  on the object's own points in the clean bundle within 6 mm of its pick (the clean grid of board 1 holds points
  125 mm away in frames ~72-240 [M, 18.1]). The pair with the largest overlap gives the **plate thickness t** and the
  mid plane. Seen before writing this [M, dev, B7]: ep24 board 1 7.4 mm; ep23 board 2 11.6 mm (and a 4.4 mm pair);
  no plane pair on any cup, the pot, the lid, the rack, the sweeper, the pitcher or the dust pan. Clean ep24 values:
  not known yet.
- **Body.** A STRUCT plate candidate if one exists (none for ep24 today: only `shell_t5p36` and `hull` [M]),
  otherwise the board's outline seen in our points (2 mm cells with points from at least 3 frames, closed, holes
  filled, largest piece), replaced by its minimum-area rectangle (it must fill at least 90 % of it) and extruded to t
  about the mid plane. No marker balls in this case (`plate_body_no_markers`). The visual GLB stays the submitted
  mesh.

### 20.3 The slot (F-I4.3, F-I4.4)
In the target's own frame, with a_L its long axis, a_W its width axis and a_T its normal:
- **width** along a_L = t of the partner + 2 x 1 mm clearance;
- **centre** along a_L = the centroid of the target's motion region (the place the partner passes through, every
  voxel counted once);
- **from** 3 mm outside the entry edge (the edge on the side the partner comes from) **to** depth D = P + 2 mm, where
  P is how deep the partner's points reach into the target's region after the pre-registered split. When the split
  applies, P is capped at the split plane;
- **through** the full thickness (t + 3 mm on each side).

Why the split plane decides the depth: each board's stereo also paints wood across its own slot, so in the data the
partner seems to pass through the whole width of the board (the regions span 131 / 128 mm [M]). The data constrain
only the sum of the two depths. The pre-registered split plane (through the centroid of both regions at the assembled
pose) divides it. Each depth is therefore a prior [E], and the **cross-lap check** tests the sum: D_1 + D_2 must lie
within 10 mm of W_x, the width of the crossing (the overlap of the two unslotted plates along the insertion direction
at the assembled pose). Otherwise both boards are pushed (`interlock_slot_inconsistent`). Budget: the slot is at most
10 % of the plate's volume and reaches at most 0.6 of its width; the slotted plate stays one piece without a hole.

### 20.4 Pieces and acceptance (F-I4.5 to F-I4.7)
- **Pieces:** three boxes per board (the solid part and the two prongs beside the slot) and one piece per marker
  ball if the body has balls. Each box is exactly a part of the body and covers no space outside it, so the keep-out
  limit (0.3 cm3 per piece) is met by construction. The gate still runs. No splitter, no CoACD.
- **Acceptance, thresholds unchanged:** P2 free travel <= max(4 mm, default + 1 mm); P3 replay over 16 jittered
  copies: lag <= 0.5 cm and <= 5 deg at assembly, never > 1 cm after it, no NaN copy, collider overlap < 1 cm3 (this
  pre-registered clause was missing from the code and is restored); P4 removal <= 1.5 x the slot and >= 90 % kept;
  P5 <= 165 shapes; P6 no new overlap (+0.1 cm3); P7 held-out overlap at most half the default's. The default is the
  same plate without the slot. P1 (the hands-free settle in FlashCHORD) stays with the Embodiment session's
  jitter_check on the delivered folder.
- **What we expect [H]:** P2 will be loose across the slot and along the insertion. The unslotted plates already
  overlap at the crossing, so the default "travel" there is just the search cap. The slot's clearance (2 mm) is fixed
  by construction, so P3 (does the cross close, and within 5 deg) and P7 (do held-out frames improve) are the tests
  that can fail. The motion-band DIAG slot closed to 0.33 cm but stayed 9.4 deg off, so P3 is the test to watch.

### 20.5 What is delivered (F-I4.8)
Only the simulator copy, as a new round folder in the Embodiment layout (`<obj>/<obj>.glb` = the unchanged submitted
mesh, `<obj>/piece_XX.obj` = the slotted plate pieces, `_fit/`, `props_gmg.json` with the 0.3 kg placeholder,
`manifest.json` with an `owner_waiver` block and `p1_pending: true`, `sources/`, and the unslotted plate under
`_default/`). It is offered only if every test except P1 passes. Their jitter_check then decides P1; no pack uses the
folder before it passes. This changes F-I2.12 (which kept carved pieces in `_carved_pending_p1/`) for this route
only, because their P1 tool reads a round folder. A failing run still writes its folder, with `DO_NOT_USE.json`
naming the test, for the record. The submitted (CD-O) board mesh is unchanged.

### 20.6 Run plan and cost (after this section and F-I4 are committed and pushed)
1. Build (new code paths, F-I3 stays the default): `platebody.py`; the `--waiver-fi4` branch in `interlock.py` and
   `tools/interlock_dev.py`; the P3 overlap clause in `simphys.py`; T-I1 additions w1-w5 (F-I4.10). Then run w1-w5
   and the existing suite with the waiver off (w2).
2. **T-I11**, clean ep24, eval semantics, the same inputs as `r1evalsem` (INTERLOCK 19.1) but without `--gen` and
   without the per-candidate physcheck: `GMG_MODE=dev GMG_RUN=<run> python -m gmg.tools.interlock_dev --run <run> --ep
   24 --bundle <scratch>/gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep24 --cands <run>/cand/public/ep24 --pick
   wooden_piece_1=shell_t5p36,wooden_piece_2=shell_t5p36 --video <scratch>/data/store/ep24_a.mp4 --calib
   <scratch>/data/calib.json --hands <run>/in/hands24/hands.npz --proxy-copies 16 --identity eval --waiver-fi4 --tag
   fi4evalsem` (run `20261031-i2probe-626ce13`; the code commit recorded in `build/I.md`).
3. Cost [E]: CPU only, on this container's 4 shared cores, one run at a time. The plane test is about 4-7 min per
   board (B7 took 257-394 s for all hypotheses), decisions about 5-15 min, P3 about 1 s per copy x 16 x 3 variants
   [M, 18.1], P2/P4/P6/P7 a few minutes: about 20-40 min for T-I11, and 15-30 min for the tests. No rental.
4. Report: P35-P38 as written (F-I4.10), with numbers, failures included. P39 (ep2, ep11 controls) only if run.

### 20.7 Limits and risks (stated before the run)
- The split between the two depths is a prior, not a measurement (20.3); the consistency check guards only the sum.
- The plane test can find no pair on the clean bundle (one face seen too little): then the pair is out of scope
  (P35 fails) and the boards stay pushed. It can also take a wrong pair (ep23 board 2 also had a 4.4 mm pair; the
  rule takes the larger overlap): then t is wrong, which P35's 5-10 mm range and the physics tests may show.
- The rectangle body ignores rounded corners and the marker balls. The visual GLB (the shell) is thicker than the
  collision plate.
- P1 at the assembled frame may be uninformative: the cross is held in the air there, and both boards dropped about
  2 cm with the hands parked in the plain-MuJoCo pre-check, slot or no slot [M, 18.1].
- On public ep24 the identity flags (IDENTITY_SWAP on both boards) still make (c) absent: the public-semantics
  decision stays IGNORE. T-I11 runs with eval semantics, as in sections 18-19. Eval 25 runs later with its own
  reference and the identical code.

### 20.8 Outcome on public ep24 (T-I11, 31 Oct; PREREG F-I4.14 outcomes) [M]
- First run (tag fi4evalsem, 16:51-16:58 UTC): no plane pair on either board (F-I4.1) -> out of scope, both PUSH.
  Diagnosis: board 1's faces are both seen but its 9 mm inlier band (sigma 3.0 mm) merges them into one plane; board 2
  is seen from one side only.
- F-I4.14 (post hoc, pushed dad65a1 before the re-run): camera-side face pair, else a one-face plate with the partner's
  thickness (same-stock prior [E]).
- Re-run (tag fi4b, 17:15-17:30 UTC): both boards plate-like (board 1 t = 6.21 mm measured; board 2 t := 6.21 mm prior),
  in scope, sweep and push gates pass, then the outline body fails on both (rectangle fill 0.895 / 0.868 < 0.9: the
  outline flares about 9 mm per side at the ends of the long axis). Both boards stay PUSH; no slot was built, no
  physics ran on a slot, nothing is delivered under F-I4. Results: `build/I/results/slot-ep24/`, outline masks
  `build/I/png/ep24_fi4b_outline_*.png`.
- Verification (`build/I/verify_slot_0.md`, `verify_slot_1.md`, 31 Oct 17:41-17:55 UTC) and record correction
  (PREREG F-I4.14, correction bullet; no rule changed): no notch confirmed. The outline "flares" are the boards' real
  I-shape (ends about 7-11 mm wider than the 125-130 mm waist, over up to 22 mm at each end), not marker balls. The 2-98 % rectangle
  idea is withdrawn (it cuts off wood); a full-width rectangle holds 22.9 / 19.5 cm3 of FREE space. A body that follows
  the outline needs a new dated post-hoc F-I4 entry (owner / orchestrator decision). Board 1's t is 6.21 mm on the
  2 mm downsample and 7.3-7.4 mm on all points. Eval 25 was not run under F-I4: the public twin has no accepted slot.

### 20.9 Result of the board-slot workflow: what is delivered and what is open (31 Oct ~18:00 UTC)
**For the owner ("Did we managed to get these faster notch?"): no.** No notch (slot) was built, physics-tested or
delivered, on public ep24 or on eval 25 [M]. Under the waiver both ep24 boards are still PUSH in both runs. Eval 25 was
not run, because the public twin has no accepted slot and the next fix is a rule change (item 1 below).

**Results** [M] (public ep24, dev, eval semantics, clean bundle `20261031-b4ext4-b61e8aa`, run
`20261031-i2probe-626ce13`, this container, CPU; commands in `build/I.md`):

| run (UTC) | code | wall | plate test | first failing gate | decision (board 1 / board 2) |
|---|---|---|---|---|---|
| fi4evalsem, 16:51-16:58 | cd2383f | 455 s | F-I4.1: no plane pair on either board (board 1: the 9 mm band at sigma 3.0 mm merges both faces; board 2: one face seen) | out of scope | PUSH T0 / PUSH T0, `interlock_disagree` |
| fi4b, 17:15-17:30 | 9ad1af9 | 914 s | F-I4.14: board 1 step 2, t = 6.21 mm; board 2 step 3, t := 6.21 mm (partner prior) | F-I4.2 outline body, fill 0.895 / 0.868 < 0.9 | PUSH T0 / PUSH T0, `interlock_disagree` |

- Kept gates that passed in fi4b before the failure: INSERTION 122.3 / 127.7 mm (straightness 0.91 / 0.92), sweep
  1.0 / 1.0, push 19.0 / 22.0 mm (> 10).
- Why F-I4.2 failed (`verify_slot_1.md` B1): the boards are I-shaped. The waist is 130 / 125 mm wide, the ends 137 /
  136 mm, over 16-22 mm at each end. Inside the 2-98 % box the outline fills 0.996 / 0.983. A waist-width rectangle cuts
  off wood; a full-width rectangle puts 22.9 / 19.5 cm3 in space the cameras saw as empty (keep-out would fail [E]).
  The gate failed for a real reason.
- Board 1's t: 6.21 mm on the 2 mm downsample the run used, 7.3-7.4 mm on all 1.76 M points [M]. Its two faces were seen
  in separate frame ranges (0-74 and 74-274).
- Physics: none on a slot. Synthetic only: w5 lag 0.033 cm / 0.16 deg; w7 (one-face partner) carves both boards,
  widths 12.17 mm, keep-out 0.0. The DIAG slot (motion band, never delivered) closed the cross to 0.33 cm / 9.4 deg
  against 1.85 cm / 113 deg for the default pieces.
- Tests: T-I1 Waiver + Controls with the F-I4.14 code: OK, 14 tests, 3 expected failures (t = 6 mm width; w6 reads
  8.07 / 8.39 mm for a true 10 mm, so the F-I4.14 falsifier fired; w6b, one cell at t = 18 mm, sigma 1 mm). The ep11
  cups control (`verify_slot_0.md`) gives identical decisions with the waiver off and on.
- Predictions: P35 failed (run 1), P36 failed (F-I4.2), P37 and P38 not tested, P39 holds for ep11 (ep2 not run), P40
  holds but is not independent (written after the diagnosis that measured the faces).
- Cost: CPU on this container's 4 shared cores, no rental, $0. About 50 min of runs in all [E, sum of the logged
  times: 455 + 914 s for T-I11, 1081 + 250 s for the tests, 127 s for the verifier's control, plus the 16:38-16:50
  tests].

**What is delivered.** Nothing new, to the Embodiment session or to the pack.
- ep24: `<scratch>/gmg/runs-dev/20261031-i2probe-626ce13/sim/public/ep24-fi4b/r0` is the old route's folder again: 32
  default pieces per board, `interlock.delivered = default`, carved 0 / 0 cm3, `DO_NOT_USE.json` (F-I3.8: ours 0.72 /
  2.0 cm3 per hull, CoACD 52.9 / 77.3 cm3). Its pieces, `props_gmg.json` (sha256 `0166d4e4...`, 0.3 kg placeholder)
  and fiducials are byte-identical to those of `ep24-r1evalsem/r0` and `ep24-fi4evalsem/r0` [M, manifest hashes]. Only
  the code block (now with `platebody.py`) and the decision records (`carve.json`, `sources/`, with a `waiver_fi4`
  block holding the plate test and the failed gate) differ. There is no `owner_waiver` block, no `p1_pending` and no
  `_default/`: nothing for their jitter_check. `code.commit` reads 42ab815 (the HEAD when the manifest was written);
  the code that ran is 9ad1af9 (the sha256 of the gmg files match).
- eval 25: no folder. The packed eval-25 simulator keeps `meshes/carve/ev25` (library_v3-based, another session's).
  There is no GT-free replacement yet. When there is one, its pieces differ from `meshes/carve/ev25` in width, depth,
  centre and split, so using them needs an eval-25 rollout re-run, not a pack-only swap.
- In git: PREREG F-I4, F-I4.12, F-I4.13, F-I4.14 (with outcomes and the correction bullet); sections 20-20.9; the code
  (`platebody.py`, the `--waiver-fi4` branch, off by default) at 9ad1af9; tests w1-w7; `build/I/results/slot-ep24/`;
  `build/I/verify_slot_0.md` and `verify_slot_1.md`. The submitted board meshes are unchanged.

**Open items** (none started; item 1 needs the owner or the orchestrator):
1. **Plate body rule.** A body that follows the outline (for example a waist box plus two end boxes, fitted to the
   edges or eroded, because the 2 mm raster grows the body: 238.4 x 133.4 mm for a true 230 x 125 in w1) would be a new
   dated post-hoc entry F-I4.15. It should state the forking path (F-I4.12, F-I4.14 and this one each followed an
   outcome), accept or narrow F-I4.14's wider plate-like test (steps 2-3; board 2's t is a prior, not a measurement),
   choose the thickness estimator (all points or the downsample), be checked on another public plate episode first
   (ep23, dev) and be frozen before eval 25. **Answered 31 Oct ~18:05 UTC by the orchestrator's decision: PREREG F-I4.15,
   section 20.10.**
2. **Synthetic tilt case.** Board 1's partner crosses 1.74 deg off its slot axis in plane; 1 mm clearance per side over
   60-75 mm of depth tolerates about 1.5-1.9 deg [E]. Add a w-case at 2-3 deg before the next real run.
3. **Eval-25 inputs.** There is no gmg eval bundle for ep25 yet (gmg extraction plus the HF eval depth cache). The local
   ep25 `poses.npz` (sha256 `e95ccaef...`) is the frozen evperc track from before the ev25idfix naming (identity swapped),
   so the mapping of our boards to the packed reference's boards must be checked per board before any slot run.
4. **Default plate pieces** fail keep-out on both boards (above). The planned fix is F-I5's cavity-preserving route
   (plates get the F-I4 boxes, section 21.2); not run yet.
5. **Records** (no outcome changes): the P3 overlap clause now applies to every pair, waiver or not (it restores
   F-I1.8, but it is a global change of the default path); the waiver CARVE branch does not reset `submitted` (not
   exercised); manifests stamp the HEAD at write time, not the launch commit; 20.3 and the `platebody.py` docstring still
   name the motion centroid as the slot centre (F-I4.12 changed it); the rest of the existing T-I1 suite was not re-run
   with the waiver off (Controls and Waiver were).

### 20.10 Round 2: a body that follows the board's outline (PREREG F-I4.15; written before any run with it)
**In plain words.** The first round stopped because the simulator board had to be a rectangle, and the boards are
not rectangles: they are I-shaped, with ends about 7-11 mm wider than the middle [M, `verify_slot_1.md` B1]. A
rectangle as wide as the ends puts about 20 cm3 of wood where the cameras saw empty space; a rectangle as narrow as the
middle cuts the ends off. The orchestrator decided (31 Oct ~18:05 UTC) on four changes:
- The simulator board becomes the **outline we see**: a polygon traced from our points, smoothed by at most 1 mm, at
  the board's thickness.
- It is cut into **flat convex pieces** (prisms). The slot is cut out of the polygon before the pieces are made.
- The **thickness** is measured on all our points, not on a thinned-out sample. The thinned sample read 6.2 mm on
  board 1, all points read 7.3-7.4 mm, and a synthetic test showed the old estimate reading thin.
- Before the rule is used on eval 25 it is run once more on ep24 (slot and physics), and on a second public episode
  with the boards (ep23: plate test and body only).

Everything else stays as in sections 20.1-20.7: the waiver's scope, the kept gates, the slot's width (the other board's
thickness + 2 mm), its centre (F-I4.12), its depth, the cross-lap check, the budget, the physics tests and the
delivery.

**What changes, by step** (PREREG F-I4.15.1-F-I4.15.4):

| step | F-I4 to F-I4.14 (round 1) | F-I4.15 (round 2) |
|---|---|---|
| plate test | plane pair, else camera-side pair, else one face (on the 2 mm downsample) | unchanged |
| thickness t, mid plane | from the test that passed, on the downsample | the camera-side face estimator on all owned points within 6 mm of the pick; a one-face board takes the partner's t (unchanged prior) |
| body | min-area rectangle of the outline at t, must fill >= 0.9 | the outline polygon at t: same 2 mm cells and rules, laid along the rectangle's axes, outer ring simplified by Douglas-Peucker at 1.0 mm, must be a simple polygon; no balls |
| rectangle | the body | the frame only (axes, centre, edge used to open the slot box); fill reported |
| slot depth D | from the rectangle's edge | from the polygon's edge at the slot's mouth (the waist); the slot bottom's position is unchanged |
| W_x, budget, topology | on boxes | on the polygon prisms (same thresholds) |
| pieces | three boxes | convex prisms: the polygon minus the slot, ear-clipped and merged by Hertel-Mehlhorn; at most floor(165 / objects) per body; <= 64 vertices each |
| keep-out gate | decides | decides, unchanged |

Why the slot's depth is measured from the waist: the cross-lap check compares the two depths with the crossing width
of the two bodies, which for polygon bodies is set by the waists. Measured from the rectangle edges, the two depths
would grow by about 15 mm in sum on ep24 [E], more than the 10 mm window.

**A point about the keep-out gate [R, code read].** The gate takes the seen-empty points (and the slot) that lie
outside all the pieces and counts how many fall inside each piece. That catches a convex piece bulging past the shape
it stands for. Pieces that tile the body exactly have no bulge, so they always pass (0.0 cm3), whether or not the body
itself reaches into space the cameras saw as empty. So the gate checks the pieces, not the body. The body's fit is the
**FREE share** (the share of the body in voxels the cameras saw as empty). It is reported, compared with the rectangle
body, and tested by prediction P53; it is not a gate. The earlier statement that a full-width rectangle "would fail the
keep-out gate" ([E], gate not run) does not follow from the code.

**New constants** (PREREG F-I4.15.9):

| name | value | origin |
|---|---|---|
| outline simplification (Douglas-Peucker) | 1.0 mm | generic: half the 2 mm raster pitch; the decision's example value |
| prisms per body | floor(165 / objects in the episode), 82 on ep24 | informed: the P5 cap of 165 shapes (F-I1.14), as F-I5.4 |
| vertices per prism | <= 64 (<= 32 per polygon part) | informed: MuJoCo limit (F-I1.14) |
| prediction thresholds (4 mm I-shape, 1/3 of the rectangle's FREE share, 16 prisms, 6.8-8.0 mm, 2.5 deg) | as stated | set now for predictions only; they decide nothing |
| fill share 0.9 | dropped | went with the rectangle body (fill still reported) |

Every other constant is reused unchanged (2 mm raster, >= 3 frames per cell, t / 2 + 3 sigma slab, 6 mm filter,
3-25 mm window, 2 x 1 mm clearance, 2 mm depth margin, 3 mm extensions, 10 mm consistency, 10 % / 0.6 budget, 0.3 cm3
keep-out, the F-I1.14 acceptance thresholds).

**Run order and the freeze** (PREREG F-I4.15.6):
1. Build in `platebody.py`; synthetic tests w1-w7 re-run, plus w6c (thickness on all points), w8 / w8b (an I-shaped
   cross at sigma 1 / 3 mm), w9 (the partner tilted 2.5 deg, open item 2 of 20.9), and the full T-I1 suite with the
   waiver off.
2. ep24, tag `fi4o`: the fi4b command with a new tag; slot, pieces, keep-out, P2-P7 on 16 copies; launch commit
   recorded.
3. ep23 (public, dev): plate test and body only, both boards, from the v6 bundle `20261031-b4ext6-90c8cce` (its v4
   board-1 crop was clipped, fixed in B4 round 2), picks `shell_t5p36` built the same way as ep24's. Board 2's track is
   the wrong board: reported, not adopted.
4. **Frozen for eval 25 only if** ep24 builds the slot on both boards and passes every test except P1 (P52), **and**
   ep23 board 1 is plate-like with a body built without a gate failure. Otherwise the round stops and reports; nothing is
   tuned; eval 25 is not run under F-I4.15. Synthetic misses and other falsified predictions are reported and do not
   stop the round.
5. Eval 25 afterwards needs the ep25 gmg bundle and the per-board check of how our board labels map to the packed
   reference (open item 3 of 20.9).

**Predictions** (PREREG F-I4.15.8; P41-P50 belong to F-I5):

| | prediction | falsified if | label |
|---|---|---|---|
| P51 | ep24: the slotted pieces of both boards pass keep-out (<= 0.3 cm3 per piece) | any piece over | [H], near-certain by construction (tests the tiling, not the body) |
| P52 | ep24: both boards CARVE (cross-lap within 10 mm, budget, topology) and P2-P7 pass on 16 copies (P3 <= 0.5 cm, <= 5 deg, overlap < 1 cm3) | any gate pushes or any test fails | [H]; reported as P52a / P52b |
| P53 | ep24: the polygon is I-shaped (ends >= 4 mm wider than the waist) and its FREE share is <= 1/3 of the rectangle body's | either fails | [H]; the I-shape part is not independent; [E] 1-4 % absolute |
| P54 | ep24 board 1: t (all points) in 6.8-8.0 mm; board 2 takes it | outside | not independent (verify_slot_1: 7.30-7.40 mm) |
| P55 | synthetic: w6c within 1 mm in all 6 cells; w8, w8b pass; w1-w5, w7 as before | any miss | [H] |
| P56 | synthetic w9 (2.5 deg tilt): P3 passes | P3 fails | [H]; [E] overlap <= 0.1 cm3 |
| P57 | ep23 board 1: plate-like, t in 5-10 mm, body built, I-shaped, FREE share <= 1/3 of its rectangle's | any fails | [H]; board 2 reported only |
| P58 | ep24: <= 16 prisms per slotted body | more | [H] |

**Limits and risks (stated before any run).**
- Each F-I4 change so far (F-I4.12, F-I4.14, F-I4.15) followed an outcome and made the route more permissive. This one
  follows the measured cause (the shape), was decided by the orchestrator, and is checked on ep23 before eval 25.
- The outline still grows the body by about 4 mm per side (synthetic w1 [M]); it is not eroded. P53 measures what that
  costs in seen-empty space.
- The slot's depths remain priors split by the split plane (20.3); the cross-lap check guards only their sum.
- Board 2's thickness is still the same-stock prior, not a measurement.
- An aligned slot with 1 mm clearance is at the limit of the replayed crossing angle on board 1 (about 1.7 deg in
  plane; verify_slot_1 B3). w9 probes it; P3 decides on ep24.
- On ep23 only board 1 can count; if board 1 is a one-face plate, its t comes from the wrong-board track and is
  reported only.
- Cost [E]: CPU on this container, about 1.5-2 h of runs in all; one self-destroying Vast CPU box only if the
  container cannot make progress (cap $5). Expected spend $0-1.

### 20.11 Round 2 result: slot built and delivered on ep24 (P1 pending); not frozen for eval 25 (31 Oct ~20:15 UTC) [M]
**In plain words.** With the outline body (F-I4.15) the simulator boards of public ep24 now carry a slot. Both boards
CARVE, every physics test we run passes, and the simulator folder is delivered with "P1 pending": the Embodiment
session's settle test (jitter_check --k 16) still has to pass on it before any pack uses it. The rule is **not frozen
for eval 25**: on the second public episode (ep23) board 1's outline is so ragged that its prisms exceed the per-body
cap (85 > 82), so the pre-registered freeze condition fails. Eval 25 is not run under F-I4.15.

| | board 1 (wooden_piece_1) | board 2 (wooden_piece_2) |
|---|---|---|
| decision (F-I3 before) | CARVE T1 (PUSH) | CARVE T1 (PUSH) |
| plate test, t | step 2; 6.21 mm downsample -> **7.40 mm all points** | step 3 one face; t := 7.40 mm (prior) |
| polygon | 86 vertices, 298.0 cm2; waist 130 / ends 137 mm | 126 vertices, 287.2 cm2; waist 126 / ends 136 mm |
| FREE share, polygon vs rectangle | 4.1 % vs 12.9 % | 1.9 % vs 10.3 % |
| slot w / D (polygon edge) / c_L | 9.40 / 67.55 / 3.97 mm | 9.40 / 66.56 / 1.36 mm |
| prisms default / slotted (cap 82) | 50 / 57 | 71 / 77 |
| keep-out per hull | 0.0 cm3 | 0.0 cm3 |

Pair: cross-lap D sum 134.11 vs W_x 128.23 mm (5.88 mm, window 10); budget 2.1 % / 2.0 %, reach 0.44 / 0.46. Physics
(16 jittered copies, P_sel = P_sim fallback): P3 carved lag **0.078 cm / 0.74 deg** (default 2.81 cm / 104 deg), overlap
0.04 cm3; P2, P4-P7 pass; 134 shapes <= 165. Delivered: `build/I/results/slot2-ep24/fi4o/r0` (also in the run folder),
`carved_p1_pending`; PNGs `build/I/results/slot2-ep24/fi4o/ep24_fi415_wooden_piece_{1,2}.png` (the red slot box sits on
the slot visible in our RGB frames; corrected in 20.12 item 1: board 1 only).

ep23 (body only): board 1 one-face plate with t = 10.8 mm borrowed from board 2's (wrong-board) track; outline partial
(PNG `build/I/results/slot2-ep23/`), 140 vertices, 85 prisms > 82 -> no body. Synthetic: w1-w6, w6c, w9 pass (the t = 6
mm width miss of round 1 is gone); w7, w8, w8b fail at the same prism cap. Cause [M]: the 1 mm simplification keeps every
2 mm raster step of a noisy edge, and each step adds about one prism.

Open (decisions for the owner / orchestrator, not taken here):
1. A prism-count fix (coarser tolerance or a rectilinear outline fit) needs a new dated entry, then ep23 again, before
   eval 25 can use this route.
2. P1 on the delivered ep24 folder (Embodiment `jitter_check --k 16`).
3. As before: an ep25 gmg bundle and the per-board P_sel -> P_sim mapping (20.9 item 3).
4. The step-1 plane pair can come out tilted (synthetic w8 B: 3.4 deg, t 5.1 mm) and F-I4.15.1 keeps its normal; the
   body then leans out of the board (21.8 % FREE). Not seen on ep24 (step 2 and step 3 there).

### 20.12 Round 2 report: verification, record corrections, hand-offs, open decisions (31 Oct ~21:15 UTC)
**In plain words.** Public ep24 now has a simulator copy of both boards with a slot. It passes every physics test we
run on our own tracks (P2-P7). It goes to the Embodiment session for the settle test (P1); no pack may use it before
that passes. Eval 25 has no slot: the rule did not freeze (on ep23, board 1 needs more convex pieces than the cap
allows), so eval 25 was not run and the pack keeps `meshes/carve/ev25`. Two independent verifiers found no blocking
problem. One finding matters for P1: board 2's slot sits about 3.5 mm off the slot we see in our own frames, because the
slot follows our tracked pose at assembly. With poses closer to the true assembly it may collide by more than its 1 mm
clearance. The submitted board meshes are unchanged.

**Accuracy, failures and cost** [M unless marked]:

| item | result |
|---|---|
| ep24 fi4o (code 19c4309, 2613 s) | both boards CARVE; t 7.40 mm (all points); 57 / 77 slotted prisms; P2-P7 pass on 16 copies (P3 0.078 cm / 0.74 deg vs default 2.81 cm / 104 deg) |
| ep23 body check (v6 bundle, 156 s) | board 1 one face, partial outline, 85 prisms > cap 82: no body; freeze condition (b) fails |
| F-I4.15 synthetic suite (4964 s + 211 s re-run) | w1-w6, w6c, w9 pass; w7, w8, w8b fail at the prism cap |
| waiver-off T-I1 suite (3951 s, at 7402553) | 24 tests OK, 2 expected failures |
| predictions | P51 (by construction), P52a, P52b, P53, P54 (not independent), P56 hold; P55, P57, P58 fail |
| verification | `build/I/verify_slot2_0.md` (V0, rule compliance) and `verify_slot2_1.md` (V1, geometry and physics): no blocking item |
| eval 25 | not run (F-I4.15.6 step 5); no ep25 output; `meshes/carve/ev25` not read |
| cost | this container's 4 shared CPU cores, no rental, $0; about 3.3 h of run and test wall time, partly in parallel [E, sum of the logged times], plus two verifier passes |

**Confirmed by the verifiers** [M]: F-I4.15 was pushed at 18:14:58, before any F-I4.15 code (18:24:30) or run; every run
used one byte-identical `platebody.py` (sha256 `a1ca8960...`); the rule text was not edited after any outcome; the code
does what the rule says (one laxer synthetic threshold, item 10); no ground truth was read; the delivered pieces are
exact convex right prisms at t = 7.401 mm that tile the polygon, with the rule's slot width, centre and depth within
the 0.25 mm check raster; P3 re-run on the delivered files gives 0.079 cm / 0.74 deg (a fresh seed 0.060 cm / 0.33
deg); no observed material lies outside the body; board 1's slot lies on the real slot (looked at, RGB frames); the
prism counts reproduce (ep24 50 / 57 and 71 / 77, ep23 85 and 56).

**Corrections and caveats to 20.11 and the PREREG F-I4.15 outcomes** (no decision changes). For P1 and the next rule:
1. **Board 2's slot is about 3.5 mm off the real slot** (V1 N1, [M + looked at]). The real gap spans u = -6..+1.5 mm
   (centre about -2 mm); the analytic footprint spans -3.34..+6.06 mm (c_L 1.36). It covers about two thirds of the
   real gap plus about 4.5 mm of real wood. Cause: our tracked relative pose at assembly (board 1's observed face lands
   about 3.7 mm inside board 2's wood), on which F-I4.12 centres the slot. On our tracks the replay is consistent, so P3
   passes. 20.11's "the red slot box sits on the slot visible in our RGB frames" holds for board 1 only. [H] On P1's
   reference poses, or on eval 25, the offset exceeds the 1 mm clearance; falsifier: the Embodiment's jitter_check
   passes on r0.
2. **The CARVE rests on F-I4.15.3** (V0 N1, [M]). Measured from the rectangle edge, the depth sum is 144.11 mm (diff
   15.88 mm > 10): `interlock_slot_inconsistent`, PUSH. The polygon-edge reading was pre-registered at 18:14 but chosen
   with the ep24 geometry known: the fourth outcome-informed step in the F-I4 chain (F-I4.12, F-I4.14, F-I4.15, and
   this reading).
3. **Board 2's D = 66.56 mm is set by a 2-4 mm polygon spike at the slot mouth** (V1 N2). Beside it, D2 is about 55-59
   mm [E] and W_x is likely inflated the same way; the 10 mm window decision is unlikely to change [E]. One spike sets
   u_e (the outermost polygon coordinate in the band). The slot removes the spike except for a 0.38 mm sliver prism.
4. **"Keep-out 0.0 cm3" is the gate's measure, and it is tautological for an exact tiling** (F-I4.15.4; V1 N3).
   Seen-empty (FREE) volume inside the delivered slotted hulls: 8.11 / 3.99 cm3 (3.7 / 1.9 %), 88-89 % of it within
   4 mm of the polygon edge (the raster growth); 10 of 134 hulls hold more than 0.3 cm3 (max 0.745). No gate tests
   this; making the FREE share a gate needs a new decision.
5. **P3's overlap clause is a median** (V1 N4): 0.04 cm3 over the assembled frames. Per frame (0.25 mm grid) the
   delivered pieces give 0.40-1.04 cm3 at f218-234 and f238, max 1.044, 2 frames over 1.0, beside the slot walls where
   the partner normal is 2.2-3.1 deg off a_L. It passes as pre-registered.
6. **Sliver prisms** (V1 N5): slotted pieces narrower than 2 mm: 21 of 57 (narrowest 1.41 mm) and 27 of 77 (0.39 mm);
   length / width up to 172. [H] They may add contact noise in a settle; falsifier: P1 passes on r0, or a variant with
   merged slivers settles no better.
7. **ep23 board 1 is a partial outline, not only a cap miss** (V1 N6): 206 cm2 against 287-298 cm2 for the same-stock
   ep24 boards (fill 0.742); it misses the part under the hand. A cap-only fix would still omit about 30 % of the board
   [E].
8. **ep23 cannot be the independent freeze check of a prism-count fix** (V0 N2): the fix would be chosen after seeing
   its count (85 against 82).

Record only (no outcome effect):
9. Run order (V0 N3): T-I1 (18:38:09) and T-I11 fi4o (18:38:27) ran in parallel, not tests first as F-I4.15.6 / .7 say;
   the waiver-off suite ran after fi4o; ep23 ran in parallel. The code was frozen at 19c4309.
10. `test_fi415.w_checks` flags keep-out only above 0.3 cm3, where F-I4.15.7 w8 says 0.0 (V0 N4). It decided nothing:
    w8 and w8b stopped at the cap first.
11. w6c's sigma-3 cells change only the declared sigma (the points keep 1 mm noise), so they test which reference plane
    is chosen, not robustness to 3 mm noise (V0 N9).
12. F-I5 interface (V0 N8, [R]): at REV 15 `plate_info` runs the all-point estimator and can turn a plate into not
    plate-like (`t_all_points_fail`); `collcarve.object_routes` uses it, so F-I4.15 does reach F-I5. No such case in the
    committed results.
13. Constants (V0 N7, [R]): shapes_max 165 and part_vmax 32 (informed, F-I4.15.9) bypass `guard.constant`, so they are
    missing from the run manifest's constants list.
14. Code identity (V0 N5, V1 N7): report.json `launch_code` is taken after the bundle stage. Its commit field reads
    3484d8d and its collcarve.py / cavpieces.py hashes are 3484d8d's; its platebody / interlock / simphys / simpieces /
    driver hashes equal 19c4309's (the F-I4 path that ran). The r0 `manifest.json` code block reads 7402553 with the
    cbed3cb interlock.py hash (written at 19:21); the process had loaded the pre-cbed3cb file. The committed
    `ep23_fi415.json` is the 19:11 re-run (code identity 3053a78, same content as the first run). The waiver-off suite
    ran at 7402553, the w8 / w8b re-run at 212d2a1 plus the harness fix later committed as bf6d7f6. The F-I4.15
    `platebody.py` first entered git in the WIP snapshots 8f72399 / caefcb4 (18:28-18:29), byte-identical to what ran;
    6ed88f1 carried only the w_checks guard (the build log said otherwise).
15. Diagnostics not in the log (V0 N6): `<scratch>/fi415/t_geom.py` (18:24), `dbg_b.py` (18:35, the w8 B tilt
    finding), `t_hm.py` (18:36), `probe_w7.py` (19:27). None changed code.
16. Not in clones: `r0/sources/*.npz` (gitignored) is only in the scratch run folder
    `<scratch>/gmg/runs-dev/20261031-i2probe-626ce13/sim/public/ep24-fi4o/r0` (otherwise identical to the committed
    copy, `diff -rq` 21:08). P4's Monte Carlo default volume for board 1 is 226.9 cm3 against an exact 220.525 cm3
    (harmless, V1 N7).

**Hand-offs** (relayed by the orchestrator; texts in the work log of 31 Oct ~21:15 UTC):
- **Embodiment session (determined-wright): P1 on the ep24 folder.** Folder
  `build/I/results/slot2-ep24/fi4o/r0` (`manifest.json` sha256 `271f9899...`, `carved_p1_pending`, `p1_pending: true`,
  no `DO_NOT_USE.json`): slotted pieces at the top level (57 / 77), unslotted `_default/` (50 / 71), `_fit/<obj>.glb`,
  `props_gmg.json` (0.3 kg placeholder). Their `jitter_check --k 16` decides P1; a fail marks the folder do-not-use
  (F-I4.8). Caveats: items 1 and 6.
- **Pack builder (focused-pascal): eval 25.** No GT-free eval-25 slot exists; keep `meshes/carve/ev25`. A future slot
  differs from it in width, depth, centre and split, so using it needs an eval-25 rollout re-run, not a pack-only
  swap. We have not read `meshes/carve/ev25` and will not compare against it before our own eval-25 slot exists.

**Open decisions** (owner / orchestrator; none taken here):
1. A new dated F-I4 entry for the prism count: its tolerance or fit method stated before any run (from a generic
   argument or the w7 / w8 shapes), with a fresh condition (b): an untouched public plate episode or a pre-written
   synthetic family.
2. Whether that entry also targets ep23's partial outline (item 7) and the tilted step-1 plane pair (20.11 item 4).
3. Whether to add an observed-notch consistency check on c_L (item 1) [H]; falsifier: board 2's c_L moves onto the
   observed gap (about -2 mm) and P3 still passes on our tracks.
4. Whether the body's FREE share becomes a gate (item 4).
5. P1 on r0 (Embodiment). A fail marks the folder do-not-use and changes nothing else.
6. The ep25 gmg bundle and the per-board mapping of our tracks to the packed reference (20.9 item 3) need no F-I4 rule
   and can be scheduled now.
7. Eval 25 then needs the frozen rule, a run with physics, the P1 report and, on the pack side, an eval-25 rollout
   re-run before any use.

Status (31 Oct 21:37 UTC): open decisions 1-3 are answered by the orchestrator's decision of ~21:20 UTC, PREREG
F-I4.16 (section 20.13): 1 by the simplification ladder and the synthetic freeze family w10; 2 by a coverage report
without a gate (the tilted step-1 plane pair is not addressed); 3 by a report-only slot-centre check (the slot is not
moved). Decision 4 (a FREE-share gate) was not taken.

### 20.13 Round 3: a simplification ladder for the piece cap, and a new freeze check (PREREG F-I4.16; written before any run with it)
**In plain words.** Round 2 gave public ep24 a slotted simulator copy of both boards, but the rule did not freeze for
eval 25: on ep23 one board needed 85 convex pieces where at most 82 are allowed, and three synthetic cases missed the
same limit. The cause is measured: we trace the board's outline on a 2 mm grid and smooth it by only 1 mm, so every
one-cell step of a noisy edge stays, and each step costs about one piece. The orchestrator decided (31 Oct ~21:20
UTC, after seeing these counts) on four changes:
- **Smooth more only when needed.** The outline is smoothed by 1.0 mm as before; if the pieces exceed the limit, by
  1.5, 2.0, 3.0 and then 4.0 mm, and the first that fits is used. 4 mm (two grid cells) is the most the outline may
  move. Nothing else about the body, the slot, the checks or the physics changes.
- **A new freeze check.** ep23 was used up as a check (we have seen its count). In its place: a new family of synthetic
  board pairs, written down here before any run, with the ep24 board shape, three thicknesses and three levels of edge
  noise. All nine must be slotted correctly under the limit, and one of them must also pass the physics tests. ep24
  must still carve and pass; if the old 1 mm smoothing fits there, its pieces must be exactly the round-2 pieces.
- **Two warnings in the record, no change to the slot:** where a board is seen from one side only, we compare the slot
  with the notch we can see from below and flag it if they differ by more than 1 mm (on ep24 board 2 the verifier saw
  about 3.5 mm); on eval 25 we also place the pieces at the poses the pack's simulator replays and report how much
  the boards overlap.
- **A coverage figure:** how much of the board's frame (and of its partner's area) the traced outline covers. ep23
  board 1 covers only about 74 %, because a hand hid part of it. Reported, not gated.

Eval 25 is run under this rule only if ep24 and the nine synthetic cases pass. The submitted board meshes are not
touched.

**What changes** (PREREG F-I4.16.1-F-I4.16.5):

| step | F-I4.15 (round 2) | F-I4.16 (round 3) |
|---|---|---|
| outline simplification | Douglas-Peucker 1.0 mm; over the cap: no body | rungs 1.0, 1.5, 2.0, 3.0, 4.0 mm, per board; the smallest whose ring is simple and whose slotted (and default) prisms fit the cap; none fits: no body (`plate_body_over_cap`) |
| order in a pair | body, default cap, slot, cross-lap, budget, slotted cap | body raster, slot footprint (rectangle frame, polygon-independent), ladder, then u_e, D, W_x, cross-lap, budget, keep-out on the chosen polygon |
| freeze condition (b) | ep23 board 1 body built | synthetic w10: 9 cells all carve correctly, one passes physics |
| freeze condition (a) | ep24 carves, P2-P7 pass | the same, and at rung 1.0 the pieces are byte-identical to round 2 |
| slot centre | not checked | report on one-face boards: observed notch vs c_L; flag if off by > 1 mm |
| eval 25 poses | - | P_sel -> P_sim overlap at the assembled frames; flag if the median > 0.3 cm3 |
| outline coverage | fill only | polygon / frame and polygon / partner (same stock); report only |

**Evidence it rests on** [M, round-2 records, Douglas-Peucker 1.0 mm, cap 82]:

| case | vertices | reflex | default prisms | slotted prisms |
|---|---|---|---|---|
| ep24 board 1 / 2 | 86 / 126 | 41 / 61 | 50 / 71 | 57 / 77 |
| ep23 board 1 (board 2: wrong-board track) | 140 (102) | 68 (49) | **85** (56) | - |
| w7 A / B | 64 / 184 | 30 / 90 | 32 / **111** | - |
| w8 A / B | 112 / 116 | 54 / 56 | 68 / 70 | 72 / **83** |
| w8b A / B | 138 / 134 | 67 / 65 | 75 / 75 | **90** / **84** |

About 1.1-1.3 prisms per reflex vertex in every case. No count at any other tolerance has been computed, so what the
ladder does is not known yet.

**Prior work checked (short review, 31 Oct)** [R]:
- Douglas and Peucker (1973, The Canadian Cartographer / Cartographica 10(2)): the method we keep. Its tolerance is a
  distance, so it can be tied to the 2 mm grid; it can produce a self-crossing ring, which we test for.
- Visvalingam and Whyatt (1993, The Cartographic Journal 30(1)): removes the points that span the smallest triangles.
  Its threshold is an area, with no direct distance bound; not chosen.
- Hertel and Mehlhorn (1983, FCT, LNCS 158): the convex partition we keep (at most 4 x the optimum). The number of
  pieces follows the number of reflex corners that survive smoothing, so smoothing is the lever.
- Lien and Amato, approximate convex decomposition of polygons (SoCG 2004; journal 2006): pieces may keep a small
  concavity (tau). With tau = 2 mm it is the named alternative for a later round. Not now, because its pieces bulge
  past the board by up to tau, which our keep-out argument does not allow without a new gate.

**The synthetic freeze family w10** (PREREG F-I4.16.2; new seeds 4161-4471, none used before):

| item | value |
|---|---|
| boards | two identical I-shaped plates, 230 mm long, 125 mm waist, 137 mm ends over 20 mm (6 mm per side, as ep24), crossing at mid-length (the T-I1 cross: 10 separated, 60 insertion, 30 assembled frames, 0.2 deg / 0.5 mm pose jitter, cameras on both sides) |
| cells | t = 6, 8, 10 mm x in-plane edge noise sigma_e = 1, 2, 3 mm (normal noise 1 mm, declared sigma 1 mm): 9 cells |
| pass (all nine) | both boards carve through the waiver route, both piece sets <= 82, keep-out <= 0.3 cm3 per piece, slot width within 1 mm of t + 2 mm |
| physics cell | t 8 / sigma_e 2: P2-P7 on 16 jittered copies (P3 <= 0.5 cm, <= 5 deg, overlap < 1 cm3) |
| w10p (report only) | the physics cell with 30 % of one board hidden under a hand-shaped blob (palm plus four fingers over the slot-side edge, scaled to 30 % of the board; as ep23) |
| w10n (report only, added by this entry) | t 8 with real isotropic 3 mm noise and declared 3 mm (tests the plate test and t, which the other cells do not) |
| also reported | w7, w8, w8b re-run; w1 at t = 10 must stay identical (code check) |

**Freeze for eval 25** (PREREG F-I4.16.3):
- (a) ep24 (tag `fi4p`): both boards carve and P2-P7 pass. If rung 1.0 fits both (expected: 57 / 77 <= 82), every
  piece file must be byte-identical to round-2 r0 and the round-2 physics stands; a byte difference fails (a). If
  another rung is chosen, physics is re-run.
- (b) w10 as above.
- If either fails, the round stops and reports; nothing is tuned; eval 25 is not run under F-I4.16. ep23, w10p, w10n,
  w7, w8, w8b and the two reports never decide the freeze.

**Slot-centre report** (one-face boards only; PREREG F-I4.16.4): from our own points before the partner arrives, the
points seen deeper than the board's mid plane inside the slot's depth band (the notch seen from above) give a profile
across the slot; its half-peak centre is compared with the slot centre c_L. If they differ by more than 1 mm (the slot's
clearance per side) and at least 100 points support it, the round folder carries `slot_centre_disagrees`. The slot is
not moved: the simulator replays our tracks, and the slot must agree with them. On eval 25 the delivered pieces are
also placed at the packed reference poses (our own submitted eval-25 prediction) at the assembled frames, and the
overlap is reported (`p_sim_overlap` if its median exceeds 0.3 cm3).

**New constants** (PREREG F-I4.16.8):

| name | value | origin |
|---|---|---|
| ladder rungs | 1.0, 1.5, 2.0, 3.0, 4.0 mm, smallest fitting first | generic in argument (half a cell, one cell, two cells of the 2 mm grid; 4 mm bounds the outline's move), post hoc in timing (after the 1.0 mm counts) |
| w10 shape, thicknesses, noise | as above | ep24's shape in round numbers; the decision's t and sigma_e; fixture otherwise |
| w10p occlusion | 30 % | ep23 board 1: 28-31 % missing against the same-stock ep24 boards [M] |
| slot-centre flag | 1 mm, >= 100 points, 8 mm band trim, +-30 mm window | the slot's clearance; the verifier's method; report only |
| P_sim overlap flag | median > 0.3 cm3 | the keep-out level per piece; report only |

Every other constant of F-I4.15 is unchanged (2 mm raster, cap floor(165 / objects), 2 x 1 mm clearance, 2 mm depth
margin, 10 mm cross-lap window, 10 % / 0.6 budget, 0.3 cm3 keep-out, the acceptance thresholds).

**Run order and cost** (PREREG F-I4.16.6): build `platebody.py` REV 16 and `tests/test_fi416.py`; then the w10 tests and
ep24 `fi4p` (in parallel; the code is frozen first and the freeze is decided after both); ep23 report; the freeze
decision; eval 25 only if frozen (ep25 bundle and per-board mapping from the parallel Prep25 step, physics with the
packed reference, `meshes/carve/ev25` read only after our r0 is written). Cost [E]: CPU; about 1 h build, 0.5-1 h of
tests, 11 min for ep24 to the pieces, 1-2 h for eval 25 with physics. On this container or one self-destroying Vast CPU
box if that is faster end to end (cap $3 for the round, ledger mesh-bold). Expected spend $0-1.

**Predictions** (PREREG F-I4.16.7; P51-P58 are F-I4.15's):

| | prediction | falsified if | label |
|---|---|---|---|
| P59 | ep24: rung 1.0 on both boards, pieces byte-identical to round 2 | another rung or a byte difference | not independent (counts known); tests the code |
| P60 | w10: all nine cells carve correctly under the cap | any cell misses | [H] |
| P61 | w10 t 8 / sigma_e 2: P2-P7 pass | any fails | [H]; [E] P3 0.05-0.3 cm |
| P62 | w10: rung 1.0-1.5 mm at sigma_e = 1, <= 3.0 mm everywhere | a sigma_e = 1 cell needs >= 2.0, or any needs 4.0 or nothing fits | [H] |
| P63 | w10: the I-shape survives (end - waist within 3 mm of 12), D from the waist edge, outline moved <= eps | any fails | [H]; the last part by construction |
| P64 | w7, w8, w8b fit a rung and carve both (report) | no rung or a push | [H] |
| P65 | w10p: body built, both carve, coverage 0.65-0.75 of the partner (report) | otherwise | [H]; if it holds, a 30 %-hidden board is carved: no coverage gate |
| P66 | w10n: plate-like, t within 1 mm, both carve (report) | otherwise | [H] |
| P67 | ep23 board 1: a rung fits, coverage 0.70-0.78 of its frame, <= 0.75 of board 2 (report) | otherwise | not independent |
| P68 | ep24 board 2: notch observable, flagged, slot centre off by -6..-2 mm | otherwise | not independent (verify_slot2_1 N1) |
| P69 | eval 25 (if frozen): both carve, P2-P7 pass with the packed reference | a push or a failed test | [H], low confidence |
| P70 | eval 25 (if frozen): P_sim overlap median <= 0.3 cm3 | > 0.3 cm3 | [H], low confidence |

**Limits and risks (stated before any run).**
- This is the fifth outcome-informed step in the F-I4 chain (F-I4.12, F-I4.14, F-I4.15, the polygon-edge depth
  reading, this one), each more permissive. The ladder's bound is generic (two grid cells), but it was chosen after the
  1.0 mm counts were seen. The freeze check is new synthetic data, not a real episode: no untouched public plate
  episode remains.
- A coarser rung can smooth away real detail up to its eps: the ep24 I-shape steps are 3.5-5 mm per side, so a 4 mm
  rung could fill in a waist recess. Reported per rung, not gated.
- The partial outline (ep23, w10p) is not gated: a board with 30 % of its outline hidden can be carved, and its
  simulator copy then lacks that part of the board.
- Board 2 of ep24 keeps its slot about 3.5 mm from the observed notch; the report flags it, the geometry stays (it is
  consistent with our tracks, on which the simulator replays).
- w10's normal noise is 1 mm in all nine cells; real 3 mm normal noise (ep24 board 1's sigma) is tested only by the
  report-only w10n.
- The tilted step-1 plane pair (20.11 item 4) and a FREE-share gate (20.12 open decision 4) are not addressed.

Status (31 Oct 22:42 UTC): superseded for delivery by PREREG F-I4.17 (section 20.14). The round-2 ep24 folder failed
P1 at determined-wright's reference and overflows the sim=rl contact limits; it is marked do-not-use (26b8c6b). Of
the F-I4.16 runs launched at 22:14, the ep24 `fi4p` run and the w10 physics cell were stopped by the orchestrator
at 22:17 (no results); the geometric w10 cells finished (files written 22:19) and Identity was still running at
22:31. Their records are F-I4.16 records, reported only; they were not read before F-I4.17 was pushed.

### 20.14 Round 3, amended: a contact budget for every delivery, and a body of a few boxes (PREREG F-I4.17; written before any run with it)
**In plain words.** The Embodiment session (determined-wright) tested the round-2 ep24 boards in the training
simulator's own settings and found two things [M, theirs]:
- **The settle test (P1) fails, but not because of the slot.** Their reference pose holds the assembled cross about
  3 cm above the table, so both boards fall, with or without the slot. Lowered to 1 mm above the table, the slotted
  boards pass every settle criterion, and the unslotted ones tip over (host tilt about 16-19 deg).
- **The slotted boards are too expensive for the simulator.** Each board was 57-77 small prisms. In the training and
  evaluation settings a scene may hold at most 256 contacts and 512 solver rows per simulated world. The slotted
  scene needed 500-670 contacts and about 2000 rows. Contacts were dropped and the boards fell through the table in
  all 16 copies. The evaluator uses the same limits, so these pieces cannot be delivered.

In the full eval-25 scene (two hands, both boards, support), the packed configuration uses at most 276 of the 512 rows
per world [M, theirs]. The hands and the support take about half.

The orchestrator decided (31 Oct, after these results, post hoc):
- **A contact-budget check for every delivery.** In our own plain-MuJoCo settle scene (both boards and the table, with
  the training limits), no copy may exceed the limits. The slotted boards may also cost at most twice the solver rows
  of a control that is one plain box per board. In the full eval scene with both hands, measured with
  determined-wright's tool, the rows must stay at or below 380 per world (about 75 % of 512). That tool does not run
  here, so they run it before any delivery counts as usable.
- **A body of a few boxes instead of many prisms.** Each board's outline is fitted with at most three rectangles
  aligned with the board: a waist, plus up to two wider ends (the I-shape). The fit must cover the traced outline with
  an overlap score (IoU) of at least 0.90; otherwise the round-3 polygon is the fallback and must pass the same budget.
  The slot is cut exactly as before. The rest is cut into boxes, about 5 per slotted board and 3 per plain board.
- **A new freeze for eval 25.** The nine synthetic w10 cases must slot correctly with the box body, and one must pass
  the physics and contact tests. ep24 must slot with the box body and pass the physics and contact tests.
- **Delivery.** The new ep24 folder goes to determined-wright for the settle test at their pose and at the lowered pose,
  and for the contact check in their simulator.

The round-2 ep24 folder is marked do-not-use. The submitted board meshes are not touched.

**What changes** (PREREG F-I4.17.1-F-I4.17.4):

| step | F-I4.16 (round 3 as written) | F-I4.17 (round 3 amended) |
|---|---|---|
| delivered body | outline polygon, smoothed 1.0-4.0 mm, convex prisms (50-90 per board seen) | union of <= 3 frame-aligned rectangles (waist + ends) fitted by IoU to the outline raster, cut into boxes (expected 5 slotted, 3 plain) |
| fallback | none | IoU < 0.90: the F-I4.16 polygon, which must pass the contact gate |
| slot | rectangle-frame footprint; D from the polygon edge at the mouth | the same footprint; D from the rectangle edge at the mouth |
| contact budget | not checked | part 1 (here, decides): no overflow of 256 contacts / 512 rows in any of 16 copies in two settle starts, and rows <= 2.0 x a one-box-per-board control; part 2 (determined-wright's budget.py, full eval scene with hands): rows <= 380 per world before the folder is usable |
| freeze (a) | ep24 carves, P2-P7 (byte identity at rung 1.0) | ep24 carves with the box body on both boards, P2-P7 and part 1 pass |
| freeze (b) | w10: 9 cells carve, k5 physics | w10: 9 cells carve with the box body (IoU >= 0.90), k5 physics and part 1 |
| polygon, ladder | delivered | reported only |

**Evidence** [M, determined-wright, commits 3c7fd32 and 9c1d100 on their branch; read, not re-run]:

| item | carved (round-2 r0, 57 / 77 prisms) | default (50 / 71 prisms) |
|---|---|---|
| P1 at their reference (f246, 16 copies, large buffers) | FAIL: drift 3.71 / 3.23 cm, tilt 3.1 / 2.0 deg | FAIL: drift 3.18 / 3.20 cm, tilt 13.1 / 7.7 deg |
| P1 lowered to 1 mm (diagnostic) | all criteria pass: 0.79 / 0.38 cm, 3.0 / 2.2 deg, sink -4.8 mm | tilt fails: 15.9 / 5.7 deg |
| sim=rl buffers (256 contacts / 512 rows), 16 copies | overflow in 16 / 16; guest ends 10-46 cm below the table | no overflow; results unchanged |
| max rows per world, large buffers (f246 / f258 / f270) | 2027 / 453 / 770 | 416 / 435 / 366 |
| eval-25 full scene, packed pieces (8 resets x 60 zero-action steps) | max 65 contacts, max 276 / median 201 rows; board-board 14, support-board 11-12, hand pairs up to 21 | (library_v3 boards without pieces: 56 contacts, 240 rows) |

**The contact-budget gate** (PREREG F-I4.17.1):
- **Limits**, from the sim=rl file (`cfg_sim_rl.yaml`, sha256 `695536b7...`; FlashCHORD's `configs/sim/rl.yaml` is not
  on this machine): njmax 512 rows per world, nconmax 256 contacts per world (pooled across worlds in MuJoCo-Warp),
  20 fps x 5 substeps, Newton, pyramidal cone, implicitfast, 100 / 50 iterations, impratio 20.
- **Part 1** (plain MuJoCo, here): the settle scene of our P1 pre-check (table and both boards free), started at the
  middle and at the first assembled frame (f246 and f218 on ep24), 16 jittered copies of 2 s, with the sim=rl options.
  Per copy, the maximum contacts and rows over all steps. Plain MuJoCo does not stop at the limits (it only grows its
  memory), so they are applied to the counts. Pass: no copy above 256 contacts or 512 rows, and the slotted pieces'
  maximum rows <= 2.0 x those of one plain box per board in the same scene. Fail: do-not-use. The unslotted pieces'
  numbers are reported too. Synthetic pairs get a table 1 mm under the cross.
- **Validity check of part 1:** it is run once on the round-2 prisms, which overflowed in MuJoCo-Warp. If plain MuJoCo
  does not flag them, part 1 is recorded as weaker than the real simulator, and part 2 carries the evidence.
- **Part 2** (determined-wright's budget.py, 9c1d100): our pieces are built into their full scene (both hands,
  support, ground) through `make_assets --pieces` and a copy of the reference with remapped object paths, 8 training
  resets x 60 zero-action steps. Pass: at most 380 rows per world. This machine has neither their simulator source
  nor its libraries, so this part is expected to go to determined-wright; until it is measured the folder carries
  `contact_budget_pending`. Caveat on every number: zero-action rollouts; a grasping policy may add contacts.
- **Docs checked** [R]: in MuJoCo a contact with condim 3 costs 4 solver rows under the pyramidal cone (3 elliptic);
  general convex colliders return one contact, multi-contact up to 4 more; box-plane up to 4. In MuJoCo-Warp the
  contact limit is pooled over worlds, the row limit is strict per world, and an overflow is undefined behaviour;
  box-box and mesh-mesh go through the convex pipeline (up to 4 contacts per pair; the special box-box collider up to
  8). So the cost grows with the number of touching piece pairs, not with their size: fewer, larger pieces is the
  lever. Our boxes still reach the simulator as mesh hulls.

**The low-piece body** (PREREG F-I4.17.2):

| item | rule |
|---|---|
| input | the outline raster of round 2 (2 mm cells along the board's frame) |
| shapes | waist rectangle over the full length; up to two end rectangles, each wider than the waist and at most a third of the length; no symmetry imposed |
| fit | maximise IoU on the cells: the waist alone (every row pair), then each end (every length and row pair), then the waist again, until nothing changes (<= 10 passes); ties to fewer rectangles, then smaller area |
| gate | IoU >= 0.90, else the F-I4.16 polygon (flag `low_piece_iou_fail`), which must pass the contact gate |
| slot | footprint unchanged; D from the rectangle edge at the slot's mouth; cross-lap, budget and topology as before |
| pieces | the slotted outline cut into boxes by slabs in both directions, the one with fewer boxes; exact tiling; an I with a waist slot gives 5 boxes, the minimum for that shape (Eppstein 2010); plain: 3 |
| reported | IoU, missed and added area, FREE share (box body, polygon, rectangle), box sizes (slivers), the polygon ladder |

**Freeze for eval 25** (PREREG F-I4.17.3):
- (a) ep24 (tag `fi4q`, physics on): both boards carve with the box body on both, P2-P7 pass on 16 copies, part 1
  passes.
- (b) w10 (round-3 fixtures unchanged): all nine cells carve with the box body (IoU >= 0.90), keep-out <= 0.3 cm3 per
  piece, slot width within 1 mm of t + 2 mm; cell k5 (t 8 mm, edge noise 2 mm) passes P2-P7 and part 1.
- Not inputs: part 2 (a delivery condition), w10p, w10n, w7, w8, w8b, ep23, the polygon reports, the slot-centre and
  coverage reports. Eval 25 is also not started if ep24's part 2 has been measured and failed.
- If either fails, the round stops and reports; nothing is tuned; eval 25 is not run under F-I4.17.

**Run order and cost** (PREREG F-I4.17.6): build REV 17 and `tests/test_fi417.py`; code checks (REV 16 reproduced, the
fit on exact masks, the box tiling, the counter); the part-1 validity check on the round-2 prisms; the w10 tests and
ep24 `fi4q` (in parallel; the freeze is decided after both); ep23 report; freeze decision; the ep24 folder to
determined-wright (P1 at their pose and at the lowered pose, sim=rl contact check, part 2); eval 25 only if frozen.
Cost [E]: CPU, a few hours of wall time in all; on this container or one self-destroying Vast CPU box (cap $3 for the
round, ledger mesh-bold). Expected spend $0-1.

**New constants** (PREREG F-I4.17.8):

| name | value | origin |
|---|---|---|
| contact / row limits | 256 contacts, 512 rows per world | sim=rl (training and evaluator configuration) |
| count scene | settle at the middle and first assembled frame, 16 copies, 2 s, sim=rl options | this entry's reading of the decision; copies and settle length reused |
| ratio to the control | 2.0 x one plain box per board | decision (hands and other objects share the scene) |
| absolute bound | 380 rows per world in the full eval scene | decision: about 75 % of 512, from the measured 276 / 201 |
| rectangles | at most 3 (waist + two ends); ends contain the waist and are <= 1/3 of the length | decision; containment and 1/3: this entry |
| IoU gate | 0.90 | decision |
| synthetic table | 1 mm under the cross, gravity along the insertion direction | this entry (the lowered diagnostic's 1 mm) |

**Predictions** (PREREG F-I4.17.7; numbered from P120, because the concurrent collision-carve entry F-I5.16 starts at
P93):

| | prediction | falsified if | label |
|---|---|---|---|
| P120 | ep24: three rectangles per board, IoU 0.93-0.99 | IoU < 0.93 or fewer rectangles | not independent (I-shape known) |
| P121 | ep24: both carve with 5 slotted and 3 plain boxes per board | a push, a fallback, other counts | [H] |
| P122 | ep24: P2-P7 pass; P3 lag <= 0.3 cm and <= 3 deg | any fails | [H] |
| P123 | ep24: part 1 passes (no overflow, ratio <= 2.0) | overflow or ratio > 2.0 | [H], low confidence: [E] ratio 1.5-3.5 |
| P124 | ep24: the plain boxes' rows lie between the control's and the slotted boxes' | outside | [H] |
| P125 | part 1 flags the round-2 prisms | not flagged | [H]; if false, part 2 carries the evidence |
| P126 | ep24 part 2: <= 380 rows per world | > 380 | [H]; [E] 200-320 |
| P127 | w10: the geometric freeze part holds in all nine cells | any cell misses | [H] |
| P128 | w10: IoU >= 0.93 everywhere, not rising with edge noise | otherwise | [H] |
| P129 | w10 k5: P2-P7 and part 1 pass | any fails | [H], low confidence (as P123) |
| P130 | w10p: the 30 %-hidden board falls back to the polygon (IoU < 0.90) | IoU >= 0.90 | [H] |
| P131 | w10n: plate-like, t within 1 mm, IoU >= 0.90, both carve | otherwise | [H] |
| P132 | w7, w8, w8b: IoU >= 0.90 and both carve | otherwise | [H] |
| P133 | ep23 board 1: IoU < 0.90 (partial outline), polygon fallback | IoU >= 0.90 | not independent |
| P134 | w1 t 10 mm: one rectangle, IoU >= 0.95, 3 slotted and 1 plain box | otherwise | [H] |
| P135 | eval 25 (if frozen): both carve with the box body, P2-P7 and part 1 pass | otherwise | [H], low confidence |
| P136 | eval 25 (if frozen): part 2 <= 380 rows | > 380 | [H]; [E] 220-320 |
| P137 | eval 25 (if frozen): P_sel -> P_sim median overlap <= 0.3 cm3 | > 0.3 cm3 | [H], low confidence |

**Limits and risks (stated before any run).**
- This is the sixth outcome-informed step in the F-I4 chain. It is the first that adds a gate. The body change follows
  a measured failure of the delivered pieces in the evaluator's settings, not an outcome of our own slot tests.
- The ratio clause (2.0 x one box per board) may fail even for boxes [E, P123]. A one-box control forms one
  board-board pair, while a slotted cross touches at several slot walls and bottoms. If it fails, the round stops and
  reports; the decision's threshold is not changed after the fact.
- Plain MuJoCo is not MuJoCo-Warp: contacts per pair and the broad phase differ, so part 1 can undercount. The
  validity check on the round-2 prisms tests this once, and part 2 (their tool, their scene) is the binding absolute
  number.
- Part 2 depends on determined-wright: until they run it, no new folder is usable. Zero-action rollouts; a grasping
  policy adds hand-board contacts.
- A three-rectangle body cannot follow a partial or irregular outline (ep23, w10p). There the polygon fallback must
  pass the budget, which its 50-90 prisms are unlikely to do [E]. Such boards are then not delivered.
- The rectangles inherit the outline raster's growth (about 4 mm per side, w1) and the slot-centre caveat of ep24 board
  2 (about 3.5 mm off the observed notch). Both are reported, not corrected.
- P1 at determined-wright's reference fails for reasons outside the slot (the 3 cm hover). Until their reference sits
  on the table, P1 cannot separate a good slot from a bad one; the lowered-pose run is the informative one.

## 21. Collision carve for every colliding pair (owner's extended waiver, 31 Oct; PREREG F-I5; written before any code or run with it)

**In plain words.** You extended the waiver ("but like we said it doesnt have to be a board it can be a cup of what
ever like if 2 mesh collide we can carve it", 31 Oct; recorded at 17:13 UTC). So any two objects whose simulator
shapes overlap again and again along our tracks may now be carved, not only the boards: a cup stacked in a cup, a lid
on the pot, a cup or pot in the rack, the sweeper in the rack or the dust pan. "The cameras saw material there" no
longer stops the cut, and neither does "a small pose correction would also remove the overlap"; we still compute that
correction and show it to you, because on eval 10 it explains most of the cup overlap. The boards keep their own route
(section 20). Submitted (scored) meshes are not touched.

Three things make this different from October's carves, which let guests sink or fall through:
- **Pieces that keep a cup empty.** Today our simulator pieces fill the inside of a cup or pot (ep11 cups: 453 / 793 cm3
  of pieces for 172 / 170 cm3 of cup; ep2 pot: 2776 cm3 for 362 cm3 [M]), and CoACD does the same. A cup cannot nest
  in a filled cup whatever we carve. So every object first gets pieces that keep cavities empty: cups and other round
  containers as rings of wall pieces around their own measured profile (16 slices around, bands up the side, a base,
  and no gap between wall and base: the 1 mm empty ring found in October's eval-10 pieces cannot happen); other shapes
  with a finer CoACD plus a repair step, or, as a last resort, exact boxes.
- **The cut is the other object's shape where it actually goes.** We cut the receiving object (the one the other is
  lowered into) by the other object's simulator pieces, placed at every frame in which the overlap persists, with a
  small clearance. Frames in which our track pushes the guest deeper than where it finally rests are not cut, so the
  pocket is never deeper than the resting place.
- **The clearance is small where the guest leans on a slope.** A cup wall tapers by about 3 degrees. One millimetre of
  extra room on such a wall lets the inner cup drop about 19 mm before it touches again; that is exactly how the
  widened eval-10 cavity failed (the inner cup sank about 11-12 mm with the hands off [M, focused-pascal]). The
  clearance is therefore computed from the slope of the guest's own surface: about 0.1 mm on a cup wall, 1 mm on a flat
  seat such as a lid rim.

Every carved pair must then pass physical tests, the main new one being the failure you saw on eval 10: **with the
hands off, the guest must stay within 4 mm and 5 degrees of where our track puts it** (16 slightly shaken copies). If
any test fails, the uncarved pieces are delivered and the numbers are reported. The order of the runs is public ep11
(cups), ep2 (pot and lid), ep12 and ep13 (cup and rack), ep31 (sweeper and rack), the boards from the board-slot runs,
then the eval twins 10, 1, 14 and 30. CPU only.

### 21.1 Scope (F-I5.0-F-I5.2)
| | F-I5 (flag `--waiver-fi5`) | unchanged |
|---|---|---|
| pairs | every pair whose colliders interpenetrate persistently, any object, any engaged run except TRANSIENT | plate pairs (both plate-like): F-I4 |
| what no longer blocks or replaces a carve | class O; the silhouette (failing, absent, or seeing wood) and the GAP width; OFFSET; the push test | |
| gates kept | engaged runs, build / check hold-out, persistence max(5, 25 %), sweep share >= 50 % of OBSERVED voxels at max(8 mm, 3 j), identity / track gate, caps, acceptance, pieces gate | |
| changed clause | the sweep's run kind: any non-TRANSIENT engaged run (SEAT included), not only INSERTION / SLIDE | |
| reported only | rigid-shift alternative, one-sidedness, the F-I1 to F-I3 decision of the same pair | |
| destination | simulator copy only (tier T1, `owner_waiver_fi5`) | submitted meshes |

Why the run-kind clause changes: the owner names seated and stacked objects; the sweep share still demands that the
other object moves through the place, so a partner resting with a pose error (the same few points entering, F-I1.3
(i)) is still not carved. Intrusion is now measured **between simulator colliders** (the partner's pieces sampled on a
2 mm grid inside the target's pieces), on our tracks exactly as on an Embodiment export (F-I1.13): the overlap that
matters is the one the simulator sees. Public runs use eval semantics (`--identity eval`), as in sections 18-20.

### 21.2 Colliders first: pieces that keep cavities empty (F-I5.4)
Measured problem [M, 18.4 item 3]: the port of `collision_decomp.py` freezes pieces whose best split removes < 10 % of
their excess, and its keep-out only counts free space within 8 mm of the surface, so hulls span container openings;
CoACD (FlashCHORD's default 0.05) fills them too, and FlashCHORD decomposes each delivered piece on its own, so what we
deliver is what collides [M, ev10w M4]. Routes, in order (a route whose pieces fail the gate falls to the next):

| route | objects | pieces |
|---|---|---|
| 1 plate | plate pairs (F-I4) | F-I4.6 analytic boxes |
| 2 lathe container | structure lathe accepted (rotc <= 3 sigma, A.6) and not plate-like | rings: 16 sectors (12, 8 if over the cap) x bands <= 30 mm (<= 10 mm where carved), from our SHELL candidate's profile completed by revolution; base = centre disc + 16 rim sectors (several contacts, so it does not rock: `lathe_collision.py`'s reason); walls start exactly at each sector's base top; a handle (shell material outside the body, >= 0.3 cm3) goes to route 3 |
| 3 others | everything else, or a lathe whose pieces fail | CoACD 0.02, then keep-out repair: split any hull holding > 0.3 cm3 of keep-out by its best plane, no minimum-gain stop, until it complies or the cap is reached |
| 4 voxel boxes | when 3 fails | the 2 mm cells inside the body and outside the keep-out, merged into maximal boxes (exact); coarser 4 / 6 / 8 mm cells (kept only if all their 2 mm cells are) if over the cap |

- **Gate** for every set (default and carved): each hull holds <= 0.3 cm3 of keep-out = points outside the body it
  stands for that lie in the carve or the guest's swept collider (weight 10) or in a FREE voxel (weight 1), with **no
  distance limit** (a hull that spans a cup's opening holds seen-empty space far from the surface).
- **Wall-continuity check** (lathe): rays at the mid-wall radius every 0.5 mm up the wall and every 1 deg around must
  each hit a piece (catches a 1 mm empty ring).
- **Cap:** floor(165 / objects in the episode) pieces per object (82 with two objects); the episode's 165-shape cap
  (P5) stays. The previous 32 / 64 cap belonged to the old splitter, which F-I5 runs do not use.
- Which object takes which route is measured in the run. Seen before [M, B7 dev bundles]: lathe accepted for the
  ep11 beige cup (2.88 sigma), the ep12 blue cup (1.61), the ep2 lid (2.04) and, wrongly, the ep40 dust pan (1.97;
  rotated points land in FREE space 38 % of the time, so its lathe pieces are expected to fail the gate and fall to
  route 3); rejected for the ep27 pot (3.01, by 0.01 sigma), the rack (8.8), the sweeper (4.2), the boards.

### 21.3 Where the carve goes and how big it is (F-I5.3)
1. **Receiver.** The object the other one is inside: the larger share of the other's collider inside its convex hull
   (a nested cup: ~1 for the outer cup, small for the inner one). Ties (< 0.1 apart): the object that moves less. Only
   the receiver is cut; cutting both would leave a gap as thick as the overlap, and the guest would sink into it.
2. **Rest pose.** The guest's mean pose in the receiver's frame over the pair's hands-off static frames (no hand
   within 30 mm of the guest), preferring the assembled stretch.
3. **Overshoot frames** (not cut, sent to the push list): build frames in which the guest's centroid is more than 4 mm
   past its rest position along the insertion direction or along gravity. On eval 10 the inner cup sits on the floor at f100-117
   and 2.5-27 mm above it (median 13 mm) at f118-160 of the same nest [M, determined-wright]: a pocket cut at every frame would be as deep as the deepest frame, and the resting cup would
   fall into it.
4. **Swept solid.** The union, over the remaining build frames in which the region is entered, of the guest's pieces
   placed by the track and grown by c (each face plane moved out by c), kept only inside the persistent region grown by
   one 4 mm voxel. The cut is exact geometry (a boolean, or per-slice radii for the rings), not 2 mm voxels: c is far
   below a voxel.
5. **Clearance** c = min(1 mm, 0.5 x 4 mm x the 99th percentile of the downward component of the guest's surface
   normal where the pocket wraps it). Worked values [E]: cup wall with a 2.8-4.7 deg taper -> 0.05-0.15 mm after
   rounding (predicted drop <= 2 mm); flat lid rim or a base on a shelf -> 1 mm (drop 1 mm). c = 0 is allowed (exact
   fit, `c_zero`).
6. **Caps** (F-I1.14 thresholds): cumulative carve <= 10 % of the receiver's round-0 collider volume; reach <= 0.6 along
   the insertion direction for INSERTION and SLIDE runs; the carved collider keeps its component count and Euler number
   on the 2 mm grid (no hole through a wall, no split). On eval 10's library-based meshes the median overlap was 14.5 /
   29.1 cm3 against a 153 cm3 blue collider [M, focused-pascal]: about 9-19 %, so the 10 % cap is expected to bind for
   cups whenever the track offset is large; our own cups and tracks are not measured yet.

### 21.4 Acceptance (F-I5.5)
Carved receiver against the same pair with both default colliders, poses P_sim, means over 16 jittered copies:

| test | pass |
|---|---|
| **S hands-off rest / sink** (new) | at up to 3 hands-off static frames: receiver fixed, guest free, gravity along our table normal, plain MuJoCo, 2 ms, 2 s (the ev10w M3 setup): mean guest displacement from its tracked pose <= 4 mm and tilt <= 5 deg; no NaN; no guest below the receiver |
| P2 free travel | gravity, +d, +-n <= max(4 mm, default + 1 mm) |
| P3 replay proxy (every run kind) | lag <= 0.5 cm and 5 deg at the S (else engaged) frames, never > 1 cm after, overlap < 1 cm3 |
| P4 over-removal | removed <= 1.5 x the carve, >= 90 % kept |
| P5 shapes | <= 165 per episode |
| P6 / P7 overlap | no frame worse than default + 0.1 cm3; held-out check frames at most half the default's |
| pieces gate | every hull <= 0.3 cm3 of keep-out |

All must pass, else the default pieces are delivered and the failing test is reported with its numbers. No hands-off
static frame: S is untestable (`sink_untestable`) and P2's gravity bound carries the sink check. FlashCHORD's own 2 s
settle (P1) stays with the Embodiment session's `jitter_check` before any pack uses the folder (`p1_pending`).

### 21.5 Delivery and what is reported (F-I5.6, F-I5.7)
- Round folder per episode and tag (Embodiment layout): carved pieces for objects whose pair passed, default pieces
  otherwise, `_default/` for all, failed carves under `_carved_failed/`, `manifest.json` with an `owner_waiver_fi5`
  block and `p1_pending: true`; do-not-use only if a default fails the gate.
- Reported per pair, never deciding: the rigid-shift alternative (translation proxy, and a rotation-augmented search
  within 1 cm / 3 deg as in ev10w M2: the share of frames it clears to <= 2 cm3), one-sidedness about a lathe axis,
  flag `carve_of_pose_error` when the shift clears >= 75 % of the frames (the carve then makes room for a track error;
  the shift also goes to the tracker), the decision the same pair gets with the flag off, S for plate pairs.

### 21.6 Run order, commands and cost
1. **Build** (new code paths; F-I1 to F-I4 stay the default; starts after the board-slot workflow's build step has
   finished editing the shared files `interlock.py`, `simphys.py`, `tools/interlock_dev.py`, `tests/test_interlock.py`):
   new `gmg/collcarve.py` (scope, receiver, rest pose and overshoot, swept solid, c, caps, rigid-shift report), new
   `gmg/cavpieces.py` (lathe rings, CoACD + repair, voxel boxes, continuity check, gate), `simphys.sink_test` (S), the
   `--waiver-fi5` branch in `interlock.decide_pair` and the driver, T-I12 x1-x11. [E] 15-30 min for the tests on this
   container.
2. **T-I13 public**, eval semantics, one tag per run, in order ep11, ep2, ep12, ep13, ep31 (ep24 from the board-slot
   runs). Template (run `20261031-i2probe-626ce13`; ep12 / ep13 first need candidates from `tools/interlock_cands.py`
   and hands from `hands_cpu.py`): `GMG_MODE=dev GMG_RUN=<run> python -m gmg.tools.interlock_dev --run <run> --ep 11
   --bundle <scratch>/gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep11 --cands <run>/cand/public/ep11 --pick
   blue_cup=shell_t5p36,beige_cup=shell_t5p36 --hands <hands.npz of ep11> --proxy-copies 16 --identity eval
   --waiver-fi5 --no-physcheck --tag fi5`. The exact command, machine, code commit and outputs of every run go to
   `build/I.md`.
3. **Eval twins** 10, 1, 14, 30, the same command on each eval bundle with P_sim = the packed eval reference when its
   provenance validates (F-I3.10), else our eval tracks (`sim_pose_fallback`). No eval bundle exists in this container
   at 17:30 UTC [M]: these runs wait for the eval extraction and are reported as blocked until then. Eval 25 comes from
   the board-slot work.
4. **Cost [E].** Per public episode on this loaded 4-core container: structure (lathe) test 4-27 min per object (B7:
   218-1612 s), pieces a few minutes (CoACD on the rack longer), intrusion and carve minutes, S (16 copies x <= 3
   frames x 2 variants x 1000 steps) and P3 (16 copies x 3 variants) 5-20 min: about 45-90 min per episode, 4-8 h for
   the five. Alternative allowed by the task: one self-destroying Vast CPU box (16-32 vCPU, about $0.15-0.40/h [E]) runs
   them in parallel in about 1.5-2.5 h, about $0.5-1.5 [E], under the $5 cap; plan and cost are stated to the owner and
   entered in the ledger (`LEDGER_SESSION=mesh-bold`, planned and actual) before renting, per the runbook. No GPU.

### 21.7 Predictions (PREREG F-I5.9; each with its falsifier)
| | prediction | falsified if |
|---|---|---|
| P41 | ep11: both cups lathe route, default pieces pass the gate, no empty ring | a cup leaves the route, a hull > 0.3 cm3, or a gap |
| P42 | ep11: default lathe colliders cut the max collider overlap along the track to <= 109 cm3 (20 % of the old 544) | above |
| P43 | ep11: the swept-partner carve keeps the guest at its tracked pose (S <= 4 mm and 5 deg at every hands-off frame, where the ev10w widening sank 11.6 mm) and P2-P7 pass | **the sink test fails on ep11**, or any other test fails |
| P44 | cups' c 0.05-0.2 mm (1.0 mm if the guest's base is in the pocket) [E] | outside |
| P45 | ep2: pot route 3 or 4, lid lathe, receiver pot, c 1.0 mm, S and P2 pass | S fails or lid gravity travel > 4 mm |
| P46 | ep12 / ep13: rack by route 3 within its cap, receiver rack, S passes | route 4 needed or S fails |
| P47 | ep31: any delivered copy keeps the sweeper's gravity travel <= 4 mm and tilt <= 5 deg | outside |
| P48 | ep11: the rigid shift clears >= 75 % of the build frames (`carve_of_pose_error`), as on eval 10 (30 / 31) | < 50 % |
| P49 | eval twins 10, 1, 14, 30 get the same per-pair outcome as ep11, ep2, ep13, ep31 | any differs |
| P50 | T-I12 x1-x11 pass as stated (x3 and x4 are built to fail S: they check that the test sees the ev10w mechanism) | any miss |

### 21.8 Prior work and tools consulted (for this design)
- **ev10w** (focused-pascal `334393e`) [M, theirs]: one-sided intrusion 60 / 61 frames, 5.4 mm axis offset, rigid
  shift <= 1 cm / 3 deg clears 30 / 31 frames; the widened cavity sinks 11.6 mm and drops hands-off settles 40 / 43 ->
  4 / 43; taper 2.8-4.7 deg; their recommendation: settle gates on hands-off frames only (adopted in S). Their
  `pipeline/lathe_collision.py` [R]: 16 segments, 30 mm bands, a multi-piece base so that MuJoCo gets several contacts,
  wall pieces as convex hulls of the profile at the segment edges (the ring layout of route 2 follows it; our profile
  comes from our own SHELL candidate, not from a library mesh).
- **determined-wright** `tools/intrusion.py` and the eval-10 diagnostic [R]: the export samples the union of pieces on
  a grid (F-I5.1 uses the same definition on our tracks); their first "cavity too narrow" reading was withdrawn after
  ev10w (axis error), which is why F-I5 measures against the receiver's own pieces and reports one-sidedness.
- **CoACD** (Wei et al., "Approximate Convex Decomposition for 3D Meshes with Collision-Aware Concavity and Tree
  Search", SIGGRAPH 2022; github SarahWeiii/CoACD) [R]: installed `coacd 1.0.14`, `run_coacd(mesh, threshold=0.05,
  max_convex_hull=-1, preprocess_mode='auto', ...)`; the concavity threshold sets how finely it cuts, but nothing in it
  knows which empty space must stay empty, hence the keep-out repair after it.
- **MuJoCo** [R]: a mesh geom collides as its convex hull, so a non-convex body needs convex pieces; in the installed
  3.17.0 multi-point convex collision is on by default (`mjDSBL_MULTICCD` is a disable flag, checked in the venv
  17:25 UTC); ev10w's M3 used 3.8.1. S runs with the defaults; parity with FlashCHORD's simulator is P1's job.
- **Swept volumes** [generic]: the swept volume of a rigid body over sampled poses is approximated by the union of its
  posed copies; between-frame motion is not covered, which matters little here because only persistent voxels are cut
  and the frames are 20 Hz.
- Hypotheses of this section are labelled [H]; the experiments that falsify them are P41-P50 and T-I12 (x3, x4 test the
  clearance reasoning directly).

### 21.9 Limits and risks (stated before any run)
- **A carve can make room for a track error.** If the rigid shift explains the overlap (as on eval 10), the carve fits
  the shapes to a wrong relative pose. The flag `carve_of_pose_error` and the push list make this visible; the physics
  tests decide delivery, not this flag (the owner's waiver).
- **One-sided offsets.** A guest pushed against one side of a pocket with an open gap on the other side may slide down
  and sideways when the hands let go, unless the pocket has a floor or shelf under it (T-I12 x2 vs x3). S decides.
- **The 10 % cap may bind for cups** (eval-10 overlaps were 9-19 % of a cup collider on library-based meshes); then
  nothing is carved and the default rings are delivered, which already remove the cavity filling.
- **Lathe completion** fills unseen sectors by revolution; a cup with a handle or a dent there is approximated. FREE
  space inside the completed body fails the gate (route 3 then).
- **Masses** remain the 0.3 kg placeholder (D-I1), so S tests geometry and contact more than the real dynamics.
- **Simulator parity.** S runs plain MuJoCo 3.17.0; FlashCHORD's simulator (the Newton / Warp stack) may differ; P1 by
  the Embodiment session remains required before packing.
- **Eval** needs eval bundles that do not exist yet; P_sim provenance may fall back to our eval tracks.

### 21.10 Build and synthetic tests (31 Oct, 17:36-18:37 UTC; PREREG F-I5.11-F-I5.13)
**In plain words.** The code is built and wired in behind the `--waiver-fi5` flag (nothing changes without it). On the
synthetic tests the rule as written **carves no cup**: every nested-cup case stops at the size and shape limits
before the physics test is reached, so the default rings (which already keep the cups hollow) would be delivered. The
three reasons, all measured: the cut follows every jittery frame of the track and so becomes wider than the cup; the
finer bands it asks for push the piece count over the cap, so the rings fall to 12 or 8 slices whose flat faces sit
up to 3 mm inside the round wall; and the board-slot limits (at most 10 % of the volume, at most 60 % of the depth)
are always exceeded by a thin layer cut along a whole cup wall. A 5 mm off-axis cup (the eval-10 case) cannot be held
by any carve: the cut would go through the 4 mm wall. The holder fixture (a stick in a blind hole) also stops at the
depth limit.

- Pieces work as designed [M]: cups get 65 ring pieces with no empty ring (0 gaps on 64,440 rays; a forced 1 mm ring is
  caught), an open box keeps its opening empty, a flat plate never takes the ring route, a folded sheet falls to CoACD.
- Plate pairs and the flag-off path are unchanged [M] (identical records).
- A CoACD crash (an internal assertion that killed the whole process) is now contained: CoACD runs in a child process
  and the object falls to exact boxes.
- Next, diagnostic only (PREREG F-I5.13, never delivered): cut the pocket at the guest's hands-off rest pose plus its
  straight approach channel, keep the normal ring layout, and let the size limits report instead of block, to answer
  the physics question (does the guest stay where the track puts it?). Its predictions are written before it runs.
  If it holds, the open decision for you is whether the 10 % / 60 % limits (made for board slots) should apply to cup
  walls and holders.
- **D2 result (19:10 UTC, diagnostic, nothing delivered; PREREG F-I5.13 outcomes).** The physics answer is yes: cut
  at the rest pose, every nested-cup carve keeps the inner cup within 2.3-3.0 mm and 3.4 degrees of where the track puts
  it with the hands off, even 5 mm off-axis. The uncarved rings move it by about the track's error (up 4.5 mm when the
  track is 9.5 mm too deep, sideways 5 mm at a 5 mm offset, 1 mm at a 1 mm offset). But none of these carves passes the
  shape test as written: the 1 mm clearance thins a 4 mm wall to about 2 mm, which the 2 mm test grid reads as holes
  (on a 1 mm grid the x1 carve is intact; thinnest wall 1.7 mm); for the 3 mm and 5 mm offsets the cut reaches 4-6 mm
  into a 4 mm wall, so they very likely go through it [E, not re-checked on 1 mm]. They also remove 19-36 % of the cup's collider (limit 10 %).
- **Open decisions (orchestrator / owner; each would be a dated PREREG entry before any real run uses it):**
  1. the carve geometry: rest pose plus approach channel (D2) instead of every raw frame;
  2. the clearance for nests: c = 1 mm comes from the guest's base corner, and it is what thins the wall; a
     wall-slope c (about 0.1 mm [E]) would leave about 0.9 mm more wall;
  3. the topology test grid (1 mm) or rule (fail only on new components or more tunnels: the lid/pot default already
     has tunnels on 2 mm);
  4. whether the 10 % volume and 0.6 reach limits apply to cup walls and holders;
  5. replacing the as-built per-piece R+ shortcut by an exact K-inside-R+ clip (code).
  Off-axis cups (3-5 mm, as on eval 10) need a cut of 3-5 mm plus clearance into a 4 mm wall, so no variant can keep
  the wall [E]: the pose correction (the push list) stays their remedy.

### 21.11 Public runs T-I13 (31 Oct, 19:15-20:57 UTC; PREREG F-I5.14 and its outcomes)
**In plain words.** We ran the collision carve as written on the five public episodes (cup in rack ep12 and ep13,
sweeper and rack ep31, cups ep11, pot and lid ep2). **Nothing was carved and delivered, and the simulator copies these
runs wrote must not be used.** The carve itself was hardly reached: the step before it, which turns each object into
simulator pieces that keep a cup or pot hollow, failed on all ten real objects and fell back to coarse 6 mm boxes that
keep only 2-9 % of each object. With such pieces the objects hardly touch (at most 0.5 cm3 of overlap along a whole
episode), so four of the five pairs have nothing to carve, and the one pair that does (the ep11 cups) fails the
physics test. When the hands let go, nothing stays put on these pieces: the inner cup falls 80 mm, the cups fall out of
the rack (91-127 mm), the lid falls 81-87 mm into the pot and the sweeper 84-87 mm through the rack.

| ep | pair | scope (rule as written) | delivered | S on the delivered pieces (diagnostic) |
|---|---|---|---|---|
| 12 | blue cup / rack | out: both components fail the sweep share (0.0) | default (6 mm boxes) | cup moves 126.8 mm (f176), 8.2 mm (f6): fail |
| 13 | blue cup / rack | out: no collider overlap at all | default | 90.6 mm (f146): fail |
| 31 | sweeper / rack | out: no collider overlap at all | default | 84.2 / 86.7 mm drop: fail |
| 11 | blue / beige cup | in: receiver beige, c 1.0 mm, caps pass (9.97 %) | default (S, P3, P4 fail) | 80.5 mm (f126): fail |
| 2 | pot / lid | out: sweep share 0.0 | default | lid 84.8 / 88.0 mm: fail |

- Why the pieces fail [M, `build/I/results/collcarve-public/README.md`]: (1) CoACD is asked for at most the piece cap
  (82) and returns exactly 82 hulls, so the keep-out repair cannot split, and 2-75 hulls per object hold more than 0.3
  cm3 of seen-empty space; (2) the ring pieces of cups and the pot are continuous (0 gaps), but the "handle" step adds
  hulls for 6-15 residual shell components per object (22-68 cm3), which push the set over the cap or fail the gate
  [corrected in 21.12 item 1: the ring pieces fail the gate on their own, and the continuity check cannot see it]; the
  ep11 blue cup misses the lathe test at 3.013 sigma (threshold 3) and the ep2 lid has three radial intervals; (3) the
  box fallback keeps a 6 mm cell only when it lies wholly inside the body, which a 3-5 mm wall almost never does.
- Predictions: P41, P43, P45, P46, P47 falsified; P42 and P48 hold only because the pieces are nearly empty; P44 void;
  P49 not tested. [Corrected in 21.12 item 8: P42 not tested, P44 holds as written.]
- **Decisions needed before any further F-I5 run (orchestrator / owner; each a dated PREREG entry first; superseded by
  the list in 21.12):**
  1. the default-pieces ladder: CoACD below the cap so the repair can work, and a bounded handle step [H, falsifiers in
     the results README];
  2. a physical delivery floor: no round folder whose delivered pieces keep less than a stated share of the body or fail
     S on the delivered pieces (today the rule delivers them because they pass the keep-out gate);
  3. the five decisions of 21.10, which are downstream of these.
- As-built gap: the rigid-shift alternative is reported only for in-scope pairs (F-I5.7 says every pair); here the
  overlaps are under its 2 cm3 level anyway.
- Eval twins 10, 1, 14, 30: still blocked (no eval bundle) and not worth running until (1) and (2) are decided.
- Cost: this container only (five runs in parallel, 45-83 min each under load 14-25), $0, no rental.

### 21.12 Report: verification, record corrections, hand-offs, open decisions (31 Oct ~21:30 UTC)
**In plain words.** The collision carve as written produced nothing usable, and there is no carved simulator piece
for any episode, public or eval. The eval step (evals 10, 1, 14, 30) was cancelled by the orchestrator (~21:30 UTC),
because no run under this rule could pass. Two independent verifiers re-checked the public runs. The numbers reproduce
and the rule was followed as written. But the physics check found that our explanation of the failure was incomplete
in three ways that change what round 2 must fix:
- The ring pieces for the cups and the pot fail the "keep it hollow" test on their own; the "handle" pieces are not the
  cause. With at most 82 pieces a 20 cm cup gets only 8 slices, and their flat inner faces cut about 3 mm into the
  cup's opening.
- Even pieces that copy our cup, pot and sweeper shapes to 2 mm fail the hands-off test at all eight frames tested,
  because our tracked poses there are physically impossible: the two ep11 cups overlap by half a cup, the ep12 / ep13
  cup sits 15-23 mm inside the table, the ep31 sweeper floats 45 mm above it. Better pieces alone cannot fix these
  pairs; the poses have to be checked first.
- Both ep11 cup shapes have no bottom, and at rest both stand on the table in nearly the same place. So ep11 does not
  test one cup nesting in another.

Submitted meshes were never touched. Round 2 (PREREG F-I5.15) is next, public episodes first.

**Accuracy, failures and cost** [M unless marked]:

| item | result |
|---|---|
| design (PREREG F-I5.0-F-I5.10) | pushed d156571 (17:34:10), before any F-I5 code (18:11) or run |
| build and synthetic tests T-I12 (F-I5.11-F-I5.13) | built behind `--waiver-fi5` (flag off: identical records); the rule as written carves no nested cup (caps stop every case before S); synthetic cup in rack slot carved (S 0.68 / 0.80 mm); P50 falsified. D2 diagnostic: a rest-pose carve keeps the guest within 2.3-3.0 mm / 3.4 deg but fails the 2 mm topology test |
| T-I13 public (F-I5.14), code 1b9f0c1 | ep11, 2, 12, 13, 31 in parallel, 45-83 min each (load 14-25); nothing carved; all 10 objects end in 6 mm boxes (1.8-9.3 % of the body); S on the delivered pieces fails on every pair, 8.2-126.8 mm |
| predictions P41-P50 | P41, P43, P45, P46, P47, P50 falsified; P48 holds only trivially; P44 holds as written; P42 and P49 not tested (corrected, item 8) |
| verification | `build/I/verify_cc_0.md` (rule compliance): no blocking item, 13 nonblocking; `build/I/verify_cc_1.md` (physics and geometry): 3 blocking items for the next round, 9 nonblocking |
| eval twins 10, 1, 14, 30 | not run (orchestrator, ~21:30 UTC): no eval bundle, and no run under this rule can pass. An eval-bundle tool (`tools/ev_extract.py`, 5bf54bc, board-slot round 3, for eval 25) was committed at 21:25 [R]; no bundle for 10, 1, 14 or 30 exists yet [M, 21:31] |
| delivered | nothing: no carved pieces anywhere, nothing uploaded or packed |
| cost | this container's 4 shared cores, no rental, $0; about 4.2 h of wall time from design (17:14) to the second verifier (21:23), runs partly in parallel [E, from the log times] |

**Confirmed by the verifiers** [M]: F-I5 reached origin at 17:34:10, before the first F-I5 code; F-I5.14 at 19:17:17,
before the first launch (19:29:39); addendum (7) at 20:30:13, before its first output (20:31:09). The module sha256 of
all five launch records and ten report records equal the 1b9f0c1 blobs (clean). The commands match F-I5.14 (2). The
hands copies equal the v6 M1 outputs, and the F-I5 code paths open no scan, mocap, parquet pose, `*_align` file or
library mesh [R]. The ep11 gates and steps follow F-I5 as written (receiver by containment 0.617 vs 0.401, 7 overshoot
frames, c = 1.0 mm, caps, S, P3, P4). Out-of-scope components keep their earlier decision, none is CARVE, and
`submitted` is False on every record. The delivered volumes, CoACD counts (82 hulls x 9, 80 x 1), routes and S numbers
reproduce; S is deterministic (the stored carved copies 0 and 2 re-run bit for bit).

**Corrections and caveats to 21.11 and the PREREG F-I5.14 outcomes.** None changes an outcome under the rule as
written. Items 1-3 change what round 2 has to decide (verify_cc_1, blocking for the next round):
1. **The lathe ring pieces fail the gate on their own** (B1). Re-run per hull: on ep11 beige all 16 failing hulls are
   rings and the 15 handle hulls pass (max 0.288 cm3); on ep13 blue 20 of 22 failing hulls are rings. Ring sets without
   any handle hull fail too (ep12 blue 15 over at 8 sectors, 18 at 16; pot 36 at 12, 45 at 16; ep11 beige 29 at 16).
   Cause: each wall piece is the hull of the profile at its two sector edges, so its inner face is a chord r_in(1 -
   cos(pi/N_s)) inside the cavity at mid-sector: measured -2.9 to -3.4 mm with 8 sectors, -1.2 to -1.3 mm with 16, -12.5
   mm for the pot. The 82-piece cap forces 8 sectors on these 186-204 mm cups (16 x 7 = 112 and 12 x 7 = 84 bands are
   both over it). 21.11's "the handle hulls push the set over the cap or fail the gate" (mechanism 2) is wrong for both
   objects whose gate was reached, and decision 1's "bounded handle step" is falsified by its own falsifier. The
   continuity check is self-referential (it tests the middle of the pieces' own chord polygon), so "0 gaps" is no
   evidence that the rings fit the wall: the 8-sector rings hold only 45-49 % of the body cells. Most of the ep12 blue
   "handle" residual is 8-sector outer-chord sag (3.5 mm > 3 sigma), not SHELL noise (V1 N5).
2. **S fails on faithful colliders too** (B2): the SHELL bodies as 2 mm boxes (736-4,751 per object, no cap) fail S at
   all eight S frames (ep11 f126 10.9 mm / 6.5 deg; ep12 f176 10.5 mm, f6 18.6 mm; ep13 f146 20.1 mm; ep31 f282 / f8
   free fall 72.6 / 74.8 mm; ep2 f24 / f328 13.9 / 29.9 mm). Causes measured at the tracked poses: interpenetration (ep11
   86.0 cm3, half the guest; ep2 25.0 / 24.1 cm3; ep12 f176 7.5 cm3); the guest inside our table plane (ep13 f146 23.3
   mm, ep12 f6 15.1 mm, SHELL bottom); the ep31 sweeper 45-46 mm above the table with zero contacts, over space the
   rack's own grid marks 88-94 % FREE. So the 6 mm boxes explain how the delivered copies fail, not why S fails on
   these pairs, and a delivery floor based on S on the delivered pieces alone cannot tell a piece failure from a pose
   failure. P47 fails whatever the pieces.
3. **ep11 is not a cup-nesting case with the v6 inputs** (B3): both cup SHELLs are bottomless (axis rays from 20
   cavity points hit nothing; the beige profile has 0 solid bins); at f126 both stand on the table (lowest points 3.2 /
   3.4 mm above it), axes 2.8 mm and 1.7 deg apart. The guest is held by the table, not by the receiver, so P43, P44 and
   "in scope, receiver beige, SEAT" say nothing about cup-in-cup sink. [H] Both tracks lock onto the same stack, or the
   SHELLs are built from the stack's surfaces; falsifier: the identity / B.2a step on v6 and each cup's observed rim
   heights. The overshoot exclusion was physically right (at f106-114 the guest's SHELL bottom lies up to 2.8 mm below
   the table).

Record and scoring corrections:
4. **"Must not be used" is a recommendation, not a rule outcome** (V0 N1). Under F-I5.4 / F-I5.6 the five round folders
   are deliverable (do-not-use only on a gate failure), and they carry no `DO_NOT_USE.json`. The recommendation rests on
   diagnostic F-I5.14 (7) and item 2. Their pieces exist only in this container's scratch
   (`<scratch>/gmg/runs-dev/20261031-fi5pub-3053a78/sim/public/ep*-fi5/r0`); git holds their manifests, props and the
   failed ep11 carve.
5. **The ep11 default S is bimodal** (V1 N1): copy 0 7.2 mm (pushed up 5.4 mm, no fall), copy 2 142.7 mm (falls 120.6
   mm), unjittered 146.7 mm. "The inner cup falls 80 mm" is a mean of no-falls and 120 mm falls. The default's per-copy
   rows are dropped (`collcarve.py:587`, `build/I/fi5_default_sink.py:130`), against F-I5.5.
6. **Exact volumes** (V1 N2-N4): `props_gmg.json` `volume_cm3` overstates the delivered boxes 1.52-1.94x (1.5 mm face
   samples; COM and inertia come from the same samples). On exact volumes ep11 removed 0.648 cm3 = 9.38 % of 6.912 cm3
   (reported 9.97 %), and P4 still fails (0.648 > 0.621). P2 passed vacuously (60 mm, the search cap, for carved and
   default alike), and the 10 % cap was relative to a 6.8 cm3 collider.
7. **Flag-off decisions** (V0 N4): `decision_f_i3` holds the F-I1 to F-I3 logic applied to the collider components,
   not the flag-off decision F-I5.7 (iv) asks for. Flag-off (`decisions.json`): ep11 PUSH (class O > 25 %, where
   `decision_f_i3` says CARVE); ep2 pot PUSH (the 20:35 log line said IGNORE). Latent: a gate-failing component keeps
   its label but loses its solid, so a CARVE label could stand with nothing carved (did not occur).
8. **Predictions** (V0 N8): P42 is not tested (its subject, default lathe colliders, never occurred), not "holds
   trivially". P44 holds as written (c = 1.0 mm is its stated alternative, as the 20:17 log scored it); 21.11's "void"
   was a post-hoc re-reading with the right reason (any axis-aligned box set gives sigma_sup >= 1/sqrt(3), so c = 1 mm).
   P47 is falsified through diagnostic (7) and, by item 2, on faithful colliders too. P43 is falsified on a
   configuration that is not a nest (item 3).
9. **As-built gaps not in F-I5.11** (V0 N2, N3, N5): no F-I5 round folder has `sources/` (`--waiver-fi5` sets
   `no_physics`, which skips the only `write_sources` call), so the Embodiment's `carve_from_intrusions` has nothing to
   read; the carved receiver skips routes 2 and 3 (`collcarve.py` line 396; ep11's carved beige went to boxes although
   its lathe test passed, effect probably none [E]); F-I5.7 (iii) "the shift goes to the push list" is not built; (ii)
   one-sidedness is null whenever the receiver's lathe route failed; the rigid shift runs for in-scope pairs only.
10. **Semantics and tier** (V0 N6, N7): the v6 bundles have no identity step, so public and eval semantics coincide on
    these inputs (on earlier bundles ep11's blue cup was IDENTITY_SWAP on public [E]). "GT-free" holds at the dev tier:
    every F-I5 body is shell_t5p36 with t0_dev = 5.36 mm, fitted on `obs_all` (library_v3 ROI), which PREREG A.1 allows
    in DEV runs only; the eval twins must use the clean t0. The dev per-object medians for the cups are 1.5 / 1.6 mm
    [R], and the SHELL cup walls the boxes sample are 5.0-5.4 mm, not "3-5 mm" (V1 N6).
11. **The kept sweep gate decided two pairs** (V0 N11): the moves-through sweep share put ep12 and ep2 out of scope.
    It is written in F-I5.2, so the runs comply, but it is missing from 21.11's decision list; once the pieces are
    fixed it will decide the resting pairs (lid on pot, cup in rack) that the owner's waiver covers.
12. Smaller records (V0 N9, N10, N12; V1 N7-N9): report.json `launch_code` is taken after the inputs load, so ep13,
    ep31 and ep11 (launched at cdc8b40) record 407a18e, with no module difference; the run folder, hands copy (19:15:26)
    and candidate builds (from 19:15) began just before F-I5.14 reached origin (19:17:17), with no outcome yet; the ep11
    guest records are tier T0 without the `owner_waiver_fi5` flag; the 20:08 log time was corrected at 20:13; route 4
    keeps 2 mm cells by their centre, so a kept 6 mm cell can stick out up to 1 mm; the ep12 blue base is only 50.9 %
    covered by its 8-sector disc and rim pieces; the side-view figures draw no table line (with one, the table
    penetration and the floating sweeper would have been visible).

**Hand-offs** (relayed by the orchestrator; texts in the work log of 31 Oct ~21:30 UTC):
- **Embodiment session (determined-wright):** no F-I5 r0 folder exists for any eval episode, and nothing changed for
  them: no carved or new default pieces, no `sources/`, nothing to check. The five public F-I5 round folders are not
  for use. Item 2's pose findings are passed on as data for their frame-by-frame fixes. The ep24 F-I4.15 P1 request
  (20.12) is separate and unchanged.
- **Pack builder (focused-pascal):** no eval episode has new carved simulator pieces; keep the pack's collision pieces
  (`meshes/carve/ev10`, `ev01`, `ev25`); no rollout re-run is needed now. Pieces from a later round would differ in
  shape and split, so adopting them would need rollout re-runs, not a pack-only swap. Item 1's chord inset applies to
  any ring layout built as hulls of the profile at the sector edges, theirs included [E].

**Open decisions for round 2** (PREREG F-I5.15; orchestrator / owner; each a dated entry before any run uses it; this
list replaces 21.11's):
1. **Ring geometry and the cap, not the handle step** (item 1): inner faces tangent to the measured inner surface
   (vertices at r_in / cos(pi/N_s) at the sector edges), band edges at profile slope changes, a cap that allows 16
   sectors on a 20 cm cup, and a continuity check against the measured wall instead of the pieces' own chords [H;
   falsifier: the gate still fails on ep11 beige and ep12 blue at 16 sectors].
2. **CoACD below the cap** so the keep-out repair can split (21.11 decision 1, first half) [H; falsifier: the repair
   still leaves hulls over 0.3 cm3 at the cap].
3. **A delivery floor with absolute bounds and exact volumes** (items 2, 6): S on a faithful reference collider (the
   2 mm SHELL boxes, 2-50 s per copy) beside S on the delivered pieces, calling a failure a piece failure only when the
   reference passes [H].
4. **A pose precheck at each S frame** (item 2): the guest's lowest point against the table plane, the faithful-body
   overlap and the contacts at t = 0. A frame that fails goes to the tracker, not to the carve.
5. **A real nesting case** (item 3): run the identity / B.2a step on v6 and check each cup's rim heights before ep11 is
   used again, or use a synthetic nest with a bottomed receiver.
6. **The sweep gate for resting pairs** (item 11).
7. **The five decisions of 21.10** (carve geometry, nest clearance, topology grid, caps for cups and holders, exact
   clip), downstream of 1-6.
8. **Records before the next delivery:** a labelled post-hoc `DO_NOT_USE.json` in the five scratch round folders
   (item 4), `sources/` in F-I5 rounds, the carved-ladder routes, the flag-off decision field, F-I5.7 (ii) / (iii), the
   default's per-copy S rows, exact-volume props (items 5-9).
9. **A focused prior-work review before the fixes are chosen** (CLAUDE.md; V0 N13). Closest prior: focused-pascal's
   `pipeline/lathe_collision.py` (334393e: rings and base only, no handle step). The fixes' falsifiers should not rest
   only on the ten public objects on which the failures were found.

Masses remain the 0.3 kg placeholder (D-I1), and S runs plain MuJoCo 3.17.0, not FlashCHORD's simulator (P1 stays with
the Embodiment session).

### 21.13 Round 2: pieces that cannot enter a cavity, a pose check before the physics test, a delivery floor (PREREG F-I5.15; written 31 Oct before any code or run with it)
**In plain words.** Round 1 delivered nothing, for three measured reasons: our ring pieces for cups and pots cut about
3 mm into the cup's opening (only 8 slices fitted under the piece cap, and each slice's inner face was a flat chord
across the round cavity); at the frames where we test "hands off, does the guest stay put", our tracked poses are
themselves impossible (the two ep11 cups overlap by half a cup, a cup sits 15-23 mm inside the table, the sweeper floats
45 mm above it); and ep11, the only public episode with two cups, does not show one cup inside the other in our data.
Round 2, decided by the orchestrator at ~21:50 UTC under your waiver, changes four things before any carve:
- **Ring pieces that cannot enter the cavity.** Each slice's inner face now touches the cavity from outside (the
  polygon goes around the round opening, not across it), and its outer face stays inside the outer wall. The number of
  slices and bands is chosen to keep as much wall as possible within the piece cap (the cap now has room for 16
  slices on a 20 cm cup, where round 1 had 8). A new check casts rays through our measured cup wall itself, not only through the pieces.
- **CoACD gets room to repair.** It is asked for at most half the cap, so the repair step can split the pieces that
  still fill a cavity.
- **A pose check first.** At every test frame we check, on faithful copies of our shapes, whether the guest is more
  than 4 mm inside the table, more than 4 mm away from anything that could hold it, or overlapping the other object in
  a way no allowed carve could remove. Such a frame is impossible as tracked: it is not used for the carve or the
  hands-off test, and it goes on a list for the pose lanes.
- **A physical floor for every delivered copy.** A round folder is marked do-not-use when a delivered object keeps less
  than half of its shape, or when it fails the hands-off test at a frame where faithful shapes pass it. The five round-1
  folders get this marker too.

Then the five open questions of 21.10 are settled: the cut is made at the resting pose plus the straight way in; the
clearance comes from the guest's wall only (about 0.1 mm on a cup wall), not from its flat bottom; the shape test runs
on a 1 mm grid and fails only on new pieces or new holes; for cups and holders the 10 % / 60 % limits made for the
boards are replaced by a rule that keeps at least 1.5 mm of wall and at most half of the object removed; and the cut is
clipped exactly. A cup that sits 3-5 mm off-centre in a 4 mm wall (eval 10) is still not carved: its pose has to be
corrected instead.

What we expect, stated before any run: the ring pieces now pass on the cups and the pot; the racks still fail (CoACD
plus the repair cannot keep a rack's openings empty within the cap), so the three rack episodes will be marked
do-not-use; no public pair gets a carve, because at their test frames the poses are impossible or the pair moves too
little to qualify. A real cup-in-cup nest is tested only on synthetic cups: we have no public episode in which our data
show one, and eval 10 is the only real one. Public episodes only, CPU, about $0.5-1.5 on one self-destroying rental box
[E] (cap $3) plus this container.

#### 21.13.1 Prior work reviewed, and what it implies (CLAUDE.md; V0 N13) [R unless marked]
| source | what it says | implication for this round |
|---|---|---|
| CoACD paper: Wei, Liu, Ling, Su, "Approximate convex decomposition for 3D meshes with collision-aware concavity and tree search", ACM TOG 41(4), SIGGRAPH 2022 (arXiv 2205.02961) | concavity = max(H_b, H_i), H_i a Hausdorff distance between interior samples; for a hollow shell the boundary distance to its hull "may be quite small", so a boundary-only metric fills the interior; plane cuts avoid voxelization errors; the merge step uses an approximate H_i (k R_v) | CoACD's own metric is collision-aware, so the cavity filling of round 1 is not explained by its metric at 0.02 [H]; see next row (item 2) |
| CoACD README (github SarahWeiii/CoACD; installed 1.0.14) | `max_convex_hull` (-1 = no limit) "works only when merge is enabled" and "may introduce convex hull with a concavity larger than the threshold"; `preprocess_mode auto` remeshes only non-manifold input (`preprocess_resolution` 50) | asking for the cap forces merges past the threshold, and round 1 got exactly the cap on 9 of 10 objects: item 2 (floor(cap/2), then the repair). [M] all ten round-1 SHELL bodies are watertight volumes (~3,900 faces), so the preprocessing did not run and is not the cause. [H, later] CoACD with -1 would show how many hulls it needs unforced |
| V-HACD v4: Mamou, github kmammou/v-hacd, `VHACD.h` | voxel based; FLOOD_FILL (default) "meshes with holes can fail and create hollow results"; SURFACE_ONLY "will create 'skins' with hollow centers"; RAYCAST_FILL; defaults 64 hulls, 400,000 voxels, 64 vertices per hull | a hollow mode exists, but 400,000 voxels over a 200 mm cup are ~2.7 mm cells, half our 5.4 mm SHELL wall: the resolution problem of route 4. Not adopted (not in the decision; not installed); at most a later hypothesis |
| MuJoCo documentation, Computation, Collision detection | collision only between convex geoms (meshes replaced by their qhull hulls), SDF plugins excepted; recommends splitting a non-convex body into convex geoms, naming "the CoACD library"; multiccd returns several contact points per pair | convex pieces stay the interface (FlashCHORD also decomposes each delivered piece, ev10w M4); SDF colliders are not deliverable; the base as a centre disc plus rim sectors stays (several contacts, no rocking) |
| Factory: Narang et al., "Factory: Fast Contact for Robotic Assembly", RSS 2022 (arXiv 2205.03532) | for tight parts, convex decompositions "can produce spatial artifacts on complex geometries"; "undesirable contact normals can be generated, and snagging may occur"; Factory uses SDF-based contacts | a polygon ring differs from the round wall by up to r (1/cos(pi/N) - 1) and tilts normals by up to pi/N. In a tapered nest that radial gap becomes sink (21.13.5): hence a 64-sector reference and the synthetic test n2 |
| focused-pascal `pipeline/lathe_collision.py` (branch claude/focused-pascal-2nz9s1, last change 334393e) | wall piece = hull of the outer radius r and the inner r - t at the band's profile bins, at the two edge angles (both faces chords); base = centre disc (r/2) plus SEG rim sectors with mid-angle points; options `--shrink`, `--inner` (per-height cavity radius and band edges), `--base_from_hulls`; no handle step, no cap | its inner chord is exactly B1's defect (inside the cavity by r_in (1 - cos(pi/N))): our inner face becomes tangent; its base layout is kept; its `--inner` band edges are our forced carve edges (D2 (b)). Its eval pieces (`meshes/carve/ev10`, `ev01`) carry the same inset [E]; not our files, reported to the pack builder only |
| Digital topology: Andres, Acharya, Sibata, "Discrete analytical hyperplanes", Graphical Models and Image Processing 59(5), 1997 | a digital plane of arithmetic thickness ‖n‖∞ (the naive plane) is 26-connected and lets no 6-connected background path through | a wall at least one cell thick is sampled on the 1 mm grid without holes or tunnels: the topology grid of decision 3 and the 1.5 mm wall floor of decision 4 (one cell plus half a cell for curvature and centre-inside sampling) |
| Round 1, measured (verify_cc_0, verify_cc_1, F-I5.12-F-I5.14) [M] | B1 chord inset -2.9 to -3.4 mm at 8 sectors (pot -12.5), 8 sectors forced by the 82 cap, the continuity check self-referential; B2 S fails on faithful SHELL boxes at all 8 S frames (impossible poses); B3 ep11 SHELLs bottomless and co-located; D2: a rest-pose carve holds a nested guest within 2.3-3.0 mm, thinnest intact wall 1.7 mm on 1 mm | items 1, 3, 4, 5 and decisions 1-4 |

#### 21.13.2 Ring pieces that cannot enter the cavity (item 1; F-I5.15 (1))
- **Profile per sector.** Rays from the structure axis through the SHELL every 1 deg in azimuth and every 1 mm in
  height (the construction rays); per ray the innermost radial interval [r_in, r_out]. Wall / solid bins stay F-I5.4's
  (2 mm, median over sectors, inner radius > max(3 sigma, 2 mm)). Where fewer than half of a sector's rays hit the
  SHELL at a height, the sector takes the median profile there (completion by revolution, as before).
- **Wall piece** of sector s (half-angle theta = pi / N_s, mid azimuth phi_m), band [h0, h1]:
  - inner face: the plane at distance rho_in(h) from the axis along phi_m, rho_in linear in h, the least such function
    with rho_in(h) >= r_in(phi, h) cos(phi - phi_m) at every construction ray of the sector and band (an upper linear
    envelope; its vertices sit at rho_in / cos(theta) at the sector edges). The inner polygon circumscribes the measured
    cavity: tangent at mid-sector for a round cavity, never inside it at a construction ray;
  - outer face: vertices at R_out(h) at the two edge angles (a chord, inscribed), R_out linear in h, the greatest such
    function with R_out(h) cos(theta) / cos(phi - phi_m) <= r_out(phi, h) at every construction ray (a lower envelope);
  - piece = hull of the 8 vertices; min wall left of the piece = min over h0, h1 of R_out cos(theta) - rho_in (mid) and
    R_out - rho_in / cos(theta) (edges).
- **Base** (solid runs): centre disc (r/2) plus N_s rim sectors, as F-I5.4, with its top at or below the SHELL's
  cavity floor and its bottom at or above the SHELL's bottom surface on the sector's axial construction rays (every
  1 mm in radius, 1 deg in azimuth). The lowest wall band of every sector starts exactly at that sector's base top.
- **Sectors x bands under the cap (the rule).** N_s in {8, 12, 16, 20, 24, 32}. Wall band edges are common to all
  sectors of a wall run and are chosen greedily: start with one band per wall run and repeatedly split the band whose
  best split (at a 1 mm level) gains the most ring volume; base bands as F-I5.4 (<= 30 mm). Pieces n = N_s B_w +
  B_s (N_s + 1) + n_h (n_h = handle hulls, F-I5.4's handle step on the candidate's rings). For each N_s take the largest
  B_w with n <= cap (cap = floor(165 / objects), 82 with two objects; more bands never lose volume) and require a min
  wall left >= w_min = 1.5 mm in every piece. The feasible candidates (at most six) are tried in order of exact ring
  volume, largest first; the first that passes the continuity check and the pieces gate is used; none: route 3. Each
  candidate tried is logged (N_s, B_w, n, volume, min wall, intrusion, continuity, gate).
  Arithmetic: a 200 mm cup with a base fits 16 sectors x 4 bands (16 x 4 + 17 = 81) or 12 x 5; a straight-tapered cup
  needs one band per wall run and fits 32 sectors (32 + 33 = 65).
- **Intrusion and wall, measured.** Intrusion along a ray = the SHELL's inner wall radius minus the pieces' first radius
  (positive = a piece inside the cavity). On the construction rays it must be <= 1e-6 m (by construction; a larger
  value is a code error and rejects the set, `ring_intrusion`); on the continuity rays it is reported (P71). Also
  reported: min wall left, exact ring and set volumes, the share of the SHELL volume inside the set.
- **Continuity check against the measured wall** (replaces the self-referential F-I5.4 check). Rays from the axis every
  0.5 mm in height over each wall run and every 1 deg in azimuth, offset by 0.5 deg from the construction azimuths, and
  axial rays through the base every 1 mm in radius and 1 deg in azimuth; each ray is intersected exactly with the SHELL
  (intervals by parity) and with the union of the pieces (exact ray / convex-hull intervals). A ray is a gap when the
  SHELL has a wall (or base) interval on it and the pieces cover less than half of its length. Route 2 is rejected
  (`lathe_wall_gap`) when gaps exceed 1 % of the rays that hold a SHELL interval, or when more than half of the
  azimuths at one height are gaps (a ring gap, the ev10 defect). No base interval on any axial ray:
  `shell_bottomless`, reported (B3), not rejected. On round 1's own geometry this check would have failed the 8-sector
  rings (they covered 1.9-2.9 mm of a 5.0-5.4 mm wall at mid-sector [M, verify_cc_1]); test r1 checks it.

#### 21.13.3 CoACD below the cap (item 2; F-I5.15 (2))
CoACD 0.02, preprocess auto, **max_convex_hull = floor(cap / 2)** (41 at cap 82); then the keep-out repair splits
without a gain stop up to the cap (F-I5.4). Expected [H]: enough for objects that round 1 left with few over-tolerance
hulls (sweeper 2, lid 16), not for the racks (65-75 hulls over at 82). The voxel-box route 4 is unchanged; its pieces
now meet the delivery floor (21.13.5), which 6 mm boxes keeping 1.8-9.3 % cannot pass.

#### 21.13.4 Pose precheck at every S frame (item 3; F-I5.15 (3))
Faithful colliders: the SHELL bodies' 2 mm cells (centre inside) merged into boxes, no cap (verify_cc_1 B2). At each S
frame of a pair (the acceptance frames of F-I5.5 and the floor frames of 21.13.5), with our tracked poses:

| check | fails when | threshold origin |
|---|---|---|
| (a) table | the guest's lowest faithful point is more than 4 mm below our table plane | s_max = 4 mm, S's own bound (F-I1.14): a guest starting deeper is pushed out by more than S allows, whatever its pieces |
| (b) support | the guest's faithful collider is more than 4 mm from both the table plane and the receiver's faithful collider | s_max: a guest with a gap above 4 mm under it falls more than S allows |
| (c) overlap | V_ov (guest faithful cells inside the receiver's) > 0 and the overlap is not carvable: the receiver's SHELL minus the guest's SHELL at that pose (exact boolean) fails decision 3 (topology, 1 mm) or decision 4 (wall integrity) against the uncut SHELL | the round-2 carve rules themselves: (c) asks whether any carve these rules allow could remove the overlap |

- A failing frame is **`pose_impossible`** (check and numbers recorded): the pair is out of carve scope at that frame, S
  is not required there, and the frame goes to `push_list_fi5r2.json` for the pose lanes (pair, frame, check, numbers,
  the F-I5.7 rigid shift when computed). The exact SHELL-mesh numbers for (a) and (b) are reported beside the box
  numbers (the boxes stand up to 1 mm off the surface).
- T_rest = the mean pose over the hands-off static segments whose S frame passes; no passing S frame: the pair is not
  carved (`pose_impossible_all`), its default is delivered.
- (a) and (b) are necessary conditions for S, not sufficient ones; S on the faithful reference (21.13.5) is the
  sufficient check. The precheck is also evaluated at round 1's S frames (ep12 f6, f176; ep13 f146; ep31 f282, f8;
  ep11 f126; ep2 f24, f328) for comparison with verify_cc_1 (P77, P78).

#### 21.13.5 Faithful reference and the physical delivery floor (item 4; F-I5.15 (4))
- **Why the reference is not 2 mm boxes for cups [E, geometry, stated before any run].** On a cup wall tapering at
  alpha = 3 deg, a radial gap delta lets the guest drop delta / tan(alpha), about 19 delta (the ev10w mechanism). 2 mm
  boxes stand up to 1 mm off each surface. Polygon rings have the same problem in a milder form: a tangent receiver
  ring and an inscribed guest ring leave a radial gap of up to rho (1/cos(pi/N) - 1) where their vertices line up: 0.66
  mm at rho = 33.7 mm (the x1 host) and 16 sectors, about 12.6 mm of drop on 3 deg. With 64 sectors the gap is
  0.0012 rho (0.04 mm, under 1 mm of drop).
- **Faithful reference collider** (S reference only, never delivered): a route-2 object = the round-2 rings at N_s = 64
  with bands <= 10 mm, no cap, plus its handle hulls; any other object = the SHELL's 2 mm boxes. Carved receivers: the
  same carve applied to the 64-sector rings (lathe), or the 2 mm boxes of the carved SHELL (boolean).
- **S_ref** = S (the F-I5.5 setup and the same 16 jitters) on the references of both objects.
- **Floor**, per object and round folder:
  1. the delivered pieces keep >= f_keep = 0.5 of the SHELL's exact volume (union of the pieces intersected with the
     SHELL, exact manifold boolean);
  2. at every floor S frame of every pair that passes the precheck and where S_ref passes, S on the delivered pieces
     passes (4 mm, 5 deg). Floor S frames: for every pair, in or out of carve scope, the middle frames of up to 3
     longest hands-off static segments (F-I5.3 (b)) of its static stretches (F-I1.1) in which the faithful colliders are
     within 4 mm of each other; receiver by containment (F-I5.3 (a)) on the faithful colliders. No such frame:
     `s_floor_vacuous`, reported.
- Failing (1) or (2) anywhere: **`DO_NOT_USE.json`** in the round folder (rule F-I5.15 (4); per object the share, per
  pair and frame the precheck, S_ref and S numbers). A default failing the pieces gate still makes the folder
  do-not-use (F-I5.6).
- **Round-1 folders:** `DO_NOT_USE.json` labelled post hoc in the five scratch folders
  `runs-dev/20261031-fi5pub-3053a78/sim/public/ep*-fi5/r0` (F-I5.15 (4) applied from diagnostic F-I5.14 (7) and
  verify_cc_1 B2; delivered boxes 1.8-9.3 % < 0.5; a file added, nothing overwritten; verify_cc_0 N1), with copies next
  to their manifests in `build/I/results/collcarve-public/ep*/r0/`.

#### 21.13.6 A real nest? (item 5; F-I5.15 (5))
- [M] Public roster (names only): ep11 (blue cup, beige cup) is the only episode with two cups; the other cup episodes
  pair the blue cup with the rack (ep12, ep13) or the pitcher (ep21, ep22).
- [M, verify_cc_1 B3] With our v6 inputs ep11 is not a nest: both SHELLs are bottomless and at the rest frame both
  stand on the table, axes 2.8 mm and 1.7 deg apart.
- [R, another lane, not an input] The C1/T1 census on library-anchored tracks (tier P1) puts the beige cup inside the
  blue cup's box from t >= 62 and nested from t >= 68. [H] ep11 shows a real nest that our tracks and SHELLs do not
  represent; falsifier: L0 below.
- So **the nest is tested on synthetic cups only** (T-I14 n1-n6), and **eval 10 (beige in blue, 3-5 mm off axis) is the
  only real nest, with no usable public twin**.
- **L0** (report only, decides nothing, for the pose lanes): per ep11 cup, the 99th-percentile height above our table
  of its owned v6 points over the hands-off static frames of the assembled stretch, and the difference (P90).

#### 21.13.7 The five decisions of 21.10 (item 6; F-I5.15 (6))
1. **Carve geometry = D2 as a rule.** Per guest piece g: K = hull(T_rest offset_c(g), shift(s_min d) T_rest
   offset_c(g)), s_min = min(0, min of s_f over the build frames entering R) (F-I5.13 (a)): the rest pose plus the
   straight approach channel along d; frames deeper than the rest and lateral or rotational deviations are not carved.
   T_rest from 21.13.4. No T_rest: not carved (`no_rest`; the raw-frame union of F-I5.3 (c) is what failed F-I5.12).
   Lathe carve: band edges at each sector's carve bottom and top (D2 (b) as amended) are added to the default edges and
   the cap rule of 21.13.2 is re-run with them forced.
2. **Clearance from the guest's wall band.** c = 0.5 x s_max x sigma_wall, floored at c_min = 0.05 mm, capped at c_max =
   1.0 mm, rounded down to 0.05 mm; sigma_wall = the 99th percentile of max(0, n . g) over the guest's union-boundary
   surface samples (0.5 mm) inside R+ at T_rest that belong to its wall band.
   - Union boundary: a sample on a facet lying inside or on another piece (non-strict, 1e-7 m) is internal and dropped.
     Shared faces between stacked band pieces have n . g = +-1; the round-1 sampler kept them (strict test), which can
     alone give sigma = 1 and c = 1 mm [H, P91].
   - Wall band: samples outside the base cap; base cap = samples within max(3 sigma_g, 2 mm) of the guest's lowest
     point along g at T_rest, plus the samples on a route-2 guest's base pieces. No wall-band sample in R+: the base
     cap's samples are used (a seat; c = 1 mm, as on a lid rim).
   - Worked value [E]: 16-sector rings on a 3 deg taper, axis along gravity: sigma_wall = sin 3 deg = 0.052, c = 0.10
     mm, predicted drop c / sigma <= 2 mm.
3. **Topology on a 1 mm grid.** Cell centres inside the union of pieces (exact half-space test), default and carved on
   the same grid; components C (26-connected), tunnels T = C + V - chi (chi = Euler number at 26-connectivity, V =
   enclosed voids = 6-connected background components - 1). Fail (`topology_fail`) only when C or T increases.
4. **Wall integrity instead of the 10 % / 0.6 caps (non-plate receivers).**
   - (a) Min remaining wall: rays from the surface samples (0.5 mm) of K inside R+ that lie inside the default receiver
     collider, along K's outward facet normal. Where the default wall chord through the sample is >= w_min = 1.5 mm,
     the carved receiver's material from the sample outward must be >= w_min.
   - (b) Removed share: removed exact volume <= s_rm = 0.5 of the default collider's exact volume.
   - Failure: `wall_integrity_fail`, default delivered. P4 keeps its over-removal clause (removed <= 1.5 x the carve
     inside the default collider); its ">= 90 % kept" clause is the old volume cap and is replaced by (b). Plate pairs
     keep F-I4.
5. **Exact clip.** K inside R+ = the convex fragments of every K piece clipped by the maximal boxes of R+ (exact), used
   by the lathe carve (its LP over the fragments' vertices) and by the boolean route; replaces F-I5.11 (3), which
   carved 19.5 cm3 for 0.39 cm3 on x2c.

#### 21.13.8 Off-axis nests (item 7; F-I5.15 (7))
A pair whose guest and receiver both take route 2, with the guest's axis at its lowest wall height inside the
receiver's cavity at T_rest, is a nest; e_ax = that axis offset, t_min = the receiver's thinnest default wall left over
the overlap heights. **If e_ax + c > t_min - w_min the pair is not carved** (`off_axis_nest`): default delivered, rigid
shift on the push list, the pose correction is the remedy. Eval 10 (e_ax 3-5 mm, 4 mm wall, t_min about 3.3 mm at 16
sectors): not carvable. Any other wall breach is caught by decision 4.

#### 21.13.9 Records fixed before any delivery (code, no rule change; 21.12 item 8)
`sources/` in F-I5 rounds (V0 N2); the carved receiver runs routes 2, 3, 4 (V0 N3); `decision_flag_off` from
`decisions.json`, `decision_f_i3` renamed `decision_f_i3_logic_on_colliders` (V0 N4); F-I5.7 for every pair, one-
sidedness from the structure axis when route 2 failed, the shift on the push list (V0 N5); per-copy S rows for every
variant (V1 N1); exact volumes, centres of mass and inertia from the hulls (V1 N2); guest records tier T1 with
`owner_waiver_fi5`, all three waiver quotes in the manifest (V0 N12); `launch_code` at launch, diagnostic launch times
logged (V0 N9, N10); a table line in the side views (V1 N9). **Unchanged, stated:** the moves-through sweep gate
(F-I5.2; 21.12 item 6 is not decided), the receiver rule, P2, P3, P5-P7, the keep-out gate, P1 with the Embodiment
session, the masses (0.3 kg placeholder).

#### 21.13.10 Constants and their origins
| constant | value | origin |
|---|---|---|
| construction rays | 1 deg x 1 mm | generic: F-I5.10's continuity azimuth step; the 1 mm topology pitch |
| sector set | 8, 12, 16, 20, 24, 32 | generic: multiples of 4 from F-I5.10's fallback 8 to twice its default 16 |
| wall bands | greedy splits at 1 mm levels, common to a run's sectors | generic |
| base bands | <= 30 mm | generic, F-I5.10 (`lathe_collision.py` default) |
| piece cap | floor(165 / objects) | informed, F-I5.4 / F-I1.14 (P5 limit 165) |
| min wall w_min (rings and carves) | 1.5 mm | generic: one cell of the 1 mm grid samples a wall without holes (naive digital plane, Andres et al. 1997) plus half a cell for curvature and centre-inside sampling; D2's thinnest intact wall was 1.7 mm [M] |
| construction intrusion | <= 1e-6 m | generic, numerical |
| continuity rays | 0.5 mm x 1 deg (offset 0.5 deg); axial 1 mm x 1 deg | generic, F-I5.10 |
| covered / gap share / ring row | >= 50 % of the SHELL interval / <= 1 % of rays / <= 50 % of a height's azimuths | generic |
| CoACD | 0.02, auto, max hulls floor(cap / 2), repair to the cap | 0.02 and auto generic (F-I5.10); floor(cap / 2) the orchestrator decision (room for the repair) |
| keep-out gate | 0.3 cm3 per hull, K weight 10, FREE weight 1 | informed, F-I1.14 / F-I5.4 |
| faithful boxes | SHELL 2 mm cells, centre inside | the orchestrator decision; verify_cc_1 B2 |
| precheck table / support | 4 mm / 4 mm | informed: s_max, S's own bound (F-I1.14) |
| reference rings | 64 sectors, bands <= 10 mm, no cap | generic: 4 x 16 (radial loss <= 0.0012 r); 10 mm = F-I5.10's carved band |
| floor share f_keep | 0.5 of the SHELL volume | informed: between verify_cc_1's 8-sector rings (45-49 % of body cells) and 16-sector rings (51-68 %), far above round 1's boxes (1.8-9.3 %) [M] |
| S | 4 mm, 5 deg, 16 copies, 2 s, 2 ms, 0.3 kg | informed, F-I5.10 |
| floor S frames | <= 3 per pair; faithful colliders within 4 mm | generic F-I5.5 count; s_max |
| clearance | c = 0.5 x 4 mm x sigma_wall in [0.05, 1.0] mm, rounded down to 0.05 mm | F-I5.10 (half, 99th percentile and rounding generic; c_0 = 1 mm informed, F-I1.14); floor = the rounding unit, generic |
| base cap | max(3 sigma_g, 2 mm) | generic, F-I5.4's wall threshold |
| internal-face tolerance | 1e-7 m | generic, numerical (the round-1 strict test's tolerance) |
| topology grid | 1 mm | the orchestrator decision (21.10 item 3); D2's 1 mm diagnostic |
| removed share s_rm | 0.5 | generic (half): a guard against runaway carves; w_min is the binding wall rule |
| P4 over-removal | 1.5 x the carve | informed, F-I1.14 (unchanged) |
| off-axis | e_ax + c > t_min - w_min | geometry of this entry |
| L0 rim difference (P90 only) | 5 mm | generic (above s_max) |
| everything else | as F-I5.10, F-I1.14, F-I4.11 | |

#### 21.13.11 Predictions (PREREG F-I5.15 (9); after P70 of F-I4.16; [H] unless marked)
| | prediction | falsified if |
|---|---|---|
| P71 | every route-2 object of T-I15 and T-I16: max intrusion <= 1e-6 m on the construction rays and <= 0.3 mm on the continuity rays | above either bound on any object |
| P72 | every route-2 cup and pot: the cap rule picks N_s >= 12 with min wall >= 1.5 mm | 8 sectors, or no feasible set, on any of them |
| P73 | ep11 beige and ep12 blue: the default sets (rings plus handle hulls) pass the continuity check and the pieces gate (21.12 item 1's falsifier) | either fails |
| P74 | every route-2 default set of T-I15 and T-I16 keeps >= 0.5 of its SHELL volume | any below 0.5 |
| P75 | the five racks (ep12, ep13, ep31; held-out ep26, ep27) still fail route 3 and end in route 4 | any rack passes route 3 |
| P76 | the ep31 sweeper and the ep2 lid pass route 3 | either fails |
| P77 [E, verify_cc_1's numbers] | at round 1's S frames the precheck fails: ep12 f6 (a), ep13 f146 (a), ep31 f282 and f8 (b), ep11 f126 (c) | any passes, or fails another check |
| P78 | ep2: every S frame passes (a) and (b) (the lid 60 mm above the table, resting on the pot) | any fails (a) or (b) |
| P79 | no public pair gets a carve delivered | any does |
| P80 | the ep12, ep13 and ep31 folders are DO_NOT_USE (not independent of P75) | any is usable |
| P81 | T-I14 n1 (bottomed 3 deg nest, x1 geometry, guest 0.5 mm radially too deep at rest, sectors half offset): carved and delivered; c = 0.10 mm; S <= 4 mm and 5 deg; topology kept; min wall >= 1.5 mm; removed <= 0.5; P2-P7 and the floor pass | any fails |
| P82 | n3 (n1 + 1 mm lateral offset) carved and delivered; n4 (3 mm) and n5 (5 mm) in the 4 mm wall not carved (`off_axis_nest` or `wall_integrity_fail`), default delivered, shift pushed | n3 not delivered, or n4 / n5 carved |
| P83 [E, geometry] | n2 (n1 with no pose error: no overlap, so nothing is carved), both cups forced to 16 sectors (diagnostic): with the vertices lined up the default lets the guest drop >= 4 mm (about 12.6 mm); half a sector offset, mean drop <= 2 mm; on the 64-sector references, mean drop <= 2 mm | aligned < 4 mm, half offset > 2 mm, or 64-sector > 2 mm |
| P84 | n6 (n1 with 6 build frames 10 mm deeper): no dipped frame carved, delivered as n1 | a dipped frame carved, or S fails |
| P85 | precheck fixtures: p1 guest 10 mm into the table -> (a); p2 guest 10 mm above everything -> (b); p3 co-located wall-crossing cups standing on the table -> (c); p4 = n1 at rest -> passes | any misclassified |
| P86 | floor fixtures: 6 mm boxes -> DO_NOT_USE (share); n1's delivery -> no marker; a delivered set that fails S where S_ref passes -> DO_NOT_USE | any differs |
| P87 | ring fixtures: r1 round-1 construction (8-sector chords) on a 5.4 mm-wall cup -> intrusion > 0 on construction rays and gaps > 1 %; r2 forced 1 mm ring above the base -> ring gap; r3 analytic tapered cup -> intrusion <= 1e-6 m and min wall within 0.05 mm of the formula | any not as stated |
| P88 | n1 carved, S on the 2 mm SHELL-box reference differs from S on the 64-sector reference by > 4 mm or gives the other verdict | both within 4 mm and the same verdict |
| P89 | controls unchanged: flag off (x10), plate pairs (x6), x7 (n2 resting, n4 TRANSIENT, wander), x8, x11; the T-I12 cup-in-rack-slot fixture carved and delivered under round 2 | any differs |
| P90 | L0: ep11's two cup rims differ by >= 5 mm at the rest frames (a real nest the tracks miss) | within 5 mm |
| P91 | the round-1 x1 fixture's sigma_sup = 1 came from shared band faces: with union-boundary samples (base cap kept) sigma < 0.2 | sigma >= 0.2 (the base corner, as F-I5.12 (iv) said) |
| P92 | the dust pans (ep18, ep39, ep40), if the lathe test accepts them, fail route 2 (gate or continuity) and fall to route 3 (B7: 38 % of rotated points in FREE) | a dust pan delivered as rings |

#### 21.13.12 Run order, commands, machine and cost
1. **Build** (this container, after this section and F-I5.15 are on origin; nice, never killing or renicing others):
   `gmg/cavpieces.py` (rings, cap rule, continuity, references, exact clip, CoACD at floor(cap / 2), exact volumes),
   `gmg/collcarve.py` (precheck, S_ref, floor and `DO_NOT_USE.json`, D2 geometry, c, 1 mm topology, wall integrity,
   off-axis rule, the records of 21.13.9), a round-2 driver option (in a new driver file if the shared
   `tools/interlock_dev.py` is busy), `tests/test_collcarve2.py` (T-I14: n1-n6, p1-p4, f1-f3, r1-r3, the P89 controls,
   the P91 diagnostic). Then the post-hoc `DO_NOT_USE.json` in the five round-1 folders. Deviations found while
   building, none a threshold, are logged as F-I5.15 as-built before any real run. [E] T-I14 30-60 min here.
2. **Code frozen, committed and pushed**; then T-I15 and T-I16 on **one self-destroying Vast CPU box** (32-64 vCPU,
   $0.3-0.6/h; `docs/runbook-vast.md`, `ops/vast.sh`; ledger `LEDGER_SESSION=mesh-bold`: show first, planned line before
   create, actual after; stall watchdog 30 min; results pushed or copied off before destroy, destroy confirmed):
   - **T-I16** public ep11, ep2, ep12, ep13, ep31, eval semantics, v6 bundles, v6 M1 hands, SHELL candidates rebuilt
     with `tools/interlock_cands.py` (picks as F-I5.14 (1)), P_sim = P_sel: the F-I5.14 command plus the round-2
     option and `--tag fi5r2`; every launch line, machine, commit and output path goes to `build/I.md`.
   - **T-I15** held-out pieces check (no pair, no carve): the lathe-candidate objects of the other public episodes
     (pots ep0, 26, 27, 41-45, lid ep0, blue cups ep21, 22, dust pans ep18, 39, 40) and the racks ep26, ep27: structure
     test, route ladder, intrusion, min wall, continuity, gate, share.
   - **L0** on ep11.
   - [E] 1.5-2.5 h wall, about $0.5-1.5 with storage and traffic; cap $3 for the round, the shared credit left to the
     other lanes. If the box's estimate exceeds the cap, stop and report.
3. **Results** to `build/I/results/collcarve-r2/` (summaries, records, figures; pieces stay in scratch), the PREREG
   outcomes, then two verifiers and the report.
4. **Eval twins 10, 1, 14, 30 are not in this round.** They need eval bundles (`tools/ev_extract.py`) and an
   orchestrator go after the public verification; then the frozen code and constants, the clean t0 (PREREG A.1, not
   t0_dev), and the precheck alone first (which S frames are possible) before any carve. Nothing is tuned on eval.

#### 21.13.13 Limits and open points (stated before any run)
- **A perfectly tracked nest is not carved and can still sink.** With no overlap there is no component to carve, and
  the polygon gap of 21.13.5 lets the guest drop by up to rho (1/cos(pi/N) - 1) / tan(alpha), depending on how the two
  ring layouts line up (n2). The floor then marks the folder do-not-use. [H, a later round] a seat carve for
  near-contact pairs (gap < c) or aligning the receiver's sectors to the guest's; both are outside the owner's "if 2
  mesh collide" and this decision.
- The SHELL bodies are dev tier (t0_dev = 5.36 mm, fitted on `obs_all`, PREREG A.1); the eval twins need the clean t0.
- The sweep gate (F-I5.2) still decides resting pairs (lid on pot, cup in rack); 21.12 item 6 stays open.
- S runs plain MuJoCo 3.17.0 with the 0.3 kg placeholder mass; FlashCHORD parity is P1's job (Embodiment session).
- The reference for boolean (non-lathe) receivers stays 2 mm boxes, which cannot resolve a 0.1 mm pocket; for cups in
  racks (seats on wires) this matters less than for tapered nests [E].
- Off-axis cups and every `pose_impossible` frame go to the pose lanes; nothing here corrects a pose.
