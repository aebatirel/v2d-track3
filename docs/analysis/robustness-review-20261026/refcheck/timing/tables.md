## 1. Object motion events: ours - mocap (frames; > 0 = ours LATE; 1 frame = 49.4 ms)

Mocap: physical onset / offset (speed >= 1 cm/s or rotation >= 10 deg/s, walked back / forward from the 1 cm / 10 deg crossing) and the number of moving bouts. Ours: sub-frame 1 cm crossing lags (on1 / off1), 10 deg rotation-crossing lag (onR), for the canonical perception (perc) and the final reference (ref; stale 20 Oct reference where no canonical one exists). Static = the object never moves 1 cm / 10 deg in mocap.

| ep | object | mocap on-off (bouts) | perc on1 | perc onR | perc off1 | ref on1 | ref onR | ref off1 | note |
|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot | 107-208 (2) | +0.6 | +0.9 | -0.2 | -61.8 | -81.7 | +75.5 | stale: off_p1_f=+76; off_p2_f=+54; off_r_f=+105; on_p1_f=-62; on_p2_f=-56; on_r_f=-82 |
| 0 | white_pot_lid | 52-267 (6) | +0.1 | +0.3 | +1.3 | +0.1 | +0.3 | +0.4 | stale:  |
| 2 | white_pot | 110-210 (1) | +0.8 | +12.9 | +0.9 | +0.8 | -0.2 | -7.7 | off_p1_f=-8; off_p2_f=-7; on_r_f=+13 |
| 2 | white_pot_lid | 55-295 (4) | +0.6 | +0.4 | -0.4 | +0.6 | +0.4 | -0.4 |  |
| 11 | blue_cup | static (max 0.49 cm) | | | | | | | ours max disp cm {'perc': 5.44, 'pre': 5.44, 'ref': 5.41} |
| 11 | beige_cup | 22-76 (1) | +0.5 | +0.9 | +16.7 | +0.4 | +0.9 | +16.6 | off_p1_f=+17; off_p2_f=+3; off_r_f=+8 |
| 12 | blue_cup | 32-132 (2) | +0.6 | +0.8 | +1.7 | +0.6 | +0.8 | +1.8 |  |
| 12 | plastic_dish_rack | static (max 0.41 cm) | | | | | | | ours max disp cm {'perc': 0.83, 'pre': 0.83, 'ref': 0.83} |
| 13 | blue_cup | 19-145 (1) | -0.6 | +0.8 | +27.7 | -0.2 | +0.6 | +1.5 | stale: off_p1_f=+28; off_p2_f=+43; off_r_f=+57 |
| 13 | plastic_dish_rack | static (max 0.09 cm) | | | | | | | ours max disp cm {'perc': 0.6, 'stale': 0.77} |
| 18 | mini_sweeper | 32-303 (2) | +0.5 | +0.6 | -0.2 | +0.3 | +0.6 | -0.2 |  |
| 18 | mini_dust_pan | 13-178 (2) | +0.9 | +0.7 | +0.6 | +0.6 | +0.7 | -3.1 | off_p1_f=-3; off_p2_f=-7 |
| 21 | blue_cup | 32-145 (1) | +0.3 | +0.1 | +1.4 | +0.3 | +0.3 | -0.9 |  |
| 21 | water_pitcher | 35-110 (2) | +0.5 | +0.5 | -0.2 | +0.5 | +0.5 | +0.1 |  |
| 22 | blue_cup | 40-124 (1) | +0.5 | +0.0 | +1.3 | +0.5 | +1.1 | +0.9 | stale:  |
| 22 | water_pitcher | 34-116 (1) | +0.4 | +0.4 | -2.9 | +0.4 | +0.2 | +0.3 | stale:  |
| 23 | wooden_piece_1 | 17-165 (2) | +106.0 | +100.2 | +86.3 | +0.5 | +0.3 | -0.1 | stale: identity swap: excluded from pooled; off_p1_f=+86; off_p2_f=+90; off_r_f=+107; on_p1_f=+106; on_p2_f=+107; on_r_f=+100 |
| 23 | wooden_piece_2 | 123-256 (2) | -105.0 | -99.3 | -56.8 | +0.7 | +0.9 | +0.2 | stale: identity swap: excluded from pooled; off_p1_f=-57; off_p2_f=-95; off_r_f=+7; off_r_f=-41; on_p1_f=-105; on_p2_f=-106; on_r_f=-99 |
| 24 | wooden_piece_1 | 6-135 (3) | +0.7 | +0.7 | +29.5 | +0.7 | +0.7 | +29.5 | off_p1_f=+30 |
| 24 | wooden_piece_2 | 111-219 (1) | -74.5 | +0.2 | +2.4 | -74.9 | +0.2 | +2.4 | off_r_f=-8; on_p1_f=-75; on_p2_f=-63 |
| 26 | plastic_dish_rack | static (max 0.43 cm) | | | | | | | ours max disp cm {'perc': 1.09, 'pre': 1.11, 'ref': 1.21} |
| 26 | white_pot | 47-99 (1) | +0.7 | +2.5 | +1.5 | +0.6 | +2.5 | -4.2 | off_p1_f=-4; off_p2_f=-4 |
| 27 | plastic_dish_rack | static (max 0.28 cm) | | | | | | | ours max disp cm {'perc': 0.69, 'pre': 0.64, 'ref': 0.64} |
| 27 | white_pot | 18-190 (1) | +0.7 | +0.4 | +3.8 | +0.7 | +0.4 | +3.8 | off_p1_f=+4 |
| 31 | mini_sweeper | 35-245 (2) | -21.5 | -21.8 | +33.2 | -21.5 | -21.6 | +33.3 | off_p1_f=+33; off_r_f=+44; on_p1_f=-21; on_r_f=-22 |
| 31 | plastic_dish_rack | static (max 0.15 cm) | | | | | | | ours max disp cm {'perc': 1.17, 'pre': 1.18, 'ref': 1.77} |
| 39 | mini_dust_pan | 45-273 (1) | +0.8 | +0.2 | +1.6 | +0.9 | +0.3 | -2.5 |  |
| 40 | mini_dust_pan | 38-210 (1) | +0.0 | +0.5 | +1.1 | +0.0 | +1.0 | +1.3 | stale:  |
| 41 | white_pot | 26-243 (1) | +0.6 | +1.3 | -1.7 | +1.1 | +0.9 | +0.3 | stale:  |
| 42 | white_pot | 33-210 (1) | +0.3 | +1.0 | +2.6 | +0.4 | +0.5 | +0.2 | stale:  |
| 43 | white_pot | 23-274 (1) | +1.7 | -0.1 | +1.5 | +1.4 | +0.6 | -0.6 | stale:  |
| 44 | white_pot | 73-185 (1) | +0.5 | +0.3 | -3.0 | +0.4 | +0.7 | -1.9 | stale: off_p1_f=-3 |
| 45 | white_pot | 47-244 (1) | +0.6 | -0.3 | -0.8 | +0.4 | -1.0 | -0.1 | stale:  |

### Pooled lags (excluding ep23; all moving objects)

| source | key | n | median (frames) | median (ms) | IQR | within +-1 frame | n with abs(lag) > 3 |
|---|---|---|---|---|---|---|---|
| perc | on_p1_f | 25 | +0.54 | +27 | [+0.28, +0.65] | 22 | 2 |
| perc | on_p2_f | 25 | +0.54 | +27 | [+0.38, +0.65] | 23 | 1 |
| perc | on_r_f | 25 | +0.46 | +23 | [+0.22, +0.77] | 20 | 2 |
| perc | off_p1_f | 25 | +1.30 | +64 | [-0.18, +2.38] | 7 | 6 |
| perc | off_p2_f | 25 | +0.72 | +36 | [+0.27, +1.38] | 14 | 2 |
| perc | off_r_f | 25 | +0.75 | +37 | [+0.09, +1.28] | 12 | 4 |
| pre | on_p1_f | 14 | +0.59 | +29 | [+0.47, +0.72] | 12 | 2 |
| pre | on_p2_f | 14 | +0.59 | +29 | [+0.50, +0.64] | 12 | 1 |
| pre | on_r_f | 14 | +0.54 | +27 | [+0.26, +0.75] | 11 | 2 |
| pre | off_p1_f | 14 | +1.56 | +77 | [+0.73, +3.46] | 4 | 4 |
| pre | off_p2_f | 14 | +0.88 | +44 | [+0.59, +1.49] | 8 | 1 |
| pre | off_r_f | 14 | +0.66 | +32 | [+0.02, +1.17] | 6 | 3 |
| ref | on_p1_f | 14 | +0.59 | +29 | [+0.32, +0.68] | 12 | 2 |
| ref | on_p2_f | 14 | +0.59 | +29 | [+0.45, +0.64] | 12 | 1 |
| ref | on_r_f | 14 | +0.44 | +22 | [+0.29, +0.68] | 12 | 1 |
| ref | off_p1_f | 14 | -0.08 | -4 | [-2.11, +3.46] | 4 | 7 |
| ref | off_p2_f | 14 | +0.40 | +20 | [-0.59, +0.92] | 8 | 4 |
| ref | off_r_f | 14 | +0.36 | +18 | [-0.93, +1.15] | 6 | 3 |
| stale | on_p1_f | 11 | +0.39 | +19 | [+0.07, +0.46] | 8 | 1 |
| stale | on_p2_f | 11 | +0.37 | +18 | [+0.21, +0.68] | 10 | 1 |
| stale | on_r_f | 11 | +0.57 | +28 | [+0.25, +0.79] | 8 | 1 |
| stale | off_p1_f | 11 | +0.32 | +16 | [+0.03, +1.12] | 7 | 1 |
| stale | off_p2_f | 11 | +0.25 | +12 | [-0.05, +0.80] | 9 | 1 |
| stale | off_r_f | 11 | +0.64 | +32 | [+0.39, +1.04] | 8 | 1 |
| sim | on_p1_f | 67 | -0.99 | -49 | [-37.17, +0.65] | 19 | 31 |
| sim | on_p2_f | 65 | -0.49 | -24 | [-15.81, +0.91] | 20 | 29 |
| sim | on_r_f | 67 | -2.41 | -119 | [-24.28, -0.21] | 22 | 31 |
| sim | off_p1_f | 67 | +27.03 | +1335 | [-2.24, +48.21] | 2 | 54 |
| sim | off_p2_f | 62 | +3.91 | +193 | [-0.79, +53.58] | 16 | 44 |
| sim | off_r_f | 62 | +25.33 | +1251 | [+0.49, +64.80] | 9 | 41 |

### Speed-edge lags (every bout: rising / falling edges of speed >= 5 cm/s, matched within 10 frames; integer frames)

| source | starts n | starts median | starts IQR | ends n | ends median | ends IQR |
|---|---|---|---|---|---|---|
| perc | 103 | +1.0 | [0.0, 1.0] | 105 | 0.0 | [0.0, 1.0] |
| pre | 48 | +1.0 | [0.0, 1.0] | 49 | 0.0 | [0.0, 1.0] |
| ref | 46 | +1.0 | [0.0, 1.0] | 49 | 0.0 | [0.0, 1.0] |
| stale | 57 | +1.0 | [0.0, 1.0] | 58 | 1.0 | [0.0, 1.0] |
| sim | 194 | +0.0 | [-1.0, 1.0] | 204 | 0.0 | [-1.0, 1.0] |

## 2. Hand contact vs the TRUE (mocap) motion window

lead = true physical onset - arrival of the contact run active at it (> 0: the hand is there BEFORE the object moves; < 0: it arrives late, the reference moves the object with no hand on it). rel = release - true physical offset (> 0: the hand stays after the object settles). unheld = true moving frames (mocap bouts inside the window) with no contact. Robot = 15 probe sites + palm of either robot hand within 2 cm of the object surface (our mesh, posed by that reference); pre = mkref/E2S output, ref = after contact retarget, glockt = grasp-lock training reference; human = perceived MANO joints within 2 cm; labels = the reference contact labels; plan = grasp-lock hold_from - true onset / end - true offset.

| ep | object | true on-off | pre robot lead / rel / unheld | ref robot | glockt robot | human | labels | plan hold_from / end |
|---|---|---|---|---|---|---|---|---|
| 0 | white_pot | 107-208 | - | - / - / 102 (stale) | - | - / - / 102 (stale) | - / - / 102 (stale) | - |
| 0 | white_pot_lid | 52-267 | - | +10 / +10 / 19 (stale) | - | +9 / +10 / 19 (stale) | +9 / +10 / 19 (stale) | - |
| 2 | white_pot | 110-210 | +75 / +23 / 0 | +73 / +23 / 0 | +73 / +132 / 0 | +70 / +23 / 0 | +74 / +23 / 0 | -5 / +127 |
| 2 | white_pot_lid | 55-295 | +19 / +16 / 25 | +3 / +14 / 20 | +14 / +28 / 0 | +6 / +12 / 26 | +10 / +8 / 26 | -6 / +9 |
| 11 | beige_cup | 22-76 | +10 / +25 / 0 | +10 / +25 / 0 | +21 / +38 / 0 | +8 / +23 / 0 | +10 / +24 / 0 | -22 / +23 (onset anchor f1) |
| 12 | blue_cup | 32-132 | +14 / +11 / 0 | +14 / +10 / 0 | +10 / +32 / 0 | +12 / +9 / 0 | +12 / +11 / 0 | -6 / +12 |
| 13 | blue_cup | 19-145 | - | +3 / +3 / 0 (stale) | - | +3 / +5 / 5 (stale) | +2 / +1 / 0 (stale) | - |
| 18 | mini_sweeper | 32-303 | -28 / +49 / 33 | +3 / +49 / 0 | +2 / +29 / 0 | +3 / +49 / 3 | -28 / +19 / 43 | -3 / +20 (onset anchor f39) |
| 18 | mini_dust_pan | 13-178 | +4 / +12 / 0 | +4 / +11 / 0 | +7 / +28 / 0 | +3 / +10 / 0 | +4 / +8 / 0 | -5 / +9 |
| 21 | blue_cup | 32-145 | +6 / +12 / 0 | +7 / +12 / 0 | +8 / +27 / 0 | +4 / +12 / 0 | +6 / +12 / 0 | -5 / +13 |
| 21 | water_pitcher | 35-110 | +29 / +44 / 0 | +29 / +44 / 0 | +5 / +38 / 0 | +27 / +41 / 0 | +22 / +24 / 0 | -3 / +25 |
| 22 | blue_cup | 40-124 | - | +33 / +22 / 0 (stale) | - | +32 / +21 / 0 (stale) | +22 / +22 / 0 (stale) | - |
| 22 | water_pitcher | 34-116 | - | +6 / -2 / 45 (stale) | - | +6 / -2 / 46 (stale) | +5 / -2 / 45 (stale) | - |
| 23 | wooden_piece_1 | 17-165 | - | +5 / +118 / 0 (stale) | - | +4 / +116 / 0 (stale) | +4 / +22 / 0 (stale) | - |
| 23 | wooden_piece_2 | 123-256 | - | +10 / +29 / 0 (stale) | - | +8 / +29 / 0 (stale) | +10 / +22 / 0 (stale) | - |
| 24 | wooden_piece_1 | 6-135 | +6 / +104 / 0 | +6 / +105 / 0 | +6 / +123 / 0 | +5 / -4 / 19 | +6 / +104 / 0 | -5 / +105 |
| 24 | wooden_piece_2 | 111-219 | +8 / +25 / 0 | +8 / +24 / 0 | +90 / +40 / 0 | +6 / +23 / 0 | +8 / +24 / 0 | -82 / +25 (onset anchor f39) |
| 26 | white_pot | 47-99 | +12 / +19 / 0 | +12 / +18 / 0 | -10 / +28 / 16 | +11 / +16 / 0 | +11 / +19 / 0 | -5 / +19 replan |
| 27 | white_pot | 18-190 | -2 / +32 / 6 | +0 / +32 / 0 | +3 / +46 / 0 | +0 / +30 / 0 | -2 / +30 / 6 | -1 / +31 |
| 31 | mini_sweeper | 35-245 | +10 / +20 / 0 | +14 / +21 / 0 | +22 / +31 / 0 | +12 / +19 / 0 | +10 / +19 / 0 | -21 / +20 (onset anchor f24) |
| 39 | mini_dust_pan | 45-273 | +11 / +23 / 0 | +11 / +23 / 0 | +4 / +29 / 0 | +11 / +20 / 6 | +10 / +19 / 0 | -4 / +19 (onset anchor f51) |
| 40 | mini_dust_pan | 38-210 | - | +20 / +19 / 0 (stale) | - | +19 / +17 / 0 (stale) | +20 / +19 / 0 (stale) | - |
| 41 | white_pot | 26-243 | - | +11 / +18 / 0 (stale) | - | +10 / +17 / 0 (stale) | +11 / +14 / 0 (stale) | - |
| 42 | white_pot | 33-210 | - | +14 / +19 / 0 (stale) | - | +13 / +17 / 0 (stale) | +14 / +19 / 0 (stale) | - |
| 43 | white_pot | 23-274 | - | +10 / +21 / 0 (stale) | - | +10 / +20 / 0 (stale) | +10 / +21 / 0 (stale) | - |
| 44 | white_pot | 73-185 | - | +66 / +22 / 0 (stale) | - | +50 / +22 / 0 (stale) | +23 / +15 / 0 (stale) | - |
| 45 | white_pot | 47-244 | - | +30 / +20 / 0 (stale) | - | +29 / +20 / 0 (stale) | +23 / +16 / 0 (stale) | - |

### Pooled (excluding ep23)

| hand source | n | lead median | lead IQR | late arrivals (lead < 0) | release median | early releases | unheld / true moving frames | lead vs OWN onset: median, late | unheld / own moving frames |
|---|---|---|---|---|---|---|---|---|---|
| glockt:robot<2cm | 14 | 7.5 | [4.25, 19.25] | 26/white_pot:-10 | 31.5 | none | 16 / 1804 | 13.0, 26/white_pot:-5 | 11 / 2029 |
| pre:robot<2cm | 14 | 10.0 | [6.0, 13.5] | 18/mini_sweeper:-28, 27/white_pot:-2 | 23.0 | none | 64 / 1804 | 12.5, 18/mini_sweeper:-21, 24/wooden_piece_2:-64 | 188 / 2053 |
| ref:human<2cm | 14 | 7.0 | [4.25, 11.75] | none | 19.5 | 24/wooden_piece_1:-4 | 54 / 1804 | 10.0, 24/wooden_piece_2:-66 | 217 / 2029 |
| ref:labels | 14 | 10.0 | [6.0, 10.75] | 18/mini_sweeper:-28, 27/white_pot:-2 | 19.0 | none | 75 / 1804 | 12.5, 18/mini_sweeper:-21, 24/wooden_piece_2:-64 | 208 / 2029 |
| ref:robot<2cm | 14 | 9.0 | [4.5, 13.5] | none | 23.0 | none | 20 / 1804 | 11.5, 24/wooden_piece_2:-64 | 141 / 2029 |
| stale:human<2cm | 10 | 11.5 | [9.25, 26.5] | none | 17.0 | 22/water_pitcher:-2 | 172 / 1591 | 17.0, 0/white_pot:-15 | 399 / 1768 |
| stale:labels | 10 | 12.5 | [9.25, 21.5] | none | 15.5 | 22/water_pitcher:-2 | 166 / 1591 | 18.0, 0/white_pot:-16 | 397 / 1768 |
| stale:robot<2cm | 10 | 12.5 | [10.0, 27.5] | none | 19.0 | 22/water_pitcher:-2 | 166 / 1591 | 18.0, 0/white_pot:-14 | 383 / 1768 |

Grasp-lock plan over 14 hold phases: hold_from - true onset median -5 frames (range -82 to -1); end - true offset median +20 (range +9 to +127).

## 3. mkref hand bookkeeping: lead-in, held / attached invalid runs, tracker-filled frames

| ep | side | first valid (lead-in cm) | invalid runs filled by mkref (start-end, attach) overlapping true motion | hand-track frames in true motion: measured / tracker-filled / invalid |
|---|---|---|---|---|
| 0 | right | None (None) | none | white_pot: 100/2/0 of 102; white_pot_lid: 86/1/0 of 87 |
| 0 | left | None (None) | none | white_pot: 82/20/0 of 102; white_pot_lid: 81/6/0 of 87 |
| 2 | right | 1 (1.0) | 77-223 (white_pot_lid; {'white_pot': 101, 'white_pot_lid': 147}) | white_pot: 0/0/101 of 101; white_pot_lid: 51/19/47 of 117 |
| 2 | left | 4 (4.0) | none | white_pot: 101/0/0 of 101; white_pot_lid: 97/20/0 of 117 |
| 11 | right | 1 (1.0) | none | beige_cup: 50/5/0 of 55 |
| 11 | left | 0 (None) | none | beige_cup: 55/0/0 of 55 |
| 12 | right | 0 (None) | none | blue_cup: 94/7/0 of 101 |
| 12 | left | 0 (None) | 60-84 (blue_cup; {'blue_cup': 25}) | blue_cup: 66/10/25 of 101 |
| 13 | right | None (None) | 145-164 (blue_cup; {'blue_cup': 1}) | blue_cup: 112/6/1 of 119 |
| 13 | left | None (None) | none | blue_cup: 89/30/0 of 119 |
| 18 | right | None (None) | 153-175 (mini_sweeper; {'mini_sweeper': 23, 'mini_dust_pan': 23}) | mini_sweeper: 203/26/17 of 246; mini_dust_pan: 84/31/23 of 138 |
| 18 | left | None (None) | none | mini_sweeper: 242/4/0 of 246; mini_dust_pan: 134/4/0 of 138 |
| 21 | right | 0 (None) | 42-97 (water_pitcher; {'blue_cup': 56, 'water_pitcher': 56}) | blue_cup: 31/18/53 of 102; water_pitcher: 17/3/56 of 76 |
| 21 | left | 0 (None) | 108-133 (blue_cup; {'blue_cup': 26, 'water_pitcher': 3}) | blue_cup: 84/1/17 of 102; water_pitcher: 73/0/3 of 76 |
| 22 | right | None (None) | 66-83 (blue_cup; {'blue_cup': 18, 'water_pitcher': 18}) | blue_cup: 36/31/18 of 85; water_pitcher: 34/31/18 of 83 |
| 22 | left | None (None) | none | blue_cup: 64/21/0 of 85; water_pitcher: 68/15/0 of 83 |
| 23 | right | None (None) | 50-109 (wooden_piece_1; {'wooden_piece_1': 60, 'wooden_piece_2': 0}) | wooden_piece_1: 60/3/53 of 116; wooden_piece_2: 114/7/0 of 121 |
| 23 | left | None (None) | none | wooden_piece_1: 116/0/0 of 116; wooden_piece_2: 121/0/0 of 121 |
| 24 | right | 17 (None) | 0-16 (wooden_piece_1; {'wooden_piece_1': 11, 'wooden_piece_2': 0}) | wooden_piece_1: 79/14/11 of 104; wooden_piece_2: 96/6/0 of 102 |
| 24 | left | 0 (None) | none | wooden_piece_1: 76/28/0 of 104; wooden_piece_2: 102/0/0 of 102 |
| 26 | right | 0 (None) | none | white_pot: 48/5/0 of 53 |
| 26 | left | 6 (6.0) | 9-107 (plastic_dish_rack; {'white_pot': 53}) | white_pot: 0/0/53 of 53 |
| 27 | right | 0 (None) | 2-34 (white_pot; {'white_pot': 17}) | white_pot: 144/11/17 of 172 |
| 27 | left | 0 (None) | none | white_pot: 172/0/0 of 172 |
| 31 | right | 0 (None) | none | mini_sweeper: 203/5/0 of 208 |
| 31 | left | 0 (None) | none | mini_sweeper: 208/0/0 of 208 |
| 39 | right | 0 (None) | 219-248 (mini_dust_pan; {'mini_dust_pan': 30}) | mini_dust_pan: 149/50/30 of 229 |
| 39 | left | 1 (1.0) | none | mini_dust_pan: 218/11/0 of 229 |
| 40 | right | None (None) | 51-77 (mini_dust_pan; {'mini_dust_pan': 27}) | mini_dust_pan: 114/31/27 of 172 |
| 40 | left | None (None) | none | mini_dust_pan: 161/11/0 of 172 |
| 41 | right | None (None) | 92-109 (white_pot; {'white_pot': 18}) | white_pot: 173/21/18 of 212 |
| 41 | left | None (None) | 91-134 (white_pot; {'white_pot': 44}); 139-159 (white_pot; {'white_pot': 21}); 202-224 (white_pot; {'white_pot': 23}) | white_pot: 90/40/82 of 212 |
| 42 | right | None (None) | none | white_pot: 173/2/0 of 175 |
| 42 | left | None (None) | none | white_pot: 106/69/0 of 175 |
| 43 | right | None (None) | none | white_pot: 162/85/0 of 247 |
| 43 | left | None (None) | 133-152 (white_pot; {'white_pot': 20}) | white_pot: 207/20/20 of 247 |
| 44 | right | None (None) | none | white_pot: 112/0/0 of 112 |
| 44 | left | None (None) | none | white_pot: 111/1/0 of 112 |
| 45 | right | None (None) | none | white_pot: 180/17/0 of 197 |
| 45 | left | None (None) | none | white_pot: 195/2/0 of 197 |

## 3b. Our object moving while the true object rests (creep.py; > 1 cm from its own rest pose)

| ep / object | true window | source | before true onset: max cm / deg, frames > 1 cm (first) | after true offset: max cm / deg, frames > 1 cm | mocap same |
|---|---|---|---|---|---|
| 0/white_pot | 107-208 | stale | 10.65 / 19.3, 59 (40) | 11.2 / 22.5, 52 | pre 0.11 / 0.6, post 0.44 / 2.0 |
| 2/white_pot | 110-210 | perc | 0.66 / 6.5, 0 (None) | 1.16 / 9.2, 1 | pre 0.29 / 0.7, post 0.23 / 1.4 |
| 11/blue_cup | static | perc | whole episode: 5.44 / 6.8, 77 (43) | | 0.49 / 2.0 |
| 11/blue_cup | static | ref | whole episode: 5.41 / 6.3, 75 (43) | | 0.49 / 2.0 |
| 11/beige_cup | 22-76 | perc | 0.32 / 2.6, 0 (None) | 1.34 / 5.0, 11 | pre 0.01 / 0.0, post 0.4 / 0.9 |
| 11/beige_cup | 22-76 | ref | 0.28 / 2.6, 0 (None) | 1.32 / 5.0, 10 | pre 0.01 / 0.0, post 0.4 / 0.9 |
| 13/blue_cup | 19-145 | perc | 0.39 / 1.8, 0 (None) | 3.08 / 13.5, 22 | pre 0.06 / 0.2, post 0.26 / 2.1 |
| 21/water_pitcher | 35-110 | perc | 0.94 / 4.9, 0 (None) | 1.05 / 1.7, 1 | pre 0.51 / 5.2, post 0.43 / 2.0 |
| 23/wooden_piece_1 | 17-165 | perc | 1.03 / 2.8, 1 (0) | 33.86 / 135.3, 79 | pre 0.05 / 0.4, post 0.38 / 2.4 |
| 23/wooden_piece_1 | 17-165 | stale | 0.16 / 1.3, 0 (None) | 1.01 / 3.6, 1 | pre 0.05 / 0.4, post 0.38 / 2.4 |
| 23/wooden_piece_2 | 123-256 | perc | 14.16 / 102.4, 102 (21) | 0.5 / 4.1, 0 | pre 0.34 / 2.6, post 0.13 / 1.7 |
| 24/wooden_piece_1 | 6-135 | perc | 0.12 / 0.4, 0 (None) | 1.12 / 5.7, 8 | pre 0.04 / 0.4, post 0.77 / 5.6 |
| 24/wooden_piece_1 | 6-135 | ref | 0.12 / 0.4, 0 (None) | 1.12 / 5.7, 8 | pre 0.04 / 0.4, post 0.77 / 5.6 |
| 24/wooden_piece_2 | 111-219 | perc | 2.69 / 6.4, 71 (40) | 0.73 / 1.2, 0 | pre 0.2 / 2.2, post 0.07 / 1.0 |
| 24/wooden_piece_2 | 111-219 | ref | 2.7 / 6.4, 72 (39) | 0.73 / 1.2, 0 | pre 0.2 / 2.2, post 0.07 / 1.0 |
| 26/plastic_dish_rack | static | perc | whole episode: 1.09 / 3.6, 2 (58) | | 0.43 / 0.9 |
| 26/plastic_dish_rack | static | ref | whole episode: 1.21 / 3.0, 2 (58) | | 0.43 / 0.9 |
| 27/white_pot | 18-190 | perc | 0.35 / 5.1, 0 (None) | 1.02 / 5.9, 2 | pre 0.04 / 0.2, post 0.81 / 2.9 |
| 27/white_pot | 18-190 | ref | 0.35 / 5.1, 0 (None) | 1.02 / 5.9, 2 | pre 0.04 / 0.2, post 0.81 / 2.9 |
| 31/mini_sweeper | 35-245 | perc | 1.76 / 17.5, 4 (26) | 1.85 / 17.9, 14 | pre 0.19 / 4.4, post 0.14 / 2.9 |
| 31/mini_sweeper | 35-245 | ref | 1.77 / 16.8, 4 (26) | 1.98 / 17.0, 14 | pre 0.19 / 4.4, post 0.14 / 2.9 |
| 31/plastic_dish_rack | static | perc | whole episode: 1.17 / 3.6, 6 (58) | | 0.15 / 0.9 |
| 31/plastic_dish_rack | static | ref | whole episode: 1.77 / 3.8, 82 (83) | | 0.15 / 0.9 |

## 4. Track-guard interventions (perception guard arm, 8 episodes)

| ep | object | counts | re-acquired frames | held frames (true object moving?) |
|---|---|---|---|---|
| 0 | white_pot_lid | {'f0_retries': 1, 'implausible': 0, 'redetect': 0, 'reacquired': 0, 'held': 0} | [] | [] |
| 23 | wooden_piece_1 | {'f0_retries': 0, 'implausible': 5, 'redetect': 4, 'reacquired': 4, 'held': 1} | [155, 168, 200, 245] | [(169, False)] |

## 5. Simulated object (rollouts r1-r5 of the canonical results dir): 1 cm onset crossing vs mocap

| ep | object | ref on1 lag | sim on1 lag per rollout | sim off1 lag per rollout |
|---|---|---|---|---|
| 2 | white_pot | +0.8 | -76, -58, -75, -62, -56 | +117, +107, +123, +123, -41 |
| 2 | white_pot_lid | +0.6 | -48, -45, -48, -48, -48 | +38, +29, +44, +45, -11 |
| 11 | beige_cup | +0.4 | -21, -21, -21, -21, -21 | -67, -67, -67, -67, -67 |
| 12 | blue_cup | +0.6 | +1, -8, -11, +2, +2 | +47, +40, +51, +48, +27 |
| 18 | mini_sweeper | +0.3 | +0, +1, -0, +1, +1 | +75, +75, +4, +77, +3 |
| 18 | mini_dust_pan | +0.6 | +2, -1, -2, +1, -1 | -5, -8, -9, -11, -8 |
| 21 | blue_cup | +0.3 | -0, -1, -0, -0, -1 | -2, -1, +2, -2, -1 |
| 21 | water_pitcher | +0.5 | +2, -2, +1, +0, +1 | +1, +35, -1, -3, +20 |
| 24 | wooden_piece_1 | +0.7 | +2, +2, +2, +0, +7 | +89, +106, +132, +88, +75 |
| 24 | wooden_piece_2 | -74.9 | -, -90, -, -, -91 | -, -181, -, -, +31 |
| 26 | white_pot | +0.6 | -48, -48, -48, -48, -48 | -75, +12, +10, +60, +60 |
| 27 | white_pot | +0.7 | +0, -1, -2, -1, -2 | +31, +36, +40, +35, +36 |
| 31 | mini_sweeper | -21.5 | -26, -24, -22, -27, -29 | +16, +48, +45, +48, +53 |
| 39 | mini_dust_pan | +0.9 | +1, +0, +1, +0, +4 | -2, -2, -2, -2, -3 |

## 6. Cost in the kit's registered AUC (in-process kit scoring; pooled onset lag L = +0.545 frames from 70 perception crossings)

| ep | src | base | shift_pool (legal constant) | shift_ep (oracle, L) | shift_obj (oracle) | rest_hold (oracle) |
|---|---|---|---|---|---|---|
| 0 | perc | 0.9641 | 0.9672 (+0.0031) | 0.9671 (+0.0030, L 0.482) | 0.9656 (+0.0015) | 0.9644 (+0.0003) |
| 2 | perc | 0.9866 | 0.9911 (+0.0045) | 0.9912 (+0.0046, L 0.567) | 0.9910 (+0.0044) | 0.9907 (+0.0041) |
| 2 | ref | 0.9798 | 0.9835 (+0.0037) | 0.9836 (+0.0038, L 0.534) | 0.9836 (+0.0038) | 0.9817 (+0.0019) |
| 11 | perc | 0.8964 | 0.9003 (+0.0039) | 0.9005 (+0.0041, L 0.498) | 0.8994 (+0.0030) | 0.9653 (+0.0689) |
| 11 | ref | 0.8844 | 0.8971 (+0.0127) | 0.8948 (+0.0104, L 0.438) | 0.8932 (+0.0088) | 0.9539 (+0.0695) |
| 12 | perc | 0.9662 | 0.9763 (+0.0101) | 0.9772 (+0.0110, L 0.609) | 0.9762 (+0.0100) | 0.9670 (+0.0008) |
| 12 | ref | 0.9354 | 0.9463 (+0.0109) | 0.9473 (+0.0119, L 0.607) | 0.9460 (+0.0106) | 0.9358 (+0.0004) |
| 13 | perc | 0.9605 | 0.9648 (+0.0043) | 0.9650 (+0.0045, L 0.478) | 0.9650 (+0.0045) | 0.9748 (+0.0143) |
| 18 | perc | 0.9380 | 0.9596 (+0.0216) | 0.9611 (+0.0231, L 0.668) | 0.9594 (+0.0214) | 0.9271 (-0.0109) |
| 18 | ref | 0.9657 | 0.9681 (+0.0024) | 0.9682 (+0.0025, L 0.627) | 0.9672 (+0.0015) | 0.9657 (+0.0000) |
| 21 | perc | 0.8372 | 0.8407 (+0.0035) | 0.8407 (+0.0035, L 0.45) | 0.8399 (+0.0027) | 0.8372 (+0.0000) |
| 21 | ref | 0.7776 | 0.7807 (+0.0031) | 0.7801 (+0.0025, L 0.425) | 0.7797 (+0.0021) | 0.7772 (-0.0004) |
| 22 | perc | 0.8710 | 0.8704 (-0.0006) | 0.8709 (-0.0001, L 0.374) | 0.8715 (+0.0005) | 0.8705 (-0.0005) |
| 23 | perc | 0.0414 | 0.0425 (+0.0011) | - | 0.0414 (+0.0000) | 0.0430 (+0.0016) |
| 24 | perc | 0.8117 | 0.8091 (-0.0026) | 0.8089 (-0.0028, L 0.612) | 0.8098 (-0.0019) | 0.8252 (+0.0135) |
| 24 | ref | 0.8163 | 0.8127 (-0.0036) | 0.8123 (-0.0040, L 0.614) | 0.8118 (-0.0045) | 0.8277 (+0.0114) |
| 26 | perc | 0.9723 | 0.9745 (+0.0022) | 0.9733 (+0.0010, L 0.652) | 0.9782 (+0.0059) | 0.9765 (+0.0042) |
| 26 | ref | 0.9229 | 0.9237 (+0.0008) | 0.9221 (-0.0008, L 0.647) | 0.9242 (+0.0013) | 0.9260 (+0.0031) |
| 27 | perc | 0.9593 | 0.9619 (+0.0026) | 0.9615 (+0.0022, L 0.726) | 0.9595 (+0.0002) | 0.9595 (+0.0002) |
| 27 | ref | 0.9621 | 0.9644 (+0.0023) | 0.9640 (+0.0019, L 0.727) | 0.9637 (+0.0016) | 0.9639 (+0.0018) |
| 31 | perc | 0.7998 | 0.8220 (+0.0222) | 0.8653 (+0.0655, L 0.944) | 0.8644 (+0.0646) | 0.8060 (+0.0062) |
| 31 | ref | 0.8233 | 0.8447 (+0.0214) | 0.8502 (+0.0269, L 0.98) | 0.8502 (+0.0269) | 0.8067 (-0.0166) |
| 39 | perc | 0.9602 | 0.9759 (+0.0157) | 0.9759 (+0.0157, L 0.614) | 0.9759 (+0.0157) | 0.9614 (+0.0012) |
| 39 | ref | 0.9559 | 0.9706 (+0.0147) | 0.9706 (+0.0147, L 0.64) | 0.9706 (+0.0147) | 0.9559 (+0.0000) |
| 40 | perc | 0.9570 | 0.9584 (+0.0014) | 0.9572 (+0.0002, L 0.262) | 0.9572 (+0.0002) | 0.9570 (+0.0000) |
| 41 | perc | 0.9910 | 0.9927 (+0.0017) | 0.9927 (+0.0017, L 0.622) | 0.9927 (+0.0017) | 0.9910 (+0.0000) |
| 42 | perc | 0.9915 | 0.9990 (+0.0075) | 0.9993 (+0.0078, L 0.325) | 0.9993 (+0.0078) | 0.9915 (+0.0000) |
| 43 | perc | 0.9482 | 0.9479 (-0.0003) | 0.9461 (-0.0021, L 0.804) | 0.9461 (-0.0021) | 0.9482 (+0.0000) |
| 44 | perc | 0.9967 | 0.9970 (+0.0003) | 0.9972 (+0.0005, L 0.478) | 0.9972 (+0.0005) | 0.9967 (+0.0000) |
| 45 | perc | 0.9795 | 0.9823 (+0.0028) | 0.9823 (+0.0028, L 0.46) | 0.9823 (+0.0028) | 0.9795 (+0.0000) |

Means over episodes (excluding ep23): {"perc": {"base": 0.9362, "base_minus_base_mean": 0.0, "base_improved": 0, "shift_pool": 0.9416, "shift_pool_minus_base_mean": 0.0055, "shift_pool_improved": 16, "shift_ep": 0.9439, "shift_ep_minus_base_mean": 0.0077, "shift_ep_improved": 16, "shift_obj": 0.9437, "shift_obj_minus_base_mean": 0.0075, "shift_obj_improved": 17, "rest_hold": 0.9416, "rest_hold_minus_base_mean": 0.0054, "rest_hold_improved": 10, "episodes_excl_ep23": 19}, "ref": {"base": 0.9023, "base_minus_base_mean": 0.0, "base_improved": 0, "shift_pool": 0.9092, "shift_pool_minus_base_mean": 0.0068, "shift_pool_improved": 9, "shift_ep": 0.9093, "shift_ep_minus_base_mean": 0.007, "shift_ep_improved": 8, "shift_obj": 0.909, "shift_obj_minus_base_mean": 0.0067, "shift_obj_improved": 9, "rest_hold": 0.9094, "rest_hold_minus_base_mean": 0.0071, "rest_hold_improved": 6, "episodes_excl_ep23": 10}}

### Per-frame error by phase (base; pooled over objects and episodes, excluding ep23 and ep0)

| src | phase | frames | ADD median cm | ADD p90 cm | mean AUC share |
|---|---|---|---|---|---|
| perc | moving_hand_measured | 2840 | 1.21 (frame-weighted mean of per-object medians) | - | 0.942 |
| perc | moving_hand_unmeasured | 425 | 1.67 (frame-weighted mean of per-object medians) | - | 0.893 |
| perc | moving_no_hand | 170 | 2.27 (frame-weighted mean of per-object medians) | - | 0.839 |
| perc | rest | 3661 | 1.27 (frame-weighted mean of per-object medians) | - | 0.923 |
| ref | moving_hand_measured | 1542 | 1.43 (frame-weighted mean of per-object medians) | - | 0.920 |
| ref | moving_hand_unmeasured | 323 | 1.95 (frame-weighted mean of per-object medians) | - | 0.857 |
| ref | moving_no_hand | 118 | 1.55 (frame-weighted mean of per-object medians) | - | 0.928 |
| ref | rest | 2674 | 1.45 (frame-weighted mean of per-object medians) | - | 0.903 |

