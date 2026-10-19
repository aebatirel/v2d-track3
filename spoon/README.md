# wooden_spoon: parametric template, R1 frame check, fitting skeleton

Status: COMPLETE (2026-10-13). This is a CPU build. No downloads or installs were made, and no ground-truth poses were
used. Tags: [V] verified here, [E] estimate, [H] hypothesis.

Sources: note 13 ("Final summary" items 1-7, Stages A/B/C), note 07, note 17 (marker catalogue) and note 20 (Stage B and
re-run: automatic stereo measurement of the marker layout and the handle). The prior scripts are
`scripts-prev/meshframe/canon.py` and `work/13/scripts/{spoon_model,c_cdo,c2_budget}.py`; their spoon models were not
watertight (overlapping parts, open marker caps).

## Bottom line
1. [V] **Asset.** `wooden_spoon.glb` / `.obj` is one closed surface with outward orientation. It is edge- and
   vertex-manifold, genus 0, a single component, with no self-intersections and no duplicate faces. It has **3,224 faces
   and 1,614 vertices**, natively under the 4,096 / 4,096 budget, so the kit packer only welds (unchanged) and pads; it does
   not decimate. The 3 marker spheres sit on black stems and are UNIONED into the body (no interior faces). The mesh is
   expressed in the R1 canonical frame (re-applying R1 to the exported file gives origin 1.5e-7 mm and axes 1.5e-6 deg).
2. [V] **Frame check: rule R1 gives frame A, not B, on this template. It is a near-tie, and it was not forced.**
   - +z runs bowl -> handle end.
   - +y points toward **M1**: skew toward M2 = **-0.0038**.
   - +x points out of the **convex** back: skew toward the concave face = -0.030.
   - skew_z = +0.226.
   - |skew_y| = 0.0038 is far below the >= 0.02 that note 13 item 7 asked for. It is of the same size as the public
     near-ties the organisers' signs did not follow (blue_cup -0.0092, white_pot -0.0087, mini_dust_pan -0.0007).
   - Under the noisy mid-axis rule (note 13 Stage C, n posterior median 5.6e3), P(B) = 0.43.
3. [V model] **Parameter uncertainty does not settle it.**
   - `frame_mc.py` (N=1000 draws within the note 13/20 brackets, 992 built) gives P(skew_y toward M2) = **0.40**, mean
     noisy P(B) = 0.45, and x-rule B = 0.36. z is bowl -> handle in 100% (min skew_z +0.14).
   - What drives skew_y (regression, R2 0.84):
     - -0.0115 per mm of M1-vs-M2 lateral asymmetry
     - -0.0039 per mm of bowl bend toward M1
     - -0.0022 per mm of M1 height
     - +0.0022 per mm of M2 height
   - This reproduces note 20's conclusion (P(B | mid-axis) ~0.34-0.47) on an independent, watertight geometry. It
     **contradicts** note 13's "commit to B" (P 0.80-0.87), which assumed in-plane M1/M2 and an on-axis M3. That layout
     gives skew_y +0.049 here (B, P 0.96), but note 20 measured it to be wrong.
4. [V] **The R1 implementation reproduces the 10 public frames.**
   - Origin <= 6e-7 mm; axis order 10/10 (angles <= 2.4e-6 deg); z sign 10/10.
   - The mid-axis sign rule gives identity on 7/10. The exceptions are exactly the 3 known y near-ties (blue_cup,
     mini_dust_pan, white_pot), which come back y- and x-flipped. The x-skew rule is also 7/10 (fails beige_cup,
     water_pitcher, wooden_piece_2).
   - The URDF inertia formula reproduces all 10 public URDFs to 6e-9 relative.

**Recommendation [E]:** the spoon roll bit is still an organiser question. Ask v2d_challenge@nvidia.com, as notes 13 and
20 say, and do not treat B as confident. If the bit must be chosen without an answer, it is close to a coin flip leaning
A (~0.55-0.60). The fitted template (`fit_spoon.py`) can sharpen this only through the bend and the M1/M2 asymmetry.

## Files
| file | what |
|---|---|
| `spoon_template.py` | Generator plus checks plus R1. Writes the GLB, OBJ, URDF and `params.json`. `--variants` adds the sensitivity table; `--params my.json` overrides parameters; `--frame B` forces B (not used; reported). |
| `wooden_spoon.glb` | Canonical frame, metres. Layout mirrors the public scans: node `world` -> `wooden_spoon`, no transforms, one primitive, POSITION + TEXCOORD_0, PBR material `_texture` (metallic 0, roughness 1, double-sided) with a 48x16 PNG atlas (wood / black / grey). trimesh loads it as `kind='texture'`, as FoundationPose expects for the public objects. |
| `wooden_spoon.obj` | Same geometry and vertex order. Vertex colours in `v x y z r g b`; no MTL. |
| `wooden_spoon_rigid.urdf` | Mirrors `blue_cup_rigid.urdf`: 0.3 kg placeholder; inertial origin 0; uniform triangle-surface inertia about the surface centroid, ixx 2.5954e-3, iyy 2.5730e-3, izz 4.555e-5 kg m2, products 0 (PCA frame); mesh `../mesh/wooden_spoon/wooden_spoon.glb` for both visual and collision. |
| `params.json` | All parameters and the resolved values (length, marker WLS), marker centres (construction and canonical), the construction -> canonical transform, the frame report (both rules, skews, noisy P(B)), mesh checks, dimensions, GLB structure, URDF inertial and the variants table. |
| `verify_rule_public.py` -> `public_frame_check.json` | R1 on the 10 public scans plus the URDF-inertia reproduction. |
| `frame_mc.py` -> `frame_mc.json` | Parameter-uncertainty Monte Carlo of the frame bits (~1 min for N=1000). |
| `fit_spoon.py` | SKELETON, not run. Documented Colab-GPU fit of the continuous parameters to rest-pose stereo (mask + depth + triangulated markers), with a bootstrap -> skew_y posterior. |
| `preview_views.png`, `preview_markers.png` | Renders of the final mesh (top = concave face with M1 up and M2 down, matching the video chirality of note 13 Stage A). |

Regenerate: `venv/bin/python spoon_template.py --variants && venv/bin/python verify_rule_public.py && venv/bin/python
frame_mc.py 1000 1`. The whole run takes about 1.5 min on CPU and needs numpy, scipy, trimesh, pygltflib and PIL (all in
`v2d-research/venv`). Output is deterministic.

## Construction (frame C, metres)
z_C runs along the straight handle axis from the bowl tip (z = 0) to the handle end. x_C points out of the concave face
(up at rest). y_C = z_C x x_C points toward M2. **Frame B = (x_C, y_C, z_C)** up to the small tilts below.
- **Body.** A loft of 55 stations x 24 section points, plus tip and end poles.
  - Each section is a rounded-stadium offset of a dished midline. The bowl is a 5 mm shell with a half-round rim. The neck
    and handle are round.
  - The bowl planform is a skewed ellipse, smooth-maxed into the neck. The dish is a paraboloid whose footprint equals the
    planform, faded where the section has no flat midline.
  - The bend and pitch are a C1 shear about the pivot station.
  - The handle diameter follows a quadratic bulge with a hemispherical end.
  - The loft functions use elementwise ops only, so they also accept `xp=torch` (untested; torch is not installed here).
- **Markers.**
  - Each marker is a sphere of radius 7.2 mm whose centre sits 0.82 r above the stem/sphere junction. The stem is a
    frustum from radius 5.5 mm (on the body) to 4.1 mm (junction), along the normal from the nearest body point.
  - Union by stitching: a hole is cut as whole loft quads in (station, column) space, with 1 cell of margin around the
    cells hit by the projected foot ring. Near the end pole the hole is a polar cap plus a tongue, smallest first. The
    foot ring is zipped to the hole boundary by angle about the stem axis. If the boundary is not a clean star-shaped
    loop, the hole is grown, then the foot is narrowed (to >= the junction radius).
  - Robustness [V]: 52/52 builds pass every check (4 resolutions from 0.6x to 4x faces, by 13 parameter sets). Failures
    raise an error; they never emit a bad mesh.
- **Marker layout ('note20').** Weighted least squares of 9 coordinates against the note 20 measurements and the
  measured triangle (chi2 0.42 for 3 extra constraints). Values in mm, relative to the handle axis:

  | marker | station | lateral | up (toward concave) |
  |---|---|---|---|
  | M1 | 121.0 +- 2.2 | 18.85 +- 0.6, toward -y | 6.0 +- 1.5 |
  | M2 | M1 + 40.9 | 15.43 +- 0.8, toward +y | 9.9 +- 2 |
  | M3 | 314.5 +- 2.2 | 1.86, toward M2 | 11.0 +- 1.5 |

  The resulting triangle is 53.5 / 153.2 / 194.6 mm (measured 53.0 +- 1.6 / 153.2 +- 0.6 / 194.2 +- 1.5).
- **Total length (`auto`).** M3 sits at the public-scan mount height (sphere centre 10.9 mm above the host surface)
  above the hemispherical end, which gives L = **306.9 mm**. M3 is then 7.6 mm past the end (note 20: 2-10 mm) and
  tilted ~32 deg from the axis onto the upper end face.
- **Mount geometry [V, measured here on the public scans].** Sphere centres sit 10.1-11.7 mm above the host surface
  (cups, pitcher, planks). There is a ~1 mm flat black pad of radius ~11-12 mm and a collar tapering from ~7 to ~4.4 mm
  radius. The pad is NOT modelled.

## Dimensions (defaults; sources and brackets)
| quantity | value | source / bracket |
|---|---|---|
| wood length | 306.9 mm | auto from M3; note 13 ruler ~30 cm +-7%; note 20 M3 station 311-319 |
| overall extent with markers | 28.7 x 52.0 x 321.6 mm | - |
| bowl length / max width | 95 / 52 mm, widest at 0.50 of the bowl | note 13: 9-10 x 5.2 cm; position [H] |
| bowl depth (rim to concave bottom) | 10 mm | [H] ~1 cm (note 13); back lowest point 10.2 mm below the axis, so it rests on the bowl back and the handle |
| bowl wall | 5 mm | note 13: 4-6 mm [H] |
| rim mid-plane above the handle axis | 2 mm | note 20: 0-4 mm |
| bowl bend toward M1 | 1.3 mm at the bowl centre (yaw about station 118) | note 20 re-run +1.3 +- 0.8 |
| neck | 16 mm round, narrowest at 105 mm | note 13 ~1.6 cm |
| handle diameter | 18.8 (172 mm) -> 21.3 (235) -> 18.8 (298), round, hemispherical end | note 20 re-run bulge 18.8 / 21.3 / 18.8; round radius 9.8-10 |
| surface area / volume | 238.3 cm2 / 84.8 cm3 | - |

## Frame check (R1: centroid origin, surface PCA, z and y by positive third moment, x = y x z)
Origin: 144.3 mm from the bowl tip along the axis (note 13 c_track had 139). Surface sd 6.2 / 10.65 / 92.4 mm. The
canonical axes are tilted 1.0-1.3 deg from frame C, which is the markers' effect.

Skews in the table are signed toward concave (x), M2 (y) and handle (z). "noisy P(B)" is the mid-axis rule with the sign
estimated from n surface points, n drawn from the note 13 posterior.

| variant | mid rule | x rule | skew x | skew y | skew z | noisy P(B) |
|---|---|---|---|---|---|---|
| **default (note-20 layout, bend 1.3)** | **A** | A | -0.030 | **-0.0038** | 0.226 | 0.43 |
| bend 0 | B | A | -0.030 | +0.0010 | 0.226 | 0.52 |
| bend 2.8 mm | A | A | -0.031 | -0.0102 | 0.226 | 0.32 |
| M2 lateral 16.6 (asymmetry -1.1 mm) | B | A | -0.034 | +0.0108 | 0.225 | 0.69 |
| M2 lateral 14.4 (asymmetry +1.1 mm) | A | A | -0.027 | -0.0153 | 0.226 | 0.25 |
| note-13 in-plane layout, bend 0 | B | B | +0.010 | +0.0485 | 0.242 | 0.96 |
| no markers, bend 1.3 | A | B | +0.006 | -0.0239 | 0.221 | 0.17 |
| no markers, bend 0 (tessellation floor) | B | B | +0.006 | 0.0000 | 0.221 | 0.50 |
| bowl depth 6 / 14 mm | A / A | A / A | -0.046 / -0.048 | -0.0060 / -0.0020 | 0.197 / 0.264 | 0.39 / 0.46 |
| oval handle and neck (aspect 0.8) | A | B | +0.081 | -0.0026 | 0.277 | 0.45 |
| rim 4 mm above the axis | A | A | -0.069 | -0.0024 | 0.226 | 0.46 |

- [V] The exact skews match independent Monte Carlo sampling (trimesh, 5 x 2e6 points along the canonical axes):
  x 0.0299, y 0.0029 +- 0.0004 (SE), z 0.2260, vs exact 0.0301 / 0.0038 / 0.2259.
- [V] Tessellation: a 4x-resolution build (12.3k faces) moves the origin by 0.04 mm and the axes by <= 0.03 deg, with
  skews -0.028 / -0.0033 / 0.226 (same labels). The kit CD-O between the two builds is 0.078 cm (sampling floor ~0.073).
- [V] CD-O of the default against variants (kit `_object_chamfer_cm`): bend 0 0.037, note-13 layout 0.117, no markers
  0.131, bowl depth 6 mm 0.104 cm. So CD-O cannot see the frame-relevant asymmetries (note 13 Stage C).
- [E] **The x bit is shape-sensitive in both directions.** skew_x runs from -0.07 to +0.08 over plausible rim heights,
  handle aspects and bowl depths, with P(toward concave) = 0.36 in the MC. So note 20's "x-skew rules -> B (0.88-1.00)"
  does not hold on this body. Under the mid-axis rule, x is the completed axis, so this only matters if the organisers
  used an x rule.

## Key uncertainties (largest first)
1. **The organisers' rule and scan [H].** We cannot know whether their spoon scan has the markers (10/10 public scans
   do), whether their y sign is noisy (n ~ 5.6e3), or how `fast_simplification` affects the thin bowl (not reproducible
   here; not installed). With markers and a noisy rule the bit is ~0.45; with no markers it is set by the bend alone
   (0.17).
2. **M1/M2 lateral asymmetry and bowl bend [E, note 20].** These are the dominant terms (-0.0115 and -0.0039 per mm).
   Measured as +3.4 +- 1 mm vs the handle line and +1.3 +- 0.8 mm. A swing of ~0.4 mm in the asymmetry or ~1 mm in the
   bend flips the sign. A parallax-free frontal rim view is still the open falsifier (note 20).
3. **Marker heights.** M1 +6 +- 1.5 and M2 +10 +- 2 mm toward the concave face (note 20, e5 only; the all-clip mean is
   ~+9 for both).
4. **Unobserved body terms [H].** Bowl depth, wall thickness, rim height, egg shape and neck thickness. These matter for
   x and only weakly for y.
5. **Length scale.** Marker-diameter ruler +-7% and stereo stations +-3 mm. CD-O is scale-free; the frame is not
   affected at first order.
6. **Unmodelled detail.** The ~23 mm black marker pads, wood grain and any real-spoon handle curvature in the x-z
   plane. Appearance is three flat colours (wood from the note 13 colour probe: H12 S61-70 V236-239).

## Limitations
- Only `marker_layout` 'note20' (default), 'note13' (in-plane model, sensitivity only) and 'none' are implemented.
- Stitching is tested on 52 builds. Handle aspect 0.7 works (M3 foot narrowed to 4.4 mm). Aspect 0.65 fails: the M3
  foot ring misses the thin end. A non-hemispherical end needs `end_cap_length` <= the handle radius.
- `fit_spoon.py` is a plan plus scaffolding: loss terms, pose parameterisation and the optimisation loop are TODOs. It
  has not been run. Its parameter export round-trips exactly through `spoon_template.py` [V].
- `--frame B` would relabel the axes only. Do not use it without an organiser answer or a fitted posterior that clearly
  favours B.
