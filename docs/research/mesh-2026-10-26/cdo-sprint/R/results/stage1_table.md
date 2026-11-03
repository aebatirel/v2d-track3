# Rack round R stage-1 screen [D]: 6 seeds 3001-3006, roster emptied, one scoring per generated mesh

Public scans stand in for the hidden scans. Single-image models: the GT-free Sim(3) copy; Pixal3D-MV: the output in
our object frame. CD-O in cm (median / mean of 6 seeds); W30 and FLIP = share of seeds with rotation error > 30 /
> 90 deg; ADD and anchor = median over the seeds, mm (of the screened copy in our track frame, not of the placed
copy). 13i = the 13i rack's 50-seed audit median (C4), so compare loosely (6 seeds, best-of-N here).
Pick: T6 = one of the 6 lowest CD-O medians (stage 2, "cdo_top6").

390 records, 0 errors

## plastic_dish_rack (13i 50-seed CD-O median 0.4016; 390 meshes; 5 with stage-1 CD-O median below it)

| model | n | best CD-O med | median of CD-O meds | W30 > 0 |
|---|---|---|---|---|
| sam3d | 120 | 0.5070 | 0.6064 | 0 |
| hy21 | 120 | 0.3876 | 0.5652 | 1 |
| trellis2 | 120 | 0.3925 | 0.4939 | 1 |
| pixal_mv | 30 | 0.5123 | 0.6105 | 0 |

| rank | mesh | CD-O med | CD-O mean | W30 | FLIP | ADD med | anchor med | amb / floor mm | pick |
|---|---|---|---|---|---|---|---|---|---|
| 1 | r/hy21/ep12_plastic_dish_rack_k18_s31337 | 0.3876 | 0.3876 | 0.0 | 0.0 | 23.92 | 23.73 | 9.88 / 4.03 | T6 |
| 2 | r/trellis2/ep27_plastic_dish_rack_k129_s7 | 0.3925 | 0.3932 | 0.0 | 0.0 | 36.41 | 32.24 | 9.72 / 3.83 | T6 |
| 3 | r/trellis2/ep27_plastic_dish_rack_k84_s42 | 0.3967 | 0.3967 | 0.0 | 0.0 | 31.52 | 31.29 | 9.63 / 3.49 | T6 |
| 4 | r/trellis2/ep27_plastic_dish_rack_k87_s123 | 0.3968 | 0.3962 | 0.0 | 0.0 | 30.70 | 30.58 | 9.67 / 3.50 | T6 |
| 5 | r/hy21/ep31_plastic_dish_rack_k3_s777 | 0.4014 | 0.4015 | 0.0 | 0.0 | 7.83 | 5.56 | 10.82 / 5.04 | T6 |
| 6 | r/trellis2/ep27_plastic_dish_rack_k132_s42 | 0.4033 | 0.4042 | 0.0 | 0.0 | 29.96 | 29.86 | 9.26 / 3.46 | T6 |
| 7 | r/hy21/ep12_plastic_dish_rack_k12_s777 | 0.4037 | 0.4050 | 0.0 | 0.0 | 26.54 | 26.34 | 9.19 / 4.10 |  |
| 8 | r/hy21/ep31_plastic_dish_rack_k0_s777 | 0.4047 | 0.4052 | 0.0 | 0.0 | 7.75 | 5.22 | 10.68 / 4.95 |  |
| 9 | r/hy21/ep12_plastic_dish_rack_k18_s7 | 0.4048 | 0.4029 | 0.0 | 0.0 | 19.18 | 18.92 | 10.95 / 4.13 |  |
| 10 | r/trellis2/ep27_plastic_dish_rack_k132_s123 | 0.4073 | 0.4071 | 0.0 | 0.0 | 29.27 | 29.16 | 10.48 / 3.58 |  |
| 11 | r/hy21/ep31_plastic_dish_rack_k6_s777 | 0.4076 | 0.4081 | 0.0 | 0.0 | 8.54 | 6.80 | 11.32 / 4.78 |  |
| 12 | r/trellis2/ep12_plastic_dish_rack_k15_s123 | 0.4090 | 0.4096 | 0.0 | 0.0 | 15.36 | 14.69 | 10.91 / 3.96 |  |
| 13 | r/trellis2/ep31_plastic_dish_rack_k0_s2025 | 0.4106 | 0.4104 | 0.0 | 0.0 | 7.41 | 5.89 | 12.43 / 4.13 |  |
| 14 | r/hy21/ep31_plastic_dish_rack_k279_s123 | 0.4107 | 0.4109 | 0.0 | 0.0 | 9.28 | 7.30 | 10.76 / 4.40 |  |
| 15 | r/trellis2/ep27_plastic_dish_rack_k129_s123 | 0.4127 | 0.4122 | 0.0 | 0.0 | 29.59 | 29.38 | 9.73 / 3.60 |  |
| 16 | r/trellis2/ep13_plastic_dish_rack_k87_s42 | 0.4155 | 0.4155 | 0.0 | 0.0 | 11.64 | 11.30 | 11.55 / 3.81 |  |
| 17 | r/trellis2/ep12_plastic_dish_rack_k15_s31337 | 0.4164 | 0.4168 | 0.0 | 0.0 | 31.02 | 30.90 | 9.46 / 3.28 |  |
| 18 | r/hy21/ep31_plastic_dish_rack_k279_s31337 | 0.4184 | 0.4193 | 0.0 | 0.0 | 10.31 | 8.28 | 11.21 / 4.37 |  |
| 19 | r/trellis2/ep31_plastic_dish_rack_k3_s42 | 0.4195 | 0.4190 | 0.0 | 0.0 | 9.02 | 6.90 | 11.72 / 3.97 |  |
| 20 | r/hy21/ep27_plastic_dish_rack_k132_s777 | 0.4207 | 0.4210 | 0.0 | 0.0 | 43.23 | 43.00 | 8.92 / 4.17 |  |

(rows 21-390 omitted; all 390 are in screen/screen6.jsonl)

