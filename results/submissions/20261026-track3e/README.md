# Track 3 submission, 26 Oct 2026 (fifth pack)

- `track3_submission.parquet`: 9,120 rows, 1,388,555 bytes, sha256
  `66551d2eb43b541771e8ae0ee50cc28c1bf7a1c15fd6d98ba55c685e240b6125`. 0 mesh warnings.
- Box `20261026-pack5-526918b`, code https://github.com/aebatirel/v2d-track3/commit/526918b (pristine evaluator
  8c778f9). Checkpoint check of all 20 rollouts: OK.
- **Changes vs pack 4** (rules fixed before results; work log, 26 Oct):
  - eval 10: gl10A2 (grasp lock on the carved cups, 5-eval mean 0.4539). Fresh rollout 0.456.
  - eval 32: frozen seed 46 (5-eval mean 0.803). Fresh rollout 0.866.
  - eval 20: same checkpoint and rollout; the submitted pitcher mesh is our lathe-completed reconstruction
    (`meshes/library_v3p`; twin ep21 registered 0.776 → 0.874 on stored rollouts).
- Our sim_vs_ref mean 0.9164 (pack 4 0.9121).

| Board | Score | Pack 4 |
|---|---|---|
| AUC | **0.80941** | 0.81056 |
| SP-SR | 0.85 | 0.85 |
| MP-SR | 0.65 | 0.65 |
| RPE | 4.01 cm | 4.03 cm |
| MPPE | 2.96 cm | 2.94 cm |

- The leaderboard keeps our best (0.81056, 5th).
- Evals 10 and 32 predict ≈ +0.003, so the pitcher mesh swap most likely cost ≈ −0.004 on eval 20. This is
  confounded; one submission cannot separate the effects. The twin result did not transfer.
