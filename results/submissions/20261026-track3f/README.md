# Track 3 submission, 26 Oct 2026 (sixth pack) — AUC 0.81391, our best

- `track3_submission.parquet`: 9,120 rows, 1,388,075 bytes, sha256
  `d59b6e63634bee584875f1c6a58a0715cd055da2b6899f535d8a0f5ee594fbb1`. 0 mesh warnings.
- Box `20261026-pack6-5203d42`, code https://github.com/aebatirel/v2d-track3/commit/5203d42.
- **Content:** pack 5's 20 official rollouts, all kept (checkpoint check OK). Eval 20's submitted pitcher mesh is
  reverted to library_v3 (owner decision after pack 5); meshes are library_v3, plus v3x for eval 8.
- Our sim_vs_ref mean 0.9164.

| Board | Pack 6 | Pack 5 | Pack 4 |
|---|---|---|---|
| AUC | **0.81391** | 0.80941 | 0.81056 |
| SP-SR | 0.85 | 0.85 | 0.85 |
| MP-SR | 0.65 | 0.65 | 0.65 |
| RPE | 3.94 cm | 4.01 cm | 4.03 cm |
| MPPE | 2.92 cm | 2.96 cm | 2.94 cm |

Pack 6 vs pack 5 differ only in eval 20's submitted mesh, so the lathe pitcher cost 0.0045 AUC (measured).
