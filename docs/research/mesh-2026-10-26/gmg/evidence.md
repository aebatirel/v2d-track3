# Generalized mesh generator (gmg): evidence synthesis, 2026-10-30

Read-only synthesis for the design stage. **Zero new scan scorings.** No repo file was edited. The only new
measurement is a GT-free census of the 33 observed-point files (`obs_census2.py` next to this file; output
`obs_census.jsonl`; it reads only the allowed npz keys `pts, cam, frame, hits, free, lo, hi, vox, args`).

Labels: **[D]** measured against the public scan (diagnostic, after inference); **[M]** measured without the scan;
**[E]** estimate; **[H]** hypothesis; **[U]** unverified source. CD-O in cm (lower is better), ADD in mm.

Sources: `STATUS.md`; `docs/work-log.md` (L3335-3405 G1, L3489-3660 sweep, L4440-4894 autokit, generators,
diagnosis); `docs/research/mesh-2026-10-26/README.md` §1-10; `ledger-of-past-mesh-work.md`; `results/gen-probe/`;
`diag-2026-10-30/`; `results/autokit-stage1/*.json`; stage-1b notes in scratchpad `auto/stage1b/{integ,gates,parts,shell}/`;
`docs/mesh-v5-spec-draft.md` §3; `pipeline/perc2.py`; `scripts/obs_points.py`, `crops.py`; `gen/*.py`; `autokit/gates.py`.

## 1. Headline facts

1. **Our points are good; the meshers waste them.** Observed points along our own tracks lie a median 0.85-1.9 mm from
   the scan and cover 59-90 % of the scan within 3 mm on 8 of 11 measured pairs [D] (rack 28 %, board 1 ep23 16 %).
2. **No GT-free route beats library_v3 on all objects, and no GT-free selector works yet.**
   - Hand kits beat library_v3 on pot, lid, rack, blue cup [D], but they are per-object code with a scan-derived ball
     prior (provisional).
   - Gates v3 (pre-registered, held-out): MUST_PASS **1/7**, MUST_FAIL 29/50 strict, selection = library on 10/10 [M].
     Stage-1b integration: **11/11** finished episodes pick library_v3 (09:38 UTC) [M].
   - Generator GT-free metric: Spearman 0.46 with CD-O, picks the best mesh on 2/10 objects, mean regret 0.12 cm [D].
3. **The best candidate per object differs by object** (lathe, sheet, plates, generator), so a generalized generator is
   a candidate-source + selection problem, and selection is the weak link.
4. **Placement is as important as shape.** CD-O is blind to our placement; ADD is not. Generators fitted by
   `sim3_fit.py` give ADD 26-29 mm (median) vs library ~6 mm [D]; Pixal3D-MV (generated in our frame) 10.3 mm.
5. **Every current input chain touches a deny-listed mesh** (section 5). library_v5 exists for only 6 objects.

## 2. Per object

Eval pairs from the kit roster (36 pairs; spoon 10, no scan). "Best GT-free" = produced and chosen without a scan;
"oracle" = best number seen on the scan, any method (not a method).

| Object | Public eps with obs | Eval pairs | library_v3 CD-O / ADD / flips [D] | Best GT-free route so far [D] | Best oracle [D] |
|---|---|---|---|---|---|
| white_pot | 0, 2, 26, 27, 41-45 (9) | 6 (1, 3, 5, 6, 8, 28); anchor in 5 | 0.437 / 6.7 / 0 of 8 | hand kit `prim_potlid` ep41 (thin lathe + bar handle + balls), picked by obs_fidelity over 8 eps: **0.342** / 3.05 / 0 of 8 (provisional: 7 mm ball prior). GT-free metric's generator pick SAM 3D s7 0.328 (ADD 8.0) | TRELLIS.2 s7 0.318; approach-2 lathe on library mesh 0.319 (library-derived) |
| white_pot_lid | 0 (broken), 2 | 1 (1) | 0.421 / 8.1 / 0 of 6 | hand kit sheet + strap + balls ep2: **0.220** / 4.46 / 0 of 6; worst over t grid 0.224 / 5.06 (provisional). Gates v3 pass it but the rank picks library (0.486 vs 0.596-0.699) | 0.220 (hand kit); Pixal3D-MV s42 0.253 |
| plastic_dish_rack | 12, 13, 26, 27, 31 | 5 (14, 15, 16, 28, 30); anchor in 4 | 0.555 / 6.0 / 0 of 7 | hand kit `prim_rack` **joint** fit eps 12/13/27: **0.456** / 5.37 / 0 of 7 (multi-episode: breaks the single-episode eval rule). Single-episode DSL ep13 unscored | 0.456; generators >= 0.604 |
| blue_cup | 11, 12, 13, 21, 22 | 5 (10, 14, 20, 32, 33); axial | 0.523 / 10.0 / 0 of 7 | `lathe_obs` hollow lathe + voxel-splat appendages ep21, episode picked by obs_fidelity: **0.291** / 4.1 / 0 of 7 (ep22 0.364, merged 0.396). Gates v2/v3 reject it | SAM 3D s7 0.268 |
| beige_cup | 11 only | 2 (8, 10); axial | 0.856 / 6.5 / 0 of 6 (eval 10); v3x 0.730 (eval 8, P1 chain) | GT-free generator pick SAM 3D s42 **0.526** (ADD 21.5); v3x 0.730 | Pixal3D-MV s42 0.274 (s7 0.512); lathe on v3x 0.292 (library-derived) |
| water_pitcher | 21, 22 | 1 (20); anchor | 0.894 / 7.6 / 0 of 6 | GT-free generator pick SAM 3D s42 **0.771** (ADD 30.4); library_v5 0.890 | Hunyuan3D-2.1 s42 0.378 |
| mini_dust_pan | 18, 39, 40 | 2 (19, 38); anchor in 38 | 0.331 / 5.6 / 0 of 6 | Pixal3D-MV, 3 posed views ep39, in our frame: **0.240 / 0.236** (both seeds; ADD 5.3-6.0, 0 of 6), not selected by any rule yet; GT-free pick SAM 3D s42 0.261 | Hunyuan3D-2.1 s42 0.231; Design O 0.251 (scan-picked) |
| mini_sweeper | 18 (hands null), 31 | 2 (19, 30); anchors | 0.317 / 5.2 med / **3 of 30** seeds flip | none clean. GT-free pick SAM 3D s7 0.437 (2/6 flips); library_v5 0.526. C1 = library_v3 + 2 observed balls: 0/30 flips (CD-O not scored) | P1 part program 0.2225 (leak-affected); M2 0.283 (leak-affected) |
| wooden_piece_1 | 23 (broken), 24 | 1 (25); anchor | 0.222 / 2.4 / 0 of 6 | `prim_boards` ep24 occ_d2: **0.189** / 3.31 / **1 of 6** flip (fails) | Pixal3D-MV s42 0.182 (4/6 flips); box+slot 0.177 (library-derived) |
| wooden_piece_2 | 23, 24 | 1 (25) | 0.216 / 3.6 / 0 of 6 | none beats library: `prim_boards` ep23 0.229 / 78.7 / 3 of 6 (wrong board's track); GT-free pick SAM 3D s42 0.321 | SAM 3D s7 0.202 (6/6 flips) |

Means: library_v3 0.477 (10 objects). Hand kits where they exist: pot 0.342, lid 0.220, rack 0.456, blue cup 0.291.
Generator oracle 0.315. GT-free {library_v3 vs GT-free-best generated} choice 0.429 [D], better on 6, worse on 3.
library_v5 (only compliant library, P1): sweeper 0.526, rack 0.818, dust pan 0.368, blue cup 0.540, pitcher 0.890,
beige cup 0.730 (as v3x); pot, lid, boards failed. Worse than v2/v3 on 4 of 5 [D].

### 2.1 Observation coverage (GT-free census of `obs_all`, [M]; scan coverage from README §4, [D])

"Spread p90" = 90th percentile angle of the per-frame camera direction from its mean, in the object frame (how much
the object turned relative to the camera). "cap60" = share of the view sphere within 60 deg of some camera direction.
"Box" = share of points within 5 mm of the ROI box faces (points the library-derived box could have cut).

| Object | Points (M) per ep | Frames | Spread p90 (deg) | cap60 | Scan within 3 mm [D] | Unseen |
|---|---|---|---|---|---|---|
| pot | 2.5-5.6 | 79-187 | static 0/2/44: 4-11; handled 26/27/43/45: 55-106; 41/42: 36-38 | 0.29-0.76 | ep41 88 % (median 1.89 mm) | base in static eps; handle hole |
| lid | ep2 1.49; ep0 0.002 | 172; 24 | 5 | 0.29 | ep2 83 % (0.85 mm) | underside, thickness (one side only) |
| rack | 1.0-3.9 | 79-145 | 1-5 (never moves) | 0.26-0.28 | ep26 28 % (1.88 mm) | floor, underside, fins behind fins |
| blue cup | 0.26-1.9 | 68-95 | 21/22: 9; 12/13: 107-129; 11: 18 | 0.30-0.83 | ep21 64 %, ep22 59 % (0.9 mm) | lower inner wall, base (static eps) |
| beige cup | 0.53 | 68 | 10 | 0.31 | not measured | base, far side; one episode |
| pitcher | 4.3-5.6 | 85-95 | 12-17 | 0.36-0.40 | ep22 61 % (1.30 mm) | base, back, inside |
| dust pan | 1.4-2.0 | 130-177 | 14-42 | 0.41-0.61 | ep39 90 % (1.07 mm) | underside |
| sweeper | 0.50-1.10 | 144-177 | 21-24 | 0.39-0.41 | ep31 68 % (1.37 mm) | bristle underside; ep18 25 % hand blob (box 6.8 %) |
| board 1 | ep24 2.04; ep23 0.04 | 138; 73 | 65; 6 | 0.53; 0.33 | ep23 16 % (identity swap) | one face per pose |
| board 2 | 0.77-1.56 | 131-163 | 40-70 | 0.48-0.50 | ep23 84 % (1.29 mm) | slot, far face |

- The ROI box rarely binds: box share < 1 % in 29/33 files; exceptions ep18 sweeper 6.8 % (hand blob), ep24 board 1
  2.1 %, ep23 board 2 1.3 %, ep26 rack 0.9 % [M].
- 8 of 33 files were built with `hands: null`: ep12 cup and rack, ep18 dust pan and sweeper, ep24 both boards, ep27
  pot and rack [M].
- Static episodes see one cone of directions (cap60 about 0.3); only handled episodes see the base.

### 2.2 Failure modes per object (measured unless marked)
- **pot:** handle smeared by track jitter (between-frame spread 5.6-9.3 mm vs 3.7-5.5 within) [M]; symmetric body
  without handle flips 2/8 [D]; generic `fit_axis` 5.9 deg off the hand-kit axis [M]; obs lathe 0.413-0.468 [D];
  4 of 5 hand-kit balls float; library base has a 4-5 cm hole; gates v3 fail HOLE 0.050 and FRAME (align 4.1 mm).
- **lid:** ep0 track broken (whole-track 23-26 mm offset, 2,104 points), so no hold-out; thickness unmeasurable;
  generic ball fit keeps 2 of about 5 visible balls; SAM 3D single view stretches it (diameter x0.7, thickness x1.6).
- **rack:** static and self-occluding; floor depth unseen (single-episode floor differs 4.8 mm from the joint fit);
  generators all >= 0.60; programs fail gates PREC 0.050-0.051 and FRAME 3.8-4.1 mm.
- **blue cup:** CD-O scale is set by area distribution against a partial scan (lathe 0.382 as scored vs 0.316 at true
  scale) [D]; fusion hurts (0.291 -> 0.396); two-sided wall t is density-sensitive (1.68-4.44 mm) [M]; SAM placement
  slides 21-32 mm along the axis [D].
- **beige cup:** one public episode, on the lap; TSDF 42 % unknown, 268 fragments; open base, falls in the simulator;
  generator seed variance (Pixal3D 0.274 vs 0.512).
- **pitcher:** not a lathe (rotational consistency 8.85 mm); see-through holes and missing half base in library;
  Pixal3D-MV fails (1.24-1.81); shells fail hold-out G_HOLE.
- **dust pan:** thin plate (real 3-5 mm, library 11-13 mm); generic plate_set probe refuted (fragmented; a gate passed
  a mesh with its largest wall removed); refine hits its bound on 30-45 % of frames.
- **sweeper:** near-symmetric under 180 deg about its long axis; only the marker balls break it; library lost the
  ball bumps (surface 6.6-8.7 mm short) -> 3/30 flips; symmetric body without balls 9/30; generators fed an edge-on
  crop make a "brush on a stick"; shells fail G_CONN (island policy).
- **boards:** near-symmetric flips (box-slot board 2: 2/6; generators up to 6/6); ep23 identity swap (board-2 track
  looks like board 1 turned 180 deg); no slot detector.

## 3. Components

| Component | Status | Evidence | Reusable? |
|---|---|---|---|
| Classic TSDF (`recon_mesh.py`, library v1-v3) | superseded | 4 mm binary solid + blur: walls 12-20 mm vs real 2-4 mm; 5 mm inflation costs AUC 0.987 -> 0.608 [D]; v5 obs grids (2 mm) worse than v2 on 4/5 [D] | no (as mesher) |
| Thin shell, route A (`autokit/shell.py`) | works on observed surface only | synthetic faces 39.97 vs 40.0 mm, t 6.01 vs 6.0 [M]; stage 1b: 27/27 shells watertight after kit `budget_mesh`, area change 0.0 % [M]; fidelity cup 1.4 vs library 6.1 mm [M]; fails hold-out G_HOLE on dust pan and pitcher (unseen surface missing); GT-free metrics cannot choose t; never scan-scored | yes: observed-surface layer, and a GT-free reference surface |
| Hits/free vote grids (4 mm) | works as evidence | keep rule (>= 3 hits, ratio 0.5) removes hands and others; shell carve gain only -0.00 to -0.05 mm at 2-3x runtime [M]; free-space violation (FSV) term in gates; grids stale in refined copies; per-frame below-table carve at 2 mm erased real wood [D] | yes (free-space evidence) |
| Part DSL (`parts.py`, `program.py`, 4 programs) | works; per-object authored | reproduces hand kits (pot 0.000 mm, lid 0.003, cup 0.000, rack 0.013 median) [M]; scale-equivariant; runs unchanged on other episodes (pot ratio 0.98-1.02); stage 1b: schema, free-fit balls, plate_set by plane, shell_patch, budget-safe builds; shape windows must be given per program (calibrated from hand kits) | yes as the part vocabulary; program choice must become automatic |
| `refine.py` (per-frame rigid refinement) | refuted as default | injected errors recovered (corr 0.91-0.995); pre-registered falsifier FAILED on the pot handle; refined shells worse on cup, dust pan, pitcher; 600/3802 frames hit the 3 deg bound [M] | no (diagnostic only) |
| Gates v3 / selector v3 (`gates.py`) | fails specificity | held-out prereg: MUST_PASS 1/7, MUST_FAIL 29/50, selection library 10/10 [M]; G_FRAME align <= 2 mm rejects fits with scan ADD 3-5 mm; rank prefers library on the lid although the program is 0.220 vs 0.421 [D]; frame_med and flip_check reference library_v3 | measurements yes; selector and thresholds no |
| Generators (SAM 3D, Pixal3D-MV, Hunyuan3D-2.1, TRELLIS.2, TripoSG) | candidate source | means 0.501 / 0.490 / 0.602 / 0.594 / 0.984 vs library 0.477; oracle 0.315 [D]; 11-42 s per mesh on H100 [M]; $4.36 batch [M]; inputs used library_v3 (GrabCut seed, z-buffer, centre/extent) | yes (SAM 3D, Pixal3D-MV) with clean masks |
| `sim3_fit.py` (Sim(3) to one-sided points) | refuted | biased: the wrong placement scores lower than the scan-ideal one on 17/20 [D]; ADD 26-29 mm; flips coin tosses on near-symmetric objects | no; replace |
| Marker-ball detector | needed; recall weak | hand-kit prior 7 mm traced to scan-fitted spoon marker catalogue (leak); generic free fit (3-15 mm): lid 2 of ~5 visible, pot 0-1 per episode, rack 0 [M]; `ball_scan` median 9.7 mm (n 11, not repeatable); sweeper ep31 free radii 7.4 / 5.9 mm [M]; adding 2 observed balls removes sweeper flips 3/30 -> 0/30 [D] | yes; must raise recall |
| Kit scorer (`scripts/mesh_metric.py`) | works (dev only) | reproduces library numbers exactly; board moved as predicted for the eval-8 swap (0.4015 vs 0.40188) [D]; `budget_mesh` watertight on only 6/144 meshes [M] | yes, counted and pre-registered |
| Perception / ROI (`perc2.py`, `obs_points.py`) | works; tainted inputs | public tracks: sweep `20261025-sweep-a894083`, templates library_v2, mean registered AUC 0.868 [D]; eval tracks templated on library_v3; obs ROI = library_v3 box + 2 cm, others = library_v3 meshes; box binds < 1 % of points in 29/33 files [M] | code yes; inputs must be re-sourced |

## 4. Lessons

**Leaks found (scan knowledge in method or constants):**
- Library v1-v4: tracks templated on the scans, scans as `--others` (deny-listed).
- Marker-ball radius 7 mm and the 5-9.5 mm window: from a marker catalogue fitted on the public scans, mislabelled as
  "our stereo". It shaped the pot, lid and rack hand kits.
- Builder briefs carried scan-measured lid and rack wall thicknesses (2.5 mm) and the rack's upright holder.
- Sweeper P1/M2: 7 mm ball radius and head band matched scan dimensions; mid-plane and ring rules changed after a scan
  comparison.
- Gates v2 tuned toward scan-validated labels; Design O dust pan and the sweeper episode were scan-picked.
- `lib` registration fix and generator crops lean on library_v3 (deny-listed).

**Refuted or failed ideas (with numbers):** multi-episode fusion (single episode wins 6/6) [D]; screened Poisson
(0.96-1.11) [D]; frame-0-only lathes (1.1-1.3, 7/7 flips) [D]; interaction carving on the submitted mesh (lid +0.14
to +0.18) [D]; per-frame below-table carve at 2 mm [D]; episode weighting R_w (1/4) [D]; generic-only probes P1 (pot)
and P2 (dust pan) [M]; refine.py as default [M]; RANSAC ball fit (larger-sphere bias) [M]; `vis` placement objective
(flips the lid) [D]; Sim(3) to one-sided points [D]; 1 mm thickness floor (area +18 %) [M]; gates v1-v3 as selectors
[M]; GT-free observed-surface metrics as selectors (always prefer the thinnest, most incomplete shell) [M].

**Measurement lessons:**
- CD-O and ADD can move in opposite directions (Design O lid: CD-O better, ADD 7.6 -> 14.0 mm). Judge both.
- CD-O's RMS-radius scale punishes a wrong area distribution against a partial scan (about 0.07 cm on the cup lathe).
- Flip margins of near-symmetric objects are tiny (0.004-0.09 mm); small asymmetric details (balls) decide them.
- Generator seed variance exceeds model differences (Hunyuan blue cup 0.298 vs 1.252).
- Held-out episodes reveal missing surface the build episode cannot see; one-episode eval selection cannot.
- One-sided alignment of partial points is biased by 2-6 mm (gates align 3.7-4.1 mm on fits whose scan ADD is 3-5 mm).
- Broken tracks poison everything downstream (ep0 lid, ep11 beige, ep23 boards); a GT-free below-table test flags
  exactly the known failures [M].

## 5. Provenance inventory

| Input of today's pipeline | Depends on | Clean replacement | Residual |
|---|---|---|---|
| Public tracks `20261025-sweep-a894083` (all `obs_all` points) | FoundationPose template **library_v2** (deny-listed), detection by DINOv2 vs grey renders of library_v2 + size gate from its extents | re-track with library_v5 templates (P1) where they exist; for pot, lid, boards a GT-free seed (gmg mesh or generator mesh from a text-prompt mask); then a washout re-track | P1 by the letter even after washout (owner decision O1 still open) |
| Eval tracks (`mesh-20261029-evdepth-92f3d86`, `20261025-evperc-4f596df`) | template **library_v3** | same re-track on the 20 eval episodes; meshes and submitted poses must come from the same tracks (the frame is the template's) | as above |
| `obs_all` ROI box | library_v3 bounds + 2 cm | generic cube (v0 used +-30 cm) around the track origin, or a box from our own frame-0 mask points with a generic margin; the free-space keep rule does the real work | low: the box binds < 1 % of points in 29/33 files [M] |
| `obs_all` `--others` | library_v3 meshes of the other objects, posed by their tracks (12 mm) | free-space votes alone (anything not rigidly attached is seen through), plus our own GT-free meshes of the other objects in a second pass | co-moving neighbours (lid on pot, cup in rack) [H] |
| Hands | G1 refs (P1); 8/33 files none | MediaPipe from the video (P0) for every episode | eval hands availability not checked [U] |
| Frame-0 masks (`det_f0.npz`) | SAM2 proposals (P0) assigned by DINOv2 vs library renders + size gate | assign by OWLv2 / Grounding DINO text prompts (object names allowed) | prompt confusion between the two boards [H] |
| Selector fallback | library_v3 | library_v5 (6 objects) or the gmg's own shell / best gated candidate | v5 is worse than v3 on 4/5 [D] |
| Gate references (`frame_med_mm`, `flip_check`) | library_v3 | the episode's own points and the candidate's own self-ambiguity | none known |
| Generator crops and Pixal3D views | library_v3 posed by tracks (GrabCut seed, z-buffer, centre/extent) | SAM2 masks / our own observed points projected; centre and extent from points | GPU re-run |
| `lib` placement fix (diag) | library_v3 surface | our own shell or observed points with free-space and silhouette terms | untested [H] |
| Hand-kit constants | 7 mm ball prior (scan), thicknesses (brief) | generic windows (commercial passive mocap markers: about 3-25 mm diameter [U]) and the t grid {1.5, 2.5, 4.0} mm | provisional scores need rebuilding |

## 6. Costs already measured, and what a gmg GPU step would cost
- Measured: eval depth 20 episodes $2.95; generator probe $4.36 (84 min H100, $2.61 of it download); G1 re-track 16
  episodes $1.1; eval perception 20 episodes $1.9; tracking sweep 3 variants x 20 episodes $3.7.
- Estimates [E]: compliant re-track of 20 public + 20 eval episodes about $2-4; SAM 3D + Pixal3D-MV on all 36 eval
  pairs x 2 seeds (11-22 s per mesh) about $3-6 with setup; the same on public crops with clean masks $3-5.
- CPU: point extraction 40-300 s per episode-object (52 min for 17); depth must be re-downloaded (0.3-0.9 GB per
  episode; 14 GB disk free); stage-1b integration takes 1-59 min per episode on 2 cores (pot about 38, rack about 59).
