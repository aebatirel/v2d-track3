# Track 3 submission, 25 Oct 2026 (second pack)

- `track3_submission.parquet`: 9,120 rows, 20 eval episodes, poses plus our meshes (library_v3, unchanged), 1,329,718
  bytes, sha256 `6e4f6f7bc8440df1ad22aee5b9fd6a1fef23864dcb7e1c576ca6f8dce097b52f`. 0 MESH WARNING.
- Made on box `20261025-pack2-46b8389` (RTX PRO 6000 S) by `ops/jobs/pack_eval.sh` with `KEEP_RESULTS`:
  - re-evaluated with the pristine evaluator (8c778f9, 0 modified files), one rollout each: eval 30 (rerun with the
    gated re-proposal detection, run `20261024-ev30rp-07eef1a`) and the seed-43 picks 3, 5, 15, 16, 19 (run
    `20261024-seed43-61101f5`, chosen by the higher mean sim_vs_ref of 5 evaluations, rule fixed beforehand);
  - the other 14 episodes keep the first pack's official rollouts (`20261024-pack-31ef267`; checkpoint sha256
    unchanged).
  - Code commit in the file: https://github.com/aebatirel/v2d-track3/commit/46b838913a5e8f071ec933a3701b7da3947532e0
- `summary.txt`: sim_vs_ref of the packed rollouts against our own reference, mean **0.7218** (first pack 0.7101). Not
  the leaderboard score. Eval 30 drew 0.551 (its policy's 5-evaluation mean is 0.722; the rollout is now judged
  against a reference with the sweeper in the rack, so its truth score should rise more than this number).
- Uploaded by the agent to the five pose boards (AUC, SP-SR, MP-SR, RPE, MPPE); CD-O not re-uploaded (same meshes).
