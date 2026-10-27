# autokit part DSL: writing a part program for an object

A part program is a small JSON file that says which parametric parts make up an object, which observed points each
part is fitted to, and how the parts join. `program.py` runs it on ONE episode's observed points and returns one
watertight mesh (manifold3d union) plus a report. `parts.py` holds the part library.

You write a program from what you can see: colour crops of the object and renders of its observed points. You never
need, and must never use, the scans, mocap, `*_align.npz` files or the parquet `pose` fields. Programs hold no
scan-measured numbers. Unseen thickness comes only from the generic grid T_GRID = {1.5, 2.5, 4.0} mm (the `--t`
argument) or from two-sided evidence in the points, which the parts measure themselves.

## 1. Running a program

```
python program.py programs/lathe_bar_balls.json white_pot 41 OUT.glb --t 0.0025      # writes OUT.glb + OUT.json
python program.py PROGRAM.json OBJ EP OUT.glb --refined 1                           # refine.py's corrected points
```
From Python:
```python
from autokit.program import run_program, load_program
from autokit.io_gt import load_obs, obs_path
mesh, report = run_program(load_program('programs/x.json'), load_obs(obs_path(OBJ, EP)), t=0.0025, lib=LIB_GLB)
```
- Run every program at the three thicknesses t ∈ {0.0015, 0.0025, 0.004}.
- Selection between programs or thicknesses is GT-free (gates.py, obs fidelity). Never use a scan score to choose.
- `test_programs.py` reproduces the four hand kits and is the regression test (section 9).

## 2. Program structure

```json
{
 "program": "name", "version": 1,
 "doc": "one paragraph: what the object looks like and why these parts",
 "prior": {"t": "arg"},
 "frame": {"type": "support", "tall_end": true},
 "parts": [
  {"name": "body", "type": "lathe", "assign": {"rule": "all"}, "params": {"method": "polar"}},
  {"name": "handle", "type": "plate", "assign": {"rule": "largest_cluster_beyond", "of": ["body"], "k": 0.66},
   "params": {"outline": "bar", "host": "body"}},
  {"name": "markers", "type": "ball", "assign": {"rule": "residual", "of": ["body", "handle"]},
   "params": {"of": ["body", "handle"]}}
 ]
}
```

- **prior.t**:
  - `"arg"` (default) takes the caller's t.
  - A number must lie on T_GRID, or the run raises ValueError.
- **frame** (optional): `{"type": "support"}` builds the table frame. Only `tube_rrect`, `cone_array` and the `slab`
  rule use it. Its fields:
  - up = normal of the lower supporting plane of the points (the table cut);
  - x = long axis, with the cameras on the -y side;
  - origin on the cut plane;
  - `tall_end` (default true) flips x so that the end holding the tall points (h > `tall_frac` × the top height,
    default 0.65) lies at -x, and stores that end's x range as `tall_lo` / `tall_hi`;
  - the table lies `table_band` (from obs_points) below the cut.
- **parts** are fitted in order. Later parts can refer to earlier ones by name, both in assignment rules and in params
  (`host`, `above`, `of`, `top_from`). Put the body first.
- **Validation**: `validate_program(program)` (program.py) runs before any fit and lists problems: duplicate
  names, unknown types or rules, references to parts that are not EARLIER in the list, a prior off the grid, a
  missing frame. `run_program` raises ValueError on any of them.
- **optional** (default true): a part whose rule assigns no points, or whose fit fails, is skipped and reported. The
  first part is never optional.

## 3. Scale: relative windows

`s` is the robust RMS radius of the object's observed points: the RMS distance to the coordinate-wise median after
dropping the 2 % farthest points (1.5 mm voxel-downsampled). The report prints it as `s_mm`.

Every size-dependent window of a part is `max(floor, frac × s)`:
- Defaults are the hand kits' absolute windows divided by s of the episode each kit was developed on (`rel(value,
  S_REF_x)` in parts.py). The defaults therefore reproduce the hand kits, and they scale to other objects.
- Override any window in `params` by its name:
  - a bare number is a fraction of s;
  - `{"frac": f, "floor": m}` sets both;
  - `{"abs": m}` is an absolute value in metres (avoid this; it makes the program object-size specific).

Absolute constants remain only for the sensor and the marker hardware:
- 1.5 mm voxel;
- 2 mm robust-loss scale;
- residual noise band APP_D = 8 mm;
- view-class cosines;
- assignment cluster voxel 3 mm;
- marker balls: 7 mm radius prior, size, gap and stem tests (BALL in parts.py).

## 4. Assignment rules (`assign`)

`resid(X)` of a part is how far a point lies outside the part. A point is **unexplained** by a list of parts if it
lies more than `band` outside every one of them. The default band is APP_D = 8 mm; set `"band": f` (fraction of s)
or `{"abs": m}` to change it.

| rule | fields | points given to the part |
|---|---|---|
| `all` | none | every observed point |
| `residual` | `of` (list), `band` | points unexplained by the parts in `of` |
| `largest_cluster_beyond` | `of`, `reach_of` (default `of[0]`), `k` (fraction of s), `min_pts` (200), `cluster_vox` | the largest voxel-connected cluster of the residual whose 99th-percentile reach beyond `reach_of` exceeds k·s. Reach: distance from the axis minus the radius for revolved parts, distance beyond the bounding sphere otherwise. Use it for a handle that sticks out. |
| `largest_cluster_extent` | `of`, `frame_of`, `min_extent` (fraction of s), `min_pts` (100) | the largest residual cluster longer than min_extent·s. Length is measured in the host's plane (e1, e2) for sheets and lathes, along the cluster's PCA axis otherwise. Use it for a strap or arch over a lid. |
| `clusters_dir` | `of`, `host` (default `of[0]`), `dir` (`+axis`/`-axis` = host axis; `+up`, `-up`, `+x`, `-x`, `+y`, `-y` = support frame), `min_offset` (fraction of s), `min_pts` (60) | every residual cluster whose centroid lies beyond the host's centre along `dir` by more than min_offset·s (e.g. a knob on top of a lid, feet under a body) |
| `slab` | `axis` (x, y or h), `min_from` / `max_from` (`"tall_lo"`, `"tall_hi"` or a fraction of s), `min_margin` / `max_margin` (fractions of s) | points with `min_from + min_margin < coord < max_from + max_margin` in the support frame |
| `cavity` | `of` (a `tube_rrect`), `inset` (fraction of s), `beyond_margin` | points inside the tube's inner face by more than inset·s. With `beyond_margin`, only points past the host's cavity clip (set by `clip_cavity`) by that margin. Use it for things standing in a tray. |

Balls use `residual` and run their own shared detector on the residual's compact clusters.

## 5. Part types

Each part fits its parameters by robust estimation: medians over azimuth sectors, trimmed planes, or soft-L1 least
squares.

Every part reports:
- `k`, the number of free parameters;
- `bounds_hit`, the parameters that ended on a bound or a clip;
- `params`;
- `diag`;
- a residual, by ownership: each observed point belongs to the nearest part, and the report gives n, median and p90
  distance.

A bound hit means the data pushed a parameter to its limit (for balls: the radius fell back to the 7 mm prior). Look at it before trusting the part.

| type | models | when you see in crops / point renders | key params (defaults) | k |
|---|---|---|---|---|
| `lathe` | thin-walled body of revolution (cups, pots, bowls, bottles) | round in every view, rim or opening | `method`: `polar` (closed floor; profile in polar coordinates about an interior point, so a rounded bottom corner is followed; robust axis search over a hemisphere) or `height` (per-height-bin profile; `floor` = `base` (closed, cavity to base + t) / `observed` / `solid` / `open` (bottomless ring)); `thick` (1.0) | 5 + profile knots |
| `sheet_of_revolution` | domed lid or plate seen from one side | flat round thing, underside never seen | none needed. The underside is top − t (prior grid); a quadratic dome under an arch | 5 + knots |
| `plate` | flat piece in its own plane | handles, fins, boards | `outline`: `bar` (straight bar with a rounded tip, optional hole, inner end inside `host`'s wall; thickness from side-seen points, else t), `occupancy` (traced outline), `rect` (min-area rectangle); `host` | 9 (bar), 5 + 2·vertices |
| `plate_set` | several plates | dust-pan sides, boxes made of sheets | `max_plates` (4), `min_pts` (300), `outline` | sum |
| `tube_rrect` | rounded-rectangle tube in the support frame | trays, holders, open boxes standing on the table | `wall`: `thin` (thickness t; lean, draft and corner free; `above`: host whose top hides the lower outer face) or `lip` (thick rim of width s0, inner face sloping by s1, outer face leaning by dout, top = robust plane; `x_min_from`: `tall_lo`, `align_frame` (true)); `carve`: `self` or `all` | 9–13 |
| `strap` | rectangle swept along a fitted centreline | arched handle over a lid, bucket handle | `host` (ends run down into the host's mid-surface) | 2 + knots |
| `cone_array` | rows of tapered round pegs, one template per row | peg rows in a dish rack | `host` (the tray: pegs stand on its floor), `top_from` (upper limit); windows `slice0`, `slice1`, `row_dy`, `peg_r` | knots + 2·pegs |
| `rounded_box` | box with rounded edges in the PCA frame | blocks, bricks | `pct` (1), `r_frac` (0.2) | 10 |
| `ball` | marker balls on optional stems (one shared detector) | grey spheres on short stems | `of` (host surface), `require_cap` (keep only curved caps), `reject_inside` (a tube: no balls over its cavity), `stems` (true) | 4 per ball |
| `splat` | voxel splat and marching cubes of each large cluster | anything irregular the vocabulary lacks | `min_pts` (400), `combine` = `union` (watertight) or `concat` | 0 |
| `tsdf_patch` | faces of OUR library TSDF mesh outside the listed parts | fallback for parts we cannot model | `of`, `margin` (APP_D); needs `lib`. Not watertight. | 0 |

How each part decides what is unexplained (`resid`):
- `lathe`:
  - `polar`: outside the solid profile hull by its distance to the outer curve;
  - `height`: radial excess over the outer profile, or beyond the ends, as lathe_obs.py does.
- `sheet_of_revolution`: height above the top surface, within the edge radius plus a band. Points beyond that band
  are not its business.
- `plate` bar: L∞ distance outside the bar box.
- `strap`: distance to the swept surface.
- All other parts: signed distance to their sampled surface.

## 6. Attachment, union and carving

- **Attachment by fitting**:
  - a `plate` bar with `host` starts inside the host lathe's wall (radius < rmax − 2t);
  - a `strap` with `host` runs its ends down to the host sheet's mid-surface;
  - a `cone_array` stands on its host tube's floor;
  - a `ball` stem runs to the nearest host surface, but only where points support it.
- **Attachment rules** (`attach` on the later part, applied right after it is fitted):
  - `{"mode": "clip_cavity", "to": HOST, "face": "+x"}`: this tube ends the host tube's cavity. The host keeps its
    cavity only beyond this part's outer face (x > face, at the host's top height). Later `cavity` assignments and
    `reject_inside` use the clip.
- **Union**: all part solids are unioned with manifold3d. A tube with `carve: all` (default for `thin`) then has its
  cavity subtracted from the whole assembly, which removes the host's material inside it. A tube with `carve: self`
  (default for `lip`) subtracts its cavity from itself only, so things standing in it survive.
- `tsdf_patch` and `splat` with `combine: concat` are concatenated after the union. Their mesh is then not a single
  watertight solid; check `watertight` in the report.

## 7. Thickness

- Parts use t only where the wall was not seen from both sides:
  - `lathe` (inner and outer wall), `plate` bar and `strap` (side-seen points), `plate` occupancy (two faces) measure
    their thickness when the evidence exists (`t_src: two_sided` or `side`), otherwise they fall back to t
    (`t_src: prior`);
  - `tube_rrect` 'lip' fits its lip width s0 and inner slope s1 from the points; its floor plate and the `thin`
    tube's wall use t;
  - `sheet_of_revolution` always uses t (its underside is never seen).
- Run all three grid values and let the GT-free gate choose. Never pick t from a scan.

## 8. Report (OUT.json)

- **Header fields**: `s_mm`, `t_mm`, `n_pts`, `faces`, `watertight`, `bodies`, `area_cm2`, `k_total`, `bounds_hit`,
  `sec`.
- **`obs_to_model`**: median and p90 distance from all points to the nearest part.
- **Per part**:
  - `n_assigned`, `k`, `params`, `bounds_hit`;
  - `residual` (n_owned, med_mm, p90_mm);
  - `diag` (fit details, e.g. the lathe's `t_src`, the tube's class counts and per-class residuals, the ball
    detector's accepted and rejected clusters with reasons);
  - `skipped` or `failed` when the part dropped out.

Read these before trusting a mesh:
- a part with many owned points and a large median residual is the wrong shape;
- a part with `bounds_hit` is at its limits;
- `bodies` > 1 means floating pieces, for example balls without stems.

## 9. Worked examples (`programs/`) and what they reproduce

Each example program reproduces a hand kit on the episode that kit was developed on (test_programs.py, [M]):

| program | object type | reproduces |
|---|---|---|
| `lathe_bar_balls.json` | open container + flat bar handle + balls | `prim_potlid.py pot --variant fit` |
| `sheet_strap_balls.json` | domed lid + arched strap + balls | `prim_potlid.py lid --variant fit` |
| `lathe_splat.json` | cup: lathe + splatted appendages | `lathe_obs.py --appendages 1` |
| `tray_holder_pegs_balls.json` | tray + tall holder at one end + peg rows + balls | `prim_rack.py build` (single episode) |

Measured 2026-10-27 (test_programs.py, final run under `scratchpad/auto/stage1/parts-dsl/final/`; t = 2.5 mm;
fidelity = obs_fidelity sum on the episode's own points, GT-free; mesh distance = exact closest-point distances of
20k samples each way):

| case | fidelity DSL / hand kit (mm) | ratio | median sym. distance (mm) | p90 (mm) | area ratio |
|---|---|---|---|---|---|
| lathe_bar_balls, ep41 | 2.907 / 2.907 | 1.000 | 0.000 | 0.000 | 1.000 |
| sheet_strap_balls, ep2 | 1.685 / 1.683 | 1.001 | 0.003 | 0.010 | 1.000 |
| lathe_splat, ep21 | 4.080 / 4.104 | 0.994 | 0.000 | 0.004 | 1.000 |
| tray_holder_pegs_balls, ep13 | 7.411 / 8.511 | 0.871 | 0.013 | 4.831 | 0.945 |

- The tray program differs from the incumbent only in the floor plate. The incumbent took a floor depth shared by
  five episodes; the DSL program uses this episode's table, as required for single-episode eval meshes.
- With the incumbent's depth forced (a development-only `floor_depth` override, `diag_floor/`), the tray matches it:
  - median 0.011 mm, p90 0.098 mm;
  - fidelity 8.484 / 8.511.
- The sheet program also matches the clean-up round at t = 1.5 and 4.0 mm: fidelity ratio 1.001 and 1.000, median
  0.003 mm.

**Same programs, unchanged, on the objects' other episodes** (`cross_*`, [M]). The windows now scale with each
episode's s, while the hand kits used absolute windows:

| case | fidelity ratio vs hand kit | median distance (mm) |
|---|---|---|
| pot, episodes 42–45 | 0.982–1.017 | 0.01–0.13 |
| cup, ep22 | 1.030 | 0.13 |
| rack, episodes 12 / 26 / 27 / 31 | 0.923 / 0.882 / 0.859 / 1.005 | 0.07 / 1.51 / 0.43 / 0.06 |

- The rack differences are mostly the floor depth. At ep26 the holder also hit its corner-radius bound.
- The cup at ep12 and ep13 and the lid at ep0 have no hand-kit mesh to compare with.
- The cup ran at both episodes (fidelity 2.30 and 2.92 mm).
- The lid at ep0 fails with an explicit error: only 396 points after downsampling, a known bad track.

**Scale test** (all windows relative, [M]): with points, cameras and voxel scaled by 1.3, the outputs scaled back
match the unscaled ones:
- cup: 0.000 mm;
- pot (balls removed): 0.001 mm;
- lid (balls removed): 0.000 mm;
- rack (balls removed): 0.053 mm; the robust-loss scale stays absolute.

## 10. Authoring checklist for a new object

1. **Look at the crops and the point renders.** List the visible pieces, then for each one decide:
   - Which part type matches it (section 5)? Prefer the fewest parts that explain the points.
   - Is it a body (fit it to `all`) or an appendage (fit it to a residual rule)?
   - Which side of it is never seen? There the shape comes from the prior t, so keep that surface small.
2. **Order the parts.** Body first, then the large appendages, then balls last with `of` listing every surface they
   may sit on.
3. **Pick assignment rules from section 4.**
   - Start with the defaults.
   - Express any window you change as a fraction of s.
   - Write in `doc` why you chose each rule.
4. **Run the program at t = 1.5, 2.5 and 4.0 mm and read the report** (section 8):
   - owned-point residuals near the stereo noise (median ≈ 1–3 mm);
   - few or no bound hits;
   - `watertight: true`;
   - a sensible number of bodies.
5. **Check fidelity.** Compare with the generic shell route (shell.py) and the library mesh by GT-free fidelity
   (gates.py), not by scan score.
6. **Mind the scorer.** CD-O normalises scale by the area-weighted RMS radius. Extra hidden surface (thick slabs,
   internal faces, splats inside the body) and missing surface both shift it.
   - Prefer `union` over `concat`.
   - Keep unseen faces at the prior thickness.

## 11. Limits (open)

- **The vocabulary is small.** There are no swept tubes of arbitrary section, no lofts, and no non-convex tube
  outlines. A `splat` or `tsdf_patch` fills gaps.
- **The marker-ball detector is shared hardware logic.** The pot's floating balls (no stem evidence) stay floating.
- **`tube_rrect` assumes a support frame** (table cut) and one tall end. It does not handle objects held in the hand
  during the whole episode.
- **The default windows are calibrated on four development episodes.** On a new object of very different size, check
  the bound hits; the windows scale with s, but the sensor floors do not.
- **Count thresholds are not density-normalised** (points per (bin, sector) cell, cluster minimum sizes). The same
  object seen with a denser point sample can change which bins count as seen: in the 'physical' scale test (test 2)
  the cup's two-sided wall estimate moved from 1.96 to 3.9 mm. Treat `t_src: two_sided` values with care and keep
  the t grid runs.
- **Hidden constants of the hand kits remain**: e.g. 2 mm corner-radius floors in tube sections, the 10 mm cavity
  overshoot above a tube top, 3.5 mm stems; they are geometric details, not fitted windows.
