# Scorer check: does our local Track 3 scoring mean what Kaggle computes? (26 Oct 2026)

Part of the public reference check (`../`) for `docs/analysis/robustness-review-20261026.md`. CPU only, no GPU, no
Kaggle, no uploads. Public mocap is read only for scoring, after inference. The eval-side checks read only our own
files (rollouts, packed file, meshes), with no ground truth.

**Short answer.**
- `pipeline/score_registered.py` is the kit's scoring code with stand-ins for the hidden scan geometry. Its pose
  metric functions are the kit's own. Its frames, worlds, slot order, seeds, mesh budget, thresholds and SP-SR /
  MP-SR definitions match the kit exactly.
- The real kit packer plus the five unmodified official metric files give the same five numbers as
  `score_registered.py`, to 4 decimals, on three stored public rollouts. The stored pack-4 submission is bit-exact
  bookkeeping: rows equal the rollouts, xyzw order, meshes equal the library files, and the link frame is the mesh
  frame.
- What we cannot reproduce is the hidden geometry. The biggest source of local-vs-Kaggle uncertainty is the
  **registration seed**: the formula is the same, but a public twin has a different episode index, so it uses a
  different seed. Its draw-to-draw noise is about ±0.01–0.03 AUC per episode, and once a flip of −0.71. The anchor
  guess moves AUC by up to 0.025, the point set and symmetry axes by ≤ 0.005.

Status labels: **[M]** measured here (command below), **[D]** taken from a doc / box-stored file, **[H]** hypothesis.

---

## 1. `pipeline/score_registered.py` vs the kit's Track 3 scoring (line by line)

Code compared:
- ours: `pipeline/score_registered.py` at commit 9eca613, md5 c2ec4af7;
- kit: `metric_code/track_3/{AUC,SP-SR,MP-SR,RPE,MPPE}.py`, `_score_registered_track3`; `v2dlb/track3_pose.py`
  and its helpers.
- The five metric files differ only in `_METRIC` / `_METRIC_DISPLAY` [M, diff].
- Every helper `score_registered.py` imports from `v2dlb` has the same AST as its inlined copy in the Kaggle metric
  file [M, AST comparison]. The helpers are `_register_object_body`, `_convert_object_body`, `_align_registered_scene`,
  `_registered_pose_metric`, `_symmetry_*`, `_axial_rotations`, `_surface_moments`, `_align_rigid`,
  `_sample_mesh_surface`, `_add_auc`, `_rotation_matrix` and `budget_mesh`. The ICP constants also match: 25
  starts, 40 iterations, 90 % trim, 3000 samples.

| Item | Kit (Kaggle) | `score_registered.py` | Same? | Effect |
|---|---|---|---|---|
| Registration | `_register_object_body(candidate, scan, anchor, 1_000_003*ep + 101*slot)` | same call, same formula | code yes; **seed value no for a twin** (public ep ≠ eval ep) | seed noise ±0.01–0.03 per episode, rare flips (§2) [M] |
| Pose conversion | `_convert_object_body`; reference `+= R_ref @ anchor` | same | yes | 0 |
| Scene alignment | `_align_registered_scene`: rotation from the **lowest slot without an axis** (or slot 0's axis + direction to slot 1 when all slots are symmetric); **translation always from slot 0's anchor** at frame 0 | same function | yes | 0. Note: translation comes from slot 0 even when slot 0 is a cup (evals 8, 10, 14, 20, 32, 33). |
| Symmetric objects | config + README: beige_cup, blue_cup order 360 (1°), white_pot_lid order 2; others none | same set and orders | yes | 0 |
| Symmetry axes | host `axis{i}` (hidden; "from the physical geometry, ignoring tracking-marker attachments") | cups: distinct PCA axis of 1000 scan samples; lid: thinnest PCA axis | stand-in | ≤ 0.002 AUC (§2) [M] |
| Anchor | host `anchor{i}` (hidden) | scan surface centroid | stand-in | all 10 public scans have their surface centroid at the origin (< 0.01 mm) [M], so "origin" and "centroid" coincide; bbox centre: −0.025 … +0.003 (§2) [M] |
| ADD points | host `points{i} − anchor` (hidden count and sampling) | 1000 area-uniform surface samples, seed 7+slot | stand-in | 4000 points: \|ΔAUC\| ≤ 0.002; 500 scan vertices (the kit's documented ADD convention, `v2dlb/vertices.py`): ≤ 0.005 (§2) [M] |
| Host scan | confidential scan, decoded with a **16 MB limit** (`_decode_archive(..., 16_000_000)`) | full public scan (~100k faces, ~300k vertices each) | stand-in | the 10 public scans need 94.5 MB (float64), so the hidden scans **must be decimated or lower-resolution** [M]; decimation to 4096 / 20000 faces: §2b |
| Candidate mesh | `object_mesh_b64` payload = `budget_mesh(glb, 4096, 4096)`, npz-encoded | `budget_mesh(glb, 4096, 4096)` directly | yes | payload round trip is lossless: decoded == `budget_mesh` bit for bit, on all 36 packed meshes [M] |
| Frames | every solution row: eval episodes have contiguous frames 0..N−1 (sample grid) [M] | rollout: world-0 frames; perception: all frames | yes | 747 stored public rollouts: frames 0..T−1 = public parquet length, 1 world, slot order = public order [M] |
| Worlds | all worlds in the solution; `worlds_per_episode` = 1 | world 0 only | yes | 0 |
| Visibility | no mask: the grid is rectangular | none | yes | 0 public object-frames invisible [D, resolve step] |
| Quaternions | normalised (submission and solution) | not normalised | tiny difference | \|norm − 1\| ≤ 1.5e−7 in rollouts and the pack [M]: none |
| Reference poses | hidden mocap (float64?), xyzw | public parquet pose (float32, wxyz → xyzw) | stand-in | assumed the same capture |
| AUC | `_add_auc`: thresholds 0.01..0.09 m (9), strict `<`, trapezoid on linspace(0,1,9), mean over bodies, then over episodes | same function, per episode | yes | 0 |
| SP-SR / MP-SR | SP: mean over objects of the time-mean position error ≤ 0.10 m and time-mean symmetric orientation error ≤ 0.5 rad. MP: every object < 0.03 m and < 30°. Positions at the registered anchor. | same function | yes | 0 |
| MPPE / RPE | 6 keypoints at ±5 cm along the registered body axes / relative position in object 1's frame, symmetry-aware | same | yes | 0 |

**Not the same metric: `sim_vs_ref` (`pipeline/qa.py policy`).** The workflow context calls it "the same kit
metric … against OUR reference". That is not accurate, and it matters for reading GT-free numbers:
- it uses the kit's **legacy unregistered** path: `_warp_to_reference_start`, which aligns all objects on **slot 0's
  full frame-0 orientation** even for a cup, and `_object_add` with **no symmetry**, so cup spin is penalised;
- its ADD points are 500 points on a **5 cm sphere about the mesh origin**, not surface points: rotation errors of
  large objects are under-weighted (rack 51 cm, pitcher 42 cm long).
- It is a consistent GT-free yardstick for one episode's variants. It is not a stand-in for Kaggle's number.
- [H1] A registered `sim_vs_ref` would rank checkpoints closer to the registered mocap AUC on public episodes. This
  would be the kit's `_score_registered_track3` path with our own mesh as the "scan" (identity registration, our
  surface centroid, symmetric axes). Falsify: on public episodes with ≥ 3 stored checkpoints, if its Spearman
  correlation with the mocap AUC is not higher than `qa.py`'s, keep `qa.py`.

---

## 2. Sensitivity of public scores to our stand-ins for the hidden geometry

Method:
- `score_variants.py` re-implements `score_registered.py` around the same kit calls. With all defaults it reproduces
  the box-stored `score_registered.json` **exactly** on all 7 tracks [M].
- Tracks: perception `poses_world_vo.npz` of the 25 Oct precision sweep (base arm), scored with `library_v2`, the
  templates they were tracked with.
- Variants: `n4000` (4000 surface points); `bbox` (anchor = bounding-box centre); `vtx500` (500 scan vertices,
  `default_rng(0)`, the kit's `v2dlb/vertices.py` ADD convention); `seed1` / `seed2` (registration seed + 1 / + 2);
  `axisz` (cup axis = scan +z); `axisfit` (cup axis = the direction that makes the scan most rotationally
  symmetric, `fit_axis`: 1.5° / 2.1° from PCA for blue / beige cup, 2.9° / 0.8° from z).

AUC change vs base [M]:

SENS_TABLE

What it means:
- **Point count / sampling and symmetry axis: negligible.** Mean \|ΔAUC\| ≤ 0.002; MPPE / RPE unchanged.
- **Anchor:** it only matters through the registration scale.
  - With scale s = r_scan / r_ours ≠ 1, the anchor enters the converted pose as R(1/s − 1)·a (`scale_ratios.txt`).
  - Our scales: cups 1.12–1.14, pot 0.963, pitcher 1.030, rack 0.976.
  - For a bbox anchor: pot 2.5 mm, pitcher 1.9 mm.
  - It also matters through the slot-0 translation pin. Measured: ep13 −0.025, ep2 −0.013, others ≤ 0.004.
  - Since every public scan is centred on its surface centroid, the centroid is the likely host anchor [H2].
    - Falsify: a public statement or kit update naming another anchor.
    - The bbox numbers are the cost if H2 is wrong.
- **Registration seed: the dominant stand-in uncertainty.**
  - Public seeds are not the eval seeds. A twin's local score is one draw.
  - Draw-to-draw: ep18 +0.023 / +0.028; ep22 +0.014 / +0.031 (pitcher 0.750 → 0.805); ep2 −0.008 / −0.014;
    ep31 +0.017 / **−0.709**.
  - The −0.709 is a registration flip: the library_v2 rounded sweeper registers at **177°** with seed 1_000_003·31+2.
    Rack AUC 0 and sweeper 0.19; SP-SR and MP-SR both flip to 0.
  - The review already lists sweeper flips (4 of 40 seeds). This is one more, on a public track.
  - Consequence: any single-seed local A/B of a submitted mesh (e.g. `meshswap-20261026`) carries this noise. See
    §2c for the pack-5 pitcher.

SENS2_BLOCK

---

## 3. Submission side: from simulated poses to submitted rows

Chain (static review):
- `ops/jobs/pack_eval.sh` → `submit_pack.sh` → the kit's `examples/run_policy_evaluation.py` (pristine FlashCHORD
  8c778f9, one world, frame 0, explicit reset).
- That writes `episode_XXXXXX.parquet`: `achieved_position_*`, `achieved_quaternion_{x,y,z,w}`; metadata
  `quaternion_order=xyzw`, `position_unit=meter`.
- `tools/pack_submission.py` reads it with `read_trajectory` (it honours `wxyz` if declared). It takes the world-0
  rows on the sample grid and writes `pos_x..quat_w` (xyzw, float64, parquet, no rounding).
- It attaches `budget_mesh(meshes/episode_X/<obj>.glb)` on each object's first row. `submit_pack.sh` copies
  `LIB/<obj>.glb` (library_v3, `EP_LIB` per episode).

The simulator body:
- `make_assets.py` / `support_fill.py` URDF: one link, visual and collision `origin 0 0 0`, `rpy 0 0 0`,
  `scale 1 1 1`. The mesh is loaded with trimesh `force='mesh'` and re-exported flat; library glbs have no
  non-identity nodes [M]. Link frame = mesh frame.
- The inertial origin is the COM offset only.

Measured:
- **Pack 4 (the uploaded file, sha256 59db1c31…) audit** [M, `check_pack.py` → `check_pack.json`]:
  - 9120 rows; row ids == the kit sample.
  - Every row == the world-0 achieved pose of the rollout pack 4 packed, max abs diff **0.0**, xyzw.
  - Body names == roster order in all 20 episodes. \|q\| − 1 ≤ 1.5e−7.
  - Exactly one payload per (episode, object), on its first row.
  - Every payload == `budget_mesh(packed glb)` bit for bit.
  - Every packed glb is byte-identical to `meshes/library_v3/<obj>.glb`; eval 8's beige cup is library_v3x, as
    the pack README says.
- **Simulator copies vs packed meshes** (`check_pack.json`, `filled_assets.txt`):
  - All URDF visuals are at origin / identity / scale 1.
  - Where the grasp-lock reference's asset differs from the packed mesh (evals 3, 19, 20, 25, 32), it is the support
    fill. The packed surface lies on the simulator surface: median 0.000 mm, extents equal within 0.5 mm. Only a slab
    of ≤ 5 mm is added below.
  - So the body frame is the same. Caveat: pack 4 pulled these asset folders with `cp -rn`; standard-learner evals
    (1, 10, 19, 25, 28, 30) used `/content/assets` built on the box from library_v3, which is not stored.
- **Link frame, not COM frame:**
  - The frame-0 gap between achieved and reference is 0.7–0.9 mm on ep21, against a COM offset of 24.0 mm for the
    pitcher.
  - It is 3.7 mm on ep11, against a COM offset of 17.8 mm for the beige cup.
  - A COM-frame recording would show the COM offset [M].
- **End to end on stored public rollouts** [M, `kit_e2e.py`]:
  - Method: the kit's unmodified packer (scratch kit copy whose roster / config / sample name the public episode),
    then the five unmodified official metric files, `score()`.
  - The host solution is built from public mocap and the public scan with `score_registered.py`'s stand-ins. The
    16 MB decode limit is raised for this test only, because the public scans are full resolution.
  - The packed rows equal the rollout exactly.

E2E_TABLE

**Frame 0 is recorded after the first control step**, and the kit aligns the whole scene on frame 0:
- The eval-20 cup is **14.71 mm below** its reference at frame 0, with rotation exactly 0.000°.
- That is free fall over one control step of 5 semi-implicit substeps of 10 ms: g·dt²·(1+…+5) = **14.715 mm**.
  Recorded frame 0 = state after step 1 [M].
- Consequences:
  - any first-step motion of the rotation-anchor object (lowest non-symmetric slot) rotates every frame;
  - any first-step motion of slot 0 translates every frame.
- Public rollouts with large first-step gaps (`frame0_gaps_public.txt`, `early_frames_public.txt`) [M]:
  - ep31 sweeper (slot 0, anchor) 9.2 mm / **11.0°**, staying ≈ 10° off;
  - ep27 / ep26 / ep12 rack ≈ 10 mm down (sinks and stays ≈ 9–12 mm low);
  - ep24 board 1 (slot 0) 10.4 mm / 3.7°.
- Eval rollouts in pack 4 (`check_pack.json`) [M]:
  - eval 20 cup (slot 0) 14.7 mm, then 40 mm and 9.6° at frame 1: the cup falls;
  - eval 30 sweeper (slot 0, anchor) 3.8 mm / 5.2°;
  - eval 32 spoon (anchor) 4.3°, cup 4.3°;
  - eval 16 spoon 3.2°.

F0_BLOCK

---

## Problems found

PROBLEMS

## Hypotheses (each with the experiment that would falsify it)

HYPOTHESES

## Commands (all on this CPU box, venv `refcheck/venv`, kit at `refcheck/kit/v2d_submission_kit`)

COMMANDS

## Files

FILES
