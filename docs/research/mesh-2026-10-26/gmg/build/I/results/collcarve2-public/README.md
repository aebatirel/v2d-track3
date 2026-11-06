# T-I16 public: collision carve round 2 (PREREG F-I5.15 / F-I5.16, as built F-I5.17) on ep11, ep2, ep12, ep13, ep31, 1 Nov 2026

**In plain words.** We re-ran the collision carve on the five public episodes with the round-2 rules: ring pieces that
cannot reach into a cup's opening, CoACD asked for half the piece cap so that its repair can split, a pose check before
any hands-off test, a delivery floor (keep at least half of each shape) and the contact budget. **Nothing was carved and
delivered, and all five round folders are marked do-not-use.** Two steps fail on our real shapes:
- **No object gets usable collision pieces.** The new ring pieces fail on every cup and on the pot. The rule makes each
  ring slice stay outside every measured point of the cup's inner surface and inside every point of its outer surface.
  Our SHELL shapes have thin stray sheets inside the cavity, near the floor and on the handle, and a single such ray
  pulls a slice's wall 21-173 mm below zero. CoACD plus the repair then still leaves 1-22 pieces filling the openings.
  So all ten objects fall back to 6 mm boxes again, which keep only 2-9 % of each shape (the floor asks for 50 %).
- **Every hands-off test frame is impossible as tracked.** At every frame where the two objects touch, our tracked poses
  make the two shapes cross each other's walls. Examples: the ep11 cups overlap by 77-85 cm3, the ep2 lid sits 21-27
  cm3 inside the pot's rim, and the ep12 / ep13 cup overlaps the rack's wires. In ep13 the cup also sits 5.7 mm inside
  the table. The ep31 sweeper floats 12 mm from the rack. The rule therefore runs no hands-off test and no contact
  count; these frames go to the pose lanes' list. A side check (it decides nothing) confirms the precheck: even on
  faithful copies of our shapes the guest moves 4.8-13 mm at every such frame, and on the delivered boxes it falls
  through by 54-110 mm.

Our own points also show no cup-in-cup nest in ep11: the two cups' rims stand within 3.3 mm of each other. So a real
nest is tested only on synthetic cups. Eval 10 is the only real nest, and it has no public twin. Machine: this
container, 90 min, no rental, $0.

- Code: commit 88f49df (gmg modules unchanged since ba3387d except the test rename; `launch_code` in every
  `report.json`, sha256 of every module in `ep<N>/drv<N>_fi5r2.launch`). Round-2 driver
  `gmg/tools/collcarve2_dev.py --fi5-rev 2` around the unedited shared `tools/interlock_dev.py`.
- Machine: this container (4 shared cores; load 6-11 from other agents' jobs). All five ran in parallel at nice 5 in
  one scheduler group. The group got about 1 core until 00:46, then about 2 (autogroup weight of my own group set to
  nice -3). Launched 00:18:23 UTC; done ep11 01:30:56 (4,349 s), ep31 01:33:43 (4,516 s), ep13 01:40:52 (4,945 s),
  ep12 01:45:43 (5,236 s), ep2 01:48:11 (5,384 s). No rental, cost $0.
- Inputs (GT-free, F-I5.8): the same as round 1, copied byte-identical from `runs-dev/20261031-fi5pub-3053a78`
  (`inputs.sha256`): the v6 clean bundles `runs/20261031-b4ext6-90c8cce`, our M1 hands of v6, and the round-1 CPU
  candidates and picks (shell_t5p36; ep2 lid: hull). The F-I5 body is the SHELL candidate (shell_t5p36 for every
  object). P_sim = P_sel (`sim_pose_fallback`). No scan, mocap, parquet pose, `*_align` or scan-derived constant.
- Command per episode (run `<scratch>/gmg/runs-dev/20261101-fi5r2pub-88f49df`): `GMG_MODE=dev nice -n 5 python -m
  gmg.tools.collcarve2_dev --fi5-rev 2 --run <run> --ep N --bundle <v6>/epN --cands <run>/cand/public/epN --pick
  <picks> --hands <run>/in/handsN/hands.npz --proxy-copies 16 --identity eval --waiver-fi5 --no-physcheck --tag fi5r2`.
- Labels: [M] measured here, [E] estimate, [H] hypothesis. Timed log: `build/I.md`, section "Collision carve round 2",
  entries 00:17-02:06 tagged (T-I16).

## Files
- `ep<N>/`: `fi5.json` (the round-2 report: routes with every layout candidate, pairs, components, precheck), `report.json`,
  `decisions.json` (flag-off decisions), `structure_<obj>.json`, `push_list.json`, `manifest.json`, driver log and
  launch record, `summary.json` (`build/I/fi517_public_summary.py`), and `r0/`: the round folder's records
  (`manifest.json`, `props_gmg.json`, `floor.json`, `contact_gate.json`, `push_list_fi5r2.json`, **`DO_NOT_USE.json`**,
  `CONTACT_GATE_PENDING.json`). The pieces stay in the scratch round folders `<run>/sim/public/ep<N>-fi5r2/r0`.
- `tables.md`: the tables below as generated.
- `diag/` (report only, decides nothing): `precheck_r1frames.json` (the precheck at round 1's S frames, P77 / P78,
  `build/I/fi515_precheck_r1frames.py`), `l0_ep11.json` (L0, P90, `build/I/fi515_l0_ep11.py`),
  `profile_ep<N>_<obj>.json` (why the ring search fails, `build/I/fi517_diag_profile.py`), `s_diag.json` (S at the
  floor frames although the precheck failed there, `build/I/fi517_s_diag.py`).
- Round-1 markers (F-I5.15 (4e)): `DO_NOT_USE.json` was added at 00:16 to the five round-1 scratch round folders
  `runs-dev/20261031-fi5pub-3053a78/sim/public/ep*-fi5/r0`. Contrary to F-I5.17 (13), they do exist on this machine;
  `build/I/fi515_round1_markers.py` had looked under the repo root. The copies next to the committed round-1
  manifests had been written by the build step.

## Pieces per object (F-I5.15 / F-I5.16 ladder) [M]

| ep | object | lathe test (rotc sigma) | route 2: rings (smallest layout) | route 3: CoACD 41 + repair to 82 | delivered | share of SHELL volume (floor 0.5) |
|---|---|---|---|---|---|---|
| 12 | blue_cup | yes (1.60) | no layout: 42 candidates (8-20 sectors, b1 / b2, 17-81 pieces), every one fails (i) min wall, -35.1 to -55.2 mm | 41 + 41 splits = 82; gate fails (12 hulls > 0.3 cm3, max 0.48) | route 4: 29 boxes (6 mm) | 0.050 |
| 12 | plastic_dish_rack | no (14.61) | - | 41 + 41 = 82; fails (22, max 0.98) | 45 boxes | 0.061 |
| 13 | blue_cup | yes (1.77) | no layout: 42 candidates, all (i), -31.8 to -88.4 mm | 41 + 34 = 75 (repair stopped: its own max 0.272); gate fails (7, max 0.70) | 25 boxes | 0.049 |
| 13 | plastic_dish_rack | no (12.80) | - | 41 + 41 = 82; fails (11, max 0.78) | 24 boxes | 0.036 |
| 31 | mini_sweeper | no (3.07) | - | 41 + 4 = 45 (repair stopped: 0.28); gate fails (1, max 0.344) | 3 boxes | 0.018 |
| 31 | plastic_dish_rack | no (9.15) | - | 41 + 41 = 82; fails (22, max 1.74) | 47 boxes | 0.047 |
| 11 | blue_cup | no (3.01) | - | 41 + 40 = 81 (repair stopped: 0.296); gate fails (21, max 1.55) | 17 boxes | 0.038 |
| 11 | beige_cup | yes (2.60) | no layout: one wall run, no solid run (bottomless, B3); 60 candidates, all (i), -21.2 to -36.1 mm | 41 + 32 = 73 (repair stopped: 0.296); fails (5, max 0.44) | 20 boxes | 0.038 |
| 2 | white_pot | yes (2.39) | no layout: 42 candidates, all (i), -49.5 to -172.9 mm | 41 + 41 = 82; fails (9, max 1.14) | 42 boxes | 0.061 |
| 2 | white_pot_lid | yes (1.86) | `lathe_profile_complex` (more than two radial intervals in a bin) | 41 + 17 = 58 (repair stopped: 0.296); fails (10, max 0.49) | 25 boxes | 0.086 |

No ring candidate got past check (i), so cavity intrusion (check (ii)) and continuity (iii) were never measured on a
real object. The delivered boxes hold no keep-out by construction (route 4 keeps only 6 mm cells wholly inside the
body). The route-2 search itself took 51-101 s per object. Most of the CPU went to the structure test (701-2,008 s per
object) and route 3 (CoACD plus the repair, 214-771 s per object).

## Per pair: scope, precheck at the S frames, carve [M]

| ep | pair | collider overlap max cm3 | scope (gates) | receiver | S frames: precheck | carve | delivered |
|---|---|---|---|---|---|---|---|
| 12 | blue_cup / plastic_dish_rack | 0.23 | out: blue_cup<-rack#0 6 vox INSERTION, rack<-blue_cup#1 9 vox SEAT, both sweep 0.0 (fail) | - | - | - | default |
| 13 | blue_cup / plastic_dish_rack | 0.00 | out: no component | - | - | - | default |
| 31 | mini_sweeper / plastic_dish_rack | 0.00 | out: no component | - | - | - | default |
| 11 | blue_cup / beige_cup | 0.48 | in: beige_cup<-blue_cup#2 11 vox SEAT, sweep 1.0 (and blue_cup<-beige_cup#0 3 vox) | beige_cup | f126: fails (c): V_ov 85.2 cm3, removed share 0.53, 1 mm topology 2 / 79 -> 119 / 127 (components / tunnels), 0.05 mm wall left | not carved: `pose_impossible_all` | default |
| 2 | white_pot / white_pot_lid | 0.16 | out: 3 / 4 vox SEAT, sweep 0.0 (fail) | - | - | - | default |

The collider overlap is measured on the delivered 6 mm boxes. With colliders this small, the scope gates see almost
nothing, as in round 1.

## Floor S frames: precheck, S on the delivered pieces, S on the faithful reference [M]

The floor frames are the middles of up to 3 hands-off static segments where the faithful colliders are within 4 mm. The
receiver is chosen by containment on the faithful colliders. Every frame fails the precheck, so the rule runs no S and no
S_ref there (F-I5.15 (3)). The S columns come from the report-only diagnostic `diag/s_diag.json`: delivered pieces with
16 copies, faithful 2 mm SHELL boxes with 4 copies. It decides nothing.

| ep | pair (receiver <- guest) | frame | precheck (rule) | S delivered, 16 copies: disp / dz (+ down) / tilt | S faithful 2 mm boxes, 4 copies: disp / dz / tilt (s) | rule outcome |
|---|---|---|---|---|---|---|
| 12 | plastic_dish_rack <- blue_cup | f176 | FAIL c (a -3.08 mm; V_ov 7.408 cm3) | 130.9 / +58.5 / 85.1 deg: fail | 13.2 / -4.6 / 9.8 deg: fail (43) | pose_impossible: no S, pushed |
| 13 | plastic_dish_rack <- blue_cup | f181 | FAIL a, c (a -5.73 mm; V_ov 2.656 cm3) | 121.8 / +53.8 / 121.3 deg: fail | 12.2 / -7.0 / 8.6 deg: fail (29) | pose_impossible: no S, pushed |
| 31 | plastic_dish_rack <- mini_sweeper | - | s_floor_vacuous (faithful gap at the hands-off segments: f285 12.0 mm, f278 11.9 mm) | - | - | no S |
| 11 | beige_cup <- blue_cup | f127 | FAIL c (a 3.14 mm; V_ov 84.504 cm3) | 96.2 / +91.2 / 50.2 deg: fail | 10.1 / +1.9 / 6.4 deg: fail (222) | pose_impossible: no S, pushed |
| 11 | beige_cup <- blue_cup | f108 | FAIL c (a -2.71 mm; V_ov 76.728 cm3) | 122.0 / +110.3 / 148.8 deg: fail | 9.8 / +2.7 / 13.9 deg: fail (164) | pose_impossible: no S, pushed |
| 2 | white_pot <- white_pot_lid | f13 | FAIL c (a 61.29 mm; V_ov 23.848 cm3) | 84.8 / +80.7 / 13.5 deg: fail | 5.0 / -1.2 / 7.8 deg: fail (115) | pose_impossible: no S, pushed |
| 2 | white_pot <- white_pot_lid | f32 | FAIL c (a 60.75 mm; V_ov 26.976 cm3) | 86.4 / +82.7 / 9.7 deg: fail | 7.9 / -6.1 / 9.6 deg: fail (127) | pose_impossible: no S, pushed |
| 2 | white_pot <- white_pot_lid | f316 | FAIL c (a 62.33 mm; V_ov 20.92 cm3) | 87.6 / +85.1 / 13.4 deg: fail | 4.8 / -2.3 / 6.1 deg: fail (107) | pose_impossible: no S, pushed |

- The S diagnostic was launched at 01:49 and done at 02:04 (nice 5, this container). Same scene, jitters and measures as
  the floor's S (`collcarve.sink_test2`: receiver fixed at its tracked pose, guest free, our table plane, 0.3 kg, 2 s
  at 2 ms, pass at a mean of 4 mm and 5 deg). [M] On the delivered boxes the guest falls through: 54-110 mm down and 85-131
  mm displaced. On the faithful SHELL boxes it is pushed 4.8-13.2 mm and tilted 6.1-13.9 deg: out of the table in ep13
  (dz -7.0 mm), out of the rack's wires in ep12 (-4.6 mm), up out of the pot's rim in ep2 (-1.2 to -6.1 mm), and
  sideways out of the overlapping cup in ep11 (9.3-9.9 mm lateral). So with faithful shapes too, S fails at every
  floor frame, because the tracked poses interpenetrate. This is the case the precheck now removes from the test,
  consistent with verify_cc_1 B2 at round 1's frames.

- Precheck thresholds (F-I5.15 (3), informed: s_max = 4 mm, S's own bound F-I1.14): (a) guest lowest faithful point
  more than 4 mm below our table plane; (b) more than 4 mm from both the table and the receiver; (c) overlap V_ov > 0
  that no allowed carve can remove (the receiver SHELL minus the guest SHELL fails the 1 mm topology rule or the
  1.5 mm wall rule).
- **Every frame with overlap fails (c) with 0.05 mm of wall left.** The guest's SHELL crosses the receiver's wall, so
  removing the overlap would cut through it. This is the pose error of verify_cc_1 B2, now caught before the test.
- Push list for the pose lanes (`r0/push_list_fi5r2.json`): ep11 3 entries (f126, f127, f108), ep2 3 (f13, f32, f316),
  ep12 1 (f176), ep13 1 (f181), ep31 0. ep31 has no floor frame at all (`s_floor_vacuous`): at its two hands-off
  segments (mid f285, f278) the faithful sweeper is 12.0 / 11.9 mm from the faithful rack.

## Contact gate (F-I5.16) [M]

| ep | gated scenes | G1 | packed default (FlashCHORD's CoACD 0.05 on our visual mesh, coacd 1.0.11), hulls | G2 (budget.py, <= 380 rows) |
|---|---|---|---|---|
| 12 | 0 (every frame pose_impossible) | `contact_gate_pair_vacuous` | blue_cup 103, rack 37 | pending |
| 13 | 0 | vacuous | blue_cup 66, rack 24 | pending |
| 31 | 0 (no floor frame) | vacuous | sweeper 98, rack 46 | pending |
| 11 | 0 (settle f126 pose_impossible, report only) | vacuous | blue_cup 58, beige_cup 47 | pending |
| 2 | 0 | vacuous | white_pot 41, lid 61 | pending |

G1 ran in plain MuJoCo 3.17.0 under the sim=rl limits read from `docs/research/work/15-verify/cfg_sim_rl.yaml` (sha256
695536b7...4b66: njmax 512, nconmax 256, Newton, implicitfast, pyramidal, impratio 20, 100 / 50 iterations). It had
nothing to gate. G2 cannot run here: there is no mujoco_warp, warp, newton or FlashCHORD tree. Each folder has
`CONTACT_GATE_PENDING.json`; none is a candidate for G2 anyway, because each is do-not-use on the floor. Caveat: G2
uses zero-action rollouts, and a grasping policy may add hand-object contacts.

## Delivery [M]

| ep | floor (share >= 0.5; S where S_ref passes) | G1 | G2 | `r0/DO_NOT_USE.json` |
|---|---|---|---|---|
| 12 | fail: shares 0.050 / 0.061; S part vacuous | vacuous | pending | **yes** |
| 13 | fail: 0.049 / 0.036 | vacuous | pending | **yes** |
| 31 | fail: 0.018 / 0.047 | vacuous | pending | **yes** |
| 11 | fail: 0.038 / 0.038 | vacuous | pending | **yes** |
| 2 | fail: 0.061 / 0.086 | vacuous | pending | **yes** |

## Precheck at round 1's S frames (P77, P78; `diag/precheck_r1frames.json`) [M]

| ep, frame | receiver <- guest | (a) lowest above table, mm | (b) table / receiver gap, mm | (c) V_ov cm3, topology (C / T), wall left | fails | prediction |
|---|---|---|---|---|---|---|
| 12 f6 | rack <- blue_cup | -15.1 | 0 / 49.1 | 0 | (a) | P77 holds |
| 12 f176 | rack <- blue_cup | -3.1 | 0 / 0 | 7.4, 7/72 -> 22/67, 0.05 mm | (c) | not in P77 |
| 13 f146 | rack <- blue_cup | -23.3 | 0 / 0 | 3.2, 13/85 -> 19/87, 0.05 mm | (a), (c) | P77: (a) as predicted, but (c) too: a miss by its "fails another check" clause |
| 31 f282 | rack <- sweeper | +46.9 | 46.9 / 11.3 | 0 | (b) | P77 holds |
| 31 f8 | rack <- sweeper | +48.0 | 48.0 / 33.3 | 0 | (b) | P77 holds |
| 11 f126 | beige <- blue | +3.3 | 3.3 / 0 | 85.2, 2/79 -> 119/127, 0.05 mm (removed 0.53) | (c) | P77 holds |
| 2 f24 | pot <- lid | +60.9 | 60.9 / 0 | 24.6, 8/44 -> 24/80, 0.05 mm | (c) | P78 holds (passes (a), (b)) |
| 2 f328 | pot <- lid | +62.8 | 62.8 / 0 | 23.7, 8/44 -> 20/75, 0.05 mm | (c) | P78 holds |

## A real nest? (F-I5.15 (5), L0, P90; `diag/l0_ep11.json`) [M]

- ep11 is the only public episode with two cups. The roster has blue cup + rack (ep12, ep13) and blue cup + pitcher
  (ep21, ep22).
- L0: over the pair's hands-off static segment f116-136 (= the run's assembled stretch; points at the 11 even frames),
  the 99th-percentile height above our table of each cup's own points is 193.5 mm for the blue cup (44,391 points) and
  196.8 mm for the beige cup (79,909 points), 3.3 mm apart. **P90 is falsified** (< 5 mm). Our observations do not show
  one rim standing above the other. Both SHELLs are bottomless (B3). At f126 the guest's lowest point is 3.3 mm above the table
  (verify_cc_1: both cups at 3.2-3.4 mm), while the two SHELLs overlap by 85 cm3. [H] Both tracks lock onto the same stack. Falsifier: the per-frame
  identity / B.2a step on v6.
- So **no public episode has a real cup-in-cup nest that our data represent; the nest is tested on synthetic cups only
  (T-I14), and eval 10 (beige in blue, 3-5 mm off axis) is the only real nest, with no public twin.** Under F-I5.15 (7)
  eval 10 is not carved anyway (off axis), and pose correction remains its remedy.

## Predictions (PREREG F-I5.15 (9) P71-P92 and F-I5.16 (4) P93-P103, the T-I16 legs)

| | outcome |
|---|---|
| P71 ring intrusion on T-I15 / T-I16 objects | **not tested**: no candidate passed check (i), so intrusion was never computed on a real object |
| P72 / P93 cups and pot at N_s >= 12 (the pot not at 12) | P93's falsifier (a cup or pot accepted at 8, the pot at 12, a cup above 16) is not met, but only because **no layout is accepted at all**. Its [H] leg (the cups land at 12 or 16) misses |
| P73 ep11 beige and ep12 blue default rings pass continuity and the gate | **falsified**: neither reaches continuity (min wall -21 to -55 mm) |
| P74 / P94 every route-2 cup and pot keeps >= 0.5 / has an accepted candidate | **falsified**: all four fall to route 3 and then route 4 (shares 0.038-0.061) |
| P75 racks still fail route 3, end in route 4 | **holds** (ep12, ep13, ep31; ep26 / ep27 are T-I15, not run) |
| P76 sweeper and lid pass route 3 | **falsified**: sweeper 1 hull over 0.3 cm3 (0.344), lid 10 (max 0.488) |
| P77 precheck fails at round 1's S frames as listed | 4 of 5 frames as predicted; ep13 f146 also fails (c): **a miss** by the "fails another check" clause |
| P78 ep2 S frames pass (a) and (b) | **holds** (f24, f328; also at the round-2 floor frames f13, f32, f316) |
| P79 no public pair gets a carve delivered | **holds** |
| P80 ep12, ep13, ep31 DO_NOT_USE | **holds** (on the share, as are ep11 and ep2) |
| P90 L0 rims differ >= 5 mm | **falsified** (3.3 mm) |
| P99 no gated G1 scene overflows | **vacuous**: no gated scene |
| P100 ep2 lid fails the G1 ratio; ep2 DO_NOT_USE | ep2 is DO_NOT_USE on the floor share. The G1 leg is **untested**: the lid's route-3 set was not delivered, and no ep2 frame was gated |
| P101 packed defaults of the T-I16 cups and pot fail the keep-out gate | **not tested**: the run records only the packed piece counts (41-103 hulls), not their keep-out |
| P102 G2 <= 380 rows | **not run** (no FlashCHORD environment here; nothing to hand off: all folders are do-not-use) |

## Mechanisms [M unless marked]
1. **B4: the exact per-ray ring envelopes collapse on stray SHELL rays.** F-I5.15 (1b) puts each slice's inner face
   outside r_in, and its outer face inside r_out, of EVERY construction ray of the sector band (1 deg x 1 mm), taken on
   the innermost radial interval. Our SHELLs have rays whose innermost interval ends far inside the wall
   (`diag/profile_*.json`; counted: rays whose r_out is > 10 mm below the row's median):
   - ep13 blue cup: 3,852 such rays in 64 of 173 wall rows at 272 of 360 azimuths, at 0.41-0.62 of the median radius,
     spread up the cavity (median 46.5 mm above the base). Example: h -85.6 mm, phi 344 deg, [5.80, 5.81] mm against a
     row median of 31.7 mm.
   - ep12 blue cup: 617 in 40 rows, 71 % within 15 mm of the base (the floor / fillet region).
   - pot: 2,526 in 46 rows (54 % within 15 mm of the base), plus handle rows where the innermost interval runs out to
     254 mm (the handle fused to the wall).
   - beige cup: only 25 such rays, but 40 % of its construction rays hit nothing (completed by the sector median), and
     there is no solid run.
   One such ray makes the outer envelope lie inside the inner one: walls of -21 to -173 mm, 10-20 of 12-24 wall pieces
   dropped as negative walls, and check (i) fails on every candidate. [H] A robust profile would keep these cups:
   instead of the innermost interval, take the interval that holds the row's median wall (or a sector quantile).
   Falsifier: with that profile, the 12-sector min wall of the ep12 / ep13 blue cups stays < 1.5 mm.
2. **The repair and the gate measure keep-out on different grids.** In 5 of 10 objects the repair stopped below the
   cap because its own measure said every hull held <= 0.3 cm3 (0.272-0.296). The gate then found 1-21 hulls over (max
   0.344-1.552). The cause is in the code (`cavpieces.keepout`). The repair scores keep-out on a 2 mm grid anchored at
   the original CoACD hulls' bounds. The gate re-samples a grid anchored at the repaired hulls' bounds. For thin hulls,
   a shift of the grid changes the count by many cells. [H] H-d: with one fixed grid in both, the lid, the sweeper and
   the beige cup pass route 3. Falsifier: they still fail the gate on the same grid. The racks need the full cap either
   way (11-22 hulls over at 82).
3. **The precheck catches every test frame.** Every frame where the shapes touch has the guest's SHELL crossing the
   receiver's wall (wall left 0.05 mm, topology broken). ep13 f181 also has the cup 5.7 mm inside the table, and ep31
   floats. This matches verify_cc_1 B2 (faithful S fails at all round-1 frames) and makes the hands-off test and the
   contact gate vacuous on public data.
4. **Route 4 cannot meet the floor.** At 6 mm, a cell is kept only if it lies wholly inside a 3-5 mm wall, which almost
   never happens: 3-47 boxes, 1.8-8.6 % of the SHELL. So the floor marks every folder do-not-use, as F-I5.15 meant it
   to for round 1's boxes.

## What this means and what needs deciding (orchestrator / owner; each a dated PREREG entry before any run uses it)
- Do not use any F-I5 round-2 public folder (`DO_NOT_USE.json` in all five). Nothing was uploaded or packed.
- The blocking step is still the default pieces on real SHELLs, not the carve. Two cheap, falsifiable changes are
  open: B4's robust ring profile (a rule change to F-I5.15 (1a) / (1b)), and H-d's single keep-out grid (a code-level
  measurement fix that changes route-3 outcomes, so it also needs an entry).
- Even with good pieces, no public pair would reach the hands-off test: every touching frame is `pose_impossible`. The
  carve can only be exercised on real data after pose correction, or on the eval twins' references (the eval precheck
  lane).
- Not run in this step: T-I15 (held-out pieces), T-I17 c1 (the ep24 v6 bundle is not on this machine), G2, and the eval
  twins.
