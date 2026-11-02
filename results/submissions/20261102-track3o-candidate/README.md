# Track 3 pack-12d candidate, 2 Nov 2026 — pack 12c + Tier A white pot and water pitcher meshes

**STATUS: READY (frame sign-off YES, ~08:55 UTC). NOT uploaded from this session**: keen-heisenberg's session verifies
and uploads on the owner's word there. Pack 12c stays on the boards as the fallback.

**Disclosure, as the mesh lane worded it:** "Pose boards expected worse than 12c on evals 1, 3, 5, 6, 8, 20, 28 [D:
kit-registration anchor error pot 5.5 vs 2.8 mm, pitcher 29 vs 6 mm]; CD-O-only variant. Expected CD-O about 0.290 [E]."
Each board keeps its best submission, so 12c stays the pose-board submission.

## Record
- File: `build_12d/track3_submission.parquet`, 9,120 rows, 1,264,400 bytes.
  sha256 `643794c6ec96ec5f31f74edcf4fe379b77ef9e63a3cffb63bd7387b2633c0b12`.
- CD-O file: `build_12d/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `1d3006d43f403d3b…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/91342da4b0e584a7f1b2d6d59ad96d29e123dc6e (on every row).
- Base: pack 12c (`results/submissions/20261102-track3n-candidate/build_12c`, sha256 3542f8e5…), first reproduced byte for
  byte from its inputs. Built by tools/pack_swap_meshes.py, `--only-episodes "white_pot:1,3,5,6,8,28;water_pitcher:20"`.

## Content
- Rollouts and simulator assets are untouched. Against 12c, only `code_commit_url` (all rows) and `object_mesh_b64` on 7
  payload rows differ: white_pot on evals 1, 3, 5, 6, 8, 28 and water_pitcher on eval 20 (slot 1).
- CD-O rows change for exactly those 7 pairs. Offline validate_submission passes. 0 MESH WARNINGs.
- Meshes: `meshes/tierA_pack12d/` (see its README), byte copies of bold-albattani's C1 T3 generate-then-fit outputs at
  25b0c54. These are the single pre-registered outputs (PREREG 2d2a8ee pushed before scoring); Tier A, clean. Transform
  none. Tier B (GT-informed) is not used.

## Frame report [M] (base = the mesh being replaced)
- **white_pot** (base C0 0264da83):
  - centroid 8.52 mm (**FLAG**); AABB centre 14.74 mm;
  - surface median / p95 / max 1.67 / 8.02 / 21.07 mm;
  - ICP 3.1 mm / 2.22°; kit proxy 5.7 mm / 1.58° (**FLAG**).
- **water_pitcher** (base library_v3):
  - centroid 10.27 mm (**FLAG**); AABB centre 34.37 mm;
  - surface median / p95 / max 4.26 / 25.51 / 49.66 mm;
  - ICP 5.83 mm / 3.46° (**FLAG**); kit proxy 7.95 mm / 3.69° (**FLAG**).

## Known risks (mesh lane, C3 README)
- **white_pot:** T3 CD-O gate WIN; pose guard FAILED (mean dAUC −0.0099, min −0.042 on ep45).
- **water_pitcher:** CD-O ok; ADD FAILED (add_med 33.0 mm), so pose boards on eval 20 are at risk.
- Each board keeps its best submission.
- Expected CD-O ≈ 0.300 → 0.290 [E].

## Frame sign-off (bold-albattani, 08:52 UTC message)
- **YES for both, transform NONE, no correction**, on white_pot_t3fit.glb (md5 b19b2e2876945cba4d932ad531f049ce, evals
  1/3/5/6/8/28) and water_pitcher_t3fit.glb (md5 61503a91d787ed0643ef40699805d1d0, eval 20 slot 1). The packer's
  replacement files have these md5s (`build_12d/swap_manifest.json`, `replacement_files`), and so do the committed copies
  in `meshes/tierA_pack12d/`.
- Their reasons:
  1. The scorer registers each submitted mesh to the scan, so CD-O does not depend on the body frame. Their [D] CD-O was
     scored at identity: pot 0.3417 → 0.3112, pitcher 0.8942 → 0.7226. A transform would be untested.
  2. The centroid / AABB / kit-proxy flags are shape differences (handles, spout, extents). Their ICP: pot 1.65 mm / 0.53°,
     pitcher 2.76 mm / 2.15°. Mine: 3.1 mm / 2.2° and 5.8 mm / 3.5°; the sampling differs.
  3. Pose: kit registration to the public scan [D], anchor error per eval seed: pot T3 5.3–5.6 mm vs C0 2.5–3.1 mm (rot
     2.6–3.8°); pitcher T3 29.4 mm vs library_v3 6.3 mm (rot 8.0°). The pitcher's error comes from registration sliding on
     the spout and handle. A 3–6 mm body-frame shift would not remove it.
