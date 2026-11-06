# verify_slot2_1: board slot round 2 (F-I4.15 outline body), public ep24 fi4o and ep23, geometry and physics lens

Verifier, 31 Oct 2026, 20:30-21:05 UTC. I did not build this; the job was to find what is wrong with it. Scope: the
round-2 Build + public runs (build commit 19c4309, record 3fbd467), T-I11 `fi4o` (results
`build/I/results/slot2-ep24/fi4o/`, run `<scratch>/gmg/runs-dev/20261031-i2probe-626ce13`, clean bundle
`20261031-b4ext4-b61e8aa`) and the ep23 body check (`results/slot2-ep23/`). Labels: [M] measured, [E] estimate,
[H] hypothesis. "Looked at" = RGB frames inspected, not measured.

## Answer in plain words

**The delivered ep24 pieces are what the record says, and the physics reproduces.** I re-measured the delivered
piece files (not the in-memory hulls):
- They are exact right prisms at t = 7.401 mm that tile the polygon with no gap, overlap or overhang.
- The slot gap in them has the rule's width, centre and depth.
- At our tracks' assembled pose, each board's material sits in the other board's slot, on the correct edge.
- Re-running the P3 replay on the delivered files gives 0.079 cm / 0.74 deg (reported 0.078 cm / 0.74 deg).
- One fresh jittered copy gives 0.060 cm / 0.33 deg.

**Board 1's slot sits on the real slot, but board 2's is about 3.5 mm off it.** Our own RGB frames and our points show
the real slot. On board 1 the analytic slot lies on it (looked at, four frames). On board 2 it is shifted about 3-4 mm
along a_L [M + looked at]. It covers roughly two thirds of the real gap plus about 4.5 mm of real wood. The cause is
the tracked relative pose at assembly, not the shape: board 1's own observed face lands about 3.7 mm inside board 2's
wood. F-I4.12 centres the slot on the tracked partner, so the replay on our tracks is consistent and P3 passes. With
any pose closer to the true assembly (a different P_sim, eval 25) board 2's slot is off by more than its 1 mm
clearance. This is not a rule violation. It corrects the build's statement that "the red slot box sits on the slot
visible in our frames" (true for board 1 only), and it is a risk for P1.

No blocking item.

## Verdict

| Item | Status |
| --- | --- |
| Pieces = exact convex right prisms tiling the polygon (slotted and default), volumes, counts | confirmed [M] |
| Slot width / centre / depth in the delivered pieces vs the rule | confirmed [M] (0.25 mm raster) |
| Outline vs observed points: no observed material outside the body | confirmed [M] |
| Outline vs seen-empty space | body about 2-4 mm oversize along its edges; 10 of 134 hulls hold > 0.3 cm3 FREE inside (the gate cannot see this, by design) [M] (N3) |
| Correct board and edge; entry direction | confirmed [M] |
| Board 1 slot on the real slot | confirmed (looked at) |
| Board 2 slot on the real slot | **about 3.5 mm off** [M + looked at] (N1) |
| Board 2 D = 66.56 mm "from the polygon edge" | measured from a run-frame spike at the slot mouth; the edge there is at -59..-63 mm (N2) |
| Keep-out per hull 0.0 cm3 | confirmed as the gate defines it (tautological for an exact tiling, as F-I4.15.4 states); physical re-measure in N3 |
| P2-P7 numbers in the logs; P3 re-run on the delivered files | confirmed [M]; per-frame overlap caveat in N4 |
| PNGs | board 1 right; board 2 slot offset visible (N1); board 2 polygon spike visible |
| ep23: board 1 over the cap, not frozen | confirmed [M]; the outline is also partial (N6) |

## What I ran (GT-free)

Scripts are in `<scratch>/verify_slot2_1/`. Outputs are in `out/` (sha256 prefixes in brackets). All runs were
`GMG_MODE=dev`, nice 5, on this container (load 9-20). Cost: $0.

| Script | What it does | Output |
| --- | --- | --- |
| `vpieces.py` | delivered `r0/<obj>/piece_*.obj` and `r0/_default/<obj>/` against `decisions.json`; pair overlaps at the mean assembled pose; entry side (1317 s) | `vpieces.json` [803a2252] |
| `vobs.py` | near points (the driver's `_near_points` with our `shell_t5p36` picks) vs polygon; FREE / UNKNOWN per hull (1 mm samples, 4 mm state grid); partner occupancy per hull (driver rule: build frames, nmin 8); density across the slot band | `vobs.log` [8976c84a] (the figure step failed: no matplotlib; numbers are in the log) |
| `vobs2.py` | board-2 spike frames, below-face profile, partner-occupancy location, figure `vobs_outline.png` | `vobs2.json` [fdb66e0e] |
| `vphys.py` | P3 replay on the delivered files: the 16 seed-0 copies, plus one fresh copy (seed 7) for slotted and default | `vphys.json` [582ba678] |
| `vovl.py` | static overlap of the delivered slotted pieces at all 29 assembled frames: the build's 200k estimator and a 0.25 mm grid near the crossing | `vovl.json` [7e90ca5b] |
| `vcross.py` | board 1's observed points at assembled frames, mapped into board 2's slot band | `vcross.json` [18c2990e] |
| `vzoom.py` | zoomed cam_a crops with the footprint edges, the centre line and test lines (looked at) | `vzoom*_<obj>.png` |

Inputs: our clean bundle (owned points, cameras, frames, tracks `data/sweep/ep24/poses.npz`, 4 mm state grids), our
picks (for the 6 mm filter only), our cam_a video, and the committed fi4o `decisions.json` and `r0` files. No scan,
mocap, parquet `pose`, `*_align`, library mesh or `meshes/carve/ev25` was read.

## Confirmed [M]

- **C1. Delivered pieces.** Counts: 57 / 77 slotted and 50 / 71 default; every file is a watertight convex volume.
  - Right prisms: |w| = t/2 to 5e-6 mm; top and bottom faces agree to 1e-5 mm; 6-10 vertices each.
  - On a 0.25 mm raster:
    - default unions 297.953 / 287.160 cm2 against polygons 297.96 / 287.16 cm2;
    - overlap between pieces <= 0.0006 cm2; nothing outside the polygon;
    - slotted pieces cover nothing inside the footprint;
    - polygon left uncovered 6.379 / 5.501 cm2 against footprint ∩ polygon 6.373 / 5.501 cm2.
  - Exact hull volumes: 220.525 / 212.532 cm3 default, 215.853 / 208.385 cm3 slotted, so 4.672 / 4.147 cm3 removed.
    This equals the record's body and slot volumes. P4's 226.9 / 222.36 cm3 for board 1 are Monte Carlo values about
    3 % high; harmless, the kept share is 0.98 either way.
- **C2. Slot in the delivered pieces vs the rule** (gap rows on the 0.25 mm raster):

  | Board | Width (rule) | Centre (rule c_L) | Entry edge (rule u_e) | Bottom (rule) | Depth (rule D) |
  | --- | --- | --- | --- | --- | --- |
  | 1 | 9.5 mm (9.4) | 4.02 mm (3.97) | -61.04 mm (-61.17) | 6.33 mm (6.38) | 67.38 mm (67.55) |
  | 2 | 9.25 mm (9.4) | 1.32 mm (1.36) | -70.87 mm (-71.0) | -4.50 mm (-4.44) | 66.38 mm (66.56) |

  All agree within the raster pitch. Board 2's narrow rows at the mouth come from the spike (N2).
- **C3. Outline vs observed points (no wood left out).**
  - Board 1: 0.01 % of 1.75 M slab points lie outside the polygon, none more than 2.6 mm out. 49 of 7,428 >=3-frame
    2 mm cells lie outside, all within 0.76 mm.
  - Board 2: 0.03 % of 1.31 M slab points outside, at most 2.9 mm. 74 of 7,138 cells, all within 0.64 mm (the 1 mm
    Douglas-Peucker tolerance).
- **C4. Correct board and edge** (our tracks, mean assembled pose, delivered files).
  - Unslotted board 1 vs slotted board 2: 3.589 cm3 of overlap, 99.96 % of it inside board 1's footprint.
  - Slotted board 1 vs unslotted board 2: 3.196 cm3, 99.95 % inside board 2's footprint.
  - Slotted vs slotted: 0.002 cm3. Unslotted vs unslotted: 6.82 cm3 (P2 reports 6.84).
  - Entry: the partner's centre approaches each board from the -v (mouth) side, s_e = -1. In board 1's frame it moves
    from v = -117.5 to -65.5 mm over f164-182; in board 2's frame from -117.9 to -65.7 mm.
  - Both boards carry their I-shape recess on the slot edge (figure `vobs_outline.png`), as one stock would.
- **C5. Physics.** P3 on the delivered files (host board 1, frames 124-274, assembled 218-274):
  - 16 seed-0 copies: mean of the per-copy medians 0.079 cm / 0.74 deg; mean max after the first assembled frame
    0.347 cm; 0 NaN. Worst copy: median 0.162 cm, max after 0.478 cm, 2.25 deg.
  - Fresh copy (seed 7): slotted 0.060 cm / 0.33 deg (max 0.344 cm); default 0.752 cm / 110.3 deg (max 9.19 cm).
  - The build's 200k overlap estimator reproduces the logged P6 series exactly (f218 0.462 ... f222 0.899 cm3).
  - P2, P4, P5, P6, P7 values in `physics_*.json` match `summary_fi415.json` and the acceptance block.
- **C6. Board 1 slot vs the real slot (looked at).** In f80, f96, f106, f110, f124, f130, f140 and f150, the dark gap
  of the real slot lies between the lines u = c_L +- 3.7 mm and is centred on c_L = 3.97 mm, from the mouth to about
  the analytic bottom (`vzoom_wooden_piece_1.png`, `vzoomb_wooden_piece_1.png`).
- **C7. ep23** (`ep23_fi415.json`, PNGs):
  - board 1: one-face plate, 140-vertex polygon, 85 default prisms > 82, `plate_body_over_cap`, so freeze (b) fails;
  - board 2: 56 prisms, reported only. Its plane pair is 10.69 mm, with other pairs at 7.47 / 9.08 mm in the record.
  - Not frozen and not run on eval 25: correct.

## Findings

### N1 (non-blocking, the main one): board 2's slot is about 3.5 mm off the real slot, because the tracked pose at assembly is

- **Below-face points [M]** (`vobs2`). Board 2 lies face-up on the table before the run. In frames < 164 and the slot's
  depth range, 428 slab points lie below the seen face (w -3.4..-0.2 mm), and almost all of them sit at u = -6.6..+2.4
  mm (peak -4.1 mm, half-peak -5.6..-1.6 mm). These are points seen into the real slot. The face density dips over
  the same range (785-900 against about 920-1100 per mm on the flanks).
  - So the real slot spans about u = -6..+1.5 mm, centred near -2 mm [E +-1 mm].
  - The analytic footprint spans -3.34..+6.06 mm (c_L 1.36 mm).
- **RGB [looked at]** (`vzoomb_wooden_piece_2.png`, f100-f118). The dark gap fills the -u half of the red band and
  runs past its -u line. The +u half of the band lies on unbroken wood.
- **Why [M, thin: 67 points].** At the assembled frames, board 1's observed face points (w1 median -3.61 mm, on its
  body face) map into board 2's slot band at u2 = 4.1..6.2 mm (median 5.2 mm). That puts board 1's mid plane at about
  u2 = 1.5 mm, which is where F-I4.12 put c_L. But that face lies about 3.7 mm beyond the real slot's +u wall: inside
  board 2's wood, which cannot happen. So our relative pose at assembly is off by about 3.5 mm along board 2's a_L.
  - [H] Either board 1's mid plane is offset along its normal (its two faces are seen in disjoint phases,
    verify_slot_1 B2) or board 2's track is off at assembly.
  - Falsifier: board 1's mid plane mapped into board 2's frame at the assembled frames, recomputed from points seen
    on both faces in the same frames, lands at u2 = -2 +- 1 mm.
- **Consequences.**
  - With P_sim = our tracks (the r0 manifest's `sim_pose_fallback`), the slot is where the replayed partner is: P2-P7
    pass, consistent.
  - With a pose source closer to the true assembly, board 2's slot is off by about 3.5 mm against 1 mm clearance. The
    partner would meet about 2.5 mm of wood along the slot. This bears on P1 (the Embodiment's `jitter_check --k 16`
    uses its own scene poses) and on the P_sel to P_sim check for eval 25 (INTERLOCK 20.9 open item 3).
  - Board 1's real slot coincides with its analytic slot (C6), so the error does not show there.
- **Record correction.** The build summary's "the red slot box sits on the slot visible in our frames" holds for
  board 1, not for board 2.
- **For the next F entry [H].** On a one-face board lying on the table, the real slot is measurable without ground
  truth from below-face points. A slot-centre consistency check (analytic c_L vs the observed notch, where one is
  observable) would have caught this. Name it before any eval-25 run.

### N2 (non-blocking): board 2's slot mouth edge is a run-frame spike; D2 = 66.56 mm is measured from it

- Board 2's polygon reaches v = -71.0 mm at the slot mouth only through a 2-4 mm wide spike, vertices (2.44, -63),
  (4.44, -71), (6.44, -71), (6.44, -67).
- Beside the spike, the slot edge runs at v = -59..-63 mm (vertices 19-38; figure `vobs_outline.png`): the same
  waist recess as board 1.
- The spike is supported by 96 points from 22 frames, only 4 of them before the run (39 points). 7 frames are
  approach frames (164-216) and 11 are assembled frames [M]. [H] Board 1 material near board 2's mouth,
  owned by board 2. Falsifier: the spike cells keep >= 3 pre-run frames when the run frames are dropped.
- Effects:
  - u_e = -71.0, "entry edge shift 0.0" and D2 = 66.56 mm come from the spike. From the board's edge, D2 would be
    about 55-59 mm [E]. W_x is likely inflated the same way, since the spike lies where board 1 sits at assembly. The
    10 mm window decision is unlikely to change [E].
  - The spike lies mostly inside the footprint, so the slot removes it from the slotted pieces. Its remnant
    (u 6.06-6.44) is a 0.38 mm x 4 mm sliver prism, the thinnest delivered piece (0.39 mm).
- Rule fragility: F-I4.15.3 takes u_e as the outermost polygon coordinate in the band, so one spike sets D.

### N3 (non-blocking; record precision): the body is 2-4 mm oversize along its edges; 10 hulls hold > 0.3 cm3 of seen-empty space

FREE (seen-empty) volume inside the delivered slotted hulls (1 mm samples on the 4 mm grid) [M]:

| Board | FREE total | Hulls with > 0.3 cm3 FREE | Max per hull | FREE within 2 mm / 4 mm / 8.5 mm of the polygon edge |
| --- | --- | --- | --- | --- |
| 1 | 8.11 cm3 (3.7 %) | 8 of 57 | 0.745 cm3 | 61 % / 88.5 % / 100 % |
| 2 | 3.99 cm3 (1.9 %) | 2 of 77 | 0.474 cm3 | 68 % / 89 % / 99 % |

- Board 2 is also 53 % UNKNOWN: its unseen half, as expected for a one-face board.
- So the seen-empty space is the known raster growth band (F-I4.15.2 known limit), not misplaced material. P53 holds,
  as recorded.
- "Keep-out per piece 0.0 cm3" is the gate's measure, which counts keep-out only outside the pieces (F-I4.15.4 says
  so). Read as FREE inside a hull, 10 of 134 hulls exceed 0.3 cm3.
- Partner occupancy inside the slotted hulls (driver rule, 4 mm voxels):
  - board 1: 6.88 cm3, of which 4.37 cm3 lies past the slot bottom, 1.57 cm3 beside the walls and 0.94 cm3 elsewhere;
  - board 2: 9.77 cm3, of which 6.64 cm3 lies past the bottom and 3.12 cm3 beside the walls.
  - The part past the bottom is the partner's own real slot, observed as filled. With sigma 3 mm (board 1) and
    table / stereo fill, the real slots do not show as gaps in the owned points (`vobs.log` density profiles), so
    the partner's 4 mm occupancy covers them.
  - This is why only a tautological gate can pass here. Not a defect of this slot.

### N4 (non-blocking): the overlap clause is a median that hides 0.3-1.0 cm3 over the first third of the assembled frames

- Static overlap of the delivered slotted pieces at the 29 assembled frames [M]:
  - build estimator: median 0.04 cm3, max 0.899 cm3 (f222), 5 frames over 0.5 cm3;
  - 0.25 mm grid at the crossing: median 0.087 cm3, max 1.044 cm3 (f222; f220 1.029), 8 frames over 0.5 cm3 and
    2 over 1.0 cm3.
- Frames 218-234 and 238 carry 0.40-1.04 cm3 (fine grid), mostly beside the slot walls, up to 4.7 mm into a wall.
  Over f218-236 the partner normal is 2.2-3.1 deg off a_L. This is verify_slot_1 B3's prediction (1 mm clearance tolerates about 1.5-1.9 deg).
- P3 as implemented judges the median (0.04 cm3), so it passes as pre-registered. A per-frame reading of "< 1.0 cm3 at
  the assembled frames" would fail on 2 frames under the fine estimate and pass narrowly under the build's.
- The dynamic replay absorbs it (C5).

### N5 (non-blocking, [H]): many sliver prisms

- Slotted pieces narrower than 2 mm: board 1 21 of 57 (narrowest 1.41 mm), board 2 27 of 77 (narrowest 0.39 mm). The
  largest length / width ratio is 172; the smallest piece is 0.02 cm2. Default pieces: 19 of 50 and 23 of 71 under
  2 mm.
- They come from ear clipping plus Hertel-Mehlhorn fans over one-cell raster steps.
- [H] Thin hulls can make contact noisy in MuJoCo settles. The plain-MuJoCo P1 pre-check fails for slotted and
  default alike, so it does not separate the effect. Falsifier: the Embodiment's P1 on r0 passes, or a merged-sliver
  variant settles no better.

### N6 (non-blocking, for the next decision): ep23 board 1 is a partial outline, not only a cap miss

- The ep23 PNG and the record show that the polygon misses the part of the board under the hand, plus a hook around a
  marker ball [looked at].
- Measured: 206 cm2 against 287-298 cm2 for the ep24 boards of the same stock; rectangle fill 0.742; "waist 108 /
  ends 74 mm".
- A coarser tolerance or rectilinear fit (the build's [H]) could bring it under 82 prisms. It would still build a
  body that omits roughly 30 % of the board [E], and P57's I-shape part would still fail.
- So ep23 board 1 tests outline coverage as much as the prism cap; the next dated entry should say which it targets.

### N7 (non-blocking, provenance)

- `report.json` `launch_code` is taken after the bundle and silhouette stage, not at launch (`interlock_dev.py`
  line 143). Its commit field reads 3484d8d, committed 18:41:24, three minutes after the 18:38:27 launch, and its
  `collcarve.py` hash is the 3484d8d file (19c4309's differs).
  - The platebody / interlock / simphys / simpieces / driver hashes do equal 19c4309's.
  - `collcarve` is not on the F-I4 path.
  - So the build's "code that ran = 19c4309" stands for every file that matters, but the field is not a true launch
    record.
- The F-I4.15 `platebody.py` was first committed by the other agents' WIP snapshots 8f72399 / caefcb4 (18:28:56 /
  18:29:11), after F-I4.15 (f62454a, 18:14:55). The build log names 6ed88f1, which carried only `test_fi415.py`.
  The content is identical to 19c4309.

## Not done

- No P1 (FlashCHORD scene not here).
- No new rule and no eval data.
- Nothing in the build was changed.
