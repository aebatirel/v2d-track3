| ep | objects | base AUC | n4000 dAUC | bbox dAUC | vtx500 dAUC | seed1 dAUC | seed2 dAUC | axisz dAUC | axisfit dAUC |
|---|---|---|---|---|---|---|---|---|---|
| 2 | white_pot + white_pot_lid | 0.9823 | +0.0001 | -0.0129 | -0.0002 | -0.0081 | -0.0137 | n/a | n/a |
| 11 | blue_cup + beige_cup | 0.8978 | -0.0004 | +0.0016 | -0.0018 | -0.0018 | +0.0075 | -0.0020 | +0.0018 |
| 13 | blue_cup + plastic_dish_rack | 0.9605 | -0.0003 | -0.0250 | -0.0001 | +0.0061 | +0.0078 | -0.0015 | -0.0003 |
| 18 | mini_sweeper + mini_dust_pan | 0.9380 | +0.0021 | -0.0007 | +0.0053 | +0.0233 | +0.0279 | n/a | n/a |
| 22 | blue_cup + water_pitcher | 0.8710 | -0.0006 | +0.0033 | -0.0026 | +0.0136 | +0.0310 | +0.0000 | +0.0000 |
| 24 | wooden_piece_1 + wooden_piece_2 | 0.8117 | +0.0000 | -0.0009 | +0.0000 | +0.0013 | -0.0032 | n/a | n/a |
| 31 | mini_sweeper + plastic_dish_rack | 0.8050 | -0.0012 | +0.0025 | +0.0018 | +0.0172 | -0.7091 | n/a | n/a |
| mean abs | | | 0.0007 | 0.0067 | 0.0017 | 0.0102 | 0.1143 | 0.0012 | 0.0007 |
| mean signed | | | -0.0000 | -0.0046 | +0.0003 | +0.0074 | -0.0931 | -0.0012 | +0.0005 |

Other metrics (base -> variant), SP_SR / MP_SR / MPPE_cm / RPE_cm:
- ep2 (base SP 1.0, MP 1.0, MPPE 0.7324, RPE 1.435): n4000: MPPE +0.00 RPE +0.00; bbox: MPPE +0.07 RPE +0.13; vtx500: MPPE +0.00 RPE +0.00; seed1: MPPE +0.02 RPE -0.12; seed2: MPPE +0.07 RPE -0.21
- ep11 (base SP 1.0, MP 1.0, MPPE 1.6375, RPE 1.739): n4000: MPPE +0.00 RPE +0.00; bbox: MPPE -0.05 RPE +0.07; vtx500: MPPE +0.00 RPE +0.00; seed1: MPPE +0.03 RPE -0.04; seed2: MPPE -0.08 RPE -0.04; axisz: MPPE +0.00 RPE -0.01; axisfit: MPPE -0.01 RPE +0.04
- ep13 (base SP 1.0, MP 1.0, MPPE 1.0632, RPE 1.3815): n4000: MPPE +0.00 RPE +0.00; bbox: MPPE +0.20 RPE -0.01; vtx500: MPPE +0.00 RPE +0.00; seed1: MPPE -0.08 RPE -0.05; seed2: MPPE -0.13 RPE -0.05; axisz: MPPE +0.01 RPE +0.02; axisfit: MPPE +0.00 RPE +0.15
- ep18 (base SP 1.0, MP 1.0, MPPE 1.1864, RPE 1.8374): n4000: MPPE +0.00 RPE +0.00; bbox: MPPE -0.04 RPE +0.09; vtx500: MPPE +0.00 RPE +0.00; seed1: MPPE -0.08 RPE -0.15; seed2: MPPE -0.24 RPE -0.32
- ep22 (base SP 1.0, MP 1.0, MPPE 1.8003, RPE 1.2222): n4000: MPPE +0.00 RPE +0.00; bbox: MPPE -0.13 RPE -0.00; vtx500: MPPE +0.00 RPE +0.00; seed1: MPPE -0.14 RPE -0.02; seed2: MPPE -0.29 RPE -0.02; axisz: MPPE +0.00 RPE -0.00; axisfit: MPPE -0.00 RPE -0.00
- ep24 (base SP 1.0, MP 1.0, MPPE 2.3599, RPE 0.9832): n4000: MPPE +0.00 RPE +0.00; bbox: MPPE +0.02 RPE -0.00; vtx500: MPPE +0.00 RPE +0.00; seed1: MPPE -0.01 RPE +0.02; seed2: MPPE +0.04 RPE -0.02
- ep31 (base SP 1.0, MP 1.0, MPPE 2.011, RPE 1.8848): n4000: MPPE +0.00 RPE +0.00; bbox: MPPE -0.37 RPE -0.38; vtx500: MPPE +0.00 RPE +0.00; seed1: MPPE -0.04 RPE -0.06; seed2: MPPE +17.37 RPE +22.38 ['SP_SR', 'MP_SR'] flips
