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
2. [V] The binding limit is the number of collision shapes, not the URDF loader. The official evaluation config uses
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
  - Open scans (cups, pot, lid, rack, pitcher): the W2 remesh (B2/B4). This is flood-filled air plus a 3 mm oriented
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
