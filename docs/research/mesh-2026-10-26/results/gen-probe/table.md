# Generative probe, batch 2: one-shot scan scores [D] next to GT-free metrics

CD-O and ADD are the kit metrics as `mesh_metric.py` computes them (eval-pair seeds), against the PUBLIC scans; diagnostic only [D]. ADD/flips for the single-image models are those of the Sim(3) copy fitted to our observed points (GT-free); the raw generator output has the same CD-O (similarity-invariant) and no meaningful ADD. GT-free = median distance (mm) between the mesh surface and our observed points, obs->mesh / mesh->obs; library_v3 values in the first column.

## Per object (CD-O cm, s42 / s7; ADD mm and flips in the detail table)

| object | library_v3 | best ours | Pixal3D-MV (posed) | Pixal3D view 0 only | TRELLIS.2 | TripoSG | Hunyuan3D-2.1 | SAM 3D |
|---|---|---|---|---|---|---|---|---|
| white_pot | 0.437 | 0.342 | 0.426 / 0.454 | - | 0.390 / 0.318 | 1.427 / 1.404 | 0.359 / 0.499 | 0.359 / 0.328 |
| white_pot_lid | 0.421 | 0.22 | 0.253 / 0.325 | - | 0.394 / 0.343 | 1.659 / 0.791 | 0.481 / 0.353 | 1.313 / 1.308 |
| blue_cup | 0.523 | 0.291 | 0.407 / 0.402 | - | 0.920* / 0.574* | 0.396 / 0.712 | 0.298 / 1.252 | 0.299 / 0.268 |
| water_pitcher | 0.894 | - | 1.810 / 1.241 | - | 0.681 / 0.693 | 1.487 / 1.432 | 0.378 / 0.570 | 0.771 / 0.649 |
| wooden_piece_1 | 0.222 | - | 0.182 / 0.204 | - | 0.473 / 0.483 | 0.340 / 0.336 | 0.338 / 0.334 | 0.192 / 0.204 |
| wooden_piece_2 | 0.216 | - | 0.274 / 0.247 | 0.255 / 0.758 | 0.220 / 0.293 | 0.429 / 0.272 | 0.309 / 0.438 | 0.321 / 0.202 |
| plastic_dish_rack | 0.555 | 0.456 | 0.716 / 0.663 | - | 1.262 / 0.636 | 2.072 / 0.726 | 0.653 / 1.853 | 0.622 / 0.604 |
| mini_sweeper | 0.317 | - | 0.479 / 0.460 | - | 0.850 / 0.618 | 1.037 / 0.829 | 0.867 / 1.022 | 0.706 / 0.437 |
| mini_dust_pan | 0.331 | - | 0.240 / 0.236 | 0.628 / 0.528 | 0.339 / 0.338 | 0.754 / 0.516 | 0.231 / 0.396 | 0.261 / 0.333 |
| beige_cup | 0.856 | - | 0.274 / 0.512 | - | 0.728 / 1.321 | 1.837 / 1.230 | 0.461 / 0.954 | 0.526 / 0.321 |

`*` TRELLIS.2 at 1024 (1536 ran out of memory on this crop).

## Per model, over the objects it covers

| model | objects | mean CD-O (seed mean) | mean CD-O library_v3, same objects | objects better than library_v3 (seed mean) | objects better than our best (pot, lid, rack, blue cup) |
|---|---|---|---|---|---|
| Pixal3D-MV (posed) | 10 | 0.490 | 0.477 | 5: white_pot_lid, blue_cup, wooden_piece_1, mini_dust_pan, beige_cup | - |
| Pixal3D view 0 only | 2 | 0.542 | 0.273 | 0: - | - |
| TRELLIS.2 | 10 | 0.594 | 0.477 | 3: white_pot, white_pot_lid, water_pitcher | - |
| TripoSG | 10 | 0.984 | 0.477 | 0: - | - |
| Hunyuan3D-2.1 | 10 | 0.602 | 0.477 | 5: white_pot, white_pot_lid, water_pitcher, mini_dust_pan, beige_cup | - |
| SAM 3D | 10 | 0.501 | 0.477 | 6: white_pot, blue_cup, water_pitcher, wooden_piece_1, mini_dust_pan, beige_cup | blue_cup |

## Detail: every scored mesh

| object | model | seed | CD-O cm | ADD mm | flips | GT-free obs->mesh / mesh->obs mm (lib) | Pixal view IoU | Sim(3) scale |
|---|---|---|---|---|---|---|---|---|
| white_pot | library_v3 | - | 0.437 | 6.7 | 0/8 | 2.15 / 2.41 | - | - |
| white_pot | Pixal3D-MV (posed) | 42 | 0.426 | 4.2 | 0/8 | 3.88 / 2.39 | 0.978 | - |
| white_pot | Pixal3D-MV (posed) | 7 | 0.454 | 25.2 | 0/8 | 6.91 / 4.74 | 0.98 | - |
| white_pot | TRELLIS.2 | 42 | 0.390 | 6.3 | 0/8 | 2.25 / 2.22 | - | 0.3553 |
| white_pot | TRELLIS.2 | 7 | 0.318 | 10.8 | 0/8 | 2.35 / 2.42 | - | 0.3434 |
| white_pot | TripoSG | 42 | 1.427 | 17.1 | 0/8 | 6.21 / 8.58 | - | 0.1695 |
| white_pot | TripoSG | 7 | 1.404 | 28.2 | 0/8 | 3.31 / 4.95 | - | 0.1871 |
| white_pot | Hunyuan3D-2.1 | 42 | 0.359 | 6.6 | 0/8 | 1.96 / 2.22 | - | 0.1742 |
| white_pot | Hunyuan3D-2.1 | 7 | 0.499 | 9.0 | 0/8 | 1.95 / 2.37 | - | 0.184 |
| white_pot | SAM 3D | 42 | 0.359 | 7.4 | 0/8 | 1.82 / 2.17 | - | 0.3645 |
| white_pot | SAM 3D | 7 | 0.328 | 8.0 | 0/8 | 1.64 / 1.94 | - | 0.3652 |
| white_pot_lid | library_v3 | - | 0.421 | 8.1 | 0/6 | 1.23 / 4.65 | - | - |
| white_pot_lid | Pixal3D-MV (posed) | 42 | 0.253 | 7.0 | 0/6 | 1.65 / 1.38 | 0.982 | - |
| white_pot_lid | Pixal3D-MV (posed) | 7 | 0.325 | 13.5 | 0/6 | 5.70 / 5.59 | 0.987 | - |
| white_pot_lid | TRELLIS.2 | 42 | 0.394 | 11.3 | 0/6 | 2.48 / 1.75 | - | 0.1814 |
| white_pot_lid | TRELLIS.2 | 7 | 0.343 | 13.2 | 0/6 | 1.35 / 1.23 | - | 0.1774 |
| white_pot_lid | TripoSG | 42 | 1.659 | 82.9 | 0/6 | 7.18 / 12.04 | - | 0.0638 |
| white_pot_lid | TripoSG | 7 | 0.791 | 60.3 | 0/6 | 2.20 / 4.57 | - | 0.095 |
| white_pot_lid | Hunyuan3D-2.1 | 42 | 0.481 | 85.5 | 3/6 | 1.38 / 1.43 | - | 0.1041 |
| white_pot_lid | Hunyuan3D-2.1 | 7 | 0.353 | 9.5 | 0/6 | 1.09 / 1.21 | - | 0.082 |
| white_pot_lid | SAM 3D | 42 | 1.313 | 40.8 | 0/6 | 3.04 / 6.22 | - | 0.1549 |
| white_pot_lid | SAM 3D | 7 | 1.308 | 74.1 | 0/6 | 2.73 / 5.79 | - | 0.1382 |
| blue_cup | library_v3 | - | 0.523 | 10.0 | 0/7 | 1.70 / 4.41 | - | - |
| blue_cup | Pixal3D-MV (posed) | 42 | 0.407 | 6.4 | 0/7 | 1.28 / 1.68 | 0.932 | - |
| blue_cup | Pixal3D-MV (posed) | 7 | 0.402 | 6.3 | 0/7 | 1.37 / 1.75 | 0.932 | - |
| blue_cup | TRELLIS.2 (1024) | 42 | 0.920 | 22.7 | 0/7 | 1.69 / 2.50 | - | 0.1521 |
| blue_cup | TRELLIS.2 (1024) | 7 | 0.574 | 11.0 | 0/7 | 1.12 / 1.93 | - | 0.1706 |
| blue_cup | TripoSG | 42 | 0.396 | 20.3 | 0/7 | 1.47 / 2.99 | - | 0.0943 |
| blue_cup | TripoSG | 7 | 0.712 | 22.2 | 0/7 | 1.28 / 2.27 | - | 0.0864 |
| blue_cup | Hunyuan3D-2.1 | 42 | 0.298 | 24.7 | 0/7 | 2.47 / 5.66 | - | 0.0951 |
| blue_cup | Hunyuan3D-2.1 | 7 | 1.252 | 118.5 | 5/7 | 6.79 / 12.66 | - | 0.1374 |
| blue_cup | SAM 3D | 42 | 0.299 | 29.7 | 0/7 | 1.68 / 5.07 | - | 0.1708 |
| blue_cup | SAM 3D | 7 | 0.268 | 18.6 | 0/7 | 1.10 / 4.81 | - | 0.1776 |
| water_pitcher | library_v3 | - | 0.894 | 7.6 | 0/6 | 2.43 / 6.35 | - | - |
| water_pitcher | Pixal3D-MV (posed) | 42 | 1.810 | 39.5 | 0/6 | 15.96 / 12.40 | 0.958 | - |
| water_pitcher | Pixal3D-MV (posed) | 7 | 1.241 | 26.6 | 0/6 | 6.35 / 4.25 | 0.958 | - |
| water_pitcher | TRELLIS.2 | 42 | 0.681 | 29.8 | 0/6 | 4.64 / 3.44 | - | 0.3134 |
| water_pitcher | TRELLIS.2 | 7 | 0.693 | 22.9 | 0/6 | 3.51 / 2.76 | - | 0.3525 |
| water_pitcher | TripoSG | 42 | 1.487 | 25.9 | 0/6 | 4.94 / 3.81 | - | 0.1521 |
| water_pitcher | TripoSG | 7 | 1.432 | 26.7 | 0/6 | 6.32 / 4.85 | - | 0.1531 |
| water_pitcher | Hunyuan3D-2.1 | 42 | 0.378 | 34.3 | 0/6 | 1.82 / 4.99 | - | 0.1648 |
| water_pitcher | Hunyuan3D-2.1 | 7 | 0.570 | 28.4 | 0/6 | 2.04 / 4.01 | - | 0.1649 |
| water_pitcher | SAM 3D | 42 | 0.771 | 30.4 | 0/6 | 1.85 / 3.44 | - | 0.3935 |
| water_pitcher | SAM 3D | 7 | 0.649 | 32.8 | 0/6 | 1.98 / 3.41 | - | 0.4105 |
| wooden_piece_1 | library_v3 | - | 0.222 | 2.4 | 0/6 | 8.61 / 14.95 | - | - |
| wooden_piece_1 | Pixal3D-MV (posed) | 42 | 0.182 | 130.6 | 4/6 | 2.13 / 14.64 | 0.985 | - |
| wooden_piece_1 | Pixal3D-MV (posed) | 7 | 0.204 | 85.0 | 4/6 | 4.27 / 17.41 | 0.983 | - |
| wooden_piece_1 | TRELLIS.2 | 42 | 0.473 | 87.1 | 6/6 | 2.58 / 11.18 | - | 0.263 |
| wooden_piece_1 | TRELLIS.2 | 7 | 0.483 | 89.5 | 3/6 | 1.93 / 11.81 | - | 0.2668 |
| wooden_piece_1 | TripoSG | 42 | 0.340 | 132.6 | 5/6 | 1.60 / 9.93 | - | 0.1 |
| wooden_piece_1 | TripoSG | 7 | 0.336 | 22.7 | 1/6 | 1.45 / 9.83 | - | 0.0959 |
| wooden_piece_1 | Hunyuan3D-2.1 | 42 | 0.338 | 85.3 | 5/6 | 1.62 / 10.44 | - | 0.0892 |
| wooden_piece_1 | Hunyuan3D-2.1 | 7 | 0.334 | 18.8 | 0/6 | 1.31 / 10.41 | - | 0.107 |
| wooden_piece_1 | SAM 3D | 42 | 0.192 | 34.9 | 2/6 | 1.30 / 10.42 | - | 0.1899 |
| wooden_piece_1 | SAM 3D | 7 | 0.204 | 32.2 | 4/6 | 1.35 / 11.64 | - | 0.1885 |
| wooden_piece_2 | library_v3 | - | 0.216 | 3.6 | 0/6 | 1.33 / 1.35 | - | - |
| wooden_piece_2 | Pixal3D-MV (posed) | 42 | 0.274 | 6.8 | 3/6 | 2.70 / 2.93 | 0.973 | - |
| wooden_piece_2 | Pixal3D-MV (posed) | 7 | 0.247 | 6.1 | 2/6 | 3.10 / 2.82 | 0.976 | - |
| wooden_piece_2 | Pixal3D view 0 only | 42 | 0.255 | 17.1 | 3/6 | 4.60 / 5.30 | 0.711 | - |
| wooden_piece_2 | Pixal3D view 0 only | 7 | 0.758 | 13.3 | 0/6 | 4.15 / 7.81 | 0.77 | - |
| wooden_piece_2 | TRELLIS.2 | 42 | 0.220 | 129.3 | 6/6 | 1.65 / 1.85 | - | 0.2979 |
| wooden_piece_2 | TRELLIS.2 | 7 | 0.293 | 30.5 | 3/6 | 1.42 / 1.43 | - | 0.218 |
| wooden_piece_2 | TripoSG | 42 | 0.429 | 129.8 | 4/6 | 1.90 / 2.57 | - | 0.138 |
| wooden_piece_2 | TripoSG | 7 | 0.272 | 28.0 | 2/6 | 1.78 / 2.04 | - | 0.1139 |
| wooden_piece_2 | Hunyuan3D-2.1 | 42 | 0.309 | 159.0 | 6/6 | 1.69 / 2.14 | - | 0.1266 |
| wooden_piece_2 | Hunyuan3D-2.1 | 7 | 0.438 | 27.0 | 1/6 | 2.32 / 2.48 | - | 0.1132 |
| wooden_piece_2 | SAM 3D | 42 | 0.321 | 159.0 | 6/6 | 1.15 / 1.42 | - | 0.2011 |
| wooden_piece_2 | SAM 3D | 7 | 0.202 | 83.1 | 6/6 | 1.39 / 1.84 | - | 0.2275 |
| plastic_dish_rack | library_v3 | - | 0.555 | 6.0 | 0/7 | 2.40 / 7.74 | - | - |
| plastic_dish_rack | Pixal3D-MV (posed) | 42 | 0.716 | 31.9 | 0/7 | 16.22 / 35.91 | 0.958 | - |
| plastic_dish_rack | Pixal3D-MV (posed) | 7 | 0.663 | 37.8 | 0/7 | 17.50 / 38.85 | 0.927 | - |
| plastic_dish_rack | TRELLIS.2 | 42 | 1.262 | 33.3 | 0/7 | 4.79 / 12.09 | - | 0.5148 |
| plastic_dish_rack | TRELLIS.2 | 7 | 0.636 | 15.2 | 0/7 | 3.20 / 8.80 | - | 0.4683 |
| plastic_dish_rack | TripoSG | 42 | 2.072 | 47.4 | 0/7 | 4.15 / 14.63 | - | 0.2165 |
| plastic_dish_rack | TripoSG | 7 | 0.726 | 16.5 | 0/7 | 3.28 / 9.75 | - | 0.2524 |
| plastic_dish_rack | Hunyuan3D-2.1 | 42 | 0.653 | 31.6 | 0/7 | 3.71 / 11.56 | - | 0.2306 |
| plastic_dish_rack | Hunyuan3D-2.1 | 7 | 1.853 | 33.4 | 0/7 | 5.17 / 17.43 | - | 0.2206 |
| plastic_dish_rack | SAM 3D | 42 | 0.622 | 28.9 | 0/7 | 2.84 / 8.20 | - | 0.4351 |
| plastic_dish_rack | SAM 3D | 7 | 0.604 | 21.0 | 0/7 | 2.85 / 8.16 | - | 0.4528 |
| mini_sweeper | library_v3 | - | 0.317 | 25.6 | 1/6 | 1.44 / 2.90 | - | - |
| mini_sweeper | Pixal3D-MV (posed) | 42 | 0.479 | 40.6 | 1/6 | 2.97 / 7.89 | 0.982 | - |
| mini_sweeper | Pixal3D-MV (posed) | 7 | 0.460 | 41.9 | 1/6 | 5.09 / 9.14 | 0.974 | - |
| mini_sweeper | TRELLIS.2 | 42 | 0.850 | 35.0 | 2/6 | 3.56 / 4.27 | - | 0.2195 |
| mini_sweeper | TRELLIS.2 | 7 | 0.618 | 69.0 | 5/6 | 2.88 / 2.66 | - | 0.1767 |
| mini_sweeper | TripoSG | 42 | 1.037 | 54.5 | 1/6 | 5.70 / 4.69 | - | 0.1295 |
| mini_sweeper | TripoSG | 7 | 0.829 | 13.3 | 1/6 | 4.55 / 2.45 | - | 0.0963 |
| mini_sweeper | Hunyuan3D-2.1 | 42 | 0.867 | 51.9 | 4/6 | 3.77 / 4.70 | - | 0.1335 |
| mini_sweeper | Hunyuan3D-2.1 | 7 | 1.022 | 85.1 | 6/6 | 3.70 / 5.40 | - | 0.1376 |
| mini_sweeper | SAM 3D | 42 | 0.706 | 32.5 | 2/6 | 2.99 / 3.65 | - | 0.1687 |
| mini_sweeper | SAM 3D | 7 | 0.437 | 8.1 | 2/6 | 1.43 / 2.24 | - | 0.1454 |
| mini_dust_pan | library_v3 | - | 0.331 | 5.6 | 0/6 | 1.95 / 1.78 | - | - |
| mini_dust_pan | Pixal3D-MV (posed) | 42 | 0.240 | 5.3 | 0/6 | 2.18 / 1.05 | 0.908 | - |
| mini_dust_pan | Pixal3D-MV (posed) | 7 | 0.236 | 6.0 | 0/6 | 2.12 / 1.09 | 0.911 | - |
| mini_dust_pan | Pixal3D view 0 only | 42 | 0.628 | 83.7 | 6/6 | 15.76 / 12.48 | 0.737 | - |
| mini_dust_pan | Pixal3D view 0 only | 7 | 0.528 | 20.2 | 0/6 | 11.25 / 9.13 | 0.751 | - |
| mini_dust_pan | TRELLIS.2 | 42 | 0.339 | 9.9 | 0/6 | 1.88 / 1.35 | - | 0.1861 |
| mini_dust_pan | TRELLIS.2 | 7 | 0.338 | 10.7 | 0/6 | 2.42 / 1.37 | - | 0.1883 |
| mini_dust_pan | TripoSG | 42 | 0.754 | 20.2 | 0/6 | 3.08 / 2.53 | - | 0.1287 |
| mini_dust_pan | TripoSG | 7 | 0.516 | 12.9 | 0/6 | 2.99 / 2.50 | - | 0.0997 |
| mini_dust_pan | Hunyuan3D-2.1 | 42 | 0.231 | 5.2 | 0/6 | 1.68 / 1.40 | - | 0.0802 |
| mini_dust_pan | Hunyuan3D-2.1 | 7 | 0.396 | 12.7 | 0/6 | 1.46 / 1.35 | - | 0.0999 |
| mini_dust_pan | SAM 3D | 42 | 0.261 | 7.5 | 0/6 | 1.21 / 1.13 | - | 0.1664 |
| mini_dust_pan | SAM 3D | 7 | 0.333 | 13.8 | 0/6 | 1.56 / 1.65 | - | 0.1828 |
| beige_cup | library_v3 | - | 0.856 | 6.5 | 0/6 | 1.51 / 2.14 | - | - |
| beige_cup | Pixal3D-MV (posed) | 42 | 0.274 | 6.2 | 0/6 | 3.38 / 2.86 | 0.986 | - |
| beige_cup | Pixal3D-MV (posed) | 7 | 0.512 | 4.3 | 0/6 | 3.92 / 3.31 | 0.94 | - |
| beige_cup | TRELLIS.2 | 42 | 0.728 | 121.1 | 6/6 | 1.86 / 3.04 | - | 0.3543 |
| beige_cup | TRELLIS.2 | 7 | 1.321 | 28.9 | 0/6 | 7.78 / 9.64 | - | 0.2658 |
| beige_cup | TripoSG | 42 | 1.837 | 125.0 | 6/6 | 4.49 / 13.44 | - | 0.1883 |
| beige_cup | TripoSG | 7 | 1.230 | 22.3 | 0/6 | 3.20 / 8.83 | - | 0.1563 |
| beige_cup | Hunyuan3D-2.1 | 42 | 0.461 | 15.3 | 0/6 | 2.05 / 5.42 | - | 0.0996 |
| beige_cup | Hunyuan3D-2.1 | 7 | 0.954 | 26.4 | 0/6 | 3.19 / 9.37 | - | 0.0963 |
| beige_cup | SAM 3D | 42 | 0.526 | 21.5 | 0/6 | 0.89 / 1.94 | - | 0.1415 |
| beige_cup | SAM 3D | 7 | 0.321 | 18.3 | 0/6 | 0.90 / 2.24 | - | 0.1505 |

## Would the GT-free metric have picked the best mesh? (per object, over its scored generated meshes)

GT-free score = median obs->mesh + median mesh->obs (mm), lower is better. Spearman rho between the GT-free score and CD-O over the object's generated meshes; pick = the GT-free argmin; regret = its CD-O minus the best CD-O among the same meshes. "beats lib" asks whether the GT-free pick has lower CD-O than library_v3.

| object | n | Spearman rho | GT-free pick | its CD-O | best generated (CD-O) | regret | GT-free pick beats library_v3? | GT-free would prefer the pick over library_v3? |
|---|---|---|---|---|---|---|---|---|
| white_pot | 10 | 0.68 | sam3d/ep41_white_pot_k279_s7 | 0.328 | trellis2/ep41_white_pot_k279_s7 (0.318) | 0.010 | yes (0.437) | yes (3.6 vs 4.6 mm) |
| white_pot_lid | 10 | 0.52 | hy21/ep2_white_pot_lid_k321_s7 | 0.353 | pixal_mv/ep2_white_pot_lid_s42 (0.253) | 0.100 | yes (0.421) | yes (2.3 vs 5.9 mm) |
| blue_cup | 10 | -0.21 | pixal_mv/ep22_blue_cup_s42 | 0.407 | sam3d/ep22_blue_cup_k156_s7 (0.268) | 0.139 | yes (0.523) | yes (3.0 vs 6.1 mm) |
| water_pitcher | 10 | 0.67 | sam3d/ep22_water_pitcher_k174_s42 | 0.771 | hy21/ep22_water_pitcher_k174_s42 (0.378) | 0.393 | yes (0.894) | yes (5.3 vs 8.8 mm) |
| wooden_piece_1 | 10 | -0.15 | triposg/ep23_wooden_piece_1_k27_s7 | 0.336 | pixal_mv/ep23_wooden_piece_1_s42 (0.182) | 0.153 | no (0.222) | yes (11.3 vs 23.6 mm) |
| wooden_piece_2 | 12 | 0.21 | sam3d/ep23_wooden_piece_2_k6_s42 | 0.321 | sam3d/ep23_wooden_piece_2_k6_s7 (0.202) | 0.120 | no (0.216) | yes (2.6 vs 2.7 mm) |
| plastic_dish_rack | 10 | 0.65 | sam3d/ep26_plastic_dish_rack_k144_s7 | 0.604 | sam3d/ep26_plastic_dish_rack_k144_s7 (0.604) | 0.000 | no (0.555) | no (11.0 vs 10.1 mm) |
| mini_sweeper | 10 | 0.22 | sam3d/ep31_mini_sweeper_k270_s7 | 0.437 | sam3d/ep31_mini_sweeper_k270_s7 (0.437) | 0.000 | no (0.317) | yes (3.7 vs 4.3 mm) |
| mini_dust_pan | 12 | 0.71 | sam3d/ep39_mini_dust_pan_k297_s42 | 0.261 | hy21/ep39_mini_dust_pan_k297_s42 (0.231) | 0.029 | yes (0.331) | yes (2.3 vs 3.7 mm) |
| beige_cup | 10 | 0.72 | sam3d/ep11_beige_cup_k6_s42 | 0.526 | pixal_mv/ep11_beige_cup_s42 (0.274) | 0.252 | yes (0.856) | yes (2.8 vs 3.7 mm) |

All 104 meshes pooled: Spearman rho(GT-free, CD-O) = 0.46. Per object: median rho 0.58 (range -0.21 to 0.72); the GT-free pick is the CD-O best on 2/10 objects; its CD-O rank among the object's meshes: [2, 4, 6, 6, 6, 9, 1, 1, 4, 5]; mean regret 0.120 cm.
A GT-free selector over {library_v3, best-GT-free generated} per object would choose generated on 9/10 objects; mean CD-O 0.429 vs library_v3 0.477 [D].
