# Weight-space repair of exercise 3's policy (pre-registered pilot, note 29 idea 2) — 2026-11-12

Status: COMPLETE. Repair agent: Claude (Opus 5.5), CPU only, this cloud container (4 cores, no GPU). No GPU rented, no
cost beyond Claude usage. Rules: work-log entry "2026-11-12 ~22:20 UTC — owner: go for all; PRE-REGISTRATION".
Development used only the unperturbed task (start frame 0, delay 0); no perturbed run was simulated before the final
evaluation. Labels: [M] measured, [H] hypothesis.

## Verdict: INCONCLUSIVE under the pre-registered rule, and in substance not a repair

| Arm | Unperturbed run | Perturbed runs completed (of 20) |
|---|---|---|
| unedited | fails (frame 352, object 0.101 m) | **9** |
| final edit (v10) | **completes** | **11** |
| random control, pre-registered construction | fails (non-finite action at the first step) | 0 |
| random control, sanitised (sensitivity check, not in the rule) | fails (frame 24, rotation) | 0 |

- **Repair?** No. The edit completes the unperturbed run, but it completes only +2 perturbed runs (the bar is +10,
  because the unedited completes k = 9 ≤ 10). It also fails one run the unedited completes (start 0, delay 3).
- **Not a repair?** Not triggered: the edit completes the unperturbed run and completes more perturbed runs than the
  random control (11 vs 0).
- **So the rule says inconclusive.** The "not a repair" clause escaped only because the random control is degenerate
  (see "Problems with the test bed"), so it is no evidence for the edit. Plainly: the edit fixed the unperturbed
  failure and made the handover more reliable, but it is far from the pre-registered repair bar.

Key numbers [M]: 21,024 of 1,160,356 stored numbers changed (1.81%): 19,415 set to zero, 1,609 written non-zero.
24 of 25 test rollouts used. Wall time 21:22–22:21 UTC (≈ 1 h); compute 308 s for the development rollouts and
410 s for the 84 final-evaluation runs (4 processes, 2 min 12 s wall).

## Where the edit helped and where it did not [M]

Failures of the 20 perturbed runs, by phase:

| | early, frames < 250 (pickup) | handover, frames 300–370 | completed |
|---|---|---|---|
| unedited | 5 (starts 8, 12, 16 at delay 0; 12, 16 at delay 3) | 6 of the 15 that reached it | 9 |
| final edit | 7 (the same five, plus start 20 at both delays) | 2 of the 13 that reached it | 11 |

- **Handover (the targeted failure):** success rose from 9 of 15 to 11 of 13 among runs that reached it.
- **Early pickup failure:** never seen in development, because perturbed starts were off-limits. With start frames
  8–20 the robot starts at that frame's reference pose with zero velocity and zeroed action filters, and the right hand
  tips the flask during the approach and grasp (rotation > 0.5 rad at frames 38–145). The unedited policy fails there
  too; the edit does not address it. It added two such failures at start 20. Chance or a side effect of the
  coordinate clearing cannot be told apart from one run each.
- **End of the episode:** every completed unedited run ends at a 0.146–0.147 m wrist error against the 0.15 m limit;
  the edit's completed runs end at 0.128–0.129 m.

Development probe on the unperturbed task (rollouts 11–24; output-bias jitter of sd 0.01 to put each run on a different
chaotic path): v10 completed 8 of 10 paths, the unedited 4 of 6. Fisher's exact test, two-sided, p ≈ 0.6. The final
evaluation agrees in size: a modest gain, not a fix.

## Diagnosis (offline analysis of traces; network replays on recorded observations; kinematics only, no simulation)

Task: right-to-left flask handover. The right hand carries the flask to ~frame 330; the left hand closes on it from
~300; the right releases ~360–385; the left carries it to ~870, places it and lets go.

Failure in rollout 1 (frame 352 = 17.60 s, object 0.1007 m), the chain I believed after rollout 1:
1. ~302–304: a ~1 cm push on the flask as the left hand closes. The left pinky MCP_FE is blocked at 0.24 rad while its
   reference closes to 1.2 rad: the flask sits ~8 cm away from the planned spot in the left-wrist frame, because the
   policy holds the left wrist ~0.43 rad off its reference orientation.
2. 305–330: the left finger command errors (ref − q, up to 4.2 sd) drive Joint6_R (right wrist) to its joint limit:
   pre-tanh 1.3 → 4.1, offset 0.40 → 0.81 rad. Block swap: the finger-command block accounts for +2.4 of the +2.8
   rise at frame 321, and it is the left fingers, not the right. The simulator's wrist-pair coupling then clips Joint7_R
   0.2–0.4 rad off its reference, and the right wrist, still holding the flask, twists (0.30 → 0.77 rad).
3. 310–353: the flask drops 3–4 cm, lags 5 cm in x, drifts 5 cm in −y. The policy's reaction to the 8-sd object-error
   inputs points roughly the right way for the right hand but is 3–10x too large.

What later rollouts showed (rollouts 2–24, all in the log below):
- **The unperturbed outcome flips under tiny weight changes** (rollout 2: an action change of 0.08 at frame 0 put the
  run on another path and it completed). One rollout cannot separate a repair from a lucky perturbation.
- **The Joint6_R climb is not necessary for failure** (rollout 3: Joint6_R held, the flask spun anyway).
- **The best predictor of a good handover is the left wrist's orientation error at ~300** about one fixed body axis
  n ≈ (0, 0.7, 0.7): 0.18–0.23 rad in every completed v10 handover, 0.27–0.57 in most failures. It is favourable, not
  necessary: two unedited runs completed at 0.36–0.37.
- **Failure modes at the handover:** a translation slip (rollout-1 type), and a spin about the common roll axis of the
  two wrists while the right grip fades (rollouts 3, 4, 7, probe seed 8). The policy's Joint7_R roll reacts to the spin
  in the corrective direction, but the right hand has lost its grip.
- **End phase:** the policy keeps the left fingers 0.15–0.30 rad more closed than the reference after placing the
  flask, so the hand stays on it. Any wrist correction then turns the flask (rollouts 6, 8, 9).

Network facts [M]: 221 of 1,024 block-1 wide units and 196 of block 0 never activate on rollout 1. But only 5 of 256
block-0 contract units (1 in block 1) are active in every frame, so writes must be designed through whatever is
active. A single input can be read cleanly from h0, block 0's input (r 0.99 for input 47), but not from h1 (−0.38).
Block 1 adds 0.7–0.8 of any write into h1 on top. All kernels have unit-norm columns (hyperspherical design); inference
does not need that preserved.

## Method: "private channels" in a residual network

The blog's networks were plain MLPs, where an idle unit can relay a signal through idle units in later layers. Here
every write into the 256-wide residual stream is seen by both blocks and by the head, through an RMS norm. So each
controller uses one cleared stream coordinate j:
- the embedding column, both blocks' reads of j, both contract units j and the head row j are set to zero;
- block-0 contract unit j becomes a wire (identity batch norm), so c0_j = relu(sum of gate writes);
- a repurposed idle block-0 wide unit reads raw inputs from h0 through a least-squares readout of the embedding kernel
  (computed from the weights only; fidelity checked on recorded traces) and writes relu(kappa · (input − threshold))
  into coordinate j;
- the value passes unchanged to the head, whose row j drives only the chosen outputs;
- inhibitors are further idle units that write negatively into the same wire, so the wire's own ReLU computes
  relu(gate − M · inhibitor): a two-level AND-NOT gate.

Clearing a coordinate costs a small change in normal behaviour (coordinate 78: action change 0.016 mean, 0.15 max on
rollout 1's observations). That is enough to move the chaotic path.

## Final edit (v10): four controllers. Code: `edit.py` → `build.v10`

| # | Controller | Coordinate / units | Gate (reads) | Output | Where the numbers come from |
|---|---|---|---|---|---|
| 1 | Joint6_R virtual limit | 78 / 887 | Joint6_R offset q − ref > +0.222 rad (input 47) | Joint6_R pre-tanh −6 per 0.1 rad (K = 60/rad) | threshold = training mean + 1.5 sd of input 47 (input batch-norm stats); also keeps the wrist-pair coupling from clipping Joint7_R during the handover; gain chosen with an offline model of the action pipeline (`j6_loop_model.py`) |
| 2 | Left-wrist orientation controller for the approach | 39 / 777, inhibitors 659 and 106 | rotation needed about body axis n > 0.15 rad, estimated from the 7 left-arm offsets (inputs 49–55) through the angular Jacobian at reference frame 290 (r 0.95–0.99 against the true error). Off while the left hand grasps (mean left finger command > 0.04, inputs 187–208) or holds (mean closure of five well-read finger inputs > 0.30) | Joint5–7_L along J567⁻¹n, K = 60/rad | n = common error direction in rollouts 1–4; Jacobians from `simulation.Kinematics` (`lwrist_controller.json`); threshold below the level of every successful handover; inhibitor thresholds from the phase separation in rollouts 2–7 |
| 3 | End-phase left-wrist position cap | 159 / 322 | m · (left-wrist body-frame position error, inputs 158–160) > 0.10 m | pinv(position Jacobian at reference frame 1000)·m on Joint1–7_L, ≈ 1.5 pre-tanh per cm on Joint4_L | m = error direction at frames 980–1021 of rollouts 2 and 5 (`lwrist_pos_controller.json`); threshold raised from 0.06 after rollouts 6, 8 and 9 showed that larger corrections turn the flask |
| 4 | Left-hand release | 161 / 67 | mean left finger command (ref − q) < −0.144 | all left finger pre-tanh −1.5 per unit gate | threshold = training mean − 3 sd of that mean; weak, it barely acts (rollout 8) |

No gradients, optimisers, data fitting or automated search. The data-derived quantities are directions (mean error
directions), thresholds read off training statistics or recorded traces, and least-squares readouts or pseudo-inverses
of the network's own weights and of the robot's Jacobians. Each is stated above and in the code.

## Rollout log (budget 25 unperturbed rollouts: start frame 0, delay 0; 24 used)

Each row: prediction written before the run; result after. Raw results: `rollouts.jsonl`.

| # | Actor | Mechanism believed / prediction (written before the run) | Result |
|---|---|---|---|
| 1 | unedited | Diagnostic. Predict the same deterministic failure as measured before: frame 352–353, object 0.101 m. Continue 60 frames past the failure for diagnosis only. | As predicted: fails at frame 352 (17.60 s), object 0.101 m, 0.325 rad, wrist 0.053 m. 6.6 s. |
| 2 | v02: Joint6_R virtual limit (coordinate 78, gate unit 887 on input 47, threshold 0.42 rad, K = 60/rad) | Mechanism tested: the Joint6_R climb (+ Joint7_R clip) twists the flask out of the reference (step 2). Predict: frames 0–300 nearly unchanged (object error at 300 within ±1 cm of 0.9 cm); Joint6_R offset ≤ 0.50 rad through 300–352 (was 0.81); right wrist orientation error ≤ 0.5 rad (was 0.77). If the twist is the main amplifier: object error at 330 ≤ 4 cm (was 6.7) and failure avoided or delayed past 360. If error at 330 is still ≥ 6 cm, the twist is not the main driver. | **Completed the reference** (max object error 4.9 cm; wrist error 0.148 m at the last frame, limit 0.15). But **the gate never fired** (max 0.0): the J6_R offset stayed ≤ 0.31 all run (rollout 1: 0.43 before the handover). The run took a different path from frame 1 (action difference 0.08 at frame 0 from clearing coordinate 78; joints 0.2 rad apart by frame 20). So the success is the side effect, not the mechanism: **the unperturbed outcome flips under a tiny weight change.** Prediction not tested. Rollout 1 vs 2 before the handover (280–300): J6_R offset +0.40 vs +0.18–0.26; J4_L −0.22 vs −0.08; J7_L +0.40 vs +0.17; flask-in-left-wrist error 9 vs 4 cm. |
| 3 | v03: as v02 with threshold 0.25 rad (physical: keeps the J7_R coupling clip off during the handover; also the training 2-sd edge, +0.28) | Same coordinate as v02, so the run is bit-identical to rollout 2 until the gate first fires (frame ~206 on rollout 2's states). Then the J6_R offset is held ≤ ~0.30. Predict: success with handover object error ≤ 3 cm through 352. A failure means pulling J6_R down from ~0.31 to ~0.27 during the carry harms it, and the threshold is rejected. | **Failed at frame 330 (16.50 s) on rotation**: object 0.040 m, 0.510 rad. The gate worked (J6_R offset held 0.28–0.32), but the flask rotated 0.08 → 0.51 rad over 300–330 while the right grip fell to 11–35 N. **The J6_R climb is not necessary for the failure; J6_R alone is the wrong lever.** Comparing rollouts 1–3 (identical until ~206 for 2 and 3): at the left hand's approach (240–250) all three have the flask 8–11 cm off the planned grasp spot in the left-wrist frame. By 300 the successful rollout 2 had corrected to 4.2 cm (J7_L +0.17, J4_L −0.08, J5_L −0.05, left wrist orientation error 0.23 rad). Failed 1 and 3 stayed at 8.7 / 7.8 cm (J7_L +0.40/+0.34, J4_L −0.22/−0.21, J5_L −0.13/−0.12; 0.44/0.37 rad). |
| 4 | v04: virtual limits at the training mean ± 1.5 sd of the joint offsets that drift in the failed runs: J6_R ≤ +0.222, J7_L ≤ +0.275, J5_L ≥ −0.079 (coordinates 78/39/159, gate units 887/777/322, K = 60/rad). J4_L skipped: its input cannot be read cleanly from h0 (r 0.66). | Hypothesis H6: the handover fails when the left hand reaches the grasp with the left-arm drifts (wrist rolled +0.3–0.4 rad), leaving the flask ~8 cm off the planned spot. Predict: the run diverges from frame 1 (three coordinates cleared: mean action change 0.03). J7_L offset ≤ ~0.32 and J5_L ≥ ~−0.13 throughout; at 300 the left wrist orientation error is ≤ 0.30 rad and the flask is ≤ 6 cm from the planned spot; the handover succeeds (object error ≤ 4 cm through 400). Falsifiers: precondition met but handover still fails → H6 is not sufficient; precondition not met despite the limits → the joint-space limits are the wrong lever. | **Failed at frame 328 (16.40 s) on rotation** (object 0.037 m, 0.529 rad), the same pattern as rollout 3. The limits held (J7_L offset +0.24 at 300, J6_R +0.27), but the **precondition was not met**: the flask was still 7.0 cm off the planned spot in the left-wrist frame at 300 (left wrist orientation error 0.31 rad). Other left joints made up the difference. **Per the falsifier: joint-space limits are the wrong lever.** In all four runs the left-wrist orientation error at the approach lies along the same body-frame axis n ≈ (0, 0.7, 0.7); along n: 0.22 (success) vs 0.31 / 0.37 / 0.44 (failures) at 300. |
| 5 | v05: J6_R limit (as v04) + left-wrist orientation controller on coordinate 39 / gate unit 777. Gate: the rotation the left wrist needs about n, estimated from the 7 left-arm offsets through the body-frame angular Jacobian at reference frame 290 (readout r 0.95–0.99 against the true error on rollouts 1–4), threshold 0.20 rad (the success level). Output: Joint5-7_L along J567⁻¹n (≈ +0.91, +0.01, −0.135 rad per rad), K = 60/rad. | Hypothesis H6 (task-space form). Predict: diverges from frame 1; the controller acts from ~120; left-wrist error along n ≤ ~0.24 rad through 240–310; at 300 the flask is ≤ 5 cm from the planned spot and the handover succeeds (object error ≤ 4 cm through 400). Falsifiers: precondition met and the handover fails → H6 not sufficient; precondition not met → controller too weak. Later phases (carry, place, release) not yet observed under an edit except rollout 2. | **Completed the reference, as predicted**: the precondition was met (left wrist error 0.21–0.24 rad over 300–330; total orientation error 0.24 at 300); clean handover (object error ≤ 1.8 cm through 352; max 4.3 cm over the run, at the carry ~500). **New risk:** the wrist error at the last frame is 0.1485 m (limit 0.15), the same as rollout 2 (0.1484). The left wrist drifts from 0.038 m (900) to 0.149 m (1022) because the policy commands left-arm offsets of 0.3–0.5 rad (J1_L −0.27, J4_L +0.40, J6_L +0.50, J7_L −0.51) after placing the flask, while the left hand keeps pressing it (200–450 N). The body-frame error is 3–5 training sd, along the same direction m ≈ (0.6, 0.27, −0.75) in both runs. |
| 6 | v06: v05 + end-phase left-wrist position controller on coordinate 159 / gate unit 322. Gate: m·(left-wrist body-frame position error, inputs 158:161) > 0.06 m (direct readout ≤ 0.017 before frame 870 on rollout 5, so no firing during the carry). Output: pinv(position Jacobian at ref frame 1000)·m, ≈ 1.5 pre-tanh per cm on Joint4_L. | Predict: diverges from frame 1 (three coordinates cleared). Handover precondition met again via the v05 controller (the handover is a robustness check of that controller on a new path); end controller acts from ~950; final wrist error ≤ 0.10 m (was 0.1485). Falsifier: end gate fires but the error still exceeds 0.12 → gain or direction wrong. | **Completed the reference, as predicted**: final wrist error 0.103 m (was 0.1485); the handover precondition held again on this new path (left wrist error 0.22–0.24 → 0.15 rad; object error ≤ 2.2 cm through 352). **Side effect:** the flask's rotation error rose from 0.09 (1000) to 0.27 rad (1022), and it was lifted 1 cm. The left hand still grips the placed flask: the reference opens the left fingers (mean 0.95 → 0.11 rad over 870–1022) but the policy keeps them 0.15–0.30 rad more closed (F_L 120–500 N). So the wrist cannot follow its reference (that is the drift), and pulling it drags the flask. |
| 7 | v07: v06 + left-hand release primitive on coordinate 161 / gate unit 67. Gate: mean of the 22 left finger commands (ref − q) < training mean − 3 sd (−0.144); before frame 900 it never went below −0.10 in rollouts 1–6, and it fires from 906–908 on rollouts 2/5/6. Output: all left finger pre-tanh −1.5 per unit gate (gate 1 per 0.1). | Predict: diverges from frame 1 (four coordinates cleared, mean action change ~0.035 where the gates are silent). Handover precondition met; release acts from ~905; at 1000 the left finger q − ref is ≤ +0.10 (was +0.22); F_L < 100 N by ~1000; final wrist error ≤ 0.10 m and final flask rotation ≤ 0.10 rad. | **Failed at frame 343 (17.15 s) on rotation** (0.506 rad), before the release phase, so the release primitive was not tested. At 300 the left-wrist error along n was 0.27 (the controller holds about 0.03–0.07 above its threshold). The flask spun about the common roll axis of both wrists (needed correction parallel to the J7_R axis, cos 0.92–1.00; J7_L 0.8–0.97). The policy's J7_R roll reaction (driven by the object-rotation-error inputs, +1.5–3.6 pre-tanh) was in the right direction, but the right hand had lost its grip (0–35 N). **Harmful side effect of my own edit found:** after the left hand closes (~300), the left-wrist controller's rotation turns the held flask *against* its reference (cos −0.64 to −0.99). Its gate was 0.4–1.0 over 300–330 in rollout 7 (0.2–0.56 in 6, ≤ 0.24 in 5), and it also fired during the carry (44–90 frames). |
| 8 | v08: v07 with the left-wrist controller (a) inhibited once the left hand grasps or holds (two inhibitor units writing −10 into the same wire, which computes relu(gate − 10·inhibit): mean left finger command > 0.04, unit 659; mean closure of the five best-read left finger inputs > 0.30, unit 106; checked offline: off from ~303 and through the carry on rollouts 2–7), and (b) threshold 0.15 rad (was 0.20). | Predict: diverges from frame 1. Left-wrist error along n ≤ ~0.20 at 280–300; controller off from ~303; handover succeeds (object rotation ≤ 0.2 rad through 352); release from ~905; final wrist error ≤ 0.10 m, final flask rotation ≤ 0.10 rad. Falsifier: the controller is off during the grasp and the precondition is met, but the flask still spins → another cause (the right grip). | **Completed the reference, as predicted for the handover**: left-wrist error along n 0.20–0.23 at 280–300, controller off from 305, the cleanest handover so far (object error ≤ 1.7 cm, rotation ≤ 0.05 rad through 352). Final wrist error 0.090 m. **End-phase risk remains:** flask rotation 0.066 → 0.374 rad over 1000–1022 (limit 0.5). The release primitive barely acted (gate ≤ 0.58): with its −0.144 threshold it can only open the hand to about ref + 0.144, and the fingers stayed +0.17. The end controller then dragged the gripped flask (F_L 250–440 N). |
| 9 | v09: v08 with (a) release v2: threshold −0.06 (the mean command never went below −0.044 during grasp and carry), gain 2× (−3 per unit gate, 1 per 0.05), inhibited while the flask is off the table (object y > −0.56 m; unit 453); (b) the end-position controller inhibited while the left hand is still closed (five-finger closure > 0.30; unit 514). Offline on rollouts 2/5/6/8: release fires from ~893–900 to the end, never during the carry. | Predict: diverges from frame 1; handover as in rollout 8; release from ~895; at 1000 left finger q − ref ≤ +0.08 (was +0.17) and F_L < 100 N; end controller acts once the hand has opened; final wrist error ≤ 0.10 m; final flask rotation ≤ 0.10 rad. | **Failed at frame 1013 (50.65 s) on flask rotation** (0.517 rad). The run was identical to rollout 8 until ~890 (same components act before then), so 8 vs 9 is a controlled comparison of the end-phase change, and the change **made things worse**. The release opened the hand only to ref + 0.07 (was +0.17), but F_L stayed 86–200 N; its inhibitor then let the end controller act from ~980 at full strength (gate 1.8–2.2) while the hand still touched the flask. Flask rotation 0.12 (1000) → 0.47 (1010). **Lesson (rollouts 5, 6, 8, 9): any wrist correction while the left hand touches the placed flask turns the flask; without the end controller the flask stays put (0.04 rad) and the wrist ends at 0.1485 m.** |
| 10 | v10: v08 exactly, except the end-position controller threshold 0.10 m (was 0.06), so it only caps the wrist error near the limit with a small late correction. On rollout 8's states, v10's actions first differ from v08's at frame 964. | Predict: identical to rollout 8 through frame 963. Then the wrist error grows as in rollout 5 and is capped at ~0.12–0.13 m from ~1000; final flask rotation ≤ 0.15 rad (rollout 8: 0.374); success. | **Completed the reference, as predicted.** Identical to rollout 8 until frame 965; wrist error capped at 0.127–0.128 m from ~1005 (rollout 8: pulled to 0.09; rollout 5, no controller: 0.1485); final flask rotation 0.088 rad (rollout 8: 0.374). Max object error 5.1 cm (carry, ~500). **Candidate.** |
| 11–15 | v10 + nuisance: output biases + N(0, 0.01²), seeds 1–5 (a robustness probe, not an edit; nothing is selected by score) | The unperturbed outcome flips under tiny weight changes (rollout 2), so v10's handover has been seen on only one independent path (rollouts 8–10). The jitter (≤ 0.01 pre-tanh) changes nothing systematic but puts each run on a different chaotic path. Predict: ≥ 4 of 5 complete. Any failure will be diagnosed for a new failure mode. | **5 of 5 completed.** The paths diverged (joints 0.1–0.2 rad apart from rollout 10 over 100–500, converging again by 900). Every handover was clean: left-wrist error along n 0.18–0.20 at 300; object error ≤ 1.5 cm and rotation ≤ 0.047 rad over 300–352. Final wrist 0.127 m, final flask rotation 0.075–0.094 rad. |
| 16–20 | unedited + the same nuisance, seeds 1–5 (baseline for the probe) | Is the unedited handover fragile under the same nuisance? Predict: ≤ 3 of 5 complete. | **4 of 5 completed** (prediction wrong: the unedited policy is more robust than rollout 1 suggested). Seed 5 failed at 372 by the rollout-1 mechanism (left-wrist error along n 0.57 at 300, flask 10.8 cm off, J6_R → +0.81). Seeds 2 and 3 completed despite 0.36–0.37 rad, so H6's precondition is not necessary, only favourable. The unedited successes have messier handovers (max flask rotation 0.165–0.198 rad over 300–352, against 0.034–0.047 for v10 on the same seeds) and end with 3–4 mm of wrist margin (0.146–0.147 m; v10: 0.127). |
| 21–24 | v10 + nuisance, seeds 6–9 | Tighten the v10 estimate. Predict ≥ 3 of 4. | **2 of 4 completed** (seeds 6, 9). Seed 7 failed at 383 (object 0.103 m) and seed 8 at 348 (rotation 0.508 rad). A mode not seen before: the left wrist was aligned when the controller switched off at 305 (0.22–0.27 rad, flask 5–6 cm), then drifted away during the grasp (0.27 → 0.51 rad in seed 7, 0.23 → 0.48 in seed 8) while the right grip weakened (seed 8: 9–37 N). The flask then slipped or spun. Rollout 7 showed that this controller, left on during the grasp, turns the flask the wrong way; these runs show that switching it off lets the wrist drift. No further edit: the one remaining rollout is not enough to develop and validate a fix. **v10 is final.** |
| 25 | — | Not used. | — |

**Development tally (unperturbed task; nuisance runs differ only by an output-bias jitter of sd 0.01): v10 completed 8
of 10 paths (rollout 10, seeds 1–9); the unedited policy 4 of 6 (rollout 1, seeds 1–5).** The difference is not
statistically meaningful (Fisher's exact test, two-sided, p ≈ 0.6). The consistent effects are cleaner handovers on the
seeds where both completed (flask rotation over 300–352 about 4× smaller) and a 2.2 cm instead of 3–4 mm wrist margin
at the last frame.

Edits built but never run: a rank-one projection of a difference-of-means "failure direction" out of the Joint6_R
readout (`derive.py`, `directions.npz`, `edits.project_out_of_readout`). Rejected offline: it over-corrected at
300–313 and under-corrected at 317–329. Also a halving of the object-error input gain, rejected offline because it
changed actions by up to 0.8 in normal frames.

## Final evaluation (run once after the last edit; not counted against the budget). Raw: `final_eval.jsonl`

Arms: unedited; final edit (v10, sha256 c0a12954d7fa7235d6c8eeaa36f8c1c9fe58ce82d0e2533bbd27c8bac0cccfac);
pre-registered random control (the same 21,024 entries, each change replaced by |change| with a random sign,
`numpy.random.default_rng(0)`, so the Frobenius norm of the change per matrix is the same; sha256 dd662cfd…c266);
sanitised random control (sensitivity check only: identical except that the 6 batch-norm running variances the literal
control makes negative take the positive sign; sha256 70ca1850…514a). Each arm: the unperturbed run + 20 perturbed runs
via `Simulation(delay_steps=d)` and `reset(frame=f)` in `runner.run_one`. (f, d) = (0, 0) is in the grid and is the
same deterministic run as the unperturbed one. "obj", "rot" and "NaN" give the threshold that failed, after the
failure frame.

| start f | delay | unedited | final edit | random (pre-registered) | random (sanitised) |
|---|---|---|---|---|---|
| unperturbed | 0 | fail 352 (obj) | **ok** | fail 0 (NaN) | fail 24 (rot) |
| 0 | 0 | fail 352 (obj) | **ok** | fail 0 (NaN) | fail 24 (rot) |
| 4 | 0 | ok | ok | fail 4 (NaN) | fail 22 (rot) |
| 8 | 0 | fail 66 (rot) | fail 121 (rot) | fail 8 (NaN) | fail 75 (rot) |
| 12 | 0 | fail 75 (rot) | fail 38 (rot) | fail 12 (NaN) | fail 98 (rot) |
| 16 | 0 | fail 132 (rot) | fail 145 (obj) | fail 16 (NaN) | fail 75 (rot) |
| 20 | 0 | fail 353 (rot) | fail 143 (obj) | fail 20 (NaN) | fail 115 (rot) |
| 24 | 0 | ok | ok | fail 24 (NaN) | fail 112 (rot) |
| 28 | 0 | ok | ok | fail 28 (NaN) | fail 111 (rot) |
| 32 | 0 | ok | ok | fail 32 (NaN) | fail 113 (rot) |
| 36 | 0 | ok | ok | fail 36 (NaN) | fail 112 (rot) |
| 0 | 3 | ok | **fail 328 (rot)** | fail 0 (NaN) | fail 19 (rot) |
| 4 | 3 | ok | ok | fail 4 (NaN) | fail 23 (rot) |
| 8 | 3 | fail 333 (rot) | fail 308 (rot) | fail 8 (NaN) | fail 64 (rot) |
| 12 | 3 | fail 91 (rot) | fail 45 (rot) | fail 12 (NaN) | fail 101 (rot) |
| 16 | 3 | fail 143 (rot) | fail 199 (obj) | fail 16 (NaN) | fail 63 (rot) |
| 20 | 3 | fail 370 (obj) | fail 146 (rot) | fail 20 (NaN) | fail 114 (rot) |
| 24 | 3 | fail 357 (rot) | **ok** | fail 24 (NaN) | fail 108 (rot) |
| 28 | 3 | ok | ok | fail 28 (NaN) | fail 108 (rot) |
| 32 | 3 | ok | ok | fail 32 (NaN) | fail 112 (rot) |
| 36 | 3 | fail 364 (rot) | **ok** | fail 36 (NaN) | fail 116 (rot) |
| **perturbed completed** | | **9 / 20** | **11 / 20** | **0 / 20** | **0 / 20** |

Margins on completed runs: the unedited ends at a maximum wrist error of 0.146–0.147 m (limit 0.15), the edit at
0.128–0.129 m. Maximum object error 4.4–6.8 cm (unedited) and 3.9–5.6 cm (edit); maximum rotation 0.16–0.37 rad
(unedited) and 0.13–0.26 rad (edit).

## Problems with the test bed and the protocol (for whoever designs the next round)

1. **Outcomes on the unperturbed task are chaotic.** An action change of 0.08 at frame 0, or an output-bias jitter of
   sd 0.01, flips success and failure. A budget of 25 rollouts on one deterministic start therefore measures luck as
   much as mechanism. I added an output-bias-jitter probe inside the budget to see robustness at all.
2. **The development task and the evaluation set test different things.** The unperturbed run fails at the handover,
   but 5–7 of the 20 perturbed runs fail during the pickup (start frames 8–20: the robot starts mid-approach with zero
   velocity and zeroed filters). That mode cannot appear in development under the rules.
3. **The pre-registered random control is degenerate for this edit.** Flipping the sign of a change made to a
   batch-norm running variance can make it negative: 6 entries here, so the network outputs NaN at the first step.
   Flipping the sign of "set to zero" doubles the weight, so the sanitised version also fails every run within 1–6 s.
   "Same entries, same Frobenius norm, random signs" is a destructive perturbation, not a size-matched placebo, for an
   edit made mostly of zeroing. A better control would be the same construction on randomly chosen coordinates and
   units, or a sign-random change restricted to entries whose original value is kept.
4. **The (0, 0) grid point equals the unperturbed run** (deterministic), so it is counted twice.
5. **The unedited policy finishes on a knife edge:** a wrist error of 0.146–0.1485 m at the last frame against a
   0.15 m limit in every completed run, so the end-of-episode check alone decides some outcomes.
6. **The bundled policy fails on this x86 CPU** (NVIDIA tested on Apple M4), as measured before; not investigated.
7. **The residual architecture makes idle-unit controllers costly.** Contract layers have almost no always-active
   units and the RMS norm couples all outputs, so each controller needed a cleared stream coordinate. Clearing it is
   itself a perturbation (action change 0.015 mean per coordinate).

## Files

- `runner.py`: headless runner (start frame, delay, full traces incl. hand–object contact forces; any actor npz).
- `net.py`: numpy forward pass with activations (identical to `policy.py`, max difference 7e-6 on recorded steps).
- `edits.py`: weight-editing primitives (private channel, gate unit, head row, diff).
- `build.py`: every tested version v02–v10, built deterministically from the original actor.
- `edit.py`: builds the final edit (v10) and the random controls (pre-registered and sanitised).
- `lwrist_controller.json`, `lwrist_pos_controller.json`: kinematic constants and their derivations.
- Analysis scripts: `summarize.py`, `check_gates.py`, `j6_loop_model.py`, `derive.py`. Robustness probe: `probe.py`.
  Final evaluation: `final_eval.py`.
- Logs: `rollouts.jsonl` (the 24 rollouts), `final_eval.jsonl` (84 runs), `edit_info.txt` (hashes and per-array
  change counts).
- Kept in the scratchpad, not the repo: the edited npz files, all traces, the copied original actor.

Reproduce (WORKSHOP = the extracted `chord_workshop` directory, PY = the exercise venv's python run with `-I`):

    PY edit.py WORKSHOP/assets/policy/actor.npz final.npz random.npz random_sanitized.npz
    PY runner.py WORKSHOP final.npz trace.npz            # unperturbed rollout
    PY final_eval.py WORKSHOP out.jsonl traces/ unedited=WORKSHOP/assets/policy/actor.npz final=final.npz random=random.npz random_sanitized=random_sanitized.npz
