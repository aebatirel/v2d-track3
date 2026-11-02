# Track 3 pack-12e candidate, 2 Nov 2026 — pack 12d + Tier B meshes (GT-informed selection; CD-O-only variant)

**STATUS: PENDING frame sign-off. Not ready, not uploaded.** The frame report flagged all five meshes. The mesh lane
(bold-albattani) must sign off on these exact files and transforms before this is published as ready. keen-heisenberg's
session uploads, on the owner's word there.

**Disclosure: ground truth entered the mesh selection.**
- Every Tier B mesh was chosen as the best of many candidates by its CD-O against the organisers' public object scans.
  Those scans are ground-truth geometry of the same physical objects that appear in the eval episodes.
- The sweeper's part program also had two construction rules changed after a comparison with the scan.
- No mesh was built from or copies a scan. tools/no_oracle.py accepts all five files (md5 and sha256 checks against the
  scan denylist).
- No eval episode was scored or used for tuning. Rollouts are unchanged.
- The owner approved this tier ("Okay I give you permission for all", in keen-heisenberg's session, relayed 19:00 UTC).
  The same qualifier applies to the 12c blue cup.

## Record
- File: `build_12e/track3_submission.parquet`, 9,120 rows, 1,272,452 bytes.
  sha256 `004f394f845d1d4d488bc2cf1778f81e7e92177b1881a83da64022445121babd`.
- CD-O file: `build_12e/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `36cce78b1b2d765c…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/9684395b077c2538b127f874070896e2976f9c31 (on every row).
- Base: pack 12d (`results/submissions/20261102-track3o-candidate/build_12d`, sha256 643794c6…), first reproduced byte for
  byte from its inputs. Built by tools/pack_swap_meshes.py with the guard on (no skip):
  `--only-episodes "water_pitcher:20;mini_sweeper:19,30;plastic_dish_rack:14,15,16,28,30;wooden_piece_1:25;wooden_piece_2:25"`.

## Content
- Against 12d, only `code_commit_url` (all rows) and `object_mesh_b64` on 10 payload rows differ:
  - plastic_dish_rack on 14/o1, 15/o0, 16/o0, 28/o0, 30/o1;
  - mini_sweeper on 19/o0, 30/o0;
  - water_pitcher on 20/o1;
  - wooden_piece_1 on 25/o0 and wooden_piece_2 on 25/o1.
- CD-O rows change for exactly those 10 pairs. Offline validate_submission passes. 0 MESH WARNINGs.
- Every payload decodes with the kit's decoder at the 4,096-row budget. The 400k-face pitcher is cut by the kit's
  budget_mesh (fast_simplification 0.2.0).
- Meshes: `meshes/tierB_pack12e/` (see its README). They are byte copies of bold-albattani's
  C3/tierB/meshes at 332eb5b. Transform none.

## Frame report [M] (base = the mesh being replaced; pack_swap_meshes.py)
| Object | Base | Centroid | AABB centre | Surface median / p95 / max | ICP | Kit proxy | Flags |
|---|---|---|---|---|---|---|---|
| plastic_dish_rack | C0 bbca8ec0 | 5.78 | 9.0 | 3.12 / 8.63 / 18.55 | 6.24 mm / 1.12° | 5.84 mm / 1.31° | centroid, ICP, proxy |
| mini_sweeper | library_v3 c126a8ff | 5.23 | 9.76 | 2.67 / 7.63 / 15.34 | 4.3 mm / 2.67° | 5.18 mm / 2.77° | centroid, proxy |
| water_pitcher | 12d T3 fit 61503a91 | 21.91 | 25.8 | 5.12 / 22.05 / 34.99 | 14.86 mm / 3.29° | 17.3 mm / 4.41° | centroid, ICP, surface median, proxy |
| wooden_piece_1 | library_v3 d152b2b5 | 3.02 | 13.2 | 1.96 / 7.25 / 20.67 | 3.85 mm / 0.68° | 3.63 mm / 0.87° | extent ratio 0.65 (thin axis 30.5 → 19.9 mm) |
| wooden_piece_2 | library_v3 825a7fe3 | 5.3 | 8.73 | 1.62 / 4.28 / 19.20 | 2.46 mm / 0.72° | 2.73 mm / **179.9°** | centroid, **proxy flip**, extent ratio 0.71 |

All distances are in mm.

## Known risks (mesh lane, C3/tierB README @ 332eb5b)
- **Pose boards:**
  - The pitcher and sweeper improve on 12d in the kit-registration anchor error [D]: pitcher 29.4 → 14.5 mm.
  - The wooden pieces are slightly worse.
  - The rack is clearly worse (about 9 mm vs about 3 mm), so the rack pairs' pose scores will probably drop.
  - The kit proxy flips wooden_piece_2 by 180°. The mesh lane saw 1 flip in 6 seeds, on an extra seed, not the eval seed.
- Each board keeps its best submission, so this is a CD-O-only variant.
- **Expected CD-O [E]:** 12d about 0.290 → 12e about 0.268 (Tier B −0.0225).
