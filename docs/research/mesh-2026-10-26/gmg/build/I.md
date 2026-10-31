# gmg I: INTERLOCK stage (slot / seat / cavity geometry) — working notes

Started 2026-10-31 ~09:10 UTC. Owner (31 Oct ~09:00 UTC): "how do you expect the wooden blocks to interlock in a
physical simulation without the slot?" Deliverables: `INTERLOCK.md` (design, owner-readable first page) and a dated
PREREG section F entry; commit + push to `claude/bold-albattani-6qmxsv`. Design only in this step. Build 1 owns
B2-B7 files; the placement slot (P workflow, `PLACEMENT.md`) runs in parallel: coordinate, do not duplicate.

## Log
- 09:10 read STATUS head, SPEC 0-16, PREREG A, B.7-B.15, E, F; P.md (placement slot started 08:45). No I.md existed.

## ORCHESTRATOR NOTE (31 Oct 08:47 UTC): the Embodiment session replied; read `build/embodiment-reply-20261031.md`
Use their proposed intrusion export fields (or state ours), their sim-copy layout (`DIR/<obj>/<obj>.glb + piece_*.obj`
for `make_assets.py --pieces`), jittered-mean judging, and add a minimum frame count + relative-motion check to the
carve rule.
- 08:50 (agent of wf_c7bae0ea-5c5; earlier entry times above are approximate) read work log 1460-1575, 3190-3200, 3705-3812, 4010-4065, 4436-4510, tail; ledger
  boards/XCarve rows and lessons; README 90-125, 285-350; SPEC 0-18; PREREG B.7-B.15, E, F; the Embodiment reply
  (`embodiment-reply-20261031.md`): use their export fields (frame, target, partner, pts_local, depth_m,
  pushed_residual_m), their sim-copy layout DIR/<obj>/<obj>.glb + piece_*.obj, jittered-mean judging, and add a
  minimum frame count + relative-motion test to the carve rule. Next: interaction-meshes design docs, the pipeline
  carve code, other sessions' branches, dev data probes.
- 08:58 probes (dev, GT-free; scratchpad `interlock/`): ep24 dev bundle (obs_all + our tracks) + B5 dev candidates.
  [M, dev] board 1 <- board 2: 56 of 79 contact frames enter board 1's HULL (f164-274), partner travel 118.6 mm,
  straightness 0.91, along board 1's width axis; entered region (>= 10 frames) sits at 0.53-0.58 of the long axis,
  12.5 mm wide (7.1 mm at >= 28 frames), spans the full width; its entry half spans 0.01-0.48 of the width (one edge to
  the middle). Board 2 <- board 1: same frames, travel 118.9 mm, straightness 0.92, entry half 0.49-1.05 (the other
  edge). 100 % of entered voxels are OBSERVED in the dev depth grid (stereo bridging and/or obs_all contamination):
  a naive "never carve observed-solid" rule would block every slot -> silhouette / bridging-prone clause needed.
  [M, dev] V2 does not catch it: HULL n_median 8 / 13 vs thresholds 39 / 65 (median over all 79 contact frames dilutes
  the 56 intrusion frames); board 2 shell is V5 flip-risk (amb 4.12 vs floor 2.34) -> HULL picked.
  [M, dev, generator outputs] SAM 3D boards (4 runs): slot centred at 0.50 of the long axis, from one edge to 0.42-0.48
  of the width, width 1.2-3.0 % of the long axis (narrower than a board: SAM gives side/length, motion gives width).
  Pixal3D-MV board 2 copied the partner board (a perpendicular plate: V2 (b) case).
- 09:02 pair probe (dev, `interlock/probe_pairs.py`, partner samples deeper than the V2 band b inside the candidate):
  ep24 b = 8.0 / 7.7 mm -> 0 deep samples in either board's shell or hull, although the partner passes through in 56
  frames: a sample inside a 10-20 mm plate is at most half the thickness deep, so any depth-below-surface test with
  b >= half thickness is blind to plate crossings -> the interlock check must be volume/through-crossing based.
  ep2 pot <- lid: HULL deep entry in 54 frames, travel 20.2 mm, straightness 0.61 (a seat, not an insertion), region
  1.6 cm3 OBSERVED, depth 6-7 mm (push-feasible); shells 0. ep11 cups: 0 at b = 8 mm (dev overstates separation).
- 09:04 design decisions: carve rule splits a region into R_U (FREE/UNKNOWN: mechanism-4 logic + persistence +
  topology guard, no motion needed) and R_O (OBSERVED: needs insertion sweep + push-infeasible + silhouette see-through
  or generator+motion agreement on a narrow gap + budget). Submitted mesh only via ICARVE candidates judged by S1
  (VI veto, VF flip guard, paired E exclusion) at tiers with two agreeing sources incl. an observational one; sim copy
  always. V5 clarification: HULL never counts as the non-flip-risk alternative (SPEC section 8 "fallback only").
  Writing INTERLOCK.md now.
- 09:15 INTERLOCK.md written (sections 0-15) and PREREG F-I1 appended (F-I1.1-F-I1.14). Probe code and outputs copied
  to `build/I/` (commands: `GMG_MODE=dev GMG_RUN=<scratch>/gmg/runs-dev/20261030-b5pool24-edba5b3 <scratch>/venv/bin/python
  build/I/probe_ep24.py` (and `probe_ep24b.py`); `probe_pairs.py <devrun> <ep>` for 20261030-b5pool11-edba5b3 11,
  20261030-b1ep2-a7d4d64 2, 20261030-b5pool24-edba5b3 24; `sam_slot.py` on the 29 Oct generator outputs; machine:
  this cloud container, 4 shared cores; code base de64bd3; dev tier, no scan). Rule changes during writing: carve rule
  reordered (O share > 25 % -> PUSH first), push test = median over the frames R is entered, R_O needs >= 75 % SIL/GAP
  and carves only those; GAP no longer needs (a) (stereo-solid narrow notch, silhouette absent, topology kept) but
  submitted candidates still need T2/T3; V4t conditional like V5. Next: commit + push.
- 09:20 committed and pushed `2eb8397` (INTERLOCK.md, PREREG F-I1, build/I probes). Design step done; next per the
  workflow: adversarial review of INTERLOCK.md / F-I1, then build BI1 (interlock.py, silhouette.py, physcheck.py,
  simpieces.py, gen_slot.py, tests/test_interlock.py) in new files only. Open: clean ep24 bundle (B4 batch v4, stream
  3) for T-I2; FlashCHORD venv absent from this container (proxy test needs `mujoco` in the gmg venv).
- 09:30 review round 1 received (B1-B7 + 14 non-blocking). Read: determined-wright physics README (phys_fit v1 ran on
  the public scans with props_public_scans.json; phys_fit.py loads `{meshes}/{n}.glb` and needs com_m/inertia),
  origin/main carve-20261030 BUILD.md + RETRAIN_PLAN.md (E1 lid sinks 0.6-1.0 cm with 6 mm free travel; E30 sweeper
  falls through, > 40 mm free travel, 35 % hull lost; v3 'ends' falsified; settle chaotic; 165-shape budget, E28 208;
  shared /content/assets leaks carves across evals), props_masses_only.json (masses = shell model on the scans' area x
  video materials: scan-derived). Checked [M, 09:33]: gmg venv lacks mujoco AND coacd; ep24_a.mp4 is in the scratch
  store. Re-ran the reviewer's `review_I/gapw.py` (outputs `interlock/rev2/gapw.out`): confirms board 1 HULL region
  thinnest 8.6 mm (inscribed 11.3), board 2 HULL 23.8 mm (inscribed 16.0), shells 8.9 / 4.0 mm, nmin 14-15, camera
  range 0.514 / 0.504 m, fx 600.2. Dev S1 picks exist for 4 objects (B5 pools ep11, ep24); the V5 clarification
  changes only wooden_piece_2's. Writing INTERLOCK v2 + F-I1 revision now.
- 09:55 INTERLOCK.md v2 and PREREG F-I1 v2 written (F-I1.0 added: SPEC section 14 override named; F-I1.1-F-I1.14
  revised). Main changes: P_sel vs P_sim pose sources (sim copy follows the replayed reference; eval 25 = packed
  ev25idfix reference; eval IDENTITY_SWAP flag-only per SPEC 7); build/check 10-frame blocks; true through-column split;
  image-plane GAP (8 depth px ~ 13.5 mm at 0.50-0.51 m); decide_pair (linked components both-or-neither); w_sim >= the
  partner's sim collider thickness; OFFSET rule (observed notch N moved by a lateral t <= 20 mm into the sim copy,
  tracker hand-off, submitted only at T2o); disagreeing source blocks submission; physical acceptance P1-P7 for every
  carved pair (16-copy settle, free travel <= 4 mm, replay proxy, over-removal, 165-shape cap, no new overlap,
  held-out overlap); per-episode asset folders; contract v2 (union of pieces in file coordinates, fiducials,
  containment, reference/fit provenance, NaN forcing; _fit/<obj>.glb + props_gmg.json delivered); VI relative to the
  best candidate; flip units inherited; V5 clarification guarded at R1 (dev: only wooden_piece_2 changes); tolerance 0;
  masses placeholder until owner decision D-I1; predictions P27a-c, P28, P29, P32, P34 rewritten so they can fail.
  Not run (stated in INTERLOCK 16): silhouette gate T-I2a, decide_pair on ep24 T-I2b. Next: commit + push; then BI1.

## ORCHESTRATOR NOTE (31 Oct 10:00 UTC): priority input, read `build/keen-heisenberg-priority-20261031.md`
After ep24, run the dev interlock on the rack seat / cavity cases before ep2/ep11 if time allows: ep31 (sweeper in the
rack; eval 30 twin, largest spread) and ep13 (cup in the rack; eval 14 twin). Report the free-travel result for the
sweeper in the rack (October's rack carve dropped it 2.5-3.5 cm).

## BI1/BI2 build (agent of the build workflow, started 31 Oct 09:53 UTC)
- 09:53 read I.md, INTERLOCK.md v2 (all sections), PREREG F-I1 (F-I1.0-F-I1.14), bundle/contact/geom/guard/pack,
  producers, pipeline/interaction_carve.py, collision_decomp.py, make_assets.py, the Embodiment reply. Load 8.9 on 4
  cores (build 1). [M] Installed into the gmg venv: mujoco 3.17.0, coacd 1.0.14 (pip, 09:58). FlashCHORD venv: not in
  this container and not rebuilt (LFS assets + Newton/warp stack; too heavy next to build 1) -> P1 runs as the plain-MuJoCo
  pre-check only (INTERLOCK 6.2 says the pre-check does not decide); P3 (replay proxy) is plain MuJoCo by design.
- Data found [M]: CLEAN ep24 and ep2 bundles exist (B4 batch v4, `gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep24`,
  `ep2`; ep11 not yet). Dev bundles: b5pool24 (ep24, obs_all), b1ep2-a7d4d64, b1ep11-a7d4d64. Video: `data/store/ep24_a.mp4`,
  `ep2_a.mp4`, `ep11_a.mp4` = ego cam_a (2028x1520, fx 1150; chain rect-left -> cam_a from `pipeline/hands_mp.geometry`,
  stereo frame k = cam_a frame k + 1). SAM 3D board meshes of 29 Oct were generated from ep23 crops (dev only), unit-normalised
  (L ~ 1.0, no saved layout): placement in our frame is by our depth (scale + rigid ICP, flip by depth residual).
- Note: PNGs go to `build/I/png/` instead of `build/i/`: a sibling folder `build/i` next to `build/I` collides on
  case-insensitive checkouts (macOS, Windows).

## ORCHESTRATOR NOTE (31 Oct 10:12 UTC): ep31 evidence added to `build/keen-heisenberg-priority-20261031.md`
The sweeper-rack contact at lift-off (ep31 f~45-53) is where the eval-30 draws split; make the ep31 seat and its
free-travel test (sweeper lifts out of the rack without knocking it) part of the dev report.

## ORCHESTRATOR NOTE (31 Oct 10:50 UTC): Embodiment's answers, see `build/embodiment-reply-20261031.md` (second reply)
P_sim for ep13 / ep31 = orcB perceived references `runs/20261030-orcB-38234d1/refs/glockt/ep{13,31}` (validate their
provenance with the section-11 validator; the orcB mocap "O" arm stays refused); ep24 path to follow. They run A3
(jitter_check --k 16) on our pieces dir. props_gmg.json must match `docs/research/physics-2026-10-30/props_masses_only.json`
(on their branch origin/claude/determined-wright-3joens if not on ours).

## ORCHESTRATOR NOTE (31 Oct 10:52 UTC): eval references + pack mesh set, see `build/focused-pascal-eval-refs-20261031.md`

## ORCHESTRATOR NOTE (31 Oct 10:55 UTC): intrusion.py exists (determined-wright 759032e); resolve their 5 open points
See the third message in `build/embodiment-reply-20261031.md`. Decisions (orchestrator, record in INTERLOCK.md section 11
as a dated "11.8 Resolutions" note and in DEVIATIONS if code-relevant):
1. manifest.json: adopt their layout `objects.<obj>.{files, fiducials}`; define the fiducials exactly (which 8 points,
   and "1 mm inward" = along the inward normal of the union surface, or drop it) in simpieces.py + INTERLOCK 11.2.
2. Reference poses for validate step 1: add a dedicated guard role for OUR reference parquets (store refs/ of our runs,
   reading only the object-pose columns the reference writer produced; the public dataset parquets stay refused), OR take
   the f_star pose from the provenance chain's poses.npz (role tracks). Choose one, test it, keep public parquets refused.
3. Provenance: existing references have no chain. Accept a RECONSTRUCTED provenance (run id, commit, job log lines and
   input sha256 from the store run folder), flagged `prov_reconstructed`, as long as the chain shows no mocap / scan /
   align / library_v1..v4 object-motion source; future references get mkref-written `.prov.json` (Embodiment side).
   Remove `poses_world_vo.npz` from the required list if mkref does not read it.
4. `--fit_commit` is fine. 5. Approximate pushed_residual_m is fine; it only feeds PUSH, and our proxy remains.
Then make the validator pass on their real ep24 export (r0 built from our pieces) as part of the dev run.
- 10:00-11:05 BI1 code written (new files only): `interlock.py` (region builder, decide_pair, OFFSET, agree/tiers,
  carve solids, ICARVE, export writer, validate, carve_from_intrusions, load_sim, round_accept, CLI), `silhouette.py`,
  `gen_slot.py`, `physcheck.py`, `simpieces.py`, `simphys.py`, `tools/interlock_dev.py` (dev driver),
  `tools/interlock_cands.py` (CPU candidates for a clean bundle via build 1's producers), `tests/test_interlock.py`.
  Implementation notes: `geom.inside` falls back to the exact float32 winding sum for ALL points on one disagreement
  (tens of minutes on 2 mm grids) -> `interlock.fast_inside` (median of 3-axis signed crossings for watertight
  meshes). The headless OpenCV has no `cv2.ml` -> numpy EM for the GMMs. Convex-hull cavities by half-spaces
  (Delaunay find_simplex took 580 s).
- [M, dev, b5pool24 obs_all bundle] decide_pair on HULLs and shells: both boards INSERTION (154.9 / 148.1 mm,
  straightness 0.91), components 542/472 voxels (hull), 296/165 (shell); image widths 15.7/15.0 px (hull),
  11.2/13.1 px (shell) > 8 -> class O 97-100 % -> PUSH (step 2); push median 29 mm (not pushable). Silhouette on the
  dev bundle: gate fails on both (board 1 accuracy 0.904 but false see-through 2.65 %; board 2 accuracy 0.898).
- [M, dev process on the CLEAN B4 v4 bundle, run `gmg/runs-dev/20261031-i2probe-626ce13`] candidates from build 1's
  producers (shell 3832/3940 faces, hull 3866/3862, all watertight packed). Board 1: no qualifying silhouette frame
  (33 of 34 separated good frames have a hand within 16 px). Board 2: gate PASSES (held-out accuracy 0.917, false
  see-through 0.27 %, 9 frames). Runs: board 1 <- 2 INSERTION f164-274, 122.3 mm, 0.908; board 2 <- 1 f162-274,
  127.7 mm, 0.915. SAM 3D placement by depth: the clean OBSERVED samples of board 1 span 417 mm (grid voxels far from
  the board) -> placement now uses the samples within 6 mm of our pick; residual 1.3 mm, flip margin 0.0-0.01 sigma
  (side unresolved, as expected for a near-symmetric board).
- T-I1 (synthetic) first runs found 5 misses, each fixed and logged as PREREG F-I2 (code/measurement fixes, no rule
  threshold changed): (1) across axis n = the component's thinnest axis picked the TARGET's thickness when the target
  is the thinner plate (w_sim 24.5 mm for a 6 mm partner) -> n from the partner's evidence near the crossing;
  (2) the partner's evidence is its observed surface (interior UNKNOWN), so the region is hollow and its image width
  too small (t = 18 mm gave 8.0 px, pre-registered 10.8) -> image width on the region closed in 3-D;
  (3) a 4 mm voxel straddling the slot edge is "seen solid" by its centre pixel (s1 t = 6 mm: 36 of 96 voxels O) ->
  silhouette votes also on the 2 mm sub-grid, a voxel is SIL if any sub-voxel is; (4) a hollow cup region leaves the
  unseen core as a separate component (topology guard -> PUSH) -> unseen orphan components inside R's hull are carved
  with R; (5) carve width w was not applied to non-plate regions -> width applied to every carve solid. Sweep s0 now
  passes as pre-registered (GAP + CARVE for 6/10/13 mm, class O + PUSH for 18/25 mm; widths 9.3-14.7 mm).

## ORCHESTRATOR NOTE (31 Oct 10:55 UTC): resolutions accepted by Embodiment; WE reconstruct reference provenance from
store run logs (mkref unchanged before the freeze). Eval 10 intrusion result (carved ev10 vs library cups) will arrive.
- 11:05-11:45 T-I1 complete for the run cases (12 tests OK, 1 expected failure = the logged P26 miss s1 t = 6 mm,
  F-I2.14); export round trip validates and a 3 mm fiducial shift is refused. Commit `18b9d07` pushed (BI1 code,
  tests, F-I2). Contract section INTERLOCK 17 written (as-built interface, export keys, delivered layout).
- BI2 ep24 (clean B4 v4 bundle, shells as picks after the V5 clarification; run `20261031-i2probe-626ce13`, tag t2,
  code 18b9d07 + the fixes listed in F-I2): decisions [M, dev process]: board 1 <- 2 split (through-column), region
  67 voxels, class O 97 %, image width 9.0 px (> 8) -> PUSH; board 2 <- 1 split, 118 voxels, U 41 / O 77 (all 77
  testable-solid in the silhouette) -> PUSH; (a) SAM 3D notch AGREES with (c) on both boards (centroid <= 10 mm,
  axis <= 15 deg, >= 50 % overlap), side unresolved (flip margin 0.00-0.01 sigma); (b) on board 2 DISAGREES (sees
  wood where the motion region is). DIAG counterfactual (forced split at the shared plane, w_sub, never delivered):
  slotted shells watertight, 3892 / 4000 faces packed; replay proxy (MuJoCo, 4 copies): default pieces lag 1.86 cm /
  112.9 deg at the assembled frames (the cross cannot close), DIAG carved 0.34 cm / 9.3 deg, contact off 0.03 cm /
  0.1 deg -> the carved copy slides in but stays 9.3 deg off (P3 needs <= 5 deg). Default pieces 32 per board (cap),
  CoACD 15 each. The proxy runs in ~1 s per copy here (not 248 s).
- ep2 first attempt crashed (MemoryError): the generator closing radius used the partner pick's thinnest extent (a
  pot's diameter); capped at t_max = 20 mm (F-I2 addition). physcheck interpenetration now uses a 1 mm occupancy grid
  per candidate (exact per-frame inside tests took ~2 s per frame). Restarted 11:47.
- 11:36 (observed 11:48) build 1's B4 wrote the B.15 cross identity test into the clean bundles in place
  (`episode.json` of ep2/ep11/ep24 modified 11:36:26; grids unchanged): ep24 BOTH boards IDENTITY_SWAP (board 1's
  shell is nearer ep24 board 2's than its own: 2.8 vs 18.0 mm; the boards are near-identical), ep11 blue cup
  IDENTITY_SWAP, ep2 none. Under F-I1.2 (public) IDENTITY_SWAP makes (c) absent -> the ep24 `final` run decides
  IGNORE for every board region (T0, no carve). Added `--identity eval` to the driver (SPEC section 7: on eval the
  identity test only flags) and launched `evalsem`: the same rule as on eval 25 with the same geometry. Our 11:10 t2
  run read the bundle before the flags were written (same grids).
- Visual check of (b) [looked at, not a measurement]: `interlock/bi/sil_ep24_b1.png`, `sil_ep24_b2.png` (copied to
  `build/I/png/`): the motion region R lies on the slot visible in the RGB frames on both boards (board 1 standing in
  the hand, board 2 on the table), from the edge to about the middle. Through the slot the camera sees the BROWN
  WOODEN TABLE, which the colour model cannot tell from the light wood: board 2's testable silhouette calls the slot
  solid ((b) disagrees), and board 1 has no qualifying frame (a hand within 16 px in 33 of 34 separated frames).
- 12:00-12:35 runs and incidents [M]: ep2 t2 was OOM-killed at 9.9 GB RSS in physcheck (1 mm occupancy grid of the
  pot, ~6 M cells) -> occupancy grid capped at ~2 M cells and `fast_inside` chunked (250 k). Both ep24 runs (final,
  evalsem) sat > 30 min in physcheck: board 1's packed HULL is not watertight after trimesh's vertex merge, so
  `fast_inside` fell back to the exact solid-angle sum on 1.44 M points -> signed crossings for any query set
  > 20 k points. Killed runs kept as `interlock/public/*-killed`. Relaunched ep24 evalsem and ep2 (tag t3) 12:29.
- ep24 DIAG counterfactual (evalsem, 16 jittered copies; never delivered): replay proxy default 1.85 cm / 113.0 deg
  (blocked), DIAG carved 0.33 cm / 9.4 deg (max after assembly 0.77 cm), contact off 0.03 cm / 0.09 deg -> P3 fails
  on rotation (> 5 deg). P2 at frame 246: gravity 3.5 mm, +d 5.0 mm, +n 13.0 mm (fail: > max(4, 0.5 + 1) mm; w_sim
  21.7 mm on board 1 vs a 12.6 mm evidence thickness), -n 0.0. P4 pass (kept 95.4 / 97.3 % of the default collider),
  P6 pass (assembled overlap median 6.9 -> 0.76 cm3), P7 pass (check-frame overlap median 6.8 -> 0.73 cm3). P1
  pre-check (plain MuJoCo, does not decide) fails for default AND carved: the cross is held in the air at the
  assembled frame, both boards drop about 2.1 cm with hands parked.
- P27 on ep24 (clean bundle, dev process; `p27.py`): P27a entry-side share 0.646 (board 1) / 0.580 (board 2) ->
  FAILS (< 0.6 on board 2); P27b (a, c) offset along the long axis -3.6 / 7.1 mm -> passes (<= 10 mm), but the placed
  SAM 3D concavity next to the region is 56-71 mm long along the board's long axis (the closing at r = 12.4 mm fills
  far more than the slot), so its centroid is weak evidence; P27c observed share 0.93 / 0.61 -> passes (>= 0.5).
  slot_summary [M]: motion band 25.1 / 19.1 mm wide along the long axis, spanning the full width (130.8 / 128.2 mm);
  carve side from the edge to 9.6 mm / -5.6 mm past the centre line; SAM notch centroid within 1.3 / 7.1 mm along L.
- ep11 evalsem (clean bundle; blue cup IDENTITY_SWAP on public -> (c) absent there): INSERTION f42-136, travel
  190 mm, straightness 0.92; regions 1214 (blue) and 782 (beige) voxels, class O 52 / 62 % (testable-solid
  silhouette) -> PUSH both; (a) and (b) disagree; one 3-voxel U carve on the beige cup (T1, 0.33 cm3; its pair has no
  carve, so no physics and default pieces delivered). VI at the assembled frames: shells overlap the partner's
  evidence by 100.7 / 73.9 cm3 vs the partner-clipped HULLs 9.1 / 33.3 cm3 -> VI would veto the SHELLS (a HULL win:
  a risk for B10, reported, not acted on). Default pieces of the partial cup shells fill the cavities (union
  697 / 666 cm3 vs solid 172 / 169 cm3; split stuck at the 32-piece cap) -> collider overlap along the track up to
  544 cm3 vs CoACD about 300 cm3: our decomposition is WORSE than CoACD here (open problem for B9).
- 12:29-13:15 final dev runs (code 78570c3 = ed204a6 + run fixes; run `<scratch>/gmg/runs-dev/20261031-i2probe-626ce13`,
  machine: this container, 4 shared cores, 15 GB; tier DEV, zero scan reads):
  - ep24 evalsem (2044 s): `GMG_MODE=dev GMG_RUN=<run> python -m gmg.tools.interlock_dev --run <run> --ep 24 --bundle
    <scratch>/gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep24 --cands <run>/cand/public/ep24 --pick
    wooden_piece_1=shell_t5p36,wooden_piece_2=shell_t5p36 --video <scratch>/data/store/ep24_a.mp4 --calib
    <scratch>/data/calib.json --hands <run>/in/hands24/hands.npz --gen "<4 SAM 3D board plys>" --diag --proxy-copies 16
    --identity eval --tag evalsem` -> PUSH both boards (results in INTERLOCK 18.1).
  - ep24 public semantics (`--tag final`, killed in physcheck at 12:28 after its decisions): IGNORE (c absent:
    IDENTITY_SWAP on both boards) - the decisions were logged before the kill (`drv24_final.log`).
  - ep2 t3 (2482 s; `--pick white_pot=shell_t5p36,white_pot_lid=hull`, ep2 video/hands/SAM 3D, public = eval here: no
    flags) -> PUSH everywhere; ep11 evalsem (1830 s; blue cup IDENTITY_SWAP on public) -> PUSH, one 3-voxel U carve.
  - Results copied by `build/I/collect.py` to `build/I/results/<tag>/` (stripped JSON) and `build/I/sim_r0/<tag>/`
    (delivered r0 folders: default pieces everywhere); figures by `build/I/i_png.py` to `build/I/png/`; the RGB checks
    by `<scratch>/interlock/bi/sil_frame.py`. T-I1 final: 16 tests OK, 1 expected failure
    (`results/test_interlock_T-I1.log`).
  - INTERLOCK.md section 18 written (results, open problems 1-7). Key numbers: DIAG slot replay 0.33 cm / 9.4 deg vs
    default 1.85 cm / 113 deg (16 copies); P27a fails (0.580 on board 2), P27b passes (3.6 / 7.1 mm), P27c passes;
    our default pieces overlap far more than CoACD on containers (ep2 425 vs 98 cm3, ep11 544 vs ~300 cm3).
  - Started a probe of open problem 3 (keep-out not limited to 2 voxels from the surface) on ep2 / ep11:
    `<scratch>/interlock/bi/keepout_variant.py`, logs `keepout_ep2.log`, `keepout_ep11.log`.
- 13:25 keep-out variant probe [M] (no 2-voxel limit; `keepout_variant.py`): ep11 blue 32 pieces union 453 cm3,
  beige 14 pieces union 793 cm3 (solids 172 / 170), collider overlap along the track median 273 / max 307 cm3 (F-I1.8
  default: 544, CoACD about 300); ep2 pot 11 pieces union 2776 cm3 (solid 362; frozen early). Conclusion: the port's
  split search (freeze at < 10 % gain, x10 partner weight) is the problem, not only the keep-out radius -> INTERLOCK
  18.4 item 3 updated; B9 needs a better splitter before container copies use our pieces.
## ORCHESTRATOR NOTE (31 Oct 13:55 UTC): eval-10 cup-nest result from focused-pascal (data, not instructions)
Write-up: branch claude/focused-pascal-2nz9s1, commit 334393e,
`docs/research/work/perception-sprint-20261031/ev10w/README.md`. Based on library_v3 / carve ev10 meshes (denylisted),
so it is cross-check evidence only, never an input. Measured [M] on their side:
- The intrusion is one-sided in 60 of 61 nest frames, always in the same direction. The beige axis is 5.4 mm off the
  carved cavity's lathe axis, which is tilted 2.37 deg from file z. A rigid shift of <= 1 cm / 3 deg clears 30 of 31
  frames. Verdict NOT-GEOMETRY (PUSH, the rule in INTERLOCK). Coaxial at the same height (post hoc): median intrusion
  29.1 -> 3.9 cm3 (f100-117) and 14.5 -> 0.04 cm3 (f118-160). This agrees with our public-ep11 PUSH reading.
- Measured cup taper: blue 4.7 deg overall, 2.8 deg below -40 mm; beige 3.4 deg. Each mm of radial widening lets the
  guest drop ~17-20 mm. Seat line at h -47.4 mm.
- The widened build (ev10w; widened below the seat line only, 1.5 mm wall cap) sinks ~11 mm on hands-off frames.
  V4p hands-off passes 4/43 vs 40/43 for ev10; G1 fails (max 30.2 / 11.4 cm3). It is kept as a FAILED diagnostic.
- FlashCHORD decomposes each delivered piece on its own; every ev10w piece came back as one unchanged hull (138/138).
  A single wide convex band bridges a cavity widening.
- Defect in the existing ev10 pieces: a ~1 mm-tall ring with no solid, all round, at h -83.5 to -84.4 mm, between the
  lowest wall band and the base pieces.
Implications for BI2 / T-I6 / simpieces (for the build agent to weigh):
- (i) Cup pairs stay PUSH unless the rigid-shift test fails. Any cup carve must also pass the sink test, and the drop
  per mm of clearance is ~17-20, so the P2 free-travel bound is the binding check.
- (ii) Lathe-style piece sets need the lowest wall band to reach the top of the base piece, with no gap ring. Add a
  piece-union gap check: no empty band between the pieces inside the solid.
- (iii) Wall bands must be split finely enough around the axis that no piece's hull bridges the cavity.

## Round-1 fix (verifier review of the BI1/BI2 build; agent of the build workflow, started 31 Oct 13:52 UTC)
- 13:52 read I.md, the review (B1-B8 + non-blocking), interlock.py, the driver, tests, simpieces, their
  `tools/intrusion.py` and `pipeline/phys_fit.py` at origin/claude/determined-wright-3joens `48cda9f`, the verifier's
  probes (`<scratch>/verify_I/adv.py`, logs, `zoom_b2.png`: slot about 6-8 mm [E], looked at again).
- 14:00-14:30 code (rule changes = PREREG F-I3.1-F-I3.11, written 14:40):
  B1 validate rewritten for their header (basename or `<obj>/` mesh keys + piece-set equality, `frames` or `T`,
  `fiducials_file`, never raises: refuses), provenance per-step inputs + `prov_reconstructed` + GT / dataset-parquet /
  library-as-motion refusals, the independent f_star pose from `ref_poses` (reader hook for B10) or our tracks when
  their sha256 is the chain's `poses.npz` (frame-free fit: common rigid frame + per-object vertical shift on the
  fiducials, AND rel_T at f_star); props_gmg.json in phys_fit's `{obj: {physics: ...}}` layout; manifest gmg-sim/2
  `objects.<obj>.{files, fiducials}` + code identity (sha256 of the code files, dirty flag); fiducial definition
  documented. B2 `make_side` (one constructor for both paths), sources saved with r0 (`sources/<obj>.npz`) and loaded
  by carve_from_intrusions, export partner samples = partner pieces lattice (n axis, push). B3 cumulative budget vs
  the round-0 solid (manifest `interlock` state), fixed hold-out (`engaged_runs(holdout=)`), round_accept rewritten
  (A1 persistent-at-engaged-check + other-pair/phase gains, nothing computed on an invalid export, A3 pending without
  the external settle, A4 from the folder), round_k checked. B4 submitted solid excludes class O; OFFSET N + t has
  budget (iv) + topology before the pair level. B5 two-way agreement (whole C_a components, reverse share >= 50 %),
  also (a, b) and OFFSET. B6 keep-out gate (ours, else CoACD, else do-not-use; `load_sim` refuses) and the three old
  r0 folders marked `DO_NOT_USE.json` (boards 0.72 / 2.0, cups 945 / 533, pot 1250 cm3 per hull > 0.3). B7 o2 split
  (o2a as pre-registered, o2b new pre-registered outcome), n4 asserted on its runs, contract test through
  carve_from_intrusions, new tests (blob generator, OFFSET budget, validator variants, chain-tracks pose incl. a 3 mm
  re-centring, two-round iteration, pieces gate). B8 F-I2.14 justification, INTERLOCK 18.1 and the test docstring
  corrected (F-I3.11). `simphys.pair_physics` (moved from the driver) = `interlock.default_physics()`.
- 14:14 tests batch 1 [M] (650 s, load 5-9): validator on their header format OK (flags prov_reconstructed,
  ref_sim_assets_library); refusals: no independent pose, no frame count, frames out of range, 15 mm pts_local shift
  (containment partner 0.0), 3 mm fiducial shift (5.2 mm), mocap / dataset parquet / library_v3 poses / scan in the
  chain, chain without poses.npz; meshes with `<obj>/` prefix accepted. Chain-tracks pose: pass with a table-frame
  transform and 2.5 / -2.5 mm vertical shifts; other tracks refused; a 6 mm re-centring gave only 0.63 mm fiducial
  residual (the fit absorbs it) -> added the rel_T-at-f_star check, test now uses 3 mm. Blob generator: (a) disagrees
  (centroid 31.8 mm, axis 89 deg, reverse share 0.03), T1, nothing submitted.
- 14:27 launched the ep24 eval-semantics re-run with the fixed code (tag r1evalsem, no --diag; writes r0 with sources
  and the pieces gate): `GMG_MODE=dev GMG_RUN=<run> python -m gmg.tools.interlock_dev --run <run> --ep 24 --bundle
  <scratch>/gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep24 --cands <run>/cand/public/ep24 --pick
  wooden_piece_1=shell_t5p36,wooden_piece_2=shell_t5p36 --video <scratch>/data/store/ep24_a.mp4 --calib
  <scratch>/data/calib.json --hands <run>/in/hands24/hands.npz --gen "<4 sam3d board plys>" --proxy-copies 16
  --identity eval --tag r1evalsem` (run `20261031-i2probe-626ce13`, HEAD e9f4dbd + uncommitted I files; log
  `drv24_r1evalsem.log`). Test batch 2 (contract same-rule, iteration, pieces gate, o2b, OFFSET budget) running.
- Their real tool: `build/I/contract_ext.py` (not a gmg process) builds an ep24 reference parquet from OUR tracks in a
  table frame (stand-in: their perceived ep24 reference is not in this container, no HF token), runs their
  `intrusion.py` on our new r0, their `phys_fit.py` (max_nfev 3, plumbing) on our `_fit` + `props_gmg.json`, and
  `intrusion.py --fit`; the gmg side then validates and carves. Runs after the driver writes r0.
- 14:31 ep24 r1evalsem decisions [M]: identical to BI2 (board 1 PUSH, U 2 / O 65, image width 9.0 px; board 2 PUSH,
  U 41 / O 77 testable-solid) but (a) now DISAGREES on both boards (two-way agreement, F-I3.5) -> `interlock_disagree`.
- 14:37 pieces gate on ep24 [M]: ours 0.72 / 2.0 cm3 max keep-out per hull (13 / 21 of 32 over 0.3), CoACD 52.9 /
  77.3 cm3 (12 of 13 / 15 over) -> neither complies, the new ep24 r0 is do-not-use (F-I3.8 amended with the numbers).
  The contract test with their tool therefore runs on it with the explicit diagnostic override (flagged).
- 14:40 test batch 2 [M] (802 s): OFFSET budget OK, pieces gate OK; 4 failures, all test-side: (1) the synthetic
  SYN_REF chain `['synthetic test']` is refused by carve_from_intrusions / round_accept (they never pass
  synthetic_ok): tests now use a real chain (tool, run id, a poses.npz input); (2) the re-centring test moved B along
  its x, which is VERTICAL in this episode: the per-object vertical shift absorbed it (rel_T 0.58 mm) -> the blind
  spot is now stated in F-I3.10 and the test re-centres along B's y; (3) o2b: A carves SIL voxels only with
  o_residual_push, B has no class O on its carve side (its overshoot lies past its split plane): my F-I3.6
  expectation "flag on both" was wrong; corrected and logged in F-I3.6, rule unchanged. Re-run 14:41 (t3.log).
- 14:42 ep24 r1evalsem driver done (897 s) [M]: r0 `<run>/sim/public/ep24-r1evalsem/r0` (gmg-sim/2, sources,
  props in phys_fit layout, code identity dirty=True: the interlock files were uncommitted then; their sha256 are in
  the manifest) marked do-not-use by the gate. Board 2's OFFSET now fails budget (iv) (reach 0.81, the N + t carve
  splits the board: components 1 -> 2), so the "OFFSET holds alone" of BI2 is gone; (a) disagrees on both boards.
- 14:43 F-I3.12 column rule added after the o2b probe (`<scratch>/interlock/r1fix/probe/o2b.py`): A's carve reached
  7.5 mm past the slot end through unseen mid-plane voxels; with the rule 1.5 mm. Full T-I1 suite relaunched with the
  final rule code (`<scratch>/interlock/r1fix/full.log`).
- 14:44 WIP commit `1bdb06b` pushed.
- 14:46 found while running the contract: (1) the parameter `round` of carve_from_intrusions shadowed the builtin
  round() (crash when writing the interlock state) -> `builtins.round`; full suite restarted at 14:47; (2) the export
  path took every frame while our bundle has stride 2, so the gate's good share was 0.5 and (c) absent (IGNORE):
  the export's frame-pairs are now restricted to the bundle's census frames (F-I3.1 text). This second change was made
  after the full suite started; it is a no-op for the stride-1 synthetic bundles of T-I1.
- 14:47-15:08 their real tool (`build/I/contract_ext.py`, outputs `<scratch>/interlock/r1fix/contract24/`):
  intrusion.py on our r0 OK (22 s, 227 / 482 frame-pairs, fiducial box margins 1.0 mm), phys_fit max_nfev 3 OK
  (691 s; plumbing), intrusion.py --fit running. Our side (`build/I/contract_gmg.py`, `--allow-do-not-use`):
  e0 VALID (independent pose from our tracks = the chain's poses.npz: residual 0.0, rel_T 0.0 mm); export decisions
  PUSH / PUSH T0 = tracks path; regions differ (pieces vs evidence samples).
- 14:45-14:51 ep31 (sweeper in the rack, eval-30 twin; eval semantics, decisions only, `--no-physics`, 398 s) [M]:
  sweeper <- rack one SLIDE run f18-40 (12 frames, 42.8 mm, straightness 0.55) with a 2-voxel region -> IGNORE
  (`one_sided_region`); rack <- sweeper no engaged run. Shell overlaps along the track <= 0.32 cm3 (sweeper shell,
  engaged frames), rack shell 0.0. No silhouette (no separated good frame: in contact in all 145 frames). Nothing to
  carve or push; the P34 free-travel check was not run (no r0 for ep31 in this round).
- 15:20 probes `<scratch>/interlock/r1fix/probe/same.py` [M]: same decisions and tiers on both paths for s1 t = 10 / 18
  mm (CARVE T2); without a silhouette at t = 10 mm the export path PUSHES (GAP image width 7.0 / 9.0 px vs 5.0 px on
  the tracks path: the export partner is its 10 mm pieces, ours its ~6 mm stereo evidence) -> F-I3.13 known
  difference, test kept as an expected failure; [H] decide export regions from our evidence moved by rel_T.
- 15:37 full T-I1 suite (23 tests, 3152 s): 20 OK, 1 expected failure (s1 t = 6), 2 failures = test expectations:
  the no-silhouette contract case (above) and A1 in the two-round test (the export path's voxel carve is partly
  refilled by our splitter: 435.3 -> 403.5 cm3, -7 %, A1 False = round rejected, which is the acceptance working).
  Tests corrected (A1 checked against its definition, not forced True); re-run of the three changed tests started.
- 15:41 e0fit (their intrusion.py --fit on the plumbing fit, 2598 s): their fit check OK; pushed_residual finite on
  352 / 482 rows, median 65 mm on the intruding rows; our validator VALID with pushed_residual KEPT; decisions PUSH /
  PUSH T0 (class O decides at step 2). Results copied to `build/I/results/contract_ep24/`.

## ORCHESTRATOR NOTE (31 Oct ~16:05 UTC): OWNER WAIVER of the camera rule for the board slot; round-1 workflow stopped
- Owner, verbatim, in session_01W8Softjo2xx7o6ofSiheuQ, 31 Oct ~16:00 UTC: "Okay I waive that camera rule". It answers
  my report that the pre-registered rule PUSHES the ep24 boards because stereo calls the slot "observed solid" (class
  O) and the RGB silhouette cannot confirm it (hand in the way on board 1; not testable on board 2).
- Scope (my reading, to be written as PREREG F-I4 before any run):
  - Plate-plate INSERTION pairs only (the boards).
  - Class O and an absent or failing silhouette no longer block a CARVE.
  - Every other gate stays: INSERTION, persistence, partner moves through, rigid-shift push test, budget, topology,
    physics acceptance, pieces keep-out.
  - Cups, pot and lid are unchanged: the ev10w result says cup intrusions are track errors.
- The interlock workflow `wf_c7bae0ea-5c5` was stopped during its round-1 test re-run (work committed at 58adcd0). A
  focused board-slot workflow continues from here.

## Board slot (owner waiver) (agent of the board-slot workflow, Amend step, started 31 Oct 16:03 UTC)
- 16:03 read I.md (all), INTERLOCK 0-3, 6, 11, 14, 18, 19, PREREG F-I1..F-I3, interlock.py (to decide_pair). Task:
  write PREREG F-I4 + INTERLOCK section 20 (waiver scope, slot geometry from GT-free evidence, plate body, analytic
  pieces, acceptance, delivery), commit + push BEFORE any code runs with it. No run in this step.
- 16:15 design decided (writing PREREG F-I4 + INTERLOCK 20 now; nothing run): plate-like = structure.py plane pair
  (accepted['plate'], slab window 3-25 mm) on owned points within 6 mm of the pick (F-I2.10 filter); t = that pair's
  thickness; body = STRUCT plate if one exists (none for ep24: cand folder has shell_t5p36 + hull only), else the box
  of the observed outline (2 mm raster, >= 3 frames per cell, min-area rectangle, fill >= 0.9) at t; slot w = t_p + 2 mm,
  centre = motion component's centroid along a_L, depth = partner's deepest penetration in R (capped at the shared
  split plane: both slots are bridged, only the sum of depths is constrained) + 2 mm; consistency |D1 + D2 - W_x|
  <= 10 mm; 3-box pieces; acceptance P2-P7 + keep-out unchanged, default = unslotted plate; P1 stays theirs; r0 with
  p1_pending (amends F-I2.12 for this route only).
- 16:16 PREREG F-I4 written (F-I4.0-F-I4.11; predictions P35-P39, T-I1 w1-w5). Next: INTERLOCK section 20 + pointers.
- 16:18 INTERLOCK section 20 written (+ header and section-0 pointers). Committing F-I4 + section 20 now (no code changed, nothing run).
- 16:19 committed and pushed c13f53c (PREREG F-I4, INTERLOCK 20, this log). Amend step done; no code changed, nothing run. Next step (build): platebody.py, --waiver-fi4 branch, P3 overlap clause, T-I1 w1-w5, then T-I11 (INTERLOCK 20.6).
- 16:20 (build step, agent of the board-slot workflow) started: F-I4 confirmed on origin (c13f53c ancestor of
  origin/claude/bold-albattani-6qmxsv). Reading interlock.py / structure.py / simphys.py / simpieces.py / driver / tests.
  Plan: new `platebody.py` (plate test, outline body, analytic slot, pieces), `--waiver-fi4` branch in decide_pair +
  driver, P3 overlap clause in simphys, T-I1 w1-w5; then T-I11 (clean ep24, eval semantics).
- 16:32 [M] first synthetic probe of the build (t = 10 mm, two-sided cameras, waiver on; `<scratch>/interlock/fi4/
  probe_w.py`): plate test 10.17 / 10.12 mm (overlap 1.0), CARVE both (old F-I3 decision CARVE via GAP), bodies
  238.4 x 133.4 mm (true 230 x 125), slot widths 12.12 / 12.17 mm, depths 69.2 / 68.6 mm (split cap), depth sum
  137.75 vs W_x 134.02 (diff 3.7 mm, ok), budget 2.6 % / reach 0.52, keep-out 0.0 cm3 per hull. MISS: the F-I4.3
  slot centre (4 mm voxel centroid of the component) is 2.76 / -2.81 mm from the true slot (w1 tolerance 2 mm) ->
  overlap at the assembled frames 2.69 cm3 -> P3 fails on the restored overlap clause (lag 0.22 cm / 0.5 deg passes;
  4 copies, 87 s). P2/P4/P6/P7 pass.
- 16:33 PREREG F-I4.12 (post hoc, before any real-data F-I4 run): slot centre = the partner's plate mid plane at the
  median assembled pose crossing the slot centre line; the component centroid stays reported and sets the split cap.
  No threshold changed. Committing F-I4.12 + this log before running anything else with it.
- 16:38-16:50 [M] T-I1 Waiver + Controls (code F-I4 + F-I4.12; logs `<scratch>/interlock/fi4/test_waiver.log`,
  `test_w1.log`, JSON `test_waiver.json`, `test_w1.json`): w1 passes at t = 10 / 13 / 18 mm (centre within 0.1 mm;
  component centroid would be 0.76-2.81 mm off; widths within 0.2 mm of t + 2; depth sum - W_x 2.6-4.3 mm; keep-out
  0.0); t = 6 mm misses the width tolerance only (plane-pair t 7.24 / 7.30 -> w 9.30 / 9.24 vs 8 +- 1): known miss,
  expected failure, PREREG F-I4.13 (no rule change); t = 25 mm out of scope (no plane pair at the window's edge) -> old
  PUSH. w2, w3 (n2/n4/n9 identical; 30 mm cylinder partner unchanged; 16 mm rod not plate-like), w4 (o2a/o2b PUSH,
  interlock_slot_inconsistent, diff 22 mm), w5 (16 copies: lag 0.033 cm / 0.16 deg, overlap 0.0) pass; Controls OK.
- 16:50 committing the build (platebody.py, waiver hooks, P3 overlap clause, write_round extra, driver flags
  --waiver-fi4 / --no-physcheck, tests, build/I/fi4_png.py) + F-I4.13, then T-I11.
- 16:52 correction: the four entries above first carried guessed clock times (16:50, 16:55, 17:00-17:15, 17:17);
  replaced by the times from the commits and files (F-I4.12 pushed in 94eed1c at 16:35:26 UTC, build in 1756947 at
  16:50:33 UTC). Order unchanged: F-I4.12 was pushed before the tests that use it and before any real-data run.
- 16:51 T-I11 launched (clean ep24, eval semantics, waiver on; code cd2383f = 1756947 clean for the gmg files;
  machine: this container, 4 shared cores, load ~7): `GMG_MODE=dev GMG_RUN=<run> python -m gmg.tools.interlock_dev --run
  <run> --ep 24 --bundle <scratch>/gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep24 --cands <run>/cand/public/ep24
  --pick wooden_piece_1=shell_t5p36,wooden_piece_2=shell_t5p36 --video <scratch>/data/store/ep24_a.mp4 --calib
  <scratch>/data/calib.json --hands <run>/in/hands24/hands.npz --proxy-copies 16 --identity eval --waiver-fi4
  --no-physcheck --tag fi4evalsem` (run 20261031-i2probe-626ce13; no --gen; log <run>/drv24_fi4evalsem.log).
- 17:00 (scope-fix step, agent of the board-slot workflow) restarted from this log: T-I11 tag fi4evalsem finished
  16:58:48 (454.6 s) [M]: plate F-I4.1 false on BOTH boards (`no_plane_pair`; owned points within 6 mm 1,759,844 /
  1,408,169, after the 2 mm downsample 36,675 / 22,304; sigma 3.0 / 0.74 mm) -> waiver out of scope, decisions as
  r1evalsem (board 1 PUSH; board 2 PUSH interlock_disagree); pieces gate 0.72 / 2.0 cm3 (do-not-use). Next: GT-free
  diagnosis of the missing plane pair (density along the thinnest axis, faces seen per frame), then ONE post-hoc
  PREREG entry F-I4.14, re-run w1-w5, then T-I11 once more (new tag).
- 17:03 [M] GT-free diagnosis of no_plane_pair (`<scratch>/interlock/fi4/diag14/diag_plane.py`, JSON
  `diag_plane.json`; our bundle points, cameras, frames, sigma and our pick only; no slot or physics output read):
  board 1 (sigma 3.0 mm -> 3 sigma band 9.0 mm): BOTH faces seen (42 % of points from the +n side, 38 frames; 58 %
  from the -n side, 101 frames); per-frame median offsets along the thinnest axis +3.88 mm (MAD 0.45) and -3.16 mm
  (MAD 0.32) -> faces ~7.0 mm apart, track jitter along n < 0.5 mm, within-frame IQR 1.75 mm. segment_planes with
  the 9 mm band merges both faces into ONE plane (26,022 pts, two-sided share 0.49, rms 3.7 mm, offset 0.3 mm = the
  middle) -> no pair can form. Cause: the inflated object-episode sigma (B7 bundle had 1.21 mm), not missing faces.
  Board 2 (sigma 0.74): ONE face only (0 % of points from the +n side, 117 frames all from -n); 4 parallel planes
  all seen from the same side (offsets -2.5 / 0 / +2.3 / +3.0 mm); 1-99 % extent along n 12.65 mm (1 % tail at
  -9.3 mm on the camera side = bump; 5-95 % 4.6 mm). Its thickness is not observable two-sided in this episode.
- 17:06 PREREG F-I4.14 written (post hoc, decided from the diagnosis only; no ep24 slot / physics output exists or
  was read): plate test order (1) F-I4.1 plane pair unchanged, (2) camera-side face pair (split the slab points by
  camera side, median offset per face, antiparallel 30 deg, t in 3-25 mm, overlap 0.5, rms <= 3 sigma, both in-plane
  extents >= 2 (t + 2 mm)), (3) one-face plate with t = the partner's measured t (same-stock prior [E]); new
  synthetic w6 (sigma 3 mm merges faces) and w7 (one-face B). Committing + pushing before any code runs with it.
- 17:07 correction: the two entries above and F-I4.14 first carried guessed clock times (17:08, 17:10-17:20, 17:20);
  replaced by the file and commit times (diagnosis JSON 17:03, F-I4.14 pushed in dad65a1 at 17:06 UTC). Order unchanged.
- 17:08-17:10 [M] F-I4.14 build (platebody `_camera_side`, `_down_idx`, `resolve_one_face`; plate flags on the records;
  driver logs the resolved plate info) + T-I1 w6 / w7 (log `<scratch>/interlock/fi4/f414/test_w67.log`, 99 s): **w6
  MISS**: at t = 10 mm with sigma 3.0 the synthetic faces are NOT merged; step 1 (F-I4.1 plane pair) still holds but
  reads 8.07 / 8.39 mm (band-biased), widths 10.39 / 10.07 vs 12 +- 1 -> kept as an expected failure (no rule change);
  step 2's estimator is now checked directly (new test w6b: t = 6 / 10 / 18 mm at sigma 1 and 3). **w7 fixture bug**:
  B's edge points (camera in the plate plane, view along z = float32 rounding of either sign) put a few hundred points
  on the -z side, so B read two-sided and failed the checks (`camera_side_two_sided_fail`), out of scope; fixture
  corrected to keep only the +z face (the w7 scenario). Re-running w6b + w7 now.

## ORCHESTRATOR NOTE (31 Oct ~17:30 UTC): OWNER EXTENDS THE WAIVER TO EVERY COLLIDING PAIR
- Owner, verbatim, this session: "but like we said it doesnt have to be a board it can be a cup of what ever like if 2
  mesh collide we can carve it".
- New scope (to be written as PREREG F-I5 before any run): any pair whose simulator colliders interpenetrate
  persistently along our tracks may be CARVED. This covers cups, pot/lid, cup or pot in rack, sweeper/dust pan/rack, and
  boards. Class O, the silhouette and the push preference no longer block a carve. The rigid-shift alternative is still
  computed and reported, not used to veto.
- Kept as acceptance, so a carve that breaks the physics is reported and not delivered:
  - pieces keep-out;
  - hands-off rest / sink;
  - free travel;
  - replay drift;
  - overlap.
- The ev10w evidence is to be addressed in the design: a widened cup cavity let the guest sink ~11 mm, and hands-off
  went 40/43 -> 4/43.
- Run as a separate workflow (collision-carve) that waits for the board-slot Build step before editing shared code.

## Collision carve (owner waiver, all pairs) (agent of the collision-carve workflow, Design step, started 31 Oct 17:14 UTC)
- 17:14 read I.md (all, incl. the 17:30 orchestrator note). Task: PREREG F-I5 + INTERLOCK section 21 (scope, swept-partner
  carve geometry, cavity-preserving pieces, acceptance incl. hands-off sink, run order, predictions), commit + push.
  Design only: no code edits, no runs. Reading INTERLOCK 0-3, 6, 11, 14, 18-20, PREREG F, code, ev10w evidence next.
- 17:12-17:14 [M] w6b + w7 (log `<scratch>/interlock/fi4/f414/test_w67b.log`, 151 s): **w7 passes** (B one-face, t =
  A's 10.17 mm via `partner_prior`, CARVE both, widths 12.17 / 12.17 mm, centres 0.15 / 0.21 mm, depth sum - W_x 4.67
  mm, 3 pieces, keep-out 0.0 cm3). **w6b (step 2 estimator)**: t = 5.81 / 5.82 (true 6), 9.57 / 9.66 (10), 17.12 /
  17.12 (18) at sigma 1 / 3 mm: all within 1 mm, reading 0.2-0.9 mm thin (edge points pull the face medians inwards);
  one cell misses: t = 18, sigma 1.0, rms check (v) fails (edge points in the 25 mm slab; step 1 holds there). Kept
  as an expected failure, no rule change. Implication for ep24 [H]: board 1's step-2 t may read ~0.2-0.5 mm thin.
- 17:15 committing the F-I4.14 code + tests, then T-I11 re-run (tag fi4b) and, concurrently, the Waiver + Controls
  re-run (w1-w5 with the new code) in the background.
- 17:24 read INTERLOCK 0-3, 4, 6, 11, 14, 18-20, PREREG F-I1..F-I4.14, interlock.py (decide_component/decide_pair,
  regions, runs), platebody header, structure.py lathe test + B7 table (lathe accepted: lid 2.04, beige 2.88, blue 1.61,
  dust pan 1.97 (false positive, rot FREE 0.38); pot 3.01 rejected; plates pass rotc alone), ev10w README (334393e),
  lathe_collision.py (16 sectors, 30 mm bands, base = centre disc + 16 rim sectors), determined-wright ev10_intrusion.
  Design points so far: c from the measured support slope (sink ~ c / sin(taper): c = 1 mm on a 3 deg taper -> ~19 mm);
  overshoot frames (partner deeper than the rest pose by > 4 mm along d or gravity) excluded from the sweep; one
  receiver per non-plate pair; cavity-preserving default for every object; S = ev10w M3 settle (host fixed, guest free).
- 17:30 design decided (writing PREREG F-I5 + INTERLOCK 21 now; nothing run, no code edited): colliders = cavity-
  preserving default pieces of every object (plate -> F-I4 boxes; lathe (A.6 rotc AND not plate-like) -> 16 sectors x
  bands from our SHELL solid's profile, walls start at each sector's base top, continuity check on 0.5 mm x 1 deg rays;
  others -> CoACD 0.02 + keep-out repair -> exact voxel boxes of (solid minus keep-out)); intrusion on colliders; gates
  = persistence + sweep share (run-kind clause relaxed to non-TRANSIENT); one receiver per non-plate pair (containment
  share); carve = receiver minus the guest's posed pieces offset by c over the build frames in R, overshoot frames
  (> 4 mm past the hands-off rest pose along d or gravity) excluded; c = min(1 mm, 0.5 x 4 mm x q99 support slope);
  caps 10 % volume, reach 0.6 (INSERTION/SLIDE), topology on 2 mm; acceptance S (ev10w M3 settle, host fixed, 16 copies,
  <= 4 mm and 5 deg) + P2-P7 + gate; push/one-sidedness reported only. Predictions P41-P49, synthetic T-I12 x1-x11.
- 17:15-17:30 [M] **T-I11 re-run, tag fi4b** (code 9ad1af9 = F-I4 + F-I4.12 + F-I4.14; same command as fi4evalsem with
  `--tag fi4b`; 914 s, concurrent with the T-I1 Waiver + Controls re-run): **plate test now holds on both boards**:
  board 1 step 2 (camera-side pair) t = 6.21 mm (faces at +4.19 / -2.02 mm, 19,431 / 17,244 points from 38 / 101
  frames, overlap 0.97, angle 1.3 deg, rms 2.5 / 1.7 mm <= 9 mm, extents 216 x 121 mm); board 2 step 3 (one face, all
  22,304 points from one side, 119 frames; 1-99 % extent 14.8 mm <= 25) with t := 6.21 mm (`plate_t_partner_prior`).
  In scope (both INSERTION); kept gates pass: sweep 1.0 / 1.0, push 19.0 / 22.0 mm (> 10). **Then F-I4.2 fails on
  both boards: `plate_outline_not_rectangular`** (fill of the min-area rectangle 0.895 / 0.868 < 0.9; rectangles
  234.5 x 142.3 / 231.1 x 142.0 mm, 7,470 / 7,124 cells of 2 mm) -> `waiver_gate_fail:plate_outline_not_rectangular`,
  the old decision stands: both PUSH (board 2 with interlock_disagree). No slot, no physics, no r0 delivery under
  F-I4; the old path wrote its r0 again (pieces gate 0.72 / 2.0 cm3, do-not-use). This is a gate failure after the
  one allowed post-hoc fix: stopping here, no tuning; reporting. P40 (board 1 by step 2, t in 5-9 mm; board 2 by
  step 3) holds; P36 (CARVE both) fails at F-I4.2.
- 17:34 PREREG F-I5 (F-I5.0-F-I5.10; predictions P41-P50; synthetic T-I12 x1-x11; real runs T-I13) and INTERLOCK
  section 21 (+ header and section-0 pointers) written. Nothing run, no code edited. Committing + pushing now (only
  PREREG.md, INTERLOCK.md, this log). Next (build step, after the board-slot build has released the shared files):
  collcarve.py, cavpieces.py, simphys.sink_test, the --waiver-fi5 branch, T-I12; then T-I13 in the F-I5.9 order.
- 17:35 pushed d156571 (F-I5 + section 21, committed 17:34:08 UTC). Correction: the entry above first said 17:36 and
  F-I5 / the INTERLOCK header said 17:40, guessed times; replaced by the commit time 17:34 (follow-up commit, text
  otherwise unchanged). Design step done; no code edited, nothing run.
