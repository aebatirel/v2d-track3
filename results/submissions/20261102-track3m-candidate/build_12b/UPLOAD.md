# Pack 12b upload (2 Nov 2026, 06:37–06:42 UTC)

- **Authority.** The owner, directly in the keen-heisenberg session:
  - "Is 12b ready what are we waiting for?" (06:36 UTC);
  - standing permission "I give you permission for everything" (1 Nov).
  - Built by the perfect-following session (record 79ffe371); uploaded by keen-heisenberg.
- **File.** sha256 `bde0ae84ccdaf442459308f0f806365cc79105e2f4af0b676c05103c14b0a0e1`; 9,120 rows; code commit fa129a11 (on
  origin).
- **Content.** Pack 11 (3c428350…) with three eval episodes swapped, each the confirmation draw 1 of a retrain with the
  packed recipe at stock limits 512 / 256 (KURSAD reference repairs, GT-free):
  - eval 14: the perception track-guard drift bridged (tools/guard_bridge.py). Run 20261101-pfC, ck 9da879d9…;
  - eval 32: the same repair. Run 20261101-pfD, ck 9a2c2f7c…;
  - eval 16: the robot's right hand held on the spoon from release (f107) to the end (tools/hold_freeze.py). Run
    20261102-pfG, ck ed25dc5f….
- **Checks run by the uploader before upload [M]:**
  - byte diff vs pack 11: only e000014 (316), e000016 (346) and e000032 (518) pose rows and checkpoints differ, plus
    code_commit_url; meshes identical;
  - kit hashes match;
  - PREREGs (pf-bridge 20:46 UTC; pf-release PREREG_B 02:06 UTC) committed before the results;
  - verdicts PASS + INCLUDE: eval 14 +0.169 (B), eval 32 +0.040 (B), eval 16 +0.124 (P);
  - no_oracle passes, so all checkpoints are stock 512 / 256;
  - dry run valid; the derived CD-O file equals the staged one.

**Scores** (Kaggle, 06:42 UTC):

| Board | Pack 12b | Pack 11 |
|---|---|---|
| AUC | **0.84405** (+0.00484) | 0.83921 |
| SP-SR | 0.85 | 0.85 |
| MP-SR | **0.75** | 0.70 |
| RPE | **3.02339 cm** | 3.17899 |
| MPPE | **2.49546 cm** | 2.54531 |
| CD-O | 0.33234 cm | 0.33234 |

Pack 12b is our best on every board.
