### Chain per episode and object (registered ADD AUC vs public mocap)

lib = our submitted meshes (library_v3; ep11 library_v3x), scan = public scans. perc = perception that fed the reference; e2s = mkref output before contact retarget; ref = final reference (evaluator reference columns); sim = rollout r1. d_mkref = e2s - perc, d_cr = ref - e2s, reg = lib - scan.

| ep | object | perc lib | e2s lib | ref lib | d_mkref | d_cr | ref-perc | perc scan | e2s scan | ref scan | reg (perc) | reg (ref) | sim lib | sim scan |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | white_pot | 0.993 | 0.993 | 0.986 | 0.000 | -0.007 | -0.007 | 0.993 | 0.993 | 0.987 | -0.000 | -0.001 | 0.626 | 0.627 |
| 2 | white_pot_lid | 0.981 | 0.957 | 0.974 | -0.023 | 0.017 | -0.007 | 0.986 | 0.994 | 0.980 | -0.005 | -0.006 | 0.276 | 0.263 |
| 2 | (scene) | 0.987 | 0.975 | 0.980 | -0.012 | 0.005 | -0.007 | 0.989 | 0.993 | 0.984 | -0.003 | -0.004 | 0.451 | 0.445 |
| 11 | blue_cup | 0.862 | 0.862 | 0.864 | 0.000 | 0.001 | 0.001 | 0.860 | 0.860 | 0.864 | 0.003 | 0.000 | 0.993 | 0.993 |
| 11 | beige_cup | 0.931 | 0.908 | 0.905 | -0.023 | -0.003 | -0.026 | 0.973 | 0.985 | 0.980 | -0.042 | -0.074 | 0.141 | 0.141 |
| 11 | (scene) | 0.896 | 0.885 | 0.884 | -0.011 | -0.001 | -0.012 | 0.916 | 0.922 | 0.921 | -0.020 | -0.037 | 0.567 | 0.567 |
| 12 | blue_cup | 0.933 | 0.933 | 0.933 | 0.000 | 0.000 | 0.000 | 0.988 | 0.988 | 0.988 | -0.055 | -0.055 | 0.870 | 0.929 |
| 12 | plastic_dish_rack | 1.000 | 0.938 | 0.938 | -0.061 | 0.000 | -0.061 | 0.939 | 0.998 | 0.998 | 0.060 | -0.060 | 0.972 | 0.939 |
| 12 | (scene) | 0.966 | 0.935 | 0.935 | -0.031 | 0.000 | -0.031 | 0.964 | 0.993 | 0.993 | 0.003 | -0.057 | 0.921 | 0.934 |
| 18 | mini_sweeper | 0.995 | 0.995 | 0.992 | 0.000 | -0.003 | -0.003 | 0.996 | 0.996 | 0.993 | -0.000 | -0.001 | 0.985 | 0.984 |
| 18 | mini_dust_pan | 0.933 | 0.947 | 0.939 | 0.013 | -0.007 | 0.006 | 0.946 | 0.959 | 0.947 | -0.012 | -0.008 | 0.935 | 0.972 |
| 18 | (scene) | 0.964 | 0.971 | 0.966 | 0.007 | -0.005 | 0.002 | 0.971 | 0.977 | 0.970 | -0.007 | -0.004 | 0.960 | 0.978 |
| 21 | blue_cup | 0.983 | 0.983 | 0.980 | 0.000 | -0.003 | -0.003 | 0.996 | 0.996 | 0.993 | -0.013 | -0.013 | 0.960 | 0.970 |
| 21 | water_pitcher | 0.692 | 0.579 | 0.575 | -0.112 | -0.004 | -0.116 | 0.919 | 0.824 | 0.823 | -0.227 | -0.248 | 0.620 | 0.858 |
| 21 | (scene) | 0.837 | 0.781 | 0.778 | -0.056 | -0.004 | -0.060 | 0.958 | 0.910 | 0.908 | -0.120 | -0.130 | 0.790 | 0.914 |
| 24 | wooden_piece_1 | 0.776 | 0.776 | 0.776 | 0.000 | 0.000 | 0.000 | 0.757 | 0.757 | 0.757 | 0.019 | 0.019 | 0.266 | 0.250 |
| 24 | wooden_piece_2 | 0.847 | 0.856 | 0.856 | 0.009 | 0.000 | 0.009 | 0.823 | 0.834 | 0.834 | 0.024 | 0.022 | 0.350 | 0.350 |
| 24 | (scene) | 0.812 | 0.816 | 0.816 | 0.005 | 0.000 | 0.005 | 0.790 | 0.796 | 0.796 | 0.021 | 0.021 | 0.308 | 0.300 |
| 26 | plastic_dish_rack | 0.997 | 0.997 | 0.991 | 0.000 | -0.007 | -0.007 | 0.997 | 0.997 | 0.991 | 0.000 | -0.001 | 0.869 | 0.867 |
| 26 | white_pot | 0.947 | 0.824 | 0.855 | -0.123 | 0.031 | -0.092 | 0.913 | 0.866 | 0.871 | 0.034 | -0.015 | 0.205 | 0.186 |
| 26 | (scene) | 0.972 | 0.911 | 0.923 | -0.061 | 0.012 | -0.049 | 0.955 | 0.932 | 0.931 | 0.017 | -0.008 | 0.537 | 0.527 |
| 27 | plastic_dish_rack | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 | 1.000 |
| 27 | white_pot | 0.919 | 0.924 | 0.924 | 0.006 | 0.000 | 0.006 | 0.878 | 0.887 | 0.887 | 0.041 | 0.038 | 0.909 | 0.866 |
| 27 | (scene) | 0.959 | 0.962 | 0.962 | 0.003 | 0.000 | 0.003 | 0.939 | 0.943 | 0.943 | 0.020 | 0.019 | 0.954 | 0.933 |
| 31 | mini_sweeper | 0.912 | 0.912 | 0.912 | 0.000 | 0.000 | 0.000 | 0.950 | 0.950 | 0.949 | -0.038 | -0.036 | 0.788 | 0.799 |
| 31 | plastic_dish_rack | 0.688 | 0.678 | 0.735 | -0.009 | 0.056 | 0.047 | 0.820 | 0.812 | 0.900 | -0.133 | -0.165 | 0.751 | 0.779 |
| 31 | (scene) | 0.800 | 0.795 | 0.823 | -0.005 | 0.028 | 0.024 | 0.885 | 0.881 | 0.924 | -0.086 | -0.101 | 0.770 | 0.789 |
| 39 | mini_dust_pan | 0.960 | 0.960 | 0.956 | 0.000 | -0.004 | -0.004 | 0.977 | 0.977 | 0.980 | -0.016 | -0.025 | 0.958 | 0.977 |
| 39 | (scene) | 0.960 | 0.960 | 0.956 | 0.000 | -0.004 | -0.004 | 0.977 | 0.977 | 0.980 | -0.016 | -0.025 | 0.958 | 0.977 |

### Perception sweep (base arm, 20 episodes) and track-guard arm (8), re-scored

| ep | object | sweep lib | sweep scan | reg | guard lib | guard scan | box-stored sweep (library_v2) |
|---|---|---|---|---|---|---|---|
| 0 | white_pot | 0.993 | 0.994 | -0.001 | 0.992 | 0.994 | 0.993 |
| 0 | white_pot_lid | 0.000 | 0.000 | 0.000 | 0.936 | 0.996 | 0.000 |
| 0 | (scene) | 0.496 | 0.497 | -0.001 | 0.964 | 0.995 | 0.496 |
| 2 | white_pot | 0.992 | 0.992 | 0.000 |  |  | 0.992 |
| 2 | white_pot_lid | 0.972 | 0.965 | 0.008 |  |  | 0.972 |
| 2 | (scene) | 0.982 | 0.979 | 0.004 |  |  | 0.982 |
| 11 | blue_cup | 0.862 | 0.860 | 0.003 | 0.862 | 0.860 | 0.862 |
| 11 | beige_cup | 0.933 | 0.992 | -0.059 | 0.933 | 0.992 | 0.933 |
| 11 | (scene) | 0.898 | 0.926 | -0.028 | 0.898 | 0.926 | 0.898 |
| 12 | blue_cup | 0.935 | 0.988 | -0.053 | 0.933 | 0.988 | 0.935 |
| 12 | plastic_dish_rack | 1.000 | 0.939 | 0.061 | 1.000 | 0.939 | 1.000 |
| 12 | (scene) | 0.967 | 0.963 | 0.004 | 0.966 | 0.963 | 0.967 |
| 13 | blue_cup | 0.933 | 0.865 | 0.068 |  |  | 0.933 |
| 13 | plastic_dish_rack | 0.988 | 0.938 | 0.051 |  |  | 0.988 |
| 13 | (scene) | 0.961 | 0.901 | 0.059 |  |  | 0.961 |
| 18 | mini_sweeper | 0.995 | 0.996 | -0.000 | 0.995 | 0.996 | 0.995 |
| 18 | mini_dust_pan | 0.933 | 0.946 | -0.012 | 0.933 | 0.946 | 0.881 |
| 18 | (scene) | 0.964 | 0.971 | -0.007 | 0.964 | 0.971 | 0.938 |
| 21 | blue_cup | 0.982 | 0.995 | -0.014 | 0.982 | 0.995 | 0.982 |
| 21 | water_pitcher | 0.683 | 0.913 | -0.230 | 0.683 | 0.913 | 0.683 |
| 21 | (scene) | 0.833 | 0.954 | -0.122 | 0.833 | 0.954 | 0.833 |
| 22 | blue_cup | 0.992 | 1.000 | -0.007 |  |  | 0.992 |
| 22 | water_pitcher | 0.750 | 0.965 | -0.215 |  |  | 0.750 |
| 22 | (scene) | 0.871 | 0.982 | -0.111 |  |  | 0.871 |
| 23 | wooden_piece_1 | 0.083 | 0.084 | -0.001 | 0.083 | 0.084 | 0.083 |
| 23 | wooden_piece_2 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 23 | (scene) | 0.041 | 0.042 | -0.000 | 0.041 | 0.042 | 0.041 |
| 24 | wooden_piece_1 | 0.776 | 0.757 | 0.019 | 0.776 | 0.757 | 0.776 |
| 24 | wooden_piece_2 | 0.847 | 0.823 | 0.024 | 0.847 | 0.823 | 0.847 |
| 24 | (scene) | 0.812 | 0.790 | 0.021 | 0.812 | 0.790 | 0.812 |
| 26 | plastic_dish_rack | 0.994 | 0.993 | 0.000 |  |  | 0.994 |
| 26 | white_pot | 0.937 | 0.903 | 0.033 |  |  | 0.937 |
| 26 | (scene) | 0.965 | 0.948 | 0.017 |  |  | 0.965 |
| 27 | plastic_dish_rack | 1.000 | 1.000 | 0.000 |  |  | 1.000 |
| 27 | white_pot | 0.922 | 0.883 | 0.039 |  |  | 0.922 |
| 27 | (scene) | 0.961 | 0.942 | 0.019 |  |  | 0.961 |
| 31 | mini_sweeper | 0.912 | 0.950 | -0.038 | 0.912 | 0.950 | 0.918 |
| 31 | plastic_dish_rack | 0.688 | 0.832 | -0.144 | 0.688 | 0.832 | 0.692 |
| 31 | (scene) | 0.800 | 0.891 | -0.091 | 0.800 | 0.891 | 0.805 |
| 39 | mini_dust_pan | 0.960 | 0.977 | -0.016 |  |  | 0.960 |
| 39 | (scene) | 0.960 | 0.977 | -0.016 |  |  | 0.960 |
| 40 | mini_dust_pan | 0.957 | 0.980 | -0.023 |  |  | 0.957 |
| 40 | (scene) | 0.957 | 0.980 | -0.023 |  |  | 0.957 |
| 41 | white_pot | 0.991 | 0.989 | 0.002 |  |  | 0.991 |
| 41 | (scene) | 0.991 | 0.989 | 0.002 |  |  | 0.991 |
| 42 | white_pot | 0.992 | 0.986 | 0.005 |  |  | 0.992 |
| 42 | (scene) | 0.992 | 0.986 | 0.005 |  |  | 0.992 |
| 43 | white_pot | 0.948 | 0.981 | -0.033 |  |  | 0.948 |
| 43 | (scene) | 0.948 | 0.981 | -0.033 |  |  | 0.948 |
| 44 | white_pot | 0.997 | 0.998 | -0.001 |  |  | 0.997 |
| 44 | (scene) | 0.997 | 0.998 | -0.001 |  |  | 0.997 |
| 45 | white_pot | 0.980 | 0.974 | 0.005 |  |  | 0.980 |
| 45 | (scene) | 0.980 | 0.974 | 0.005 |  |  | 0.980 |

### Per-object mean AUC over public episodes (n = object-episodes)

newest perc = guard arm where it exists (0, 11, 12, 18, 21, 23, 24, 31), else sweep base; excl. ep23 = without the frame-0 board swap of ep23 (identity failure, the boards then score 0.08 / 0.00).

| object | review midpoint | sweep base lib (n) | sweep base scan | newest perc lib | newest perc scan | newest lib excl. ep23 | newest scan excl. ep23 | canonical perc lib (n) | e2s lib | reference lib | reference scan |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pot | 0.97 | 0.972 (9) | 0.967 | 0.972 | 0.967 | 0.972 | 0.967 | 0.953 (3) | 0.914 | 0.922 | 0.915 |
| lid | 0.965 | 0.486 (2) | 0.482 | 0.954 | 0.980 | 0.954 | 0.980 | 0.981 (1) | 0.957 | 0.974 | 0.980 |
| blue | 0.95 | 0.941 (5) | 0.942 | 0.940 | 0.942 | 0.940 | 0.942 | 0.926 (3) | 0.926 | 0.925 | 0.948 |
| beige | 0.93 | 0.933 (1) | 0.992 | 0.933 | 0.992 | 0.933 | 0.992 | 0.931 (1) | 0.908 | 0.905 | 0.980 |
| rack | 0.95 | 0.934 (5) | 0.940 | 0.934 | 0.940 | 0.934 | 0.940 | 0.921 (4) | 0.903 | 0.916 | 0.972 |
| sweeper | 0.96 | 0.954 (2) | 0.973 | 0.954 | 0.973 | 0.954 | 0.973 | 0.954 (2) | 0.954 | 0.952 | 0.971 |
| pan | 0.95 | 0.950 (3) | 0.967 | 0.950 | 0.967 | 0.950 | 0.967 | 0.947 (2) | 0.953 | 0.948 | 0.964 |
| pitcher | 0.66 | 0.717 (2) | 0.939 | 0.717 | 0.939 | 0.717 | 0.939 | 0.692 (1) | 0.579 | 0.575 | 0.823 |
| board | 0.82 | 0.427 (4) | 0.416 | 0.427 | 0.416 | 0.812 | 0.790 | 0.812 (2) | 0.816 | 0.816 | 0.796 |

### Stale 20 Oct refsweep pairs (public-scan templates; scored with the scans)

| ep | object | perc | ref | ref - perc |
|---|---|---|---|---|
| 0 | white_pot | 0.366 | 0.366 | 0.000 |
| 0 | white_pot_lid | 0.001 | 0.001 | 0.000 |
| 0 | (scene) | 0.184 | 0.184 | 0.000 |
| 13 | blue_cup | 0.996 | 0.996 | 0.000 |
| 13 | plastic_dish_rack | 1.000 | 1.000 | 0.000 |
| 13 | (scene) | 0.998 | 0.998 | 0.000 |
| 22 | blue_cup | 1.000 | 1.000 | 0.000 |
| 22 | water_pitcher | 0.988 | 0.982 | -0.007 |
| 22 | (scene) | 0.994 | 0.991 | -0.003 |
| 23 | wooden_piece_1 | 0.999 | 0.999 | 0.000 |
| 23 | wooden_piece_2 | 0.998 | 0.997 | -0.001 |
| 23 | (scene) | 0.999 | 0.998 | -0.000 |
| 40 | mini_dust_pan | 0.997 | 0.997 | 0.000 |
| 40 | (scene) | 0.997 | 0.997 | 0.000 |
| 41 | white_pot | 0.999 | 0.999 | 0.000 |
| 41 | (scene) | 0.999 | 0.999 | 0.000 |
| 42 | white_pot | 0.986 | 0.986 | 0.000 |
| 42 | (scene) | 0.986 | 0.986 | 0.000 |
| 43 | white_pot | 0.993 | 0.993 | 0.000 |
| 43 | (scene) | 0.993 | 0.993 | 0.000 |
| 44 | white_pot | 0.999 | 0.999 | 0.000 |
| 44 | (scene) | 0.999 | 0.999 | 0.000 |
| 45 | white_pot | 0.966 | 0.966 | 0.000 |
| 45 | (scene) | 0.966 | 0.966 | 0.000 |

### Rollout r1: sim AUC vs sim_vs_ref x reference AUC (the hidden-loss model)

| ep | sim lib | sim_vs_ref (box, r1) | ref lib | sim_vs_ref x ref lib | static floor lib |
|---|---|---|---|---|---|
| 2 | 0.451 | 0.478 | 0.980 | 0.468 | 0.490 |
| 11 | 0.567 | 0.476 | 0.884 | 0.421 | 0.595 |
| 12 | 0.921 | 0.941 | 0.935 | 0.880 | 0.595 |
| 18 | 0.960 | 0.992 | 0.966 | 0.958 | 0.635 |
| 21 | 0.790 | 0.987 | 0.778 | 0.768 | 0.346 |
| 24 | 0.308 | 0.375 | 0.816 | 0.306 | 0.203 |
| 26 | 0.537 | 0.551 | 0.923 | 0.508 | 0.619 |
| 27 | 0.954 | 0.978 | 0.962 | 0.941 | 0.556 |
| 31 | 0.770 | 0.751 | 0.823 | 0.618 | 0.442 |
| 39 | 0.958 | 1.000 | 0.956 | 0.956 | 0.175 |

### Registration cost split by object (perception path / final reference; AUC per object)

Slot 0 is the first object listed: the kit aligns the scene on its frame-0 position.

| ep | path | object | all scans | only slot-0 object ours | only slot-1 object ours | all ours |
|---|---|---|---|---|---|---|
| 11 | perception | blue_cup | 0.860 | 0.862 | 0.860 | 0.862 |
| 11 | perception | beige_cup | 0.973 | 0.961 | 0.948 | 0.931 |
| 11 | reference | blue_cup | 0.864 | 0.864 | 0.864 | 0.864 |
| 11 | reference | beige_cup | 0.980 | 0.957 | 0.946 | 0.905 |
| 12 | perception | blue_cup | 0.988 | 0.950 | 0.989 | 0.933 |
| 12 | perception | plastic_dish_rack | 0.939 | 1.000 | 0.998 | 1.000 |
| 12 | reference | blue_cup | 0.988 | 0.950 | 0.989 | 0.933 |
| 12 | reference | plastic_dish_rack | 0.998 | 0.959 | 0.998 | 0.938 |
| 21 | perception | blue_cup | 0.996 | 0.997 | 0.979 | 0.983 |
| 21 | perception | water_pitcher | 0.919 | 0.810 | 0.798 | 0.692 |
| 21 | reference | blue_cup | 0.993 | 0.995 | 0.977 | 0.980 |
| 21 | reference | water_pitcher | 0.823 | 0.700 | 0.695 | 0.575 |
| 31 | perception | mini_sweeper | 0.950 | 0.912 | 0.950 | 0.912 |
| 31 | perception | plastic_dish_rack | 0.820 | 0.756 | 0.812 | 0.688 |
| 31 | reference | mini_sweeper | 0.949 | 0.912 | 0.949 | 0.912 |
| 31 | reference | plastic_dish_rack | 0.900 | 0.776 | 0.835 | 0.735 |

### Frame-level diagnosis of the flagged links (diag.py)

dAUC = B - A; trans/rot = the change with only B's position (orientation) applied; change = B - A in the kit-aligned frame; dz err = mean vertical error of the anchor point vs mocap (A -> B).

| link | ep | object | meshes | dAUC | frame-0 share | trans only | rot only | frames worse / better | change dz cm (mean) | change rot deg (mean / max) | dz err A -> B cm | worst segment |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cr | 18 | mini_dust_pan | ours | -0.007 | +0.0000 | -0.002 | -0.009 | 45 / 7 | -0.18 | 2.43 / 13.05 | +0.96 -> +0.78 | f69-105 (-0.006) |
| cr | 26 | plastic_dish_rack | ours | -0.007 | +0.0000 | -0.007 | -0.001 | 17 / 0 | -0.22 | 1.83 / 3.22 | -0.38 -> -0.60 | f47-59 (-0.003) |
| cr | 26 | white_pot | ours | +0.031 | +0.0000 | +0.031 | -0.002 | 1 / 62 | +0.65 | 2.15 / 6.68 | -2.28 -> -1.63 | f96-157 (+0.032) |
| cr | 2 | white_pot | ours | -0.007 | +0.0000 | -0.007 | +0.000 | 24 / 3 | -0.08 | 2.31 / 4.57 | +0.06 -> -0.03 | f191-205 (-0.006) |
| cr | 2 | white_pot_lid | ours | +0.017 | +0.0000 | +0.018 | -0.002 | 20 / 111 | +0.15 | 2.99 / 4.40 | -0.81 -> -0.67 | f313-342 (+0.004) |
| cr | 31 | plastic_dish_rack | ours | +0.057 | +0.0000 | +0.007 | +0.003 | 0 / 124 | -0.81 | 1.71 / 3.14 | +2.97 -> +2.16 | f17-80 (+0.028) |
| mkref | 11 | beige_cup | ours | -0.023 | +0.0000 | -0.023 | +0.000 | 25 / 0 | +0.31 | 0.01 / 0.01 | +1.00 -> +1.32 | f41-80 (-0.020) |
| mkref | 11 | beige_cup | scan | +0.012 | +0.0000 | +0.012 | +0.000 | 9 / 34 | +0.31 | 0.03 / 0.03 | -0.30 -> +0.02 | f104-136 (+0.015) |
| mkref | 12 | plastic_dish_rack | ours | -0.061 | -0.0003 | -0.061 | +0.000 | 178 / 0 | +0.99 | 0.00 / 0.00 | +0.43 -> +1.43 | f0-180 (-0.061) |
| mkref | 12 | plastic_dish_rack | scan | +0.059 | +0.0003 | +0.059 | +0.000 | 0 / 170 | +0.99 | 0.00 / 0.00 | -0.97 -> +0.03 | f92-180 (+0.030) |
| mkref | 18 | mini_dust_pan | ours | +0.013 | +0.0000 | +0.013 | +0.000 | 1 / 68 | -0.32 | 0.00 / 0.00 | +1.28 -> +0.96 | f49-114 (+0.010) |
| mkref | 21 | water_pitcher | ours | -0.112 | -0.0007 | -0.112 | +0.000 | 167 / 0 | +0.93 | 0.00 / 0.00 | +2.59 -> +3.52 | f0-185 (-0.112) |
| mkref | 21 | water_pitcher | scan | -0.095 | -0.0003 | -0.095 | +0.000 | 161 / 0 | +0.93 | 0.00 / 0.00 | +1.06 -> +1.99 | f0-185 (-0.095) |
| mkref | 26 | white_pot | ours | -0.123 | -0.0016 | -0.123 | +0.000 | 113 / 3 | -2.59 | 0.00 / 0.00 | +0.31 -> -2.28 | f0-68 (-0.101) |
| mkref | 26 | white_pot | scan | -0.047 | -0.0008 | -0.047 | +0.000 | 69 / 21 | -2.59 | 0.00 / 0.00 | +0.83 -> -1.76 | f0-69 (-0.063) |
| mkref | 2 | white_pot_lid | ours | -0.024 | -0.0002 | -0.024 | +0.000 | 128 / 1 | -0.16 | 0.00 / 0.00 | -0.65 -> -0.81 | f272-300 (-0.004) |
| mkref | 2 | white_pot_lid | scan | +0.008 | +0.0000 | +0.008 | +0.000 | 2 / 45 | -0.16 | 0.00 / 0.00 | +0.25 -> +0.09 | f116-146 (+0.004) |
| mkref | 31 | plastic_dish_rack | ours | -0.009 | +0.0000 | -0.009 | +0.000 | 22 / 0 | +1.03 | 0.00 / 0.00 | +1.94 -> +2.97 | f156-178 (-0.006) |
| reg | 0 | white_pot_lid | scan->ours | -0.059 | -0.0002 | -0.059 | -0.000 | 350 / 1 | -0.70 | 2.28 / 2.59 | -0.43 -> -1.13 | f76-246 (-0.029) |
| reg | 11 | beige_cup | scan->ours | -0.042 | -0.0005 | -0.037 | -0.012 | 86 / 1 | +1.30 | 130.65 / 130.71 | -0.30 -> +1.00 | f46-103 (-0.024) |
| reg | 12 | blue_cup | scan->ours | -0.055 | +0.0000 | -0.058 | +0.000 | 105 / 2 | +1.33 | 1.86 / 2.05 | -0.25 -> +1.08 | f78-180 (-0.053) |
| reg | 12 | plastic_dish_rack | scan->ours | +0.060 | +0.0003 | +0.060 | +0.000 | 1 / 176 | +1.40 | 0.01 / 0.07 | -0.97 -> +0.43 | f92-180 (+0.031) |
| reg | 21 | blue_cup | scan->ours | -0.013 | +0.0000 | -0.013 | +0.000 | 40 / 0 | +0.01 | 1.72 / 1.86 | +0.34 -> +0.34 | f43-91 (-0.011) |
| reg | 21 | water_pitcher | scan->ours | -0.227 | -0.0010 | -0.227 | -0.002 | 186 / 0 | +1.54 | 1.03 / 3.02 | +1.06 -> +2.59 | f0-185 (-0.227) |
| reg | 22 | blue_cup | scan->ours | -0.007 | +0.0000 | -0.007 | +0.000 | 22 / 0 | -0.03 | 1.39 / 1.87 | +0.11 -> +0.07 | f46-60 (-0.003) |
| reg | 22 | water_pitcher | scan->ours | -0.215 | -0.0010 | -0.214 | -0.006 | 189 / 0 | +1.60 | 1.07 / 3.83 | +0.66 -> +2.26 | f0-188 (-0.215) |
| reg | 26 | white_pot | scan->ours | +0.034 | +0.0000 | +0.031 | +0.008 | 1 / 66 | -0.53 | 2.48 / 3.39 | +0.83 -> +0.31 | f68-157 (+0.035) |
| reg | 27 | white_pot | scan->ours | +0.041 | +0.0000 | +0.045 | +0.002 | 1 / 89 | -0.37 | 1.81 / 2.47 | +1.02 -> +0.65 | f5-71 (+0.024) |
| reg | 31 | mini_sweeper | scan->ours | -0.038 | +0.0000 | -0.038 | -0.001 | 106 / 0 | -0.05 | 0.84 / 1.62 | -0.16 -> -0.21 | f99-145 (-0.015) |
| reg | 31 | plastic_dish_rack | scan->ours | -0.133 | -0.0009 | -0.008 | -0.008 | 290 / 0 | +0.99 | 3.49 / 3.51 | +0.95 -> +1.94 | f0-289 (-0.133) |
| reg | 43 | white_pot | scan->ours | -0.033 | +0.0000 | -0.017 | -0.017 | 164 / 5 | +0.39 | 2.52 / 3.44 | +0.13 -> +0.52 | f236-325 (-0.017) |

### Flags

- {"kind": "ref_below_perc", "ep": 11, "object": "beige_cup", "perc_lib": 0.9307, "ref_lib": 0.9051, "e2s_lib": 0.9078}
- {"kind": "lib_below_scan_perc", "ep": 11, "object": "beige_cup", "lib": 0.9307, "scan": 0.9726}
- {"kind": "lib_below_scan_ref", "ep": 11, "object": "beige_cup", "lib": 0.9051, "scan": 0.9795}
- {"kind": "ref_below_perc", "ep": 11, "object": "(scene)", "perc_lib": 0.8964, "ref_lib": 0.8844, "e2s_lib": 0.885}
- {"kind": "lib_below_scan_ref", "ep": 11, "object": "(scene)", "lib": 0.8844, "scan": 0.9215}
- {"kind": "lib_below_scan_perc", "ep": 12, "object": "blue_cup", "lib": 0.9327, "scan": 0.9879}
- {"kind": "lib_below_scan_ref", "ep": 12, "object": "blue_cup", "lib": 0.9327, "scan": 0.9879}
- {"kind": "ref_below_perc", "ep": 12, "object": "plastic_dish_rack", "perc_lib": 0.9997, "ref_lib": 0.9382, "e2s_lib": 0.9382}
- {"kind": "lib_below_scan_ref", "ep": 12, "object": "plastic_dish_rack", "lib": 0.9382, "scan": 0.9979}
- {"kind": "ref_below_perc", "ep": 12, "object": "(scene)", "perc_lib": 0.9662, "ref_lib": 0.9354, "e2s_lib": 0.9354}
- {"kind": "lib_below_scan_ref", "ep": 12, "object": "(scene)", "lib": 0.9354, "scan": 0.9929}
- {"kind": "ref_below_perc", "ep": 21, "object": "water_pitcher", "perc_lib": 0.6915, "ref_lib": 0.5753, "e2s_lib": 0.5793}
- {"kind": "ref_below_perc_scan", "ep": 21, "object": "water_pitcher", "perc_scan": 0.9187, "ref_scan": 0.8229, "e2s_scan": 0.8236}
- {"kind": "lib_below_scan_perc", "ep": 21, "object": "water_pitcher", "lib": 0.6915, "scan": 0.9187}
- {"kind": "lib_below_scan_ref", "ep": 21, "object": "water_pitcher", "lib": 0.5753, "scan": 0.8229}
- {"kind": "ref_below_perc", "ep": 21, "object": "(scene)", "perc_lib": 0.8372, "ref_lib": 0.7776, "e2s_lib": 0.7811}
- {"kind": "ref_below_perc_scan", "ep": 21, "object": "(scene)", "perc_scan": 0.9575, "ref_scan": 0.9079, "e2s_scan": 0.9099}
- {"kind": "lib_below_scan_perc", "ep": 21, "object": "(scene)", "lib": 0.8372, "scan": 0.9575}
- {"kind": "lib_below_scan_ref", "ep": 21, "object": "(scene)", "lib": 0.7776, "scan": 0.9079}
- {"kind": "ref_below_perc", "ep": 26, "object": "white_pot", "perc_lib": 0.9474, "ref_lib": 0.8552, "e2s_lib": 0.8244}
- {"kind": "ref_below_perc_scan", "ep": 26, "object": "white_pot", "perc_scan": 0.913, "ref_scan": 0.8706, "e2s_scan": 0.8663}
- {"kind": "ref_below_perc", "ep": 26, "object": "(scene)", "perc_lib": 0.9723, "ref_lib": 0.9229, "e2s_lib": 0.9108}
- {"kind": "ref_below_perc_scan", "ep": 26, "object": "(scene)", "perc_scan": 0.9551, "ref_scan": 0.931, "e2s_scan": 0.9318}
- {"kind": "lib_below_scan_perc", "ep": 31, "object": "mini_sweeper", "lib": 0.9121, "scan": 0.9504}
- {"kind": "lib_below_scan_ref", "ep": 31, "object": "mini_sweeper", "lib": 0.9121, "scan": 0.9485}
- {"kind": "lib_below_scan_perc", "ep": 31, "object": "plastic_dish_rack", "lib": 0.6875, "scan": 0.8203}
- {"kind": "lib_below_scan_ref", "ep": 31, "object": "plastic_dish_rack", "lib": 0.7345, "scan": 0.9}
- {"kind": "lib_below_scan_perc", "ep": 31, "object": "(scene)", "lib": 0.7998, "scan": 0.8853}
- {"kind": "lib_below_scan_ref", "ep": 31, "object": "(scene)", "lib": 0.8233, "scan": 0.9242}
- {"kind": "lib_below_scan_guard", "ep": 0, "object": "white_pot_lid", "lib": 0.9363, "scan": 0.9955}
- {"kind": "lib_below_scan_guard", "ep": 0, "object": "(scene)", "lib": 0.9641, "scan": 0.9945}
- {"kind": "lib_below_scan_sweep", "ep": 11, "object": "beige_cup", "lib": 0.9334, "scan": 0.9922}
- {"kind": "lib_below_scan_guard", "ep": 11, "object": "beige_cup", "lib": 0.9334, "scan": 0.9922}
- {"kind": "lib_below_scan_sweep", "ep": 12, "object": "blue_cup", "lib": 0.9347, "scan": 0.9879}
- {"kind": "lib_below_scan_guard", "ep": 12, "object": "blue_cup", "lib": 0.9327, "scan": 0.9879}
- {"kind": "lib_below_scan_sweep", "ep": 21, "object": "water_pitcher", "lib": 0.6835, "scan": 0.9133}
- {"kind": "lib_below_scan_guard", "ep": 21, "object": "water_pitcher", "lib": 0.6835, "scan": 0.9133}
- {"kind": "lib_below_scan_sweep", "ep": 21, "object": "(scene)", "lib": 0.8325, "scan": 0.9543}
- {"kind": "lib_below_scan_guard", "ep": 21, "object": "(scene)", "lib": 0.8325, "scan": 0.9543}
- {"kind": "lib_below_scan_sweep", "ep": 22, "object": "water_pitcher", "lib": 0.7497, "scan": 0.9646}
- {"kind": "lib_below_scan_sweep", "ep": 22, "object": "(scene)", "lib": 0.871, "scan": 0.9821}
- {"kind": "lib_below_scan_sweep", "ep": 31, "object": "mini_sweeper", "lib": 0.9119, "scan": 0.9496}
- {"kind": "lib_below_scan_guard", "ep": 31, "object": "mini_sweeper", "lib": 0.9119, "scan": 0.9496}
- {"kind": "lib_below_scan_sweep", "ep": 31, "object": "plastic_dish_rack", "lib": 0.6879, "scan": 0.8319}
- {"kind": "lib_below_scan_guard", "ep": 31, "object": "plastic_dish_rack", "lib": 0.6879, "scan": 0.8319}
- {"kind": "lib_below_scan_sweep", "ep": 31, "object": "(scene)", "lib": 0.7999, "scan": 0.8907}
- {"kind": "lib_below_scan_guard", "ep": 31, "object": "(scene)", "lib": 0.7999, "scan": 0.8907}
- {"kind": "lib_below_scan_sweep", "ep": 43, "object": "white_pot", "lib": 0.9482, "scan": 0.9808}
- {"kind": "lib_below_scan_sweep", "ep": 43, "object": "(scene)", "lib": 0.9482, "scan": 0.9808}
