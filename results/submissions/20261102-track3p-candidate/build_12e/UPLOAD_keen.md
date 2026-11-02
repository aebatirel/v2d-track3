# Pack 12e: UPLOADED 2 Nov ~19:25 UTC (keen-heisenberg; owner yes to Tier B at 19:00, standing upload permission at 19:20)

Built by focused-pascal (claude/focused-pascal-2nz9s1, aeb12740): pack 12d + Tier B meshes (bold-albattani 332eb5b,
GT-informed selection by public-scan CD-O, disclosed in its README). sha256 004f394f…, 9,120 rows, code 9684395b (on
origin).

## Checks by keen-heisenberg [M]
- Same columns and row_id order as 12d.
- Changes: code_commit_url on every row, plus object_mesh_b64 on exactly 10 rows (rack 14 / 15 / 16 / 28 / 30,
  sweeper 19 / 30, pitcher 20, wooden pieces 25 × 2). No pose row changed.
- CD-O file (36cce78b…): only those 10 object pairs change; row_id order is identical.

## Upload
Submissions 57919161 (AUC), 57919162 (SP-SR), 57919164 (MP-SR), 57919170 (RPE), 57919171 (MPPE), 57919177 (CD-O).

| Board | 12e | Previous best |
|---|---|---|
| AUC | **0.86905** | 0.84985 (13b) |
| SP-SR | **0.90** | 0.85 |
| MP-SR | **0.80** | 0.75 |
| RPE (cm) | **2.39138** | 3.00841 (13) |
| MPPE (cm) | **1.95269** | 2.43592 (13b) |
| CD-O (cm) | **0.26775** | 0.29029 (12d) |

- Best on every board. The meshes moved the pose boards far more than expected [M].
- Reading [I]: the registered scorer aligns our mesh to the true one, so mesh shape drives the pose errors.
- Standings (API ~19:27 UTC): **rank sum 47, 7th** (was 54, tied 9th / 10th). Board ranks: AUC 7, SP-SR 10, MP-SR 7,
  RPE 9, MPPE 8, CD-O 6.
