# Test G-A result

- Verdict: **FAIL (rho <= 0.46 and top mesh = CD-O best on 2 or fewer objects)**
- rho = Spearman(Gemini expected score, -CD-O) over 104 meshes: **0.4260** (bar > 0.46; object-bootstrap 95 % CI 0.16 to 0.65)
- Gemini top mesh = CD-O best on **1** of 10 objects (bar > 2)
- Reference, GT-free metric on the same meshes: rho 0.4650, hits 2
- Missing answers: 0 

| object | n | rho | Gemini pick (E) | its CD-O | CD-O rank | best (CD-O) | regret | GT-free rho |
|---|---|---|---|---|---|---|---|---|
| white_pot | 10 | 0.58 | sam3d/ep41_white_pot_k279_s7 (3.05) | 0.328 | 2 | trellis2/ep41_white_pot_k279_s7 (0.318) | 0.010 | 0.68 |
| white_pot_lid | 10 | 0.58 | trellis2/ep2_white_pot_lid_k321_s42 (2.89) | 0.394 | 5 | pixal_mv/ep2_white_pot_lid_s42 (0.253) | 0.140 | 0.52 |
| blue_cup | 10 | 0.36 | sam3d/ep22_blue_cup_k156_s42 (3.12) | 0.299 | 3 | sam3d/ep22_blue_cup_k156_s7 (0.268) | 0.031 | -0.21 |
| water_pitcher | 10 | 0.07 | sam3d/ep22_water_pitcher_k174_s42 (3.19) | 0.771 | 6 | hy21/ep22_water_pitcher_k174_s42 (0.378) | 0.393 | 0.67 |
| wooden_piece_1 | 10 | 0.76 | sam3d/ep23_wooden_piece_1_k27_s7 (3.07) | 0.204 | 3 | pixal_mv/ep23_wooden_piece_1_s42 (0.182) | 0.022 | -0.15 |
| wooden_piece_2 | 12 | 0.02 | hy21/ep23_wooden_piece_2_k6_s7 (2.98) | 0.438 | 11 | sam3d/ep23_wooden_piece_2_k6_s7 (0.202) | 0.237 | 0.21 |
| plastic_dish_rack | 10 | 0.82 | sam3d/ep26_plastic_dish_rack_k144_s7 (2.98) | 0.604 | 1 | sam3d/ep26_plastic_dish_rack_k144_s7 (0.604) | 0.000 | 0.65 |
| mini_sweeper | 10 | 0.55 | pixal_mv/ep31_mini_sweeper_s42 (2.40) | 0.479 | 3 | sam3d/ep31_mini_sweeper_k270_s7 (0.437) | 0.042 | 0.22 |
| mini_dust_pan | 12 | 0.26 | sam3d/ep39_mini_dust_pan_k297_s42 (3.20) | 0.261 | 4 | hy21/ep39_mini_dust_pan_k297_s42 (0.231) | 0.029 | 0.71 |
| beige_cup | 10 | 0.27 | hy21/ep11_beige_cup_k6_s42 (2.97) | 0.461 | 3 | pixal_mv/ep11_beige_cup_s42 (0.274) | 0.187 | 0.72 |
