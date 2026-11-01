# Pack 10 upload (1 Nov 2026, 08:38–08:43 UTC)

- **Authority.** The owner, directly in the keen-heisenberg session:
  - "I give you permission for everything" (02:50 UTC);
  - after the session's permission check blocked the first attempt, "Upload it" (08:38 UTC).
  - Uploaded by keen-heisenberg. focused-pascal built the pack and did not upload.
- **File.** `track3_submission.parquet` from `claude/focused-pascal-2nz9s1` (record 0e2d245f) at this path.
  - sha256 `e1bef1e5d7df3513ff9b0ddba19429c5933fe7baa4f05ea8807e245615fd0e2a`; 9,120 rows over 20 episodes.
  - Code commit URL a187a8c (on origin).
- **Content.** 9a+ (e02736ea…) with eval 10's rollout replaced by draw 1 of run 20261101-e10cs-50c2d90.
  - The policy is seed 43 (ca7c4e3a…), trained at stock limits (njmax 512 / nconmax 256) on the ev10cs5 cavity-safe
    collision pieces and e10v's V4p reference.
  - It is not the njmax-1024 diagnostic.
- **Checks run by the uploader before upload [M]:**
  - **Verdict** (`docs/research/work/eval10-cs4-20261101/results/verdict.txt`) against PREREG 13c4133 (05:40 UTC,
    before launch): SWAP-ELIGIBLE [EQUAL FLOOR], INCLUDE.
    - Gain over the packed policy: +0.069 vs V, +0.059 vs P; n 10 / 10; every clause holds on both references.
    - Seed choice by the rule: s43 0.5096 beats s42 0.4768.
  - **Byte diff against 9a+:**
    - only e000010's 322 pose rows and its checkpoint differ (76a12265 → ca7c4e3a);
    - code_commit_url changes on every row;
    - object_mesh_b64 is identical.
  - **Kit hashes** in the rows: eval 160d24f5…, eval code b1b3ebe3…, packer 49b13052…, uploader d31d4a7c….
  - **Stock limits:** cells.json shows njmax 512, and the confirmation draws logged 0 overflow lines.
  - **Dry run** valid (19 uploads left per board). The derived CD-O file equals the staged one.

**Scores** (Kaggle, all six boards, 08:43 UTC):

| Board | Pack 10 | 9a+ | 9b |
|---|---|---|---|
| AUC | **0.81915** (new best, +0.00158) | 0.81757 | 0.81677 |
| SP-SR | 0.80 (worse by one episode) | 0.85 | 0.85 |
| MP-SR | 0.65 | 0.65 | 0.65 |
| RPE | **3.68275 cm** (new best) | 3.87853 | 3.88283 |
| MPPE | **2.84759 cm** (new best) | 2.89663 | 2.90186 |
| CD-O | 0.33234 cm | 0.33234 | 0.33234 |

**Reading.**
- AUC moved +0.0016, against the +0.002 estimate [E]. RPE and MPPE improved by about 0.2 and 0.05 cm.
- SP-SR lost one of 20 episodes, and only eval 10 changed. [H] The old eval-10 policy counted as a success because
  the cup barely moved, while the new one moves the cup 10 cm without completing the nest.
- On a board-by-board best, SP-SR keeps 0.85 from earlier submissions.
