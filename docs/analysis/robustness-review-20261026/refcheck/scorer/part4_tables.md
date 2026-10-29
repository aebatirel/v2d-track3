### f0: rollout frame 0 replaced by its reference frame 0 (sim trajectory, registered vs public mocap)

| ep | rollout | objects | AUC base | AUC f0ref | dAUC | per-object dAUC | SP/MP base -> f0ref |
|---|---|---|---|---|---|---|---|
| 2 | r1 | white_pot + white_pot_lid | 0.4513 | 0.4515 | +0.0002 | white_pot -0.001, white_pot_lid +0.001 | 0/0 -> 0/0 |
| 11 | r1 | blue_cup + beige_cup | 0.5668 | 0.5652 | -0.0016 | blue_cup -0.000, beige_cup -0.003 | 1/0 -> 1/0 |
| 12 | r1 | blue_cup + plastic_dish_rack | 0.9213 | 0.9204 | -0.0009 | blue_cup -0.024, plastic_dish_rack +0.022 | 1/1 -> 1/1 |
| 21 | r1 | blue_cup + water_pitcher | 0.7903 | 0.7720 | -0.0183 | blue_cup -0.000, water_pitcher -0.036 | 1/0 -> 1/0 |
| 21 | r2 | blue_cup + water_pitcher | 0.7712 | 0.7616 | -0.0096 | blue_cup -0.001, water_pitcher -0.018 | 1/0 -> 1/0 |
| 24 | r1 | wooden_piece_1 + wooden_piece_2 | 0.3076 | 0.3645 | +0.0569 | wooden_piece_1 +0.036, wooden_piece_2 +0.078 | 0/0 -> 0/0 |
| 26 | r1 | plastic_dish_rack + white_pot | 0.5370 | 0.5738 | +0.0368 | plastic_dish_rack +0.074, white_pot +0.000 | 0/0 -> 0/0 |
| 27 | r1 | plastic_dish_rack + white_pot | 0.9544 | 0.9113 | -0.0431 | plastic_dish_rack -0.062, white_pot -0.024 | 1/1 -> 1/1 |
| 31 | r1 | mini_sweeper + plastic_dish_rack | 0.7697 | 0.8231 | +0.0534 | mini_sweeper +0.075, plastic_dish_rack +0.032 | 1/1 -> 1/1 |
| 31 | r2 | mini_sweeper + plastic_dish_rack | 0.7359 | 0.8056 | +0.0697 | mini_sweeper +0.050, plastic_dish_rack +0.090 | 1/1 -> 1/1 |
| 31 | r3 | mini_sweeper + plastic_dish_rack | 0.7412 | 0.7913 | +0.0501 | mini_sweeper +0.058, plastic_dish_rack +0.042 | 1/1 -> 1/1 |

mean dAUC +0.0176, mean |dAUC| 0.0310, n = 11

### Pitcher swap (library_v3 -> library_v3p) on the ep21 twin, same rollouts, per scoring variant

| variant | r1 v3 | r1 v3p | r1 d | r2 v3 | r2 v3p | r2 d | mean d | pitcher reg. rot v3 / v3p (deg) |
|---|---|---|---|---|---|---|---|---|
| seed0 | 0.7903 | 0.8678 | +0.0775 | 0.7712 | 0.8718 | +0.1006 | +0.0891 | 2.65 / 6.19 |
| seed1 | 0.8172 | 0.8992 | +0.0820 | 0.8046 | 0.8938 | +0.0892 | +0.0856 | 2.28 / 5.43 |
| seed2 | 0.8238 | 0.8579 | +0.0341 | 0.8101 | 0.8590 | +0.0489 | +0.0415 | 2.55 / 6.95 |
| seed3 | 0.7680 | 0.4360 | -0.3320 | 0.7594 | 0.4266 | -0.3328 | -0.3324 | 2.47 / 10.61 |
| seed4 | 0.8249 | 0.4982 | -0.3267 | 0.8098 | 0.4782 | -0.3316 | -0.3291 | 1.81 / 7.53 |
| evalseed | 0.7715 | 0.8323 | +0.0608 | 0.7611 | 0.8283 | +0.0672 | +0.0640 | 2.62 / 3.11 |
| evalseed_h20000 | 0.7685 | 0.7619 | -0.0066 | 0.7589 | 0.7505 | -0.0084 | -0.0075 | 2.80 / 2.98 |
| h20000 | 0.8031 | 0.8805 | +0.0774 | 0.7826 | 0.8900 | +0.1074 | +0.0924 | 2.43 / 6.40 |
| bbox | 0.8120 | 0.8695 | +0.0575 | 0.8001 | 0.8758 | +0.0757 | +0.0666 | 2.65 / 6.19 |
| vtx500 | 0.7881 | 0.8673 | +0.0792 | 0.7688 | 0.8698 | +0.1010 | +0.0901 | 2.65 / 6.19 |

public-seed draws (seed0..4, both rollouts): swap d mean -0.0891, min -0.3328, max +0.1006, n = 10

- library_v3 pitcher: seed0 vs seed0 body-frame change 0.00 deg, cand anchor [-0.373, 0.381, 0.38] cm
- library_v3 pitcher: seed1 vs seed0 body-frame change 0.38 deg, cand anchor [-0.332, 0.352, 0.443] cm
- library_v3 pitcher: seed2 vs seed0 body-frame change 0.64 deg, cand anchor [-0.383, 0.393, 0.464] cm
- library_v3 pitcher: seed3 vs seed0 body-frame change 0.43 deg, cand anchor [-0.356, 0.422, 0.392] cm
- library_v3 pitcher: seed4 vs seed0 body-frame change 0.92 deg, cand anchor [-0.328, 0.346, 0.388] cm
- library_v3 pitcher: evalseed vs seed0 body-frame change 0.42 deg, cand anchor [-0.354, 0.319, 0.367] cm
- library_v3 pitcher: evalseed_h20000 vs seed0 body-frame change 0.51 deg, cand anchor [-0.331, 0.416, 0.612] cm
- library_v3 pitcher: h20000 vs seed0 body-frame change 0.26 deg, cand anchor [-0.361, 0.376, 0.324] cm
- library_v3 pitcher: bbox vs seed0 body-frame change 0.00 deg, cand anchor [-0.659, 2.321, 6.454] cm
- library_v3 pitcher: vtx500 vs seed0 body-frame change 0.00 deg, cand anchor [-0.373, 0.381, 0.38] cm
- library_v3p pitcher: seed0 vs seed0 body-frame change 0.00 deg, cand anchor [-0.245, 1.744, 2.733] cm
- library_v3p pitcher: seed1 vs seed0 body-frame change 0.97 deg, cand anchor [-0.259, 1.579, 2.45] cm
- library_v3p pitcher: seed2 vs seed0 body-frame change 1.70 deg, cand anchor [-0.353, 1.611, 2.615] cm
- library_v3p pitcher: seed3 vs seed0 body-frame change 15.58 deg, cand anchor [0.255, 1.63, 1.877] cm
- library_v3p pitcher: seed4 vs seed0 body-frame change 12.04 deg, cand anchor [0.006, 1.756, 2.381] cm
- library_v3p pitcher: evalseed vs seed0 body-frame change 3.71 deg, cand anchor [-0.29, 1.511, 1.943] cm
- library_v3p pitcher: evalseed_h20000 vs seed0 body-frame change 5.51 deg, cand anchor [-0.181, 1.625, 2.124] cm
- library_v3p pitcher: h20000 vs seed0 body-frame change 0.29 deg, cand anchor [-0.255, 1.619, 2.725] cm
- library_v3p pitcher: bbox vs seed0 body-frame change 0.00 deg, cand anchor [-0.007, 3.67, 9.007] cm
- library_v3p pitcher: vtx500 vs seed0 body-frame change 0.00 deg, cand anchor [-0.245, 1.744, 2.733] cm

### Registration of the submitted meshes at Kaggle's eval seeds (GT-free; host = public scan)

Mode = the registration with most neighbours within 5 deg over all seeds and hosts. "dev" = symmetric body-frame distance from the mode; "ident" = symmetric distance from identity (a correct registration of a mesh built in the scan frame is a few degrees; > 90 = flip).

| mesh | host faces | eval seeds (ep/slot) | eval dev from mode (deg) | eval ident (deg) | public seeds | public dev max | public flips | eval flips |
|---|---|---|---|---|---|---|---|---|
| library_v3/beige_cup | full | 8/0, 10/1 | 0.0, 3.6 | 3.6, 3.2 | 1 | 4.6 | 0 | 0 |
| library_v3/beige_cup | 20000 | 8/0, 10/1 | 0.1, 3.9 | 3.6, 3.5 | 1 | 4.2 | 0 | 0 |
| library_v3/beige_cup | 4096 | 8/0, 10/1 | 0.3, 0.4 | 3.6, 3.6 | 1 | 0.5 | 0 | 0 |
| library_v3/blue_cup | full | 10/0, 14/0, 20/0, 32/0, 33/0 | 0.0, 0.5, 0.8, 0.7, 0.6 | 1.7, 1.3, 0.9, 1.0, 1.1 | 5 | 1.0 | 0 | 0 |
| library_v3/blue_cup | 20000 | 10/0, 14/0, 20/0, 32/0, 33/0 | 0.3, 0.5, 0.7, 0.7, 0.3 | 1.8, 1.3, 1.0, 1.0, 1.4 | 5 | 0.7 | 0 | 0 |
| library_v3/blue_cup | 4096 | 10/0, 14/0, 20/0, 32/0, 33/0 | 0.4, 0.5, 1.0, 0.8, 0.8 | 2.1, 1.3, 0.7, 0.9, 0.9 | 5 | 0.8 | 0 | 0 |
| library_v3/mini_dust_pan | full | 19/1, 38/0 | 0.0, 1.1 | 2.3, 2.7 | 3 | 0.7 | 0 | 0 |
| library_v3/mini_dust_pan | 20000 | 19/1, 38/0 | 0.7, 1.1 | 2.2, 2.7 | 3 | 0.7 | 0 | 0 |
| library_v3/mini_dust_pan | 4096 | 19/1, 38/0 | 0.2, 1.4 | 2.3, 2.8 | 3 | 1.3 | 0 | 0 |
| library_v3/mini_sweeper | full | 19/0, 30/0 | 0.0, 0.7 | 3.1, 2.8 | 2 | 0.9 | 0 | 0 |
| library_v3/mini_sweeper | 20000 | 19/0, 30/0 | 0.4, 0.4 | 2.8, 2.9 | 2 | 179.5 | 1 | 0 |
| library_v3/mini_sweeper | 4096 | 19/0, 30/0 | 0.9, 179.9 | 3.4, 177.7 | 2 | 0.6 | 0 | 1 |
| library_v3/plastic_dish_rack | full | 14/1, 15/0, 16/0, 28/0, 30/1 | 0.0, 0.6, 1.4, 0.4, 0.7 | 0.5, 1.0, 1.9, 0.6, 1.1 | 5 | 1.4 | 0 | 0 |
| library_v3/plastic_dish_rack | 20000 | 14/1, 15/0, 16/0, 28/0, 30/1 | 0.7, 0.2, 0.9, 0.7, 0.9 | 0.9, 0.4, 1.3, 1.1, 1.2 | 5 | 1.5 | 0 | 0 |
| library_v3/plastic_dish_rack | 4096 | 14/1, 15/0, 16/0, 28/0, 30/1 | 0.7, 0.5, 0.6, 1.1, 1.0 | 0.4, 0.8, 1.0, 1.6, 1.3 | 5 | 2.2 | 0 | 0 |
| library_v3/water_pitcher | full | 20/1 | 0.0 | 2.6 | 2 | 0.6 | 0 | 0 |
| library_v3/water_pitcher | 20000 | 20/1 | 0.5 | 2.8 | 2 | 0.4 | 0 | 0 |
| library_v3/water_pitcher | 4096 | 20/1 | 0.4 | 2.4 | 2 | 0.6 | 0 | 0 |
| library_v3/white_pot | full | 1/0, 3/0, 5/0, 6/0, 8/1, 28/1 | 0.0, 1.0, 0.3, 1.0, 2.5, 1.6 | 1.6, 2.0, 1.8, 1.7, 2.4, 1.8 | 9 | 2.1 | 0 | 0 |
| library_v3/white_pot | 20000 | 1/0, 3/0, 5/0, 6/0, 8/1, 28/1 | 1.0, 1.7, 1.5, 1.4, 1.1, 1.4 | 1.7, 1.8, 1.6, 1.6, 1.8, 1.7 | 9 | 1.4 | 0 | 0 |
| library_v3/white_pot | 4096 | 1/0, 3/0, 5/0, 6/0, 8/1, 28/1 | 0.5, 1.0, 1.5, 1.0, 0.8, 0.8 | 1.6, 1.5, 1.7, 1.5, 1.8, 1.7 | 9 | 1.6 | 0 | 0 |
| library_v3/white_pot_lid | full | 1/1 | 0.0 | 1.6 | 2 | 2.3 | 0 | 0 |
| library_v3/white_pot_lid | 20000 | 1/1 | 0.4 | 1.8 | 2 | 0.8 | 0 | 0 |
| library_v3/white_pot_lid | 4096 | 1/1 | 0.7 | 1.1 | 2 | 1.2 | 0 | 0 |
| library_v3/wooden_piece_1 | full | 25/0 | 0.0 | 0.3 | 2 | 0.5 | 0 | 0 |
| library_v3/wooden_piece_1 | 20000 | 25/0 | 1.2 | 1.1 | 2 | 0.3 | 0 | 0 |
| library_v3/wooden_piece_1 | 4096 | 25/0 | 0.2 | 0.2 | 2 | 0.3 | 0 | 0 |
| library_v3/wooden_piece_2 | full | 25/1 | 0.0 | 0.7 | 2 | 0.5 | 0 | 0 |
| library_v3/wooden_piece_2 | 20000 | 25/1 | 0.1 | 0.7 | 2 | 179.2 | 1 | 0 |
| library_v3/wooden_piece_2 | 4096 | 25/1 | 0.1 | 0.7 | 2 | 0.4 | 0 | 0 |
| library_v2/mini_sweeper | full | 19/0, 30/0 | 0.0, 0.2 | 2.5, 2.5 | 2 | 1.0 | 0 | 0 |
| library_v2/mini_sweeper | 20000 | 19/0, 30/0 | 0.6, 0.2 | 2.6, 2.5 | 2 | 179.8 | 1 | 0 |
| library_v2/mini_sweeper | 4096 | 19/0, 30/0 | 0.4, 179.9 | 2.5, 178.1 | 2 | 0.6 | 0 | 1 |
| library_v3p/water_pitcher | full | 20/1 | 3.7 | 3.1 | 2 | 2.7 | 0 | 0 |
| library_v3p/water_pitcher | 20000 | 20/1 | 5.5 | 3.0 | 2 | 2.0 | 0 | 0 |
| library_v3p/water_pitcher | 4096 | 20/1 | 8.1 | 4.2 | 2 | 2.3 | 0 | 0 |
| library_v3x/beige_cup | full | 8/0, 10/1 | 0.0, 0.5 | 4.0, 3.8 | 1 | 0.5 | 0 | 0 |
| library_v3x/beige_cup | 20000 | 8/0, 10/1 | 0.3, 0.7 | 4.3, 3.8 | 1 | 0.0 | 0 | 0 |
| library_v3x/beige_cup | 4096 | 8/0, 10/1 | 3.7, 3.0 | 2.0, 3.1 | 1 | 2.3 | 0 | 0 |

### Host-scan resolution (welded, then decimated; registration only)

| ep | objects | base AUC | h50000 dAUC | h20000 dAUC | h4096 dAUC |
|---|---|---|---|---|---|
| 2 | white_pot + white_pot_lid | 0.9823 | -0.0032 | -0.0013 | -0.0003 |
| 13 | blue_cup + plastic_dish_rack | 0.9605 | +0.0078 | +0.0046 | +0.0115 |
| 18 | mini_sweeper + mini_dust_pan | 0.9380 | -0.0048 | -0.0166 | +0.0174 |
| 22 | blue_cup + water_pitcher | 0.8710 | +0.0066 | +0.0149 | +0.0050 |
| 24 | wooden_piece_1 + wooden_piece_2 | 0.8117 | -0.0154 | -0.4235 | +0.0007 |
| 31 | mini_sweeper + plastic_dish_rack | 0.8050 | -0.7093 | -0.7093 | +0.0559 |
| mean abs | | | 0.1245 | 0.1950 | 0.0151 |
| mean signed | | | -0.1197 | -0.1885 | +0.0150 |

Other metrics (base -> variant), SP_SR / MP_SR / MPPE_cm / RPE_cm:
- ep2 (base SP 1.0, MP 1.0, MPPE 0.7324, RPE 1.435): h50000: MPPE +0.03 RPE -0.04; h20000: MPPE +0.01 RPE -0.20; h4096: MPPE +0.00 RPE -0.14
- ep13 (base SP 1.0, MP 1.0, MPPE 1.0632, RPE 1.3815): h50000: MPPE -0.13 RPE -0.07; h20000: MPPE -0.04 RPE -0.01; h4096: MPPE -0.19 RPE -0.05
- ep18 (base SP 1.0, MP 1.0, MPPE 1.1864, RPE 1.8374): h50000: MPPE +0.01 RPE -0.02; h20000: MPPE +0.09 RPE +0.07; h4096: MPPE -0.04 RPE -0.09
- ep22 (base SP 1.0, MP 1.0, MPPE 1.8003, RPE 1.2222): h50000: MPPE -0.05 RPE +0.00; h20000: MPPE -0.16 RPE -0.08; h4096: MPPE -0.03 RPE +0.04
- ep24 (base SP 1.0, MP 1.0, MPPE 2.3599, RPE 0.9832): h50000: MPPE +0.24 RPE -0.07; h20000: MPPE +2.72 RPE -0.04 ['SP_SR', 'MP_SR'] flips; h4096: MPPE +0.02 RPE -0.05
- ep31 (base SP 1.0, MP 1.0, MPPE 2.011, RPE 1.8848): h50000: MPPE +17.39 RPE +22.41 ['SP_SR', 'MP_SR'] flips; h20000: MPPE +17.40 RPE +22.47 ['SP_SR', 'MP_SR'] flips; h4096: MPPE -0.10 RPE -0.12

### Pitcher registration over 30 seeds (from Kaggle's eval-20 seed 20000161), host = public scan (GT-free)

Distance = body-frame rotation from identity (our meshes are built in the scan frame). Yaw is about the scan z.

| mesh | host faces | yaw min / median / max (deg) | rot from identity median / max (deg) | seeds > 5 deg from the median pose | eval seed yaw / rot |
|---|---|---|---|---|---|
| library_v3/water_pitcher | full | -2.7 / -1.2 / 0.0 | 2.3 / 4.0 | 0 of 30 | -1.6 / 2.6 |
| library_v3/water_pitcher | 20000 | -2.5 / -1.2 / -0.2 | 2.3 / 3.6 | 0 of 30 | -1.3 / 2.8 |
| library_v3/water_pitcher | 4096 | -2.3 / -1.1 / -0.2 | 2.4 / 3.4 | 0 of 30 | -1.2 / 2.4 |
| library_v3p/water_pitcher | full | -14.2 / -0.1 / 7.0 | 6.9 / 15.4 | 20 of 30 | 1.5 / 3.1 |
| library_v3p/water_pitcher | 20000 | -10.7 / 2.2 / 6.9 | 5.6 / 11.9 | 10 of 30 | -0.3 / 3.0 |
| library_v3p/water_pitcher | 4096 | -10.8 / 3.2 / 6.9 | 5.4 / 11.8 | 4 of 30 | -2.7 / 4.2 |

### Fixed Kaggle eval seed, host = public scan welded + decimated to N faces (GT-free)

Cell = body-frame rotation from identity (deg); **bold** = flip (> 90 deg).

| mesh | eval seed | full | 50000 | 30000 | 20000 | 16000 | 12000 | 8192 | 6000 | 4096 | 3000 | 2000 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| library_v3/mini_sweeper | 19000057 | 3.1 | 2.7 | 3.0 | 2.8 | **178** | 2.9 | 2.6 | 2.7 | 3.4 | 2.8 | 2.9 |
| library_v3/mini_sweeper | 30000090 | 2.8 | 3.0 | 2.9 | 2.9 | 3.0 | 2.8 | 3.1 | 3.3 | **178** | 3.2 | 2.8 |
| library_v3/water_pitcher | 20000161 | 2.6 | 2.6 | 2.4 | 2.8 | 2.5 | 2.5 | 2.4 | 2.5 | 2.4 | 2.7 | 2.2 |
| library_v3p/water_pitcher | 20000161 | 3.1 | 3.7 | 7.7 | 3.0 | 3.8 | 3.6 | 3.3 | 9.2 | 4.2 | 8.9 | 3.8 |
| library_v3/wooden_piece_1 | 25000075 | 0.3 | 0.5 | 0.3 | 1.1 | 0.3 | 1.1 | 0.7 | 1.0 | 0.2 | 0.9 | 0.7 |
| library_v3/wooden_piece_2 | 25000176 | 0.7 | 0.8 | 1.1 | 0.7 | 0.7 | 0.5 | 0.8 | 0.4 | 0.7 | 0.6 | 0.6 |
