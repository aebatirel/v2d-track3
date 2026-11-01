# PREREG T3: "a resting object does not float" (written and pushed BEFORE any T3 score)

Session physics-perception, 1 Nov 2026 ~21:45 UTC. CPU, $0. Public episodes only.

## Evidence before this test
- D4 (oracle): constant translation offsets after the kit alignment are worth +0.030 (vertical +0.019, along the f0
  camera ray +0.020, lateral +0.009; overlapping); +0.0195 after the exact-tilt oracle. Largest: ep24, ep31, ep11.
- D5 (`scripts/d5_float.py`; mocap only for the TRUE column): 10 runs where an object is > 10 mm above our table with
  no detected hand and no support. 7 are real (held, hand missed by MediaPipe: 54–280 mm high, the pitcher during
  pours, pot, dust pan, sweeper, ep21 cup). 3 are false floats, low and static: ep11 blue cup 23 vs truth 0.6 mm,
  ep23 board 1 16 vs 1.3, ep24 board 2 16.6 vs 2.3. Scans rest 0–2 mm above the table at f0 in every episode.
- Disclosure: STATIC_MM = 3, CAP_MM = 40, MINRUN = 10 were chosen after D5, in-sample. The GT-free dry run
  (`scripts/pp_drop.py`, out/F1dry) applies exactly ep11 blue cup f103–136 and ep24 board 2 f245–274 and nothing else.
  This test can confirm the rule does no harm and measures its size; it is not an independent test of the thresholds.

## Transform: `scripts/pp_drop.py` (docstring has the rule). Translation along our table normal only; 3-frame ramps.

## Arms
| arm | content | role |
|---|---|---|
| **F1** | pp_drop on the base tracks | primary, gated |
| F1P1 | T1 P1 (fused anchor tilt) then pp_drop | stack, gated on its own |

## Gate (unchanged): mean ΔAUC >= +0.003 over 20; no episode < −0.010; mean ΔMPPE <= 0, mean ΔRPE <= 0.
Expected [E]: F1 ≈ +0.001 (two short segments), so likely below the mean clause; F1P1 ≈ +0.0025.
