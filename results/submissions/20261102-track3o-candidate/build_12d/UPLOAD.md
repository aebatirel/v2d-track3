# Pack 12d upload (2 Nov 2026, 12:42–12:47 UTC): CD-O-only variant

- **Authority.** The owner, directly in the keen-heisenberg session: "sure go ahead" (12:41 UTC), in reply to "upload pack
  12d". Built by focused-pascal (beee0581); frame sign-off by bold-albattani. Uploaded by keen-heisenberg.
- **File.** sha256 `643794c6ec96ec5f31f74edcf4fe379b77ef9e63a3cffb63bd7387b2633c0b12`; 9,120 rows; code commit 91342da4.
- **Content.** Pack 12c with the pre-registered T3 meshes (PREREG 2d2a8ee): white_pot on evals 1 / 3 / 5 / 6 / 8 / 28 and
  water_pitcher on eval 20. Rollouts are identical to 12c.
- **Checks [M].** vs 12c only 7 object_mesh_b64 payload rows and code_commit_url differ; kit hashes match; dry run
  valid; CD-O file equal to the staged one.

**Scores** (Kaggle, 12:47 UTC):

| Board | Pack 12d | Pack 12c |
|---|---|---|
| AUC | 0.84005 | **0.84738** |
| SP-SR | 0.85 | 0.85 |
| MP-SR | 0.75 | 0.75 |
| RPE | 3.14219 cm | **3.00843** |
| MPPE | 2.52460 cm | **2.46736** |
| CD-O | **0.29029 cm** | 0.30008 |

- As expected, CD-O improves and the pose boards get worse (disclosed in the build README). Each board keeps our best,
  so 12c counts for the pose boards and 12d for CD-O.
- At the final selection: 12c for AUC / SP-SR / MP-SR / RPE / MPPE, 12d for CD-O. The rollouts are identical, so the
  container re-run is the same.
