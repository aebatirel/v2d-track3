# Placement collision carves: build and CPU test (30 Oct 2026, this cloud container, CPU)

Markers: [M] measured here, [E] estimate, [H] hypothesis. No git operation. Eval carves read only OUR meshes and OUR eval
references; mocap appears only in the public-twin diagnostics (marked GT). Only the SIMULATOR collision copy changes
(URDF <collision> pieces); the submitted mesh, visual and inertial are untouched.

Scratch root `S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/carve`.
Tool: `/home/user/v2d-track3/pipeline/placement_carve.py` (new). Cases: `$S/cases.txt`.

## 1. Pre-registered pass criterion (written 30 Oct before any carve was built or tested)

A carve passes only if ALL hold, for the case's (host, guest) pair:
1. **Overlap:** the hull-hull overlap at the placed frame (guest's collision hulls inside the host's collision hulls,
   1.5 mm grid, cm3) falls by >= 80 % against the default FlashCHORD hulls (CoACD 0.05). Also reported: frame 0 and
   the maximum over all relative-rest contact frames.
2. **Settle:** 2 s hands-free settle (FlashCHORD scene, hands parked, gravity, no drive; `$S/scripts/settle_at.py`)
   from the reference pose at the placed frame (and at frame 0 when the initial rest is in contact): guest AND host
   drift <= 1 cm and tilt <= 5 deg at 2 s, no NaN.
3. **No new overlap elsewhere:** at every checked frame (stride 4 over the whole reference + all rest frames) the
   carved overlap is <= the default overlap + 0.1 cm3 (grid noise). (Pieces are subsets of the default hulls, so an
   increase would mean a bug.)
4. **No debris:** every carved piece is a valid convex hull with volume >= 1e-12 m3 (the tool also drops pieces
   < 2e-8 m3 and slivers thinner than a 0.2 mm inscribed ball, and reports the dropped volume).

Not part of the criterion (diagnostic only, never used to tune eval carves): on public twins, ADD (cm, our mesh
vertices) of the settled poses vs mocap GT at the same frame, against the reference's own ADD.
Parameters are fixed before testing: margin 1.5 mm, grid 1.5 mm, relative rest < 0.2 cm and < 1 deg per frame
(5-frame median), contact > 0.3 cm3 on a 3 mm grid, mutual guest carve only when the host's real material inside the
guest's hull fill is >= 0.5 cm3. One build per case; any later change is a new version, reported as such.

(results below)

## 2. Build log (in order)
- Code: `/home/user/v2d-track3/pipeline/placement_carve.py` (uncommitted, repo HEAD 92c8e38). Runner scripts in
  `$S/scripts/` (run_place.sh, run_settle.sh, settle_at2.py = settle_at.py + final poses, twin_gt_score.py, table.py);
  logs in `$S/blogs/`. Machine: this cloud container, 4 CPU, CPU-only Warp/MuJoCo Warp (fcvenv).
- **v0 (E14 only, discarded before any test):** box cover split up to 3 levels gave 204 rack / 147 cup pieces (71
  debris pieces dropped). Changed to one split level (FILL 3) before any settle: 90 / 114 pieces [M]. v0 carve.json kept
  as `$S/blogs/ev14_v0_depth3_carve.json`. Overlap metric fix: before/after now use the same guest grid (first E14 run
  showed +0.118 cm3 "increase" that was grid-origin noise).
- **v1 (pre-registered thresholds) on all cases.** E30: NO rest-contact segment found: the sweeper's reference rotates
  1.5-2.7 deg/frame relative to the rack (5-frame median) even where its world translation is < 0.1 cm/frame [M]
  (thin object, pose jitter), so the 1 deg/frame rule rejects every frame; v1 E30 = not carved
  (`$S/blogs/ev30_v1_carve.json`). P31mck v1 found only hand-held segments [8,14], [41,45] (kept in
  `$S/twins/P31mck_v1`).
- **v2 (sweeper cases only, E30 and P31mck; new version, not a re-tune on results):** --rest_cm 0.25 --rest_deg 3.0.
- **v3 (pre-registered here, 30 Oct, after the v1/v2 settle results below and BEFORE any v3 test):** hypothesis [H]:
  the claim union over every relative-rest contact segment, including short hand-held ones (E30 [44,48], [156,168];
  P31 eight segments; E1 [31,43], [275,298]; E28 [188,197]) and 1.5-3 deg/frame reference jitter, carves a pocket wider
  than any single placement, so thin or tall guests lose their lateral support (sweeper falls 43-85 deg after the
  carve). v3 = `--segments ends`: claim only from the segment at frame 0 and the last segment; everything else
  unchanged (sweeper cases keep the v2 rest thresholds). Order: public twins first (P31mck, P2mck); evals get v3 only
  with the rule unchanged. Falsified if P31mck v3 still tips > 5 deg. Same pass criterion as section 1.
  **v3 result [M]: falsified.** P31mck v3: sweeper at f269 5.45 cm / 72.8 deg (v2 5.03/55.2), f0 1.68/15.3; P2mck v3
  f334 0.72/2.8, f0 1.09/5.0 (v1 passed: 0.94/2.0). v3 is not applied to evals. Outputs: `$S/twins/v3/`.

## 3. Results [M] (2 s hands-free settle; drift cm / tilt deg at 2 s; overlap = guest hulls in host hulls, cm3)

| Case (host/guest) | placed (f0 rest) | overlap placed: def -> cut | f0 | rest max | guest settle def -> cut | host cut | pieces host, guest | GT rel ADD cm ref / def / cut | pass |
|---|---|---|---|---|---|---|---|---|---|
| E14 rack/cup (v1) | 150 (-) | 16.73 -> 0 (100 %) | 0 -> 0 | 17.64 -> 0 | 2.21/22.5 -> 1.48/12.5 (rocking) | 0.86/3.6 | 43->90, 75->114 | eval | **no** |
| E30 rack/sweeper (v2) | 242 (0) | 13.93 -> 0 | 12.53 -> 0 | 34.83 -> 0 | f242 2.52/7.0 -> 4.69/48.2; f0 2.37/7.2 -> 4.38/42.8 | 0.31/1.4 | 43->85, 19->32 | eval | **no (worse)** |
| E1 pot/lid (v1) | 305 (0) | 50.09 -> 0 | 44.24 -> 0 | 57.21 -> 0 | f305 2.33/14.5 -> 1.08/8.1; f0 2.16/12.4 -> 1.47/11.5 | 0.54/3.9 | 31->53, 41->107 | eval | **no** |
| E28 rack/pot (v1) | 206 (0) | 42.77 -> 0 | 0.44 -> 0 | 47.20 -> 0 | f206 2.45/9.0 -> 3.31/18.2 (*); f0 0.24/0.8 -> 0.08/1.0 | 0.21/0.5 | 43->104, 31->104 | eval | **no** (*) |
| P12gl rack/cup (E14 twin) | 170 (-) | 11.73 -> 0 | 0 -> 0 | 11.73 -> 0 | 3.08/14.4 -> 1.14/6.3 | 1.43/2.7 (def 1.19) | 43->97, 69->113 | 0.37 / 3.59 / 0.73 | no (narrow) |
| P31mck rack/sweeper (E30 twin, v2) | 269 (0) | 21.31 -> 0 | 6.65 -> 0 | 34.64 -> 0 | f269 4.49/29.7 -> 5.03/55.2; f0 2.02/16.7 -> 4.69/85.4 | 0.36/0.5 | 43->116, 19->28 | f269 1.06 / 4.33 / 6.38; f0 0.85 / 2.95 / 6.96 | no (worse) |
| P2mck pot/lid (E1 twin) | 334 (0) | 53.83 -> 0 | 50.80 -> 0 | 55.50 -> 0 | f334 4.22/60.7 -> 0.79/2.8; f0 5.99/25.5 -> 0.94/2.0 | 0.30/0.8 | 31->39, 41->97 | f334 1.18 / 6.83 / 1.71; f0 0.97 / 6.30 / 1.60 | **yes** |
| P26mck rack/pot (E28 twin) | 35 (0) | 38.42 -> 0 | 43.23 -> 0 | 46.22 -> 0 | f35 7.58/49.5 -> 0.72/1.6; f0 13.47/90.9 -> 0.68/2.8 | 0.86/2.4 | 43->117, 31->100 | f35 3.04 / 9.66 / 3.27; f0 3.09 / 17.76 / 3.13 | **yes** |
| P0 pot/lid (old perc2 ref) | none | v1 found no rest-contact segment (coarse overlap up to 171 cm3) | | | | | | | not carved |

(*) E28 carved: 0.26 cm / 1.8 deg until 1.85 s, then one rocking transient (2.17/11.0 at 1.9 s, 3.31/18.2 at 2.0 s); a
4 s diagnostic run (`$S/settle/E28_cut4s.json`, not a re-test) shows it back at 0.29/1.6 at 2.3 s and 0.59/1.9 at 3.8 s.
Criteria 1, 3, 4 hold for every carve: placed overlap -100 %; max overlap increase over all checked frames 0.0 cm3;
smallest piece 1.9e-11 m3 (an untouched CoACD hull), new pieces >= 2e-8 m3. Criterion 2 decides every case.
GT rel ADD = guest-in-host pose vs mocap (absolute ADD is meaningless here: the reference world frame differs from the
mocap frame by 13-32 cm). All carves are mutual (host material inside the guest's hull fill 3.1-22.6 cm3 >= 0.5).

## 4. Readings
- [M] The carve removes all rest overlap and, on the pot twins (P2 lid on pot, P26 pot in rack), turns a 4-13 cm /
  25-91 deg default collapse into < 1 cm / < 3 deg and keeps the settled pose within 0.1-0.6 cm of the reference's
  error vs mocap. On the same pairs in eval episodes (E1, E28) it halves the lid's drift and holds the pot until a late
  transient, but does not meet the pre-registered bar.
- [M] Over-removal: removed hull volume / claim volume is 1.05-1.8x on hosts but 4-13x on guests (lid 62.5 cm3 removed
  for a 4.8 cm3 claim in E1; sweeper loses 35 % of its hull volume in E30). The PCA box covers are loose on thin claim
  shells. [H] This is why the sweeper falls: test with a tighter guest-side cover on P31mck first.
- [M] The in-motion overlap at frame 44 of E14 (32.9 cm3, cup in hand during insertion) is unchanged: a rest carve
  does not address insertion contacts.
- [M] The rack itself jumps ~1 cm in the first 50 ms in E14/P12 with default AND carved hulls. [H] rack-support
  (table) interpenetration; falsify by measuring rack-support overlap at those frames.
- Pieces grow 1.3-3.4x (rack up to 117, lid 107, pot 104): more collision pairs for training [E: slower step].
