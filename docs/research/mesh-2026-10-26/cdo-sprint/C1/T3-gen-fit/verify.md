# C1 / T3 generate-then-fit: adversarial verification

Verifier: a separate agent that did not build T3. Date 2026-10-31, 16:47-17:00 UTC. CPU only, $0.
Verified: PREREG `2d2a8ee`, results commit `66d60c0` (HEAD at the start was `9e41d09`).
Labels: [D] = public-scan diagnostic, [M] = GT-free measurement, [E] = estimate, [H] = hypothesis.
My working files are in the scratchpad under `cdo_c1/t3_verify/` (`scripts/rerun.sh`, `rerun.log`, the fit and AUC
outputs). My steps are logged as the `VERIFY` lines in `NOTES.md`.

## Verdict

**No blocking issue.** I reproduced every number in the T3 result, and the integrity rules held:
- the pre-registration was pushed before the first scan read;
- construction and choices are GT-free;
- the meshes are byte-identical across the chain;
- the gates were applied as written;
- the AUC runs used the intended mesh dirs.

My re-runs reproduced byte for byte (one fitted mesh, one AUC twin, base and single).

The conclusion stands: **nothing from T3 is adopted.** It has 3 CD-O-gate WINs (pot, blue cup, dust pan), and all 3
fail the AUC guard [D].

The headline "H-GF not falsified" is literally correct, but it says almost nothing about the fitting step
(non-blocking items 1 and 2).

## Checks and results

### 1. Pre-registration before any scan read: PASS
Times come from git and from file birth times.
- The PREREG commit `2d2a8ee` was made at 16:02:51. The remote-tracking ref shows it pushed at 16:02:53 (`git reflog
  origin/...`).
- The first scan read came after that:
  - `score.log` was created at 16:02:59 (the scoring process started);
  - the first `scores.jsonl` record was written at 16:05:16.
- AUC runs ran 16:33-16:40. The ep18/39/40 parquets were downloaded at 16:39:11-16:40:05, during the guard.
- The scoring and verdict scripts were all committed before `2d2a8ee`: `fit.py` in `d721d97`; `gates.py`,
  `run_auc.sh`, `run_fits.sh` in `48cd00b`; `guard.py` in `f0a1e2c`; `cfg_frozen.json` in `24004a2`.
- Since `2d2a8ee`, no change to `PREREG.md`, `cfg_frozen.json` or any script except the new `results_table.py`
  (`git diff 2d2a8ee HEAD`).
- The working tree matches HEAD.

### 2. GT-free construction and choice: PASS
- **No GT reads in construction.** I grepped every T3 script in the repo and in scratch (`fit.py`, `picks.py`,
  `manifest.py`, `run_fits.sh`, `ana*.py`, `slices.py`, `summ.py`, `test_*.py`) for scan, mocap, parquet, `pose`,
  align and hfds. There are no hits outside docstrings.
  - `fit.py` reads only `--mesh` (the placed mesh) and `--obs` (the obs npz).
  - Scans and parquets appear only in `score.py`, `gates.py`, `guard.py` and `run_auc.sh`, which all ran after the
    push.
- **Upstream inputs.** `gen/sim3_fit.py` reads only `--obs` pts and the generated mesh. `scripts/obs_points.py` reads
  our tracks, depth, calibration and the library_v3 ROI mesh. library_v3 is our own reconstruction (its README).
- **Picks.** `selection.json` `pick` is the GT-free argmin of the probe's observed-point metric.
- **Input hashes.** I re-resolved the picks with `picks.py`; they are identical to the build's `picks.jsonl`.
  - All 10 placed meshes hash to an entry of `results/gen-probe/SHA256SUMS`, and to the PREREG table.
  - All 10 obs npz hashes match the PREREG.
- **Dev rule re-applied from `dev_diag/*.diag.json`.**
  - v4: input held tmean90 2.141; stage 0 2.155, within the 0.02 tie, so the stiffer one wins, i.e. the input.
  - v5: stage 0 2.021, against 2.048 and 2.090 for the later stages.
  - v5 stage 0 constraints: flips 0; self-intersections 50 <= 12 + 120; area 1.026; free 0.0723 <= 0.0865.
  - So k* = stage 0, as frozen.
- **Build config.** Every build `diag.json` carries a config equal to `cfg_frozen.json` and the PREREG placed-mesh
  sha.
- **One caveat (not an integrity breach).** The raw picks' [D] CD-O were already in `selection.json` and
  `gen-probe/scores.jsonl` while T3 was designed. No T3 choice uses them; the dev object was chosen by eval-pair count.

### 3. Byte identity of meshes: PASS
For all 10 objects, these agree:
- the PREREG sha256;
- the file in `meshes/`;
- the git blob at `2d2a8ee`;
- the scratch build `fit.glb`;
- `build_manifest.json`;
- the scored record's `sha` (sha1[:16]; the scored path is the repo file);
- for the 3 WINs, the `<obj>.glb` in the AUC single-swap dir.

`scores.jsonl` holds 10 records with 10 distinct shas, one scoring each. Neither scratch nor the repo holds another
score record of a T3 mesh.

### 4. Gates applied as written: PASS
I recomputed the gate from `scores.jsonl` and `results/baseline_library.jsonl`. I did not use `gates.py` or
`gates.json`.
- **Baselines.** CD-O and add_med are pot 0.4371/6.69, lid 0.4211/8.13, rack 0.5551/5.79, blue 0.5233/10.14,
  pitcher 0.8942/7.97, dust pan 0.3307/5.65, sweeper 0.3170/5.245, boards 0.2219/2.49 and 0.2158/3.315. The beige cup
  is 0.8562/6.965 for v3 and 0.7299/5.51 for v3x.
- **Flips.** I counted them from the per-seed records:
  - the sweeper and both boards have 30 extra seeds, 1001-1030 (n_extra = 30);
  - every other object has 0 flips.
- **WINs.** WIN = pot, blue cup and dust pan: 3 WINs, the same as `gates.json`.
- **Fitted vs raw.** The fitted mesh is worse than the raw pick on 3 of 10 objects (lid, blue cup, beige cup).
  - Mean d vs raw is -0.0178, median -0.0114.
  - The raw picks of the same 3 objects pass the same gate.
- **Wording I checked against the records.** Every per-object note and verdict in the T3 result JSON matches them.
  These include all the "FAIL (...)" reasons, add_med -1.91, -2.05 and -0.71 mm vs raw, and the [E] board effect
  6 x 0.1259 / 36 = -0.021 cm.
- **Other claims confirmed.**
  - `mesh_metric.py` uses `n_extra = max(min_extra, 6 - n_eval)` (line 275).
  - pymeshlab has no `meshing_close_holes` here.
  - The watertight, body and face counts (blue cup 4002) match: I reloaded all 10 meshes with trimesh.

### 5. AUC guard and mesh dirs: PASS
- **Twins.** They equal the object sets of the perception tracks (`data/sweep/ep*/poses.npz` keys) for all 10
  objects.
- **Mesh dirs.**
  - Each single-swap dir differs from `cdo_c0/base` only in the swapped object's file, which is byte-identical to the
    committed mesh.
  - `cdo_c0/base` matches `meshes/library_v3` file by file (10 public objects).
  - It is unchanged since 15:28:57 and matches `cdo_c0/mesh_dirs_sha256.json`.
  - No `episode_XXXXXX/` subdir could shadow a file.
  - The current `score_registered.py` raises `no candidate mesh` rather than falling back to the scan.
- **Each run JSON's `meshes` field.**
  - The 17 base runs point at `cdo_c0/base`.
  - The 9 / 5 / 3 single runs point at their `single_<obj>` dir.
  - In every single run, only the swapped object's registration differs from base.
- **Base reuse.**
  - The 14 reused base JSONs are byte-identical to C0's (`C0/auc/base/` and scratch `cdo_c0/runs/base/`).
  - They come from the same kit, scans, parquets and track recipe (`C0/scripts/run_auc_guard.sh`).
- **Inputs.** `auc_runs/inputs_sha256.txt` re-checks 37 of 37 OK.
- **Recomputation from the run JSONs** (rule: mean >= -0.005, min >= -0.02, dMPPE <= +0.2, dRPE <= +0.2):

| Object | mean dAUC | min dAUC | mean dMPPE cm | mean dRPE cm | Verdict |
|---|---|---|---|---|---|
| white_pot | -0.0099 | -0.0416 (ep45) | +0.148 | +0.088 | FAIL |
| blue_cup | +0.0217 | -0.0422 (ep13) | -0.228 | +0.009 | FAIL |
| mini_dust_pan | -0.0056 | -0.0425 (ep18) | -0.031 | +0.106 | FAIL |

These are identical to `auc_*.json`.

### 6. Independent re-runs: PASS (byte-identical)
- **GT-free fit.** I re-ran the fit of `mini_dust_pan` with the frozen config, as a new process into a new dir:
  `fit.py --mesh <placed> --obs obs_all/ep39_mini_dust_pan.npz --cfg cfg_frozen.json` (19.5 s).
  - Output sha256 `64a48c0ff0da33c4…`, equal to the committed mesh.
  - Held-out tmean90 1.70 mm [M], as in `build_manifest.json`.
- **AUC twin ep18, base and single** [D].
  - Set-up:
    - I rebuilt the ep18 track from `data/sweep/ep18/poses.npz`; it matches T3's with max abs diff 2.2e-16;
    - I assembled a new single-swap dir.
  - Ran `pipeline/score_registered.py 18 … --meshes {cdo_c0/base | new dir}`.
  - Result: AUC 0.9642 (base) and 0.9217 (single).
  - The perception and registration blocks equal the committed JSONs exactly.
  - Integrity note: this was 1 extra scan read, a re-run of an existing single-swap run. It was requested for
    verification and it informs no choice.

## Non-blocking findings

1. **The H-GF rule cannot credit the fit.** The falsifier's WIN arm is met only because the raw picks are good: the
   raw picks of all 3 WIN objects already pass the same gate. So "not falsified" carries no evidence for the fitting
   step itself.
   - The evidence for the fit is the vs-raw arm: better on 7 of 10, mean -0.018 cm, median -0.011 [D].
   - The raw-vs-fitted decimation path is a confound. It was pre-registered but not controlled.
   - RESULTS says "the fit created no new WIN". The verdict line should lead with that, not with "not falsified".
2. **`gates.json` says `"verdict": "SUPPORTED"`.** A falsify-only rule can only return "not falsified" (RESULTS uses
   that wording). Relabel it.
3. **The 9/10 held-out sign agreement is weak evidence.**
   - The marginals are 8/10 held-out better and 7/10 CD-O better. Given them, 9 is the largest agreement possible.
   - Its permutation probability is C(8,7) / C(10,7) = 8/120 = 0.067. Chance expectation is 6.2 of 10 [M].
   - Three of the 9 agreements have |dCD-O| <= 0.0064 cm, which may sit inside the decimation confound.
   - The proposed falsifier (<= 6/10) only fires at chance level. A stronger test would use a rank correlation of the
     magnitudes on new fits.
4. **What the hold-out tests.** Held-out frames are 10-frame blocks interleaved with training blocks (20 %). The
   held-out points therefore see the same surfaces from almost the same viewpoints. The "held-out residual" mainly
   detects noise fitting, not shape generalisation to unseen surface. Describe it that way.
5. **Self-intersection limit checked only on the dev pot.** The dust pan WIN mesh would fail the dev constraint
   (49 -> 527 > 49 + 120 at 12k faces). So would the rack (389) and the sweeper (355). This is moot while nothing is
   adopted, but it matters if the dust pan fit is ever reconsidered.
6. **Commit message vs content.** The `2d2a8ee` message says "build manifest, meshes". Those files, plus
   `score_manifest.tsv` and `guard.py`, entered git 4 s earlier in the WIP snapshot `f0a1e2c`. They are
   byte-identical at `2d2a8ee`, so the pre-registration covers them; only the message is inaccurate.
7. **Rounding.** The sweeper's 0.41855 appears as 0.4185 (RESULTS) and 0.4186 (NOTES). The dust pan's 0.25415
   appears as 0.2541 and 0.2542. "Median displacement 0.7-2.2 mm" is 0.69-2.25. All trivial.
8. **The AUC run JSONs do not record the candidate mesh hashes.** Mesh identity rests on the dir contents I checked
   after the runs, and on my identical ep18 re-run. Recording a sha per object in `score_registered.py` output would
   close this gap for future guards.
9. **[H] Blue-cup registration rotations.** In the single swap they are 75, 175 and 105 deg on ep11, 13 and 21 (base
   0.8-1.9 deg). A spin about the cup axis is harmless. The 175 deg on ep13, the min-dAUC twin, may instead be an
   upside-down registration that mesh_metric's 7 flip seeds did not sample.
   - Falsifier: the registered axis for ep13 points the same way as the scan axis.
   - This does not change the verdict.

## Cost
CPU only, $0. About 40 s of fit and AUC compute plus hashing, at nice 10 next to the other workflows.
