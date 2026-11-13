# T-I13 public: collision carve (PREREG F-I5, rule as written) on ep12, ep13, ep31, ep11, ep2, 31 Oct 2026

**In plain words.** We ran the owner's extended collision carve on the five public episodes, under the rule as it is
written (no decision of INTERLOCK 21.10 was taken). **Nothing was carved and delivered, and the simulator copies the
runs produced must not be used.** The step that fails is the one before the carve: turning each object into
cavity-preserving simulator pieces. On real data every one of the ten objects fell to the last fallback, 6 mm voxel
boxes, which keep only 1.8-9.3 % of the object's volume. With such colliders the objects barely overlap (0.0-0.5 cm3
along the whole track), so three of the five pairs have no persistent overlap left to carve, one fails the
moves-through gate, and the one pair in scope (ep11 cups) fails the physics acceptance. On the pieces the round
folders deliver, every hands-off test fails by 8-127 mm: the inner cup falls 80 mm, the cups fall out of the rack
(91-127 mm), the lid falls 81-87 mm into the pot and the sweeper 84-87 mm through the rack.

- Code: gmg modules at 1b9f0c1 (3053a78 + the report-only `diag_sink` option, PREREG F-I5.14), launched at HEAD
  cdc8b40 / 407a18e (no gmg module differs); `launch_code` in each `report.json`, sha256 of every module in each
  `drv<N>_fi5.launch`.
- Machine: this container (4 shared cores, load 14-25 from other agents' jobs), all five in parallel at nice 5,
  19:29-20:53 UTC: ep11 2716 s, ep12 3511 s, ep2 3664 s, ep13 4940 s, ep31 4952 s; candidates 19:15-19:32. No rental,
  cost $0.
- Inputs (GT-free, F-I5.8): v6 clean bundles `runs/20261031-b4ext6-90c8cce` (extract rc 0, strace audit forbidden 0;
  the v6 identity step has not run); our M1 hands of v6 (copied, sha256 in the run's `in/SOURCES.sha256`); CPU
  candidates rebuilt from v6 with `tools/interlock_cands.py`; picks shell_t5p36 (ep2 lid: hull), F-I5 body = the
  SHELL candidate. P_sim = P_sel (`sim_pose_fallback`). No scan, mocap, parquet pose, `*_align` or scan-derived constant.
- Command per episode (dev run `runs-dev/20261031-fi5pub-3053a78`): `GMG_MODE=dev nice -n 5 python -m
  gmg.tools.interlock_dev --run <run> --ep N --bundle <v6>/epN --cands <run>/cand/public/epN --pick <picks> --hands
  <run>/in/handsN/hands.npz --proxy-copies 16 --identity eval --waiver-fi5 --no-physcheck --tag fi5` (no `--video`).
- Order: ep12, ep13, ep31, ep11, ep2 launched within 3 min of each other (owner priority; the code was frozen).
- Labels: [M] measured here, [E] estimate, [H] hypothesis.

## Files
- `ep<N>/`: `fi5.json` (F-I5 report: routes, pieces gates, overlap, pairs, decisions), `report.json`, `decisions.json`
  (the flag-off F-I1..F-I3 decisions, no silhouette), `structure_<obj>.json` (lathe test), `summary.json`
  (`fi5_public_summary.py`), `figure_data.json` (`fi5_png_data.py`: overlap series, collider vs body volumes),
  `delivered_sink.json` + `.log` (`fi5_default_sink.py`, PREREG F-I5.14 (7)), driver log + launch record, candidate
  log, `r0/manifest.json` (the round folder's manifest; the pieces stay in the scratch run) and `r0/_carved_failed/`.
- Figures `build/I/png/fi5pub_ep<N>.png`: collider overlap along the track; side view of the delivered pieces (2 mm
  samples) against the SHELL bodies at the rest / S frame; S displacement.

### Pieces per object (F-I5.4 ladder)

| ep | object | lathe rotc (sigma) | routes tried | delivered pieces | delivered collider / SHELL body cm3 |
|---|---|---|---|---|---|
| 12 | blue_cup | 1.60 | 2_lathe (lathe_over_cap (with the handle)) -> 3_coacd (gate fail: 36 hulls > 0.3 cm3, max 4.864) -> 4_voxels (29 boxes at 6.0 mm) | 29 | 11.88 / 230.0 (5.2 %) |
| 12 | plastic_dish_rack | 14.61 | 3_coacd (gate fail: 75 hulls > 0.3 cm3, max 6.608) -> 4_voxels (45 boxes at 6.0 mm) | 45 | 23.33 / 357.2 (6.5 %) |
| 13 | blue_cup | 1.77 | 2_lathe (gate fail: 22 hulls > 0.3 cm3, max 2.008) -> 3_coacd (gate fail: 31 hulls > 0.3 cm3, max 5.184) -> 4_voxels (25 boxes at 6.0 mm) | 25 | 10.80 / 221.3 (4.9 %) |
| 13 | plastic_dish_rack | 12.80 | 3_coacd (gate fail: 66 hulls > 0.3 cm3, max 3.528) -> 4_voxels (24 boxes at 6.0 mm) | 24 | 11.02 / 285.3 (3.9 %) |
| 31 | mini_sweeper | 3.07 | 3_coacd (gate fail: 2 hulls > 0.3 cm3, max 0.336) -> 4_voxels (3 boxes at 6.0 mm) | 3 | 0.65 / 35.4 (1.8 %) |
| 31 | plastic_dish_rack | 9.15 | 3_coacd (gate fail: 65 hulls > 0.3 cm3, max 14.464) -> 4_voxels (47 boxes at 6.0 mm) | 47 | 20.30 / 404.8 (5.0 %) |
| 11 | blue_cup | 3.01 | 3_coacd (gate fail: 36 hulls > 0.3 cm3, max 2.992) -> 4_voxels (17 boxes at 6.0 mm) | 17 | 6.48 / 178.0 (3.6 %) |
| 11 | beige_cup | 2.60 | 2_lathe (gate fail: 16 hulls > 0.3 cm3, max 3.248) -> 3_coacd (gate fail: 29 hulls > 0.3 cm3, max 2.248) -> 4_voxels (20 boxes at 6.0 mm) | 20 | 6.91 / 170.4 (4.1 %) |
| 2 | white_pot | 2.39 | 2_lathe (lathe_over_cap (with the handle)) -> 3_coacd (gate fail: 51 hulls > 0.3 cm3, max 4.232) -> 4_voxels (42 boxes at 6.0 mm) | 42 | 23.54 / 369.9 (6.4 %) |
| 2 | white_pot_lid | 1.86 | 2_lathe (lathe_profile_complex (more than two radial intervals in a bin)) -> 3_coacd (gate fail: 16 hulls > 0.3 cm3, max 1.304) -> 4_voxels (25 boxes at 6.0 mm) | 25 | 16.85 / 180.7 (9.3 %) |

### Per pair (rule as written)

| ep | pair | collider overlap max cm3 | gates (component: voxels, run, sweep share) | scope | receiver | c mm | overshoot frames | caps: removed cm3 (share), reach, topology | S (acceptance) | P2-P7, gate | delivered | rigid shift clears |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 12 | blue_cup / plastic_dish_rack | 0.23 | blue_cup<-plastic_dish_rack#0: 6 vox, INSERTION, sweep 0.0 FAIL sweep; plastic_dish_rack<-blue_cup#1: 9 vox, SEAT, sweep 0.0 FAIL sweep | out | - | - | - | - | - | - | default | - |
| 13 | blue_cup / plastic_dish_rack | 0.00 | no component | out | - | - | - | - | - | - | default | - |
| 31 | mini_sweeper / plastic_dish_rack | 0.00 | no component | out | - | - | - | - | - | - | default | - |
| 11 | blue_cup / beige_cup | 0.48 | blue_cup<-beige_cup#0: 3 vox, SEAT, sweep 1.0; blue_cup<-beige_cup#1: 4 vox, SEAT, sweep 0.0 FAIL sweep; beige_cup<-blue_cup#2: 11 vox, SEAT, sweep 1.0 | in | beige_cup | 1.00 | 7 | 0.68 cm3 (10.0 %), reach -, topology kept | f126: carved 31.6 mm / 42.4 deg, default 80.5 mm / 67.9 deg | P2:ok P3:FAIL P4:FAIL P5:ok P6:ok P7:ok gate:ok | default | 100 % of 11 |
| 2 | white_pot / white_pot_lid | 0.16 | white_pot<-white_pot_lid#0: 3 vox, SEAT, sweep 0.0 FAIL sweep; white_pot_lid<-white_pot#1: 4 vox, SEAT, sweep 0.0 FAIL sweep | out | - | - | - | - | - | - | default | - |

### S on the delivered pieces (diagnostic, PREREG F-I5.14 (7); decides nothing)

| ep | pair | receiver (fixed) | S frame | displacement mm | drop dz mm | lateral mm | tilt deg | S (4 mm, 5 deg) |
|---|---|---|---|---|---|---|---|---|
| 12 | blue_cup / plastic_dish_rack | plastic_dish_rack | f176 | 126.8 | 60.4 | 111.4 | 99.9 | FAIL |
| 12 | blue_cup / plastic_dish_rack | plastic_dish_rack | f6 | 8.2 | -6.1 | 5.4 | 3.8 | FAIL |
| 13 | blue_cup / plastic_dish_rack | plastic_dish_rack | f146 | 90.6 | 28.9 | 85.1 | 115.3 | FAIL |
| 31 | mini_sweeper / plastic_dish_rack | plastic_dish_rack | f282 | 84.2 | 84.1 | 1.8 | 26.0 | FAIL |
| 31 | mini_sweeper / plastic_dish_rack | plastic_dish_rack | f8 | 86.7 | 86.7 | 1.7 | 24.5 | FAIL |
| 11 | blue_cup / beige_cup | beige_cup | f126 | 80.5 | 67.7 | 32.7 | 67.9 | FAIL |
| 2 | white_pot / white_pot_lid | white_pot | f24 | 84.8 | 80.6 | 26.4 | 12.5 | FAIL |
| 2 | white_pot / white_pot_lid | white_pot | f328 | 88.0 | 87.1 | 12.7 | 6.2 | FAIL |

## Predictions (PREREG F-I5.9)
| | outcome |
|---|---|
| P41 ep11 cups lathe route, gate pass, no ring | **falsified**: blue cup rotc 3.013 sigma (not lathe; B7 dev bundle 1.61); beige cup lathe pieces fail the gate (16 hulls > 0.3 cm3, its 6 handle components); both end as 6 mm boxes |
| P42 ep11 default overlap <= 109 cm3 | holds, **trivially**: 0.48 cm3, because the colliders keep 3.6-4.1 % of the cups |
| P43 ep11 S and P2-P7 pass | **falsified**: S fails (carved 31.6 mm / 42 deg, default 80.5 mm / 68 deg), P3 (12.3 deg lag) and P4 (removed 0.68 > 1.5 x 0.41 cm3) fail |
| P44 cups' c 0.05-0.2 mm, or 1.0 mm with the base in the pocket | c = 1.0 mm (sigma_sup 0.999); **void as a test**: a box collider has flat bottoms, so sigma_sup = 1 whatever the cup |
| P45 ep2 pot route 3/4, lid lathe, receiver pot, S and P2 pass | **falsified**: the lid fails the lathe profile (3 intervals); the pair is out of scope (sweep 0.0); the delivered lid falls 81-87 mm |
| P46 ep12 / ep13 rack by route 3, receiver rack, S passes | **falsified**: route 4 on both racks; both pairs out of scope; the delivered cups fall 91-127 mm |
| P47 ep31 delivered sweeper drop <= 4 mm, tilt <= 5 deg | **falsified**: 84-87 mm, 24-26 deg (delivered-pieces S) |
| P48 ep11 rigid shift clears >= 75 % | holds, **trivially**: 11 / 11 frames at 0 mm (every frame's overlap <= 0.51 cm3, under the 2 cm3 clear level) |
| P49 eval twins match | not tested: no eval bundle exists |

## Rigid-shift alternative (F-I5.7)
Computed only for the in-scope pair (ep11): cleared at 0 mm on 11 / 11 frames. As built, `FI5.apply` computes it inside
the in-scope branch only (F-I5.7 says every pair); for the other pairs the collider overlap along the track is at most
0.23 cm3 (stride 4), under the 2 cm3 clear level, so the shift would also be 0 mm [M from the overlap series]. With
these colliders the report says nothing about pose errors.

## Mechanisms [M unless marked]
1. **CoACD fills the piece cap, so the keep-out repair never runs.** Route 3 calls CoACD 0.02 with max_convex_hull =
   the cap (82); it returned 82 hulls for 9 of the 10 objects (80 for the ep13 rack, which then got 2 splits). The
   repair splits only while the cap allows, so 0 splits; 2-75 hulls per object stay over 0.3 cm3 of keep-out (max
   0.34-14.5 cm3) and the gate fails (CoACD time 287-1383 s per object under load).
2. **The lathe route fails on our SHELL candidates, though its rings are continuous.** Where rings were built (ep12
   and ep13 blue cups, ep11 beige cup, ep2 pot: 8-12 sectors, 56-73 ring pieces, 0 gaps on 82,080-144,720 continuity
   rays) the set failed through the "handle" step: shell material outside the revolved body by > 3 sigma in components
   >= 0.3 cm3 (ep12 blue 15 components / 22.1 cm3, ep13 blue 10 / 29.8, ep11 beige 6 / 31.5, pot 8 / 68.3), each
   decomposed and added: over the 82 cap (ep12 blue, pot) or the gate fails (ep13 blue 22 hulls, ep11 beige 16 hulls
   over 0.3 cm3; which hulls, rings or handle pieces, was not logged). Elsewhere: rotc 3.013 sigma (ep11 blue, the
   threshold is 3) and three radial intervals in a bin (ep2 lid). [H] the cups' "handle" components are SHELL
   residuals (the blue cup has no handle); falsifier: they cluster at one azimuth and persist across frames' points.
3. **Route 4 coarse grids keep only cells wholly inside the body.** 2 and 4 mm boxes exceed the 82 cap, and at 6 mm a
   cell is kept only if all 27 of its 2 mm cells are inside, which a 3-5 mm wall almost never satisfies: 3-109 cells
   per object, 1.8-9.3 % of the SHELL volume. The gate passes by construction (no keep-out), so the rule delivers them.
4. **Downstream:** with near-empty colliders the collider intrusion is 0.0-0.5 cm3, so most pairs have no persistent
   component (ep13, ep31) or tiny ones that fail the sweep share (ep12, ep2: 0.0); ep11's 11-voxel component passes,
   carves 0.41 cm3 inside the body, and S fails because the guest falls through the boxes.

## What this means and what needs deciding (orchestrator / owner; each a dated PREREG entry before any run uses it)
- The F-I5 round folders of this run (`<scratch>/gmg/runs-dev/20261031-fi5pub-3053a78/sim/public/ep*-fi5/r0`) **must
  not be used**: they pass the rule's pieces gate but none holds its objects (table above). They were not uploaded or
  packed anywhere.
- The default-pieces ladder (F-I5.4) needs a change before any carve question can be asked on real data, e.g. [H]:
  (a) CoACD with max_convex_hull below the cap (room for the repair); falsifier: the repaired set still has hulls over
  0.3 cm3 at the cap on these 10 objects; (b) a delivery floor that is physical, not only keep-out: delivered collider
  volume vs body volume, and S on the delivered default pieces, with do-not-use when it fails; (c) the lathe handle
  test (residual components) bounded so that noise does not push a good ring set over the cap; falsifier: the ring
  set without the residual hulls fails the gate or S on the same pairs.
- INTERLOCK 21.10's open decisions (carve geometry, c for nests, topology grid, the 10 % / 0.6 caps for non-plates,
  exact R+ clip) remain open and are downstream of this one.
- Eval twins (10, 1, 14, 30): still blocked (no eval bundles), and pointless until the pieces step is fixed.
