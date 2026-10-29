# autokit part DSL: writing a part program for an object

A part program is a small JSON file that says which parametric parts make up an object, which observed points each
part is fitted to, and how the parts join. `program.py` runs it on ONE episode's observed points and returns one mesh
(manifold3d union of the part solids) plus a report. `parts.py` holds the part library and its parameter schema.

You write a program from what you can see: colour crops of the object and renders of its observed points. You never
need, and must never use, the scans, mocap, `*_align.npz` files or the parquet `pose` fields, or any number measured
on them. Unseen thickness comes only from the generic grid T_GRID = {1.5, 2.5, 4.0} mm (the required `t` argument)
or from two-sided evidence in the points, which the parts measure themselves.

Stage 1b (2026-10-27) changed the DSL; programs written for stage 1 need updating:
- every part type has a parameter **schema**, and unknown keys are now errors (section 5);
- the per-object calibration constants are gone from `parts.py`: **shape windows have no default** and must be given
  in the program (section 3);
- balls use a **generic free-fit rule** with no radius prior (section 8);
- new: `plate_set` segments by plane, plate outlines can `keep_holes`, lathe cell thresholds are density-normalised,
  `t_src` + `variants()` exercise the t grid, and the `shell_patch` part adds route-A surface inside a program
  (section 9).

## 1. Running a program

```
python program.py programs/lathe_bar_balls.json white_pot 41 OUT.glb --t 0.0025      # writes OUT.glb + OUT.json
python program.py PROGRAM.json OBJ EP OUT.glb --t 0.0015 --refined 1                # refine.py's corrected points
python program.py --schema-md [--write DSL.md]                                      # the schema tables of section 5
python program.py --render-points OBJ EP OUT.png                                     # the episode's points (authoring)
python program.py PROGRAM.json OBJ EP OUT.glb --t 0.0025 --budget 4000 --render OUT.png   # mesh over the points
```
From Python:
```python
from autokit.program import run_program, load_program, validate_program, variants
from autokit.io_gt import load_obs, obs_path
prog = load_program('programs/x.json')
for tag, pr in variants(prog):                       # 'base' and, if a part can measure t, 'tprior'
    for t in (0.0015, 0.0025, 0.004):
        mesh, report = run_program(pr, load_obs(obs_path(OBJ, EP)), t=t, lib=LIB_GLB)
        # with a shell_patch part: run_program(..., budget=4000) so the kit's 4096-face decode only welds (section 9)
```
- `t` is required (no default). Run every program at the three grid values, and every variant `variants()` returns.
- Selection between programs, variants or thicknesses is GT-free (gates.py, obs fidelity). Never use a scan score.
- `lib` (our library mesh, only for `tsdf_patch`) is loaded through the io_gt guard.
- `test_programs.py` is the regression test (section 11).

## 2. Program structure

```json
{
 "program": "name", "version": 2,
 "doc": "one paragraph: what the object looks like, why these parts, why each non-default value",
 "prior": {"t": "arg"},
 "frame": {"type": "support", "tall_end": true},
 "parts": [
  {"name": "body", "type": "lathe", "assign": {"rule": "all"},
   "params": {"method": "polar", "rim_w": 0.22, "body_w": 0.22, "t_max": {"frac": 0.066, "floor": 0.003}}},
  {"name": "handle", "type": "plate", "assign": {"rule": "largest_cluster_beyond", "of": ["body"], "k": 0.66},
   "params": {"outline": "bar", "host": "body", "T_max": 0.088, "inner_search": 0.66, "hole_tip": 0.66}},
  {"name": "balls", "type": "ball", "assign": {"rule": "residual", "of": ["body", "handle"]},
   "params": {"of": ["body", "handle"]}}
 ]
}
```

- **Keys.** Program: `program`, `version`, `doc`, `prior`, `frame`, `parts`, `preprocess`. Part: `name`, `type`,
  `assign`, `params`, `attach`, `optional`, `doc`. Any other key is a validation error, as is a `params` key that
  the part type's schema does not declare or an `assign` field the rule does not declare.
- **prior.t**: `"arg"` (default) takes the caller's t. A number must lie on T_GRID.
- **frame** (optional): `{"type": "support"}` builds the table frame used by `tube_rrect`, `cone_array` and the
  `slab` rule (fields in section 5.3):
  - up = normal of the lower supporting plane of the points (the table cut);
  - x = long axis, with the cameras on the -y side; origin on the cut plane;
  - `tall_end` flips x so that the end holding the tall points lies at -x, and stores that end's x range as
    `tall_lo` / `tall_hi`;
  - the table lies `table_band` (from obs_points) below the cut.
- **parts** are fitted in order. Later parts refer to earlier ones by name (params of kind `ref` / `refs`, assignment
  fields `of`, `reach_of`, `frame_of`, `host`, attach `to`). `of` may be a name or a list. Put the body first.
- **Validation**: `validate_program(program)` runs before any fit and lists every problem; `run_program` raises
  ValueError on any of them.
- **optional** (default true): a part whose rule assigns no points, or whose fit fails, is skipped and reported. The
  first part is never optional.

## 3. Scale and windows

`s` is the robust RMS radius of the object's observed points: the RMS distance to the coordinate-wise median after
dropping the 2 % farthest points (1.5 mm voxel-downsampled). The report prints it as `s_mm`.

A **window** is a length parameter. Its value in a program is:
- a bare number: a fraction of s (preferred: the program then works at any object size);
- `{"frac": f, "floor": m}`: max(m, f·s);
- `{"abs": m}`: m metres (avoid for shape windows; it ties the program to one object size).

Every window has a **class** (the schema tables in section 5 list it):

| class | meaning | default |
|---|---|---|
| `sensor` | resolution or noise scale of OUR stereo points: bins, bands, grids | generic absolute value from the sensor constants (voxel 1.5 mm, robust scale 2 mm, residual band 8 mm), the same on every object |
| `generic` | a rule chosen without any object in mind (ball radius window 3–15 mm = "any small sphere"; thickness floor 1.5 mm = the smallest grid value) | absolute value |
| `shape` | depends on the object's shape (flange radii, peg slice heights, plausible extents) | **none: required.** A program that uses the window must give it (validation error otherwise) |

Some windows are required only for one variant of a part (e.g. `rim_w` only for `lathe` with `method: polar`); the
tables say "required when ...".

The four example programs give every window explicitly, including the sensor ones: their values are the hand kits'
absolute windows divided by s of the episode each kit was developed on (GT-free; `gen_programs.py` in the stage-1b
outputs records the arithmetic). That per-object calibration used to sit in `parts.py` as `S_REF_*` constants and
now sits in the programs, which are the per-object side of the method.

## 4. Assignment

`resid(X)` of a part is how far a point lies outside the part. A point is **unexplained** by a list of parts if it lies
more than `band` outside every one of them (default band 8 mm; `"band": f` is a fraction of s, `{"abs": m}` metres).
The rules and their fields are in section 5.2. Notes:
- `residual` without `of` takes the residual of **every earlier part** (used by `shell_patch`);
- `largest_cluster_beyond` measures reach as distance from the axis minus the radius for revolved parts, distance
  beyond the bounding sphere otherwise (a handle that sticks out);
- `largest_cluster_extent` measures length in the host's plane (e1, e2) for sheets and lathes, along the cluster's
  PCA axis otherwise (a strap or arch over a lid);
- `clusters_dir` keeps every residual cluster whose centroid lies beyond the host's centre along `dir` (a knob on top
  of a lid, feet under a body);
- `slab` selects by support-frame coordinate; `cavity` selects points inside a `tube_rrect`'s inner face (things
  standing in a tray).
- `cluster_vox` in assignment rules is absolute metres (connectivity of the sensor's points).

## 5. Part types and their parameters

Each part fits its parameters by robust estimation (medians over azimuth sectors, trimmed planes, soft-L1 least
squares). Every part reports `k` (free parameters), `bounds_hit` (parameters that ended on a bound or clip),
`params`, `diag` and an ownership residual (each observed point belongs to the nearest part: n, median and p90
distance). A bound hit means the data pushed a parameter to its limit; look at it before trusting the part.

How each part decides what is unexplained (`resid`):
- `lathe` polar: outside the solid profile hull by its distance to the outer curve; height: radial excess over the
  outer profile, or beyond the ends;
- `sheet_of_revolution`: height above the top surface, within the edge radius plus `resid_edge`;
- `plate` bar: L∞ distance outside the bar box; `strap`: distance to the swept surface;
- all other parts: signed distance to their sampled surface.

The tables below are generated from `parts.PART_TYPES` (do not edit them by hand).

<!-- schema:begin (generated by `program.py --schema-md --write DSL.md`; do not edit by hand) -->

### 5.1 Part types

| type | models | when you see in crops / point renders | k |
|---|---|---|---|
| `lathe` | thin-walled body of revolution (open containers, bowls, bottles) | round in every view, rim or opening | 5 + profile knots |
| `sheet_of_revolution` | domed cover or dish seen from one side | flat round thing, underside never seen | 5 + knots |
| `plate` | flat piece in its own plane | handles, fins, flat slabs | 9 (bar), 5 + 2 x vertices |
| `plate_set` | several flat plates (sides of a box, a scoop) | flat sheets meeting at edges | sum of plates |
| `strap` | rectangle swept along a fitted centreline | arched handle over a cover, bucket handle | 2 + knots |
| `tube_rrect` | rounded-rectangle tube in the support frame | trays, holders, open boxes standing on the table | 9-13 |
| `cone_array` | rows of tapered round pegs, one template per row | peg rows standing in a tray | knots + 2 x pegs |
| `rounded_box` | box with rounded edges in the PCA frame | blocks, bricks | 10 |
| `ball` | small spheres (markers) on optional stems | small round knobs / grey spheres on short stems | 4 per ball (+1 per stem) |
| `tsdf_patch` | faces of OUR library TSDF mesh outside the listed parts | fallback for parts we cannot model | 0 |
| `splat` | voxel splat + marching cubes of each large cluster | anything irregular the vocabulary lacks | 0 |
| `shell_patch` | route-A thin shell over observed surface the parts did not explain | leftover observed pieces after the parts | 0 |

#### `lathe` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `method` | enum: `"polar"` / `"height"` | `"polar"` | 'polar': closed floor, profile in polar coordinates about an interior point, robust hemisphere axis search; 'height': per-height-bin profile, open end from inner-wall evidence |
| `floor` | enum: `"base"` / `"observed"` / `"solid"` / `"open"` | `"base"` | height method: 'base' closed (cavity to base + t), 'observed' cavity only as deep as the inner wall was seen (GLOBAL RULE ONLY, never a per-object pick motivated by scan coverage), 'solid' no cavity, 'open' bottomless ring |
| `thick` | float | `1.0` | polar: multiplier on the wall thickness (sensitivity runs only) |
| `dphi_deg` | float | `2.0` | polar: angular profile bin (deg) |
| `gap_bins` | int | `3` | height, floor 'observed': bins of missing inner wall tolerated |
| `nseg` | int | `96` | height: revolve segments |
| `axis_refine` | bool | `false` | height: refine lathe_obs.fit_axis's direction by a local rotational-consistency search (stabilises the two-sided t across point densities; off = reproduces lathe_obs) |
| `t_src` | enum: `"auto"` / `"prior"` | `"auto"` | thickness source: 'auto' = measured where both faces (or the side) were seen, else the prior t; 'prior' = always the prior t (program.variants() emits this as the t-grid variant) |
| `cell_q` | float | `0.25` | density-normalised cell threshold: fraction of the median occupied-cell count |
| `cell_min_pts` | int | optional (off) | fixed (bin, sector) cell threshold instead (hand kits: 8); omit = density-normalised |
| `rim_w` | window (shape) | **required** when method=polar | axis search: rim window beyond the body radius |
| `body_w` | window (shape) | **required** when method=polar | profile: body points within the 60th-pct radius + body_w |
| `t_min` | window (generic) | 1.5 mm | smallest wall thickness (= smallest grid value) |
| `t_max` | window (shape) | **required** when method=polar | largest measured wall thickness accepted (clip) |
| `rim_near` | window (sensor) | 8 mm | points within this of the mid-surface define the rim height |
| `resample` | window (sensor) | 3 mm | profile resampling step |
| `dh` | window (sensor) | 3 mm | height bin |
| `body_margin` | window (sensor) | 5 mm | body points: radius below the outer profile max + margin |
| `cap_margin` | window (sensor) | 3 mm | floor points lie inside the inner radius by this |
| `floor_layer` | window (sensor) | 10 mm | spread (q10-q90) below which floor points form one observed layer |

#### `sheet_of_revolution` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `thick` | float | `1.0` | multiplier on the prior t of the unseen underside |
| `edge_w` | window (sensor) | 3 mm | per-sector edge band (98th-pct radius minus edge_w) |
| `flange_r0` | window (shape) | **required** | inner radius of the flat annulus used to refit the normal |
| `flange_r1` | window (shape) | **required** | outer radius of that annulus |
| `flange_h` | window (sensor) | 6 mm | height band of the annulus points |
| `rbin` | window (sensor) | 2 mm | radius bin of the first-pass surface |
| `surf_band` | window (sensor) | 4 mm | points within this of the surface are surface points |
| `tilt_rmin` | window (shape) | **required** | tilt refinement uses radii above this |
| `tilt_rbin` | window (sensor) | 4 mm | radius bin of the tilt refinement |
| `prof_dr` | window (sensor) | 2 mm | radius bin of the top profile |
| `dome_r0` | window (shape) | **required** | inner radius of the ring the near-axis quadratic dome is fitted on |
| `dome_r1` | window (shape) | **required** | outer radius of that ring |
| `resample` | window (sensor) | 3 mm | profile resampling step |
| `resid_edge` | window (shape) | **required** | band beyond the edge radius in which points are this part's business |

#### `plate` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `outline` | enum: `"bar"` / `"occupancy"` / `"rect"` | `"bar"` | 'bar' straight bar with rounded tip and optional hole; 'occupancy' traced outline; 'rect' minimum-area rectangle |
| `host` | ref | none | bar: the body whose wall the bar starts inside |
| `hole` | bool | `true` | bar: look for a hole near the tip |
| `len_bin` | window (sensor) | 5 mm | bar: length bin of the width profile |
| `T_min` | window (generic) | 1.5 mm | bar: smallest measured thickness (= smallest grid value) |
| `T_max` | window (shape) | **required** when outline=bar | bar: largest measured thickness accepted (clip) |
| `inner_search` | window (shape) | **required** when outline=bar | bar: how far behind the inner end the host wall is searched |
| `hole_grid` | window (sensor) | 2 mm | bar: occupancy cell of the hole search |
| `hole_tip` | window (shape) | **required** when outline=bar | bar: a hole must lie within this of the tip |
| `grid` | window (sensor) | 1.5 mm | occupancy cell of the outline (= VOX) |
| `close` | window (sensor) | 3 mm | closing scale of the occupancy mask (2 x VOX) |
| `t_min` | window (generic) | 3 mm | smallest two-face thickness accepted as measured (carried from prim_boards) |
| `t_max` | window (generic) | 25 mm | largest two-face thickness accepted as measured (carried from prim_boards) |
| `keep_holes` | bool | `false` | occupancy outline keeps its holes (no hole filling): rings, handles with a hole |
| `hole_min_d` | window (sensor) | 6 mm | smallest hole kept (equivalent diameter; 2 x the closing scale); bar: smallest tip hole, as the side of a square of equal area (area >= hole_min_d^2, as the hand kit) |
| `t_src` | enum: `"auto"` / `"prior"` | `"auto"` | thickness source: 'auto' = measured where both faces (or the side) were seen, else the prior t; 'prior' = always the prior t (program.variants() emits this as the t-grid variant) |

#### `plate_set` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `segment` | enum: `"plane"` / `"cluster"` | `"plane"` | 'plane': sequential plane segmentation; 'cluster': voxel connectivity (legacy) |
| `outline` | enum: `"occupancy"` / `"rect"` | `"occupancy"` | outline of each plate |
| `min_pts` | int | `300` | points of a plate |
| `max_plates` | int | `4` | largest number of plates |
| `seeds` | int | `200` | RANSAC seeds per plane |
| `plane_deg` | float | `30.0` | normal tolerance of a plane inlier (deg, either sign) |
| `plane_dist` | window (sensor) | 3 mm | distance tolerance of a plane inlier (2 x VOX) |
| `conn_vox` | window (sensor) | 3 mm | voxel connectivity of a plate's inliers |
| `grid` | window (sensor) | 1.5 mm | occupancy cell of the outline (= VOX) |
| `close` | window (sensor) | 3 mm | closing scale of the occupancy mask (2 x VOX) |
| `t_min` | window (generic) | 3 mm | smallest two-face thickness accepted as measured (carried from prim_boards) |
| `t_max` | window (generic) | 25 mm | largest two-face thickness accepted as measured (carried from prim_boards) |
| `keep_holes` | bool | `false` | occupancy outline keeps its holes (no hole filling): rings, handles with a hole |
| `hole_min_d` | window (sensor) | 6 mm | smallest hole kept (equivalent diameter; 2 x the closing scale); bar: smallest tip hole, as the side of a square of equal area (area >= hole_min_d^2, as the hand kit) |
| `t_src` | enum: `"auto"` / `"prior"` | `"auto"` | thickness source: 'auto' = measured where both faces (or the side) were seen, else the prior t; 'prior' = always the prior t (program.variants() emits this as the t-grid variant) |

#### `strap` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `host` | ref | none | the sheet / body the strap ends run down into |
| `t_src` | enum: `"auto"` / `"prior"` | `"auto"` | thickness source: 'auto' = measured where both faces (or the side) were seen, else the prior t; 'prior' = always the prior t (program.variants() emits this as the t-grid variant) |
| `len_bin` | window (sensor) | 3 mm | length bin of the top curve |
| `W_min` | window (shape) | **required** | smallest strap width (clip) |
| `W_max` | window (shape) | **required** | largest strap width (clip) |
| `T_min` | window (generic) | 1.5 mm | smallest measured thickness (= smallest grid value) |
| `T_max` | window (shape) | **required** | largest measured thickness (clip) |
| `end_ext` | window (sensor) | 4 mm | extension of the ends beyond the last top-seen bin |
| `resample` | window (sensor) | 2 mm | centreline resampling step |

#### `tube_rrect` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `wall` | enum: `"thin"` / `"lip"` | `"thin"` | 'thin': wall thickness t, lean / draft / corner free; 'lip': thick rim s0, inner face sloping by s1, outer face leaning by dout, top = robust plane |
| `above` | ref | none | thin: host tube whose top hides this tube's lower outer face |
| `x_min_from` | enum: `null` / `"tall_lo"` | none | 'tall_lo': the -x end is fixed at the frame's tall region |
| `align_frame` | bool | `true` | lip: re-express the program frame in the fitted outline frame |
| `carve` | enum: `null` / `"self"` / `"all"` | none | 'self' (default for lip) or 'all' (default for thin) |
| `lean` | bool | `true` | thin: lean and draft free |
| `lean_max` | float | `0.25` | thin: lean / draft bound |
| `iters` | int | optional (off) | robust-fit rounds (default 4 lip, 5 thin) |
| `floor_depth` | window (shape) | optional (off) | development only: floor plate at this depth below the top |
| `r0` | window (shape) | **required** | initial corner radius |
| `r_min` | window (shape) | **required** | corner radius lower bound |
| `r_max` | window (shape) | **required** | corner radius upper bound |
| `class_gate` | window (sensor) | 8 mm | point-class gate around the current surface |
| `skip_end` | window (shape) | **required** when x_min_from=tall_lo | points within this beyond the tall region are not used (x_min_from) |
| `skip_lip` | window (shape) | **required** when wall=lip, x_min_from=tall_lo | lip-top samples start this far beyond the tall region |
| `edge_band` | window (shape) | **required** when wall=lip | lip: band along the outline edges for top samples |
| `top_seg` | window (sensor) | 10 mm | lip: segment length of the top samples |
| `top_robust` | window (sensor) | 3 mm | lip: inlier band of the top plane |
| `s0_init` | window (shape) | **required** when wall=lip | lip: initial rim width |
| `e_min` | window (shape) | **required** when wall=lip | lip: smallest half extent |
| `e_max` | window (shape) | **required** when wall=lip | lip: largest half extent (y; x: 10x) |
| `s0_min` | window (shape) | **required** when wall=lip | lip: smallest rim width |
| `s0_max` | window (shape) | **required** when wall=lip | lip: largest rim width |
| `near_in` | window (shape) | **required** when wall=lip | lip: points this far inside the outline are near |
| `near_out` | window (shape) | **required** when wall=lip | lip: points this far outside the outline are near |
| `low` | window (sensor) | 3 mm | lip: outer-class points above this height |
| `below_top` | window (sensor) | 6 mm | lip: wall classes end this far below the top |
| `low_in` | window (sensor) | 6 mm | lip: inner-class points above this height |
| `lip_below` | window (sensor) | 3 mm | lip: top class from this far below the top |
| `lip_above` | window (sensor) | 4 mm | lip: ... to this far above it |
| `lip_in` | window (shape) | **required** when wall=lip | lip: top class reaches this far inside the outline |
| `lip_out` | window (sensor) | 6 mm | lip: ... and this far outside it |
| `flat_band` | window (shape) | **required** when wall=thin | thin: y band of the robust top height |
| `init_above` | window (shape) | **required** when wall=thin | thin: initial outline from points this far above the host top |
| `ex_min` | window (shape) | **required** when wall=thin | thin: smallest half extent x |
| `ex_max` | window (shape) | **required** when wall=thin | thin: largest half extent x |
| `ey_min` | window (shape) | **required** when wall=thin | thin: smallest half extent y |
| `ey_max` | window (shape) | **required** when wall=thin | thin: largest half extent y |
| `near` | window (shape) | **required** when wall=thin | thin: points within this of the surface are near |
| `top_above` | window (sensor) | 4 mm | thin: near points up to this above the top |
| `host_band` | window (sensor) | 4 mm | thin: band above the host top |
| `out_in` | window (sensor) | 6 mm | thin: outer class reaches this far inside |
| `in_out` | window (sensor) | 3 mm | thin: inner class reaches this far outside |
| `rim_band` | window (sensor) | 3 mm | thin: rim class within this below the top |
| `floor_in` | window (sensor) | 4 mm | thin: raised-floor points lie inside the inner face by this |

#### `cone_array` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `host` | ref | none | the tray (tube_rrect) whose floor the pegs stand on |
| `top_from` | ref | none | part whose top height limits the pegs |
| `slice0` | window (shape) | **required** | lower height of the detection slice |
| `slice1` | window (shape) | **required** | upper height of the detection slice |
| `grid` | window (sensor) | 2 mm | occupancy cell of the slice |
| `row_dy` | window (shape) | **required** | pegs within this in y form a row |
| `peg_r` | window (shape) | **required** | point radius around a peg centre |
| `h0` | window (sensor) | 2 mm | lowest knot height |
| `dh` | window (sensor) | 6 mm | knot spacing of the row template |
| `a0` | window (shape) | **required** | initial peg radius |
| `a_min` | window (shape) | **required** | smallest peg radius |
| `a_max` | window (shape) | **required** | largest peg radius |
| `centre_move` | window (shape) | **required** | largest peg-centre move |
| `min_above_host` | window (shape) | **required** | rows must rise this far above the host top |
| `above_host` | window (sensor) | 2 mm | points this far above the host top count for the pegs |

#### `rounded_box` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `pct` | float | `1.0` | robust extent percentile |
| `r_frac` | float | `0.2` | edge radius / smallest half extent |

#### `ball` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `mode` | enum: `"free"` / `"none"` | `"free"` | 'free': balls only where a free sphere fit passes every test; 'none': no balls |
| `fit` | enum: `"lsq"` / `"ransac"` | `"lsq"` | 'lsq': least squares on the whole cluster + one inlier refit; 'ransac': MSAC over 4-point sphere hypotheses inside the radius window, support = points near the sphere that face their camera (stage-1b experiment: radii biased to the top of the window on the 3 dev episodes; kept as an option, not the default) |
| `ransac_tol` | window (sensor) | 2 mm | ransac: support band around the sphere (= the stereo noise scale F_SCALE) |
| `of` | refs | none | earlier part(s) whose surface is the host (a name or a list) |
| `reject_inside` | ref | none | tube whose cavity footprint must not hold a ball centre |
| `stems` | bool | `true` | stems where points support them |
| `min_pts` | int | `25` | points of a cluster (a 3 mm hemisphere cap holds ~25 voxels of 1.5 mm) |
| `min_frames` | int | `3` | frames a ball must be seen in (one mis-tracked frame cannot make a ball) |
| `cap_min` | float | `0.08` | cap spread 1 - \|mean radial\| (half-angle >= ~33 deg) |
| `convex_min` | float | `0.8` | share of cap points whose fitted outward normal faces their camera |
| `iso_min` | float | `0.25` | tangent spread isotropy (rims, pegs, fillets curve one way only) |
| `stem_min` | int | `15` | observed points in the stem cylinder |
| `r_min` | window (generic) | 3 mm | smallest radius ('any small sphere'; generic, not from any scan) |
| `r_max` | window (generic) | 15 mm | largest radius ('any small sphere'; generic, not from any scan) |
| `res_max` | window (sensor) | 1.5 mm | largest median \|d - r\| of the fit (= VOX) |
| `gap_max` | window (generic) | 30 mm | largest ball-surface to host-surface gap (= 2 r_max) |
| `cluster_vox` | window (sensor) | 3 mm | voxel connectivity of the residual clusters |

#### `tsdf_patch` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `of` | refs | none | earlier part(s) whose surface is the host (a name or a list) |
| `margin` | window (sensor) | 8 mm | library faces farther than this outside every listed part are kept |

#### `splat` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `vox` | window (sensor) | 2 mm | splat voxel |
| `min_pts` | int | `400` | points of a splatted cluster |
| `combine` | enum: `"union"` / `"concat"` | `"union"` | 'union' (watertight) or 'concat' (separate mesh) |

#### `shell_patch` parameters

| name | kind | default | meaning |
|---|---|---|---|
| `of` | refs | none | host parts the patch must not duplicate (default: every earlier part) |
| `min_pts` | int | `100` | points of a residual cluster that gets a patch |
| `cluster_vox` | window (sensor) | 3 mm | voxel connectivity of the residual clusters |
| `max_faces` | int | optional (off) | face cap of the patch (default: none, or budget_share x the program budget) |
| `budget_share` | float | `0.4` | budget mode (run_program budget=...): share of the face budget the patch may use |

### 5.2 Assignment rules (`assign`)

| rule | field | kind | default | meaning |
|---|---|---|---|---|
| `all` | (none) | | | every observed point |
| `residual` | `of` | refs | none | earlier part(s); default: every earlier part |
| `residual` | `band` | band | none | unexplained = more than band outside every part in of (fraction of s or {"abs": m}; default APP_D = 8 mm) |
| `largest_cluster_beyond` | `of` | refs | none | earlier part(s); default: every earlier part |
| `largest_cluster_beyond` | `band` | band | none | unexplained = more than band outside every part in of (fraction of s or {"abs": m}; default APP_D = 8 mm) |
| `largest_cluster_beyond` | `reach_of` | ref | none | part whose reach is measured (default of[0]) |
| `largest_cluster_beyond` | `k` | float | `0.5` | the cluster's 99th-pct reach must exceed k x s |
| `largest_cluster_beyond` | `min_pts` | int | `200` | points of a cluster |
| `largest_cluster_beyond` | `cluster_vox` | float | `0.003` | cluster connectivity voxel (ABSOLUTE metres) |
| `largest_cluster_extent` | `of` | refs | none | earlier part(s); default: every earlier part |
| `largest_cluster_extent` | `band` | band | none | unexplained = more than band outside every part in of (fraction of s or {"abs": m}; default APP_D = 8 mm) |
| `largest_cluster_extent` | `frame_of` | ref | none | part whose plane (e1, e2) measures the length (default of[0]) |
| `largest_cluster_extent` | `min_extent` | float | `0.5` | the cluster must be longer than min_extent x s |
| `largest_cluster_extent` | `min_pts` | int | `200` | points of a cluster |
| `largest_cluster_extent` | `cluster_vox` | float | `0.003` | cluster connectivity voxel (ABSOLUTE metres) |
| `clusters_dir` | `of` | refs | none | earlier part(s); default: every earlier part |
| `clusters_dir` | `band` | band | none | unexplained = more than band outside every part in of (fraction of s or {"abs": m}; default APP_D = 8 mm) |
| `clusters_dir` | `host` | ref | none | part whose centre / axis is the origin (default of[0]) |
| `clusters_dir` | `dir` | enum: `"+axis"` / `"-axis"` / `"+up"` / `"-up"` / `"+x"` / `"-x"` / `"+y"` / `"-y"` | `"+axis"` | direction |
| `clusters_dir` | `min_offset` | float | `0.0` | centroid beyond the host centre by > min_offset x s |
| `clusters_dir` | `min_pts` | int | `60` | points of a cluster |
| `clusters_dir` | `cluster_vox` | float | `0.003` | cluster connectivity voxel (ABSOLUTE metres) |
| `slab` | `axis` | enum: `"x"` / `"y"` / `"h"` | `"x"` | support-frame axis |
| `slab` | `min_from` | slab | none | 'tall_lo', 'tall_hi' or a fraction of s |
| `slab` | `max_from` | slab | none | 'tall_lo', 'tall_hi' or a fraction of s |
| `slab` | `min_margin` | float | `0.0` | fraction of s added to min_from |
| `slab` | `max_margin` | float | `0.0` | fraction of s added to max_from |
| `cavity` | `of` | ref | none | a tube_rrect |
| `cavity` | `inset` | float | `0.0` | inside the inner face by > inset x s |
| `cavity` | `beyond_margin` | float | optional (off) | only points past the host cavity clip by this x s |

### 5.3 Frame (`frame`)

| name | kind | default | meaning |
|---|---|---|---|
| `type` | enum: `"support"` | `"support"` | the only frame type: table support frame |
| `tall_end` | bool | `true` | flip x so the end holding the tall points lies at -x |
| `tall_frac` | float | `0.65` | tall points: h > tall_frac x the 99.8 % height |
| `cell` | window (sensor) | 10 mm | cell of the lower supporting plane fit |
| `band` | window (sensor) | 3 mm | inlier band of the lower supporting plane |

<!-- schema:end -->

## 6. Attachment, union and carving

- **Attachment by fitting**: a `plate` bar with `host` starts inside the host lathe's wall (radius < rmax − 2t); a
  `strap` with `host` runs its ends down to the host sheet's mid-surface; a `cone_array` stands on its host tube's
  floor; a `ball` stem runs to the nearest host surface, only where points support it.
- **Attachment rules** (`attach` on the later part, applied right after it is fitted):
  `{"mode": "clip_cavity", "to": HOST, "face": "+x"}`: this tube ends the host tube's cavity, which then exists only
  beyond this part's outer face. Later `cavity` assignments and `reject_inside` use the clip.
- **Union**: all part solids are unioned with manifold3d. A tube with `carve: all` (default for `thin`) has its cavity
  subtracted from the whole assembly; `carve: self` (default for `lip`) subtracts it from itself only.
- `tsdf_patch`, `splat` with `combine: concat`, and a `shell_patch` that is not watertight are concatenated after the
  union; the mesh is then not one watertight solid (check `watertight` in the report).

## 7. Thickness and the t grid

- Parts use t only where the wall was not seen from both sides. `lathe` (inner and outer wall), `plate` bar and
  `strap` (side-seen points) and `plate` / `plate_set` occupancy (two faces) measure their thickness when the evidence
  exists (`diag.t_src`: `two_sided` or `side`), else they use t (`prior`). `diag.t_src_evidence` says whether the
  evidence existed.
- **`t_src: "prior"`** forces the prior even where evidence exists. `program.variants(prog)` returns the program and a
  `tprior` copy with every such part on `prior`, so that the grid {1.5, 2.5, 4.0} mm is exercised even where a
  thickness was measured (the measured value moves with point density). Run both and let the GT-free gate choose.
- **Density-normalised cells** (`lathe`): a (bin, sector) cell counts as seen when it holds at least
  max(3, `cell_q` × the median count of the occupied cells) points (`cell_q` = 0.25), so a denser sample of the same
  object sees the same cells. `cell_min_pts: 8` restores the hand kits' fixed count (comparison runs only).
- `tube_rrect` 'lip' fits its lip width and inner slope from the points; its floor plate and the `thin` tube's wall
  use t. `sheet_of_revolution` always uses t (its underside is never seen).

## 8. Balls (generic rule, no radius prior)

`ball` keeps a sphere only where the observed points themselves show one. Each compact residual cluster gets a FREE
sphere fit, `fit: "lsq"` (default) or `"ransac"`:
- `lsq`: algebraic fit, Gauss-Newton, one inlier refit (|d − r| < 3 × median) on the whole cluster.
- `ransac` (option, stage-1b experiment): 400 hypotheses, each the sphere through 4 points of one 2 `r_max`
  neighbourhood with a radius inside the window, scored by the MSAC cost over the points that face their camera
  (support band `ransac_tol` = 2 mm, the stereo noise scale); the 5 best get one Gauss-Newton pass on their own
  inliers. Hypothesis: robust to the mount or strip of host wall that shares a ball's cluster, so more visible balls
  would be kept. Not supported on the three development episodes [M] (`lsq` → `ransac`): lid 2 → 2 balls (r 7.3/8.7
  → 10.6/8.7 mm), rack 1 → 1 (7.7 → 9.7 mm), pot 1 → 2 (11.3 → 12.0 mm floating 7.8 mm off the host, and 4.5 mm),
  and 10 of the 12 pot fits ran to 12–15 mm, the top of the window: a bias towards a larger sphere that also
  explains points around a ball's base. On the synthetic scene of `test_programs.py --only synth` (4.5 and 11 mm
  caps, flat disc, rod, concave bowl, 25 mm cap) `lsq` keeps exactly the two balls (4.8, 11.0 mm) while `ransac`
  overestimates them (5.5, 11.4 mm) and accepts a false 14.6 mm ball on the rod. Not the default.

The ball is kept only if every test passes:
- radius within [`r_min`, `r_max`] = [3, 15] mm, a generic "any small sphere" window (not taken from any scan;
  there is no fixed-radius fallback: a cluster whose free fit leaves the window is rejected, not snapped to a size);
- support (inliers) ≥ `min_pts` points, median fit residual ≤ `res_max` (1.5 mm = the voxel);
- seen in ≥ `min_frames` (3) frames;
- cap spread 1 − |mean radial direction| ≥ `cap_min` (0.08: half-angle ≥ ~33°; flat patches fail);
- convex: ≥ `convex_min` (80 %) of the cap points (`ransac`: of all points within `ransac_tol` of the sphere) have a
  fitted outward normal facing their camera (concave fits fail);
- isotropic: tangent spread ratio ≥ `iso_min` (0.25; rims, pegs and fillets curve one way only);
- centre not inside the host and ball surface within `gap_max` (30 mm) of it; not over a `reject_inside` cavity.

A stem is added only where ≥ `stem_min` observed points lie in the gap within 0.6 r of the stem axis and at least
twice as many as in either control cylinder one ball diameter to the side; its radius is measured from those points.
`mode: "none"` gives no balls. The report lists every cluster with its statistics and rejection reason
(`diag.markers`). Expect fewer balls than the stage-1 kits, whose 7 mm radius prior came from the scans.

## 9. A inside B: `shell_patch`

`{"name": "patch", "type": "shell_patch", "assign": {"rule": "residual"}}` as the LAST part adds observed surface the
parts did not explain: the residual of every earlier part (voxel clusters of ≥ `min_pts`) goes, as raw points, to
`shell.surface_patch` (route A: a closed thin shell of thickness t over them, trimmed where it would duplicate the
host = union of the earlier parts). The report's `diag.impl` says which implementation ran (`shell.surface_patch`;
`parts.surface_patch_standin` only if shell.py lacks it).

**Face budget.** The kit decodes every mesh to 4096 faces with one global decimation, which thins closed thin-shell
patches (measured: decode area −2 to −11 % on the stage-1b patch rows built without a budget). Run programs that
contain a patch with `run_program(..., budget=4000)`: the patch is built within `budget_share` (40 %) of the budget
and kept as a separate closed mesh, and only the solid union is decimated (the kit's own decimator,
fast_simplification) to the rest, so the kit's `budget_mesh` only welds (`report.budget`). Patches add surface;
compare with and without by the GT-free gate, never by scan score.

## 10. Report (OUT.json)

- **Header**: `s_mm`, `t_mm`, `n_pts`, `faces`, `watertight`, `bodies`, `area_cm2`, `k_total`, `bounds_hit`, `sec`;
  `obs_to_model`: median and p90 distance from all points to the nearest part.
- **Per part**: `n_assigned`, `k`, `params`, `bounds_hit`, `residual` (n_owned, med_mm, p90_mm), `diag` (e.g. the
  lathe's `t_src` and `cell_min_pts`, the tube's class counts, every ball cluster with its tests, the plate_set
  segmentation, the patch's `impl`), `skipped` / `failed`.
- Read these before trusting a mesh: many owned points with a large median residual = wrong shape; `bounds_hit` = at
  its limits; `bodies` > 1 = floating pieces (e.g. balls without stem evidence).

## 11. Worked examples (`programs/`) and the regression test

| program | object type | reproduces |
|---|---|---|
| `lathe_bar_balls.json` | open container + flat bar handle + balls | `prim_potlid.py pot --variant fit`, except the balls |
| `sheet_strap_balls.json` | domed lid + arched strap + balls | `prim_potlid.py lid --variant fit`, except the balls |
| `lathe_splat.json` | cup: lathe + splatted appendages | `lathe_obs.py --appendages 1` |
| `tray_holder_pegs_balls.json` | tray + tall holder at one end + peg rows + balls | `prim_rack.py build` (single episode), except the balls |

`test_programs.py` runs the reproductions, the scale tests, the cross-episode runs, the schema checks and smoke runs
(`--only dsl`) and the stage-1b matrix (`--only s1b_pot,s1b_lid,s1b_rack,s1b_cup`). Stage-1 measurements (with the
old balls) are in `results/autokit-stage1/`; the stage-1b matrix results are in section 13.

## 12. Authoring a program for a NEW object (from crops and point renders alone)

Inputs you may use: the object's colour crops (`crops.py`), renders of ONE episode's observed points (and of a
program's mesh over them), the object name and slot from the episode, the reports of your own runs, the GT-free gate.
Inputs you may not use: scans, scan-derived numbers (sizes, thicknesses, marker radii, coverage), mocap,
`*_align.npz`, parquet poses, any CD-O or other scan score. Validation labels must not come from scan scores either.

0. **Render the points**: `program.py --render-points OBJ EP OUT.png` draws the episode's observed points from the
   mean camera direction (as the crops see the object) and from ±60°. After each run, `--render OUT.png` draws the
   program's mesh (grey) over the points (blue): blue blobs standing in front of the mesh are observed surface no
   part explains (e.g. balls the ball rule rejected, a missing appendage).
1. **List the visible pieces** in the crops and point renders. For each: which part type (section 5.1)? Is it a body
   (rule `all`) or an appendage (a residual rule)? Which side is never seen (there the shape comes from t; keep that
   surface small)? Prefer the fewest parts that explain the points.
2. **Order the parts**: body first, then large appendages, balls last with `of` listing every surface they may sit
   on, then optionally `shell_patch` for what is left.
3. **Fill the required windows** (section 5 tables, class `shape`). Measure them on the POINT RENDERS of the episode,
   as fractions of the reported `s_mm`: e.g. a flange annulus from its radii in a top-down render, a peg slice from
   the heights in a side render. Write in `doc` where each value came from. Leave sensor and generic windows at their
   defaults unless the report shows why not.
4. **Run** at t = 1.5, 2.5, 4.0 mm and every `variants()` copy; also with `ball` `mode: none` and with a
   `shell_patch`. Read the report (section 10): owned residuals near the stereo noise (median ≈ 1–3 mm), few bound
   hits, sensible bodies, ball clusters rejected for the right reasons.
5. **Choose GT-free**: compare candidates with the shell route (shell.py) and the library mesh by the gate (gates.py)
   and obs fidelity, never by scan score. Pre-register the choice rule before any scan round.
6. **Coverage switches are global rules, never per-object picks.** A coverage switch changes how much UNOBSERVED
   surface a part invents or drops: `lathe` `floor: "observed"` (cavity only as deep as the inner wall was seen),
   `ball` `mode: "none"`, adding or leaving out a `shell_patch` or `tsdf_patch`, `t_src: "prior"`. Such a switch may
   only be (a) one rule applied to every object, written down before any scan round, or (b) a choice the GT-free
   gate makes between variants that are all built (run both, let the gate pick). An author must never set it for
   one object because that object's scan is partial, because "a scanner sees about as far in", or because a scan
   score improved. Shape switches are different: `floor: "open"` (a bottomless ring), `floor: "solid"`, `keep_holes`
   (a hole you can see), `carve` describe the object's shape and are set from what the crops and point renders
   SHOW; write the evidence in `doc`.
7. **Mind the scorer**: CD-O normalises scale by the area-weighted RMS radius. Extra hidden surface (thick slabs,
   internal faces, splats inside the body) and missing surface both shift it. Prefer `union` over `concat`; keep
   unseen faces at the prior thickness.

## 13. Stage-1b measurements (2026-10-29, GT-free, CPU)

All numbers are [M] on our own points; no scan was opened or scored. Outputs: `scratchpad/auto/stage1b/parts/`
(`final/` = matrix from the frozen snapshot `snap/` (SHA256SUMS), `final2/` = budget-mode patch rows after the
fixes below, `balls*/`, `tdiag/`, `synth_final/`, `render/`, `PROGRESS.md`).

<!-- s1b-results:begin -->
**Reproduction** (t = 2.5 mm, generic balls, full resolution) against the hand-kit incumbent meshes (`--only
lid,pot,cup,rack`): obs fidelity sum (mm, lower is better) program / incumbent, and symmetric mesh-to-mesh distance
median / p90 (mm).

| program on episode | fidelity | distance to incumbent | note |
|---|---|---|---|
| sheet_strap_balls, lid ep2 | 1.701 / 1.683 | 0.003 / 0.017 | 2 generic balls instead of 3 (2 at the old 7 mm prior) |
| lathe_bar_balls, pot ep41 | 2.908 / 2.907 | 0.391 / 0.814 | density-normalised cells: two-sided wall 3.96 mm (fixed 8-point cells: 4.77 mm, distance 0.0 / 0.0) |
| lathe_splat, cup ep21 | 4.081 / 4.104 | 0.009 / 0.244 | |
| tray_holder_pegs_balls, rack ep13 | 7.448 / 8.511 | 0.013 / 4.831 | single-episode floor plate, as in stage 1 |

**Generic balls** (`fit: lsq`, no radius prior) against the stage-1 rule (7 mm scan-derived prior):

| episode | stage 1 | stage 1b | balls visible in our colour crops |
|---|---|---|---|
| lid ep2 | 3 (7.35; 7.0 and 7.0 at the prior) | 2 (7.3, 8.7 mm) | 5 (on black mounts) |
| pot ep41 | 5 (4 at the prior) | 1 (11.3 mm, at the handle base; radius looks inflated, the fit probably includes the mount) | about 4-5 |
| rack ep13 | 2 (8.0 mm with stem; 7.0 at the prior) | 1 (7.7 mm, no stem) | not counted |

No stem was kept anywhere. Fidelity with / without balls (as decoded by the kit, base, t 2.5): lid 1.693 / 1.800,
pot 2.893 / 2.922, rack 7.448 / 7.479. The remaining visible balls are rejected because the small caps share their
cluster with the black mount and the surface around it (free fits of 13-53 mm, concave or flat); a smaller residual
band (4 or 3 mm instead of 8) keeps the same 2 lid balls and finds no new one; the `ransac` fit is not better
(section 8). On the other public episodes (programs unchanged, t = 2.5 mm) the generic rule keeps pot ep42 1 ball
(10.3 mm), ep43 1 (10.0 mm), ep44 0, ep45 0, and rack ep12, 26, 27, 31 none; the stage-1 rule had kept 2-3 balls on
each of these pot and rack episodes, every one at the 7 mm prior except a single 5.4 mm free fit (rack ep27).
Fidelity there against the stage-1 cross meshes: pot 2.737 / 2.706, 2.886 / 2.881, 5.177 / 4.727, 5.662 / 5.327 mm;
racks within 0.05 mm (balls and the cell rule both differ; their shares are not separated). The lid program fails
on lid ep0 (the sheet's edge circle finds 0 of 36 sectors). **Ball recall is the main open issue of route B.**

**t grid.** `base` measures the wall where both faces were seen, so its mesh does not move with t (pot: wall
3.96 mm at every t; cup: 1.75 mm). The `tprior` variant exercises the grid [M, decoded fidelity at t = 1.5 / 2.5 /
4.0 mm]: pot 2.971 / 2.909 / 2.859 (balls free; the program's `t_min` window clips 1.5 to 2.0 mm), cup 4.105 /
4.086 / 4.067 (budget mode), lid (always the prior) 1.446 / 1.699 / 2.269. The cup's measured two-sided wall is
density-dependent: 1.68 / 1.75 / 4.44 mm at voxel 2.0 / 1.5 / 1.0 mm and 6.56 / 2.84 mm after 25 % / 50 % raw
thinning, mostly through the axis (lathe_obs.fit_axis moves 2.4-7.1 deg between samplings; with the axis fixed t =
1.75-2.69 mm). `lathe` `axis_refine: true` (local rotational-consistency search, off by default) brings the same 7
samplings to 1.50-2.36 mm (spread 0.86 mm; pre-stated falsifier "> 1 mm" not met). Density-normalised cells alone
do not stabilise it.

**A inside B (`shell_patch`, budget mode, decoded fidelity base t = 2.5 mm, without / with patch):** lid 1.699 /
1.656 (patch 40 cm², 3 bodies), rack 7.448 / 7.222 (74 cm², 16 bodies), pot 2.906 / 2.965 (240 cm², 20 bodies:
worse), cup 4.073 / 4.073 (the splats leave no residual). Every budget-mode mesh is decoded by the kit's budget_mesh
with welding only (area change 0.00 %); lid and cup stay watertight, the rack union is not watertight even without a
patch (as in stage 1). Without the budget, the decode changed area by −2 to −11 % on patch rows (first stage-1b run).

**plate_set** on the dust pan (ep39, all points): plane segmentation 6 plates, fidelity 2.54 mm; voxel connectivity
1 plate, 6.83 mm. `keep_holes` kept no hole on the pan (its ring is not one of the plates); on the synthetic plate the
30 mm hole survives (area 95.7 → 89.1 cm², expected −7.1).

**Synthetic scene** (`--only synth`): `lsq` keeps exactly the 4.5 and 11 mm caps (4.79, 11.03 mm) and rejects the
disc, rod, concave bowl and 25 mm cap; `ransac` fails (5.51, 11.43 and a false 14.58 mm ball on the rod);
plate_set by plane 2 plates, by connectivity 1.

**Scale** (`--only scale,scale_all`, points × 1.3, windows mode): output scaled back equals the original (median
0.0 mm for cup, lid, pot; 0.053 mm rack; area within 0.7 %). Physical mode (same 1.5 mm voxel): cup wall 1.75 →
4.94 mm, the density effect above.

**Integrity.** Every production command ran under `strace -f -e trace=openat,open,openat2,execve`: 0 forbidden
opens (`final/strace_audit.json`; the only pattern hit is Python's json/scanner.pyc).
<!-- s1b-results:end -->

## 14. Limits (open)

- **Ball recall**: the generic rule keeps 2 of 5 crop-visible lid balls and 1 of about 4-5 pot balls (section 13);
  small caps that share a cluster with their mount are not separated. No stems are found.
- **`shell_patch` is not a free win**: it lowers the fidelity sum on the lid and rack but raises it on the pot at
  every t and variant (+0.03 to +0.10 mm), and it adds many small bodies (lid 3, rack 11-17, pot 20-49). Use it only
  as a variant the GT-free gate chooses.
- **The rack program's union is not watertight** (tube carving), with or without budget mode.
- **Example `t_min` windows can clip the grid**: the pot program's `t_min` (max(1.5 mm, 0.022 s) = 2.0 mm) turns the
  1.5 mm grid value into 2.0 mm.
- **Two-sided walls depend on the axis**: use `axis_refine` (height method) or the `tprior` variant; the polar
  method's axis search is already local-refined.

- **The vocabulary is small**: no swept tubes of arbitrary section, no lofts, no ring/torus part, no free-form curved
  sheet; `splat`, `tsdf_patch` or `shell_patch` fill gaps.
- **`tube_rrect` assumes a support frame** (table cut) and one tall end.
- **Example windows are development choices** on four episodes (hand kits); whether each hand-kit window was set
  before or after a scan scoring of its kit is not recorded. The work log (2026-10-27 primitive-assembly round)
  records 2 development scan scorings each for the lid and rack families (the pot's 32 scored variants were scored
  at selection time) and two leaks that were removed then (scan wall thickness as the rack / lid t; the upright cup
  holder). Treat the example windows as possibly scan-informed development choices: a NEW object's windows must come
  from its crops and point renders only (section 12).
- **Other count thresholds are still absolute** (cluster minimum sizes, the floor-layer 200 points, ball `min_pts`
  and `stem_min`); only the lathe cell threshold is density-normalised.
- **Hidden geometric constants of the hand kits remain** (2 mm corner-radius floors in tube sections, the 10 mm
  cavity overshoot above a tube top).
- `parts.py` still imports geometry helpers from `scripts/prim_potlid.py`, `prim_rack.py` (which holds an object name
  for its own driver) and `prim_boards.py`; no object-specific value flows from them into autokit, but they are not
  yet ported.
