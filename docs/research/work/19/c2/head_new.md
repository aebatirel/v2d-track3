# 19 — Collision hulls: can the CoACD inflation be removed on the asset side? (2026-10-06/07; stages A-C done, final)

Dig 19 (round 4, "D18 Hull inflation" in 16-synthesis §4). Markers: [V] verified, [E] estimate, [H] hypothesis.
Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/19/ (a_* stage A, b/ stage B, c/ and c2/ stage C;
verifier scripts in work/19-verify/). Source pins: nvidia-isaac/video_to_data @ 8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef
(evaluator), coacd 1.0.11 (tag b678aa08), newton 1.2.0, warp 1.14.0, trimesh 4.12.2, mujoco / mujoco-warp 3.8.1; kit
v2d_submission_kit (runner examples/run_policy_evaluation.py, scorer metric_code/track_3/AUC.py). Background: note 15
§C2/C4 (GT contact states 4-15 mm inside the pinned hulls).
Sections 1-6 were rewritten at the end of stage C2 (2026-10-07). They fold in the verifier (X1-X9) and the stage-B
addendum (B24-B30), which changed three earlier statements: the evaluation builds 1 world, so RAM is not the limit of
the documented path (X1, C17); the voxel term is as large as the concavity term on most pairs (B25); and only S60r120,
not S120, reaches the floor in both contact directions (B29). Earlier versions: work/19/c/notes_before_rewrite.md,
work/19/c2/notes_before_stageC2.md. The append-only logs (stages A, B, C, verifier, B addendum, C2) follow below and
hold the evidence for every number.
Platform caveat: every hull in this note except c/xplat, c2/rd/lin and c2/rd/lin64 was computed with the macOS coacd
wheel. Linux gives other hulls for the same input (C10, X5, X9), and Linux x86_64 and aarch64 can differ slightly
(C22). Single depths therefore carry about +-1-3 mm of platform noise, and the debris screen must run on Linux (C22).
The tolerance laws, counts and conclusions do not depend on this.

## 1. Answer (most important first)

1. [V] Yes, the inflation can be removed on the asset side, without touching the evaluator, the CoACD call or any
   physics setting. Every change is to files our reference parquet names (`object_urdf_paths` -> URDF -> meshes, A7).
   The loader accepts any number of `<collision>` meshes and primitives per link; each mesh is decomposed on its own,
   primitives are never decomposed, and a closed convex piece comes back from CoACD unchanged (A3, A9, A14, A15, C2).
2. [V] There are two independent causes, and both are removable (B10-B19, B25, B28):
   (a) Voxel preprocessing. Any mesh that fails CoACD's index-based manifold check is voxel-remeshed at L/100 and
       pushed out by about half a voxel per surface (lid voxel 1.9 mm, pot 3.6, pitcher 4.2, rack 5.1). All ten public
       collision meshes fail as newton loads them: UV-seam triangle soups, open scans, and the boards on a single
       duplicate vertex (A12, B26c). Over the 21 public GT contact states: median +2.9 mm in the A-in-B direction and
       +1.3 mm in the reverse direction. Watertight, welded input removes it.
   (b) Concavity tolerance. Hulls reach up to 0.025 x L of each mesh handed to CoACD; 110+ meshes obey this (rack
       12.6 mm, pitcher 10.2, pot 8.7, lid 4.6, cups 3.9-4.5, sweeper 3.1). Median +3.9 mm and +1.5 mm. Only smaller
       meshes (several `<collision>` meshes per link) or exact pieces remove it.
   The two terms are of similar size for lid/pot and cup/rack. Concavity dominates only where the rack hosts the
   sweeper (+7.5..+9.3 mm).
3. [V] The target is the floor, not zero. Exact colliders (the W2 solids) still show 1.6-4.3 mm in the GT contact
   states, from GT pose and scan error. Results against that floor (union-depth metric, both directions, B29/B30):
   - Watertight input alone (V1) removes 44 % of the public-asset excess in the A-in-B direction (median 2.4 mm) and
     31 % in the reverse direction.
   - Rack and pot split into parts of at most 120 mm (S120) bring A-in-B within ~1 mm of the floor. They leave
     +1.1-2.3 mm where an unsplit lid, cup or sweeper is the host.
   - S60r120 (lid, pot, sweeper and cups at <= 60 mm parts, rack at <= 120 mm) puts all 21 states within 0.9 mm of the
     floor in both directions.
   - The recommended set REC (§2: rack and pot S120, blue cup in 2 parts, lid, beige cup and sweeper whole) gives a
     median of +0.5 mm over the floor A-in-B and +1.0 mm B-in-A (C21). That removes about 90 % and 55 % of the
     public-asset excess; the public assets themselves are at +5.4 and +2.3 mm.
4. [V] At the documented evaluation (1 world), the limit is neither the loader nor RAM. The kit runner defaults to
   `--world-count 1`, and tracks.json submits one world (X1, C17). At 1 world even rack S120 + pot S120 builds in
   0.6 GB (X2). What splitting really costs:
   (i) Build-crash risk. CoACD sometimes emits debris hulls below 1e-15 m3, which MuJoCo refuses to compile (C6, X3).
       On macOS that is about 1 per 2,100 split hulls, plus 1 hull below 1e-12 m3 per ~650; it also happens on Linux,
       on other parts (C22). Our part construction is not the cause (C18). Every shipped part must therefore be
       screened on Linux and re-drawn if needed (C20, C22).
   (ii) Contact capacity (nconmax 4096 per world). When both partners of a seated or nested pair are split fine, the
       reset alone makes 760-1,340 contacts, and step cost rises about 10x (C7, C19).
   (iii) Cold-cache CoACD time: about 0.5 h for the split rack (C19).
   (iv) Platform dependence (C10).
   (v) Build RAM for 4096-world training: 0.1-1 TB for split rack episodes (C4, C14). This limits how we train, not how
       we are evaluated.
5. [V] The cheapest clear wins need zero geometric change: weld the dedicated collision meshes.
   - Boards (eval 25): the GT clearance of 1.6-3.2 mm is kept, instead of 1.5-2.7 mm of spurious interpenetration
     (B26b/c).
   - Sweeper / dust pan (eval 19): from +0.8-1.2 mm above the floor to +0.2-0.6 mm (B26b).
6. [V] Three alternatives are worse or no better:
   - `decompose_objects: false` would collide each object as one convex hull of <= 64 vertices, so every cavity
     disappears; it is also a physics-configuration change (C1).
   - Our own budgeted HACD-style merge does not beat CoACD at a fixed piece count (C8).
   - Re-orienting the input only re-draws the same tolerance (C12).
7. [E] A hull-aware reference projection (R4) is needed whatever the assets. Even floor-level colliders drift 5-11 mm
   in a 1 s hands-free settle from the GT reset states (C7). The asset fix shrinks the projection R4 needs from
   5-15 mm to 2-4 mm, and it shrinks the reset jolt: lid on pot 10.6 -> 1.7 mm, pot on rack 13.7 -> 2.4 mm. The 1 s
   tilt of a cup on the rack drops from 24 to 2-3 deg. On ADD-AUC's 1-9 cm bins each persistent centimetre costs about
   0.125 of that object's AUC (C19), so these are score-relevant magnitudes.
8. [V] The build-crash risk of splitting is real on Linux and has a working per-part fix (C18, C20, C22).
   - Of the four parts with a macOS crash hull, one (the lid part) also crashes on Linux aarch64 and x86_64
     (5.25e-16 m3); the other three are clean there.
   - One small re-draw (a 3 deg rotation, undone by `<origin rpy>`) cleared every crash hull on both platforms.
   - The two Linux architectures can still differ (95 vs 98 hulls, up to 0.5 mm) for the same input.
   - So the debris screen must run on the evaluator's Linux architecture (or on both) and iterate per part. A macOS
     screen proves nothing.

## 2. Recommended asset recipe (what the pinned loader accepts, for a 1-world evaluation)

- R0 [V]: keep `scene.decompose_objects: true` and every evaluator and physics setting. Change only the files our
  reference parquet names.
- R1. Every object; ship by default. Same hull count as the public assets and no new risk [V]:
  - Open scans (cups, pot, lid, rack, pitcher): W2 remesh (B2/B4).
    - Method: flood-filled air plus a 3 mm oriented shell behind single-sided walls, on a 1 mm grid; marching cubes at
      +0.3 mm; the field nudged off the iso level.
    - Fidelity: within 0.55 mm p99 of the scan; the lid reaches 1.5 mm at open rims.
    - Drop sealed inner void shells (the pitcher has four, B26d).
    - Do not use QEM or edge-collapse decimation; it fails CoACD's self-intersection check (B3).
    - Optional coarse grid (h 2 mm, iso 0.6 mm) for whole objects that host no seated contact, such as the pitcher
      and an unsplit rack. It cuts cold-cache time 1.5-2.5x for +0.2 mm median (B27).
  - Already-closed collision meshes (sweeper, dust pan, boards): weld by position, nothing else (B9, B26).
  - Packaging (A9-A16, C2):
    - one untextured binary STL per `<collision>`, all on a single root link;
    - URIs relative to the URDF;
    - an explicit `<inertial>`;
    - the visual GLB unchanged;
    - shipped under an `assets/` tree beside the reference parquet.
  - Result: V1 hull counts are 9-88 per object, and the smallest hull is >= 7e-9 m3 (coarse-grid variants included), far from the crash threshold (C18).
- R2. Targeted splits, only where a measured at-risk contact needs one (1-world evaluation) [V geometry; E physics]:
  - Rack at <= 120 mm (S120: 15 parts, ~1,200 hulls). Eval 14, 15, 16, 28, 30. The highest-value single item.
  - Pot at <= 120 mm (S120: 7 parts, 415 hulls), or its rim band only (RIM33, 399). Eval 1, 3/5/6, 28.
  - Blue cup in 2 parts (CUP2, 179 hulls). Eval 32/33 interior, also usable in 10 and 14.
  - Keep the lid, beige cup and sweeper whole (V1 or welded). Splitting these hosts to 60 mm would remove the
    remaining +1.1-2.3 mm in the reverse direction (C21). The cost is 6-8x the reset contacts in seated and nested
    states (C19), and the S60 lid part also produced a crash hull on Linux (C22).
  - Part construction (B11): recursive bisection of the W2 solid down to L_max. Each part is closed with flat caps
    (marching cubes on max(field, box SDF), same nudge). One STL per part.
  - Acceptance screen per part (C20, C22). Run it in Linux containers with the manylinux coacd 1.0.11 wheel, on
    x86_64 and aarch64 (they can differ), on the float32 vertices that trimesh 4.12.2 loads from the shipped STL:
    - "Mesh Manifoldness: true";
    - smallest hull volume > 1e-12 m3 (1000x margin over MuJoCo's 1e-15); otherwise re-draw the part with a small
      rotation compensated by `<origin rpy>`, or with shifted cut planes, and screen again;
    - newton `add_urdf` keeps every `<collision>`;
    - reset contacts at the public twin states well below nconmax ([E] target < 1,000 including hands);
    - record the hull counts and the cold-cache build time.
  - Training: at 4096 worlds these assets need 0.1-1 TB of build RAM (C14 model). Either train the rack episodes at
    <= ~60-110 worlds per 16 GB, or train on R1 files and evaluate on R2 files under the same paths ([H]: a mm-level
    sim gap).
- R3. Exact pieces [V mechanism (A14, A15, C10); H for whole objects]: URDF primitives or closed convex pieces with
  <= 64 vertices. They never change in CoACD, carry no debris and do not depend on the platform.
  - Spoon (fully ours; no public asset): a capsule chain for the handle plus <= 4 closed convex bowl pieces, i.e.
    <= 8 shapes.
  - Rack as boxes: not prototyped. This is the only route to floor-level rack contacts that would also keep 4096-world
    training cheap.
- R4 [E; needed in every case]: project the reference states out of penetration against the Linux hulls of the shipped
  assets, then settle-test them (note 15 design need 4).

## 3. Effect on the at-risk eval episodes

Notation:
- Depths are union depths in mm from the public twin states (B30, C21), written as floor / V0 public / V1 (R1) /
  recommended set (REC, C21; for eval 1 also RIM33 from X7). The two directions are separated by ";" (A in B; B in A).
- Jolt is the A-relative-to-B displacement 50 ms after reset; settle is after 1 s (C7, MuJoCo CPU, no hands) [E]. The
  third value is C7's S120 set (rack and pot split, others V1), the closest measured set to REC.
- Shapes are the collision shapes per episode with the recommended assets. Cold is the first-build CoACD time on this
  macOS host.
- RAM4096 is the C14 model for 4096-world training; at 1 world every row builds in < 1 GB (X2).

| eval | contact that matters | depths floor / V0 / V1 / REC | jolt, settle V0 -> V1 -> S120 | recommended | shapes, cold, RAM4096 |
|---|---|---|---|---|---|
| 1 pot+lid | lid on pot, start and end | lid in pot 2.8-3.1 / 7.5-8.3 / 7.0-7.7 / 3.6-4.1 (RIM33 3.0-3.7); pot in lid 3.2-4.0 / 5.7-6.4 / 5.0-6.1 / 5.2-5.7 | 10.6 -> 7.9 -> 1.7 mm; 1 s 15.6 -> 17.8 -> 11.1 mm | pot S120 (or RIM33) + lid V1; reset contacts 171 (lid S60 too: 3.0-3.7; 3.5-4.3, but 1,338 contacts) | 467, ~10 min, ~100 GB |
| 3/5/6 pot+spoon | spoon stirring in the basin | basin diameter 10 mm above the floor W2 130 / V0 110 / V1 113 / S120 129 mm; basin cells risen > 5 mm 36 / 30 / 2.9 % | n/a (spoon is ours) | pot S120 + spoon R3 | 423, ~8 min, ~85 GB |
| 10 blue+beige | nested cups | beige in blue 3.5-3.7 / 4.9-5.1 / 4.1-4.2 / 3.7 (CUP2); blue in beige 3.4-3.7 / 4.8-4.9 / 4.9-5.0 / 4.8-4.9 (S60 both cups: 4.3; 3.9-4.0) | 1.4 -> 1.4 mm; 1 s 14.6 -> 8.7 mm | blue CUP2 + beige V1; splitting the beige cup too gains ~1 mm in one direction for 6x the contacts (759) | 220, ~5 min, ~28 GB |
| 14 blue+rack | inverted cup on rack at end | blue in rack 1.6-2.3 / 5.7-8.9 / 3.2-6.0 / 2.1-3.0; rack in blue 1.6-2.0 / 3.5-4.0 / 2.2-3.3 / 2.0-2.6 | 7.2 -> 5.5 -> 3.8 mm; tilt 24 -> 15 -> 2.3 deg | rack S120 + blue CUP2 | 1,377, ~30 min, ~0.8 TB |
| 15/16 rack+spoon | spoon handle into the utensil tower | tower opening 5/15 mm above its floor W2 38/40, V0 22/30, V1 blocked/36, S120 38/38 mm; floor cells risen > 10 mm 50 / 35 / 2.9 % | n/a | rack S120 (same files) + spoon R3 | 1,206, ~26 min, ~0.6 TB |
| 28 rack+pot | inverted pot on rack at end | pot in rack 1.6-3.4 / 6.5-9.9 / 3.0-6.4 / 2.0-4.3; rack in pot 2.1-2.8 / 6.4-9.0 / 3.0-4.7 / 2.3-3.7 | 13.7 -> 4.7 -> 2.4 mm; 1 s 13.1 -> 4.6 -> 6.0 mm | rack S120 + pot S120 | 1,613, ~34 min, ~1 TB |
| 30 sweeper+rack | slot-0 sweeper starts between the dividers | sweeper in rack 1.8-2.8 / 10.4-15.3 / 9.4-12.1 / 2.4-3.1; rack in sweeper 3.4-4.0 / 5.1-6.0 / 4.8 / 4.5-4.6 | 5.5 -> 4.7 -> 4.8 mm; 1 s 12.9 mm/14 deg -> 11.7/16 -> 8.7/7 | rack S120 + sweeper welded; R1 alone does nothing here | 1,228, ~27 min, ~0.6 TB |
| 32/33 blue+spoon | spoon in the cup | interior diameter 10/40/120 mm above the floor W2 64/68/78, V0 62/68/73, V1 59/63/74, CUP2 61/67/76, S60 63/68/77 mm | n/a | CUP2 + spoon R3; V1 alone is worse than V0 near the floor | 187, ~4 min, ~22 GB |

Other eval episodes (R1 only):
- 25 boards: welding restores the GT clearance (the cheapest clear-cut fix).
- 19 sweeper / dust pan: weld both.
- 20 blue cup / pitcher: no object contact in the GT; W2 pitcher without its void shells.
- 8 beige cup / pot: no GT contact case among the public twins.
- 35-37 spoon: R3. 38 dust pan: weld.

Summary [E]:
- R1 is the safe baseline everywhere. It matters most for eval 25 (boards), 28 (pot jolt 13.7 -> 4.7 mm) and 14
  (cup tilt 24 -> 15 deg).
- The rack S120 is the one split shared by five episodes (14, 15, 16, 28, 30). It is the only fix for eval 30, where
  V1 leaves 9.4-12.1 mm in a 1.8-2.8 mm floor.
- Pot S120 serves 1, 3/5/6 and 28; CUP2 serves 32/33.
- Eval 10 is already near the floor.
- All rows still need R4. The board-level AUC estimate stays 16-synthesis rank 5 (+0.02-0.05); C19 gives the mm-to-AUC
  scale.

## 4. Question for the organisers (proposed wording; supersedes 16-synthesis §5 Q4)

"Track 3 simulation assets (FlashCHORD @8c778f90, evaluated with the kit's examples/run_policy_evaluation.py). Our
reference parquet names the object URDFs (`object_urdf_paths`).

(a) May we ship our own collision geometry for the provided objects, keeping the evaluator, the CoACD call
(`scene.decompose_objects: true`, threshold 0.05) and all physics parameters unchanged, and the visual mesh as given?
We mean:
- the provided collision meshes welded, or the scans made watertight (within 0.55 mm p99 of the scan);
- the same geometry split into several `<collision>` meshes on one link;
- URDF primitives or convex pieces fitted to the provided scans;
- for the spoon, which has no public asset, our own collision geometry.
Reason: with the provided meshes, CoACD's voxel preprocessing and its 0.05 tolerance put the public ground-truth
contact states 4-15 mm inside the collision hulls (lid on pot; cups, pot and sweeper in the rack; nested cups). The two
wooden boards, whose GT clearance is 1.6-3.2 mm, start 1.5-2.7 mm interpenetrated, because each board collision GLB
has one unwelded vertex and so is voxel-remeshed.

(b) The same question for `<inertial>`. The provided URDFs call the 0.3 kg mass a placeholder.

(c) Does validation run the kit runner at world_count 1 (tracks.json "worlds_per_episode": 1), or the flash_sac.yaml
default of 4096? Is there a time or memory limit on scene building? A split collision mesh can need up to about 30 min
of CoACD on a cold cache, and at 4096 worlds newton's build memory grows with (collision shapes per episode)^2.

(d) Which platform and CPU architecture runs validation (Linux x86_64 or aarch64)? For the same input, CoACD 1.0.11
gives different hulls on macOS and Linux, and slightly different ones on Linux x86_64 and aarch64. In rare cases this
decides whether MuJoCo compiles the scene at all: a CoACD hull below 1e-15 m3 stops the build with 'mesh volume is
too small'."

Until answered:
- [E] R1 is the least contentious change: it is the provided geometry, welded or made watertight. It is still an asset
  change and should be disclosed.
- R2 and R3 wait for (a); R2 also for (c).

## 5. Next steps (each with its falsification test)

1. Build the shipped R1 + R2 file set in a Linux container: rack S120, pot S120, CUP2 as STL parts, plus all R1 files.
   Screen every part as in §2 and re-draw the failures.
   Test: every part passes on both Linux aarch64 and x86_64 with min hull volume > 1e-12 m3. Expect the two to differ by
   up to ~0.5 mm (C22); the twin metrics of step 2 should be computed on the organisers' architecture once it is known.
2. Recompute the twin metrics (union depth, both directions) and the settle test on those Linux hulls, and compute the
   R4 projections.
   Test: the projected public twin states settle by < 2 mm / < 1 deg in 1 s.
3. GPU smoke (16-synthesis E1) at world_count 1 on the eval-28/30 twins, V0 vs R1 vs R1+R2 with hand grasps. Record
   peak host RAM, cold and warm build time, step time and maximum contacts.
   Test: no nconmax/njmax overflow, and step time within 2x of V0.
4. Spoon R3 asset: capsules plus closed convex bowl pieces.
   Test: every piece comes back from CoACD unchanged on Linux and has <= 64 hull vertices.
5. Send the §4 question; record the answer here and in 16-synthesis §5.
6. Optional R3 rack (boxes).
   Test: within 1 mm of the floor with <= 100 shapes; otherwise drop R3 for the rack.

## 6. Artifacts

- Stage A: work/19/a_*.py/.out; pinned sources in work/19/{src,newton,coacd}/.
- Stage B: work/19/b/ (W2 remeshes b/W2, b/W2c; hull sets b/V0x, b/V1, b/V1w, b/V1c, b/V2*, b/V3, b/V4_120,
  b/V4_60, b/MIX_*; parts b/S120, b/S60; logs b/logs/; V0 = work/15-verify/hulls11).
- Stage C: work/19/c/:
  - c_export.py and c_e2e.py: loader end-to-end check;
  - c_scale.py: build-RAM scaling;
  - c_cavity.py: cavity metrics;
  - c_settle.py: approximate settle test;
  - c_sliver*.py: debris crash check;
  - c_hmerge.py: own budgeted merge (negative result);
  - c_csplit.py and c/CS/: contact-zone splits;
  - c_rotdecomp.py and c_align.py: input orientation;
  - c_lincoacd.py, c_xcmp.py and c/xplat/: cross-platform check;
  - c_zone.py: contact zones.
  - The split-pot URDF and STL example is c/assets/white_pot/white_pot_split.urdf.
- Stage C2: work/19/c2/:
  - c2_debris.py: debris origin;
  - c2_redraw.py, run_redraw.sh and run_redraw_lin.sh: re-draw test, inputs c2/rd/, hulls c2/rd/{mac,lin,lin64}/;
  - c2_utable.py and c2/REC/ (link dir of the recommended set): union-depth table of the recommended recipe;
  - c2_splice.py: this rewrite (pre-rewrite copy c2/notes_before_splice.md);
  - logs in c2/logs/.
- Verifier: work/19-verify/ (v_scale.py, v_sliver.py, v_coacd.py, v_uniondepth*.py, xplat/).
- Environment: own venv work/19/venv (trimesh 4.12.2, newton 1.2.0, warp 1.14.0, mujoco and mujoco-warp 3.8.1,
  manifold3d, scikit-image, libigl, rtree); macOS coacd 1.0.11 from work/15-verify/pylib11; Linux coacd at
  c/xplat/lib_{arm64,amd64}, run in docker python:3.12-slim-bookworm.

---

