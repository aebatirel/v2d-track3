# 12 — Spin observability of near-symmetric objects (cups, lid, pot, pitcher)

Status: complete (stages A, B, C on 2026-10-05, verifier pass the same day, stage B and C re-runs on 2026-10-06).
Agent 12. Work dir `/Users/aebatirel/Documents/Code/v2d-research/work/12/` (stage C in `c/`, re-runs in `b2/` and `c2/`).
Tags: [V] verified here, [E] estimate or simulation, [H] hypothesis, [lit] read in the source, [lit-m] from memory.
Research and analysis only. Public GT was used only for analysis and scoring. Eval videos were viewed for method design
only; no labels were recorded or used. No SlamDunk code was read.

## Answer

Spin about the rest-up axis **can be seen in the video for all five objects. For the two cups, the only cue is the
mocap marker spheres**, plus a base inscription when the base faces the camera. Geometry alone fixes white_pot (its
handle) and water_pitcher (spout and handle). The lid is 2-fold by geometry, and its top markers break the tie. The
scorer uses plain ADD with one slot-0 frame-0 alignment, so the anchor's spin must be within about 5 deg. Note 11 B2:
AUC >= 0.9 needs <= ~5 deg, and MP-SR needs <= ~5-8 deg. A 120 deg flip costs about 0.8 AUC on that episode.

Precision is not the problem. One marker centred to 1 px fixes spin to 0.4-0.7 deg in cam a. On a real public frame
the solver agrees with GT to ~1-2.5 deg; the bound is set by the camera, which was fitted to GT. The risk is
**identity flips**. Blue cup and pot are robust. **The beige cup's three markers form a near-equilateral triangle.**
That is the layout mocap vendors warn about, because it makes rigid bodies flip. Two detected beige markers fit the
true spin and a ~-131 deg branch about equally well (real frame: 21-28 of 40 flips). They can only decide it if the cup
centre is known to ~1 mm, which we cannot assume. The third marker decides it, and it is usually a low-contrast sphere
at the silhouette. The new finding is that **checking each branch's predicted marker location** for a sphere and black
mount separates the branches on the very frame where bottom-up detection failed. Eval 8, the only beige anchor, shows all
three markers at frame 0.

| object | spin cue | single-frame MC, cam a (base / tight prior), median; flips > 30 deg | realistic flips (2 mm model error) | real frame (public ep 11 f0) | eval exposure |
|---|---|---|---|---|---|
| white_pot | handle geometry + 7 markers | 0.24 / 0.21 deg; 0.01 / 0.00 | not run (expected low) | not run | anchor eps 1, 3, 5, 6 |
| blue_cup | 4 irregular markers (2 rim, 2 base); base inscription when inverted | 1.8 / 1.0 deg; 0.08 / 0.05 | 0.12 (base) | 3 true blobs: 0/40 flips, all errors -0.1 to -1.4 deg | anchor eps 10, 14, 20, 32, 33 |
| beige_cup | 3 rim markers, near-3-fold (104/119/136 deg); base inscription | 1.0 / 0.7 deg; **0.20 / 0.09** | **0.35** (3 detected: 0.27) | 2 markers: **21-28/40 flips**; third added: 0-1/40, 0.85-0.99 deg | anchor ep 8; slot 1 ep 10 |
| white_pot_lid | 2-fold bar handle + 5 top markers (two sizes) | 0.6 / 0.5 deg; 0.07 / 0.03 | not run | not run | slot 1 ep 1 |
| water_pitcher | spout + arch handle (+4 markers) | markers only: 1.5 / 0.8 deg; 0.09 / 0.06 | not run | not run | ep 20 (not anchor) |

How to read the table:
- MC v3 assumes the exact scan marker layout, the exact camera, 1.5 px noise and independent misses. Its rates are
  lower bounds. With N(0, 2 mm) error on the marker model, the beige flip rate roughly doubles; blue barely changes
  (verifier C4).
- Base prior is 5 mm centre and 2 deg tilt; tight is 2 mm and 1 deg. Fusing 5 independent views (multi5) gives
  0.00-0.02 flips, which is optimistic.
- Cam b gives the same flip rates, with medians 1.2-2x larger.
- The real-frame camera is a 6-point PnP on GT-placed markers (4.07 px), fitted to the same pixels. Its spin numbers
  show agreement, not measured accuracy (verifier C2).

## Automatic spin-resolution design

1. **Body pose first, spin left free.** Use a tracker, the rim ellipse, stereo and the table plane for the centre and
   tilt (with the stable-pose snap from note 11), and keep the spin as a free parameter. FoundationPose's own spin
   choice for the cups is not trusted [H] (see the literature notes).
2. **Bottom-up sphere detector** [H, required]. The hand-made detectors miss spheres seen against the grey floor at
   the silhouette, and spheres behind the far rim [V]. Those spheres have low contrast: 25th-percentile Lab dE 5-8
   against 32-47 on the blue wall (stage B re-run).
   - Train a small heatmap network on public frames from all objects (same sphere type), in cam a and cam b.
   - Get labels automatically: solve a per-frame camera from automatic blobs by RANSAC PnP against every GT-placed
     scan marker in the scene; `pnp_check.py` reaches 4.1 px on ep 11 f0. Then project all markers with z-buffer
     visibility, counting a sphere as visible when >= 25 % of its disk is free.
   - Expected sphere size: 35-40 px in cam a and 17-20 px in cam b at 0.42-0.50 m (stage B re-run, measured at the
     GT-projected centres).
3. **Top-down branch verifier** [V one frame, design H]. For every spin branch the solver keeps, predict which markers
   should be visible and where. Score a learned patch classifier (sphere plus black mount, trained on GT-projected
   public crops) at those locations, within about 6 px.
   - On public ep 11 f0 the two beige branches predict the missing third marker 50 px apart. Simple hand-made cues
     already favour the true one: edge completeness at the 83rd vs 47th percentile, and black-mount pixels 0.017 vs
     0.000 (`c2/topdown*.py`).
   - Only two candidate locations need checking, which is much easier than full silhouette recall.
   - This is the useful form of render-and-compare: restricted to marker locations, with a learned appearance model.
4. **Identity and spin solver** (`c/mc_spin.py: solve`) [V synthetic and real]. Scan the spin in 2 deg steps with a
   gated robust cost and a visibility-aware missing-marker term. Refine the best 6 minima jointly (spin, centre, tilt),
   then add the top-down verifier score to each branch. **Output a multi-modal spin likelihood, not only the argmin.**
   - The marker layout comes from the scan spheres; public GT confirms it (within 4 px, spin within ~2 deg, ep 11).
   - Refining the layout by bundle adjustment over public frames is possible for blue (5 episodes) but **beige has
     only public ep 11**.
5. **Stereo is for rejecting outliers, not for identity** [V one frame].
   - The ego a-to-b baseline is 37 mm. At 0.5 m that gives ~12 mm of depth per cam b pixel, and 1-3 px of
     matching/sync error gave 13-32 mm depth errors. So the beige chord test (pair distances 97.9 / 91.7 / 84.4 mm,
     6.2 mm margin) is unreliable.
   - Stereo does reject false blobs by depth: a false blob triangulated to 0.57 m against 0.42-0.46 m for the cup.
   - The b/c pair (75 mm) halves the depth error. It is untested for identity [H].
6. **Temporal fusion.** Sum the branch likelihoods over the anchor's static prefix (13-117 frames, median 39 per note
   02); spin is constant there. Fusion helps mainly when **another marker comes into view**. Parallax on the same two
   markers needs about a 24 deg change in viewpoint before it separates the beige branches (`c2/branch_margin2.py`).
   Carry later evidence back to frame 0 through the tracked relative rotation in the batch smoother [H]: more markers,
   or the base inscription when a cup is inverted (eval 14, last ~40 %) or tipped (eval 8 pours).
7. **Base-inscription matcher** for upside-down or tipped cups. The scan template is unique inside r < 25 mm (peak
   half-width 2-6 deg, lookalikes <= 0.37), and the rim ring must be masked [V scan]. The marks are visible in cam a,
   and faintly in cam b and cam c, at ~1.05 px/mm (stage B re-run). Matching on video has not been run.
8. **Whole-object render-and-compare only as a weak tie-breaker.** A splat render of the textured scan picked the
   right beige branch by an NCC margin of only 0.016, and the wrong branch on the marker regions [V]. The silhouette
   and rim do not change between branches, and the scan colours and lighting differ from the video.
9. **Fallback priors (note 11)** when the branch margin stays small.
   - Eval 14: cup-vs-rack relative yaw (LOO 1.9-2.7 deg).
   - Eval 20: pitcher-vs-cup (6-8 deg, too loose for MP-SR).
   - Eval 10 is insensitive (stacked cups on the anchor axis).
   - Eval 8, 32 and 33 have no prior, so vision must decide; report the uncertainty there.
10. **Automatic per-episode diagnostics:** markers detected per frame, branch margin with and without the verifier,
    whether the fallback fired, and stereo depth consistency. No hand labels.

## Achievable yaw accuracy [E]

- **Precision.** One marker at 1 px gives 0.4-0.7 deg in cam a and 0.8-1.3 deg in cam b. The real-frame bound is ~1-2.5
  deg, limited by the camera. The GT-free joint fit gave 1.1-2.6 deg [V].
- **white_pot anchors (eval 1, 3, 5, 6):** <= 0.5 deg and ~0 % flips from markers alone, with the handle as a second
  cue. This is not yet run on real frames.
- **blue_cup anchors (eval 10, 14, 20, 32, 33):** about 1-2 deg median.
  - Single-frame flips are 5-8 % ideal and ~12 % with model error. Static-prefix fusion should bring them to ~0-1 %
    if the detector reaches ~90 % recall.
  - Two markers decide the branch even with a 3-5 mm centre error: the wrong branch stays >= 11 px off at the 10th
    percentile (`c2/branch_margin.py`).
  - Real frame: 0/40 flips.
- **beige_cup anchor (eval 8):** the deciding risk.
  - Single-frame flips: 9-20 % ideal; 24-44 % with 1-2 mm marker-model error or detector-like recall (verifier C4).
    With only two markers it is ~50-70 % (real frame).
  - Two markers decide the branch only with a ~1 mm centre and well under 1 deg of tilt. At 2 mm, 22-46 % of views
    are marginal.
  - With all three markers (bottom-up or top-down) it is 3 % ideal and 0-1/40 on the real frame, but 27 % in the MC
    with 2 mm marker-model error. So the beige layout itself must be accurate: bundle-adjust it on ep 11. All three
    markers are in view at eval 8 frame 0.
  - [E] So eval 8 either scores normally (~1-2 deg) or has about a 1-in-3 to 1-in-2 chance of a ~120-130 deg flip if
    the verifier fails. That flip means AUC ~0.2 with SP-SR and MP-SR 0 for the episode.
- **Budget (notes 02/11).** A 2 deg anchor rotation costs almost nothing (AUC 0.997, MP-SR 1.0). 5 deg gives AUC
  ~0.95. A 90/180 deg spin gives AUC 0.195/0.165.

## Literature (brief)

- [lit] **BOP 2020** (Hodan et al., arXiv 2009.07378, Sec. 2.3).
  - An object's symmetry set is every transform whose Hausdorff distance is below max(15 mm, 0.1 d), "to avoid
    breaking the symmetries by too small details". Transforms the organisers judge resolvable by texture are removed.
  - MSSD, MSPD and VSD are symmetry-aware.
  - By this rule our cups (marker sets 13-13.5 mm from another spin) and the lid count as symmetric. So BOP-tuned
    methods are neither trained nor scored to resolve this spin. Our scorer is plain ADD.
- [lit] **FoundationPose** (Wen et al., CVPR 2024, arXiv 2312.08344).
  - Generates 42 icosphere views x 12 in-plane rotations = 504 hypotheses, refined and ranked by render-and-compare on
    160x160 crops. It has no symmetry-specific handling.
  - Its stated failure case: texture-less objects with occlusion and few edges get a wrong orientation.
  - At 160 px a 35-40 px marker shrinks to ~18 px, and the branch differences to ~5-10 px [E]. Nothing in training
    makes it weight markers. FoundationPose spin on cups should be treated as unreliable until measured on public frames.
- [lit] **EPOS** (Hodan et al., CVPR 2020, arXiv 2004.00605) handles symmetries with surface fragments and many-to-many
  correspondences. **SurfEmb** (Haugaard & Buch, CVPR 2022, arXiv 2111.13489) learns multi-modal correspondence
  distributions without symmetry labels. Both keep the ambiguity explicit.
- [lit-m] Related methods not re-fetched: Manhardt et al. ICCV 2019 (multiple hypotheses), Implicit-PDF (ICML 2021),
  SpyroPose (2023), and MegaPose and CosyPose (symmetry-aware losses, which deliberately ignore spin).
- [lit] **OptiTrack Motive, "Rigid Body Tracking"** (docs.optitrack.com/motive/rigid-body-tracking, fetched
  2026-10-06).
  - At least 3 markers are needed; 4-12 are recommended.
  - The docs say to avoid squares and isosceles or equilateral triangles, because symmetric sets "may cause the Rigid
    Body assets to flip"; distinct inter-marker distances identify an asset.
  - The beige cup is the 3-marker near-equilateral case, mild for a mocap system that measures 3D distances to sub-mm
    and the worst case for monocular video. The blue cup's 4 irregular markers follow the rule.
- **Takeaway.** No off-the-shelf pose method targets near-symmetries that are broken only by small physical details.
  The design follows the mocap and keypoint view: model the markers explicitly as keypoints with a known 3D layout,
  search over identities, keep a multi-modal distribution, and verify each hypothesis where it predicts evidence.
  Whole-object render-and-compare and priors are the fallback.

## Limitations and open issues

- Every real-image result comes from **one public frame** (ep 11 f0). That frame's camera is fitted to GT-placed
  markers (4.07 px, 3 of 6 points located by eye), so its spin numbers show agreement, not accuracy. The pot and lid
  were not run on real frames, and the full-episode real test is still to do.
- MC v3, `branch_margin*.py` and the stereo depth estimates are idealised.
  - They assume the object at rest, a known or simple camera, Gaussian pixel noise and independent misses. They ignore
    motion blur and hand-correlated occlusion.
  - The pot and pitcher runs use markers only, without handle or spout geometry.
  - multi5 is optimistic.
- The top-down verifier has been tested with hand-made cues on one frame only (83rd vs 47th percentile; mount 0.017 vs
  0.000). Its reliability needs a learned classifier and many frames.
- The beige cup appears in one public episode, so there is no fresh public beige holdout.
- The a/b stereo matches needed a 2-3 px shift off the epipolar curve: a residual extrinsic or time-sync offset [H].
  Time sync between the streams is untested.
- The base inscription has been checked for uniqueness in the scan and seen in video, but never matched on video.
  Video shows it on blue only; beige is never tipped in public data.
- The principal-point convention is still open: the as-given and rotated K fit equally (4.07 vs 4.03 px).

## Next steps

1. Auto-label public frames (eps 0, 2, 11, 12, 13, 21, 22, 26, 27, 41-45; cam a, plus cam b where downloaded).
   - Per-frame camera by RANSAC PnP from automatic blobs against all GT-placed markers, with z-buffer visibility.
   - Measure detector recall per background type: wall, floor, rim, hand.
2. Train the sphere heatmap detector and a sphere-plus-mount patch verifier.
   - Targets: >= 95 % recall of visible spheres, silhouettes included, at <= 0.5 false blobs per object; verifier
     AUROC on predicted-location crops.
   - Re-run `real_ep11.py`-style scoring with the verifier term per frame over whole public episodes. Report spin
     error, flip rate (beige: ep 11 is the only case) and latency.
3. Static-prefix fusion and the multi-modal anchor-spin factor in the batch smoother. Score with the official scorer on
   the public cup-anchor episodes (11, 12, 13, 21, 22), then on fresh holdouts (blue only).
4. Base-inscription matcher on the inverted frames of public eps 12 and 13, in cam a and cam b/c. Check it against
   the marker-derived spin.
5. Optional: b/c stereo (75 mm) depth for the marker centres, and a sync/extrinsic check between a and b over moving
   frames.

---

# Appendix: running logs (stages A, B, C; kept as history; later entries supersede earlier ones where marked)

## Running log

- 10:45 Downloaded public ego_cam_a for episodes 0, 11, 12, 13, 21, 41 and ego_cam_b for 11 into
  `data/track_3/public/videos/chunk-000/...` (`work/12/fetch.sh`).
- [V] The textured scans contain the mocap markers: grey/white spheres on black mounts appear both
  in the textures and as geometry bumps (renders `work/12/out/<name>_views.png`).
- [V] The markers are clearly visible in the ego colour video (ep 0 lid/pot, 11 cups, 12 blue cup,
  21 blue cup + watering can, 41 pot): `work/12/out/raw_f0_grid.jpg`, `raw_a11_f0.jpg`.
- [V] **The HF colour MP4s are already upright.** Rotating them 180 deg makes the frame upside down
  (a "CHARGE" shelf label reads upside down; hands enter from the top). The mono ego_cam_b MP4 is
  upright too. The calibration JSON's ego pair note ("left/right swapped: a 180 degree rotation
  mirrors the baseline direction") is consistent with streams that were rotated before release.
  Do NOT rotate again. Principal-point convention still to be checked (PnP test below).
- 11:05 [V] Marker spheres found in the scan geometry (`work/12/markers.py`, `out/markers_raw.json`):
  sphere radius 7.1-7.8 mm (about 14.6 mm markers) on black mounts. Counts: blue_cup 4 (2 near
  rim, 2 near base), beige_cup 3 (all near rim, spacings 119/136/104 deg), white_pot_lid 4 (on the
  top plate, spheres poorly reconstructed; mount centroids used), white_pot 7, water_pitcher 4.
- [V] Area-weighted self-similarity (`selfsim.py`, plots `out/cups_selfsim.png`): with markers removed
  the cups deviate from a surface of revolution by < 1 mm mean, and texture differences are smooth
  low-frequency shading (blue 0.03, beige 0.08 mean |dRGB|, one broad lobe: baked scan lighting [H]).
  Without markers spin is not observable in practice [E]. Markers are ~3 % of area, so area metrics
  dilute them; they are point features and must be handled as such.
- [V] **PnP validation, public ep 11 frame 0** (`pnp_check.py`, `spin_scan.py`): 6 marker blobs
  (3 automatic, 3 located by eye on a public frame for this check only) vs scan markers placed by
  the GT poses of both cups. Best assignment 4.1 px mean reprojection (next 13.5 px), camera 0.53 m
  from the cups. Spinning one cup about its axis while re-solving the camera: minimum at -2 deg
  (beige) and +2 deg (blue) from the GT spin; error 9-13 px at +-10 deg. So the physical markers sit
  where the scan has them, and image markers fix cup spin to about 2 deg on this frame.
- 11:20 (resumed after outage) [V] Area-weighted self-similarity for the other three objects
  (`out/selfsim_rest.log`, `out/selfsim_white_pot_lid_white_pot_water_pitcher.json`). Note the
  `second @ 12 deg` entries in the log are only the shoulder of the zero-angle minimum (the summary
  excluded only +-10 deg), not secondary minima. Proper local-minimum scan of the stored curves
  (mean NN distance in mm; floor at 0 deg is the two-sample-set noise floor 0.19-0.33 mm):
  - blue_cup geo (no markers): max 0.75, at 180 deg 0.61; no secondary minimum below 0.6 => body is
    a surface of revolution within scan noise. Colour: 0.002 at 0 vs 0.026-0.031 everywhere else (flat).
  - beige_cup geo (no markers): max 0.72, shallow minima at 106 (0.61) and 256 (0.59). Colour flat 0.074 at 180.
  - white_pot_lid geo (no markers): peak 1.84 at 104 deg, secondary minimum 1.30 at 180 deg => the bar
    handle gives a 2-fold geometric near-symmetry (only ~30 % contrast because the handle is small).
  - white_pot geo: 6.9 mm almost everywhere (handle), single minimum at 0 => unique (handle).
  - water_pitcher geo: 7.8-8.2 mm everywhere, single minimum at 0 => unique (spout + handle).
  Caveat: pitcher axis was assumed to be mesh z through the origin; the mesh frame is a PCA frame
  (note 07) so z is the longest extent, which for this can may be the spout direction, not "up".
- 11:30 [V] Physical spin axis = world z in object coords from public GT (`upaxis.py`, `out/upaxis.json`;
  `axes2.py`, `out/axes2.json`). Revolution-axis fits now agree with GT "up" to 0.5-1.8 deg:
  blue_cup / beige_cup -z (cups rest rim-up with mesh z pointing down), white_pot_lid +x,
  white_pot (0.975, 0.038, 0.219) (body r 86 mm; handle along +z), water_pitcher (0, 0.60, 0.80)
  (body axis, 52 deg from mesh z). **Correction:** the 11:20 white_pot curve used a fit biased
  18.7 deg by a mask that clipped the 86 mm body; the water_pitcher curve used mesh z (52 deg off).
  Both are superseded by the re-run below. The cups and lid curves stand.
  GT also shows non-rest orientations: blue_cup tips ~90 deg in eps 12/13 (min cos 0.01), white_pot is
  upside down at frame 0 in eps 26/43 and flips in 27/45, the pitcher tilts 80+ deg in eps 21/22 (pouring).
- 11:45 [V] Re-run about the GT-consistent axes (`symm2.py`, `summ2.py`, `out/symm2_<name>.json`), cups:
  geometry without markers deviates <= 0.76 mm mean at any spin (blue weak 2-fold at 180 deg, depth 0.25,
  consistent with slight out-of-roundness [H]; beige shallow minima at 102/256 deg). Plain high-pass
  colour correlation stays 0.78-0.85 at every spin for the marker-free blue cup: the residual is
  dominated by spin-invariant rings (rim, base band), so it must be made spin-specific before it can
  classify (next: subtract the ring mean at each (height, radius) bin). Unrolled textures show only
  baked shading and vertical specular streaks besides the markers (view-dependent, not physical [H]).
- 12:05 [V] Marker constellations about the spin axis (`markers2.py`, `out/markers2.{json,log}`; (theta deg, h mm, r mm)):
  blue_cup (-139,-72,44) (-28,51,52) (47,-65,45) (110,70,53): two rim + two base markers, irregular.
  beige_cup (-69,71,54) (35,69,53) (171,63,52): **all three at rim height, spacings 104/136/119 deg => near 3-fold**;
  spin 119 deg maps the set onto itself with 13 mm mean mismatch.
  white_pot_lid (-92,2,57) (-32,0,67) (72,2,46) (117,-1,64): on the top plate, irregular radii.
  white_pot 7 markers, best non-identity full-set mismatch 26 mm; water_pitcher 4 markers, 20 mm.
  Full constellations are unique for all five (no spin >15 deg matches within 13 mm).
- [E] Single-view subset model (camera 0.5 m, elevation 30/55/80 deg, side marker visible if within
  75 deg of its outward normal, lid markers face up; another spin "explains" the view if the visible
  sets have equal size and mean 3D mismatch < 6 mm / 12 mm):
  beige_cup ambiguous at 44 % / 97 % of azimuths (el 30) and 71 % / 100 % (el 55): mostly one rim marker
  in view, which any of the other two can impersonate. blue_cup 0-3 % / 8-24 %. lid 0 % (all four seen
  from above). pot 0 % (1.7-2.3 visible). pitcher 0-12 % (12 % = azimuths with no marker in view, where
  geometry still decides). At el 80 the side-marker model sees none (model limit, not measured).
- 12:20 [V] Geometry about the corrected axes (`symm2.py`; mean NN mm at 0 / worst / best secondary
  minimum outside the main basin; markers removed):
  blue_cup 0.21 / 0.76 / 0.63 @ 182 (depth 0.25); beige_cup 0.22 / 0.74 / 0.60 @ 102 (0.26);
  white_pot_lid 0.22 / 1.88 / 1.31 @ 180 (0.34, bar handle 2-fold); white_pot 0.28 / 1.72 / flat,
  basin half-width 6 deg (handle, unique); water_pitcher 0.37 / 7.36 / 3.16 @ 180 (0.60).
  Fraction of points moved > 2 mm by a spin (markers removed): cups 3-8 % at any spin, and these
  are interior points (r 35-44 mm vs outer wall; the scan's cup interior is lumpy [H: reconstruction
  artefact]); lid 13-23 % (16 % at 180); pot 15 % at every spin > 20 deg; pitcher 84 % at 90 deg
  but 39 % at 180 deg: its body is oval, so 180 deg is a partial geometric lookalike that only the
  spout/handle break. Pitcher remains unique by geometry (3 mm mean residual at 180 deg).
- 12:30 [V] Spin-specific texture (`symm3.py`: DoG band-pass 3-10 mm colour minus its ring mean per
  2 mm (h, r) bin; correlation with the spun copy). blue_cup: residual rms 0.038 (RGB 0-1) with
  markers, 0.023 without; the 7.6 % marker area carries 65 % of the spin-specific energy; marker-free
  correlation peaks 0.39 at 344 deg (broad basin, no repeat). Unrolled maps at x8 gain
  (`aniso_map.py`, `out/{blue,beige}_cup_aniso_unrolled.png`, top = colour, bottom = detail):
  apart from the markers the cups show only faint vertical specular streaks, broad shading blotches
  and voxel-grid ringing; no print, logo or seam. Marker-free detail is about 0.03 RGB rms
  (~8/255) and smooth [H: baked scan illumination, not albedo, so it will not follow the cup's spin in
  video]. => both cups are featureless apart from mocap markers.
- 12:40 [V] Lid top view (`aniso_top.py`, `out/white_pot_lid_aniso_top.png`, left colour, right detail x8):
  a diagonal bar handle (screw heads at both ends) through roughly the centre gives the 2-fold
  geometric lookalike; the plate texture is plain apart from 4-5 black marker mounts with white spheres
  in an irregular layout (one small mount at r ~46 mm); the scan rim is ragged/brownish (artefact).
- 12:50 [V] Outer-wall detail maps `out/white_pot_aniso_unrolled.png`, `out/water_pitcher_aniso_unrolled.png`:
  pot wall is plain apart from 7 markers and the handle socket (a dark notch at the handle root,
  visible from the side); a faint thin dark line runs along the upper wall [H: scan seam]. Pitcher
  body is plain apart from 4 markers; the spout/handle region shows as a V-notch and ridge.
- [V] Exposure (kit `data/track_3_evaluation_objects.json`): a near-symmetric object is the slot-0 anchor
  in 10 of 20 eval episodes: white_pot eps 1, 3, 5, 6; beige_cup ep 8; blue_cup eps 10, 14, 20, 32, 33.
  Non-anchor appearances: white_pot_lid ep 1, white_pot eps 8, 28, beige_cup ep 10, water_pitcher ep 20.
- 13:05 [V] Spin-specific texture correlation, all five (`symm3.py`, `out/symm3_<name>.json`, curves
  `out/spin_selfsim_curves.png`; corr at 0 / half-width of the zero peak / value at 180):
  with markers: blue 0.95 / 13 deg / +0.08; beige 0.96 / 21 / -0.39; lid 0.94 / 12 / -0.24;
  pot 0.93 / 11 / -0.23; pitcher 0.96 / 10 / +0.28.
  markers removed: blue 0.95 / 16 / +0.03; beige 0.96 / **63** / -0.42; lid 0.95 / 20 / -0.26;
  pot 0.94 / **46** / -0.30; pitcher 0.90 / 14 / +0.44.
  Marker share of the spin-specific colour energy: blue 0.65, beige 0.45, lid 0.49, pot 0.52,
  pitcher 0.76 (on 3-10 % of the area). Without markers the curves are broad single bumps that go
  negative at 180 deg, i.e. a one-sided brightness gradient [H: baked scan lighting]; the narrow
  10-21 deg peak exists only when markers are kept. No object shows a texture repeat (k-fold peak)
  above +0.12 except the pitcher's 180 deg (+0.28/+0.44, from its oval body/shading).
- 13:20 [V] Marker-subset ambiguity with a spin search (`markers3.py`, `out/markers3.log`; axis and height
  assumed known; tolerance 6 / 10 mm): one visible marker -> candidate spins: blue 1,1,1,1 / 1,2,1,2;
  beige 2,1,2 / **3,3,3**; lid 1,2,1,2 / 2,3,1,2; pot all 1 / 1-2; pitcher all 1 / all 1.
  Two visible markers -> pairs with a lookalike pair: blue 0/6 / 1/6; beige 0/3 / **2/3** (best
  lookalike residual 8.8 mm); lid 2/6 (5.5 mm) / 2/6; pot 0/21; pitcher 0/6.
- [V] Eval frame 0 (`out/eval_f0_grid.jpg`, eps 10/14/20/8): the grey marker spheres are plainly visible
  on the eval blue/beige cups, pitcher and pot, including at silhouettes, and the camera looks down
  into the cups. So the marker cue exists in eval video too (no eval labels used).
- [E] Visibility-cone sensitivity (`markers2c.py 95`, `out/markers2_cone95.log`; markers count as visible
  up to 95 deg from their outward normal because the spheres stand ~15 mm proud): ambiguous azimuths
  at 6 / 12 mm become blue 0 / 0 %, **beige 22 / 96 %**, lid 0 / 0, pot 0 / 0, pitcher 0 / 0.

## Stage A conclusion (scan-only spin self-similarity)

| object | geometry, markers removed | texture, markers removed | mocap markers | spin class |
|---|---|---|---|---|
| blue_cup | featureless: surface of revolution, max 0.76 mm mean residual; faint 180 deg minimum (0.63 mm) [V] | featureless: smooth one-sided shading only [V], likely baked lighting [H] | 4, irregular (2 rim at h 51/70 mm, 2 base at -72/-65 mm, base pair 174 deg apart) [V] | **featureless body; unique with markers** (full set 13.5 mm from any other spin; single-view ambiguity 0-3 % at 6 mm) |
| beige_cup | featureless (max 0.74 mm) [V] | featureless [V] | 3, all at rim height, 104/136/119 deg apart [V] | **featureless body; near 3-fold with markers** (119 deg spin = 13 mm mismatch; one visible marker gives 2-3 candidates; 22-71 % of single views ambiguous at 6 mm, ~96-100 % at 12 mm) [E] |
| white_pot_lid | **2-fold**: bar handle, 180 deg minimum 1.31 vs 1.88 mm peak [V] | featureless [V] | 4-5 on the top plate, irregular, all visible from above [V] | **2-fold body; unique with markers** (0 % single-view ambiguity from above) [E] |
| white_pot | **unique**: handle, flat 1.7 mm beyond +-12 deg, basin half-width 6 deg [V] | featureless apart from the handle socket [V] | 7 [V] | **unique** (geometry alone suffices) |
| water_pitcher | **unique**: spout and handle, 7.4 mm worst; partial 180 deg lookalike from the oval body (3.2 mm) [V] | featureless [V] | 4 [V] | **unique** (not a near-symmetric object) |

Implications [H, for stages B/C]:
- Spin of the cups and the lid's 2-fold ambiguity can only come from the mocap marker spheres. They are
  physical, appear in the public scans (usable for tracking) and are visible in eval video. Any
  silhouette, depth or appearance tracker that ignores or blurs the markers cannot fix cup spin.
  Texture and geometry of the bodies hold no reliable spin cue (<1 mm, ~8/255 smooth shading).
- beige_cup is the risky case (eval ep 8 as slot-0 anchor, ep 10 slot 1). It needs >= 2 markers resolved
  to better than ~8 mm in one view, or temporal accumulation across views, to break the near-3-fold
  ambiguity. A wrong pick is a ~120 deg spin of the anchor.
- blue_cup is the anchor in 5 eval episodes. Its markers fix spin when one rim marker or two markers are
  seen. If only the two base markers show, it is near 2-fold.
- white_pot (anchor in 4 eval eps) and water_pitcher are safe on geometry (handle/spout) alone.
- Stage B (proposed): measure on public video with GT how often each object shows 0/1/2+ markers on
  frame 0 and over time, and the spin error of marker-based PnP. Check the beige 3-fold flip rate and
  frame-0 marker visibility of the eval anchors (eps 1, 3, 5, 6, 8, 10, 14, 20, 32, 33) automatically.
- 12:50 Stage B started (video appearance of markers/features, pixel sizes). All needed clips already on disk (public a: 0, 11, 12, 13, 21, 41; b: 0, 11, 12, 21; c: 12). No new downloads.
- [V] Object sizes about the GT spin axis (`b/dims.py`): cups 170 mm tall, outer wall r ~44 mm (rim dia ~88 mm),
  markers reach r 54-62 mm; white_pot_lid dia ~190 mm, 48 mm tall incl. bar handle; white_pot body r 86 mm,
  110 mm tall, long stick handle reaching r 235-253 mm; water_pitcher 329 mm tall, body r ~63 mm, spout/handle to r 200 mm.
  Intrinsics: ego_cam_a fx 1150 px (2028x1520), ego_cam_b fx 567 px (1280x800). Predicted marker sphere
  (14.6 mm) diameter: cam a 34 / 24 / 17 px at 0.5 / 0.7 / 1.0 m; cam b 17 / 12 / 8 px.
- [V] Ep 11 frame 0, full-res crops (`b/crop.py`; `b/c11a_f0.png` cam a 1:1, `b/c11b_f0_z2.png` cam b x2).
  Cam a: both cups plainly show 3 markers each (blue: left rim, right rim, front base; beige: left rim,
  right rim, back rim). Spheres ~30-34 px, black mounts ~20x25 px, sharp; rim widths ~226-230 px
  => Z ~0.45 m [E, using 88 mm rim]. Cup walls are uniform matte: no logo, print, text, seam, mould line
  or wear mark is visible on either cup at ~2.6 px/mm. The only other structure is the rim ellipse and
  the cast shadow. Cam b (mono, ~1.9 MB/clip, heavy compression): cups ~105 px wide; spheres ~12-14 px,
  soft; grey sphere vs beige wall is low contrast in mono, the black mount is the more salient blob.
  Markers remain detectable by eye in cam b at this range.
- [V] Ep 21 frame 0 (`b/c21a_f0_pitcher.png`, `b/c21a_f0_cup.png`, cam a 1:1): the "water_pitcher" is a
  watering can with a long tapering spout and an open arch handle; it fills ~700x850 px and its
  silhouette alone fixes spin (consistent with stage A). 2 markers visible (~28-30 px spheres), plain
  white plastic otherwise, no print/logo. Blue cup: rim ~217 px wide => Z ~0.48 m [E]; 3 markers visible
  (~28-32 px), wall uniform blue with a soft vertical sheen only; no print, seam or wear.
- [V] Ep 0 frame 0, pot + lid (`b/c0a_f0_pot.png` 1:1, `b/c0a_f0_lidmk_z3.png` x3): lid ~407 px wide
  => Z ~0.54 m [E, 190 mm dia]. **The lid carries two marker sizes**: 3 large spheres (~28 px, ~14 mm) on
  black bases and 2 small spheres (~13-14 px, ~6-7 mm [E]) on round black bases (~25 px), all 5 visible
  from above. Bar handle (~200 px long) with screw heads at both ends (~16 px); concentric pressed rings
  (spin-invariant); plain white, no print. Pot: plain white body, side markers on both flanks, one marker
  on the long stick handle, two handle rivets (~12 px) at the handle root. Pot spin is fixed by the handle
  (~260 px long here). The small lid spheres are under-resolved in the scan (stage A "poorly reconstructed");
  size difference is an extra discrete cue [H: usable only at <= ~0.6 m in cam a, ~7 px in cam b].
- [V] Ep 11 beige cup x3 (`b/c11a_f0_beige_z3.png`): all three beige markers are the same large size
  (~28-30 px spheres at ~0.45 m), unlike the lid. Mounts are irregular black pads (putty/foam-like, ragged
  edges, ~25x35 px), each a different shape [H: mount shape could identify individual markers, but it is
  a ~10 mm, view-dependent cue that the scan only roughly captures]. Wall and interior plain; soft
  interior shading only. So nothing in the video beyond marker layout breaks the beige near-3-fold.
- [V] **New cue: the blue cup's base carries moulded relief marks.** Ep 12 frame 180 (cup upside down in the
  rack; `b/c12a_f180.png` 1:1, `b/c12a_f180_base_z3.png` x3): the outside of the base shows an asymmetric
  set of embossed marks (a rounded-rectangle mark ~25x15 px, a small symbol, and a cluster of small rings),
  typical of mould/recycling codes [H about meaning]. Base ~170 px wide => Z ~0.47 m [E]; marks are
  ~10-25 px (~4-10 mm), low contrast (relief shading only, no ink), softened by compression. Visible only
  when the base faces the camera (cup tipped or inverted); in the rack episodes (12/13) it is a spin cue
  independent of the markers. Two base markers also visible (left, right) plus one lower-wall marker.
- [V] Scan check of the cup bases (`b/base_render.py`, `b/cup_bases_scan.png`; colour / colour detail x8 /
  normal shading): **the beige_cup scan base carries a clear embossed inscription** (a row of character-like
  marks across the centre, ~50x15 mm, visible in both texture detail and geometry shading). The blue_cup
  scan base looks plain at this gain (dark texture, noisy), although the video shows relief marks on it.
  Stage A missed the bases because its maps covered the walls and rims only.
- [V] CLAHE base renders (`b/base_render2.py`, `b/cup_bases_scan2.png`; left colour, middle/right normal
  shading under two lights): **both** cup scans carry the base inscription in the texture: rectangular
  boxed character groups, a small ring/circle symbol and character columns, spread over ~50-60 mm of the
  ~70 mm base, clearly asymmetric (no rotational repeat). Geometry shading shows only triangle-facet noise
  (~3-5 mm facets), so the relief is baked into the texture, not resolved in the mesh. Usable as a
  spin template from the public scan whenever a cup's base faces the camera.
- [V] Inner floors (`b/inner_render.py`, `b/cup_inner_floor_scan.png`): plain for both cups (beige shows
  lumpy reconstruction artefacts at the floor edge only). The inscription is outside-only, so it is
  hidden for an upright cup on the table and helps only when the base faces the camera.
- [V] Ep 11 over time (cam a, 2 fps samples, `b/tsheet.py`, `b/ts_a11.jpg`), by-eye marker counts
  (blue / beige): f0 3/3; while grasped and lifted 1-2 / 1-3; final stack (beige nested in blue) 2/2-3.
  Every sample shows >= 1 marker on each cup; >= 2 on most. The grasping hand covers the gripped side
  (usually one marker). The lifted beige cup is motion-blurred in 2 of 14 samples (markers smeared to
  ~2x their length). Cup walls show no other feature in any sample; the blue cup base stays hidden.
- [V] Ep 0 over time (`b/ts_a0.jpg`, 38 samples at 2 fps): the lid's 5 top markers and its bar handle stay
  visible in almost every sample; the grasping hand covers 1-3 of them while the lid is moved, and the lid is
  steeply tilted (top foreshortened, markers bunched) in ~3 samples during removal/replacement. The lid is
  never inverted. The pot's long white stick handle (with a hanging hole at its end) is visible in every
  sample, so pot spin never depends on markers; the pot interior is plain. Motion blur hits the lifted pot
  in ~3 samples (rim and handle smeared). No print or logo on either object.
- [V] Ep 21 over time (`b/ts_a21.jpg`, 19 samples): the blue cup is lifted and held tilted by the left hand
  for the pour (~samples 6-15); the hand covers one side, 1-3 markers stay visible, the interior faces the
  camera and the base is never seen. The watering can tilts ~80 deg while pouring and is partly cut by the
  top image edge in ~5 samples, but its spout or arch handle stays in view (2 markers on the body seen in
  most samples). Spin of the can is never in doubt; cup spin rests on 1-3 markers throughout.
- [V] Ep 11 cam b over time (`b/ts_b11.jpg`, crop x0.9): the same markers are visible as in cam a, as
  ~10-14 px blobs; on the beige (light grey in mono) cup the black mount is the salient part, on the blue
  (mid grey) cup the light sphere is. Occlusion pattern is the same as cam a (cam b sits ~beside cam a).
  The lifted beige cup looks sharper in cam b than in cam a samples 4-5 [E: shorter exposure on the mono
  sensor], so cam b can bridge cam a motion-blur frames for marker localisation [H].
- [V] Blur check, ep 11 frame 30 (`b/blur_ab11.png`: cam a x0.8 | cam b x1.6, then frame 40): while the beige
  cup is lifted, cam a shows a ~25-35 px smear (doubled rim, marker sphere a grey streak), whereas cam b at
  the same frame index is sharp: sphere and rectangular black mount both crisp. Confirms the cam b
  exposure advantage on fast motion [V for this frame; general rate untested]. (Frame-40 crops missed the cup.)
- [V] Ep 12 over time (`b/ts_a12.jpg`, 19 samples): upright cup with 2-3 markers (samples 1-4); hands wrap
  the cup while it is turned horizontal (6-9, 1-3 markers, base end-on to the side); then it is inverted
  into the rack, and **the base inscription faces the camera in samples 11-19 (~frame 100 to the end,
  ~45 % of the episode)**, clearly legible as a mark pattern even at x0.4. A spin-invariant moulded ring
  (a small step on the wall ~1/4 height from the base) is also visible when the cup lies sideways.
- [E] Pixel budget (`b/pixel_table.txt`; fx a 1150 / b 567; observed table range at frame 0 is Z 0.45-0.55 m,
  lifted objects come to ~0.35 m): large marker sphere 37 / 30 / 24 / 17 px in cam a at Z 0.45 / 0.55 /
  0.7 / 1.0 m (cam b 18 / 15 / 12 / 8 px), matching the 28-34 px measured at 0.45-0.54 m. Small lid sphere
  17 / 14 px (cam a) and 8 / 7 px (cam b). Base inscription marks (~6 mm) 15 / 12 px in cam a, 8 / 6 px in
  cam b; the whole inscription (~50 mm) 128 / 105 px. Spin sensitivity of a rim marker (r 54 mm,
  side-on): cam a 2.4 px/deg at 0.45 m, 1.6 px/deg at 0.7 m; cam b 1.2 / 0.8 px/deg. With ~1 px marker
  centroids, a visible marker pins spin to ~0.4-0.7 deg (cam a) or ~0.8-1.3 deg (cam b), far below the
  30 deg MP-SR and 0.5 rad SP-SR limits; the risk is identity (which marker), not precision. The beige
  119 deg lookalike's best-pair 3D mismatch (8.8 mm) projects to at most ~22 / 15 px (cam a at 0.45 /
  0.7 m) or 11 / 7 px (cam b): separable only when two markers and the rim are seen together.
- [V] Scan close-ups of each cup marker, radial outside view (`b/mount_render.py`, `b/cup_mounts_scan.png`).
  Beige: marker @35 deg (h 69 mm) and @-69 deg (h 71) sit in visible square/rectangular black mounts
  ~20 mm across; marker @171 deg (h 63) shows almost no mount (sphere directly on the wall) and sits
  lowest, ~19 mm below the rim top vs ~11-13 mm for the other two (rim top h ~82 mm). In cam a at 0.45 m
  the rim-to-sphere gap is ~48 px for @171 vs ~25-33 px for the others [E], so a single visible
  @171 marker is identifiable when the rim is in view; @35 vs @-69 differ by only ~2 mm in height and
  stay confusable from one marker (consistent with stage A's 2 candidates per single marker).
  Blue: all four markers sit in black mounts of similar size; identity comes from layout (rim vs base).
  Sphere texture in the scan is coarse (blocky ~2 mm texels); mounts are dark texture plus slight relief.
- [V] Eval glance for method design only (no labels recorded or used; `b/ts_e8.jpg`, `b/ts_e14.jpg`,
  `b/ce8a_f0_beige.png`). Eval ep 8 (beige_cup = slot-0 anchor): at frame 0 the upright beige cup is at
  Z ~0.48 m [E, rim ~217 px] and **all three of its markers are in view** (one front-left with its mount,
  one at the back rim, one at the right silhouette), so the full constellation, which is unique (stage A:
  13 mm best non-identity mismatch, ~30 px here), is available at the anchor frame. Later the cup is lifted
  and tilted to pour into the pot (base partly toward the camera in ~3 of 22 samples). Eval ep 14 (blue_cup
  anchor + dish rack) repeats public ep 12: upright with 2-3 markers at frame 0, then inverted into the rack
  with the base inscription facing the camera for the last ~40 % of samples. A spin-invariant moulded
  ring near the base is visible on the beige cup too.

## Stage B conclusion (video appearance, public eps 0/11/12/21 cam a + ep 11 cam b; eval 8/14 glance)

Spin cues seen in the video (cam a sizes at Z ~0.45-0.55 m, cam b about half):

| object | mocap markers in video | other spin cues seen | no cue found |
|---|---|---|---|
| blue_cup | large grey spheres (~30-37 px a / 13-18 px b) on black mounts; 2-3 visible upright, 1-3 while grasped [V] | **embossed base inscription** (marks ~10-25 px, extent ~130 px) when tipped or inverted (ep 12 last ~45 %, eval 14 last ~40 %) [V]; it is also in the scan texture [V] | wall: no print, logo, seam or wear; moulded ring near base and specular streaks are spin-invariant [V] |
| beige_cup | same large spheres; mounts differ: @171 deg marker sits lower (19 vs 11-13 mm below rim) with almost no mount [V scan] | base inscription in the scan texture [V]; base seen only while pouring (eval 8, ~3 samples) | wall plain [V] |
| white_pot_lid | 5 on top, **two sizes** (3 large ~28 px, 2 small ~13-14 px) [V]; visible from above in almost every frame | bar handle (2-fold) with screw heads (~16 px) [V] | plain white |
| white_pot | side, flank and handle markers [V] | long stick handle with end hole, rivets; always visible [V] | interior plain |
| water_pitcher | 2 on body usually visible [V] | spout and arch handle dominate the silhouette [V] | plain white |

Main points:
- [V] The markers are the only spin cue for an upright cup. They are large and sharp in cam a (24-37 px at
  0.45-0.7 m) and resolvable but soft in cam b (12-18 px; heavy compression, low sphere contrast on the beige
  cup in mono). At least one marker per cup was visible in every 2 fps sample of eps 11, 12 and 21.
- [V] New since stage A: both cups carry an asymmetric embossed inscription on the outside of the base, present
  in the public scan textures. It gives an independent, marker-free spin template whenever the base faces the
  camera, which happens in the rack task (public 12, eval 14) and briefly during pours (eval 8). Stage A's
  wall-only maps missed it. The interiors are plain.
- [V] The lid uses two marker sizes, an extra discrete cue the scan barely resolves.
- [E] Precision is not the bottleneck: one marker localised to ~1 px pins spin to ~0.4-0.7 deg in cam a
  (~0.8-1.3 deg in cam b), against the 30 deg / 0.5 rad success limits. The failure mode is identity (which
  marker, or which beige 120 deg branch), plus occlusion by the grasping hand and cam a motion blur
  (~25-35 px smear when lifted; cam b stayed sharp in the same frame).
- [V, view only] For the beige anchor (eval 8) all three markers are visible at frame 0, so the unique full
  constellation is available exactly where the scorer anchors.
- Correction: the ep 11 frame 0 entry says "no mould line"; a spin-invariant moulded ring near the base is
  visible on both cups from other angles (it carries no spin information).

Proposed stage C [H]: (1) automatic marker detection with an identity search against the scan constellation
(both cams, stereo for depth) on public eps 11/12/13/21/22 with GT, giving the spin error and the beige 3-fold
flip rate per frame; (2) a base-inscription template matcher from the scan texture, scored on public ep 12/13
inverted frames; (3) an automatic frame-0 marker count for all eval anchors.

## Stage C running log (automatic spin resolution, yaw accuracy, literature)

- 13:xx Stage C started (resumed session). Work dir `work/12/c/`. Plan: (1) record the reused GT-free joint fit
  (`joint_fit.py`, `out/joint_fit_ep11.json`, never logged before the outage); (2) Monte Carlo of a marker
  identity + spin solver on the scan constellations with occlusion, false blobs and pose-prior noise (cam a/b);
  (3) automatic blob detector + spin solver on real public frames scored against GT; (4) base-inscription
  render-and-compare feasibility on ep 12; (5) literature check; (6) final design and rewrite.
- [V] Context reused from notes 02 and 11 (not re-measured): scorer is plain ADD (not ADD-S) with one rigid
  slot-0 frame-0 alignment (`metric_code/track_3/AUC.py` `_object_add`, `_warp_to_reference_start`, checked
  here). Anchor-spin budget (note 11 B2): AUC >= 0.9 needs <= ~5 deg, 0.7 at 10 deg, ~0.5 at 15; MP-SR needs
  <= ~5-8 deg; SP-SR tolerates 20-30 deg. Placement priors (note 11): Cup_In_Dish_Rack cup-vs-rack relative yaw
  LOO 1.9-2.7 deg; Water_Can pitcher-vs-cup 6-8 deg; no prior for eval 8/32/33 (vision needed).
- [V] Reused, previously unlogged: `joint_fit.py` (GT-free; two upright cups on one unknown table plane, unknowns
  plane normal/offset + per-cup base position and spin, fitted to 6 marker blobs of ep 11 frame 0, 3 of them
  located by eye; GT read only to score). Relative pose of blue cup in beige frame: 6.0-8.6 mm position,
  1.8-3.2 deg rotation, bearing (anchor-spin proxy) error 1.1-2.6 deg at 0-2 px added blob noise (13 trials);
  at 4 px: 5 of 6 trials 0.0-3.3 deg bearing, **1 of 6 a ~120 deg flip** (rel. rotation 121 deg, fit rms still
  only 2.0 px, i.e. the beige near-3-fold branch fits almost as well) (`out/joint_fit_ep11.json`). Table plane
  distance 0.51 m. So with 3 + 3 markers seen, identities are right at <= 2 px noise, and the beige 120 deg
  branch already appears at 4 px with a residual that does not flag it.
- 13:xx Running job: `work/12/c/mc_spin.py <object> 300` for the five objects in parallel (launched from `work/12`,
  logs `c/out/mc_<object>.log`, results `c/out/mc_<object>.json`). Synthetic marker-identity Monte Carlo, configs
  base / tight / harsh / multi5, cam a and cam b. Smoke test (beige, 20 trials, base): median error 1.1 deg (cam a),
  but 25 % of trials > 30 deg; 4 of 7 single-detection trials flipped, 0 of 11 two-detection trials.
- [E] MC v1 (`c/out/v1/mc_*.log`, 300 trials per cell, markers only: the solver uses no silhouette/handle/spout
  geometry, so pot and pitcher numbers are marker-only upper bounds on error). Visibility in v1 = sphere-centre
  pixel test, which the real frame below showed to be too strict at silhouettes (pessimistic; superseded by v2).
  Cam a, |spin error| median / P(>5 deg) / P(>30 deg):
  base (centre prior 5 mm, tilt 2 deg, 1.5 px, p_det 0.9, hand drop 0.3, 0.5 false blobs): blue 2.6 / 0.33 / 0.10,
  beige 2.6 / 0.41 / 0.31, lid 0.6 / 0.13 / 0.08, pot 0.3 / 0.02 / 0.01, pitcher 2.3 / 0.27 / 0.13.
  tight (2 mm, 1 deg): blue 1.3 / 0.11 / 0.06, **beige 1.1 / 0.29 / 0.21**, lid 0.5 / 0.06 / 0.04.
  harsh (3 px, p_det 0.75, drop 0.5, 1.5 false): blue 0.37, beige 0.52, lid 0.25 flip rate (>30 deg).
  multi5 (5 views, +-8 deg azimuth sway, joint): blue 0.7 / 0.10 / 0.01, **beige 0.5 / 0.12 / 0.08**, lid 0.3 / 0.02 / 0.02.
  Cam b: similar flip rates, medians ~1.5x larger. Flips concentrate where <= 1 marker is detected
  (beige base: 1 detection -> 30-57 % flips, 2 -> 0-8 %).
- [V] Real frame, public ep 11 frame 0 cam a (`c/real_ep11.py`, overlay `c/out/real_ep11_f000_crop.png`): GT-placed
  scan markers project onto the real spheres (eval camera 4.1 px). The simple colour blob detector (`detect2d.py`,
  inside a GT-box stand-in for a tracker mask, size-gated) found only the spheres seen against the cup bodies:
  blue 2 of 3 visible, beige 1 of 3, 0 false blobs; it **misses grey spheres seen against the grey floor at the
  silhouette** (3 misses). Spin from these detections (40 prior draws): blue median 2.3 deg (5 mm prior) / 1.3 deg
  (2 mm), 0/40 flips; **beige (1 detection) 19/40 flips at 5 mm, 10/40 at 2 mm** (errors -137, -133, +109 deg =
  the 120 deg branches). A detector that also finds silhouette spheres is required for the beige anchor.
- 14:xx Launched MC v2 (same configs; visibility = >= 30 % of the projected sphere disk unoccluded) -> `c/out/mc_*`.
- [V] Missed spheres (`c/out/miss_crops.png`, x3): grey spheres against grey textured floor at the cup silhouettes,
  clearly visible to the eye but with the same hue/saturation as the floor, so colour thresholding merges them with
  it. Hough circles (`c/detect_hough.py`, radius 0.6-1.35 x expected) find 5 of 6 only at loose thresholds (387
  candidates in the two cup boxes; 103 at a tighter one with 4 of 6). A hand-made score (radial edge strength / interior
  std / saturation) ranks the 4 hits 2, 4, 5, 10 of 103. => Hand-crafted detection is not reliable enough; the
  design needs a learned sphere detector (heatmap) trained on public frames with labels projected from GT [H].
- [V] Real frame with the combined detector (colour blobs + top-5 Hough candidates per cup box; `real_ep11.py 0 comb`,
  `c/out/real_ep11_f000_comb.json`): blue 3 blobs (2 true, 1 false) -> spin median 0.35 deg (5 mm prior), 0/40 flips.
  **Beige 3 blobs (2 true, 1 false) -> 24/40 (5 mm) and 27/40 (2 mm) flips to the -131 deg branch.** Diagnosis
  (`c/dbg_beige.py`, `c/dbg_vis.py`): the two front beige markers are explained almost equally by the true spin and the
  -131 deg branch (projections 5-12 px apart, the near-3-fold); the deciding third marker (back rim, visible in the image
  at the silhouette, 40-69 % of its disk unoccluded) was classed hidden by the coarse visibility table (sub-4 z-buffer
  with a 3 px min-filter: 20 %), so it could not vote, and one false blob tipped the balance. Lesson: for the beige cup the
  visibility model and the detector must both handle silhouette spheres; two markers are not enough under the near-3-fold.
- [E] MC v2 (`c/out/v2/`, disk visibility at sub-4, threshold 30 %) ~= v1: cam a flip rate (>30 deg) base / tight / multi5:
  blue 0.10 / 0.05 / 0.01, beige 0.32 / 0.22 / 0.05, lid 0.09 / 0.05 / 0.01, pot 0.01 / 0.00 / 0.00, pitcher (markers only)
  0.13 / 0.11 / 0.00. Launched v3 (sub-2 z-buffer, 150k points, threshold 25 %; matches the real frame's visibility).
- [V] Base inscription as a spin template (`c/base_autocorr.py`, `c/out/base_autocorr.json`; scan base face rendered
  along the spin axis at 4 px/mm, band-passed, NCC with its own rotation, markers/background masked). Inside r < 25 mm
  (the inscription; excludes the spin-invariant rim ring): blue half-width of the zero peak 2 / 4 deg (0.25-1.5 mm /
  0.5-3 mm band), best correlation beyond +-20 deg 0.04 / 0.15; beige 2 / 6 deg, 0.07 / 0.37. => unique, sharp
  template, no rotational repeat. Including r 25-30 mm (rim ring) with the coarse band gives broad 54-76 deg peaks and
  0.77-0.87 lookalikes, so the matcher must mask the rim. Video-side matching (ellipse rectification of the inverted
  base, ep 12 frames 100-262) was NOT run here; stage B saw the marks at 10-25 px, i.e. inside this band [E].
- Literature check (fetched 2026-10-05; [lit] = read in the source, [lit-m] = from memory, not re-fetched):
  - [lit] BOP 2020 (Hodan et al., arXiv 2009.07378, Sec. 2.3): an object's symmetry set is every transform whose
    Hausdorff distance is below max(15 mm, 0.1 d), "to avoid breaking the symmetries by too small details", minus
    those the organisers judge resolvable by texture; MSSD/MSPD take the minimum over that set and VSD scores visible
    surface only. Under that rule both cups (whole marker set 13-13.5 mm from another spin) and the lid count as
    symmetric, so BOP-tuned methods are neither trained nor scored to resolve our spins. Our scorer is plain ADD.
  - [lit] FoundationPose (Wen et al., CVPR 2024, arXiv 2312.08344 HTML): 42 icosphere views x 12 in-plane rotations
    = 504 hypotheses, refined and ranked by render-and-compare on 160x160 crops; no symmetry-specific handling; Sec.
    5.4 failure case: texture-less + occlusion + few edges -> wrong orientation; positives for the ranking loss are
    poses within 10 deg [lit, via the HTML summary]. At 160 px a cup crop (~300 px wide) is scaled ~0.5, so a 30 px
    marker becomes ~15 px and the 8.8-13 mm branch differences ~5-10 px [E]: possibly rankable, but nothing in training
    pushes the scorer to weight markers, and our rim/base markers are the only cue. [H] FoundationPose spin on cups
    should be treated as unreliable until measured on public frames.
  - [lit] EPOS (Hodan et al., CVPR 2020, arXiv 2004.00605): surface fragments with many-to-many correspondences
    handle global/partial symmetries; SurfEmb (Haugaard & Buch, CVPR 2022, arXiv 2111.13489): learned multi-modal
    correspondence distributions with no symmetry labels, sample/score/refine hypotheses. Both keep ambiguity explicit;
    the useful idea for us is to output a multi-modal spin distribution, then let marker evidence and priors pick.
  - [lit-m] Distribution/ambiguity methods: Manhardt et al. ICCV 2019 (multiple hypotheses for ambiguous poses),
    Implicit-PDF (Murphy et al., ICML 2021), SpyroPose (Haugaard et al., 2023); MegaPose (Labbe et al., CoRL 2022) and
    CosyPose (ECCV 2020) use render-and-compare with symmetry-aware losses (i.e. they deliberately ignore spin).
  - Implication [H]: no off-the-shelf method is built to resolve near-symmetries from small physical details; the
    marker spheres must be modelled explicitly (keypoints with known 3D layout = classic PnP with identity search, as
    for active/retro-reflective marker tracking), with render-and-compare as a check and priors as fallback.
- [V] Real frame re-run with the finer visibility table (v3; `c/out/real_ep11_f000_comb*.json`), beige with 2 true + 1
  false blob: still 21-31 of 40 prior draws flip to the -131 deg branch, with or without the missing-marker term
  (`base_wm0`/`tight_wm0`). The two front markers fit both branches within 5-12 px, comparable to the ~4 px model/camera
  error of this frame, so two beige markers cannot decide. **Oracle-recall test** (`real_ep11.py 0 comb add3`: the missed
  back-rim silhouette sphere added at its by-eye position, public frame, test only): 0/40 flips, median 0.85-0.99 deg in
  all four prior settings. Blue (2 true + 1 false): 0/40 flips, median 0.35-0.51 deg in all settings.
  => On a real frame the solver is accurate to ~1 deg once identities are right; beige needs all three markers.
- [E] **MC v3 final** (`c/out/v3/mc_*.{json,log}`; sub-2 z-buffer visibility, 25 % disk threshold; mean visible markers
  el 25-60 deg: blue 2.8, beige 2.6, lid 3.4, pot 5.3, pitcher 2.5). |spin error| median / P(>5) / P(>30), cam a:
  | object | base (5 mm, 2 deg) | tight (2 mm, 1 deg) | harsh | multi5 (5 views) |
  |---|---|---|---|---|
  | blue_cup | 1.8 / 0.23 / 0.08 | 1.0 / 0.08 / 0.05 | 4.6 / 0.48 / 0.28 | 0.45 / 0.04 / 0.00 |
  | beige_cup | 1.0 / 0.28 / **0.20** | 0.7 / 0.13 / **0.09** | 8.9 / 0.57 / 0.39 | 0.27 / 0.02 / 0.02 |
  | white_pot_lid | 0.6 / 0.10 / 0.07 | 0.5 / 0.04 / 0.03 | 1.8 / 0.34 / 0.24 | 0.25 / 0.00 / 0.00 |
  | white_pot | 0.24 / 0.01 / 0.01 | 0.21 / 0.00 / 0.00 | 0.65 / 0.06 / 0.03 | 0.08 / 0.00 / 0.00 |
  | water_pitcher (markers only) | 1.5 / 0.18 / 0.09 | 0.8 / 0.08 / 0.06 | 3.8 / 0.42 / 0.25 | 0.50 / 0.02 / 0.00 |
  Cam b: same flip rates within +-0.04, medians 1.2-2x larger (blue base 2.2, beige 1.9, lid 1.0, pot 0.45 deg).
  By number of detected markers (cam a base, flip rate): blue 0:0.71 1:0.22 2:0.06 3:0.01; **beige 0:0.57 1:0.46 2:0.17
  3:0.03** (47 of 60 beige flips fall in 100-140 deg = the 3-fold branch); lid 1:0.27 2:0.10 3:0.02 4:0.00.
  Caveat: multi5 draws detections independently per view, so it is optimistic: real consecutive frames share the same
  occlusions and misses. Prior/trial setup: object upright at rest, D 0.42-0.70 m, elevation 25-60 deg.
- [V] Render-and-compare branch check, beige, public ep 11 frame 0 (`c/rc_branch.py`, `c/out/rc_branch_ep11_f000.{json,png}`):
  for each spin branch (0, -120, +120, -131, +113 deg) the centre shift and spin were fitted to the two front blobs,
  then the textured scan was point-splat rendered (400k samples, z-buffered) with the real camera. Whole-cup gradient
  NCC: true 0.237, -131 branch 0.221, -120 0.152, +120 0.098, +113 0.134 (right answer, 0.016 margin). Restricted to
  the union of all branches' marker disks (where the branches differ): **-131 branch 0.172 vs true 0.056** (wrong
  answer). Luminance high-pass NCC is ~0 everywhere. So a crude render-and-compare does not reliably separate the beige
  branches: the silhouette/rim dominate and are branch-invariant, the scan colours (greenish, baked lighting) differ
  from the video, and the 4 px camera error is comparable to the 5-12 px branch differences. Caveats: no lighting model,
  splat renderer, evaluation camera from 6 points. Explicit marker detection with full recall (above) did decide (0/40).
- Stage C closed; notes rewritten (summary, design, accuracy, literature, next steps at the top; pre-rewrite copy at
  `work/12/c/out/notes12_before_rewrite.md`). Stage C artifacts (`work/12/c/`): `mc_spin.py` (simulator + solver; run from
  `work/12`: `venv/bin/python c/mc_spin.py <object> 300`), `real_ep11.py` (`0 [comb] [add3] [png]`), `detect_hough.py`,
  `dbg_beige.py`, `dbg_vis.py`, `base_autocorr.py`, `rc_branch.py`; outputs in `c/out/` (`v1/`, `v2/`, `v3/` MC runs,
  `real_ep11_f000*.json`, `real_ep11_f000_crop.png`, `miss_crops.png`, `base_autocorr.json`, `rc_branch_ep11_f000.*`).
  No jobs running.

## Skeptical verification (verifier, 2026-10-05; scripts in `work/12-verify/`)

- C1 geometry [V, own code `v_c1_geo2.py`, trimesh sampling, axis re-fitted by minimising outer-wall
  out-of-roundness, markers excluded 16 mm, rotated points falling in marker holes dropped]: spin NN mean <= 0.63 mm
  (blue, @104) / 0.56 mm (beige, @200) vs noise floor 0.24-0.25 mm; outer-wall out-of-roundness median 0.22 / 0.06 mm,
  p95 0.59 / 0.22 mm. Remaining > 2 mm bins are exclusion holes and the base edge, not bumps. Reproduces "<= 0.76 mm
  mean" (theirs includes hole effect). Wording fix: this is a *mean* NN distance to a spun copy of a tapered surface of
  revolution, not "within 0.76 mm of a perfect cylinder"; p99 of the spun-copy distance is ~3.3 mm. Note: an axis from
  one GT frame without re-fitting (2 mm offset) inflates blue to 2.1 mm mean, so the result depends on a fitted axis.
- C1 texture [V, re-ran `symm3.py blue_cup` in `work/12-verify/rerun/`]: identical numbers (aniso rms 0.0376 / 0.0232
  marker-free, markers carry 0.65 of energy, marker-free max corr 0.39 @344). Note the marker-free blue peak is still
  narrow (half-width ~16 deg vs 13 with markers), i.e. the scan texture has spin-specific detail away from markers;
  calling it "smooth shading only" rests on the [H] that it is baked lighting, plus the video crops.
- C2 circularity [V, `v_c2_circ.py`, public ep 11 f0]: the evaluation camera is a PnP fit of GT-placed scan markers to
  the same 6 marker pixels the spin solver then uses (3 placed by eye; the add3 "oracle" pixels are two of them). Best
  pure-reprojection spin of each cup: 6-pt camera -0.65 / +1.45 deg (blue / beige); joint camera+spin -1.5 / +2.3 deg;
  3 px bootstrap of the camera SD 0.8 deg (90 % range ~2.5 deg); camera from the other cup only (P3P, 1.7-2.7 deg away)
  -5.1 / +4.7 deg at ~20 px. So 0.35-1.0 deg is agreement inside a GT-fitted camera, not a measured accuracy; this
  frame can only support ~1-2.5 deg (consistent with the GT-free joint_fit 1.1-2.6 deg).
- C2/C3 re-run [V, copy `work/12-verify/real_ep11_copy.py 0 comb`, outputs redirected]: bit-identical to the stored
  run. Blue 2 true + 1 false blob, median 0.35/0.50/0.51/0.50 deg, 0/40 flips in all four settings, every error
  negative (-0.1 to -1.4 deg, i.e. the 6-pt camera bias found above). Beige 2 true + 1 false: 28/25/22/21 of 40 flips
  to ~-131 deg (base/tight/base_wm0/tight_wm0), so the range is 21-28, not 21-31. Stored add3 file: beige tight_wm0
  has 1/40 flip (not 0/40 in all four settings).
- C4 stored MC v3 logs/json match every quoted number (base/tight >30 deg: blue .08/.05, beige .20/.09, lid .07/.03,
  pot .01/.00, pitcher .09/.06; multi5 .00-.02; beige by ndet 0:.57 (n=14) 1:.46 (n=57) 2:.17 (n=134) 3:.03 (n=95);
  47/60 beige flips in 100-140 deg). Blue and lid flips are mostly 140-180 deg (2-fold-like), not 120.
- C4 re-run [V reproduction, E sensitivity; `work/12-verify/v_c4_mc.py` calling the original simulate/solve, cam a,
  300 trials, same seeds]: beige base/tight reproduce exactly (.200/.093, same by-ndet and histogram). Sensitivity
  not in the original: the solver assumes the exact scan marker layout, exact camera, the simulator's own visibility
  table and 1.5 px noise. With the solver's marker centres perturbed by N(0, 2 mm)/axis (about the ~5-6 px per-marker
  model error implied by the real frame's 4.07 px 6-point PnP residual) the beige flip rate rises .20 -> .35, and with
  all 3 markers detected .03 -> .27. Recall 0.67 + 1 false blob (closer to the real-frame detector): .44. So the
  single-frame rates are lower bounds under an idealised model, not only multi5.
- C2 blob accounting [V, `real_ep11_copy2.py` dump]: blue's "false" blob at (798,988) is the left-rim silhouette
  sphere blue#2 (4.6 px from its GT projection), which the evaluation z-buffer marks hidden; blue really had 3 true
  blobs and 0 false. Beige: blobs = mk0 front-left (3.1 px), mk1 right silhouette (5.3 px), and a real false blob at
  (1404,1194); mk2 (back rim, by-eye (1273,888)) missed and also marked hidden.
- C3 branch fit [V, `v_c3_branch.py`, 6-pt camera]: no refit, true-branch projections are 3-5 px from the two beige
  blobs, the -131 branch 14-16 px. With spin + table-plane shift refit under a 5 mm prior, -131 fits better than the
  truth (2.1/2.5 px with a 5.9 mm shift vs 2.9/3.5 px); +-120 fits poorly (14-16 px). The decisive third marker is
  predicted ~50 px apart by the two branches ((1277,888) vs (1325,871)). Conclusion of C3 holds; "5-12 px" is not
  reproduced (0-shift: 3-5 vs 14-16 px; refit: both <= 3.5 px).
- C3 false-blob test [V, `real_ep11_copy3.py 0 comb nofalse`, verifier oracle drops blobs > 10 px from any GT
  marker]: beige with only its 2 true blobs gives the identical 28/25/22/21 of 40 flips. The false blob plays no role;
  the stage C remark "one false blob tipped the balance" does not hold. Two beige blobs alone are ambiguous.
  `dbg_beige.py` re-run: the "5-12 px" is the separation of branch projections (5.8 / 12 px, undistorted), and the
  v3 solver visibility table marks all 3 beige markers visible at GT (the "classed hidden" explanation was v2 only).
- C4 sensitivity, more [E]: beige base with 1 mm marker error .24 (3-detected .06); tight with 2 mm .29 (tight's gain
  vanishes); blue base .083 -> .087 (1 mm) -> .117 (2 mm). Blue is robust, beige is not.
- C1 base inscription [V]: public GT shows the blue cup inverted in ep 12/13 (53 / 63 % of parquet rows with up_z <
  -0.5); the beige cup is never tipped in public data (ep 11, min up_z 0.98). So the beige inscription is verified
  in the scan only, never in video. (Side note: parquet rows per episode are 137-190, fewer than the ~262 video
  frames, so any frame > 0 GT lookup must map video time to rows; frame 0 checks are unaffected.)
- Verifier verdicts: C1 holds with wording fixes; C2 numbers reproduce but are not an accuracy measurement (camera
  fitted to the same pixels with GT); honest real-frame bound ~1-2.5 deg; blue blobs were 3 true / 0 false; C3 holds
  (21-28/40); C4 reproduces but single-frame rates are idealised lower bounds (beige roughly doubles with mm-level
  model error).
- Correction to the verifier side note above: ep 11 has 137 video frames (cam a, 20 fps) and 137 parquet rows with
  frame_index 0..136, so rows and frames do correspond; episode lengths simply vary. Withdrawn.

## Stage B re-run (2026-10-06; workflow "try again")

- Stage B was already complete on 2026-10-05 (conclusion above; artifacts in `work/12/b/` present and checked:
  crops, time sheets `ts_*.jpg`, `pixel_table.txt`, scan renders). Clips on disk, no new downloads. This pass fills
  stage-B gaps only: (1) does the scan's beige identity cue (@171 deg marker lower, almost no mount) show in video;
  (2) is the base inscription resolvable in cam b; (3) automatic (not by-eye) sphere size and contrast at known
  marker positions. Outputs in `work/12/b2/`.
- [V] Gap 1, beige identity cue in video (`b2/beige_id.py`, `b2/beige_id_ep11_f0.{png,json}`; public ep 11 f0 cam a,
  analysis-only camera = stored 6-point GT-marker PnP, 4.07 px). Projected sphere outlines land on the real spheres for
  all three beige markers. In this frame @35 is front-left, @171 is at the right silhouette against the floor, @-69 is
  behind the far rim (partly hidden by it). Scan rim-top minus marker height: @35 13.3 mm, @171 19.3 mm, @-69 11.0 mm.
  Projected rim-to-sphere gaps are 40 / 32 / 15 px, so the image gap follows the viewpoint (foreshortening, which side
  of the cup), not the 6-8 mm height difference. At ~55 deg elevation and Z 0.44 m the height difference itself is
  only ~10 px (1150 x 7 mm x cos 55 / 0.44) [E], about 2-3x the 4 px model/camera error. So "lower marker" is a cue
  only inside the full pose solver, not a stand-alone label. Mount appearance: @35 shows a large ragged black pad;
  @-69 shows a black band across the sphere; @171 shows a thin dark sliver where it meets the wall, consistent with
  the scan's small mount but not clearly different when seen at the silhouette. So mount shape is not a reliable
  single-frame identity cue in this view [V, one frame].
- [V] Automatic sphere size at known positions (same file): predicted diameters at the GT-projected centres are
  35-40 px for beige (Z 0.42-0.48 m) and 30-36 px for blue (Z 0.47-0.57 m). The crops fit the drawn outlines, so the
  stage B by-eye 28-34 px slightly under-read the size (the grey sphere edge fades into the grey floor) [V].
- [V] Gap 2, base inscription in the mono cams (`b2/camb12.py`, `b2/base_snr.py`, `b2/base_snr.json`,
  `b2/e12_f180_base_abc.png` top: crops with the measured base ellipse (red, inner 70 %) and a plain-wall box (green);
  bottom: 0.7-3 mm band-pass; `b2/e12_f180_base_bc_z4.png` cam b | cam c x4). Public ep 12 frame 180, blue cup
  inverted in the rack. Base width: cam a 152 px (2.2 px/mm), cam b 74 px, cam c 72 px (~1.05 px/mm). Band-pass rms in
  the base vs the plain wall: cam a 4.4 vs 2.0 grey levels (x2.2), cam b 2.9 vs 1.6 (x1.8), cam c 4.0 vs 1.3 (x3.1).
  The wall box includes the spin-invariant moulded ring, so the wall reference is a slight overestimate. By eye on the
  band-pass maps, the same marks (rounded-rectangle mark top-left, ring cluster lower-right) show in all three cams.
  They are crisp in cam a and faint but placeable in cam b and cam c, where they are ~4-6 px marks on a ~70 px base.
  So the inscription is a usable coarse spin template in the mono pair too, at roughly half the cam a resolution
  (stage B table: ~2.3 deg/px at r 20 mm). Cam c, which stage B did not view, matches cam b [V, one frame].
- [V] Gap 3, automatic sphere contrast at the GT-projected centres (`b2/sphere_contrast.py`,
  `b2/sphere_contrast_ep11_f0.json`; public ep 11 f0 cam a; inner disc 0.6 R vs annulus 1.25-1.7 R, Lab delta E76
  median / 25th percentile; share of the R circle with radial gradient < 20):
  blue @-28 front rim on the blue wall 55 / 32, 0.39; blue @-139 front base 48 / 47, 0.44; **blue @110 left
  silhouette against the floor 18 / 8, 0.47**; blue @47 is on the far side (hidden) 3 / 2, 0.78.
  beige @35 front on the beige wall 20 / 17, 0.39; beige @171 right silhouette 28 / 14, 0.49; **beige @-69 behind the
  far rim 17 / 5, 0.64**. So the grey sphere is strong against the blue wall (dE ~50), only moderate against the beige
  wall (dE ~20, a grey-on-beige contrast), and weakest at silhouettes and behind the rim, where part of the surround
  is the same grey floor (25th percentile dE 5-8). The two lowest rows are exactly the spheres the stage C
  hand-made detectors missed or found only at loose thresholds, so these numbers explain the silhouette recall gap.
  Beige is the harder cup for detection on contrast as well as on layout [V, one frame].
- [V] Gap 3b, cam b at known positions (`b2/camb_proj.py`, `b2/camb_proj_cands.{json,png}`, `b2/camb_Eraw_markers.png`).
  The ep 11 f0 cam a camera (GT-marker PnP, analysis only) was carried to ego_cam_b with the factory extrinsics, under
  12 conventions (stored transform or its inverse, with or without the a/c pair transform, with or without
  diag(-1,-1,1) conjugation for the 180 deg release rotation). **Only the ego_cam_a `extrinsics_to_stereo_left`
  matrix applied as stored (X_b = R X_a + t, t_x = -0.0374 m; no flip; cam b K and distortion as given)** puts all
  six visible markers on the cam b spheres, within ~2-3 px by eye at x5. The inverse of that matrix with the flip
  conjugation gives the same result (within 1 px). The flipped or sign-swapped variants land ~100 px off. The
  occluded blue @47 base marker projects onto the cup wall, as it should. So in the released upright streams, the
  stored a-to-"stereo left" matrix maps cam a to cam b. That is useful for stereo marker triangulation [V, one static
  frame; time sync between streams not tested].
- [V] Cam b sphere sizes at those positions: predicted 15-20 px diameter (Z 0.42-0.56 m), and the crops fill the
  drawn outlines. The stage B by-eye 12-14 px under-read cam b as well. Corrected pixel budget at Z 0.42-0.50 m:
  cam a 35-40 px, cam b 17-20 px (pixel_table values hold, since they used Z directly).
- [V] Grey-level sphere contrast, cam a vs cam b (`b2/camb_contrast.py`, `b2/camb_contrast_ep11_f0.json`; |annulus -
  inner disc| median / 25th percentile, weak-edge share): blue @-28 18/10 vs 29/18; blue @-139 71/44 vs 38/17;
  **blue @110 silhouette 17/9 vs 14/4 (weak edge 0.47 vs 0.67)**; beige @35 27/18 vs 20/13; beige @171 silhouette
  63/35 vs 77/54 (weak 0.49 vs 0.10); **beige @-69 behind the rim 30/11 vs 10/3 (weak 0.64 vs 0.62)**. So cam b does
  not rescue the two hard spheres here. The far-rim beige sphere is the weakest in cam b (~9 px radius, 2-3 px
  projection uncertainty, so the numbers are indicative). The beige silhouette sphere is stronger in mono than in
  colour. Mono does not uniformly lose contrast against colour; it depends on the background [V, one frame].
- Stage B re-run conclusion (2026-10-06). The 2026-10-05 stage B findings stand. Additions:
  (1) [V] The beige "@171 lower / no mount" cue does not work as a stand-alone single-marker label in video. The image
  rim gap follows the viewpoint, and the 6-8 mm height difference is ~10 px at 55 deg elevation, a weak term for the
  pose solver only. The beige near-3-fold therefore still needs >= 3 markers or temporal evidence.
  (2) [V] The base inscription is resolvable, though faint, in both mono cams (~1.05 px/mm, marks 4-6 px), so it can
  be matched in cam b/c too.
  (3) [V] Measured at GT-projected centres, spheres are 35-40 px (cam a) and 17-20 px (cam b) at Z 0.42-0.50 m, larger
  than the by-eye stage B reading. Silhouette and behind-rim spheres have low contrast (25th-percentile dE 5-8 in
  colour), which explains the detector misses. Cam b does not fix the far-rim beige sphere.
  (4) [V] The ego_cam_a stored extrinsic maps cam a to cam b in the released streams, so markers can be triangulated
  across a/b without a convention search.
  No downloads, no jobs running. No eval labels were made; only public frames were measured.

## Stage C re-run (2026-10-06; workflow "try again")

- Stage C was complete on 2026-10-05 (design, MC v3, real ep 11 f0, render-and-compare, literature, verifier). This pass
  (1) folds the verifier corrections and the stage B re-run into the top sections, and (2) tests one new idea the
  stage B re-run opened: **a/b stereo marker triangulation, where the 3D distance between two markers (a rigid
  invariant) names the beige marker pair without any centre prior**. Outputs in `work/12/c2/`. Public frames only.
- [V] Rigid pair distances of the scan constellations (`c2/pairs.py`, `c2/pairs.json`). Beige: 97.9 mm (@35-@171,
  136 deg apart), 91.7 (@171-@-69, 120 deg), 84.4 (@-69-@35, 104 deg); nearest-other-pair margin 6.2-7.3 mm. So a
  pair of beige markers whose 3D distance is known to about +-3 mm names its two markers with no centre or spin prior
  (order then follows from the up axis). Blue: 89.6-163.1 mm, but two pairs differ by only 2.0 mm (146.3 vs 144.3),
  so the blue chord test is weaker there; lid margins 9-18 mm; pot and pitcher have many near-equal pairs (0.3-2 mm).
- [V] Calibration: the ego a-to-b baseline is only **37.4 mm** (t = (-0.0374, 0, -0.0002) m, 1.6 deg rotation); the
  ego b/c pair is 75 mm. Cam a sits between b and c.
- [V] **a/b stereo chord test, public ep 11 f0** (`c2/stereo_chord.py`, `c2/stereo_chord_ep11_f0.json`). Input: the six
  automatic cam a blobs (verifier dump; 3 blue true, beige 2 true + 1 false). Cam b match by NCC of the rescaled cam a
  patch along the epipolar curve, then a +-2 px 2D refinement. No GT in matching or triangulation; GT-projected cam b
  points (stage B re-run) only score it. All six matches land on the right sphere (1.4-5.1 px from the GT projection;
  NCC 0.82-0.94, but 0.53 for the beige silhouette sphere). The refinement moved 4 of 6 matches by 2.0-2.8 px off the
  epipolar curve: a residual extrinsic or a/b sync offset of ~2 px [H]. Triangulated depth vs GT (cam b Z): blue
  0.462/0.464, **0.530/0.498 (+32 mm)**, 0.470/0.463; beige 0.437/0.418 (+19 mm), 0.452/0.439 (+13 mm); the false
  blob triangulates to 0.57 m, off the cup. Chords: beige true pair 101.3 mm (epipolar-only 109.1) vs 97.9 true and
  91.7 for the -131 branch; blue 101.7 vs 99.5 (good) but 170.2 vs 146.3 and 180.9 vs 163.1 (the 0.53 m blob).
  => With a 37 mm baseline, depth is ~12 mm per cam b pixel at 0.5 m, so 1-3 px of matching/sync error gives 13-32 mm
  depth error. The chord test leans the right way for beige here (3.4 vs 9.6 mm away) but is not reliable. **a/b stereo
  does not resolve the beige near-3-fold on its own.** It does reject false blobs by depth (0.57 m vs 0.42-0.46 m).
- [E] **How well must the body pose be known for two markers to name the branch?** (`c2/branch_margin.py`, logs
  `c2/bm_*.log`, `c2/branch_margin_*.json`; synthetic, deterministic; upright cup, cam a, D 0.45/0.60 m, el 30/45/60,
  az every 10 deg, markers visible within 95 deg of their outward normal; every visible true pair vs every wrong ordered
  assignment, fitted with free spin and a centre shift bounded per axis by s; residual = wrong-branch RMS in px).
  | centre bound s (per axis) | 0 | 1 mm | 2 mm | 3 mm | 5 mm | 8 mm |
  |---|---|---|---|---|---|---|
  | beige, tilt fixed: p10 px / share < 6 px | 9.2 / 0.00 | 6.9 / 0.05 | 4.5 / 0.22 | 2.6 / 0.38 | 1.2 / 0.54 | 0.0 / 0.67 |
  | beige, tilt +-1 deg free | 6.4 / 0.08 | 4.0 / 0.27 | 1.9 / 0.46 | 0.7 / 0.54 | 0.0 / 0.68 | 0.0 / 0.76 |
  | blue, tilt fixed | 18.4 / 0.00 | 17.5 / 0.01 | 15.9 / 0.01 | 13.8 / 0.04 | 10.8 / 0.07 | 6.0 / 0.10 |
  A wrong beige fit becomes exact with a shift of ~5.5 mm along the ray plus ~5.4 mm lateral (spin 104-138 deg), so
  depth and lateral position both matter. Reading: with 1.5 px detection noise plus 2-4 px real model error, a branch
  separation below ~6 px cannot be trusted. **Two beige markers decide the branch only if the cup centre is known to
  ~1 mm per axis and the tilt to well under 1 deg** (still ~5 % of views marginal). At 2 mm, 22-46 % of beige views are
  marginal. Blue two-marker decisions stay safe up to ~3-5 mm (p10 >= 11 px), matching the real frame (blue 0/40 flips).
  This explains why the real-frame "tight" prior (2 mm per axis, 1 deg, drawn around GT) still flipped beige 25/40.
  Design consequence: for beige, do not count on a body-pose prior. Get the third marker (silhouette recall) or
  temporal evidence. A mm-level centre would need the rim ellipse + table plane + b/c stereo together; that is not
  shown here [H].
- [V] Public data per object (parquet object lists): blue_cup in eps 11, 12, 13, 21, 22 (137-190 frames each);
  **beige_cup only in ep 11 (137 frames)**; white_pot_lid eps 0, 2; white_pot eps 0, 2, 26, 27, 41-45; water_pitcher eps
  21, 22. So a beige-specific layout refinement (bundle adjustment of its 3 markers) or beige-specific validation has a
  single public episode. A sphere detector can still train on every object's spheres (same physical sphere type), but
  the beige flip rate can be measured on one public episode only; no fresh beige holdout exists in public data.
- [lit] OptiTrack Motive docs, "Rigid Body Tracking" (docs.optitrack.com/motive/rigid-body-tracking, fetched
  2026-10-06): at least 3 markers define a rigid body, 4-12 are recommended; avoid squares and isosceles or equilateral
  triangles, because symmetric sets "may cause the Rigid Body assets to flip"; distinct inter-marker distances
  identify an asset. The beige cup uses the minimum of 3 markers in a near-equilateral triangle (chords 84/92/98 mm,
  spacings 104/119/136 deg). That is acceptable for the 3D mocap system, which measures sub-mm 3D distances, but it is
  the worst case for monocular video, where depth is not observed. The blue cup's 4 irregular markers follow the
  vendor rule. This is the vendor-documented form of our beige near-3-fold. It confirms that a solver which uses only
  inter-marker geometry needs >= 3 markers or accurate depth.
- [E] Does camera motion over the static prefix help when the same two beige markers stay the only ones seen?
  (`c2/branch_margin2.py`, `c2/bm2_beige_daz{6,12,24}.log`; two views, relative camera motion assumed known from
  ego-motion, one shared centre shift and spin for the wrong branch, tilt fixed). Wrong-branch p10 px / share of
  view-pairs < 6 px, single view vs azimuth change 6 / 12 / 24 deg: at a 5 mm centre bound 1.2 / 0.54 -> 1.9 / 0.52,
  2.9 / 0.47, 4.9 / 0.23; at 8 mm 0.0 / 0.67 -> 1.6 / 0.67, 2.8 / 0.59, 4.9 / 0.26. So parallax on the same pair helps
  only for large motion (~24 deg, about 0.2 m of head translation at 0.45-0.5 m), which a static prefix rarely gives.
  Temporal fusion helps beige mainly when **another marker** comes into view (MC: 3 detected -> 0.03 flips), not
  through parallax. For eval 8 that points to the frame-0 view, where all three markers are in view (stage B).
- [V, one frame] **Top-down check of the predicted third marker** (`c2/topdown.py`, `c2/topdown2.py`,
  `c2/topdown*_ep11_f0.{json,png}`). On public ep 11 f0, the true branch and the -131 branch both fit the two detected
  beige blobs (verifier `v_c3_branch.py`: 2.9/3.5 px vs 2.1/2.5 px). They predict the undetected third marker at
  (1277, 888) and (1325, 871), 50 px apart. Rather than wait for bottom-up recall, each branch is scored by asking
  whether a sphere is present where it predicts one. Scores are percentiles against 150 random points in the cup and
  floor region. Circular-edge completeness at the expected 18.5 px radius, best within 6 px: true 0.80 (83rd pct) vs
  -131 0.53 (47th). Black-mount pixels (V < 0.2) inside the disk: true 0.017 (93rd pct; background median 0) vs -131
  0.000. DoG and fine texture do not separate them. The crop (`c2/topdown_ep11_f0.png`) makes it plain to the eye: a
  half-hidden sphere with its black band behind the rim at the true prediction, and bare speckled floor at the -131
  prediction. The +120 branch also predicts a marker near the true sphere (10 px away), but it fits the two blobs at
  14-16 px, so it is already excluded. => **Hypothesis-driven verification** (is there a sphere/mount where this branch
  predicts a visible marker?) separates the beige branches on the frame where bottom-up detection failed. That is
  much easier than full silhouette recall: two candidate locations against one patch classifier. The hand-made
  margins are modest (83rd vs 47th pct), so a learned patch verifier trained on public GT-projected crops is still
  needed [H]. One frame only.
- Stage C re-run closed (2026-10-06). The top sections were rewritten with the verifier corrections, the stage B
  re-run and this pass (pre-rewrite copy: `work/12/c2/notes12_before_rewrite2.md`). Artifacts are in `work/12/c2/`:
  - `pairs.py`, `pairs.json`
  - `stereo_chord.py`, `stereo_chord_ep11_f0.json`
  - `branch_margin.py`, `branch_margin2.py`, `bm*.log`, `branch_margin*.json`
  - `topdown.py`, `topdown2.py`, `topdown*_ep11_f0.{json,png}`
  No downloads and no running jobs. Only public frames were measured, and no eval labels were made.

## Skeptical verification, round 2 (verifier, 2026-10-06; claims C1-C4 of the re-run; scripts in `work/12-verify/r2/`)

- Started. Plan: C1 re-run symm2/symm3 numbers (beige texture share not re-run before); C2 pair distances and
  real_ep11 comb/add3 re-run; C3 re-run branch_margin.py (beige, beige tilt, blue) and audit its assumptions;
  C4 re-run topdown*.py, then test the GT-fitted-camera circularity (the 6-pt camera includes the by-eye pixel of
  the very sphere the true branch is checked against).
- [V] C2 layout, independent marker finder (`r2/c2_layout.py`: own sampling, up axis from GT ep 11 f0, wall-circle
  axis point, clusters standing > 6 mm proud of the wall, robust sphere fit on bright points). Beige angles 105.1 /
  135.7 / 119.2 deg and heights 71.4 / 68.8 / 62.7 mm reproduce stage A. But the @171 sphere comes out **1.75 mm**
  from the stage-A centre (r 54.0 vs 52 mm; my fitted sphere radius 7.23 mm vs stage A's 8.30 mm, while the other two
  markers fit 7.25-7.39 mm in both). Chords become 84.8 / 93.2 / 99.6 mm (stage A 84.4 / 91.7 / 97.9), margins 8.4 /
  6.4 mm. With my centres the 6-pt ep 11 f0 PnP residual drops 4.07 -> 3.52 px, and the @171 point 2.8 -> 1.2 px
  (`r2/c2_pnp171.py`). So the stage-A beige model likely carries a ~1.75 mm error on @171, one of the two markers
  detected on ep 11 f0. Near-equilateral conclusion unchanged; the quoted chords are ~0.5-1.7 mm low.
- [V] C1 stored curves (`out/symm2_*`, `out/symm3_*`): marker-free worst-spin mean NN 0.76 (blue) / 0.74 (beige) mm,
  0.21 / 0.22 at 0 deg, as claimed. Texture shares of spin-specific energy in marker neighbourhoods (16 mm radius,
  sphere + mount + wall) are **0.65 blue and 0.45 beige**; the quoted "45-76 %" range includes the pitcher (0.76),
  not a cup. Marker-free correlation curves are not just "smooth one-sided shading": blue drops 0.95 -> 0.42 by
  15 deg and ~0 by 40 deg, with no broad lobe (fine, non-repeating detail); beige drops to 0.52 by 20 deg, then a
  broad one-sided lobe (-0.42 at 180). The non-marker detail is 35 % (blue) / 55 % (beige) of the spin-specific
  energy. That it is not physical rests on [H] (baked lighting, specular streaks, ringing) and on the video crops.
- [V] C1 video: `b/c11a_f0.png` shows plain cup walls (no print, seam or wear) on both cups; markers on black mounts.
- [V] C3 re-run of `c2/branch_margin.py` (copy `r2/branch_margin_r2.py`, outputs redirected): beige tilt fixed and
  blue reproduce every quoted number exactly (beige < 6 px share 0 / .05 / .22 / .38 / .54 / .67 at 0-8 mm; wrong fit
  at 8 mm: |d_ray| 5.5, |d_lat| 5.4 mm; blue p10 18.4 ... 13.8 (3 mm), 10.8 (5 mm), share < 6 px .04 / .07).
  "Blue >= 11 px at p10" is 10.8 px at 5 mm (rounding).
- [V] Re-runs reproduce exactly: `branch_margin.py beige_cup tilt` (.08 / .27 / .46 / .54 / .68 / .76 at 0-8 mm);
  `symm3.py beige_cup` (share 0.45, rms 0.0372 / 0.0283); `real_ep11.py 0 comb` (blue 0/40 x4; beige 28/25/22/21)
  and `0 comb add3` (beige medians 0.85 / 0.91 / 0.86 / 0.99 deg, flips 0/0/0/1). Note add3 adds a by-eye pixel
  (1276,888) that is also one of the 6 PnP points defining the camera, so 0.85-0.99 deg is agreement, not accuracy.
- [E] C3 independent re-implementation (`r2/c3_margin_indep.py`: own camera looking at the marker-height axis point,
  own projection, 3 spin starts per wrong assignment; same grid, 95 deg cone, < 6 px rule). Stage-A markers, 3D box:
  share < 6 px .13 / .33 / .59 / .64 / .68 / .75 at s = 0/1/2/3/5/8 mm (original .00 / .05 / .22 / .38 / .54 / .67).
  Height fixed by the table plane (xy shift only): .13 / .24 / .40 / .54 / .59 / .60. Verifier-refit markers (@171
  moved 1.75 mm): box .10 / .23 / .44 / .58 / .62 / .69; plane .10 / .17 / .26 / .35 / .50 / .51. So the direction
  holds (beige two-marker decisions are fragile, much worse than blue), but the shares at small s are
  implementation-sensitive by 2-3x; "1 mm is enough (5 % marginal)" is not robust: my version gives 23-33 % at 1 mm
  and 10-13 % even at 0 mm. Diagnosing the gap next (spin start / look-at point).
- [V] C2 sensitivity to the @171 centre (`r2/real_ep11_r2.py 0 comb fix171`: verifier-refit beige centres in both the
  6-pt camera, now 3.52 px, and the solver): two beige blobs give **17 / 8 / 23 / 13 of 40 flips** (base / tight /
  base_wm0 / tight_wm0) instead of 28 / 25 / 22 / 21. With add3: 0 / 0 / 1 / 0, medians 0.52-0.72 deg. So two
  markers stay ambiguous, but the "21-28/40" count is partly a product of the stage-A @171 error; it is model-dependent.
- [V] C4 re-run of `c2/topdown.py` / `topdown2.py` (copies in r2): identical (circ 0.804 / 83rd pct vs 0.527 / 47th;
  dark 0.017 / 93rd vs 0.000; background circ p50 / p90 0.54 / 0.89).
- [V] C4 circularity test (`r2/c4_noncirc.py`): the 6-pt camera includes the by-eye pixel (1273,888) of the sphere
  that the true branch is then checked against. A 5-pt camera without it (3.41 px) gives the same predictions,
  true (1277,888) 3.8 px from the by-eye sphere and -131 (1325,871). With the beige pose perturbed (centre N(0, 2-5
  mm) per axis, tilt N(0, 1 deg), 30 draws each, both branches re-fitted to the two blobs) the true prediction stays
  3.8-8.3 px from the sphere; circ true > wrong in 97-100 % of draws, dark true > wrong in 100 %. Meanwhile the -131
  branch fits the two blobs better than the truth in 87-100 % of draws (median 1.9-3.2 vs 2.7-4.3 px). So C4's
  separation is not an artefact of the GT-fitted camera on this frame. Still one frame and hand-made cues; the true
  sphere's edge score sits below the background p90 (0.80 vs 0.89).
- [V] **C3 modelling error found.** `branch_margin.py` (and `mc_spin.py`/`real_ep11.py`, same gauge) spins the
  markers about the gauge origin c0 = mean of scan surface samples, which is **2.8 mm off the beige revolution axis**
  (1.8 mm for blue). A spin branch is a rotation about the body's own axis (the body tracker fixes the axis, not the
  marker-weighted centroid). Rotating about c0 gives each ~120-131 deg wrong branch a built-in 4.8-5.1 mm offset that
  the bounded shift must absorb, so the wrong branch looks worse than it is at small s. My re-implementation with
  `OFFAXIS=both` (spin about c0, camera at c0) reproduces the original (.00 / .04 / .23 / .38 / .56 / .67); spin
  about c0 but camera at the axis gives .00 / .09 / .27 / .48 / .65 / .71; the start count does not matter (`SINGLE`).
  **Spin about the true axis: beige < 6 px share .13 / .33 / .59 / .64 / .68 / .75 at 0 / 1 / 2 / 3 / 5 / 8 mm**
  (box; table-plane height known: .13 / .24 / .40 / .54 / .59 / .60). So "two beige markers decide with a ~1 mm
  centre (5 % marginal)" is refuted: even an exact centre leaves 13 % of view-pairs marginal, 1 mm leaves 24-33 %.
  Running: real_ep11 with the gauge origin moved onto the axis (`axisc0`), and blue with the axis spin.
- [V] Real frame with the solver's gauge origin moved onto the revolution axis (`real_ep11_r2.py 0 comb axisc0`; moves
  beige 2.84 mm, blue 1.82 mm): beige two-blob flips 23 / 20 / 26 / 15 of 40 (was 28 / 25 / 22 / 21); blue unchanged
  0/40. So the gauge offset does not systematically favour either branch on this frame. Across the variants tried
  (gauge, @171 centre) beige two-blob flips range 8-28 of 40: always ambiguous, count model-dependent.
- [V] Both corrections together (`comb fix171 axisc0`): beige two-blob flips 20 / 8 / 19 / 9 of 40, medians of the
  non-flipped draws ~0.9-1.7 deg. Range over all variants: 8-28 of 40.
- [E] Blue with spin about the true axis (`r2/c3_margin_indep_obj.py`, OBJ=blue_cup): p10 17.6 / 16.3 / 14.9 / 12.9 /
  8.9 / 4.5 px and share < 6 px .00 / .02 / .04 / .05 / .09 / .13 at 0 / 1 / 2 / 3 / 5 / 8 mm (original p10 18.4 ...
  13.8 / 10.8 / 6.0; share .04 / .07 / .10 at 3 / 5 / 8). Blue stays far safer than beige; "safe to 3 mm" holds,
  "to 5 mm with p10 >= 11 px" becomes 8.9 px and 9 % marginal.
- [E] C3 "a wrong fit becomes exact with ~5.5 mm along the ray + ~5.4 mm lateral" reproduces, but it is the median
  over only the view-pairs whose wrong fit reaches < 1 px inside the 8 mm box (~40 % of them). Unbounded exact
  fits (`r2/c3_exact_shift.py`, spin about the axis) need |shift| median 24.7 mm (p10 6.5 mm), mostly along the ray
  (median 20 mm; lateral 5 mm). Near-exact (few-px) wrong fits with small shifts are what make beige ambiguous.
- [V] `comb add3 axisc0`: beige 0 / 0 / 1 / 0 of 40, medians 0.85-1.00 deg (unchanged).
- Round-2 verdicts. **C1 holds with fixes**: cup marker shares are 0.45 / 0.65 (not 45-76 %), and the non-marker scan
  texture has fine, non-repeating detail (35-55 % of spin-specific energy) whose non-physical origin is [H]; the
  video shows plain walls. **C2 holds with fixes**: layout and two-marker ambiguity confirmed. The stage-A @171 centre
  is likely 1.75 mm off (chords 84.8 / 93.2 / 99.6 mm). The flip count is model-dependent (8-28/40), and add3 is
  agreement inside a camera fitted to the same by-eye pixel. The missed sphere is @-69 behind the far rim; the
  silhouette sphere @171 was detected. **C3 refuted quantitatively**: the margin script spins about a point 2.8 mm
  off the axis. With spin about the axis, even an exact centre leaves 13 % of beige view-pairs < 6 px, 1 mm 24-33 %,
  2 mm 40-59 %, 5 mm 59-68 %. The direction holds (beige two-marker decisions unreliable, blue safe to ~3 mm).
  **C4 holds** on this frame: it is not an artefact of the GT-fitted camera, and it is robust to 2-5 mm / 1 deg pose
  noise. It is still one frame with modest hand-made margins. No jobs left running (all r2 runs finished).
