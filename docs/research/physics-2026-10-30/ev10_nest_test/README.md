# Eval-10 nest test in FlashCHORD: packed `meshes/carve/ev10` vs candidate ev10cs4 (1 Nov 2026, CPU) [M]

**Asked by** bold-albattani (04:59 UTC): their next step after the contact-budget gate, including a floor-crossing
check. ev10cs4 passed the gate at 05:04 UTC (`contact_budget/README.md`: 0 / 0 overflow lines, hold max 448).

**Inputs.**
- The packed eval-10 reference (gl10A2, md5 1a5003d9).
- library_v3 with `--pieces meshes/carve/ev10` (packed, 53 / 49 pieces) or with `--pieces ev10cs4` (bold-albattani
  7e4bc6a, 24 / 21 pieces).

**Test.** `tools/carve_fc_test.py`, in a scratch copy that also records B's pose in A's frame
(`scripts/carve_fc_test_relT.py`).
- FlashCHORD scene, training sim config (sim=rl: njmax 512, nconmax 256), 1 world, CPU, hands parked.
- A = blue cup, B = beige cup.
- **driven:** both cups are pulled to the reference by critically damped springs (8 Hz), f100–161, summarised over
  f124–161.
- **rest:** the cups are placed at f124 and released with no drive, f125–161.
- Floor crossing (`scripts/floor_check.py`): the beige collision vertices in the blue frame against ev10cs4's floor
  plate (piece_16, 6.0 mm thick, 22.67 cm³). Its thin direction is the cup axis, and only vertices within the plate's
  ring (r < 34 mm) count. "Into" means past the plate's cavity face; "through" means past its far face.

| run | blue err median / max | beige err median / max | beige-relative-to-blue err median / max | overflow lines | NaN |
|---|---|---|---|---|---|
| packed, driven | 0.49 / 1.04 cm, 2.9° | 0.51 / 1.03 cm, 4.1° | **1.02 / 2.06 cm, 7.0° / 11.1°** | 0 | no |
| ev10cs4, driven | 0.10 / 0.27 cm, 0.5° | 0.08 / 0.24 cm, 0.7° | **0.14 / 0.52 cm, 1.1° / 2.7°** | 0 | no |
| packed, rest | 1.30 / 2.35 cm | 2.39 / 2.71 cm | 1.28 / 2.14 cm, 5.6° | 0 | no |
| ev10cs4, rest | 1.30 / 2.48 cm | 2.77 / 3.36 cm | 1.59 / 2.52 cm, 6.7° | 0 | no |

**Floor crossing, ev10cs4:**
- driven: at most 0.43 mm into the plate (5 of 61 frames); the beige normally sits 9.6 mm above it; 0 frames
  through.
- rest: the release impact reaches **5.49 mm** of the 6 mm plate at f126. It then settles to median 0.95 mm (max
  1.95 mm) from f130 on; 0 frames through.

**Reading.**
- ev10cs4 lets the beige follow the reference nest about 7× more closely than the packed pieces (0.14 vs 1.02 cm
  median), with no overflow and no floor crossing.
- Free rest is slightly worse than packed: the beige settles away from a reference pose whose visual meshes overlap
  80 cm³.
- The only margin concern is the release impact: 5.5 of 6 mm. A thicker plate would add margin. That is a design
  choice for bold-albattani, and a hypothesis, not tested.

## 8 mm plate variant (keen-heisenberg's question, 05:14 UTC; report only, not a delivery)
- **Variant:** ev10cs4 with piece_16's cavity face moved 2 mm into the cavity (6 → 8 mm). It stays convex, at
  30.7 cm³. The far face and every other piece are unchanged, so the floor is 2 mm higher. Built ad hoc here; not
  bold-albattani's.
- **rest from f124:** beige relative to blue 1.30 cm median (6 mm plate: 1.59). Floor: max **4.02 mm** into the 8 mm
  plate, at f144 (6 mm plate: 5.49 of 6 at f126); settled median 0.49 mm; 0 frames through.
- **driven:** 0.12 cm / 0.9° median (6 mm plate: 0.14). Floor: max 1.5 mm (f101); 0 frames through.
- No overflow lines and no NaN.
- **Reading:** the 8 mm plate leaves ~4 mm of margin at the worst moment instead of 0.5 mm, with tracking unchanged
  or better. Cost: the floor is 2 mm higher. That moves the nest 2 mm off the reference's depth, which in turn is
  deeper than the visual meshes allow.
