# posefix: physics rest projection of our tracked poses, public episodes: result (1 Nov 2026)

**Verdict: the gate fails. The fix is not proposed for eval.** Rule A gives mean dAUC **-0.0107** over the 20 public
episodes. The gate needs >= +0.002. The worst episode is ep41 at **-0.0342** (the floor is -0.01). 17 episodes get
worse, 1 gets better (ep18, +0.0061) and 2 are unchanged. MPPE worsens by +0.128 cm and RPE by +0.087 cm on average.
All numbers are [D]: public episodes, our perception tracks, public scans standing in for the hidden ones.

Labels: [M] measured, [D] diagnostic (scored against public ground truth), [E] estimate, [H] hypothesis.
Pre-registration: `PREREG.md`, pushed as df60ff2 (04:53:42 UTC) before any scoring step. The transformed tracks'
sha256 were pushed as 4ef1305 (05:14:39 UTC) before the scoring inputs were staged. Results: e3b1fcd.

## 1. In plain words

At frames with no hand near an object, our tracked poses often put objects inside each other or inside the table. We
tested a fix that moves the object at rest by the smallest rigid shift that clears the overlap, held over the stretch.
On public data it makes the poses **worse**, not better.

- **Direction check.** The shift points away from the truth more often than toward it. Its cosine with the true
  correction is <= 0 on 28 of 50 shifted segments, so the prediction is falsified as the brief wrote it.
  - For segments with a pair overlap, the direction is mostly right (11 of 16 positive).
  - But the shifts are too large: a median 5.7 times the error component along them (where that is positive). The
    position error fell on only 3 of 50 segments.
- **Mesh check.** It shows why the shifts are too large. The overlaps come mostly from our meshes, not from our poses.
  - Placed exactly at the true (mocap) poses, our meshes still overlap: the ep11 cups by 65 cm3, the ep2 lid and pot
    by 5.9 cm3, the ep31 sweeper and rack by 11.1 cm3 (more than at our own poses), and the ep24 boards by 9.9 cm3.
  - Our C0 pot mesh reaches 6.9-8.3 mm below the real pot's base in all 9 pot episodes. The v3 pitcher reaches 7-11 mm
    below.
  - So the "pot in the table" seen in our tracks is the mesh, and lifting the pose out of the table moves a nearly
    correct pose by 6-12 mm.
  - Only the cup in the rack (ep12, ep13) is half pose error. There the shift (a 17 mm lift on ep12) overshoots too.
- **Report-only variants.** All of them are also negative:
  - no shift at frame 0 (C): -0.0051;
  - pair overlaps only, no table (D): -0.0024, 4 episodes changed, all worse;
  - support drop added (B): -0.0106.
- **For eval.** The evidence points to fixing the meshes (pot base, nestable cups, the lid, rack slots, board slots),
  not to shifting the reference poses. See section 6.

## 2. Gate, direction check, mesh check

| check | rule (PREREG) | result | verdict |
|---|---|---|---|
| gate (variant A) | mean dAUC >= +0.002 and min >= -0.01 over 20 episodes | mean -0.0107, min -0.0342 (ep41) | **fail**: not proposed for eval |
| direction (A) | falsified if cos <= 0 on more than half of the shifted segments | 28 of 50 <= 0 (median cos -0.11); pair segments 5 of 16 <= 0; table-only 23 of 34 <= 0 | **falsified** (pair-only leg holds, P5) |
| mesh (A rest frames) | our meshes at the mocap poses vs at our poses | overlap persists or grows at the true poses for 4 of 6 overlapping pairs; cup / rack drops by 1/2 to 2/3 | mostly **meshes too fat or wrong shape**, partly pose (cup in rack) |
| bottoms | our mesh lowest point minus the scan's, at the mocap pose | C0 pot -6.9 to -8.3 mm (9 of 9 episodes), v3 pitcher -7.3 / -10.7 mm | the table contact is a mesh artefact for pot and pitcher |

Predictions (PREREG section 8):
- P1 holds: A changes 19 of 20 episodes (only ep11 is unchanged: its beige segment is unresolved).
- P2 holds: unresolved segments are ep0 lid, ep11 beige, ep13 cup (end), ep23 board 1 (end), ep24 board 1 and ep31
  rack (end); ep26 pot (start) is unresolved but keeps its inherited support shift. ep23 board 1 was not in the list.
- P3 holds: mean dAUC on 41-45 is -0.0217.
- P4 holds: the gate fails.
- P5 holds: 11 of 16 pair segments have cos > 0.
- P6 holds: at the mocap poses ep11 shows 65.2 cm3, ep2 5.9 cm3, ep31 11.1 cm3.
  - The scans' leg is mixed. Cup / rack and sweeper / rack scans are below 1 cm3 at the mocap poses.
  - The cup / cup and pot / lid scans overlap 252 cm3 and 28 cm3 at the mocap poses. The public scans of these
    objects are not a zero-overlap reference [H: closed scan cavities].
- P7 holds: the pot is -7.5 mm (median of 9).

## 3. Per-episode scores [D]

Before = `pipeline/score_registered.py` on the original tracks with the 9a+ meshes. **They equal the stored 9a+ runs
on all 18 episodes that have one** (AUC, SR, MPPE, RPE and per-object AUC to 4 decimals; `tables.md`). 23 and 24 have
no stored run. "Shifted" counts segments with a nonzero shift, inherited support shifts included.

| ep | objects | AUC before | MPPE before cm | RPE before cm | A segments: shifted / unresolved / all, max shift mm | dAUC A | dMPPE A | dRPE A | dADD A cm (mean of objects) | dAUC B | dAUC C | dAUC D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot, white_pot_lid | 0.4963 | 12.161 | 22.876 | 2 / 1 / 3, 6.9 | -0.0013 | +0.187 | +0.123 | +0.190 | -0.0013 | +0.0000 | +0.0000 |
| 2 | white_pot, white_pot_lid | 0.9783 | 0.726 | 0.864 | 5 / 0 / 6, 24.4 | -0.0110 | +0.222 | +0.182 | +0.207 | -0.0110 | -0.0003 | -0.0042 |
| 11 | blue_cup, beige_cup | 0.9058 | 1.574 | 1.695 | 0 / 1 / 4, 0.0 | +0.0000 | +0.000 | +0.000 | +0.000 | +0.0027 | +0.0000 | +0.0000 |
| 12 | blue_cup, plastic_dish_rack | 0.9580 | 1.126 | 1.235 | 4 / 0 / 5, 17.4 | -0.0032 | +0.035 | +0.186 | +0.034 | -0.0032 | -0.0291 | -0.0265 |
| 13 | blue_cup, plastic_dish_rack | 0.9661 | 1.018 | 1.218 | 2 / 1 / 3, 8.8 | -0.0238 | +0.178 | +0.347 | +0.178 | -0.0238 | +0.0000 | +0.0000 |
| 18 | mini_sweeper, mini_dust_pan | 0.9628 | 1.052 | 1.591 | 3 / 0 / 4, 6.7 | +0.0061 | -0.018 | +0.102 | -0.011 | +0.0061 | -0.0288 | +0.0000 |
| 21 | blue_cup, water_pitcher | 0.8325 | 2.148 | 1.255 | 2 / 0 / 6, 6.9 | -0.0094 | +0.063 | +0.095 | +0.063 | -0.0094 | -0.0084 | +0.0000 |
| 22 | blue_cup, water_pitcher | 0.8710 | 1.800 | 1.222 | 4 / 0 / 5, 8.1 | -0.0082 | +0.028 | +0.157 | +0.029 | -0.0082 | -0.0145 | +0.0000 |
| 23 | wooden_piece_1, wooden_piece_2 | 0.0414 | 16.140 | 18.569 | 2 / 1 / 4, 17.9 | +0.0000 | -0.573 | +0.177 | -0.512 | +0.0000 | +0.0000 | +0.0000 |
| 24 | wooden_piece_1, wooden_piece_2 | 0.8117 | 2.360 | 0.983 | 2 / 1 / 4, 15.7 | -0.0061 | +0.134 | +0.087 | +0.133 | -0.0061 | -0.0030 | +0.0000 |
| 26 | plastic_dish_rack, white_pot | 0.9775 | 0.781 | 1.052 | 4 / 1 / 4, 12.3 | -0.0018 | +0.093 | +0.104 | +0.070 | -0.0018 | -0.0097 | -0.0133 |
| 27 | plastic_dish_rack, white_pot | 0.9879 | 0.536 | 0.840 | 3 / 0 / 3, 24.3 | -0.0044 | +0.070 | +0.179 | +0.065 | -0.0044 | -0.0044 | -0.0044 |
| 31 | mini_sweeper, plastic_dish_rack | 0.8611 | 1.854 | 1.706 | 3 / 1 / 4, 3.0 | -0.0181 | +0.069 | +0.008 | +0.067 | -0.0181 | +0.0000 | +0.0000 |
| 39 | mini_dust_pan | 0.9755 | 0.856 | 0.000 | 2 / 0 / 3, 10.9 | -0.0176 | +0.291 | +0.000 | +0.279 | -0.0176 | +0.0018 | +0.0000 |
| 40 | mini_dust_pan | 0.9803 | 0.648 | 0.000 | 2 / 0 / 2, 4.9 | -0.0070 | +0.122 | +0.000 | +0.117 | -0.0070 | +0.0000 | +0.0000 |
| 41 | white_pot | 0.9893 | 0.601 | 0.000 | 2 / 0 / 3, 8.1 | -0.0342 | +0.479 | +0.000 | +0.458 | -0.0342 | +0.0000 | +0.0000 |
| 42 | white_pot | 0.9920 | 0.598 | 0.000 | 2 / 0 / 2, 7.3 | -0.0056 | +0.095 | +0.000 | +0.080 | -0.0056 | +0.0000 | +0.0000 |
| 43 | white_pot | 0.9778 | 0.747 | 0.000 | 2 / 0 / 2, 12.3 | -0.0232 | +0.367 | +0.000 | +0.292 | -0.0232 | -0.0058 | +0.0000 |
| 44 | white_pot | 0.9975 | 0.446 | 0.000 | 2 / 0 / 2, 10.0 | -0.0291 | +0.468 | +0.000 | +0.454 | -0.0291 | +0.0000 | +0.0000 |
| 45 | white_pot | 0.9759 | 0.723 | 0.000 | 2 / 0 / 2, 6.6 | -0.0166 | +0.258 | +0.000 | +0.246 | -0.0166 | +0.0000 | +0.0000 |

**Means over the 20 episodes**

| variant | episodes changed | mean dAUC | min dAUC (ep) | max dAUC | mean dMPPE cm | mean dRPE cm | mean dSP-SR | mean dMP-SR | mean dADD cm | mean dAUC 41-45 |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 19 | -0.01073 | -0.0342 (41) | +0.0061 | +0.1284 | +0.0874 | +0.000 | -0.050 | +0.1220 | -0.02174 |
| B | 20 | -0.01059 | -0.0342 (41) | +0.0061 | +0.1270 | +0.0846 | +0.000 | -0.050 | +0.1207 | -0.02174 |
| C | 17 | -0.00511 | -0.0291 (12) | +0.0018 | +0.0528 | +0.0447 | +0.000 | -0.050 | +0.0504 | -0.00116 |
| D | 4 | -0.00242 | -0.0265 (12) | +0.0000 | +0.0215 | +0.0418 | +0.000 | +0.000 | +0.0208 | +0.00000 |

- MP-SR changes on one episode only: ep22 goes 1 -> 0 under A, B and C. SP-SR does not change.
- ADD is the symmetric ADD that the AUC is built on, averaged over frames and objects (`pf_diag.py`, the kit chain
  replicated). Its replicated AUC equals the scorer's AUC, before and after, in all 80 episode-variant diagnostics.
- Full per-segment records: `out/<V>/ep<e>.posefix.json`. Scorer JSONs: `runs/<tag>/ep<e>.json`. Diagnostics:
  `diag/<V>/ep<e>.json`. All tables: `tables.md`. Machine-readable results: `results.json`.

## 4. What the transform did (GT-free) [M]

- **A, 71 rest segments.**
  - 47 were shifted by translation, 1 by the lift search (ep2 lid, 24.4 mm), and 1 inherited its support's shift
    (ep2 lid on the pot, 8.3 mm).
  - 6 are unresolved (left at zero) and 1 keeps an inherited shift (ep26 pot). 15 were already clean.
  - No segment needed the rotation stage.
  - Median shift 7.1 mm, max 24.4 mm.
  - Most shifts are lifts out of the table: pots mostly 5-12 mm (ep45 end 3.4 mm; ep27 end 24.3 mm, in the rack),
    racks 2-12 mm, dust pan 4-11 mm, pitcher 5-8 mm, boards 5-18 mm.
- **Penetration of the shifted segments fell** (median constraint frame of the segment, before -> after):
  - pots ~8 -> 0-0.8 mm;
  - ep12 cup in the rack 6.6 -> 0.6 mm;
  - ep2 lid in the pot 2.3 -> 0.7 mm.
  - The physics goal was met where the rule could act. The poses got further from the truth.
- **Pairs only (D):** it shifted 4 segments, each a guest on or in a pot or a rack:
  - ep2 lid lift 16.5 mm;
  - ep12 cup 16.6 mm out of the rack;
  - ep26 pot 21.0 mm;
  - ep27 pot 16.9 mm.
  - All four episodes got worse (-0.0042, -0.0265, -0.0133, -0.0044).

## 5. Direction and mesh checks [D]

**Direction** (cosine of the push with the correction mocap - ours, both under the before run's scene alignment):

| variant | shifted segments | cos <= 0 | median cos | with pair constraint: n / cos <= 0 | table only: n / cos <= 0 | falsified (cos <= 0 on > half) |
|---|---|---|---|---|---|---|
| A | 50 | 28 | -0.113 | 16 / 5 | 34 / 23 | yes |
| B | 51 | 28 | -0.086 | 17 / 5 | 34 / 23 | yes |
| C | 22 | 14 | -0.259 | 7 / 2 | 15 / 12 | yes |
| D | 4 | 3 | -0.113 | 4 / 3 | 0 / 0 | yes |

- **Magnitude.** The position error of the shifted object, under the same alignment, fell on 3 of 50 A segments.
- **Overshoot.** On the 22 segments with a positive correction along the push, the push is a median 5.7 times that
  component.
- **Table-only lifts** have cos <= 0 on 23 of 34 segments. Their corrections are small at the
  start segments (0.2-1.7 mm for pots), where the lifts are 6-12 mm.
- Full list: `tables.md` ("Variant A segments").

**Mesh check** (frames where both objects are at rest; every second frame; median / max overlap, median depth):

| ep | pair | rest frames | ours at our poses: median / max cm3, median depth mm | ours at mocap poses | scans at mocap poses |
|---|---|---|---|---|---|
| 0 | white_pot / white_pot_lid | 130 | 0.00 / 0.48, 0.0 | 6.43 / 6.51, 2.4 | 25.99 / 27.64, 53.7 |
| 2 | white_pot / white_pot_lid | 48 | 4.68 / 5.10, 2.3 | 5.85 / 6.00, 2.3 | 28.42 / 28.64, 54.9 |
| 11 | blue_cup / beige_cup | 42 | 91.36 / 98.90, 13.9 | 65.24 / 65.95, 22.0 | 252.25 / 253.41, 25.6 |
| 12 | blue_cup / plastic_dish_rack | 63 | 2.24 / 4.68, 5.8 | 0.74 / 1.84, 2.3 | 0.29 / 0.61, 1.4 |
| 13 | blue_cup / plastic_dish_rack | 93 | 4.09 / 10.23, 4.4 | 1.92 / 3.89, 4.1 | 0.06 / 0.20, 1.1 |
| 18 | mini_sweeper / mini_dust_pan | 10 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 |
| 21 | blue_cup / water_pitcher | 36 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 |
| 22 | blue_cup / water_pitcher | 50 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 | 0.00 / 0.00, 0.0 |
| 23 | wooden_piece_1 / wooden_piece_2 | 55 | 0.00 / 0.00, 0.0 | 10.05 / 10.09, 6.2 | 1.14 / 1.26, 2.8 |
| 24 | wooden_piece_1 / wooden_piece_2 | 31 | 10.51 / 10.55, 6.1 | 9.94 / 10.00, 6.2 | 0.90 / 0.91, 2.5 |
| 26 | plastic_dish_rack / white_pot | 68 | 0.00 / 1.80, 0.0 | 0.00 / 2.36, 0.0 | 0.00 / 30.13, 0.0 |
| 27 | plastic_dish_rack / white_pot | 60 | 0.00 / 1.59, 0.0 | 0.00 / 1.50, 0.0 | 0.00 / 26.57, 0.0 |
| 31 | mini_sweeper / plastic_dish_rack | 30 | 5.39 / 7.91, 8.6 | 11.14 / 12.16, 8.6 | 0.74 / 1.42, 3.0 |

- **What the overlaps are.**
  - Where our poses overlap, our meshes still overlap at the true poses: ep2 lid / pot, ep11 cups, ep24 boards.
  - On ep31 sweeper / rack they overlap more at the true poses (11.1 vs 5.4 cm3).
  - On ep23 our tracks keep the boards apart while the true poses interlock them (10.1 cm3 with our slot-less boards).
  - Only the cup in the rack (ep12, ep13) is mostly pose: 2.2 -> 0.7 and 4.1 -> 1.9 cm3 at the true poses.
- **Bottoms** (mocap z up; the scans' lowest point sits at z = 599-602 mm at rest in every episode, so the table is
  flat there).
  - Placed at the true pose, our C0 pot's lowest point lies 6.9-8.3 mm below the real one in all 9 pot episodes. The
    v3 pitcher lies 7.3 / 10.7 mm below, and wooden_piece_2 5.5 mm (ep24).
  - The dust pan (-1.7 to -2.4 mm), sweeper, rack (+1 to +4 mm) and boards (ep23) are within a few mm.
  - The pot's lowest region is its main base (2,542 vertices within 8 mm of the bottom, spread 106 mm), not the
    marker balls (separate 14 mm bodies 17-108 mm higher; GT-free check).
  - The base sits low in the kit's registration frame [H: the surface-moment registration, or the base shape].
- **Public scans as a reference.**
  - Scans at the mocap poses overlap little for cup / rack, sweeper / rack and boards (0.06-1.14 cm3).
  - For the cups they overlap by 252 cm3, and for pot / lid by 26-28 cm3 with 54 mm depth. The true ep11 end is a real
    nest, and these scans count as solid across their opening in our inside test [H].
  - So scan overlap is not a zero reference for those pairs. The comparison that matters is ours-at-ours vs
    ours-at-mocap.

## 6. Should this go to the eval references? (for the pack lane)

**No, not this rule.** It fails its gate, and the direction and mesh checks say why: the public "impossible poses" at
rest are mostly mesh shape, not pose. Per eval reference:
- **Eval 10, cups up to 88.5 cm3.** The nearest public case is ep11. There the true pose is a nest, and our meshes
  overlap 65 cm3 even at the true poses. The lever is nestable meshes (the ev10 cavity-safe lane), not a shift. The
  rule leaves ep11 unresolved anyway (> 30 mm).
- **Eval 1, lid in pot up to 34.9 cm3.** The nearest public cases are ep2 and ep0. Our meshes overlap 5.9 / 6.4 cm3 at
  the true poses, and the lid lift (24 mm) took the lid 6.7 -> 23 mm from the truth. Fix the lid / pot meshes first.
- **Eval 14, cup in rack 10.7 cm3.** The nearest public cases are ep12 and ep13. About half to two-thirds of the
  overlap is pose, but the minimal shift overshoots (ep12 cup: 17 mm lift; dAUC -0.0265 in D). A pose fix there would
  need a different, bounded rule tested on new public data, for example a shift capped by the measured overlap depth,
  or a lateral-only shift. That rule is not tested here [H].
- **Eval 30, sweeper in rack 8.4 cm3.** The nearest public case is ep31. The overlap is larger at the true poses, so
  it is mesh (rack slot / sweeper shape). The rule left the end segment unresolved.
- **Evals 15 / 16, spoon unsupported 6.5 / 8 mm.** No public spoon episode exists. Support drop (B) touched one public
  segment (ep11 beige, +0.0027), which is too little evidence to propose it.
- **Table contact in general.** Do not lift reference poses out of the table. For the pot and the pitcher the
  penetration is the mesh base sitting 7-11 mm low relative to the real base. Correct the meshes, or accept the
  contact.
- **Not measured here.** This test scores perception accuracy. It does not measure simulator stability (contact
  overflow, ejection at start). If the simulator needs penetration-free references for stability, that trade has to
  be judged by the simulator gates (budget.py, FlashCHORD), knowing that the pose cost on public data is about -0.01
  AUC for A and -0.0024 for pair-only D [D].

## 7. Run record

- **Code:**
  - PREREG and scripts df60ff2 (pushed 04:53:42 UTC): `scripts/pf_lib.py`, `pf_measure.py`, `pf_transform.py`,
    `pf_diag.py`, `run_posefix.sh`;
  - sha256 of the outputs 4ef1305 (05:14:39), with `pf_report.py` (it only formats);
  - `scripts/diag_variant.sh` = the `run_posefix.sh diag` loop for one variant, used to run A while B-D were scoring,
    and then B, C, D in parallel.
- **Machine:** this cloud container (4 shared cores, load 2-8 from other agents), CPU only, no rental, **$0**.
- **Commands** (`R=/home/user/v2d-track3/docs/research/mesh-2026-10-26/posefix/scripts`):
  - `python -I $R/stage_inputs.py <scratch>/posefix/inputs.json` (stage meshes and tracks; GT-free);
  - `python -I $R/pf_measure.py <scratch>/posefix/tracks <scratch>/posefix/explore <20 eps>` (GT-free, before PREREG);
  - `bash $R/run_posefix.sh transform` (04:54:00-05:14:03; C 05:08, D 05:10, A 05:13:58, B 05:14:03; 0 FAIL);
  - `bash $R/run_posefix.sh stage0` (05:14:40-05:14:55; ep23 / ep24 parquets downloaded from HF
    `nvidia/video_to_data_challenge`, the other 18 linked from the C0 / C1 stagings);
  - `bash $R/run_posefix.sh score` (05:15:09-05:32:54; **100 of 100 runs OK, 0 FAIL, 0 re-runs**);
  - `bash $R/diag_variant.sh A|B|C|D` (A 05:26:49-05:38:38, B / C / D 05:32-05:43:45; 80 of 80 OK);
  - `python -I $R/pf_report.py <this folder>`.
- **Inputs, with hashes:**
  - meshes (md5): PREREG section 2 and `inputs.json`;
  - tracks, hands and bundle `episode.json` (sha256): `inputs.json`;
  - scoring inputs (parquets and scans, sha256): `t3_inputs_sha256.txt`;
  - transformed tracks and reports (sha256): `out_sha256/<V>.txt`, `out_sha256/before.txt`;
  - scorer `pipeline/score_registered.py` 6a4cd60a0d26e3f8, kit `track3_pose.py` b4b99f698eb4893a.
- **Outputs:**
  - repo: this folder (scorer JSONs, posefix reports, diagnostics, tables, results);
  - scratch (regenerable, not in git): `<scratch>/posefix/out/<V>/ep<e>/poses_world_vo.npz`, the SDF caches
    `<scratch>/posefix/sdf`, `sdf_scan`, and the logs `<scratch>/posefix/logs`.
- **Timings** [M]:
  - SDF grids of the 10 meshes: 2-33 s each;
  - transform per episode: 1-280 s (pair episodes with thin shells are slowest);
  - scorer: 5-30 s per run;
  - diagnostic: 0.5-1.5 min per episode.

## 8. Deviations, caveats, limits

- **No deviation from PREREG** in constants, episodes, variants or scoring. Each run was executed once.
- **GT-free development before the PREREG** (stated in PREREG section 3). The measurement and dev transform runs on 8
  episodes changed the success share (q90 -> median frame), added support inheritance and added the lift stage. No
  score had been computed then.
- **Direction sign.** The cosine is taken with (mocap - ours), not the brief's (ours - mocap), so "cos > 0" means the
  push helps. This was stated in PREREG before scoring.
- **Frame-0 coupling [H, consistent with C].** The kit aligns each episode once at frame 0. Variant C, which keeps
  frame-0 segments, halves the loss (-0.0051) but is still negative. So the loss is not only the alignment artefact.
- **Scoring.** The before / after deltas use the public scans as hidden-scan stand-ins and the scorer's guessed anchor
  and points (as in every CD-O sprint guard). The board scores simulator rollouts, not perception tracks.
- **Mesh check.** It places our meshes through the kit's registration, so "ours at mocap" includes registration error.
  Bottoms assume mocap z is up (supported by the flat 599-602 mm rest heights).
- **Inside test.** Our inside test counts the cup and pot scans as solid across the opening [H]. Scan-scan overlaps
  for those pairs are therefore not a floor.
- **Shared records.** STATUS.md and docs/work-log.md were not edited by this agent (orchestrator's files). Text for
  them is in the hand-off.
