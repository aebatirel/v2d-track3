# ev10-cavsafe: cavity-safe eval-10 cup pieces (four measured candidates)

1 Nov 2026, 02:47-03:25 UTC; v4 04:47-05:00 UTC (section 9). CPU on this container, no rental, $0. GT-free.

These are candidates for the pack lane. No pack was changed. `meshes/carve/ev10` stays what the packed eval-10 policy
uses.

Tags: [M] measured here, [R] read from another lane, [E] estimate, [H] hypothesis.

The gates were written before any candidate number: `GATES.md` (commit 98ddccf), with amendments A1 (cbb6d29),
A2 (dafc911), A3 (c5500c7) and A4 (fedccf6, v4). Section 7 gives the time order.

**v4 (`ev10cs4`, 24 / 21 pieces), added later: section 9.** In plain MuJoCo it passes gates 1-3 (rest overlap
0.21 / 2.61 cm3; pair-scene max nefc 488, 0 / 48 copies over the limits). It fails gate 4a for the blue cup, as every
set does, and fails the drop check. FlashCHORD 32 x 60 is pending with determined-wright.

## In plain words

**Why the packed pieces overlap.**
- In the packed eval-10 collision pieces, the receiver (blue cup) cuts into its own cavity.
- Each 30-degree wall piece has a flat inner face. Its midpoint sits up to 1.4 mm inside the round cavity, and more where
  the cup's profile curves.
- Measured: up to 3.5 mm deep, and 54 cm3 of the cavity is filled by the blue cup's own pieces.

**What we rebuilt.** The same tool and the same constants, changed so that:
- no blue piece enters the blue cavity (measured 0.0 mm, 0.0 cm3);
- no beige piece pokes out of the beige outline.

**What that did, and what it did not do.**
- At the hands-off nested rest of the packed reference (f124-f160), the piece overlap drops from 11.9 cm3 (median) to
  1.9 cm3 with 12 sectors, and to 0.4 cm3 with 8 sectors.
- The rest is not a piece problem. The visual meshes themselves overlap at every rest frame (80.8 cm3 median).
  - 33.8 cm3 of that lies in the blue cup's wall or base, not just in the part of its cavity that the blue mesh fills.
  - The reference puts the beige cup 4-7 mm off the blue cup's axis (focused-pascal ev10w [R]) and too deep for these
    meshes.
  - So the floor is the pose: pieces can only shrink the overlap by making the beige smaller than its mesh.

**Removing the overlap moved the contact problem to the floor.**
- Freed from the overlap, the beige slides 4-27 mm down into the blue and lands on its floor. There, 13 beige base
  pieces meet 17 blue base pieces whose tops all lie in the floor plane: up to 191 contacts.
- v2 makes the blue floor one piece. In the plain-MuJoCo pair scene this brings the settled nest to 212 constraint rows
  (v3: 160), against 68-484 for packed.
- Short peaks still pass 512 in a few copies: v2 5 / 48, v3 6 / 48, packed 48 / 48. The v3 peaks follow a 14-32 mm
  drop of the cup pair in the hands-free test scene (section 4).

**FlashCHORD, the final contact gate** (determined-wright [R]).
- v1, the pre-registered candidate:
  - sampled nefc max 510 against packed 536;
  - 4 overflow lines against 13,544;
  - cup-cup contacts at most 31 against 68;
  - their verdict: "improved, NOT clean at 512; do not retrain on it".
- v2 and v3 are delivered for their budget.py run (their pass criterion: sampled nefc max <= about 460 and 0 overflow
  lines).

**Kept volume.** Gate 4 fails for the blue cup in every set, packed included. The blue visual mesh fills its own cavity.
A piece set that keeps the cavity empty therefore cannot hold 80 % of the mesh volume.

## Delivery (for determined-wright and the pack lane)

1. **Piece folders.** Each is laid out exactly like `meshes/carve/ev10`:
   - `<obj>/piece_NN.obj`, one convex hull each;
   - `<obj>/inertia.json`, the uniform solid of the pieces at 0.3 kg, which `make_assets.py --pieces` reads;
   - `<obj>/lathe_collision.json`;
   - `carve.json` with the note, commands and input hashes.

   Use: `python pipeline/make_assets.py meshes/library_v3 OUT --pieces <folder>`. Tested on all four: it writes 53 / 49,
   44 / 49, 32 / 33 and 24 / 21 `<collision>` elements.

   | Folder | What it is | Blue / beige pieces |
   |---|---|---|
   | `ev10cs/` | v1, pre-registered: cavity-safe walls, ev10's 17 base hulls | 53 / 49 |
   | `ev10cs2/` | v2 (A2, post hoc on v1's contact trace): v1 + a one-piece blue floor | 44 / 49 |
   | `ev10cs3/` | v3 (A3): v2 with 8 sectors instead of 12, fewer and larger hand-facing pieces | 32 / 33 |
   | `ev10cs4/` | v4 (A4): v3 with 8 cm bands (2 per wall), a beige base of 1 + 4 rim pieces and a 6 mm blue floor (F2) | 24 / 21 |

2. **Pairs with** the packed eval-10 reference:
   - `runs/20261026-gl10A2-5e0e100/refs/glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/ref_gl_ilc.parquet`;
   - md5 `1a5003d94852c275519066645a1b9869`, from focused-pascal's `docs/research/work/masses-eval-20261031/packed_refs.json`
     (HF store `aebatirel/v2d-store`);
   - visual meshes `meshes/library_v3/blue_cup.glb` (md5 75426314...) and `beige_cup.glb` (md5 6226281f...);
   - the pieces are in the library_v3 mesh (link) frame, as ev10.
3. **Critical frames:**
   - **f124-f160**, the nested hands-off rest: all 37 frames carry no hand-contact label. Note that the pair is still
     14-24 mm above the table at f124-f142 and reaches it at f160 (blue lowest point 24.4 / 13.9 / 0.4 mm at
     f124 / f142 / f160 [M]).
   - Pair-scene gate frames: f111, f142, f116. f111 and f116 are in hand; f142 has no label.
   - determined-wright's explicit frames: f0, f124, f142, f160.

## 1. Numbers: packed vs candidates [M]

The gates are defined in `GATES.md`. Contacts are counted in the plain-MuJoCo 3.17.0 pair scene: sim=rl options and
limits (njmax 512, nconmax 256), 16 jittered copies x 2 s, no hands. These are plain-MuJoCo-only numbers: cc2eval
(I.md, 03:06) found plain MuJoCo stricter than MuJoCo-Warp. FlashCHORD is the final gate.

| | packed `ev10` | v1 `ev10cs` | v2 `ev10cs2` (post hoc) | v3 `ev10cs3` |
|---|---|---|---|---|
| Pieces, blue / beige | 53 / 49 | 53 / 49 | 44 / 49 | 32 / 33 |
| **Gate 1**: piece overlap f124-f160, median / max, cm3 (pass: <= 1.0 / 3.0) | 11.86 / 32.67 | 1.92 / 6.82 FAIL | 1.92 / 6.82 FAIL | **0.38 / 2.99 PASS** (max within 0.01 of the bar) |
| Gate 1, min; max over all 161 frames (in hand included) | 3.41; 36.2 (f105) | 0.16; 10.96 (f109) | 0.16; 10.96 (f109) | 0.007; 7.61 (f109) |
| Pose floor beside it: faithful visual overlap f124-f160, median / max, cm3 | 80.6 / 88.5 | same | same | same |
| **Gate 2**: max nefc / ncon at f111, f142, f116; overflow copies of 48 | 1,296 / 324; 48 | 936 / 234; 40 FAIL | 548 / 137; 5 FAIL | 756 / 189; 6 FAIL |
| Max nefc (overflow copies of 16) at f111 / f142 / f116 | 1,252 (16) / 656 (16) / 1,296 (16) | 804 (10) / 936 (15) / 808 (15) | 468 (0) / 548 (1) / 544 (4) | 756 (2) / 376 (0) / 752 (4) |
| Step-0 nefc at f111 / f142 / f116 | 1,004 / 568 / 1,280 | 700 / 296 / 808 | 416 / 296 / 544 | 224 / 152 / 272 |
| Report: f124 / f160 max nefc (overflow of 16) | 876 (16) / 580 (4) | 1,056 (16) / 788 (16) | 612 (2) / 388 (0) | 684 (3) / 380 (0) |
| Settle trace, settled rows (median over the last 0.5 s) at f124 / f142 / f160 | 484 / 384 / 68 | 574 / 746 / 738 | 212 / 212 / 212 | 160 / 160 / 160 |
| **Gate 3**: blue pieces in the cavity, depth mm / volume cm3 (pass: <= 0) | 3.54 / 54.2 (all 36 wall pieces) | **0.0 / 0.0 PASS** | **0.0 / 0.0 PASS** | **0.0 / 0.0 PASS** |
| Beige pieces beyond the shrunk beige profile / beyond the unshrunk one, mm | +2.71 / -5.29 | 0.00 / -8.0 | 0.00 / -8.0 | 0.00 / -8.0 |
| **Gate 4a**: piece volume / visual volume, blue / beige (pass: >= 0.80) | 0.381 / 1.921 | 0.325 FAIL / 1.675 | 0.329 FAIL / 1.675 | 0.340 FAIL / 1.584 |
| Piece union volume, cm3, blue / beige (visual 400.3 / 157.8) | 152.5 / 303.1 | 130.1 / 264.3 | 131.9 / 264.3 | 136.1 / 250.1 (build) |
| 4b: visual volume kept, (pieces ∩ visual) / visual | 0.296 / 0.176 | 0.181 / 0.134 | 0.181 / 0.134 | 0.153 / 0.097 |
| 4c: piece volume / ev10's | 1 / 1 | 0.853 / 0.872 | 0.865 / 0.872 | 0.891 / 0.825 |
| Piece-count target of A3 (<= 2/3 of ev10: 35 / 33) | - | - | - | 32 / 33 pass |
| **FlashCHORD budget.py** (determined-wright [R], 90e3e41) | sampled nefc max 536 (median 473), 13,544 overflow lines; f0 / 124 / 142 / 160 max 441 | 510 (443), 4 lines (largest 518); explicit max 409, 0 lines; "improved, not clean" | pending (theirs) | pending (theirs); criterion: <= ~460 and 0 lines |

Notes on the table:
- The packed rerun reproduces the precheck exactly (V_packed median 11.856, max 32.67; nefc 1,252 / 656 / 1,296).
- v2's gate 1 equals v1's: the floor plate lies below every frame's overlap.
- In v3, f111 / f116 (in hand: the reference holds the pair 32 mm above the table) and f124 drop the pair in the
  hands-free scene. 31-35 guest-table contacts appear at those maxima.

## 2. What changed, and why each constant

All other constants are ev10's (`meshes/carve/ev10/carve.json`):
- `--seg 12 --band 0.06`;
- blue wall 3 mm; blue base = the 17 FlashCHORD CoACD hulls of library_v3 clipped below the inner floor;
- beige shrink 8 mm, fitted wall 7.41 mm, base extended 7.1 mm, ring base.

The tool is `scripts/lathe_cavsafe.py`, a copy of focused-pascal's `pipeline/lathe_collision.py` (blob 680cc2f9) with
opt-in flags. Without the flags it rebuilds ev10 at a vertex Hausdorff distance of 0.0 mm (all 53 + 49 pieces), with
the blue base bytes equal and the inertia within 2e-9 m.

- **R1' (blue, `--inner_circ --outer_circ`).** Both wall faces sit at r / cos(pi/12) at the sector edges, so the wall
  polygon circumscribes the lathe wall, the mirror of ev10, which inscribes it.
  - The inner face is then tangent to the cavity at mid-sector.
  - Amendment A1 added the outer face. With the outer face unchanged, the mid-sector wall came out negative at two bins:
    -1.30 mm at the mouth lip and -0.30 mm at the bottom corner.
  - Cost: the blue cup's outer surface lies 0 to about 1.6 mm (3.3 mm at 8 sectors) outside its lathe profile.
- **R2 (blue).** In each band, r_in = r - 3 mm is replaced by its least convex majorant: a linear program with no
  constant. A convex hull spanning concave profile bins would otherwise cut into the cavity.
  - It raises the inner face by up to 2.75 mm at the mouth lip and 2.13 mm at the bottom corner, and <= 0.5 mm elsewhere.
  - Thinnest mid-sector wall: **0.25 mm at the mouth bin and 0.875 mm at the bottom bin**, >= 2.49 mm in band 2.
- **G1 (beige, `--outer_insc`).** In each band, the shrunk outer profile is replaced by its greatest concave minorant.
  - The edge points stay on the profile, so the faces are inscribed.
  - It lowers the outer face by up to 4.83 mm in band 2 (h 50-70 mm), below a step in the profile (33.5 -> 35.0 mm).
  - In ev10 that band bulged 2.7 mm beyond the shrunk profile [M], though still 5.3 mm inside the unshrunk one.
- **F1 (v2 and v3, `--floor_plate`).** The blue cavity floor becomes one convex piece: the hull of the circumscribed
  rings over [h_base - 3 mm, h_base], the tool's own base-plate span, 10.5-10.8 cm3.
  - The 17 base hulls are clipped to h >= h_base with `pipeline/interaction_carve.clip`. 7 survive; the other 10 lie
    above the plane or leave a slab thinner than the clip's 0.2 mm ball.
  - The footing is unchanged: the 7 kept hulls are the ones whose bottoms reach 79.1-80.0 mm. The ev10 hulls ending at
    76.5-78.5 mm sit 1.5-3.5 mm above the lowest hull points.
  - No new constant.
- **8 sectors (v3, A3).** A judgment constant, chosen before any v3 number: a third fewer hand-facing pieces per band,
  the step that FlashCHORD's ~60-100-row target asks for.
  - Chord error at r = 40 mm: 3.0 mm inside the beige and 3.3 mm outside the blue's outer face, about the 3 mm wall.
  - 6 sectors would give 5.4-6.2 mm, about the pose offset.
- **COM shifts against ev10** (uniform solid of the pieces, 0.3 kg):
  - blue +3.6 mm (v1) / +4.6 mm (v2, v3) toward the base, along file z;
  - beige -1.9 mm (v1, v2) / -1.5 mm (v3) toward the mouth.
  - Ixx and Iyy: blue -6 %, beige +7 % (v1).

## 3. Do the visual meshes overlap at rest? Yes: the floor is the pose [M]

Over f124-f160, median (range), cm3, computed by `scripts/cavsafe_measure.py`:

| Measure | Value |
|---|---|
| Beige visual mesh inside the blue visual mesh (1.5 mm / 1 mm grids) | 80.8 (67.8-88.6) |
| ... of it inside the blue's lathe cavity (the blue mesh fills its own cavity; a cavity-safe piece set drops it) | 46.1 (41.9-50.5) |
| ... of it outside the cavity (the beige mesh crosses the blue's wall or base) | **33.8 (25.2-38.5)** |
| Design floor: the exact shrunk beige lathe body (rho <= r - 8 mm) outside the blue cavity, inside the blue envelope | 6.68 (1.26-21.28) |

- At every rest frame, the two visual meshes interpenetrate beyond the cavity. That means the pose: the 4-7 mm axis
  offset and the depth [R, ev10w], together with the mesh sizes.
- No piece set that is faithful to both meshes can be overlap-free there.
- The candidates reach 0.4-1.9 cm3 only because the beige pieces are 8 mm (plus the chord) inside the beige mesh.
- Even perfect lathe bodies of this design would overlap 6.7 cm3 (median). v1 and v3 stay below that because their
  inscribed chords sit inside the exact body.

## 4. Why the contacts moved to the floor (settle trace, `scripts/settle_trace.py`) [M]

One unjittered copy per frame, 2 s, plain MuJoCo.

- **Packed.** The beige stays wedged on the blue's walls; the axial drift is -1.2 to +12.4 mm. The rows at the
  maximum are spread over the wall bands.
- **v1.** The overlap is gone, so the beige slides down the blue's axis: +4.3 / +12.0 / +27.4 mm at f124 / f142 / f160.
  - It lands on the floor, where its 13 base pieces meet the 17 base hulls.
  - All 17 hull tops lie on the floor plane.
  - 166-191 of the 185-194 contacts at the max-nefc step are base against base. Settled: 574-746 rows.
- **v2.** The same slide, onto one floor piece. The settled nest holds 53 contacts / 212 rows at all three frames.
- **v3.** Settled 40 contacts / 160 rows.
  - Its peaks come from impact: at f124 step 8 of the hands-free drop (the blue lands from 24 mm), 104 guest-base
    contacts include the beige base touching the table plane through the blue's floor.
  - That is the 3 mm plate plus 1.6 mm of hull, against 6.8 mm of axial travel in one 10 ms step.
  - [H] Thin floors can be crossed at drop impacts above about 0.5 m/s at this time step. The packed ev10 floor is just
    as thin (4.6 mm), but its beige never reached it.
- In this MuJoCo build, mesh-mesh contacts give up to 4 contacts per piece pair for face-on-face contact (v3 f124: 59
  pairs, 172 contacts). Fewer touching pairs is the lever.

## 5. What the pack lane would need to do

1. **determined-wright:** budget.py on `ev10cs2` and `ev10cs3` with the same sampled resets and explicit frames as for
   v1 and packed. Their criterion: sampled nefc max <= about 460 and 0 overflow lines.
2. **If one passes:** a FlashCHORD rest / nest test on the packed reference (`tools/carve_fc_test.py`, like ev10's
   `rest_robustness`: max tilt over starts, hands parked). The floor plate, the 0.25 mm mouth-lip wall and the deeper
   nest are new. It should check:
   - that the beige does not cross the blue floor;
   - that the blue does not fall over.
3. **Then one eval-10 training** at the stock sim=rl limits:
   - `make_assets.py meshes/library_v3 OUT --pieces <folder>`, with the same packed reference and recipe;
   - first check: the "nefc overflow" line count, against about 6-8 M per run today [R];
   - then lift > 0 and sim_vs_ref.
   - Any packed use stays the owner's call.

## 6. Limits

- **Plain MuJoCo.** Every contact number here is plain MuJoCo 3.17.0, not MuJoCo-Warp. The pair scene is reduced: no
  hands, zero action, 0.3 kg placeholders.
  - The reference holds the pair in the air at f111 / f116 (32 mm) and f124-f142 (24-14 mm above the table with no
    hand near after f130), so the scene drops it.
  - Gate 2's frames are the precheck's, fixed before the candidates.
- **The beige ends lower than the reference.** In the candidates it settles 4-27 mm deeper in the blue than the
  reference puts it. The ev10 overlap was what held it up. A policy tracking this reference may see that as tracking
  error [H].
- **Gate 3's depth definition was corrected after its first run.** It was ill-posed at the floor plane: a base hull's
  top face on h = h_floor read "30.5 mm". This is stated in the script. Interior grid volumes were unaffected.
  `results/logs/measure_run1.log` keeps the first run.
- **Post hoc variants.** v2 and v3 were designed after v1's numbers (A2, and A3 after determined-wright's v1 numbers).
  The constant 8 is a judgment value. v3's gate-1 max (2.99) passes by 0.01 cm3.
- **Profiles regenerated.** They were rebuilt with trimesh 5.2.0, and their bytes differ from focused-pascal's 4.12.2
  profiles. The ev10 geometry rebuilt from them is identical, Hausdorff 0.0 mm.
- **Gate 1 measures piece-vs-piece volume only.** Depth comes from the precheck's guest-mesh-in-pieces lower bound.

## 7. Time order (UTC, 1 Nov)

| Time | Event |
|---|---|
| 02:47 | Start |
| 02:49 | Profiles regenerated |
| 02:51 | ev10 rebuild check |
| 02:54 | GATES.md committed (98ddccf) |
| 02:57 | v1 build fails the wall check |
| 02:59 | A1 committed (cbb6d29) |
| 03:00-03:03 | Gate 1 |
| 03:02 | Gate-3 definition corrected |
| 03:03-03:06 | Gate 2 |
| 03:08 | Settle trace |
| 03:09 | Gate 3 |
| 03:10 | A2 committed (dafc911) |
| 03:11 | v2 built |
| 03:13 | v2 numbers; determined-wright's v1 FlashCHORD numbers relayed |
| 03:14 | A3 committed (c5500c7) with v2's folder |
| 03:16 | v3 built and pushed (5cd0433) before our v3 numbers |
| 03:17-03:21 | v3 numbers |

## 8. Inputs and commands

**Inputs (md5 unless noted):**
- packed reference `ref_gl_ilc.parquet` `1a5003d94852c275519066645a1b9869`;
- support `t3_ep010_support.usda` `cd611b11f86a313620e750e438f7c34d`, table top 0.600 m;
- library_v3 blue_cup.glb `7542631493e3a0564f6d74009de67d54`, beige_cup.glb `6226281f120192c52bffec7680fa9d8f`;
- `meshes/carve/ev10` piece sets (md5 of the sorted per-file md5 list): blue `1e85cf2d...`, beige `4300e6e8...`;
- candidates: ev10cs blue `94fe3263...`, beige `a13180ab...`;
- profiles (sha256):
  - blue_cup_profile.npz `e8dfcff6...`, blue_cup.json `4b92dd8d...`;
  - beige_cup_v3_profile.npz `d10d8eae...`, beige_cup_v3.json `2c6736a6...`;
- `cfg_sim_rl.yaml` sha256 `695536b7...4b66`.

The references come from the precheck's download (`../collcarve2-evalcheck/inputs`). Nothing read here is a scan,
mocap, a dataset `pose` field or an `*_align` file.

**Commands.** R = this folder's `scripts/`, E = `../collcarve2-evalcheck/scripts/`, P = profile dir. Python 3.13 venv:
trimesh 5.2.0, numpy 2.5.4, scipy 1.18.1, mujoco 3.17.0.

```
python docs/research/approaches-2026-10-25/approach2-scripts/lathe_fit2.py blue_cup meshes/library_v3/blue_cup.glb P/blue_cup
python docs/research/approaches-2026-10-25/approach2-scripts/lathe_fit2.py beige_cup_v3 meshes/library_v3/beige_cup.glb P/beige_cup_v3
# v1 / v2 / v3 blue (v2 adds --floor_plate; v3 also --seg 8)
python -I R/lathe_cavsafe.py P/blue_cup_profile.npz P/blue_cup.json OUT/blue_cup --seg 12 --band 0.06 --wall 0.003 \
    --base_pieces meshes/carve/ev10/blue_cup --base_first 36 --inner_circ --outer_circ [--floor_plate]
python -I R/lathe_cavsafe.py P/beige_cup_v3_profile.npz P/beige_cup_v3.json OUT/beige_cup --seg 12 --band 0.06 \
    --shrink 0.008 --base_to_mesh meshes/library_v3/beige_cup.glb --ext_max 0.0071 --outer_insc
python -I <scratch>/cavsafe/mkcfg.py ...                                  # results/cfg.json: tags packed, cand, cand2, cand3
python -I E/evalcheck.py results/cfg.json geo_<tag> <tag>                 # gate 1, volumes (81-203 s)
python -I R/contacts_fixed.py results/cfg.json <tag> geo_<tag> contacts_<tag>.json      # gate 2
python -I R/settle_trace.py results/cfg.json <tag> geo_<tag> settle_<tag>.json 124,142,160
python -I R/cavsafe_measure.py P meshes/carve/ev10 <candidate dir> geo_packed/eppacked_poses.npz measure_<v>.json   # gate 3, floor
python -I R/summarize_cavsafe.py <run dir> results/summary.json
```

**Outputs in `results/`:**
- `summary.json` (all gates per set);
- `contacts_<tag>.json` (per copy);
- `settle_<tag>.json`;
- `measure_*.json`;
- `per_frame/ep<tag>_frames.json`;
- `cfg.json`;
- `logs/`.

## 9. v4 (`ev10cs4`): fewer, larger pieces and a 6 mm floor (A4)

### In plain words

**What v4 is.** v3 with fewer, larger pieces where the hands and the blue floor touch the cups:
- 2 wall bands per cup instead of 3;
- a beige base of 1 + 4 pieces instead of 1 + 8;
- the blue cup's one-piece floor, made 6 mm thick.

The pre-registered drop check of the 3 mm build fired, so A4's rule (F2) gave it the thicker floor. That raises the
blue cavity floor by 3 mm.

**What it passes in plain MuJoCo.**
- The rest overlap is 0.21 cm3 median, 2.61 cm3 max (gate 1 passes).
- The pair scene stays under the limits in all 48 gate copies, max 488 rows (gate 2 passes).
- No blue piece enters the (raised) cavity (gate 3 passes).

**What it does not fix.**
- Gate 4a fails for the blue cup, as it does for every set.
- When the hands-free test scene drops the pair 24-32 mm, the beige still goes through the blue floor in some copies,
  even at 6 mm.

**What the final verdict waits on.** FlashCHORD at 32 x 60, determined-wright's large-sample standard. Its target: 0
overflow lines and a hold-window max <= 480 rows.

### Numbers [M]

Same scripts and frames as section 1. "v4, 3 mm" is the build before F2. It was measured, but it is not delivered.

| | packed `ev10` | v3 `ev10cs3` | v4, 3 mm (before F2) | **v4 `ev10cs4` (F2, delivered)** |
|---|---|---|---|---|
| Pieces, blue / beige | 53 / 49 | 32 / 33 | 24 / 21 | **24 / 21** |
| Gate 1: overlap f124-f160, median / max, cm3 | 11.86 / 32.67 | 0.38 / 2.99 | 0.21 / 2.61 | **0.21 / 2.61 PASS** (min 0.000) |
| Max overlap over all frames, cm3 (in hand included) | 36.2 (f105) | 7.61 (f109) | 9.47 (f109) | 17.12 (f109) |
| Gate 2: max nefc at f111 / f142 / f116 (overflow copies of 16) | 1,252 (16) / 656 (16) / 1,296 (16) | 756 (2) / 376 (0) / 752 (4) | 484 (0) / 344 (0) / 504 (0) | **488 (0) / 212 (0) / 336 (0) PASS**; max ncon 122 |
| Report: f124 / f160 / rule frame f117 | 876 / 580 / - | 684 (3) / 380 (0) / 712 (13) | 468 (0) / 256 (0) / 508 (0) | 460 (0) / 196 (0) / 448 (0) |
| Step-0 nefc at f111 / f142 / f116 | 1,004 / 568 / 1,280 | 224 / 152 / 272 | 144 / 88 / 176 | 176 / 88 / 204 |
| Settled nest rows at f124 / f142 / f160 (settle trace) | 484 / 384 / 68 | 160 / 160 / 160 | 96 / 96 / 96 | 96 / 104 / 96 |
| Beige axial sink by the end of the trace, mm (f124 / f142 / f160) | -0.8 / -1.2 / 12.4 | 4.3 / 12.0 / 27.3 | 4.3 / 12.0 / 27.3 | 1.3 / 9.1 / 24.4 |
| Drop check: copies with guest-table contacts at the max step, f111 / f142 / f116 / f124 / f160 (of 16) | - | 2 / 2 / 4 / 5 / 4 | 3 / 1 / 6 / 3 / 1 | **8 / 0 / 2 / 6 / 0** |
| Drop check, unjittered settle traces | - | 33 / 14 / 0 contacts | 0 / 0 / 0 | 0 / 0 / 0 |
| Gate 3: cavity depth / volume | 3.54 mm / 54.2 cm3 | 0.0 / 0.0 | 0.0 / 0.0 | **0.0 / 0.0 PASS** against the raised floor (h_base - 6 mm); against v1-v3's cavity the plate fills its bottom 3 mm, 9.4 cm3 (by F2's design) |
| Gate 4a: blue / beige | 0.381 / 1.92 | 0.340 / 1.58 | 0.356 / 1.79 | **0.384 FAIL** / 1.79 |
| 4b, kept visual / 4c, union against ev10 | 0.296, 0.176 / 1, 1 | 0.153, 0.097 / 0.891, 0.825 | 0.151, 0.094 / 0.936, 0.934 | 0.177, 0.094 / 1.008, 0.934 |
| Thinnest blue mid-sector wall: mouth bin / bottom bin, mm | - | 0.25 / 0.875 | 0.54 / 1.39 | 0.54 / 1.39 |
| Beige outer face lowered at most (G1), mm | - | 4.83 | 2.39 | 2.39 |
| COM against ev10: blue / beige, mm along file z | 0 / 0 | +4.6 / -1.5 | +7.2 / -1.4 | **+12.8 / -1.4** |
| FlashCHORD 32 x 60, overflow lines sampled / explicit; hold-window max ([R], determined-wright 6b04fba) | 380 / 9,723; 661 | 110 / 576; 534 | - | pending |

In v4, the gate-2 maxima at f111 / f116 / f124 are frames where the scene drops the pair. At f111 the 122 contacts are
77 guest-receiver, 20 guest-table and 25 receiver-table.

### The drop check [M]: `scripts/drop_peek.py`, `results/logs/v4_droppeek_f124.log`

At f124 the pair is 24 mm above the table, and the scene has no hands.
- In 6 of 16 copies, the beige base reaches h 79.0-80.5 mm along the blue axis at step 8, the blue cup's impact on the
  table. That is past the 6 mm plate (top 72.4 mm) and at the blue cup's lowest point (80.0 mm).
- In the other copies it still sinks 0.4-4.9 mm into the plate.
- So F2 removed the guest-table contacts at the hands-off frames f142 and f160 (1 -> 0 copies), but not at the drop
  frames (f111: 3 -> 8 copies, f116: 6 -> 2, f124: 3 -> 6).
- A4 allowed one application and no further iteration, so the result is reported as it is.

[H] At a 10 ms step, a soft contact lets a 0.7 m/s impact sink about v x timeconst, roughly 14 mm at MuJoCo's default
0.02 s. No floor that fits in this cup (4.6 mm below the lathe floor, 7.6 mm with F2) stops a free drop. It only matters
if the policy lets the pair fall. Falsifier: a FlashCHORD drop of the nested pair from 24 mm at the training contact
settings, with the beige staying above the plate.

### Trades (stated in A4; measured here)

- **Shape.**
  - The blue cup's outer faces lie up to 3.3 mm (3.9 mm at the lip) outside its lathe profile at the sector edges.
  - The beige is 8 mm plus up to 3 mm (chord) plus up to 2.4 mm (G1) inside its mesh. Its base stands on 4 rim pieces.
- **Settle depth.** The beige still slides down to the blue floor, 1.3-24.4 mm deeper than the reference puts it. That
  is 3 mm less than v1-v3.
- **Insertion frames.** The raised floor meets the beige at the in-hand insertion frames f100-f117, where the
  reference puts the beige base at the old floor height. The all-frame max overlap is 17.1 cm3 at f109, against 9.5 cm3
  with the 3 mm plate. The rest frames are unaffected.
- **Mass distribution.** The blue COM moves 12.8 mm toward its base: the 22.7 cm3 plate inside a 154 cm3 uniform solid
  at 0.3 kg.

### Hand-off to determined-wright

- **Folder:** `ev10cs4/`, in the `make_assets.py --pieces` layout (tested: 24 / 21 `<collision>` elements).
  - md5 of the per-piece md5 lists: blue `8ca4996c...`, beige `7f8bff4c...`.
- **Paired reference:** the packed gl10A2 `ref_gl_ilc.parquet`, md5 `1a5003d94852c275519066645a1b9869`, with the
  library_v3 visual meshes.
- **Frames:**
  - nested hands-off rest f124-f160;
  - explicit f0, f124, f142, f160;
  - plus f111 and f116, the in-hand pair-scene gate frames where this scene drops the pair.
- **Target (A4):** FlashCHORD 32 x 60, 0 overflow lines sampled and explicit, hold-window max <= 480 rows.
- **Next, if it passes:** the rest / nest test in FlashCHORD, including whether the beige crosses the floor at the
  training contact settings, before any training run.

### Time order (UTC)

| Time | Event |
|---|---|
| 04:47 | Request |
| 04:48-04:49 | Profile-only dry runs |
| 04:50 | A4 committed (fedccf6), before building |
| 04:51 | v4 (3 mm) built; v3 rebuild byte-identical |
| 04:52-04:53 | v4 3 mm numbers; the drop check fired |
| 04:53 | F2 build |
| 04:55-04:57 | F2 numbers and drop peek |

## 10. v5 (`ev10cs5`, standby): ev10cs4 with an 8 mm floor plate (A5)

`ev10cs4` is frozen (FROZEN.md, fa2ec41) and was not touched; its md5 list was re-checked after this build: all OK.

**The build.** v5 is ev10cs4 rebuilt with `--plate_t 0.008` instead of 0.006, so the blue floor plate spans
[h_base - 8 mm, h_base] and the cavity floor is 2 mm higher.
- By md5, every file is byte-identical to ev10cs4 except three: `blue_cup/piece_16.obj` (the plate, md5
  `f8cec72184b8d4def1f2ea991817db92`; ev10cs4 `97b48703...`), `blue_cup/inertia.json` and
  `blue_cup/lathe_collision.json`.
- The plate is 30.93 cm3. Its top ring is the circumscribed profile at the new floor, r = 38.46 mm.
- determined-wright's tested variant moved the old plate's face (30.7 cm3) [R], so the two plates are close but not
  byte-identical [E].

**Numbers [M]** (plain MuJoCo, indicative only; same scripts and frames):

| | v4 `ev10cs4` (6 mm) | **v5 `ev10cs5` (8 mm)** |
|---|---|---|
| Gate 1: overlap f124-f160, median / max, cm3 | 0.206 / 2.609 PASS | **0.206 / 3.885 FAIL** (max at f124: the raised floor meets the beige base) |
| Max overlap over all frames (insertion frames) | 17.12 (f109) | 22.26 (f109) |
| Gate 2: max nefc at f111 / f142 / f116 (overflow copies of 16) | 488 (0) / 212 (0) / 336 (0) PASS | **560 (3) / 204 (0) / 252 (0) FAIL**; max ncon 140 |
| Report: f124 / f160 / rule frame f117 | 460 / 196 / 448 (all 0) | 352 / 192 / 268 (all 0) |
| Settled nest rows at f124 / f142 / f160 | 96 / 104 / 96 | 96 / 104 / 96 |
| Beige axial sink by the end of the trace, mm | 1.3 / 9.1 / 24.4 | -0.6 / 7.1 / 22.3 |
| Drop check: copies with guest-table contacts at the max step, f111 / f142 / f116 / f124 / f160 / f117 | 8 / 0 / 2 / 6 / 0 / 6 | **3 / 0 / 0 / 0 / 0 / 1** (still fires, at the in-hand drop frames) |
| Drop peek at f124: copies through the floor; deepest beige base | 6 of 16; 80.5 mm (floor top 72.4) | **0 of 16**; 75.9 mm (floor top 70.4, i.e. at most 5.5 mm into the 8 mm plate) |
| Gate 3: cavity, against the raised floor | 0.0 PASS | 0.0 PASS |
| Gate 4a: blue / beige | 0.384 FAIL / 1.79 | 0.402 FAIL / 1.79 |
| Blue COM against ev10, along file z | +12.8 mm | +16.1 mm |

**Reading.**
- The thicker plate stops the f124 drop crossing (0 of 16 copies), in line with determined-wright's nest test
  (max 4.02 mm into the plate, 0 through) [R].
- The cost is gate 1: the plate now reaches the beige base at the start of the rest (f124, 3.9 cm3 > 3.0).
- The f111 drop frame (the pair 32 mm in the air, in hand) still overflows in 3 of 16 copies in plain MuJoCo.
- A5's expectation "gate 1 unchanged" is **falsified** at the max; the median is unchanged.
- FlashCHORD remains the contact gate. v5 is a standby; ev10cs4 stays the frozen candidate.

**Time order (UTC, this machine's clock; other sessions' stamps may be offset).**

| Time | Event |
|---|---|
| 05:12 | Request read |
| 05:13 | A5 committed (99be31e), before building |
| 05:13 | v5 built; md5 diff against ev10cs4 |
| 05:14-05:15 | Measures |
