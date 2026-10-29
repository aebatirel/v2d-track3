| ep | objects | base AUC | scan4096 dAUC | scan20000 dAUC | seed3 dAUC | seed4 dAUC | seed5 dAUC | seed6 dAUC |
|---|---|---|---|---|---|---|---|---|
| 2 | white_pot + white_pot_lid | 0.9823 | -0.0011 | -0.0039 | +0.0003 | -0.0008 | -0.0101 | -0.0008 |
| 18 | mini_sweeper + mini_dust_pan | 0.9380 | +0.0347 | -0.7165 | +0.0224 | +0.0264 | +0.0256 | +0.0255 |
| 22 | blue_cup + water_pitcher | 0.8710 | -0.4016 | -0.0623 | +0.0174 | -0.0173 | +0.0020 | +0.0478 |
| 24 | wooden_piece_1 + wooden_piece_2 | 0.8117 | -0.7549 | -0.7790 | -0.0012 | +0.0072 | -0.0069 | +0.0257 |
| 31 | mini_sweeper + plastic_dish_rack | 0.8050 | -0.7092 | -0.7090 | -0.0058 | +0.0004 | +0.0059 | -0.7092 |
| mean abs | | | 0.3803 | 0.4541 | 0.0094 | 0.0104 | 0.0101 | 0.1618 |
| mean signed | | | -0.3664 | -0.4541 | +0.0066 | +0.0032 | +0.0033 | -0.1222 |

Other metrics (base -> variant), SP_SR / MP_SR / MPPE_cm / RPE_cm:
- ep2 (base SP 1.0, MP 1.0, MPPE 0.7324, RPE 1.435): scan4096: MPPE +0.01 RPE -0.19; scan20000: MPPE +0.13 RPE +0.07; seed3: MPPE -0.02 RPE -0.03; seed4: MPPE +0.01 RPE +0.02; seed5: MPPE +0.04 RPE -0.15; seed6: MPPE +0.00 RPE +0.03
- ep18 (base SP 1.0, MP 1.0, MPPE 1.1864, RPE 1.8374): scan4096: MPPE -0.37 RPE -0.41; scan20000: MPPE +26.02 RPE +38.57 ['SP_SR', 'MP_SR'] flips; seed3: MPPE -0.08 RPE -0.22; seed4: MPPE -0.17 RPE -0.26; seed5: MPPE -0.16 RPE -0.26; seed6: MPPE -0.14 RPE -0.26
- ep22 (base SP 1.0, MP 1.0, MPPE 1.8003, RPE 1.2222): scan4096: MPPE +4.02 RPE +0.61 ['MP_SR'] flips; scan20000: MPPE +0.48 RPE +0.90 ['MP_SR'] flips; seed3: MPPE -0.20 RPE -0.01; seed4: MPPE +0.20 RPE -0.07 ['MP_SR'] flips; seed5: MPPE -0.01 RPE -0.07; seed6: MPPE -0.37 RPE -0.07
- ep24 (base SP 1.0, MP 1.0, MPPE 2.3599, RPE 0.9832): scan4096: MPPE +17.06 RPE +20.08 ['SP_SR', 'MP_SR'] flips; scan20000: MPPE +17.06 RPE +20.02 ['SP_SR', 'MP_SR'] flips; seed3: MPPE +0.03 RPE -0.04; seed4: MPPE -0.06 RPE -0.05; seed5: MPPE +0.11 RPE -0.06; seed6: MPPE -0.13 RPE +0.10
- ep31 (base SP 1.0, MP 1.0, MPPE 2.011, RPE 1.8848): scan4096: MPPE +18.69 RPE +24.92 ['SP_SR', 'MP_SR'] flips; scan20000: MPPE +18.04 RPE +23.66 ['SP_SR', 'MP_SR'] flips; seed3: MPPE +0.01 RPE -0.03; seed4: MPPE +0.01 RPE +0.03; seed5: MPPE -0.06 RPE +0.03; seed6: MPPE +17.34 RPE +22.32 ['SP_SR', 'MP_SR'] flips
