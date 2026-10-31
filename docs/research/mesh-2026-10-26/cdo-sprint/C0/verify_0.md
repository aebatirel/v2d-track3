# C0 verification 0: integrity, provenance and format (stage 3, adversarial)

- **When and where:** 2026-10-31, 16:13-16:30 UTC, on the cloud VM (4 shared cores, load about 11). CPU only, $0.
- **What was checked:** the C0 deliverables at HEAD `d495956`:
  - NOTES, PREREG, MANIFEST, roster, frame_check, AUC_RESULTS, guard_result and the 51 `auc/` JSONs;
  - `meshes/library_c0` and `meshes/library_c0x` (commit `5cce3d2`);
  - the source score records and the scratchpad build files;
  - git and reflog times, and file mtimes.
- **Labels:**
  - [M] measured here, without ground truth (mesh files, our own score JSONs, git metadata);
  - [D] existing public-scan diagnostics, quoted and not recomputed;
  - [E] estimate;
  - [H] hypothesis.
- **Ground truth:** none was read. No scan, parquet or mocap was opened. Symlink targets were read with `readlink`
  only. Nothing was tuned, and no CD-O or AUC scoring was run.
- **Scripts and raw outputs:** scratchpad `verify0_c0/` (not committed). Run with `venv/bin/python -I`:
  - `ident.py`: hashes and record trace;
  - `budget.py`: kit budget, decode, watertightness and glTF format;
  - `frame_check.py`: the C0 script, re-run unchanged;
  - `icp.py`: independent rigid ICP;
  - `regate.py`: independent recomputation of the rule;
  - outputs `*.json`, progress in `PROGRESS.md`.
- **Overlap:** `verify_handoff.md` (another verifier, 694dc73) covered much of the same ground. I repeated its checks
  with my own code and did not rely on it.

## Verdict

- The four C0 meshes are byte-identical to the meshes that produced the cited [D] numbers. Every copy matches:
  scratchpad, AUC-guard directories, `library_c0` and `c0x`, and the md5s sent to focused-pascal.
- The frame check and the kit budget/watertight check reproduce exactly.
- The MANIFEST covers the 36 roster pairs and changes only the 4 objects.
- PREREG `081b37e` was pushed before any ground truth was staged or any AUC output was written.
- The frozen rule is applied correctly; I recompute every number in `guard_result.json`.
- **Two blocking items for the hand-off text:**
  - B1, a scan-derived parameter in the pot, lid and rack that no C0 document flags;
  - B2, conflicting statements of what C0-final is.
- Neither invalidates the AUC-guard runs.

## BLOCKING

### B1. The pot, lid and rack carry a scan-derived marker-ball prior that no C0 document flags

**What the code does.** `prim_potlid.py` fits marker balls (`markers_from`, also used by `prim_rack.py`).
- When the free sphere fit fails, it falls back to a fixed radius `MK_R0 = 0.007` m.
- A free fit is accepted only inside the window `MK_RMIN, MK_RMAX = 5-9.5 mm`.

**Where the values come from.** The 29 Oct audit (work log, around line 4658, blocker 1) found that `MK_R0` and the
5-9.5 mm window trace to the scans: the spoon template's note 17 is a marker catalogue fitted on the public scans.
- The code comment had said "our own stereo"; commit `14eaf37` corrected it to "SCAN-DERIVED".
- The audit: it "shaped the balls of the pot (4 of 5), lid (2 of 3) and rack (1 of 2) hand kits that passed today's
  scan rounds. Those passes are now provisional until rebuilt with a generic ball rule."
- Stage 1b closed on 30 Oct without that rebuild (STATUS, 30 Oct ~12:15).
- The C0 pot, lid and rack are exactly those 27 Oct meshes. The pot `ep41 fit` "rebuilds byte-identical" with the
  clean-up code `2971a10`, which still uses `MK_R0`.

**Measured in the C0 files [M].** Sphere fit to each body. The residual is 0.00 mm on every ball, so they are exact
spheres.

| Object | Body radii (mm) | Build record (`*.json` markers) |
|---|---|---|
| white_pot | 7.00, 7.00, 7.00, 6.94 | balls in `mode: prior` (r 7.0), plus one `free` at 6.94 (inside the scan-derived window) |
| white_pot_lid | 7.00 (the floating ball) | 1 `free` at 7.35, plus `prior` 7.0 balls |
| plastic_dish_rack | 7.00, 5.22 | - |

**What the C0 documents say.** No C0 document mentions this:
- `MANIFEST.json` has `white_pot.flags = []`;
- PREREG §1, AUC_RESULTS §5 and both `library_c0*` READMEs list only T_LID, T_WALL and the blue-cup flags.

**Why it blocks.** The hand-off tells the pack builder and the owner that the pot is clean and that only the blue cup
has a ground-truth-informed choice. That is the stated reason pack 9a takes the pot, lid and rack and holds back the
blue cup (work log 16:20). For the three shipped meshes, that statement is wrong.

**Fix, before the pack 9a upload.** Add the flag to the MANIFEST, AUC_RESULTS, both library READMEs and the pack notes,
then put it to the owner and the score session. Whether to ship as is or rebuild without ground truth is their call.

**Effect on scores** [H]. The balls are a small share of the surface, so the CD-O effect is probably small. Their
positions come from our points; only the radius and the acceptance window are priors.
- Falsifier: rebuild pot, lid and rack with no balls, or with a generic free-radius ball (3-15 mm, the stage-1b part).
  This needs no ground truth.
  - The rack's `joint_nomk` variant already exists in the same run.
  - Compare obs_fidelity. A CD-O number would need a newly pre-registered single scan scoring.

### B2. The hand-off documents disagree about C0-final

| Document | What it says |
|---|---|
| `guard_result.json` `c0_final` | all 4 objects |
| AUC_RESULTS | "C0-final = {white_pot, white_pot_lid, plastic_dish_rack, blue_cup}" |
| `MANIFEST.json` `status` | "assembled, AUC guard pre-registered (PREREG.md), not adopted" (stale since stage 2) |
| work log, 16:20 UTC | pack 9a = pot, lid, rack; the blue cup stays library_v3 unless the owner includes it |

**Why the blue cup's "ADOPTED" is not enough.** It is an AUC-guard verdict only. The mesh was chosen by
`obs_fidelity.py`, and that selector was written after its five lathes had been scored against the scan. Work log
26 Oct: "It picks the CD-O winner (0.291)". The ep21 g1 file is the lowest CD-O of all 12 blue-cup records in
`lathe_obs.jsonl` [D]. So it does not meet the brief's "picked GT-free under pre-registered rules".

**Fix, in stage 4:**
- state C0-final for packing as {pot, lid, rack}, with the blue cup only on the owner's explicit inclusion;
- record the hold-back as a deviation from PREREG §5 ("C0-final = the adopted objects. There is no other selection"),
  made for integrity reasons;
- update the MANIFEST `status`;
- after B1, state the same qualifier for the three meshes that ship.

## Non-blocking

1. **The PREREG time is wrong.** PREREG.md says "Written 2026-10-31 ~15:40 UTC". It was committed at 15:32:36 and
   pushed at 15:32:38 (origin reflog). Taken literally, 15:40 falls after stage 0 started (15:34:15). Correct the
   time.
2. **The pack 9a configuration already has its twin numbers [D].** The c0 run is not what ships. Pot, lid and rack
   with the blue cup at library_v3 equals an existing run on every twin:
   - which run: c0 on 0, 2, 26, 27, 31, 41-45; single rack on 12 and 13; base on 11, 21, 22;
   - mean dAUC **+0.0079**, min -0.0092 (ep12);
   - dMPPE -0.059 cm, dRPE -0.121 cm, dMP-SR 0.

   Report this in stage 4. The c0 joint minimum of -0.024 on ep13 comes from the blue cup.
3. **In-sample twins.** Each mesh was fitted to points of some of its own twins: pot ep41, lid ep2, rack 12/13/27,
   cup ep21.
   - The lid verdict rests only on ep2, its build episode; ep0 gives 0 because the lid track failed.
   - Out-of-sample twins (diagnostic, not the rule):

     | Object | Twins | mean dAUC | min dAUC | dRPE cm |
     |---|---|---|---|---|
     | pot | without ep41 | +0.0036 | -0.0159 | -0.121 |
     | rack | 26 and 31 | +0.0323 | +0.0034 | -0.071 |
     | cup | without ep21 | +0.0175 | -0.0049 | +0.016 |
4. **The blue-cup dRPE pass depends on one twin** (diagnostic). The margin is 0.0375 cm. Leaving out ep12 gives
   +0.273, over the limit.
5. **Blue-cup frame [M].** My own ICP (new to library_v3, seeds 7/8, trimmed 90 %) gives 6.67 mm / 2.58°. Of that,
   +6.45 mm is along the cup axis, matching `verify_handoff` B1.
   - The `library_c0*` READMEs say the swaps are "in the same object frame as library_v3"; for the blue cup that is
     not confirmed.
   - The other three:

     | Object | ICP shift | ICP rotation |
     |---|---|---|
     | pot | 1.9 mm | 0.94° |
     | lid | 2.5 mm | 1.36° |
     | rack | 2.1 mm | 2.26° (a real rotation, as `verify_handoff` N2 found) |
6. **Blue cup after the kit budget [M].**
   - It is not watertight: 11 bodies, 5 non-manifold edges.
   - The main body keeps only 2594 of the 4096 faces. The four appendage bodies take 288-450 faces each.
   - The library_v3 blue cup is also not watertight (6 bodies). The kit never tests watertightness (grep of `v2dlb`
     and `metric_code/track_3`).
7. **Provenance tier wording.**
   - The MANIFEST states, on every swapped pair, "tier P1: fitted to our stereo points along library_v3-anchored tracks
     (same tier as library_v3)".
   - It does not say that library_v3 itself was fused along scan-templated tracks, which is the open organiser
     question in STATUS. This is `verify_handoff` N4, still open.
   - The T_LID 2.5 mm flag is stated in the MANIFEST, PREREG, AUC_RESULTS and the READMEs.
   - The 2.5 mm default was pre-registered on 27 Oct as the shipped value if all three thicknesses passed (work log
     ~4535), so it was not picked after the fact.
8. **The object set itself was chosen with [D] scores.**
   - Pot, lid and rack passed a scan pass-rule that was pre-registered; the blue cup had no such rule.
   - Do not call C0 "chosen GT-free" without that qualifier, now plus B1.
9. **Cosmetic, still open from `verify_handoff` N8.**
   - Both library READMEs point to `cdo-sprint/C0/README.md`, which does not exist.
   - The rack's "sha256 (16)" in the READMEs has 17 characters.
   - The pot `fit` and `nostem` ep41 files are byte-identical: two labels, one sha1, so there is no impact.
10. **Outside C0, for the orchestrator.** `cdo-sprint/E0/jobs/frozen/.../scripts/prim_potlid.py` is byte-identical to
    `2971a10`. It carries `MK_R0 = 0.007` with the old, wrong comment "our own stereo".
    - E0's eval-built pot, lid and rack will inherit B1 unless E0 uses a variant with no balls or with generic balls.
    - The E0 PREREG does not mention it.
    - Tell the E0 workflow before its box runs.

## Confirmed, with numbers

### 1. Byte identity and score-record trace [M]

Method:
- sha256 and sha1[:16] are taken over the whole file (`mesh_metric.py sha()`).
- Each object has exactly 1 record with the cited label, and that record's `sha` equals the file.
- The record's `path` file still exists, and its sha256 equals the repo file.
- `cdo_eval`, `add_eval` and `flips_all` equal the MANIFEST values.
- Every record is `mesh_mode: budget` with `ref_mode: budget`, so the [D] numbers were scored on the kit-budgeted mesh.

| Object | sha256[:16] | Bytes | sha1[:16] = record `sha` | Record | CD-O / ADD / flips [D] |
|---|---|---|---|---|---|
| white_pot | 355ad72e397e1080 | 297072 | 4bf2135570c1da26 | `potlid/fit/ep41` | 0.3417 / 3.047 / 0 of 8 |
| white_pot_lid | 0bac47f4b86e9ae3 | 172708 | 67632273f5723dc9 | `clean/lid/t2.5_fit` | 0.2199 / 4.46 / 0 of 6 |
| plastic_dish_rack | c22f504ccb885541 | 43256 | b855279b68ecb432 | `clean/rack/t2.5_lean1/all_joint` | 0.4560 / 5.368 / 0 of 7 |
| blue_cup | 81a201cb23325161 | 557540 | 1bd4c8f5f475596f | `lathe_obs_g/a1/ep21/blue_cup` | 0.2906 / 4.088 / 0 of 7 |

Copies equal to the MANIFEST sha256:
- scratchpad `cdo_c0/c0/<o>.glb` and `cdo_c0/single/<o>/<o>.glb`;
- `meshes/library_c0/<o>.glb` and `meshes/library_c0x/<o>.glb`;
- for the blue cup, also scratchpad `lathe/ep21_blue_cup_g1.glb` and the repo `C0/meshes/` copy.

md5 of the `library_c0` swaps equals the md5s in the work log (sent to focused-pascal): `0264da83…`, `35727a10…`,
`bbca8ec0…`, `9e3a74fd…`.

The frozen `inputs/mesh_dirs_sha256.json` entries hold the C0 hash exactly where the swap belongs (`c0/<o>` and
`single/<o>/<o>`), and the library_v3 hash everywhere else.

### 2. MANIFEST and roster [M]
- **Roster:** the kit roster `track_3_evaluation_objects.json` has 20 episodes and 36 pairs. The MANIFEST `pairs` list
  is the same, in the same order.
- **Counts:** spoon 10, pot 6, rack 5, blue cup 5, beige 2, sweeper 2, dust pan 2, lid 1, pitcher 1, board 1 and
  board 2 1 each.
- **Swapped pairs:** 17 (pot 6, including eval 8 slot 1 from `library_v3x`; lid 1; rack 5; blue cup 5). Each
  `replaces_sha256` equals the pack-7 file.
- **Unchanged pairs:** 19, each equal to the pack-7 file.
- **Pack 7** is library_v3 everywhere except the eval-8 beige cup from v3x (work log ~5115; focused-pascal refs file
  line 13).
- **Libraries:** `library_c0` vs `library_v3` and `library_c0x` vs `library_v3x` have the same 11 `.glb` names and
  differ in exactly the 4 swapped files. `mini_sweeper.flatten.json` is identical in all four.
- **AUC directories:** scratchpad `cdo_c0/base` equals library_v3. `c0` differs only in the 4 swaps, and each
  `single/<o>` only in `<o>`.

### 3. Frame check, re-run [M]
`C0/scripts/frame_check.py` (sha256 891a8b47722ef08f), re-run unchanged on the same meshes, reproduces
`frame_check.json` exactly (0 differing values):
- pot: centroid 5.44 mm, median surface distance 2.73 mm;
- lid: 7.31 / 2.35;
- rack: 11.46 / 3.43;
- blue cup: 3.53 / 2.53.

For the independent ICP, see non-blocking 5.

### 4. Kit budget, encode/decode, watertightness, glTF [M]
Method:
- `v2dlb.mesh_budget.budget_mesh(4096, 4096)` is deterministic: two calls give identical arrays;
- `track3_pose._encode_archive` and `_decode_object_mesh` pass for all 8 meshes (4 new, 4 library);
- environment: fast_simplification 0.2.0, trimesh 5.2.0.

glTF:
- every file is glTF 2 from trimesh, with 1 node, 1 mesh, no node transform and no extensions;
- every primitive is triangles;
- signed volume is positive and winding consistent for all.

| Object | Active faces | Vertices | Watertight | Bodies | Library_v3 (wt / bodies) |
|---|---|---|---|---|---|
| white_pot | 4096 | 2058 | yes | 5 | no / 6 |
| white_pot_lid | 4096 | 2050 | yes | 2 | yes / 1 |
| plastic_dish_rack | 2356 (not decimated) | 1184 | yes | 3 | no / 10 |
| blue_cup | 4096 | 2059 | **no** (5 non-manifold edges) | **11** | no / 6 |

These equal the stage-1 claims in `frame_check.json`.

### 5. No ground truth in the C0 choice, and the timeline [M]

**Scripts.**
- `build_c0.py` reads repo meshes, existing jsonl records, the kit roster and our sweep `poses.npz`.
- `frame_check.py` reads mesh files only.
- `guard_eval.py`, `report_auc.py` and `verify_inputs.py` read our own JSONs and hashes.
- A grep for scan, parquet, mocap and `_align` finds no read in these scripts.

**Build code.** The same grep on `obs_points.py`, `lathe_obs.py` and `obs_fidelity.py` finds no read.
`prim_potlid.py` and `prim_rack.py` read no scan, but they carry the scan-derived constants of B1 and the T_LID and
T_WALL priors. The blue-cup lathe was built with `--spheres 0`, so no `MK_R0`.

**Twins.** They are exhaustive. Every sweep episode that contains the object is used. The other sweep episodes
(18, 23, 24, 39, 40) hold none of the four objects, judged from our own `poses.npz` keys. So nothing was cherry-picked.

**Frozen files.** PREREG, MANIFEST, roster, frame_check, `inputs/`, `build_c0.py`, `frame_check.py`,
`run_auc_guard.sh`, `guard_eval.py` and `pipeline/score_registered.py` are unchanged from `081b37e` to HEAD.
`score_registered.py` was last changed in 46b8389, and its seed is `1_000_003*ep + 101*slot` as stated.

**Timeline** (UTC, 31 Oct):

| Time | Event | Source |
|---|---|---|
| 15:28:57 | AUC mesh directories and tracks written | mtimes; nothing rewritten later |
| 15:32:36 / 15:32:38 | PREREG commit `081b37e` / pushed | git / origin reflog |
| 15:34:15 | first ground-truth file (HF tree cache) | `cdo_c0/hf` mtime |
| 15:34:16 | first parquet symlink `t3/ep0.parquet` | mtime |
| 15:36:44 | first AUC output `runs/single_white_pot/ep0.json` | mtime |
| 16:09:59 | last run JSON | mtime |

- The t3 scan links point to scratchpad `data/scan/*.glb`, the files used by the [D] records.
- The repo `auc/` directory equals scratchpad `cdo_c0/runs`, JSONs and `inputs_sha256.txt` alike (`diff -r`).

### 6. The rule [M, from our own score JSONs]
`regate.py` recomputes PREREG §5 independently from the 51 JSONs, with the same 1e-9 tolerance and the same
missing-data rule. It reproduces `guard_result.json` exactly:

| Object | mean dAUC | min dAUC | mean dMPPE cm | mean dRPE cm | Missing | Verdict |
|---|---|---|---|---|---|---|
| white_pot | +0.00299 | -0.0159 | -0.0566 | -0.1079 | 0 | ADOPTED |
| white_pot_lid | +0.00555 | 0.0000 | -0.0794 | -0.1205 | 0 | ADOPTED |
| plastic_dish_rack | +0.01582 | -0.0092 | -0.0433 | -0.0970 | 0 | ADOPTED |
| blue_cup | +0.02406 | -0.0049 | -0.2494 | +0.1625 | 0 | ADOPTED |

- Joint c0: mean dAUC +0.0148, dMPPE -0.128 cm, dRPE -0.058 cm. The values match AUC_RESULTS.
- The rule is applied as written. B2 concerns what is done with its output, not how it was computed.
- The [E] CD-O arithmetic in `cdo_estimate.json` checks out:
  - all four: 0.402 → 0.334;
  - pot, lid and rack: 0.367 (0.3667 in the file; stage 1 rounded it to 0.366).
  - Both rest on the stated assumption that the hidden scans equal the public ones.
