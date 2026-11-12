# Weight-space repair of exercise 3's policy (pre-registered pilot, note 29 idea 2) — 2026-11-12

Status: IN PROGRESS. Repair agent: Claude (Opus 5.5), CPU only, this cloud container (4 cores, no GPU).
Started 21:22 UTC. Rules: work-log entry "2026-11-12 ~22:20 UTC — owner: go for all; PRE-REGISTRATION".
Development used only the unperturbed task (start frame 0, delay 0); no perturbed run was simulated before the final
evaluation.

## Diagnosis from rollout 1 (offline analysis of its trace; scripts: net.py, analysis commands in this log)

Task: right-to-left flask handover. The right hand carries the flask to ~frame 330; the left hand closes on it from
~300; the right releases ~360–385; the left carries it to frame ~870 and places it.

Failure (rollout 1, frame 352 = 17.60 s, object 0.1007 m): the chain I believe, with evidence.
1. ~302–304: a sudden ~1 cm push on the flask (−x, −y, +z) as the left hand closes. The left pinky MCP_FE is blocked at
   0.24 rad while its reference closes to 1.2 rad: the flask sits ~8 cm away from the planned spot in the left-wrist
   frame, because the policy holds the left wrist ~0.43 rad off its reference orientation (left wrist command inputs
   at ~2 sigma).
2. 305–330: the left finger command errors (ref − q; pinky, ring, index MCP_FE, up to 4.2 sigma) drive Joint6_R
   (right wrist) to the joint limit: pre-tanh 1.3 → 4.1, offset from reference 0.40 → 0.81 rad (block swap:
   finger-command block +2.4 of the +2.8 rise at frame 321; left fingers, not right). The simulator's wrist-pair
   coupling then shrinks Joint7_R's range (limit 1.13 → 0.83 rad), so Joint7_R is clipped 0.2–0.4 rad off its
   reference. The right wrist, still holding the flask, twists (orientation error 0.30 → 0.77 rad).
3. 310–330: the flask drops 3–4 cm and lags 5 cm in x; 335–353 it drifts 5 cm in −y with the left wrist.
   The object-error inputs reach 8 sigma; the policy's reaction to them (inputs 209:216 vs. zero error) is roughly in
   the right direction for the right hand but 3–10x too large, and the left hand's reaction points the wrong way.
4. The network's residual stream leaves its normal range: rms 1.3–1.9 normally, 0.82 at 312 (near cancellation),
   then 2–7. 62 block-1 wide units are active only in the failure window.

Network census (rollout 1): 221 of 1024 block-1 wide units and 196 of block-0 never activate; but only 5 of 256 block-0
contract units and 1 of block-1 are active in all frames, so a write into the stream must be designed through
whatever is active. A single input can be read cleanly from h0 (block 0's input; correlation 0.99 for input 47) but
not from h1 (−0.38). Block 1 adds 0.7–0.8 of any write into h1 on top.

Construction used for gated controllers ("private channel"): one coordinate j of the 256-wide stream is cleared
(embedding column, both blocks' reads of j, both contract units j, head row j). Block-0 contract unit j becomes a wire
(identity norm). An idle block-0 wide unit reads raw inputs from h0 through a least-squares readout of the embedding
kernel (a weights-only computation) and writes relu(kappa·(input − threshold)) into coordinate j; it passes unchanged
to the head, whose row j drives only the chosen outputs. Clearing coordinate 78 (the least damaging of the 256) changes
actions on rollout 1's observations by 0.016 mean, 0.15 max.

## Rollout log (budget 25 unperturbed rollouts: start frame 0, delay 0)

Each row: prediction written before the run; result after.

| # | Actor | Mechanism believed / prediction (written before the run) | Result |
|---|---|---|---|
| 1 | unedited | Diagnostic. Predict the same deterministic failure as measured before: frame 352–353, object 0.101 m. Continue 60 frames past the failure for diagnosis only. | As predicted: fails at frame 352 (17.60 s), object 0.101 m, 0.325 rad, wrist 0.053 m. 6.6 s. |
| 2 | v02: Joint6_R virtual limit (coordinate 78, gate unit 887 on input 47, threshold 0.42 rad, K = 60/rad) | Mechanism tested: the Joint6_R climb (+ Joint7_R clip) twists the flask out of the reference (step 2). Predict: frames 0–300 nearly unchanged (object error at 300 within ±1 cm of 0.9 cm); Joint6_R offset ≤ 0.50 rad through 300–352 (was 0.81); right wrist orientation error ≤ 0.5 rad (was 0.77). If the twist is the main amplifier: object error at 330 ≤ 4 cm (was 6.7) and failure avoided or delayed past 360. If error at 330 is still ≥ 6 cm, the twist is not the main driver. | **Completed the reference** (max object error 4.9 cm; wrist error 0.148 m at the last frame, limit 0.15). But **the gate never fired** (max 0.0): the J6_R offset stayed ≤ 0.31 all run (rollout 1: 0.43 before the handover). The run took a different path from frame 1 (action difference 0.08 at frame 0 from clearing coordinate 78; joints 0.2 rad apart by frame 20). So the success is the side effect, not the mechanism: **the unperturbed outcome flips under a tiny weight change.** Prediction not tested. Rollout 1 vs 2 before the handover (280–300): J6_R offset +0.40 vs +0.18–0.26; J4_L −0.22 vs −0.08; J7_L +0.40 vs +0.17; flask-in-left-wrist error 9 vs 4 cm. |
| 3 | v03: as v02 with threshold 0.25 rad (physical: keeps the J7_R coupling clip off during the handover; also the training 2-sd edge, +0.28) | Same coordinate as v02, so the run is bit-identical to rollout 2 until the gate first fires (frame ~206 on rollout 2's states). Then the J6_R offset is held ≤ ~0.30. Predict: success with handover object error ≤ 3 cm through 352. A failure means pulling J6_R down from ~0.31 to ~0.27 during the carry harms it, and the threshold is rejected. | (pending) |
