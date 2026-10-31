# GT-free screen of the pack-7 eval references for gross errors (H-gross), 31 Oct 2026

CPU only (this cloud VM, 4 cores), $0. No Vast, no GPU, no Kaggle; nothing posted; no reference, pack or submission
changed. Labels: [M] measured here, [E] estimate, [H] hypothesis. The flags were pre-registered in `PREREG.md`
(block 1 16:41 UTC, block 2 16:43 UTC) before any eval indicator was computed (first eval screen 16:44:43 UTC).

## Answer first

1. **No persistent gross error (> 5 cm or > 20° over a large share of an episode) in any of the 36 reference
   objects [M].** No identity swap, no below-table or interpenetrating object, and no wrong frame-0 placement.
   - The two look-alike pairs pass the identity check. Eval 10 cups: the blue cup images 107 grey levels darker than
     the beige cup on 8 of 8 frames. Eval 25 boards: correct at frames 0–55 (perception: knob score −64 as tracked
     vs +51 swapped).
   - Frames 0–9 agree with depth for every object (only the eval-20 pitcher: 6 of 10 frames, median residual 0.3 cm).
2. **What the screen does find: transient errors, 10–45 frames each [M].** All are in hand-held phases.
   - Three blue-cup tracking errors while the cup is in hand: eval 32 f21–33 (on the wrist/watch, a known failure
     type), eval 14 f35–45 (lags behind the lifting hand) and eval 33 f46–90 (rendered behind or beside the hand).
   - Fast-motion jumps of the spoon (evals 32, 33, 36).
   - Reference-stage downward shifts of 3–5 cm on held or placed objects (evals 3, 6, 8, 20, 28, 32). Depth agrees
     with the perception, not with the reference.
3. **Board impact [E]:** if the rollout followed every flagged window, the sum is ≈ 0.15–0.2 cm of board RPE. That is
   ≈ 10–15 % of the ≈ 1.5 cm gap.
   - The rollout does follow the reference in these windows (mean sim − ref 0.4–2.8 cm inside them [M]).
   - The exception is eval 32's watch latch: sim − ref is 13.1 cm there. That window inflates our GT-free RPE, not
     the board's.
4. **H-gross is weakened.** Gross reference errors of the kinds this screen can see do not carry the 1.5 cm.
   - That points to H-diffuse (cm-level, mostly constant offsets that depth and these indicators cannot see), to
     H-spoon, or to the registration of our meshes onto the hidden scans.
   - Bound: the calibration has one gross public positive (ep23, a latched track plus a swap). A sideways offset at
     rest, a roll flip of a thin near-symmetric object (spoon, dust pan) and a constant registration offset are
     invisible to every indicator here.

## Ranked list (policy reference R; flags J/U/X/D/RP/I as in `PREREG.md`)

| rank | eval / object | flags | evidence (frames, magnitudes) [M] | sim − ref in window [M] | verdict |
|---|---|---|---|---|---|
| 1 | 32 blue_cup | J | f21: step 19.7 cm, axis flip 153°; f34: 14.5 cm, 148° back. Outline on the left wrist/watch in f21–33 (`fig/ev32_j21.jpg`); perception the same. Episode effect if followed ≈ 13 f × 18 cm / 259 f ≈ 0.9 cm [E] | **13.1 cm (not followed)** | transient latch (watch), known type; costs our GT-free RPE, not the board |
| 2 | 14 blue_cup | J | f46: step 18.8 cm (height 4.9 → 20.0 cm). The reference lags at the rack while the hand lifts the cup (f35–45 hidden in depth, `fig/ev14_j46.jpg`) | 2.4 cm (followed) | transient lag ≈ 11 f, ≈ 0.7 cm episode [E] |
| 3 | 33 blue_cup | J | f91: step 10.9 cm, 56°, after 45 frames hidden in depth (f46–90). The held cup is rendered behind or beside the hand, ≈ 5–10 cm (`fig/ev33_cup46.jpg`) | 1.4 cm (followed) | transient, ≈ 0.8 cm episode [E] |
| 4 | 32 wooden_spoon | J, D | steps 5.2–9.0 cm at f93/94/115/116 (stirring); depth-bad 0.305 (perception 0.212), runs f91–115, f199–220; the outline stays on the spoon (`fig/ev32_spoon91.jpg`) | 1.8 / 0.9 cm | thin and fast; no latch visible; H-spoon territory |
| 5 | 33 wooden_spoon | J, D | steps 5.1–8.6 cm at f190/252/262/263/282; depth-bad 0.348 (perception 0.293) (`fig/ev33_spoon251.jpg`) | 1.4–1.5 cm | same |
| 6 | 3 white_pot (RP-type, no flag) | – | the reference sits 4.9 cm **below** perception at f97 (> 3 cm on 41 frames, f81–231). Depth-bad in that window: ref 0.65, perception 0.00; median residual −1.8 vs 0.0 cm | 1.9 cm (followed) | reference-stage shift (glockt / rest settle), ≈ 0.6 cm episode [E] |
| 7 | 28 white_pot (no flag) | – | 4.0 cm below perception at f175, window f171–219 (end placement into the rack). Depth-bad: ref 1.00, perception 0.00 | 1.8 cm | same, final placement |
| 8 | 6 white_pot, 20 blue_cup, 8 beige_cup, 32 cup and spoon (no flag) | – | 3.3–4.2 cm downward shifts, 10–22 frames > 2 cm. Depth: ref worse, perception clean (`refperc_eval.json`) | 0.4–1.1 cm | same, small |
| 9 | 25 wooden_piece_1 / _2 | D, I / I | Knob rule on R: d < −20 on 10 consecutive sampled frames (f70–115); on P only 4. **False alarm:** board 1 (4 corner knobs) is the one lifted, and board 2 lies under the forearm (`fig/ev25_knobs_crop.jpg`); per-board scores in `id_eval/ev25_boards_ref.json`. The tracks are continuous (max step 3.4 cm) and stay apart until the cross. D: R lies within 1.2 cm / 2.9° of P but is shifted ≈ 1 cm on an edge-on board (depth-bad f36–118; P 0.003) | 2.8 cm | not gross; a ≈ 1 cm reference shift |
| 10 | 30 plastic_dish_rack; 19 mini_sweeper | D | rack: R 0.297 vs P 0.008, R within 0.83 cm of P (thin prongs); sweeper: R 0.281 vs P 0.226 (thin, in hand) | 1.2 / 2.2 cm | not gross |
| – | 36 wooden_spoon | J | 6.3 cm step at f151 | – | single-object episode, RPE 0 |

- Flags on the perception only (repaired by the reference z-snap): U on evals 14 and 32 blue cup (−3.9 / −4.0 cm
  below the table).
- No pre-registered flag at all on evals 1, 3, 5, 6, 8, 10, 15, 16, 20, 28, 35, 37 or 38. Evals 3, 6, 8, 20 and 28
  carry only the sub-threshold reference-stage shifts listed above.
- The visual contact sheets (6 frames per episode, `fig/sheets/ev*.jpg`) show the outlines on the right objects in
  all 16 two-object episodes. At that scale, misalignments under ≈ 3–4 cm do not show.

## GT-free fix ideas (none tested; each needs a public-twin gate against mocap before use)

- **Cup latch guard (evals 14, 32, 33):**
  - When the tracked cup steps > 5 cm, flips its axis by > 45°, or reads hidden in depth for ≥ 5 frames while a hand
    is within reach, replace the window by hand-rigid transport from the last trusted frame, or by interpolation
    between trusted frames.
  - It would touch the perc2 tracks and mkref references of evals 14, 32 and 33, then a retrain.
  - [E] ≤ 0.05 cm board RPE each.
- **Depth-checked reference settle (evals 3, 6, 20, 28; 8, 32):**
  - Reject or cap (for example at 2 cm) any contact-retarget / rest-settle / glockt correction that makes the depth
    agreement worse than the feeding perception's.
  - It would touch the reference build (`contact_retarget.py` / `grasp_lock.py` / mkref settle) and a retrain of those
    evals.
  - [E] ≤ 0.1 cm board RPE in total.
  - [H] Falsifier: on public twins (ep2, ep26/27, ep21/22), the capped reference has no lower mocap RPE than the
    current one. The rpe-decomp found reference-level changes move RPE by ≤ 0.01 cm, so expect little.
- **Knob rule hardening (not a fix of eval 25):** score only boards whose knob side faces the camera and which lie
  outside the hand mask.

## Calibration (public only, before any eval value) [M]

Public set: the 20 public 25-Oct perception tracks, 33 objects (the tracks the 30 Oct depth audit scored). The gross
label comes from the existing public per-frame table `docs/research/work/depth-audit-20261030/calib_gt/v2/per_frame.csv`
(global-alignment ADD > 5 cm).

| indicator | clean max (31 objects) | ep23 piece 1 (latched, swapped) | ep23 piece 2 (swapped) |
|---|---|---|---|
| per-frame COM step | 3.3 cm | 22.3 cm | 2.4 |
| per-frame rotation step | 28° | 148° | 11° |
| below the table | −2.8 cm, 0 frames < −3 | −4.7 cm, 29 frames | −2.4 |
| penetration | 0.9 cm | 0.9 | 0.9 |
| depth-bad share / longest run | 0.155 / 36 | 0.342 / 73 | 0.132 / 9 |
| knob rule d < −20, longest run (sampled every 5) | ep24: 0 | **29 (f0–140)** | (same pair) |

- Cups (grey level, because ego_cam_c is monochrome): ep11 blue 55–73 vs beige 147–166 while the cups stand apart.
- Not used as flags: rest float (it fires on held-still objects) and rest tilt (it fires on the pitcher and the
  beige cup, whose meshes give 44–58° on clean tracks).

## Integrity and disclosures

- **No eval ground truth was read.** The inputs were:
  - our eval perception (`poses.npz`), table frames, hands and policy references from the HF store;
  - the eval depth caches (deleted after use);
  - the eval ego_cam_c videos and the calibration;
  - our meshes;
  - the evaluator output parquets of our own rollouts (achieved and reference columns).
- `refine.assert_inference_input` guarded the depth and screen inputs.
- Public GT was used only as calibration labels, through the existing public `per_frame.csv`. The public dataset
  parquets that sit in this scratchpad (`t3/`, from an earlier task) were not opened.
- Before PREREG block 1, the only eval values looked at were format checks: eval 3's `T_table_from_world` matrix and
  array shapes, and the eval-25 rollout parquet schema. No indicator value was computed before block 1.
- **Amendment (cup rule):**
  - The pre-registered window ("before either cup first moves, static mask") was empty. The beige cup's static mask is
    false on every frame, because cup spin jitter exceeds 2° per frame.
  - I replaced it with "both cups within 2 cm of their frame-0 position" (frames < 38). This was done after seeing the
    empty window and after the whole-episode grey percentiles had been printed.
  - The verdict does not depend on the window: blue is darker by 100–110 grey levels on every one of the 8 frames.
- **The I flag on eval 25 fired by the pre-registered rule.** I classify it as a false alarm on post-hoc evidence (per-board
  scores, full-resolution frames). It is reported as fired.
- **D on references is more sensitive than its perception-mode calibration.** Thin or edge-on objects shifted ≤ 1.2 cm
  trip it (eval 25 piece 1, eval 30 rack).

## Method and commands (code: branch `claude/standings-20261031` @ ca853ea plus this folder, uncommitted)

`S=/tmp/claude-0/-home-user-v2d-track3/6190fffb-f3a1-5d0e-84bd-7370ece99c2f/scratchpad`; `D=` this folder;
the pylib is `$S/eg/pylib` (embreex 4.4.0.post1, opencv-python-headless 5.0.0.93, rtree).

```
python3 -I $D/fetch.py $S/eg/dl small; python3 -I $D/fetch_pub.py $S/eg/dlpub poses   # + video_pub / video_eval
PYTHONPATH=$S/eg/pylib python3 $D/screen.py $D/manifest_pub.json $D/screen_pub.json      # public calibration
python3 $D/calib_depth_pub.py docs/research/work/depth-audit-20261030/calib_gt/v2/per_frame.csv $D/calib_depth_pub.json
PYTHONPATH=$S/eg/pylib python3 $D/identity.py boards|cups <video> <calib> <out> --poses .. [--ref .. --table ..] --meshes meshes/library_v3
PYTHONPATH=$S/eg/pylib python3 $D/screen.py $D/manifest_eval.json $D/screen_eval.json      # eval, after PREREG
S=$S R=<repo> bash $D/run_depth.sh <ep>    # x20, 2 parallel: fetch depth, depth_audit.py perception + --ref modes, delete
python3 $D/depth_summ.py $S/eg/depth $D/depth_eval.json
PYTHONPATH=$S/eg/pylib python3 $D/events.py $D/screen_eval.json $D/manifest_eval.json $D/events_eval.json
python3 $D/final.py $D/screen_eval.json $D/depth_eval.json $D/events_eval.json $D/id_eval $D/evalgross.json
PYTHONPATH=$S/eg/pylib python3 $D/refperc.py $D/manifest_eval.json $S/eg/depth $D/refperc_eval.json
python3 $D/simfollow.py <pack6 results dir> <c33B results dir> $D/simfollow_eval.json
PYTHONPATH=$S/eg/pylib python3 $D/overlay.py <video> <calib> <poses> <ref> <table> <meshes> f1,f2,.. <out.png>
```

- Depth audits: `pipeline/depth_audit.py` (sha256 53fc8abf…), thresholds unchanged, `--no_rest`, every frame.
  - It ran on 20 episodes × 2 modes, 16:44–16:56 UTC. The outputs are in `depth_audit/{perc,ref}/ep*/`.
- Compute: ≈ 15 min of CPU in total.

## Files

| File | Content |
|---|---|
| `PREREG.md` | flags and thresholds, timestamped before the eval values |
| `evalgross.json` | per-object flags, magnitudes, jump events, ranking, identity results |
| `screen_{pub,eval}.json`, `depth_eval.json`, `calib_depth_pub.json` | raw indicators |
| `refperc_eval.json`, `simfollow_eval.json`, `events_eval.json` | reference − perception shifts with depth verdicts; rollout following; jump events |
| `id_pub/`, `id_eval/` | knob-rule and cup-grey series |
| `fig/` | overlays (red/green hull = reference, dots = perception), `sheets/` = 6 frames per eval episode |
| `*.py`, `run_depth.sh`, `manifest_*.json` | code and inputs |
