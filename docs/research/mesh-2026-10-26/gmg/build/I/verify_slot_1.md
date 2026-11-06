# verify_slot_1: board slot under the owner's waiver (F-I4 / F-I4.14), public ep24, geometry and physics lens

Verifier, 31 Oct 2026, 17:41-17:55 UTC. I did not build this; the job was to find what is wrong with it. Scope: T-I11
runs `fi4evalsem` (code cd2383f) and `fi4b` (code 9ad1af9), results in `build/I/results/slot-ep24/`, run
`<scratch>/gmg/runs-dev/20261031-i2probe-626ce13`, clean bundle `20261031-b4ext4-b61e8aa`. Labels: [M] measured,
[E] estimate, [H] hypothesis.

## Answer to the owner: did we get the notch?

**No.** I confirm that no slot exists on either ep24 board in either run. No slotted piece, body file or physics result
was produced under F-I4. The one simulator folder that was written (`sim/public/ep24-fi4b/r0`) holds the old default
pieces and is marked do-not-use.

The builder's account of *why* it failed is only half right:
- **Right:** the F-I4.2 rectangle test failed on both boards.
- **Wrong:** the guessed cause (marker balls or bumps at the board ends) and the suggested next step (a rectangle that
  ignores the end flares).

**The boards are not rectangles. They are I-shaped: the ends are wider than the middle.** Both our own camera frames
and our own points show this [M]. So the rectangle gate was right to fail. A rectangle at the full end width would
also have failed the keep-out gate, because about 10 % of its volume is space our cameras saw as empty. A rectangle
at the waist width would cut off real wood at the ends. The next design needs a body that follows the outline
(details in B1 below).

## Verdict

| Item | Status |
| --- | --- |
| No notch, both boards PUSH, r0 = default pieces (do-not-use) | confirmed [M] |
| Plate-test, fill, gate and timing numbers in the build result | confirmed [M], reproduced from the same code and inputs |
| Cause of the F-I4.2 failure ("marker balls / bumps") and the [H] fix (2-98 % rectangle) | **wrong (blocking for the next F-I4 entry)** |
| Board-1 thickness 6.21 mm "measured" | **depends on the 2 mm downsample: all-point estimates are 7.3-7.4 mm** (non-blocking for the sim, see B2) |
| Slot on the correct board and edge (crossing geometry, identity semantics) | consistent [M], with one eval-25 risk (N6) |
| Slot width / centre / depth / cross-lap sum, keep-out of slotted pieces, body watertightness, slot physics | **not measurable: nothing was built.** On purpose, I computed no counterfactual slot, gate or physics outcome on ep24 |

## What I checked and how (GT-free)

The scripts are in `<scratch>/verify_slot1/`:
- `vgeom.py`: the same `platebody.plate_info` / `resolve_one_face` on the same bundle and picks, plus all-point
  thickness, flare-point provenance and crossing angles.
- `vcross.py`: the decomposition of the crossing angles.
- `vfree.py`: the F-I4.2 "reported, not used" FREE share of the body, and the outline width profile.

Outputs are in `<scratch>/verify_slot1/out/`: `vgeom.json` (sha256 a5c233b5...), `vcross.json` (95380c7e...) and
`vfree.json` (61d3f8d9...).

Inputs: our clean bundle (owned points, cameras, frames, tracks, grid states, table plane), our shell picks, our hands
file (`in/hands24/hands.npz`, role own) and the `fi4b/decisions.json` body boxes. Reading the committed RGB check
frames is looking, not measuring. No scan, mocap, parquet pose, `*_align` or library geometry was used. Runs were
`GMG_MODE=dev`, nice 5, one at a time: 143 s, 2 s and about 20 s on this container.

## Findings

### B1 (blocking for the next step): the outline "flares" are the boards' real I-shape, not marker balls

Evidence:
1. **Images (looked at).** The committed RGB check frames show stepped, wider ends on both boards, with the long edges
   recessed between them:
   - `build/I/png/sil_ep24_b2.png`: board 2 at f26 and f102, lying on the table.
   - `build/I/png/sil_ep24_b1.png`: board 1 at f104 and f138, held in the hand.

   The four marker balls sit on the face, inside the outline. The slot is visible as a dark line under the red motion
   region, running from the waist edge to about the middle.
2. **Flare points lie in the face planes, not above them [M].** Offset from the mid plane, 5-95 %:
   - board 1: flare -5.5..+5.7 mm, core -5.3..+5.3 mm;
   - board 2 (one face seen): flare -1.0..+4.2 mm, core +1.0..+4.4 mm.

   Balls would stand 10-20 mm off the face toward the cameras. The camera-side shares are also the same as the core's
   (0.44 vs 0.41 on board 1).
3. **They are not hand points [M].** No flare point lies within 30 mm of one of our hand joints in the same frame
   (0 of about 20 k sampled points, on both boards). The median distance is 73 mm on board 1 (core 80 mm) and 195 mm
   on board 2 (core 110 mm).
4. **They are not table points [M].** No flare point lies within 3 mm of our table plane, on either board.
5. **They are seen across the whole episode [M]:** 53,418 / 23,973 points from 138 / 81 frames, at both ends of the
   long axis. The cells have fewer frames (median 13 / 16 per cell, against 86 / 70 in the core), as expected for edge
   lugs.
6. **Width profile of the outline mask [M]** (2 mm raster, includes the raster and noise growth seen in synthetic w1,
   about +8 mm overall):

   | Board | Waist (30-70 % of the length) | Ends (outer 10 %) | Lugs at least 8 mm wider than the waist |
   | --- | --- | --- | --- |
   | 1 | 130 mm | 137 mm | 22 / 6 mm long |
   | 2 | 125 mm | 136 mm | 16 / 20 mm long |

   Inside the 2-98 % box (222 x 126 / 218 x 126 mm) the mask fills **0.996 / 0.983**. The board is a clean rectangle
   between the lugs and an "I" overall.

Consequences:
- **(a) The fill gate failed correctly.** My recomputed fills (0.893 / 0.875) match the run's (0.895 / 0.868); the
  small difference comes from rasterising in the rectangle frame.
- **(b) The rectangle at the lug width would put empty space inside the body [M].** The pre-registered "reported, not
  used" quantity of F-I4.2 is the FREE share of the body (FREE = voxels our cameras saw as empty) [M]:

  | Board | FREE share of the whole body | FREE volume | FREE share of the waist side bands |
  | --- | --- | --- | --- |
  | 1 | 11.5 % | 22.9 cm3 | 83 % of 14.8 cm3 |
  | 2 | 9.9 % | 19.5 cm3 | 80 % of 19.9 cm3 |

  Those bands lie on the body surface, so the F-I3.8 keep-out gate (<= 0.3 cm3 per hull) would fail by far [E: I did
  not run the gate]. P37 ("keep-out met by construction") is true only if the body itself stays out of FREE space,
  and a rectangle cannot do that on these boards.
- **(c) The builder's [H] fix would cut off real wood.** The 2-98 % rectangle drops the measured lugs, about 5-9 mm per
  side over 16-22 mm at each end.
- **(d) Both boards have the same I-shape.** This supports the same-stock prior of F-I4.14 step 3.

[H] for whoever writes the next dated, post-hoc F-I4 entry:
- Make the body follow the outline: a rectilinear decomposition of the mask (waist box plus two lug boxes, extruded
  at t), with fill measured against that polygon. Its pieces are boxes, so the keep-out stays checkable. The slot is
  cut in the waist box.
- Falsifier: on ep24 the body's FREE share stays above about 2 %, or the keep-out gate fails, or a synthetic I-shaped
  w-case misses.
- That entry must also not be tuned on the numbers above beyond the cause.

### B2 (non-blocking; affects realism, not the sim clearance): board-1 t = 6.21 mm comes from the downsample

The step-2 estimator (`_camera_side`) runs on structure's first-point-per-2 mm-voxel downsample (36,675 points). The
same camera-side split on all 1.76 M near points reads [M]:

| Estimate | t |
| --- | --- |
| F-I4.14 step 2 (downsample, as run) | 6.21 mm |
| median per face, all points (faces +3.98 / -3.42 mm about the run's mid plane) | 7.40 mm |
| median of per-frame face medians | 7.30 mm |
| interior only (more than 15 mm from the outline edges) | 7.35 mm |
| earlier values: B7 dev / diag14 per frame | 7.4 / 7.0 mm |

So the bias is about -1.1 to -1.2 mm, larger than the 0.2-0.9 mm thin bias of synthetic w6b. Probable reason [H]: the
downsample keeps the first point per voxel, so the earliest frames dominate, and the + face drifts by up to about 2 mm
along n over frames 0-74.

**The two faces are never seen together** [M]: the + face only in frames 0-74 (38 frames), the - face only in frames
74-274 (101 frames), with 1 frame in common. So t is a cross-phase number that relies on the track being consistent
between the two phases. Per-frame face offsets spread +2.69..+4.97 mm and -4.33..-2.78 mm (5-95 %), so treat t as
about +-1 mm [E].

Effect:
- In the simulator, w = t_p + 2 mm is set against the partner's simulator body, which is built from the same t, so the
  1 mm per-side clearance holds by construction.
- Both simulator boards would be about 15 % thinner than our all-point reading.
- Board 2's prior inherits 6.21 mm.
- Prediction P40 (5-9 mm) holds either way.

The build result should say "6.21 mm on the 2 mm downsample; 7.3-7.4 mm on all points" rather than just "measured".

### B3 (non-blocking, [E]/[H]): an aligned slot with 1 mm clearance is at the limit of the replayed crossing angle

From our tracks at the 29 assembled frames, with the fi4b axes [M]:
- The partner's plate normal is 2.06 deg off board 1's a_L, and 1.51 deg off board 2's (per frame, 5-95 %: 1.3-3.0
  and 0.8-2.2 deg).
- The in-plane part of that tilt (rotation about a_T) is what sweeps the partner along a_L across the slot's depth. It
  is 1.74 deg on board 1 (per frame 0.8-2.8 deg) and 1.05 deg on board 2 (-0.2-1.7 deg).

F-I4.12 moves the slot to the partner's mid plane but keeps it parallel to a_L. A 1 mm per-side clearance over a
60-75 mm deep slot tolerates about atan(1 / (D / 2)) = 1.5-1.9 deg [E, arithmetic]. Board 1's median tilt sits at that
limit, and its worst assembled frames exceed it by up to about 0.7 mm at the slot mouth and bottom [E]. The overlap
volume this implies is small, about 0.1 cm3 or less [E], under P3's 1 cm3 clause. But the replay will be
contact-driven, so P3's rotation limit (5 deg) stays the binding test, as INTERLOCK 20.4 expects. Not a defect of the
build; a design risk worth a synthetic case with a 2-3 deg in-plane tilt.

### Confirmed

- **C1. Nothing was delivered under F-I4 [M].** Both runs end in PUSH / PUSH:
  - fi4evalsem with `no_plane_pair`;
  - fi4b with `waiver_gate_fail:plate_outline_not_rectangular`, and `interlock_disagree` on board 2.

  The `ep24-fi4b/r0` folder contains:
  - 32 default pieces per board, all convex, summing to 264.7 / 256.6 cm3;
  - manifest `interlock.delivered = "default"` and `carved_cm3` 0 / 0;
  - `DO_NOT_USE.json` (F-I3.8: ours 0.72 / 2.0, CoACD 52.9 / 77.3 cm3 per hull, as logged);
  - no `_default/` folder and no slotted pieces;
  - `physcheck.json` = {} (the run used `--no-physcheck`).

  The submitted shells are watertight but measure 42.1 x 146.3 x 234.7 mm and 38.5 x 142.9 x 235.8 mm. The 38-42 mm
  "thickness" comes from the marker bumps on the faces. This is why the old route's pieces cannot meet the keep-out
  limit.
- **C2. Plate-test numbers [M].** My re-run of `plate_info` reproduces:
  - board 1: step 2, t 6.212 mm, faces +4.19 / -2.02 mm, overlap 0.968, 1.3 deg, rms 2.49 / 1.66 mm;
  - board 2: step 3, t := 6.212 mm. Its mid plane is the seen face (3.613 mm) moved 3.106 mm away from the cameras,
    to 0.507 mm. I checked the sign: correct.
- **C3. Kept gates [M].**
  - INSERTION runs: 122.3 / 127.7 mm, straightness 0.908 / 0.915.
  - Sweep 1.0 / 1.0, push 19.0 / 22.0 mm.
  - Rectangles 234.5 x 142.3 / 231.1 x 142.0 mm.
- **C4. Order and code [M].**
  - F-I4.14 pushed in dad65a1 at 17:06:51. Code 9ad1af9 at 17:14:55. fi4b launched at 17:15:14.
  - The sha256 of platebody.py, interlock.py, simphys.py and tools/interlock_dev.py in the r0 manifest equal those at
    9ad1af9.
  - No `--gen`; the inputs were GT-free.
- **C5. Slot on the right board and edge, given the identity semantics [M].**
  - Under public semantics both boards carry IDENTITY_SWAP, so (c) is absent and the decision is IGNORE. T-I11 used
    eval semantics, as pre-registered.
  - With our tracks:
    - each insertion runs along that board's width axis (d . a_W = 0.998 / 0.999, 4.0 / 3.0 deg; 87.4 deg from a_T);
    - the two width axes are antiparallel (177.95 deg), so the two entry edges face each other, as a cross-lap needs;
    - the partner's mid plane crosses a_L 2.0 / 0.9 mm from the rectangle centre, i.e. mid-length. This matches the
      slot seen in the RGB frames.
  - Both boards are the same stock (both I-shaped), so a label swap does not move the slot within a board.
- **C6. Physics numbers quoted [M].**
  - From `results/ep24-evalsem/diag_*.json` (the DIAG motion-band slot, 16 copies):

    | Collider | Lag at assembly (P3) |
    | --- | --- |
    | default | 1.849 cm / 112.98 deg |
    | DIAG carved | 0.333 cm / 9.40 deg |
    | no collision | 0.032 cm / 0.09 deg |

    P2 +n is 13.0 mm (fail); P4, P6 and P7 pass; the plain-MuJoCo P1 pre-check fails for both colliders (it does not
    decide).
  - Synthetic w5 (test_waiver.json): 0.033 cm / 0.16 deg, overlap 0.0 cm3. w7: widths 12.17 mm, centre 0.15 / 0.21 mm.
  - **Re-running a jittered copy was not possible:** there are no slotted pieces to run.

### Non-blocking notes

- **N1.** The r0 manifest `code.commit` says 42ab815: another agent's HEAD at 17:26, during the run. The code that ran
  is 9ad1af9 (the sha256 values match). The driver should record the launch commit.
- **N2.** The slot-centre rule is stale in two places. INTERLOCK 20.3 and the `platebody.py` module docstring still say
  the centre is the motion component's centroid; F-I4.12 changed it to the partner's mid plane (`slot_for` itself is
  correct).
- **N3.** The build result puts diag14's "42 % / 58 % of points per side" (all near points) next to the run's step-2
  result. The run's downsample splits 53 % / 47 % (19,431 / 17,244). Both are correct for their own point sets.
- **N4.** The outline PNGs have no scale, axes or rectangle drawn. Putting them beside the existing RGB frames
  (`sil_ep24_b*.png`) would have shown the I-shape at once.
- **N5.** The outline-rectangle bodies are inflated by the raster, as in synthetic w1 (238.4 x 133.4 mm for a true
  230 x 125) [E]. Any outline-based body will carry the same growth unless it is eroded or edge-fitted [H].
- **N6. Eval-25 risk [H].** The slot is built from P_sel (our tracks) but replayed on P_sim (the packed eval-25
  reference). If that reference labels or orients the boards differently from our tracks, the entry edges could land
  on the wrong side. Check the P_sel -> P_sim mapping per board (width-axis sign) before any eval-25 F-I4 run.

## Cost

CPU only, this container, about 3 min of compute in total. No rental, $0.
