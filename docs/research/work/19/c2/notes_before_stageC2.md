# 19 — Collision hulls: can the CoACD inflation be removed on the asset side? (2026-10-06/07; stages A-C done)

Dig 19 (round 4, "D18 Hull inflation" in 16-synthesis §4). Markers: [V] verified, [E] estimate, [H] hypothesis.
Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/19/ (a_* stage A, b/ stage B, c/ stage C). Source pins:
nvidia-isaac/video_to_data @ 8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef (evaluator), coacd 1.0.11 (tag b678aa08),
newton 1.2.0, warp 1.14.0, trimesh 4.12.2, mujoco / mujoco-warp 3.8.1. Background: note 15 §C2/C4 (GT contact states
4-15 mm inside the pinned hulls). Sections 1-6 were rewritten at the end of stage C; the append-only logs (stages A, B,
C) follow below and hold the evidence for every number. Backups: work/19/c/notes_before_stageC.md,
work/19/c/notes_before_rewrite.md.
Platform caveat: every hull in this note was computed with the macOS coacd wheel. Linux gives other hulls for the same
input (C10), so single depths carry about +-1-3 mm of platform noise. The tolerance laws, counts and conclusions do not
depend on this.

## 1. Answer (most important first)

1. [V] The inflation can be removed on the asset side without touching the evaluator, but in practice there is a
   limit. It has two sources (B6-B19).
   (a) CoACD's concavity tolerance, about 0.025 x L, where L is the longest extent of each mesh handed to it: rack
       12.6 mm, pot 8.7, lid 4.6, cups 3.9-4.5, sweeper 3.1. This is the dominant term.
   (b) Voxel preprocessing of the non-watertight public scans: +1-2.3 mm of object inflation and +1-4 mm of contact
       depth.
   Watertight input removes (b). Small closed parts remove (a): with the rack and pot at <= 120 mm parts, or with
   contact-zone splits, every public GT contact state comes within about 0.9 mm of the "floor" of 1.5-4 mm, and finer splits reach it. The floor is the penetration
   that even exact colliders show, from GT pose and scan error; no asset can go below it.
2. [V code + measured scaling; E extrapolation to 4096 worlds] The binding limit is the number of collision shapes,
   not the URDF loader. The official evaluation config uses
   `world_count: 4096`. Newton keeps per-world Python lists of collision-filter pairs (every shape pair on one body)
   and of candidate contact pairs, and replicates them across worlds (C3). Measured build RAM is about 185 B x 4096 x
   (S^2/2 + 52 S + 1.3k), where S is the number of object shapes in an episode (C4). That gives:
   - the public assets (V0) and watertight assets (V1): 4-16 GB;
   - floor-level splits: 367-1,600 shapes, 66 GB to about 1 TB;
   - the S120 rack + pot (eval 28): about 1 TB, which is infeasible.
   For a 16 / 32 / 64 GB build the budget is roughly 150 / 240 / 360 shapes per episode.
3. [V] Splitting can crash the evaluator. CoACD leaves micron-sized debris hulls (< 1e-15 m3) on some split parts,
   and newton's SolverMuJoCo then fails with "mesh volume is too small" (C6).
4. [V] CoACD 1.0.11 is not reproducible across platforms. On macOS it gives other hulls than on Linux (64 vs 69 hulls
   for one part; surfaces up to 2-4 mm apart), while Linux aarch64 and x86_64 agree. Any offline reproduction of the
   evaluator's hulls, including hull-aware reference projection, must therefore run in a Linux container (C10).
5. [V] `decompose_objects: false` is worse, not a fix. MuJoCo would collide each object as a single convex hull of
   <= 64 vertices, which removes every cavity (C1).
6. [V] Watertight input alone (V1) is nearly free in shape count (-24 % to +29 % hulls vs V0) and helps most where the rack is the
   partner:
   - pot/rack: 6.5-9.7 mm -> 2.9-6.4 mm;
   - cup/rack: 5.7-8.4 mm -> 3.2-6.0 mm;
   - one sweeper/rack state: 15.2 mm -> 6.3 mm.
   It barely helps lid/pot (7.7-8.3 -> 7.0-7.7 mm) and does not restore cavities (C5).
7. [E] Even near-floor colliders (S120/S60r120) drift 5-20 mm over 1 s of free settling from the GT reset states (approximate
   MuJoCo CPU, no hands). A hull-aware reference projection is therefore needed whatever the assets. The asset fix
   only shrinks the projection it needs, from 5-15 mm to about 2-4 mm (C7).
8. [V negative] Neither our own budgeted convex merge (HACD-style) nor re-orienting CoACD's input beats CoACD at a
   fixed piece count (C8, C12). The 3-6 mm features of the scans set the count: rim grooves, marker posts and thin
   folded shells.

## 2. Recommended asset recipe (within what the pinned loader, MuJoCo export and 4096-world build accept)

- R0 [V]: keep `scene.decompose_objects: true` and every evaluator and physics setting. All changes are to files
  named by our reference parquet (`object_urdf_paths` -> URDF -> meshes, A7).
- R1 (ship now; same shape budget as the public assets) [V]: watertight collision input.
  - Open scans (cups, pot, lid, rack; the pitcher is not done yet): the W2 remesh (B2/B4). This is flood-filled air plus a 3 mm oriented
    shell behind single-sided walls, on a 1 mm grid, marching cubes at +0.3 mm, with the field nudged off the iso
    level. It sits within 0.55 mm p99 of the scan (lid 1.5 mm at open rims). Do not decimate (B3).
  - Already-closed collision meshes (sweeper, dust pan, boards): weld by position (B9).
  - Packaging (A9-A16, C2): one untextured binary STL per `<collision>`, all on the single root link, mesh URIs
    relative to the URDF; keep an explicit `<inertial>`; the visual GLB is unchanged; ship under an `assets/` tree
    beside the reference parquet.
  - Acceptance checks per file, in a Linux container with the manylinux coacd 1.0.11 wheel, on the float32 vertices
    that trimesh 4.12.2 actually loads:
    - "Mesh Manifoldness: true" (a rotation alone can flip it, C12);
    - min hull volume > 1e-15 m3 (C6);
    - hull count within the episode budget (C4);
    - newton `add_urdf` keeps every `<collision>` (unresolved URIs are silently dropped, A16).
- R2 (only with confirmed RAM headroom and organiser approval) [V geometry / E RAM]: contact-zone splits of the object
  whose tolerance dominates the pair. Examples:
  - pot rim band in 8 arcs (RIM33): lid/pot at the floor, 451 shapes, about 96 GB;
  - rack tower zone (359 hulls): spoon opening restored, 367 shapes with the spoon, about 66 GB;
  - blue cup in 2 parts (CUP2): small gain, 179 hulls, 22-28 GB.
  Any rack episode needs 1,200+ hulls this way, so splitting is not a route for the rack (C11, C13).
- R3 (the only route to floor-level contacts within about 150-240 shapes) [H]: pass-through pieces that we author.
  - URDF primitives (`<box>`, `<cylinder>`, `<capsule>`, `<sphere>`) never reach CoACD (A3, A15).
  - Closed convex meshes come back from CoACD as exactly themselves, on macOS and Linux (A14, C10), with no debris
    and no platform dependence.
  - Targets: the rack as boxes (fins, dividers, base slats, tower walls and floor; [E] about 60-100), and revolve
    walls (pot, cups, lid seat) as frustum segments of <= 64 vertices.
  - Falsification test: build the rack this way and require cup/rack, pot/rack and sweeper/rack public twin states
    within 1 mm of the floor with <= 100 rack shapes. Otherwise R3 fails for the rack.
- R4 (needed in every case) [E]: project the reference poses out of penetration against the hulls of the shipped
  assets, as decomposed on Linux, and settle-test them (note 15 design need 4).
- Spoon (fully ours): a capsule chain for the handle plus <= 4 closed convex bowl pieces, i.e. <= 8 exact shapes,
  with nothing left to CoACD's 0.025 x 300 mm = 7.5 mm tolerance [H, design rule from A3/A14].

## 3. Effect on the at-risk eval episodes

Notation:
- Contact depths are from public twin states (B table and C11), max mm, written as floor / V0 public / V1 watertight /
  best split.
- Shape counts and build RAM are per episode at 4096 worlds (C4 model; the spoon counted as 8 shapes).
- Settle values are from C7 [E].

| eval | contact that matters | twin evidence | R1 (V1) effect | floor-level option and its cost |
|---|---|---|---|---|
| 1 pot+lid | lid on pot at start and end | ep0/2: 2.8-3.1 / 7.7-8.3 / 7.0-7.7 / RIM33 2.5-2.7; reset jolt in 50 ms V0 10.6, V1 7.9, S120 1.7 mm | small (97 shapes, 8 GB) | RIM33 + lid V1: 451 shapes, ~96 GB; or R3 pot rim |
| 3/5/6 pot+spoon | spoon in pot basin | basin diameter 10 mm above floor: W2 130, V0 110, V1 113, S120 129 mm; basin cells risen > 5 mm: 36 / 30 / 2.9 % | none for the basin (53 shapes, 4 GB) | S120 pot + spoon: 423 shapes, ~85 GB; or R3 pot walls; spoon exact (R3) |
| 10 blue+beige | nest | ep11: 3.5-3.7 / 4.1 / 3.7 / CUP2 3.1-3.5 | floor-dominated already | none needed; R4 projection of ~4 mm |
| 14 blue+rack | inverted cup on rack at end | ep12/13: 1.6-2.3 / 5.7-8.4 / 3.2-6.0 / S120 1.8-2.7; 1 s tilt V0 24, V1 15, S120 2.3 deg | partial (156 shapes, 16 GB) | rack S120: 1,286 shapes, ~680 GB, infeasible -> R3 rack |
| 15/16 rack+spoon | spoon handle into tower | tower opening 5/15 mm above its floor: W2 38/40, V0 22/30, V1 blocked/36, tower split 38/38 mm; floor cells risen > 10 mm: V0 50 %, V1 35 %, split 2.9 % | partial (76 shapes, 6 GB) | tower zone split: 359 hulls + spoon = 367 shapes, ~66 GB; or R3 tower boxes |
| 28 rack+pot | inverted pot on rack at end | ep26/27: 1.6-3.4 / 6.5-9.7 / 2.9-6.4 / S120 1.3-1.9; reset jolt V0 13.7, V1 4.7, S120 2.4 mm | most of the gain (113 shapes, 10 GB) | S120 rack+pot: ~1,600 shapes, ~1 TB, infeasible -> R3 rack |
| 30 sweeper+rack | slot-0 sweeper starts between dividers | ep31: 1.8-2.8 / 10.5-15.2 / 6.3-12.1 / S120 1.6-3.0; 1 s V0 12.9 mm/14 deg, V1 11.7/16, S120 8.7/7 | insufficient (99 shapes, 9 GB) | rack S120: 1,229 shapes, ~620 GB -> R3 rack (highest-value R3 target) |
| 32/33 blue+spoon | spoon in cup | interior diameter 10/40/120 mm above floor: W2 64/68/78, V0 62/68/73, V1 59/63/74, CUP2 61/67/76, S60 63/68/77 | none (V1 is no better than the public asset here) | CUP2 + spoon: 187 shapes, 22 GB, small gain; R3 cup walls |

Summary [E]:
- R1 is worth shipping for the rack episodes 14 and 28 (and partly 15/16).
- Eval 1, 3/5/6 and 30 need either R2 RAM that the evaluation may not have, or R3. The rack is the common
  denominator of 14, 15, 16, 28 and 30.
- Eval 10 is already at the floor.
- R4 projection is needed everywhere.

## 4. Question for the organisers (proposed wording; supersedes 16-synthesis §5 Q4)

"Track 3 simulation assets (FlashCHORD @8c778f90). Our reference parquet names the object URDFs
(`object_urdf_paths`).

(a) May we ship our own collision geometry for the provided objects, keeping the evaluator, the CoACD call
(`scene.decompose_objects: true`, threshold 0.05) and all physics parameters unchanged, and the visual mesh as given?
We mean:
- the provided scans made watertight,
- the scans split into several `<collision>` meshes, or
- primitives and convex pieces fitted to the provided scans.
With the provided meshes, CoACD puts the public ground-truth contact states 4-15 mm inside the collision hulls (lid on
pot; cups, pot and sweeper on the rack; nested cups), so objects start interpenetrating and are pushed apart at reset.

(b) The same question for `<inertial>`. The provided URDFs call the 0.3 kg mass a placeholder.

(c) Is the official evaluation run at `world_count: 4096` (configs/evaluation/flash_sac.yaml), and on how much host
RAM? Newton builds per-world Python lists that grow with world_count x (collision shapes per episode)^2. A split asset
with about 400 shapes per episode needs about 100 GB at 4096 worlds. Is there a shape limit we should respect, or may
the world count be lowered?

(d) Which platform runs the evaluator (Linux x86_64 or aarch64)? CoACD 1.0.11 gives different hulls on macOS and Linux
for the same input."

Until answered:
- [E] R1 is the least contentious change: it is the provided geometry within 0.55 mm p99, only made watertight. It is
  still an asset change and should be disclosed.
- R2 and R3 should wait for (a) and (c).

## 5. Next steps (each with its falsification test)

1. Rebuild the R1 assets and all reference hulls in a Linux container (coacd manylinux wheel); recompute the hull-aware
   reference projection (R4) against them.
   Test: Linux hulls of the shipped files are bit-stable across re-runs, and the projected public twin states settle by
   < 2 mm / < 1 deg in 1 s.
2. Prototype the R3 rack (boxes) and measure the twin states (cup/rack, pot/rack, sweeper/rack) plus the tower opening.
   Test: within 1 mm of the floor with <= 100 shapes; otherwise drop R3 for the rack.
3. GPU smoke (16-synthesis E1): run FlashCHORD's real scene build at 4096 worlds with V0 vs R1 vs one R2 asset and
   record peak host RAM, build time and nconmax overflow.
   Test: the measured RAM is within 20 % of the C4 model.
4. Send the section 4 question; record the answer here and in 16-synthesis §5.

## 6. Artifacts

Stage C scripts are in work/19/c/:
- c_export.py and c_e2e.py: loader end-to-end check;
- c_scale.py: build-RAM scaling;
- c_cavity.py: cavity metrics;
- c_settle.py: approximate settle test;
- c_sliver*.py: debris crash check;
- c_hmerge.py: own budgeted merge (negative result);
- c_csplit.py: contact-zone splits;
- c_rotdecomp.py and c_align.py: input orientation;
- c_lincoacd.py and c_xcmp.py: cross-platform check;
- c_zone.py: contact zones.

Logs are in work/19/c/logs/. Hull sets:
- c/CS/{rim33,cup2,tower}/;
- c/ROT/;
- c/HM/;
- Linux results in c/xplat/.

Environment:
- Own venv work/19/venv (trimesh 4.12.2, newton 1.2.0, warp 1.14.0, mujoco and mujoco-warp 3.8.1, plus the B
  extras); coacd 1.0.11 from work/15-verify/pylib11.
- Linux coacd at c/xplat/lib_{arm64,amd64}, run in docker python:3.12-slim-bookworm.

Stage B hulls: b/V1 (R1), b/V4_120, b/V4_60, b/MIX_*.

---

# Logs (append-only; evidence for sections 1-6)

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

## Stage C — recommended asset recipe, effect on the at-risk eval episodes, rules question

Log (append-only). Work dir: work/19/c/. Backup of this note before Stage C: work/19/c/notes_before_stageC.md.
- 2026-10-07 C0 [V data] Resume check: Stage C section was absent (fresh start). Eval objects (kit
  data/track_3_evaluation_objects.json): 1 pot+lid; 3/5/6 pot+spoon; 10 blue+beige cup; 14 blue cup+rack; 15/16
  rack+spoon; 28 rack+pot; 30 sweeper+rack; 32/33 blue cup+spoon (also 8 beige cup+pot, 19 sweeper+dustpan, 20 blue
  cup+pitcher, 25 boards, 35-37 spoon, 38 dustpan). The spoon has no public scan/URDF/GT, so its collision asset is
  entirely ours (note 15).
- C1 [V code, runtime/sim.py:24-38 @8c778f90; newton solver_mujoco.py:4702-4740] FlashCHORD runs SolverMuJoCo with
  `use_mujoco_contacts=True` (MuJoCo native contacts), 200 Hz physics (fps 50 x 4 substeps), nconmax 4096 / njmax
  16384 per world. Every mesh geom is compiled "through its convex-hull path" (newton's own comment, 4712-4713), with
  maxhullvert 64. So `scene.decompose_objects: false` would NOT give exact concave colliders: each object would collide
  as ONE convex hull of <= 64 vertices (pot, cups and rack lose their cavities entirely; lid-in-pot, nesting, stirring
  and rack placement become impossible). Newton's own pipeline (`use_mujoco_contacts=False`, SDF/mesh contacts) is a
  sim-config change and drops the geom contact parameters needed for grasping (sim.py:37-38). => The decomposition is
  the only concave-collision path in the pinned evaluator; the inflation fix must stay on the asset side (what CoACD is
  given), not on the decomposition switch.
- C2 [V run, c/c_export.py, c/c_e2e.py -> c/logs/e2e_pot_S120.log; b_mcheck on c/assets/reloaded/] End-to-end loader
  check of the split recipe on the pot (S120, 7 parts): each part exported as an untextured binary STL, one
  `<collision>` per part on the single root link, public `<inertial>` kept, original GLB as `<visual>`
  (c/assets/white_pot/white_pot_split.urdf). Reloaded with trimesh.load(force="mesh") every part keeps its vertex/face
  count, is watertight and winding-consistent, moves by <= 7e-6 mm (float32 STL), and passes CoACD's manifold check
  ("Mesh Manifoldness: true", no preprocessing). newton add_urdf with FlashCHORD's flags: 1 body, 7 colliding mesh
  shapes + 1 visual, mass 0.3 kg; FlashCHORD's verbatim `_decompose_object_collision`: 417 hulls in 472.6 s (stage B
  direct float64 calls: 415; identical hull-union bbox), 277/417 hulls > 64 vertices (MuJoCo caps them, B18), and
  90,136 collision-filter pairs for this one object. => The loader accepts the recipe as designed; float32 rounding
  changes CoACD's output only marginally.
- C3 [V code: FlashCHORD configs/evaluation/flash_sac.yaml @8c778f90 (fetched to work/19/src/), scene/builder.py:438-490,
  evaluation/harness.py:363; newton 1.2.0 sim/builder.py:2115-2160 (replicate), 3135-3141 (add_builder), 5537-5542
  (add_shape), 9866-9868 and 10598/10803-10860 (finalize), solver_mujoco.py:4441,4493-4509] THE HULL COUNT IS NOT FREE.
  The official evaluation config sets `world_count: 4096`, and FlashCHORD builds ONE scene copy and calls
  `builder.replicate(copy, world_count)`. (1) newton's `add_shape` adds a collision-filter pair between the new shape and
  EVERY shape already on the same body ("no contacts between shapes of the same body"), so an object with S collision
  shapes (hulls or primitives) carries S(S-1)/2 filter pairs; FlashCHORD's decomposition loop re-checks the same pairs.
  (2) `add_builder` copies the Python list of filter pairs for every world, and finalize turns all of them into one
  Python set. (3) finalize always calls `find_shape_contact_pairs`, a pure-Python double loop over all pairs of colliding
  shapes in each world, which stores every unfiltered cross-body pair (object-object and hand-object hull pairs) in a
  Python list and then a device array. So build time and host memory scale as world_count x (sum of S_i^2/2 + cross-body
  shape pairs). For the public assets (V0: rack 54 + pot 40 hulls, eval 28) that is ~2.2k filter pairs and a few
  thousand contact pairs per world; for the S120 recipe (rack 1198 + pot 415) it is ~0.8M filter pairs and ~0.5M
  rack-pot contact pairs per world, i.e. ~3.3e9 filter tuples and ~2e9 contact tuples at 4096 worlds [E: arithmetic;
  measured scaling in C4]. MuJoCo itself only instantiates the first world's geoms (solver_mujoco.py:4441), but the
  Newton model is built for all worlds first.
- C4 [V run, c/c_scale.py -> c/logs/scale.out; newton 1.2.0 + warp 1.14.0 CPU; template = 2 free objects with H box
  shapes each + 40 one-shape "hand" bodies; replicate N worlds + finalize] Measured cost of shapes per object:
  filter pairs/world = H(H-1) (two objects), contact pairs/world = H^2 + 80H + 780, exactly as the code predicts (C3).
  Peak RSS grows linearly at ~180-190 bytes per (filter + contact) pair and finalize time at ~0.5 us per pair:
  H 50: N 64/256/1024 -> 0.37/0.72/2.09 GB, 0.3/1.3/5.0 s; H 200: N 64/256 -> 1.42/4.89 GB; H 800: N 16/32 ->
  4.45/7.91 GB, 10/21 s; H 1600: N 8 -> 8.10 GB. Extrapolated to the official world_count 4096 [E, linear, ~185 B/pair]:
  H 50 -> ~7.5 GB; eval 28 with V0 (rack 54 + pot 40, ~9k pairs/world) ~7 GB, V1 (68 + 45, ~11.6k) ~9 GB;
  eval 28 with S120 (rack 1198 + pot 415: 0.80M filter + 0.56M contact pairs/world) ~5.6e9 pairs ~ 1 TB of host
  RAM => INFEASIBLE; S120 is feasible only at <= ~64 worlds (~16 GB). A practical budget of ~16 GB at 4096 worlds is
  ~20k pairs/world, i.e. roughly (S_A + S_B)^2/2 + 40(S_A + S_B) <= 20k -> S_A + S_B <~ 165 collision shapes for the
  two objects of an episode (hand-shape count 40 is an assumption [E]). => The stage-B split recipe (hundreds to
  thousands of hulls per object) removes the inflation geometrically but cannot be shipped for a 4096-world
  evaluation; the asset recipe must reach small inflation with ~50-80 pieces per object.
- C5 [V run, c/c_cavity.py -> c/logs/cavity.out (occupancy with a 2 um tolerance; the run without it is kept as
  c/logs/cavity_nopad.out); diagnostics c/c_leak.py, c/c_leak2.py] Cavities used by the at-risk eval episodes,
  object-only (no GT), vs the exact W2 solid. D = inscribed-circle diameter of the free cross-section (1 mm pixels),
  rise = how much higher the collider's first surface is than W2's along the cavity axis (2 mm columns).
  Pot basin (stirring 3/5/6, lid seat 1), W2 floor 112 mm below the rim: D at 10/30/60 mm above the floor W2 130/165/162,
  V0 110/154/156, V1 113/152/153, S120 129/162/161, S60 129/164/162 mm; basin cells risen > 5 mm V0 36 %, V1 30 %,
  S120 2.9 %, S60 0.5 % (central floor itself rises <= 4-6 mm even in V0: the loss is the wall-floor fillet, ~10 mm
  per side near the floor); air inside the pot's hull filled by colliders V0 385 cm3, V1 278, S120 31, S60 4 cm3.
  Blue cup interior (stirring 32/33, nest 10), floor 158 mm deep: D at 10/40/80/120/150 mm W2 64/68/71/78/82, V0
  62/68/71/73/78, V1 59/63/67/74/78, S60 63/68/71/77/81 mm; cells risen > 10 mm V0 16 %, V1 33 %, S60 0.9 %. Beige cup
  similar (V0 63/65/72/73/77 vs W2 64/68/73/78/83). Rack utensil tower (spoon insertion 15/16), floor 62 mm below the
  tower top: D at 5/15/30/45 mm above the floor W2 38/40/42/44, V0 22/30/34/36, V1 blocked at 5 mm (floor raised)
  then 36/40/42, S120 38/38/40/42, S60 38/39/41/43 mm; tower floor cells risen > 10 mm V0 50 %, V1 35 %, S120 2.9 %,
  S60 1.3 %. => [V] With the public assets the tower's free opening near its floor is ~22-30 mm instead of 38-40 mm,
  the pot basin loses ~10 mm per side at its floor fillet, and the cups lose ~2-5 mm of diameter (mostly near the
  mouth). Watertight input alone (V1) does not fix cavities (cups are slightly worse than V0); small pieces do (S120/
  S60 within 1-2 mm of W2). Coverage check: S120/S60 leave 40/92 of 323,728 pot W2 voxels uncovered, all within
  0.2 mm (max 1.2 mm) of the hull union (specks < 0.05 cm3 dropped at part cuts) - no through-gaps.
- C6 [V run, c/c_sliver.py; c/c_sliver_newton.py with mujoco 3.8.1 + mujoco-warp 3.8.1 added to work/19/venv by uv
  (FlashCHORD's pins)] Split recipes can CRASH the evaluator. CoACD 1.0.11 leaves micron-scale debris hulls at some
  part caps: rack S120 has one hull of 5.6e-17 m3 (extent 3 x 9 x 13 um); S60 sets have them in lid (8.7e-17), beige
  (6.0e-16) and blue cup (9.0e-17). None in V0/V1 (min 1.5e-8 m3). A single such hull given to newton's
  SolverMuJoCo (CPU path, same MjSpec compile as the GPU path) fails with MuJoCo's "mesh volume is too small ... Try
  setting inertia to shell" (threshold mjMINVAL 1e-15 m3: 6.0e-16 fails, 1.7e-15 and 2.8e-13 compile). newton's
  `spec.add_mesh` sets no inertia mode, and FlashCHORD has no filter. => Any recipe that lets the evaluator's CoACD cut
  our meshes must be checked for debris (min hull volume > 1e-15 m3) after the exact call; pass-through convex pieces
  avoid the issue by construction. (My first settle run hit the same error for S120/S60r120; logs/settle.out.)
- C7 [E approximate physics, c/c_settle.py -> c/logs/settle_run1.out (V0/V1), c/logs/settle_split.out (split sets,
  debris hulls < 1e-12 m3 dropped); MuJoCo 3.8.1 CPU, NOT mujoco-warp; FlashCHORD's dt 0.005, implicitfast, Newton,
  pyramidal, impratio 20, friction 1, solref (0.02, 1) = newton's default ke 2.5e3/kd 100 via convert_solref
  (newton kernels.py:185-199; the eval config passes no object contact overrides), maxhullvert 64, 0.3 kg, no hands,
  table at the support's lowest hull vertex] Free settle from the public GT reset states. A-rel-B displacement
  (mm / deg) at 50 ms and 1 s; contacts at reset:
  lid/pot ep0 f0 (eval 1): V0 10.6 -> 15.6/4.5 (55 contacts), V1 7.9 -> 17.8/4.6 (64), S120 1.7 -> 11.1/1.6 (171),
  S60r120 0.5 -> 20.0/13.2 (1338). Sweeper/rack ep31 f0 (eval 30): V0 5.5 -> 12.9/13.7 (22), V1 4.7 -> 11.7/16.0,
  S120 4.8 -> 8.7/6.9 (52), S60r120 3.4 -> 6.4/4.2 (96). Pot/rack ep26 f4 (eval 28): V0 13.7 -> 13.1/10.1 (16),
  V1 4.7 -> 4.6/2.6 (8), S120 2.4 -> 6.0/3.4 (49), S60r120 5.8 -> 5.0/4.7. Cup/rack ep12 end (eval 14): V0 7.2 ->
  35.0/24.4 (32), V1 5.5 -> 25.1/15.2, S120 3.8 -> 7.6/2.3 (53), S60r120 3.2 -> 8.2/3.3. Nest ep11 f96 (eval 10):
  V0 1.4 -> 14.6/10.1 (145), V1 = S120 1.4 -> 8.7/7.4 (131), S60r120 0.8 -> 8.7/1.1 (759).
  => [E] Less inflation shrinks the reset jolt (first 50 ms) roughly in proportion (lid 10.6 -> 0.5-1.7 mm, pot/rack
  13.7 -> 2.4 mm) and the 1-s tilt for cup/rack and sweeper/rack (24 -> 2-3 deg, 14 -> 4-7 deg), but even
  floor-level colliders still drift 5-11 mm (lid S60r120 20 mm) in 1 s from the 1.5-4 mm GT floor plus unsupported (hand-free) poses, so
  a hull-aware reference projection stays necessary; the asset fix shrinks the projection it needs from 5-15 mm to
  ~2-4 mm. Fine splits raise reset contacts to 760-1340 for one pair (nconmax 4096/world incl. hands).
- C8 [V run, negative; c/c_hmerge.py -> c/logs/hm_lid.out, c/HM/; diagnostic c/c_hmdiag.py] Own budgeted convex
  decomposition (HACD-style greedy merging of 6 mm grid cells, exact cost = max distance of the merged hull's surface
  outside W2, pieces closed and convex so they would pass CoACD unchanged): on the lid, 2251 cells merge to 400/200/100/
  60/40 pieces with median piece cost 2.2/2.7/3.2/3.6/4.0 mm and max 4.6 mm from the start; CoACD's own V1 has 52 hulls
  at max 4.6 mm and V3 (threshold 0.02) 287 at 1.85 mm. Even 6 mm cells already reach 3.4 mm (no margin) at the lid's
  rim grooves and marker posts. => A generic merge is no better than CoACD at a fixed piece count; the scans' 3-6 mm
  features (rim grooves, marker spheres/posts, thin folded shells) set the hull count, so a budget-feasible fix must
  either simplify geometry away from contacts or split only the contact zone (C9). Hand-built primitives (rack
  fins/tower walls as boxes, revolve shells as frustum segments) remain [H].
- C9 [V data, c/c_zone.py] Public-GT contact zones (W2 vertices within 10 mm of the partner over all contact states):
  pot vs lid (ep0/2, 5 states): pot x 21.8..77.9 mm, full circumference (top 56 mm of the pot: upper inner wall + rim);
  lid vs pot: lid x -10..8.7 (lower 19 mm, whole disk); rack vs sweeper (ep31, 3 states): x -24..49, y -71..68,
  z -9..213 mm (a 73 x 139 x 222 mm block of dividers, ~45k of 499k W2 vertices).
- C10 [V run, c/c_lincoacd.py in docker python:3.12-slim-bookworm (linux/arm64 native, linux/amd64 emulated), PyPI
  coacd 1.0.11 manylinux wheels installed to c/xplat/lib_*; c/c_xcmp.py; logs/xplat_lid_arm64.log] CoACD is NOT
  reproducible between macOS and Linux. Same input bytes, exact FlashCHORD call: pot S120 part p003 -> 64 hulls on
  macOS (bit-identical on re-run) vs 69 hulls on Linux aarch64 and 69 on Linux x86_64; the two Linux runs agree to
  0.00 mm (not bit-identical, floating-point level), while macOS vs Linux hull surfaces differ by up to 2.1 mm (p99
  0.6-0.9 mm). Whole lid W2: 52 hulls on both, but surfaces differ by up to 3.7 mm (p99 0.6-0.9 mm); lid/pot GT depth
  pot-in-lid-hulls 3.7 (macOS) vs 4.2 mm (Linux), lid-in-pot unchanged (same pot). [H] Likely cause: std:: random
  distributions differ between libc++ (macOS wheel) and libstdc++ (manylinux), so CoACD's seeded MCTS takes other
  cuts. => Every offline reproduction of the evaluator's hulls (hull-aware reference projection, contact checks,
  all stage-B/C numbers, which were computed on macOS) must be re-run in a Linux container to match a Linux
  evaluator; differences are up to ~0.7 x the CoACD tolerance. Stage B/C conclusions are statistical (counts and
  tolerance laws) and stand, but individual depths carry +-1-3 mm platform noise. Pass-through convex pieces avoid
  the dependence: [V Linux aarch64] a closed 24-segment cylinder -> 1 hull, exact; a 177-vertex convex piece (a V1 pot
  hull) -> 1 hull within 0.0025 mm (c/xplat/cyl24*, pothull3*).
- C11 [V run, c/c_csplit.py (zone box split into a grid of closed parts + ONE closed remainder part), exact call per
  part via b/b_decomp_parts.py; c/logs/cs_*.log, eval_pairs_cs.out, cavity_cs.out] Contact-zone splits (macOS hulls):
  RIM33 = pot rim band x 20..81 mm (the C9 lid zone) in 8 arcs (L 52-69 mm) + remainder (body + handle, L 358): arcs
  21-80 hulls each (370) + remainder 29 = 399 hulls (S120 whole pot: 415). Lid(V1)/pot depth 2.7/2.5/2.6 mm = at or
  below the floor (2.8-3.1; S120 3.6-3.7, V1 7.0-7.7); pot/rack 5.9/3.3 (rack V1 dominates); basin unchanged vs V1
  (remainder at L 358). CUP2 = blue cup in 2 parts (L 103/88 mm): 49 + 130 = 179 hulls (V1 88, S60 531); nest 3.5/3.1
  mm (V1 3.7, floor 3.5-3.7); cup/rack unchanged (rack-dominated); interior D 61/67/70/76/80 vs W2 64/68/71/78/82 mm,
  air filled 17 cm3 (V0 36, V1 45, S60 1.5). => [V] Hull count is set by the tolerance needed on the contact surface,
  not by how much of the object is split: the lid seat alone costs ~370 hulls to reach the floor. At 4096 worlds,
  eval 1 with RIM33 + lid V1 (451 shapes) needs ~96 GB of build RAM [E, C4 model]; CUP2 + beige V1 (eval 10) ~28 GB,
  CUP2 + spoon (32/33) ~22 GB.
- C12 [V run, c/c_align.py, c/c_rotdecomp.py, c/logs/rot_*.log, eval_pairs_rot.out, eval_obj_rot.out] Same geometry,
  different CoACD input orientation (vertices rotated by R in the file, compensated by the `<collision><origin rpy>`,
  which FlashCHORD keeps for every hull, A3): rack aligned to its dominant planes (4.76 deg; the scan frame is tilted
  ~4 deg, cf. GT up (0.998, -0.011, -0.068)) -> 55 hulls (V1 68), object p99/max 8.4/13.2 mm (V1 8.8/12.6); contact
  depth sweeper/rack 9.3/6.1 (V1 9.7/6.3), pot/rack 6.0/4.1 (6.4/4.6), cup/rack ep12 11.3/11.0 (5.9/6.0, worse),
  ep13 3.9/3.6 (same). Lid rotated 15/30 deg about its axis: 59/60 hulls, lid/pot 6.9-7.6 mm (V1 7.0-7.7), pot-in-lid
  3.8-4.6 (3.7-3.9). Lid rotated 45 deg: the float Moeller check FAILED ("Mesh Manifoldness: false") -> voxel
  preprocessing -> 49 hulls, pot-in-lid 4.8-6.0 mm. => [V] Orientation is a re-draw of the same tolerance (local
  depths move by up to +-5 mm, no systematic gain); and the manifold check is fragile to float rounding, so every
  shipped file must be re-checked on exactly the float32 vertices newton loads (C2 did this for the pot parts).
  [H, low value] picking the best of K orientations per episode on Linux could gain a few mm at known contact sites.
- C13 [V run, c/c_csplit.py rack zone x -12..80, y -80..68, z -212..-118 mm in 2 parts (L 95 mm) + remainder;
  c/logs/cs_tower_decomp.log; cavity with the zone hulls only (c/CS/tower/Z, the remainder lies below the tower floor)]
  Tower zone: 148 + 162 = 310 hulls. Tower D at 5/15/30/45 mm above its floor 38/38/40/42 mm (W2 38/40/42/44, V0
  22/30/34/36, V1 blocked/36/40/42); floor cells risen > 10 mm 2.9 % (V0 50 %, V1 35 %). => restores the spoon
  opening for 15/16, but with the remainder and a spoon the episode needs ~380 shapes (~55 GB build RAM at 4096
  worlds [E]).
- C14 [V data / E model; FlashCHORD assets/urdfs/sharpawave/left_sharpawave.urdf @8c778f90 fetched to work/19/src/]
  The Sharpa hand URDF has 26 `<collision>` meshes (left_cvx/*.STL, already convex) per hand, i.e. ~52 hand shapes
  (FlashCHORD's filter_sharpa_collisions may drop some). Refined per-episode build model (C4 constants): pairs/world
  = S_A(S_A-1)/2 + S_B(S_B-1)/2 + S_A S_B + 52(S_A+S_B) + 1.3k, RAM ~ pairs x 4096 x 185 B. Per episode (spoon = 8
  shapes): V0 3.8-13 GB, V1 4.1-16 GB (eval 14 blue V1 88 + rack V1 68 = 156 shapes is the largest); RIM33 + lid
  (eval 1) ~96 GB; S120 pot + spoon (3/5/6) ~85 GB; CUP2 + beige (10) ~28 GB, CUP2 + spoon (32/33) ~22 GB; rack S120
  with anything 600 GB-1 TB. Budget: S = 150 / 240 / 360 / 530 shapes per episode for 16 / 32 / 64 / 128 GB.
- C15 [V run; correction to C13's estimate] The tower remainder (rest of the rack, L 510 mm) gave 49 hulls, so the
  tower-zone rack has 359 hulls (967 s of exact calls); with an 8-shape spoon, eval 15/16 = 367 shapes, ~66 GB at 4096
  worlds (C13 said ~380 / ~55 GB). Debris check (c/c_sliver.py) on the contact-zone sets: min hull volume RIM33
  1.3e-13, CUP2 7.3e-11, tower 6.6e-13 m3 -> all compile (> 1e-15), but each has one hull < 1e-12 m3, i.e. close to
  the crash threshold; on Linux the hulls differ (C10), so the check must be repeated there.
- C16 Notes rewritten (sections 1-6 above the logs) on 2026-10-07; the pre-rewrite file is
  work/19/c/notes_before_rewrite.md. Stage C ran no SlamDunk code and changed no SlamDunk file other than this note.

## Verification (skeptical verifier, 2026-10-07; scripts in work/19-verify/)

- X1 [V data, kit examples/run_policy_evaluation.py:42,74 (sha256 0bcc41f5... = KIT_MANIFEST) and config/tracks.json
  _comment + track_3 "worlds_per_episode": 1] Against C3/C4/C14's premise: 4096 is only the default of
  configs/evaluation/flash_sac.yaml. The kit's documented Track 3 runner passes `evaluation.world_count=<--world-count>`
  with default 1, and tracks.json says evaluate_policy.py "defaults to world_count=4096, but ... only one world is
  submitted". Participants run the evaluator themselves (track_3 README step 1). So the official submission path builds
  1 world by default, and the C4 build-RAM model then gives ~4096x less (S120 rack+pot ~0.26 GB, not ~1 TB). The
  4096-world RAM numbers apply only if someone runs the YAML default (e.g. an organiser re-run); they are not the binding
  constraint of the documented path.
- X2 [V run, work/19-verify/v_scale.py (own unequal-object template, 52 one-shape hand bodies), newton 1.2.0 CPU]
  C3/C4 mechanics reproduce: pairs/world = S_A(S_A-1)/2 + S_B(S_B-1)/2 + S_A S_B + K(S_A+S_B) + K(K-1)/2 exactly
  (1,385,280 for S120 rack 1198 + pot 415, K 52); RSS 181-203 B/pair (S 156 at N 256: 1.0 GB incremental ->
  ~16 GB at 4096 [E]). Code cites at newton builder.py 3137-3140 (filter list copied per world), 5537-5540 (same-body
  filter pairs), 9866-9868 (set), 10598/10803-10861 (pure-Python pair loop) confirmed. BUT at N = 1 (kit runner
  default, X1) the S120 rack+pot build is 0.6 GB peak RSS and 0.8 s finalize. FlashCHORD configs/scene/train.yaml has
  world_count 4096 (eval.yaml 1), so the C4 RAM budget binds 4096-world TRAINING (and any 4096-world eval re-run),
  not the documented evaluation path. Hand: left_sharpawave.urdf has 26 `<collision>` elements [V].
- X3 [V run, work/19-verify/v_sliver.py, mujoco 3.8.1 via newton 1.2.0 SolverMuJoCo CPU] C6 reproduces in a stricter,
  evaluator-like setup (body with explicit mass/inertia, hulls added with density 0 and float32 vertices as in
  FlashCHORD objects.py): rack S120 hull 755 (5.6e-17 m3, 2.8 x 9.1 x 13.2 um) -> "mesh volume is too small"; a
  normal hull alone compiles. Threshold bracket with a tetrahedron: 9.5e-16 fails, 1.05e-15 compiles (mjMINVAL 1e-15).
  Min volumes reproduced: rack S120 5.6e-17, lid S60 8.65e-17, blue S60 9.0e-17, beige S60 6.0e-16; V1 min 1.49e-8,
  V0 (15-verify/hulls11) min 9.6e-8 m3. Caveat: all debris hulls are macOS CoACD output; not yet shown on Linux.
- X4 [V run, c_cavity.py on c/CS/tower/Z (310 zone hulls) vs c/CS/tower/H (all 359, incl. the L-510 remainder) vs V0;
  work/19-verify/cavity_tower_ZvsH.out] The tower result does not depend on leaving the remainder out: TZ and TH give
  identical tower openings D 38.0/38.0/40.0/42.0 mm at 5/15/30/45 mm (W2 38/40/42/44, V0 22.4/30.1/34.0/36.1) and
  identical floor rise (>10 mm: 2.9 %, V0 50.1 %). The remainder fills 54 vs 12 cm3 of region air elsewhere. C13/C15
  tower numbers reproduced (macOS hulls).
- X5 [V run, work/19-verify/v_coacd.py (own copy of the exact call), macOS PyPI wheel cp39-abi3-macosx_11_0_arm64
  (15-verify/pylib11) and the manylinux wheel in docker python:3.12-slim-bookworm linux/arm64; outputs
  work/19-verify/xplat/] C10 reproduced on pot S120 part p003 (input bit-identical to b/S120/white_pot/white_pot_p003):
  macOS 64 hulls, bit-identical to the stage-B hulls and to c/xplat mac_rerun; Linux aarch64 69 hulls; my aarch64 run
  vs the earlier aarch64 run and vs the earlier amd64 run: 0.00 mm (not bit-identical, even run-to-run on aarch64);
  macOS vs Linux (c_xcmp metric) max 2.06/1.94 mm, p99 0.56/0.93 mm.
- X6 [V run, b_eval.py re-run -> work/19-verify/eval_pairs_S120.out, eval_pairs_rim33.out, eval2_pairs_rim33.out]
  B17 set 1 and C11 RIM33 lid/pot reproduce exactly with the per-hull metric (S120 3.7/3.7/3.6, 1.6/2.3, 1.9/1.5,
  2.1/2.7/2.5/2.4, 3.7/3.7; RIM33 lid-in-pot 2.7/2.5/2.6, set 2 2.6/3.0). The claim quotes only the A-in-B direction:
  the reverse direction (hullB-in-hullsA vs W2B-in-W2A floor) of S120 is up to +1.1 mm above the floor (sweeper/rack
  4.9/4.5 vs 4.0/3.4; rack-in-pot 3.9 vs 2.8; rack-in-cup 2.6-2.7 vs 1.6; nest 4.6-4.7 vs 3.6-3.7).
- X7 [V run, work/19-verify/v_uniondepth.py -> uniondepth_lidpot.out] Metric check. b_eval's depth is the max over
  hulls of the per-hull inward distance, a lower bound of the depth inside the hull UNION; the floor uses the exact
  distance to the W2 surface (a union depth). With union depth (nearest union-boundary sample, 0.5 mm spacing,
  coplanar cut faces excluded) lid-in-pot is V1 7.0-7.7 (= per-hull), S120 3.6-4.1 (per-hull 3.5-3.7), RIM33 3.0-3.7
  (per-hull 2.5-3.0). So RIM33's "at or below the floor" is partly a metric artefact of its many small hulls; on a
  like-for-like metric it is +0.2-0.7 mm above the floor (2.8-3.1), still near floor. Pot-in-lid (lid V1 in every
  variant) union depth is 5.0-6.1 mm vs per-hull 3.6-3.8 and floor 3.2-4.0, i.e. ~1.5-2.5 mm above floor in V1, S120
  and RIM33 alike: the unsplit lid's own tolerance is still present.
- X8 [V run, work/19-verify/v_uniondepth2.py -> uniondepth_S120.out, uniondepth_V1.out; floors from b/logs/eval*_floors.out]
  All 21 states, S120, union depth vs floor: A-in-B +0.0-1.1 mm (lid/pot +0.6-1.1, pot/rack +0.4-0.9, cup/rack
  +0.2-1.0, sweeper/rack +0.5-0.8, nest +0.5-0.7); B-in-A +0.2-2.3 mm (pot-in-lid +1.5-2.3, blue-in-beige +1.3-1.5,
  rack-in-sweeper +0.8-1.4, rack-in-cup up to +1.1). So "every state within ~0.9 mm of the floor" holds only for the
  quoted direction with the per-hull metric; like-for-like (union) and in both directions the S120 residual is up to
  ~1 mm on split partners and ~1.5-2.3 mm where the unsplit V1 lid/cups are the host. Sphere-containment check
  (v_sphere.py): around the deepest pot-in-lid(V1) point a 4.5 mm sphere lies wholly inside the lid hull union while
  the per-hull depth there is 1.6 mm, so the union depths are real, not sampling artefacts.
- X9 [V run, docker linux/amd64 (emulated) with the manylinux wheel] pot p003 -> 69 hulls in 37 s; vs my aarch64 run
  0.00 mm; vs macOS max 2.06/1.94 mm. C10's three-platform result is fully reproduced.

## Stage B addendum (resumed run, 2026-10-07 07:2x; "Try again" of the stage-B step)

Log (append-only). Same work dir (work/19/b/), venv and coacd as stage B. Scope: gaps left open by stage B and the
verifier (X6-X8), not a re-run of B1-B23.
- B24 [V data] Resume check: the Stage B log (B1-B23) and its summary were complete; no stage-B job was running
  (ps). Stored hull sets re-counted from the npz files and equal to the stage-B tables: V0 (15-verify/hulls11)
  48/40/24/54/81/54, V2 51/38/22/50/73/38, V1 52/45/31/68/88/41 (lid/pot/sweeper/rack/blue/beige), V3 lid 287 / pot 247,
  V4_120 rack 1198 / pot 415, V4_60 831/1118/180/2875/531/423; MIX_S120 and MIX_S60r120 are symlink sets as B21 says.
  Open gaps taken up here: (i) the B table uses the per-hull depth (a lower bound of the union depth, X7) in one
  direction only, so the V0/V2/V1 cause separation is re-measured with the union metric in both directions; (ii) the
  voxel term at more than one preprocessing resolution; (iii) the four public objects stage B did not cover (pitcher,
  dust pan, boards); (iv) the "then decimate" step that B3 left as [E].
- B25 [V run, ../19-verify/v_uniondepth2.py V0=15-verify/hulls11 V2=b/V2 -> b/logs/uniondepth_V0V2.out; V1/S120 from
  19-verify/uniondepth_{V1,S120}.out; floors b/logs/eval*_floors.out (exact distance to the W2 surface = a union
  depth); table script b/b_utable.py -> b/logs/utable.out] Cause separation redone on the like-for-like union metric,
  both directions, all 21 states (42 rows). Per-state terms: prep = V2 - V1 (same W2 geometry, voxel preprocessing on
  vs off); concavity = V1 - floor (exact call, no preprocessing, whole-object L).
  A-in-B (the direction quoted in the B table): floor 1.6-3.7, V0 5.7-15.3 (excess over floor median 5.4 mm), prep
  term median +2.9 (range +0.1..+6.1), concavity term median +3.9 (+0.5..+9.3); V0 -> V1 removes median 2.4 mm
  (44 % of the excess); S120 - floor median +0.6, max +1.1.
  B-in-A (the reverse direction, where the lid, cups or sweeper host the contact): V0 excess median 2.3 mm, prep median
  +1.3 (+0.2..+4.0), concavity median +1.5 (+0.2..+2.6); V0 -> V1 removes median 0.6 mm (31 %); S120 - floor up to
  +2.3 (pot-in-lid +1.5-2.3: the lid is unsplit in S120, X8).
  Largest single terms: concavity sweeper-in-rack +7.5..+9.3 (rack 0.025 L = 12.8 mm); prep sweeper-in-rack ep31 f160
  +6.1, pot/rack +2.8..+4.1, cup-in-rack +2.9..+4.4. Per-hull (B table) and union depths agree within 0.1 mm for most
  rows; union is larger by 0.6-3.1 mm in 9 of 42 rows (cup-in-rack V0/V2 +0.6-1.8, nest V2 +1.3, pot-in-lid V0/V1
  +1.4-2.3, sweeper-in-rack ep31 f160 V1 +3.1: the per-hull 6.3 was really 9.4).
  => [V] Correction to B6/B8 wording: on the union metric the voxel-preprocessing term is about as large as the
  concavity term for the lid/pot and cup/rack pairs (A-in-B prep 2.0-4.4 vs concavity 1.1-4.7 mm) and in the reverse
  direction (prep 1.3 vs concavity 1.5 mm median); the concavity term dominates only where the rack (12.8 mm
  tolerance) hosts the sweeper (+7.5..+9.3). The ep31 f160 "V1 6.3 mm" in the B table understates V1 (union 9.4 mm),
  so watertight input alone does NOT fix that sweeper state; only the rack split does (S120 2.5). Both causes are real
  and both have to go: watertight input for the prep term, small parts for the concavity term.
- B26a [V run, b/run_w2more.sh -> b/logs/remesh_W2_more.out; b/b_mine2.py -> b/logs/mine2.out] The four public
  objects stage B left out. W2 (1 mm, iso +0.3 mm, 3 mm shell) is closed and winding-consistent for all four:
  dust pan 139.5k faces, 79.5 cm3; boards 128.4k / 129.9k faces, 211.5 / 253.6 cm3; pitcher 668.3k faces, 342.1 cm3
  (91 -> 5 components after dropping specks; W2 vertices p99 +0.34 mm, max +3.17 mm from the scan; scan samples outside
  W2 by > 0.5 mm 0.00 %, max 0.94 mm). Contact mining (every frame, W2 vs W2 field):
  ep18 sweeper / dust pan: 10 of 353 frames > 0.5 mm, deepest 3.9 mm at f88-89 and f111-112 (a real contact state,
  eval 19); ep21/22 blue cup / pitcher: never within the field grid of each other (no contact; pouring is contact-free
  in the GT, eval 20); ep23/24 board / board: never in contact, closest W2 clearance 1.6 mm (ep23 f278) and 3.2 mm (ep24
  f246), i.e. about 2.2 / 3.8 mm between the scans (eval 25). For the boards the risk is the opposite one: a collider
  inflated by more than that clearance turns a near miss into a contact.
- B27a [V run, b/run_w2c.sh -> b/logs/remesh_W2c.out; b/b_mcheck.py -> b/logs/mcheck_W2c.out] "Then decimate" via a
  coarser marching-cubes grid instead of edge collapse (raw MC topology, same nudge, no collapses): W2 at h 2 mm and
  3 mm. At iso +0.3 mm the coarse grid drops thin features (lid h 2: 10.2 % of scan samples > 0.5 mm outside, max
  6.6 mm; h 3 at iso 0.6: 13 %, max 7.4 mm). Raising the iso level to about 0.3 h keeps the scan inside:
  h 2 / iso 0.6 mm: lid 0.46 % > 0.5 mm (max 1.73), pot 0.00 % (0.59), rack 0.02 % (2.96), blue cup 0.00 % (0.48);
  h 3 / iso 1.0 mm: lid 1.71 % (2.60), pot 0.03 % (1.05), rack 0.07 % (1.49), cup 0.03 % (1.03).
  Faces vs the 1 mm W2: h 2 lid 47.9k (/4.3), pot 124.4k (/4.0), rack 212.9k (/4.7), cup 63.5k (/3.9); h 3 lid 20.4k
  (/10), pot 54.6k (/9.2), rack 93.4k (/10.7), cup 28.5k (/8.8). The cost is extra offset: volume lid 112.6 -> 132.5
  (h 2) / 154.6 cm3 (h 3), rack 795.8 -> 1057 / 1184 cm3. All nine coarse meshes checked (h2/iso0.6 x4, h3/iso1.0 x4,
  lid h2/iso0.3) pass CoACD's check: "Mesh Manifoldness: true". => [V] A 4-10x reduction that passes the exact
  manifold check exists (coarse MC with raised iso), unlike QEM/edge collapse (B3); its price is +0.3-0.7 mm of
  extra offset. Exact-call effect on hulls and depths: B27b.
- B28a [V run, diagnostic (the resolution is fixed at 50 in the evaluator); b/run_vres.sh -> b/logs/V2r{25,100}_*.log;
  b/logs/eval_obj_vres_lid.out] Voxel term vs voxel size on identical geometry (lid W2, forced preprocessing,
  threshold 0.05). Voxel = L/(2 x resolution): res 25 3.8 mm, res 50 1.9 mm, res 100 0.95 mm, V1 none.
  Hull-vs-W2 p99 / max (mm): 5.46/6.95, 4.06/5.51, 3.51/4.65, 3.05/4.64; hulls 46/51/54/52. Excess p99 over V1:
  +2.41, +1.01, +0.46 mm = 0.63 / 0.53 / 0.48 voxel. => [V] The preprocessing term is about half a voxel of outward
  offset (A13's 0.55-voxel offset) and scales with L/resolution; at the fixed resolution 50 it is ~0.5 x L/100 per
  object surface, so it can be removed (watertight input) or shrunk (smaller parts, since L is per mesh), but no
  setting we control changes the resolution itself. CoACD runtime 30 / 75 / 251 s (res 25/50/100; V1 without
  preprocessing 132 s; shared host, so timings are indicative).
- B26b [V run, b/run_more.sh -> b/logs/V0x_*.log, V1w_*.log; b/b_eval_more.py -> b/logs/eval_more_floors.out,
  b/logs/eval_more_pairs.out; link dirs b/NEW_V0 (sweeper and boards = 15-verify/hulls11, dust pan = b/V0x),
  b/NEW_V1 (sweeper V1, pan and boards V1w), b/NEW_V1w] Exact call on the newly covered objects: dust pan as newton
  loads it "Mesh Manifoldness: false" -> 64 hulls (103 s); dust pan welded "true" -> 66 hulls (115 s); boards welded
  "true" -> 9 and 10 hulls (12 / 11 s; V0 9 and 11). Depths (mm; per-hull / union; floor = W2 vs W2):
  sweeper / dust pan ep18 f88 and f111, sweeper-in-pan: floor 2.2 / 2.1, V0 3.3-3.4, V1 2.3-2.4, V1w (welded
  sweeper) 2.3-2.4; pan-in-sweeper: floor 4.2 / 4.3, V0 5.0-5.1, V1 4.7-4.9, V1w 4.5-4.6.
  boards (no GT contact; negative = clearance): ep23 f278 floor -1.6, V0 +2.6/+2.7 and +2.5/+2.6 (penetration!),
  V1w -1.3 and -1.5 (per-hull plane distance, a lower bound of the clearance); ep24 f246 floor -3.2, V0 +1.5/+1.8,
  V1w -2.0/-2.1.
  => [V] For the boards the public asset turns a 1.6-3.2 mm GT clearance into 1.5-2.7 mm of interpenetration
  (the dedicated board collision GLBs fail the manifold check on a single duplicate vertex (A12), so they get the
  voxel offset of ~0.5 x L/100 = ~1.1 mm per board; a 227 mm board's concavity tolerance is unused because the boards
  are nearly convex). Shipping the same board collision mesh position-welded (untextured STL, B9) restores the
  clearance with zero geometric change. This is the cheapest R1 item and it is specific to eval 25. For sweeper /
  dust pan (eval 19) the public asset is +1.1-1.2 mm (sweeper-in-pan) and +0.8 mm (pan-in-sweeper) above the floor;
  welding both removes most of it (V1 +0.2 / +0.4-0.6 mm).
- B26c [V run, b/V0in/*.npz (as trimesh 4.12.2 loads the board collision GLBs: 17,237 / 14,507 vertices vs 17,236 /
  14,506 welded), b/b_mcheck.py -> b/logs/mcheck_boards_V0.out] Confirms the B26b mechanism: both as-loaded board meshes
  fail CoACD's check with "Unclosed mesh" -> "Mesh Manifoldness: false" (so the evaluator voxel-preprocesses them),
  while the welded copies pass. One unwelded UV-seam vertex per board decides between ~2-3 mm of spurious
  interpenetration and the GT clearance.
- B28b [V run, diagnostic; b/b_ud_sub.py -> b/logs/uniondepth_V2res.out (V2r25, V2r100), V2/V1 rows from B25] Lid/pot,
  5 GT states, union depth (mm), voxel sizes lid + pot: res 25 3.8 + 7.2, res 50 1.9 + 3.6, res 100 0.95 + 1.8, V1
  none. Lid-in-pot: 11.5-12.4 / 9.6-9.7 / 8.9-9.2 / 7.0-7.7 (floor 2.8-3.1). Pot-in-lid: 8.0-9.1 / 6.7-7.3 / 6.1-6.4 /
  5.0-6.1 (floor 3.2-4.0). Pot hulls at res 25/50/100: 33/38/44 (V1 45). Excess over V1 (lid-in-pot) = 4.4-4.9 /
  2.0-2.6 / 1.5-2.1 mm, i.e. 0.40-0.76 x (sum of the two voxel sizes). => [V] The preprocessing term grows linearly
  with the voxel size of each partner (about half a voxel per surface) and vanishes only when preprocessing is skipped;
  the concavity term (V1 - floor, 4.0-4.7 mm here) is untouched by the resolution. These are the two independent
  causes, and neither is a function of the other.
- B27b [V run, b/run_v1c.sh -> b/logs/V1c_white_pot_lid_h2_d0.6.log, b/logs/eval_obj_V1c.out,
  b/logs/uniondepth_V1c_lid.out (link dir b/C2: lid = V1c, others V1)] Lid, coarse W2 (h 2 mm, iso 0.6 mm, 47.9k
  faces) through the exact call: "Mesh Manifoldness: true", 57 hulls in 86 s (1 mm W2: 52 hulls, 132 s); hull
  vertices 5,848 (V1 12,376), hulls > 64 vertices 39 (V1 47); hull-vs-W2 p99/max 3.44/4.81 mm (V1 3.05/4.64).
  With pot V1: lid-in-pot union 7.0-7.7 (V1 7.0-7.7), pot-in-lid 5.3-6.0 (V1 5.0-6.1). => [V] The 4x coarser input
  gives the same contact depths within ~0.4 mm; the concavity term (0.025 L) dwarfs the extra 0.3 mm iso offset.
- B26d [V run, b/logs/eval_obj_more.out (b_eval.objstats), b/logs/V0x_water_pitcher.log, b/logs/V1_water_pitcher.log]
  Object inflation of the newly covered objects (hulls; hull-vs-W2 p99 / max mm; 0.025 L in brackets):
  pitcher (L 415 mm [10.4]): V0 46 hulls (49 s, preprocessed) 9.45 / 12.30; V1 (W2) 48 hulls (456 s, 668k faces)
  7.90 / 10.23. Dust pan (L 178 [4.5]): V0 64, 3.96 / 5.15; V1w (welded) 66, 2.70 / 3.94. Boards (L 227 [5.7]):
  V0 9 / 11, 2.66 / 5.38 and 2.37 / 5.19; V1w 9 / 10, 2.08 / 4.25 and 1.53 / 3.84 (the max sits at the 2 mm-scale
  edge bevels; the nearly convex boards do not use their tolerance). The 0.025 L law holds for the pitcher too
  (V1 max 0.98 x 0.025 L). [H] The pitcher has no GT object-object contact, so its ~8-10 mm tolerance matters only
  for the hand: fingers closing on the handle meet the collider up to ~10 mm early. Detail: the pitcher W2 holds four
  sealed inner void shells (negative volume: one 13.9 cm3 void, 18 x 66 x 83 mm, and three ~9 mm voids). They pass
  the check and the hulls fill them, but a shipped mesh should drop inward shells (keep only positive-volume
  components) so the file carries no internal surfaces.
- B28c [V run, diagnostic; b/logs/eval_obj_more.out] Resolution series for the two large objects (hull-vs-W2 p99 mm
  at res 25 / 50 / 100 / V1; voxel = L/(2 res)): rack (voxel 10.2 / 5.1 / 2.55 mm) 14.11 / 10.81 / 9.91 / 8.79, i.e.
  +5.3 / +2.0 / +1.1 mm = 0.52 / 0.40 / 0.44 voxel; pot (7.2 / 3.6 / 1.8 mm) 10.99 / 9.31 / 7.35 / 7.04, +3.95 / +2.27
  / +0.31 = 0.55 / 0.63 / 0.17 voxel. Hulls rack 47 / 50 / 56 / 68, pot 33 / 38 / 44 / 45; runtime rack 20 / 43 /
  183 / 396 s. => [V] Same half-voxel law as the lid (B28a). Coarser preprocessing also yields fewer hulls (the
  voxelised mesh is smoother) at the price of a thicker collider.
- B27c [V run, b/logs/V1c_*.log, b/logs/eval_obj_V1c.out, b/logs/uniondepth_C2all.out (link dir b/C2all: lid, pot,
  rack, blue cup = coarse h 2 mm / iso 0.6 mm; sweeper, beige = V1)] Coarse W2 through the exact call, all "Mesh
  Manifoldness: true": pot 41 hulls in 79 s (V1 45, 199 s), rack 63 in 252 s (V1 68, 396 s), blue cup 88 in 170 s
  (V1 88, 158 s; host load varies), lid 57 in 86 s; lid at h 3 / iso 1.0 (20.4k faces): 59 hulls in 32 s. Hull-vs-W2
  p99 / max (mm), coarse vs V1: pot 7.88 / 8.95 vs 7.04 / 8.73, rack 8.65 / 12.58 vs 8.79 / 12.59, blue 3.53 / 4.50 vs
  3.32 / 4.52. GT states, union depth, coarse set minus V1 over 42 rows (21 states x 2 directions): median +0.20 mm,
  range -0.8..+1.3; 13 rows > +0.5 mm: lid-in-pot +1.0..+1.3 (pot at iso 0.6), beige-in-blue +1.2..+1.3,
  rack-in-cup +1.0..+1.1.
  => [V] Decimation by coarse marching cubes is safe for CoACD's check and keeps the hull count, but costs ~+0.2 mm
  median and up to +1.3 mm in nested/seated contacts (it adds 0.3 mm of iso offset plus a redraw of the 0.025 L
  tolerance). Use it where face count matters (cold-cache build time; the 1 mm rack takes ~400 s per exact call) and
  keep the 1 mm W2 for hosts of seated contacts (pot seat, cup interior). QEM/edge-collapse decimation stays rejected
  (B3).
- B29 [V run, ../19-verify/v_uniondepth2.py S60r120=b/MIX_S60r120 -> b/logs/uniondepth_S60r120.out; floors as B25]
  Like-for-like check of the split claim (X8 had done S120 only). Union depth minus floor, 21 states:
  S60r120 (lid, pot, sweeper, cups at <= 60 mm parts; rack <= 120 mm): A-in-B median +0.4, range +0.0..+0.9; B-in-A
  median +0.3, range -0.5..+0.6 mm -> every state in both directions within 0.9 mm of the exact-collider floor.
  S120 (rack, pot split; lid, cups, sweeper V1): A-in-B +0.6 (0.0..+1.1), B-in-A +1.0 (+0.1..+2.3); 10 of 21 states
  exceed +1 mm in some direction, all with an unsplit V1 object as host (pot-in-lid +1.5..+2.3, blue-in-beige +1.3..
  +1.5, rack-in-sweeper +1.4, rack-in-cup +1.1).
  => [V] Restated B17/B20 on the union metric: rack + pot <= 120 mm puts the A-in-B direction within ~1 mm of the
  floor, but the reverse direction needs the small hosts split as well (S60r120). Then every public GT contact state
  is within 0.9 mm of the floor in both directions. The hull-count cost of S60r120 (4,281 hulls) is as in B20.
- B27d [V run, b/logs/V1c_*_h3_d1.0.log, b/logs/eval_obj_V1c.out] h 3 mm / iso 1.0 mm (10x fewer faces): rack
  93.4k faces -> 51 hulls in 82 s (1 mm W2: 68 hulls, 396 s), hull-vs-W2 p99 / max 9.27 / 13.00 mm (V1 8.79 / 12.59);
  lid 20.4k faces -> 59 hulls in 32 s, 3.61 / 5.15 (V1 3.05 / 4.64). => [E] For whole objects that the 0.025 L term
  dominates anyway (rack, pitcher), the h 3 input is a ~5x faster cold-cache build for +0.4-0.6 mm of p99; for split
  parts the extra 0.7 mm offset would be a large share of their ~1 mm tolerance, so split parts should stay at h 1.
- B30 [V run, b/b_utable2.py -> b/logs/utable2.out] Compact union-depth table (mm; range over the states of each
  contact type; both directions; floor = exact W2 colliders; C2all = coarse h 2 lid/pot/rack/blue + V1 sweeper/beige):

| contact (states) | floor | V0 | V2 | V1 | C2all | S120 | S60r120 |
|---|---|---|---|---|---|---|---|
| lid in pot (5) | 2.8-3.1 | 7.5-8.3 | 9.6-9.7 | 7.0-7.7 | 8.2-8.5 | 3.6-4.1 | 3.0-3.7 |
| pot in lid (5) | 3.2-4.0 | 5.7-6.4 | 6.7-7.3 | 5.0-6.1 | 5.2-6.1 | 5.2-5.7 | 3.5-4.3 |
| sweeper in rack (3) | 1.8-2.8 | 10.4-15.3 | 9.9-15.5 | 9.4-12.1 | 9.7-12.3 | 2.3-3.6 | 2.0-3.3 |
| rack in sweeper (3) | 3.4-4.0 | 5.1-6.0 | 5.3-6.1 | 4.8 | 4.3-4.7 | 4.7-4.8 | 3.5-4.2 |
| pot in rack (4) | 1.6-3.4 | 6.5-9.9 | 7.1-9.9 | 3.0-6.4 | 3.1-6.0 | 2.0-4.3 | 1.9-4.3 |
| rack in pot (4) | 2.1-2.8 | 6.4-9.0 | 6.6-8.7 | 3.0-4.7 | 3.0-5.1 | 2.3-3.7 | 2.3-3.3 |
| blue in rack (6) | 1.6-2.3 | 5.7-8.9 | 6.4-9.3 | 3.2-6.0 | 3.8-5.5 | 2.1-2.9 | 2.0-2.7 |
| rack in blue (6) | 1.6-2.0 | 3.5-4.0 | 3.8-4.2 | 2.2-3.3 | 3.1-3.5 | 2.2-2.7 | 1.8-2.0 |
| beige in blue (3) | 3.5-3.7 | 4.9-5.1 | 5.9 | 4.1-4.2 | 5.2-5.4 | 4.1-4.2 | 4.3 |
| blue in beige (3) | 3.4-3.7 | 4.8-4.9 | 5.1-5.3 | 4.9-5.0 | 4.7-4.8 | 4.9-5.0 | 3.9-4.0 |
| sweeper in dust pan (2, B26) | 2.1-2.2 | 3.3-3.4 | - | 2.3-2.4 (welded) | - | - | - |
| dust pan in sweeper (2) | 4.2-4.3 | 5.0-5.1 | - | 4.7-4.9 | - | - | - |
| board vs board (2, clearance <0) | -1.6 / -3.2 | +2.7 / +1.8 | - | <= -1.3 / <= -2.0 (welded) | - | - | - |

### Stage B addendum summary (answers; supersedes the B6/B8 wording "concavity dominant, voxel secondary")
1. Two independent causes, now separated on the like-for-like union metric, both directions (B25, B28):
   - Voxel preprocessing term. It is triggered by any input that fails CoACD's manifold check: all six public scans
     and the boards, which fail on ONE unwelded vertex (B26c). It is about half a voxel of outward offset per surface,
     and voxel = L/100 at the fixed resolution 50: lid 1.9 mm, pot 3.6, rack 5.1, pitcher 4.2. Measured 0.40-0.76 x
     the summed voxel sizes of a pair at res 25/50/100. Over the 21 states: median +2.9 mm (A-in-B) and +1.3 mm
     (B-in-A).
   - Concavity term: at most 0.025 x L of each mesh handed to CoACD (B10-B19's 107 meshes, plus the pitcher, dust
     pan and boards, B26d). Over the 21 states: median +3.9 mm (A-in-B) and +1.5 mm (B-in-A). The resolution does
     not change it.
   - The two are of similar size for lid/pot and cup/rack. Concavity dominates only where the rack hosts the sweeper
     (+7.5..+9.3 mm). B6's "V1 6.3 mm" for ep31 f160 was a per-hull artefact: the union depth is 9.4 mm.
2. Asset-side removal [V]:
   - The voxel term goes with watertight input that passes the check: W2 remesh for open scans, position welding for
     already-closed meshes. V1 removes a median 2.4 mm (44 %) of the public-asset excess A-in-B and 0.6 mm (31 %)
     B-in-A.
   - The concavity term goes with smaller meshes: S60r120 is within 0.9 mm of the exact-collider floor for every
     public GT contact state in both directions (B29). S120 manages that only in the A-in-B direction.
   - Floor: 1.6-4.3 mm. The GT poses and scans interpenetrate even with exact colliders.
3. Decimation [V]: QEM/edge collapse fails the check (B3). Coarse marching cubes with the iso raised to about
   0.3 h passes it with 4-10x fewer faces and about the same hull counts. The exact call is 0.9-2.5x faster at h 2
   and 4-5x faster at h 3 (shared host). It costs +0.2 mm median and up to +1.3 mm on seated or nested contacts
   (B27). Keep h 1 for split parts and seat hosts.
4. Newly covered objects (B26):
   - Boards (eval 25): the public asset turns a 1.6-3.2 mm GT clearance into interpenetration
     (union depth 1.5-2.7 mm). Welding alone restores the clearance. This is the cheapest and most clear-cut asset
     fix found.
   - Sweeper / dust pan (eval 19): the public asset is +0.8..+1.2 mm above the floor; welded meshes cut that to
     +0.2..+0.6.
   - Pitcher (eval 20): no GT object contact. Its 0.025 L = 10.4 mm tolerance only affects hand contact (V1 p99
     7.9 mm). Drop the four sealed inner void shells before shipping.
5. Not changed by this addendum: the hull-count and RAM costs of splitting (B11-B23, C3/C4, X1/X2) and the macOS-only
   caveat on single depths (C10).
