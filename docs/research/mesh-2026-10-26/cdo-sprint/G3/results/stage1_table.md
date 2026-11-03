# G3 stage-1 screen [D]: 6 seeds 3001-3006, roster emptied, one scoring per generated mesh

Public scans stand in for the hidden scans. Single-image models: the GT-free Sim(3) copy; Pixal3D-MV: the output in
our object frame. CD-O in cm (median / mean of 6 seeds); W30 and FLIP = share of seeds with rotation error > 30 /
> 90 deg; ADD and anchor = median over the seeds, mm (of the screened copy in our track frame, not of the placed
copy). 13h = the 13h mesh's 50-seed audit median (C4), so compare loosely (6 seeds, best-of-N here).
Pick: T4 = one of the 4 lowest CD-O medians (stage 2, "cdo_top4").

468 records, 0 errors

## white_pot (13h 50-seed CD-O median 0.2861; 144 meshes; 1 with stage-1 CD-O median below it)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 48 | 0.3197 | 0.5098 | 1 |
| hy21 | 48 | 0.3504 | 0.6210 | 4 |
| trellis2 | 48 | 0.2404 | 0.4889 | 3 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g3/trellis2/ep45_white_pot_k9_s2025 | 0.2404 | 0.2406 | 0.0 | 0.0 | 4.49 | 4.27 | 9.38 / 2.79 | T4 |
| 2 | g3/trellis2/ep42_white_pot_k240_s2025 | 0.3094 | 0.3098 | 0.0 | 0.0 | 5.37 | 2.62 | 10.52 / 3.41 | T4 |
| 3 | g3/sam3d/ep2_white_pot_k258_s42 | 0.3197 | 0.3192 | 0.0 | 0.0 | 5.79 | 5.52 | 12.74 / 3.48 | T4 |
| 4 | g3/trellis2/ep42_white_pot_k237_s2025 | 0.3221 | 0.3234 | 0.0 | 0.0 | 5.82 | 3.06 | 8.91 / 3.29 | T4 |
| 5 | g3/trellis2/ep45_white_pot_k6_s2025 | 0.3271 | 0.3276 | 0.0 | 0.0 | 10.98 | 10.17 | 12.16 / 3.45 |  |
| 6 | g3/trellis2/ep2_white_pot_k240_s123 | 0.3341 | 0.3340 | 0.0 | 0.0 | 2.63 | 2.30 | 9.32 / 3.20 |  |
| 7 | g3/trellis2/ep45_white_pot_k6_s7 | 0.3350 | 0.3394 | 0.0 | 0.0 | 10.02 | 8.84 | 10.79 / 3.45 |  |
| 8 | g3/sam3d/ep42_white_pot_k237_s42 | 0.3364 | 0.3365 | 0.0 | 0.0 | 6.54 | 4.46 | 12.58 / 3.42 |  |
| 9 | g3/trellis2/ep42_white_pot_k240_s7 | 0.3372 | 0.3383 | 0.0 | 0.0 | 6.17 | 2.85 | 10.55 / 3.40 |  |
| 10 | g3/trellis2/ep45_white_pot_k9_s7 | 0.3457 | 0.3454 | 0.0 | 0.0 | 8.73 | 7.86 | 8.78 / 3.14 |  |
| 11 | g3/trellis2/ep42_white_pot_k237_s42 | 0.3462 | 0.3462 | 0.0 | 0.0 | 6.71 | 4.32 | 12.67 / 3.42 |  |
| 12 | g3/trellis2/ep2_white_pot_k258_s2025 | 0.3500 | 0.3499 | 0.0 | 0.0 | 7.46 | 7.35 | 12.62 / 3.10 |  |

(rows 13-144 omitted; all 144 are in screen/screen6.jsonl)

## plastic_dish_rack (13h 50-seed CD-O median 0.4016; 48 meshes; 1 with stage-1 CD-O median below it)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 16 | 0.5559 | 0.6231 | 0 |
| hy21 | 16 | 0.5312 | 0.7819 | 3 |
| trellis2 | 16 | 0.3953 | 0.4660 | 0 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g3/trellis2/ep27_plastic_dish_rack_k147_s7 | 0.3953 | 0.3969 | 0.0 | 0.0 | 31.26 | 31.09 | 9.47 / 3.36 | T4 |
| 2 | g3/trellis2/ep27_plastic_dish_rack_k147_s123 | 0.4260 | 0.4253 | 0.0 | 0.0 | 29.81 | 26.07 | 9.84 / 4.16 | T4 |
| 3 | g3/trellis2/ep13_plastic_dish_rack_k66_s42 | 0.4376 | 0.4368 | 0.0 | 0.0 | 22.69 | 22.21 | 9.77 / 3.69 | T4 |
| 4 | g3/trellis2/ep27_plastic_dish_rack_k144_s2025 | 0.4394 | 0.4388 | 0.0 | 0.0 | 28.80 | 28.54 | 8.26 / 3.57 | T4 |
| 5 | g3/trellis2/ep27_plastic_dish_rack_k144_s123 | 0.4416 | 0.4425 | 0.0 | 0.0 | 34.30 | 34.08 | 8.92 / 3.49 |  |
| 6 | g3/trellis2/ep27_plastic_dish_rack_k147_s2025 | 0.4463 | 0.4471 | 0.0 | 0.0 | 43.44 | 36.96 | 9.97 / 4.14 |  |
| 7 | g3/trellis2/ep13_plastic_dish_rack_k66_s7 | 0.4605 | 0.4606 | 0.0 | 0.0 | 22.59 | 22.13 | 10.33 / 3.73 |  |
| 8 | g3/trellis2/ep27_plastic_dish_rack_k147_s42 | 0.4619 | 0.4623 | 0.0 | 0.0 | 33.85 | 33.72 | 9.59 / 3.63 |  |
| 9 | g3/trellis2/ep13_plastic_dish_rack_k66_s2025 | 0.4660 | 0.4662 | 0.0 | 0.0 | 23.13 | 22.78 | 9.74 / 3.99 |  |
| 10 | g3/trellis2/ep13_plastic_dish_rack_k69_s7 | 0.4724 | 0.4733 | 0.0 | 0.0 | 22.64 | 22.20 | 11.09 / 3.65 |  |
| 11 | g3/trellis2/ep13_plastic_dish_rack_k69_s123 | 0.4839 | 0.4830 | 0.0 | 0.0 | 11.03 | 10.76 | 10.87 / 3.92 |  |
| 12 | g3/trellis2/ep27_plastic_dish_rack_k144_s42 | 0.4845 | 0.4845 | 0.0 | 0.0 | 26.45 | 26.15 | 9.00 / 3.65 |  |

(rows 13-48 omitted; all 48 are in screen/screen6.jsonl)

## mini_dust_pan (13h 50-seed CD-O median 0.2291; 84 meshes; 6 with stage-1 CD-O median below it)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 24 | 0.2203 | 0.3353 | 0 |
| hy21 | 24 | 0.2246 | 0.3882 | 2 |
| trellis2 | 24 | 0.2831 | 0.5036 | 7 |
| pixal_mv | 12 | 0.2061 | 0.5356 | 8 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g3/pixal_mv/ep39_mini_dust_pan_s2025 | 0.2061 | 0.2067 | 0.0 | 0.0 | 5.62 | 4.75 | 6.87 / 1.44 | T4 |
| 2 | g3/sam3d/ep18_mini_dust_pan_k108_s2025 | 0.2203 | 0.2203 | 0.0 | 0.0 | 6.34 | 6.31 | 5.87 / 1.82 | T4 |
| 3 | g3/pixal_mv/ep39_mini_dust_pan_s123 | 0.2230 | 0.2231 | 0.0 | 0.0 | 5.69 | 4.92 | 6.87 / 1.50 | T4 |
| 4 | g3/sam3d/ep18_mini_dust_pan_k99_s2025 | 0.2234 | 0.2230 | 0.0 | 0.0 | 5.18 | 5.11 | 6.31 / 1.88 | T4 |
| 5 | g3/sam3d/ep18_mini_dust_pan_k108_s7 | 0.2238 | 0.2241 | 0.0 | 0.0 | 3.72 | 3.64 | 6.20 / 1.88 |  |
| 6 | g3/hy21/ep40_mini_dust_pan_k12_s123 | 0.2246 | 0.2249 | 0.0 | 0.0 | 14.17 | 12.92 | 6.36 / 1.91 |  |
| 7 | g3/hy21/ep39_mini_dust_pan_k297_s42 | 0.2292 | 0.2295 | 0.0 | 0.0 | 5.06 | 3.75 | 6.85 / 1.83 |  |
| 8 | g3/pixal_mv/ep39_mini_dust_pan_s7 | 0.2336 | 0.2330 | 0.0 | 0.0 | 5.83 | 4.83 | 6.25 / 1.46 |  |
| 9 | g3/hy21/ep18_mini_dust_pan_k108_s123 | 0.2385 | 0.2391 | 0.0 | 0.0 | 8.74 | 8.45 | 6.56 / 1.84 |  |
| 10 | g3/pixal_mv/ep39_mini_dust_pan_s42 | 0.2404 | 0.2400 | 0.0 | 0.0 | 5.36 | 4.40 | 6.23 / 1.36 |  |
| 11 | g3/sam3d/ep18_mini_dust_pan_k108_s42 | 0.2562 | 0.2564 | 0.0 | 0.0 | 5.78 | 5.66 | 6.81 / 1.94 |  |
| 12 | g3/sam3d/ep39_mini_dust_pan_k297_s42 | 0.2598 | 0.2608 | 0.0 | 0.0 | 6.75 | 5.72 | 6.04 / 1.88 |  |

(rows 13-84 omitted; all 84 are in screen/screen6.jsonl)

## beige_cup (13h 50-seed CD-O median 0.2501; 28 meshes; 0 with stage-1 CD-O median below it)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 8 | 0.3212 | 0.5266 | 0 |
| hy21 | 8 | 0.2618 | 0.4586 | 0 |
| trellis2 | 5 | 0.4353 | 0.7339 | 3 |
| trellis2_1024 | 3 | 0.2680 | 0.2760 | 0 |
| pixal_mv | 4 | 0.2643 | 0.4578 | 0 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g3/hy21/ep11_beige_cup_k0_s2025 | 0.2618 | 0.2624 | 0.0 | 0.0 | 12.16 | 12.12 | 5.67 / 2.46 | T4 |
| 2 | g3/pixal_mv/ep11_beige_cup_s42 | 0.2643 | 0.2661 | 0.0 | 0.0 | 6.45 | 5.86 | 7.88 / 1.78 | T4 |
| 3 | g3/trellis2_1024/ep11_beige_cup_k0_s2025 | 0.2680 | 0.2681 | 0.0 | 0.0 | 26.80 | 26.70 | 4.82 / 2.41 | T4 |
| 4 | g3/trellis2_1024/ep11_beige_cup_k6_s2025 | 0.2760 | 0.2765 | 0.0 | 0.0 | 24.62 | 24.55 | 6.03 / 2.37 | T4 |
| 5 | g3/sam3d/ep11_beige_cup_k6_s7 | 0.3212 | 0.3201 | 0.0 | 0.0 | 19.04 | 19.05 | 8.71 / 2.26 |  |
| 6 | g3/hy21/ep11_beige_cup_k6_s2025 | 0.3219 | 0.3231 | 0.0 | 0.0 | 14.50 | 14.46 | 5.09 / 2.57 |  |
| 7 | g3/sam3d/ep11_beige_cup_k0_s7 | 0.3482 | 0.3487 | 0.0 | 0.0 | 18.94 | 18.89 | 9.04 / 2.08 |  |
| 8 | g3/pixal_mv/ep11_beige_cup_s2025 | 0.3657 | 0.3670 | 0.0 | 0.0 | 4.07 | 3.34 | 7.45 / 1.74 |  |
| 9 | g3/hy21/ep11_beige_cup_k0_s42 | 0.3671 | 0.3672 | 0.0 | 0.0 | 18.39 | 18.39 | 4.40 / 2.54 |  |
| 10 | g3/hy21/ep11_beige_cup_k0_s7 | 0.3875 | 0.3876 | 0.0 | 0.0 | 18.17 | 18.02 | 5.46 / 2.48 |  |
| 11 | g3/sam3d/ep11_beige_cup_k0_s123 | 0.4133 | 0.4130 | 0.0 | 0.0 | 20.95 | 20.85 | 8.04 / 2.24 |  |
| 12 | g3/sam3d/ep11_beige_cup_k6_s123 | 0.4264 | 0.4279 | 0.0 | 0.0 | 22.50 | 22.37 | 7.73 / 2.22 |  |

(rows 13-28 omitted; all 28 are in screen/screen6.jsonl)

## white_pot_lid (13h 50-seed CD-O median 0.2177; 52 meshes; 0 with stage-1 CD-O median below it)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 16 | 0.9833 | 1.3464 | 16 |
| hy21 | 16 | 0.3435 | 0.4485 | 16 |
| trellis2 | 16 | 0.2675 | 0.3963 | 10 |
| pixal_mv | 4 | 0.2462 | 0.3037 | 0 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g3/pixal_mv/ep2_white_pot_lid_s42 | 0.2462 | 0.2463 | 0.0 | 0.0 | 6.69 | 6.65 | 6.99 / 1.67 | T4 |
| 2 | g3/pixal_mv/ep2_white_pot_lid_s2025 | 0.2667 | 0.2663 | 0.0 | 0.0 | 7.89 | 7.75 | 7.05 / 1.63 | T4 |
| 3 | g3/trellis2/ep2_white_pot_lid_k315_s2025 | 0.2675 | 0.2674 | 0.0 | 0.0 | 7.07 | 6.61 | 6.17 / 1.59 | T4 |
| 4 | g3/trellis2/ep2_white_pot_lid_k315_s42 | 0.2737 | 0.2725 | 0.0 | 0.0 | 8.45 | 7.55 | 7.16 / 1.68 | T4 |
| 5 | g3/pixal_mv/ep2_white_pot_lid_s123 | 0.3037 | 0.3037 | 0.0 | 0.0 | 13.95 | 13.48 | 9.31 / 1.76 |  |
| 6 | g3/pixal_mv/ep2_white_pot_lid_s7 | 0.3244 | 0.3246 | 0.0 | 0.0 | 13.75 | 13.28 | 9.49 / 1.77 |  |
| 7 | g3/trellis2/ep2_white_pot_lid_k321_s2025 | 0.3317 | 0.3325 | 0.0 | 0.0 | 9.61 | 7.67 | 8.13 / 1.64 |  |
| 8 | g3/trellis2/ep2_white_pot_lid_k321_s7 | 0.3403 | 0.3486 | 1.0 | 0.0 | 59.12 | 9.09 | 7.95 / 1.65 |  |
| 9 | g3/hy21/ep2_white_pot_lid_k315_s7 | 0.3435 | 0.3436 | 0.5 | 0.0 | 53.87 | 11.73 | 2.52 / 1.67 |  |
| 10 | g3/hy21/ep2_white_pot_lid_k315_s42 | 0.3457 | 0.3430 | 1.0 | 1.0 | 84.97 | 10.43 | 2.77 / 1.67 |  |
| 11 | g3/hy21/ep2_white_pot_lid_k321_s7 | 0.3566 | 0.3552 | 1.0 | 1.0 | 85.16 | 11.32 | 2.09 / 1.65 |  |
| 12 | g3/hy21/ep2_white_pot_lid_k321_s123 | 0.3705 | 0.3695 | 0.667 | 0.667 | 82.74 | 9.45 | 2.06 / 1.67 |  |

(rows 13-52 omitted; all 52 are in screen/screen6.jsonl)

## mini_sweeper (13h 50-seed CD-O median 0.222; 56 meshes; 0 with stage-1 CD-O median below it)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 16 | 0.2394 | 0.4146 | 15 |
| hy21 | 16 | 0.4116 | 0.9273 | 14 |
| trellis2 | 16 | 0.4169 | 0.6371 | 13 |
| pixal_mv | 8 | 0.2392 | 0.4547 | 4 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g3/pixal_mv/ep18_mini_sweeper_s123 | 0.2392 | 0.2387 | 0.0 | 0.0 | 6.52 | 6.33 | 3.49 / 1.45 | T4 |
| 2 | g3/sam3d/ep18_mini_sweeper_k162_s123 | 0.2394 | 0.2402 | 1.0 | 1.0 | 89.53 | 38.14 | 2.26 / 1.92 | T4 |
| 3 | g3/sam3d/ep18_mini_sweeper_k264_s123 | 0.2779 | 0.2769 | 1.0 | 1.0 | 75.15 | 29.62 | 2.04 / 1.86 | T4 |
| 4 | g3/sam3d/ep18_mini_sweeper_k264_s2025 | 0.2807 | 0.2814 | 1.0 | 1.0 | 87.55 | 29.96 | 2.33 / 1.89 | T4 |
| 5 | g3/sam3d/ep18_mini_sweeper_k264_s42 | 0.2820 | 0.2820 | 1.0 | 1.0 | 76.05 | 32.32 | 2.17 / 1.88 |  |
| 6 | g3/sam3d/ep18_mini_sweeper_k162_s42 | 0.2920 | 0.2920 | 1.0 | 1.0 | 77.77 | 36.86 | 2.12 / 1.90 |  |
| 7 | g3/sam3d/ep18_mini_sweeper_k264_s7 | 0.2980 | 0.2974 | 1.0 | 1.0 | 75.31 | 30.16 | 2.23 / 1.91 |  |
| 8 | g3/pixal_mv/ep18_mini_sweeper_s42 | 0.3022 | 0.3024 | 0.0 | 0.0 | 6.52 | 6.13 | 4.24 / 1.54 |  |
| 9 | g3/sam3d/ep18_mini_sweeper_k162_s2025 | 0.3027 | 0.3030 | 1.0 | 1.0 | 83.44 | 38.05 | 2.17 / 1.95 |  |
| 10 | g3/sam3d/ep18_mini_sweeper_k162_s7 | 0.3090 | 0.3082 | 1.0 | 1.0 | 88.58 | 35.69 | 1.95 / 1.80 |  |
| 11 | g3/pixal_mv/ep18_mini_sweeper_s2025 | 0.3232 | 0.3238 | 0.0 | 0.0 | 4.75 | 4.03 | 5.04 / 1.47 |  |
| 12 | g3/pixal_mv/ep18_mini_sweeper_s7 | 0.3448 | 0.3456 | 0.0 | 0.0 | 4.60 | 4.12 | 4.87 / 1.35 |  |

(rows 13-56 omitted; all 56 are in screen/screen6.jsonl)

## wooden_piece_1 (13h 50-seed CD-O median 0.1872; 28 meshes; 13 with stage-1 CD-O median below it)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 8 | 0.1754 | 0.1868 | 8 |
| hy21 | 8 | 0.1633 | 0.1743 | 5 |
| trellis2 | 8 | 0.1781 | 0.3346 | 6 |
| pixal_mv | 4 | 0.1629 | 0.2243 | 0 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g3/pixal_mv/ep24_wooden_piece_1_s7 | 0.1629 | 0.1629 | 0.0 | 0.0 | 4.81 | 4.76 | 2.85 / 2.25 | T4 |
| 2 | g3/hy21/ep24_wooden_piece_1_k3_s2025 | 0.1633 | 0.1639 | 1.0 | 1.0 | 89.67 | 26.74 | 2.58 / 2.36 | T4 |
| 3 | g3/hy21/ep24_wooden_piece_1_k3_s42 | 0.1651 | 0.1670 | 0.167 | 0.167 | 27.00 | 26.43 | 2.79 / 2.36 | T4 |
| 4 | g3/hy21/ep24_wooden_piece_1_k3_s123 | 0.1659 | 0.1660 | 1.0 | 1.0 | 165.74 | 25.89 | 2.62 / 2.38 | T4 |
| 5 | g3/hy21/ep24_wooden_piece_1_k6_s7 | 0.1713 | 0.1717 | 0.0 | 0.0 | 24.43 | 24.24 | 2.86 / 2.37 |  |
| 6 | g3/hy21/ep24_wooden_piece_1_k6_s42 | 0.1743 | 0.1741 | 0.0 | 0.0 | 29.18 | 29.08 | 2.64 / 2.33 |  |
| 7 | g3/sam3d/ep24_wooden_piece_1_k3_s123 | 0.1754 | 0.1757 | 1.0 | 1.0 | 133.32 | 23.68 | 2.57 / 2.46 |  |
| 8 | g3/trellis2/ep24_wooden_piece_1_k6_s7 | 0.1781 | 0.1781 | 0.0 | 0.0 | 25.76 | 25.25 | 2.97 / 2.35 |  |
| 9 | g3/sam3d/ep24_wooden_piece_1_k6_s7 | 0.1790 | 0.1785 | 0.5 | 0.5 | 57.01 | 22.99 | 2.51 / 2.46 |  |
| 10 | g3/hy21/ep24_wooden_piece_1_k3_s7 | 0.1831 | 0.1831 | 0.0 | 0.0 | 27.41 | 26.78 | 2.67 / 2.41 |  |
| 11 | g3/sam3d/ep24_wooden_piece_1_k3_s42 | 0.1840 | 0.1843 | 0.333 | 0.333 | 24.93 | 23.14 | 2.62 / 2.48 |  |
| 12 | g3/sam3d/ep24_wooden_piece_1_k6_s42 | 0.1858 | 0.1863 | 0.833 | 0.833 | 165.38 | 23.27 | 2.64 / 2.55 |  |

(rows 13-28 omitted; all 28 are in screen/screen6.jsonl)

## wooden_piece_2 (13h 50-seed CD-O median 0.1649; 28 meshes; 3 with stage-1 CD-O median below it)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 8 | 0.1600 | 0.1728 | 8 |
| hy21 | 8 | 0.2029 | 0.2374 | 6 |
| trellis2 | 8 | 0.3138 | 0.4145 | 8 |
| pixal_mv | 4 | 0.2845 | 0.5433 | 4 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g3/sam3d/ep24_wooden_piece_2_k9_s42 | 0.1600 | 0.1598 | 0.167 | 0.167 | 17.77 | 16.96 | 2.19 / 2.16 | T4 |
| 2 | g3/sam3d/ep24_wooden_piece_2_k9_s2025 | 0.1643 | 0.1645 | 1.0 | 1.0 | 103.62 | 17.87 | 2.37 / 2.25 | T4 |
| 3 | g3/sam3d/ep24_wooden_piece_2_k6_s2025 | 0.1643 | 0.1647 | 1.0 | 1.0 | 80.17 | 17.21 | 2.41 / 2.24 | T4 |
| 4 | g3/sam3d/ep24_wooden_piece_2_k9_s123 | 0.1660 | 0.1664 | 0.333 | 0.333 | 19.21 | 18.69 | 2.08 / 2.11 | T4 |
| 5 | g3/sam3d/ep24_wooden_piece_2_k9_s7 | 0.1728 | 0.1725 | 0.833 | 0.833 | 157.05 | 18.05 | 2.45 / 2.19 |  |
| 6 | g3/sam3d/ep24_wooden_piece_2_k6_s7 | 0.1761 | 0.1769 | 1.0 | 1.0 | 127.05 | 18.80 | 2.47 / 2.26 |  |
| 7 | g3/hy21/ep24_wooden_piece_2_k6_s42 | 0.2029 | 0.2032 | 1.0 | 1.0 | 80.46 | 17.01 | 2.57 / 2.06 |  |
| 8 | g3/hy21/ep24_wooden_piece_2_k9_s42 | 0.2059 | 0.2082 | 1.0 | 1.0 | 80.87 | 15.43 | 2.61 / 2.06 |  |
| 9 | g3/sam3d/ep24_wooden_piece_2_k6_s42 | 0.2072 | 0.2078 | 1.0 | 1.0 | 126.48 | 19.81 | 2.54 / 2.48 |  |
| 10 | g3/hy21/ep24_wooden_piece_2_k6_s123 | 0.2193 | 0.2199 | 0.0 | 0.0 | 18.93 | 18.69 | 2.84 / 2.13 |  |
| 11 | g3/hy21/ep24_wooden_piece_2_k6_s2025 | 0.2277 | 0.2276 | 0.667 | 0.667 | 103.65 | 17.99 | 3.37 / 2.08 |  |
| 12 | g3/sam3d/ep24_wooden_piece_2_k6_s123 | 0.2309 | 0.2305 | 1.0 | 1.0 | 81.06 | 18.41 | 2.41 / 2.24 |  |

(rows 13-28 omitted; all 28 are in screen/screen6.jsonl)

