[← Index](../README.md) · [Summary](../00-summary.md) · [← 12](12-symmetry-observability.md) · [14 →](14-policy-tracking-error.md)

# 13 — The wooden spoon: appearance, frame-sign rules, reconstruction, roll decision

Status: COMPLETE research note. Stages A, B and C ran on 2026-10-05. Stages B and C were re-run, reproduced and extended on
2026-10-06 (sections at the end), and this summary was rewritten after them. Research only: nothing submitted, no SlamDunk
code read or changed. Agent id 13. Work dir `/Users/aebatirel/Documents/Code/v2d-research/work/13/` (scripts `scripts/`,
outputs `out/`, frames `frames/`, Track 2 geometry `t2/`). Tags: [V] verified, [E] estimate, [H] hypothesis. Sections: final
summary; progress log (chronological, some early items superseded and marked); Stage A (appearance, visibility); Stage B
(sign-rule search on the 10 Track 3 scans); Stage C (scorer facts, tracker accuracy, Track 2 holdout, CD-O and frame
stability, reconstruction choice, decision analysis); Stage B retry; Stage C retry (reproduction, mesh budget, smoothing,
rule sources, A/B value).

## Final summary (read this first; rewritten 2026-10-06)
1. Object [V visual]: one plain pale wooden cooking spoon, ~30 cm (+-7%), shallow oval bowl ~9-10 x 5.2 cm, round ~2 cm
   handle, 3 mocap spheres (M1 bowl-neck side edge, M2 opposite edge ~4 cm further up, M3 handle end). It is in 10 eval
   episodes; slot 0 only in 35-37. It starts flat, concave-up and untouched in 10/10. Delivered videos are already
   upright: do NOT rotate them 180 deg (the calibration flag describes the sensor).
2. Frame convention [V Track 2 holdout, H transfer to Track 3]: origin = area-weighted surface centroid (exact in all 10
   Track 3 and all 29 Track 2 scans); axes = surface PCA; the LARGEST and MIDDLE axes are signed by positive third
   moment, estimated with some noise (effective n ~ 5.6e3 points [1.6e3, 1.8e4]); the smallest axis completes
   right-handed. Track 2 (29 public scans, a fresh holdout) supports it: mid axis 12/14 on unseen non-degenerate scans
   (P = 0.006 under random bits), z 13/16 (P = 0.011), every failure a near-tie; joint LR vs random 4.8e10. Stage B
   found no significant rule on Track 3 alone because half its mid-axis skews are near-ties.
3. Spoon frame [E]: +z bowl -> handle end (P >= 0.9999 given the rule); +y toward M2 (the handle-side side marker),
   +x = y x z out of the CONCAVE face (up when resting concave-up) = "frame B". P(B) ~ 0.80-0.87 overall: 0.85-0.92 under
   the mid-axis rule if the organisers' scan includes the markers (10/10 public scans do), 0.5 if it does not. This
   reverses note 07's "+x to the convex back". Commit to B; do not hedge.
   Stage B retry [V]: over 9,139 parameter-free Track 3-only rules none is significant (null P 0.21-0.28), but every rule
   that is not a coin flip on the real spoon also gives B. No public spoon asset exists (Track 1 has no meshes; Track 2's
   29 scans hold no utensil).
4. Decision [E + V doc]: commit to B and email v2d_challenge@nvidia.com or ask on the Discord for the spoon frame (cheap,
   legitimate, fair to all teams). The kit, the challenge page and the FAQ PDF say nothing on object frames, leaderboard
   probing or final-submission selection. So a two-variant A/B chosen by the board is not forbidden by any text seen, but it
   is a 1-bit probe of confidential reference data, which this project's rules forbid. Costs: one submission per variant (one
   packed file goes to all six Track 3 boards; 5 per week per track, unlimited in the final 3 days), a second set of 10 spoon
   policies (the observation is body-frame: ~20-40 GPU-h, ~5-10 fine-tuned), and two commit and hash provenance chains. Its
   expected value is ~0.08 SP-SR, ~0.01 MP-SR, ~0.5 cm MPPE and ~0.01 AUC. Do it only with the user's decision and organiser
   approval, and then in the final 3 days.
   A wrong bit hurts most in 35-37, where the spoon is slot 0. There the scorer's one rigid warp from slot 0 at frame 0 turns a
   180 deg roll error into a mirrored path: a lifted spoon is placed below the table (note 07: 20.5 cm MPPE on moving hosts).
5. Reconstruction [V model]: CD-O is scale/pose-free (Sim(3) + ICP) and any complete spoon-shaped mesh scores 0.11-0.16 cm
   against a 0.073 cm sampling floor (spoon = 10 of 36 CD-O pairs, so <= 0.03 cm on the board). Frame stability is what
   matters: use ONE automatically fitted parametric template with the markers modelled (origin ~3 mm, tilt ~0.6 deg).
   Never canonicalise a partial fusion: a missing bowl underside flips z in 85% of shapes. Stereo fusion and generative
   completion are measurements or priors for the template fit, not the asset. Generate the template NATIVELY under 4,096
   faces and 4,096 vertices (~3.5k faces is enough). The packer then does not decimate it, and the full-resolution version would
   differ by only 0.0005 cm CD-O and 0.2 mm origin, with the same skew signs [V model]. Canonicalise, simulate and submit that
   one file.
6. Tracking [V model]: the stereo marker triangle gives ~1 deg long-axis tilt but 2.5-6 deg median roll at 0.5 px (b+c),
   1.3-3 deg with the colour camera added, and 10 deg median / 45 deg p90 roll at 2 px blur. Roll is the thin-object weak
   spot. It matters for MPPE and the 30 deg MP-SR gate more than for ADD. Use the calibration file AS GIVEN (left = ego_cam_c;
   colour extrinsic targets ego_cam_b; notes 11 and 15). Its measured 1.2-2.6 px epipolar residual makes the 1-2 px rows the
   realistic ones. A 9-frame quadratic Savitzky-Golay window on the triangulated markers halves roll error. With b+c at 2 px it
   cuts frames over 30 deg from 21% to 6.5%, and with the colour camera added to ~1%. Systematic calibration error, outliers,
   marker swaps and 2-marker phases (15/16 in the cup, fist over M3) are not covered and need the robust gating, silhouette
   and collision mitigations of Stage C.
7. Open items / falsifiers: the organisers' answer; whether their spoon scan includes the markers; the M1/M2 stations and
   handle section from automatic stereo at rest (35-37 f0) on our own fitted mesh, where skew_y must point to M2 with
   |skew_y| >= 0.02; whether Track 3 shares Track 2's sign step; the reference-side `fast_simplification` effect on the thin bowl
   (not reproducible here); and a real tracker test on a public marker-bearing object with GT (e.g. wooden_piece_1/2) to replace
   the iid-noise model.

## Progress log
- 2026-10-05 start: read 10-synthesis, 07-mesh-frame. Downloads of eval colour clips (35,36,37,3,15,5,6,16,32,33),
  ego_cam_b (35,36,37,3,15), ego_cam_c (35,36) started in background (`scripts/dl.sh`, log `out/dl_a.log`).
- 10:50 [V] Delivered ego_cam_a/b videos are ALREADY UPRIGHT (torso at bottom, hands from below; raw frame
  `work/13/frames/cmp_raw35.jpg`). Rotating them 180 deg turns them upside down. calibration.json still carries
  `rotation_deg: 180` for the ego device and swaps stereo left/right (left=ego_cam_c). Whether K's principal point
  is in the delivered (rotated) image frame must be checked by whoever owns P1 -- do NOT blindly rotate frames.
  [SUPERSEDED 2026-10-06: closed by notes 11 and 15; the calibration AS GIVEN describes the stored upright frames, see the
  Stage C retry section.]
- 10:55 [V] The spoon carries 3 retro-reflective mocap markers (grey ~1.3 cm spheres on black bases): one on the
  handle end, one on one side edge at the bowl-neck junction, one on the OPPOSITE side edge ~1/3 along the handle
  (crops `frames/crop36_f0.png`, `crop37_f0.png`).
- 10:58 [V] The public scans INCLUDE the mocap markers (wooden_piece_1: 4 marker spheres on its +x face; render
  `render/wooden_piece_1_+x_-x_+y.jpg`). So the organisers' spoon scan very likely includes its 3 markers, which
  break the spoon's mirror symmetry -> the frame sign bits are set by marker placement, which is visible in video.
- 11:10 [V] Marker spheres in all public scans fitted at r = 6.6-7.7 mm (median ~7.2 mm, i.e. 14.4 mm markers);
  captured sphere area 2-6 cm2 each (`out/markers.log`). wooden_piece_1 has 4 markers on its +x face (skew_x +0.98);
  wooden_piece_2 has 3 markers on its -x face (skew_x -0.54): the published x does NOT follow the markers.
- 11:15 [V] Spoon marker layout from video (held views ep35 f72/f108, ep36 f238/f272 `frames/held35.jpg`,
  `held36.jpg`): M1 on one side edge at the bowl-neck junction, protruding laterally in the spoon plane; M2 on the
  opposite side edge ~5 cm further toward the handle; M3 on the handle end face, along the long axis.
  Chirality [V from ep36/37 rest frames, bowl concave-up]: with z = bowl->handle and x = toward the CONVEX back of
  the bowl, y = z cross x points to M1's side (the near-bowl marker).
- 11:40 [V model] Parametric spoon + 3 markers (`scripts/spoon_model.py`, `spoon_decomp*.py`, MC `spoon_mc.py`,
  600 samples, logs `out/spoon_mc_*.log`): skew_z > 0 bowl->handle in 600/600 (min +0.20); skew_y measured along
  the M1 side is NEGATIVE in 92% (mean -0.034, sd 0.027) -- driven by the two side markers sitting at different
  z (they tilt the y axis ~0.1-0.2 deg toward z, which picks up the bowl's large E[y^2 z]); swapping the markers'
  z order flips it, equal z gives 0. [SUPERSEDED in Stage B: that MC used a 7-13 mm thin handle; a ~2 cm round handle gives skew_x toward the concave face in 90%] skew_x is a COIN FLIP (P>0 = 0.47, sd 0.15): depends on handle thickness,
  bowl depth and marker height -- note 07's "+x to convex back" holds only for a thin flat handle.
  => Under the y-skew hypothesis the spoon frame is "B": +y toward M2 (handle-side marker), +x toward the CONCAVE
  (inside) face of the bowl. This reverses note 07's recommendation (which assumed a marker-free symmetric spoon).
- [V] Public V2D repo (nvidia-isaac/video_to_data @ e0bebca, 2026-10-05) has no scan-canonicalisation code; its
  mesh_to_usd geometry uses "largest |component| positive" signs on SVD axes (a different, basis-dependent rule).

## Stage A — appearance, manipulation, visibility (resumed 2026-10-05 ~11:20)
- [V] Eval object order (`kit/.../track_3_evaluation_objects.json`): spoon is SLOT 0 only in 35,36,37 (spoon-only);
  SLOT 1 in 3,5,6 (slot0 white_pot), 15,16 (slot0 plastic_dish_rack), 32,33 (slot0 blue_cup). So the spoon's own
  frame-0 pose sets the scorer's rigid alignment only in 35-37; elsewhere its error is measured after the pot/rack/cup alignment.
- [V] ego_cam_a clip lengths at 20 fps (ffprobe packets): 3:313, 5:288, 6:243, 15:166, 16:173, 32:259, 33:348,
  35:421, 36:407, 37:151 frames (7.5-21 s). All 10 colour clips + cam_b {3,15,35,36,37} + cam_c {3,35,36} on disk.
- [V] Re-confirmed on `frames/cmp_raw35.jpg` and `sheet_a_35.jpg`: delivered colour frames are upright as stored
  (table/hands at bottom, torso at bottom edge). The brief's "rotate 180" must NOT be applied to these mp4s.
- [V visual] Appearance (crops `frames/crop36_f0.png`, `crop37_f0.png`): a plain light (beech-like) wooden cooking
  spoon, pale pink-beige, matte, nearly textureless (faint fine grain only; no print, no logo). Shallow oval bowl
  (~1/3 of length, ~2x handle width at its widest), narrow neck, then a round-section handle that thickens slightly
  toward a blunt rounded end. Three grey ~14 mm mocap spheres on small BLACK bases (high-contrast, the only crisp
  features). The pale wood against the orange-brown round table is low-contrast in hue but separable in saturation;
  against the grey floor it is high-contrast. No flat faces: only the bowl rim/silhouette and markers give pose.
- [V visual] Ep 35 (421 f, `sheet_a_35.jpg`, every 36 f): spoon at rest flat on the round table, bowl upper-left,
  handle toward camera-right, bowl concave-up. ~f36 two-hand pick-up; f72-f144 lifted to a near-VERTICAL pose
  (f72-108 handle-end up / bowl down held at bowl by right hand; f144 bowl up, gripped at handle end); f180-f324
  repeated hand-to-hand transfers with large in-air rotations (horizontal bowl-left, oblique, bowl-up), held
  10-25 cm above the table; ~f360 placed back flat (bowl left, handle upper-right) and released by f396.
  Category: pick -> in-hand reorientation/handover sequence -> place. Largest rotation range of the 10 clips.
- [V visual] Ep 36 (407 f, `sheet_a_36.jpg`, every 34 f): rest flat, bowl left / handle right, concave-up.
  f34 right hand grasps mid-handle (covers M1/M2 region); f68-f340 spoon held mostly bowl-UP and near-vertical or
  steeply tilted, swapped between hands (f204 both hands, f238-272 left hand at handle bottom), roll about the
  long axis varies; ~f374 placed back flat bowl-left with right hand still on handle. Handle-end marker M3 often
  hidden in the fist while held vertical.
- [V visual] Ep 37 (151 f, `sheet_a_37.jpg`, every 13 f): rest flat bowl-left / handle-right, concave-up.
  f13-26 right hand grasps the HANDLE END (over M3); f39-52 spoon lifted fast and high toward the far side, kept
  roughly horizontal (bowl left), visible motion blur; the head also pitches (table drops in image); f78-104 set
  back down ~flat a few cm right of start, then released (f117-143 hands open). Simple pick-lift-place; the end
  pose differs from the start mainly by a translation.
- [V visual] Ep 3 (313 f, `sheet_a_3.jpg`, every 27 f; spoon slot 1 after white_pot): white saucepan (long white
  handle toward camera) on the left of the table, spoon at rest on the right, diagonal (bowl far/upper-left, handle
  near/lower-right toward the table edge), concave-up. f27 right hand reaches the handle end; f54-81 spoon raised
  near-vertical bowl-UP by the right hand while the left hand grips and lifts/steadies the pot handle; f108-162
  spoon tilted over the pot; ~f189 bowl INSIDE the pot (stirring) -> bowl and neck markers occluded by the pot
  wall, only the handle and M3 visible; f216-243 lifted out vertical bowl-up; ~f270 laid back on the table near
  its start (rotated ~20-30 deg in-plane), released ~f297. Task looks like "stir the pot". The pot itself moves.
- [V visual] Ep 15 (166 f, `sheet_a_15.jpg`, every 14 f; slot 1 after plastic_dish_rack): white dish rack along
  the far side of the table with a tall utensil cup at its LEFT end; spoon lies in front of the rack nearest the
  camera, bowl-left / handle-right, concave-up. f28 right hand grasps the handle end; f42-56 lifted and swung
  (two hands) to the left; f70 flipped to bowl-UP / handle-DOWN and inserted HANDLE-FIRST into the utensil cup;
  f84-98 pushed down; f112-165 final rest standing near-vertical in the cup (tilted ~10-20 deg), released.
  Final state: handle and M3 (and probably M2) hidden inside the opaque white cup; only bowl, neck and ~1 marker
  above the rim. Final pose is constrained by the cup geometry (rack is slot 0, its pose known to us).
- [V visual] Ep 16 (173 f, `sheet_a_16.jpg`, every 15 f): near-repeat of ep 15. Spoon in front of the rack,
  bowl-left/handle-right, concave-up; f30 right hand at the handle end; f45-60 lifted, two-hand regrasp, raised
  near-vertical bowl-up; f75 inserted handle-first into the utensil cup; f90-135 adjusted by the right hand;
  f150-172 standing in the cup, released. A bystander sits/moves at the left image edge (not occluding).
  15 and 16 form a matched pair: same start layout, same goal (spoon in utensil cup).
- [V visual] Ep 5 (288 f, `sheet_a_5.jpg`, every 24 f; slot 1 after white_pot): same "stir the pot" layout as
  ep 3 (pot left with handle toward camera; spoon right, pointing away: bowl far, handle near the table edge,
  concave-up). f24 left hand takes the pot handle; f48 right hand lifts the spoon; f72-f192 the bowl is inside the
  pot and the spoon is held near-horizontal from the right (handle end + M3 to the right, bowl/M1 behind the pot
  wall or seen through the opening), pot lifted and moved with motion blur (~f96); f216 lifted out near-vertical
  bowl-up; f240-287 laid back down near its start, right hand still touching at the end. Longest in-pot phase.
- [V visual] Ep 6 (243 f, `sheet_a_6.jpg`, every 21 f; slot 1 after white_pot): third "stir the pot" repeat
  (3,5,6 share the layout). Spoon right of the pot, bowl far / handle near, concave-up. f21 left hand on pot
  handle; f42 right hand lifts the spoon; f63-f147 bowl in the pot, spoon held near-horizontal from the right
  (M3 at right end visible, M1 near the pot rim), pot slightly lifted; f168-f210 placed back near its start
  (bowl far, handle near), released by ~f231. The spoon bowl is visible THROUGH the pot opening from above in
  several in-pot frames (top-down view), so in-pot occlusion is partial, not total.
- [V visual] Ep 32 (259 f, `sheet_a_32.jpg`, every 22 f; slot 1 after blue_cup): blue cup on the left (left hand
  ALREADY on it at f0), spoon on the right, bowl far / handle near, concave-up. f22 cup lifted; f44 right hand
  takes the handle; f66 spoon raised bowl-up; f88 and ~f154 the BOWL is put INTO the hand-held cup (cup tipped
  toward the spoon; scooping/stirring), bowl hidden by the opaque blue cup wall, handle + M3 outside; f110-f132 and
  f176 spoon out in the air between dips; f198-f258 laid back on the table near its start; right hand still on the
  spoon and left hand still holding the cup at the last frame (end pose may not be a free rest).
- [V visual] Ep 33 (348 f, `sheet_a_33.jpg`, every 29 f): same layout as 32 (cup left, spoon right diagonal, bowl
  far-left / handle near-right, concave-up). f29 left hand on cup; f58 spoon picked by the right hand; then 3-4
  dip cycles: bowl into the hand-held cup (~f87, f145, f203-232) alternating with in-air horizontal/oblique poses
  held high above the table (~f116, f174, f261, often above the far table edge, against the grey floor);
  ~f290 laid back on the table near its start; hands still on cup and spoon at f319-347.
- [V] Colour probe, ep 37 f0 (24x24 px patches, `scripts/colour_probe.py`, `frames/stageA/e37_f0_probe.jpg`),
  OpenCV HSV (H 0-180) / LAB medians: spoon bowl H12 S61 V239, handle H12 S70 V236 (LAB 209-215,137,144-146);
  palms H7-8 S83-90 V176-194 (LAB 148-166,143-145,143-144); table H14 S210 V165; floor H87 S11 V182.
  => the spoon is trivially separable from table (saturation 60-70 vs 210) and floor (S ~11), but NOT robustly
  from bare skin: same hue, only ~20 S and ~40-60 L apart, and hand shading closes the L gap. Any colour/
  appearance segmenter must handle spoon-in-hand explicitly (learned segmenter or 3D/marker cues), not thresholds.
- [E] Spoon size from ep 37 f0 (spoon flat on the table, near image centre; `scripts/spoon_size.py 37 0
  700,915,1400,1065 1180,900,1420,948`, overlays `frames/stageA/e37_f0_size.jpg`, `e37_markers_zoom.png`).
  Wood mask (S 48-130, V>170, glare box excluded) undistorted with ego_cam_a K + 14-coef rational model; ruler =
  marker sphere, diameter read off 6x zooms as 29-30 px (threshold blobs under-read 21-28 px) -> ~0.0264
  normalized; sphere = 14.4 mm (public-scan fit, r 6.6-7.7 mm). Scale ~0.545 m per normalized unit (depth ~0.55 m).
  Overall wood length ~30 cm (+-2 cm, +-7% from ruler); bowl ~9-10 cm long, max width ~5.2 cm; neck ~1.6 cm;
  handle ~1.9-2.4 cm wide, widest ~3/4 along, rounding off at the end. Along-axis marker centres from the bowl
  tip: M1 ~11.4 cm (side edge, lateral -1.9 cm), M2 ~15.5 cm (opposite edge, lateral +1.0 cm), M3 ~30.6 cm (end
  face). Thickness not observable top-down (round handle, so ~2 cm assumed [H]); bowl depth unknown (~1 cm [H]).
  Cross-check against a second ruler (stereo b/c disparity, or a scanned pot/cup at known height) still TODO.
- [V visual] In-hand views (`frames/held35.jpg`, `held36.jpg`): grasps are power grips around the handle covering
  ~5-8 cm (often the mid-handle including M2, or the end including M3) or pinches at the bowl; the bowl stays
  visible in most held frames. Held vertical/oblique poses foreshorten the spoon strongly (it points at/away from
  the head-mounted camera). Fast moves show 5-20 px motion blur on the handle edges at 20 fps. The bowl's concave
  face shows a soft shading gradient and the convex back is evenly lit, so concave/convex is usually visible at
  bowl sizes of >=150 px; together with the side markers (M1 near the bowl, M2 opposite and further toward the
  handle) this resolves the spoon's roll about its long axis when the neck is unoccluded.
- [V visual] Occlusion probes (`frames/stageA/occl_quad.jpg`): ep 15 f160 spoon standing bowl-up in the utensil
  cup: bowl + neck + BOTH side markers M1/M2 visible above the rim, lower ~half of the handle and M3 hidden.
  ep 3 f189 / ep 5 f144 (bowl in the white pot): the head looks down INTO the pot, so the bowl is still visible
  through the opening; all 3 markers visible; hand covers the mid-handle; moderate blur in ep 5. ep 32 f88 (bowl in
  the tipped blue cup): bowl fully hidden by the opaque cup, but neck/handle (~20 cm), M1/M2 at the rim and M3
  visible. So the worst occlusions are cup/holder insertions (15,16 final rest; 32,33 dips), not the pot stirs.
- [V visual] Frame-0 crops of all spoon clips (`frames/stageA/f0_montage.jpg` for 3,5,6,15,16,32,33,35; 36/37 in
  `crop36_f0.png`/`crop37_f0.png`): in 10/10 the spoon starts at rest, flat on the table, CONCAVE-UP, fully visible,
  untouched (only ep 32 has a hand on the other object at f0). Marker layout is the same in every view, as it must
  be for one rigid spoon: seen from above with the bowl->handle direction pointing image-right, M1 (near the bowl) is
  on the far/upper side and M2 on the near/lower side.

### Stage A per-episode summary (all [V visual] from 12-frame contact sheets plus spot frames; frames approximate)
| ep | slot | others | task (inferred) | start | main motion | worst visibility | end |
|---|---|---|---|---|---|---|---|
| 35 | 0 | - | pick, reorient, hand-over, place | flat, bowl far-left | large in-air rotations incl. vertical | fists on handle, blur | flat on table, released |
| 36 | 0 | - | pick, hold bowl-up, hand-over, place | flat, bowl left | mostly vertical bowl-up, roll changes | M3/handle in fist, end-on views | flat, hand still on |
| 37 | 0 | - | pick-lift-place | flat, bowl left | fast lift high, ~horizontal | blur f39-52 | flat, shifted right, released |
| 3 | 1 | white_pot | stir pot | flat, right of pot | vertical bowl-up, bowl in pot | bowl in pot (seen from above) | flat near start, released |
| 5 | 1 | white_pot | stir pot | flat, right of pot | bowl in pot ~f72-192, pot moved | blur, pot rim | flat near start, hand touching |
| 6 | 1 | white_pot | stir pot | flat, right of pot | bowl in pot ~f63-147 | pot rim | flat near start, released |
| 15 | 1 | plastic_dish_rack | put spoon in utensil cup | flat, in front of rack | flip bowl-up, insert handle-first | handle+M3 inside cup at end | standing in cup |
| 16 | 1 | plastic_dish_rack | same as 15 | same | same | same | standing in cup |
| 32 | 1 | blue_cup | dip/scoop into hand-held cup | flat, right of cup | 2 dips into tipped cup | bowl hidden in cup | flat near start, hands on |
| 33 | 1 | blue_cup | same as 32, 3-4 dips | flat, right of cup | dips + high in-air poses | bowl hidden in cup | flat near start, hands on |
Spoon appears to stay inside the colour FOV in all sampled frames [E: 12 samples/clip, not every frame checked].
- [V] Mono probe, ego_cam_b ep 35 f0 (12x12 px medians, `frames/stageA/b35_f0_probe.jpg`): spoon bowl 216, handle
  193, table 107, palms 148-155, floor 181. In mono (IR-sensitive) the spoon is near-white: excellent contrast to the
  table, ~40-60 levels above skin, but only ~10-35 above the grey floor. Colour (saturation) and mono (brightness)
  fail on different backgrounds (colour: skin; mono: floor), so a fused segmenter is the robust choice [H].
  In the mono pair the spoon spans ~260 px when flat at f0 and a marker is ~14 px across (black base clearest).

### Stage A method design (proposals [H]; nothing implemented yet)
1. Own mesh (needed for CD-O and as the sim asset; no public scan exists). Parametric spoon: curved centreline,
   lofted elliptical sections (shallow ellipsoidal bowl shell ~10x5.2 cm, neck ~1.6 cm, round handle ~2 cm,
   total ~30 cm), plus 3 sphere+base markers at the measured stations. Fit the planform to the 10 frame-0
   top views (flat, concave-up, untouched in 10/10; undistort and map to the table plane), fit thickness/bowl
   depth from side and end-on views (ep 35/36 vertical holds) and stereo. Whether the CD-O mesh includes the markers,
   and the x/y sign choice, are Stage B/C questions (see the marker-skew results above).
2. Frame-0 initialisation (automatic, no hand labels): the spoon is the pale low-saturation blob inside the orange
   table disc, with 3 grey/black marker blobs; bowl end = wide end of the width profile (works on ep 37). The pose is
   then 3 DoF on the table plane (x, y, yaw) with known roll (concave-up, at rest). This matters most in 35-37,
   where the spoon is slot 0 and its f0 pose sets the scorer's alignment.
3. Per-frame pose, primary cue = markers. Detect the black-base/grey-sphere blobs in ego_cam_b+c (~14 px) and
   colour (~29 px), gated by the spoon mask because pot/cup/rack carry markers too. Triangulate them (75 mm
   baseline, f~565 px, Z~0.55 m: disparity ~77 px, ~4 mm depth error per 0.5 px) and run Kabsch on the M1/M2/M3
   triangle for full 6-DoF. Identity follows from geometry: M3 at the handle end; M1/M2 at ~11.4 vs ~15.5 cm from
   the bowl tip, on opposite sides. The triangle is thin (~3 cm across, ~19 cm long), so expect roll error of
   about 5 deg from markers alone [E].
4. Fallback cue = silhouette/edge render-and-compare with a fused colour-saturation + mono-brightness mask, used
   when <=2 markers show (fist over M2/M3; in-cup in 15/16/32/33). Roll comes from the side of the visible marker
   and from concave-face shading. Mirror and concave/convex flips are the main failure mode.
5. Temporal/physical layer: an SE(3) smoother with static rest segments (start, end, in-cup), and a collision-aware
   projection against the table and the tracked slot-0 object (pot walls in 3/5/6, utensil cup in 15/16, blue cup in
   32/33), so the FlashCHORD policy gets a feasible reference. World-frame poses need head ego-motion (the head
   pitches visibly, e.g. ep 37 f52), which can be shared with the other digs.
6. Falsification tests with no spoon GT needed: (a) at f0 in 35/36/37, the stereo-triangulated inter-marker
   distances must agree across episodes within ~3 mm, and all 3 marker heights must fit a body resting on the table
   plane; (b) validate the stereo-marker tracker on a PUBLIC marker-bearing object with GT (fit the scan's marker
   spheres as in `out/markers.log`, project them via GT, measure detection and ADD error); (c) check that the
   ~30 cm length agrees with the stereo scale, since the marker-diameter ruler is only +-7%.
Stage A status: COMPLETE (2026-10-05). Next: Stage B per orchestrator.

## Stage B — deterministic axis-sign rule search (CPU), started 2026-10-05
- Resume marker. Inputs reused: note 07 rule R1 (origin/axes exact; z by skew 10/10), `scripts-prev/meshframe/canon.py`,
  `work/13/out/stats.{json,log}` (11 sign statistics x 3 axes on the 10 visual + 3 collision scans),
  `work/13/scripts/spoon_model.py` (lofted spoon + 3 markers) and its 600-sample MC (`out/spoon_mc_*.log`).
  New Stage B scripts go to `work/13/scripts/b_*.py`, outputs to `work/13/out/b_*`.
- [V] Re-checked the public V2D snapshot (`work/13/out/v2drepo/`, nvidia-isaac/video_to_data @ e0bebca): `object_pose_frame.py`
  only READS a stored alignment matrix ("centered_axis_aligned"), `canonicalization.py` is about policy heading frames, and
  `evaluate_mesh_quality.py` (CD-O) uses an unsigned PCA basis plus all 24 proper axis maps with ICP. No primary-source sign
  rule exists, so Stage B is an empirical search on the 10 published frames.
- [V] Extended catalogue (`scripts/b_feats.py` -> `out/b_feats.json`, table `scripts/b_table.py` -> `out/b_table.log`): 28
  axis-odd statistics per axis on the 10 visual scans (exact degree-5 quadrature moments; one-sided moments sign(a)|a|^k for
  k=0, 0.5, 2, 4; -median; percentile asymmetry q_p+q_(1-p) for p=1,5,10,25%; bbox/extreme centre; sign of the farthest
  vertex along the axis and in 3D; mixed moments E[a b^2], E[a|b|], E[a r^2], E[a z|z|], E[a z^3]; vertex mean/skew (raw and
  welded); convex-hull surface/volume centroid offsets and hull skew; volume-centroid offset). Skews reproduce note 07 exactly.
  Net area-vector is ~1e-18, so the scans are geometrically CLOSED (only unwelded); volume-based statistics are meaningful.
- [V] Single-statistic counts (published direction positive, out of 10): z: 10/10 for skew, signed square (CPCA) and the new
  q10 asymmetry (q90+q10 > 0); 9/10 for m5, s4, -median, q05, extreme/bbox, vskew. x: best 8/10 (vertex mean; -shalf).
  y: best 9/10 (far3d: the 3-D farthest vertex has y>0, fails blue_cup; vskew, fails white_pot). So NO single statistic
  fixes the roll on all 10 scans, in either polarity.
- [V] Roll-rule search (`scripts/b_search.py`, log `out/b_search.log`, hybrids `out/b_hybrids.json`; z fixed by skew_z>0;
  28 odd statistics, both polarities). Rules that reproduce all 10 published (x, y) signs:
  F1 single statistic on x or y: 0/112. F4 kurtosis-selected axis (min/max kurt or |kurt| of x,y) signed by any statistic:
  0/224. F2 "sign the x/y axis with the larger |r|" by statistic s: 15/1624, ALL signed by a low-order one-sided statistic
  (s_half = E[sign(a)|a|^0.5] < 0 in 13; area fraction < 0, -median > 0, q05 asymmetry > 0 once each), ranked by
  |skew|, |m5|, |ssq|, |s4|, skew z-score, |ext|, ... F2b 3-axis cascade (fix the two axes with the largest |r|, complete
  the third right-handed): 1/1404 (rank by |s_half|, sign by q05 asymmetry > 0). F3 hybrids "if |s1(a1)| >= tau use s1
  else s2 on a2" (tau fitted): 154 of 12,544 primary/fallback shapes admit a tau (best: q10 on y, else far3d on y,
  tau in [0.0022, 0.41)).
- [V] Multiple-comparison null (`scripts/b_null.py`, 2000 random per-scan roll flips, same search rerun; `out/b_null.log`):
  P(>=1 rule fits 10/10) = F1 0.054, F2 0.208, F2b 0.013, F4 0.106, F3 0.948; jointly for the parameter-free families
  (F1|F2|F2b|F4) 0.296, and 0.955 once hybrids are allowed. Observed counts vs null tails: F2 15 rules (P(>=15)=0.035),
  F3 154 shapes (P(>=154)=0.092). => Finding SOME deterministic rule that reproduces all 10 roll bits is expected by chance
  (about 30% without thresholds, 95% with one fitted threshold). The search gives NO significant evidence for any roll rule.
  The best single-family p (F2b, 0.013) is not significant after correcting for the ~5 families tried (~0.065) and
  rests on a statistic with no textbook pedigree. [V for the numbers; H that the null of independent roll bits is the right one]
- [V] Leave-one-out (`scripts/b_loo.py` -> `out/b_loo.log`; null `scripts/b_loo_null.py` -> `out/b_loo_null.log`). For each
  held-out scan: the rules that fit the other 9, and the share of them that predict its roll. Parameter-free union
  (F1|F2|F2b|F4): mean share 0.73. It is ~1.0 on the 7 scans where the same 15-16 all-10 rules dominate, but 0.53 on
  beige_cup, 0.28 on wooden_piece_1 and 0.09 on wooden_piece_2. Hybrids (tau refitted on 9): mean 0.61 (0.25-0.96).
  Null for the union (1000 random roll configurations): mean 0.24, P(share >= 0.725) = 0.197 => not significant.
  The selected rules do NOT generalise to the scans that decide them (the two wooden pieces).
- [V] z-sign positive control, same machinery: single statistics fitting z on 10/10 are skew, CPCA signed square and q10
  asymmetry; null P(>=1 of 28 statistics fits | random z bits) = 0.022; LOO share 1.0 on 9 scans, 0.25 on wooden_piece_2,
  whose skew_z = +0.0003 is a near-tie. So the z rule rests on 9 informative scans plus 1 tie. It is supported (p ~ 0.02,
  as in note 07), and the spoon's z is not near a tie (skew_z +0.2..+0.4).
- [V] Margins of the 16 surviving parameter-free rules (`scripts/b_margin.py` -> `out/b_margin.log`). All 15 F2 rules use
  the same axis choice in effect: y for beige_cup and water_pitcher, x for the other 8. 13 are signed by -s_half and decide
  wooden_piece_1 by 0.0009 and wooden_piece_2 by 0.0030. "Rank |s_half|, sign q05" decides every scan by >= 0.023, but
  its wp1 axis choice rests on |s_half_y| 0.0015 vs |s_half_x| 0.0009. The F2b rule decides the lid's y by 0.0003. So every
  rule found fits at least one scan only through a near-tie.
- [V] Sampling SD of each statistic at n = 1e5 surface points (`scripts/b_sample.py`, 40 draws/scan -> `out/b_sample.json`):
  skew 0.004-0.013, s_half 0.0006-0.0014. The near-tie margins above are about 1 SD, i.e. coin flips for any implementation
  that samples points or differs in tessellation.
- [V] Noisy-sign models (`scripts/b_noisy.py` -> `out/b_noisy.log`, `out/b_noisy_z.log`): the published bit = sign of p*s(a)
  computed on n random samples, P = Phi(s/SE_n), likelihood maximised over n in [1e2, 1e9], against random roll bits (2^-10).
  Best roll model: y by q10 asymmetry at n* ~ 3e4, LR 54. Next come y by -E[y|x|], m5, s4, skew (LR 14-17, n* ~ 3e3).
  Note 07's skew_y hypothesis peaks at LR 14 at n ~ 3e3 and drops to 0.1 at n = 1e5. Null for the max LR over all models
  (2000 random roll configs): median 12.7, mean 75, P(max >= 54) = 0.18 => NOT significant. Control: z by skew/ssq/q10
  reaches the maximum LR 1024 at n -> inf, null P = 0.019.
  => Conclusion [V within this catalogue]: the 10 published frames carry evidence for the z rule (p ~ 0.02) but none for any
  roll rule. Deterministic, noisy, cascade and threshold rules alike are indistinguishable from random roll bits after
  the look-elsewhere correction. The roll prior for the spoon stays near 50/50 from the scans alone. [H] The roll was
  possibly set by an unrecorded step (hand edit, original capture frame, sampled sign) not visible in the final meshes.
- [V visual, weak] Handle section from oblique/edge-on held views (`frames/held35.jpg` panels 1, 3, 4; `held36.jpg`): the
  handle looks about as thick as it is wide (near-round, ~2 cm). It runs on from the bowl rim line, with the bowl a thin
  shell below it. So the earlier MC's handle thickness of 7-13 mm was too thin. Stage B spoon MC: thickness/width 0.75-1.05
  (round) as the main case, 0.5-0.75 (oval) as sensitivity.
- [RUNNING 2026-10-05] Spoon-rule MC `scripts/b_spoon.py N seed mode` (round x2 seeds 1,2 N=150; oval seed 3 N=150; nomark
  seed 4 N=100), output appended per sample to `out/b_spoon_<mode>_<seed>.jsonl` (resumable: count lines). Smoke test
  (3 round samples): skew_x -0.07..-0.10, skew_y -0.02..-0.04, skew_z +0.26 -> frame B under skew_x, skew_y, hybrid and
  larger_abs.
- [DONE] Spoon-rule MC finished: 550 samples (round 300, oval 150, nomark 100); summary `scripts/b_spoon_sum.py` ->
  `out/b_spoon_sum.log`. Frame labels: A = +x to the CONVEX back, +y to M1; B = +x out of the CONCAVE face, +y to M2
  (handle-side marker); +z bowl -> handle in 550/550 (skew_z +0.12..+0.45, >= 50 SE at n=1e5; never near a tie).
  [V model] Spoon statistics in the construction frame (mean +- sd; P(>0)):
  | mode | skew_x | P(skew_x>0) | skew_y | P(skew_y>0) | skew_z |
  |---|---|---|---|---|---|
  | round + markers (main) | -0.075 +- 0.058 | 0.10 | -0.035 +- 0.009 | 0.00 | +0.27 |
  | oval (th/2w 0.5-0.75) + markers | -0.014 +- 0.078 | 0.39 | -0.038 +- 0.009 | 0.00 | +0.34 |
  | round, no markers | -0.072 +- 0.034 | 0.02 | +0.000 +- 0.011 | 0.51 | +0.25 |
  The brief's premise holds for MAGNITUDE (|skew_x| ~ 16 SE at n=1e5 for a round handle). Its SIGN points to the CONCAVE
  face, the opposite of note 07's thin-handle expectation: a ~2 cm round handle, centred near the rim plane, sticks
  out beyond the rim on the concave side, while the bowl's thin shell stays inside the handle's x-range on the convex side.
  Drivers (oval mode): a deeper bowl pushes skew_x toward the convex back (P(skew_x>0) by Db tercile 0.08/0.22/0.88,
  corr +0.74), a thicker handle pushes it toward the concave face (corr -0.50). Round mode: P(>0) <= 0.23 in every tercile.
  skew_y is set by the markers: M1 (near the bowl) and M2 (further up) sit at different z, so skew_y < 0 (toward M2) in
  450/450 marker samples (~6 SE at n=1e5). Without markers it is a coin flip.
- [V model] Spoon roll by rule (P(frame A); main round+markers / oval / no markers):
  note-07 skew_x 0.10 / 0.39 / 0.02; skew_y 0.00 / 0.00 / 0.51; hybrid(0.02) 0.003 / 0.00 / 0.02; larger|skew| 0.01 / 0.27 / 0.04.
  The 15 F2 survivors 0.00-0.06 / 0.05-0.21 / 0.04-0.11 (except F2|absmax|-shalf at 0.52 without markers). The F2b
  survivor 0.03 / 0.15 / 0.04. Noisy best models: y by q10 0.02 / 0.00 / 0.51; y by m5, s4 0.00; x by -s_half 0.06 / 0.21 / 0.06.
  The 154 F3 hybrids, tau at geometric mid: mean share A 0.21 / 0.23 / 0.35.
  EXCEPTIONS that favour A: x by far3d (0.82 / 0.87 / 1.00) and the widest hybrids with a far3d_y fallback. On the spoon,
  far3d is ALWAYS the M3 cap at the handle end, whose lateral offsets are 1.5 mm (x) and 0.4 mm (y), set by how M3 is
  mounted. These rules are coin flips on the real spoon and carry no information.
  => Every surviving rule that is not a near-tie on the spoon gives frame B for the main shape. The rules disagree
  on WHICH public scans they fit, but they agree on the spoon, because its x and y statistics are far from ties
  (unlike wooden_piece_1/2 and the cups).
- [E] Model average (`scripts/b_bma.py` -> `out/b_bma.log`, sensitivity `out/b_bma_sens.log`). Classes: random roll /
  parameter-free deterministic rules (16/3364 fit) / noisy single-statistic models (log-uniform n), each weighted by its
  average likelihood on the 10 published rolls. Posterior class weights at equal class priors: 0.15 / 0.72 / 0.13 =>
  P(B) = 0.90 (round), 0.81 (oval), 0.79 (no markers). The DET weight is inflated by the 15 near-duplicate F2 rules. With a
  sceptical prior (0.8 or 0.9 on random roll, justified by the non-significant null), P(B) = 0.69 / 0.61 (round) and
  0.65 / 0.59 (oval). So P(B) ~ 0.6-0.9: B is the better bet under every prior tried, but it is NOT a confident call.
- [V] Textbook cascades (`out/b_textbook.log`): "fix the axis with the largest |skew| (or skew z-score, or |ssq|) first,
  then the next, by sign of the same statistic, complete right-handed" = 9/10, failing only on wooden_piece_2 (skew_x
  -0.54, confident). The q10 or extreme versions score 6-7/10. On the spoon the |skew| order is z (0.27) > x (0.075) >
  y (0.035), so this cascade signs z and x by skew and gives B (P(A) 0.01 round, 0.27 oval).
  wooden_piece_2 remains the one confident counter-example to every x-moment rule: its 3 markers are on its -x face and
  it rests -x up, whereas wp1's markers are on +x and it rests +x up. Both rest marker-up, but their published x
  relative to the markers is opposite. [H] There may be an unrecorded manual or capture-frame step.

### Stage B summary (2026-10-05)
1. [Stage C: the Track 2 holdout supports the noisy mid-axis skew rule, P = 0.006 on 14 fresh scans] [V] No deterministic sign rule in a wide catalogue reproduces all 10 published roll bits robustly. That covers 28
   odd statistics x polarity x {single axis, larger-|r| selection, 3-axis top-2 cascade with right-hand completion,
   kurtosis selection, one-threshold hybrids}. 16 parameter-free rules fit 10/10, and all fit at least one scan by a
   near-tie (0.0003-0.0015, ~1 sampling SD at n=1e5). Random roll bits produce some fitting parameter-free rule 30% of the
   time, and a fitting hybrid 95% of the time. LOO share 0.73 vs null P = 0.20; best noisy model LR 54 vs null P = 0.18.
   The z rule passes the same tests (p ~ 0.02).
2. [V model] The spoon itself is NOT near a tie. With a ~2 cm round handle and the 3 markers, skew_z > 0 (bowl -> handle),
   skew_x < 0 (toward the concave face) in 90%, and skew_y < 0 (toward M2) in 100%. So almost every candidate rule maps
   it to the same frame. Frame B: +z bowl -> handle end; +x out of the concave (inside) face of the bowl, i.e. UP when
   the spoon rests concave-up; +y = z x x toward the M2 (handle-side marker) edge. In a top view with z pointing
   image-right and the spoon concave-up, +y points to the near/lower image side, where M2 is (Stage A). The only rules
   that give A use far3d, which is a coin flip on the spoon.
3. [UPDATED in Stage C to ~0.80-0.87 by the Track 2 holdout] [E] P(spoon frame = B) ~ 0.6-0.9, depending on how much prior weight goes to "the roll is not a moment rule"
   (0.69 at a sceptical 0.8 prior; 0.90 at equal class priors), for the round-handle shape. This REVERSES note 07's
   "+x toward the convex back" recommendation. Note 07 assumed a thin flat handle and no markers.
4. Recommendation for whoever builds the spoon asset [H]: apply R1 (origin/axes) to our closed spoon mesh WITH the 3
   markers and bases modelled. Then compute skew_x and skew_y in the physical frame. If skew_x points to the concave face
   AND skew_y points to M2 (expected), every non-tie rule agrees: commit to frame B and record it as a ~0.7-0.9 bet. If
   our mesh gives skew_x toward the convex back, the x- and y-based rules split and the bet drops to ~0.5-0.6.
   Committing still beats hedging (note 07, section 5).
5. Falsifiers / Stage C inputs needed: (a) handle thickness and bowl depth from edge-on views (ep 35 f72-f144, ep 36)
   plus stereo. A thin oval handle (th/2w < 0.6) with a deep bowl (Db > 12 mm) flips skew_x to the convex back. (b) The
   z order of M1 and M2 from stereo at frame 0 (35-37): M1 nearer the bowl tip than M2 sets skew_y < 0. Equal z would
   make y a tie. (c) Whether the organisers' spoon scan includes the markers; all public scans do (`out/markers.log`).
   Without markers skew_y is a tie, but x still gives B for a round handle. (d) Only the organisers' rule or spoon
   frame can settle it. Asking them is still worth ~0.5 SP-SR (note 07).
Stage B status: COMPLETE (2026-10-05). Scripts `work/13/scripts/b_*.py`; outputs `work/13/out/b_*`.

## Stage C — reconstruction options, CD-O, frame stability, tracking mitigations, roll decision (started 2026-10-05)
- Resume marker. Stage C scripts go to `work/13/scripts/c_*.py`, outputs `work/13/out/c_*`.
- [V code] CD-O scorer (`kit/.../metric_code/track_3/CD-O.py`): per (episode, slot) the candidate is (1) rescaled about its
  area centroid to the reference's surface radius of gyration, (2) rigidly ICP-aligned from 25 starts (identity + the
  proper PCA-axis permutation/sign maps; 3,000 samples, 40 iterations, 90% trimmed), then (3) scored as the symmetric mean
  nearest-neighbour distance between 10,000 area-weighted surface samples per mesh, in cm. Both meshes first go through
  `v2dlb/mesh_budget.py` (weld, quadric-decimate to <= 4,096 faces, pad with zero-area faces). Consequences: CD-O is
  blind to our absolute scale, origin, axes and the roll bit; only SHAPE counts. Each eval episode carries its own spoon
  mesh row set (10 rows of the CD-O mean are the spoon), so one good spoon mesh can be reused for all 10.
- [V code] Submission rules (`kit/.../config/tracks.json`): 5 submissions per week, unlimited in the final 3 days, at most
  2 final submissions, `private_fraction` 0 (every scored row is on the public board, so the public board IS the final
  ranking), every row carries one GitHub commit URL, and pose CSVs carry per-episode policy-checkpoint and evaluator
  SHA-256 hashes. Organisers can inspect the commit.
- [V code] FlashCHORD observation (`work/14/repo/observation.py:603-640`): the policy sees the object's world quaternion and the
  command quaternion inv(q_obj) * unique(q_ref), i.e. quantities expressed in the object's BODY frame, with a sign
  canonicalisation (`unique_quat`) on the reference. A 180 deg change of the spoon body frame is therefore not a linear
  relabelling of the observation: a policy trained in frame A cannot be reused for frame B by re-export or by folding a
  fixed matrix into its first layer. A genuine frame-B variant needs its own spoon policies (10 episodes; note 14 plans
  2-4 GPU-h per policy, so ~20-40 GPU-h per seed sweep, or less with warm starts from the A policies [E]). The object
  keypoint reward (+-1 m body points, note 14) is invariant to a 180 deg flip about z, so the two MDPs are the same
  physics; only the observation encoding differs [V code, E consequence].
- [V model] Per-frame stereo marker-triangle tracker accuracy (`scripts/c_track.py` -> `out/c_track.log`; prior-mean spoon,
  markers relative to the R1 centroid: M1 (-2, +19, -25) mm, M2 (-2, -19, +15) mm, M3 (-2, 0, +166) mm; R1 centroid 139 mm
  from the bowl tip; surface sd per axis 5.7 / 10.6 / 88.9 mm). Linear triangulation + Kabsch, iid 2-D centre noise sigma,
  3,000 poses each; random orientations at 0.35-0.7 m unless "flat" (resting on the table, camera pitched 40-60 deg, 0.55 m):
  | cameras, sigma | rot med / p90 (deg) | roll med / p90 | tilt med | origin med (mm) | ADD med / p90 (cm) | MPPE med (cm) | rot > 30 deg |
  |---|---|---|---|---|---|---|---|
  | b+c, 0.5 px | 3.0 / 10.3 | 2.5 / 10.2 | 0.9 | 2.1 | 0.29 / 0.65 | 0.35 | 0.3% |
  | b+c, 1.0 px | 6.3 / 21.7 | 5.2 / 21.3 | 1.8 | 4.3 | 0.59 / 1.31 | 0.71 | 5.6% |
  | b+c, 2.0 px (blur) | 12.4 / 45.2 | 10.1 / 44.9 | 3.5 | 8.3 | 1.16 / 2.66 | 1.43 | 19% |
  | a+b+c, 0.5 px | 1.6 / 5.3 | 1.3 / 5.1 | 0.5 | 1.2 | 0.15 / 0.34 | 0.18 | 0% |
  | b+c, 0.5 px, marker model +-2 mm | 4.9 / 12.7 | 4.4 / 12.4 | 1.4 | 3.0 | 0.41 / 0.76 | 0.50 | 0.4% |
  | b+c, 0.5 px, flat on table | 6.0 / 13.8 | 5.7 / 13.7 | 1.3 | 2.5 | 0.37 / 0.66 | 0.53 | 0.1% |
  | a+b+c, 0.5 px, flat on table | 3.2 / 7.7 | 3.0 / 7.6 | 0.6 | 1.3 | 0.19 / 0.34 | 0.28 | 0% |
  Reading: almost all of the rotation error is ROLL about the long axis, set by the 3.8 cm M1-M2 lateral lever; the long
  axis itself (tilt, M1/M2 -> M3 lever ~17 cm) is good to ~1 deg. Because the spoon is thin, roll errors cost little ADD/
  MPPE (<= 0.7 cm at 1 px) but they do enter the orientation means of SP-SR (0.5 rad) and MP-SR (30 deg): at 2 px (motion
  blur) a fifth of single frames exceed 30 deg, so temporal smoothing and the colour camera are needed. With only 2
  markers visible (fist over M3, or M3 inside the utensil cup in 15/16) the rotation about the M1-M2 line is unobservable
  from markers [V geometry]; the long axis must then come from the silhouette/edge fit. Assumptions: markers detected and
  correctly identified; no outliers; calibration exact (principal-point frame still unverified, Stage A). [E]
- [V] New public-data lead for the roll rule: Track 2 (`track_2/tier_1_multiview_caption/mesh/`, HF dataset, public) holds 29
  more organiser scans (baseball_bat, cane, squeegee, iron, ...). Note 14's GLB headers (`work/14/t2/glbhead/`, bboxes
  `glb_bbox.json`) show identity nodes and extents whose THINNEST axis is y and LONGEST is z (e.g. big_black_box 0.52 x 0.40
  x 0.86 m, big_red_bowl 0.30 x 0.13 x 0.30), so Track 2 is not in R1's (x thin, y mid, z long) order as stored. If it is a
  permuted R1 (centroid origin, covariance-diagonal axes), its 29 sign bits are a FRESH HOLDOUT for the z and roll rules.
  Geometry only (positions + indices) is ~124 MB in total via HTTP range requests; testing a few long objects first.
- [V] Track 2 geometry probe (`scripts/c_t2geom.py`, range-fetched positions+indices to `work/13/t2/<name>.npz`, stats
  `out/c_t2geom.jsonl`; axes test `scripts/c_t2axes.py`). First 7 scans (cane, baseball_bat, squeegee, iron, spray_bottle,
  big_red_bowl, light_blue_book; ~99k faces each): area-weighted surface centroid = origin to 0.01 mm in 7/7 (same origin
  rule as Track 3). Stored axes are close to, but not exactly, the area-PCA axes: 0.2-1 deg off when well conditioned
  (2-41 deg when two eigenvalues nearly tie: iron, spray_bottle, baseball_bat); vertex or welded-vertex PCA is not closer.
  [H] the axes were computed before a final decimation to ~100k faces. Axis ORDER differs from Track 3: y = smallest
  variance, x = middle, z = largest (7/7). Skews along the stored axes: z > 0 in 6/6 non-ties (book +-0.0006 tie); x (middle
  axis) > 0 in 7/7 (+0.015..+0.45); y (smallest) > 0 in 6/7 (squeegee -0.18). Track 3 for comparison (`out/b_table.log`):
  middle axis y skew > 0 in 7/10, smallest x in 7/10. So "middle axis signed by positive skew" fits Track 2 so far but
  not Track 3: either the pipelines differ in more than axis order, or Track 3's roll bits are noise. Remaining 22 scans
  are downloading (`out/c_t2geom_bg.log`).
- Pre-registration (written before the remaining 22 Track 2 scans are analysed): role-ordered axes (min, mid, max variance)
  map Track 3 (x, y, z) and Track 2 (y, x, z). Tests on the 22 unseen scans, excluding roll-degenerate ones (min/mid sd
  ratio > 0.91, as for the cups): H1 "mid axis signed by positive skew" (suggested by the first 7, so only the 22 count);
  H2 the 16 Track 3 parameter-free survivors of Stage B; H3 z (max) by skew > 0; H4 the textbook cascade. Under random
  roll bits each pre-registered rule scores Binomial(n, 0.5). Script `scripts/c_t2rules.py`.
- [V] Track 2 holdout results, all 29 scans (`scripts/c_t2rules.py` -> `out/c_t2rules.log`, features along the STORED axes
  `out/c_t2feats_stored.json`). Note: statistics must be taken along the stored axes. Along recomputed exact-PCA axes
  (`out/c_t2rules_pca.log`, `c_t2feats_pca.json`) they change materially for long objects: a 0.5 deg tilt moves the cane's
  min-axis skew from +0.90 to +0.66 by mixing in E[a^2 z]. 11 scans are roll-degenerate (min/mid sd > 0.91) and 7 are
  z-degenerate (mid/max > 0.91).
  | pre-registered test | all non-degenerate | fresh (22 unseen) non-degenerate | P under random bits (fresh) |
  |---|---|---|---|
  | H1 mid axis (Track 2 x) by skew > 0 | 16/18 | 12/14 | 0.006 |
  | same with signed square (ssq) / -median / q10 | 17/18 each | 13/14 each | 0.001 |
  | min axis (Track 2 y) by skew > 0 | 10/18 | 7/14 | 0.61 (coin flip, as expected for the completed axis) |
  | H3 max axis z by skew > 0 | 18/22 | 13/16 | 0.011 |
  | H2 Stage B's 16 Track 3 survivors | 12-14/18 | 9-11/14 | 0.03-0.21 |
  | H4 textbook |skew| cascade | 10/18 | 7/14 | 0.61 |
  Every failure is a near-tie. The mid-axis failures are rolling_luggage (skew -0.009) and step_ladder (-0.0005). The z
  failures are cyan_water_bottle (-0.008), light_blue_book (-0.0006), skateboard (-0.002) and toy_stroller (-0.012). All
  sit within 0.8 sampling SE at n = 1e4 points, so every scan with a clearly non-zero skew obeys "mid and max axes by
  positive skew, smallest axis completes right-handed". Track 3 re-read under the same rule: its 3 mid-axis (y)
  failures are also near-ties: blue_cup -0.0092, mini_dust_pan -0.0007, white_pot -0.0086. All 5 confident Track 3 y
  skews are positive: beige_cup 0.12, mini_sweeper 0.055, plastic_dish_rack 0.032, water_pitcher 0.58, wooden_piece_1 0.018.
  => [V for Track 2; H that Track 3 shares the rule] The organisers' sign rule is most likely note 07's "y-skew" form: z
  (largest) and the MIDDLE axis signed by positive third moment, computed with some noise (points sampled, or a
  different mesh version). Stage B could not see this in Track 3 alone because 5 of its 10 mid-axis skews are near-ties.
  This raises the weight on the spoon rule "y by skew_y", which gives frame B whenever the scan includes the markers.
- [V] Noisy-sign fit of "mid + max axes by positive skew, estimated from n points" (`scripts/c_noisy.py` -> `out/c_noisy.log`;
  P(bit) = Phi(s sqrt(n)/se1), log-uniform n in [1e2, 1e9], average LR vs random bits; degenerate axes excluded):
  Track 3 mid (8 bits, 6 +) avg LR 3.3, n ~ 5.6e3 [355, 3.5e4]; Track 2 mid (18 bits) LR 1.4e3, n ~ 7.9e3 [1e3, 4e4];
  Track 2 max (22 bits) LR 7.1e3, n ~ 1.8e3; joint Track 3 + Track 2 mid + max (57 bits, 49 +) LR 4.8e10, n ~ 5.6e3
  [1.6e3, 1.8e4] (10-90%). The two tracks' n posteriors overlap, so one noise level explains both. Contrast: the
  smallest axis by skew has LR 0.15 (Track 3) and 5e-18 (Track 2), so it is decisively not signed by skew; it is the
  completed axis.
- [V model] Spoon roll under this rule. Mechanism (a), exact axes with the skew sign from n points (`scripts/c_spoonP.py` ->
  `out/c_spoonP.log`, Stage B spoon MC shapes): P(B) averaged over the joint n posterior = 0.90 (round handle), 0.92 (oval),
  0.50 (no markers). By n: 0.73 at 1e3, 0.86 at 3e3, 0.96 at 1e4, 0.996 at 3e4 (round). Mechanism (b), PCA axes AND skew both
  from the same n-point sample (`scripts/c_spoonPb.py` -> `out/c_spoonPb_<mode>.log`, 12 shapes x 150 draws): round 0.71 / 0.81 /
  0.93 / 0.99 / 1.00 at n = 1e3 / 3e3 / 1e4 / 3e4 / 1e5; oval 0.76 / 0.88 / 0.98 / 1.00 / 1.00; no markers 0.40-0.52.
  P(z = bowl->handle) >= 0.9999 in every case. The fact that the near-tie Track 2 and 3 axes flip while the spoon's does not is
  consistent: the spoon's marker-induced skew_y (-0.035) is ~3-4x the failing near-ties (|s| <= 0.012).
- [E] Updated roll bet: P(rule = mid-axis skew) ~0.85-0.9 (Track 2 holdout plus the shared origin and z rules; [H] that
  Track 3 shares Track 2's pipeline), times P(B | rule, markers in scan) ~0.85-0.9, plus the Stage B rule mixture ~0.7 for the
  rest, times P(the organisers' spoon scan includes its markers) ~0.95 (10/10 Track 3 scans do), else 0.5:
  P(B) ~ 0.80-0.87 (was 0.6-0.9 after Stage B). Frame B stays the recommendation, now with a firmer basis.
- [V model] Expected CD-O and R1-frame stability of spoon reconstruction options (`scripts/c_cdo.py` -> `out/c_cdo_<seed>_m<0|1>.jsonl`,
  summary `scripts/c_cdo_sum.py` -> `out/c_cdo_sum.log`). The truth is a Stage B round-handle spoon with markers (60 shapes) or
  without (15). CD-O is the kit's own `_object_chamfer_cm`. The estimates are built in the same physical coordinates, so the
  frame deltas isolate shape effects. Truth WITH markers:
  | option (proxy) | CD-O cm mean (p90) | above floor | origin shift mm med / p90 | x-axis tilt deg med | skew sign agrees x / y / z |
  |---|---|---|---|---|---|
  | floor: same spoon, re-tessellated | 0.073 (0.075) | 0 | 0 | 0 | 1 / 1 / 1 |
  | T4 stereo/TSDF fusion, complete, 1.5 mm smooth noise | 0.108 (0.114) | +0.036 | 0.8 / 1.7 | 0.80 | 0.88 / 0.85 / 1.00 |
  | T1 template fitted (planform 2%, thickness 15%, bowl depth 30%, markers 2 mm) | 0.115 (0.137) | +0.042 | 2.9 / 5.7 | 0.64 | 0.85 / 1.00 / 1.00 |
  | T0 prior-mean template, no fitting | 0.128 (0.158) | +0.056 | 3.5 / 9.3 | 0.72 | 0.88 / 1.00 / 1.00 |
  | T3 visual hull (bowl concavity filled) | 0.129 (0.142) | +0.056 | 1.6 / 2.4 | 0.54 | 0.28 / 1.00 / 1.00 |
  | T1 fitted, markers omitted | 0.151 (0.172) | +0.078 | 6.8 / 10.3 | 0.65 | 0.82 / tie / 1.00 |
  | T5 right category, wrong instance (generative proxy) | 0.154 (0.187) | +0.081 | 5.1 / 10.3 | 1.06 | 0.83 / 1.00 / 1.00 |
  | T1 loose fit (5% / 30% / 50%, markers 5 mm) | 0.158 (0.210) | +0.085 | 6.6 / 15.1 | 0.80 | 0.67 / 1.00 / 1.00 |
  | T4 fusion with the bowl underside never seen (open) | 0.220 (0.241) | +0.148 | 21.2 / 22.6 | 0.90 | 0.92 / 0.90 / **0.15** |
  Truth WITHOUT markers: the marker penalty is mirrored (T1 with markers 0.150, without 0.111). So model the markers
  exactly when P(scan has markers) > 0.5, which holds here (~0.95).
  Readings: (1) Every complete spoon-shaped option lands within 0.04-0.09 cm of the 0.073 cm sampling floor. The spoon is
  10 of the 36 CD-O pairs, so the choice moves the board CD-O by <= 0.03 cm, and CD-O should NOT drive the method choice.
  (2) Gross failures dominate. A missing bowl underside costs +0.15 cm CD-O, shifts the origin by 21 mm and FLIPS THE Z
  SIGN in 85% of shapes (less bowl area moves the skew tail). That is the catastrophic 180 deg error of note 07 (~-0.48
  SP-SR on the board). Hand or table fragments would also inflate the scorer's radius normalisation. (3) Filling the bowl
  (visual hull) flips skew_x in 72% but keeps y and z, harmless under the mid-axis rule but fatal for an x-based rule.
  (4) Origin shifts of 3-7 mm and tilts <= 1 deg cost ~0 SR and <= 0.01 AUC (note 07 table). The markers are the largest
  single frame term (6.8 mm if omitted).
- [E] Roll-bit decision options (loss if wrong, note 07 upper bounds on the board: SP-SR -0.48, MP-SR -0.50 clean / -0.07
  with 1 cm / 5 deg tracking noise, MPPE +3.2-4.3 cm, AUC -0.07..-0.13; P(B) ~0.83 from above):
  | option | legality | cost | expected loss vs knowing the bit |
  |---|---|---|---|
  | 1. Commit to B (default) | clean | 0 | 0.17 x loss: ~0.08 SP-SR, 0.01-0.09 MP-SR, 0.6-0.7 cm MPPE, 0.01-0.02 AUC |
  | 2. Ask the organisers (v2d_challenge@nvidia.com or the forum) for the spoon frame or sign rule, plus whether Track 2 and 3 share it | clean, and fair to all teams (Track 3 publishes the other 10 scan frames, not the spoon's) | ~0; the answer may become public | removes the loss if answered (P(answer) ~0.3-0.6 [E]) |
  | 3. Two genuine pipeline variants (spoon frame A vs B), keep the one the board prefers | NOT forbidden by any text in the kit (`config/tracks.json`, READMEs; full Kaggle rule text not in the kit, unverified). But it is a deliberate 1-bit readout of confidential reference data, which this project's rules forbid ("no leaderboard probing"). Needs the user's decision and preferably written organiser approval | each variant is its own commit: frame flag -> asset/URDF -> references -> spoon policies retrained (observation is body-frame, see above) -> evaluator -> packer. ~20-40 GPU-h for the second set of 10 spoon policies at 1 seed (5-10 GPU-h if fine-tuned from the A policies [E]); 1-2 of the 5 weekly submissions; no CSV post-editing (it would break the checkpoint/evaluator provenance) | removes the loss (signal 3-4 cm MPPE on the board, far above seed noise) |
  | 4. 90 deg hedge | clean | 0 | dominated (note 07) |
  Recommendation: do 1 + 2 now. Do 3 only if the user decides to and the organisers confirm it is acceptable. Its value
  (~0.08 SP-SR, ~0.6 cm MPPE expected) is modest now that P(B) ~0.83, and it carries reputational and disqualification
  risk. One more GT-free check before committing: confirm on our own reconstructed spoon mesh (closed, markers modelled)
  that the mid-axis skew points to M2 with |skew_y| >= 0.02 and that z runs bowl -> handle.
- Reconstruction options compared ([E] unless marked; literature and licences per note 03, not re-reviewed here):
  1. Stereo fusion along tracked poses (ego_cam_b/c 75 mm baseline; TSDF/2DGS; FoundationStereo-class matcher, licence
     caveat in note 03). Pale, textureless wood gives few matches inside the silhouette, only on edges and markers.
     Depth error ~4 mm per 0.5 px at 0.55 m. The bowl's convex back is seen only during the in-air phases of 35/36 (and
     briefly in 3/15/16 lifts). Proxy T4: complete gives CD-O 0.108 and origin 0.8 mm; never-seen underside gives 0.22 cm,
     21 mm and a z flip. Use it as a MEASUREMENT for the template fit (surface heights, bowl depth, handle section),
     not as the canonicalised asset.
  2. Generative completion (SAM 3D Objects / TRELLIS.2 / Hunyuan3D, note 03): complete and closed, but scale-free, shape
     hallucinated, markers usually absent or blobby, and the thin bowl shell is unreliable. Proxy T5 (right category,
     wrong instance): CD-O 0.154 and origin 5 mm (p90 10 mm). Useful as a prior for planform/profile or as a sanity check,
     after Sim(3) registration to the markers.
  3. Parametric template (lofted bowl shell + neck + round handle + 3 sphere-on-base markers; `work/13/scripts/c_cdo.py`
     `body()` / `spoon()`), fitted automatically. Planform from the 10 frame-0 top views (flat, concave-up, untouched in
     10/10; undistort, table-plane homography from stereo). Marker stations from stereo triangulation at rest (35-37 f0,
     averaged over the static prefix). Handle section and bowl depth from stereo heights at rest (marker centres above the
     table: M3 ~ handle radius, M1/M2 ~ rim height) and edge-on held views. Proxy T1: CD-O 0.115, origin 2.9 mm (p90 5.7),
     tilt 0.6 deg, mid-axis skew sign right in 100%. Closed and clean by construction, best frame stability, gives the
     tracker's marker model, and makes a straightforward sim collision asset (convex pieces). RECOMMENDED as the single
     spoon mesh for all 10 episodes, for CD-O, sim and frame. Stage A's hand measurements may serve only as priors and
     checks. Fitted values must come from the automatic pipeline (no per-episode hand labels).
  Checks before use [H]: the kit packer's quadric decimation to 4,096 faces must not collapse the 3.5-6 mm bowl shell or
  the marker bases (`fast_simplification` is not in our venv; run `tools/pack_reconstruction.py` on the mesh once). The
  area ratio against a smoothed copy should be ~1 (note 07). Compute R1 plus the mid-axis skew sign on the final mesh.
- Thin-object tracking mitigations (beyond the marker triangle quantified above) [H unless marked]:
  (a) Triangulate markers in a+b+c (halves roll error vs b+c, [V model]) with sub-pixel sphere-centre fits on the black base
  plus grey sphere. Weight by blur (handle-edge blur 5-20 px in fast moves, Stage A). (b) Marker identity from the distinct
  inter-marker distances (model: M1-M2 ~55 mm, M2-M3 ~152 mm, M1-M3 ~192 mm), gated by the spoon mask, because the pot, cup
  and rack also carry markers. (c) With <= 2 markers, take the long axis from line fits to the handle edges in 2-3 views, and
  roll from the visible side marker plus concave/convex bowl shading, or from the grasping hand's fist axis (hand
  estimator). (d) Offline bidirectional SE(3) smoothing with a robust loss: penalise 180 deg roll jumps, lock static
  segments (start and end rest, in-cup rest in 15/16), and give rests 3 DoF (x, y, yaw on the table, concave-up).
  (e) Collision-aware projection against the table and OUR reconstruction of the slot-0 object: pot walls (3/5/6),
  utensil-cup cylinder (15/16: handle inside the cup), tipped blue cup (32/33). (f) Score note: MPPE's +-5 cm keypoints make
  roll errors cost more than ADD does. A 10 deg roll error moves the four x/y keypoints by 0.87 cm each (~0.58 cm MPPE),
  while ADD over the thin spoon moves ~0.3 cm. So roll smoothing pays mainly on MPPE and on the 30 deg MP-SR gate.

### Stage C summary (2026-10-05)
1. [V code] CD-O = Sim(3)-normalised (surface radius of gyration) + 25-start trimmed ICP + 10k-sample symmetric Chamfer,
   after decimation to <= 4,096 faces. It is blind to scale, pose, frame and roll. The spoon is 10 of 36 pairs.
2. [V data] The Track 2 public scans (29) share the area-centroid origin and support "largest and middle axes by positive skew,
   noisy (n ~ 5.6e3), smallest axis completed". Pre-registered tests on the unseen scans: mid 12/14 (P = 0.006), z 13/16
   (P = 0.011); Stage B's 16 survivors and the textbook cascade do not transfer (P 0.03-0.61; best single rule 11/14, not significant after 17 tests); the min axis is a coin
   flip. All failures in both tracks are near-ties (|skew| <= 0.012).
3. [V model + E] Under that rule the spoon is frame B (+z bowl->handle, +y toward M2, +x out of the concave face) with P
   0.85-0.92 given markers in the scan. Overall P(B) ~0.80-0.87. Without markers in the organisers' scan it is 50/50.
4. [V model] Reconstruction: complete spoon-shaped meshes all score CD-O 0.11-0.16 cm (floor 0.073). A fitted parametric
   template with markers gives the best frame stability (origin ~3 mm, tilt ~0.6 deg, mid-axis sign right). Partial fusion
   (no bowl underside) flips z in 85% and must never be canonicalised. Model the markers (they are ~7 mm of origin).
5. [V model] Tracking: the stereo marker triangle is accurate in tilt (~1 deg) and weak in roll (median 2.5-6 deg at 0.5 px,
   10 deg at 2 px blur). Adding the colour camera halves it. Mitigations (a)-(f) above.
6. [E] Decision: commit to B, ask the organisers. A two-variant board A/B is a legal grey zone and a probe by this project's
   rules; it costs a second spoon-policy set (~20-40 GPU-h, or 5-10 fine-tuned) and 1-2 weekly submissions for ~0.08 SP-SR /
   ~0.6 cm MPPE expected value. It is not recommended without user and organiser approval.
Open items / falsifiers: (a) the organisers' answer (settles everything); (b) whether the confidential spoon scan includes
the markers; (c) the M1/M2 z order and the handle section from automatic stereo at rest (35-37 f0) on our own fitted mesh,
where skew_y must point to M2 with |skew_y| >= 0.02; (d) whether Track 3 really shares Track 2's sign step (Track 3 axes
are exact PCA of the published mesh, Track 2 axes are 0.2-1 deg off, so the sign step may have run on another mesh
version); (e) whether the 4,096-face decimation keeps the bowl shell; (f) the principal-point frame of the delivered
(upright) videos, which is still open from Stage A.
Stage C status: COMPLETE (2026-10-05). Scripts `work/13/scripts/c_*.py`; outputs `work/13/out/c_*`; Track 2 geometry
`work/13/t2/*.npz` (29 scans, ~124 MB fetched by HTTP range, positions + indices only).

## Stage B re-run (workflow retry, 2026-10-06)
- Resume marker. Stage B (above) and Stage C were already COMPLETE on 2026-10-05; all their scripts and outputs are intact
  (`work/13/scripts/b_*.py`, `out/b_*`). This retry (a) re-checks that the Stage B numbers reproduce, (b) fills gaps in the
  rule families the brief names (kurtosis- and extreme/bbox-ordered 3-axis cascades with right-hand completion, z not
  pre-fixed; tie-break cascades), and (c) re-derives the spoon roll per surviving rule on spoon shapes conditioned on the
  Stage A measurements. New scripts `work/13/scripts/b2_*.py`, outputs `work/13/out/b2_*`.
- [V] Reproduction with the reused `scripts-prev/meshframe/canon.py` (`scripts/b2_canon_check.py` -> `out/b2_canon_check.log`):
  on all 10 public visual scans, canon's origin lies at the published origin (|c| < 1e-4 mm), its exact third moments match
  `out/b_feats.json` to <= 6e-9, and its x/y rules reproduce the published roll in skew_x 7/10, skew_y 7/10, hybrid(0.02)
  9/10 (fails wooden_piece_2). The Stage B catalogue therefore rests on the same R1 frame as note 07.
- [V] Gap-filling families, all THREE bits required, z not pre-fixed (`scripts/b2_cascades.py` -> `out/b2_cascades.log`; 26
  odd statistics, both polarities): G1 kurtosis-ordered cascade (top-2 axes by kurt high/low or |kurt| high/low signed, third
  completed right-handed) 0/208 fit, best 7/10; G2 variance-ordered fixed pair (xy, xz or yz signed by one statistic, third
  completed) 0/156, best 8/10; G2m z by s1 then x or y by s2, third completed, 0/5,408, best 9/10 (z by skew/ssq/q10 with y by
  far3d fails water_pitcher, with y by vertex skew fails white_pot); G7 per-axis majority of 7 moment/extreme statistics
  (skew, m5, ssq, s4, -median, q10, bbox centre), top-2 by |skew| completed: 9/10, fails wooden_piece_2 (confident skew_x
  -0.54); fixed y,z or x,z pairs 5-8/10. Null (1,000 random roll configurations): P(>=1 fit) G1 0.000, G2 0.004, G2m 0.054,
  G7 0.000. So no new family member reproduces all 10 published frames; together with Stage B's F1/F2/F2b/F4/F3 (16
  parameter-free survivors, all through near-ties) the deterministic catalogue is exhausted without a robust survivor.
- [V model] Spoon roll under the new near-survivors (`scripts/b2_spoon_new.py` -> `out/b2_spoon_new.log`, the 550 stored Stage B
  spoon MC shapes; round+markers / oval+markers / round no markers): G7 majority-of-7 top-2 cascade gives B in 296/300, 110/150,
  96/100 and keeps z bowl->handle in 550/550. G2m "z by skew, y by far3d" gives A in 300/300 and 150/150 but 49/51 without
  markers: far3d is the M3 cap, whose model y-offset is exactly 0, so the A call is a model artefact; on the real spoon it is
  set by sub-mm marker mounting, a coin flip (as for far3d in Stage B). Vertex-skew rules depend on the organisers'
  tessellation and cannot be evaluated on our mesh.
- [V data, H interpretation] Physical rest-pose rule (`scripts/b2_restup.py` -> `out/b2_restup.log`, public GT, first and last
  frame of the 20 public episodes, world up expressed in the published body frame). Objects whose thin axis x is vertical at
  rest: mini_dust_pan x+ up 6/6, plastic_dish_rack x+ 10/10, white_pot x+ 15/18, white_pot_lid x+ 4/4, wooden_piece_1 x+ or
  y+ (2/2 each, a diagonal rest), wooden_piece_2 x- or y- (2/2 each). Cups and pitcher rest with z or y vertical. So "the
  thin axis points up when the object rests naturally" holds for 5 of 6 flat objects and fails on wooden_piece_2. That is
  the same scan, failing the same way, as skew_x > 0. On flat objects the two are CONFOUNDED (resting face down puts the
  surface tail upward), so the GT adds no independent evidence. If it were the rule, the spoon (resting concave-up in 10/10
  eval clips) would be frame B, like the moment rules that are not near-ties.
- [V] Reproduction: `scripts/b_search.py` rerun today gives a log identical to `out/b_search.log` (F1 0/112, F2 15/1,624,
  F2b 1/1,404, F4 0/224, F3 154 shapes). Union of every parameter-free family, Stage B plus retry (`scripts/b2_union.py` ->
  `out/b2_union.log`; 9,139 rules): 16 fit 10/10 (the Stage B ones; none new). LOO share per held-out scan 0.53 / 0.84 / 0.94 /
  1 / 1 / 0.73 / 0.64 / 1 / 0.28 / 0.09 (beige_cup ... wooden_piece_2), mean 0.705. Holding out wooden_piece_2 leaves 181 rules
  that fit the other 9, and only 9% of them predict its bit. Null (1,000 random roll configurations): P(>=1 rule fits) =
  0.283, null LOO mean 0.238, P(LOO >= 0.705) = 0.206. Not significant, as in Stage B. P(#fitting >= 16) = 0.031, but the 16 are
  near-duplicates (15 share one axis choice), so the count overstates the evidence.
- [V] Mesh-version check (`out/b2_collision.log`): if the features of the 3 public collision meshes (mini_sweeper,
  wooden_piece_1, wooden_piece_2) replace the visual-mesh features, all 15 F2 survivors still fit 10/10, and the F2b survivor
  drops to 9/10 (fails wooden_piece_1). The collision meshes give clear positive mid-axis skews, y = +0.075 / +0.049 / +0.047
  (visual +0.055 / +0.018 / +0.004). This agrees with the Stage C "mid axis by positive skew" reading: the visual-mesh near-ties
  get a clear margin on another mesh version of the same object. [H] that the organisers signed on a mesh version other than
  the published visual GLB.
- [V model] Spoon shapes need no re-conditioning: the Stage B MC priors already bracket every Stage A measurement (length
  28-31 cm vs ~30 +-7%; bowl 8.5-10 x 4.8-5.6 cm vs 9-10 x 5.2; handle end width 1.9-2.4 cm; M1 10.4-12.4 cm from the tip vs
  11.4; M2 3-5 cm above M1 vs 4.1). The unmeasured terms that matter are the handle thickness/width ratio and the bowl depth.

### Stage B retry summary (2026-10-06)
1. [V] The Stage B results of 2026-10-05 reproduce: the reused `canon.py` matches the catalogue's moments to <= 6e-9 and the
   published origin exactly, and `b_search.py` gives an identical log.
2. [V] The families the brief names that Stage B had not covered all fail to reproduce the 10 published frames: kurtosis-ordered
   3-axis cascades (best 7/10), variance-ordered fixed pairs (8/10), two-statistic z-then-roll pairs (9/10, 0/5,408 at 10/10),
   and a majority-of-7 cascade (9/10, fails wooden_piece_2). Over all 9,139 parameter-free rules, only Stage B's 16 survive.
   Every one of them fits at least one scan by a near-tie. The 16 fits, the LOO share 0.705 (null P = 0.21) and P(>=1 fit by
   chance) = 0.28 show no significant deterministic roll rule.
3. [V model] Spoon roll per rule, unchanged: every surviving or near-surviving rule that is not a coin flip on the real spoon
   gives frame B for a ~2 cm round handle with markers (15 F2: P(A) 0.00-0.06; F2b 0.03; G7 0.01; skew_y 0.00; q10_y 0.02). The
   exceptions are far3d-based rules, set by sub-mm M3 mounting (uninformative), and F2|absmax without markers (0.52). An oval
   handle with a deep bowl moves x-based rules toward A (P(A) up to 0.39), but not the y-based rules while the markers are in the scan.
4. [V data, H] A physical "thin axis up at natural rest" rule fits 5 of 6 flat public objects. It fails on wooden_piece_2 and
   is confounded with skew_x > 0. It would also give B (the spoon rests concave-up in 10/10 eval clips).
5. [E] The roll bet is unchanged from Stage C: P(B) ~0.80-0.87, driven by the Track 2 holdout for the mid-axis skew rule, not by
   any Track 3-only rule. Recommendation unchanged: build the closed spoon template with markers, check skew_y -> M2
   (|skew_y| >= 0.02) and skew_z bowl -> handle on it, commit to frame B, and ask the organisers.
Stage B retry status: COMPLETE (2026-10-06). New scripts `work/13/scripts/b2_{canon_check,cascades,restup,spoon_new,union}.py`;
outputs `work/13/out/b2_*.log`.

## Stage C re-run (workflow retry, 2026-10-06)
- Resume marker. Stage C was COMPLETE on 2026-10-05 (section above). This retry (a) re-checks that the Stage C numbers
  reproduce, (b) fills open items: the scorer's slot-0 alignment and what a wrong roll bit costs per slot role, the 4,096-face
  decimation of a thin template, and (c) rewrites the final summary. New scripts `work/13/scripts/c2_*.py`, outputs
  `work/13/out/c2_*`.
- [V] Reproduction (2026-10-06): reruns of `c_cdo_sum.py`, `c_track.py`, `c_noisy.py` (incl. `c_noisy_post.npy`) and `c_spoonP.py`
  give output byte-identical to the stored `out/c_*.log`. `c_t2rules.py` matches too, except for the 29 per-scan feature lines,
  which are printed only on the first, uncached run. The Stage C tables above stand as written.
- [V code] Slot-0 warp re-read in the scorer (`kit/.../metric_code/track_3/AUC.py` `_warp_to_reference_start`, lines ~113-127; the same
  in all 5 pose metrics): q_align = q_ref(slot 0, f0) * conj(q_ours(slot 0, f0)), applied with its offset to EVERY body and frame.
  That is exactly the mechanism note 07 section 5 models (slot >= 1: constant body-frame error; slot 0: error 0 at t=0, then a 180 deg
  roll error rotates the whole predicted path about the frame-0 long axis, so a lifted spoon is placed below the table; 20.5 cm MPPE
  on moving hosts). Note 07's per-role loss table is therefore reused here unchanged rather than recomputed.
- [V, cross-reference] Open item (f) is CLOSED by other digs: note 15 (Progress 2 and section 11, `work/15/rectcheck2.py`,
  `work/15-verify/epi_bc.py`) and note 11 section 13.2 (`s33_kcheck.py`) show that `camera_calibration.json` AS GIVEN (left =
  ego_cam_c, right = ego_cam_b, K and D unchanged, no extra 180 deg flip) describes the stored upright frames. b<->c median
  epipolar error is 1.2-2.6 px, against 5.5-28 px for flipped or conjugated variants. ego_cam_a's `extrinsics_to_stereo_left`
  targets ego_cam_b (the raw device left), not ego_cam_c. Consequence for the spoon tracker: triangulate with the file as given.
  The measured 1-2.6 px epipolar residual is 2-5x the 0.5 px assumed in the c_track table. So the b+c rows at 1.0-2.0 px are the
  realistic ones (roll median 5-10 deg) unless a per-recording refinement of the stereo rotation brings it down [H].
- [V doc] Rule sources re-checked (2026-10-06) for the roll-bit A/B question: kit `README.md` and `LEADERBOARDS.md`, the public
  challenge page and its FAQ PDF (`nvidia-isaac.github.io/video_to_data/v2d_challenge/assets/v2d_challenge_2026_faqs.pdf`,
  3 pages, read via the fetch tool's local cache). Facts: (1) each Track 3 metric is its own Kaggle competition (track3-auc,
  -sp-sr, -mp-sr, -rpe, -mppe, -cd-o), and the uploader sends one packed file to all six, so one variant costs one submission
  across all six boards; (2) "five submissions per week" applies per track and tier, unlimited in the final 3 days (page); (3)
  every submission carries a git commit URL plus evaluator and submission hashes, and top solutions must reproduce their results
  and release code under Apache 2.0; (4) "participants should submit their own reconstructed meshes" even where public meshes
  exist; (5) pretrained models and external data are allowed; (6) questions go to v2d_challenge@nvidia.com or the Discord. None of
  these sources mentions object frame conventions, leaderboard probing, test-set tuning or final-submission selection. The
  per-competition Kaggle rule pages are not in the kit and were not fetched (they need a login). So the two-variant A/B stays
  NOT FORBIDDEN BY ANY TEXT SEEN, and it still conflicts with this project's own "no leaderboard probing" rule.
- [V model] Temporal smoothing of the marker tracker (`scripts/c2_smooth.py` -> `out/c2_smooth.log`). Model: 60 smooth random
  trajectories x 200 frames at 20 fps; angular speed RMS 60 or 180 deg/s, translation RMS 0.2 m/s within 0.35-0.7 m; c_track
  geometry; iid 2-D marker-centre noise sigma; per-frame triangulation; then raw Kabsch vs Kabsch on Savitzky-Golay (quadratic)
  smoothed 3-D marker tracks over 5 / 9 / 15 frames. Pooled frames:
  | cams, sigma (60 deg/s) | raw roll med / p90 | SG9 roll med / p90 | SG15 roll med / p90 | frames > 30 deg raw / SG9 / SG15 | MPPE med raw / SG9 cm |
  |---|---|---|---|---|---|
  | b+c, 1.0 px | 4.9 / 21.6 | 2.5 / 11.1 | 1.9 / 8.5 | 5.4% / 0.7% / 0.2% | 0.66 / 0.34 |
  | b+c, 2.0 px | 10.3 / 49.2 | 5.0 / 23.1 | 4.0 / 17.3 | 20.7% / 6.5% / 3.4% | 1.40 / 0.70 |
  | b+c, 2.6 px | 13.4 / 59.2 | 6.9 / 30.9 | 5.4 / 24.2 | 28.7% / 10.9% / 6.5% | 1.80 / 0.92 |
  | a+b+c, 1.0 px | 2.7 / 11.5 | 1.4 / 5.9 | 1.1 / 4.6 | 0.7% / 0% / 0% | 0.37 / 0.20 |
  | a+b+c, 2.0 px | 4.8 / 23.0 | 2.4 / 11.6 | 1.9 / 8.9 | 6.5% / 1.1% / 0.3% | 0.71 / 0.37 |
  At 180 deg/s the numbers are within ~10%, except that a 15-frame window starts to lag (a+b+c 1 px: rotation median 1.8 at SG9
  vs 2.2 at SG15). Reading: a 9-frame (0.45 s) quadratic window halves roll error and cuts the share of frames over the 30 deg
  gate 3-7x, and adding the colour camera halves it again. With both, marker-only tracking stays under the 30 deg gate on ~99% of
  frames at 2 px. Limits [E]: iid noise only. A systematic stereo-calibration error (the 1-2.6 px epipolar residual of notes 11/15
  may be partly systematic) does NOT average out. There are no outliers, marker swaps or occlusions in this model; those need
  the robust gating of mitigation (b)-(d). Smoothing the reference also makes it easier for the policy to track (note 14) [H].
- [V code] Mesh budget (`kit/v2dlb/mesh_budget.py`): the packer welds vertices and calls `fast_simplification` ONLY if the welded
  mesh has more than 4,096 faces; the budget is 4,096 faces and 4,096 vertices (`config/tracks.json`), padded with zero-area faces.
  So a template generated natively under budget skips decimation on our side entirely. The organisers' reference spoon IS
  decimated (the docstring claims <= 0.83 mm mean surface deviation for every pseudo-GT object, measured 2026-09-22).
  `fast_simplification` is not in our venv and was not installed (no downloads), so the reference-side decimation is not reproduced.
- [V model] Native-budget template (`scripts/c2_budget.py` -> `out/c2_budget_7.jsonl`, summary `scripts/c2_budget_sum.py` ->
  `out/c2_budget_sum.log`; 30 Stage C round+markers shapes, T1 fitted template). Body loft 64 x 24 plus 8-ring spheres and 12-gon
  bases gives 3,324-3,648 faces and <= 1,992 vertices, against ~33.7k faces at full resolution.
  | comparison | CD-O cm mean (p90) | origin shift mm med / max | axis change deg max | skew signs kept x / y / z |
  |---|---|---|---|---|
  | truth at budget vs truth full-res (tessellation floor) | 0.077 (0.080) | 0.18 / 0.58 | 0.03 | 1 / 1 / 1 |
  | our T1 fit full-res vs truth | 0.107 (0.127) | - | - | - |
  | our T1 fit AT BUDGET vs truth | 0.107 (0.126) | 3.1 / 8.2 (fit error, as in Stage C) | 1.9 (x, z) | 0.93 / 1 / 1 |
  | our fit at budget vs our fit full-res | - | 0.20 / 0.65 | 0.03 | 1 / 1 / 1 (min abs skew_y 0.023) |
  Reading: the 4,096-face budget costs our template nothing (CD-O +0.0005 cm, origin 0.2 mm, skew signs unchanged). Ship the
  spoon mesh natively under 4,096 faces and 4,096 vertices, and canonicalise the same mesh that is submitted and used as the sim
  asset. Then the packer cannot alter it, and the CD-O row, the sim asset and the frame all come from one file. In this sample the
  true skew_y (along M1) is -0.051 to -0.022 in 30/30, and the fitted template keeps its sign with abs >= 0.023: frame B again.
- [V data] No public spoon asset can settle the bit. HF dataset tree via the API (2026-10-06): `track_1/` has meta, data and videos
  but no mesh folder (73 paths). `track_2/` mesh folders hold the 29 scans already used (baseball_bat ... woven_basket), none
  spoon-, ladle- or utensil-like. Track 3 public has the 10 scans of Stage B. The only legitimate ways to learn the spoon bit
  remain the organisers' answer or the board.
- [E] Value of the A/B, restated with the retry facts. P(B) ~0.83, so committing to B costs in expectation 0.17 x note 07's
  noisy-tracking board deltas (SP-SR -0.477, MP-SR -0.073, MPPE +3.20 cm, AUC -0.072): ~0.081 SP-SR, ~0.012 MP-SR, ~0.54 cm MPPE,
  ~0.012 AUC. If the organisers answer (P ~0.3-0.6 [E]) that drops to 0. Costs of the A/B: 2 of the 5 weekly Track 3 submissions
  (one per variant, each covering all six boards), a second set of 10 spoon policies (~20-40 GPU-h, or ~5-10 fine-tuned from the
  first), two complete commit-and-hash provenance chains, and conflict with this project's no-probing rule. The board signal
  would be unambiguous (3-4 cm MPPE and ~0.5 SP-SR, far above seed noise), so one pair of submissions would suffice. If the user
  ever authorises it, run it in the LAST 3 DAYS (unlimited submissions) so it uses no weekly slots. Recommendation unchanged:
  commit to B and email v2d_challenge@nvidia.com or ask on the Discord now.

### Stage C retry summary (2026-10-06)
1. [V] Every Stage C output that can be regenerated reproduces byte-identically (`c_cdo_sum`, `c_track`, `c_noisy`, `c_spoonP`,
   `c_t2rules`). The Track 2 holdout, P(B) and the CD-O and tracker tables stand.
2. [V code] The scorer's single slot-0, frame-0 warp is as modelled in note 07. A wrong roll bit costs most in 35-37 (spoon in slot 0).
3. [V code + model] The packer decimates only above 4,096 faces. A spoon template emitted natively at ~3.5k faces loses nothing:
   CD-O +0.0005 cm, origin 0.2 mm, axes 0.03 deg, skew signs unchanged, |skew_y| >= 0.023 toward M1 (frame B).
4. [V cross-ref] The principal-point question (former open item f) is closed by notes 11 and 15: use the calibration as given.
   Its 1.2-2.6 px epipolar residual sets the realistic marker noise.
5. [V model] Savitzky-Golay smoothing of the triangulated markers over 9 frames halves roll error. a+b+c at 2 px keeps ~99% of
   frames under the 30 deg gate (iid noise only).
6. [V doc] The kit, the challenge page and the FAQ do not address frames, probing or final selection. The six Track 3 boards
   receive one packed file per submission; the cap is 5 per week per track, unlimited in the final 3 days. Code must be
   reproducible (commit plus hashes).
   [V data] No public spoon asset exists in Tracks 1-2.
7. [E] Decision unchanged: frame B (P ~0.80-0.87); ask the organisers now. The A/B is worth ~0.08 SP-SR / ~0.5 cm MPPE in
   expectation. It conflicts with this project's no-probing rule and needs the user's decision plus organiser approval; if
   authorised, run it in the final 3 days.
Stage C retry status: COMPLETE (2026-10-06). New scripts `work/13/scripts/c2_budget.py`, `c2_budget_sum.py`, `c2_smooth.py`; outputs
`work/13/out/c2_budget_7.{jsonl,log}`, `c2_budget_sum.log`, `c2_smooth.log` (smoke-test file `c2_budget_991.jsonl`, 2 shapes, is
excluded from the summary).


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 12](12-symmetry-observability.md) · [14 →](14-policy-tracking-error.md)
