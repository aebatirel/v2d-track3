# Pack 11 upload (1 Nov 2026, 11:39–11:44 UTC)

- **Authority.** The owner, directly:
  - in keen-heisenberg: "I give give you go" (09:11 UTC), to pack the njmax-1024-trained eval-10 policy evaluated at
    stock limits;
  - in focused-pascal's session: approval of the single sha-specific guard exception.
  - Uploaded by keen-heisenberg; built by focused-pascal (record 34f4279d).
- **File.** sha256 `3c428350ec8a3558ec39d8f2072236704e4c52d0538c80ebef125fcb26c055ec`; 9,120 rows; code commit 5031231
  (on origin).
- **Content.** Pack 10 (e1bef1e5…) with eval 10 replaced by conf512 draw 1 of run 20261101-e10nj-451b82d.
  - Checkpoint ck512, aaa077eb….
  - **Disclosure:** trained with njmax 1024 / nconmax 512 (training-only); evaluated at stock 512 / 256.
- **Checks run by the uploader [M]:**
  - **Byte diff against pack 10:** only e000010's 322 pose rows and its checkpoint differ (ca7c4e3a → aaa077eb);
    code_commit_url changes on every row; meshes and kit hashes are identical.
  - **Stock limits.** checks.json shows the stored config at sim / env.sim njmax 512, and solver_build_ck512 built
    njmax 512 on the pristine tree.
  - **Verdict** (amendment 998385b0, committed before scoring; it states the values were already seen):
    - INCLUDE: +0.371 (V) / +0.361 (P);
    - fail rate 0 / 10 vs 10 / 10;
    - every clause holds.
  - Dry run valid (18 uploads left per board). The derived CD-O file equals the staged one.

**Scores** (Kaggle, 11:44 UTC):

| Board | Pack 11 | Pack 10 | 9a+ |
|---|---|---|---|
| AUC | **0.83921** (+0.020) | 0.81915 | 0.81757 |
| SP-SR | 0.85 | 0.80 | 0.85 |
| MP-SR | **0.70** | 0.65 | 0.65 |
| RPE | **3.17899 cm** | 3.68275 | 3.87853 |
| MPPE | **2.54531 cm** | 2.84759 | 2.89663 |
| CD-O | 0.33234 cm | 0.33234 | 0.33234 |

**Reading.**
- One episode, eval 10, moved AUC by +0.020. The proxy gain of +0.37 transferred: [E] +0.015 was expected.
- SP-SR is back to 0.85, and MP-SR gained one episode.
