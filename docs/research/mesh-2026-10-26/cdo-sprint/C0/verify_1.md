# C0 verification 1 (stage 3): reproduce and arithmetic

- **When / where:** 2026-10-31, 16:13-16:35 UTC. Cloud VM (4 cores, shared, load ~9-11). CPU only, $0.
- **Lens:** re-run the scorer, re-apply the pre-registered rule with my own code, recompute the [E] board CD-O, and
  look for scorer-input mistakes. I did not build C0.
- **Checked against:** `PREREG.md` (081b37e), `AUC_RESULTS.md`, `guard_result.json` and `auc/` (edb4ffa), `MANIFEST.json`,
  `cdo_estimate.json`, `inputs/*.json`.
- **Labels:** [M] measured here. [D] scored against public ground truth (the twins' mocap and the public scans).
  [E] estimate. [H] hypothesis.
- **Scratch outputs (not committed):**
  - re-run JSONs and logs: scratchpad `cdo_c0_verify1/runs/<tag>/ep<e>.{json,log}`;
  - runner: `cdo_c0_verify1/scripts/rerun.sh`;
  - log: `cdo_c0_verify1/rerun.log`;
  - notes: `cdo_c0_verify1/NOTES_verify1.md`.

## Verdict

**No blocking item.**
- The four re-runs reproduce the stored JSONs byte for byte.
- My own code, written from PREREG §5, gives the same four ADOPTED verdicts and the same aggregates.
- The [E] CD-O arithmetic reproduces.
- I found no scorer-input mistake: no wrong mesh directory, no unpicked mesh name, no wrong episode-object mapping, no
  missing decimation, and no track-conversion error.

The non-blocking findings below matter for the hand-off. **N1** (the pack-9a CD-O number) and **N2** (the pot twins do
not cover the pot's main eval configuration) should be stated in any message to the pack 9a builder.

## BLOCKING

None.

## 1. Independent re-runs [M]

I chose four runs:
- `single/white_pot` ep2: the single swap with the most negative dAUC, -0.0159;
- `base` ep2: its baseline;
- `c0` ep13: the joint run with the most negative dAUC, -0.0240;
- `single/blue_cup` ep21: the 146.9 deg registration and the largest dRPE.

Each call is the same as `run_auc_guard.sh` `one()`: the same Python (`venv/bin/python -I`), the same
`pipeline/score_registered.py` (sha256 6a4cd60a0d26e3f8), the same `--meshes cdo_c0/<cfg>`, `--t3 cdo_c0/t3` and kit.
Only the output directory differs. The runs went two at a time at nice 5:

```
bash scratchpad/cdo_c0_verify1/scripts/rerun.sh   # 16:15:03-16:18:10 UTC; 40 s, 48 s, 111 s, 76 s
```

| run | result | key numbers (stored = re-run) |
|---|---|---|
| single_white_pot ep2 | **byte-identical** (`cmp`) | AUC 0.9664; pot 0.9931, lid 0.9397 |
| base ep2 | **byte-identical** | AUC 0.9823; pot 0.9923, lid 0.9723 |
| c0 ep13 | **byte-identical** | AUC 0.9365; blue 0.9007, rack 0.9724 |
| single_blue_cup ep21 | **byte-identical** | rot 146.9 deg / shift 0.46 cm; AUC 0.8827, RPE 2.0021 |

So the scorer is deterministic under a different load and process mix. The stored values are what this code and these
inputs produce. The 51 repo JSONs in `auc/` are also byte-identical to scratchpad `cdo_c0/runs/`. `runs.log` has 51
OK lines and 0 FAIL lines, and no run log contains "error" or "traceback".

## 2. Scorer inputs [M]

All of the following were checked by hashing and reading files. Nothing in this section read a scan or a parquet pose.

**Mesh directories.**
- `cdo_c0/base/` equals `meshes/library_v3/` for all 10 objects (sha256).
- `c0/` and each `single/<o>/` equal base plus exactly the intended swaps. Each swap equals its repo file:
  - `results/prim/meshes/white_pot_ep41_fit.glb`;
  - `results/prim/meshes/white_pot_lid_ep2_fit_v2.glb`;
  - `results/prim/meshes/plastic_dish_rack_joint_v2.glb`;
  - `cdo-sprint/C0/meshes/ep21_blue_cup_g1.glb`.
- All 60 files match `inputs/mesh_dirs_sha256.json`.
- Every run JSON's `meshes` field names the right directory for its tag (51/51).

**Mesh names and fallback.**
- `score_registered.py` `candidate_mesh()` looks up `<dir>/episode_XXXXXX/<obj>.glb`, then `<dir>/<obj>.glb`, and
  raises `SystemExit` if neither exists. There is no fallback to the scan when `--meshes` is given.
- The directories hold flat `<obj>.glb` files and no `episode_*` subdirectories, so every candidate is the intended
  file.

**Decimation.** Every candidate goes through the kit's `budget_mesh(path, 4096, 4096)`, the same function and limits
as the kit packer (`mesh_budget.py` 8f29481d52a82c46). The rack has 2356 faces, below the budget, so it is not
decimated, which is also what the packer does.

**Scans.**
- `t3/mesh/<obj>/` holds one symlink per object to `data/scan`. `scan_path()` falls back to `<obj>_visual.glb` only for
  the sweeper and the two wooden pieces, which are the only names on disk for those three.
- `auc/inputs_sha256.txt`: 25/25 hashes still match (`sha256sum -c`).

**Episode, object and track mapping.**
- For all 15 twins, `tracks.json` source and output paths name the right episode, and the source sha256 matches
  `data/sweep/ep<e>/poses.npz` today.
- The object order and frame count in `tracks.json` equal the parquet-derived `objects` and `frames` of every run JSON.
- Each twin's object list contains its object (pot 9, lid 2, rack 5, blue cup 5). These are all the sweep episodes that
  contain these four objects (the sweep has 20 episodes).

**Track conversion.** I recomputed `world_T_cam @ cam_T_obj` from the sweep `poses.npz` for ep2, 13 and 21. The max
abs difference from `poses_world_vo.npz` is 2.2e-16.

**Track frame vs eval frame.**
- The public sweep tracks were templated on library_v2 (gmg SPEC §1; C1 T1 PREREG). The eval tracks behind pack 7
  were templated on library_v3 (focused-pascal refs note).
- For all four swapped objects library_v2 equals library_v3 byte for byte. So base on the twins reproduces the eval
  situation: the track template equals the packed mesh.
- The sweeper differs between v2 and v3. It is not swapped; it is only the anchor partner on ep31.

**Frozen code.** These files are unchanged since 081b37e, and their sha256 equals PREREG §3:
- `PREREG.md`, `guard_eval.py`, `run_auc_guard.sh`, `inputs/`, `MANIFEST.json`, `cdo_estimate.json`, `roster.json`;
- `pipeline/score_registered.py`;
- kit `track3_pose.py` and `mesh_budget.py`.

**Integrity order.**
- The origin remote-tracking reflog shows 081b37e pushed at 15:32:38 UTC.
- The 15 parquets have mtimes from 15:34:15 to 15:35:07 UTC. So no ground truth was downloaded before the PREREG was
  in origin.
- My own re-runs read scans and parquets only through `score_registered.py`.

## 3. Rule re-applied by my own code [D numbers, M arithmetic]

The code is my own, written from PREREG §5 and not from `guard_eval.py`.
- Deltas are computed with exact `Fraction`s of the 4-decimal JSON values. The thresholds are exact.
- Same twins, same `perception` entries, no tolerance needed, because no value is near a threshold.

| object | n | mean dAUC (≥ -0.005) | min dAUC (≥ -0.02) | mean dMPPE cm (≤ 0.2) | mean dRPE cm (≤ 0.2) | verdict | guard_result.json |
|---|---|---|---|---|---|---|---|
| white_pot | 9 | +0.002989 | -0.0159 | -0.05663 | -0.10786 | ADOPT | same |
| white_pot_lid | 2 | +0.005550 | 0.0000 | -0.07940 | -0.12050 | ADOPT | same |
| plastic_dish_rack | 5 | +0.015820 | -0.0092 | -0.04326 | -0.09696 | ADOPT | same |
| blue_cup | 5 | +0.024060 | -0.0049 | -0.24938 | +0.16250 | ADOPT | same |

- **Joint c0, 15 twins:** mean dAUC +0.014813, min -0.0240 (ep13), mean dMPPE -0.12781, mean dRPE -0.05842. This
  equals `guard_result.json` and `AUC_RESULTS.md`.
- **Spot-checked claims in AUC_RESULTS §1/§3.** All of these match the JSONs:
  - per-object AUCs: pot ep2, lid ep2, rack ep12 / ep31, ep13 c0;
  - the registration ranges for the rack (rot 2.1-3.23 deg, shift 0.20-0.63 cm);
  - mean dMP-SR +0.067;
  - runtime 34.5 min.

## 4. [E] board CD-O recomputed [M arithmetic on D numbers]

**Inputs.**
- Pair weights come from the kit roster `data/track_3_evaluation_objects.json`: 36 pairs; spoon 10, pot 6, rack 5,
  blue cup 5, beige 2, dust pan 2, sweeper 2, lid 1, pitcher 1, board 1 1, board 2 1.
- `cdo_eval` values come from `results/baseline_library.jsonl` and the four swap records. Each record is matched by
  the sha1[:16] of the file on disk:
  - pot 4bf2135570c1da26 = 0.3417;
  - lid 67632273f5723dc9 = 0.2199;
  - rack b855279b68ecb432 = 0.4560;
  - blue cup 1bd4c8f5f475596f = 0.2906;
  - library_v3: 0.437117 / 0.4211 / 0.55506 / 0.52332.

| quantity | mine | cdo_estimate.json |
|---|---|---|
| non-spoon sum, library_v3 only / pack 7 (v3x on eval 8) | 12.7754 / 12.6491 | — / 12.6491 |
| non-spoon mean, v3 only / pack 7 | 0.4914 / 0.4865 | 0.4914 / 0.4865 |
| spoon inferred `(0.402*36 - 12.6491)/10` | 0.1823 | 0.1823 |
| board delta: pot / lid / rack / blue cup | -0.0159 / -0.0056 / -0.0138 / -0.0323 | same |
| **C0, all 4** | **0.3344** | 0.3344 |
| **pot + lid + rack (pack 9a)** | **0.36675** (prints as 0.3668) | 0.3667 |

The 3-object value sits exactly on a rounding boundary. The difference between 0.3667 and 0.3668 is rounding only.

**One calibration point [E].**
- On 25 Oct pack 3 changed eval 8's beige cup from library_v3 to v3x (`EP_LIB 8:library_v3x`). The board CD-O went from
  0.405 to 0.402.
- The model predicts (0.72995 - 0.85625)/36 = -0.0035. That is consistent with the observed -0.003 within the board's
  3-decimal display.
- This holds only if that beige swap was the only change to a packed mesh between packs 2 and 3. Work log line 3978
  says pack 2 used library_v3, but I did not verify every episode. n = 1.

## 5. Non-blocking findings

**N1. The pack 9a CD-O number is 0.367, not 0.334 [E].**
- Pack 9a takes pot, lid and rack only; the blue cup is held back (work log ~16:20 UTC).
- AUC_RESULTS §4 states only the 4-object estimate (0.334, "between 14th and 10th").
- For pack 9a the operative estimate is **0.367**, which `cdo_estimate.json` already holds as 0.3667. By the brief's
  table that is above 0.338, so it does not reach 14th.
- The blue cup carries 48 % of the 4-object gain: -0.0323 of -0.0676.

**N2. The pot's twins do not cover the pot's main eval configuration [D/H].**
- In the kit's `_align_registered_scene`, the first object without a symmetry axis sets the frame-0 world rotation.
  Object 0 sets the offset.
- On eval the pot is the rotation anchor of a scored partner in 5 of its 6 pairs:
  - eval 1 (lid);
  - eval 3, 5 and 6 (spoon: 3 of the spoon's 10 pairs);
  - eval 8 (beige cup, which is object 0 there).
- Among the pot's nine twins:
  - 5 are single-object episodes (41-45). There, rotation and offset are both pinned on the pot, so no partner exists to
    show the effect. RPE is 0 by construction.
  - 26 and 27 have the rack as anchor.
  - ep0 has a lid AUC of 0 in every run.
- The only informative twin of the eval configuration is **ep2, the pot's worst at -0.0159**. All of it is the lid:
  the lid's AUC falls by 0.0326 while the pot's own AUC rises by 0.0008.
- Splitting the episode dAUC into the swapped object's own change and the partner's change (mean over twins):
  - pot: own +0.0048, partner -0.0018;
  - rack: own +0.0104, partner +0.0055.
- Over the pot's four multi-object twins the mean dAUC is +0.0003 and the mean dRPE is -0.243 cm. The rule still
  passes on that subset.
- [H] On eval 3, 5 and 6 the pot swap moves the spoon's frame as it moved the lid's on ep2. Whether the spoon gains or
  loses is untested: no public pot + spoon twin exists. Not a rule violation: the twin set was pre-registered.

**N3. The blue cup's margin comes mostly from its partner [D].** This is moot for pack 9a.
- The partner's change contributes +0.0205 of the cup's +0.0241 mean dAUC. The cup's own change contributes +0.0036.
- Most of the partner gain is the pitcher on ep21 and ep22, each about +0.095 per object. It comes through the frame-0
  offset, because the cup is object 0 there.
- The cup's own AUC cannot show its own frame-0 anchor error: the offset pins that object to ground truth at frame 0.
- The pitcher configuration is 2 of 5 twins but 1 of 5 eval pairs (eval 20). Without the pitcher twins (11, 12, 13)
  the mean dAUC is +0.0069.

**N4. The ep21 146.9 deg registration depends on the seed [M].**
- Across the five blue-cup twins the candidate mesh, the scan, the slot (0) and so the host points (seed 7 + slot) are
  identical. Only the registration seed `1_000_003*ep` differs.
- The C0 cup lands at about 147 deg for 1 of 5 seeds (others 2.5-5.8 deg). The library_v3 cup lands there 0 of 5
  times.
- The base library_v3 beige cup also registers at 145.3 deg on ep11.
- So this is an ICP basin that the host's own seed may or may not hit on each eval pair. Whether it is a spin about the
  axis stays [H]. I did not run the spin/tilt split, because it reads the scan outside `score_registered.py`
  (PREREG §8).

**N5. The pack-9a configuration, taken from stored runs [D], with no new scoring.**
- For each twin containing pot, lid or rack, I took the run that equals the pack-9a mesh set:
  - c0 on ep0, 2, 26, 27, 31 and 41-45, which contain no blue cup;
  - single_plastic_dish_rack on ep12 and 13.
- Results over 12 twins:
  - mean dAUC +0.0099, min -0.0092 (ep12);
  - mean dMPPE -0.074 cm, mean dRPE -0.151 cm;
  - dSP-SR and dMP-SR 0.
- The joint flag on ep13 (-0.0240) needs the blue cup and does not arise in pack 9a; there ep13 is +0.0056.

**N6. Diluted or structural deltas.**
- The pot's mean dRPE averages 5 structural zeros (single-object twins). Its effective n is 4.
- The lid's effective n is 1 (ep2):
  - ep0 dAUC is structurally 0, because the lid's AUC is 0 in base and swap alike;
  - its ep0 dRPE and dMPPE (+0.095 / +0.045 cm) come from a failed track.

**N7. Selection context for the [E].**
- The blue-cup [D] CD-O 0.2906 is the best of 12 blue-cup lathe variants scored in `lathe_obs.jsonl`; the next best
  is 0.3637.
- Its selector is GT-free but was written after those scores, a flag already carried.
- The [D] noise is small (cdo_sd 0.0026). The risk is the assumption that the hidden scans match the public ones,
  and that risk weighs most on this object.
- Harmless: `potlid/nostem/ep41` and `potlid/fit/ep41` in `metric_all.jsonl` have the same sha1. That is one file
  under two labels.

**N8. Cosmetic.**
- The PREREG header says "Written ... ~15:40 UTC", but its commit is 15:32:36 UTC and NOTES logs it at 15:32:23. The
  header time is wrong; the order of events is not affected.
- AUC_RESULTS §2 says "load ~11"; NOTES says ~13.

## 6. Not done, and why

- **No new CD-O scoring.** None is pre-registered.
- **No scan-reading diagnostic** (the ep21 spin/tilt split). This follows PREREG §8 and needs its own go-ahead.
- **No re-run of the other 47 runs.** Determinism was shown on 4 runs, and the remaining JSONs equal the scratchpad
  runs that `runs.log` lists as OK.
- **Shared files untouched.** STATUS.md, the work log and C0/NOTES.md were not edited, because the brief says to commit
  this file only. My running notes are in scratchpad `cdo_c0_verify1/NOTES_verify1.md`.
