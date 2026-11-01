# C0b public results: the C0 mesh methods rebuilt without scan-derived constants

PREREG: `PREREG.md` (commit 8174998), applied exactly. Machine-readable copy: `PUBLIC_RESULTS.json`. Step log:
`NOTES.md`. Implementation deviations (written before scoring): `DEVIATIONS_PUBLIC.md`.
Labels: [M] measured without ground truth; [D] diagnostic scored against the public scans / mocap (stand-ins for the
hidden ones); [E] estimate; [H] hypothesis.

## Result

**Adopted for pack 10 (PREREG section 8: WIN and AUC-guard pass): white_pot and beige_cup.** The lid, the rack and the
blue cup are not adopted. For those three, C0's mesh (flagged, as in pack 9a) or library_v3 stays, by the owner's
choice. C0b recommends neither.

| Object | C0b pick (GT-free, PREREG 5) | fid ALL mm [M] | CD-O [D] | add_med mm [D] | flips [D] | WIN | mean / min dAUC [D] | dMPPE / dRPE cm [D] | guard | Adopted |
|---|---|---|---|---|---|---|---|---|---|---|
| white_pot | `pot/ep43/fit` | 3.407 | **0.3924** (needs <= 0.4171) | 4.94 (<= 8.69) | 0 | yes | +0.0009 / -0.0107 (9 twins) | -0.025 / -0.027 | pass | **yes** |
| white_pot_lid | none: 16/16 builds failed | - | - | - | - | no | - (twins 0, 2 missing) | - | no data | no |
| plastic_dish_rack | `rack/ep13/full` | 33.32 | 1.6324 (<= 0.5351) | 31.24 (<= 7.79) | 0 | no | -0.1325 / -0.3043 (5) | +1.160 / +1.132 | fail | no |
| blue_cup | `cup/ep21/g1` | 3.377 | 1.6770 (<= 0.5033) | 119.97 (<= 12.14) | 7 (exempt) | no | -0.5462 / -0.6273 (5) | +4.652 / +18.00 | fail | no |
| beige_cup | `beige/ep11/g1` | 3.910 | eval 10: **0.3007** (<= 0.8363); eval 8: **0.2983** (<= 0.7100) | 2.94 (<= 8.965) | 0 (exempt) | yes | +0.0139 / +0.0139 (twin 11) | -0.214 / +0.018 | pass | **yes** |

For comparison only (decides nothing) [D]:

| Object | C0b CD-O | C0 CD-O (C0b - C0) | library_v3 CD-O | C0 guard mean / min dAUC |
|---|---|---|---|---|
| white_pot | 0.3924 | 0.3417 (+0.0507) | 0.4371 | +0.0030 / -0.0159 |
| white_pot_lid | - | 0.2199 | 0.4211 | +0.0055 / 0.0000 |
| plastic_dish_rack | 1.6324 | 0.4560 (+1.176) | 0.5551 | +0.0158 / -0.0092 |
| blue_cup | 1.6770 | 0.2906 (+1.386) | 0.5233 | +0.0241 / -0.0049 |
| beige_cup | 0.3007 / 0.2983 | C1/T1 0.2475 / 0.2549 (+0.053 / +0.043) | 0.8563 (v3, eval 10) / 0.7300 (v3x, eval 8) | C1: +0.008 |

Joint c0b run (the four picks swapped together, 15 twins; reported only): mean dAUC -0.2159, min -0.9293 (ep13).

Picked meshes (`meshes/`, sha256 in `meshes/SHA256SUMS`; committed in 9f99ae0 before any scoring):
`white_pot_c0b_pot_ep43_fit.glb` (098ade9d...), `beige_cup_c0b_beige_ep11_g1.glb` (5c39b656...), and the two
non-adopted picks `plastic_dish_rack_c0b_rack_ep13_full.glb`, `blue_cup_c0b_cup_ep21_g1.glb` (kept for the record).

## What happened, per object

- **white_pot (adopted).** 32/32 candidates built and eligible. The pick ep43/fit ties ep43/nostem at 3.407 (same
  face count; the label decides; no ball got a post, so the two meshes have the same geometry). It carries 26 gmg balls
  (radii 7.5-12.4 mm, no stems). Its wall is measured, 7.21 mm (C0: 4.77 mm), and the handle bar is 1.5 mm thick (side
  evidence, at the new clip floor). [D] It wins against library_v3 (0.392 vs 0.437) but is 0.051 worse than C0.
- **white_pot_lid (no candidate).** All 16 builds (ep0, ep2 x 4 variants x a6b1/a6b2) stopped in the flange step
  (`LinAlgError`: no point fell in the A.6b flange window with the 3 sigma band). [M] GT-free reading of our own points:
  the cube-ROI lid files hold static clutter. ep2 pass B was rebuilt at 0.45 m by the cube guard; its 59 k voxel points
  span 208 x 408 x 532 mm, and robust_scale s is 107 mm against a lid of about 65 mm. So the PCA disc normal, the edge
  circle and the s-relative windows are all wrong. ep0 has 6 k points (its lid track failed in C0 too). No retry with
  changed settings (PREREG 13).
- **plastic_dish_rack (no WIN, guard fail).** 12/12 built and eligible; the fidelity values are 33-115 mm because the
  ALL points are dominated by clutter (C0's rack and library_v3 score 39.7 and 39.4 on the same points). The pick
  ep13/full carries 45 balls. Its fit hit bounds: cup-holder half-extents at their 80 / 120 mm limits, s1 = 0, s0 = T.
  [D] CD-O 1.632, add 31 mm.
- **blue_cup (no WIN, guard fail).** 5/5 built. [M] The ep21 g1 lathe body matches C0's (height 165 vs 164 mm, rmax
  46 mm, the same axis), but it carries 5 appendage blobs from 21.7 k residual points (clutter inside the cube). That
  moves the mesh centroid 29.6 mm and turns the major PCA axis 73 deg from library_v3 (frame check, reported only).
  The kit registration then fails ([D] add 120 mm, 7 flips, CD-O 1.68). Fidelity cannot see this: the ALL points
  contain the same clutter, so the blobs lower fid (3.38 vs C0's mesh 3.92 on these points).
- **beige_cup (adopted).** M_sep(own) kept 32 of 69 extraction frames, 502,266 points (qualifies). g1 (3.91) beat g0
  (5.17). The wall is measured at 1.54 mm. [D] WIN on both eval pairs and guard pass; 0.05 worse than the C1/T1 beige
  that pack 9a+C1 carries.

## Why three objects failed: the cube ROI admitted static clutter [M]

PREREG 3.4 named this risk ([H]: "the larger box admits static clutter within 30 cm while the object rests").

- **Cube guard.** It fired (> 0.1 % of kept points within 8 mm of a 0.30 m face) on 16 of 33 pass-A files and 11 of
  the 26 multi-object pass-B files; those were rebuilt at 0.45 m. Single-object pass B is a copy of pass A (D2). Pass-A
  ep21 blue_cup was still at 0.16 % at 0.45 m; its pass-B file passed at 0.30 m.
- **Kept points vs C0's `obs_all`.** Several files hold far more: ep21 blue cup 2.13 M vs 1.20 M; ep27 rack 6.86 M vs
  2.91 M; ep2 lid 2.37 M vs 1.49 M.
- **What the guard cannot do.** It only detects clipping at the faces; it cannot remove clutter. Fidelity on ALL then
  rewards meshes that explain the clutter.
- **The pot and the beige cup survived.** The pot is large and its handle and balls do not dominate. The beige cup's
  M_sep mask keeps only separated frames.

The marker detector behaved as the B7 dev notes warned (frozen settings, sha 488ac3b6): 23-69 balls per object (ep0
lid 0), with consensus radii of 9.9-12.1 mm, near the window top of 12.5 mm. The pick kept balls on the pot (26) and the rack (45).

## Hypotheses (PREREG 12)

| Hypothesis | Prediction | Outcome |
|---|---|---|
| H-C0b | each object stays a WIN vs library_v3 | **Falsified** for lid, rack and blue cup; survives for pot and beige. |
| Cost of the cleanup | each pick within 0.03 cm of C0's CD-O | **Falsified**: pot +0.051, rack +1.18, blue +1.39, beige +0.05 / +0.04 vs T1. |
| Markers | pot and rack picks are nomk or carry <= 5 balls | **Falsified**: the pot pick has 26 balls, the rack pick 45. |

## Run record

| Step | Where | Command / tool | Outputs | Result |
|---|---|---|---|---|
| Options + regression | local, code 00e8584 | prim_potlid / lathe_obs / prim_rack rebuilds (`NOTES.md`) | scratchpad `c0b/regress` | lid ep2 t2.5_fit, pot ep2 fit (+ axis), cup ep21 g1 byte-identical to C0; rack run orig vs modified 12/12 glb identical (joint = C0 rack md5 bbca8ec0) |
| Dry run | local | `C0B_LOCAL=1 ... C0B_EPS=11 C0B_STRIDE=8 bash jobs/c0b_box.sh` | scratchpad `c0b/dry` | found D1 (cube windows), then C0B-DONE |
| Box | Vast 58564958 (EPYC 7773X, 128 cores, 125 GB, Taiwan, $0.502/h) | `SETUP=none DISK=150 V2D_COMMIT=00e8584... ops/vast.sh create 57678419 mesh-20261031-c0b-00e8584 'bash docs/research/mesh-2026-10-26/cdo-sprint/C0b/jobs/c0b_box.sh'` | store `runs/mesh-20261031-c0b-00e8584/` (1598 files, 2.2 GB incl. bulk points); records `results/box/` | C0B-DONE rc=0, 66 min; created 18:22:57Z, gone 19:33:35Z; **~$0.68 [E]** (ledger planned $1.50, actual $0.68) |
| Pick | local | `python -I scripts/c0b_pick_local.py <box results> <run>` | `results/{picks,candidates_manifest}.json`, `results/fidelity_table.md`, `meshes/` | equal to the box selection for all 4 objects; committed 9f99ae0 before scoring |
| Scoring | local | `python -I scripts/score_c0b.py OBJ MESH results/score_c0b.jsonl` x 4 | `results/score_c0b.jsonl` | 4 scorings, each mesh once ($0) |
| Frame check (reported only) | local | `bash scripts/report_frame_c0b.sh results/picks.json results/frame_check_report.json` | same | C0's frame_check.py vs library_v3; kit budget OK for all 4 |
| AUC guard | local | `scripts/check_base_c0b.py`, then `C0B_OBJS="white_pot plastic_dish_rack blue_cup beige_cup" bash scripts/run_auc_guard_c0b.sh all`, then `scripts/guard_eval_c0b.py` | `results/guard_inputs_c0b.json`, `results/auc/`, `results/guard_result_c0b.json` | base reuse checks all pass (C0's 15 base runs reused); 20 single + 15 joint runs, 0 failures ($0) |

Box-side GT-free records [M]:
- **t0_C0b = 4.559 mm.** A.1 is fittable: 6 objects have >= 200 measurements. The lid had 0 measurements and the rack
  3, so both used t0_C0b.
- **sigma.** 0.83-1.69 mm; the ep26 and ep27 rack sit at the 3 mm clamp.
- **Scorings.** Run at commit 9f99ae0 (`score_c0b.py` unchanged since 00e8584); results committed in 3926430. The two parallel scoring streams wrote
  to two files, which were merged afterwards; the four meshes are distinct (sha1 5d883a54, 84195053, 92e758ad,
  7d1202e3).

## For pack 10 and E0b

- **Shipped through E0b (PREREG 9).** The adopted objects, white_pot and beige_cup, ship through E0b: the eval-built
  pick, with this public pick as the fallback (and as the 0.85 x fidelity override).
- **Lid, rack, blue cup.** E0b meshes for these are not shipped (PREREG 8).
- **Inputs for E0b.** t0_C0b = 4.559 mm (`results/box/t0_c0b.json`) is frozen. The frame-check references are
  `meshes/white_pot_c0b_pot_ep43_fit.glb` and `meshes/beige_cup_c0b_beige_ep11_g1.glb`.
  - The pot's threshold set is the other-episode public candidates, in the store run.
  - The beige cup has one public episode, so its eval frame check is reported and excludes nothing.
- **[H] Risk for E0b.** The same cube-ROI clutter will be in the eval points. The pre-registered rules are unchanged,
  so E0b can only report it.
- **Open caveat (PREREG 10).** Eval 8 was tracked with library_v3x; one beige mesh ships on both pairs.
