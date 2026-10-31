# verify_cc_1: physics and geometry check of the T-I13 public collision-carve runs (head 124fc86)

Verifier of the collision-carve workflow, physics and geometry lens. 31 Oct 2026, 20:59-21:22 UTC. Checked: the T-I13
public runs (PREREG F-I5.14, INTERLOCK 21.11, `build/I/results/collcarve-public/`, figures `build/I/png/fi5pub_ep*.png`)
against the run's own pieces, bodies, tracks and logs.

**Integrity.** All inputs are GT-free: the v6 clean bundles (tracks, grids, our table plane), the run's SHELL
candidates (`shell_t5p36`), its structure JSON, its round folders and its logs. No scan, mocap, parquet pose, `*_align`
file or scan-derived constant was used. Everything below is a post-hoc diagnostic. It decides nothing and delivers
nothing. No gmg code was changed. The code was read at the run's hashes (cavpieces 2f5a3776, collcarve a27f7b95,
simphys 12013ff2, simpieces 248623ea, structure 4055ed43, the same as `drv11_fi5.launch`). It ran on this container
(nice 10, load 5-11), took about 10 CPU minutes and cost $0. Labels: [M] measured here, [E] estimate, [H] hypothesis.

## Verdict

The run's measurements reproduce. The delivered volumes, CoACD counts, routes, overshoot frames, c, the caps and the S
numbers all match, and two stored S copies re-run bit for bit. **The run's explanation of the failure is wrong in two
places, and the list of decisions in INTERLOCK 21.11 is not enough.**

- **(B1)** The lathe ring pieces fail the pieces gate on their own. The "handle" step is not what breaks the ring route,
  so "bound the handle step" (21.11 decision 1) cannot rescue it. The run's own stated falsifier for that proposal has
  already fired. The continuity check behind "the rings are continuous, 0 gaps" cannot see this failure.
- **(B2)** S also fails on **faithful** colliders (the SHELL bodies themselves, as 2 mm boxes, with no piece cap) at all
  eight S frames. The tracked poses interpenetrate (86 cm3 in ep11, 25 cm3 in ep2), sit inside our table plane (ep12 f6,
  ep13) or float with nothing under them (ep31). So the 6 mm boxes are not the only reason the delivered copies fail. A
  better piece builder plus a delivery floor (decisions 1-2) would still deliver nothing usable on these five pairs.
- **(B3)** ep11 cannot serve as a cup-nesting case with these inputs. Both cup SHELLs are bottomless tubes. At the S
  frame both stand on the table in nearly the same place (axes 2.8 mm and 1.7 deg apart, overlapping 86 cm3).

None of this changes the run's outcome under the rule as written: nothing was carved and nothing may be used. All three
change what has to be decided before the next run.

## Blocking findings

### B1. The ring pieces fail the gate without any handle hull, and the continuity check cannot catch it [M]

I rebuilt each lathe ring set exactly as the run did: `cavpieces.Lathe.from_mesh` on the SHELL, the structure axis and
the bundle sigma, then `Lathe.pieces(n_s)`. The rebuild is the run's geometry: its handle residual reproduces the run's
handle components exactly (ep11 beige 6 components, 31.5 cm3; ep12 blue 15, 22.1 cm3; ep13 blue 10, 29.8 cm3; pot 8,
68.3 cm3). I then ran the F-I5.4 pieces gate (`cavpieces.keepout` / `excess`) on the **ring pieces only**:

| object (sectors the run used) | ring pieces > 0.3 cm3 keep-out at the run's sectors (max cm3) | same at 16 sectors, no cap | run's route-2 record | mid-sector inner face vs the profile's inner radius (median, mm) | ring volume inside the cavity (cm3) | body cells inside some ring piece |
|---|---|---|---|---|---|---|
| ep11 beige_cup (8) | **16** (3.232) | 29 (1.552) | gate fail, 16 hulls over, max 3.248 | -2.94 (16 sectors: -1.19) | 64.9 (16: 22.5) | 48.7 % (16: 62.1 %) |
| ep13 blue_cup (8) | **20** (2.008) | not run | gate fail, 22 hulls over, max **2.008** | -3.44 | 96.7 | 44.9 % |
| ep12 blue_cup (8) | **15** (2.520) | 18 (1.472) | over the cap with the handle (gate never reached) | -3.07 (16: -1.31) | 70.3 (16: 26.9) | 48.9 % (16: 68.0 %) |
| ep2 white_pot (12) | **36** (17.28) | 45 (13.10) | over the cap with the handle | -12.46 (16: -12.03) | 224.2 (16: 190.5) | 45.7 % (16: 50.7 %) |

- **The run's full sets, split by hull kind** (`cavpieces.lathe_route` re-run, then the gate per hull) [M]:
  - ep11 beige: 71 hulls, gate max 3.248, sum 25.72, keep-out 25.696 cm3, identical to `fi5.json`. **All 16 failing
    hulls are rings** (max 3.248). The 15 handle hulls all pass (max 0.288).
  - ep13 blue: 81 hulls, 22 over, max 2.008, sum 27.04, identical to `fi5.json`. **20 of the 22 failing hulls are
    rings**, 2 are handle hulls (max 0.624).

  The README (mechanism 2), the 20:56 correction and INTERLOCK 21.11 say the handle hulls "push the set over the cap or
  fail the gate". That is wrong for both objects whose gate was reached. (The ring-only column above reads 3.232 rather
  than 3.248 for ep11 because the keep-out grid's origin follows the union's bounds.)
- **Mechanism.** Each wall piece is the hull of the profile points at the sector's two edge angles (F-I5.4 as written).
  Its inner face is therefore a chord that sits r_in(1 - cos(pi/N_s)) inside the cavity at mid-sector: about 3.0 mm at
  r = 40 mm with 8 sectors, and 0.8 mm with 16 [E, formula]. A 30 mm band hull over a tapering or curving profile adds
  more (the pot reaches 12 mm, from the base-to-wall corner). The cavity of these SHELLs is mostly seen empty (FREE), so
  that sliver is keep-out: about 1.9 cm3 per 8-sector, 30 mm piece at r_in = 40 mm [E], against the 0.3 cm3 tolerance.
- **The cap forces 8 sectors on these cups.** The cup SHELLs are 186-204 mm tall along their axes, which makes 7 bands
  of 30 mm. 16 x 7 = 112 and 12 x 7 = 84 both exceed the 82-piece cap, so 8 sectors is the only count left
  [M, from the profiles]. Even at 16 sectors with no cap, the rings fail the gate (18-45 pieces over).
- **The continuity check is self-referential (code reading, confirmed [M]).** `cavpieces.continuity` places its test
  points at the middle of the pieces' own chord polygon, scaled by cos(th)/cos(phi - fm). It never compares the pieces
  with the measured wall. Measured: 0 gaps on 129,240-144,720 rays, while the 8-sector rings hold only 45-49 % of the
  body cells and overlap the 5.0-5.4 mm SHELL wall by only 1.9-2.9 mm at mid-sector (median). The log entries "rings
  fine", "0 gaps" (20:01, 20:07, 20:14, 20:56) are true but are no evidence that the rings fit the wall.
- **Consequence.** README proposal (c) and 21.11 decision 1 (the "bounded handle step") would not make the lathe route
  pass. Its own falsifier ("the ring set without the residual hulls fails the gate ... on the same pairs") has fired on
  all four objects tested. Any change to the lathe route has to fix the ring geometry and the cap, not the handle test.
  [H, not tested] inner vertices placed so the inner chord is tangent to the measured inner surface (r_in / cos(pi/N_s)
  at the sector edges), plus band edges at profile slope changes. Falsifier: the gate still fails on ep11 beige and
  ep12 blue at 16 sectors.
- **What the "handle" residual is [M].** For ep12 blue, 68 % of the residual lies *inside* the profile's outer radius,
  67 % falls in the middle half of the sectors (50 % if uniform), and 74 % lies beyond the outer chord + 3 sigma. Most
  of it is wall material cut off by the 8-sector outer chord, which sags 0.076 r = 3.5 mm at r = 46 mm, more than
  3 sigma = 2.98 mm. That mostly falsifies the run's [H] "the handle components are SHELL residuals" for this cup. For
  ep11 beige and the pot, 58-67 % lies more than 2 mm outside the profile radius (material the revolution does not
  explain, or axis error), so there it is a mix.

### B2. S fails on faithful colliders too: the pose and the bodies are blockers, not only the pieces [M]

Setup, diagnostic only. The S scene of F-I5.5 (`simphys.sink_xml` geometry: receiver fixed at its tracked pose, guest
free at its tracked pose, our table plane, 0.3 kg, 2 s at 2 ms, plain MuJoCo 3.17.0). The colliders are the **SHELL
bodies' 2 mm cells** (centre inside), merged by `cavpieces._boxes` and given to MuJoCo as primitive boxes: 736-4,751
boxes per object, about 100 % of the body, no cap. One unjittered copy per S frame; ep11 also ran copy 0 of the stored
jitters.

| ep, S frame | SHELL overlap of guest in receiver (cm3; guest SHELL cm3) | guest lowest point above our table (SHELL / delivered pieces, mm) | contacts at t = 0 | faithful S: displacement / dz (+ = down) / tilt | delivered-box S (run) |
|---|---|---|---|---|---|
| 11 f126 | **86.0** (172.6) | +3.2 / +77.4 | 27,285 | **10.9 / +1.5 / 6.5 deg** (copy 0: 11.5 / +1.8 / 6.7) | 80.5 mm |
| 12 f176 | 7.5 (224.6) | -2.2 / +1.3 | 3,132 | **10.5 / -2.4 / 4.6 deg** | 126.8 mm |
| 12 f6 | 0.0 | **-15.1** / -8.1 | 698 | **18.6 / -12.1 / 9.3 deg** | 8.2 mm |
| 13 f146 | 3.1 (212.6) | **-23.3** / -14.7 | 2,571 | **20.1 / -17.7 / 9.6 deg** | 90.6 mm |
| 31 f282 | 0.0 (34.9) | **+45.0** / +79.2 | **0** | **87.3 / +72.6 / 101 deg** | 84.2 mm |
| 31 f8 | 0.0 | +46.1 / +82.3 | **0** | **98.3 / +74.8 / 105 deg** | 86.7 mm |
| 2 f24 | **25.0** (180.8) | +60.5 / +87.2 | 10,833 | **13.9 / -11.5 / 11.8 deg** | 84.8 mm |
| 2 f328 | **24.1** | +62.0 / +88.1 | 11,516 | **29.9 / -27.5 / 19.0 deg** | 88.0 mm |

- All eight frames fail S (4 mm, 5 deg) with colliders that keep the whole body. The causes are visible in the inputs:
  - **Interpenetration at the tracked rest pose** (ep11 86 cm3, half the guest; ep2 24-25 cm3; ep12 f176 7.5 cm3): the
    faithful pieces push the guest out slowly. In ep2 the lid is still rising at 2 s.
  - **The guest starts inside our table plane** (ep13 f146 by 15-23 mm, ep12 f6 by 8-15 mm): the plane pushes it up
    12-18 mm. No carve can fix this, because the table is not an object.
  - **The ep31 sweeper floats.** Its lowest SHELL point is 45-46 mm above the table, with zero SHELL overlap and zero
    contacts at t = 0, so it free-falls (40-48 mm in the first 0.1 s). The rack's own grid says the 45 mm path under it
    is 88-94 % FREE (seen empty), 3.5-6.7 % OBSERVED and 2.6-5.4 % UNKNOWN. This is not hidden rack structure the SHELL
    missed. [H] The track is high, or a hand still holds the sweeper. Falsifier: our depth points of the sweeper at f282
    against its posed SHELL along the table normal.
- So the README / 21.11 wording "the cups fall out of the rack", "the sweeper falls through the rack's boxes to the
  table", "the lid falls into the pot" correctly describes what the 6 mm boxes do. It is not why S fails on these
  pairs. P47 is falsified whatever the pieces (the sweeper drops 73-75 mm on faithful colliders).
- **Consequence for 21.11.** Decisions 1-2 are necessary but not sufficient. (a) A delivery floor that uses "S on the
  delivered pieces" would also reject a perfect piece set at these poses, so it cannot tell a piece failure from a pose
  failure. [H] Also run S on a faithful reference collider (the 2 mm SHELL boxes above take 2-50 s per copy here), and
  call a failure a piece failure only when the reference passes. (b) Add an S-frame precheck on the guest's lowest
  point against the table plane, plus the faithful-body overlap at the S frame. Three of the five pairs (ep12 f6, ep13,
  ep31) fail S for reasons no carve can address.

### B3. ep11 is not a cup-nesting case with these inputs [M]

- **Both ep11 cup SHELLs are bottomless.** Rays along the structure axis from 20 points inside each cavity (on the axis
  and 10 mm off it), in both directions, hit nothing. The beige profile has 0 solid bins out of 101. The ep12, ep13 and
  pot SHELLs do have a bottom (20/20 rays hit). A lathe or any faithful collider of the ep11 receiver therefore has no
  floor: a bigger defect than the ev10 1 mm ring, and one the continuity check does not test (it starts at "the base
  top").
- **At the S frame f126** both SHELLs stand on the table: lowest points 3.2 mm (blue) and 3.4 mm (beige) above it,
  tops 205.7 / 202.7 mm, axis feet 2.8 mm apart and axes 1.7 deg apart. Through the rest frames 118-136 both bottoms
  stay 3-5 mm above the table. The guest is held by the table, not by the receiver. Two nested rigid cups of this size
  cannot occupy this pose, so S on ep11 says nothing about cup-in-cup sink. P43 and P44 on ep11 do not test what F-I5.9
  meant them to test. [H] Both tracks lock on the same stack, or each cup's SHELL is built from the stack's surfaces.
  Falsifier: the per-frame identity / B.2a step (not yet run on v6) and the observed rim heights of each cup.
- The overshoot exclusion is physically right here [M]: at the overshoot frames 106-114 the guest's SHELL bottom lies
  up to 2.8 mm *below* the table (f108), an impossible pose.

## Nonblocking findings

- **N1. The default S is bimodal, and its per-copy rows were dropped** [M]. I re-ran S at ep11 f126 one copy at a time
  with `simphys.jitters(16, seed=2)`. The carved (failed) copies 0 and 2 reproduce the stored rows exactly (4.23 /
  0.72 / 2.88 deg and 112.54 / 111.63 / 68.05 deg). Default copy 0: 7.2 mm, the guest pushed **up** 5.4 mm, tilt 21.7
  deg, no fall. Copy 2: 142.7 mm, falls 120.6 mm. Unjittered: 146.7 mm, falls 120.6 mm. So "the inner cup falls 80 mm"
  is the mean of no-falls and 120 mm falls. F-I5.5 says "per-copy dz, lateral and tilt are reported, and the
  default's". `collcarve.py:587` and `build/I/fi5_default_sink.py:130` drop the default's per-copy rows. This is a
  reporting gap only. S still fails either way.
- **N2. Volumes** [M]. The delivered volumes reproduce exactly (exact box volumes: 6.48, 6.912, 11.88, 23.328, 10.80,
  11.016, 0.648, 20.304, 23.544, 16.848 cm3, all boxes 6 mm, delivered = default for every object). But
  `props_gmg.json` `volume_cm3` overstates them **1.52-1.94x** (blue_cup ep11 11.15 vs 6.48; sweeper 1.26 vs 0.648).
  `simpieces.props` counts 1.5 mm grid samples on the faces of grid-aligned boxes, and the COM and inertia in those
  props come from that inflated sample set. The copies are do-not-use anyway; this matters if box pieces are ever
  delivered.
- **N3. ep11 caps and P4 on exact volumes** [M]. Removed 0.648 cm3 = **9.38 %** of the exact 6.912 cm3 (reported 0.678
  = 9.97 % of a sampled 6.8 cm3). The cap passes either way, but the sampled figure sat 0.03 points under the 10 %
  limit. P4 still fails on exact volumes (0.648 > 1.5 x 0.414 = 0.621), by 4 %. Borderline cap and P4 decisions on box
  pieces should use exact volumes. The carved boxes lie wholly inside the default boxes (0.0 cm3 outside, 0.5 mm grid).
- **N4. The relative criteria pass vacuously against a broken default** [M]. P2 passes with +-n free travel of 60 mm
  (the search cap) for carved and default alike, since the bound is "default + 1 mm". The 10 % cap is relative to a
  6.8 cm3 collider. A delivery floor (21.11 decision 2) should include absolute bounds.
- **N5. The handle components were not logged by kind; the B1 table now gives the ring-only split** [M]. The run's
  handle components reproduce exactly (see B1), so the README's handle numbers are right. Only their role in the
  failure was misattributed.
- **N6. Wall thickness** [M]. The README says the 6 mm boxes fail on "a 3-5 mm wall". The SHELL walls these boxes
  sample are 5.0-5.4 mm (profile medians, cups); a 6 mm cell still cannot fit. The pot profile's 14.9 mm median is a
  profile artefact: its 370 cm3 body implies a 3-5 mm wall [E]. That artefact is also why the pot rings reach 12 mm
  into the cavity.
- **N7. Route 4 "wholly inside" is approximate** (code reading, not measured). The 2 mm cells are kept by "centre
  inside", so a 6 mm cell can stick out up to 1 mm past the SHELL surface.
- **N8. Empty ring** [M]. No ev10-type ring at the base top, by construction (shared band edge). But the ep12 blue cup's
  6 mm base is only 50.9 % covered by the 8-sector rim and disc pieces (wall cells 48.9 %), and the ep11 cups have no
  base at all (B3).
- **N9. Figures.** I checked the PNG bars against the JSON (80.5 / 31.6; 126.8 / 8.2; 84.2 / 86.7; 84.8 / 88.0) and the
  side-view arrays (`fi5png/ep31.npz`: sweeper 95.5 mm tall, its lowest point 55.8 mm above the rack's lowest, which
  matches my table numbers). They are consistent. The side views draw no table line. Adding it would have shown the
  ep12 f6 and ep13 table penetration and the floating sweeper at a glance.

## Confirmed [M]

- Piece routes and counts: CoACD returned 82 hulls for 9 objects and 80 for the ep13 rack, with 0 repair steps (2 for
  the ep13 rack). The 6 mm cell counts were 3-109. The blue cup rotc was 3.0126 sigma.
- ep11 records: 7 overshoot frames at 4.27-9.21 mm along d; c = 1.0 mm (sigma_sup 0.99919); caps topology 14 / 14; the
  S means; the ep11 S frame and receiver of the diagnostic.
- Code identity: the module hashes match the launch record.
- The SHELL overlap along the box colliders is under 0.5 cm3, as reported.
- The run kept the rule's do-not-use. Nothing was uploaded or packed, and the README says the round folders must not be
  used.

## Reproduction

Scripts and JSON (scratch, not in git) are in `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/vcc1/`. Each was run as
`GMG_MODE=dev nice -n 10 <venv>/python -I <script> [args]`, with `guard.set_run` on the run folder, read-only:

| script | sha256 (prefix) | what it does |
|---|---|---|
| `vol.py` | 0af9b788 | volumes |
| `lathe_check.py EP OBJ SECTORS` | 2790e43d | B1 |
| `fullset_gate.py EP OBJ` | 1629dfc6 | B1, full set by hull kind |
| `sink_rerun.py` | 0cfb8141 | SHELL overlap, S copies, box heights |
| `faithful_s.py EP FRAME [copies]` | 3d00df0c | B2 |
| `table.py`, `table11.py` | f24e5e71, b2de8aa5 | table heights, ep11 frames, axes |
| `bottom.py` | c8213557 | bottoms |
| `ring_junction.py` | 4155a672 | N8 |
| `ep31_state.py` | 2cc7b62c | rack grid along the sweeper's drop |

Run folder read: `<scratch>/gmg/runs-dev/20261031-fi5pub-3053a78`. Bundles:
`<scratch>/gmg/runs/20261031-b4ext6-90c8cce/bundle/public/ep{11,12,13,31,2}`.
