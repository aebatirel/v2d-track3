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
