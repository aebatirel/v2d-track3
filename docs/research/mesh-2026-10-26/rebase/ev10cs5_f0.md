# Eval-10 cup pieces at the start frame: ev10cs5 against ev10cs4 and the packed ev10 (1 Nov 2026, report only)

The orchestrator asked for this at ~07:00 UTC. It informs the reading of the ev10cs5 retrain, which has been running
since 06:29 (s42). It decides nothing. The frozen folders (`gmg/build/I/results/ev10-cavsafe/ev10cs4`, `ev10cs5`,
`meshes/carve/ev10`) are read, not changed. CPU, $0, GT-free.

## What was run

- **Reference.** The packed eval-10 reference: `runs/20261026-gl10A2-5e0e100/refs/glockt/ep10/.../ref_gl_ilc.parquet`,
  md5 1a5003d9 (matches `packed_refs.json`). It names `/content/assets`, so each variant's assets are
  `make_assets.py meshes/library_v3 OUT --pieces <folder>`. Its `inertia.json` sets each cup's COM and inertia (0.3 kg).

| Variant | Pieces folder | Pieces blue / beige | Blue URDF md5 | Beige URDF md5 |
|---|---|---|---|---|
| packed | `meshes/carve/ev10` | 53 / 49 | 82ff6cb8 | b994e584 |
| ev10cs4 | frozen ev10cs4 | 24 / 21 | 8511f0d3 | 1a8cb9d8 |
| ev10cs5 | frozen ev10cs5 (folder hash 44661a9a) | 24 / 21 | ac8d296b | 1a8cb9d8 (identical to cs4) |

- **Scene.** The f0-survey method (`f0_survey.md`): plain MuJoCo with the sim=rl options, both cups free, no hands,
  table plane at the support usda top (0.600 m), 2.0 s. Each frame gets the exact pose plus 16 copies with both cups
  jittered 0.5 mm / 0.005 rad (seed 2). Falls over = rotation >= 30 deg.
- **Frames.**
  - **f0.**
  - **First H30 rest frame.**
    - The beige cup's first run of >= 5 frames with no hand within 30 mm and < 2 mm per-frame motion starts at **f147**.
    - The blue cup has no such run, and neither does the pair.
    - At f147 both hands are about 200 mm away.
  - **f124**, as requested. Both cups are within 1.2-1.5 mm of a hand there.
- **The reference floats the stack at f124 and f147** [M]. The blue cup's lowest point is 24.4 mm (f124) and 11.5 mm
  (f147) above the table. The beige cup's is 32.2 / 30.4 mm.
  - So a hands-free settle there drops the stack 11-26 mm in every variant.
  - The number that tells the variants apart is the **beige cup's motion relative to the blue cup** (the nest).
- Script: `scripts/ev10x_settle.py`. Output: `results/ev10x/ev10x.json`.

## Numbers [M]

Exact copy at 2 s; jitter = the 16 copies, median / max. No copy falls over and none goes NaN.

| Frame | Variant | Blue cup, mm / deg | Beige cup, mm / deg | Beige in blue (nest), mm / deg | Jitter beige mm / deg (max) | Jitter nest mm (max) | Max nefc, exact / 16 copies |
|---|---|---|---|---|---|---|---|
| f0 | packed | 2.35 / 1.52 | **6.50 / 3.98** | 5.40 / 3.16 | 6.42 / 3.91 (7.58 / 4.51) | 5.85 (6.76) | 220 / 356 |
| f0 | ev10cs4 | 0.86 / 0.55 | **6.54 / 3.98** | 5.66 / 3.75 | 6.43 / 3.91 (7.57 / 4.51) | 5.50 (7.66) | 100 / 116 |
| f0 | **ev10cs5** | **0.86 / 0.55** | **6.54 / 3.98** | 5.66 / 3.75 | 6.43 / 3.91 (7.57 / 4.51) | 5.50 (7.69) | 100 / 116 |
| f147 (first H30, beige) | packed | 14.90 / 4.41 | 14.06 / 6.58 | **3.91 / 6.73** | 14.24 / 6.55 (15.73 / 7.40) | 4.27 (4.93) | **556 / 728** |
| f147 | ev10cs4 | 14.36 / 3.74 | 26.26 / 6.39 | **13.21 / 6.84** | 25.77 / 5.28 (27.20 / 7.16) | 12.78 (14.51) | 232 / 248 |
| f147 | **ev10cs5** | 14.33 / 3.78 | 23.99 / 6.40 | **10.84 / 6.95** | 23.99 / 5.75 (25.78 / 11.38) | 11.17 (12.88) | 136 / 228 |
| f124 | packed | 26.18 / 3.79 | 25.18 / 7.44 | **4.48 / 8.19** | 25.07 / 7.40 (26.05 / 8.73) | 4.96 (6.03) | **780 / 948** |
| f124 | ev10cs4 | 25.72 / 6.59 | 27.09 / 4.19 | **5.13 / 6.93** | 27.32 / 6.60 (28.18 / 10.73) | 4.98 (7.78) | 272 / 488 |
| f124 | **ev10cs5** | 26.10 / 4.36 | 25.58 / 5.42 | **2.78 / 7.60** | 25.60 / 6.76 (26.65 / 9.67) | 4.57 (7.59) | 188 / 288 |

## Reading

- **The beige corner-below-support issue carries over unchanged** [M].
  - At f0 the beige cup moves 6.54 mm / 3.98 deg with ev10cs4 / cs5, against 6.50 / 3.98 packed. The jittered copies
    agree to within 0.01 mm.
  - With cs4 / cs5 only 5 collision vertices lie within 1 mm of its lowest point (12 with packed). The COM is 15.8 mm
    outside them (12.8 packed), but 17.2 mm inside the 3 mm band in both.
  - So the beige cup rocks off a low corner onto its base. cs4 / cs5 changed the beige pieces (49 -> 21) but kept that
    corner.
  - The pack's own FlashCHORD rest check [R] has the beige cup 7.6 mm / 4.0 deg off before the hand at f23. That is the
    same size and fits this cause [H].
- **The blue cup at f0 is better with cs4 / cs5**: 0.86 mm / 0.55 deg, against 2.35 / 1.52 packed. ev10cs5's 8 mm
  floor changes nothing at f0 compared with cs4.
- **Nest (relative) motion when the stack is dropped hands-free:**
  - f147: cs5 lets the beige cup move 10.8 mm in the blue (cs4 13.2, packed 3.9). This fits the known cs trade: the
    beige sits deeper than the reference (STATUS: 1-24 mm).
  - f124: cs5 2.8 mm against cs4 5.1 and packed 4.5.
- **Contacts.** Packed overflows the 512-row limit at the nest (556-948 rows). cs5 stays at 136-288 rows, cs4 at
  232-488. That is the overflow the cs folders were built to remove.
- **For reading the s42 run:**
  - a start-frame wobble of the beige cup (about 6.5 mm / 4 deg before the hand comes) is expected with ev10cs5, as
    with the packed pieces;
  - the blue cup should start steadier;
  - in a drop or release at the nest, the beige cup may sit up to about 11 mm deeper in the blue than the reference.
- **A fix, if wanted later** (a separate pre-registered step): clip the beige pieces at the 3 mm band level, as b1 did
  for the eval-20 pitcher. [H] It would remove the corner. Falsifier: the f0 settle still moves the beige cup by more
  than 4 mm or 5 deg.

## Caveats

- Plain MuJoCo, not MuJoCo-Warp. No hands. A plane instead of the usda cylinder.
- At f124 / f147 the absolute numbers are mostly the reference's floating stack falling, so only the nest numbers
  separate the variants there.
- f124 is not hands-off: hands are within 1.5 mm.
