# 12 — Spin observability of near-symmetric objects (cups, lid, pot, pitcher)

Status: complete (stages A, B, C), 2026-10-05. Agent 12. Work dir `/Users/aebatirel/Documents/Code/v2d-research/work/12/`
(stage C in `work/12/c/`). Tags: [V] verified here, [E] estimate or simulation, [H] hypothesis, [lit] read in the source.
Research and analysis only. Public GT was used only for analysis and scoring. Eval videos were viewed for method design
only; no labels were recorded or used. No SlamDunk code was read.

## Answer

Spin about the rest-up axis **is observable from appearance for all five objects, but for the two cups only through
the mocap marker spheres** (plus a base inscription when the base faces the camera). Geometry alone fixes white_pot
(handle) and water_pitcher (spout and handle). The lid is 2-fold by geometry, and its top markers break the tie. The
scorer uses plain ADD with one slot-0 frame-0 alignment, so the anchor spin must be within about 5 deg (note 11 B2:
AUC >= 0.9 needs <= ~5 deg; MP-SR needs <= ~5-8 deg). With markers, that accuracy is reachable: on a real public frame
the marker solver gives 0.35-1.0 deg once the marker identities are right. The real risk is **identity flips**,
mostly the beige cup's near-3-fold marker layout (a wrong pick is a ~120 deg spin). Avoiding them needs a detector that
also finds the spheres at the silhouette.

| object | spin cue | single-frame accuracy, cam a (MC v3, base / tight prior) | flips > 30 deg | real frame (public ep 11 f0) | eval exposure |
|---|---|---|---|---|---|
| white_pot | handle geometry + 7 markers | 0.24 / 0.21 deg median | 0.01 / 0.00 | not run | anchor eps 1, 3, 5, 6 |
| blue_cup | 4 markers (2 rim, 2 base); base inscription when inverted | 1.8 / 1.0 deg | 0.08 / 0.05 | **0.35-0.5 deg, 0/40 flips** (2 true + 1 false blob) | anchor eps 10, 14, 20, 32, 33 |
| beige_cup | 3 rim markers, near-3-fold (104/136/119 deg); inscription | 1.0 / 0.7 deg | **0.20 / 0.09** | 2 markers found: **22-31/40 flips**; all 3: 0/40, 0.85-0.99 deg | anchor ep 8; slot 1 ep 10 |
| white_pot_lid | 2-fold bar handle + 4-5 top markers (two sizes) | 0.6 / 0.5 deg | 0.07 / 0.03 | not run | slot 1 ep 1 |
| water_pitcher | spout + arch handle (+4 markers) | marker-only 1.5 / 0.8 deg (geometry not used) | 0.09 / 0.06 (marker-only) | not run | ep 20 (non-anchor) |

Fusing 5 views (multi5) brings flips to 0.00-0.02 for every object (optimistic: views drawn independently). Cam b gives
the same flip rates with 1.2-2x larger medians. Base prior = centre 5 mm, tilt 2 deg; tight = 2 mm, 1 deg (rim, stereo
and table cues). Full table in the stage C log (MC v3).

## Automatic spin-resolution design (stage C)

1. **Body pose, spin left free.** A tracker plus the rim ellipse, stereo and the table plane give the centre (target
   <= 2 mm) and the tilt (<= 1 deg, stable-pose snap from note 11). The spin is left as a free parameter. FoundationPose's
   own spin choice for the cups is not trusted (see the literature notes) [H].
2. **Learned marker-sphere detector** [H, required]. The hand-made detectors failed on silhouette spheres seen against
   the grey floor [V]: the colour detector found 3 of 6 spheres with 0 false blobs, and Hough plus a score ranked the hits
   2, 4, 5 and 10 of 103 candidates. Train a small heatmap network on public frames. Get labels automatically: solve each
   frame's camera by PnP on the GT-placed scan markers of all objects (`pnp_check.py` gives 4.1 px), then project every
   marker with z-buffer visibility, counting silhouette spheres as visible when >= 25 % of the disk is free. Run it on
   cam a, and on cam b/c in frames where cam a is motion-blurred (cam b stayed sharp in ep 11 frame 30 [V, one frame]).
3. **Identity and spin solver** (`c/mc_spin.py: solve`) [V on synthetic and real data]. Scan the spin in 2 deg steps with
   a gated robust cost and a visibility-aware missing-marker term (z-buffer of the scan at sub-2 resolution). Refine the
   best 6 minima jointly (spin, centre, tilt), re-matching blobs to markers each round. **Return a multi-modal spin
   likelihood, not only the argmin.** The marker layout comes from the scan spheres; public GT validates it (scan markers
   land on the image spheres within 4 px, spin within ~2 deg, ep 11). Refining the 3D marker positions by bundle
   adjustment over public frames with GT poses is optional [H].
4. **Temporal fusion.** Sum the branch likelihoods over the anchor's static prefix (13-117 frames, median 39 per note 02;
   spin constant there). Carry later evidence (frames that show more markers, the base inscription when the cup is
   inverted or tipped) back to frame 0 through the tracked relative rotation in the batch smoother [H].
5. **Base-inscription matcher** for upside-down or tipped cups (eval 14 last ~40 %, eval 8 pours). The scan base template
   is unique inside r < 25 mm (peak half-width 2-6 deg, lookalikes <= 0.37) [V]. The rim ring must be masked. Matching
   on video was not run [E].
6. **Render-and-compare only as a weak tie-breaker.** A splat render of the textured scan picked the correct beige
   branch on whole-cup gradient NCC by only 0.016, and the wrong one on the marker regions [V]. Silhouette and rim do
   not change between branches, and scan colours and lighting differ from the video.
7. **Fallback priors (note 11)** when the branch margin is small: eval 14 cup-vs-rack relative yaw (LOO 1.9-2.7 deg);
   eval 20 pitcher-vs-cup (6-8 deg, too loose for MP-SR); eval 10 is insensitive (stacked cups on the anchor axis).
   Eval 8, 32 and 33 have no prior, so vision must decide; report the uncertainty there.
8. **Per-episode diagnostics (automatic):** markers detected per frame, branch margin, and whether the fallback fired.
   No hand labels.

## Achievable yaw accuracy [E]

- Precision is not the limit. One marker centred to 1 px fixes spin to 0.4-0.7 deg in cam a (stage B pixel budget). The
  solver reached 0.35-1.0 deg on a real frame once identities were right [V], and 0.2-1.8 deg median in simulation.
- The expected error is set by the flip rate. For blue-cup anchors (5 eval episodes): about 5-8 % per frame from a
  single frame, ~0 % with static-prefix fusion if the detector reaches ~90 % recall [E, MC]. For the beige anchor (eval
  8): 9-20 % single-frame, 2 % fused; but it rises to ~50-75 % whenever only the two front markers are found (real
  frame) [V]. At eval 8 frame 0 all three beige markers are in view (stage B), so silhouette recall decides that episode.
- The white_pot anchors (eval 1, 3, 5, 6) are safe: <= 0.5 deg and ~0 % flips from markers alone, with the handle as a
  second cue.
- Budget translation (note 11): a 1-2 deg median error costs little (AUC >= 0.95 [E]); a 120 deg flip costs about
  AUC 0.2, SP-SR 0, MP-SR 0 for that episode (note 02: 90/180 deg spin gives 0.195/0.165).

## Literature (brief)

- [lit] BOP 2020 (Hodan et al., arXiv 2009.07378, Sec. 2.3): an object's symmetry set is every transform whose
  Hausdorff distance is below max(15 mm, 0.1 d), so that tiny details do not break symmetries, minus those the
  organisers judge resolvable by texture. MSSD/MSPD/VSD are symmetry-aware. By that rule our cups (marker sets 13 mm
  from another spin) and the lid count as symmetric, so BOP-tuned methods are neither trained nor scored to resolve
  this spin. Our scorer is plain ADD.
- [lit] FoundationPose (Wen et al., CVPR 2024, arXiv 2312.08344): 42 icosphere views x 12 in-plane rotations = 504
  hypotheses, refined and ranked by render-and-compare on 160x160 crops. It has no symmetry handling. Its stated
  failure case is texture-less objects with occlusion and few edges giving a wrong orientation. At 160 px a 30 px
  marker shrinks to ~15 px and the branch differences to ~5-10 px [E], so marker-aware ranking is not guaranteed.
- [lit] EPOS (Hodan et al., CVPR 2020, arXiv 2004.00605) uses surface fragments with many-to-many correspondences.
  SurfEmb (Haugaard & Buch, CVPR 2022, arXiv 2111.13489) learns multi-modal correspondence distributions without
  symmetry labels. [lit-m, not re-fetched] Manhardt et al. ICCV 2019 (multiple hypotheses), Implicit-PDF (ICML 2021),
  SpyroPose (2023), MegaPose and CosyPose (symmetry-aware losses). The idea we keep: carry a multi-modal spin
  distribution and resolve it with explicit marker evidence and priors. No off-the-shelf method targets near-symmetries
  that only small physical details break.

## Limitations and open issues

- Real-image validation covers a single frame (public ep 11 frame 0), both cups, with an evaluation camera from 6 blobs,
  3 of them located by eye (4.1 px). The pot and lid were not run on real frames. The full-episode real test needs
  per-frame public cameras (next step 1).
- The MC models the object at rest, a known camera, Gaussian pixel noise, and independent misses and false blobs. It
  ignores motion blur, hand-correlated occlusion and the lid's two marker sizes; the pot and pitcher runs use markers
  only (no handle or spout geometry). multi5 is optimistic.
- The base inscription has been verified only in the scan (uniqueness), not matched on video.
- Principal-point convention: the as-given and rotated K fit equally (4.07 vs 4.03 px) at ep 11 frame 0. Still open.

## Next steps

1. Auto-label public frames: per-frame camera by PnP on GT-placed markers of all objects (public eps 0, 11, 12, 13, 21,
   22; cam a, plus cam b where downloaded), z-buffer visibility. Measure the recall of the current detectors per
   background type (wall, floor, hand).
2. Train the sphere heatmap detector; target >= 95 % recall of visible spheres, silhouettes included, at <= 0.5 false
   blobs per object. Re-run `real_ep11.py`-style scoring per frame over whole public episodes: spin error, flip rate,
   latency.
3. Static-prefix fusion and the multi-modal anchor-spin factor in the batch smoother; score with the official scorer on
   public cup-anchor episodes (11, 12, 13, 21, 22), then on fresh holdouts.
4. Base-inscription matcher on public ep 12/13 inverted frames, checked against the marker-derived spin.
5. Identity cues for beige: the @171 deg marker sits ~6-8 mm lower and has no mount; a mount-presence classifier [H].

---

# Appendix: running logs (stages A, B, C; kept as history; later entries supersede earlier ones where marked)

