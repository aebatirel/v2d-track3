# E0 selection (pre-registered rule, PREREG.md section 4; GT-free)

## white_pot (6 eval pairs): pick pot/ep3/fit, recommendation E0

| label | fid ALL sum (o->m, m->o) mm | faces | wt | budget f/v ok | centroid / median mm | axes deg | excluded |
|---|---|---|---|---|---|---|---|
| pot/C0 | 2.914 (1.923, 0.991) | 16454 | True | True/True | 5.4 / 2.73 | [3.0, 4.7, 4.6] |  |
| pot/ep3/fit | 2.922 (1.978, 0.944) | 15574 | True | True/True | 6.5 / 3.20 | [3.0, 3.4, 4.4] |  |
| pot/ep3/nostem | 2.922 (1.978, 0.944) | 15574 | True | True/True | 6.5 / 3.20 | [3.0, 3.4, 4.4] |  |
| pot/ep3/thick | 3.077 (1.955, 1.123) | 15574 | True | True/True | 6.6 / 2.73 | [3.1, 3.1, 4.3] |  |
| pot/ep3/tsdf | 3.103 (2.028, 1.075) | 18801 | False | True/True | 5.9 / 2.29 | [3.6, 3.9, 3.8] | not watertight |
| pot/ep28/thick | 3.382 (2.345, 1.037) | 15944 | True | True/True | 3.9 / 2.95 | [3.0, 2.4, 3.0] |  |
| pot/ep5/fit | 3.487 (2.317, 1.17) | 16124 | True | True/True | 7.8 / 2.90 | [3.6, 3.3, 4.9] |  |
| pot/ep5/nostem | 3.487 (2.317, 1.17) | 16124 | True | True/True | 7.8 / 2.90 | [3.6, 3.3, 4.9] |  |
| pot/ep1/tsdf | 3.544 (2.338, 1.206) | 18377 | False | True/True | 6.1 / 2.26 | [3.6, 3.9, 4.0] | not watertight |
| pot/ep1/fit | 3.611 (2.475, 1.136) | 15250 | True | True/True | 7.5 / 2.97 | [2.5, 1.8, 3.1] |  |
| pot/ep1/nostem | 3.611 (2.475, 1.136) | 15250 | True | True/True | 7.5 / 2.97 | [2.5, 1.8, 3.1] |  |
| pot/ep8/fit | 3.665 (2.365, 1.3) | 15568 | True | True/True | 9.1 / 2.65 | [2.3, 4.9, 5.4] |  |
| pot/ep8/nostem | 3.665 (2.365, 1.3) | 15568 | True | True/True | 9.1 / 2.65 | [2.3, 4.9, 5.4] |  |
| pot/ep5/tsdf | 3.681 (2.403, 1.278) | 18441 | False | True/True | 7.4 / 2.27 | [3.1, 4.0, 4.7] | not watertight |
| pot/ep1/thick | 3.692 (2.226, 1.466) | 15540 | True | True/True | 7.7 / 2.60 | [2.7, 2.1, 3.3] |  |
| pot/ep28/tsdf | 3.72 (2.653, 1.067) | 19505 | False | True/True | 7.0 / 2.15 | [2.2, 2.8, 3.0] | not watertight |
| pot/ep28/nostem | 3.743 (2.764, 0.979) | 15836 | True | True/True | 4.1 / 3.21 | [3.1, 2.6, 3.0] |  |
| pot/ep28/fit | 3.745 (2.764, 0.981) | 15944 | True | True/True | 4.2 / 3.23 | [3.2, 2.6, 3.0] |  |
| pot/ep8/tsdf | 3.762 (2.373, 1.389) | 17954 | False | True/True | 8.3 / 2.15 | [2.7, 5.2, 5.5] | not watertight |
| pot/ep6/fit | 3.879 (2.535, 1.345) | 16142 | True | True/True | 9.4 / 2.84 | [3.6, 2.8, 4.6] |  |
| pot/ep6/nostem | 3.879 (2.535, 1.345) | 16142 | True | True/True | 9.4 / 2.84 | [3.6, 2.8, 4.6] |  |
| pot/library_v3 | 3.881 (2.462, 1.42) | - | - | -/- | nan / nan | [] |  |
| pot/ep5/thick | 3.901 (2.338, 1.563) | 15844 | True | True/True | 7.9 / 2.81 | [3.0, 3.3, 4.5] |  |
| pot/ep6/tsdf | 4.062 (2.63, 1.432) | 17862 | False | True/True | 8.6 / 2.43 | [3.1, 3.7, 4.6] | not watertight |
| pot/ep8/thick | 4.414 (2.556, 1.857) | 15282 | True | True/True | 9.3 / 2.98 | [1.9, 4.7, 5.0] |  |
| pot/ep6/thick | 4.473 (2.538, 1.935) | 16170 | True | True/True | 9.0 / 2.86 | [3.4, 3.5, 4.8] |  |

Per episode (diagnostic): {"ep1": {"own_best": "pot/ep1/fit", "own_best_fid": 4.484, "pick_fid": 3.648, "c0_fid": 3.963, "library_v3_fid": 4.997}, "ep3": {"own_best": "pot/ep3/fit", "own_best_fid": 3.344, "pick_fid": 3.344, "c0_fid": 3.624, "library_v3_fid": 5.291}, "ep5": {"own_best": "pot/ep5/fit", "own_best_fid": 3.806, "pick_fid": 3.018, "c0_fid": 3.367, "library_v3_fid": 4.764}, "ep6": {"own_best": "pot/ep6/fit", "own_best_fid": 4.369, "pick_fid": 3.138, "c0_fid": 3.45, "library_v3_fid": 4.967}, "ep8": {"own_best": "pot/ep8/fit", "own_best_fid": 5.15, "pick_fid": 4.181, "c0_fid": 3.974, "library_v3_fid": 5.412}, "ep28": {"own_best": "pot/ep28/thick", "own_best_fid": 2.456, "pick_fid": 3.291, "c0_fid": 2.895, "library_v3_fid": 4.438}}

## white_pot_lid (1 eval pairs): pick lid/ep1/t2.5_fit, recommendation E0

| label | fid ALL sum (o->m, m->o) mm | faces | wt | budget f/v ok | centroid / median mm | axes deg | excluded |
|---|---|---|---|---|---|---|---|
| lid/ep1/t2.5_fit | 1.675 (0.928, 0.747) | 9488 | True | True/True | 7.2 / 2.66 | [74.4, 74.4, 1.6] |  |
| lid/C0 | 1.772 (1.024, 0.748) | 9550 | True | True/True | 7.3 / 2.35 | [38.2, 38.2, 0.8] |  |
| lid/ep1/t2.5_tsdf | 1.787 (1.016, 0.772) | 9089 | False | True/True | 7.2 / 2.45 | [66.7, 66.7, 1.8] | not watertight |
| lid/library_v3 | 5.186 (1.429, 3.757) | - | - | -/- | nan / nan | [] |  |

Per episode (diagnostic): {"ep1": {"own_best": "lid/ep1/t2.5_fit", "own_best_fid": 1.675, "pick_fid": 1.675, "c0_fid": 1.772, "library_v3_fid": 5.186}}

## plastic_dish_rack (5 eval pairs): pick rack/joint/joint, recommendation E0

| label | fid ALL sum (o->m, m->o) mm | faces | wt | budget f/v ok | centroid / median mm | axes deg | excluded |
|---|---|---|---|---|---|---|---|
| rack/library_v3 | 5.881 (2.633, 3.248) | - | - | -/- | nan / nan | [] |  |
| rack/C0 | 6.245 (1.844, 4.402) | 2356 | True | True/True | 11.5 / 3.43 | [2.4, 2.0, 3.1] |  |
| rack/joint/joint | 6.419 (1.87, 4.55) | 2638 | True | True/True | 9.4 / 3.43 | [2.3, 0.8, 2.3] |  |
| rack/joint/joint_nomk | 6.432 (1.874, 4.558) | 2238 | True | True/True | 10.0 / 3.43 | [2.2, 0.8, 2.3] |  |
| rack/ep14/full | 6.674 (1.968, 4.706) | 2210 | True | True/True | 11.2 / 3.63 | [2.0, 2.7, 3.4] |  |
| rack/ep14/nomk | 6.674 (1.968, 4.706) | 2210 | True | True/True | 11.2 / 3.63 | [2.0, 2.7, 3.4] |  |
| rack/ep16/full | 6.779 (1.827, 4.952) | 2602 | True | True/True | 12.2 / 3.60 | [2.6, 0.3, 2.7] |  |
| rack/ep16/nomk | 6.828 (1.848, 4.98) | 2202 | True | True/True | 12.5 / 3.59 | [2.6, 0.3, 2.6] |  |
| rack/ep28/full | 7.131 (2.13, 5.001) | 1844 | True | True/True | 14.8 / 3.42 | [1.4, 5.2, 5.4] |  |
| rack/ep28/nomk | 7.188 (2.16, 5.028) | 1644 | True | True/True | 14.7 / 3.41 | [1.4, 5.3, 5.4] |  |
| rack/ep30/full | 7.437 (1.98, 5.457) | 2618 | True | True/True | 11.3 / 3.66 | [2.3, 1.8, 2.5] |  |
| rack/ep30/nomk | 7.488 (2.001, 5.486) | 1886 | True | True/True | 11.9 / 3.67 | [2.3, 2.1, 2.7] |  |
| rack/ep15/full | 7.553 (1.929, 5.624) | 2498 | True | True/True | 11.5 / 3.82 | [2.9, 1.3, 3.2] |  |
| rack/ep15/nomk | 7.611 (1.95, 5.661) | 1998 | True | True/True | 11.6 / 3.86 | [2.9, 1.4, 3.2] |  |

Per episode (diagnostic): {"ep14": {"own_best": "rack/ep14/full", "own_best_fid": 7.501, "pick_fid": 7.444, "c0_fid": 7.212, "library_v3_fid": 6.986}, "ep15": {"own_best": "rack/ep15/full", "own_best_fid": 9.743, "pick_fid": 8.721, "c0_fid": 8.37, "library_v3_fid": 7.737}, "ep16": {"own_best": "rack/ep16/full", "own_best_fid": 8.51, "pick_fid": 8.512, "c0_fid": 8.139, "library_v3_fid": 7.727}, "ep28": {"own_best": "rack/ep28/full", "own_best_fid": 8.812, "pick_fid": 8.824, "c0_fid": 8.501, "library_v3_fid": 7.464}, "ep30": {"own_best": "rack/ep30/full", "own_best_fid": 7.565, "pick_fid": 7.379, "c0_fid": 7.339, "library_v3_fid": 7.63}}

## blue_cup (5 eval pairs): pick cup/ep32/g1, recommendation E0

| label | fid ALL sum (o->m, m->o) mm | faces | wt | budget f/v ok | centroid / median mm | axes deg | excluded |
|---|---|---|---|---|---|---|---|
| cup/ep32/g1 | 2.646 (1.438, 1.208) | 23348 | True | True/True | 4.0 / 2.48 | [3.6, 69.3, 69.4] |  |
| cup/ep32/g0 | 2.664 (1.457, 1.207) | 22464 | True | True/True | 3.5 / 2.51 | [2.9, 6.8, 7.3] |  |
| cup/C0 | 2.723 (1.585, 1.138) | 30924 | True | True/True | 3.5 / 2.53 | [3.1, 15.0, 15.3] |  |
| cup/ep14/g0 | 2.824 (1.516, 1.308) | 22848 | True | True/True | 2.5 / 2.25 | [4.0, 89.2, 89.1] |  |
| cup/ep33/g1 | 2.846 (1.48, 1.367) | 29968 | True | True/True | 3.3 / 2.48 | [2.8, 33.4, 33.4] |  |
| cup/ep14/g1 | 2.892 (1.421, 1.471) | 48488 | True | True/True | 6.9 / 2.14 | [2.8, 18.3, 18.2] |  |
| cup/library_v3 | 2.906 (1.866, 1.041) | - | - | -/- | nan / nan | [] |  |
| cup/merged/g1 | 3.007 (1.493, 1.514) | 59954 | True | True/True | 5.6 / 2.34 | [2.7, 18.2, 18.0] |  |
| cup/ep33/g0 | 3.024 (1.622, 1.402) | 21312 | True | True/True | 4.9 / 2.58 | [3.4, 72.8, 72.8] |  |
| cup/ep20/g1 | 3.079 (1.74, 1.339) | 27610 | True | True/True | 5.1 / 2.36 | [3.2, 13.7, 13.8] |  |
| cup/ep20/g0 | 3.153 (1.831, 1.322) | 21504 | True | True/True | 5.4 / 2.36 | [0.9, 68.3, 68.3] |  |
| cup/ep10/g0 | 3.531 (2.289, 1.242) | 23616 | True | True/True | 9.1 / 2.25 | [1.4, 27.6, 27.6] |  |
| cup/ep10/g1 | 3.55 (2.288, 1.262) | 24660 | True | True/True | 10.3 / 2.29 | [2.4, 3.3, 2.7] |  |

Per episode (diagnostic): {"ep10": {"own_best": "cup/ep10/g1", "own_best_fid": 5.624, "pick_fid": 7.748, "c0_fid": 7.689, "library_v3_fid": 7.223}, "ep14": {"own_best": "cup/ep14/g1", "own_best_fid": 3.912, "pick_fid": 4.417, "c0_fid": 4.734, "library_v3_fid": 4.125}, "ep20": {"own_best": "cup/ep20/g1", "own_best_fid": 6.046, "pick_fid": 5.895, "c0_fid": 5.741, "library_v3_fid": 7.59}, "ep32": {"own_best": "cup/ep32/g1", "own_best_fid": 5.196, "pick_fid": 5.196, "c0_fid": 5.041, "library_v3_fid": 5.765}, "ep33": {"own_best": "cup/ep33/g1", "own_best_fid": 3.999, "pick_fid": 4.073, "c0_fid": 3.9, "library_v3_fid": 5.217}}

