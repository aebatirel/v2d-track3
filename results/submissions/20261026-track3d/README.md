# Track 3 submission, 26 Oct 2026 (fourth pack)

- `track3_submission.parquet`: 9,120 rows, 20 eval episodes, 1,388,433 bytes, sha256
  `59db1c316d4075f57dc6607593cd5ee7ebc8a65267bb3fabc9ed98ea73d06e5d`. 0 mesh warnings.
  - Submitted meshes unchanged: library_v3, plus library_v3x for eval 8.
  - The carved collision copies (meshes/carve/ev25, ev10) are simulator-only.
- Made on box `20261026-pack4-f7a49a9` by `ops/jobs/pack_eval.sh`.
  - Code: https://github.com/aebatirel/v2d-track3/commit/f7a49a94bc08bb2140a7d7292a476cbeab9ace4e.
  - Pristine evaluator 8c778f9, 0 modified files.
  - Every packed rollout was sha256-checked against `checkpoints.json`: OK.
- **Re-evaluated:** one fresh official rollout each (rules fixed before the results; work log, 26 Oct).
  - **Eval 10:** carve s43 (hybrid cup collision copy, standard learner), 5-eval mean 0.452. The rule winner, s42,
    was unavailable: its chosen checkpoint had been pruned from the store.
  - **Eval 25:** carve s42 (board slot collision copy, standard learner), 5-eval mean 0.792.
  - **Eval 33:** frozen grasp lock, seed 43, 5-eval mean 0.785.
- **Kept:** pack 3's rollouts for 1, 6, 8, 14, 19, 20, 28, 30, 32 and 35–38. Pack 2's seed-43 rollouts for 3, 5, 15 and
  16, which restores the rule's choice (the pack-3 bug).
- `summary.txt`: our sim_vs_ref of the packed rollouts, mean **0.9121** (pack 3 0.883). Fresh draws: 10 0.447,
  25 0.894, 33 0.932. This is not the leaderboard score.
- **Uploaded by the agent to the five pose boards.** CD-O was not re-uploaded (same meshes).

| Board | Score | Rank (26 Oct ~11:00 UTC) | Before (pack 3) |
|---|---|---|---|
| AUC | **0.81056** | **5th** | 0.78893 (4th; DDD has since moved to 0.82716) |
| SP-SR | 0.85 | — | 0.80 |
| MP-SR | 0.65 | — | 0.60 |
| RPE | 4.03 cm | — | 4.59 cm |
| MPPE | 2.94 cm | — | 3.29 cm |

AUC board at 11:00 UTC:

| Rank | Team | AUC |
|---|---|---|
| 1 | richchentw | 0.932 |
| 2 | SoySauceChicken | 0.902 |
| 3 | Zihao Guo | 0.865 |
| 4 | DDD | 0.827 (03:36 UTC today) |
| 5 | **us** | **0.811** |
| 6 | SRL | 0.752 |
