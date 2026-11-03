# Track 3 pack-13h candidate, 2 Nov 2026 — CD-O variant on 13f with the G2 pot, blue cup and rack

**STATUS: PENDING frame sign-off (mesh lane). Not ready, not uploaded.** keen-heisenberg's session uploads, on the owner's
word there.

**This is a CD-O-only variant** (coordinator 23:17 UTC). It is built on 13f (best CD-O, 0.26249 [M]), not on the pose packs.
Each board keeps our best submission, so its pose boards do not matter. It inherits 13f's eval-25 wooden_piece_2 plate,
which fails D1 against the raw scan (docs/research/work/flipcheck-20261102). The plate does not affect CD-O.

**Disclosure: GT-informed selection** (as for Tier B; meshes/g2_pack13h/README.md).
- These are best-of-N picks from 264 generated meshes: SAM 3D, Hunyuan3D-2.1 and TRELLIS.2 on 22 GT-free crops of
  public-episode video, 4 seeds each.
- The meshes were frozen in git (1a3a044) before any scan read. Selection then ran:
  1. a 6-seed public-scan CD-O screen;
  2. the top 4 per object, placed with GT-free place.py and T3-fit copies;
  3. a frozen 50-seed audit;
  4. pre-registered rules (A) / (B) / (C) plus the D1 veto (C4 PREREG sections 3, 7, 9 and 10).
- No scan geometry is in any mesh, and none is a scan copy or template. No leaderboard input.
- All of 13f's disclosures carry over (Tier B / B+ selection, eval-15 clause-c waiver, 12c blue-cup selector).

## Record
- File: `build_13h/track3_submission.parquet`, 9,120 rows, 1,302,068 bytes.
  sha256 `d917b0022336d5c9b7037052df32949705a9fc0e3199aab36a6760c794ae5a4e`.
- CD-O file: `build_13h/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `062895386385d823…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/9610329e1177921827a9b66e38103e746efd8a0c (on every row).
- Base: pack 13f (`results/submissions/20261102-track3r-candidate/build_13f`, fa1e31f5…), reproduced byte for byte from its
  packer inputs first. Built by tools/pack_swap_meshes.py with the guard on:
  `--only-episodes "white_pot:1,3,5,6,8,28;blue_cup:10,14,20,32,33;plastic_dish_rack:14,15,16,28,30"`.
- Meshes: `meshes/g2_pack13h/`, byte copies at 8cd7fe77. Transform none.

| Object | md5 | Replaces |
|---|---|---|
| white_pot | 5243c309… | T3 pot b19b2e28 |
| blue_cup | ab012e4e… | sam3d s7 cup 672c4048 |
| plastic_dish_rack | a289d009… | dev1 rack 1176443c |

## Checks [M]
- vs 13f: only `code_commit_url` (all rows) and `object_mesh_b64` on 16 payload rows differ:
  - pot on 1/3/5/6 o0 and 8/28 o1;
  - cup on 10/14/20/32/33 o0;
  - rack on 14 o1, 15/16/28 o0, 30 o1.
- CD-O changes exactly those 16 pairs. Offline validate_submission passes. 0 MESH WARNINGs.
- **D1 PASS in both reference modes** [D] (d1pairs.py on the packed bytes; eval seed + 6): 0/7 flips on all 16 pairs.
  - Pot: rot ≤ 2.5°, anchor 1.8–2.8 mm.
  - Rack: rot ≤ 2.2°, anchor 3.2–4.6 mm.
  - Blue cup: tilt ≤ 2.0°, eval-seed rot ≤ 3.9°. Spins up to 170° on extra seeds are about the kit's symmetry axis.
  - Files: `build_13h/d1_raw.json`, `build_13h/d1_budget.json`.
- Frame report vs the 13f meshes (`summary.txt`, mm):
  - pot: centroid 5.95, ICP 5.06 mm / 2.46°, proxy 5.73 (FLAGS);
  - cup: centroid 1.46, ICP 1.01 mm / 2.84° (ok);
  - rack: centroid 20.57, ICP 8.83 mm / 1.97°, proxy 7.04, x extent 125.5 → 161.3 (ratio 1.285) (FLAGS).
  - Against the public scan, the rack's anchor is 3.2–4.6 mm [D]. The 13f rack's was 8.1–9.7 mm (12e record).

## Expected [E] (mesh lane)
- From the 50-seed medians: pot −0.0041, cup −0.0043, rack −0.0023, about −0.011 in total.
- On 13f (measured 0.26249) that gives CD-O ≈ 0.252 [E].
