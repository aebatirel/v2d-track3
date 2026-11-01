# ev10-cavsafe: gates and design, fixed before any candidate number

Written 1 Nov 2026, 02:55 UTC, and committed before the candidate pieces were built or measured. The gates are the
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

## Amendment A1 (1 Nov, 03:12 UTC, after building, before any gate number)

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
