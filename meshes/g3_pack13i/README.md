# meshes/g3_pack13i — G3 audit winners for pack 13i, a CD-O variant on 13h (3 Nov 2026)

Byte copies, renamed to the object names, from claude/bold-albattani-6qmxsv @ 82c09955,
docs/research/mesh-2026-10-26/cdo-sprint/C4-audit/meshes_13i/. Transform none: library_v3 body frame. Each was placed GT-free
with C1/T2 place.py; the board was then also T3-fit to our observed points.

| File | Source | md5 | Evals (slot) | Replaces in 13h |
|---|---|---|---|---|
| white_pot.glb | white_pot_g3_trellis2_ep45_k9_s2025_lib.glb | c3fc0a7cb235b4c270ac3b8599b88472 | 1, 3, 5, 6 (0); 8, 28 (1) | G2 pot 5243c309 |
| mini_dust_pan.glb | mini_dust_pan_g3_pixal_mv_ep39_s2025_lib.glb | 3fe34bcc9206e222bb1ff8e803720a9e | 19 (1), 38 (0) | hy21 dust pan 1530b1d3 |
| wooden_piece_1.glb | wooden_piece_1_g3_hy21_ep24_k3_s123_lib_t3fit.glb | 36b292a560b6e25e44a276dabdb4366a | 25 (0) | Tier B occupancy board 1 015aaae3 |

**GT-informed selection** (as for G2 / Tier B).
- These are best-of-N picks from the G3 batch: 468 meshes from SAM 3D, Hunyuan3D-2.1, TRELLIS.2 and Pixal3D-MV, on
  GT-free public-episode crops and views, 4 seeds each.
- Selection ran:
  1. a 6-seed public-scan CD-O screen;
  2. the top 4 per object, as placed, T3-fit and GT-free trim copies;
  3. a frozen 50-seed audit;
  4. pre-registered rules (A) / (B) / (C) plus the D1 veto (C4 PREREG sections 3, 9, 10 and 12).
- No scan geometry is in any mesh, none is a scan copy or template, and no leaderboard input was used.
- Record: C4-audit/results/{adoption_g3.json, d1_g3.jsonl, raw_g3/} and cdo-sprint/G3/README.md.
- The pot's registration ADD is 6.8 vs 2.7 mm for the G2 pot [D], so it is for the CD-O pack only, not pose packs.
