# Track 3 pack-12c candidate, 2 Nov 2026 — pack 12b + the C0 blue-cup mesh payloads

**STATUS: READY (2 Nov 2026 ~09:00 UTC). NOT UPLOADED from this session.** The frame report flagged the blue cup
(below). The mesh lane (bold-albattani) signed off at 08:37 UTC on this exact file, with transform NONE and no translation
correction (details below). The owner's word decides the upload, in the session where it is given (keen-heisenberg).

## Record
- File: `build_12c/track3_submission.parquet`, 9,120 rows, 1,313,130 bytes.
  sha256 `3542f8e546e8e3212594d28dc398fd7e27a4a9abb0e3fb4f1f1c85719c4c8567`.
- CD-O file derived by the uploader's offline step: `build_12c/track3_submission.cd-o.parquet`, 294,912 rows,
  sha256 `116a97512432d518…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/7d7f8d3abf13ec1822cf54b67fd06cb6cf1337c9 (on every row).
- Base: pack 12b (`results/submissions/20261102-track3m-candidate/build_12b/` on claude/perfect-following-20261101,
  sha256 bde0ae84…).
  - First reproduced BYTE FOR BYTE with tools/pack_swap_rollouts.py. Inputs: pack 11's packer inputs plus 12/12b's swapped
    rollouts (pfC ep14, pfD ep32, pfG ep16), 12b's commit URL, and a packing venv with pandas 3.0.5.
  - Then tools/pack_swap_meshes.py ran on those inputs with `--replace` = meshes/c0_pack12c (blue_cup only).

## Content
- Rollouts and simulator assets are untouched. Against 12b, only `code_commit_url` (all rows) and `object_mesh_b64` on the
  5 blue_cup payload rows differ (evals 10, 14, 20, 32, 33, slot 0: every roster episode with a blue cup).
- Mesh: `meshes/c0_pack12c/blue_cup.glb`, a byte copy of bold-albattani's `meshes/library_c0/blue_cup.glb` at 5cce3d2
  (md5 9e3a74fd…, 557,540 B). Transform none.
- CD-O rows change for exactly those 5 pairs. Offline validate_submission passes. 0 MESH WARNINGs.

## Frame report (blue cup = axial symmetry) [M]
- centroid offset 3.53 mm; AABB centre offset 8.21 mm.
- extent base [95.08, 96.47, 167.02] vs new [92.95, 103.61, 167.27] mm.
- surface distance median / p95 / max: 2.58 / 8.51 / 34.33 mm.
- **FLAG:** ICP correction 6.64 mm / 2.55° (limits 5 mm / 5°).
- **FLAG:** kit-registration proxy moves the body 9.91 mm (limit 5 mm).
- The mesh lane's own check: axis tilt 1.24°, axis offset 2.0 mm, closed end +z, no flip.

## Frame sign-off (bold-albattani, 08:37 UTC 2 Nov) — YES, transform NONE, evals 10/14/20/32/33 slot 0
- **The flags measure distance to library_v3, which is itself off the true shape** [D].
  - Setup: the kit's own registration (pipeline/score_registered.py → the kit's _register_object_body), with the public
    scan standing in for the confidential one, over the same 5 eval-pair seeds.
  - Error at the scan's anchor point: library_v3 blue_cup 9.1 / 10.0 / 9.8 / 10.4 / 10.1 mm; C0 2.9 / 3.1 / 3.5 / 2.1 / 3.6 mm.
  - The 6.6 mm ICP and 9.9 mm kit-proxy moves are about library_v3's own ~10 mm error. A correction toward library_v3
    would push C0 back toward that error.
- **CD-O and the pose scorers register the submitted mesh to the scan before scoring.** A body-frame translation is absorbed.
  - Registration converges: 0 of 5 flips for both meshes.
  - Rotation error after registration: C0 2.4–2.7°, library_v3 0.7–2.0°.
- **Every measurement was at identity:** CD-O 0.523 → 0.291 cm [D]; incremental AUC guard on 9a+ public twins, mean
  dAUC +0.022, min −0.030 (ep13). A transform would be an untested configuration.
- **Caveats:**
  - the [D] numbers assume the public scan matches the confidential one;
  - the pose boards can move either way (ep13 −0.03 AUC);
  - rotation registers ~1° worse than library_v3;
  - each board keeps its best submission.

## Disclosure
- The selector that picked this lathe (obs_fidelity.py) was written after the 12 blue-cup lathes were scored against
  the public scan. This is GT-informed public selection.
- The owner accepted it on 2 Nov 2026 at 08:10 UTC (relayed by keen-heisenberg).
- Expected effect [E]: CD-O ≈ 0.332 → 0.300 (the public minimal-variant estimate: 0.523 → 0.291). The pose boards may
  move either way: the kit proxy shifts the body ~1 cm on these 5 episodes.
