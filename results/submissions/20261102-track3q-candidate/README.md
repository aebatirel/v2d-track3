# Track 3 pack-13e candidate, 2 Nov 2026 — pack 13b's poses + pack 12e's mesh payloads

**STATUS: READY. NOT uploaded from this session**: keen-heisenberg's session verifies and uploads on the owner's word
there. The mesh payloads are byte-identical to pack 12e's, which the mesh lane signed off (12d at 08:52, 12e at 19:15 UTC),
so no new frame sign-off was needed.

## Record
- File: `build_13e/track3_submission.parquet`, 9,120 rows, 1,272,315 bytes.
  sha256 `0ea45fcd22e369fd3e99c7ecec1ca9899495034004935b3f8cb2d08852c07ba1`.
- CD-O file: `build_13e/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `74137f15ff1112bb…`. It equals pack 12e's
  CD-O file in every column except `code_commit_url`.
- Code: https://github.com/aebatirel/v2d-track3/commit/b96170b9a539442fb13644d33f5e21c5d91afecb (on every row).
- Base: pack 13b (claude/perfect-following-20261101, `results/submissions/20261102-track3m-candidate/build_13b`, sha256
  c8b85ba4…) = 12c + the eval-15 and eval-20 lift-window rollouts.
  - **13b reproduced byte for byte** with the kit packer from 12c's packer inputs plus the two rollouts. Rollouts are from
    the store, `runs/20261102-pfJ-cf8cc34/results/pf_arms/conf_ep{15,20}_plw/r1`; their parquet and json sha256 match 13b's
    and 13's manifests. no_oracle accepts both.
- Built by tools/pack_swap_meshes.py with the guard on, on those inputs with 12c's meshes, swapping the six 12e
  replacement files:
  - Tier A: white_pot (meshes/tierA_pack12d).
  - Tier B: water_pitcher, mini_sweeper, plastic_dish_rack, wooden_piece_1 and wooden_piece_2 (meshes/tierB_pack12e).
  - `--only-episodes "white_pot:1,3,5,6,8,28;water_pitcher:20;mini_sweeper:19,30;plastic_dish_rack:14,15,16,28,30;wooden_piece_1:25;wooden_piece_2:25"`.

## Checks [M] (`build_13e/crosscheck.txt`, `build_13e/summary.txt`)
- **vs 13b:** only `code_commit_url` (all rows) and `object_mesh_b64` on 16 payload rows differ. That is exactly the row set
  where 12e's mesh payloads differ from 12c's (6 pot, 1 pitcher, 9 Tier B). Every other column equals 13b's.
- **vs 12e:** `object_mesh_b64` is identical on every row. Outside evals 15 and 20, only `code_commit_url` differs. In
  evals 15 and 20, the pose columns (735 rows) and `checkpoint_sha256` (736 rows) differ, i.e. 13b's rollouts.
- **CD-O:** equal to 12e's except `code_commit_url`.
- Offline validate_submission passes. 0 MESH WARNINGs.
- Frame flags as in 12d / 12e, on the same files and the same packed payloads. The pitcher is now reported against
  library_v3, the mesh it replaces in 13b: centroid 14.06 mm, ICP 9.48 mm / 3.38°, surface median 5.17 mm. The mesh lane's
  own check was 6.31 mm / 3.38° vs library_v3.

## Disclosures carried over
- **Eval 15 (from 13b):** included under the owner's post-hoc waiver of swap-rule clause c (median RPE +0.47 mm), recorded on
  claude/perfect-following-20261101.
- **Tier B meshes (from 12e):** ground truth entered the selection: the best of many candidates by CD-O against the public
  scans. For the sweeper, two construction rules were also changed after a scan comparison. The owner said yes in
  keen-heisenberg's session (19:00 UTC).
- **Wooden pieces (from 12e):** the plates are near 180°-symmetric; the eval seed does not flip [D], but 1 in 6 seeds does.
  CD-O is unaffected, and eval-25 pose is at risk.
- **Blue cup (from 12c):** GT-informed public selector.

## Expected [E]
- 12e measured AUC 0.86905, SP-SR 0.90, MP-SR 0.80, RPE 2.391, MPPE 1.953, CD-O 0.26775.
- 13e changes evals 15 and 20 the way 13 / 13b changed 12c: pack 13 measured AUC 0.84924 vs 12c 0.84738. CD-O should be
  unchanged at ≈ 0.2678.
