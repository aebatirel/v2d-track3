# Pack 13e: UPLOADED 2 Nov ~19:35 UTC (keen-heisenberg; owner's standing upload permission)

Built by focused-pascal (claude/focused-pascal-2nz9s1, 76f66f65): 13b's poses + 12e's mesh payloads. sha256
0ea45fcd…, 9,120 rows, code b96170b9 (on origin).

## Checks by keen-heisenberg [M]
- vs 13b: code_commit_url + 16 object_mesh_b64 rows (pot 1 / 3 / 5 / 6 / 8 / 28, pitcher 20, rack 14 / 15 / 16 /
  28 / 30, sweeper 19 / 30, boards 25 × 2); nothing else.
- vs 12e: identical meshes; pose and checkpoint changes only on evals 15 / 20; code_commit_url.
- CD-O equals 12e's except code_commit_url.

## Upload
Submissions 57919442 (AUC), 57919443 (SP-SR), 57919449 (MP-SR), 57919450 (RPE), 57919452 (MPPE), 57919454 (CD-O).

| Board | 13e | 12e |
|---|---|---|
| AUC | **0.87166** | 0.86905 |
| SP-SR | 0.90 | 0.90 |
| MP-SR | 0.80 | 0.80 |
| RPE (cm) | 2.39478 | **2.39138** |
| MPPE (cm) | **1.92180** | 1.95269 |
| CD-O (cm) | 0.26775 | 0.26775 |

Best per board: AUC / MPPE 13e; RPE 12e (by 0.003 cm); the others tie. Ranks unchanged (rank sum 47, 7th).
