# ev10cs5: provenance

- Byte copy of `docs/research/mesh-2026-10-26/gmg/build/I/results/ev10-cavsafe/ev10cs5/` at commit `2b016b4a309cecb8ce0f1d507927712ffaef1b8d` (git tree `6ff0b6a3a74b980894bca40374d3fbb547888692`), imported 2026-11-01 05:18 UTC by `tools/e10cs_pieces.py import`.
- 50 input files; `MD5SUMS` lists them (md5 of MD5SUMS `045d8921d5fe548ffebbee3cc21e798b`); `FROZEN.md` is the source's own freeze, byte copy, and lists the same md5s (checked at import).
- Check: `python3 tools/e10cs_pieces.py check --dir meshes/carve/ev10cs5`.

## What it is ([R] the mesh lane, bold-albattani; [M] measured here)
- ev10cs4 with only the blue floor plate thickened to 8 mm (`--plate_t 0.008`, amendment A5 `99be31e`, written before the
  build; built `7935261`, frozen `2b016b4`). Standby set for the eval-10 retrain (PREREG section 2.2 decides which set).
- [M] `tools/e10cs_pieces.py compare --base meshes/carve/ev10cs4 --cand meshes/carve/ev10cs5`: 46 of 51 files
  byte-identical; differing: `blue_cup/piece_16.obj` (the floor plate, 22.665 -> 30.933 cm3, 6 -> 8 mm) and the four
  records that follow it (`blue_cup/inertia.json`, `blue_cup/lathe_collision.json`, `carve.json`, `FROZEN.md`). Every other
  piece and every beige_cup file identical (clause (a) holds).
- GT-free as ev10cs4 (same inputs, one constant changed); `tools/no_oracle.py`: accepted [M].
- make_assets.py library_v3 + this folder (CPU): blue_cup_rigid.urdf md5 ac8d296b440ceeb24e895366f45365d8, beige
  1a8cb9d813c7a8085b4759347a16a8ba (= ev10cs4's). Blue COM (0.46, 1.04, 19.05) mm (+16.1 mm vs ev10), ixx / iyy / izz
  1.0036e-3 / 1.0031e-3 / 4.448e-4 (+1.9 / +2.0 / +1.0 % vs ev10); beige as ev10cs4.
- Trades: as ev10cs4 (its PROVENANCE.md), with the lane's plain-MuJoCo v5 notes (indicative only; plain MuJoCo
  over-counts against MuJoCo-Warp): f124 drops 0 of 16 copies through the floor (v4 6 / 16); gate 1 max overlap at f124
  3.9 cm3 against their 3.0 bar (FAIL; median unchanged 0.206); f111 3 of 16 copies over the limits (gate 2 FAIL); gate 4a
  blue 0.402 FAIL (as every set). determined-wright's 8 mm nest test (05:17 UTC) used their own variant of the plate
  (30.7 cm3), close to but not byte-identical with this one [R].
- [M] Its V4p nest seat moves the beige 0.88 cm median (1.63 max) from V over the hands-off frames
  (docs/research/work/eval10-cs4-20261101/cpu/out/seat_compare.json).
