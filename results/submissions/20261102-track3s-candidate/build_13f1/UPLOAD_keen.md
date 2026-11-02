# Pack 13f1 (= "13f2"): UPLOADED 2 Nov ~20:38 UTC (keen-heisenberg; owner's standing upload permission)

Built by focused-pascal (claude/focused-pascal-2nz9s1, 600061c1 / e90b653d): 13f with only eval 25 slot 1
(wooden_piece_2) reverted to library_v3; the payload is byte-identical to 12c's. Reason: the mesh-v5 D1 no-flip safety
gate. 13f's Tier B plate flips 179.2° at the eval seed against the raw public scan, and 2 / 10 seeds flip. sha256
c25abef2…, 9,120 rows, code e182f362 (on origin).

## Checks by keen-heisenberg [M]
- vs 13f: code_commit_url + exactly 1 object_mesh_b64 row (e000025 o1), equal to 12c's payload.
- The CD-O file changes only t3m_000025_wooden_piece_2.

## Upload
Submissions 57920845 (AUC), 57920846 (SP-SR), 57920850 (MP-SR), 57920851 (RPE), 57920853 (MPPE), 57920856 (CD-O).

| Board | 13f1 | 13f | Best so far |
|---|---|---|---|
| AUC | 0.87191 | **0.87225** | 13f |
| SP-SR | 0.90 | 0.90 | tie |
| MP-SR | 0.80 | 0.80 | tie |
| RPE (cm) | **2.37520** | 2.38260 | 13f1 |
| MPPE (cm) | 1.92513 | 1.92530 | 13e 1.92180 |
| CD-O (cm) | 0.26393 | **0.26249** | 13f |

## Reading
- The expected +0.02 AUC did not appear. [I] The hidden scorer's reference probably does not flip the Tier B plate
  (consistent with the budget-reference mode, where it registers at 1.05°).
- The revert was decided beforehand by the D1 safety gate. The leaderboard result is not used for later mesh choices,
  and D1 stays as a conservative veto in both reference modes.
- RPE improved slightly (new best); AUC −0.0003.
