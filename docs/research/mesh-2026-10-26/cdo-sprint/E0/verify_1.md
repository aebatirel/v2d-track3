# E0 verify_1: adversarial verification, frame and kit lens

- **When and where.** 2026-10-31, about 17:00 to 18:30 UTC. Cloud VM with 4 shared cores, already loaded. CPU only, $0.
  I did not build E0.
- **Code version.** HEAD a009c32 when this was written. The E0 package commit is 3fbc1d1, and the box ran b05f001.
- **Scope.** This review covers:
  - each shipped E0 mesh against library_v3: centroid, median symmetric distance and axis angles at identity, plus
    the rigid-ICP motion that takes the new mesh onto library_v3;
  - units, up axis and handedness;
  - the kit path `budget_mesh` -> encode -> decode, then faces, vertices, watertightness, bodies and quality flags;
  - glTF structure;
  - byte identity of `library_e0` and `library_e0x` against the MANIFEST, the box and library_c0/v3;
  - whether the tracks the meshes were fitted in are library_v3 body poses;
  - the kit's own pose-board body registration with each packed mesh.
- **Labels.** [M] measured here. [D] quoted from an earlier document. [H] hypothesis.
- **Ground truth.** None was read. I opened no scan, mocap, parquet or `*_align` file. The inputs were our meshes, the
  kit code, the box results downloaded to scratchpad, and the hashes and job log of the store run
  `20261025-evperc-4f596df`. verify_0 (integrity lens, 42ab815) is separate. Its B1, the marker-ball prior, is not
  repeated here.

## Verdict

- **Blocking: 1 (B1).** It is scoped. It blocks putting `library_e0` into the pose-board pack. It does not block a
  CD-O-only submission.
- **Non-blocking: 6 (N1-N6).**
- **Confirmed: 8 (C1-C8).** These are:
  - every byte matches;
  - the 36 pairs match the kit roster;
  - the tracks are library_v3 body poses;
  - the identity frame checks reproduce;
  - ICP finds no frame shift;
  - units, up axis and handedness are right;
  - the kit path passes;
  - the glTF structure is the same as library_v3 and C0.

## Blocking

### B1. `library_e0` also changes the five pose boards, and E0 has no pose-board guard

- **What the kit does [M].** All five Track 3 pose metrics register the submitted mesh to the hidden reference before
  scoring. These are AUC, MPPE, RPE, SP-SR and MP-SR (`metric_code/track_3/{AUC,MPPE,RPE,SP-SR,MP-SR}.py` lines
  867-869). Each one calls `_register_object_body(candidate, mesh, anchor, seed)` and then
  `_convert_object_body(achieved, ...)`. The packed mesh therefore sets the body anchor and the rotation that the
  submitted poses are converted with.
- **How our pack carries the mesh [M].** `ops/jobs/submit_pack.sh` copies `LIB/<object>.glb` into the pose
  submission through `pack_object_meshes`.
- **This has already been seen [D].** The work log of 31 Oct ~18:20 UTC records that pack 9a+ moved AUC +0.003, RPE
  -0.053 and MPPE -0.025 when only the meshes changed. It also says: "the public-twin AUC guard held on eval".
- **What E0 says.** None of E0's documents mentions the pose boards (README, MANIFEST, PREREG, BOX, both library
  READMEs). The MANIFEST says "packed mesh only; simulator copies and rollouts unchanged (as C0)". C0, however, had a
  pre-registered public-twin AUC guard (`../C0/AUC_RESULTS.md`), and E0 has none. A pack built from `library_e0` would
  change 17 pose-board pairs without the check that C0 needed for the same kind of swap.
- **GT-free proxy [M] (`v1_kitreg.py`).** I ran the kit's `_register_object_body` exactly as the metric does: packed
  4096/4096 arrays, and the metric's seed `1_000_003*episode + 101*slot` for each eval pair. Two things stand in for
  the hidden data: library_v3 (budgeted) for the reference, and its surface centroid for the anchor. Against library_v3
  itself, the conversion is the identity (shift < 1e-13 mm, rotation < 3e-6 deg).

  | object (pairs) | C0: anchor shift mm / rotation deg | E0: anchor shift mm / rotation deg | reference/candidate scale C0, E0 |
  |---|---|---|---|
  | white_pot (6) | 4.35-5.24 / 0.60-1.25 | 5.17-5.42 / 0.73-2.04 | 1.053, 1.063 |
  | white_pot_lid (1) | 12.12 / 162.1 (axis tilt 0.71) | 11.82 / 2.06 (axis tilt 1.70) | 1.017, 0.992 |
  | plastic_dish_rack (5) | 3.39-4.74 / 1.70-2.63 | 4.58-6.08 / 1.20-2.24 | 1.044, 1.035 |
  | blue_cup (5) | 9.91-12.15 / spin 3-178, **axis tilt 0.92-2.30** | 2.23-5.43 / spin 13-86, **axis tilt 3.26-7.33** | 0.951, 0.945 |

- **What the proxy says.** Pot, lid and rack move by the same order as C0's guarded meshes. Direct ICP puts E0 within
  1 deg and 1.5 mm of C0 for those three (C5).
- **The blue cup does not fit that pattern.** The kit tilts the E0 cup's axis by 3.3-7.3 deg, depending on the seed.
  C0's cup tilted 0.9-2.3 deg. By ICP, the E0 cup's axis is 3.7 deg from the C0 cup's (N2). The C0 cup passed the
  guard [D] but was never shipped, and its RPE margin was the tightest of the four (+0.16 against +0.20 cm).
- **[H] What follows for transfer.** For pot, lid and rack, C0's guard result probably transfers to E0. For the blue
  cup it does not transfer automatically. The hypothesis is falsified if the guard below fails for pot, lid or rack.
- **Fix: choose one.**
  - **(a)** Submit `library_e0` to the CD-O competition only (`pack_reconstruction`). Keep the pack 9a+ meshes in the
    pose-board parquet. No guard is needed.
  - **(b)** Before E0 meshes go into the pose-board parquet, run C0's guard unchanged with the E0 meshes in place of
    C0's. The scripts are `../C0/scripts/run_auc_guard.sh` and `guard_eval.py`, run on the 15 public twins under the
    same frozen rule: mean dAUC >= -0.005, min dAUC >= -0.02, mean dMPPE <= +0.2 cm, mean dRPE <= +0.2 cm. Adopt per
    object. C0's guard ran on this VM at $0 (`../C0/AUC_RESULTS.md` section 2). This is public data used as a
    diagnostic, not eval tuning.
- **In either case,** E0's README and MANIFEST should say that the packed mesh drives the pose-board registration.

## Non-blocking

**N1. PREREG's frame check does not gate the lid's spin, but the metric is sensitive to it. Measured fine here.**
- The kit lists `white_pot_lid` as **half-turn** symmetric (`config/tracks.json`, `half_turn_symmetric_objects`). Its
  in-plane spin therefore matters modulo 180 deg.
- PREREG section 4 marks the lid's major and middle axes "not checked", because the eigenvalues are near-degenerate.
  The E0 lid shows 72.3 deg there, and the check reports it only.
- I measured the spin directly [M]:
  - ICP from identity takes E0 onto library_v3 with a 2.22 deg total rotation, of which 1.98 deg is tilt.
  - In the 48-hypothesis flip test, identity ranks first at 7.132 mm. The half-turn about the normal comes second at
    7.347 mm, and the 90 deg spin scores 7.681 mm.
  - The kit registration lands at 2.06 deg.
- The arch handle therefore points where library_v3's does. For later rebuilds, add an ICP-motion or flip-test gate
  for half-turn objects.

**N2. The blue cup's axis tilt is the largest frame difference in E0. It comes from one episode's track and is shipped
to all five pairs [M].**
- After ICP, the cup's lathe axis is tilted 4.44 deg from library_v3 (C0: 2.58 deg) and 3.69 deg from C0. This is
  inside the PREREG gate of 9.43 deg on the PCA major axis, where the measured value is 3.61 deg.
- The g1 lathe axes of the five eval-episode builds lie 0.93-4.10 deg from library_v3's PCA axis: ep10 1.35, ep14 4.10,
  ep20 0.93, ep32 2.99 and ep33 3.45 deg. The merged build is at 5.67 deg.
- The pick, ep32, therefore carries ep32's track tilt into evals 10, 14, 20 and 33.
- [H] Which axis is closer to the truth cannot be known GT-free. B1 (b) is the test for whether it matters to the pose
  boards. CD-O removes rotation and is not affected.

**N3. The centroid-offset gate measures shape as well as frame.** The rigid ICP motion is the frame number [M]:

| object | centroid offset mm | ICP centroid motion mm |
|---|---|---|
| lid | 7.19 | 0.62 |
| rack | 9.40 | 3.91 |
| pot | 6.48 | 3.81 |

The lid's 7 mm comes from its thinner, flatter body: its extent along the normal is 41 mm against 52 mm. It is not a
shift. This does not change any E0 result, because every gate passes. It would make a future gate looser than intended.

**N4. "library_v3 with four files replaced" holds for the .glb and .json files, but not for the whole folder [M].**
- `library_e0` lacks library_v3's 10 `*.recon.json` files, and `library_e0x` lacks library_v3x's 9.
- No packer reads them. A grep finds them only in `docs/research/work/interaction-meshes-2026-10-22/prototypes/finalize_lib.sh`.
- `library_c0` was the same. Only the README wording is affected.

**N5. The kit's registration of near-round objects depends on the seed. This is reported only [M].**
- E0 cup: spin 13-86 deg and tilt 3.3-7.3 deg across the 5 pair seeds.
- C0 lid (pack 9a, outside E0's scope): it lands at 162 deg against the library_v3 stand-in, which is 18 deg away from
  the half-turn, even though ICP from identity is 1.3 deg. The E0 lid lands at 2.1 deg.
- [H] This is the kit's 25-start ICP choosing among nearly equal minima. The C0 lid passed its public guard [D].
  Against the real reference the outcome can differ, and only B1 (b)-style scoring measures it.

**N6. `library_e0` is a per-object source, not a drop-in library for the next pack.**
- The pack now on Kaggle is 9a+, uploaded about 18:20 UTC, after E0 was packaged [D] (STATUS.md, work log 31 Oct
  ~18:20 UTC). It is pack 8 plus three sets of meshes:
  - C0's pot, lid and rack;
  - the C1 beige-cup obs-lathe (evals 8 and 10);
  - the C1 dust pan (evals 19 and 38).
- `library_e0` and `library_e0x` keep library_v3's beige cup and dust pan [M] (C1). Packing either folder whole would
  silently revert those four 9a+ pairs to library_v3.
- The MANIFEST's "19 unchanged" pairs are unchanged against library_c0 and pack 7, not against 9a+.
- Before packing, take E0's four objects one by one into the current pack's library.

## Confirmed

**C1. Bytes [M].**
- Every file in `library_e0` and `library_e0x` matches the MANIFEST's sha256, md5 and byte count.
- The 4 swapped files are identical across all of these copies:
  - `E0/meshes/<pick>.glb`;
  - the box candidate file and the box `SHA256SUMS`;
  - `library_e0`, `library_e0x` and the MANIFEST `picks`.
- Their sha256 values:
  - pot af321725...;
  - lid e3dd5861...;
  - rack fc67c59b...;
  - cup e6c18b2a....
- Every other .glb and .json is byte-identical to library_c0/c0x and to library_v3/v3x, including `beige_cup.v5.json`
  and `mini_sweeper.flatten.json`. No file is missing from the MANIFEST.

**C2. Pairs [M].**
- The 36 MANIFEST pairs equal the kit roster (`track_3_evaluation_objects.json`) in episode, slot and object, and no
  roster pair is missing.
- Each `mesh` path is `library_e0x` for eval 8 and `library_e0` otherwise, and each sha256 matches the file.
- 17 pairs are swapped.

**C3. The meshes live in the library_v3 body frame [M].**
- The 14 `inputs/eval/ep<N>/poses.npz` files the box used are sha256-identical to the store's
  `runs/20261025-evperc-4f596df/results/evalperc/ep<N>/poses.npz` (14/14, LFS sha256 from the hub API).
- That run's `job.log` line 2 reads: "eval_perc code 4f596df ... LIB /content/v2d-track3/meshes/library_v3".
- `meshes/library_v3` is unchanged between 4f596df and HEAD: its last change is a30ac72 on 22 Oct, an ancestor of
  4f596df.
- Pot, lid, rack and cup are byte-identical in library_v3 and library_v3x.
- Library_v3's own fidelity on the eval points is also consistent with this [D]: pot 3.88, lid 5.19, rack 5.88 and cup
  2.91 mm.

**C4. The identity frame check reproduces [M].**
- My re-measurement uses independent sample seeds: area-weighted centroid, 200 k-sample PCA, and a dense-sample
  median distance.

  | object | centroid offset mm (box) | median sym. distance mm (box) | PCA axis angles deg (box) |
  |---|---|---|---|
  | pot | 6.475 (6.475) | 3.20 (3.20) | 3.05, 3.37, 4.36 (2.99, 3.39, 4.41) |
  | lid | 7.188 (7.188) | 2.65 (2.66) | minor 1.62 (1.59) |
  | rack | 9.396 (9.396) | 3.45 (3.43) | 2.29, 0.53, 2.31 (2.27, 0.76, 2.33) |
  | cup | 4.038 (4.038) | 2.55 (2.48) | major 3.61 (3.63) |

- Every value is inside `inputs/thresholds.json`. The tightest is the lid's minor axis, 1.6 against 2.39 deg.
- The box's C0 rows reproduce `../C0/frame_check.json` exactly for all four objects: same sha, centroid, median, axis
  angles and budget block.

**C5. No frame shift [M].** Trimmed (90 %) point-to-point ICP from identity, 12 k source points to 150 k target
points:

| object | E0->v3: rotation deg (axis tilt) / centroid motion mm | C0->v3 | E0->C0 | v3->E0 (reverse) | median residual before -> after mm |
|---|---|---|---|---|---|
| pot | 0.93 / 3.81 | 0.90 / 2.55 | 0.95 / 1.47 | 1.04 / 5.26 | 3.24 -> 2.96 |
| lid | 2.22 (1.98) / 0.62 | 1.32 (1.24) / 2.33 | 0.94 (0.93) / 0.55 | 1.83 / 5.23 | 2.35 -> 1.92 |
| rack | 0.96 / 3.91 | 2.31 / 2.05 | 0.25 / 0.80 | 2.39 / 4.98 | 3.90 -> 3.52 |
| cup | 4.74 (4.44) / 3.39 | 2.62 (2.58) / 6.71 | 3.69 (3.69) / 2.79 | 1.14 / 3.13 | 2.80 -> 2.38 |

- A real frame error would show as tens of mm or many degrees. Every motion is within about 2 deg and 4 mm, except the
  cup's axis tilt (N2), and is the same order as C0's, which ships in pack 9a.
- The rack's joint fit was built in the ep14 frame. From its build record:
  - per-episode alignment of evals 15, 16, 28 and 30 to ep14 is at most 0.46 deg and 2.1 mm;
  - the mean-frame correction is 0.05 deg and 0.27 mm.
- The first and second runs gave identical numbers. The process is deterministic.

**C6. Units, up axis, handedness [M].**
- **Units.** Metres. Extents match library_v3 within about 20 % on every axis:
  - pot 134 x 184 x 352 mm against 131 x 190 x 362;
  - lid 41 x 187 x 187 against 52 x 189 x 185;
  - rack 124 x 167 x 487 against 109 x 159 x 496;
  - cup 91 x 91 x 177 against 95 x 96 x 167.
- **Volumes.** All positive and winding-consistent.
- **Flip test.** For each of the 48 signed axis permutations: centroid-matched, then 25 ICP iterations, then trimmed
  symmetric distance.

  | object | identity mm (rank of 48) | best up-flipped mm (ratio) | best improper mm | reading |
  |---|---|---|---|---|
  | pot | 7.771 (2) | 19.48 (2.51x) | 7.768 (y-mirror) | up axis right; the pot is mirror-symmetric, so a mirror cannot be seen and does not matter |
  | lid | 7.132 (1) | 7.71 (1.08x) | 7.433 | up axis, spin (N1) and handedness right |
  | rack | 8.992 (1) | 16.95 (1.88x) | 9.796 | up axis and handedness right (the rack is asymmetric) |
  | cup | 6.052 (6; top 6 within 0.11 mm, all keep the axis) | 11.25 (1.86x) | 5.939 | up axis right; spin and mirror are lathe symmetries |

- The C0 meshes rank the same way: pot 1, lid 1, rack 1, cup 2.

**C7. The kit path [M].** `budget_mesh(path, 4096, 4096)` -> `_encode_archive` -> `_decode_object_mesh` is
`pack_object_meshes`' own sequence. It was then followed by `mesh_quality_flags`.

| object | raw faces | non-padding faces | vertices | watertight | bodies | volume cm3 | quality flags | max raw <-> budget deviation mm | payload chars |
|---|---|---|---|---|---|---|---|---|---|
| pot | 15574 | 4096 | 2054 | yes | 3 | 274.9 | none | 1.74 | 84032 |
| lid | 9488 | 4096 | 2048 | yes | 1 | 79.1 | none | 1.23 | 80892 |
| rack | 2638 | 2638 (no decimation) | 1325 | yes | 3 | 724.6 | none | 2.45 (sampling floor only) | 37804 |
| cup | 23348 | 4096 | 2052 | yes | 2 | 180.0 | none | 2.68 | 86044 |

- Notes on these numbers:
  - Decoded shapes are (4096, 3) and (4096, 3).
  - No value is non-finite, and no non-padding face has zero area after welding.
  - Medians are 0.3-0.6 mm, mostly the sampling floor of the 150 k-sample comparison.
  - Payloads are far below the decoder's 800 k-character limit.
- `library_e0x` gives identical results, because its bytes are identical.
- The box's budget rows are identical too: pot 4096/2054, lid 4096/2048, rack 2638/1325, cup 4096/2052, all
  watertight.

**C8. glTF structure [M].** Each file has one node with no matrix, translation, rotation or scale, one mesh, and one
primitive with `POSITION` only. The generator is trimesh. This matches C0. library_v3 adds `COLOR_0`, which the kit
does not read. trimesh's `force='mesh'` load (kit) therefore sees the file frame directly.

## Run record

- **Scripts.** Written for this check. They are in scratchpad, not committed, because the task commits only this file.
  - `scratchpad/verify_e0_frame/v1_frame_kit.py` (sha1 1aad91bd8b46): bytes, pairs, identity frame, ICP, flip test, kit
    path and glTF.
  - `scratchpad/verify_e0_frame/v1_kitreg.py` (sha1 54856c6ecf1a): the kit pose registration.
  - Store queries: `sha_evperc.py` and `get_evperc.py` (huggingface_hub, read only).
- **Commands.** Venv python, `-I`, nice 10:
  - `v1_frame_kit.py REPO KIT BOX_RESULTS OUT [objects]`, as two parallel runs, `blue_cup,white_pot_lid` and
    `white_pot,plastic_dish_rack`. They produced `v1_fk_A.json` and `v1_fk_B.json`, merged into
    `v1_frame_kit_merged.json`.
  - `v1_kitreg.py REPO KIT v1_kitreg.json`.
  - KIT = `scratchpad/kit/v2d_submission_kit`; BOX_RESULTS = `scratchpad/cdo_e0/box/dl/runs/mesh-20261031-e0-b05f001/results/e0`.
- **One failure.** The first all-object run was stopped at the 30-minute background limit after the pot, lid and rack
  rows and the cup's E0 row had printed. Its log is kept at `v1_frame_kit.run1_killed.log`. Its numbers equal the
  re-run's.
- **Timing.** About 25 min of wall time per pair of objects at load ~5-6. Cost $0.
