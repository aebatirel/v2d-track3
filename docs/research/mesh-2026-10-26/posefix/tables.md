### Before = stored 9a+ runs

| ep | stored run | equal (AUC, SR, MPPE, RPE, per-object AUC) |
|---|---|---|
| 0 | <scratch>/cdo_c0/runs/c0/ep0.json | yes |
| 2 | <scratch>/cdo_c0/runs/c0/ep2.json | yes |
| 11 | <scratch>/cdo_c1/t1/auc/runs/single_ep11.json | yes |
| 12 | <scratch>/cdo_c0/runs/single_plastic_dish_rack/ep12.json | yes |
| 13 | <scratch>/cdo_c0/runs/single_plastic_dish_rack/ep13.json | yes |
| 18 | <scratch>/cdo_c1/t2/auc/runs/single_mini_dust_pan/ep18.json | yes |
| 21 | <scratch>/cdo_c0/runs/base/ep21.json | yes |
| 22 | <scratch>/cdo_c0/runs/base/ep22.json | yes |
| 23 | - | no stored run |
| 24 | - | no stored run |
| 26 | <scratch>/cdo_c0/runs/c0/ep26.json | yes |
| 27 | <scratch>/cdo_c0/runs/c0/ep27.json | yes |
| 31 | <scratch>/cdo_c0/runs/c0/ep31.json | yes |
| 39 | <scratch>/cdo_c1/t2/auc/runs/single_mini_dust_pan/ep39.json | yes |
| 40 | <scratch>/cdo_c1/t2/auc/runs/single_mini_dust_pan/ep40.json | yes |
| 41 | <scratch>/cdo_c0/runs/c0/ep41.json | yes |
| 42 | <scratch>/cdo_c0/runs/c0/ep42.json | yes |
| 43 | <scratch>/cdo_c0/runs/c0/ep43.json | yes |
| 44 | <scratch>/cdo_c0/runs/c0/ep44.json | yes |
| 45 | <scratch>/cdo_c0/runs/c0/ep45.json | yes |

### Per episode (perception, kit chain; d = after - before)

| ep | objects | AUC before | MPPE before cm | RPE before cm | A segments: shifted / unresolved / all, max shift mm | dAUC A | dMPPE A | dRPE A | dADD A cm (mean of objects) | dAUC B | dAUC C | dAUC D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot, white_pot_lid | 0.4963 | 12.161 | 22.876 | 2 / 1 / 3, 6.9 | -0.0013 | +0.187 | +0.123 | +0.190 | -0.0013 | +0.0000 | +0.0000 |
| 2 | white_pot, white_pot_lid | 0.9783 | 0.726 | 0.864 | 5 / 0 / 6, 24.4 | -0.0110 | +0.222 | +0.182 | +0.207 | -0.0110 | -0.0003 | -0.0042 |
| 11 | blue_cup, beige_cup | 0.9058 | 1.574 | 1.695 | 0 / 1 / 4, 0.0 | +0.0000 | +0.000 | +0.000 | +0.000 | +0.0027 | +0.0000 | +0.0000 |
| 12 | blue_cup, plastic_dish_rack | 0.9580 | 1.126 | 1.235 | 4 / 0 / 5, 17.4 | -0.0032 | +0.035 | +0.186 | +0.034 | -0.0032 | -0.0291 | -0.0265 |
| 13 | blue_cup, plastic_dish_rack | 0.9661 | 1.018 | 1.218 | 2 / 1 / 3, 8.8 | -0.0238 | +0.178 | +0.347 | +0.178 | -0.0238 | +0.0000 | +0.0000 |
| 18 | mini_sweeper, mini_dust_pan | 0.9628 | 1.052 | 1.591 | 3 / 0 / 4, 6.7 | +0.0061 | -0.018 | +0.102 | -0.011 | +0.0061 | -0.0288 | +0.0000 |
| 21 | blue_cup, water_pitcher | 0.8325 | 2.148 | 1.255 | 2 / 0 / 6, 6.9 | -0.0094 | +0.063 | +0.095 | +0.063 | -0.0094 | -0.0084 | +0.0000 |
| 22 | blue_cup, water_pitcher | 0.8710 | 1.800 | 1.222 | 4 / 0 / 5, 8.1 | -0.0082 | +0.028 | +0.157 | +0.029 | -0.0082 | -0.0145 | +0.0000 |
| 23 | wooden_piece_1, wooden_piece_2 | 0.0414 | 16.140 | 18.569 | 2 / 1 / 4, 17.9 | +0.0000 | -0.573 | +0.177 | -0.512 | +0.0000 | +0.0000 | +0.0000 |
| 24 | wooden_piece_1, wooden_piece_2 | 0.8117 | 2.360 | 0.983 | 2 / 1 / 4, 15.7 | -0.0061 | +0.134 | +0.087 | +0.133 | -0.0061 | -0.0030 | +0.0000 |
| 26 | plastic_dish_rack, white_pot | 0.9775 | 0.781 | 1.052 | 4 / 1 / 4, 12.3 | -0.0018 | +0.093 | +0.104 | +0.070 | -0.0018 | -0.0097 | -0.0133 |
| 27 | plastic_dish_rack, white_pot | 0.9879 | 0.536 | 0.840 | 3 / 0 / 3, 24.3 | -0.0044 | +0.070 | +0.179 | +0.065 | -0.0044 | -0.0044 | -0.0044 |
| 31 | mini_sweeper, plastic_dish_rack | 0.8611 | 1.854 | 1.706 | 3 / 1 / 4, 3.0 | -0.0181 | +0.069 | +0.008 | +0.067 | -0.0181 | +0.0000 | +0.0000 |
| 39 | mini_dust_pan | 0.9755 | 0.856 | 0.000 | 2 / 0 / 3, 10.9 | -0.0176 | +0.291 | +0.000 | +0.279 | -0.0176 | +0.0018 | +0.0000 |
| 40 | mini_dust_pan | 0.9803 | 0.648 | 0.000 | 2 / 0 / 2, 4.9 | -0.0070 | +0.122 | +0.000 | +0.117 | -0.0070 | +0.0000 | +0.0000 |
| 41 | white_pot | 0.9893 | 0.601 | 0.000 | 2 / 0 / 3, 8.1 | -0.0342 | +0.479 | +0.000 | +0.458 | -0.0342 | +0.0000 | +0.0000 |
| 42 | white_pot | 0.9920 | 0.598 | 0.000 | 2 / 0 / 2, 7.3 | -0.0056 | +0.095 | +0.000 | +0.080 | -0.0056 | +0.0000 | +0.0000 |
| 43 | white_pot | 0.9778 | 0.747 | 0.000 | 2 / 0 / 2, 12.3 | -0.0232 | +0.367 | +0.000 | +0.292 | -0.0232 | -0.0058 | +0.0000 |
| 44 | white_pot | 0.9975 | 0.446 | 0.000 | 2 / 0 / 2, 10.0 | -0.0291 | +0.468 | +0.000 | +0.454 | -0.0291 | +0.0000 | +0.0000 |
| 45 | white_pot | 0.9759 | 0.723 | 0.000 | 2 / 0 / 2, 6.6 | -0.0166 | +0.258 | +0.000 | +0.246 | -0.0166 | +0.0000 | +0.0000 |

### Means over the 20 episodes

| variant | episodes changed | mean dAUC | min dAUC (ep) | max dAUC | mean dMPPE cm | mean dRPE cm | mean dSP-SR | mean dMP-SR | mean dADD cm | mean dAUC 41-45 |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 19 | -0.01073 | -0.0342 (41) | +0.0061 | +0.1284 | +0.0874 | +0.000 | -0.050 | +0.1220 | -0.02174 |
| B | 20 | -0.01059 | -0.0342 (41) | +0.0061 | +0.1270 | +0.0846 | +0.000 | -0.050 | +0.1207 | -0.02174 |
| C | 17 | -0.00511 | -0.0291 (12) | +0.0018 | +0.0528 | +0.0447 | +0.000 | -0.050 | +0.0504 | -0.00116 |
| D | 4 | -0.00242 | -0.0265 (12) | +0.0000 | +0.0215 | +0.0418 | +0.000 | +0.000 | +0.0208 | +0.00000 |

### Direction check (cos of push vs correction = mocap - ours)

| variant | shifted segments | cos <= 0 | median cos | with pair constraint: n / cos <= 0 | table only: n / cos <= 0 | falsified (cos <= 0 on > half) |
|---|---|---|---|---|---|---|
| A | 50 | 28 | -0.113 | 16 / 5 | 34 / 23 | yes |
| B | 51 | 28 | -0.086 | 17 / 5 | 34 / 23 | yes |
| C | 22 | 14 | -0.259 | 7 / 2 | 15 / 12 | yes |
| D | 4 | 3 | -0.113 | 4 / 3 | 0 / 0 | yes |

#### Variant A segments

| ep | object | frames | status | pair | push mm | correction mm | correction along push mm | cos | pos err before mm | after (same alignment) mm |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot | 0-37 | shift_t | no | 5.9 | 0.8 | +0.1 | +0.160 | 1.4 | 5.8 |
| 0 | white_pot | 281-372 | shift_t | yes | 6.9 | 3.1 | +2.2 | +0.718 | 3.4 | 5.3 |
| 2 | white_pot | 0-39 | shift_t | no | 7.9 | 0.4 | -0.0 | -0.079 | 1.2 | 8.0 |
| 2 | white_pot_lid | 0-44 | shift_lift | yes | 24.4 | 6.7 | +2.3 | +0.340 | 6.7 | 23.0 |
| 2 | white_pot | 234-267 | shift_t | yes | 7.3 | 1.4 | +1.3 | +0.942 | 1.9 | 6.1 |
| 2 | white_pot_lid | 310-342 | inherited | yes | 8.3 | 5.3 | +3.1 | +0.590 | 5.6 | 6.9 |
| 2 | white_pot | 336-342 | shift_t | no | 8.3 | 3.3 | +1.3 | +0.390 | 4.2 | 7.9 |
| 12 | plastic_dish_rack | 0-137 | shift_t | no | 5.1 | 8.4 | -6.6 | -0.784 | 8.8 | 13.0 |
| 12 | blue_cup | 0-19 | shift_t | yes | 4.8 | 0.8 | +0.5 | +0.624 | 1.2 | 4.5 |
| 12 | plastic_dish_rack | 140-180 | shift_t | no | 3.4 | 10.3 | -9.1 | -0.878 | 10.4 | 13.5 |
| 12 | blue_cup | 143-180 | shift_t | yes | 17.4 | 16.9 | -15.0 | -0.887 | 17.0 | 33.3 |
| 13 | plastic_dish_rack | 0-189 | shift_t | no | 8.8 | 8.0 | -3.1 | -0.394 | 8.2 | 14.0 |
| 13 | blue_cup | 0-14 | shift_t | yes | 2.6 | 1.0 | +0.9 | +0.895 | 1.3 | 2.1 |
| 18 | mini_sweeper | 0-26 | shift_t | no | 5.1 | 0.6 | -0.5 | -0.778 | 0.9 | 5.6 |
| 18 | mini_dust_pan | 0-9 | shift_t | yes | 6.7 | 16.4 | -13.3 | -0.813 | 16.4 | 22.1 |
| 18 | mini_dust_pan | 190-352 | shift_t | no | 6.2 | 16.5 | -13.7 | -0.829 | 16.5 | 21.9 |
| 21 | water_pitcher | 0-7 | shift_t | no | 6.9 | 23.7 | -21.0 | -0.884 | 23.8 | 30.0 |
| 21 | water_pitcher | 153-185 | shift_t | no | 5.2 | 36.2 | -34.7 | -0.959 | 36.2 | 41.2 |
| 22 | water_pitcher | 0-26 | shift_t | no | 8.1 | 25.7 | -23.4 | -0.908 | 25.8 | 33.2 |
| 22 | blue_cup | 0-6 | shift_t | yes | 2.6 | 1.0 | +0.7 | +0.773 | 1.4 | 2.1 |
| 22 | water_pitcher | 146-188 | shift_t | no | 7.9 | 25.9 | -23.8 | -0.919 | 25.9 | 33.3 |
| 22 | blue_cup | 146-188 | shift_t | yes | 3.2 | 3.2 | +2.3 | +0.711 | 3.4 | 2.7 |
| 23 | wooden_piece_2 | 0-12 | shift_t | no | 17.9 | 19.2 | +15.0 | +0.782 | 19.2 | 12.3 |
| 23 | wooden_piece_1 | 0-114 | shift_t | yes | 16.2 | 77.1 | -42.6 | -0.553 | 91.6 | 99.6 |
| 24 | wooden_piece_2 | 0-26 | shift_t | no | 15.7 | 3.5 | -1.9 | -0.535 | 3.5 | 17.8 |
| 24 | wooden_piece_2 | 28-103 | shift_t | no | 5.0 | 19.0 | -16.4 | -0.865 | 19.4 | 23.8 |
| 26 | plastic_dish_rack | 0-107 | shift_t | no | 12.3 | 6.0 | +3.4 | +0.568 | 6.6 | 10.6 |
| 26 | white_pot | 0-27 | unresolved_inherited | yes | 12.3 | 8.2 | +0.1 | +0.018 | 8.4 | 14.8 |
| 26 | white_pot | 117-157 | shift_t | no | 11.5 | 6.5 | -5.8 | -0.898 | 6.5 | 17.6 |
| 26 | plastic_dish_rack | 118-157 | shift_t | yes | 8.3 | 4.3 | +3.3 | +0.766 | 4.5 | 5.8 |
| 27 | plastic_dish_rack | 0-245 | shift_t | no | 7.4 | 1.0 | +0.5 | +0.543 | 1.9 | 7.1 |
| 27 | white_pot | 0-34 | shift_t | yes | 12.0 | 8.5 | -3.2 | -0.383 | 8.7 | 17.3 |
| 27 | white_pot | 221-245 | shift_t | yes | 24.3 | 6.4 | -1.2 | -0.195 | 6.5 | 26.3 |
| 31 | plastic_dish_rack | 0-8 | shift_t | no | 2.3 | 18.3 | -10.7 | -0.584 | 18.3 | 19.7 |
| 31 | mini_sweeper | 0-20 | shift_t | yes | 3.0 | 1.0 | +0.5 | +0.517 | 1.3 | 2.8 |
| 31 | mini_sweeper | 267-289 | shift_t | no | 1.7 | 16.3 | -6.0 | -0.368 | 16.4 | 17.1 |
| 39 | mini_dust_pan | 0-31 | shift_t | no | 6.7 | 0.9 | -0.1 | -0.139 | 1.1 | 6.9 |
| 39 | mini_dust_pan | 295-318 | shift_t | no | 10.9 | 9.3 | +7.4 | +0.790 | 9.3 | 6.9 |
| 40 | mini_dust_pan | 0-17 | shift_t | no | 4.9 | 0.4 | +0.3 | +0.889 | 0.8 | 4.7 |
| 40 | mini_dust_pan | 229-259 | shift_t | no | 4.1 | 1.5 | -0.1 | -0.067 | 1.9 | 4.5 |
| 41 | white_pot | 0-15 | shift_t | no | 8.1 | 1.7 | +1.4 | +0.859 | 1.8 | 6.8 |
| 41 | white_pot | 261-298 | shift_t | no | 5.1 | 4.2 | -1.0 | -0.244 | 4.3 | 7.4 |
| 42 | white_pot | 0-18 | shift_t | no | 7.3 | 1.6 | +0.3 | +0.188 | 2.0 | 7.3 |
| 42 | white_pot | 229-256 | shift_t | no | 5.9 | 3.4 | -0.9 | -0.273 | 3.6 | 7.7 |
| 43 | white_pot | 0-11 | shift_t | no | 12.3 | 0.5 | +0.2 | +0.382 | 1.3 | 12.2 |
| 43 | white_pot | 296-325 | shift_t | no | 5.9 | 4.2 | -3.5 | -0.832 | 4.3 | 9.7 |
| 44 | white_pot | 0-9 | shift_t | no | 8.0 | 0.2 | -0.0 | -0.086 | 0.7 | 8.0 |
| 44 | white_pot | 208-248 | shift_t | no | 10.0 | 3.1 | +2.2 | +0.721 | 3.2 | 8.1 |
| 45 | white_pot | 0-15 | shift_t | no | 6.6 | 0.6 | -0.3 | -0.551 | 1.1 | 7.0 |
| 45 | white_pot | 265-289 | shift_t | no | 3.4 | 4.6 | -4.4 | -0.962 | 4.7 | 7.9 |

### Mesh check (pairs at rest together; every second frame; medians, max)

| ep | pair | rest frames | ours at our poses: median / max cm3, median depth mm | ours at mocap poses | scans at mocap poses |
|---|---|---|---|---|---|
| 0 | white_pot / white_pot_lid | 130 | 0.00 / 0.48, 0.0 | 6.43 / 6.51, 2.4 | 25.99 / 27.64, 53.7 |
| 2 | white_pot / white_pot_lid | 48 | 4.68 / 5.10, 2.3 | 5.85 / 6.00, 2.3 | 28.42 / 28.64, 54.9 |
| 11 | blue_cup / beige_cup | 42 | 91.36 / 98.90, 13.9 | 65.24 / 65.95, 22.0 | 252.25 / 253.41, 25.6 |
| 12 | blue_cup / plastic_dish_rack | 63 | 2.24 / 4.68, 5.8 | 0.74 / 1.84, 2.3 | 0.29 / 0.61, 1.4 |
| 13 | blue_cup / plastic_dish_rack | 93 | 4.09 / 10.23, 4.4 | 1.92 / 3.89, 4.1 | 0.06 / 0.20, 1.1 |
| 18 | mini_sweeper / mini_dust_pan | 10 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 |
| 21 | blue_cup / water_pitcher | 36 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 |
| 22 | blue_cup / water_pitcher | 50 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 |
| 23 | wooden_piece_1 / wooden_piece_2 | 55 | 0.00 / 0.00, 0.0 | 10.05 / 10.09, 6.2 | 1.14 / 1.26, 2.8 |
| 24 | wooden_piece_1 / wooden_piece_2 | 31 | 10.51 / 10.55, 6.1 | 9.94 / 10.00, 6.2 | 0.90 / 0.91, 2.5 |
| 26 | plastic_dish_rack / white_pot | 68 | 0.00 / 1.80, 0.0 | 0.00 / 2.36, 0.0 | 0.00 / 30.13, 0.0 |
| 27 | plastic_dish_rack / white_pot | 60 | 0.00 / 1.59, 0.0 | 0.00 / 1.50, 0.0 | 0.00 / 26.57, 0.0 |
| 31 | mini_sweeper / plastic_dish_rack | 30 | 5.39 / 7.91, 8.6 | 11.14 / 12.16, 8.6 | 0.74 / 1.42, 3.0 |

### Bottom check (mocap z up; our mesh lowest point at the mocap pose minus the scan lowest point; rest frames)

| ep | object | frames | ours - scan, median mm | scan lowest z median mm (IQR) |
|---|---|---|---|---|
| 0 | white_pot | 65 | -7.3 | 600.1 (0.3) |
| 0 | white_pot_lid | 187 | +2.7 | 687.6 (88.1) |
| 2 | white_pot | 41 | -7.9 | 599.9 (0.6) |
| 2 | white_pot_lid | 118 | +2.9 | 602.4 (86.9) |
| 11 | blue_cup | 21 | +8.3 | 600.4 (0.0) |
| 11 | beige_cup | 24 | +4.8 | 631.4 (7.7) |
| 12 | blue_cup | 32 | -3.1 | 609.5 (9.4) |
| 12 | plastic_dish_rack | 90 | +2.6 | 599.0 (0.4) |
| 13 | blue_cup | 47 | -2.4 | 605.9 (3.2) |
| 13 | plastic_dish_rack | 95 | +2.2 | 599.2 (0.4) |
| 18 | mini_sweeper | 25 | -1.0 | 602.5 (57.1) |
| 18 | mini_dust_pan | 87 | -2.4 | 601.4 (0.2) |
| 21 | blue_cup | 41 | +8.9 | 599.9 (55.8) |
| 21 | water_pitcher | 49 | -7.3 | 682.7 (277.7) |
| 22 | blue_cup | 25 | +8.4 | 599.3 (0.4) |
| 22 | water_pitcher | 60 | -10.7 | 602.7 (192.6) |
| 23 | wooden_piece_1 | 147 | +1.4 | 601.6 (0.8) |
| 23 | wooden_piece_2 | 28 | +0.0 | 602.0 (0.3) |
| 24 | wooden_piece_1 | 18 | +2.0 | 601.0 (0.0) |
| 24 | wooden_piece_2 | 67 | -5.5 | 601.2 (0.7) |
| 26 | plastic_dish_rack | 74 | +1.0 | 598.7 (0.3) |
| 26 | white_pot | 35 | -8.1 | 600.9 (17.1) |
| 27 | plastic_dish_rack | 123 | +1.8 | 598.7 (0.4) |
| 27 | white_pot | 30 | -6.9 | 600.8 (17.7) |
| 31 | mini_sweeper | 22 | +1.4 | 605.6 (0.2) |
| 31 | plastic_dish_rack | 15 | +4.1 | 598.8 (0.3) |
| 39 | mini_dust_pan | 43 | -1.7 | 601.8 (196.8) |
| 40 | mini_dust_pan | 25 | -1.8 | 601.9 (0.8) |
| 41 | white_pot | 36 | -7.5 | 601.4 (29.0) |
| 42 | white_pot | 24 | -7.1 | 601.3 (0.3) |
| 43 | white_pot | 21 | -8.3 | 601.1 (0.4) |
| 44 | white_pot | 26 | -7.7 | 601.1 (0.0) |
| 45 | white_pot | 21 | -8.3 | 601.5 (0.4) |
