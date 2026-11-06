# Digest: project reports, part 1

43 reports from the V2D Track 3 repository, dated roughly 2026-10-18 to 2026-11-03. Labels follow the sources: [M] measured, [E] estimate, [D] public-twin diagnostic against mocap, [H] hypothesis, [I] inference. "sim_vs_ref" is the rollout scored against our own reference, not against ground truth.

### README.md
- **Date:** undated (repo state around 2026-11-03; freeze 2026-11-04 17:00 EST).
- **Purpose:** entry point and layout of the repository.
- **Key facts:** perc2 is the validated perception stage (mean AUC 0.809 on 20 public episodes). perc4 is built but not validated. Evaluator pin 8c778f9.
- **Verdict:** orientation document, no result.

### docs/analysis/arda-feedback-20261031.md
- **Date:** 31 Oct 2026.
- **Purpose:** analyse a professor's feedback on the Learner Notebook: rollout variance, the claim that training lacks domain randomisation, frame-by-frame failure location, and the two-part view.
- **Method:** repository and branch check, no runs.
- **Results:** 10-draw sd per eval (sim_vs_ref): eval 30 0.255 (sweeper inside rack mesh); eval 1 0.239, cured by a geometry carve to 0.924 ± 0.017 over 20 draws; eval 14 0.199; eval 33 0.137, cured by CURR_SCALE 0.4 to 0.934 ± 0.008; evals 25/16/3/32 at 0.099/0.077/0.072/0.068. Policy loss 0.083 [M]; reference loss ≈0.10 [E].
- **Verdict:** domain randomisation is open [H-DR]. Falsifier: 10-draw sd falls by ≥40% on 2 of 3 contact-sensitive episodes, or mean falls by >0.02. A CPU control costs $0; a GPU check ≈ $1.5–2 [E].
- **Lessons:** overlapping collision shapes drive the largest spreads; geometry and shorter curricula are the measured cures.

### docs/analysis/drawdiv-20261031/README.md
- **Date:** 31 Oct; masses check 1 Nov 2026.
- **Purpose:** find where draws of one checkpoint part ways.
- **Method:** CPU, $0. Ten official draws per arm on public episodes (ep11/13/31 oracle twins; ep2 masses check, 2 seeds × 10 draws). Failure onset: object >3 cm off for ≥8 frames.
- **Results:** ep11 P draws fail identically (sd 0.003). ep31 P 0.758 ± 0.019; ep31 O 0.883 ± 0.045. Draws split by 2 cm at the same event in nearly every pair. Ep2 masses: mass0 s42 0.559 ± 0.349, mass1 s42 0.648 ± 0.358, mass1 s43 0.813 ± 0.307. Ep2 rest-projection pose fix falsified (ΔAUC −0.0107; 17/20 worse).
- **Verdict:** failures cluster at contact events. Variance appears only where a policy is marginal. The estimated-mass arm was not adopted (ep12 −0.013).
- **Lessons:** targeted event fixes look more promising than global noise [I], with n=3 twins.

### docs/analysis/episode-scoreboard-20261026.md
- **Date:** 26 Oct 2026.
- **Purpose:** per-episode table for the owner.
- **Method:** packs 1–4 with sim_vs_ref per eval; Kaggle reports totals only.
- **Results:** AUC 0.575 (9th), 0.583 (9th), 0.789 (4th). Own means 0.710 → 0.722 → 0.883. Estimated losses: reference vs truth ≈0.075 [E]; policies not following reference ≈0.115 [E]; single-draw swings of 0.2–0.6 on evals 14, 25, 33. Eval 10 was the largest loss (0.34).
- **Verdict:** informs priorities; loss splits are estimates.
- **Lessons:** sim_vs_ref cannot see reference-vs-truth error.

### docs/analysis/ev10-stack-20261026/README.md
- **Date:** 26 Oct 2026.
- **Purpose:** why no learner stacks the cups in eval 10; test the owner's "8 mm collision shrink" hypothesis.
- **Method:** CPU zero-action replays, GT-free, qa.py metric.
- **Results:** hypothesis rejected (planner already uses the shrunk surface, 1.3 mm gap). Trained policies move neither cup (0.4 cm total). Zero-action replay 0.579 (A) and 0.663 (B) vs trained 0.454 and 0.438. Best variant 0.632, but ±3–6 mm wrist jitter gives 0.42–0.54 (mean ≈0.48). Across 64 stored results, training beats zero action by +0.175 on average.
- **Verdict:** no GPU rerun ("knife-edge"). A zero-residual submission is an owner decision, against the 22 Oct rule that submissions be learned policies.
- **Lessons:** a gain that vanishes under 3–6 mm perturbation is not evidence.

### docs/analysis/eval-20261024-low-scores.md
- **Date:** 24–26 Oct 2026.
- **Purpose:** why the low eval episodes scored low on the 24 Oct submission (AUC 0.575, MPPE 8.7 cm, CD-O 0.405 cm).
- **Method:** 20 packed rollouts, per-object diagnostics, 20 rendered videos.
- **Results:** packed rollouts average 0.710; reference-vs-truth takes this to 0.575. Causes: mesh (≈0.08), perception (≈0.09), grasps (≈0.11), reference vs truth (≈0.135). Eval 1 0.205: lid mesh starts 7.6 mm inside pot, 8% of lid surface points inside. Eval 25 0.232: board meshes have no slots, so the cross cannot assemble. Eval 20 0.336: pitcher is a twisted shell. Eval 10 0.342: open-shell beige cup.
- **Verdict:** mesh rebuilds and rest-on-rim fixes queued.
- **Lessons:** mesh validity and object identity are first-order; watch the videos.

### docs/analysis/evalaudit-20261031/README.md
- **Date:** 31 Oct 2026.
- **Purpose:** GT-free audit of packs 7 and 8, each rollout against our own reference.
- **Method:** kit metric functions; no ground truth read.
- **Results:** one failure in 20: eval 10 beige cup left behind (sim travel 0.7 cm vs reference 25.1 cm; RPE 15.76 cm, MPPE 8.54, AUC 0.458); H5 gave 0.4495 ± 0.007 over 10 draws. Board pack 7, GT-free: RPE 2.450 vs board 3.932; MPPE 1.561 vs 2.921; AUC 0.911 vs 0.8146. Eval 10 adds 0.79 cm to 20-episode RPE. About 1.5 cm of board RPE is not reference deviation [E].
- **Verdict:** eval 10 is the one actionable failure; the remainder is unexplained by this audit.
- **Lessons:** one unbounded failure dominates RPE.

### docs/analysis/evalgross-20261031/README.md
- **Date:** 31 Oct 2026.
- **Purpose:** screen the 36 pack-7 eval reference objects for gross errors (>5 cm or >20° persistent).
- **Method:** CPU; flags pre-registered in PREREG.md before any eval indicator was computed.
- **Results:** no persistent gross error in any object. Transient errors of 10–45 frames, all during hand-held phases: eval 32 cup watch latch (19.7 cm step at f21); eval 14 cup lag (f35–45); eval 33 cup hidden f46–90. Board impact ≈0.15–0.2 cm of RPE, about 10–15% of the ≈1.5 cm gap [E].
- **Verdict:** H-gross weakened. Fix ideas (cup latch guard, depth-checked settle) are untested, each ≤0.05–0.1 cm [E].
- **Lessons:** gross-error indicators miss cm-level bias, the likelier residual.

### docs/analysis/forensics-20261026/README.md
- **Date:** 26 Oct 2026.
- **Purpose:** forensics of the third submission (leaderboard AUC 0.789, 4th).
- **Method:** the 20 official pack-3 rollouts; videos with robot hands; CPU hull census.
- **Results:** sim_vs_ref 0.883; policy loss 0.117 [M]; reference/anchor/mesh loss ≈0.075 [derived]. Largest policy losses: eval 10 (0.344; beige cup open shell, 112 cm³ stacked-cup overlap); eval 33 (0.602; two-handed hold); eval 32 (0.809). Pitcher on public twin ep21: reference 0.775 vs mocap; pitcher mesh 0.571 with our mesh vs 0.95 with the scan.
- **Verdict:** collision geometry and holds identified as causes; replay 0.529 for eval 1 is far below its official 0.89–0.93 (replay path differs).
- **Lessons:** collision-copy errors, not only the policy, cost score; replays can mislead.

### docs/analysis/hand-aware-20261103/README.md
- **Date:** 3 Nov 2026.
- **Purpose:** test a hand-masked ray correction (HRC, config F1) on held objects.
- **Method:** pre-registered, public only, 13-episode holdout, 10 seeds; gate ΔAUC ≥ +0.005 and ≥ 2× noise (noise 0.0015). $0.
- **Results:** whole-episode ΔAUC −0.0042; worst ep24 −0.0466 (board 2 pushed ≈21 cm). Held mean ADD 1.893 → 1.812 cm (−4.3%, gate 10%). Dev +0.0045 over 7 episodes. Rigid-in-grasp with MediaPipe hands: −0.12 to −0.79 per episode. 70% of public AUC loss lies in held frames.
- **Verdict:** FAILS every holdout gate; nothing to eval.
- **Lessons:** do not use hands as pose source; depth-residual ray corrections break on thin or flat objects.

### docs/analysis/ipose-20261103/README.md
- **Date:** 3 Nov 2026 (box run, RTX 4090 at $0.556/h, ≈1.4 h, ≈$0.8 [E]).
- **Purpose:** an instance-level pot pose network against our tracker.
- **Method:** pre-registered; train eps 0, 26, 41–43; test 2, 27, 44, 45; 10 seeds.
- **Results:** R (rendered only) mean pot ΔAUC −0.065, ep27 −0.257. R+M (uses mocap labels, GT-informed) −0.0085, ep27 −0.035. Control AUCs 0.9935 / 0.9677 / 0.9979 / 0.9742.
- **Verdict:** FAILS both arms; rendered-only spoon network judged not trustworthy.
- **Lessons:** a render-to-real gap can break a per-frame method on the hardest phase.

### docs/analysis/lowvid-20261101/README.md
- **Date:** 1 Nov 2026.
- **Purpose:** videos of the lowest eval episodes (report only).
- **Method:** H5p7 fresh-draw means; CPU renders with collision geometry; robot-hand GPU videos ($0.70).
- **Results:** means: 14 0.727, 16 0.850, 32 0.852, 25 0.878, 20 0.893, 30 0.897. Eval 14 failure onset f42–45 in 7/10 draws (hand-over); cup thrown 63–162 cm in 3 draws. Static racks sit 0.2–0.6 cm low in sim (40–48% constant offset).
- **Verdict:** informs the single-hand lock for eval 14.
- **Lessons:** constant offsets matter for static objects, tracking error for moving ones.

### docs/analysis/markers-20261031/README.md
- **Date:** 31 Oct 2026.
- **Purpose:** GT-free marker correction layer (spoon first).
- **Method:** pre-registered gate on 16 public units; CPU, $0.
- **Results:** mean ΔAUC −0.083, 1/16 improved, worst −0.407; every variant fails. Marker fixes 1.0–2.2 cm vs tracker 0.26–0.42 cm on the pot. Eval spoon: ≥2 markers in 34–73% of frames, ≥3 in 2–18%. Eval 16 shift would put the spoon 19.7 mm below the table. Hypothesis: rack markers (153.5 mm apart) match the spoon's 154.3 mm.
- **Verdict:** FAILS; not adopted; markers kept only as part of the spoon template.
- **Lessons:** a second sensor must beat the tracker; check look-alike marker distances.

### docs/analysis/meshswap-20261026/README.md
- **Date:** 26 Oct 2026.
- **Purpose:** swap one submitted mesh at a time for alternatives, re-scored with the registered scorer.
- **Method:** public rollouts on eps 2, 11, 12, 21, 27; 3 rollouts each.
- **Results:** pitcher lathe variant +0.098 episode AUC (ep21); appendage-only +0.163 but scores above the scan (0.940 vs 0.907). Blue cup and beige cup lathe swaps −0.044 to +0.023; pot lathe swap ≈0; pot appendage-only −0.175 and −0.463.
- **Verdict:** switch eval 20 pitcher to the lathe; expected ≈ +0.005 board AUC [E]. The appendage-only mesh rejected.
- **Lessons:** a mesh that beats the true shape is compensating for errors, not improving registration.

### docs/analysis/nvidia-default-timing-20261030/README.md
- **Date:** 30 Oct 2026.
- **Purpose:** how far ahead of NVIDIA's method we are.
- **Method:** NVIDIA's default timing (motion_speed 0.5) with perfect perception and robot, scored on 20 public episodes; CPU, $0.
- **Results:** AUC 0.415, SP-SR 0.30, MP-SR 0.00, MPPE 9.5 cm. "Nothing moves" floor: 0.446 / 0.45 / 0.00 / 9.3 cm (matches the 12 Oct log). No Track 3 baseline is posted.
- **Verdict:** the shipped chain is capped below the floor (a ceiling for unmodified defaults). A real comparison needs a GPU run, ≈$15–20 for 7 single-object episodes or ≈$60–70 for all 20 [E]; not run.
- **Lessons:** check default timing against floors.

### docs/analysis/overnight-20261101/README.md
- **Date:** night of 31 Oct → 1 Nov 2026; spend ≈$56 [E].
- **Purpose:** collect results of four lanes.
- **Method:** proxy = sim_vs_ref over 10 official draws.
- **Results:** uploads: 9a+ AUC 0.81757 (SP-SR 0.85); 9b 0.81677; pack 10 0.81915 (RPE 3.68275, MPPE 2.84759). Eval 10 at njmax 1024: proxy 0.913 vs 0.459 (stock 512: 0.903). Cavity-safe pieces ev10cs5: 0.532 vs 0.463 (+0.069), in pack 10 (+0.0016 board AUC). D arm (start randomisation): only eval 33 passed. Masses v2: mean +0.0034, not adopted. Zero-lag RTS on tracks: kit gate −0.00011, FAIL. Arm V: −0.024.
- **Verdict:** adopted only the eval 10 cavity-safe pieces.
- **Lessons:** a swap needs proxy gain ≥ +0.02 from pack 10 on; the biggest wins came from the physical failure cause; robot-side tweaks were negative or inconclusive.

### docs/analysis/overnight-20261102/README.md
- **Date:** 2–3 Nov 2026 (written 03:20 UTC).
- **Purpose:** morning report on the night's uploads.
- **Method:** pre-registered public-evidence selections (GT-informed where disclosed); two-host confirmation.
- **Results:** rank sum 58 (10th) → 46 (7th). Boards: AUC 0.84738 → 0.88571 (pack 14p); SP-SR 0.85 → 0.90; MP-SR 0.75 → 0.80; RPE 3.008 → 2.213; MPPE 2.467 → 1.798; CD-O 0.300 → 0.2516 (pack 13h). Passed: pot and rack pose-mesh CV (+0.021, +0.023), board AUC +0.010. Failed: mesh placement from depth for all objects (+0.0026), tracking with new meshes (−0.043). Spend ≈$45 overnight.
- **Verdict:** final selection 14p for five boards, 13h for CD-O.
- **Lessons:** the registered scorer makes mesh placement drive pose boards; choose by public pose evidence, not scan CD-O; confirm on two hosts.

### docs/analysis/perfect-following-20261101/README.md
- **Date:** 1 Nov 2026.
- **Purpose:** CPU preflight and H5p7 error timelines (no ground truth).
- **Method:** 200 draws (10 per eval); symmetric and plain sim_vs_ref.
- **Results:** symmetric minus plain ≤ +0.009 everywhere, so cup spin is not where losses occur. Onsets are deterministic in many evals: 14 (cup, f42–46, 9/10), 16 (spoon, f112–120, 10/10), 32 (cup, f19, 10/10). Hold-rigidity: relative spread 2–28 cm, even on near-perfect evals.
- **Verdict:** losses are at specific frames, so they are reference problems, not draw variance.
- **Lessons:** fix the reference events the policy cannot follow.

### docs/analysis/physperc-20261101/README.md
- **Date:** 1 Nov 2026.
- **Purpose:** physics as a second sensor for perception, public episodes.
- **Method:** pre-registered gate: mean ΔAUC ≥ +0.003, no episode < −0.010, MPPE and RPE not worse. CPU, $0.
- **Results:** best stack F1P1 +0.00298 (14 better, 0 worse), bootstrap CI [+0.0008, +0.0059]; missed the mean clause by 0.00002. Tilt oracle +0.0164 (pitcher ep21 +0.135, ep22 +0.098). Constant-offset diagnostic +0.030. Board value ≈ +0.002 [E].
- **Verdict:** no test passed; not handed on as a pass.
- **Lessons:** a near-miss under a strict gate is still a fail; physics is a weak sensor on these meshes.

### docs/analysis/ptrk-20261102/README.md
- **Date:** 2 Nov 2026.
- **Purpose:** GT-free changes that bring perceived trajectories closer to mocap.
- **Method:** pre-registered; 20 public episodes; control noise: two identical runs differ by mean |ΔAUC| 0.0012.
- **Results:** mask-guided tracking −0.0009 (FAIL); full-resolution stereo −0.0079; lathe pitcher template −0.249; SAM-6D-style scores +0.0010 (below the +0.005 bar); Stage 1 rest fit −0.0088. Findings: the half-frame advance (S2) is in no packed eval reference (+0.006 public, ≈+0.004 board [E]). Ep23 was a wiring gap: identity_fix moves 0.041 → 0.663. Spend ≈$25–26 [E].
- **Verdict:** all tracker changes failed; S2 and identity_fix handed on.
- **Lessons:** single-episode gains are weak evidence; wire fixes into the default pipeline.

### docs/analysis/robot-side-20261031/README.md
- **Date:** 31 Oct 2026.
- **Purpose:** jitter in robot targets and finger synergies.
- **Method:** training plans of public ep2/12/18/24; CPU, $0.
- **Results:** commanded wrist acceleration 2.0–11.7 m/s² raw, 2–5× the smoothed value. Synergy PCA of solver edits: 3 / 6 / 10 components for 80 / 90 / 95%. Zero-lag smoothing of the robot targets: +0.002 to +0.014 on grasp-lock plans, −0.027 to +0.014 on solved plans, against a required +0.03.
- **Verdict:** command smoothing falsified; synergy sampling not run (parked).
- **Lessons:** smoothing can undo the solver's tuning.

### docs/analysis/robustness-review-20261026.md
- **Date:** 26 Oct 2026; corrections 27 Oct.
- **Purpose:** loss budget of the whole flow.
- **Method:** pack-4 summary and public mocap checks.
- **Results:** pack 4 AUC 0.8106, loss 0.189: policy 0.088; reference ≈0.10 [E]; draw luck +0.027 in our favour (14 +0.25, 33 +0.15, 25 +0.10). Mesh damage test: clean 0.987, convex hull 0.947, bottom missing 0.904, 3 mm noise 0.825, 5 mm thicker 0.608. Corrections on 27 Oct: frame-0 alignment and registration are lotteries (sweeper flips on 3–4 of 24 stand-ins); spoon accuracy 0.73–0.76, not 0.80.
- **Verdict:** a registration-stability gate on every submitted mesh is the top item.
- **Lessons:** hand-applied fixes do not generalise to held-out episodes.

### docs/analysis/roman-cs-20261101/README.md
- **Date:** 1 Nov 2026.
- **Purpose:** check a compressed-sensing proposal with synthetic signals.
- **Method:** script on public `capture_time` values; $0.
- **Results:** resampling cannot separate aliases (a 13 Hz sine fits 7, 13, 27 and 33 Hz equally). `capture_time` steps: mean 50.0 ms, sd 1.0–4.3 ms per episode, lag-1 correlation ≈ −0.5. A 63 Hz sine is recovered in 50/50 trials at noise 10, but 0/50 at noise 0.2.
- **Verdict:** open; a test is proposed (100/120 Hz lighting flicker).
- **Lessons:** aliasing cannot be undone by resampling; calibrate detection with synthetic vibrations first.

### docs/analysis/roman-ep2-20261031/README.md
- **Date:** 31 Oct 2026.
- **Purpose:** delay vs noise, and a per-object Kalman filter.
- **Method:** public ep2 plus all 20 public episodes; CPU, $0.
- **Results:** perception delay ≈25 ms (0.50 frame); noise median 0.15 cm. Half-frame advance: ADD −4.4% mean, 32 better / 1 worse. Causal Kalman: +1.3 to +7.8% (worse). Offline RTS: −0.7 to −0.8%. Cross-validated smoother: held-out −1.2% on top of the advance. The robot video's visible lag is drift and failure (1–14 cm), not delay.
- **Verdict:** half-frame advance adopted in refine.py but not wired into pipeline_ep.sh; Kalman rejected.
- **Lessons:** the visible delay is the robot, not the tracker.

### docs/analysis/roman-meeting-20261030.md
- **Date:** 30 Oct 2026 (31-minute meeting).
- **Purpose:** check Roman Klis's proposals against the evidence.
- **Method:** repository and live branches; no ground truth.
- **Results:** the judged video shows the simulated robot, not the tracker. Kinematic human-hand twin scores P 0.323 / 0.617 / 0.331 / 0.194 vs 0.506 / 0.605 / 0.619 / 0.220 leaving objects alone. Perceived index finger 6.25–6.45 cm vs 10.45 cm Sharpa and ≈9.5 cm anthropometric. Plausible masses: cup 128 g, lid 88 g, dust pan 44 g (placeholder 0.3 kg).
- **Verdict:** hands are off in depth and scale; grasp lock already uses contact points; the kinematic twin does not carry objects.
- **Lessons:** a good 2-D overlay is not the test.

### docs/analysis/roman-meeting-20261031.md
- **Date:** 31 Oct 2026 (29-minute meeting).
- **Purpose:** check a second round of proposals (per-object UKF, VLM separation, simpler hand).
- **Method:** live branches; no runs.
- **Results:** over 70 public draws the reference is ≈10% of RPE and ≈16% of MPPE; failed draws score 10–77 cm. Constant per-object offset: AUC +0.050 (19/20 better); frame-0 tilt +0.040. Marker sensor fails; depth-ICP recovers almost none of the offset. Eval 10 twin 0.940 with true motion vs 0.595 ours. Choosing draws by GT-free MPPE would cut public RPE 13.7 → 6.4, rejected as cherry-picking.
- **Verdict:** no UKF before the freeze unless noise is shown; bias observability is the open question [H].
- **Lessons:** bias, not noise, dominates the reference error.

### docs/analysis/roommap-20261102/README.md
- **Date:** 2 Nov 2026.
- **Purpose:** test a room-map camera against perc2's camera under a pre-registration.
- **Method:** PREREG pushed before any map; $0; ~3.5 h wall.
- **Results:** G0 pass; G1 fail (eval bound mean 0.0029 vs ≥0.01); G2 fail on clause 1 (ep22 ΔAUC −0.0164). Ep24 alone: +0.1477 (0.834 → 0.982, perc2 camera 37 mm off). Mean over 19 public: +0.0070, but −0.0008 without ep24.
- **Verdict:** step 2 does not proceed. A selective rule (ep35 only on eval) is post hoc; expected ≈ +0.002 board AUC [E].
- **Lessons:** the map helps only where drift is large; a rule formed after seeing scores needs fresh evidence.

### docs/analysis/rpe-decomp-20261031/README.md
- **Date:** 31 Oct 2026.
- **Purpose:** decompose RPE, MPPE and AUC on public episodes.
- **Method:** kit definitions read from source; 70 official P-arm draws; CPU, $0.
- **Results:** successful draws 1.4–3.5 cm RPE; failed draws 10–77 cm. P-arm mean RPE 13.7 cm, of which reference 1.4 (≈10%); MPPE 8.4 cm, reference 1.3 (≈16%). Public 20: RPE 1.66, MPPE 1.90, AUC 0.890; without ep23, RPE 1.00, AUC 0.935. K1 rest-hold (ΔAUC +0.001) and K2 initial-hold (ΔAUC +0.001) both fail.
- **Verdict:** failures are the lever; reference candidates rejected.
- **Lessons:** an unbounded mean is dominated by single failed rollouts.

### docs/analysis/sr-vs-ref-20261103/README.md
- **Date:** 3 Nov 2026.
- **Purpose:** SP-SR and MP-SR of pack 14p against our own reference.
- **Method:** kit per-world logic with our packed reference; CPU, GT-free.
- **Results:** all 20 episodes pass vs our reference. Board policies' 10-draw rates: SP-SR 1.0 on all 19; MP-SR 0.9 on evals 1, 20, 28, 30 (one bad draw each).
- **Verdict:** the board's 2 SP-SR and 4 MP-SR failures lie in reference-vs-truth error; policy fixes cannot buy them.
- **Lessons:** only reference accuracy can recover those episodes.

### docs/context-and-decisions.md
- **Date:** decisions 20–25 Oct 2026.
- **Purpose:** record the owner's goals, rules and decisions.
- **Method:** owner conversations.
- **Results:** perception-first pipeline approved; no spending cap; Vast.ai only; RTX PRO 6000 default; interruptible machines after checkpoint resume is verified; overnight top-up $50 (21–22 Oct); "use both" learners (25 Oct) with a GT-free choice rule. Estimates (guesses until measured): tracking on eval 0.72–0.81; first submission 0.60–0.75; after fixes 0.75–0.85.
- **Verdict:** decisions recorded; owner revised several rules on 20 Oct.
- **Lessons:** keep owner rules and public-only Kaggle rules explicit; an API key pasted in chat was treated as exposed.

### docs/forensics-2026-10-21.md
- **Date:** 21 Oct 2026, evening.
- **Purpose:** architecture forensics and out-of-box ideas, against leader AUC 0.831.
- **Method:** validation runs and CPU replays.
- **Results:** ep27 0.965, ep2 0.926, ep12 0.890 (another seed 0.604), ep21 0.826, ep18 0.396 (8 rollouts 0.13–0.41, sd 0.08), ep24 0.232. On ep18 the policy is below the do-nothing floor (0.637). Stiff wrist (kp 400) falsified: ep18 0.193 vs 0.381. Hand lead-in fix: ep24 0.080 → 0.232.
- **Verdict:** physics preflight gate ranked first; stiff-wrist hypothesis falsified.
- **Lessons:** CPU replays answer questions faster and free; rollout noise is large.

### docs/gpu-rental/report.md
- **Date:** prices snapshot 18 Oct 2026.
- **Purpose:** find the cheapest compliant GPU rental.
- **Method:** market listings plus a spec-based cost model (an estimate, not a measurement).
- **Results:** Vast RTX PRO 6000: $0.99–1.12/h on demand, $0.43–0.53/h interruptible. RunPod Community $1.69/h; RunPod Secure $2.49–2.59; Nebius $1.80. Estimated campaign cost: $80–155 on Vast (central ≈$110); $170–255 on RunPod Community. Packing two runs per card is untested.
- **Verdict:** Vast RTX PRO 6000 adopted.
- **Lessons:** rank by cost per trained policy, not per hour; preemption rates and checkpoint resume are unmeasured.

### docs/gpu-rental/vast-snapshot-2026-10-20.md
- **Date:** 20 Oct 2026 snapshot.
- **Purpose:** record Vast market offers.
- **Method:** public offers API; cost per policy is an estimate using assumed relative speeds.
- **Results:** verified on-demand RTX PRO 6000 WS $1.136/h (≈$2.20 per policy, estimate); interruptible Max-Q minimum bid $0.188/h (≈$0.60 per policy).
- **Verdict:** day 1 on demand; then interruptible if resume works. Max-Q speed to be benchmarked.
- **Lessons:** bids can be outbid at any time; storage bills while stopped.

### docs/mesh-v5-spec-draft.md
- **Date:** 22 Oct 2026; status proposed; freeze 4 Nov.
- **Purpose:** specification for mesh pipeline v5.
- **Method:** five evidence reports; acceptance rules written before runs.
- **Results:** observation-first mesher E0: −0.0154 cm CD-O, −1.25 mm registration offset, no new flip (below-table votes gave flips: wp1 1/6, wp2 2/6). Decimation 15/15 watertight. Hand-flattened sweeper: ep18 0.345 → 0.715 (one seed, confounded). Expected ≈ −0.015 cm eval-weighted CD-O over 26 pairs. All [D] numbers came from scan-contaminated inputs.
- **Verdict:** several decisions adopted provisionally; GPU checks G1 ≈ $2–3, G2 ≈ $13–18 need the owner's go-ahead.
- **Lessons:** choose global shape from scans only; confirm on compliant inputs.

### docs/organiser-email-draft-2026-10-22.md
- **Date:** 22 Oct 2026.
- **Purpose:** draft questions to the organisers (not sent by the agent).
- **Method:** none; questions on collision geometry, hidden-region completion, bootstrapping with public scans, the spoon, and a stiffer wrist (kp 25 → 400 N/m).
- **Results:** no measurements.
- **Verdict:** unsent; owner action.
- **Lessons:** ask about rules before final runs.

### docs/organiser-email-late-registration-2026-10-31.md
- **Date:** 31 Oct 2026.
- **Purpose:** draft a late-registration request after the form closed.
- **Method:** unsent Gmail draft; owner fills brackets.
- **Results:** claims an AUC board position of 8th (0.8146, 31 Oct). Kaggle team IDs for six Track 3 competitions; team renamed "Imitation.Tech".
- **Verdict:** unsent; owner action.
- **Lessons:** the Kaggle deadline (4 Nov 22:00 UTC) is the hard limit.

### docs/overnight-2026-10-22.md
- **Date:** 21–22 Oct 2026.
- **Purpose:** test contact-anchored retargeting on four validation episodes.
- **Method:** registered ADD-AUC, 6 official evaluations per policy; hard episodes also seed 43.
- **Results:** base vs retargeting: ep12 0.725 ± 0.067 → 0.790 ± 0.023; ep27 0.942 ± 0.017 → 0.911 ± 0.017; ep18 0.345 ± 0.046 → 0.319 (seed 43: 0.361); ep24 0.297 → 0.307. Sweeper flattened (kfi): ep18 0.715 ± 0.240, 5 of 6 rollouts 0.79–0.84; do-nothing floor 0.637. Evaluation spread ±0.01–0.10; two seeds differ by ≈0.04.
- **Verdict:** retargeting not a universal win; choose per episode by sim_vs_ref; sweeper fix adopted (one seed, confounded).
- **Lessons:** need ≥2 seeds × 6 evaluations; mesh validity is the main lever.

### docs/plans/new-perception-20261103.md
- **Date:** 3 Nov 2026.
- **Purpose:** plan a new perception method.
- **Method:** literature check; pre-registration planned.
- **Results:** payload-only mesh changes reach the board directly (12e +0.029, 13p +0.010, 13p2 +0.0015). Tracker errors are systematic: smoothing −0.0001; rest-frame oracle +0.032. Proposal H1: learn a per-object body-frame bias from public mocap. Expected +0.005–0.015 board AUC [E].
- **Verdict:** proposed; calibration on public mocap is GT-informed, so eval use needs owner approval.
- **Lessons:** payload changes need no retrain, but GT-informed calibration needs approval.

### docs/plans/perfect-following-20261101.md
- **Date:** 1 Nov 2026.
- **Purpose:** plan to follow the perceived trajectory on all 20 eval episodes (target sim_vs_ref 1.0).
- **Method:** six-step plan with CPU preflight first.
- **Results:** H5p7 baseline mean 0.921. Budget ≈$75–95 GPU (ceiling ≈$115) [E]; credit $23.56 at 18:57 UTC, so a ~$100 top-up is needed.
- **Verdict:** proposed; step 1 is CPU and free.
- **Lessons:** budget gates before each retrain; keep a record of what has been tried.

### docs/professor-package/00-summary.md
- **Date:** 10 Oct 2026.
- **Purpose:** summary and direction for the professor, before any training.
- **Method:** research on a laptop CPU with public data.
- **Results:** guessed central estimate 0.75 (range 0.65–0.85), unmeasured. Leader ADD-AUC 0.649 (6 Oct). Findings: timing bug caps AUC near 0.42; world drift ≈ −0.20; inflated collision hulls; symmetric anchor objects; weak wrist. NVIDIA Track 2: AUC 0.51 with clean mocap, 0.002 with an off-the-shelf reconstruction.
- **Verdict:** superseded by later measured results (board AUC 0.8857 on 3 Nov).
- **Lessons:** pre-measurement estimates were far from the measured results.

### docs/registration-form-draft-2026-10-30.md
- **Date:** 30 Oct 2026.
- **Purpose:** draft answers for the team registration form (owner submits).
- **Method:** Kaggle API check of deadlines.
- **Results:** Kaggle deadline 2026-11-04 22:00 UTC; team IDs for six competitions; board AUC 0.81460 (7th, 30 Oct). Team rename needs a browser login. The repository was private and did not include the organiser account.
- **Verdict:** draft; owner action; share the repo before citing it.
- **Lessons:** verify access before citing links in submissions.

### docs/research/approaches-2026-10-25/approach1-motion-constrained-meshes.md
- **Date:** 25 Oct 2026 (22 Oct experiments).
- **Purpose:** test meshes shaped by the motion they must allow.
- **Method:** CPU and web; public twins against mocap after inference.
- **Results:** eval 25 board identities were swapped (and one board turned 180°). Identity rule on public ep24: 0.029 → 0.706 [D]; a swap alone drops a 0.795 track to 0.057 [D]. Our boards overlap 10.65 cm³ at assembly. A slot in the collision copy brings a driven board to 0.05 cm / 0.5°. Submitted-mesh carves were neutral or harmful (lid min-cut +0.14–0.18 cm CD-O; nested cups 1.17 → 1.43 cm).
- **Verdict:** identity-check prototype built; carve only the collision copy; submitted-mesh edits rejected. Expected +0.005–0.009 AUC [E].
- **Lessons:** silent identity swaps are costly; carve the collision copy, not the submitted mesh.

### docs/research/approaches-2026-10-25/approach2-primitive-meshes.md
- **Date:** 25 Oct 2026.
- **Purpose:** rebuild meshes from primitives, then refine physically.
- **Method:** pre-registered rules (RULES.md); scans used only for diagnostics; CPU.
- **Results:** lathe fits: blue cup CD-O 0.523 → 0.307 cm; pot 0.437 → 0.319 cm; beige cup 0.730 → 0.292 cm, but its ADD rises 5.4 → 8.2 mm. Package passes the acceptance rule (ΔCD-O −0.103 cm; ΔADD −0.41 mm over 26 pairs). Board box-with-slot adds 2 registration flips (ADD 157 mm on 2 of 6 seeds). Pitcher, lid, rack and sweeper fail the lathe gate.
- **Verdict:** simulator copy now; submitted mesh only after CPU rescoring and owner decision; skip pitcher, lid, rack, sweeper, dust pan. Expected AUC +0.01–0.03 [I].
- **Lessons:** primitives add symmetry, and symmetry causes registration flips.

## Recurring lessons

- Pre-register gates before scoring. Several plausible ideas (hand-aware correction, markers, physics fusion, tracker variants) failed their gates and were caught this way.
- Single draws and single seeds are noisy: one policy's rollouts spread with sd ≈0.08; two seeds differ by ≈0.04. Decide with ≥2 seeds × 6–10 draws.
- sim_vs_ref measures only policy-vs-reference. Reference-vs-truth error (≈0.075–0.135 by estimate) is invisible to it.
- Unbounded RPE/MPPE means are dominated by single failed rollouts; check failures before tuning references.
- Mesh validity (overlaps, open shells, missing slots, stand-ability, identity swaps) repeatedly gave the largest measured gains; fix the collision copy first.
- Payload-only changes (mesh shape and placement) reach the board without retraining, but scan-based choices are contaminated and need public-evidence gates.
- Test on CPU first: zero-action replays and drop tests cost $0 and caught several failures before GPU spend.
- Label every number and keep estimates separate. Several early estimates (the professor package, the 0.75 central case) were overtaken by measurement.
- Wire working fixes into the default pipeline. Two gains (the half-frame advance, identity_fix) were measured but not used in eval packs.