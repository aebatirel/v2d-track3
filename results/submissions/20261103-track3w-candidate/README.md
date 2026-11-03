# Track 3 pack-13i candidate, 3 Nov 2026 — CD-O variant on 13h with the G3 pot, dust pan and board 1

**STATUS: PENDING frame sign-off (mesh lane). Not ready, not uploaded.** keen-heisenberg's session uploads, on the owner's
word there.

**This is a CD-O-only variant** on 13h (itself a CD-O variant on 13f). The G3 pot registers 6.5–7.1 mm off the public scan
[D] (the 13h G2 pot: about 2.3 mm), so it is meant for the CD-O board only. Each board keeps our best submission.

**Disclosure: GT-informed selection** (as for G2 / Tier B; meshes/g3_pack13i/README.md).
- These are best-of-N picks from the G3 batch: 468 meshes from SAM 3D, Hunyuan3D-2.1, TRELLIS.2 and Pixal3D-MV, on GT-free
  public-episode crops and views.
- Selection ran:
  1. a 6-seed public-scan CD-O screen;
  2. the top 4 per object (placed, T3-fit and GT-free trim copies);
  3. a frozen 50-seed audit;
  4. pre-registered rules (A) / (B) / (C) plus the D1 veto (C4 PREREG sections 3, 9, 10 and 12).
- No scan geometry is in any mesh, none is a scan copy or template, and no leaderboard input was used.
- All of 13h's disclosures carry over: G2 / Tier B / B+ selection, the rack bulge defect, 13f's inherited eval-25 plate,
  the eval-15 clause-c waiver, the 12c blue-cup selector.

## Record
- File: `build_13i/track3_submission.parquet`, 9,120 rows, 1,286,523 bytes.
  sha256 `1bcbdcfae42a810115ac713e61271d3a048f125338a4b2ef616e3f2b917362a3`.
- CD-O file: `build_13i/track3_submission.cd-o.parquet`, 294,912 rows, sha256 `485d3c1c1467de04…`.
- Code: https://github.com/aebatirel/v2d-track3/commit/edd6d69058a9bc5d17a769440e92ea7116a3333d (on every row).
- Base: pack 13h (`results/submissions/20261102-track3v-candidate/build_13h`, d917b002…), reproduced byte for byte from its
  packer inputs first. Built by tools/pack_swap_meshes.py with the guard on:
  `--only-episodes "white_pot:1,3,5,6,8,28;mini_dust_pan:19,38;wooden_piece_1:25"`.
- Meshes: `meshes/g3_pack13i/`, byte copies at 82c09955. Transform none.
  - pot c3fc0a7c…, replacing G2 5243c309;
  - dust pan 3fe34bcc…, replacing hy21 1530b1d3;
  - board 1 36b292a5…, replacing Tier B 015aaae3.

## Checks [M]
- vs 13h: only `code_commit_url` (all rows) and `object_mesh_b64` on 9 payload rows differ: pot 1/3/5/6 o0 and 8/28 o1;
  dust pan 19 o1 and 38 o0; board 1 on 25 o0.
- CD-O changes exactly those 9 pairs. Offline validate_submission passes. 0 MESH WARNINGs.
- **D1 PASS in both reference modes** [D] (d1pairs.py on the packed bytes; eval seed + 6): 0/7 flips on all 9 pairs.
  - Pot: rot ≤ 1.9°, anchor 6.5–7.1 mm.
  - Dust pan: rot ≤ 4.0°, anchor 2.2–2.9 mm.
  - Board 1: rot ≤ 1.3°, anchor 1.8–3.8 mm.
  - Files: `build_13i/d1_raw.json`, `build_13i/d1_budget.json`.
- Frame report vs the 13h meshes (`summary.txt`, mm):
  - pot: centroid 6.89 (FLAG), ICP 4.5 mm / 0.55°, extent [127.8, 193.1, 358.5] → [144.0, 196.8, 375.8];
  - dust pan: x extent 46.7 → 82.0 (ratio 1.755, FLAG), surface max 44.8, ICP 2.7 mm / 4.0°;
  - board 1: extent [19.9, 149.9, 247.0] → [24.0, 131.0, 231.7] (FLAG), ICP 0.24 mm / 0.23°.

## Expected [E] (mesh lane)
- 13h about 0.2516 → 13i about 0.242: pot −0.0077, dust pan −0.0013, board 1 −0.0008.
