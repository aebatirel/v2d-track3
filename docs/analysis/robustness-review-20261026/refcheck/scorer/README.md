# Scorer check: does our local Track 3 scoring mean what Kaggle computes? (26–27 Oct 2026)

Part of the public reference check (`../`) for `docs/analysis/robustness-review-20261026.md`. CPU only (this 4-core
container), no GPU, no Kaggle, no uploads. Public mocap is read only for scoring, after inference. The eval-side checks
(§2d, §3) read only our own files and the public scans: no ground truth, no poses.

**Short answer.**
- **The bookkeeping is right.**
  - `pipeline/score_registered.py` is the kit's own scoring code with stand-ins for the hidden scan geometry.
  - Frames, worlds, slot order, the seed formula, mesh budget, thresholds and the SP-SR / MP-SR definitions match the
    kit exactly.
  - The kit's unmodified packer plus the five unmodified official metric files reproduce `score_registered.py` to
    4 decimals on 3 stored public rollouts.
  - The uploaded pack-4 file is bit-exact: rows equal the rollouts, xyzw order, meshes equal the library files, and
    link frame = mesh frame (§3).
- **What a local number does not mean: the registration step makes every episode score a lottery draw.**
  - The kit registers our mesh to a hidden scan with a fixed seed.
  - The hidden scan cannot be the released public scan file. One 16 MB decode limit covers all 11 objects, and the
    10 public scans alone need 94.5 MB as float64 soups [M, 26 Oct]. So it is a lower-resolution or re-meshed copy, of unknown
    resolution.
  - The registration of the **rotation-anchor object** (lowest slot without a symmetry axis) rotates the whole scene.
  - Stable meshes: about ±0.01–0.03 AUC per episode from seed or host resolution [M].
  - Near-symmetric meshes: a 180° flip and an AUC collapse of up to −0.71, at some seeds or host resolutions [M]:
    - sweeper (ep31) and boards (ep24) on public twins;
    - at Kaggle's own eval seeds, the submitted sweeper flips for 1 of 11 host resolutions on **eval 19** and 1 of 11
      on **eval 30** [M, GT-free].
- **The pack-5 pitcher swap (twin +0.098, Kaggle about −0.09 on eval 20) is explained by registration instability,
  not by the anchor or point stand-ins.**
  - The lathe pitcher `library_v3p` registers at a yaw spread of −14° … +7° over 30 seeds; library_v3 spreads −2.7° …
    0°.
  - On the same twin rollouts the swap is +0.04 … +0.10 at 3 of 5 seeds and −0.33 at the other 2. Mean −0.089 [M].
  - At Kaggle's eval-20 seed it is +0.064 with the full scan and −0.008 with a 20k-face scan.
  - Changing the anchor or the point set keeps it between +0.06 and +0.09 [M].
  - The 26 Oct work-log lesson ("hidden anchor and points differ") should be corrected to "registration of a
    near-rotationally-symmetric mesh is unstable".
- **Our stand-ins for the hidden anchor, points and axes matter little:**
  - 4000 points: \|ΔAUC\| ≤ 0.002;
  - bbox anchor: ≤ 0.025;
  - vertex points: ≤ 0.005;
  - cup axis: ≤ 0.002 [M].

Labels: **[M]** measured here (command in §Commands), **[D]** from a doc or a box-stored file, **[H]** hypothesis.

---

## 1. `pipeline/score_registered.py` vs the kit's Track 3 scoring (line by line)

Code compared:
- ours: `pipeline/score_registered.py`, last changed in commit 9eca613, md5 c2ec4af7;
- kit: `metric_code/track_3/{AUC,SP-SR,MP-SR,RPE,MPPE}.py` `score()` → `_score_registered_track3`, and
  `v2dlb/track3_pose.py` with its helpers.

Checks [M]:
- The five metric files differ only in `_METRIC` / `_METRIC_DISPLAY` (diff).
- Every `v2dlb` helper `score_registered.py` calls has the same AST as its inlined copy in the Kaggle metric file.
  The ICP constants also match: 25 starts, 40 iterations, 90 % trim, 3000 samples.

| Item | Kit (Kaggle) | `score_registered.py` | Same? | Effect |
|---|---|---|---|---|
| Registration | `_register_object_body(candidate, scan, anchor, 1_000_003*ep + 101*slot)`: scale = RMS-radius ratio, 3000 samples, trimmed ICP, best of 25 starts | same call, same formula | code yes; **seed value no for a twin** (public ep ≠ eval ep); host scan differs | §2b–2e: the dominant uncertainty |
| Pose conversion | `_convert_object_body`; reference `+= R_ref @ anchor` | same | yes | 0 |
| Scene alignment | `_align_registered_scene`, once at frame 0:<br>• rotation from the **lowest slot without an axis**; the lid (order 2) has an axis, so it never anchors;<br>• all slots symmetric: slot 0's axis plus the direction to slot 1;<br>• **translation always from slot 0** | same function | yes | 0. Translation comes from slot 0 even when slot 0 is a cup (evals 8, 10, 14, 20, 32, 33). |
| Symmetric objects | beige_cup and blue_cup order 360 (1° steps); white_pot_lid order 2; all others none | same set and orders | yes | 0 |
| Symmetry axes | host `axis{i}` (hidden) | cups: distinct PCA axis of 1000 scan samples; lid: thinnest PCA axis | stand-in | ≤ 0.002 AUC [M] |
| Anchor | host `anchor{i}` (hidden) | scan surface centroid; every public scan has it at the origin (< 0.01 mm) [M] | stand-in | bbox centre: −0.025 … +0.003 [M] |
| ADD points | host `points{i} − anchor` (hidden) | 1000 area-uniform samples, seed 7+slot | stand-in | 4000: ≤ 0.002; 500 vertices: ≤ 0.005 [M] |
| Host scan | hidden; the whole geometry archive (all 11 objects) is decoded with a **16 MB limit** | full public scan (~100k faces) | stand-in | the public scans cannot fit, so the hidden ones are lower resolution [M]. Effect: §2c–2d |
| Candidate mesh | `object_mesh_b64` = `budget_mesh(glb, 4096, 4096)`, npz | `budget_mesh(glb, 4096, 4096)` | yes | the payload round trip is lossless on all 36 packed meshes [M] |
| Frames / worlds | every solution row, rectangular grid; `worlds_per_episode` = 1 | world-0 rollout frames, or all perception frames | yes | 747 stored public rollouts have frames 0..T−1 = the public parquet length, 1 world, public slot order [M] |
| Visibility | no mask | none | yes | 0 invisible public object-frames [D, resolve] |
| Quaternions | normalised | not normalised | ~yes | \|q\| − 1 ≤ 1.5e−7 [M] |
| AUC | `_add_auc`: 9 thresholds 0.01–0.09 m, strict `<`, trapezoid on linspace(0,1,9), mean over bodies, then mean over episodes | same function | yes | 0 |
| SP-SR / MP-SR | **SP**: per object, time-mean position error ≤ 0.10 m and time-mean symmetric orientation error ≤ 0.5 rad, averaged over objects.<br>**MP**: every object < 0.03 m and < 30°.<br>Positions are taken at the registered anchor. | same function | yes | 0 |
| MPPE / RPE | MPPE: 6 keypoints at ±5 cm on the registered axes.<br>RPE: relative position in object 1's frame.<br>Both symmetry-aware. | same | yes | 0 |

**`sim_vs_ref` (`pipeline/qa.py policy`) is not this metric.**
- It uses the kit's legacy **unregistered** path (`_warp_to_reference_start`):
  - it aligns on slot 0's full frame-0 orientation, even when slot 0 is a cup;
  - it has no symmetry handling;
  - its ADD points are a 5 cm sphere about the mesh origin.
- It is a GT-free yardstick for comparing variants of one episode. It does not stand in for Kaggle's number.
- [H1] A registered `sim_vs_ref` would rank checkpoints closer to the registered mocap AUC.
  - Method: `_score_registered_track3` with our own mesh as the "scan".
  - Falsify: its Spearman correlation with the mocap AUC on public episodes with ≥ 3 checkpoints is not higher than
    `qa.py`'s.

---

## 2. Sensitivity of public scores to the stand-ins for the hidden geometry

Method: `score_variants.py` re-implements `score_registered.py` around the same kit calls, with each stand-in
switchable.
- Defaults: reproduces the box-stored `score_registered.json` exactly on all 7 tracks [M].
- `--n_points 4000`: equals `score_registered.py --n_points 4000` exactly on ep18 and ep2 (`n4000_direct/`) [M].
- Tracks: sweep-base perception (`20261025-sweep-a894083`), scored with `library_v2`, their tracking templates.

### 2a. Anchor, points, symmetry axis: small

| ep | objects | base AUC | 4000 pts | bbox anchor | 500 vertices | cup axis = z | cup axis fitted |
|---|---|---|---|---|---|---|---|
| 2 | pot + lid | 0.9823 | +0.0001 | −0.0129 | −0.0002 | | |
| 11 | blue + beige cup | 0.8978 | −0.0004 | +0.0016 | −0.0018 | −0.0020 | +0.0018 |
| 13 | blue cup + rack | 0.9605 | −0.0003 | **−0.0250** | −0.0001 | −0.0015 | −0.0003 |
| 18 | sweeper + dust pan | 0.9380 | +0.0021 | −0.0007 | +0.0053 | | |
| 22 | blue cup + pitcher | 0.8710 | −0.0006 | +0.0033 | −0.0026 | +0.0000 | +0.0000 |
| 24 | boards | 0.8117 | +0.0000 | −0.0009 | +0.0000 | | |
| 31 | sweeper + rack | 0.8050 | −0.0012 | +0.0025 | +0.0018 | | |
| mean \|Δ\| | | | 0.0007 | 0.0067 | 0.0017 | 0.0012 | 0.0007 |

- The anchor enters only through the registration scale, R(1/s − 1)·a (`scale_ratios.txt`), and through the slot-0
  translation pin.
- Our scales: cups 1.12–1.14, pot 0.963, pitcher 1.030 (lathe 1.001).
- [H2] The host anchor is the surface centroid, since every public scan is centred on it.
  - Falsify: a kit update or an organiser statement naming another anchor.
- SP-SR / MP-SR do not change in any of these variants; MPPE and RPE move by ≤ 0.4 cm (`sens/table.md`).

### 2b. Registration seed: ±0.01–0.03, and flips

Public seeds are not the eval seeds, so a twin's local score is one draw. AUC at seed offsets 0..6 (`seed_noise.md`,
from `sens/` and `sens2_INVALID_unwelded_decimation/`; the seed columns there are valid, only its decimation columns
are not) [M]:

| ep | objects | AUC at offset 0..6 | median | flips |
|---|---|---|---|---|
| 2 | pot + lid | 0.982 / 0.974 / 0.969 / 0.983 / 0.982 / 0.972 / 0.982 | 0.982 | – |
| 11 | blue + beige cup | 0.898 / 0.896 / 0.905 | 0.898 | – |
| 13 | blue cup + rack | 0.961 / 0.967 / 0.968 | 0.967 | – |
| 18 | sweeper + dust pan | 0.938 / 0.961 / 0.966 / 0.960 / 0.964 / 0.964 / 0.964 | 0.964 | – |
| 22 | blue cup + pitcher | 0.871 / 0.885 / 0.902 / 0.888 / 0.854 / 0.873 / 0.919 | 0.885 | – |
| 24 | boards | 0.812 / 0.813 / 0.808 / 0.810 / 0.819 / 0.805 / 0.837 | 0.812 | – |
| 31 | sweeper + rack | 0.805 / 0.822 / **0.096** / 0.799 / 0.805 / 0.811 / **0.096** | 0.805 | 2 of 7 (sweeper 177°) |

(`seed_noise.md` labels ep11 "flips [0, 1]" by mistake. Its flip test counted the library_v2 beige cup's registration
rotation over 90° (145° and 118°) without symmetry. That rotation is a harmless spin about the cup axis: the beige-cup
AUC stays 0.930–0.948 [M, `sens/ep11.json`].)

### 2c. Host-scan resolution: as large as the seed

The scan used for registration is welded and then decimated (`fast_simplification`). Anchor, points and axis stay from
the full scan.
- Decimation barely changes the geometry: centroid ≤ 0.46 mm, radius ratio 0.997–1.002
  (`decimation_quality_welded.txt`).
- The first attempt did not weld. The public scans are triangle soups, which decimate badly, so that attempt is
  invalid. It is kept as `sens2_INVALID_unwelded_decimation/`.

ΔAUC vs the full scan [M, `sens3/`]:

| ep | objects | base | 50k faces | 20k faces | 4096 faces |
|---|---|---|---|---|---|
| 2 | pot + lid | 0.9823 | −0.0032 | −0.0013 | −0.0003 |
| 13 | blue cup + rack | 0.9605 | +0.0078 | +0.0046 | +0.0115 |
| 18 | sweeper + dust pan | 0.9380 | −0.0048 | −0.0166 | +0.0174 |
| 22 | blue cup + pitcher | 0.8710 | +0.0066 | +0.0149 | +0.0050 |
| 24 | boards | 0.8117 | −0.0154 | **−0.4235** (board flip; SP and MP 1 → 0) | +0.0007 |
| 31 | sweeper + rack | 0.8050 | **−0.7093** (sweeper flip) | **−0.7093** | +0.0559 |

### 2d. Kaggle's own eval seeds, GT-free: which submitted meshes can flip?

Method:
- `reg_flip.py`: every submitted mesh is registered with the kit function at the exact eval seeds. Host = the public
  scan at full / 20k / 4096 faces.
- `reg_seeds.py` (via `run_part6.sh`): at each fixed eval seed, the host is swept over 11 resolutions from 2000 faces
  to full.
- Our meshes are built in the scan frame, so a correct registration is 0.2–4°. Full tables: `part4_tables.md`.

Results [M]:
- **No flips** at any eval seed and any of the 3 hosts for:
  - white_pot (6 evals), lid, blue_cup (5), beige_cup v3 and v3x, dust pan, rack (5), pitcher v3;
  - boards: 11 hosts.
- **Sweeper (library_v3 as submitted; library_v2 the same): it flips 178° about its long axis.**
  - Eval 30 (slot 0, rotation anchor): flips at 4096 faces only.
  - Eval 19 (slot 0, rotation anchor): flips at 16000 faces only.
  - That is 1 of 11 hosts each, consistent with the review's 4 of 40 random seeds.
  - A flip costs ≈ −0.7 episode AUC (ep31) and SP / MP 1 → 0, i.e. ≈ −0.035 Track 3 AUC per flipped episode
    (derived).
  - Whether Kaggle's hidden scan triggers it is unknowable from here: [H3].
  - This corrects the review's §9 statement that "the scorer's seeds sit in the majority". That holds only for the
    full-resolution host, which the 16 MB limit rules out.
- **Lathe pitcher (library_v3p, pack 5 only):** 3.0–9.2° at the eval-20 seed depending on the host. library_v3:
  2.2–2.8°.

### 2e. The pack-5 pitcher swap, re-examined

Same two ep21 twin rollouts (`20261025-twin21arc-ee7ba8e` r1, r2); only the submitted pitcher changes [M,
`meshswap_seeds/`]:

| scoring variant | r1 v3 → v3p | r2 v3 → v3p | mean Δ | pitcher frame change vs seed 0 (v3 / v3p) |
|---|---|---|---|---|
| seed 0 (the scorer's twin seed) | 0.790 → 0.868 | 0.771 → 0.872 | +0.089 | 0 / 0 |
| seed +1 | 0.817 → 0.899 | 0.805 → 0.894 | +0.086 | 0.4° / 1.0° |
| seed +2 | 0.824 → 0.858 | 0.810 → 0.859 | +0.042 | 0.6° / 1.7° |
| seed +3 | 0.768 → **0.436** | 0.759 → **0.427** | **−0.332** | 0.4° / 15.6° |
| seed +4 | 0.825 → **0.498** | 0.810 → **0.478** | **−0.329** | 0.9° / 12.0° |
| Kaggle's eval-20 seed, full scan | 0.772 → 0.832 | 0.761 → 0.828 | +0.064 | 0.4° / 3.7° |
| Kaggle's eval-20 seed, 20k-face scan | 0.769 → 0.762 | 0.759 → 0.751 | **−0.008** | 0.5° / 5.5° |
| 20k-face scan, seed 0 | 0.803 → 0.881 | 0.783 → 0.890 | +0.092 | 0.3° / 0.3° |
| bbox anchor | 0.812 → 0.870 | 0.800 → 0.876 | +0.067 | |
| 500 scan vertices | 0.788 → 0.867 | 0.769 → 0.870 | +0.090 | |

Seed spread over 30 seeds from Kaggle's eval-20 pitcher seed 20000161 [M, `regseeds/`, GT-free]:

| mesh | host | yaw min / median / max | seeds > 5° from the median pose |
|---|---|---|---|
| library_v3 | full / 20k / 4096 | −2.7 / −1.2 / 0.0 · −2.5 / −1.2 / −0.2 · −2.3 / −1.1 / −0.2 | 0 / 0 / 0 of 30 |
| library_v3p | full / 20k / 4096 | −14.2 / −0.1 / 7.0 · −10.7 / 2.2 / 6.9 · −10.8 / 3.2 / 6.9 | 20 / 10 / 4 of 30 |

Reading:
- The lathe body is nearly rotationally symmetric, so ICP barely constrains its spin about the vertical axis.
- In eval 20 / ep21 the pitcher is the rotation anchor (the cup is symmetric), so its registered yaw rotates the whole
  scene about the slot-0 cup.
- The +0.098 of `docs/analysis/meshswap-20261026` was a favourable draw.
- Kaggle's ≈ −0.09 on eval 20 (derived: −0.0045 × 20 episodes, `docs/work-log.md`, 26 Oct 17:15) lies inside the
  twin's draw distribution (−0.33 … +0.10, mean −0.089).
- The anchor and point stand-ins do not reverse the sign.
- Also: with the stable library_v3 pitcher, the episode AUC still ranges 0.768–0.825 over seeds. The pitcher moves
  ≤ 0.9° and the cup's registration also changes. ±0.03 is the floor for any single-draw twin A/B.

---

## 3. Submission side: from simulated poses to submitted rows

Chain (static review):
- `ops/jobs/pack_eval.sh` → `submit_pack.sh` → the kit's `examples/run_policy_evaluation.py` (pristine FlashCHORD
  8c778f9; one world, frame 0, explicit reset).
- That writes `episode_XXXXXX.parquet`: `achieved_position_*` and `achieved_quaternion_{x,y,z,w}`, with metadata
  `quaternion_order=xyzw` and `position_unit=meter`.
- `tools/pack_submission.py` reads it with `read_trajectory` (it honours a declared `wxyz`). It writes the world-0
  rows on the sample grid as `pos_x..quat_w`: xyzw, float64, no rounding.
- It attaches `budget_mesh(meshes/episode_X/<obj>.glb)` on each object's first row. `submit_pack.sh` copies
  `LIB/<obj>.glb` (library_v3; `EP_LIB` per episode).
- The simulator URDF (`make_assets.py` / `support_fill.py`) has one link:
  - visual and collision `origin 0 0 0`, `rpy 0 0 0`, `scale 1 1 1`;
  - library glbs have no non-identity nodes, so link frame = mesh frame [M];
  - the inertial origin is only the COM offset.

Measured [M]:
- **Pack 4, the uploaded file (sha256 59db1c31…)** (`check_pack.py` → `check_pack.json`):
  - 9120 rows; row ids == the kit sample.
  - Every row == the world-0 achieved pose of the packed rollout: max abs diff 0.0, xyzw.
  - Body names == roster order in all 20 episodes.
  - Exactly one payload per object, each == `budget_mesh(packed glb)` bit for bit.
  - Every packed glb is byte-identical to `meshes/library_v3/<obj>.glb`. Eval 8's beige cup is library_v3x, as
    documented.
  - Where a simulator asset differs from the packed mesh (evals 3, 19, 20, 25, 32), it is the support fill: the
    packed surface lies on the simulator surface (median 0.000 mm) plus a slab of ≤ 5 mm below
    (`filled_assets.txt`).
  - Caveat: the standard-learner evals (1, 10, 19, 25, 28, 30) used `/content/assets` built on the box from
    library_v3, which is not stored.
- **Link frame, not COM frame:**
  - the frame-0 achieved-vs-reference gap is 0.7–0.9 mm on ep21, against a pitcher COM offset of 24.0 mm;
  - it is 3.7 mm on ep11, against a beige-cup COM offset of 17.8 mm.
- **End to end on stored public rollouts** (`kit_e2e.py`):
  - the kit's unmodified packer (scratch kit copy whose roster / config / sample name the public episode), then the
    five unmodified official metric files' `score()`;
  - host solution = public mocap + public scan with `score_registered.py`'s stand-ins; the 16 MB limit was raised for
    this test only.

| ep | rollout | mesh lib | kit AUC / SP-SR / MP-SR / RPE / MPPE | `score_registered.py` | packed − rollout |
|---|---|---|---|---|---|
| 21 | twin21arc r1 | v3 | 0.790323 / 1 / 0 / 1.981356 / 2.505146 | 0.7903 / 1 / 0 / 1.9814 / 2.5051 | 0.0 |
| 2 | e3 r1 | v3 | 0.451348 / 0 / 0 / 17.690907 / 10.671308 | 0.4513 / 0 / 0 / 17.6909 / 10.6713 | 0.0 |
| 11 | twin11v3x r1 | v3x | 0.566834 / 1 / 0 / 16.719368 / 9.137477 | 0.5668 / 1 / 0 / 16.7194 / 9.1375 | 0.0 |

**Frame 0 is recorded after the first control step**, and the kit aligns the scene on frame 0.
- Evidence: the eval-20 cup is 14.71 mm below its reference at frame 0, with 0.000° rotation. That is free fall over
  5 semi-implicit 10 ms substeps, g·dt²·(1+…+5) = 14.715 mm [M].
- Test (`f0/`): replace the rollout's frame 0 by its reference frame 0. This is a diagnostic only; submitted rows must
  stay the rollout's.

| ep | rollout | first-step gap of the anchor / slot 0 | AUC | AUC with frame 0 = reference | Δ |
|---|---|---|---|---|---|
| 31 | ev30rp r1 / r2 / r3 | sweeper (slot 0, anchor) 9.2 mm, **11°**, stays ≈ 10° off | 0.770 / 0.736 / 0.741 | 0.823 / 0.806 / 0.791 | **+0.053 / +0.070 / +0.050** |
| 24 | ev3 r1 | board 1 (slot 0) 10.4 mm, 3.7° | 0.308 | 0.365 | +0.057 |
| 26 | w1 r1 | rack (slot 0) 9.0 mm down | 0.537 | 0.574 | +0.037 |
| 27 | ev2 r1 | rack (slot 0) 10.7 mm down, stays low | 0.954 | 0.911 | −0.043 |
| 21 | twin21arc r1 / r2 | 0.7–0.9 mm | 0.790 / 0.771 | 0.772 / 0.762 | −0.018 / −0.010 |
| 12 | ev2 r1 | rack 10.7 mm (slot 1) | 0.921 | 0.920 | −0.001 |
| 2, 11 | e3 r1, twin11v3x r1 | 1–3.7 mm | 0.451, 0.567 | 0.452, 0.565 | +0.000, −0.002 |

Reading:
- The transient is not a uniform penalty.
- Replacing frame 0 gains +0.04–0.07 where the slot-0 or anchor object moves in the first step and then tracks badly:
  - ep31: the sweeper settles 11° off its reference and stays there;
  - ep24 and ep26 also gain.
- Where the object sinks and stays sunk (ep27), the sim's own frame 0 is the better alignment (−0.043).
- So the cost of the transient is an episode-specific ±0.05, not a fixed bias.
- Eval rollouts in pack 4 with similar first-step motion [M, `check_pack.json`]:
  - eval 30 sweeper (slot 0, anchor) 3.8 mm / 5.2°;
  - eval 32 spoon (anchor) 4.3°;
  - eval 20 cup (slot 0) 14.7 mm, then it falls.
- [H4] Starting the simulation from a settled reference (objects resting on the table, not penetrating or floating)
  would remove most of the anchor transient. Falsify: on ep31, a rollout from a settled initial state still shows an
  anchor rotation over 5° in step 1.

---

## Problems found

1. **Registration lottery (dominant):**
   - The kit's fixed-seed registration to a hidden, necessarily lower-resolution scan flips near-symmetric meshes at
     some seeds or host resolutions.
   - Public: ep31 sweeper (−0.71) and ep24 board (−0.42).
   - At Kaggle's eval seeds: the submitted sweeper flips for 1 of 11 host resolutions on eval 19 and on eval 30.
2. **Single-draw twin A/Bs of submitted meshes are not reliable.**
   - The pitcher swap (+0.098 local, ≈ −0.09 Kaggle) came from the lathe mesh's yaw instability.
   - The 26 Oct lesson in `docs/work-log.md` names the wrong cause (anchor / points).
   - `docs/analysis/meshswap-20261026` needs a seed- and host-ensemble re-score before any further swap.
3. **The review's §9 sweeper statement is incomplete.** "The scorer's seeds sit in the majority" holds only for the
   full-resolution host.
4. **`sim_vs_ref` is not the kit metric.** It is unregistered, ignores symmetry and uses 5 cm sphere points (from
   26 Oct, unchanged).
5. **The frame-0 transient of the rotation anchor costs up to 0.07 per episode** (ep31). The worst eval candidates are
   eval 30 and eval 32 (anchor rotated 4–5° in step 1).
6. **Our own bugs, fixed:**
   - `score_variants.py --trajs sim` removed the reference before `f0_from_ref`, so the 26 Oct `f0/` results (in
     commit e2f0a6b) were a no-op. They are moved to `f0_INVALID_noop/` and re-run.
   - The 26 Oct unwelded decimation (`sens2_INVALID_unwelded_decimation/`) is invalid; its seed columns are valid.
7. **Asset provenance caveat:** the box-built `/content/assets` of the standard-learner evals are not stored.

## Hypotheses (each with the experiment that would falsify it)

- **H1** A registered `sim_vs_ref` ranks checkpoints closer to the mocap AUC. Falsify: Spearman on public episodes
  with ≥ 3 checkpoints is not higher than `qa.py`'s.
- **H2** The host anchor is the scan's surface centroid. Falsify: a kit update or organiser statement naming another
  anchor.
- **H3** The hidden scans are decimated public scans, so the eval-19 / eval-30 sweeper flip risk is about 1 in 10 per
  episode.
  - Falsify, GT-free: none. The direct test is a submission that changes only the sweeper mesh (owner's call;
    it would tune on eval results).
- **H5** A registration-stability gate predicts Kaggle-side flips.
  - Gate: refuse a submitted mesh if over 10 % of (30 seeds × 11 host resolutions) land more than 5° from the
    median pose.
  - It would have rejected library_v3p (20 of 30 seeds at full resolution).
  - Falsify: on public objects, gate verdicts do not match flips against the true scan in a seed × host sweep.
- **H6** A sweeper mesh that breaks the 180° near-symmetry (for example, the scan-side handle details) removes the
  flip mode. Falsify: `run_part6.sh` on that mesh still flips at some host resolution at the eval-19 / eval-30 seeds.
- **H4** (§3) A settled initial state removes the anchor transient.

## Commands

Machine: this CPU container (4 cores). Venv `refcheck/venv`, kit `refcheck/kit/v2d_submission_kit`, store `refcheck/store`
(paths in the scripts). Repo branch main-bsky37 at e2f0a6b plus these uncommitted scripts. One heavy process at a time.

```
# 26 Oct (previous session of this check)
bash run_sensitivity.sh        # §2a, §2b seeds 1-2   -> sens/ep*.json, sens/table.md (summarise.py)
bash run_part3.sh              # §3 e2e (kit_e2e.py + score_registered.py), §2b seeds 3-6 -> e2e/, sens2_INVALID_unwelded_decimation/
                               #   (its f0 step was a no-op, see Problems 6; the session ended during it)
python -I check_pack.py ...    # §3 pack-4 audit -> check_pack.json (inputs in its docstring)
python -I scan_geometry.py T3 KIT LIB... > scan_geometry.json   # anchors, axes, node transforms
# 27 Oct (this session), 03:23-04:06 UTC
bash run_part4.sh              # f0/ (fixed), meshswap_seeds/, regflip/reg_flip.json, sens3/
bash run_part5.sh              # regseeds/water_pitcher_library_v3{,p}.json (30 seeds x 3 hosts)
bash run_part6.sh              # reghosts/*.json (fixed eval seed x 11 host resolutions)
python -I pipeline/score_registered.py {18,2} <sweep-base>/ep{18,2}/poses_world_vo.npz --meshes meshes/library_v2 \
    --n_points 4000 --t3 ... --kit ... --out n4000_direct/ep{18,2}_score_registered_n4000.json
KIT=... T3=... python -I summarise_part4.py . > part4_tables.md
```

Logs: `refcheck/work/scorer/{sens,p3,p4}/` in the scratchpad (not in git). No step failed on 27 Oct.

## Files

- Scripts:
  - `score_variants.py`: stand-in variants of `score_registered.py`;
  - `kit_e2e.py`: kit packer plus official metric files;
  - `check_pack.py`: pack-4 audit;
  - `reg_flip.py`: eval-seed registrations;
  - `reg_seeds.py`: seed or host sweep of one mesh;
  - `scan_geometry.py`;
  - `summarise.py`, `summarise_part4.py`;
  - `run_*.sh`.
- Results:
  - `sens/`, `sens3/`, `seed_noise.md`;
  - `e2e/`, `check_pack.json`;
  - `f0/`;
  - `meshswap_seeds/`, `regflip/`, `regseeds/`, `reghosts/`;
  - `n4000_direct/`;
  - `part4_tables.md` (all 27 Oct tables);
  - `scale_ratios.txt`, `scan_geometry.json`, `decimation_quality*.txt`, `filled_assets.txt`,
    `frame0_gaps_public.txt`, `early_frames_public.txt`.
- Invalid, kept as a record: `f0_INVALID_noop/`, `sens2_INVALID_unwelded_decimation/` (decimation columns only).
- 26 Oct drafts that never ran, superseded by `run_part4.sh`: `run_f0.sh`, `run_meshswap_seeds.sh`,
  `run_scan_decimation.sh`.
