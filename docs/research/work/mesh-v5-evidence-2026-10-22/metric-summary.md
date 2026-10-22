# Mesh acceptance metric - results (2026-10-22)

Eval pairs 36; 26 on the 10 objects with a public scan (spoon: 10 pairs, no scan). Weights: wooden_spoon 10, white_pot 6, blue_cup 5, plastic_dish_rack 5, beige_cup 2, mini_sweeper 2, mini_dust_pan 2, white_pot_lid 1, water_pitcher 1, wooden_piece_1 1, wooden_piece_2 1.

All scan columns are [D] (public scan as stand-in for the hidden scan, eval seeds of the kit scorer, kit packer budget on both meshes). amb is [M] (mesh only).

## Library sets, eval-pair-weighted over the 26 known-object pairs [D]

| set | CD-O_w eval seeds (cm) | CD-O_w all seeds | ADD_w eval seeds (mm) | ADD_w all seeds | ADD_w median-seed | flips eval / all seeds (objects) |
|---|---|---|---|---|---|---|
| library_v1 | 0.5393 | 0.5402 | 8.12 | 7.68 | 6.64 | 1 / 2 (mini_sweeper) |
| library_v2 | 0.4913 | 0.4920 | 8.31 | 7.83 | 6.78 | 1 / 2 (mini_sweeper) |
| library_v3 | 0.4914 | 0.4920 | 8.35 | 7.34 | 6.82 | 1 / 1 (mini_sweeper) |
| library_v4 | 0.4918 | 0.4923 | 8.34 | 7.32 | 6.82 | 1 / 1 (mini_sweeper) |

### Per object, library_v2 / v3 / v4 [D]

| object (w) | set | CD-O eval | CD-O all | ADD eval mm | ADD all (max) | rot max deg | flips e/a of n | amb-floor mm [M] |
|---|---|---|---|---|---|---|---|---|
| white_pot (6) | library_v2 | 0.437 | 0.437 | 6.7 | 6.6 (7.0) | 2 | 0/0 of 8 | 10.22 |
| blue_cup (5) | library_v2 | 0.523 | 0.526 | 10.0 | 9.9 (10.5) | 2 | 0/0 of 7 | 4.48 |
| plastic_dish_rack (5) | library_v2 | 0.555 | 0.555 | 6.0 | 6.0 (6.6) | 2 | 0/0 of 7 | 8.46 |
| beige_cup (2) | library_v2 | 0.856 | 0.861 | 6.5 | 7.2 (8.1) | 4 | 0/0 of 6 | 6.25 |
| mini_sweeper (2) | library_v2 | 0.316 | 0.316 | 25.1 | 18.3 (45.6) | 178 | 1/2 of 6 | 1.84 |
| mini_sweeper (2) | library_v3 | 0.317 | 0.316 | 25.6 | 11.8 (45.7) | 178 | 1/1 of 6 | 1.81 |
| mini_sweeper (2) | library_v4 | 0.317 | 0.316 | 25.6 | 11.8 (45.7) | 178 | 1/1 of 6 | 1.81 |
| mini_dust_pan (2) | library_v2 | 0.331 | 0.332 | 5.6 | 5.7 (6.1) | 3 | 0/0 of 6 | 4.44 |
| white_pot_lid (1) | library_v2 | 0.421 | 0.417 | 8.1 | 8.1 (8.8) | 2 | 0/0 of 6 | 3.02 |
| water_pitcher (1) | library_v2 | 0.894 | 0.889 | 7.6 | 7.8 (8.5) | 3 | 0/0 of 6 | 10.44 |
| wooden_piece_1 (1) | library_v2 | 0.222 | 0.223 | 2.4 | 2.8 (4.0) | 1 | 0/0 of 6 | 1.19 |
| wooden_piece_1 (1) | library_v4 | 0.227 | 0.226 | 2.5 | 2.9 (3.6) | 1 | 0/0 of 6 | 1.15 |
| wooden_piece_2 (1) | library_v2 | 0.216 | 0.216 | 3.6 | 3.4 (4.7) | 1 | 0/0 of 6 | 0.31 |
| wooden_piece_2 (1) | library_v4 | 0.221 | 0.219 | 3.2 | 2.9 (3.8) | 1 | 0/0 of 6 | 0.27 |

## Candidate global changes under the rule [D]

Rule: accept only if the eval-pair-weighted CD-O change <= 0 AND the eval-pair-weighted ADD_static change <= 0 (both at the scorer's eval seeds, summed over the objects the change touches, normalised by the 26 known pairs) AND no object gains a flip on any seed (eval or extra).

| change | objects: dCD-O cm / dADD mm / flips base->new | wdCD-O (cm) | wdADD (mm) | verdict |
|---|---|---|---|---|
| library_v3 vs v2 (sweeper flatten_base) | mini_sweeper +0.001 / +0.4 / 2->1 | +0.0001 | +0.03 | reject (CD-O, ADD) |
| library_v4 vs v2 (board edge flatten) | wooden_piece_1 +0.005 / +0.1 / 0->0; wooden_piece_2 +0.005 / -0.3 / 0->0 | +0.0004 | -0.01 | reject (CD-O) |
| Design O sec.0 set vs library_v2 | white_pot_lid -0.044 / +4.5 / 0->0; mini_dust_pan -0.080 / -1.8 / 0->0; white_pot +0.288 / +4.8 / 0->0; wooden_piece_1 -0.037 / +1.7 / 0->0; wooden_piece_2 +0.013 / +0.0 / 0->1 NEW FLIP | +0.0576 | +1.20 | reject (CD-O, ADD, flip) |
| Design O sec.0 set, pot on fallback, vs library_v2 | white_pot_lid -0.044 / +4.5 / 0->0; mini_dust_pan -0.080 / -1.8 / 0->0; wooden_piece_1 -0.037 / +1.7 / 0->0; wooden_piece_2 +0.013 / +0.0 / 0->1 NEW FLIP | -0.0088 | +0.10 | reject (ADD, flip) |
| Design O sec.0 set vs library_v4 | white_pot_lid -0.044 / +4.5 / 0->0; mini_dust_pan -0.080 / -1.8 / 0->0; white_pot +0.288 / +4.8 / 0->0; wooden_piece_1 -0.042 / +1.6 / 0->0; wooden_piece_2 +0.008 / +0.4 / 0->1 NEW FLIP | +0.0572 | +1.21 | reject (CD-O, ADD, flip) |
| Design O largest component (review2/lc) vs library_v2 | white_pot_lid -0.033 / +5.4 / 0->0; mini_dust_pan -0.047 / -1.7 / 0->0; white_pot +0.429 / +6.3 / 0->0; wooden_piece_1 -0.033 / -0.4 / 0->2 NEW FLIP; wooden_piece_2 +0.016 / +0.6 / 0->0 | +0.0935 | +1.53 | reject (CD-O, ADD, flip) |
| Design O + local fallback (fb12) vs library_v2 | white_pot_lid -0.021 / +5.0 / 0->0; mini_dust_pan -0.105 / -2.4 / 0->0; white_pot -0.070 / -1.7 / 0->0 | -0.0251 | -0.39 | ACCEPT |
| Design O 4 mm only, all-episode lid (obs/out2/lid) vs library_v2 | white_pot_lid -0.052 / +4.1 / 0->0 | -0.0020 | +0.16 | reject (ADD) |
| Design O pot, band mask (potbm) vs library_v2 | white_pot +0.234 / +4.0 / 0->0 | +0.0539 | +0.93 | reject (CD-O, ADD) |
| Design O pot, band mask, no below-carve (potbmnb) vs library_v2 | white_pot +0.185 / -3.5 / 0->0 | +0.0427 | -0.80 | reject (CD-O) |
| Design O boards without silhouette/step 5 (wooden_piece_N/4c12) vs library_v2 | wooden_piece_1 -0.006 / +0.8 / 0->1 NEW FLIP; wooden_piece_2 +0.110 / +1.9 / 0->2 NEW FLIP | +0.0040 | +0.10 | reject (CD-O, ADD, flip) |
| XCarve ep24 (xc) vs its own ep24 base | wooden_piece_1 +0.006 / -0.1 / 6->5; wooden_piece_2 +0.007 / +103.2 / 2->3 NEW FLIP | +0.0005 | +3.97 | reject (CD-O, ADD, flip) |
| XCarve ep24 base grid vs library_v2 | wooden_piece_1 +0.007 / +161.1 / 0->6 NEW FLIP; wooden_piece_2 +0.294 / +24.3 / 0->2 NEW FLIP | +0.0115 | +7.13 | reject (CD-O, ADD, flip) |
| XCarve ep2 (xch) vs its own ep2 base | white_pot +0.007 / -0.0 / 0->0 | +0.0017 | -0.00 | reject (CD-O) |
| XCarve ep2 (mot) vs its own ep2 base | white_pot +0.006 / +0.2 / 0->0; white_pot_lid +0.052 / -9.5 / 0->0 | +0.0034 | -0.33 | reject (CD-O) |
| XCarve ep18 (nj1) vs its own ep18 base | mini_sweeper +0.001 / +0.0 / 6->6; mini_dust_pan +0.012 / +0.2 / 0->0 | +0.0010 | +0.02 | reject (CD-O, ADD) |
| Joint min-cut ep2 joint_a vs none | white_pot +0.015 / +0.4 / 0->0; white_pot_lid +0.175 / -12.5 / 0->0 | +0.0103 | -0.38 | reject (CD-O) |
| Joint min-cut ep2 joint_h1 vs none | white_pot +0.010 / +0.1 / 0->0; white_pot_lid +0.140 / -10.4 / 0->0 | +0.0078 | -0.37 | reject (CD-O) |
| Joint carve_both ep2 vs none | white_pot +0.067 / +0.5 / 0->0; white_pot_lid +0.165 / -6.5 / 0->0 | +0.0219 | -0.14 | reject (CD-O) |
| Single-episode ep2 rebuild (joint/ep2/none) vs library_v2 | white_pot +0.128 / -0.6 / 0->0; white_pot_lid +0.147 / +13.0 / 0->0 | +0.0352 | +0.37 | reject (CD-O, ADD) |

## Per object: range over all evaluated variants [D] (information only; picking per object from this = scan leak)

| object (w) | n variants | v2 CD-O / ADD | best CD-O (variant, its ADD) | best ADD (variant, its CD-O) | variants with any flip |
|---|---|---|---|---|---|
| white_pot (6) | 32 | 0.437 / 6.7 | 0.322 (review2/potsingle/ep27/4c12_adj_g2_f0_cont, 3.2) | 3.2 (obs/out2/potbmnb/4c12_adj_g2_f0_cont, 0.622) | 0 |
| blue_cup (5) | 4 | 0.523 / 10.0 | 0.523 (library_v1/blue_cup, 10.0) | 10.0 (library_v1/blue_cup, 0.523) | 0 |
| plastic_dish_rack (5) | 4 | 0.555 / 6.0 | 0.555 (library_v1/plastic_dish_rack, 6.0) | 6.0 (library_v1/plastic_dish_rack, 0.555) | 0 |
| beige_cup (2) | 4 | 0.856 / 6.5 | 0.856 (library_v1/beige_cup, 6.5) | 6.5 (library_v1/beige_cup, 0.856) | 0 |
| mini_sweeper (2) | 6 | 0.316 / 25.1 | 0.316 (library_v1/mini_sweeper, 25.1) | 25.1 (library_v1/mini_sweeper, 0.316) | 6 |
| mini_dust_pan (2) | 15 | 0.331 / 5.6 | 0.226 (obs/out2/dpfb/4c12_adj_g2_f0_cont__fb12_fill_g0_f0_bin, 3.3) | 3.3 (obs/out2/dpfb/4c12_adj_g2_f0_cont__fb12_fill_g0_f0_bin, 0.226) | 0 |
| white_pot_lid (1) | 32 | 0.421 / 8.1 | 0.365 (obs/out2/lid/4_none_g0_f0_cont, 12.3) | 8.1 (library_v1/white_pot_lid, 0.421) | 0 |
| water_pitcher (1) | 4 | 0.894 / 7.6 | 0.894 (library_v1/water_pitcher, 7.6) | 7.6 (library_v1/water_pitcher, 0.894) | 0 |
| wooden_piece_1 (1) | 40 | 0.222 / 2.4 | 0.163 (obs/out2/wooden_piece_1_nobc/6c12_adj_g2_f0_cont, 3.3) | 1.5 (obs/out2/wooden_piece_1_nobc_mask/6c12_adj_g2m_f0_cont, 0.169) | 11 |
| wooden_piece_2 (1) | 40 | 0.216 / 3.6 | 0.215 (obs/out2/wooden_piece_2_nobc_mask/6_adj_g2m_f0_cont, 1.4) | 1.4 (obs/out2/wooden_piece_2_nobc_mask/6_adj_g2m_f0_cont, 0.215) | 21 |

## GT-free ambiguity vs measured flips

amb = residual (symmetric mean distance, mm) of the mesh ICP-registered to an independent sample of itself from the best non-identity PCA start that stays > 90 deg away (declared symmetries excluded); floor = identity residual (sampling noise). excess = amb - floor; small excess = a flipped copy fits almost as well.

| object | scan excess [D] | our meshes: excess range [M] | meshes with a flip / evaluated | excess of flipping meshes | excess of non-flipping meshes |
|---|---|---|---|---|---|
| white_pot | 8.05 | 5.52 - 15.27 | 0 / 32 | - | 5.52 - 15.27 (median 9.36) |
| blue_cup | 5.56 | 4.48 - 4.48 | 0 / 4 | - | 4.48 - 4.48 (median 4.48) |
| plastic_dish_rack | 7.00 | 8.46 - 8.46 | 0 / 4 | - | 8.46 - 8.46 (median 8.46) |
| beige_cup | 5.61 | 6.25 - 6.25 | 0 / 4 | - | 6.25 - 6.25 (median 6.25) |
| mini_sweeper | 0.37 | 1.81 - 3.83 | 6 / 6 | 1.81, 1.81, 1.84, 1.84, 3.82, 3.83 | - |
| mini_dust_pan | 5.54 | 4.19 - 6.54 | 0 / 15 | - | 4.19 - 6.54 (median 5.10) |
| white_pot_lid | 3.54 | 2.77 - 7.40 | 0 / 32 | - | 2.77 - 7.40 (median 3.23) |
| water_pitcher | 6.66 | 10.44 - 10.44 | 0 / 4 | - | 10.44 - 10.44 (median 10.44) |
| wooden_piece_1 | 0.36 | 0.29 - 1.86 | 11 / 40 | 0.34, 0.42, 0.70, 0.80, 1.68, 1.70, 1.72, 1.73 | 0.29 - 1.35 (median 0.54) |
| wooden_piece_2 | 0.24 | 0.25 - 2.37 | 21 / 40 | 0.34, 0.34, 0.36, 0.37, 0.37, 0.38, 0.38, 0.39 | 0.25 - 0.55 (median 0.39) |

All meshes with a scan: n = 181, flipping (any seed) = 38. Spearman(excess, flip fraction) = -0.33 (p = 7.6e-06).
Mann-Whitney (flipping meshes have smaller excess): p = 2.6e-06. Flip rate by excess band: excess < 0.5 mm: 12/39; excess < 1.0 mm: 18/61; excess < 1.5 mm: 18/66; excess < 2.0 mm: 29/77; excess < 3.0 mm: 36/92; excess >= 3 mm: 2/89.

## Objects without a scan (GT-free amb only) [M]

| label | faces in | watertight/bodies | amb mm | floor mm | excess | flip-like rotation of best start |
|---|---|---|---|---|---|---|
| library_v1/wooden_spoon | 3224 | y/1 | 3.41 | 1.40 | 2.00 | 177.5 |
| library_v2/wooden_spoon | 3224 | y/1 | 3.41 | 1.40 | 2.00 | 177.5 |
| library_v3/wooden_spoon | 3224 | y/1 | 3.41 | 1.40 | 2.00 | 177.5 |
| library_v4/wooden_spoon | 3224 | y/1 | 3.41 | 1.40 | 2.00 | 177.5 |
| spoon_template/wooden_spoon | 3224 | y/1 | 3.41 | 1.40 | 2.00 | 177.5 |
