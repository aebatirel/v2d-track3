# Track 3 pack-13f1 candidate, 2 Nov 2026 — pack 13f with eval 25's wooden_piece_2 reverted to library_v3 (flip fix)

**STATUS: READY. NOT uploaded from this session**: keen-heisenberg's session verifies and uploads on the owner's word
there. The reverted payload is byte-identical to the one in packs 9a+ to 12d, which was already on the boards.

**Why.** The 12e/13f wooden_piece_2 payload registers to the public scan **upside down at eval 25's kit seed**. Rotation
is 179.2° with a 179.1° tilt, against 0.7° for library_v3 [D]. Reported by tracking-perception at 20:23 UTC and confirmed
here: docs/research/work/flipcheck-20261102/. If the hidden scan behaves like the public one, eval 25's piece-2 poses are
scored upside down in 12e/13f. tracking-perception measured public ep24 piece-2 AUC 0.862 → 0.000 with that mesh.

## Record
- File: `build_13f1/track3_submission.parquet`, 9,120 rows, 1,321,475 bytes.
  sha256 `c25abef27d2e9dfd521f009f349321bd698391caec4a1ec6c727046d0028cb12`.
- CD-O file: `build_13f1/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `89c921acd5285657…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/e182f362bcfc7fc7d402515fca8a9b3522f76646 (on every row; it holds the
  flip-check scripts).
- Base: pack 13f (`results/submissions/20261102-track3r-candidate/build_13f`, fa1e31f5…), built from 13f's own packer
  inputs. Built by tools/pack_swap_meshes.py with the guard on: `--only-episodes "wooden_piece_2:25"`, replacement
  meshes/library_v3/wooden_piece_2.glb (md5 825a7fe3…).

## Checks [M] (`build_13f1/crosscheck.txt`)
- vs 13f: only `code_commit_url` (all rows) and `object_mesh_b64` on 1 row (eval 25 slot 1) differ.
- That payload equals 12c's eval-25 slot-1 payload byte for byte (library_v3).
- CD-O changes only that pair's points. Offline validate_submission passes. 0 MESH WARNINGs.
- Frame flags in summary.txt (centroid 5.3 mm, proxy 179.7°, extents) compare library_v3 against the flipped Tier B plate
  it replaces, so they show the same flip from the other side. Against the public scan, the reverted payload registers at
  0.7° [D] (`docs/research/work/flipcheck-20261102/results/flipall_13f1.json`). Every other pair is as in 13f.

## Expected [E]
- CD-O: eval 25 slot 1 goes 0.1642 → 0.2158 [D], so about +0.0014 on the board vs 13f.
- Pose boards: eval-25 piece 2 is no longer flipped, about +0.02 AUC (tracking-perception's estimate), if the hidden scan
  flips as the public one does.
- Each board keeps its best submission, so 13f stays the CD-O submission if it scores better there.
- All of 13f's disclosures carry over (Tier B / B+ GT-informed selection, eval-15 clause-c waiver, 12c blue-cup selector).
