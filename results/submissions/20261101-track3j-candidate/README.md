# Track 3 pack-9b candidate, 1 Nov 2026 — pack 9a+ with a fresh official eval-33 rollout (D arm)

**NOT UPLOADED from this session.** The upload is the owner's decision. It happens in the session where the owner gave
the word (as with 9a+, the score-status session), or on the owner's own word in this session.

## Record
- File: `build_9b/track3_submission.parquet`, 9,120 rows, 1,312,426 bytes.
  sha256 `a6c4105abb4a6a85f90cb4eb0e1a93030e7e4d5fb4f4532306e641c402744e4a`.
- CD-O file derived by the uploader's own offline step: `build_9b/track3_submission.cd-o.parquet`, 294,912 rows,
  sha256 `9b251a4d92c75362…`. It is identical row for row to the one derived from 9a+, because meshes are unchanged.
- Code: https://github.com/aebatirel/v2d-track3/commit/dd24ed412714ecc12cbda275be9b45180a00744e (on every row).
- Built on CPU by `tools/pack_swap_rollouts.py`:
  - Inputs are 9a+'s own packer inputs. Base = `results/submissions/20261031-track3i-candidate/build_9aplus/track3_submission.parquet`
    (e02736ea…).
  - The packing venv is pandas 3.0.6, pyarrow 26.0.0, numpy 2.5.4, trimesh 5.2.0, fast_simplification 0.2.0.
  - Self-test: a pure repack with 9a+'s commit URL rebuilds 9a+ byte for byte.

## Content
- 19 of 20 episodes byte-identical to 9a+ in every column except code_commit_url. That includes every mesh payload
  (9a+'s C0 / C1 meshes, as flagged and disclosed there).
- **Eval 33:** the draw-1 rollout (by position) of confirmation box `20261101-drC-a1a7e25`.
  - Policy: run `20261031-drG-a1a7e25`, seed 42, `results/drs42_glock_public/ep33/best/policy.safetensors`,
    sha256 `7c5eb060b8a390ae83ebdcf414e5759393077b3addcd7c8729358e24e8dd6332`.
  - It was trained with the packed eval-33 recipe plus D (start-state randomisation of sampled training resets,
    ±1.5 mm / ±0.015 rad / fingers ±0.01 rad; `ops/box/patch_flashchord_dr.py` md5 570a7f47…). D is a TRAINING-only
    change: the evaluator is the pristine kit evaluator (clean tree 8c778f9, 0 modified files), with no FC_DR_* in
    evaluation (dr_pack_check ok on both draw paths).
  - The rollout replaces pack 7's eval-33 rollout (c33B draw 1, checkpoint df90b216…).
- Checks against 9a+:
  - only eval 33's 696 pose rows and its checkpoint_sha256 differ;
  - object_mesh_b64 is identical on every row;
  - the uploader's offline validate_submission passes;
  - tools/no_oracle.py passes, including the swap's reference path.

## Why: the pre-registered per-episode swap rule
PREREG `docs/research/work/pack9b-20261031/PREREG.md` (2ce1872, before any D result). Verdict:
`docs/research/work/pack9b-20261031/results/verdict.txt`. GT-free sim_vs_ref vs our packed reference P; 10 official
draws of the D candidate vs 10 fresh draws of the packed policy (run 20261031-h5p7-1a7cdff).

| eval | D candidate | new mean | packed mean | fail rate new / packed | verdict |
|---|---|---|---|---|---|
| 14 | s43 | 0.6864 | 0.7269 | 8 / 4 of 10 | NO-SWAP (a b c s) |
| 16 | s43 | 0.8311 | 0.8498 | 1 / 0 | NO-SWAP (a b c) |
| 25 | s42 | 0.8580 | 0.8782 | 1 / 0 | NO-SWAP (a b) |
| 30 | s42 | 0.8164 | 0.8972 | 1 / 1 | NO-SWAP (a c) |
| 33 | s42 | 0.9358 | 0.9234 | 0 / 0 | **PASS**; draw 1 0.9419 vs old packed 0.9401 |

## Expected effect [estimate]
- Expected change: +0.0018 sim_vs_ref on one of 20 episodes (draw 1 0.9419 vs the replaced rollout's 0.9401, GT-free
  proxy), about +0.0001 AUC. That is within noise.
- The swap's value is robustness on eval 33. Official draws: min 0.903 vs the packed policy's 0.847. Training box: sd 0.006.
- Cost of the D arm: 5 training boxes $17.24 + confirmation $2.17 = **$19.41** measured.
