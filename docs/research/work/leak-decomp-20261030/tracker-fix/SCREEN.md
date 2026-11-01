# GT-free eval screen for the four tracker failure modes (PLAN §4 item 2), 31 Oct 2026

This is eval QA outside the leak study (`../PLAN.md` §6). It reads only our own stored eval perception outputs and our meshes,
with the detectors and thresholds frozen in `PLAN.md` §3 and the four DIAGs. It changes no reference and tunes nothing.
CPU on this VM, $0; no GPU, Vast or Kaggle; no commit. Labels: [M] measured, [E] estimate, [H] hypothesis.
Eval episodes have no ground truth. Nothing here reads mocap, scans, `observation.objects` or scores.

Provenance: an earlier attempt (≈ 23:45–00:05 UTC, cut by a usage limit, committed as WIP in e50ec1e) pulled the inputs and
ran screens A–E. This continuation reviewed that work, re-ran S6 with the committed `pipeline/refine.py`, and added four
checks: which VO switches rule K can see, the eval-36 burst, the eval-10 camera, and the sweeper lean. It also corrected
three readings (§6).

## Verdict
1. **M4, the frame-0 detection decoy (ep0), is not flagged on any screened eval (1, 3, 5, 6, 8, 20, 28 for the area gate; 8, 14, 32, 33 for S9) [M].**
   - Area screen: all 14 chosen proposals on evals 1, 3, 5, 6, 8, 20 and 28 have area ratios 0.60–1.07. The flag is > 1.5.
   - The smallest margin over an oversized decoy is eval 8's beige cup at 0.077. Eval 1's pot is next at 0.106. On public
     ep0 the margin was 0.005.
   - S9 fires on none of evals 8, 14, 32 and 33. Eval 8's packed perception has no guard event. The re-acquisitions on 14,
     32 and 33 follow 9–12 cm of carry, not a quasi-static wrong segment.
2. **M2, the rotation anchor's frame-0 tilt (ep31), is not flagged on any eval [M].**
   - Every rotation anchor's post-guard mask coverage is ≥ 0.855. The gate is < 0.70.
   - Eval 30's sweeper scores 0.855, against 0.52 on its twin ep31.
   - On 19, 32, 33 and 35–37 the anchors score 0.89–0.95.
3. **M3, the VO camera jump (ep24), is not flagged on any eval [M].** Only evals 35 and 36 have a burst (≥ 4 keyframe switches
   in 25 frames). Rule K (S7) stays below 1 cm on every eval (max 0.80 cm, eval 28).
   - Eval 25 is the DIAG's main M3 target. It has 3 keyframes, at most 1 switch in 25 frames, and K 0.36 cm. An untouched
     board was seen at both switches, so eval 25 is clean.
   - Eval 36: the burst falls at the end (f375–394), while the spoon rests. The spoon moves ≤ 0.32 cm across the burst's
     keyframes, so there is no jump.
   - Eval 35 stays **unresolved**. Its burst (f25–48) happens while the spoon is picked up and held, so no track can measure
     the camera there.
4. **M1, the static container lifting under a nested object (ep11): eval 10's track shows ep11's M1 signature [M on our track; H that it is a tracker error: GT-free depth at f150 is ambiguous], and S6 as frozen does not fire there [M].** The committed `refine.step_S6` freezes only the racks of evals 14, 15, 16, 28 and 30. They move ≤ 0.75 cm and
   do not lift.
   - Eval 10's blue cup really slides 4.1–4.9 cm at f38–46, so its horizontal travel exceeds the 2 cm rule. Four checks
     agree: the left fist moves 4.0 cm with it, the depth fits the slid pose, the camera is right to ≤ 0.6 cm, and a power
     check recovers an injected 4.5 cm offset.
   - It then shows ep11's signature:
     - +3.1 to +3.7 cm while the beige cup is lowered into it (f100–117);
     - +1.6 to +2.4 cm held after both hands have left (f120–160).
     - The camera's share is ≤ 0.4 cm.
5. **Eval targets for PLAN §4** (step 1's eval leg included, because S6 has none):
   - **Step 1 (S6):** no eval-10 target under the frozen rule.
   - **Step 3 (T5 VO):** no confirmed eval target. Eval 35 is the only open candidate.
   - **Step 4 (GPU perception box):** one eval target, eval 10, through T2's masking. T3 (S8) and T4 (area gate, S9) have
     none and are insurance for any re-perception.
   - **Step 5 (rollout gates):** neither listed gate has an eval target (ep31 for M2, ep24 for M3). The gate eval 10 needs is
     ep11, with whichever M1 fix passes T2.

## 1. Inputs and method
**Eval perception behind packs 6 and 7.** The sources follow `ops/jobs/h5_reeval.sh` RUNS and `../../depth-audit-20261030/MAP.md`
§3, which has the sha256-checked feeding perception of every packed reference.

| evals | run behind the packed reference |
|---|---|
| 1, 3, 5, 6, 10, 15, 16, 19, 20, 28, 35–38 | `runs/20261026-pack6-5203d42/perc2/ep<N>` |
| 8 | `runs/20261025-evb0810-ee7ba8e/perc2/ep8` (library_v3x beige cup) |
| 14 | `runs/20261025-evb1420-ee7ba8e/perc2/ep14` |
| 25 | `runs/20261026-c25s42-feb0407/perc2/ep25` |
| 30 | `runs/20261025-std30-ee7ba8e/perc2/ep30` |
| 32 | `runs/20261026-fr32s46b-5e0e100/perc2/ep32` |
| 33 | `runs/20261026-fr3233s43-6a8a0e2/perc2/ep33` (pack 7's eval 33 uses the same reference) |

- Eval 10's reference was built from `20261024-evB-664e5fd` files with the same sha256 as pack 6's copies (`T1/scripts/t1_eval10.sh`).
- The pack-8 candidate's eval-1 carve is not covered.

**Files per eval:**
- `det_f0.npz`: frame-0 proposals, masks, scores and half-resolution depth;
- `vo.json`: keyframes;
- `poses.npz`: `world_T_cam`, `cam_T_<obj>`;
- `track_guard.json` where the guard was on (8, 14, 25, 32, 33);
- `refs/perc2mck/ep<N>/hands_refined.npz` from the same run;
- `meshes/library_v3` (`library_v3x` for eval 8's beige cup).

Every track, detection, depth, VO and hands path the code opens passes `refine.assert_inference_input` (refine's own
`checked()` for S6). Meshes are our library files.

**Re-acquisition frames.** They come from the store listing (`det_f46.npz` on 14, `det_f21/f34` on 32, `det_f91` on 33) and
from the tracks' own jumps, which agree. The perc2 `log.txt` files were pulled and grepped by hand only, as a cross-check.
They are perception logs (GT-free), but `assert_inference_input` refuses that file name, so no code reads them.

**Screens** (`screen/scripts/eval_screen.py`, logic copied from the DIAG scripts; thresholds as frozen):

| screen | mode | rule (frozen) | evals |
|---|---|---|---|
| A area ratio | M4 | chosen proposal's metric area / the template's largest silhouette > 1.5 | 1, 3, 5, 6, 8, 20, 28 |
| B S9 trigger | M4 | first re-acquisition at k jumps > 5 cm or > 30°, and the track over [0, k) stayed within 4 cm / 25° | 8, 14, 32, 33 |
| C VO burst + S7 | M3 | ≥ 4 keyframe switches in 25 frames, plus rule K's camera correction ≥ 1 cm (h3_r5_w2) | all 20 |
| D anchor coverage | M2 | rotation anchor's mask coverage of its predicted visible silhouette < 0.70 | 30, 19, 32, 33, 35–37 (all 20 computed) |
| E S6 static hold | M1 | horizontal travel < 2 cm (non-axisymmetric also rotation < 10°) | all 20 |

**Calibration on public data, GT-free** (`--public`: the 25 Oct `refine/in` tracks plus Phase-1 P_o; `public_check.log`) [M].
Every number below reproduces the DIAG's value.

| check | public result |
|---|---|
| S6 frozen set | exactly ep11's blue cup and the racks of 12, 13, 26, 27, 31 |
| coverage | ep31 sweeper 0.516, ep18 0.505, ep26 rack 0.001 |
| area | ep0 P_o pot margin 0.005; chosen ratios 0.16–1.09 |
| bursts | ep24 7, ep22 4, ep41 4, all others ≤ 3 |
| rule K end corrections, P_o | ep24 2.63, ep12 0.58, ep13 0.41, ep22 0.37, ep27 0.30, ep0 0.11 cm |

- S6 was re-run with the committed code: `refine.step_S6` / `s6_plane` / `Obj` at e50ec1e (unchanged at 6bbb52a), defaults
  2 cm / 10°, plane from `det_f0` depth (`s6_committed.json`). The frozen sets and per-object numbers are identical to
  screen E's on all 20 evals [M].
- **Post-guard masks.** No eval in screen D's set had a frame-0 retry. The guard was off on 19, 30 and 35–37, and
  `f0_retries` = 0 on 32 and 33. So `det_f0`'s chosen mask is the post-guard mask there. This differs from public ep0's lid,
  where it is not (PLAN §1).

## 2. Results per screen
### A. Area ratio of the chosen frame-0 proposals (M4) [M]

| eval | object (slot; * = rotation anchor) | ratio | oversized eligible decoys | margin over best decoy | flag |
|---|---|---|---|---|---|
| 1 | white_pot (0*) / white_pot_lid (1) | 0.716 / 1.071 | 4 / 0 | 0.106 / – | no |
| 3 | white_pot (0*) / wooden_spoon (1) | 0.860 / 0.817 | 1 / 3 | 0.403 / 0.140 | no |
| 5 | white_pot (0*) / wooden_spoon (1) | 0.829 / 0.846 | 2 / 3 | 0.384 / 0.231 | no |
| 6 | white_pot (0*) / wooden_spoon (1) | 0.856 / 0.810 | 3 / 5 | 0.397 / 0.198 | no |
| 8 | beige_cup (0) / white_pot (1*) | 0.916 / 0.816 | 1 / 1 | **0.077** / 0.417 | no |
| 20 | blue_cup (0) / water_pitcher (1*) | 0.597 / 0.604 | 0 / 2 | – / 0.324 | no |
| 28 | plastic_dish_rack (0*) / white_pot (1) | 0.805 / 0.909 | 0 / 1 | – / 0.442 | no |

Eval 1's pot mask (13.0k px) is about pot + lid (predicted 5.9k + 7.4k px; IoU 0.41 with the pot alone), as in ep0's P_o
choice. Its decoys are table-sized (2.4–3.6×). Eval 8's beige decoy is proposal 47 (2.1×, score 0.300 vs 0.377); with the
gate it would be barred.

### B. S9 conditions on the re-acquisitions (M4) [M]

| eval | guard events in the packed perception | first k | jump at k | cup-axis jump (spin-free) | track over [0, k) | S9 |
|---|---|---|---|---|---|---|
| 8 | none (`evb0810`: 0 retries, 0 re-acquisitions) | – | – | – | – | no trigger |
| 14 | 1 re-acquisition (blue cup) | 46 | 19.7 cm, 116° | 7.9° | 12.4 cm, 70° | does not fire |
| 32 | 2 (blue cup) | 21 (then 34) | 15.4 cm, 167° | 155° | 9.0 cm, 97° | does not fire |
| 33 | 1 (blue cup) | 91 | 11.4 cm, 103° | 57° | 9.6 cm, 128° | does not fire |

- Eval 8's "frame-0 retry + 2 re-acquisitions" (work log, 25 Oct) belonged to the guard check run with the v3 beige cup.
  The packed `evb0810` re-track with `library_v3x` has none.
- What precedes k on 14, 32 and 33 (`reacq_profiles.txt`) is not a wrong frame-0 segment but a **cup lost mid-carry**:
  - frames 0 to the first touch stay within ≤ 0.7 cm;
  - the cup is then carried 9–12 cm;
  - the track drops away from the hand and sinks: 14 f41–45, 32 f18–20 and f22–33, 33 f49–90 (42 frames). Its centre sits
    3–6 cm below the cup's resting height, with up to 1.8–2.1 cm of the surface under our table plane;
  - the guard then re-acquires the cup next to the hand (0.4–1.4 cm).
  - That is outside M1–M4 (§3).

### C. VO keyframe bursts and the S7 magnitude, all 20 evals (M3) [M]
Columns: "max switches / 25 f" with its start frame; "K max" is rule K's camera correction; "switches K sees" counts switches
with an anchored object within ±2 frames (`k_coverage.txt`).
- K = 0 at an unseen switch means **not measurable**, not "no jump".
- The burst count is the primary detector. Publicly a jump came only with 7 switches (ep24); bursts of 4 (ep22, ep41) had none.

| eval | frames | keyframes | max switches / 25 f | burst ≥ 4 | K max (cm) | switches K sees |
|---|---|---|---|---|---|---|
| 1 | 335 | 3 | 1 (f58) | no | 0.35 | 1/2 |
| 3 | 313 | 5 | 1 (f17) | no | 0.38 | 2/4 |
| 5 | 288 | 5 | 2 (f35) | no | 0.00 | 0/4 |
| 6 | 243 | 3 | 1 (f40) | no | 0.00 | 0/2 |
| 8 | 219 | 5 | 2 (f82) | no | 0.00 | 0/4 |
| 10 | 161 | 3 | 1 (f54) | no | 0.00 | 0/2 |
| 14 | 158 | 5 | 3 (f74) | no | 0.00 | 4/4 |
| 15 | 166 | 5 | 1 (f32) | no | 0.21 | 4/4 |
| 16 | 173 | 4 | 1 (f57) | no | 0.30 | 1/3 |
| 19 | 235 | 3 | 1 (f151) | no | 0.00 | 1/2 |
| 20 | 202 | 9 | 3 (f14) | no | 0.00 | 0/8 |
| **25** | 356 | 3 | 1 (f66) | no | 0.36 | **2/2** |
| 28 | 220 | 7 | 2 (f25) | no | **0.80** | 6/6 |
| 30 | 263 | 3 | 1 (f203) | no | 0.00 | 1/2 |
| 32 | 259 | 4 | 2 (f28) | no | 0.37 | 2/3 |
| 33 | 348 | 9 | 3 (f330) | no | 0.28 | 4/8 |
| **35** | 421 | 16 | **5 (f25)** | **yes** | 0.41 (end rest, f414–415) | 1/15; burst 0/5 |
| **36** | 407 | 14 | **4 (f375)** | **yes** | 0.00 | 2/13; burst 1/4 |
| 37 | 151 | 3 | 1 (f38) | no | 0.00 | 0/2 |
| 38 | 263 | 4 | 1 (f36) | no | 0.00 | 1/3 |

- **Eval 36** (`burst36.txt`). The spoon is released at about f374 and rests through f376–406. Its steps at keyframes
  382 / 388 / 394 are 0.19 / 0.19 / 0.07 cm, against 0.02–0.32 cm between keyframes. Segment-mean steps across them are
  0.32 / 0.07 / 0.12 cm; net f377→406 is 0.26 cm. Keyframe 375 coincides with the release and cannot be read. There is no
  ≥ 1 cm camera step in the rest of the burst [M].
- **Eval 35** (`burst35.txt`). Keyframes 25 / 30 / 35 / 39 / 48 fall while the spoon is picked up and lifted 12 cm, held
  (hand ≤ 1 cm). One object, held, so its camera step is not measurable from tracks. **Unresolved.** Two things could
  resolve it on CPU: the T5 VO re-run, or the background-ICP check of §4 on 2–3 eval-35 depth frames. Eval 35 is in the
  depth audit's spoon set, so reading its depth would put it under `PREREG.md` note 2, as eval 3 already is.

### D. Rotation-anchor mask coverage, post-guard (M2) [M]
Gate < 0.70. PLAN's set is in bold.

| eval | anchor | coverage | eval | anchor | coverage |
|---|---|---|---|---|---|
| 1 | white_pot | 0.928 | 20 | water_pitcher | 0.930 |
| 3 | white_pot | 0.968 | 25 | wooden_piece_1 | 0.991 |
| 5 | white_pot | 0.966 | 28 | plastic_dish_rack | 0.969 |
| 6 | white_pot | 0.964 | **30** | **mini_sweeper** | **0.855** (IoU 0.695) |
| 8 | white_pot | 0.961 | **32** | **wooden_spoon** | **0.905** |
| 10 | none: cups only (blue 0.938, beige 0.963) | – | **33** | **wooden_spoon** | **0.934** |
| 14 | plastic_dish_rack | 0.967 | **35** | **wooden_spoon** | **0.893** |
| 15 | plastic_dish_rack | 0.983 | **36** | **wooden_spoon** | **0.951** |
| 16 | plastic_dish_rack | 0.985 | **37** | **wooden_spoon** | **0.944** |
| **19** | **mini_sweeper** | **0.908** | 38 | mini_dust_pan | 0.986 |

- The S8 gate opens on no eval.
- Side information, not a detector (`lean.txt`): the sweeper's frame-0 lean from our table normal is 7.7° on eval 30 (end
  rest 6.7°) and 1.5° on eval 19.
  - Publicly it is 8.6° on ep31, which had a 9° registration error, and 3.6° on ep18.
  - A real lean against a fin cannot be told from a tilted registration without truth, so lean decides nothing here.

### E. S6 frozen sets, all 20 evals (M1) [M]
- **Frozen (identical with the committed `refine.step_S6`):** the rack on evals 14, 15, 16, 28 and 30.
  - Horizontal travel 0.59 / 0.50 / 0.72 / 0.75 / 0.67 cm; rotation ≤ 3.7°.
  - Largest rise while another object is over the rack's footprint: 0.16 / 0.58 / 0.65 / 0.69 / 0.59 cm.
  - So no rack shows the M1 lift. Freezing moves each rack by ≤ 0.75 cm (twin gains ≤ +0.007 lib; ep11 DIAG puts these evals
    at ≤ +0.001 LB together [E]).
- **Not frozen:** every other object. The smallest horizontal travels are 4.91 cm (eval 10 blue cup), 6.55 (eval 3 pot),
  6.87 (eval 33 blue cup), 6.96 (eval 20 blue cup) and 7.70 (eval 8 pot).
  - The public gap was ≤ 1.0 cm static vs ≥ 4.3 cm moving.
  - Eval 3's pot is the PLAN's marginal M1 candidate ("held on the table while stirring"). Our track lifts it 5–7.7 cm while
    held (f66–216) and puts it back by f246. MAP.md §5 found pack-6 perception agreeing with depth at f100 (median
    r −0.01 cm). So this is most likely a real lift, not M1.

## 3. Per eval: which modes are present
"–" = mode not applicable (object classes outside the screen's set).

| eval | M1 static container lifts | M2 anchor f0 tilt | M3 VO jump | M4 f0 decoy / S9 | other |
|---|---|---|---|---|---|
| 1 | no | no (0.93) | no | no (0.72, margin 0.106) | – |
| 3 | no (pot really lifted) | no | no | no | – |
| 5 | no | no | no (K blind, 2 switches) | no | – |
| 6 | no | no | no | no | – |
| 8 | no | no | no (K blind, 2 switches) | no (beige margin 0.077; no guard event) | – |
| **10** | **YES (signature); S6 does not fire, the cup slides 4.9 cm** | – (cups) | no | – | §4 |
| 14 | no (rack frozen, no lift) | no | no | no (S9 does not fire) | cup lost mid-carry f41–45 |
| 15 | no (rack frozen) | no | no | – | – |
| 16 | no (rack frozen) | no | no | – | – |
| 19 | no | no (0.91) | no | – | – |
| 20 | no | no | no (3 switches; K blind) | no | – |
| 25 | no | no | **no: clean (2/2 switches seen, ≤ 0.36 cm)** | – | – |
| 28 | no (rack frozen) | no | no (K 0.80 < 1) | no | – |
| 30 | no (rack frozen) | **not flagged (0.855)** | no | – | – |
| 32 | no | no (0.91) | no | no (S9 does not fire) | cup lost f18–20, f22–33; spoon one-frame steps 6–9 cm (f93, 94, 115) |
| 33 | no | no (0.93) | no | no (S9 does not fire) | cup lost f49–90; spoon steps 5–8 cm (f190–282) |
| 35 | no | no (0.89) | **burst flagged; magnitude not measurable → unresolved** | – | – |
| 36 | no | no (0.95) | burst flagged; resting spoon shows ≤ 0.32 cm → no | – | spoon 6.2 cm step at f151, 33° spin at f74 |
| 37 | no | no | no | – | – |
| 38 | no | no | no | – | – |

The cup losses on 14, 32 and 33 and the one-frame spoon steps match none of the frozen rules. Whether they survive into the
packed policy references (contact retarget, rest settle, glockt) was not checked. The fix class for the losses is the ep0
DIAG's F2 "moving case" (backward re-track) [H, untested].

## 4. Eval 10: the M1 lift is there, but the blue cup is not static
Per-frame data: `e10_profile.txt`, `e10_hand_rerun.txt`, `e10_depth.txt`, `e10_vo_bg.txt`.

**The cup really slides [M]:**
- **Track and fist.** At f38–46 the blue cup's track steps 0.24 → 4.56 cm along one direction (max 4.91 at f52, 4.1 at the
  end). Over the same frames the left-hand centroid, a fist on the cup (joint-to-centre ≈ 4 cm), moves 0.20 → 3.95 cm along
  it. The hands are MediaPipe, independent of the object tracker.
- **Depth (our stored stereo depth, f60).** The tracked pose fits: median |r| 1.27 cm, 2.7 % of pixels behind. The cup held
  at its frame-0 position does not: 5.55 cm, 39.8 % behind. At f150: 0.96 cm / 26.8 % vs 4.91 cm / 68.4 %.
- **Camera.** Depth alone cannot tell a moved cup from a moved camera, so the VO was checked against the static background:
  - back-project f30/60/150 through our `world_T_cam`, drop the cups, hands and table top, and align onto f0 with trimmed
    ICP;
  - the correction is 0.16 cm at f60 and 0.60 cm at f150, 0.08 / 0.00 cm along the cup's step;
  - with the cup's step injected as a camera offset, the same ICP recovers 4.41 / 4.64 cm (power check).
  - So the camera did not move; the cup did.
- **Repeat run.** The 29 Oct evdepth perception run is bit-identical (deterministic). It rules out run-to-run noise only.

**The M1 signature after the slide** (v = height change of the cup centre along our plane normal, + up) [M]:
| frames | what happens | v |
|---|---|---|
| f0–35 | at rest | ≤ 0.15 cm |
| f40–95 | slide, fist, beige approaching | −0.4 to +1.6 cm |
| f100–117 | beige over the blue cup's centre (0.4–0.5 cm horizontal, 1.4–1.9 cm above), i.e. the nest | +3.1 to +3.7 cm (peak 3.69 at f117) |
| f120–160 | no hand within 7.7–21 cm from f125 | +1.6 to +2.4 cm (end +1.77) |

- **Camera share** [M, approx.]: at f150 the background ICP puts the camera's vertical part at +0.44 cm, so about +1.6 cm sits
  on the cup's own track.
- **Mechanism.** This matches ep11: P_o peaked at +5.3 cm at the insertion and held +2.4 cm after release, with the hands off.
  A released cup cannot stand 1.6 cm above its own frame-0 support [H: that it rests on the table at the end].
- **Depth at f150 is ambiguous** for the height: tracked vs frame-0 height gives median |r| 0.96 vs 0.97 cm, behind 26.8 % vs
  13.9 %, front 1.1 % vs 9.8 %.

**Consequences:**
- S6 (rule frozen in PLAN §3, ep11 DIAG Fix 1) freezes nothing on eval 10 [M]. The ep11 DIAG named this risk: "if eval 10's
  blue cup is actually [moved] … F1 does not trigger".
- The PLAN's eval-10 value (+0.004 to +0.012 LB, central +0.007 [E]) is still available, but only to a fix that does not need
  the container to be static over the whole episode:
  - **T2's masking** (other objects rendered out of the tracker's input, tracking frame by frame) [H]. It was pre-registered
    without eval data, and its ep11 test (blue \* ≥ 0.95) is the falsifier.
  - **A time-windowed static hold** (S6 applied after the last horizontal move) [H, new]. It would be designed after seeing
    eval 10's track. Its thresholds would have to come from public data only, under its own pre-registered public test.
    No public twin has a container that slides before the nest, so that part would stay untested.

## 5. What this does to PLAN §4
| step | eval target now | reading |
|---|---|---|
| 1 S6 static hold | **none** (racks only, ≤ 0.75 cm) | T1's public reference part ran in parallel and fails its rule on the P_o arm (ep27 * −0.0023). The T1 rollouts ($2.6–5.2) and the eval-10 S6 retrain ($2.6) have no eval target under the frozen rule. |
| 3 T5 robust VO + plane (CPU) | **none confirmed**; eval 35 unresolved | Eval 25 is clean, so the planned +0.004 central falls to ≈ +0.001 [E, weak]: eval 35 alone, p ≈ 0.1–0.35 from 1 jump in 3 public bursts, × +0.005–0.008 per jumped eval. Insurance for any re-perception; the $0 ep24 part on this VM is the only part with tool value now. |
| 4 GPU perception box (T2, T3, T4b) | **eval 10, through T2 masking** | T3/S8 (M2): no target (no anchor < 0.70). T4 area gate + S9 (M4): no target (insurance; smallest decoy margin 0.077, eval 8). The box's eval value now rests on T2's ep11 test. |
| 5 rollout gates | **none of those listed** | ep31 (M2) and ep24 (M3) have no eval target. If T2 passes, the gate that matters is ep11 (eval 10's twin) with the masked re-track, then an eval-10 retrain under the multi-draw rule. |

Revised value [E]:

| mode | PLAN central | now | why |
|---|---|---|---|
| M1 | +0.007 | unchanged in size | reachable only by masking (or a new rule), not by S6 |
| M2 | +0.003 | 0 | gate closed on eval 30 |
| M3 | +0.004 | ≈ +0.001 | eval 35 only |
| M4 | 0 | 0 | insurance |

## 6. Review of the earlier attempt (e50ec1e), corrections made here
- **Rule K's zeros.** "K max 0" was read as "no camera jump". On 5, 6, 8, 10, 20 and 37 rule K sees none of the switches, so
  0 there means not measurable. The verdicts stand, because the burst count is below 4 on all of them.
- **The evdepth re-run** was cited as reproducing the eval-10 step. It is bit-identical, so it is not independent evidence.
  The camera check above replaces it.
- **The depth test** (tracked vs unmoved cup) cannot separate a moved cup from a moved camera. Hence the background-ICP check
  with its power test.
- `lean.py` had run without saving its output; it is saved now (`lean.txt`).
- S6 was confirmed with the committed refine code; screen E's copy agrees exactly.
- The eval-8 guard history is clarified (§2 B).
- Eval-10 depth provenance gap: 4 frames (0/30/60/150) of our stored eval-10 stereo depth were pulled by the earlier attempt
  at 00:02 UTC: store `cache/depth/eval/ep10/`, the 29 Oct recomputation, 25.6 MB. The pull command was not saved. Eval 10 is
  not in the depth audit's spoon set, and nothing on eval was tuned or changed.

## 7. Not done / caveats
- Eval 35's camera (above).
- Whether the cup losses on 14, 32 and 33 reach the policy references.
- Overlay QA of eval 10's lift with `pipeline/track_overlay.py`. The parallel T1 step writes `T1/eval10/e10_s6_overlay.png`.
- The frozen screens are as good as their public calibration: one M3 case and one M2 case among 20 public episodes, and no
  public twin of a sliding container. "Not flagged" means "not flagged by the frozen detector".
- Eval 10's held height offset is [M] on our track and our camera. That the true cup sits on the table at the end is [H].

## 8. Commands, files, cost
This VM, CPU, $0. Code: repo at 6bbb52a (`pipeline/refine.py` as in e50ec1e) plus `screen/scripts/`.
`S` = scratchpad, `PY=$S/map/scoring/venv/bin/python`.

Earlier attempt, from `$S/screen`:
1. `$PY -I scripts/dl_retry.py dl store_pull_list.txt`: 73 single files, 16.6 MB, no listing, no 429.
2. `$PY -I scripts/eval_screen.py out/eval_screen.json` → `eval_screen.{json,log}`; with `--public` → `public_check.{json,log}`.
3. `$PY -I scripts/reacq_profile.py EP blue_cup F0 F1` → `reacq_profiles.txt`.
4. `$PY -I scripts/profile_s6.py 10 blue_cup` → `e10_profile.txt`.
5. `$PY -I scripts/e10_check.py` → `e10_hand_rerun.txt`.
6. `$PY -I scripts/e10_depth.py $S/screen/dl_depth/ev10_f0_30_60_150.npy` → `e10_depth.txt`.

This continuation, from `$S/screen` (lean) and `$S/screen2` (the rest), no store traffic:
1. `$PY -I scripts/lean.py` → `lean.txt`.
2. `$PY -I scripts/s6_committed.py out/s6_committed.json` (committed `refine.step_S6`).
3. `$PY -I scripts/k_coverage.py out/k_coverage.json` → `k_coverage.{json,txt}`.
4. `$PY -I scripts/burst_profile.py 36 366 406` and `… 35 15 55` → `burst36.txt`, `burst35.txt`.
5. `$PY -I scripts/e10_vo_bg.py $S/screen/dl_depth/ev10_f0_30_60_150.npy` → `e10_vo_bg.txt` (300-iteration trimmed ICP, about 2 min).

All scripts and outputs are in `screen/` here.

## Review amendments (31 Oct ~06:30 UTC, adversarial review of this report)
- The hands live in perc2's camera frame, so the fist moving with eval 10's cup rules out a tracker-only slip, not a
  camera error. The camera conclusion rests on T1's controlled 6-DoF camera check (passed its public controls; 0.09 cm
  vertical on eval 10, `T1/camcheck/eval10.json`) and on the ICP background check, which has only an injected
  pure-translation power check and no real positive control; its −0.44 cm at f150 sits inside its own floor (0.53 cm at f30).
- Wording corrected per the review: M1 on eval 10 is [M] on our track and [H] as a tracker error; the camera's share of the
  held offset is ≤ 0.4 cm; M4 is "not flagged on the screened evals", not "not present".
