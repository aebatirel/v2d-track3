# Track 3 submission, 25 Oct 2026 (third pack)

> **Correction (26 Oct, forensics):** the rollouts packed for evals **3, 5, 15 and 16** are the FIRST pack's seed-42
> rollouts (checkpoint sha256 8d256c33…, 3cc946c5…, cf0c9328…, b297186c…), not the second pack's seed-43 rollouts
> described below. A pulled run's old submission folder was copied in first and `cp -n` kept it. Evals 6, 10 and 35–38
> are unaffected. See docs/work-log.md (26 Oct); fixed in ops/jobs/pack_eval.sh.

- `track3_submission.parquet`: 9,120 rows, 20 eval episodes, poses plus our meshes, 1,387,467 bytes, sha256
  `dc3a5ad19007c22641302f6e110b22454d252bc6f76f26ad7c1bd4fb7e0396fe`. 0 mesh warnings.
  - Meshes are library_v3 for every episode except eval 8: library_v3x, the v5 beige cup adopted by the ep11 twin.
  - `track3_submission.cd-o.parquet` is the CD-O file the kit uploader extracted.
- Made on box `20261025-pack3-3758189` by `ops/jobs/pack_eval.sh`, code
  https://github.com/aebatirel/v2d-track3/commit/3758189c9a823687372f9220464002535d0e2b9c, with the pristine evaluator
  (8c778f9, 0 modified files).
- **Re-evaluated:** one fresh official rollout each for evals 1, 8, 14, 19, 20, 25, 28, 30, 32 and 33. The
  policies were chosen without ground truth, by the highest mean sim_vs_ref of 5 official evaluations against our
  own reference. The rules were fixed before the results (`docs/work-log.md`, 25 Oct).
  - **Standard learner (FDR RL, 250M):** evals 1, 19 and 28 (stored references) and 30 (ev30rp reference).
  - **Standard learner, eval 25:** reference rebuilt with the boards named correctly by the GT-free knob rule.
  - **Grasp lock (eval_both recipe):** evals 8, 14 and 20, on references rebuilt with the track guard. Eval 20 uses the
    arc foot, which its public twin adopted: ep21 0.657 → 0.772 vs mocap.
  - **Grasp lock (frozen recipe):** evals 32 and 33, on rebuilt references.
- **Kept:** the second pack's official rollouts for evals 3, 5, 6, 10, 15, 16, 35, 36, 37 and 38 (checkpoint
  unchanged).
- `summary.txt`: our own sim_vs_ref of the packed rollouts, mean **0.883** (second pack 0.7218). This is not the
  leaderboard score.
- **Uploaded by the agent to all six boards:**

| Board | Score | Rank (25 Oct ~20:10 UTC) | Before (second pack) |
|---|---|---|---|
| AUC | **0.78893** | **4th** | 0.58252, 9th |
| SP-SR | 0.80 | 5th (tied with 4th) | 0.50, 10th |
| MP-SR | 0.60 | 4th | 0.40, 7th |
| RPE | 4.59 cm | 4th | 8.82 cm, 9th |
| MPPE | 3.29 cm | 4th | 6.69 cm, 9th |
| CD-O | 0.402 cm | 11th | 0.405 cm, 10th |
