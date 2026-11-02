# Pack 13: verification record (not uploaded; waits for the owner's word)

Built by perfect-following (branch claude/perfect-following-20261101, commit 6291a766):
results/submissions/20261102-track3m-candidate/build_13/.

- **Content:** pack 12c (3542f8e5…) plus eval 20.
  - Eval 20 policy: lift-window grasp-lock arm plw, seed 43, run 20261102-pfJ-cf8cc34, checkpoint 1e08b92f….
- **File:** sha256 `791c3922fffd15f3d63657c3a34bf5e0ee971ec6158f5d2b5e5db2580defb094`, 9,120 rows.
  code_commit_url b45b377b…, which is on origin (claude/perfect-following-20261101).

## Checks by keen-heisenberg (2 Nov ~17:50 UTC) [M]
- Rows 9,120; same columns and row_id order as 12c.
- Pose columns change only on the 404 e000020 rows (403 changed); checkpoint_sha256 changes only there
  (61dcd7a6… → 1e08b92f…); code_commit_url changes on every row (new commit).
- CD-O: the pack's file (d55cc9f6…) equals the dry run's derived file row for row. It also equals the CD-O uploaded
  with 12c (staged 116a9751…) except code_commit_url. So the meshes are unchanged and CD-O is expected to equal 12c's.
- Kit: uploader d31d4a7c…, packer 49b13052…, as for 12b / 12c. Uploader offline validation passes (builder), and the
  dry run here is valid ("looks valid", 6 boards, nothing submitted).
- Swap verdict (verdict_ep20_plw.json, pack-9b PREREG §4 + addendum B, cf8cc347 at 12:48 UTC, before pfJ launched):
  - fresh 10 draws 0.9259 ± 0.018 vs packed 0.8933; 0 fails each;
  - median RPE 1.378 vs 1.671 cm;
  - draw 1 0.938 vs the board row's 0.895;
  - gain +0.0326 ≥ +0.02 → PASS + INCLUDE.
  - Box seed 43 0.921 vs fresh 0.926, so the box-overstates pattern of eval 14 is absent here.
- Stock limits / no_oracle: pass (builder). This is not an njmax-1024 policy.

## Expectation [E]
Small: one episode, about +0.002 on the 20-episode sim_vs_ref mean. The effect against GT is unknown.

## Not included: eval 15
Eval 15 is a near miss and is NO-SWAP under the rule. A waiver is the owner's call.
- Fresh 0.958 vs 0.906; 0 fails vs 1 / 10.
- It fails clause c only: median RPE 1.346 vs 1.299 cm, i.e. 0.47 mm worse.
