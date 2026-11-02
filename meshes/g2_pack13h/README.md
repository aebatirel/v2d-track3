# meshes/g2_pack13h — G2 audit winners for pack 13h, a CD-O variant on 13f (2 Nov 2026)

Byte copies, renamed to the object names, from claude/bold-albattani-6qmxsv @ 8cd7fe77,
docs/research/mesh-2026-10-26/cdo-sprint/C4-audit/meshes_13h/. Transform none: library_v3 body frame. Each was placed GT-free
with C1/T2 place.py; the blue cup and the rack then got the GT-free T3 fit to our observed points.

| File | Source | md5 | Evals (slot) | Replaces in 13f |
|---|---|---|---|---|
| white_pot.glb | white_pot_g2_sam3d_ep44_k0_s7_lib.glb | 5243c309b6758f682b62e29ade6ff34f | 1, 3, 5, 6 (0); 8, 28 (1) | T3 pot b19b2e28 |
| blue_cup.glb | blue_cup_g2_sam3d_ep22_k159_s7_lib_t3fit.glb | ab012e4e0add44c3923fd172c4639734 | 10, 14, 20, 32, 33 (0) | sam3d s7 cup 672c4048 |
| plastic_dish_rack.glb | plastic_dish_rack_g2_hy21_ep31_k282_s123_lib_t3fit.glb | a289d009c45c6ee09d7dd787b8e7dbcf | 14 (1), 15 (0), 16 (0), 28 (0), 30 (1) | dev1 ep31 rack 1176443c |

**GT-informed selection** (as for Tier B).
- These are best-of-N picks. 264 meshes were generated: SAM 3D, Hunyuan3D-2.1 and TRELLIS.2 on 22 GT-free crops of
  public-episode video, 4 seeds each.
- The 264 were frozen in git (1a3a044) before any scan read. Selection then ran:
  1. a 6-seed public-scan CD-O screen;
  2. the top 4 per object, placed, plus T3-fit copies;
  3. a frozen 50-seed audit;
  4. pre-registered rules (A) / (B) / (C) plus the D1 veto (C4 PREREG sections 3, 7, 9 and 10).
- No scan geometry is in any mesh. None is a byte copy or a template of a scan (CD-O ≥ 0.23). No leaderboard input.
- Record: C4-audit/results/{audit_table_g2.md, adoption_g2.json, d1_g2.jsonl} and cdo-sprint/G2/README.md.
