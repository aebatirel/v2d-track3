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
