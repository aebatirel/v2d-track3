| ep | objects | S2 R_lib Po | ΔR_lib Po | ΔR_lib refineP | ΔR_* Po | S2 RPE_lib Po (cm) | ΔRPE_lib Po (cm) | near frames (share) | S13 change mean / max (cm), worst object |
|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot, white_pot_lid | 0.9669 | +0.0003 | +0.0000 | +0.0019 | 1.343 | -0.001 | 0.65, 0.31 | 0.033 / 0.19, white_pot_lid f171 |
| 2 | white_pot, white_pot_lid | 0.9911 | -0.0009 | +0.0001 | -0.0002 | 1.379 | -0.001 | 0.77, 0.31 | 0.039 / 0.23, white_pot f340 |
| 11 | blue_cup, beige_cup | 0.9012 | +0.0005 | +0.0005 | +0.0016 | 1.717 | -0.001 | 0.69, 0.66 | 0.047 / 0.31, blue_cup f65 |
| 12 | blue_cup, plastic_dish_rack | 0.9763 | +0.0002 | +0.0005 | -0.0001 | 1.116 | -0.004 | 0.66, 0.01 | 0.065 / 0.73, blue_cup f63 |
| 13 | blue_cup, plastic_dish_rack | 0.9623 | +0.0015 | +0.0010 | +0.0015 | 1.349 | -0.007 | 0.59, 0.00 | 0.105 / 0.91, blue_cup f166 |
| 18 | mini_sweeper, mini_dust_pan | 0.9162 | +0.0000 | -0.0006 | -0.0013 | 4.012 | -0.004 | 0.76, 0.52 | 0.137 / 5.37, mini_sweeper f153 |
| 21 | blue_cup, water_pitcher | 0.8389 | -0.0005 | -0.0005 | +0.0020 | 1.179 | +0.000 | 0.56, 0.49 | 0.148 / 0.96, water_pitcher f94 |
| 22 | blue_cup, water_pitcher | 0.8704 | -0.0022 | -0.0030 | -0.0052 | 1.114 | -0.002 | 0.74, 0.37 | 0.105 / 0.60, water_pitcher f82 |
| 23 | wooden_piece_1, wooden_piece_2 | 0.0425 | +0.0006 | +0.0006 | +0.0005 | 14.152 | -0.059 | 0.45, 0.83 | 0.295 / 8.02, wooden_piece_1 f155 |
| 24 | wooden_piece_1, wooden_piece_2 | 0.8091 | -0.0011 | -0.0011 | -0.0002 | 0.807 | -0.001 | 0.87, 0.51 | 0.050 / 0.33, wooden_piece_2 f40 |
| 26 | plastic_dish_rack, white_pot | 0.9717 | +0.0012 | -0.0006 | +0.0006 | 1.180 | -0.008 | 0.06, 0.56 | 0.078 / 0.35, plastic_dish_rack f70 |
| 27 | plastic_dish_rack, white_pot | 0.9634 | +0.0000 | -0.0007 | +0.0008 | 1.184 | -0.003 | 0.00, 0.76 | 0.059 / 0.28, plastic_dish_rack f61 |
| 31 | mini_sweeper, plastic_dish_rack | 0.8239 | -0.0015 | -0.0044 | -0.0010 | 1.850 | -0.002 | 0.85, 0.90 | 0.029 / 0.16, mini_sweeper f20 |
| 39 | mini_dust_pan | 0.9759 | -0.0008 | -0.0008 | -0.0008 | – | – | 0.73 | 0.063 / 0.79, mini_dust_pan f240 |
| 40 | mini_dust_pan | 0.9584 | +0.0000 | +0.0000 | -0.0010 | – | – | 0.82 | 0.036 / 0.23, mini_dust_pan f121 |
| 41 | white_pot | 0.9927 | +0.0004 | +0.0004 | -0.0002 | – | – | 0.76 | 0.041 / 0.24, white_pot f101 |
| 42 | white_pot | 0.9990 | +0.0000 | -0.0003 | +0.0003 | – | – | 0.82 | 0.039 / 0.17, white_pot f162 |
| 43 | white_pot | 0.9486 | -0.0011 | -0.0014 | -0.0009 | – | – | 0.87 | 0.033 / 0.15, white_pot f321 |
| 44 | white_pot | 0.9970 | +0.0007 | +0.0007 | +0.0000 | – | – | 0.79 | 0.032 / 0.14, white_pot f222 |
| 45 | white_pot | 0.9823 | +0.0005 | +0.0005 | +0.0004 | – | – | 0.86 | 0.040 / 0.14, white_pot f188 |

| arm | mean S2 R_lib | mean S13 R_lib | mean ΔR_lib | min ΔR_lib (ep) | better / worse | mean ΔR_* | min ΔR_* | mean RPE_lib S2 → S13 (multi-object) | mean ΔRPE_lib | ΔRPE > +0.5 cm | rule |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Po | 0.8944 | 0.8943 | -0.00011 | -0.0022 (22) | 9 / 7 | -0.00006 | -0.0052 | 2.491 → 2.484 | -0.0072 | none | FAIL |
| refineP | 0.8982 | 0.8978 | -0.00046 | -0.0044 (31) | 8 / 10 | -0.00002 | -0.0045 | 2.440 → 2.433 | -0.0076 | none | FAIL |

Verdict: **FAIL**

| ep | per-object ΔAUC lib, Po |
|---|---|
| 0 | white_pot +0.0000, white_pot_lid +0.0006 |
| 2 | white_pot +0.0000, white_pot_lid -0.0018 |
| 11 | blue_cup +0.0009, beige_cup +0.0000 |
| 12 | blue_cup +0.0003, plastic_dish_rack +0.0000 |
| 13 | blue_cup +0.0000, plastic_dish_rack +0.0029 |
| 18 | mini_sweeper -0.0011, mini_dust_pan +0.0010 |
| 21 | blue_cup +0.0003, water_pitcher -0.0014 |
| 22 | blue_cup -0.0043, water_pitcher +0.0000 |
| 23 | wooden_piece_1 +0.0012, wooden_piece_2 +0.0000 |
| 24 | wooden_piece_1 -0.0005, wooden_piece_2 -0.0018 |
| 26 | plastic_dish_rack +0.0004, white_pot +0.0020 |
| 27 | plastic_dish_rack +0.0000, white_pot +0.0000 |
| 31 | mini_sweeper +0.0009, plastic_dish_rack -0.0038 |
| 39 | mini_dust_pan -0.0008 |
| 40 | mini_dust_pan +0.0000 |
| 41 | white_pot +0.0004 |
| 42 | white_pot +0.0000 |
| 43 | white_pot -0.0011 |
| 44 | white_pot +0.0007 |
| 45 | white_pot +0.0005 |
