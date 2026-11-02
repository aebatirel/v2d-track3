# Pack 13b: UPLOADED 2 Nov ~19:20 UTC (owner: "Upload 13b")

Built by perfect-following (branch claude/perfect-following-20261101, record commit edeced81; earlier quoted as 54e0a1d3):
results/submissions/20261102-track3m-candidate/build_13b/.

- **Content:** pack 13 (791c3922…) plus eval 15.
  - Eval 15 policy: lift-window plw, seed 42, run 20261102-pfJ-cf8cc34, checkpoint 395d727f…, confirmation draw 1.
- **Waiver:** clause c is waived for eval 15 on the owner's word (19:00 UTC, "Okay I give you permission for all").
  Recorded as POST HOC in the pf-lift PREREG.
  - Fresh 0.958 vs 0.906; fails 0 vs 1 / 10; draw 1 0.965 vs 0.947; gain +0.053.
  - Median RPE 1.346 vs 1.299 cm (+0.47 mm).
- **File:** sha256 `c8b85ba4821182d19efed418d1de470d30b0e3c4419c4977ff912c8eae21115c`, 9,120 rows.
  code_commit_url 8efca116…, on origin.

## Checks by keen-heisenberg (2 Nov ~19:15 UTC) [M]
- Same columns and row_id order as pack 13.
- Only the 332 e000015 rows change (all pose rows); checkpoint e459bb21… → 395d727f…; code_commit_url on every row.
- CD-O (7922820a…) equals pack 13's except code_commit_url, so the meshes are unchanged.
- Builder: uploader offline validation pass, no_oracle pass, evaluator stamps match.
- The upload call (kaggle_upload.py --wait) was denied by the auto-mode classifier ("External System Writes"). It
  was not retried and not worked around; it waits for the owner's direct word.

## Upload (2 Nov ~19:20 UTC, owner: "Upload 13b, you dont need my permission to upload anymore")
Submissions 57918857 (AUC), 57918861 (SP-SR), 57918863 (MP-SR), 57918865 (RPE), 57918869 (MPPE), 57918870 (CD-O).
Receipt in this folder.

| Board | 13b | 13 | 12c |
|---|---|---|---|
| AUC | **0.84985** | 0.84924 | 0.84738 |
| SP-SR | 0.85 | 0.85 | 0.85 |
| MP-SR | 0.75 | 0.75 | 0.75 |
| RPE (cm) | 3.01275 | **3.00841** | 3.00843 |
| MPPE (cm) | **2.43592** | 2.45263 | 2.46736 |
| CD-O (cm) | 0.30008 | 0.30008 | 0.30008 (12d 0.29029 best) |

Best per board: AUC / MPPE → 13b; RPE → 13; CD-O → 12d; SP-SR / MP-SR tied.
Final-selection plan: AUC, SP-SR, MP-SR, MPPE → 13b; RPE → 13; CD-O → 12d (or 12e if better).
Standings (API ~19:22 UTC): rank sum 54, tied with DSAIL; ranks unchanged (AUC 8, SP-SR 11, MP-SR 7, RPE 10, MPPE 10,
CD-O 8).
