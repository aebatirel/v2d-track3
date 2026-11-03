# meshes/r_pack13j — round-R rack for pack 13j, a CD-O variant on 13i (3 Nov 2026)

`plastic_dish_rack.glb` is a byte copy of claude/bold-albattani-6qmxsv @ ead6a10c,
docs/research/mesh-2026-10-26/cdo-sprint/C4-audit/meshes_13j/plastic_dish_rack_r_hy21_ep12_k18_s31337_lib_t3fit.glb,
md5 1882b7a2e09ba03d1ebee370ca95d657. It goes on evals 14 (1), 15 (0), 16 (0), 28 (0) and 30 (1), replacing 13i's G2 rack
a289d009. Transform none: library_v3 body frame, placed GT-free with place.py, then a GT-free T3 fit to our observed points.

**GT-informed selection** (as for G2 / G3).
- Picked from rack round R: 390 generated racks from SAM 3D, Hunyuan3D-2.1, TRELLIS.2 and Pixal3D-MV, on GT-free crops of
  public episodes not used before, 6 seeds each.
- Selection ran:
  1. a 6-seed public-scan CD-O screen;
  2. the top 6, as placed, t3fit, trim and outer copies;
  3. a frozen 50-seed audit;
  4. pre-registered rules A / B / C plus the D1 veto (C4 PREREG sections 3, 9, 13 and 14).
- No scan geometry, no scan copy or template, no leaderboard input.
- 50-seed audit [D] vs the 13i rack: CD-O 0.3775 vs 0.4016; W30 0; anchor 3.07 vs 3.78 mm; ADD 3.74 vs 4.30 mm.
- Provisional: 90 GT-free primitive refits are still in the audit. A lower qualifying one would come as a 13j2.
