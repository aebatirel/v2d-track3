# C0 hand-off verification (independent, adversarial)

- **When / where:** 2026-10-31, about 15:45-16:15 UTC. Cloud VM (4 cores, shared). CPU only, $0.
- **What was checked:**
  - `meshes/library_c0` and `meshes/library_c0x` as committed in `5cce3d2`. Working tree equals HEAD for `meshes/`.
  - The C0 docs as committed in `081b37e`. `MANIFEST.json` is unchanged since then (sha256 `22209582f5698543…`).
  - Kit: scratchpad `kit/v2d_submission_kit`. `mesh_budget.py` `8f29481d52a82c46`, `track3_pose.py` `b4b99f698eb4893a`,
    `mesh_quality.py` `691878c6ba6ab68d`, `pack_submission.py` `49b13052e3bbdd05`, roster `be92ef6db25aa60c`. These are
    identical to the `loc/kit` copy that `mesh_metric.py` used for the [D] scores.
  - Python env: trimesh 5.2.0, fast_simplification 0.2.0, numpy 2.5.4.
- **Labels:** [M] = measured here, ground-truth-free (mesh files only). [D] = existing public-scan diagnostic records,
  quoted and not recomputed. Nothing in this check read a scan, mocap or a parquet pose.
- **Scripts and raw outputs:** scratchpad `c0verify/`. They are not committed (the brief allows committing this file only).
  - `v12.py`: identity and roster;
  - `dry.py`: pack mesh-path dry run;
  - `frame_v4.py`, `cup_axis.py`, `lid_rim.py`: frame checks;
  - outputs `v12.json`, `dry/<tag>/dry.json`, `frame_v4.json`, `cup_axis.json`.

## Verdict

The hand-off is pack 9a: the pot, lid and rack of C0. The blue cup stays library_v3 by default (work log, ~16:20 UTC).
**No blocking item for pack 9a.**

Per-object frame answer, as asked by focused-pascal:

| object | frame yes/no | why (no registration; rigid ICP of new onto library_v3) |
|---|---|---|
| white_pot | **YES** | ICP moves it 2.49 mm / 0.80°. The 5.4 mm centroid offset is shape, not frame. |
| white_pot_lid | **YES (borderline)** | ICP 3.03 mm / 1.24° (axis tilt 1.20°). The in-plane rim-centre offset is 5.8 mm, but the library lid's rim is not circular. |
| plastic_dish_rack | **YES (with caveat)** | ICP 2.09 mm, but a real 2.3° rotation: about 10 mm at the ends of the 0.49 m rack. |
| blue_cup | **NO (not confirmed)** | ICP 6.67 mm / 2.67°, almost all along the cup axis (6.45 mm). The main body's base and rim sit 3.2 / 5.9 mm lower than library_v3. |

In every case, the [D] static registration offset to the public scan improves on library_v3 (ADD pot 6.67→3.05,
lid 8.12→4.46, rack 5.99→5.37, cup 9.97→4.09 mm). So where a geometric offset exists, the scan diagnostics put it
toward the scan frame, not away from it.

## BLOCKING

- **None for pack 9a (pot, lid, rack).**
- **B1, conditional: only if the blue cup is packed.**
  - Both library READMEs say the swapped meshes "are in the same object frame as library_v3". For the blue cup, that
    is not confirmed at the few-mm level:
    - rigid ICP new→library_v3: 6.67 mm / 2.67° (translation [-1.34, -1.02, +6.45] mm, z = cup axis);
    - reverse ICP: 5.66 mm / 2.71°;
    - main-body axial range [-82.5, 83.1] mm against library_v3 [-79.3, 89.0] mm: base 3.2 mm lower, rim 5.9 mm
      lower, height 2.6 mm shorter;
    - outer radius 1.5-3.7 mm smaller along the height; lateral axis offset 1.1 mm; axis tilt 2.4°;
    - the kit's own registration (`_register_object_body`, new as candidate, library_v3 as reference, 3 seeds) moves
      the anchor 10.6-10.9 mm (about -9.5 mm along the axis). The scale normalisation adds to this: the four extra appendage
      bodies inflate the new mesh's RMS radius, 64.0 against 60.8 mm.
  - An axial offset of 3-6 mm cannot be separated from shape GT-free. [D] suggests it is a correction toward the scan
    frame (ADD 9.97→4.09 mm).
  - If the owner includes the blue cup:
    - state the axial offset in the READMEs / MANIFEST instead of "same frame";
    - take the AUC guard's blue-cup verdict (twins 11, 12, 13, 21, 22; 4 of 5 single runs done at 16:04 UTC) into
      the decision.

## Non-blocking (record or fix when convenient)

- **N1. AUC guard not finished at hand-off.** 33 of 51 runs were done at 16:04 UTC.
  - `MANIFEST.json` still reads "not adopted". PREREG §5 says "C0-final = the adopted objects. There is no other
    selection."
  - The score session ruled the guard "information for tonight, not a gate" (work log ~15:45-16:00). Record that as a
    deviation from PREREG §5.
  - If the guard later rejects the pot, lid or rack, say in the pack notes that pack 9a carries a non-adopted object.
- **N2. Rack rotation is real, not shape noise.**
  - The PCA major axis is well conditioned (SD 145 vs 44 mm) and turns 2.49°. ICP turns it 2.30° (rotvec
    [0.0, -1.8, -1.4]°). The kit registration new→library_v3 gives 1.3-2.5°.
  - [D] rot_max to the scan worsens 1.75° → 3.29° while ADD improves 5.99 → 5.37 mm.
  - The guard's rack twins (12, 13, 26, 27, 31) measure what this costs.
- **N3. Lid in-plane registration is weakly constrained.**
  - The kit's new→library_v3 registration gives 4.9° / 10.6° / 19.1° about the lid normal over 3 seeds (anchor
    5.0-11.3 mm). The new lid is a lathe; the library_v3 rim is not circular (22 of 72 angular bins are more than
    2 mm off a circle).
  - Against the scan this is not an issue per [D]: rot_max 2.18° (library_v3 2.27°), 0 flips on 6 seeds.
- **N4. Provenance wording.**
  - MANIFEST and READMEs say "same tier as library_v3 (tier P1)". They do not say that library_v3 itself was built
    along scan-templated tracks: that is one of the open organiser questions in STATUS (email draft not sent), and
    library_v3 is on the gmg denylist.
  - The owner's call is recorded in STATUS. Spell it out in the pack notes so a reader of the MANIFEST alone is not
    misled.
- **N5. The object set was chosen with public-scan [D] gates.**
  - The per-object variant picks are GT-free (obs_fidelity).
  - Pot, lid and rack passed a pass rule pre-registered on 27 Oct, before scoring.
  - The blue cup has no pre-registered selector; this is flagged.
  - Do not describe C0 as "chosen GT-free" without this qualifier.
- **N6. Pack invocation checklist** (`ops/jobs/pack_eval.sh` / `submit_pack.sh`):
  - change only `LIB` and `EP_LIB`, with absolute paths;
  - `ASSET_LIB` (simulator assets, default library_v3) and `ASSET_PIECES` must stay as in pack 8. Setting `ASSET_LIB`
    to library_c0 would change the simulated bodies.
  - **Eval 8 has a white_pot (slot 1).** If pack 9a is made by copying files into pack 8's per-episode folders, the
    12 files to replace are:
    - white_pot in episodes 1, 3, 5, 6, **8**, 28;
    - white_pot_lid in episode 1;
    - plastic_dish_rack in episodes 14, 15, 16, 28, 30.
  - If the blue cup is added, also blue_cup in episodes 10, 14, 20, 32, 33.
  - The eval-8 beige cup must stay the v3x file (md5 `ebea224c…`). The md5s sent to focused-pascal match the
    committed files: pot `0264da83…`, lid `35727a10…`, rack `bbca8ec0…`, blue cup `9e3a74fd…`.
- **N7. Decimation version.** `pack_eval.sh` runs `pip install -q fast_simplification` unpinned.
  - The [D] scores used budget_mesh with fast_simplification 0.2.0. Another version on the GPU box could decimate the
    pot, lid and cup differently.
  - The rack (2356 faces) is under budget and is not decimated.
  - Same exposure as every library mesh. Pinning 0.2.0 removes it.
- **N8. Cosmetic.**
  - Both library READMEs point to `cdo-sprint/C0/README.md`, which does not exist (the file is `NOTES.md`).
  - The rack's "sha256 (16)" in the READMEs has 17 characters (`c22f504ccb8855418`; correct `c22f504ccb885541`).
- **N9. Known construction defects.**
  - Pot: 4 of 5 marker balls float, no handle hole. Lid: a floating ball, 2 bodies. Blue cup: 11 bodies and not
    watertight after budget.
  - None is checked by the kit. The simulator does not use these meshes.

## Confirmed, with numbers

### 1. Byte identity [M]
- **library_c0 vs library_v3:**
  - 11 .glb in each, same names;
  - the 7 unswapped files are byte-identical (sha256);
  - the 4 swapped files equal the MANIFEST sha256 and the repo source mesh, and differ from library_v3.
- **library_c0x vs library_v3x:** the same holds. c0 and c0x differ only in `beige_cup.glb` (`f7309312…` vs
  `af327b80…`), exactly as v3 vs v3x.
- **Frozen hashes:** all 10 public-object files equal `inputs/mesh_dirs_sha256.json["c0"]`, frozen at the PREREG
  commit.
- **sha1[:16]** with `mesh_metric.py sha()` (whole-file sha1). For each object, the c0 file, the c0x file, the repo
  source, `MANIFEST public_D.sha1_16`, and the score record's `sha` (exactly 1 record per label) are all equal. The
  scratchpad build file named in the record still exists with full sha256 equal to the repo file. CD-O, ADD and flips
  in the MANIFEST equal the record. library_v3 baseline sha1 and CD-O also match `baseline_library.jsonl`.

| object | sha256[:16] | sha1[:16] = record | record | CD-O cm (lib→new) [D] | ADD mm [D] |
|---|---|---|---|---|---|
| white_pot | 355ad72e397e1080 | 4bf2135570c1da26 | potlid/fit/ep41 | 0.4371 → 0.3417 | 6.67 → 3.05 |
| white_pot_lid | 0bac47f4b86e9ae3 | 67632273f5723dc9 | clean/lid/t2.5_fit | 0.4211 → 0.2199 | 8.12 → 4.46 |
| plastic_dish_rack | c22f504ccb885541 | b855279b68ecb432 | clean/rack/t2.5_lean1/all_joint | 0.5551 → 0.4560 | 5.99 → 5.37 |
| blue_cup | 81a201cb23325161 | 1bd4c8f5f475596f | lathe_obs_g/a1/ep21/blue_cup | 0.5233 → 0.2906 | 9.97 → 4.09 |

### 2. Roster coverage [M]
- The kit roster has 20 episodes and 36 (episode, object) pairs. Every object has `<object>.glb` in both library_c0
  and library_c0x.
- The MANIFEST lists exactly 36 pairs, equal to the roster including slot order. 17 are swapped
  (pot 6, lid 1, rack 5, blue cup 5); 19 are unchanged.
- **What the pack would copy:** with `LIB=library_c0 EP_LIB=8:library_c0x`, each copied file's sha256 equals the
  MANIFEST `c0_sha256` for all 36 pairs.
- **Objects that change against pack 7** (`library_v3`, `8:library_v3x`): exactly {white_pot, white_pot_lid,
  plastic_dish_rack, blue_cup}.

### 3. Kit compatibility [M]
- **Method.** `dry.py` does the following:
  - copies meshes exactly like `submit_pack.sh`;
  - fills a dummy pose frame from the kit's `track_3_sample_submission.parquet` (all 9,120 row ids) with a valid
    commit URL;
  - calls `v2dlb.track3_pose.pack_object_meshes`, the mesh path `pack_submission.py` runs: `find_mesh`, then
    `budget_mesh(4096, 4096)`, then encode, decode-validate, then `report_mesh_quality`;
  - runs the uploader's `validate_submission(track_3)`, which re-decodes and reprints the quality checks;
  - runs `cd_o_submission` and `validate_submission(track_3_mesh)`.
- **Results**, the same for all three variants (C0 full, pack 9a = 3 swaps, pack 7 baseline):
  - 36 payloads;
  - **0 `MESH WARNING`**;
  - the uploader's validation passes;
  - CD-O file: 294,912 rows, 0 non-finite.
- **Payload changes** against pack 7: exactly the 17 swapped pairs for C0 and the 12 pot/lid/rack pairs for 9a. The 9a
  payloads are byte-identical to C0's for the same files, so decimation is deterministic in this environment.
- **What the kit validates:**
  - the payload is 4096×3 vertices plus 4096×3 faces;
  - it is under 400 kB decoded;
  - all values are finite;
  - face indices are valid;
  - the surface area is positive;
  - advisory only: fewer than 32 vertices or triangles, planar, box-like, sphere-like, or an identical mesh for
    different names.
- **Watertightness and body count are never checked.** Nothing in `metric_code/track_3`, `track3_pose.py`,
  `mesh_quality.py` or `mesh_budget.py` tests watertightness; inside/winding tests appear only in track-1 code (`metric_code/track_1`, `v2dlb/mhr_*`).
- CD-O is scale-normalised and rigidly aligned (`CD-O.py _object_chamfer_cm`), so it does not depend on the mesh frame.
  The frame matters only for the pose boards, through `_register_object_body`.

Budgeted (decoded payload). Library_v3 in brackets:

| object | active faces | vertices | watertight | bodies |
|---|---|---|---|---|
| white_pot | 4096 (4096) | 2058 (2042) | yes (no) | 5 (6) |
| white_pot_lid | 4096 (4096) | 2050 (2044) | yes (yes) | 2 (1) |
| plastic_dish_rack | 2356 + 1740 padding (4096) | 1184 (2033) | yes (no) | 3 (10) |
| blue_cup | 4096 (4096) | 2059 (2046) | **no** (no) | **11** (6) |

### 4. Frame consistency [M] (no registration unless stated; meshes loaded with the kit's loader)
- **Format:**
  - all 8 files (new and library_v3) are glTF 2 written by trimesh;
  - 1 node, 1 mesh, no node transforms, no extensions;
  - units are metres: extents agree with library_v3 within 1-15 mm;
  - signed volumes are positive for all (outward winding).
- **Up axis and sense:** the dominant axis is the same in new and library_v3, with the same sign of the third moment.
  So nothing is upside down or axis-swapped. The dominant axis is z for the pot, rack and cup, and x (the normal) for
  the lid.
- **Handedness:** ICP of x/y/z-mirrored copies is never better than the unmirrored fit beyond the object's own mirror
  planes:
  - pot: x mirror 9.40 vs 3.42 mm;
  - rack: x 8.63, z 8.94 vs 4.11 mm;
  - cup: z 4.60 vs 2.20 mm;
  - the lid is flat and round, so mirroring is not identifiable.

| object | centroid offset mm (claim) | PCA axis angles ° | median sym. surface dist mm (claim) | p90 mm | ICP new→lib: mm / ° | ICP lib→new: mm / ° | kit registration new→lib (3 seeds): anchor mm / ° |
|---|---|---|---|---|---|---|---|
| white_pot | 5.44 (5.4) | 2.9 / 4.4 / 4.4 | 2.70 (2.73) | 8.5 | 2.49 / 0.80 | 4.63 / 0.78 | 4.2-4.7 / 1.1-1.5 |
| white_pot_lid | 7.31 (7.3) | 69 / 69 degenerate / 0.86 normal | 2.32 (2.35) | 9.9 | 3.03 / 1.24 | 7.54 / 0.87 | 5.0-11.3 / 4.9-19.1 |
| plastic_dish_rack | 11.46 (11.5) | 2.5 / 1.7 / 3.0 | 3.41 (3.43) | 9.7 | 2.09 / 2.30 | 4.42 / 2.21 | 4.0-4.6 / 1.3-2.5 |
| blue_cup | 3.53 (3.5) | 3.4 / 18 / 18 degenerate | 2.54 (2.53) | 6.8 | **6.67 / 2.67** | 5.66 / 2.71 | **10.6-10.9** / 3.5-16 |

How the table was measured:
- Surface distance: exact closest point, 20,000 samples each way, seed 21; the brief's claims used seed 0.
- ICP: trimmed (90 %) point-to-point, from identity, 30,000 samples.
- The frame_check.json claims are reproduced within 0.03 mm.

Reading:
- **Pot and rack:** the large centroid offsets (5.4 and 11.5 mm) are mass-distribution differences.
  - Rigid ICP removes only 2.1-2.5 mm of translation.
  - Library_v3 has extra surface where the primitive has none, so the reverse ICP is larger (4.4-4.6 mm).
- **Lid:** library_v3's underside reaches 12 mm deeper along the normal: [-17.0, 35.5] mm against [-5.1, 37.4] mm.
  That explains its 4.9 mm normal centroid shift and the 7.5 mm reverse ICP.
- **Blue cup:** see B1.

### 5. Integrity [M, from files and git]
- **C0 assembly read no scans and no mocap.**
  - `build_c0.py` reads repo meshes, existing score records (jsonl), the kit roster and our sweep `poses.npz`.
    `frame_check.py` reads mesh files only. A grep finds no scan, parquet or mocap paths. Their docstrings say the same.
  - The timeline holds:
    - PREREG commit `081b37e` at 15:32:36 UTC;
    - stage 0 of the guard (GT download) at 15:34-15:35 UTC;
    - the libraries in `5cce3d2` at 15:42:59 UTC are byte copies of meshes whose hashes were frozen in `081b37e`. So no
      file changed after ground truth was staged.
- **The source meshes** were built on 26-27 Oct. The 27 Oct auditors read all fitting code: "No code reads a scan".
  - The scan-informed upright rack cup holder was replaced by the pre-scan lean design, chosen by GT-free fidelity.
  - The pot wall is measured from our points (4.77 mm).
- **The flags are stated in MANIFEST.json and in both library READMEs:**
  - lid T_LID and rack T_WALL 2.5 mm equal values leaked from the scans; the clean-up grid passed at 1.5/2.5/4.0 mm;
  - the blue-cup obs_fidelity selector was written after the five lathes were scored (lathe file 16:27, score
    commit 16:49, selector ~16:40 UTC on 26 Oct);
  - the blue cup is not watertight after budget.
- The provenance wording is incomplete; see N4.

## Commands (scratchpad `S` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`)

```
S/venv/bin/python -I S/c0verify/v12.py /home/user/v2d-track3 S/kit/v2d_submission_kit > S/c0verify/v12.json
S/venv/bin/python -I S/c0verify/dry.py S/kit/v2d_submission_kit /home/user/v2d-track3 S/c0verify/dry c0 library_c0 8:library_c0x
S/venv/bin/python -I S/c0verify/dry.py S/kit/v2d_submission_kit /home/user/v2d-track3 S/c0verify/dry pack7 library_v3 8:library_v3x
S/venv/bin/python -I S/c0verify/dry.py S/kit/v2d_submission_kit S/c0verify/fake9a S/c0verify/dry pack9a lib9a 8:lib9ax
S/venv/bin/python -I S/c0verify/frame_v4.py S/kit/v2d_submission_kit /home/user/v2d-track3 S/c0verify/frame_v4.json
S/venv/bin/python -I S/c0verify/cup_axis.py /home/user/v2d-track3 S/c0verify/cup_axis.json
S/venv/bin/python -I S/c0verify/lid_rim.py /home/user/v2d-track3
```

How the pack 9a dry run was set up: `fake9a/meshes/lib9a` = library_v3 plus the pot, lid and rack from library_c0.
`lib9ax` = library_v3x plus the same three files. Runtime: dry runs about 18 s each; frame_v4 7.4 min.
