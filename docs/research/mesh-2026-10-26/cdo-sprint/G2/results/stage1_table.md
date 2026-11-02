# G2 stage-1 screen [D]: 6 seeds 3001-3006, roster emptied, one scoring per GT-free Sim(3) copy

Public scans stand in for the hidden scans. CD-O in cm (median / mean of 6 seeds); W30 and FLIP = share of seeds
with rotation error > 30 / > 90 deg; ADD and anchor = median over the seeds, mm (of the Sim(3) copy in our track
frame, not of the placed copy). Shipped = the 13f mesh's 50-seed audit median (C4), so compare loosely.
Pick: T4 = one of the 4 lowest CD-O medians (stage 2, "cdo_top4"); A = among the 2 lowest ADD medians with CD-O <=
shipped + 0.005 ("add_ext" when not already T4).

## white_pot (shipped 50-seed CD-O median 0.3107; 72 meshes; 6 with CD-O <= 0.3157)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 24 | 0.2852 | 0.4092 | 1 |
| hy21 | 24 | 0.3027 | 0.4980 | 0 |
| trellis2 | 24 | 0.2948 | 0.3686 | 0 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g2/sam3d/ep44_white_pot_k0_s7 | 0.2852 | 0.2857 | 0.0 | 0.0 | 6.14 | 5.92 | 11.51 / 3.34 | T4 A |
| 2 | g2/trellis2/ep41_white_pot_k279_s2025 | 0.2948 | 0.2949 | 0.0 | 0.0 | 6.58 | 6.28 | 11.14 / 3.04 | T4 A |
| 3 | g2/hy21/ep44_white_pot_k3_s42 | 0.3027 | 0.3025 | 0.0 | 0.0 | 8.37 | 8.28 | 11.27 / 3.32 | T4 |
| 4 | g2/trellis2/ep41_white_pot_k285_s7 | 0.3098 | 0.3133 | 0.0 | 0.0 | 9.84 | 8.91 | 10.35 / 3.30 | T4 |
| 5 | g2/sam3d/ep44_white_pot_k3_s7 | 0.3124 | 0.3127 | 0.0 | 0.0 | 6.79 | 6.54 | 11.47 / 3.24 |  |
| 6 | g2/trellis2/ep41_white_pot_k279_s7 | 0.3146 | 0.3170 | 0.0 | 0.0 | 11.07 | 10.35 | 11.23 / 3.24 |  |
| 7 | g2/hy21/ep44_white_pot_k0_s42 | 0.3165 | 0.3162 | 0.0 | 0.0 | 10.59 | 10.57 | 12.44 / 3.41 |  |
| 8 | g2/hy21/ep44_white_pot_k3_s7 | 0.3188 | 0.3188 | 0.0 | 0.0 | 7.69 | 7.55 | 11.53 / 3.43 |  |
| 9 | g2/trellis2/ep41_white_pot_k285_s2025 | 0.3188 | 0.3189 | 0.0 | 0.0 | 5.24 | 4.54 | 10.04 / 3.35 |  |
| 10 | g2/trellis2/ep44_white_pot_k0_s2025 | 0.3218 | 0.3226 | 0.0 | 0.0 | 9.15 | 9.09 | 11.49 / 3.19 |  |
| 11 | g2/hy21/ep43_white_pot_k303_s42 | 0.3229 | 0.3227 | 0.0 | 0.0 | 9.61 | 3.63 | 11.79 / 3.50 |  |
| 12 | g2/hy21/ep41_white_pot_k279_s42 | 0.3235 | 0.3231 | 0.0 | 0.0 | 5.77 | 5.22 | 11.09 / 3.37 |  |

(rows 13-72 omitted; all 72 are in screen/screen6.jsonl)

## blue_cup (shipped 50-seed CD-O median 0.2646; 72 meshes; 5 with CD-O <= 0.2696)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 24 | 0.2430 | 0.3894 | 1 |
| hy21 | 24 | 0.2448 | 2.0196 | 12 |
| trellis2 | 18 | 0.3641 | 0.6543 | 4 |
| trellis2_1024 | 6 | 0.4295 | 0.5731 | 1 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g2/sam3d/ep22_blue_cup_k159_s7 | 0.2430 | 0.2420 | 0.0 | 0.0 | 18.02 | 17.91 | 6.96 / 2.19 | T4 A |
| 2 | g2/hy21/ep22_blue_cup_k159_s123 | 0.2448 | 0.2455 | 0.0 | 0.0 | 21.28 | 21.11 | 4.95 / 2.49 | T4 |
| 3 | g2/hy21/ep22_blue_cup_k156_s123 | 0.2565 | 0.2561 | 0.0 | 0.0 | 23.80 | 23.56 | 5.56 / 2.59 | T4 |
| 4 | g2/sam3d/ep22_blue_cup_k156_s7 | 0.2615 | 0.2621 | 0.0 | 0.0 | 18.38 | 17.85 | 7.74 / 2.39 | T4 A |
| 5 | g2/sam3d/ep21_blue_cup_k15_s42 | 0.2630 | 0.2623 | 0.0 | 0.0 | 26.88 | 26.84 | 4.11 / 2.30 |  |
| 6 | g2/sam3d/ep21_blue_cup_k18_s42 | 0.2837 | 0.2842 | 1.0 | 1.0 | 118.64 | 20.60 | 3.76 / 2.34 |  |
| 7 | g2/hy21/ep22_blue_cup_k156_s42 | 0.2968 | 0.2969 | 0.0 | 0.0 | 23.97 | 23.71 | 4.12 / 2.25 |  |
| 8 | g2/hy21/ep22_blue_cup_k159_s42 | 0.2989 | 0.2991 | 0.0 | 0.0 | 23.75 | 23.71 | 3.77 / 2.25 |  |
| 9 | g2/sam3d/ep22_blue_cup_k156_s42 | 0.2996 | 0.2982 | 0.0 | 0.0 | 28.59 | 28.55 | 4.98 / 2.27 |  |
| 10 | g2/sam3d/ep12_blue_cup_k156_s42 | 0.3248 | 0.3237 | 0.0 | 0.0 | 13.84 | 13.36 | 5.22 / 2.56 |  |
| 11 | g2/sam3d/ep21_blue_cup_k18_s123 | 0.3279 | 0.3278 | 0.0 | 0.0 | 22.99 | 22.87 | 5.18 / 2.43 |  |
| 12 | g2/sam3d/ep12_blue_cup_k156_s7 | 0.3285 | 0.3282 | 0.0 | 0.0 | 17.16 | 16.80 | 6.37 / 2.63 |  |

(rows 13-72 omitted; all 72 are in screen/screen6.jsonl)

## plastic_dish_rack (shipped 50-seed CD-O median 0.4182; 72 meshes; 1 with CD-O <= 0.4232)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 24 | 0.5353 | 0.6020 | 0 |
| hy21 | 24 | 0.4027 | 0.6665 | 0 |
| trellis2 | 24 | 0.4294 | 0.5026 | 0 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g2/hy21/ep31_plastic_dish_rack_k282_s123 | 0.4027 | 0.4024 | 0.0 | 0.0 | 9.91 | 7.89 | 11.75 / 4.61 | T4 A |
| 2 | g2/hy21/ep31_plastic_dish_rack_k285_s123 | 0.4279 | 0.4288 | 0.0 | 0.0 | 8.71 | 7.26 | 10.60 / 4.34 | T4 |
| 3 | g2/trellis2/ep31_plastic_dish_rack_k282_s42 | 0.4294 | 0.4284 | 0.0 | 0.0 | 8.82 | 7.67 | 11.48 / 3.86 | T4 |
| 4 | g2/hy21/ep12_plastic_dish_rack_k24_s42 | 0.4418 | 0.4416 | 0.0 | 0.0 | 26.34 | 26.26 | 9.94 / 4.23 | T4 |
| 5 | g2/hy21/ep12_plastic_dish_rack_k24_s7 | 0.4499 | 0.4497 | 0.0 | 0.0 | 23.92 | 23.50 | 10.21 / 4.57 |  |
| 6 | g2/trellis2/ep31_plastic_dish_rack_k285_s7 | 0.4503 | 0.4511 | 0.0 | 0.0 | 6.29 | 3.37 | 11.41 / 3.89 |  |
| 7 | g2/trellis2/ep31_plastic_dish_rack_k282_s7 | 0.4526 | 0.4511 | 0.0 | 0.0 | 8.98 | 5.47 | 12.49 / 4.06 |  |
| 8 | g2/trellis2/ep26_plastic_dish_rack_k144_s7 | 0.4657 | 0.4653 | 0.0 | 0.0 | 15.92 | 15.60 | 12.14 / 3.79 |  |
| 9 | g2/hy21/ep12_plastic_dish_rack_k24_s123 | 0.4685 | 0.4692 | 0.0 | 0.0 | 27.05 | 26.84 | 8.84 / 4.14 |  |
| 10 | g2/trellis2/ep31_plastic_dish_rack_k285_s42 | 0.4700 | 0.4710 | 0.0 | 0.0 | 8.38 | 5.76 | 10.11 / 3.91 |  |
| 11 | g2/trellis2/ep31_plastic_dish_rack_k282_s123 | 0.4701 | 0.4707 | 0.0 | 0.0 | 6.83 | 4.73 | 11.68 / 3.85 |  |
| 12 | g2/trellis2/ep31_plastic_dish_rack_k285_s2025 | 0.4707 | 0.4718 | 0.0 | 0.0 | 9.05 | 7.71 | 10.94 / 4.03 |  |

(rows 13-72 omitted; all 72 are in screen/screen6.jsonl)

## water_pitcher (shipped 50-seed CD-O median 0.3713; 48 meshes; 0 with CD-O <= 0.3763)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 16 | 0.6718 | 0.8039 | 0 |
| hy21 | 16 | 0.3868 | 1.2311 | 8 |
| trellis2 | 16 | 0.4653 | 0.7258 | 1 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | g2/hy21/ep22_water_pitcher_k174_s123 | 0.3868 | 0.3866 | 0.0 | 0.0 | 35.14 | 33.60 | 9.95 / 3.81 | T4 |
| 2 | g2/trellis2/ep22_water_pitcher_k33_s42 | 0.4653 | 0.4647 | 0.0 | 0.0 | 28.56 | 27.68 | 9.61 / 3.09 | T4 |
| 3 | g2/trellis2/ep22_water_pitcher_k33_s2025 | 0.4729 | 0.4723 | 0.0 | 0.0 | 27.59 | 26.36 | 11.78 / 3.11 | T4 |
| 4 | g2/trellis2/ep22_water_pitcher_k33_s7 | 0.4777 | 0.4774 | 0.0 | 0.0 | 29.59 | 26.91 | 12.74 / 2.98 | T4 |
| 5 | g2/trellis2/ep21_water_pitcher_k171_s123 | 0.5456 | 0.5462 | 0.0 | 0.0 | 37.51 | 33.30 | 12.64 / 4.01 |  |
| 6 | g2/trellis2/ep22_water_pitcher_k33_s123 | 0.5585 | 0.5578 | 0.0 | 0.0 | 22.29 | 21.64 | 13.60 / 3.07 |  |
| 7 | g2/trellis2/ep22_water_pitcher_k174_s2025 | 0.6003 | 0.5990 | 0.0 | 0.0 | 26.05 | 24.94 | 16.12 / 2.93 |  |
| 8 | g2/hy21/ep22_water_pitcher_k33_s123 | 0.6098 | 0.6098 | 0.0 | 0.0 | 36.97 | 36.02 | 8.02 / 4.09 |  |
| 9 | g2/trellis2/ep21_water_pitcher_k33_s123 | 0.6196 | 0.6183 | 0.0 | 0.0 | 34.78 | 33.33 | 14.96 / 3.05 |  |
| 10 | g2/trellis2/ep21_water_pitcher_k171_s2025 | 0.6490 | 0.6493 | 0.0 | 0.0 | 20.51 | 19.12 | 14.14 / 3.60 |  |
| 11 | g2/sam3d/ep21_water_pitcher_k171_s123 | 0.6718 | 0.6648 | 0.0 | 0.0 | 34.97 | 34.03 | 9.54 / 3.91 |  |
| 12 | g2/sam3d/ep22_water_pitcher_k174_s42 | 0.7060 | 0.7107 | 0.0 | 0.0 | 33.77 | 30.04 | 11.13 / 3.89 |  |

(rows 13-48 omitted; all 48 are in screen/screen6.jsonl)

