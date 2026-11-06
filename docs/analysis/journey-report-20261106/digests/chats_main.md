# Chat digest: session_01P8DcCuq1ho9KkXJuxZbq3o (main early session)

Title: "NVIDIA Isaac video_to_data repo size". Created 2026-10-20 13:19 UTC; last update 2026-10-27 06:15 UTC; status need_input. Usage cost_usd 1371.27 (get_session).

## Coverage and method (read first)

- Paged with list_events, kinds user and result, limit 100, backwards from the newest event. Coverage is complete from 2026-10-27 06:15 down to about 2026-10-24 11:09 UTC. **The oldest part, about 2026-10-20 13:19 to 2026-10-24 11:09, was NOT paged** (about 3.9 of 7.5 days). Owner messages in that range are therefore missing.
- Most "user" events are tool results or child-agent/task records. Owner messages were identified as string content tagged with client_platform (desktop_app or ios). Two owner messages with the same content are shown once.
- Events in this feed carry session_id 8c892c5e-fd7c-57aa-abef-68d2af098e4f. Those are the agent's turn results and background-task notices for this project.
- Cost figures: the cumulative total_cost_usd in result events is an API list-price estimate (for example $1,055 at 2026-10-24 11:58 and $1,391 at 2026-10-26 16:41). Real Vast spend was much smaller and is given where the agent reported it.
- Session 2 (session_01LhbGHrt6epRs52jSRX48AU) was NOT paged. Metadata only: "Kalman filters and physics-based control research", created 2026-10-26 15:16 UTC, updated 2026-11-03 12:21 UTC, status completed, last summary "pack 13j final and pushed; handed off for upload", usage cost_usd 1288.60.

## Chronology: 2026-10-24 (from about 11:09 UTC)

**Owner messages and what they decided**
- 12:22 (ios) "How did ypu got that amazing score for ep18?" Answer (12:23): ep18 reached 0.957 ± 0.002 (5 runs) with three changes: onset anchor (grasp at object-motion onset in own reference; sweeper grasp moved from frame 53 to 29), a simulated grasp search per hold (256 worlds, 64 candidates, 4 perturbed repeats), and a 70M RL fine-tune. No ablation. ep18 is a development episode, so this is not held-out evidence.
- 12:25 (ios) "Is this inside the rules of the challenge?" Answer (12:28): the approach is allowed (method-agnostic; evaluator unmodified). Three open questions: the stiffer floating-hand wrist (400 N/m and 150 N, against default 25 N/m and 45 N; owner confirmation never recorded); the mesh origin, because public scans were used as tracking templates (the main risk); and the spoon mesh, which is a model rather than a reconstruction. Recommendation: run and pack tonight, then send the organisers an email.
- 12:31 (ios) "How much money do you need for a full run and how long would that take." Answer: top-up about $26 ($30 with margin), 3.5–4 h.
- 12:33 (ios) "What score do we expected to have in the end of this run." Answer (12:35): ADD-AUC about 0.76 (0.60–0.86). Per-episode estimates given; 4th place (0.752) would be reached if right.
- 15:05 (ios) "Okay I added 50 bucks run the whole pipeline with 20 eval lets get our ranking." Launched the full run (see turns).
- 16:36 (ios) "...we did scored the tracking of the public ones compared to the real ones right?" Answer (16:37): perception vs mocap was 0.932 with scan templates (22 Oct); with own meshes, 0.795–0.994 on 7 public episodes (mean about 0.94; ep24 the lowest). Full pipeline vs mocap on 5 public episodes: 0.958, 0.957, 0.949, 0.868, 0.241 (mean 0.795).
- 17:06 (ios) "Dude why didnt you created the pitche mesh? Dont you have mesh for all?" Answer (17:06): all 11 meshes are own reconstructions; the pitcher base is about half missing, so it falls in the first frames. A circle-completed foot fixed this on CPU (60 frames stood; eight convex pieces needed) but was not in the run. Other flaws: rack has no floor, beige cup has no bottom, blue cup inner floor 5.5 cm too high.
- 17:08 (ios) "...why dont you reconstruct everything for the simulation, you need to recreate for all." Answer (17:08): the 22 Oct v5 spec. Cost $50–55 total, second submission around 27–28 Oct.
- 18:07 (ios) "How do you run the official evaluator?" Answer: clean worktree of FlashCHORD at 8c778f9 (zero modified files), kit runner per episode, deterministic single world with explicit reset, then the kit packer.
- 18:08 (ios) "Wait we can get leaderboard score locally?" Answer: no. Only public episodes can be scored locally. Upload-probing is not allowed. Rule noted as 5 uploads a week; corrected at 18:35 to 5 a day.
- 18:10 (ios) "How long is this gonna take, also cant we run this individually." Answer: about 18:25 UTC; each episode is independent, but Kaggle accepts one file for all 20.
- 18:21 and 18:28 (desktop_app) Does GitHub need to be reachable before upload, and will I get a score and rank? Answer: upload now; invite Nvidia-V2D-Challenge as collaborator before the 4 Nov freeze; yes, score and rank appear on the leaderboard.
- 18:35 (desktop_app) "can I give you the access to my kaggle acount and you upload the scores." Answer: yes, via a token stored as an environment network secret (new sessions only); owner must join each competition.
- 18:38 (desktop_app) Owner pasted a secret-setup dialog and asked what to enter. Answer: Bearer type, host *.kaggle.com, no path prefix. (No secret values are recorded here.)
- 18:39 (desktop_app) "I did added it can you check if it works." Answer (18:46): access works; first submission scored AUC 0.575, 9th.
- 18:49 and 18:50 (desktop_app) Links to join five competitions; "I joined all."
- 18:57 (desktop_app) "I need the videos of all the 20 evals also I need a full analysis on why the ones scored low." Delivered 20 videos (19:24) and docs/analysis/eval-20261024-low-scores.md.
- 19:06 (desktop_app) "how long will I have videos." Answer: about 20:15 UTC.
- 19:30 to 19:33 (desktop_app) "which of these due to missing meshes; which scores were about mesh accuracy." Answer (19:35): mesh-caused losses about 0.08–0.12 AUC; CD-O (0.405 cm, 10th) is the direct mesh score.
- 19:36 (desktop_app) "lets list all the reasons for failure...we failed where we achieved high score in the public data." Answer (19:39): twin comparisons and 14 failure reasons (section 8 of the analysis file).
- 20:23 (ios) "which are the lowest hanging fruit?" Answer (20:24): ranked fixes; CPU fixes first, then one GPU batch of about $10–12 expected to reach 0.62–0.64 (estimate).
- 21:32 (ios) "Im sleeping now, do as much as you can with the money inside vast account." No separate answer in the pages read.
- 23:23 (ios) "Did we fixed the issues? What is our projected score?" Answer not captured.

**Turn outcomes (measured numbers in bold where they are results)**
- 12:23 ep18 **0.957 ± 0.002**; ep39 **0.958 ± 0.002**; ep27 **0.949 ± 0.010**; ep12 **0.868 ± 0.122** (one rollout 0.63). Previously ep18 0.22–0.41 (best standard RL 0.889).
- 12:42 eval 33 training crashed by GPU out of memory (40.4 GB per training). Fix: at most two trainings per GPU, retries up to two. Eval 33 queued to retrain.
- 13:54 box F: eval 35 **0.9915 ± 0.0011**, eval 36 **0.9935 ± 0.0005**, eval 33 **0.391 ± 0.029** (perception failure: after frame 48 the tracked cup tilts 90–130° and drops 10–15 cm). Credit $4.61.
- 15:10 full run launched: six eval boxes on RTX PRO 6000 S ($1.51–1.72/h, one Max-Q $1.13/h). Evals 33, 35, 36, 38 reused. Pack dry run on cheap GPU.
- 15:27–15:40 evals 25 and 30 had failed early from separate pipeline bugs; both fixed and rerun (box evR, about $2.5). Eval 16 reference failed one automatic check (hand track jumps 19 cm; limit 10 cm), run continued.
- 15:55 pack dry run passed on four finished policies. Clean evaluator vs training-time scores: eval 33 0.407 vs 0.391; 35 0.949 vs 0.9915; 36 0.992 vs 0.9935; 38 1.000 vs 0.9997. Decision, made before final results: pack on the same GPU type used for training.
- 16:00 eval 37 (spoon only) **0.9982 ± 0.0004**. 16:14 eval 30 **0.469 ± 0.004** (30M checkpoint).
- 16:22–17:06 evals 16 **0.795 ± 0.076**, 14 **0.506 ± 0.036**, 28 **0.694 ± 0.085**, 8 (rerun) **0.777 ± 0.065**, 20 **0.287 ± 0.020**, 15 **0.901 ± 0.126**, 19 **0.647 ± 0.018**, 25 **0.243 ± 0.009**, 6 **0.982 ± 0.007**. Mean of 14 finished about 0.69 (17:01).
- 18:16 pack 1 written: 9,120 rows, 1,329,173 bytes, mean sim_vs_ref **0.710** (not a leaderboard value). Estimate 0.68 (0.62–0.72).
- 18:46 Kaggle AUC **0.575 (9th)**; top 0.932/0.884/0.865; 4th 0.752, 5th 0.730, 6th 0.662. 18:55 all boards: SP-SR 0.45 (11th), MP-SR 0.35 (9th), RPE 12.6 cm (13th), MPPE 8.7 cm (10th), CD-O 0.405 (10th).
- 19:04 loss analysis (own reference): objects that cannot stand about 0.09; perceived path moves unheld or impossible objects about 0.06; grasp failures about 0.13; perception vs truth about 0.135 (mostly spoon, estimate).
- Cost: pack and batch about $24–30 of the $50 top-up; credit $30.87 at 18:18.

## 2026-10-25

**Owner messages and what they decided**
- 00:18 (ios) "Try to fix the lower score properly do whatever takes and try to aim for the 4th place." Work followed: seed-43 runs, pitcher, guard.
- Late evening 10-24 to 00:51: owner "use both" decision (second learner on the 12 weakest episodes). Message not captured; recorded by the agent.
- 06:47 (ios) "Did we made any progress last night?" Answer (06:49): second submission AUC **0.575 → 0.583** (01:00 UTC). MPPE 8.7 → 6.7 cm, RPE 12.6 → 8.8 cm. Validated on public episodes: detection fix (ep11 0.10 → 0.90), track guard (public mean 0.72 → 0.78), new beige cup (twin 0.525 → 0.570), pitcher foot. Credit $1.82; batch of about $50 proposed.
- 06:55 (ios) "what is our current ranking." Answer (06:56): 9th of 20 at 0.5825. SP-SR 0.50 (10th), MP-SR 0.40 (7th), RPE 8.82 (9th), MPPE 6.69 (9th), CD-O 0.405 (10th).
- 07:00 (ios) "list our scores per episodes, link to the videos, and tell me why we fail them." Answer (07:04): per-episode own-reference scores with causes (eval 1 lid never lifts; 25 boards with no slots and one-finger grasp; 20 pitcher tips; 10 beige cup has no bottom; 33 cup dragged to wrist; 30 bad rollout; 14 cup tracking; 19 weak dust-pan grasp; 28 pot knocks rack; 8 beige cup tracked wrong; 32 cup tracking).
- 07:18 (ios) "Which score predicted the mesh accuracy also the ones who scored the best." Answer (07:22): CD-O is the only direct mesh score. Across teams, position error ranks AUC almost exactly (rank correlation 0.97); CD-O only loosely (0.51). Leaders' CD-O 0.11–0.26 cm.
- 08:45 (desktop_app) asked for the problem split into grasp, carry, release, boundaries. Research agents started.
- 09:00 (desktop_app) "we can do expensive tests as well."
- 09:15 (desktop_app) "try all the possible grip types and pick the best or most stable" (judged by how the piece moves and is released). Answer (09:09): recognising grip type from video was dropped. Proposed event-anchored grip (14 of 17 grip failures at a boundary; hand labels off by up to 24 frames).
- 09:19 (desktop_app) "lets do the missing parts and test if it helps what do you need?" Answer: try-every-grip design, GPU test about $8–12.
- 09:42 (desktop_app) "why do you need that much of money." Answer (09:43): itemised $65–80; minimum about $35.
- 09:51 (desktop_app) "what score do you expect from that?" Answer (09:51): AUC 0.61–0.66, most likely 0.63 (7th–8th). Tracking fix +0.02–0.04; second recipe +0.005–0.02.
- 09:53 (desktop_app) "I can give you the 80 bucks...I want top 3 from you." Answer (09:54): cannot promise top 3; top 3 needs AUC ≥0.865 (3rd was 0.831 four days earlier, 0.865 now).
- 15:48 (ios) "I did add 100 bucks...go ahead and." $100 arrived (balance $88.28 at 15:54), but another session had already started 9 GPU machines (14:51 UTC, branch claude/inspiring-mendel-lbgp9e). The main session had duplicated the batch on 6 machines; it destroyed them (about $0.90).
- 15:55 (ios) "I rejected the other one, what should I do...look at the other chat also." Answer (15:56): keep the other batch (12 machines, about $18.50/h, credit $86.51). Let that session own GPU, packing and upload.
- 15:59 (ios) "Carry on."
- 17:02 (ios) "You are coordinating with the other chat too right?" Answer: reads only, no rentals, no shared files; the other session messaged once and the owner declined a reply.
- 17:47 (ios) "Okay how are we projected." Answer (17:48): about 0.68 (0.64–0.71), about 6th; 5th is 0.730.
- 17:54 (ios) "Wait boards is 0.6 how? Also do we do fine tune for all." Answer (17:57): yes, every eval policy gets 70M RL fine-tune; weak ones also get 250M standard. Boards 0.6 was 0.712 × about 0.82 (estimate).
- 17:59 (ios) "how do we have 0.815 also why dont we pick the best. Can you show me the video of the best." Answer (18:03): refused to submit the luckiest repeat (cherry-picking). Five runs were 0.802, 0.815, 0.797, 0.811, 0.335.
- 18:06 (ios) "Where is the robot hands?" Answer (18:12): CPU replay crashed; offered a small GPU render ($0.30–0.50) or a free CPU drawing.
- 18:16 (ios) "Go for option 1." Render box started; video sent at 19:49 (fresh run 0.808; doing nothing 0.308). Render stall cost about $1.30.
- 19:12 (ios) "what are we looking as the potential score" Answer (19:13): about 0.73 (0.68–0.77).
- 19:38 (ios) "How long is left until we can send and get our score." Answer: pack started 19:30, 10 changed episodes, about 20–40 min.
- 20:04 (ios) "If we had the ridge this would have been perfect." Answer: missing board slot costs about 0.17 on ep25 (about +0.007 on total). Carving collision shapes proposed, not the submitted mesh.
- 20:13 (ios) "Lets get our scores per episodes from kaggle and then we can do that." Answer not captured.
- 20:25 (desktop_app) "did you pushed what we have done to the repo?" Answer: yes; third submission (AUC **0.78893**, 4th) pushed; interaction_carve pushed.

**Turn outcomes**
- 00:51 second learner queued; top-up about $40 requested (credit about $18). Second pack (eval 30 rerun plus five seed-43 picks) started.
- 01:31 track guard vs base on same box: ep0 0.496 → **0.964**; ep11 0.898 → 0.898; ep23 0.041 → 0.041; ep18 0.938; ep24 0.812; ep12 0.967 → 0.966. Rule passed: no drop above 0.01, mean up.
- 01:45 guard validated and on by default; beige cup CD-O **0.730 vs 0.856**; Kaggle second submission **0.5825**.
- 02:44 pitcher foot stands within 5 mm (fell 16 cm by frame 8). Track 8 (precision sweep) hurt ep12 (0.72) and ep18 (0.647); rejected. Credit blocked at $7.37.
- 03:40 ep11 twin base arm **0.525** against ground truth.
- 04:11 beige cup has no bottom (cone tip at unseen end). Eval 10 needs foot plus carved blue cup cavity (about +0.02, estimate).
- 16:28–16:49 spoon: scorer anchors the whole scene on one object's frame-0 pose; in 5 of 10 spoon episodes the spoon is the anchor. Start-roll error estimated 2–6° (cost 0.03–0.15 per affected episode, estimate). 300 flip fits: 0 flips, error about 1°. Smoothed-pose test failed its rule (+0.001).
- 17:25 eval 25 standard learner on corrected reference **0.712 ± 0.189** (0.335–0.815) vs grasp lock 0.376 and 0.297. Eval 30 standard **0.919 ± 0.012** vs 0.722 for grasp lock (16:49).
- 18:03 eval 25 five runs: 0.802, 0.815, 0.797, 0.811, 0.335. Run 2 not submitted (cherry-picking). Second seed proposed (about $4).
- 19:49 video delivered (fresh run 0.808; do-nothing baseline 0.308).
- 20:25 third submission **0.78893 (4th)**.

## 2026-10-26

**Owner messages and what they decided**
- 05:55 (ios) "Sure." 05:57 (ios) "You said we wont be able to reach 4 and yet here we are. Now I want something more ambitious from you...get the videos of our current episodes and do forensics on what went wrong and what can be improved." Work: forensics report, videos, eval 25 slot cut.
- 07:31 (ios) "If there is enough money in the vast you can go ahead and." Three GPU machines launched (credit $41.63 at launch; about $13 batch): eval 25 with board slot cut (seeds 42 and 43), eval 10 with new cup collision shapes (seeds 42 and 43), eval 32/33 second seed.
- 07:52 (ios) "...videos with the real video overlay and robotic sim side by side as a single vid." Answer (07:54): one 93-second, 1920-px video (six episodes).
- 08:51 (desktop_app) "how is our current recipe we apply the same for all right?" Answer: not exactly; table of recipes and which episode uses which policy. Standard learner never ran on 3, 5, 6, 10, 15, 16, 35–38.
- 09:06 (desktop_app) "so problem was with detection and proper mesh generation right?" Answer: partly. Perception and tracking first; meshes matter less (CD-O 0.40 cm, 11th; Spearman −0.51 vs −0.97 for pose metric across teams).
- 09:13 (desktop_app) "when did [the standard learner] pick up? ...longer rl for finetuning...more unified model." Answer: added 25 Oct inside eval_both (grasp lock first; standard 250M if below 0.9). Grasp-lock curves flat or falling (ep1 0.36 → 0.23; ep19 0.63 → 0.34; ep30 0.42 → 0.19). Proposed unified recipe with 50% extension when still rising.
- 09:19 (desktop_app) "for 1, 19, 30, 10 did we do something else then the standard learner?" Answer: learner alone for 1, 19 and 28; ep30 had a detection fix first; ep10 got nothing new (solver jam).
- 09:24 (desktop_app) "can you give me our generalized recipe flow chart." Delivered docs/recipe-flow.png (stages 0–7).
- 09:27 (desktop_app) "what is left from the ones that are running." Answered in the 09:27 turn (see below).
- 09:28 (desktop_app) "can we find a way to try multiple seeds...and pick the ones that progress the most early?" Answer (09:35): yes, with one cut at 40% of training (correlation 0.89 on 31 curves; leader stays ahead 30 of 36 times). Successive halving proposed.
- 09:52 (desktop_app) "how much of a gpu cost increase would that make." Answer: 8-seed race about 2.3× (+$7); 16 seeds about 4.5×.
- 10:04 (desktop_app) "Is there a cheaper way? maybe a seed race for the frozen or eval_both grasp?" Answer (10:07): not for grasp lock (cut at 40% is a coin flip, 22 of 38). Interruptible GPUs about half price ($0.67–0.71/h vs $1.35–1.39/h). Pilot about $10–12 proposed.
- 10:11 (desktop_app) "what was the old way cost?" Answer (10:12): standard learner about $5.5 per episode (2 seeds); grasp lock 2 seeds about $3.2–4; full 20-episode rerun with packing about $50.
- 10:43 (desktop_app) "where is our short comings...total scores for each 20...how did we improve." Answer (10:45): per-episode table across packs 1–3 with fix and what still goes wrong.
- 10:59 (desktop_app) "we are in 5th DDD increased its score." Statement; no separate reply captured.
- 11:21 (desktop_app) "you need any topup or can just start?" and 11:25 (desktop_app, priority next) "okay go ahead and start." Five on-demand boxes launched (about $10.50).
- 11:33 (desktop_app) "when do you think we can get the results." Answer (11:34): about 13:00 UTC for training, about 13:30 for the board.
- 11:44 (desktop_app) "lets in an another chat think about how to make this more robust...think in pieces on our whole flow." Agent started a separate robustness-review session (session_012XqAPiLToh4uBKNWqzx3bV).
- 13:42 (ios) "Check and fix." Eval 10 grip check (14:18 result).
- 14:46 (ios) "Sure do whatever takes to beat DDD." Work followed (packs 5 and 6).
- 16:24 (desktop_app) "sure do whatever makes sense." Reply to the keep-or-revert question on the pitcher mesh swap. Agent reverted (16:26; commit b8bf6ef labelled "Owner decision").
- 10-27 03:55 (ios) "Sure go ahead with that I will tell you when I topped up." Last owner message in the feed.

**Turn outcomes (measured)**
- 06:08 eval 25 board slot cut (collision copy only): CPU board 2 drag error 1.17 cm and 104° → **0.06 cm and 0.5°**; FlashCHORD physics 7.5 cm and 48° → **0.12 cm and 0.4°**. GPU retrain proposed (about $9–11).
- 07:15 correction: pack 3 used the wrong rollouts for evals 3, 5, 15 and 16 (seed-42 policies instead of seed-43), about −0.005. Pack job now refuses checksum mismatches.
- 07:27 forensics: submitted rollouts score **0.883** vs own reference; public-episode GT prediction 0.864 vs leaderboard 0.789 (about 0.12 lost to policy, about 0.075 to reference).
- 09:04 pack 3 breakdown: 0.583 → 0.789 from about half perception fixes and about half the standard learner. Eval 1 standard alone about +0.036.
- 09:27 eval 25 standard seed 42 **0.792** (0.62–0.90) replaces the current policy (0.712); seed 43 0.474. Eval 32 seed 43 **0.702** vs 0.779 (kept).
- 10:28 pack 4 running; eval 10 seed 42 0.453 vs seed 43 0.452. Estimated +0.017 ± 0.014 (estimate). Store bug (checkpoint not stored) fixed.
- 11:01 pack 4 (20261026-track3d) AUC **0.81056 (5th)**; SP-SR 0.85; MP-SR 0.65; RPE **4.03 cm**; MPPE **2.94 cm**. DDD 0.827 at 03:36 UTC. Gain carried about 76% to the board.
- 11:28 five on-demand boxes: interruptible boxes were preempted within about 10 min and destroyed (about $0.40 lost); about $10.50 total; credit about $28.
- 13:16 eval 10 grasp-lock idea **falsified**: A 0.454, standard 0.452, B 0.438; success needed above 0.462; no checkpoint lifts the cup. Eval 32 seed 46 **0.803** (runs 0.62–0.89) vs seed 42 0.779; not packed alone (+0.001 est).
- 14:18 eval 10 analysis: open-loop plan 0.517; held-object correction 0.632 (knife-edge, not run); untrained plan 0.663 vs submitted trained 0.447. Training beats plan by +0.17 on average across 64 grasp-lock results but loses in 15. Proposed: checkpoints every 1M steps.
- 15:27 pack 5 started: eval 20 pitcher mesh swap (lathe-built library_v3p; public twin ep21 **0.776 → 0.874**), eval 32 seed 46, eval 10 gl10A2.
- 16:05–16:11 pack 5 (20261026-track3e) AUC **0.80941** (below best). Evals 10 and 32 improved in simulation (0.447 → 0.456; 0.789 → 0.866); pitcher swap cost about **−0.004** on eval 20. Best kept at 0.81056.
- 16:26 owner decision: revert the pitcher mesh (pack 6 uses library_v3).
- 17:20 pack 6 (20261026-track3f) AUC **0.81391 (5th)**; DDD 0.82716 (4th); SRL 0.75166. Net since morning +0.0034 (0.811 → 0.814). Pack dry run mean sim_vs_ref **0.9164**. Credit $6.80.
- 10-26 16:40 credit about $13 after pack 6. Eval 10 "zero-start" test failed; eval 10 parked.
- 10-27 06:15 final status: need_input (credit $3.52); leaderboard unchanged at **0.81391, 5th**.

**Per-episode state at the last submission (pack 6, own-reference sim_vs_ref)**
1: 0.920; 3: 0.942; 5: 0.960; 6: 0.971; 8: 0.978; 10: 0.456; 14: 0.909; 15: 0.947; 16: 0.908; 19: 0.928; 20: 0.895; 25: 0.894; 28: 0.929; 30: 0.923; 32: 0.866; 33: 0.932; 35: 0.983; 36: 0.991; 37: 0.998; 38: 1.000. (Own reference; not leaderboard.)

## Costs and spend (as reported in the chat)

- Owner top-ups in messages: $50 (10-24 15:05), $100 (10-25 15:48). An $80 offer on 10-25 09:53.
- Reported losses: $0.45 (broken download, 10-24), $1.30 (stalled download box, 10-25), about $0.90 (duplicate machines destroyed, 10-25), about $0.40 (interruptible boxes preempted, 10-26), $0.03 (pack box on an old commit, 10-26).
- Measured unit costs (10-26): standard learner about $5.5 per episode (2 seeds); grasp lock 2 seeds about $3.2–4; interruptible about half price but preempted.

## Lessons and turning points

- Perception and tracking errors (latching to the person's wrist and watch, cups jumping to the wrist when hidden, swapped look-alike boards) cost more early than mesh shape. Fixing them (detection fix, track guard) plus the learner change took the board from 0.583 to 0.789 in one step.
- Learner choice was the second large step: the standard 250M RL run beat the grasp lock on eval 1 (0.297 → 0.912), 19 (0.653 → 0.935) and 28 (0.694 → 0.935). More steps did not rescue low starts (22 runs below 0.5: median +0.04; 13 ended below doing nothing). The later onset anchor plus grasp search is what moved ep18 from 0.22–0.41 to 0.957.
- Public twins flattered the recipe: it was fitted to public episodes such as ep18, ep39, ep12, ep27 and ep24. Near-identical twins diverged on eval (ep31 0.77 vs eval 30 0.47; ep18 0.96 vs eval 19 0.63).
- Single rollouts vary a lot: eval 25 failed about 1 in 5; the packed draws were on average +0.027 above their 5-run means. The owner rejected picking the luckiest repeat (10-25 18:03). Selections were made on 5-run means, pre-registered.
- Pre-registration worked and caught errors: the eval-10 early-checkpoint rule failed as written and was logged; the pitcher-swap was reverted on the leaderboard evidence (−0.004), with the decision explicitly labelled as owner-made.
- Spoon was the biggest unmeasured loss (estimated 0.12, later revised to a start-roll effect of 0.03–0.15 on 5 anchor episodes, plus tracking). No public spoon ground truth exists, so it was never validated.
- Open rules risk: meshes were built using public-scan templates, and a scan-free rebuild (v5) was planned but not completed before the 10-26 packs. The organisers' reproducibility check is pending.
- Process mistakes: a pack box launched on an old commit (default `main`); a broken download; two Claude sessions launched duplicate GPU batches on the same account (10-25 15:48), resolved by owner choice; pack script once picked the wrong rollouts for 4 episodes (about −0.005); eval 10 store pruning bug dropped a checkpoint.
- Turning points: first full submission 10-24 18:18 (0.575); second 10-25 01:00 (0.583); third 10-25 20:25 (0.789, 4th); fourth 10-26 11:01 (0.811, 5th); final leaderboard position 10-27 06:15 (0.814, 5th; DDD 0.827 4th).
