# Start-frame survey of the packed eval simulator assets (1 Nov 2026, report only)

The orchestrator asked for this at 06:36 UTC, relaying keen-heisenberg. It is report only: no gates, no new pieces,
nothing changed. `sets/ev20` (frozen, `FROZEN.md`) is untouched. CPU, this container, $0. GT-free: the inputs are the
packed references (object poses, robot hand frames), our meshes, the packed collision pieces and our table (each
reference's support usda).

Labels: [M] measured here, [R] read from the pack's own stored files, [H] hypothesis.

## In plain words

- **All 20 packed eval references were rebuilt and settled at f0.** Every object is free, with no hands, on its
  packed collision pieces, and is simulated for 2 s in plain MuJoCo. None failed to rebuild.
- **Two objects fall over at the start frame with no hand near them** [M]:
  - the **eval-20 pitcher**: 195 mm / 95 deg, all 16 jittered copies fall;
  - the **eval-19 sweeper**: 90 mm / 89 deg, all 16 copies fall.
- **Two more move clearly:**
  - the **eval-30 sweeper**: 24 mm / 25 deg; 13 of 16 jittered copies fall. It starts 12.2 cm3 inside the rack's
    packed pieces.
  - the **eval-10 beige cup**: 6.5 mm / 4 deg; a hull corner sits below its support.
- **Everything else stays within 4.3 mm and 5.1 deg.** That covers every pot, every rack, all the spoons, the boards
  and the dust pans.
- **Held objects are not candidates.** The eval-20 blue cup (48.7 mm) is in a hand at f0, 47.7 mm above the table, so
  a hands-free drop is expected.
- **The pack's FlashCHORD rest checks [R] disagree with this survey on many objects.** Those checks replay zero
  actions with the robot hands moving. In them, pots and spoons on evals 3, 5, 6, 8, 16 and 33 move 4.9-65 mm or
  8-24 deg before a hand comes for them. Hands-free, the same objects stay within 0.2-1.8 mm here.
  - So their start motion is not explained by geometry under gravity.
  - [H] The robot hands or arm touch them during the approach, or the replay tracks a reference that itself moves.
  - Falsifier: a FlashCHORD zero-action replay with the hands parked away from the objects. If those objects then stay
    within 5 mm / 2 deg, the hands cause it.
  - A start-frame geometry fix would not help those objects.

## Ranked list, start frame f0 [M] (`results/f0/f0_tables.md`, `results/f0_survey.json`)

"Settle" = the exact reference pose after 2.0 s. "Jitter" = 16 copies with every object jittered 0.5 mm / 0.005 rad
(seed 2). Falls over = rotation >= 30 deg at 2 s. The visible cause is a heuristic, and is given only for objects that
move more than 4 mm or 5 deg.

| # | Eval | Object | Settle, mm / deg | Falls over | Jitter: median / max mm (falls) | Hand at f0, mm | Table pen., mm | Packed overlap, cm3 | Visible cause | FlashCHORD rest check [R] |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 20 | water_pitcher | **195.2 / 94.6** | **yes** | 193.6 / 200.1 (16/16) | 31.2 | -0.13 | 0 | COM outside the footprint at the f0 pose (1 mm band: COM 33 mm outside; 3 mm band: 0.8 mm outside). The arc foot was certified for f152, and support_fill marked f0 "UNSTABLE" | 10.4 mm / 3.9 deg before the hand at f14 (fail) |
| 2 | 19 | mini_sweeper | **90.2 / 88.8** | **yes** | 90.2 / 91.5 (16/16) | 170.2 | 0.58 | 0 | Narrow footprint: COM 4.2 mm inside the 1 mm band at 63 mm height, so it tips past 3.8 deg. It stands on its bristles. Eval 19 is std mode, with no support_fill | none stored (std) |
| 3 | 20 | blue_cup | 48.7 / 1.6 | no | 48.7 / 49.2 | **5.8 (held)** | -47.7 | 0 | Held at f0, 47.7 mm above the table: a hands-free drop, not a fix candidate | 0 / 0 (until f1) |
| 4 | 30 | mini_sweeper | **23.9 / 25.0** | no (13/16 copies do) | 25.3 / 233.5 (13/16) | 260.6 | 0.58 | rack 12.15 | Starts 12.2 cm3 inside the rack's packed pieces; COM outside the footprint (-1.5 / -0.5 mm) | none stored (std) |
| 5 | 10 | beige_cup | **6.5 / 4.0** | no | 6.4 / 7.6 | 178.1 | -0.87 | 0 | Hull corner below the support (COM 12.8 mm outside the 1 mm band, 17.2 mm inside the 3 mm band); `ev10` lathe pieces | 7.6 mm / 4.0 deg (fail) |
| 6 | 1 | white_pot_lid | 4.3 / 1.6 | no | 4.6 / 10.8 | 170.8 | (on the pot) | 0 | Rests 0.2 mm from the pot mesh, but the `ev01` carve leaves a gap to the pot's pieces (median 3.6 mm, evalcheck [R]), so the lid drops onto them | none stored (std) |
| 7 | 32 | blue_cup | 3.3 / 2.1 | no | 3.4 / 4.5 | 13.3 (held) | 0.74 | 0 | Held; no H30 rest run in the whole reference | 0 / 0 |
| 8 | 30 | plastic_dish_rack | 3.2 / 0.9 | no | 7.7 / 41.5 | 73.6 | 0.16 | sweeper 12.15 | Pushed by the sweeper overlap | none stored (std) |
| 9 | 14 | blue_cup | 2.9 / 1.9 | no | 3.0 / 4.2 | 316.4 | 0.08 | 0 | - | 4.0 mm / 2.4 deg (fail) |
| 10 | 33 | blue_cup | 2.6 / 1.7 | no | 2.7 / 3.9 | 174.6 | 0.27 | 0 | - | 2.5 / 1.5 |
| 11 | 10 | blue_cup | 2.4 / 1.5 | no | 2.4 / 3.6 | 68.8 | 0.00 | 0 | - | 3.4 / 4.1 (fail) |
| 12 | 8 | beige_cup | 1.9 / 1.0 | no | 2.2 / 3.2 | 201.0 | 1.47 | 0 | - | 8.1 / 5.5 (fail) |
| 13 | 15 | wooden_spoon | 1.8 / 3.4 | no | 1.9 / 2.5 | 121.1 | -1.01 | 0 | - | 5.4 / 12.7 (fail) |
| 14 | 3 | white_pot | 1.7 / 1.6 | no | 1.6 / 2.0 | 214.0 | 1.20 | 0 | - | **65.1 / 11.4 (fail)** |
| 15 | 38 | mini_dust_pan | 1.4 / 2.8 | no | 1.2 / 1.7 | 207.6 | 0.50 | 0 | - | 2.0 / 3.8 (fail) |
| 16 | 28 | plastic_dish_rack | 1.2 / 1.2 | no | 0.9 / 2.5 | 72.1 | 1.06 | pot 0.46 | - | none stored (std) |
| 17 | 14 | plastic_dish_rack | 1.1 / 0.3 | no | 0.9 / 1.8 | 144.6 | -0.70 | 0 | - | 2.8 / 1.6 |
| 18 | 5 | wooden_spoon | 1.0 / 1.7 | no | 1.1 / 1.7 | 157.6 | 0.02 | 0 | - | 4.3 / 4.8 (fail) |
| 19 | 35 | wooden_spoon | 0.9 / 5.1 | no | 1.0 / 1.5 | 109.3 | 0.18 | 0 | Rocks 5 deg, then still | 4.0 / 8.1 (fail) |
| 20 | 19 | mini_dust_pan | 0.9 / 2.3 | no | 1.0 / 1.3 | 10.2 (held) | 0.29 | 0 | - | none stored (std) |
| 21 | 28 | white_pot | 0.9 / 0.5 | no | 0.9 / 2.6 | 76.2 | -0.18 | rack 0.46 | - | none stored (std) |
| 22 | 32 | wooden_spoon | 0.8 / 4.0 | no | 0.9 / 1.1 | 112.0 | 0.52 | 0 | - | 3.8 / 4.5 (fail) |
| 23 | 33 | wooden_spoon | 0.6 / 1.7 | no | 0.7 / 1.3 | 167.1 | -0.40 | 0 | - | **24.5 / 21.7 (fail)** |
| 24 | 8 | white_pot | 0.6 / 0.3 | no | 0.6 / 1.3 | 222.4 | -0.21 | 0 | - | **38.6 / 14.3 (fail)** |
| 25 | 25 | wooden_piece_2 | 0.5 / 1.9 | no | 0.6 / 1.1 | 119.8 | -0.07 | 0 | - | none stored (std) |
| 26 | 16 | wooden_spoon | 0.5 / 2.5 | no | 0.6 / 0.9 | 186.2 | 0.05 | 0 | - | 4.9 / **24.2** (fail) |
| 27 | 36 | wooden_spoon | 0.5 / 0.7 | no | 0.8 / 1.4 | 97.5 | -0.14 | 0 | - | 3.8 / 2.5 (fail) |
| 28 | 25 | wooden_piece_1 | 0.4 / 0.5 | no | 0.3 / 0.8 | 143.4 | -0.19 | 0 | - | none stored (std) |
| 29 | 5 | white_pot | 0.4 / 0.5 | no | 0.6 / 1.0 | 79.5 | 0.23 | 0 | - | **25.7 / 9.1 (fail)** |
| 30 | 37 | wooden_spoon | 0.4 / 1.9 | no | 0.7 / 1.2 | 138.5 | 0.22 | 0 | - | 3.9 / 8.1 (fail) |
| 31 | 15 | plastic_dish_rack | 0.4 / 0.3 | no | 0.4 / 0.8 | 43.3 | -0.01 | 0 | - | 3.1 / 0.4 |
| 32 | 6 | wooden_spoon | 0.4 / 1.6 | no | 0.5 / 0.9 | 140.8 | 0.01 | 0 | - | 12.2 / 8.0 (fail) |
| 33 | 3 | wooden_spoon | 0.3 / 0.6 | no | 0.4 / 1.0 | 83.2 | -0.21 | 0 | - | 2.4 / 1.6 |
| 34 | 1 | white_pot | 0.3 / 0.3 | no | 0.6 / 0.9 | 158.7 | 0.25 | 0 | - | none stored (std) |
| 35 | 16 | plastic_dish_rack | 0.2 / 0.4 | no | 0.5 / 0.9 | 96.4 | 0.54 | 0 | - | 2.5 / 1.9 |
| 36 | 6 | white_pot | 0.2 / 0.2 | no | 0.5 / 0.8 | 167.1 | 0.13 | 0 | - | **17.5 / 3.1 (fail)** |

**First H30 rest frame** (report only). This applies where an object has a hand within 30 mm at f0. Each such object
gets its own first run of >= 5 hands-off static frames; the first run in which every object is hands-off is also used.
- **Eval 20.** The pitcher's packed pieces are poor here too:
  - the blue cup's first H30 rest is f180: pitcher 3.30 mm / 5.89 deg (cup 0.75 mm);
  - the first all-object H30 rest is f181: pitcher 2.93 mm / 8.02 deg, 3 of 16 jittered copies fall (cup 0.60 mm);
  - cause: a hull corner below the arc foot. This is the case `sets/ev20` (b1) fixes.
- **Eval 19.** The dust pan's first H30 rest is f201: dust pan 0.94 mm / 2.1 deg. The sweeper is held there (3.6 mm),
  so it drops.
- **Eval 32.** The blue cup has no H30 rest run in the whole reference.

**Not reconstructed:** none. All 20 references matched their listed md5.

## Where a start-frame fix could pay (ranked; hands-off objects whose start pose physics will not keep)

1. **Eval-20 pitcher.**
   - Measured: it falls over from f0 (16/16 copies), and in FlashCHORD it is already 10.4 mm / 3.9 deg off before the
     hand reaches it at f14 [R].
   - A fix already exists in part: the frozen `sets/ev20` (b1) gives 8.5 mm / 3.2 deg at f0 in plain MuJoCo (`README.md`
     section 2). It also holds the f152, f183 and f192 rests.
   - The f0 pose itself is unsupported by any packed foot: support_fill could not certify it.
   - [H] A foot (or fill) certified at the f0 pose would stop the start motion. It would have to clear the f152 rest
     too.
2. **Eval-19 sweeper.**
   - Measured: it falls over from f0 (16/16), hands 170 mm away. It stands on its bristles with the COM 4.2 mm inside
     a 1 mm support band.
   - Eval 19 is a std-mode reference, so support_fill never ran on it. Public ep18's brush had the same failure, which
     support_fill was written for.
   - [H] support_fill's certified underside fill / arc foot at f0 keeps it standing. Falsifier: the settle with the
     support_fill output still tips more than 5 deg.
   - It is cheap to test: support_fill.py on the packed eval-19 reference, then this settle. That needs a dated
     pre-registered step.
3. **Eval-30 sweeper.**
   - Measured: 24 mm / 25 deg, with 13/16 copies falling. It starts 12.2 cm3 inside the rack's packed pieces, and its
     COM is outside its footprint.
   - The earlier placement carve (`ev30`) let it fall through the slot (do-not-use).
   - This is the rack-slot / pose lane's problem (evalcheck: the CoACD rack fills the slot), not a base fix.
4. **Eval-10 beige cup.**
   - Measured: 6.5 mm / 4.0 deg; FlashCHORD 7.6 mm / 4.0 deg [R].
   - Cause: a hull corner of the `ev10` lathe pieces sits below its support.
   - It belongs to the eval-10 cavity-safe lane (ev10cs4 / ev10cs5, frozen). Their floor and base pieces should be
     checked at f0 with this settle before use; this survey did not run them.
- **Not candidates for a geometry fix:**
  - **Pots on evals 3, 5, 6, 8 and spoons on evals 16, 33.** The large FlashCHORD start motion [R] does not appear
    hands-free (<= 1.8 mm here); see the [H] above.
  - **The eval-1 lid.** Its 4.3 mm drop onto the `ev01` pieces is the carve's designed gap.
  - **Held objects** (eval-20 cup, eval-32 cup, eval-19 dust pan).

## Method and run record

- **References and assets.** focused-pascal's `packed_refs.json` (a7ed39d6), all 20 episodes. Downloaded from the
  store with `collcarve2-evalcheck/scripts/dl.py` into scratch (evals 1, 3, 5, 6, 8, 20, 28 earlier; the other 13 now).
- **Collision per object** = the URDF the reference names:
  - `refs/sf/epN/assets` copies are used as stored;
  - `/content/assets` is rebuilt with focused-pascal's `make_assets.py` from the listed library, plus `--pieces` for
    evals 1 (`ev01`), 10 (`ev10`, with its `inertia.json`) and 25 (`ev25`). Their md5s are identical on both branches.
  - glb collisions go through FlashCHORD's CoACD call (coacd 1.0.11, threshold 0.05), cached by glb md5; obj / stl
    collisions are one piece each.
  - Counts and URDF md5s are in `results/f0/ep<N>.json`.
- **Scene.** As `scripts/settle.py`: sim=rl options (`cfg_sim_rl.yaml` sha256 checked; dt 0.01 s, Newton,
  implicitfast, pyramidal, impratio 20), condim 3, friction 1.0, URDF mass / COM / inertia (0.3 kg placeholders), a
  table plane at the usda top, all objects free, no hands, 2.0 s.
- **Commands.**
  - `python -I scripts/f0_survey.py packed_refs.json <dl>,<dl2> <fp pipeline> <coacd1011> <work> <out> <eps>`: three
    processes, about 1-90 s per episode; evals 19, 20 and 32 were re-run after the per-object H30 change.
  - `python -I scripts/f0_report.py <out> <rest checks> results/f0_survey.json > results/f0/f0_tables.md`.
- **The [R] rest checks.** The pack's own `rest_check.json` files (FlashCHORD zero-action replay of each grasp-lock
  reference; within 5 mm / 2 deg until a hand comes) were read from the store into `results/rest_check_R/`. Std-mode
  references (1, 19, 25, 28, 30) store none.
- **Caveats.**
  - This is plain MuJoCo, not MuJoCo-Warp: no hands, a plane instead of the usda cylinder, default solref / solimp.
  - "Falls over" and the causes are heuristics on the f0 geometry. They are not gates.
  - The survey sees only gravity and contacts at f0, not hand-object interaction.
