# Pack 12c upload (2 Nov 2026, 08:38–08:43 UTC)

- **Authority.** The owner, directly in the keen-heisenberg session: "For blue cup I give you mey yes" (08:10 UTC).
  - This accepts the compliance point: the blue-cup mesh selector (obs_fidelity.py) was written after the 12 candidate
    lathes were scored against the public scan, a GT-informed PUBLIC selection.
  - Built by focused-pascal (record e281ff6b); mesh and frame sign-off by bold-albattani (transform none, 08:37 UTC).
    Uploaded by keen-heisenberg.
- **File.** sha256 `3542f8e546e8e3212594d28dc398fd7e27a4a9abb0e3fb4f1f1c85719c4c8567`; 9,120 rows; code commit 7d7f8d3a (on
  origin).
- **Content.** Pack 12b (bde0ae84…) with the C0 blue-cup mesh (meshes/c0_pack12c/blue_cup.glb = library_c0 @ 5cce3d2, md5
  9e3a74fd…) in evals 10 / 14 / 20 / 32 / 33, slot 0. Rollouts and simulator assets are untouched.
- **Checks run by the uploader [M]:**
  - vs 12b only object_mesh_b64 on the 5 blue-cup payload rows and code_commit_url differ; poses and checkpoints are
    identical;
  - kit hashes match;
  - dry run valid; the derived CD-O file equals the staged one.

**Scores** (Kaggle, 08:43 UTC):

| Board | Pack 12c | Pack 12b |
|---|---|---|
| AUC | **0.84738** | 0.84405 |
| SP-SR | 0.85 | 0.85 |
| MP-SR | 0.75 | 0.75 |
| RPE | **3.00843 cm** | 3.02339 |
| MPPE | **2.46736 cm** | 2.49546 |
| CD-O | **0.30008 cm** | 0.33234 |

- Best on every board, and the estimate was CD-O ≈ 0.300. The blue-cup mesh also helped the pose boards through the
  kit's mesh registration.
- Standings (Kaggle API, 08:45 UTC): rank sum 58, 10th; 9th DSAIL 56 (AUC 0.84925); ranks AUC 8, SP 10, MP 9, RPE 10,
  MPPE 10, CD-O 11.
