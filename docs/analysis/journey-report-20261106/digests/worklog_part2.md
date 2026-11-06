# Digest: worklog_part2 (log entries 24-31 Oct 2026)

Times UTC unless marked. "sim_vs_ref" = agreement with our own reference (no ground truth). "reg. AUC" = registered AUC vs mocap (public episodes only). "LB" = Kaggle leaderboard.

## Perception (depth, detection, identity, tracking, hands, room map, point tracks)

- **24 Oct, Grounding DINO off on all eval boxes (bug).** `ensure_gdino` never called ("No module named 'transformers'"). Replay with and without the term: no eval choice changes. Fixed 88822b2.
- **24 Oct, eval 30 sweeper (H: re-propose SAM2 masks from Grounding DINO boxes).** Chosen "sweeper" was the watch strap, 7.9 cm from the wrist. Plain re-proposal failed no-regression (93 to 95 labelled, 2 regressions). Gated version (only where G < 0.2) passed: 93 to 95, no regression. Changes only eval 30 (strap G 0.001 to broom G 0.284). Eval 30 sim_vs_ref 0.472 (old reference) to **0.7216** (std 0.249, min 0.304, max 0.929). Adopted 22:50 UTC 24 Oct.
- **25 Oct, on-table rule (pre-registered).** Proposals >3 cm below table plane barred. Variant 1 failed (regressions ep18 f0, ep11 f68). Variant 2 passed: 95 to **97**, no regression, no eval frame-0 change. Shipped.
- **25 Oct, TRACK_GUARD (frame-0 retry; re-detect on implausible frames).** 8 public episodes: mean reg. AUC **0.7239 to 0.7821**; ep0 0.496 to **0.964**; no episode below -0.01. Default on. Eval rerun: guard fires only on evals **8, 14, 32, 33**.
- **25 Oct, precision sweep (pre-registered).** Mean reg. AUC base **0.8677**, t4 0.8551, t8 0.8640; t8 drops ep18 by 0.25-0.29. Base kept.
- **24-25 Oct, G1 re-track (library_v2, 16 public).** Mean reg. AUC 0.810. Failures: ep0 0.496 (pot mask covers lid), ep11 0.102 (beige cup on the lap), ep23 0.041 (identity swap). ep11 after on-table rule: **0.898**.
- **25 Oct, spoon.** Observed length 30.0-30.7 cm; template 30.7-31.0 cm: H1 "template wrong length" not supported. Registration flips 0/300 (30 variants x 10 seeds; rotation median 1.0 deg, p95 2.5 deg).
- **25 Oct, anchor frame-0 pose test "A-f0" (adopt if mean gain >= +0.01).** NOT adopted: mean +0.001 over ep2, ep39, ep21, ep31.
- **26 Oct, sweeper flip (22 Oct claim).** Not reproduced: 4 of 40 random seeds flip 179 deg; eval 19 and 30 seeds within 0.9 deg.
- **26 Oct, S6 static hold (T1).** Mean +0.004 but fails no-harm by 0.0003 on P_o; freezes nothing on eval 10 (track slides 4.1-4.9 cm). Unused.
- **26 Oct, T5 robust VO on ep24: PASSES.** P_o 0.8105 to 0.9941 (cause: perc2's 2 m depth clip). No confirmed eval target.
- **30 Oct, depth audit (pre-registered): FALSIFIED.** AUROC **0.600** (CI 0.40-0.78; 19 episodes, 1,447 positives); informative needs >= 0.75. No reference spend on it.
- **30 Oct, phase-1 with scan templates.** P_s vs mocap >= 0.96 on 16 episodes; ep11 0.863, ep31 0.863, ep24 0.849, ep0 0.078. Leak readings: L2 template +0.039 mean dR (17/20); L3 true template +0.076 (+0.033 without ep0/ep23); L1 no leak.
- **31 Oct, perception sprint (CPU, pre-registered).** S11 constant-offset ICP FAILED (best dR +0.0005). S10 heldpose FAILED (proxy -0.018). S12 mask10 cup-nest PASSED on ep11 at reference level (hold 0.901 to 0.969); other 19 byte-identical.
- **Eval 33 diagnosis.** Cup track tilts 87-130 deg and dips 10-15 cm after f~48 while the left hand's contacts stay non-empty: perception failure, not grasp. Hand/forearm masking is an untested fix.

## Policies and following (RL training, recipes, retrains, sim, seeds, flips)

- **24 Oct, grasp-lock validation (public; frozen recipe; 64 candidates x 4 jittered copies; 20 generations; 70M fine-tune; 5-eval means).** ep39 **0.958 +/- 0.002** (before: grasp lock 0.174; std RL 0.802 +/- 0.280); ep18 **0.957 +/- 0.002** (grasp lock 0.22-0.41; std 0.776 / 0.889); ep24 **0.241 +/- 0.125** (grasp lock 0.202; std 0.307-0.318); ep27 **0.949 +/- 0.010**; ep12 **0.868 +/- 0.122** (one rollout in five fails). Cost ~$8.
- **24 Oct, 20-episode eval run (frozen recipe).** sim_vs_ref per eval: 1 0.297, 3 0.851, 5 0.855, 6 0.982, 8 0.777, 10 0.334, 14 0.506, 15 0.901, 16 0.795, 19 0.647, 20 0.287, 25 0.243, 28 0.694, 30 0.469, 32 0.838, 33 0.391, 35 0.992, 36 0.994, 37 0.998, 38 1.000. Mean 0.692 (spoon 0.860, others 0.525). Estimates: 0.74 (0.58-0.85) after eval 33; 0.66 (0.60-0.70) after full run; pack estimate 0.68 (0.62-0.72). Actual AUC 0.57468.
- **25 Oct, second training seed (43) on same references, chosen by 5-eval mean.** Seed 43 chosen for evals 3 (0.9285 vs 0.851), 19 (0.6534 vs 0.6469), 15 (0.9411 vs 0.901), 5 (0.9662 vs 0.855), 16 (0.8045 vs 0.795). Eval 28 kept seed 42 (0.694 vs 0.6675).
- **25-26 Oct, learner choice (rule: higher 5-eval mean on same reference).** Std learner beat grasp lock for evals 1 (0.9122 vs 0.2969), 19 (0.935 vs 0.6534), 25 (0.712 vs 0.376), 28 (0.9347 vs 0.6938), 30 (0.9188 vs 0.7216). Glock kept for 8 (0.9705, frozen 0.7615), 14 (0.6595), 16, 20 (0.8923); frozen chosen for 32 (0.779) and 33 (0.7728).
- **29-30 Oct, recipe arms (pre-registered; A control, B CURR_SCALE 0.4, C ball wrist kd 2).** ep12 mocap AUC A 0.912 +/- 0.033, B 0.892, C 0.909. Eval 32: A 0.631 +/- 0.166, B 0.743 +/- 0.138, C 0.702 +/- 0.200. Eval 33: A 0.906 +/- 0.058, B 0.923 +/- 0.013, C 0.883 +/- 0.014. **Inconclusive**; neither falsified; no second seed bought. Costs $6.37 / $3.82 / $4.26.
- **30 Oct, eval 33 confirmation (B's checkpoint, 10 fresh draws).** **0.9344 +/- 0.0076** vs packed H5 0.854 +/- 0.137; passed (mean >= 0.884, sd <= 0.137). Used in pack 7.
- **29 Oct, H5 re-evaluation (10 fresh official draws per pack-6 checkpoint).** Mean of means **0.8755** vs packed 0.9164 ("pack 6 is lucky" not falsified; threshold 0.905). Estimated LB at 0.74-0.78 transfer ~0.782-0.784. High variance: eval 1 0.822 +/- 0.239; 14 0.615 +/- 0.199; 25 0.850 +/- 0.099; 30 0.798 +/- 0.255; 33 0.854 +/- 0.137. Eval 10 0.450 +/- 0.007.
- **30 Oct, oracle twins (P = perceived reference, O = mocap object motion; grasp lock).** ep11 (eval 10 twin): O **0.940 +/- 0.032** vs P 0.595 (delta +0.345, SE 0.011), class perception-limited. ep13 (eval 14): O 0.544 = P 0.543, learner-limited. ep31 (eval 30): delta +0.086 (SE 0.020), inconclusive. Cost $7.80.
- **25 Oct, training-curve analysis (CPU; 29 standard curves).** 22 start < 0.5 at 100M; median +0.04 by 250M; 13/22 end below floor. - **26 Oct, seed-race analysis (CPU; 31 standard curves, 66 grasp-lock).** Score at 40 % vs final Pearson 0.89 (standard); leader ends better 30/36 (standard) vs 22/38 (grasp lock). Early cut suits standard learner only; not adopted.
- **26 Oct, eval 10 early checkpoints (falsifier: any curve checkpoint > 0.47).** B' 1M-8M 0.446-0.465; C' (object ILC on blue at rest) 0.450-0.456 from 1M to 70M, chosen 23M 0.4528. Falsified.
- **27 Oct, eval 10 zero-start (residual head, zero-init mean; plan zero action 0.526).** Chosen 25M 0.4459 < 0.4539. Falsified. Reading: RL moves away from the plan within ~1M steps and settles on not touching the cups.
- **26 Oct, eval 10 carve (hybrid cups).** s42 0.4532 +/- 0.003, s43 0.4520 +/- 0.0014; floor 0.448. Stacking not learned. Grasp lock on carved cups: 0.4539 (A, chosen) vs 0.4377 (B); needed > 0.462: falsified.
- **26 Oct, eval 25 carve (board slots).** Carve s42 **0.7919 +/- 0.103** (min 0.618); s43 0.4739. Carve s42 chosen (rule).
- **26 Oct, eval 32 / 33 frozen seeds.** Eval 32: s43 0.7016, s44 0.397, s45 0.634, **s46 0.803 +/- 0.105** (chosen; s42 was 0.779). Eval 33: s43 **0.7853 +/- 0.255** (s42 0.7728 +/- 0.053; s43 chosen).
- **25-26 Oct, ep21 arc-foot twin (adopt iff arc >= base - 0.02 and pitcher arc >= base).** Base reg. AUC **0.6565 +/- 0.093** (pitcher 0.414); arc foot **0.7723 +/- 0.009** (pitcher 0.591). ADOPTED. Eval 20 rebuilt with arc foot.
- **30 Oct, eval 14 carve (cup into rack).** Seed 42 0.617 +/- 0.236; seed 43 0.579 +/- 0.099. Rule needed >= 0.645 and sd <= 0.199: NOT adopted. Eval 30 carve dropped (sweeper falls through).
- **30 Oct, eval 1 carve (pot/lid overlap).** Training box seed 43 0.931 +/- 0.006; official 20 fresh draws **0.9241 +/- 0.017** (min 0.884) vs packed H5 0.822 +/- 0.239. Adopted for pack-8 candidate (not uploaded).
- **Physics study (other session, realistic masses vs 0.3 kg).** Grasp-lock mean +0.090 on 4 public episodes (ep2 +0.160, ep12 +0.103, ep18 +0.011, ep24 +0.084). Our mass-transfer check (31 Oct, box 58502738) launched; result not in this log.

## Grasp and references (contact labels, reference building, lift windows, grip)

- **24 Oct, ep39 root cause.** Pan rises from f51 while the human-retargeted hand is still 48-51 cm away; hand arrives f65-70; hold starts f70. Same on ep18 sweeper (+21 frames) and ep24 board 2 (+63); not on ep12 (-2) or ep27 (-3).
- **24 Oct, onset anchor (`--onset_anchor 1`).** ep39 zero action 0.164 (old 0.176); ep18 sweeper hold from f29 (was 53); zero action 0.137 (old 0.135).
- **24 Oct, CMA-ES grasp edit (28 parameters: wrist 6 + finger offsets 22).** ep39 round 1 best 0.810 (unedited 0.309). Round 2 (window f22-312): window AUC 0.865 (unedited 0.108); zero-action sim_vs_ref **0.877** (vs 0.176 old). Std RL tracked the same reference at 0.826. Sensitivity: 1e-3 jitter mean 0.841 (0.78-0.91); 1e-2 mean 0.46.
- **24 Oct, search bug (warm start).** `mjw_data.qacc_warmstart` survives `env.reset`: same edit 0.5078 fresh vs 0.41-0.59 after other batches. Fixed (bbe57e6, fresh env per generation 72d60cb). Jitter 1e-5 moves a best score to 0.18-0.44: the search had picked a lucky trajectory.
- **24 Oct, 0.889 template (ep18 policy's key pinch).** Open-loop template on ep39 **0.243**, vs copied grip 0.164, evolved 0.877. CMA-ES from template: no candidate beats it in 14 generations. Not in recipe.
- **25 Oct, grip portfolio P1 (ep24 board 1, CVaR 25 %).** copy 0.321 (lift 22.0 cm at f30); clamp_long 0.297; **clamp_short 0.475** (lift 4.9 cm); platform 0.392. Not falsified; only GPU A/B can decide.
- **25 Oct, event-anchored windows T2 (adopt if >= +0.05 on 3 of 4).** FAILED: ep24 0.160 to 0.058; ep2 0.104 to 0.090; ep39 0.0625 to 0.0623; ep18 0.128 to 0.053.
- **25 Oct, contact slot names (owner decision).** mkref writes `contact_slot_names`; `mano_link_names` kept. Corrected biomechanics: thumb 0.09-0.52, opposition 0.05-0.22 (was 0.38-0.69); lid palm 0.00; pitcher palm 0.92; ep26 pot palm 0.70.
- **24 Oct, support fallback (9c63c87).** Eval 30 table plane lifted sweeper 7.11 cm, rack snapped 0.88 cm; eval 8 beige cup (7.03 cm under table) also needed it. Eval 25 ILC NaN fixed (78f7d65).
- **24 Oct, start overlap (eval 1, 8).** Overlap only in eval 1 (344 of 3,000 lid samples) and eval 8 (17 pot samples). SETTLE box destroyed before running (~$0.2); estimated gain <= 0.002 AUC.
- **30 Oct, refine stage (20 public, baseline 0.8921).** S2 0.545-frame advance adopted (+0.0061, 17/20 better). S1 snap rejected (-0.0077); S3 tilt-to-plane rejected (-0.0013); S4 pre-contact hold neutral (+0.0003).
- **26 Oct, eval 10 hybrid cup collision copy.** Rest 0/6 falls (today's beige 6/6 falls, 46-89 deg); driven nest 0.44 cm / 2.5 deg (today 4.45 cm / 8.6 deg). Pre-registered standing rule failed (frame error).
- **26 Oct, zero action vs trained.** Zero action beats training by > 0.02 in 15 of 64 stored results; eval 10 zero action 0.663 vs submitted 0.447. Zero-residual policies excluded (22 Oct learned-policies-only rule).

## Meshes and CD-O (templates, scans, registration, mesh tiers, mesh adoption)

- **24 Oct, mesh v5 decision (owner).** Pipeline v5 for all objects after the pack; base-completion rule.
- **25 Oct, library v5 (box 57580685, ~$4.2).** Pitcher, dust pan (O), blue cup (O), sweeper (F4), rack (F4) built. Pot, lid, boards failed (broken G1 tracks ep0, ep23; missing M0).
- **25 Oct, E2 CD-O at eval seeds (cm, v5 vs v2; 0 flips).** Pitcher 0.890 vs 0.894; dust pan 0.368 vs 0.331; sweeper 0.526 vs 0.316; rack 0.818 vs 0.555; blue cup 0.540 vs 0.523. v5 worse on 4 of 5: not adopted.
- **25 Oct, eval 25 identity.** Stored track swapped the boards (as-tracked +50.0, rank 21 of 32; repaired -20.9). A fresh box named them correctly (rank 1): naming is near a coin flip.
- **25 Oct, beige cup v5 (fused on re-tracked ep11).** E2 PASS: CD-O 0.730 vs v2 0.856; 0 flips in 6 seeds. Ep11 twin: library_v3 reg. AUC 0.525 vs library_v3x 0.570 (beige 0.03-0.06 vs 0.141). **Adopted** as library_v3x (used for evals 8, 10).
- **26 Oct, lathe from observed points.** Blue cup 0.523 to **0.364** (ADD 10.0 to 4.7 mm, 0/7 flips); pot 0.437 to 0.468. Approach-2 library lathe: cup 0.307, pot 0.319. Single-frame points (cups 1.28, 7/7 flips) rejected.
- **26 Oct, pitcher lathe (library_v3p) on eval 20.** Public ep21 reg. AUC: ours 0.776, lathe 0.874, scan 0.907. Pack 5 with it gave AUC 0.80941 vs 0.81391 after owner revert (pack 6): the lathe pitcher cost -0.0045 (measured).
- **25 Oct, pitcher v5 (CPU).** Step 1 passes on paper (0.890 < 0.894, 0 flips), but the v5 pitcher took the classic fusion branch (same as v3). Not pursued; the arc foot was the fix.
- **27 Oct, primitive assembly (pre-registered; CD-O, ADD, flips).** Pot ep41 0.342 (lib 0.437), ADD 3.05: PASS. Lid 0.219 (0.421): PASS, provisional. Rack 0.454 (0.555), ADD 6.41: PASS, provisional. Board 1 0.189 (0.222), 1/6 flips: FAIL. Board 2 ADD 78.7 mm, 3/6 flips: FAIL. Leak found: wall/lid thickness and lean taken from scans; clean-up grid {1.5, 2.5, 4.0} mm pre-registered.
- **26 Oct, eval mesh review (36 pairs, visual, GT-free).** Priority of problems: blue cup, white pot, dish rack, beige cup, pitcher, dust pan, sweeper, board 1, lid, board 2; spoon good.

## Scorer and task understanding (how the metric works, what it rewards, measured facts about the task)

- **AUC.** Per-object ADD-AUC with thresholds 1-9 cm; a 1.5 cm track error costs ~0.06 AUC per object vs ~0.8 cm (estimate). Kit `AUC.py`: mean over 20 submitted episodes; nothing re-run. Checkpoint hashes kept "for later validation".
- **CD-O.** Kit Chamfer after Sim(3) (scale from area-weighted RMS radii). Flat mean over 36 (episode, object) pairs. Surface-area distribution matters: a blue lathe ratio 0.92 gives 0.382 vs 0.316 at true scale.
- **Rank correlations (25 Oct, across teams).** MPPE -0.97 (n 18), RPE -0.93, MP-SR +0.93, SP-SR +0.90, CD-O only -0.51 (n 16). CD-O leader (0.112 cm) is 17th on AUC. Top-3 AUC teams: MPPE 1.24-1.83 cm vs our 6.69 (pack 2): pose, not shape, separates us.
- **SP-SR / MP-SR.** About 9 and 7 of 20 episodes count as successes.
- **Spoon anchor.** The kit aligns the scene on the anchor's frame-0 pose; spoon anchors evals 32, 33, 35, 36, 37. A 10 deg roll error costs 0.09-0.28 AUC there.
- **Transfer.** Public twins ~0.96 x sim_vs_ref (24 Oct); measured LB/sim transfer 0.74-0.78 (29 Oct); pack 4 predicted +0.0285, measured +0.0216 (~76 %). Implied hidden loss ~0.082.
- **Simulator facts.** Hands pass through the table. Policy sees live contact points and force directions (no magnitude), no look-ahead, no object velocity. Training resets hold the reference 20 steps with VOC 1.0; evaluator starts at frame 0 with no hold (train/eval mismatch). Evaluator is pristine FlashCHORD 8c778f90.
- **Wrist.** Default soft wrist saturates on 23/27 moving public tracks (5.8 % of moving frames). PD kp 100 carry error 3.7 cm vs 11.9 cm default (27 Oct). FAQ: "Other embodiments are welcome" (27 Oct); wrist gains not a gate.
- **Public data.** No public episode starts with an object in hand, or has a spoon in a cup. Only ground truth: object mocap and scans (no hand, contact or mass truth).

## Leaderboard and submissions (every upload: pack name, date, change, board scores, rank)

| Pack | Date (UTC) | Change | AUC (rank) | SP-SR | MP-SR | RPE cm | MPPE cm | CD-O cm |
|---|---|---|---|---|---|---|---|---|
| 1, `20261024-track3` (6f1aea3) | 24 Oct 18:45 | first full run | 0.57468 (9th) | 0.45 (11th) | 0.35 (9th) | 12.58 (13th) | 8.66 (10th) | 0.405 (10th) |
| 2, `20261025-track3b` (46b8389) | 25 Oct 01:03 | eval 30 rerun, seed 43 for 3/5/15/16 | 0.58252 (9th) | 0.50 (10th) | 0.40 (7th) | 8.82 (9th) | 6.69 (9th) | 0.405 (10th) |
| 3, `20261025-track3c` (3758189) | 25 Oct ~20:05 | std learners for 1, 19, 25, 28, 30; glock 8, 14, 20; frozen 32, 33 | 0.78893 (4th) | 0.80 (5th) | 0.60 (4th) | 4.59 (4th) | 3.29 (4th) | 0.402 (11th) |
| 4, `20261026-pack4-f7a49a9` | 26 Oct 10:55 | eval 10 carve s43, eval 25 carve s42, eval 33 s43 | 0.81056 (5th) | 0.85 | 0.65 | 4.03 | 2.94 | n/r |
| 5 | 26 Oct 16:06 | eval 10 gl10A2, eval 32 s46, eval 20 lathe pitcher | 0.80941 | 0.85 | 0.65 | 4.01 | 2.96 | n/r |
| 6 | 26 Oct 17:15 | pack 5 with eval 20 pitcher reverted (owner) | 0.81391 (best then) | 0.85 | 0.65 | 3.94 | 2.92 | n/r |
| 7, `20261030-track3g-candidate` | 30-31 Oct ~06:45 | pack 6 with eval 33 from arm B | 0.81460 (7th) | 0.85 | 0.65 | 3.932 | 2.921 | not re-sent |

- Packed sim_vs_ref means: pack 1 0.710; pack 2 0.7218; pack 3 0.883; pack 4 0.9121; pack 6 0.9164. Pack 8 candidate (pack 7 + eval 1 carve) **not uploaded**.
- Pack 3 bug (found 26 Oct): evals 3, 5, 15, 16 shipped the first pack's seed-42 rollouts, not seed 43 (sha256 mismatch). Sim_vs_ref 3 0.942 intended vs 0.867 submitted; 16 0.908 vs 0.843. Fixed in `pack_eval.sh`.
- Leaderboard 30 Oct (AUC): richchentw 0.940, DDD 0.931 (0.827 on 27 Oct), Zihao Guo 0.883, Purple 0.870, rlwrld 0.860, SRL 0.856, us 0.8146 (7th), DSAIL 0.773. 5th needs +0.046.
- Upload rule (kit `config/tracks.json`): 5 per week; unlimited in final 3 days before freeze (4 Nov 2026, 5 pm EST); 2 final picks; daily cap 5 per board.

## Process, cost and infrastructure (GPU rentals, $ spent, bugs, failures, tooling, rules adopted)

- **Credit (owner top-ups).** 24 Oct +$10 and +$50 (credit $54.61). 25 Oct +$100 (credit $101.82; $54.6 spent by 20:05). 26 Oct credit $41.63 to $28.23 (10:55) to $17.29 (13:14). 27 Oct $6.80. 29 Oct +$100 (credit $103.51; night cap $60). 31 Oct +$100 "lean" (credit $128.43).
- **Costs.** Eval box (3 episodes, RTX PRO 6000) $1.38-1.72/h, typically $3-6 per box; standard learner 2 episodes per box 3.5-4.5 h, $5-6.4 each; pack $0.5-1.5. 24 Oct eval boxes ~$22. 30 Oct ledger $35.48 actual (10:09).
- **Market.** 26 Oct: 4 compliant on-demand offers $1.81-2.53/h (morning $1.35). Interruptible $0.67-0.91/h: paused within ~10 min at $0.80 bid; 4 of 5 offers vanished. Abandoned for seed races.
- **Failures.** Eval 33 CUDA OOM with 3 trainings (40.4 GB each on 96 GB); fixed with `TRAIN_SLOTS=2`. Eval 10 grasp lock "nefc overflow" every step (stacked cups), stopped. HF store HTTP 429 on parallel pulls (24-31 Oct). `pull-run` size mismatch from live source run (fixed `PULL_SUB`). Video box 26 Oct: 0 videos from a three-pattern `hf download --include`. Box vanished before start (30 Oct, $0). 5-hour usage-limit gaps cut CPU workflows (25-31 Oct).
- **Bugs fixed.** Warm start survives reset (24 Oct); stale curve scores from a pulled run (`ckpt_curve` skipped existing `qa_policy.json`); `vast.sh` defaulted to origin/main (26 Oct); push aborted silently under `set -e` (27 Oct); STEPS not a multiple of 4096 (27 Oct); ledger overwrite erased lines (29 Oct, fixed 8be9e27); `fast_simplification` and `rtree` missing on boxes (25 Oct); wrist_ilc NaN divergence (78f7d65); mkref aborted when no plane passed (9c63c87).
- **Rules adopted.** Pre-registration (rules fixed in repo docs before results); "no best-of-N draw is ever packed" (29 Oct, rule d); checkpoint chosen by mean of 5 official evaluations; rollouts kept only if checkpoint sha256 unchanged (26 Oct); leak guard `tools/no_oracle.py` in pack, H5 and submit scripts (30 Oct); kit dry run before each upload; uploads by the agent after owner go-ahead.
- **Parallel sessions.** Branches focused-pascal (physics), inspiring-mendel (duplicate 25 Oct batch, destroyed in setup ~$0.9; carve work), bold-albattani (mesh), main-bsky37 (packs).

## Owner decisions and quotes (short verbatim quotes with dates)

- 24 Oct, ~07:15 UTC: "Lets go with 2 make sure it is the case all the failed ones, do research on grasping and holding something anatomically humanly ..."
- 24 Oct, ~15:05 UTC: "run the whole pipeline with 20 eval, let's get our ranking."
- 25 Oct, 00:22 UTC: "fix the lower scores properly, do whatever it takes, aim for 4th place."
- 25 Oct, ~14:55 UTC: "go and get me a proper score, I need the ranking."
- 25 Oct, 18:03 UTC: "we cannot pick and choose" (best-of-N rollout for eval 25).
- 26 Oct, ~11:46 UTC: "let's in another chat think about how to make this more robust ... where we are losing what."
- 26 Oct, ~15:40 UTC: "Sure do whatever takes to beat DDD."
- 26 Oct, ~16:15 UTC: "sure do whatever makes sense" (revert eval 20 pitcher).
- 30 Oct, ~09:40 UTC: "intentionally go for the hard ones."
- 30 Oct, ~12:10 UTC: "okay go with b then."
- 30-31 Oct: "you can send the pack 7 to get the score lets see what improve."
- 31 Oct, ~09:10 UTC: "Is there anything we can do to improve perception? Are we doing anything for that?"
- Owner rules: contact_slot_names (25 Oct); "use both" learners (25 Oct); "only run the extra if it makes sense" (25 Oct, eval 10); eval-20 pitcher revert (26 Oct, disclosed as informed by the pack-5 result).

## Lessons stated in the log

- Pre-register every test with pass/fail before results; a plain re-proposal failed no-regression, its gated version passed (24 Oct).
- Search state leaks: MuJoCo-Warp warm start and cross-generation state (24 Oct); jitter 1e-5 changes a score 0.18-0.44.
- Verify packed inputs by sha256: stale and wrong-seed rollouts shipped unnoticed (25-26 Oct).
- Zero-action gates do not predict fine-tuned order; keep as a warning, not a gate (24 Oct).
- Early checkpoints already break an open-loop grip by 1M steps (26 Oct); a residual head did not change it (27 Oct).
- A +0.098 gain on one public twin did not transfer; mesh swaps need >= 2 twins or a reference-free argument (26 Oct).
- A better template pays on the leaderboard only if it is also the submitted mesh (31 Oct phase-1 scoring).
- Packed draws are bimodal and partly lucky: packed 0.9164 vs 10-draw mean 0.8755 (29 Oct).
- Insurance swaps (~+0.0005 each) cannot close the +0.046 AUC gap to 5th; only reference-side levers (perception, spoon, templates, eval 10) can (30 Oct).
- Grasp-lock seeds run to the end; early cuts suit only the standard learner (26 Oct).
