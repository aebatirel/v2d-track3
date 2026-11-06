# Digest: V2D Track 3 work log, part 1 (Imitation.Tech)

Source: `scratchpad/report/corpus/worklog_part1.md` (all 2,954 lines, branch `origin/claude/affectionate-turing-5l53o6`), covering 2026-10-01 to 2026-10-24. Times are TRT (UTC+3) unless marked UTC. Costs are Vast credit changes as logged. [H] = hypothesis, [I] = the log's inference. The log records no submission by our team.

## Perception (depth, detection, identity, tracking, hands, room map, point tracks)

- **2026-10-12 Colab exp1 (public ep12, perception only):** FoundationStereo + OWLv2 + SAM2 + FoundationPose with public scans. Cup only: AUC 0.927, MPPE 1.45 cm (position error median 1.30, max 3.74 cm). Both objects: AUC 0.964, MPPE 1.00 cm. Adopted as the base.
- **2026-10-13 OWLv2 detector (perc.py), 20 public episodes:** ep12 0.991, ep13 0.997, but grayscale OWLv2 missed the white pot (ep0, ep2) and swapped ep11 twin cups (0.10). Replaced.
- **2026-10-13 perc2 (SAM2 proposals x DINOv2 similarity, size gate, Hungarian), 20 public episodes:** mean AUC 0.809, SP 0.90, MP 0.85, MPPE 4.76 cm. Per episode: ep0 .179, ep11 .871, ep12 .995, ep18 .935, ep21 .858, ep24 .820, ep26 .031, ep27 .994, ep31 .885, ep39 .550, ep41 .795, ep45 .836 (others 0.80-0.99). Lesson: FoundationPose register scores are not comparable across masks (a rack fragment scored 143 against 73 for the true cup).
- **2026-10-20 night, detection prior `DET_PRIOR=compact DET_K=80`:** joint choice over each object's top-80 proposals with a penalty on pairwise distance beyond 0.45 m [H: task objects start close together]. A/B on 20 public episodes, one seed: mean AUC 0.883 to 0.932; ep26 0.065 to 0.988; ep45 +0.026; worst -0.003 (noise). Adopted as default. Still weak: ep0 0.18 (lid symmetry), ep24 0.85, ep11 0.87, ep31 0.89.
- **Hands (2026-10-13 to 10-21):** MediaPipe found hands on colour camera a in 173 of 181 frames (ep12) but almost none with two hands on mono camera c, so hands are taken from camera a and lifted with stereo depth. Viterbi identity linker fixed the ep12 hand-over but gave 276 wrist steps > 5 cm against 255 for greedy (IK-confounded) and more spurious tracks; greedy kept as default. The fitted hand scale is pinned at its 0.85 clamp; a wider bound moved it to 0.84 with no change in palm steps (unresolved).
- **Detection rules (2026-10-23 06:45, frozen at ab06a32):** baseline 78 of 116 instances correct (22 of 29 at frame 0). Shipped rule (reach gate 1.0 m, size term on the eroded extent, Grounding DINO tiny term 0.2) gives 93 of 116 (24 of 29), 0 lost. Geometric check and merge rejected. Eval spoon frame-0 check (inference only, reported, not used to tune): spoon chosen correctly in 10 of 10 spoon episodes.
- **Room map (owner answer, 2026-10-22 11:20):** not in the pipeline. Its mocap registration used public ground-truth constants (table height 0.6012 m, GT lean and heading), so it is inadmissible. A GT-free rebuild would gain about +0.01 over decent visual odometry. Dropped.

## Policies and following (RL training, recipes, retrains, sim, seeds, flips)

- **2026-10-12 Colab smoke:** sharpa_flash_sac on tissue_box_simple, 4,096 worlds: about 45,300 env steps/s, 40.5 GB GPU; 250M steps estimated at 1.5-2 h. The 20M-step tissue-box policy against its own reference: add_auc 0.918, maniptrans_sr 1.0, MPPE 1.63 cm.
- **2026-10-20 evening, first end-to-end score: invalid.** ep12 AUC 0.009; both objects fell 55-60 cm in 10 frames. Cause: one RANSAC on a ring around the objects picked the floor (55 % of points) over the table (39 %). Fix 30d3633 (sequential RANSAC, nearest plane under the objects, abort guard). Sanity check: old policy on the corrected scene 0.603 against static floor 0.604.
- **2026-10-20 night, first valid score (ep12, perc2, greedy hands, 250M, one seed):** sim vs mocap AUC 0.890, SP 1.00, MP 1.00, MPPE 1.5 cm (cup 0.780, rack 1.000). Reference 0.973; sim vs reference 0.863; floor 0.604. Oracle diagnostic with mocap objects (evaluation only): AUC 0.858, MP 0.00. Reading: policy tracking costs about 0.14 AUC on ep12, perception about 0.03.
- **Wrist IK cost (2026-10-20 night, `mkref --wrist_cost` 0.2 / 1.0 / 3.0):** ep44 right p95 11.7 / 7.3 / 2.5 cm, wrist max step 30.9 / 16.8 / 4.6 cm; fingertip error rises from 0.8-1.4 to 1.6-3.1 cm. Option "c", not the default. Bone normalisation: mixed (ep12 right median 4.8 to 14.6 cm), not adopted.
- **ep12 vw (Viterbi hands + kp 400 wrist, 2026-10-21):** AUC 0.860 against 0.890; no gain (one seed). **ep12 vc (Viterbi + wrist cost 3.0):** AUC 0.604, equal to the floor; the cup flipped at table height from f60. ep27 vc 0.965 (floor 0.559), ep2 vc 0.926 (floor 0.503) worked. Verdict: no wrist cost 3.0 without multi-seed tests.
- **Hard-episode A/B (2026-10-21 11:10-11:25, one seed, default vs c):** ep21 0.826 vs 0.793 (floor 0.359); ep24 0.235 vs 0.167 (floor 0.232); ep18 0.127 vs 0.337 (floor 0.610). Policy failure, not perception, dominates hard tasks.
- **Validation attempt 1 (2026-10-21 18:05, own meshes, route A):** ep18 mc seed 42 150M: AUC 0.381 (registered 0.396), harmful. ep24: 0.096 (registered 0.080), harmful. Both fail on wrist tracking. Eight repeat evaluations of ep18: mean 0.332, std 0.08, range 0.131-0.410; a single evaluation misleads by about 0.07.
- **Mid wrist mcw (2026-10-21 18:55-20:00):** ep18 0.193 (mc 0.381), ep24 0.050 (mc 0.096). Falsified.
- **Hand separation mcs (2026-10-21 19:00-20:50, ep24):** robot hands interpenetrated at reset (-6 to -14 mm) and popped board 1; `mkref.separate_hands` added. Result: AUC 0.231 (floor 0.229); boards never lifted. Not adopted as a score gain.
- **Start mismatch (2026-10-22 03:05):** training resets scale fingers by U(0, 0.7) with a 20-step object hold; the evaluator starts at frame 0 with exact fingers and no assist. Opt-in fix `FC_IMMEDIATE_FIRST_FRAME=0.25`.
- **Contact retargeting, "k" (2026-10-22, six evaluations each, registered AUC):**
  - ep12: base 0.725 +/- 0.067; k 0.790 +/- 0.023; ki 0.763 +/- 0.025.
  - ep18: base 0.345 +/- 0.046; k s42 0.319 +/- 0.042; k s43 0.361 +/- 0.038; start fix alone 0.351 +/- 0.056; kq (object keypoints 0.15 m) 0.381 +/- 0.012.
  - ep24 (base 0.297 +/- 0.055): k 0.307 +/- 0.002; kq 0.313 +/- 0.011; ki 0.318 +/- 0.001; primitive-collision hand 0.282 +/- 0.023.
  - ep27 (base 0.942 +/- 0.017): k 0.911 +/- 0.017 (-0.031); ki 0.897 +/- 0.013.
  - Reading: retargeting narrows the spread (ep12 +/-0.067 to +/-0.023) but the mean moves within noise and costs ep27. Not adopted as a blanket change. Primitive hand: ep18 0.377 +/- 0.021 (+0.032), ep24 -0.015.
- **Stable sweeper (2026-10-22 06:45-08:00, ep18 kfi s42):** the sweeper's unobserved rounded underside made it unable to stand; `flatten_base.py` (library_v3) plus stable-pose rest settling. AUC 0.715 +/- 0.240 (rollouts 0.785, 0.179, 0.841, 0.815, 0.842, 0.828). One seed; the gain is attributed to the stable sweeper (kri with the rounded sweeper: 0.368).
- **FDR rewards (design 2026-10-23 00:50; A/B 02:35-04:15, six evaluations each):** training-only reward reusing FlashCHORD's term slots: object point match on 128 surface points at true size, one-sided fingertip bound, and down-weighted contact wrench terms. Hypothesis: FlashCHORD's object reward has no gradient past 0.3-0.5 rad rotation error (CPU check: 0.00 against 0.15 at 1.5 rad).
  - ep12: FDR s42 0.891 +/- 0.015 (k 0.790); FDR s43 0.762 +/- 0.078.
  - ep18: FDR s42 0.776 +/- 0.229 (kfi 0.715 +/- 0.240); FDR s43 0.889 +/- 0.011.
  - The pre-set rule (both episodes gain on both seeds, or one gains at least 0.05 and the other loses at most 0.02) was not strictly met (ep12 s43 is below its s42 baseline). Recommended; owner made it default on 2026-10-23 04:40. Cost about $5.0 and $5.4.
- **Spoon ep35 capped lead-in (2026-10-23 01:20-03:50):** the lead-in moved the right hand 18 cm in 6 frames. Capped retrain: sim_vs_ref 0.147 (was 0.127; floor 0.112). The start was not the main limit; the spoon needs an in-hand turn of up to 140 degrees. Cost about $3.1.
- **Spoon rehearsal seed 42 before the VOC fix (2026-10-23 12:05-13:10):** ep3 0.410 (floor 0.439) and ep35 0.105 (floor 0.112), both harmful; no object moved. Root cause: FlashCHORD's virtual object controller uses the mean inertia diagonal; the spoon's inertia ratio is 38, so explicit damping diverges above VOC about 0.13. The first four curriculum stages (about 64M of 250M steps) trained on exploding spoon episodes.
- **VOC fix (`FC_VOC_INERTIA`, full body-frame inertia), seed 42, seven evaluations each (2026-10-23 13:50-13:58):** ep35 mean 0.289 (range 0.106-0.394; stock 0.105), spoon lifted in all seven; ep3 mean 0.380 (floor 0.439; stock 0.410), chosen 70M, later checkpoints lift and lose the spoon. Training 54-61k steps/s against 27.5k stock. Curves: pick-up appears at 70-90M, flat to 250M; [I] longer training will not fix the hold.
- **Spoon RL fine-tune on the kp 400 wrap reference (2026-10-23 16:10-16:55, one evaluation per checkpoint):** ep3 seed 42: 40M 0.965, 50M 0.946, 60M 0.980, 70M 0.981 (zero action 0.658; RL alone 0.380 and 0.413; floor 0.439). ep35 seed 42: 10M 0.943 to 70M 0.961 (zero action 0.412; RL alone 0.337; floor 0.112). Seed 43: ep35 40M 0.973; ep3 40M 0.843 (pot within 3 cm only 54 % of frames). Caveat: our-reference metric, single evaluations vary by about 0.1.
- **Public recipe check (grasp-lock + fine-tune, frozen, five evaluations, 2026-10-23 18:15):** ep27 0.972 +/- 0.004 (previous 0.942-0.956); ep12 0.910 +/- 0.023 (previous 0.891 / 0.762); ep18 0.320 +/- 0.072 (previous 0.889); ep24 0.202 +/- 0.072 (previous 0.307). Wins on grippable objects with 3.5x fewer steps; loses on plates, boards and tool tasks.
- **Support fill (`support_fill.py`, 2026-10-23 21:30):** the centre of mass must sit over the support with a tip margin. Calibration: pot 44 degrees, dust pan 21, cup 18 stayed; filled brush at 3.7 degrees fell. ep12 0.886 +/- 0.039 (against 0.910); ep27 0.963 +/- 0.006 (against 0.972). Not adopted without a gain. Recovery drops (`FC_DROP_START`): ep12 0.869 +/- 0.052, ep18 0.220 +/- 0.103.
- **Re-plan (`grasp_lock --sim_trace`, 2026-10-23 22:00 UTC onward):** ep18 0.405 +/- 0.016; ep26 zero action 0.490 against 0.212, final 0.383 +/- 0.131; ep21 not kept.
- **Grasp lock on settled ep18 (E1, 2026-10-23 22:58 UTC):** 0.302 +/- 0.094; curve 0.446, 0.357, 0.307, 0.060 at 10/30/50/70M, so training degrades it.
- **Standard recipe on ep39 (2026-10-24 01:07 UTC):** the dust pan is lifted: 0.802 +/- 0.280 (rollouts 0.946, 0.241, 0.948, 0.937, 0.937). Grasp lock on the same reference: 0.174 +/- 0.003. Cost about $2.0.

## Grasp and references (contact labels, reference building, lift windows, grip)

- **Contact-anchored retargeting (stage 3c, `CONTACT_RETARGET=1`, 2026-10-21 22:35-23:05, CPU):** ep24 dirty frames 242 of 275 to 62; penetration p95 20.1 to 6.0 mm; median start-frame pop 8.6 to 2.9 degrees; frame 0 6.2 to 0.8 degrees. ep18 penetration p95 16 to 2.7 mm. Adopted in the pipeline; its score effect is in the policy section.
- **Wrap grasp (`grasp_lock --wrap`, 2026-10-23 14:30-15:20, ep3, zero action):** floor 0.4388; original 0.380; pinch + ILC 0.367; wrap + ILC 0.462. With kp 400 wrist: wrap 0.658 against kp 25 wrap 0.462; spoon within 3 cm 87.5 % of frames against 16.9 %. Hold trials: 8 of 8 whole-hold trials at 1.5 cm / 5 degree disturbance.
- **Single-hand carry, ep35 (zero action):** spoon held to f392, sim_vs_ref 0.205 (original 0.093). Release variants 0.218, 0.267, 0.150; replays of one variant 0.150, 0.172, 0.185.
- **Anatomy closing (MCP first, 10-frame close, palm press, 2026-10-23 15:50-16:10):** ep35 0.521 (uniform) and 0.501 (force design), against 0.150-0.267 before; the pick-up roll was the main loss. On ep3 (kp 400) the same rule gave 0.429-0.454 against 0.658.

## Meshes and CD-O (templates, scans, registration, mesh tiers, mesh adoption)

- **Admissibility (owner 2026-10-21 13:20, route A):** eval episodes use only our own meshes; public scans are a development aid. The FAQ (downloaded 2026-10-21) says participants "should reconstruct the objects ... and submit their own reconstructed meshes". Library v1 and v2 used public scans as `--others`, so library_v5 was rebuilt from own meshes (2026-10-22/23).
- **Registration sensitivity (2026-10-21 08:25, six episodes):** clean 0.987; convex hull 0.947; bottom 20 % removed 0.904; 3 mm noise 0.825; 5 mm inflation 0.608, with flips (ep23 0.052, ep18 0.247, ep39 0.470).
- **Own reconstruction (`recon_mesh.py`, TSDF), ep41 white pot against scan 0.9985:** v0 0.9925; with the table and hand fixes 0.9881; cube +-30 cm 0.9979. v5 (`--close auto`): ep41 0.998, ep23 0.997 (flip rate 0), ep39 dust pan 0.880 (edge filter; 0.953 without).
- **Library v1 (2026-10-21, registered AUC ours / scan):** ep41 0.987 / 0.999; ep27 0.993 / 0.994; ep2 0.983 / 0.977; ep24 boards 0.864 / 0.840; dust pan 0.992 / 0.997; sweeper flips 0.12-0.25. Beige cup 0.857 / 0.914 after keeping pieces within 15 cm.
- **Library v2:** pot and dust pan rebuilt with `--below_carve` (lowest point vs table: v1 -3.3 to -5.5 cm; v2 -0.2 to -0.6 cm). Pot AUC 0.987 to 0.998; CD-O 0.58 to 0.44 cm; dust pan CD-O 0.52 to 0.33 cm, AUC 0.992 to 0.982 (accepted).
- **Library v4 (flattened boards, wave 1 2026-10-23 22:45 UTC):** perception AUC 0.029 on ep24 (v2 boards 0.795). Unusable for perception.
- **Interaction census (2026-10-22 10:30):** boards lack interlocking notches (10.8 cm3 column in ep23 and ep24); lid on pot has a 20-25 cm3 ring; nested cups 42.7 cm3. CoACD refills the slot (hull overlap 16.9-17.0 cm3). Collision geometry, not the mesh alone, is the gap.
- **Mesh v5 evidence round (2026-10-22 21:45, CPU):** of 186 meshes only the observation-first set for lid, dust pan and pot passes "no worse" (-0.025 cm CD-O, -0.39 mm offset). Critic: the fallback is much worse on the ep18 sweeper (0.510 cm, flips 6 of 6); spec not adopted; port estimated 3-4 days.
- **Organisers' meshes on ep24 (2026-10-22 16:45-20:15):** 0.389 +/- 0.077 (seed 42), 0.245 +/- 0.001 (seed 43), mean 0.317, against our meshes 0.307. The ep24 limit is reference and learning, not the mesh.
- **Sim collision bug (2026-10-21 16:20):** Newton splits colour-coded meshes into one shape per colour; our board became 174 fragments, CoACD ran past 10 minutes and the job was killed. Fix: uncoloured simulator copy (scene build 4.2 s, 0.61 GB).

## Scorer and task understanding (how the metric works, what it rewards, measured facts about the task)

- **Metric (kit `AUC.py`, read 2026-10-21/22):** per frame and object, ADD after mesh registration and one frame-0 alignment. Per-frame score 1.0 below 1 cm, -0.125 per further cm, 0 at 9 cm. Mean over frames, then objects, then a plain mean over the 20 eval episodes.
- **Object weights (roster):** wooden_spoon 32.5 %, white_pot 15 %, blue_cup 12.5 %, plastic_dish_rack 12.5 %, mini_dust_pan 7.5 %, beige_cup 5 %, mini_sweeper 5 %, lid, pitcher and two wooden pieces 2.5 % each.
- **Registration:** the kit registers the submitted mesh to a hidden scan (ICP, 25 starts) and aligns the world at frame 0; errors are symmetry-aware (cups any spin; lid 0/180). Our scorer is unregistered, so our numbers are not exactly official. Shape errors move the registration (2-4 degrees, or a flip on flat, near-symmetric objects), and that error enters every frame.
- **Evaluator facts:** start at frame 0, exact fingers, no settle or assist; VOC scale 0; termination at wrist 0.15 m, object 0.10 m or 0.50 rad. Perception-only AUC cannot be submitted; a do-nothing rollout cannot be submitted.
- **Simulator (`sim_physics_inventory`):** MuJoCo-Warp, 20 fps x 5 substeps, contact mu 1.0, finger kp 1.7 Nm/rad, wrist kp 25 N/m, spoon and pot 0.3 kg placeholder. `njmax` 512 overflows (45 of 294 log lines); NVIDIA's recipe uses 1024; raising it needs organiser or owner approval.
- **Predictive check:** over 27 stored policies, corr(sim_vs_ref, registered AUC) 0.997, mean difference 0.021; pairs differing by at least 0.02 were ranked correctly 63 of 63. sim_vs_ref cannot see a wrong reference (ep3 case).

## Leaderboard and submissions (every upload: pack name, date, change, board scores, rank)

- **No submission by our team in this part.** `ops/jobs/submit_pack.sh` written (2026-10-22), not run. The owner chose CPU work and 3-4 public episodes before any baseline submission (2026-10-22 12:00); the baseline was planned for about 27 Oct.
- **2026-10-12, 5 teams:** SoySauceChicken AUC 0.765, SP 0.80, MP 0.50, CD-O 0.583; Zimo Li 0.368; Xueyi Wang 0.296; Panav Raaj 0.276 (best CD-O 0.112); Zihao Guo 0.229. [H] Teams 2-5 score below the public "nothing moves" floor, so their errors are likely systematic.
- **2026-10-22 10:38 UTC (leader):** richchentw AUC 0.903, SP 1.00, MP 0.95, RPE 1.50 cm, MPPE 1.46 cm, CD-O 0.282 cm (2 submissions). Then SoySauceChicken 0.848 (CD-O 0.065), Zihao Guo 0.831, SRL 0.694. The log reads the gap as tracking, physics and policy success, not mesh polish.

## Process, cost and infrastructure (GPU rentals, $ spent, bugs, failures, tooling, rules adopted)

- **Vast.ai costs (as logged):**
  - Smoke box (GTX 1070, $0.061/h): $0.01. Day-1 box 1 (RTX PRO 6000 WS, $1.444/h): about $0.29, failed at a missing pandas import.
  - 2026-10-20: about $22.78 of $25 spent; credit $2.22 at the end.
  - 2026-10-21: top-ups took credit to $27.19, then $19.79 after $10, $9.78 at 19:20, $2.69 at 23:00.
  - 2026-10-22 overnight: $50 top-up, 13 boxes, $49.76 spent, credit $2.93 at 09:15. Further top-ups to $12.90, $14.37, $28.80 (2026-10-23 07:10).
  - 2026-10-23 to 10-24: credit $23.02, $9.06, $15.01 before a batch, $4.08 at 06:50 UTC.
  - Prices: RTX PRO 6000 WS $1.38-1.76/h; Max-Q $1.07-1.36/h; S $1.38-1.69/h; RTX 5090 $0.83/h (32 GB, rejected). Max-Q gives 76 % of the WS speed (41.7k against 55.1k steps/s). Pre-campaign estimate: $110 (range $80-155).
- **Owner rules (2026-10-20 review, 29 rules):** kept 18; removed 5 (including colab: "no need you can yolo in vastai"); changed 5 (no fixed time limit with a stall watchdog; small results committed, bulk data out; "exhaust improvements before changing architecture"). Undecided: remote.
- **Working rules in force:** no downloads without asking (2026-10-07); budget guard (estimate + $3 margin within credit); hold guard and watchdog; GPU boxes write only to the HF store; commit and command recorded per run; eval changes only generic, never per-episode.
- **Bugs and failures (dated):**
  - setup.sh printed a mirror OK on an empty store; fixed 27a4e8c (2026-10-20). Vast image lacked pandas.
  - pinocchio 4.1.0 MJCF signature mismatch; fixed 3aa3b5f.
  - `hard_ab.sh` copied references before the target existed; hands silently re-ran; fixed d4ac331 (2026-10-22), all variants had failed.
  - Bare `wait` on a hold loop deadlocked three job scripts; fixed by waiting on worker PIDs.
  - `render_rollout.sh` rendered 181 frames for every episode (fixed e8b5735, 2026-10-21).
  - Container restart 2026-10-22 about 11:30; session worker down 01:06-06:50 UTC on 2026-10-24 (no boxes running).

## Owner decisions and quotes

- 2026-10-05: "anything goes" for the leaderboard (within the rules).
- 2026-10-20: colab removed from the rules: "no need you can yolo in vastai".
- 2026-10-21 13:20: route A (own meshes only on eval); "do whatever it takes for the best score".
- 2026-10-21 21:40: "faster attempts on the failure places; start from the cleanest frames, multiple starts that meet".
- 2026-10-21 22:35: "snap the fingertips, let the wrist follow".
- 2026-10-22 08:30-09:00: "would this be a robust solution ... what would be the stages ... look at the research"; "when creating meshes we see how pieces interact with each other and build the meshes according to that".
- 2026-10-22 11:20: "don't you re-create the mesh for the eval episodes" (adopted as per-episode re-fusion seeded by the library mesh).
- 2026-10-22 12:00: "first finish what you need to do ... with cpu and then ... 3-4 public examples ... if we get acceptable results we go for full 20".
- 2026-10-22 16:45: "do we get good score with pre mesh for the ep 24 ... I added 10 bucks".
- 2026-10-22 (01:00 TRT): "go crazy, I trust you" ($50 top-up).
- 2026-10-23 04:40: "Fdr can be default ... We need to fix the spoon episodes before full launch."
- 2026-10-23 07:10: "make sure 3 and 35 run well, then full eval".
- 2026-10-23 14:15: "secure grasp is more important than replicating it".
- 2026-10-23 15:05: "wrap the hand around the handle, that's the strongest grasp".
- 2026-10-23 15:50 (on the ep35 video): "the grasp works; know which hand holds what and when, act accordingly, copy the hand switches in a way that makes sense; the curl hold is usually the right solution".
- 2026-10-23 ~21:30: "a mathematical requirement to make sure it starts stable".
- 2026-10-23 ~22:30: "snap and grasp in the dynamic world; a drop should not stop the recipe".
- 2026-10-24 ~01:15 TRT: "exhaust the credits to test the robustness of our recipe ... no early stopping ... top 3".
- Pending in the log (no answer recorded): best-of-N selection; the kp 400 wrist as submission embodiment ("owner to confirm before any submission uses it"); spoon placeholder mass 0.3 kg; njmax 1024; organiser questions (spoon frame, own-mesh rule).

## Lessons stated in the log

- A sanity check against the static floor caught a floor-fit bug that had given AUC 0.009 (2026-10-20).
- Single evaluations mislead (+/-0.07 on a 0.30-mean policy); change one thing per A/B; three changes at once (kp 400 + primitive + start fix) were stopped (2026-10-23 04:15).
- Registration makes the scorer sensitive to mesh shape; flat, near-symmetric objects flip.
- A wrong reference can hide behind a good-looking policy score; check perception and reference QA separately.
