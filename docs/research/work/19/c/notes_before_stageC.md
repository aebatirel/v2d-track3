# 19 — Collision hulls: can the CoACD inflation be removed on the asset side? (started 2026-10-06)

Dig 19 (round 4, "D18 Hull inflation" in 16-synthesis §4). Markers: [V] verified, [E] estimate, [H] hypothesis.
Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/19/. Source pin: nvidia-isaac/video_to_data @
8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef (evaluator pin). Background: note 15 §C2/C4 (GT contact states 4-15 mm
inside the coacd 1.0.11 hulls, threshold 0.05, preprocess auto).

## Stage A — how FlashCHORD loads and decomposes collision meshes (code @ pin)

Log (append-only):
- 2026-10-06 A1 [V code @8c778f90] Fetched via `gh api .../contents/<path>?ref=8c778f90...` into
  work/19/src/ (file names = repo path with `/`->`_`; sizes equal the git tree at the pin, tree in work/19/tree.json):
  assets/{mesh,registry,__init__}.py, scene/{objects,builder,setup,collision,support,__init__}.py,
  configs/scene/*.yaml, configs/collision/*.yaml, evaluation/harness.py, configuration.py, runtime/sim.py, pyproject.toml.
- A2 [V code] `assets/mesh.py:62-96 convex_decompose(vertices, faces, threshold=0.05, max_convex_hull=-1,
  preprocess_mode="auto", cache_dir=None, **coacd_kwargs)` -> `coacd.run_coacd(coacd.Mesh(v,f), **params)` with only
  those three params (+ any kwargs; none passed by callers). Disk cache: `$FLASH_CHORD_CACHE_DIR` or
  `<flash_chord/assets>/.cache/convex/<sha1[:16]>.npz`, key = sha1("v1" + float64 vertex bytes + int64 face bytes +
  repr(sorted(params))) (`mesh.py:32-43,82-85`). The cache is keyed by OUR geometry, so it cannot be pre-seeded from
  outside the evaluator container; it only makes rebuilds fast. There is no "skip if already convex" or "use as is" path
  in mesh.py: every colliding mesh shape goes through run_coacd (or its cached result).
- A3 [V code] `scene/objects.py:159-210 _decompose_object_collision`: iterates EVERY imported shape of the object
  component whose type is `GeoType.MESH` AND whose flags include COLLIDE_SHAPES (lines 165-172). Per such shape it
  decomposes the shape's own source vertices/indices (unscaled, shape-local frame), adds each hull as a new invisible
  mesh shape on the SAME body with the SAME shape transform and scale (`add_shape_mesh(body, xform=transform,
  scale=scale)`), density 0 (no mass contribution), material (ke, kd, kf, ka, mu, restitution) copied from the original,
  then clears COLLIDE_SHAPES on the original (line 201). All new hulls of one object are pairwise collision-filtered
  (203-209). Non-mesh collision shapes (URDF box/cylinder/sphere/capsule primitives) are NOT touched: they stay as exact
  analytic colliders. => (a) multiple collision meshes per link are supported, each decomposed independently;
  (b) primitives bypass CoACD entirely.
- A4 [V code] `objects.py:375-413 _spawn_component`: `component.add_urdf(source=asset.urdf_path, floating=True,
  enable_self_collisions=False, collapse_fixed_joints=True, ignore_inertial_definitions=False)`, then decompose
  (if `decompose_collision`), then raises if no active collision shape remains. Objects are imported one URDF per asset,
  multi-link allowed (fixed joints collapsed, one free root required, movable joints must be declared revolute/prismatic).
- A5 [V code] Parameters are not configurable at eval: `scene/setup.py:68-85` never passes `decompose_params`, so
  `build_scene(decompose_params=None)` -> `spawn_objects(decompose_params={})` -> mesh.py defaults. configs/scene/
  eval.yaml, train.yaml, replay.yaml all set `decompose_objects: true`, scale 1.0-1.0, friction 1.0.
- A6 [V code] `builder.py:302-338,359` the only place that rejects non-mesh object collision shapes is
  `_object_lowest_world_z`, called only when object scale != 1 (`_apply_object_scales` returns early at 359 when all
  scales are 1.0). Eval/train configs fix scale 1.0, so primitive collision shapes are accepted [V code].
- A7 [V code] Where the URDF comes from: `data/motion_v1.py:250-266` reads the reference parquet's
  `object_urdf_paths` column (one URDF per rigid object body) -> `assets/registry.py:163-194
  resolve_object_asset_specs` -> `ObjectAssetSpec(urdf_path=resolve_asset_path(p, reference_path=parquet))`.
  `resolve_asset_path` (registry.py:43-65) uses the stored path verbatim if it is an existing file; otherwise it re-roots
  on the last `/assets/` component (first beside the reference parquet's own `.../assets/` ancestor, then FlashCHORD's
  vendored assets) or on `/data/object_assets/`. So the URDF (and the meshes it references) are named by OUR
  reference parquet, i.e. they are our inputs.
- A8 [V code] The eval harness rebuilds the scene from the CHECKPOINT's saved config, not from configs/scene/eval.yaml:
  `evaluation/harness.py:376-420 evaluate_checkpoint` -> `apply_evaluation_composition` (216-251) overrides only
  world_count, auto_reset, voc (0), reset seed 42, always_reset_to_first_frame and termination limits; then
  `setup_scene(..., decompose_objects=cfg.scene.decompose_objects, contact_friction=..., collision=cfg.collision ...)`
  with the checkpoint's own values. `task.parquet` is the checkpoint's saved reference path (optionally re-rooted by
  `source_root`). Kit README (tracks/track_3/README.md): participants run the kit's `flash_chord/scripts/
  evaluate_policy.py` themselves "in a compatible FlashCHORD environment"; the CSV carries checkpoint, eval script and
  eval-code SHA-256 (harness.py:115-157: eval-code hash covers only evaluation/{__init__,harness,metrics,rollout}.py)
  plus a COMMIT_URL that organisers can inspect. => Inputs that are OURS: the reference parquet (incl.
  object_urdf_paths), the URDF files, every mesh they reference, URDF inertials, and the checkpoint (whose saved config
  includes scene.decompose_objects). FIXED: FlashCHORD code at the pin (mesh.py call, coacd==1.0.11, newton==1.2.0,
  trimesh==4.12.2, mujoco-warp 3.8.1), evaluation composition, scorer. [E] Flipping `scene.decompose_objects: false` in
  our training config would be honoured by the harness, but it is a physics-configuration change, not an asset change;
  treat as off-limits unless organisers approve (16-synthesis §5 Q4).
- A9 [V code, newton v1.2.0 `newton/_src/utils/import_urdf.py`, fetched to work/19/newton/] URDF parsing:
  every `<collision>` element of every link is parsed (line 622 `findall("collision")`; `parse_visuals_as_colliders`
  default False, FlashCHORD does not set it), each yielding shapes on that link (`parse_shapes` 403-515): `<box>`,
  `<sphere>`, `<cylinder>` (axis Z, `length`), `<capsule>` (`radius`, `height`) become analytic Newton shapes;
  `<mesh filename scale>` -> `load_meshes_from_file(resolved, scale=scale_attr, maxhullvert=Mesh.MAX_HULL_VERTICES)`
  -> one or more mesh shapes. Collision origin `<origin xyz rpy>` becomes the shape transform (kept by
  `_decompose_object_collision`). With `collapse_fixed_joints=True`, extra links joined by fixed joints are merged into
  the root body, so collision geometry may also be spread over several fixed-joint links. `<inertial>` overrides mass,
  COM and inertia (639-667) because FlashCHORD passes `ignore_inertial_definitions=False`; collision-shape density then
  does not set the mass. Mesh URIs: absolute, relative to the URDF directory, `package://`, and http(s) are resolved
  (`resolve_urdf_asset` 227-311).
- A10 [V code, newton v1.2.0 `utils/mesh.py:478-882 load_meshes_from_file`] Mesh files are read with
  `trimesh.load(filename, force="mesh")` (line 690; trimesh==4.12.2 pinned) with default processing, scaled per axis
  (vertex * scale, so CoACD sees SCALED vertices; shape_scale stays 1). `force="mesh"` concatenates a multi-geometry
  GLB/scene into ONE mesh, so several convex pieces packed in one file reach CoACD as one (multi-component,
  self-intersecting) mesh. Conversely the loader SPLITS one file into several mesh shapes by per-face material
  (`visual.face_materials`), DAE material groups, unique face colours, or unique vertex-colour face averages
  (lines 762-853) -- each split piece is an open patch that CoACD then decomposes separately. => Safe asset format for
  a hand-made collision piece: one colourless, untextured, watertight mesh per file (STL/OBJ without colours/materials),
  one `<collision>` element per piece. [E: the split behaviour on our textured GLBs still needs an empirical check with
  trimesh 4.12.2; see A11.]
- A11 [V code, newton v1.2.0 `geometry/types.py:135,190-192`, `solvers/mujoco/solver_mujoco.py:4702-4740`] Every
  object hull is created in objects.py as `newton.Mesh(v, f, compute_inertia=False)` without `maxhullvert`, so it gets
  `Mesh.MAX_HULL_VERTICES = 64`. SolverMuJoCo exports each mesh shape as a MuJoCo mesh asset
  `spec.add_mesh(uservert=v*shape_scale, userface=f, maxhullvert=64)`; MuJoCo collides every mesh geom through its convex
  hull (qhull, stopped after maxhullvert vertices => for a hull with >64 vertices an INNER approximation using a
  64-point subset [E from MuJoCo docs; not re-checked in mujoco 3.8.1 source]). Geom `gap` is always 0 (line 4793) and
  margins are zeroed when the model has boxes or multiccd meshes (3183-3184, 4795-4799). Planar mesh colliders raise
  under MuJoCo contacts (4729-4734), so a collision piece must have volume. => The effective collider of each hull =
  convex hull of <=64 of its vertices; hand-made pieces should keep <=64 hull vertices to be represented exactly.
- A12 [V data, work/19/a_loader.py -> a_loader.out; own venv work/19/venv with the pinned trimesh 4.12.2, numpy 2.4.6]
  Mimicking newton's `load_meshes_from_file` branch logic on the 10 public URDF collision meshes: every file loads as
  ONE TextureVisuals mesh, branch "single" -> exactly one Newton mesh shape per object (no material/colour split).
  The visual GLBs used as collision (cups, pan, rack, pitcher, pot, lid) arrive as near triangle soups
  (V ~= 3F: beige cup V 295,579 / F 98,563; rack 298,326 / 99,460; pot 293,329 / 97,803; lid 297,615 / 99,231),
  because trimesh's default merge keeps UV seams and these scans have per-face UVs; the dedicated *_collision.glb files
  (sweeper V 55,354 / F 96,428; boards 17,237 / 34,468 and 14,507 / 29,008) are welded (V ~= F/2). NONE is watertight
  as loaded (`is_watertight` False for all 10). [H] So CoACD's `preprocess_mode="auto"` manifold check most likely
  fails for every public asset and the voxel manifold preprocessing (default resolution 50 over the bbox) runs, which is a
  candidate inflation source on top of the 0.05 concavity threshold -- to be tested (A13).
- A12b [V data, work/19/a_weld.py -> a_weld.out] Welding by position (NOT done by newton) closes the dust pan, sweeper
  collision mesh and both boards (watertight, 1 body) but the cups, rack, pitcher, pot and lid scans still have open
  boundaries (46-685 boundary edges, 2-4 bodies = floating scan fragments). As newton loads them, even the boards fail
  watertightness (one duplicate vertex: loaded V 17,237 vs welded 17,236) and the sweeper keeps 7,156 seam duplicates.
- A13 [V code, CoACD 1.0.11 = tag commit b678aa08, fetched to work/19/coacd/] What run_coacd does with our mesh:
  `public/coacd.cpp:75-111`: `Model::Load` copies vertices/indices verbatim (NO vertex welding, model_obj.cpp:556-584);
  `Normalize()` maps the bbox centre to 0 and the LONGEST extent L to length 2 (model_obj.cpp:617-643); then with
  `preprocess_mode="auto"` `IsManifold` (process.cpp:13-100) is INDEX-based: fails on any repeated directed edge
  ("wrong orientation"), any edge without its opposite ("unclosed"), or any triangle-triangle self-intersection (BVH);
  only a pass skips preprocessing. On failure `ManifoldPreprocess` (preprocess.cpp:7-63) rebuilds the surface from an
  OpenVDB signed distance field of the normalized mesh scaled by prep_resolution=50 (voxel = L/100) and extracts the
  iso-surface at dmc_thres=0.55 voxel, i.e. an outward offset of ~0.0055 L plus voxel-scale thickening of thin walls
  (rack L 510 mm: voxel 5.1 mm, offset 2.8 mm; pot 357: 3.6 / 2.0; lid 190: 1.9 / 1.0; cups ~170: 1.7 / 0.9;
  sweeper 143: 1.4 / 0.8). Python defaults used (python/package/__init__.py:81-99): preprocess_resolution 50,
  resolution 2000, mcts_nodes 20, mcts_iterations 150, mcts_max_depth 3, pca False, merge True, decimate False,
  max_ch_vertex 256 (inactive without decimate), extrude False, apx_mode "ch", seed 0, real_metric False.
  The concavity threshold 0.05 is in NORMALIZED units (L = 2), i.e. a hull may deviate from its part by up to
  ~0.025 L [E: cost = max(Hausdorff, rv_k*volume term), src/cost.cpp not re-read]: rack 12.7 mm, pot 8.9, lid 4.8,
  blue cup 4.3, sweeper 3.6 mm. [H] These per-object tolerances line up with note 15's measured GT-contact depths
  (sweeper/rack 10.5-15.3, pot/rack 7.2-9.8, cup/rack 6.0-8.4, lid/pot 7.7-8.4, nest 4.1-4.3 mm), so the threshold
  scaled by the WHOLE object's size is the likely main driver and preprocessing a secondary one. Because both scale
  with the size of the mesh handed to CoACD, splitting an object into several smaller, watertight collision meshes
  shrinks both terms per piece.
- A14 [V run, work/19/a_passthru.py, pinned coacd 1.0.11 from 15-verify/pylib11, exact FlashCHORD call] Pre-decomposed
  convex pieces pass through unchanged when the piece is welded and closed: box 120x30x200 mm (8 v), 24-segment
  cylinder (48 hull v), 96-segment cylinder (192 hull v), 300x200x3 mm plate -> 1 hull each, every output vertex
  exactly on the input's own hull (max outside 0.000 mm). The SAME shapes as unwelded triangle soups trigger
  "Unclosed mesh" -> preprocessing -> 1 hull inflated by 0.0055 L as predicted (cylinder L 100 mm: +0.24..+0.55 mm,
  1216 hull vertices; plate L 300 mm: +0.44..+1.65 mm). => YES, pre-decomposed hull files are effectively accepted, but
  only through CoACD as a no-op: each must be its own mesh shape (own `<collision>` element or own file), index-welded,
  closed, consistently oriented, free of self-intersection, and ideally <=64 hull vertices (A11). A non-convex piece
  would be re-decomposed with a tolerance of ~2.5 % of that piece's own longest extent.
- A15 [V run, end-to-end on CPU: work/19/a_mkurdf.py -> a_urdf/probe.urdf; work/19/a_probe.py -> a_probe.out; own venv
  with newton 1.2.0 + warp 1.14.0 + trimesh 4.12.2; FlashCHORD's `_decompose_object_collision` executed verbatim from
  the pinned objects.py (ast-extracted), mesh.py copied verbatim into work/19/shim, coacd 1.0.11]. Probe = one link with
  7 `<collision>` elements + one fixed-joint child link with 2. `add_urdf` with FlashCHORD's flags gives 1 body,
  10 collision shapes: welded box STL (8 v) -> 1 hull, exact; 24-seg cylinder STL -> 1 hull (48 v); the same cylinder as
  an untextured OBJ triangle soup is WELDED by trimesh's default processing (50 v) -> 1 exact hull (only UV-carrying
  files such as the textured scan GLBs stay unwelded, A12); `<box>`, `<cylinder>` and the child link's `<sphere>` stay
  analytic shapes with collide=True after decomposition (CoACD never sees them); a GLB holding 2 geometries loads as ONE
  16-v mesh shape -> CoACD returned 2 exact hulls here (disjoint closed boxes; overlapping pieces would fail the
  self-intersection check and be voxel-remeshed); a 30 mm cube with 2 face colours is SPLIT into 2 open 7-v patches ->
  17 hulls, all +0.16 mm outside the cube (= 0.0055 L preprocessing offset at L 30 mm); the child link's mesh with
  `scale="0.5 0.5 0.5"` arrives pre-scaled (8 v). Total 23 hulls; every original mesh shape is left non-colliding.
  Mass: the root link's `<inertial>` (0.3 kg) is kept, but the collapsed fixed-joint child without `<inertial>` adds its
  density-derived mass (body mass 0.31 kg) -> keep all collision on the root link or give every link an inertial.
  Cache: 7 npz files written under `$FLASH_CHORD_CACHE_DIR/convex/` (one per distinct mesh geometry; identical
  geometry+params reuse one file).
- A16 [V code, newton import_urdf.py:227-311,473-481] A mesh URI that does not resolve only emits a warning and the
  `<collision>` element is silently dropped (FlashCHORD raises only if NO collision shape survives,
  objects.py:411-413). Relative URIs resolve against the URDF's directory; `package://` against the URDF's folders.
  Portability for organiser re-runs: the URDF path stored in the reference parquet is used as-is if it exists, else
  re-rooted at the last `/assets/` component (A7), so ship the URDF and meshes under an `assets/` tree beside the
  reference parquet and reference meshes relative to the URDF.
- A17 [V code, CoACD 1.0.11 src/cost.cpp:9-89, process.cpp:238-311,495] Upgrades A13's [E]: a part's cost is
  max(face-sampled Hausdorff distance between the part and its convex hull, rv_k=0.3 x equivalent-sphere radius of the
  volume difference), both in normalized units; a part is cut further only while cost > threshold (process.cpp:495),
  and MergeConvexHulls merges neighbouring hulls while the merged cost stays <= threshold (293-296). So with
  threshold 0.05 every output hull may sit up to 0.05 x L/2 = 0.025 L from the surface of the mesh it was cut from
  (L = longest bbox extent of the mesh handed to run_coacd). `real_metric` (absolute threshold) exists in 1.0.11 but
  FlashCHORD never passes it. Also [V diff]: the kit's flash_chord/scripts/evaluate_policy.py is byte-identical to the
  pin's scripts/evaluate_policy.py.

### Stage A summary (answers)
| Question | Answer | Evidence |
|---|---|---|
| Who decomposes? | FlashCHORD `scene/objects.py:_decompose_object_collision`, every build, when the checkpoint config has `scene.decompose_objects: true` (all shipped configs) | A3, A5, A8 |
| Exact call | `coacd.run_coacd(coacd.Mesh(v_f64, f_i64), threshold=0.05, max_convex_hull=-1, preprocess_mode="auto")`, other args at 1.0.11 defaults (prep res 50, dmc 0.55, merge on, seed 0); not configurable | A2, A5, A13 |
| Unit of decomposition | each colliding MESH shape separately (one per `<collision><mesh>` file, more if newton splits a file by material/colour; a multi-geometry file is concatenated into one) | A3, A10, A15 |
| Multiple collision meshes per link? | Yes: all `<collision>` elements of all links (fixed joints collapsed onto the root) are imported; each mesh is decomposed on its own; all resulting hulls of one object are mutually filtered | A3, A9, A15 |
| Primitives? | `<box>`, `<sphere>`, `<cylinder>`, `<capsule>` are kept as exact analytic colliders, never decomposed; accepted at scale 1.0 (eval/train configs) | A3, A6, A15 |
| Pre-decomposed hull files accepted? | Not as a format, but effectively yes: a convex piece that is index-welded, closed, consistently oriented and non-self-intersecting passes the manifold check and comes back from CoACD as exactly its own convex hull (0.000 mm); keep <=64 hull vertices (MuJoCo maxhullvert) | A11, A14, A15 |
| Caching | disk cache `$FLASH_CHORD_CACHE_DIR` or `flash_chord/assets/.cache/convex/<sha1(geometry+params)[:16]>.npz`; keyed by our geometry, purely a speed-up, cannot inject hulls | A2, A15 |
| Inflation mechanism | (1) concavity tolerance 0.025 x L of the mesh handed in (rack 12.7 mm, pot 8.9, lid 4.8, cup 4.3, sweeper 3.6); (2) for non-manifold input (all 10 public assets as newton loads them, A12) voxel remesh at L/100 with +0.55-voxel offset and thin-wall thickening | A12, A13, A14, A17 |
| Ours | reference parquet `object_urdf_paths`, URDF (links, `<collision>` elements, primitives, mesh files, scale, `<inertial>`), all mesh files, the checkpoint (incl. its saved scene config) | A7, A8 |
| Fixed | FlashCHORD @8c778f90 code and its pins (coacd 1.0.11, newton 1.2.0, trimesh 4.12.2, mujoco(-warp) 3.8.1), CoACD parameters, eval composition, MuJoCo maxhullvert 64, scorer | A2, A5, A8, A11 |

Implication for stages B/C [H]: the inflation can very likely be removed on the asset side, without touching the
evaluator, by authoring our collision geometry as (i) analytic primitives where shapes allow (rack dividers/fins as
boxes, sweeper ring/handle as capsules/boxes, flat boards as boxes) and (ii) many small, welded, closed convex pieces
(<=64 vertices, one `<collision>` element and colourless STL per piece, all on the root link) for curved walls (cups,
pot, lid). Each piece then passes CoACD unchanged, so the colliders equal our own geometry. Remaining risks to measure:
penetration-free authoring of GT contact states against our pieces; MuJoCo contact count/perf with many geoms; mass
via explicit `<inertial>`; and whether organisers regard hand-authored collision geometry as acceptable (16-synthesis
§5 Q4). Keeping `decompose_objects: true` avoids any physics-configuration change.

## Stage B — offline watertight remesh / split / exact re-decomposition (coacd 1.0.11, CPU)

Log (append-only). Work dir: work/19/b/. Python: own venv work/19/venv (trimesh 4.12.2, numpy 2.4.6) + added there with
uv: manifold3d 3.5.4, scikit-image 0.26.0, fast-simplification 0.2.0, libigl 2.6.3 (fast winding number), rtree 1.4.1.
coacd 1.0.11 from work/15-verify/pylib11. Baseline hulls (V0, as newton loads the scan) = work/15-verify/hulls11.
- 2026-10-06 B1 [V data, b/b_holes.py -> b_holes.out, b_loops2.py -> b_loops2.out] Hole structure of the
  position-welded scans: lid 21 small loops (<= 8 mm) + one 17 mm floating fragment; pot 11 loops incl. two LARGE ones
  (165, 155 mm) + a second 159 mm body (15.6k faces); rack 23 loops (largest 87, 62, 36 mm) + 3 fragments (102, 87,
  15 mm); blue cup ONE 78 mm loop that lies inside the cup (z -59..-7 mm of a -84..+88 mm cup: the scanned inner wall
  stops short of the inner floor) + a closed inward-oriented 64 mm disc body near the top (z 75-85, vol -13.8 cm3) and a
  small sliver; beige cup one 114 mm loop + a 65 mm second body; sweeper collision mesh closed after welding.
  => Small-hole closing (morphology at a few mm) is not enough for cups/pot/rack: a flood-fill inside/outside test would
  leak through the missing inner floors into the walls. Use a generalized-winding-number (GWN) sign instead (robust to
  open scans; Jacobson et al. 2013, libigl fast_winding_number), magnitude = unsigned distance to the scan.
- B2 [V run, b/b_remesh.py, b/dbg5.py] GWN-signed remesh is WRONG for the cups and pot: the cups are stored mouth-down
  (mouth z -84, closed bottom z +87.5) and their scanned inner wall stops at the 78/114 mm loop, so the winding number
  fills the upper cavity (blue cup W volume 578 cm3 vs ~185 cm3 for walls only; pot 1214 vs 324 cm3). The baseline
  hulls (V0 = coacd's own OpenVDB preprocessing, flood-fill sign) keep the cavity open. => Switched to
  b/b_remesh2.py ("W2"): exact pseudonormal-signed distance to the welded scan on a 1 mm grid; air = voxels with
  udf > 0.6 h 6-connected to the grid boundary (may leak through scan holes); in leaked air behind a scanned surface
  the field becomes udf - t, i.e. a t = 3 mm solid shell on the material side of every single-sided wall; enclosed
  voxels are solid; marching cubes at iso +0.3 mm; specks < 0.05 cm3 dropped. Cross-sections (dbg6.py) now show open
  cavities with 2-3 mm walls where V0 has 3-6 mm walls and large merged solid blocks (pot).
- B3 [V code, CoACD 1.0.11 src/bvh.cpp:165-230, src/shape.h:82] CoACD's manifold check fails a mesh if ANY two
  triangles that share no vertex (by index, or by position within 1e-5 normalized units, e.g. 2.6 um for the rack)
  intersect by the Moeller test in FLOAT precision. [V run, b/b_mcheck.py] Raw 1 mm marching-cubes meshes pass for the
  lid and cups, but QEM/edge-collapse decimation output fails it at every tolerance tried (manifold3d simplify 0.005-
  0.05 mm; fast_simplification also leaves non-manifold edges), and the raw pot/rack meshes failed until the field was
  nudged off the iso level (|f - iso| < 0.05 h -> iso +/- 0.05 h) and degenerate triangles were disallowed. With the
  nudge all six W2 meshes pass ("Mesh Manifoldness: true"), so the exact FlashCHORD call skips voxel preprocessing.
  Decimation was therefore dropped: W2 meshes keep 77k (sweeper) to 999k (rack) faces. [E] A decimated asset would
  need a self-intersection-free simplifier verified with this exact check; a raw MC mesh of ~200k faces took 162 s
  in the exact call (lid, single core, shared host).
- B4 [V run, logs/remesh_W2.out] W2 fidelity vs the scan (pseudonormal-signed, + = outward): W2 vertices sit
  +0.30 mm (the iso offset) at the median, p99 0.37-0.55 mm (lid 1.51, beige cup 0.95: open-rim / fragment regions),
  max 0.74-3.53 mm (shell spill past open boundary edges); scan samples outside W2 by > 0.5 mm: <= 0.06 %, max 0.24-
  2.49 mm. Volumes cm3: lid 112.6, sweeper 92.5, blue cup 185.0, beige cup 152.7, pot 323.9, rack 795.8.
  Faces: 204k, 77k, 250k, 254k, 503k, 999k. (h 1.5/2 mm with iso 0 lost 11/24 % of the lid's thin rim, so 1 mm + iso
  0.3 mm was kept.)
- B5 [V run, b/b_eval.py floors -> logs/eval_floors.out] FLOOR = penetration of the GT contact states with exact,
  non-inflated colliders (the W2 solids themselves; each already +0.3 mm, so a pair carries ~0.6 mm of offset). Same
  13 states and depth definition as note 15 pen2 (max depth of sampled surface points inside the other solid):
  lid/pot 2.8-3.1 mm (W2B-in-W2A 3.2-4.0); sweeper/rack 1.8-1.9 (rack-in-sweeper 3.4-4.0); pot/rack 1.6-3.4;
  blue cup/rack 1.6-2.3; beige-in-blue nest 3.6-3.7 mm. Note-15 baseline hulls: 7.7-8.2, 10.6-15.1, 7.1-9.8, 6.1-8.3,
  4.0-4.2 mm. => [V] most of the measured GT-contact penetration is collider inflation, but a 1.5-4 mm residual is in
  the GT poses/scans themselves (pose noise, scan registration, scan thickness) and cannot be removed by any
  collider that reproduces the scan. The nest case is almost all residual (3.6 of ~4.1 mm).
- B6 [V run, logs/V1_*.log, logs/eval_obj_V0V1.out, logs/eval_pairs_V0.out, logs/eval_pairs_V1.out] V1 = W2 mesh ->
  EXACT FlashCHORD call; every log shows "Mesh Manifoldness: true" (no voxel preprocessing). Runtime 117-199 s for
  cups/pot (single process each, shared host); hulls lid 52, pot 45, sweeper 31, rack 68, blue 88, beige 41
  (V0: 48, 40, 24, 54, 81, 54). My evaluator reproduces note 15's V0 depths within 0.1-0.5 mm.
  Object inflation, hull samples vs scan (mm, p99 / max), V0 -> V1: lid 4.3/5.7 -> 3.4/5.0; pot 8.2/10.7 -> 6.2/9.4;
  sweeper 3.1/3.9 -> 2.4/3.4; rack 10.8/14.7 -> 9.1/13.4; blue cup 3.5/4.9 -> 3.1/6.5; beige 4.2/5.1 -> 3.7/6.6.
  Max values track the concavity bound 0.025 L (rack 12.7, pot 8.9, lid 4.8, cups 4.3, sweeper 3.6 mm).
  GT contact depth hullA-in-hullsB max (mm), V0 -> V1 [floor B5]: lid/pot 7.7/8.1/8.2 -> 7.0/7.7/7.0 [2.8-3.1];
  sweeper/rack ep31 f0 10.5 -> 9.7, f160 15.2 -> 6.3 [1.8-1.9]; pot/rack 9.7/7.2 -> 6.4/4.6 [3.4/1.6];
  blue cup/rack 8.4/8.3/6.3/6.1 -> 5.9/6.0/3.9/3.6 [1.6-2.3]; nest 4.1/4.1 -> 3.7/3.7 [3.6-3.7].
  => [V] Removing the voxel preprocessing alone (watertight input, same call) removes 0.4-1.1 mm on the lid/pot and
  cup/rack pairs, 3-9 mm only where a preprocessing artefact sat at the contact (sweeper f160), and leaves 4-8 mm above
  the floor for lid/pot, sweeper f0, pot/rack and cups/rack: the concavity threshold (scaled by the whole object's L)
  is the dominant cause, the voxel preprocessing secondary.
- B7 [E run, b/common.py cap_hull, b/b_cap.py -> logs/cap64.out] MuJoCo maxhullvert=64 (A11) barely shrinks these
  hulls: a greedy furthest-point emulation of qhull "TA60" (initial simplex + 60 furthest points; optimistic vs
  qhull's facet-order insertion) loses at most 0.24-0.53 mm per hull (median 0.01-0.15 mm), V0 and V1 alike, although
  74-95 % of the hulls have > 64 vertices. So hull-level depths are a fair proxy for the simulated colliders at the mm
  scale; the cap is not a hidden deflation that cancels the 4-15 mm inflation.
- B8 [V run, logs/V2_*.log, logs/eval_pairs_V2.out, logs/eval_obj_V2.out] Cause separation on IDENTICAL geometry:
  V2 = the same W2 meshes with preprocess_mode="on" (resolution 50, i.e. what the exact call does to any non-manifold
  input) vs V1 = W2 through the exact call (manifold -> no preprocessing). Contact depth max (mm) V2 -> V1:
  lid/pot 9.5/9.5/9.6 -> 7.0/7.7/7.0; sweeper/rack 9.3/15.3 -> 9.7/6.3; pot/rack 10.0/8.4 -> 6.4/4.6; cup/rack
  8.0/7.5/7.8/7.8 -> 5.9/6.0/3.9/3.6; nest 4.6/4.5 -> 3.7/3.7. Object p99 outward (mm) V2 -> V1: lid 4.4 -> 3.4,
  pot 8.5 -> 6.2, sweeper 3.3 -> 2.4, rack 11.1 -> 9.1, blue 4.2 -> 3.1, beige 4.8 -> 3.7.
  => [V] voxel preprocessing at L/100 accounts for ~1-2.3 mm of p99 object inflation and 1-4 mm of contact depth
  (9 mm in one sweeper state); the remaining V1 excess over the floor (lid/pot ~4.5, sweeper f0 ~8, pot/rack ~3,
  cup/rack ~1.5-4 mm) is the 0.05 concavity tolerance at whole-object scale. V0 (raw scan, prep 50) sits between V2 and
  V1 because W2 itself is slightly fatter than the scan (+0.3 mm iso, 3 mm shells behind single-sided walls).
- B9 [V run, b/WELD/] Cheapest fix for already-closed meshes: the position-welded sweeper collision mesh, dust pan and
  both boards pass CoACD's manifold check unchanged (no self-intersections). Exported as untextured STL or OBJ and
  re-loaded with trimesh.load(force="mesh") (newton's loader, trimesh 4.12.2) they come back with identical vertex
  count (48,198) and watertight, i.e. shipping these collision meshes without UV seams removes the voxel
  preprocessing with zero geometric change. Cups, pot, lid and rack are open scans and need a remesh (W2).
- B10 [V run, b/b_partdev.py -> logs/partdev_V1.out] The concavity-tolerance model (A13/A17) holds quantitatively:
  for V1 (manifold input, no preprocessing) the maximum outward distance of the hulls from the exact mesh they were
  computed from is 0.92-1.05 x 0.025 L for all six objects (rack 12.6 mm at L 510; pot 8.7 at 358; lid 4.6 at 190;
  blue cup 4.5 at 172; beige 3.9 at 170; sweeper 3.1 at 144), p99 0.7-0.8 x 0.025 L. CoACD uses its tolerance
  fully, so the only asset-side lever on this term is the extent L of each mesh handed to it.
- B11 [V run, b/b_split.py, b/b_decomp_parts.py, logs/split.out, logs/V4_*.log, logs/eval_pairs_split_partial.out,
  logs/eval_pairs_S60partial.out] Splitting = recursive bisection of the W2 solid's longest occupied extent until
  each part is <= Lmax; each part is closed with flat caps (marching cubes on max(field, box SDF), same nudge) and
  handed to the exact call separately (= one <collision> mesh per part). All 7+15+82+38+16+8+16+16 part meshes pass
  CoACD's manifold check. Results so far (hulls, runtime of all exact calls for that object):
  pot S120 (7 parts, L <= 120): 415 hulls, 476 s; pot S60 (38 parts): 1118 hulls, 703 s; lid S60 (16 parts, L <= 49):
  831 hulls, 515 s; sweeper S60 (8): 180 hulls, 132 s; blue cup S60 (16): 531 hulls, 444 s; beige S60 (16): 423, 317 s.
  Lid/pot contact depth max (mm): V1 7.0/7.7/7.0 -> pot S120 (lid V1) 3.7/3.7/3.6 -> lid S60 + pot S60 3.0/3.0/3.1
  = the floor (2.8-3.1). Pot/rack with pot split but rack V1: 6.5/3.3 (V1 6.4/4.6): the rack's own tolerance
  (12.6 mm) dominates there. Sweeper welded (V1w, exact scan geometry, 30 hulls): 9.5/5.9 vs V1 9.7/6.3 -> the
  sweeper/rack excess is on the rack side.
  => [V] Splitting removes the concavity term (lid/pot reaches the floor), but the hull count grows ~10-25x
  (CoACD fills each part to 0.025 L_part, and thin curved walls then need many pieces). [H] Hundreds to >1000 hulls
  per object is a MuJoCo cost/contact-capacity risk (runtime nconmax 4096/world, njmax 16384; contacts per hull
  pair), so the split level should be chosen per contact region, or the thin walls authored as primitives (stage C).
- B12 [V run, diagnostic only (threshold is fixed at eval), logs/V3_*.log, logs/eval_pairs_V3.out,
  logs/partdev_V3.out] V3 = W2 lid and pot through the exact call but threshold 0.02: hull deviation max = 0.39 x
  0.025 L (= 0.97 x 0.01 L; pot 3.45 mm, lid 1.85 mm), 287 and 247 hulls (vs 52/45 at 0.05), lid/pot depth
  3.9/4.0/4.1 mm (V1 7.0-7.7, floor 2.8-3.1). The concavity term scales linearly with threshold x L, confirming it
  as the residual cause. Hull count is set by the absolute tolerance, not by how it is obtained: pot at ~3-3.5 mm
  tolerance needs 247 hulls via threshold or 415 via 7 parts (S120; caps add pieces).
- B13 [V run, logs/eval_obj_split.out] Object inflation of the split / low-threshold sets (hull samples vs scan, mm,
  p99 / max; vs W2 in brackets): lid S60 1.69/3.63 [0.58/1.19]; pot S60 1.24/3.67 [0.69/1.58]; pot S120 1.94/4.70
  [1.70/2.95]; sweeper S60 0.89/1.77 [0.58/1.42]; blue S60 1.65/4.26 [0.64/1.23]; beige S60 1.48/4.07 [0.64/1.36];
  lid V3(0.02) 1.80/3.98; pot V3 2.45/5.92. The remaining 3-4 mm max vs the scan is W2's own spill past open scan
  boundaries (B4), not CoACD. Scan coverage stays complete (uncovered > 1 mm <= 0.07 %).
  [E] Hull count vs absolute tolerance tol = threshold/2 x L_piece (lid 52 @4.7 mm, 287 @1.9, 831 @1.2; pot 45 @8.9,
  247 @3.6, 415 @3.0, 1118 @1.5; rack 68 @12.7, ~1200 @2.9 (S120), ~3600 projected @1.5 (S60, 27/82 parts gave
  1195 hulls)) follows roughly hulls ~ tol^-1.85 for these thin-walled scans.
- B14 [V run, logs/partdev_S60lid.out, logs/partdev_S120pot.out] The same law holds per part: lid S60 parts
  (L 47-49 mm) max hull deviation 0.95-1.08 mm, max/(0.025 L_part) median 0.89, max 1.00 (n 16); pot S120 parts
  median 0.93, max 0.99 (n 7). So the collider error of any mesh we ship is predictable before running CoACD:
  ~0.025 x (longest extent of that mesh), i.e. ~0.5 mm needs pieces of L <= 20 mm.
- B15 [V run, b/b_mine.py -> logs/mine.out; W2 field grids b/FG/] Automatic contact mining over ALL 20 public GT
  episodes (every 2nd frame, all pairs of the six objects, W2 surface samples inside the other W2 solid > 0.5 mm):
  contact pairs occur only in ep0/2 (lid-pot, 86/187 and 62/172 sampled frames), ep11 (nest, 39/69), ep12/13
  (blue cup-rack, 30/91, 41/95), ep26/27 (pot-rack, 26/79, 28/123) and ep31 (sweeper-rack, 103/145) -- exactly the
  episodes of note 15's case list, so the 13 states cover every public contact episode among these objects. Deepest
  W2-floor frame per episode: 2.4-3.9 mm (ep0 f28, ep2 f314, ep11 f124, ep12 f168, ep13 f130, ep26 f12, ep27 f218,
  ep31 f238); these 8 states are added as a second evaluation set.
- B16 [V run, logs/eval2_floors.out, logs/eval2_pairs.out] Second set (deepest mined W2 frame per contact episode),
  hullA-in-hullsB max mm, floor / V0 / V2 / V1: ep0 f28 lid-pot 3.0/7.7/9.5/7.1; ep2 f314 lid-pot 3.0/8.3/9.7/7.6;
  ep11 f124 nest 3.5/4.1/4.5/3.7; ep12 f168 cup-rack 1.9/8.3/7.5/5.8; ep13 f130 cup-rack 2.1/5.7/6.3/3.2;
  ep26 f12 pot-rack 2.2/6.5/7.3/2.9; ep27 f218 pot-rack 1.6/7.1/8.4/4.5; ep31 f238 sweeper-rack 2.8/12.9/12.2/12.1.
  Same ordering as the first set (V2 >= V0 > V1 > floor); ep31 f238 shows a sweeper-in-rack state where removing the
  preprocessing does nothing (12.1 mm) because the rack's whole-object concavity tolerance (12.6 mm) fills the slot.
- B17 [V run, logs/V4_120_plastic_dish_rack.log, logs/eval_pairs_S120.out, logs/eval2_pairs.out,
  logs/eval_obj_split.out] S120 = rack and pot split into parts of L <= 120 mm (rack 15 parts, 1198 hulls, 1571 s of
  exact calls on the loaded host; pot 7 parts, 415 hulls, 476 s), lid/sweeper/cups left as V1. Contact depth max (mm),
  set 1 [floor]: lid/pot 3.7/3.7/3.6 [3.1/2.8/2.8]; sweeper/rack 1.6/2.3 [1.8/1.9]; pot/rack 1.9/1.5 [3.4/1.6];
  cup/rack 2.1/2.7/2.5/2.4 [1.6/1.9/2.3/2.2]; nest 3.7/3.7 [3.7/3.6]. Set 2: 3.5/3.5 [3.0/3.0], nest 3.7 [3.5],
  cup/rack 2.7/1.8 [1.9/2.1], pot/rack 1.3/1.5 [2.2/1.6], sweeper/rack 3.0 [2.8] (V1 12.1).
  Rack S120 object inflation vs W2 p99 1.52 / max 2.79 mm (V1 8.8/12.6). (Depth max is not monotone in hull size,
  so values slightly under the W2 floor are sampling/shape effects, not negative inflation.)
  => [V] With watertight inputs and the two large objects split to <= 120 mm parts, every public GT contact state is
  within ~0.6 mm of the exact-collider floor (lid/pot within 0.5-0.9 mm) -- the asset-side route removes the
  inflation, at the cost of ~1.6k hulls for rack + pot.
- B18 [E run, logs/cap64.out] Split hulls are small and mostly <= 64 vertices; the emulated maxhullvert cap loses
  <= 0.07-0.38 mm (median 0.00) for S120/S60 sets, so the split results also hold for MuJoCo's capped hulls.
- B19 [V run, logs/partdev_S60.out] Per-part law re-checked on every S60 part of pot (n 38), sweeper (8), blue (16)
  and beige (16): max hull deviation / (0.025 L_part) median 0.83-0.89, max 0.98-1.05. Together with B10/B14 (6 whole
  objects, 23 more parts): 107 of 107 meshes obey max deviation <= 1.05 x 0.025 L.
- B20 [V run, logs/eval_pairs_S60r120.out, logs/eval2_pairs_S60r120.out, logs/V4_60_plastic_dish_rack.log]
  S60r120 = lid/pot/sweeper/cups at L <= 60 mm parts + rack at L <= 120 mm: every state of both sets is at the
  floor within sampling noise: set 1 lid/pot 3.0/3.0/3.1 [3.1/2.8/2.8], sweeper/rack 1.8/2.5 [1.8/1.9], pot/rack
  2.1/1.6 [3.4/1.6], cup/rack 2.0/2.2/2.4/2.2 [1.6/1.9/2.3/2.2], nest 3.8/3.6 [3.7/3.6]; set 2 2.9/3.1/3.4/2.2/2.0/
  1.2/1.7/2.5 [3.0/3.0/3.5/1.9/2.1/2.2/1.6/2.8]. Hull totals: lid 831 + pot 1118 + sweeper 180 + cups 531/423 +
  rack 1198 = 4281 hulls. Rack at L <= 60 mm (82 parts) finished: 2875 hulls, 3314 s of exact calls (shared host
  under load ~110 from other jobs; three workers for the last parts).
- B21 [V run; CORRECTION to B20 set 2] The first S60r120 set-2 run resolved the rack through "V4_60,V4_120" while
  the rack's S60 file appeared (00:50:05) mid-run, so some set-2 rack states used the S60 rack. Re-run with an
  explicit link dir b/MIX_S60r120 (lid/pot/sweeper/cups -> V4_60, rack -> V4_120; b/MIX_S120 likewise for S120):
  set 1 unchanged; set 2 = 2.9/3.1/3.4/2.2/2.0/1.2/1.6/2.7 (B20 had 1.7 and 2.5 for ep27/ep31). Old outputs kept as
  logs/*S60r120.INVALID_racksource.out. Conclusion unchanged.
- B22 [V run, logs/eval_pairs_S60.out, logs/eval2_pairs_S60.out, logs/eval_obj_split.out] S60 for all six (rack 82
  parts, 2875 hulls; vs W2 p99 0.64 / max 1.37 mm): set 1 3.0/3.0/3.1, 1.5/2.4, 1.9/1.7, 1.7/2.0/2.1/2.0, 3.8/3.6;
  set 2 2.9/3.1/3.4/2.1/1.7/1.2/1.7/2.5 -- floor everywhere; versus S60r120 only cup/rack moves (by 0.2-0.4 mm),
  so the rack at L <= 120 mm is already enough.
- B23 [V run (counts) / E (contact implication), b/b_pairs_count.py -> logs/pairs_count.out] Narrowphase load at the
  set-2 GT states: hull pairs with overlapping world AABBs / pairs that actually interpenetrate (vertex test), i.e.
  pairs MuJoCo must resolve at reset because of the 1.5-4 mm GT floor: V1 lid-pot 99/57, nest 181/109, cup-rack
  35-41/4-30, pot-rack 17-20/6-7, sweeper-rack 38/20. S120 (pot+rack split): lid-pot 306/160-171, pot-rack 74-106/
  29-31, cup-rack 53-111/9-50, sweeper-rack 80/54. S60r120: lid-pot 2259-2562/1098-1260, nest 1170/636, pot-rack
  77-114/37-39, cup-rack 38-127/12-71, sweeper-rack 187/126. S60all: lid-pot as S60r120, sweeper-rack 241/143.
  [E] With runtime nconmax 4096 contacts/world and njmax 16384 (FlashCHORD runtime/sim.py:32-33), >1000 touching
  hull pairs on one object pair (lid/pot, nest) is a real overflow/performance risk once hand contacts are added;
  S120-level splitting (+ V1 lid/cups) keeps the counts in the low hundreds. Not run in MuJoCo here (stage C).

### Stage B summary (answers)
Variants (exact FlashCHORD call `run_coacd(threshold=0.05, max_convex_hull=-1, preprocess_mode="auto")`, coacd
1.0.11, unless marked diagnostic): V0 = scan as newton loads it (non-manifold -> voxel preprocessing at L/100;
= note-15 hulls11); V2 (diagnostic) = W2 + forced preprocessing res 50; V1 = W2 watertight remesh (manifold -> no
preprocessing); S120 = rack + pot split into parts <= 120 mm (others V1); S60r120 = lid/pot/sweeper/cups <= 60 mm
parts + rack <= 120 mm; S60 = all six <= 60 mm; floor = the exact W2 solids (no CoACD; each W2 is the scan + 0.3 mm).
Depth = max depth (mm) of sampled hull-surface points of A inside B's hull union (note-15 pen2 definition).
Rows 1-13 = note-15 states; rows 14-21 = deepest mined W2 state per contact episode (B15).

| GT state (A in B) | floor | V0 | V2 | V1 | S120 | S60r120 | S60 |
|---|---|---|---|---|---|---|---|
| ep0 f0 lid in pot | 3.1 | 7.7 | 9.5 | 7.0 | 3.7 | 3.0 | 3.0 |
| ep2 f0 lid in pot | 2.8 | 8.1 | 9.5 | 7.7 | 3.7 | 3.0 | 3.0 |
| ep0 f372 lid in pot | 2.8 | 8.2 | 9.6 | 7.0 | 3.6 | 3.1 | 3.1 |
| ep31 f0 sweeper in rack | 1.8 | 10.5 | 9.3 | 9.7 | 1.6 | 1.8 | 1.5 |
| ep31 f160 sweeper in rack | 1.9 | 15.2 | 15.3 | 6.3 | 2.3 | 2.5 | 2.4 |
| ep26 f4 pot in rack | 3.4 | 9.7 | 10.0 | 6.4 | 1.9 | 2.1 | 1.9 |
| ep27 f216 pot in rack | 1.6 | 7.2 | 8.4 | 4.6 | 1.5 | 1.6 | 1.7 |
| ep12 f160 blue in rack | 1.6 | 8.4 | 8.0 | 5.9 | 2.1 | 2.0 | 1.7 |
| ep12 f180 blue in rack | 1.9 | 8.3 | 7.5 | 6.0 | 2.7 | 2.2 | 2.0 |
| ep13 f176 blue in rack | 2.3 | 6.3 | 7.8 | 3.9 | 2.5 | 2.4 | 2.1 |
| ep13 f189 blue in rack | 2.2 | 6.1 | 7.8 | 3.6 | 2.4 | 2.2 | 2.0 |
| ep11 f96 beige in blue | 3.7 | 4.1 | 4.6 | 3.7 | 3.7 | 3.8 | 3.8 |
| ep11 f136 beige in blue | 3.6 | 4.1 | 4.5 | 3.7 | 3.7 | 3.6 | 3.6 |
| ep0 f28 lid in pot | 3.0 | 7.7 | 9.5 | 7.1 | 3.5 | 2.9 | 2.9 |
| ep2 f314 lid in pot | 3.0 | 8.3 | 9.7 | 7.6 | 3.5 | 3.1 | 3.1 |
| ep11 f124 beige in blue | 3.5 | 4.1 | 4.5 | 3.7 | 3.7 | 3.4 | 3.4 |
| ep12 f168 blue in rack | 1.9 | 8.3 | 7.5 | 5.8 | 2.7 | 2.2 | 2.1 |
| ep13 f130 blue in rack | 2.1 | 5.7 | 6.3 | 3.2 | 1.8 | 2.0 | 1.7 |
| ep26 f12 pot in rack | 2.2 | 6.5 | 7.3 | 2.9 | 1.3 | 1.2 | 1.2 |
| ep27 f218 pot in rack | 1.6 | 7.1 | 8.4 | 4.5 | 1.5 | 1.6 | 1.7 |
| ep31 f238 sweeper in rack | 2.8 | 12.9 | 12.2 | 12.1 | 3.0 | 2.7 | 2.5 |

Per object: hulls / p99 / max outward distance of hull samples from W2 (mm); 0.025 L = predicted max (B10/B14/B19).

| Object | L mm | 0.025 L | V0 | V2 | V1 | S120 | S60 |
|---|---|---|---|---|---|---|---|
| white_pot_lid | 190 | 4.7 | 48 / 4.01 / 5.37 | 51 / 4.06 / 5.51 | 52 / 3.05 / 4.64 | - | 831 / 0.58 / 1.19 |
| white_pot | 358 | 9.0 | 40 / 7.76 / 9.70 | 38 / 9.31 / 10.69 | 45 / 7.04 / 8.73 | 415 / 1.70 / 2.95 | 1118 / 0.69 / 1.58 |
| mini_sweeper | 144 | 3.6 | 24 / 2.83 / 3.62 | 22 / 3.05 / 4.07 | 31 / 2.10 / 3.07 | - | 180 / 0.58 / 1.42 |
| plastic_dish_rack | 510 | 12.8 | 54 / 10.46 / 14.35 | 50 / 10.81 / 14.47 | 68 / 8.79 / 12.59 | 1198 / 1.52 / 2.79 | 2875 / 0.64 / 1.37 |
| blue_cup | 172 | 4.3 | 81 / 3.05 / 4.53 | 73 / 4.15 / 5.13 | 88 / 3.32 / 4.52 | - | 531 / 0.64 / 1.23 |
| beige_cup | 170 | 4.2 | 54 / 3.93 / 4.76 | 38 / 4.14 / 5.05 | 41 / 3.17 / 3.92 | - | 423 / 0.64 / 1.36 |

Answers:
1. Watertighting [V]: a winding-number remesh fills the cups' and pot's cavities (open inner walls); use flood-fill
   air + a 3 mm oriented shell behind single-sided walls (W2, 1 mm grid, iso +0.3 mm). QEM/edge-collapse decimation
   always failed CoACD's float Moeller self-intersection check, so W2 stays undecimated (77k-999k faces); nudging
   the field off the iso level made all raw MC meshes and all 198 split parts (22 at S120, 176 at S60) pass ("Mesh Manifoldness: true").
   Already-closed meshes (sweeper collision mesh, dust pan, boards) pass as-is once welded (ship as untextured
   STL/OBJ; B9).
2. Cause separation [V]: (a) concavity tolerance: the hull set of any mesh handed to CoACD reaches out to
   0.83-1.05 x 0.025 L of that mesh (107/107 meshes), i.e. 12.6 mm on the rack, 8.7 on the pot, 4.6 on the lid --
   this is the dominant term; (b) voxel preprocessing (non-manifold input): +1-2.3 mm p99 object inflation, +1-4 mm
   contact depth (9 mm in one sweeper state) on identical geometry (V2 vs V1). Removing (b) alone leaves 4-9 mm on
   lid/pot and sweeper/rack states (V1).
3. Residual floor [V]: even exact colliders give 1.5-4 mm in the GT states (pose/scan error; nest 3.4-3.8 mm),
   so no asset fix can reach zero; the target is "floor", not 0.
4. Asset-side removal [V]: watertight input + splitting rack and pot into parts <= 120 mm puts every public GT
   contact state within ~0.9 mm of the floor (lid/pot 3.5-3.7 vs 2.8-3.1; all rack states at floor); adding
   lid/pot/sweeper/cups at <= 60 mm reaches the floor everywhere. No evaluator/physics change is needed; the
   decomposition still runs with decompose_objects true.
5. Cost [V counts / E sim impact]: hulls grow ~tol^-1.85 (rack 68 -> 1198 -> 2875; pot 45 -> 415 -> 1118; lid
   52 -> 831), cold-cache CoACD time grows to ~8 min (pot S120) and ~26-55 min (rack S120/S60) of single-core exact
   calls, and penetrating hull pairs at reset rise from ~60 to ~1100-1260 for lid/pot at S60 (nconmax 4096/world).
   Recommended asset recipe for stage C [H]: W2-type watertight remesh for every open scan, split only rack and pot
   to <= 120 mm (or replace the rack's bars/fins with analytic boxes and the pot/lid rims with a few hand pieces),
   keep lid/cups/sweeper whole (V1 or welded), then verify contact counts and settling in MuJoCo.
