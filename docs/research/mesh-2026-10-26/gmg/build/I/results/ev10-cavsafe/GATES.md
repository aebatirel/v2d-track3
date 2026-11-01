# ev10-cavsafe: gates and design, fixed before any candidate number

Written 1 Nov 2026, 02:54 UTC (commit 98ddccf), and committed before the candidate pieces were built or measured. The gates are the
orchestrator's (relayed at about 02:52 UTC; the owner approved collision-overlap fixes at 02:50 UTC). Definitions,
frame sets and tolerances are added here and fixed now. Tags: [M] measured, [E] estimate, [H] hypothesis.

## What was done and seen before this file (time order, honest record)

- 02:47-02:49: read the precheck (`../collcarve2-evalcheck`), `meshes/carve/ev10` (carve.json, lathe_collision.json),
  focused-pascal's `pipeline/lathe_collision.py` and their ev10w README.
- 02:49: regenerated the approach-2 lathe profiles from `meshes/library_v3` (blue cup and beige cup) with
  `approach2-scripts/lathe_fit2.py`.
- 02:51: rebuilt ev10 with carve.json's own commands. All 49 beige pieces and the 36 blue wall pieces match the packed
  ev10 at a vertex Hausdorff distance of 0.0 mm. Then printed the profiles.
- No candidate piece built, and no candidate number of any kind (overlap, contacts, intrusion, volume) measured.
- Packed ev10 numbers already known from the precheck [M]:
  - piece overlap over f124-f160: median 11.9 cm3, max 32.7 cm3;
  - faithful overlap: median 80.6 cm3;
  - pair scene: max nefc 656-1,296, overflow in 16 of 16 copies;
  - piece union volumes: blue 152.5 cm3, beige 303.1 cm3;
  - visual volumes: blue 400.3 cm3, beige 157.8 cm3.

## Candidate design (fixed now)

Same tool, inputs and constants as ev10:
- `lathe_collision.py`, `--seg 12 --band 0.06`, the same regenerated profiles;
- blue: wall 3 mm, and the 17 ev10 base hulls (`piece_36`-`piece_52`) copied byte for byte (they lie below the cavity
  floor plane by construction);
- beige: shrink 8 mm, fitted wall 7.41 mm, base extended 7.1 mm, ring base.

The piece counts therefore stay 53 / 49. Only these changes:

- **R1 (blue, the receiver).** The inner wall points sit at r_in / cos(pi/12) at the two sector edges, so the inner
  chord touches r_in at mid-sector (a regular 12-gon circumscribing the cavity circle). The outer points are unchanged.
- **R2 (blue).** Within each 6 cm band, a convex hull's inner face spans profile bins along the height. Where r_in(h) is
  concave, that face cuts into the cavity. So in each band, r_in is replaced at the bins by its least convex majorant f:
  - a linear program: minimise sum(f - r_in) subject to f >= r_in and f convex in h;
  - R1 then applies to f.
  - Generic geometry: it is the smallest change for which a hull of those bins cannot enter the cavity.
- **G1 (beige, the guest).** Within each band, the shrunk outer profile r_s = r - 8 mm is replaced at the bins by its
  greatest concave minorant:
  - maximise sum(f) subject to f <= r_s and f concave in h;
  - so the hull's outer face never bulges beyond r_s between bins.
  - The edge points already lie on r_s, so the mid-sector chord is inside: the outer faces are inscribed. The guest's
    inner points stay at r_s - 7.41 mm, as in ev10.
- **Not changed:** bands, sectors, shrink, wall, base. Nothing is tuned on any overlap or contact number.

## Gates (pass / fail), all on the packed reference's replayed poses

Inputs:
- the packed reference: `runs/20261026-gl10A2-5e0e100/refs/glockt/ep10/.../ref_gl_ilc.parquet`, md5 1a5003d9...;
- its support stage;
- the visual meshes `meshes/library_v3/{blue_cup,beige_cup}.glb`.

The same code runs for the packed ev10 and for the candidate. That code is the precheck's `evalcheck.py` and
`contacts.py`, run with only the piece paths changed.

1. **Piece-vs-piece overlap at the hands-off nested rest.**
   - Frames: f124-f160. All 37 are H0, meaning no contact label in either hand [M, precheck].
   - Measure: the precheck's V_packed. That is the guest pieces' union, as centres of a 1.5 mm grid, inside the
     receiver pieces' union occupancy on a 1 mm grid, in cm3.
   - Pass: median <= 1.0 cm3 and max <= 3.0 cm3.
   - Reported beside it: the faithful visual-mesh overlap (2 mm cells, V_faithful) as the pose floor.
2. **Pair scene in plain MuJoCo with sim=rl.**
   - `contacts.py` unchanged: 16 jittered copies x 2 s, sim=rl options and limits (njmax 512, nconmax 256).
   - Frames: the precheck's three, f111, f142 and f116, for both sets.
   - Pass: 0 overflow copies at every frame, max nefc <= 512 and max ncon <= 256.
   - Report only: the frames that contacts.py's own rule picks for the candidate, if they differ, and f124 / f160.
3. **Cavity intrusion of the receiver pieces.**
   - Frame: the blue lathe frame (c0, d, e1, e2 of the profile).
   - Cavity: C = { h_mouth <= h <= h_floor, rho < r_in(h) }, where:
     - r_in = r - 3 mm, linear between profile bins;
     - h_mouth = the first wall bin;
     - h_floor = h_base - 3 mm.
   - Depth: the max of r_in(h) - rho over all 53 pieces. It is evaluated at their vertices, at surface samples
     <= 0.5 mm apart, and at interior points of a 0.5 mm grid.
   - Pass: depth <= 0 mm, with a tolerance of 0.001 mm for float rounding in the OBJ files. The intruding volume on the
     0.5 mm grid is reported too.
4. **Kept volume.**
   - Reference: the visual mesh volume. Both library_v3 meshes are watertight [M, precheck: trimesh is_watertight],
     so the visual mesh is the reference, not the ev10 pieces.
   - (4a) Gate as written: the union volume of the pieces (1 mm grid, centre inside) / the visual mesh volume. Pass:
     >= 0.80 for each cup.
   - Report only:
     - (4b) the visual volume the pieces keep: (pieces ∩ visual) / visual;
     - (4c) the union volume / the ev10 pieces' union volume.

## Expected outcomes, stated before measuring [H]

- **Gate 4a fails for the blue cup** for packed ev10 already (152.5 / 400.3 = 0.38 [M]). It will fail for any piece set
  with an empty cavity, because the blue visual mesh fills 38.7 % of its cavity (spoon-diag). Beige ev10 passes 4a
  (303.1 / 157.8 = 1.92) only because its pieces sit mostly in the beige mesh's own cavity. On 4b, ev10 keeps
  0.30 (blue) and 0.18 (beige) [M]. Gate 4 cannot separate good from bad piece sets here. I report it as written.
- **Gate 1 likely fails.**
  - The packed overlap reaches 3.2 mm deep (a lower bound).
  - R1 gains about 1.3 mm at mid-sector and 0 mm at the sector edges.
  - focused-pascal's ev10w found the rest overlap is a relative-pose offset of 4-7 mm.
  - Falsifier: candidate median <= 1.0 cm3 and max <= 3.0 cm3.
- **Gate 3 passes** by construction. Falsifier: any sampled depth > 0.001 mm.

## Amendment A1 (1 Nov, 02:59 UTC, after building, before any gate number; time corrected from a mistyped 03:12)

**What happened.** Building R1 + R2 with the blue cup's outer points unchanged failed the tool's own validity check:
the mid-sector wall (outer chord minus the inner tangent f) is negative at two bins.

| Bin (h) | Where | Inner f raised by R2 | Mid-sector wall |
|---|---|---|---|
| -83.6 mm | the mouth lip, where the outer profile curls inward | 2.75 mm | -1.30 mm |
| 74.4 mm | the rounded bottom corner | 2.13 mm | -0.30 mm |

A single convex piece per band cannot follow a concave profile from the cavity side unless its outer face moves out
too.

**Change (R1').** The blue cup's outer points are also placed at r / cos(pi/12) at the sector edges. The wall polygon
then circumscribes the lathe wall on both faces. This is the mirror of ev10, which inscribes both faces. It adds no
constant.
- Cost: the blue cup's outer surface lies 0 to r (1/cos(pi/12) - 1), about 1.6 mm, outside the lathe profile, against
  0 to 1.6 mm inside it in ev10. The base hulls, which carry the table contact, are unchanged.
- Mid-sector wall as built [M, from the build log, not a gate]:
  - >= 2.49 mm in band 2;
  - 0.25 mm at the mouth bin (band 1);
  - 0.875 mm at the bottom bin (band 3);
  - elsewhere near t - raise.
- Blue piece volume 130.4 cm3 (ev10 152.9).

**Also seen while building [M, not a gate].**
- G1 lowers the beige cup's outer points by up to 4.83 mm in band 2 (h 50-70 mm), below a step of the profile (r_s 33.5
  -> 35.0 mm at h 42-52 mm). Beige piece volume 264.0 cm3 (ev10 302.9).
- Both stay as designed.

**Unchanged.** Gates 1-4, the frames and the expected outcomes.

## Amendment A2 (1 Nov, 03:10 UTC): variant v2, designed AFTER v1's gate numbers, before any v2 number

**Why (post hoc on v1) [M].**
- v1 (`ev10cs`) passes gate 3 and fails gates 1, 2 and 4a.
- The settle trace (`scripts/settle_trace.py`) shows the gate-2 rows come from the blue cup's floor. The beige slides
  down the wider cavity, 4-27 mm along the axis, onto the blue floor.
- There its 13 ring-base pieces meet the 17 CoACD base hulls. All 17 hulls have their top face on the floor plane, so
  166-191 of the 185-194 contacts at the max-nefc step are base against base.

**v2 design (`ev10cs2`).** v1 unchanged except for the blue cup's base. Change F1:
- The cavity floor becomes **one** convex piece: the hull of the circumscribed 12-gon rings, r(h) / cos(pi/12), at
  h_floor and at the profile bins up to h_base.
  - This is lathe_collision.py's own base plate span [h_base - t, h_base], with t = 3 mm.
  - Its top face lies on the floor plane, so it does not enter the cavity.
- The 17 ev10 base hulls are clipped to h >= h_base with the tool's own `interaction_carve.clip`. That function drops a
  piece thinner than a 0.2 mm inscribed ball. The footing on the table is unchanged: it is the hulls' bottom faces.
- No new constant.
- The blue count is 36 + 1 + K <= 53, which needs K <= 16. Otherwise v2 is not built as specified, and that is
  reported.

**Gates.** Gates 1-4 as above, and the same frames.
- Report only: the settle trace at f124, f142 and f160.
- Expected [H]: at the max-nefc step, guest-base x receiver-floor contacts <= 13.
- Falsifiers: more than 50 such contacts, or gate 2 fails with its maximum at the floor.
- v2 is labelled post hoc everywhere. v1 stays the pre-registered candidate.

## Amendment A3 (1 Nov, 03:14 UTC): variant v3, written before any v3 number

**Inputs (data, relayed by the orchestrator).**
- determined-wright, 03:13 UTC, their contact_budget/README.md 90e3e41 [R]. FlashCHORD full scene on v1 (`ev10cs`,
  dafc911):
  - sampled nefc max 510 / median 443, against packed 536 / 473;
  - 4 overflow lines, against 13,544;
  - cup-cup contacts max 31, against 68.
- Their verdict: improved, not clean at 512. Hands now dominate (the right hand on the beige cup, about 44 contacts).
  Their lever is fewer, larger pieces where the hands touch, plus the single-piece receiver floor (A2).
- Our v2 numbers seen before this amendment [M, plain MuJoCo]:
  - gate 1 = v1 (median 1.92, max 6.82 cm3);
  - gate 2: max nefc 548, ncon 137, overflow 5 / 48;
  - gate 3: 0.0 mm;
  - settle: 212 rows at rest at f124, f142 and f160.

**v3 design (`ev10cs3`) = v2 with `--seg 8` for both cups.** Everything else is unchanged:
- bands 6 cm;
- R1' / R2 on the blue cup, G1 on the beige cup;
- the floor plate (its rings are 8-gons) and the same 7 clipped base hulls;
- the beige ring base with 1 + 8 pieces.

Counts: blue 24 + 1 + 7 = 32, beige 24 + 9 = 33.

**Why 8.** It is a judgment constant, chosen before any N = 8 number and not derived.
- 8 / 12 cuts the hand-facing pieces per band by a third, the step that the FlashCHORD target (about 60-100 rows off
  about 124 contacts) asks for.
- The chord error at r = 40 mm is 3.0 mm inside for the beige (inscribed) and 3.3 mm outside for the blue's outer face
  (circumscribed), about the wall constant t = 3 mm.
- N = 6 would give 5.4-6.2 mm, about the 4-7 mm pose offset.

**Gates for v3.**
- Gates 1-4 as above, on the same frames, plus the settle trace.
- Piece-count target: at most two thirds of ev10 per cup (blue <= 35, beige <= 33).
- **FlashCHORD criterion, the final contact gate** (measured by determined-wright with budget.py, not by us): sampled
  nefc max <= about 460 and 0 overflow lines.
- Expected [H]: plain-MuJoCo gate 2 max nefc below v2's 548. Gate 1 changes: the 8-gon chords sit further inside the
  beige, and the blue's inner faces stay tangent. Falsifier: gate 1 median above v1's 1.92 cm3.

v2 (`ev10cs2`) is delivered as built.
