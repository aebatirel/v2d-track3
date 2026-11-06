# Digest: early session session_01P8DcCuq1ho9KkXJuxZbq3o (2026-10-20 to 2026-10-23)

Scope: the session's first result events through 2026-10-23 22:58 UTC (task limit 23:01 UTC). Times are UTC record timestamps; agent-quoted Turkey time (TRT = UTC+3) is marked. "Credit" is the Vast.ai account balance. The session's `total_cost_usd` field is the session's own model-API cost, not Vast spend. Estimates are marked as estimates.

## 2026-10-20

### 13:20-14:52: accounts, network, secrets
- The owner's first turns were setup. The session's network policy returned 403 for the Vast API and huggingface.co; outbound SSH (port 22) timed out, 443 connected. The agent asked for network access "Full" (or two allowed domains), network secrets for a new Vast API key and a Hugging Face read token, HF_TOKEN and GH_TOKEN as Vast account variables, $25-50 of credit, and a private dataset repo aebatirel/v2d-store.
- The agent asked for restricted tokens: a GitHub fine-grained token for the one repo with Contents read-only, expiry 2026-11-30; a Hugging Face token limited to the store. It warned that rented machines belong to third parties.
- 14:24: the Vast API answered (HTTP 200) with a $0 balance. HF_TOKEN and GH_TOKEN became visible after the owner added them (14:40). An API key had been pasted into chat; the agent advised rotating it. Auto top-up was left off; balance $25.00 by 14:52. The agent noted that Vast charges a saved card on a negative balance and advised keeping the card (risk: cents).
- SSH from the session was confirmed blocked. Monitoring moved to Vast labels, the Vast logs API, uploads to the store every 30 minutes, and an HTTPS/WebSocket terminal on the box.

### 14:56-15:04: permission friction
- The agent tried to add an allow rule for its own launcher to the repo's settings. The safety check blocked it as self-modification and the file was removed. A launcher fix (`ops/vast.sh` taking settings as arguments) was committed to main-bsky37; an earlier message wrongly said it was pushed, and the agent admitted this. Two later launches were blocked, including a plain test. The agent said only the owner's settings could lift the check and offered: switch the session mode to "Accept edits" and approve each command, or choose an allow rule explicitly.

### 15:04-15:20: smoke test passed
- One RTX PRO 6000 (WS) in Greece at $1.44/h, deleted itself at 15:19 UTC. Passed: key and token delivery, private repo download, a 0.69 GB Hugging Face download in 45 s, store upload, label progress, live HTTPS commands, self-deletion. Cost $0.01; $24.99 left. Not yet tested: full setup on Vast's image, and auto-delete on a stalled job.

### 15:33-16:17: first real GPU box, episode 12
- The first attempt stopped because `pandas` was missing from the image ($0.29). Setup now checks every import, and a failed job keeps the box up 30 minutes. The second attempt (15:48 UTC, same machine) finished setup in about 10 minutes (IMPORTS-OK). The FoundationStereo weights (3.3 GB) and both FoundationPose models went to the store, so later boxes no longer need Google Drive.
- 16:02: perception on episode 12 reproduced Colab: tracking AUC 0.997 (SP-SR 1.0, MP-SR 1.0, MPPE 0.52 cm) against 0.986-0.998 on Colab. Scored after inference against ground truth.
- 16:17: two episode-12 trainings started: `oracle` (motion-capture poses, diagnosis only) and `perc2` (the real pipeline). GPU 100%, 41.5 GB of 96 GB. Alone, one training ran at about 45k steps/s; together about 50k combined. A resume test ("resuming from state_10002432") was run. An environment snapshot went to the store (19:07 TRT).

### 16:43-18:33: cost, Colab, and what counts
- 18:15: the owner asked cost. The agent reported $3.97 spent of $25; about $2 per policy on demand (two trainings per card), about $1 interruptible (estimate). Its project estimate through the Nov 4 freeze: $300-450 on demand, central about $250 (estimates).
- 18:30: the owner asked whether the leaderboard was being smashed. Answer: the Colab figure was tracking only (mean AUC 0.809 over 20 public episodes), which cannot be submitted; only a trained policy run by the official evaluator counts. The Colab robot test (20M steps) scored 0.918 against its own reference.
- 18:33: the owner asked whether public episodes must be run. Answer: no; a submission is the 20 eval episodes (videos only, 20 policies). Harder eval features (survey note 15): the wooden spoon in 10 of 20 eval episodes (no scan), the white pot in 6, stirring, hand-overs, a mid-air cup start, a second person in view.

### 19:09-20:07: first end-to-end score was invalid
- The first end-to-end run gave AUC 0.009 and mean position error 61 cm (the evaluator agreed: 0.008). Even the dish rack, which never moves, scored 0.009. Cause: `mkref.py` took the table from depth around the objects, and the floor past the table edge had more depth points (55% against 39%). The simulated table sat 60 cm too low, so both trainings (about 3 hours) learned on a broken scene.
- Fix: several flat surfaces considered, the one under the objects taken, and an error if none fits. The old policy on the fixed scene scored 0.603 (do-nothing baseline). Retrain started at 19:19 UTC; cost so far about $9-10 (estimate).
- 20:07: credit $17.23 (23:07 TRT), two boxes about $2.91/h together. Plan kept a buffer of about $4 per box.

### 20:22-22:35: perception A/B and the first valid episode
- The compact detection prior (made default, ef3f4e2): no regressions on episodes 0, 12, 27, 39 (within +/-0.003). Episode 26 went 0.065 to 0.988; episode 2 0.977 to 0.993; episode 31 0.876 to 0.887. Episode 39 scored 0.998 here against 0.55 on Colab (large run-to-run variance).
- 22:30: the first valid end-to-end score was recorded (episode 12). Credit $10.11 at 01:35 TRT; the agent projected $2.70 at the end and no new runs.

### 01:53 (2026-10-21): three valid scores
- Episode 12 (cup into rack) AUC 0.890; episode 27 (pot flipped onto rack) 0.965; episode 2 (lid off, pot lifted) 0.926; mean 0.927 (easy episodes, not a leaderboard estimate). SP and MP were 1.00 in all three.
- Perception rule (objects starting close together are assigned separately) raised the 20-episode mean from 0.883 to 0.932; episode 26 from 0.065 to 0.988. Robot wrist jumps of 10-31 cm per frame traced to NVIDIA's hand-to-robot conversion; a higher wrist weight cut them to 8 cm or less. Credit $2.22; about $22.80 spent in the day; all machines deleted.

## 2026-10-21

### 03:05-04:33: explanation and the hard-episode plan
- The owner asked why numbers differed. The agent's three stages: tracking against mocap; the reference on the fitted table; the end-to-end score. Episode 12 went 0.997, 0.973, 0.890: the gap was the robot.
- The owner was offered three hard public twins (episode 24 for eval 25, episode 18 for eval 19 and 30, episode 21 for eval 20). A/B: 6 trainings, default wrist against wrist cost 3.0. Cost about $13-14; top-up $20 requested.
- 04:30: two trainings share one card (82 of 96 GB; about 51k steps/s together); about $2 per policy on demand. Interruptible cards ($0.68-0.72/h) estimated at about $1 per policy; a restarted box re-downloads a 30 GB snapshot. Full submission estimated at about $50 on demand, $25 interruptible.

### 10:01-12:24: own meshes, a hand diagnosis, a validation box
- 10:01: the mesh route defined. Own meshes (from depth stacks) are used for tracking and the submitted mesh; the stacks need poses from scan-based tracking. A-lite (2-3 days): scans only as a development aid on public videos. A-strict (5+ days): no scans at all. Own versus scan (Kaggle-style): pot 0.998 vs 0.999; boards 0.992-0.997 vs 0.999; dustpan 0.953 vs 0.997; cup and pitcher 0.917 vs 0.975.
- 10:35: spent about $39.60 (day one and night about $22.80; hard-episode test about $16.60; store cleanup $0.25). Vast $10.35 left. 44 GB of old checkpoints deleted from the store.
- 10:45: owner asked why the hard episodes failed. Answer: not perception. Boards 0.235 against 0.232 for doing nothing; sweeper and dust pan 0.13-0.34, worse than doing nothing (0.61). Causes: rigid thin objects in the simulator, centimetre hand errors, one training per episode.
- 11:12: hand diagnosis of episode 24: depth at the grasped board made the left hand 4 cm from wrist to fingertip after frame 100 (real about 18 cm; good episodes 10-15 cm). The robot fitted the squashed hand, with wrist errors up to 17-20 cm, so the slide-to-edge move never reached the reference.
- 11:40: top-up of about $120 requested (only $9.79 left): about $20 for public tests, $5 for eval tracking, $60-100 for 20 eval trainings. The approval appears in an unseen turn.
- 11:59-12:24: validation box on episodes 18 and 24 (one retry each). Episode 24's first reference failed the automatic check (wrist errors 98 and 176 mm, jumps up to 22 cm per frame). The wrist-cost retry passed (15 and 30 mm, jumps 7 cm) and training started at 12:24 UTC.

### 13:22-18:01: false bottoms, OOM, first hard-episode scores
- 13:22: the validation box failed twice. The dustpan reconstruction was 3.5 cm under the table and the white pot 5.5 cm, because the camera never sees a resting object's underside. Both episode-24 trainings ran out of memory: the simulator split each colour into a piece, giving 174 pieces per copy across 4,096 worlds. Colourless copies fixed both. Relaunched 13:35 UTC on ep18 (Greece, $1.44/h) and ep24 (Alberta, $1.49/h); credit $18.39 before launch.
- 18:01: own-mesh registered scores. Ep18: 0.396 (was 0.128 and 0.337); doing nothing 0.637; reference 0.982. Ep24: 0.232 (was 0.236 and 0.152); doing nothing 0.229; reference 0.816. The stiffer wrist made both worse. Competitors noted: a Duke team at 0.848 (mesh error 0.065 cm; own 0.3-0.6 cm) and another at 0.831. FlashDexRetarget (arXiv 2610.01849) was flagged as most useful (86% success on this hand against 50% for NVIDIA's method).

### 18:28-20:43: physics search, hand fix, round plan
- Proposed: contact-anchored retargeting and a sampling physics search (about 1,000 variants per window in parallel; SPIDER, Do as I Do). Estimate $1.50-3 per hard episode.
- 19:22: the owner's principle confirmed: object motion is the goal, the human hand is the guide; the leaderboard scores only the object.
- 20:04: hand-placement fix CPU-tested: frames with the robot hand more than 2 mm inside something fell from 242 of 275 to 62 (ep24) and from about 77% to 41 of 361 (ep18). A/B on two boxes, about $7-8, credit $2.69.
- 20:43: $50 top-up proposed for three rounds (about $14, $15, $15). Guardrails: no box starts unless credit covers its estimate plus $3; every box destroys itself; each result committed; averages over repeat evaluations.

### 22:44-23:49: round results
- Round 3 (mean of 6 evaluations): ep24 base 0.297 +/- 0.055; fixed hand reference 0.307 +/- 0.002 (seed 42) and 0.306 +/- 0.018 (seed 43); with keypoint scale 0.313 +/- 0.011; primitive hand 0.282 +/- 0.023. Ep18 base 0.345 +/- 0.046; fixed reference 0.319 +/- 0.042.
- Two root causes found: a start mismatch (training never practised the evaluation's exact start; the sweeper is knocked in the first 10 frames) and floating objects (resting boards 2-4 cm above the table in the reference). Both got opt-in fixes.

## 2026-10-22

### 00:08-03:55: overnight rounds
- 00:08: credit about $36 (03:25 TRT), about $26 committed. Primitive hand on ep18 0.377 +/- 0.021 against base 0.345 +/- 0.046; on ep24 slightly below base.
- 01:01: episode 27 with the fixed reference fell from 0.942 +/- 0.017 to 0.911 +/- 0.017. 01:18: ep18 with fixed reference plus keypoint scale 0.381 +/- 0.012 (base 0.345); ep24 0.313 +/- 0.011 (base 0.297).
- 01:46: ep24 with the start fix 0.318 +/- 0.001. 02:08: episode 12 with fixed reference plus start fix 0.763 +/- 0.025. Every ep24 variant landed between 0.306 and 0.318: the limit was the lift-and-stand phase.
- 02:16: credit $16.12. 03:50: the overnight run totalled 12 GPU boxes and 15 trainings, six evaluations per policy. Report: docs/overnight-2026-10-22.md. Credit at 03:55 UTC: $52.69 to $7.55 over the night (as stated by the agent).

### 03:17-05:21: the sweeper underside
- 03:17: the reconstructed sweeper could not stand in the simulator; its underside was rounded because the table hid it. Fix: flattened underside (library_v3) plus settled start pose. 05:00: ep18 0.345 to 0.715 on average; five of six evaluations 0.79-0.84. Ep24 still about 0.30.
- 05:11: the owner's video check: the robot laid the boards flat; the person stood each board on its edge. 05:12: about $100 for a robust 20-episode submission, about $55 lean; about $6 to validate two fixes first (estimates).

### 05:49-08:41: novelty, rest settling, owner answers
- 05:52: owner's interaction idea (space the camera sees past a hand or table counts as empty) agreed as "the general form of the slot fix".
- 06:11: rest settling on episode 12 scored 0.740 against 0.790 for retargeting alone (one seed). 06:12: asked about novelty, the agent said "not very, so far"; 07:06: rated 1.5-2 out of 5.
- 08:07: the owner's four answers: spoon from eval videos (agreed); automatic rules only (agreed); room map dropped; eval meshes recreated from eval videos (adopted).
- 08:41: a container restart killed the interaction-mesh design workflow; resumed from two saved designs.

### 10:12-14:23: perception accuracy, session limit, organisers' meshes
- 10:19: usage limit hit, blocked until 10:50 UTC; resumed 11:02. 10:12: a full episode through the physics with zero policy action took 34 s.
- 10:23: the owner asked whether the best checkpoint is late. Answer: likely, but measure it. Of 19 picked policies, the best was 250M nine times, 200M six times, 150M and 100M twice each.
- 11:32: CPU evidence round: of 186 mesh variants, mesh polish barely moved the metric. 12:01: real-versus-sim videos (mean of six): ep18 0.715, ep12 0.790, ep27 0.942.
- 10:37: perception on the 20 public episodes: mean 0.932; 15 of 20 at or above 0.95; ep0 0.18.
- 13:41: ADD-AUC mechanics read from the kit. Test on episode 24 with the organisers' meshes: own meshes 0.307 (seed 42) and 0.306 (seed 43), mean 0.307; organisers' meshes 0.389 and 0.245, mean 0.317. Conclusion: "it's not the mesh".
- 14:23: board 2 in the reference floated 2.6 cm above the table; a synced video followed.

### 15:24-18:30: owner questions, spoon run, money
- 15:24: marker spheres: no direct use; indirect only through the mesh.
- 16:08: spoon run launched (owner's approval came earlier): eval 3 (stirring) and 35 (spoon passed between hands) on a Max-Q box in Japan at $1.30/h (about 3 h, about $4, estimate). 17:05: spoon found and tracked in eval videos 3 and 35 ("first eval run ever"). 17:16: no spoon ground truth exists, so no spoon score can be computed.
- 18:18: credit $14.37. Episode 35 moved to its own box in France (RTX PRO 6000 S, $1.38/h); episode 3 continued on the Japan box. 18:30: CPU round finished; mesh rebuilding gives small, risky gains.

### 19:43-21:16: detection and the CHORD question
- 19:43: ep3 at 230M of 250M steps; ep35 at 90M. 20:01: ep3 failed: the detector took the pot handle for the spoon. Fix: size match (0.3-1.3x) and no double-claiming.
- 20:08: Grounding DINO tiny adopted as one weighted vote (it separates objects standing apart, not nested ones).
- 20:53-21:16: the owner was shown official CHORD material. Corrections: whole object motion is fed; the robot does not purely mimic (corrections of +/-5 cm and +/-0.15 rad around the human motion); early training has an assist. Object pose weight 20, contact 10, hand copy 0.5.
- FDR (FlashDexRetarget) numbers are the authors', not reproduced: a shared policy for many motions; its reward weights hand tracking more and gains freedom from wider limits (+/-10 cm, +/-1 rad). Each change needs training from scratch. Test: episode 12 (baseline 0.790) and episode 18 (0.715), two seeds each; seed noise about +/-0.04, up to 0.14 on hard episodes.

### 21:21-23:45: FDR build, ep35 fix
- 21:48: FDR coded (training rewards only): object reward on 128 surface points (worst-3 mean) and a one-sided fingertip-distance reward.
- 21:49: ep35 0.127 (do-nothing 0.112); ep3 0.298 (do-nothing 0.326).
- 22:00: FDR test trained on the GPU with both rewards; episode 12 at 39k steps/s, about 1 h 45 min per run. Cost about $12 for FDR plus $2 for ep35 retrain (estimates).
- 22:08: all boxes working. 22:10: ground-truth masks for the spoon detector rendered for 18 of 20 public episodes (ep0 and ep26 excluded: tracking 5.7 cm and 35 cm off).
- 23:45: seed 43 table (against own reference; single rollouts at 100M, 150M, 200M, 250M, then 250M six-run mean): seed 42 0.708 / 0.871 / 0.902 / 0.914 / 0.905; seed 43 0.687 / 0.812 / 0.741 / 0.836 / 0.774. Agent: "less stable rather than badly chosen".

## 2026-10-23

### 00:47-01:12: ep35 retrain and the FDR result
- 00:47: ep35 with the right-hand start fix (approach from 6 cm, not 18 cm) scored 0.147 (from 0.127; do-nothing 0.112).
- 01:03: seed 42 FDR beats the old setup: episode 12 0.891 against 0.790 (+0.10); episode 18 0.776 against 0.715 (+0.06). Every episode-18 rollout improved except one sweeper drop.
- 01:12: all three boxes finished and were destroyed.

### 04:52-05:42: FDR default, detection plan, eval procedure
- 04:52: owner decision recorded: "FDR is now the default for every run". Vast $4.54; last night's three boxes cost $13.40 in total.
- 04:54: owner asked about VLM detection; Grounding DINO tiny adopted as one vote. 04:58: the kit lists objects per eval episode: spoon alone in 35-37; pot and spoon in 3, 5, 6; rack and spoon in 15, 16; cup and spoon in 32, 33; no spoon in the other 10. The list fixes slot order.
- 05:08: detection test on the 20 public episodes on an India card at $1.34/h (about 1.3 h, $1.75; estimates).
- 05:24: owner asked: two seeds everywhere (about $100-120) or a second seed only where the first scored below 0.85?
- 05:35: two evaluators explained: the official FlashCHORD evaluator (produces the rollout we submit, about 12 s per run) and sim_vs_ref (our reconstruction; no ground truth).
- 05:42: procedure adopted: seeds 42 and 43; six official runs per seed (frame 0, no assist); score each against our reconstruction; keep the higher six-run mean; submit that rollout.

### 06:04-09:40: detection and spoon retests
- 06:04: detection test: 93 of 116 objects correct with the new rules against 78 now; no correct object lost. No public episode contains a spoon.
- 06:10: owner approval (unseen turn) for one seed of each spoon episode (about 2-2.5 h, about $5.50) or two seeds (about $11). 06:14: ep35 retest launched with $28.80 available.
- 06:22: first-frame detection found the spoon in all 10 eval spoon episodes. In eps 3, 5 and 6 the pot and handle form one object.
- 08:20: both spoon retests about 70% through seed 42.
- 09:00: owner asked whether early checks predict the end. Over 29 stored runs (67 pairs): at 40% (100M) the early run was better at the end in 48 of 67 (72%); at 60% (150M) in 53 of 67 (79%). Owner also asked whether seeds were chosen from thousands of trials: no; seeds 42 and 43 fixed in advance; 1,248 detection-rule variants checked on CPU; 4,096 parallel worlds per run.
- 09:40: both boxes retrained both spoon episodes on the fixed approach, two seeds each; seed 42 expected about 11:00, both by about 12:40 UTC.

### 09:48-11:41: drift, ep35 fix, grip problem
- 09:48: reference fingers within about 1 cm of the spoon; with zero policy action the wrist drifted 1-3 cm. The owner's point that the policy pulls hands away was confirmed. Existing reward: -100 at episode end if the wrist drifts more than 15 cm or the spoon more than 10 cm (0.5 rad); -1 per missed contact.
- 10:06: the evaluator accepts only FlashCHORD checkpoints; the same ep3 checkpoint scored 0.34-0.43 over seven runs.
- 10:52: ep35 after the fix: mean of seven runs 0.105 to 0.289; spoon lifted in all seven (10-29 cm; reference 22 cm). Do-nothing 0.112.
- 10:58: ep3 after the fix: 0.410 to 0.380 (do-nothing 0.439).
- 11:07: learning curve (seed 42, 25 checkpoints): pick-up appears only at about 90M; from 100M to 250M the spoon drops at the same moment in every checkpoint (frames 141-147 in ep35; 105-109 in ep3). Last 160M steps taught nothing new about holding; 90-120M may be enough.
- 11:41: pot grasp-lock with lag correction lifts the pot with no policy (6 cm against the reference's 8.3 cm). The spoon does not: about 370 grip variants in the evaluator's physics, none held; a stiffer wrist (400 N/m instead of 25) did not lift it. Decision asked: keep a box about 2 hours for the grip builder (about $3).

### 12:12-14:31: owner questions, stiffer wrist, seed 43
- 12:16: owner's four questions (research note 23 pushed at 12:12, b92d013): other embodiments are allowed (FlashCHORD ships simpler-collision Sharpa, stiffer-wrist Sharpa, arm plus Sharpa, a 3-finger hand); no official Sharpa grasp library (BODex and Dexonomy adaptable in one to two days); anything magnetic must be gone by evaluation (training uses a fading helper force); holding from below is physically right and the wrap does it.
- 12:16: opening fingertips before the knuckles kept the spoon within 2 mm, but pulling away dragged it; score 0.150 against 0.267 with the same grip (noise; replayed three times).
- 12:24: stiffer wrist fixed the episode-3 carry (0.462 to 0.658) but made episode 35 slip. 12:52: ep35 stiffer-wrist force design 0.163; 25-degree angled grip 0.093. Diagnosis: the problem starts at pick-up.
- 12:59: ep35 no-RL "best so far" 0.267.
- 13:22: anatomy rule (knuckles first, palm press): ep3 0.658 to 0.429, but ep35 about 0.18 to 0.52. Rejected for ep3.
- 13:55: means of five official runs against own reconstruction. Episode 3 (spoon and pot): do-nothing 0.439; RL alone 0.38-0.41; new recipe 0.968. Episode 35 (spoon): do-nothing 0.112; RL alone 0.29-0.34; new recipe 0.978. Owner: "a real step up". Caveat: own reconstruction, not hidden mocap; the leaderboard will be lower. Spoon is 32.5% of the final score.
- Recipe: (1) build the grip from video (wrap the hand round the handle, knuckles first, thumb last, palm pressing); (2) lock the hand while carried and correct wrist lag; (3) stiffer-wrist setting; (4) RL fine-tune of 40-70M steps, 11-19 min on one GPU.
- 14:22: seed 43 reproduced: ep35 0.971 at 30M, 0.973 at 40M. Ep3 seed 42 0.965 at 40M and 0.981 at 70M (mean of five 0.968); seed 43 0.843 at 40M (the pot, held by a copied grip, was weak: within 3 cm only 54% of frames).
- Rule adopted: train 70M steps; re-run each candidate several times; keep the best by the agent's own reconstruction score (no ground truth). 14:31: the box was destroyed after its hold expired; the agent could not confirm the upload from the session.

### 16:59-20:58: costs, public check, support fill
- 16:59: new recipe about $0.80-1.10 per episode on an RTX PRO 6000 at about $1.38/h, against about $3.30 for the old RL-only pipeline (estimates from timings). 17:01: Vast balance $9.06; owner rule: estimate plus $3 must fit in credit.
- 17:11: public check on a PRO 6000 WS at $1.761/h (estimate $4.20-4.90).
- 19:20: public check done; box destroyed; batch cost about $3.90; credit $5.15. Against real mocap, five runs each: ep27 0.972 +/- 0.004 (70M) vs 0.94-0.96 (250M); ep12 0.910 +/- 0.023 (70M) vs 0.891 (250M; other seed 0.762); ep18 0.320 +/- 0.072 vs 0.889 (much worse); ep24 0.202 +/- 0.072 vs 0.307 (worse; no slide-to-edge step yet). Carry episodes worked with about 3.5 times less training.
- 20:04: support fill under resting objects and thickness-based grips proposed (no GPU cost to build). 20:29: stability check (pipeline/support_fill.py), simulator check (tools/rest_check.py), and note 25 pushed.
- 20:58: a no-action replay of ep12 scored 0.656 on one box and 0.560 on another with the same reference (GPU randomness, about 0.10).

### 20:51-21:43: episode 18 re-plan, recovery, fill
- 21:03: ep18 without fill: the brush fell 86 mm and 82 degrees before any hand reached it. Re-plan (triggered by a 12.6 cm and 71-degree offset): no-action score 0.093 to 0.273; a second round scored 0.100 on the same spot; part of the gain may be luck.
- 21:37: re-planned policy curve 0.304 (10M), 0.184 (30M), 0.346 (50M), 0.168 (70M); 50M picked. Re-planning alone did not rescue ep18.
- 21:42: root cause (owner-facing): the cameras never see the brush underside; the reconstruction closed it; the brush touched the table on 0.3 cm2 with its centre of mass 3.3 cm outside and fell in about five steps. The 0.889 run combined flattened underside, settled start, and 250M steps. The grasp-recipe check had used the default rounded brush, which was a gap.
- 21:43: ep27 with fill finished: 70M checkpoint 0.976 against its reference (0.972 before).

### 22:14-22:58: early approach, hands, final checks
- 22:14-22:25: early approach works on the GPU: the brush stands until grasp (max 9.4 mm and 9.5 degrees movement before frame 55), where the old reference hand knocked it flat (88 degrees).
- 22:30: episode 39 (dust pan alone) reference from raw video: perception 0.982 against mocap. Episode 2 (lid on pot): perception 0.994; the lid pops 31 mm and 27 degrees before any touch because the pot's collision pieces fill part of the rim.
- 22:43-22:46: trainings on the four new episodes; submission packaging job (ops/jobs/submit_pack.sh) written; Kaggle upload needs the owner's account. Commit 37cc551 (wave 1). 22:53: settling committed as option SETTLE=1, off by default.
- 22:58: ep18 checkpoint curve against own reference: 10M 0.446; 30M 0.357; 50M 0.307; 70M 0.060. Training got worse the longer it ran on ep18; the agent pointed at the copied clamp grasp. The 0.889 run used the standard recipe without grasp lock.

## Lessons and turning points

- A broken scene produced the first end-to-end number (AUC 0.009, 61 cm). Scene sanity checks should come before the first training; the pipeline now stops on them.
- Most decisive findings came from CPU replays and no-action rollouts (squashed hand, floating boards, rounded sweeper underside, slot assignment, start fault), at no GPU cost. The agent then adopted measure-first as a rule.
- The sweeper's flattened underside plus settled start moved ep18 from 0.345 to 0.715 (one seed; five of six evaluations 0.79-0.84). The wrap grasp with a stiff wrist moved the spoon episodes to 0.968 and 0.978 against own reconstruction (do-nothing 0.439 and 0.112).
- Several fixes failed or were mixed: fixed hand reference (ep27 0.942 to 0.911), primitive hand (mixed), rest settling (ep12 0.790 to 0.740), stiffer wrist on the spoon (ep35 slip), anatomy rule (ep3 0.658 to 0.429). Each was reported with its spread.
- Noise is large: ep12 scored 0.890, 0.860 and 0.858 in three trainings and 0.604 once; seed spread up to 0.14 on hard episodes. Adopted: two seeds, six repeat evaluations, selection only by the agent's own reconstruction score.
- Training length was episode-specific: 250M was best in 9 of 19 picked policies; the spoon's pick-up appeared only between 70M and 90M; the ep18 curve worsened with length under the copied grasp. The rule became 70M steps with candidates re-run.
- Money was the binding constraint: credit $52.69 to $7.55 over one night (agent's figures); repeated top-ups; boxes self-destroy; a $25 account ceiling; per-policy estimate moved from about $2 on demand to about $1 interruptible.
- Artefact discipline slipped once: five final checkpoints were lost when the Hugging Face store hit its quota. The surviving seven policies (35 MB) went into git with a SHA-256 index; the store was upgraded to Pro (1 TB private, 2026-10-21).
- Access limits: SSH was blocked from the session throughout; a safety check blocked the agent's self-written permission rule and its own launches, so the owner changed the mode. A usage limit blocked the session 10:19-10:50 UTC on 2026-10-22.
- Owner ideas that worked: the twin-episode selection (eval 25, 19, 30, 20), the object-motion-is-goal framing, the interaction-based slot idea, and recreating eval meshes from eval videos. Dropped: the room map (used ground truth); marker spheres (no direct use).

## Coverage

- Oldest result event reached: 2026-10-20 13:20:49 UTC. Two further reads returned no result events, so the session start was reached.
- Newest result event covered: 2026-10-23 22:58:08 UTC (task limit 23:01 UTC).
- Method: `list_events` with `kinds: ["result"]`, paging backward by `before_id`; pages without result events were normal.
- Per-page cursors, timestamps and the figures behind this digest are in /tmp/claude-0/-home-user-v2d-track3/40ae8bef-a6ac-5623-abee-9e3e721c7845/scratchpad/report/digests/chats_early2_progress.md.
- Gaps: the owner's own messages are not in the results; their wording is taken from the agent's replies. Several cost and timing figures are the agent's estimates and are marked as such where stated.
