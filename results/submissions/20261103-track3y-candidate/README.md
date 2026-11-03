# Track 3 pack-13j candidate, 3 Nov 2026 — CD-O variant on 13i with the round-R rack

**STATUS: READY (frame sign-off YES, transform none, 10:29 UTC). NOT uploaded from this session**: keen-heisenberg's
session verifies and uploads on the owner's word there. Provisional: 90 GT-free primitive refits are still in the rack audit
(about 1.5 h). A lower qualifying one would come as a 13j2.

**This is a CD-O-only variant** on 13i (board CD-O 0.24177 [M], per the mesh lane).

**Disclosure: GT-informed selection** (as for G2 / G3; meshes/r_pack13j/README.md).
- Picked from rack round R: 390 generated racks from SAM 3D, Hunyuan3D-2.1, TRELLIS.2 and Pixal3D-MV, on GT-free crops of
  public episodes not used before.
- Selection ran:
  1. a 6-seed public-scan CD-O screen;
  2. the top 6, as placed, t3fit, trim and outer copies;
  3. a frozen 50-seed audit;
  4. pre-registered rules A / B / C plus the D1 veto (C4 PREREG sections 3, 9, 13 and 14).
- No scan geometry, no scan copy or template, no leaderboard input.
- All of 13i's disclosures carry over: G3 / G2 / Tier B / B+ selection, the 13f eval-25 plate, the eval-15 clause-c waiver,
  the 12c blue-cup selector. The 13h rack's bulge defect leaves with this swap.

## Record
- File: `build_13j/track3_submission.parquet`, 9,120 rows, 1,285,551 bytes.
  sha256 `7e8704373085930f868f81f9f6aac57b21bf7f150fe2b0fb3a1b3ffdd078b4ea`.
- CD-O file: `build_13j/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `8b44cd09b758ceef…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/3a933d1dc2b63696572b0e3f211ca81bd58c1ad6 (on every row).
- Base: pack 13i (`results/submissions/20261103-track3w-candidate/build_13i`, 1bcbdcfa…), reproduced byte for byte from its
  packer inputs first. Built by tools/pack_swap_meshes.py with the guard on,
  `--only-episodes "plastic_dish_rack:14,15,16,28,30"`.
- Mesh: `meshes/r_pack13j/plastic_dish_rack.glb`, md5 1882b7a2…, replacing the G2 rack a289d009. Transform none.

## Checks [M]
- vs 13i: only `code_commit_url` (all rows) and `object_mesh_b64` on 5 payload rows differ: 14 o1, 15 o0, 16 o0, 28 o0,
  30 o1.
- CD-O changes exactly those 5 pairs. Offline validate_submission passes. 0 MESH WARNINGs.
- **D1 PASS in both reference modes** [D] (d1pairs.py on the packed bytes; eval seed + 6): 0/7 flips on all 5 pairs.
  - Raw scan: rot ≤ 2.5°, anchor 2.7–3.4 mm.
  - Budgeted scan: rot ≤ 2.2°, anchor 2.6–3.6 mm.
  - For comparison, the G2 rack it replaces: 3.2–4.6 mm.
- Frame report vs the G2 rack (`summary.txt`): ICP 2.66 mm / 0.58°, kit proxy 1.71 mm / 0.48°, centroid 3.74 mm; the frame
  is clean.
  - The only flag is the x extent, 161.3 → 129.2 mm (ratio 0.80): the G2 rack's hallucinated +x bulge (13h known defect)
    is gone.
  - The surface max of 55.9 mm is that bulge seen from the new mesh.
  - The public scan's smallest extent is 117 mm [D].

## Expected [E] (mesh lane)
- CD-O 0.24177 − 5 × 0.0241 / 36 ≈ 0.2384 (3rd place: 0.23900).

## Frame sign-off (bold-albattani, 10:29 UTC message)
- **YES, transform NONE.**
- The x-extent drop (161 → 129 mm) and the 55.9 mm surface max are the G2 rack's hallucinated +x bulge going away. That
  bulge was the 0.5% of the surface at x +37…+110 mm that our ep31 points never supported.
- The new rack's 129 mm is close to the dev1 primitive (125 mm) and to the scan's thinnest extent (117 mm [D]).
- Frame consistent: ICP 2.66 mm / 0.58°, kit proxy 1.7 mm.
- 50-seed [D]: CD-O 0.3775 vs 0.4016; anchor 3.07 vs 3.78 mm. That matches the D1 anchors here.
