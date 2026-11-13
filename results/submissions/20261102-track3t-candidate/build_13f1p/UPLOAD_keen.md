# Pack 13p (= 13f1p): UPLOADED 2 Nov ~21:55 UTC (keen-heisenberg; owner's standing upload permission)

Built by focused-pascal (claude/focused-pascal-2nz9s1, 5d97c898) on 13f1: pose-board meshes chosen by
perception-tracking's pre-registered public-pose leave-one-episode-out test (PREREG_posemesh + addendum 1 @ 029145e).
- TSDF white pot (3591440e…) on evals 1 / 3 / 5 / 6 / 8 / 28;
- library_c0 rack (= 12c payloads) on evals 14 / 15 / 16 / 28 / 30.

D1 passes in both reference modes. sha256 3134dfc6…, 9,120 rows, code 116dfe70 (on origin).

## Checks by keen-heisenberg [M]
- vs 13f1: code_commit_url + exactly 11 object_mesh_b64 rows; the rack rows equal 12c's byte for byte.
- The CD-O file changes exactly those 11 pairs.

## Upload
Submissions 57922330 (AUC), 57922331 (SP-SR), 57922335 (MP-SR), 57922337 (RPE), 57922339 (MPPE), 57922340 (CD-O).

| Board | 13p | Previous best |
|---|---|---|
| AUC | **0.88257** | 0.87225 (13f) |
| SP-SR | 0.90 | 0.90 |
| MP-SR | 0.80 | 0.80 |
| RPE (cm) | **2.22667** | 2.37520 (13f1) |
| MPPE (cm) | **1.82356** | 1.92180 (13e) |
| CD-O (cm) | 0.26869 | **0.26249** (13f keeps it) |

- The public-pose CV choice transferred to eval: public held-out estimate pot +0.021 / rack +0.023 per object
  episode; board AUC +0.010.
- Standings (API ~21:57 UTC): **rank sum 46, 7th**; RPE 9th → 8th. Ranks: AUC 7, SP-SR 10, MP-SR 7, RPE 8, MPPE 8,
  CD-O 6.
