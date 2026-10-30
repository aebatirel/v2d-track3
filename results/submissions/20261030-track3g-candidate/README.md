# Track 3 candidate pack 7, 30 Oct 2026: pack 6 with eval 33 replaced

**UPLOADED 30 Oct ~06:40 UTC on the owner's approval** ("you can send the pack 7 to get the score"). Scores below. This folder has no Kaggle receipt, and this session made no

| Board | Pack 7 | Pack 6 |
|---|---|---|
| AUC | **0.81460** | 0.81391 |
| SP-SR | 0.85 | 0.85 |
| MP-SR | 0.65 | 0.65 |
| RPE | 3.932 cm | 3.942 cm |
| MPPE | 2.921 cm | 2.925 cm |

AUC +0.00069 (expected ≈ +0.0003 [estimate], well inside the ±0.008 band). AUC board at 06:45 UTC (API, first rows):
1 richchentw 0.940, 2 DDD 0.931, 3 Zihao Guo 0.883, 4 Purple 0.870, 5 rlwrld 0.860, 6 SRL 0.856, **7 us 0.8146**,
8 DSAIL 0.773. Submissions 57795535 / 537 / 538 / 540 / 541; receipt in this folder.
Kaggle call.

- `track3_submission.parquet`: 9,120 rows, 1,388,061 bytes, sha256
  `137c8687a097da94cc935ad13609e996ab59319be425ea23b70c0510a28cfea7`. 0 mesh warnings.
- Built on CPU in session `claude/focused-pascal-2nz9s1` with the kit's `tools/pack_submission.py`. No GPU box was
  used. The code commit in the file is
  https://github.com/aebatirel/v2d-track3/commit/465320b8e2f3b0f5eb5f35ec232b239241634c32. That commit is pushed and
  contains the eval-33 jobs (`0202139`, `34bf6ae`) and pack 6's commit `5203d42`.

## Content

The only change from pack 6 (`results/submissions/20261026-track3f/`, AUC 0.81391) is eval 33.

| Item | Source |
|---|---|
| Evals 1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 35, 36, 37, 38 | Pack 6's rollout files, byte-identical: `runs/20261026-pack6-5203d42/results/submission/results/` |
| Eval 33 | `runs/20261030-c33B-0202139/results/submission/results/episode_000033.{json,parquet}` |
| Meshes | Pack 6's `meshes/` folder, unchanged: library_v3, plus v3x for eval 8. Eval 20's pitcher is library_v3. |

- **Eval 33 policy:** arm B's checkpoint `runs/20261029-rcB-34bf6ae/results/glock_public/ep33/best/policy.safetensors`
  (policy_40001536), sha256 `df90b2162885a17c83ea69ce90067ec567b89434adbcdedc0fba19d4b0c07ccb`.
  - It was trained REUSE_REF on the same stored reference as pack 6's eval-33 policy. Both episode JSONs name the same
    reference parquet.
- **Eval 33 rollout:** draw 1 of the c33B confirmation box. It was picked by its position, before the confirmation
  result existed.
  - Evaluator: the pristine FlashCHORD evaluator, a worktree at 8c778f9 with 0 modified files (c33B `job.log`).
  - sim_vs_ref of this rollout: 0.9401. Pack 6's packed eval-33 rollout scored 0.9319.
  - Disclosure: by score this draw ranks 9th of the 10 (ascending; the draws span 0.917–0.945). It was taken by position
    (draw 1), not chosen by score; the difference from the 10-draw mean (0.934) is +0.006.
- `checkpoints.json` gives, for each of the 20 episodes, the run, the checkpoint's path in the store, its sha256 and
  the rollout it came from.
- `summary.txt`: sim_vs_ref of the packed rollouts against our own reference. The mean is 0.9168, against 0.9164 for
  pack 6. This is not the leaderboard score.

## Why eval 33 changed: pre-registered rule, measured

The rule was fixed in the work log on 30 Oct, before any result. Arm B's checkpoint replaces eval 33 only if its
10-draw mean sim_vs_ref is at least 0.884 (the H5 mean + 0.03) and its sd is at most 0.137 (the H5 sd).

| Policy | 10 fresh draws, sim_vs_ref | min |
|---|---|---|
| Pack 6's eval-33 policy (sha 88b20644…), H5 | 0.854 ± 0.137 | 0.576 |
| Arm B's checkpoint (sha df90b216…), c33B | **0.934 ± 0.008** | 0.917 |

The rule passes.

## Checks (all measured)

**Checkpoints**
- The rcB checkpoint downloaded from the store hashes to the `checkpoint_sha256` in c33B's `episode_000033.json`
  and in its parquet metadata. It differs from pack 6's eval-33 checkpoint.
- In all 20 pack-6 episode JSONs, `checkpoint_sha256` equals the value packed in pack 6's parquet. All 19 kept
  rollouts are reused byte for byte.

**Provenance hashes** (identical to pack 6)

| Hash | Value |
|---|---|
| eval_script_sha256 | `160d24f5…` |
| eval_code_sha256 | `b1b3ebe3…` |
| packer_script_sha256 | `49b13052…` |
| uploader_script_sha256 | `d31d4a7c…` |

- The local kit matches its own `KIT_MANIFEST.json` for all 54 files. The manifest names evaluator commit 8c778f9.

**Toolchain reproduces pack 6.** Repacking pack 6's own inputs with the same local kit and venv, and pack 6's commit
URL, gives a byte-identical `d59b6e63…`.
- Venv: Python 3.13, pandas 3.1.0, pyarrow 26.0.0, numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, fast_simplification
  0.2.0.
- With pandas 3.0.5 the table content was identical. Only the `pandas_version` string in the schema metadata
  differed.

**Difference from pack 6, by column**
- The 696 eval-33 rows differ in their poses and `checkpoint_sha256`.
- `code_commit_url` differs on all rows.
- Everything else is identical, including `row_id` order and `object_mesh_b64`.
- The eval-33 rows are identical to the eval-33 rows of the c33B box's own pack (`8eaf5bf0…`), apart from the commit
  URL.

**Kit `tools/preflight.py`** (`--track track_3 --results <build>/results --skip-kaggle`, see `preflight.log`)
- Ok: Python, numpy, pandas, pyarrow, trimesh, fast_simplification, the public Track 3 inputs, 20 trajectory parquets,
  all 20 scored episodes present.
- Its one FAIL is "kaggle missing". The Kaggle package is deliberately not installed in the packing venv, and the
  Kaggle checks were skipped.
- Preflight checks the environment and the rollout folder, not the packed file.

**Ground truth:** none was read. The packer reads only `row_id` from the kit's sample submission, plus the object
roster.

## Expected effect (estimates, not measured)

- **Policy view [estimate]:** +0.080 on one episode of 20 is +0.004 mean sim_vs_ref, roughly +0.003 on the
  leaderboard at the measured transfer of 0.74–0.78. This is the expected gain over *fresh draws*: 0.854 → 0.934.
- **This file vs pack 6's file [estimate]:** the leaderboard scores the submitted trajectories, not the policy's
  average over draws. Pack 6's packed eval-33 rollout was already a good draw (0.9319). The measured packed difference
  is therefore +0.0082 on eval 33, which is +0.0004 mean sim_vs_ref. At the same transfer that is about +0.0003 on the
  leaderboard, probably within noise.
- The main gain is robustness. Pack 6's eval-33 policy collapses in some draws (sd 0.137, min 0.576); arm B's does
  not (sd 0.008, min 0.917). That gain shows only if the checkpoints are evaluated again.

## How it was made

Scratch root `S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad`.

1. Downloads, each into its own new folder:
   - `$S/pack7/dl_pack6`: pack 6's episode files, meshes, logs and parquet;
   - `$S/pack7/dl_c33B`: c33B's eval-33 files, qa, h5 summary, job log and pack;
   - `$S/pack7/dl_ckpt2`: the rcB checkpoint;
   - `$S/pack7/dl_c33B_meshes33`: c33B's eval-33 meshes, for comparison only. They are identical to pack 6's and to
     `meshes/library_v3`.
2. `$S/pack7/build/results`: pack 6's 38 episode files except eval 33, plus c33B's `episode_000033.{json,parquet}`.
   No hydra folder; the packer only globs `*.parquet` and `*.json`.
3. `$S/pack7/build/meshes`: a copy of pack 6's `meshes/` (`diff -r` clean).
4. Packing (cwd = the kit, as on the box):

```
cd $S/map/scoring/kit/v2d_submission_kit && $S/pack7_venv/bin/python -I tools/pack_submission.py --track track_3 \
  --results $S/pack7/build/results --meshes $S/pack7/build/meshes \
  --code-commit "https://github.com/aebatirel/v2d-track3/commit/465320b8e2f3b0f5eb5f35ec232b239241634c32" \
  --eval-script $S/map/scoring/kit/v2d_submission_kit/flash_chord/scripts/evaluate_policy.py \
  -o $S/pack7/build/track3_submission.parquet > $S/pack7/build/pack.log 2>&1
```
