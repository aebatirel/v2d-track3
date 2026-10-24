# Track 3 submission, 24 Oct 2026 (first full 20-episode run)

- `track3_submission.parquet`: 9,120 rows, 20 eval episodes, poses plus our meshes, 1,329,173 bytes,
  sha256 `ff6a2051990799df0b7a634d61e18b0d9d57dac15003e98d23521e455e155393`. 0 MESH WARNING.
- Made on box `20261024-pack-31ef267` (RTX PRO 6000 S) by `ops/jobs/pack_eval.sh`:
  - the pristine FlashCHORD evaluator, a worktree at 8c778f9 with 0 modified files, run through the kit's
    `examples/run_policy_evaluation.py`: one rollout per episode, 1 world, explicit reset;
  - meshes from `meshes/library_v3`;
  - the kit packer, rerun by hand after `pip install fast_simplification` (now in pack_eval.sh, commit 6f1aea3).
  - Code commit in the file: https://github.com/aebatirel/v2d-track3/commit/6f1aea3751a372a50473aa6934e5bf0dbc00bd3a
- `checkpoints.json`: the checkpoint per episode, chosen by mean sim_vs_ref over 3 evaluations (no ground truth).
- `summary.txt`: sim_vs_ref of the packed rollouts against our own reference, mean 0.710. It is not the leaderboard
  score.
- Upload (owner, kit root, Kaggle credentials, rules accepted for all six Track 3 competitions):
  `python3 submit/v2d_submit.py track3_submission.parquet --track track_3 -m "first full run 24 Oct" --wait`
- `track3_submission.cd-o.parquet`: the CD-O (mesh) file, extracted from the combined file with the kit uploader's
  own code (`v2dlb.track3_pose.cd_o_submission`), 294,912 rows, 3,010,505 bytes. Both files pass the kit uploader's
  `validate_submission` locally.
- Manual upload in the Kaggle web page: the combined `track3_submission.parquet` goes to the five pose competitions
  (AUC, SP-SR, MP-SR, RPE, MPPE), the same file the uploader sends them; `track3_submission.cd-o.parquet` goes to CD-O.
