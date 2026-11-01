# verify_slot3_1: board slot round 3 (F-I4.17), geometry, physics and contact-budget lens

Verifier, 31 Oct - 1 Nov 2026, 23:50-00:35 UTC. I did not build this. My job was to find what is wrong with it.

Scope:
- the round-3 Build + public runs under F-I4.17: build dc4a2a4 / a130449, records up to 7cbe443;
- ep24 `fi4q`: `build/I/results/slot3-ep24/fi4q/`, clean bundle `20261031-b4ext4-b61e8aa`, picks in
  `runs-dev/20261031-i2probe-626ce13`;
- the w10 records in `slot3-tests/fi417/`;
- the gate validity check on the round-2 r0 (`slot2-ep24/fi4o/r0`).

Labels: [M] measured by me, [R] read from code or records, [E] estimate, [H] hypothesis.

I re-measured with my own code wherever the lens asks for a re-measure:
- cuboid recovery from the delivered OBJ files;
- rasterising the delivered boxes onto the outline raster;
- an exact global optimum of the rectangle family;
- slot geometry from the boxes;
- voxel-state shares and the FREE volume per hull;
- my own MuJoCo count scene (own XML, exact inertia, own counter);
- my own P3 replay.

I reused committed code only for:
- loading the bundle, `plate_info` / `_outline` (the outline raster itself), `Evidence` (the voxel states) and
  the relative poses;
- `simphys.jitters` (the same jitter draws);
- the w10 fixture and `run_pair`, to rebuild cells that have no saved pieces.

The gmg code I imported is byte-identical to a130449. `git diff a130449 HEAD` is empty for `platebody`,
`interlock`, `simpieces`, `simphys`, `contactgate_fi4`, `guard`, `silhouette`, `test_fi415`, `test_fi416` and
`test_interlock`, and the working tree is clean for them.

## Answer in plain words

**The build's numbers reproduce, and the freeze verdict "not frozen" stands.**
- My own count scene reproduces the ep24 part-1 result exactly when it uses the same body-frame convention as the
  build: delivered 124 rows, default 112, one-box control 32, so the ratio is 3.875 > 2.0. No copy overflows.
- The fail is robust:
  - native box geoms, multiccd off, another jitter draw: 3.75;
  - bodies placed at the world origin: 3.75-5.17.
- The delivered boxes are exactly what the manifest says, and the fit is the global optimum of its family.
- The slot has the rule's width, centre and depth.
- The P3 replay reproduces on ep24 (0.0741 cm / 0.68 deg) and on w10 k5 (0.031 cm / 0.14 deg).

**Three things the record does not show.**
1. **The w10 freeze family cannot see outline growth** (N1).
   - Against the true synthetic plate, the low-piece body is 8-18 % too large in area, and 8-14 mm too long and
     5-13 mm too wide.
   - Its IoU with the truth is 0.93 at sigma_e 1, 0.87-0.89 at sigma_e 2 and 0.85 at sigma_e 3.
   - The gated IoU (against the outline raster) stays at 0.97-0.99, because the raster grows together with the
     body.
   - So "(b) holds" is true as F-I4.17.3 reads it, but it is not evidence that the body has the right shape.
2. **The ratio on ep24 is set by how the boxes stand on the table, not by the slot** (N2, N3).
   - The pair settles standing on its edges. Every box along the resting edge adds 4 contacts (16 rows).
   - The one-box control does not stay assembled: its boxes start 7.7 cm3 inside each other, are pushed apart
     and end lying flat.
   - Cutting board 1 in the other direction (partition B) gives 72 rows (2.25). Cutting both boards that way
     gives 64 rows (2.0), but 80 rows (2.5) with the other body-frame convention.
   - So on ep24 the gate's verdict depends on the box-partition tie rule and on chaos at the limit. This is a
     diagnostic, not a proposal: the partition rule was fixed before the run.
3. **The keep-out gate is empty by construction for box pieces** (N4).
   - On ep24, 6 of 10 delivered hulls hold more than 0.3 cm3 of seen-empty (FREE) space, up to 6.1 cm3. On w10
     (k4-k6), 8-10 of 10 hulls per cell do, up to 12.5 cm3.
   - The recorded keep-out of 0.0 cm3 cannot be anything else. The freeze criterion "keep-out <= 0.3 cm3 per hull"
     therefore carries no information here.

**Two smaller points.**
- The w10 ratio margin is thinner than one contact. Between implementations, k2 and k6 swap sides of 2.0 (N5).
- The gate-validity counts at S2 change by up to 3.5 x with the free-joint frame placement (N6).

**No blocking item.** The round stopped on (a), and every item above makes the stop more justified, not less.
N1 must be dealt with before any re-freeze.

## Verdict

| Item | Status |
| --- | --- |
| ep24 delivered pieces: 5 slotted / 3 default exact cuboids per board, t 7.4012 mm on the mid plane, boxes = manifest | confirmed [M] |
| ep24 rectilinear IoU vs the outline raster 0.958257 / 0.952413 | confirmed [M], own rasterisation of the delivered default boxes |
| ep24 fit is the optimum of the F-I4.17.2 family | confirmed [M], exact global optimum (Dinkelbach) equals the recorded theta on both boards |
| ep24 slot w / c_L / bottom / D | confirmed [M]: 9.4012 = t + 2; 3.972 / 1.358; 6.383 / -4.436; 67.550 / 54.562 mm |
| ep24 slot on the partner's tracked mid plane at f246 | confirmed [M]: 0.09 mm (board 1), 0.34 mm (board 2) |
| ep24 seen-empty share of the body (FREE) 5.9 % / 2.2 % | confirmed [M] (6.0 % / 2.2 % in the slotted union) |
| ep24 keep-out per hull 0.0 cm3 | as the gate defines it, yes (by construction); seen-empty inside hulls is up to 6.1 cm3 (N4) |
| ep24 wood cut by the slot | 96.5 % / 65.6 % of the removed volume lies in OBSERVED voxels, 1.5 % / 0 % in FREE (N7) |
| ep24 P3 (0.074 cm / 0.68 deg; default 0.849 cm / 104 deg) | confirmed [M] on 16 copies; copy 0 = 0.060 cm / 0.77 deg |
| ep24 part 1: 124 / 112 / 32 rows, ratio 3.875, no overflow | confirmed [M] exactly with my own XML at the same convention; robust under 6 variants (N2) |
| "almost all contacts are board-table, the boards settle on their edges" | confirmed [M]: 28 board-table + 0-3 board-board; both boards on edge within 0.2 deg |
| w10 cells: 5 / 3 boxes, \|w - (t + 2)\| <= 0.33 mm, raster IoU 0.972-0.996 (keep-out 0.0 by construction, N4) | confirmed [M] on k2, k4, k5, k6 (rebuilt): exact cuboids, raster IoU = record, \|w - (t_true + 2)\| <= 0.26 mm |
| w10 low-piece body matches the plate | **no**: IoU vs the true plate 0.85-0.93, area +8 to +18 % (N1) |
| w10 k5 P2-P7 (P3 0.031 cm / 0.14 deg) and part 1 (ratio 1.75) | confirmed [M]: P3 0.031 / 0.139; part 1 1.58-1.92 over 4 draws / implementations, all <= 2.0 |
| w10 part-1 ratios of the other cells | reproduced within one contact; k2 2.08 -> 2.00, k6 2.00 -> 2.08 (N5) |
| gate validity: part 1 flags the round-2 prisms (P125) | confirmed [M]: S1 860 rows, 3 / 16 copies over 512 (record 868, 3 / 16); S2 numbers depend on a convention (N6) |
| part 2 cannot run here | confirmed [M]: `warp`, `newton`, `mujoco_warp`, `flash_chord` not importable in the venv |

## What I ran

All runs were `GMG_MODE=dev`, nice 10, on this container. The load was 6-14 from other agents' jobs. My dev run is
`<scratch>/gmg/runs-dev/20261031-vslot31-7cbe443`. Scripts are in `<scratch>/vslot31/scripts/`, outputs in
`<scratch>/vslot31/out/` (sha256 prefixes in brackets, launch times in `*.launch`). No rental, $0. GT-free: only
our clean bundle, our picks, our tracks and the committed r0 files. For w10, "truth" means the synthetic fixture's
own plate (`iplate10`, `footprint10`, `R_B`), which is not ground truth of any episode.

| Script | What it does | Output |
| --- | --- | --- |
| `vlib.py` | own helpers: cuboid recovery, raster union, exact family optimum (Dinkelbach; given (w0, w1, e) the end's lower and upper parts separate), state shares, exact trimesh inertia, own count XML (sim=rl options, `<size njmax 512 nconmax 256>`) and counter | - |
| `v_ep24_geo.py` | delivered and default OBJ boxes vs manifest, raster IoU, family optimum, slot, FREE / OBSERVED shares, per-hull FREE, static overlap at assembled frames (0.7 mm grid), cross-lap alignment (218 s) | `ep24_geo.json` [cc200e23] |
| `v_ep24_gate2.py` | part 1 with my XML, bodies at their object poses (the build's convention); variants: box geoms, multiccd off, jitter seed 11, partition B, no board-board collision; final orientations | `ep24_gate2.json` [766c0282] |
| `v_ep24_gate.py` | the same, bodies at the world origin (my first version) | `ep24_gate.json` [1d725b4c] (v1 with a partition-B tolerance bug: `ep24_gate_v1.json`, superseded) |
| `v_ep24_p3.py` | P3 replay, own XML / inertia / drive, 16 copies (seed 0) incl. copy 0 | `ep24_p3.json` [59bced5d] |
| `v_ep24_valid.py` | gate validity on the round-2 r0 prisms (world-origin bodies); control initial overlap | `ep24_valid.json` [abf4a65a] |
| `v_inertia_sens.py`, `v_frame_sens.py` | why my S2 validity counts differed: the build's counter in my process; my XML with the build's sampled inertia; body frame and plane axes swapped | `inertia_sens.json` [fc5dcf7e], `frame_sens.json` [8c3b117c] |
| `v_w10.py` | w10 cells rebuilt (committed fixture, REV 17), then own measurement incl. truth comparison and own part-1 count | `w10_k5.json` [bb488a1a], `w10_k462.json` [03decc77], `w10_k5_j11.json` [477b6e71], `w10_k5_j21.json` [f63418d6] |
| `v_w10_p3.py` | k5 P3 replay with own code | `w10_k5_p3.json` [844744c9] |

## Findings

### N1. The low-piece body and its raster grow with edge noise; the IoU gate cannot see it [M; cause E]

I rebuilt four w10 cells with the committed fixture and code, then compared the delivered default boxes (U) with the
fixture's own plate. The true plate is 230 mm long, 125 mm at the waist and 137 mm at the 20 mm long ends, 292.3 cm2.
Each cell has two boards (A / B).

| cell (t mm, sigma_e mm) | raster IoU (record) | IoU vs true plate | U area cm2 | length mm | waist mm | ends mm | end length mm | D_A + D_B mm (true crossing 125) | FREE in pieces | max FREE per hull cm3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| k4 (8, 1) | 0.983 / 0.983 | **0.928 / 0.926** | 315.1 / 315.6 | 238 / 238 | 130 / 130 | 140-142 | 26 | 133.0 | 4.8 / 5.0 % | 5.7 / 5.7 |
| k5 (8, 2) | 0.980 / 0.972 | **0.874 / 0.874** | 334.5 / 334.4 | 242 / 244 | 136 / 134 | 144-146 | 30-32 | 137.4 | 10.4 / 10.4 % | 9.2 / 10.7 |
| k6 (8, 3) | 0.982 / 0.986 | **0.851 / 0.851** | 343.6 / 343.6 | 244 / 244 | 138 / 138 | 148-150 | 30-32 | 141.4 | 12.7 / 12.8 % | 12.5 / 10.5 |
| k2 (6, 2) | 0.972 / 0.975 | **0.875 / 0.885** | 334.1 / 330.3 | 242 / 242 | 136 / 134 | 144-146 | 26-30 | 137.2 | 17.3 / 18.6 % | 10.3 / 10.6 |

What holds:
- The frame is centred on the true plate within 1 mm.
- The slot centre lies within 0.04-0.56 mm of the true crossing at t 8, and within 1.4 mm at t 6.
- The slot width is the all-point t + 2 mm, with t 0.1-0.3 mm under the true value.

What does not:
- U contains the true plate (IoU = true area / U area in every cell) and adds 1.5-4 mm per side at sigma_e 1,
  3.5-7 mm at sigma_e 2 and 5.5-7 mm at sigma_e 3 (over length, waist and ends). The slots therefore come out 8-16 mm
  deeper in total than the true crossing.
- In the fixture, FREE means outside the true mesh. So 11.8-36 cm3 of each delivered body lies outside the plate.

Cause [E]: the outline raster counts a 2 mm cell when at least 3 distinct frames of 100 put a point in it, and then
applies a 3 x 3 closing. With sigma_e of 1-3 mm per frame, cells several sigma beyond the true edge collect three
frames. U is fitted to that grown raster, so the raster IoU stays at 0.97-0.99. This also explains P128's "IoU rises
with sigma_e" clause failing: the raster and U grow together.

Consequence: F-I4.17.3 (b) holds as written, because it gates the raster IoU, CARVE, the keep-out and the width. It
does not test shape. Against the true plate, IoU falls below the 0.90 gate value at sigma_e >= 2 mm.

[H] ep24 has the same growth. Its boards show sigma 1-2 mm per frame, and its outline uses more frames (178) than w10
(100). Indications:
- Board 1's FREE share in U is 6.0 % [M]. That lies between w10 sigma_e 1 (4.8-5.0 %) and sigma_e 2 (10.4 %). The
  voxel grids differ, so this is only an indication [E].
- verify_slot2_1 N3 found the round-2 polygon 2-4 mm oversize.

Falsifier: a w10 cell with ep24's frame count and per-frame sigma whose U has IoU >= 0.95 against the true plate. A
GT-free check on ep24 is the per-frame median edge position against U's edges.

Not a defect of the build: the gate, the raster rule and the fixture are pre-registered. It belongs in the next
decision before any re-freeze.

### N2. Part 1 on ep24 reproduces exactly and fails robustly [M]

My own XML has the sim=rl options: dt 0.01 s, Newton, pyramidal, implicitfast, 100 / 50 iterations, impratio 20, and
`<size njmax="512" nconmax="256"/>`. Inertia is exact (trimesh), at 0.3 kg. Bodies sit at their object poses. The
jitter draws are the build's (`jitters(16, seed=1)`), at S1 = f246 and S2 = f218.

The table gives max nefc / max ncon over S1 and S2 and both scenes' 32 copies, with the ratio to the control of the
same variant. No copy overflowed in any variant (max 160 rows, 40 contacts).

| variant | delivered | default | control | ratio |
| --- | --- | --- | --- | --- |
| mesh geoms, multiccd on (= the gate) | **124 / 31** | 112 / 28 | 32 / 8 | **3.875** (record 3.875) |
| native box geoms | 120 / 30 | 120 / 30 | 32 / 8 | 3.75 |
| multiccd off | 120 / 30 | - | 32 / 8 | 3.75 |
| jitter seed 11 | 120 / 30 | - | 32 / 8 | 3.75 |
| bodies at the world origin (v1): gate / J11 / multiccd off | 120 / 140 / 124 | 112 | 32 / 32 / 24 | 3.75 / 4.375 / 5.17 |

Where the contacts come from:
- At the max-nefc step the delivered contacts are 28 board-table and 0-3 board-board. Default: 14-20 board-table
  and 8 board-board. Control: 8 board-table and 0 board-board.
- After 2 s both delivered boards stand on an edge: a_T is perpendicular to the table normal and a_W parallel to it,
  within 0.2 deg.
- Board 1 rests on its v = +66.8 mm edge. All five A-direction strips share that edge, so it makes 5 x 4 = 20
  contacts. Board 2 rests on its two end boxes (v = -67.0 mm), 8 contacts. 20 + 8 = 28 [M for the counts, E for
  the reading].
- The lowest delivered vertex starts 21.7 mm above the table. The I.md phrase "the pair starts 16.7 mm above our
  table" is the rigid lowering computed over all sets. The control box's lowest vertex is at 17.7 mm. This is a
  wording nit.

### N3. The control is two separated flat boxes; the box partition sets the ratio [M; reading E]

The control:
- The two one-box controls start with 7.70 cm3 (S1) and 7.78 cm3 (S2) of mutual overlap at the cross.
- MuJoCo pushes them apart. In copy 0 of both scenes both boxes end lying flat (a_T parallel to the table normal),
  with 0 board-board contacts at the max step. The build's own per-copy classes show the same.
- With board-board collision switched off, the control boxes stay on edge, and the count is still 32. So the
  denominator 32 is stable: it is two boxes at 4 table contacts each. But it is not "a plain board" in the assembled
  scene, which the decision's wording suggests.
- In my world-origin variant, most S1 control copies were thrown kilometres away (median max 16 rows). That was an
  artifact of my body frame, gone at the build's convention, where the median is 32. I mention it so that nobody
  reuses that variant.

Partition diagnostics (not rules):

| variant | rows | ratio |
| --- | --- | --- |
| partition B on board 1 only (5 boxes, the tie that rule A won) | 72 | 2.25 |
| partition B on both boards (board 2 then has 7 boxes) | 64 | 2.00 |
| partition B on both, world-origin bodies | 80 | 2.5 |

With partition B, board 1's resting edge is one box: 12 board-table contacts instead of 28.

[E] Under the 2.0 x one-box ratio, a pair standing on edge passes only if about two boxes per board touch the table
and the slot contacts stay few. On ep24 that depends on the partition direction and on chaos at the limit. Changing
the partition now would be tuning on a freeze input: a new dated decision is needed (the build said so).

### N4. Keep-out per hull is 0.0 by construction; the seen-empty space inside the hulls is not [M]

`keepout_gate` takes the keep-out points outside the union of the slotted pieces (`ins`). For pieces that tile the
body exactly, no keep-out point can lie inside any hull. F-I4.15.4 states this.

Measured directly on a 2 mm grid against each object's voxel states:

| | FREE inside each delivered hull, cm3 | hulls > 0.3 cm3 |
| --- | --- | --- |
| ep24 board 1 | 6.11 (left end, 17 % of that box), 3.18, 0.13 (under-slot), 2.70, 2.22 | |
| ep24 board 2 | 1.14, 0.03, 0.00, 0.10, 3.76 | |
| ep24 total | | 6 of 10 |
| w10 k5 | | 10 of 10 (largest 10.7) |
| w10 k6 | | 10 of 10 (largest 12.5) |

The F-I4.17.3 (b) criterion "keep-out <= 0.3 cm3 per hull" is therefore always met by box pieces and decides nothing.
verify_slot2_1 N3 made the same point for the prisms. Report: non-blocking, but the freeze summary should not count
it as evidence.

### N5. The w10 ratio margin is under one contact [M]

My own count on the rebuilt cells (J1 draws), mine against the record:

| cell | delivered / control | ratio | record |
| --- | --- | --- | --- |
| k2 | 96 / 48 | 2.00 | 100 / 48 = 2.08 |
| k4 | 72 / 48 | 1.50 | 1.50 |
| k5 | 80 / 48 | 1.67 | 84 / 48 = 1.75 |
| k6 | 100 / 48 | 2.08 | 96 / 48 = 2.00 |

- Two other jitter draws on k5 give 92 / 48 = 1.92 (seed 11) and 76 / 48 = 1.58 (seed 21).
- No overflow anywhere.
- The freeze cell k5 passes in all four draws or implementations (1.58-1.92). Cells k2 and k6 swap sides of the
  limit, with a difference of one contact.
- In the synthetic scene the host's object frame is the world frame and the guest's origin sits at the crossing.
  So my w10 bodies are effectively at their object poses, and the remaining difference is inertia (exact against
  sampled at 1.5 mm).

### N6. Gate validity (P125) holds; its S2 counts depend on the free-joint frame placement [M]

Round-2 prisms, 16 copies per scene:

| run | S1 rows | S1 copies > 512 | S2 rows | S2 copies > 512 |
| --- | --- | --- | --- | --- |
| build record | 868 | 3 | 512 | 0 |
| mine, build's convention (bodies at object poses) | 860 | 3 | 440 | 0 |
| mine, bodies at the world origin | 860 | 4 | 1524 (381 contacts) | 8 |

- At the world origin, the round-2 default prisms also give 676 rows with 10 / 16 copies over the limit at S2. The
  record has 432 and none.
- The build's own counter run in my process returns the record exactly (S2 512, same per-copy values).
- My XML with the build's sampled inertia but world-origin bodies returns 1520 rows with 9 copies over the limit.
- The plane's in-plane axes have no effect.

So the cause is the body frame lying about 0.5 m from the centre of mass, not inertia. [E] This is plausibly the
implicitfast step coupling rotation into the origin's velocity at dt 0.01 s during deep depenetration.

For the box pieces the convention does not matter (120-124 rows). P125 holds either way, and more strongly at the
world origin. The build's convention, each body at its object pose, is the natural reading of loading each object
with its own frame. I did not check FlashCHORD's loader.

### N7. The slot removes wood that our own evidence saw [M]

On ep24:
- The removed slot volume (default minus slotted) is 4.700 / 3.796 cm3, exact from the boxes. P4's sampled values
  are 5.03 / 3.85, both under the 1.5 x limit.
- That volume lies 96.5 % / 65.6 % in OBSERVED voxels, 1.5 % / 0 % in FREE and 2.1 % / 34.4 % in UNKNOWN.
- The outline raster has no notch at either slot: 169 of 170 and 135 of 135 removed raster cells are in the raster.

This is the owner's waiver at work: the slot comes from the partner intrusion, not from seen-empty space. It matches
board 2's `slot_centre_disagrees` (delta -5.0 mm, report only, not re-measured here). Report only.

### N8. Physics numbers re-run [M]

ep24 P3 with my own XML, exact inertia and drive loop, 16 copies (seed 0):

| set | copy 0 | 16 copies | record |
| --- | --- | --- | --- |
| carved | 0.060 cm / 0.77 deg, after-max 0.30 cm | 0.0741 cm (sd 0.0237) / 0.678 deg / 0.315 cm | 0.074 / 0.024 / 0.68 / 0.315 |
| default | | 0.851 cm / 105.3 deg | 0.849 / 104.18 |
| no-collide | | 0.032 cm / 0.094 deg | 0.032 / 0.09 |

- Replay row counts: carved 50, default 94, as recorded.
- Static overlap of the delivered pieces at 9 assembled frames is 0.0-0.64 cm3, median 0.054. P6 records a median of
  0.039 over all 29. The largest value is at f218 (S2).
- Exact body volumes: 225.29 / 213.81 cm3 (default), 220.59 / 210.01 cm3 (slotted).

w10 k5 P3 (same code): carved copy 0 is 0.029 cm / 0.13 deg. Over 16 copies it is 0.031 cm / 0.139 deg, after-max
0.052 cm (record 0.031 / 0.14 / 0.052). Default: 1.170 cm / 104.4 deg (record 1.174 / 103.55).

P2 travel, P4 and P7 were read, not re-implemented.

## Not done

- W_x (120.52 mm) was not recomputed. D_A + D_B = 122.11 mm is confirmed, and the 1.59 mm difference sits well
  inside the 10 mm window.
- ep24 board 2's slot-centre report was not re-measured.
- ep23, w10p, w10n, w7, w8 and w8b were not re-measured.
- Part 2 was not run (see the verdict table).

## Integrity

- No scan, mocap, parquet pose, `*_align`, library mesh or eval file was read.
- The w10 "truth" is the synthetic fixture's own plate.
- Nothing in the repository was changed except this file.
- No threshold or rule is proposed as adopted. The partition-B and no-board-board runs are diagnostics.
- Machine: this container only, $0.
