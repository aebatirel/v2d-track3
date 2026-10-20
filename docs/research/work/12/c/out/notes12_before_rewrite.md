# 12 — Spin observability of near-symmetric objects (cups, lid, pot, pitcher)

Status: Stage A (scan-only self-similarity) and Stage B (video appearance, pixel budget) complete 2026-10-05; stage C pending. Agent 12. Work dir `/Users/aebatirel/Documents/Code/v2d-research/work/12/`.
Tags: [V] verified here, [E] estimate, [H] hypothesis.

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
  false blob: still 22-31 of 40 prior draws flip to the -131 deg branch, with or without the missing-marker term
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
