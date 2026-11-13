# Pack 13p2: UPLOADED 2 Nov ~22:20 UTC (keen-heisenberg; owner's standing upload permission)

Built by focused-pascal: 13p (3134dfc6…) + the eval 20 water_pitcher placed from depth. The fit is GT-free, on eval
20's stereo depth and SAM2 masks (perception-tracking @ 0b067405); the procedure was chosen by public pose CV
(held-out +0.106). sha256 19ac10e3…, 9,120 rows, code b0bd91fc (on origin).

## Checks by keen-heisenberg [M]
- vs 13p: code_commit_url + exactly 1 object_mesh_b64 row (e000020 o1).
- The CD-O file changes only t3m_000020_water_pitcher. D1 passes (builder).

## Upload
Submissions 57922817 (AUC), 57922822 (SP-SR), 57922825 (MP-SR), 57922826 (RPE), 57922828 (MPPE), 57922829 (CD-O).

| Board | 13p2 | 13p |
|---|---|---|
| AUC | **0.88403** | 0.88257 |
| SP-SR | 0.90 | 0.90 |
| MP-SR | 0.80 | 0.80 |
| RPE (cm) | **2.22531** | 2.22667 |
| MPPE (cm) | **1.80932** | 1.82356 |
| CD-O (cm) | 0.26869 | 0.26869 (13f 0.26249 best) |

AUC +0.0015, close to the predicted low end (+0.004–0.006 [E] was the range). Best on AUC / RPE / MPPE.
