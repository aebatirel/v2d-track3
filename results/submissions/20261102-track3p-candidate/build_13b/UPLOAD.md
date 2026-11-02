# Pack 13b: verification record (not uploaded; the upload call was blocked by this session's permission classifier)

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
