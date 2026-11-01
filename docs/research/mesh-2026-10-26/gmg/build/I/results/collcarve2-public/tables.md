### Pieces per object (F-I5.15 / F-I5.16 ladder)

| ep | object | lathe test (rotc sigma) | routes tried | delivered route, pieces | ring layout (N_s x B_w + base, n_h) | min wall mm | cavity intrusion mm (construction / continuity rays) | keep-out (hulls > 0.3 cm3, max cm3) | share of SHELL volume |
|---|---|---|---|---|---|---|---|---|---|
| 12 | blue_cup | yes (1.60) | 2_lathe (no_accepted_layout; 8b1:min_wall, 8b2:min_wall, 12b1:min_wall, 8b1:min_wall, 8b2:min_wall, 16b1:min_wall) -> 3_coacd (gate fail: 12 > 0.3, max 0.480; n 82) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 29) | 4_voxels, 29 | - | - | - / - | 0, 0.000 | 0.050 |
| 12 | plastic_dish_rack | no (14.61) | 3_coacd (gate fail: 22 > 0.3, max 0.976; n 82) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 45) | 4_voxels, 45 | - | - | - / - | 0, 0.000 | 0.061 |
| 13 | blue_cup | yes (1.77) | 2_lathe (no_accepted_layout; 8b1:min_wall, 8b2:min_wall, 8b1:min_wall, 12b1:min_wall, 8b2:min_wall, 16b1:min_wall) -> 3_coacd (gate fail: 7 > 0.3, max 0.704; n 75) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 25) | 4_voxels, 25 | - | - | - / - | 0, 0.000 | 0.049 |
| 13 | plastic_dish_rack | no (12.80) | 3_coacd (gate fail: 11 > 0.3, max 0.776; n 82) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 24) | 4_voxels, 24 | - | - | - / - | 0, 0.000 | 0.036 |
| 31 | mini_sweeper | no (3.07) | 3_coacd (gate fail: 1 > 0.3, max 0.344; n 45) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 3) | 4_voxels, 3 | - | - | - / - | 0, 0.000 | 0.018 |
| 31 | plastic_dish_rack | no (9.15) | 3_coacd (gate fail: 22 > 0.3, max 1.736; n 82) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 47) | 4_voxels, 47 | - | - | - / - | 0, 0.000 | 0.047 |
| 11 | blue_cup | no (3.01) | 3_coacd (gate fail: 21 > 0.3, max 1.552; n 81) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 17) | 4_voxels, 17 | - | - | - / - | 0, 0.000 | 0.038 |
| 11 | beige_cup | yes (2.60) | 2_lathe (no_accepted_layout; 8b1:min_wall, 8b2:min_wall, 12b1:min_wall, 12b2:min_wall, 8b1:min_wall, 8b2:min_wall) -> 3_coacd (gate fail: 5 > 0.3, max 0.440; n 73) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 20) | 4_voxels, 20 | - | - | - / - | 0, 0.000 | 0.038 |
| 2 | white_pot | yes (2.39) | 2_lathe (no_accepted_layout; 8b1:min_wall, 12b1:min_wall, 8b2:min_wall, 8b1:min_wall, 16b1:min_wall, 8b2:min_wall) -> 3_coacd (gate fail: 9 > 0.3, max 1.136; n 82) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 42) | 4_voxels, 42 | - | - | - / - | 0, 0.000 | 0.061 |
| 2 | white_pot_lid | yes (1.86) | 2_lathe (lathe_profile_complex (more than two radial intervals in a bin); ) -> 3_coacd (gate fail: 10 > 0.3, max 0.488; n 58) -> 4_voxels (gate pass: 0 > 0.3, max 0.000; n 25) | 4_voxels, 25 | - | - | - / - | 0, 0.000 | 0.086 |

### Per pair: scope, precheck at the S frames, carve

| ep | pair | collider overlap max cm3 | scope (gates) | receiver | S frames: precheck | carve | delivered |
|---|---|---|---|---|---|---|---|
| 12 | blue_cup|plastic_dish_rack | 0.23 | out: blue_cup<-plastic_dish_rack#0: 6 vox INSERTION, sweep 0.0 FAIL sweep; plastic_dish_rack<-blue_cup#1: 9 vox SEAT, sweep 0.0 FAIL sweep | - | - | - | default |
| 13 | blue_cup|plastic_dish_rack | 0.00 | out: - | - | - | - | default |
| 31 | mini_sweeper|plastic_dish_rack | 0.00 | out: - | - | - | - | default |
| 11 | blue_cup|beige_cup | 0.48 | in: blue_cup<-beige_cup#0: 3 vox SEAT, sweep 1.0; blue_cup<-beige_cup#1: 4 vox SEAT, sweep 0.0 FAIL sweep; beige_cup<-blue_cup#2: 11 vox SEAT, sweep 1.0 | beige_cup | f126: c_overlap | not carved: pose_impossible_all | default |
| 2 | white_pot|white_pot_lid | 0.16 | out: white_pot<-white_pot_lid#0: 3 vox SEAT, sweep 0.0 FAIL sweep; white_pot_lid<-white_pot#1: 4 vox SEAT, sweep 0.0 FAIL sweep | - | - | - | default |

### Floor S frames: precheck, S on the delivered pieces, S on the faithful reference (S_ref)

| ep | pair | receiver | frame | precheck | S delivered: disp / dz / tilt (pass) | S_ref: disp / dz / tilt (pass) | floor |
|---|---|---|---|---|---|---|---|
| 12 | blue_cup|plastic_dish_rack | plastic_dish_rack | f176 | FAIL c_overlap (a -3.08 mm; b table 0.00 / recv 0.00 mm; V_ov 7.4 cm3) | - | - | - |
| 13 | blue_cup|plastic_dish_rack | plastic_dish_rack | f181 | FAIL a_table,c_overlap (a -5.73 mm; b table 0.00 / recv 0.00 mm; V_ov 2.7 cm3) | - | - | - |
| 31 | mini_sweeper|plastic_dish_rack | plastic_dish_rack | - | s_floor_vacuous (faithful gap at the hands-off segments: f285 12.0 mm, f278 11.9 mm) | - | - | - |
| 11 | blue_cup|beige_cup | beige_cup | f127 | FAIL c_overlap (a 3.14 mm; b table 3.14 / recv 0.00 mm; V_ov 84.5 cm3) | - | - | - |
| 11 | blue_cup|beige_cup | beige_cup | f108 | FAIL c_overlap (a -2.71 mm; b table 0.00 / recv 0.00 mm; V_ov 76.7 cm3) | - | - | - |
| 2 | white_pot|white_pot_lid | white_pot | f13 | FAIL c_overlap (a 61.29 mm; b table 61.29 / recv 0.00 mm; V_ov 23.8 cm3) | - | - | - |
| 2 | white_pot|white_pot_lid | white_pot | f32 | FAIL c_overlap (a 60.75 mm; b table 60.75 / recv 0.00 mm; V_ov 27.0 cm3) | - | - | - |
| 2 | white_pot|white_pot_lid | white_pot | f316 | FAIL c_overlap (a 62.33 mm; b table 62.33 / recv 0.00 mm; V_ov 20.9 cm3) | - | - | - |

### Contact gate G1 (sim=rl limits; plain MuJoCo 3.17.0)

| ep | receiver / guest | gated rows | delivered max nefc / ncon (overflow copies) | packed default max nefc (pieces) | ratio | verdict |
|---|---|---|---|---|---|---|
| 11 | blue_cup|beige_cup | 0 | None / None (None) | None [] | None | pass contact_gate_pair_vacuous |

### Delivery

| ep | floor | G1 | G2 | DO_NOT_USE.json | reasons |
|---|---|---|---|---|---|
| 12 | FAIL | pass | pending | yes | floor share blue_cup 0.0497; floor share plastic_dish_rack 0.0607 |
| 13 | FAIL | pass | pending | yes | floor share blue_cup 0.0485; floor share plastic_dish_rack 0.0361 |
| 31 | FAIL | pass | pending | yes | floor share mini_sweeper 0.0185; floor share plastic_dish_rack 0.0468 |
| 11 | FAIL | pass | pending | yes | floor share blue_cup 0.038; floor share beige_cup 0.0378 |
| 2 | FAIL | pass | pending | yes | floor share white_pot 0.0609; floor share white_pot_lid 0.0865 |
