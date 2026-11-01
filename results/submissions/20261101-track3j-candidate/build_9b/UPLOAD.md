# Pack 9b upload (1 Nov 2026, 04:57–05:02 UTC)

- **Authority.** The owner, directly in the keen-heisenberg session:
  - "Upload automatically" (31 Oct, 21:14:50 UTC), for pack 9b = 9a+ plus D cells that pass the pre-registered swap rule;
  - "I give you permission for everything" (1 Nov, 02:50 UTC).
  - Uploaded by keen-heisenberg, the single uploader. focused-pascal built the pack and did not upload.
- **File.** `track3_submission.parquet` from `claude/focused-pascal-2nz9s1` (commit 874c9d3) at this path.
  - sha256 `a6c4105abb4a6a85f90cb4eb0e1a93030e7e4d5fb4f4532306e641c402744e4a`; 9,120 rows over 20 episodes.
  - Code commit URL: dd24ed4 (on origin).
- **Checks run by the uploader before upload [M]:**
  - **Swap rule.** Verdict (`docs/research/work/pack9b-20261031/results/verdict.txt`) against PREREG §4. The PREREG was
    committed in 2ce1872 at 21:32 UTC 31 Oct, before any D launch, and has not changed since.
    - Eval 33: PASS on every clause, with n 10 / 10:
      - (a) 0.9358 ≥ 0.9234;
      - (b) 0 / 10 ≤ 0 / 10 fails;
      - (c) median RPE 1.9647 ≤ 2.0599;
      - (s) draw 1 0.9419 ≥ 0.9401 − 0.05.
    - Evals 14, 16, 25, 30: NO-SWAP.
  - **Byte diff against 9a+** (sha256 e02736ea…, the uploaded 9a+):
    - only e000033's 696 rows differ in pos / quat and checkpoint_sha256, from df90b216… (pack-7 rcB) to 7c5eb060…
      (the D policy, drG s42);
    - code_commit_url changes on every row, from d7ecaef to dd24ed4;
    - object_mesh_b64 is identical on every row;
    - every other episode is identical in every other column.
  - **Script hashes in the rows:** eval 160d24f5…, eval code b1b3ebe3…, packer 49b13052…, uploader d31d4a7c…. The packer
    and uploader hashes match the kit's `tools/pack_submission.py` and `submit/v2d_submit.py`.
  - Poses are all finite; quaternion norms are within 2.2e-7.
  - Dry run: valid, 5 uploads left per board. The CD-O file the uploader derived equals the staged one in pandas (294,912 rows).
- **Tool.** Kit `submit/v2d_submit.py` via `tools/kaggle_upload.py` (kaggle 2.2.5), `--receipt --wait`. Receipt: beside
  this file.

**Scores** (Kaggle, all six boards, 05:02 UTC), against 9a+ (our best):

| Board | 9b | 9a+ | Change |
|---|---|---|---|
| AUC | 0.81677 | 0.81757 | −0.00080 (worse) |
| SP-SR | 0.85 | 0.85 | = |
| MP-SR | 0.65 | 0.65 | = |
| RPE | 3.88283 cm | 3.87853 | +0.0043 (worse) |
| MPPE | 2.90186 cm | 2.89663 | +0.0052 (worse) |
| CD-O | 0.33234 cm | 0.33234 | = |

**Reading.**
- The swap was expected to be within noise: +0.0018 on the GT-free proxy for one episode, about +0.0001 AUC [E].
- On the board it cost −0.0008 AUC [M]. Our GT-free sim_vs_ref proxy cannot rank two rollouts that differ by 0.002 on
  one episode.
- 9a+ remains our best board score. 9b's value is robustness on eval 33: the D policy's official draws have a minimum of
  0.903, against 0.847 for the packed policy. That matters only if the organisers' reproduce check re-runs policies.
