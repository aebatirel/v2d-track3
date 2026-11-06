# Digest: reports_part2 (project analysis reports, 2026-10-01 to 2026-11-02)

Labels as in the sources: [M] measured without ground truth, [D] diagnostic against public scans or mocap, [E] estimate, [I] inference, [H] hypothesis. Some source files were already truncated in the corpus.

### docs/research/approaches-2026-10-25/approach3-grasp-taxonomy.md
- Date: 2026-10-25. CPU and web only.
- Question: does a grasp-type classifier, or a type label as seed, improve grasps?
- Method: rule-based classifier on 44 holds (6 public twins, 8 eval episodes) [M]; seed test on ep39 dust pan; literature.
- Results: thumb-finger opposition (>=110 deg) in at least half the frames of only 5 of 40 holds. Perceived thumb touches the object in 3-36% of frames for 9 of 14 plate/board/sweeper holds. Seed test ep39: zero action 0.243; CMA-ES from lateral-pinch seed 0.373; from copied human grasp 0.81-0.865. 14 of 17 grasp-related failure instances sit at phase boundaries [I].
- Verdict: classifier rejected (adds about 0). Recommended event-anchored grasp-lock, expected +0.01 to +0.03 AUC [I]. Grip-type portfolio open (about $12-19 search, estimate).
- Lesson: event timing, not the type label, is the bottleneck.

### docs/research/approaches-2026-10-25/training-steps.md
- Date: 2026-10-25. CPU only.
- Question: does more training rescue a low early score?
- Method: 29 checkpoint curves from 21-22 Oct sweeps (sim_vs_ref at 100/150/200/250M), plus spoon and eval fine-tunes.
- Results: of 22 curves starting below 0.5, median gain to 250M was +0.04; 1 of 22 ended >=0.45; 13 of 22 ended below the zero-action floor. Of 7 starting >=0.5, median +0.09, all ended >=0.45. Seed spread on hard twins 0.04-0.10.
- Verdict: adopted as a gate. Extend a run only if checkpoint means come from >=3 evaluations, the last two means each rose by >0.03, and lift is >=50% of reference height; then add 50% steps once. The [H] extension test (about $1) is not reported as run.
- Lesson: a low start is usually structural; steps cannot remove it.

### docs/research/competitors-2026-10-21.md
- Date: 2026-10-21. Read-only.
- Question: who leads the leaderboard and what do papers offer?
- Results: snapshot 2026-10-21: top team AUC 0.848, CD-O 0.065; second AUC 0.831 with SP-SR 0.95; third AUC 0.694. Most of the report is identity research on individual competitors, with unresolved name collisions; this digest omits it. Literature: contact-structure transfer beats fingertip or joint transfer (Morphometric 56.5% to 91.8% success; C2Dex 57.8% to 17.8% without contact consolidation).
- Verdict: context only. Ledger notes Spearman(CD-O, AUC) across teams is only -0.51.
- Lesson: profile-based identity claims are unverified.

### docs/research/contact-retargeting-2026-10-21.md
- Date: 2026-10-21. Read-only; 24 arXiv full texts and six repos.
- Question: which contact-anchored retargeting algorithm suits Track 3?
- Results (paper numbers, other datasets): Gen2Dex raw reset 0 of 10 tasks vs validated 9 of 10; OmniHOI physics-in-loop 9-29% to 85-89%; SPIDER kinematic replay ADD-AUC 11-24 vs 49-58 after physics; CHORD contact reward collapses at about 25 mm / 25 deg noise.
- Verdict: recommended segment-wise contact-anchored grasp retargeting, CPU-verified before any GPU. Open; not built.
- Lesson: kinematic snapping is necessary but not sufficient; video noise is the main hazard.

### docs/research/grasp-ep13-20261101/README.md
- Date: 2026-11-01. CPU, $0; pre-registered (PREREG frozen before solves).
- Question: does GRASP's window optimiser (ported, MIT) beat our annealed sampler on public ep13?
- Method: jittered means of 16 copies (0.5 mm / 0.005 rad noise); Test A (twins' references), Test B (two-hand re-lock).
- Results: Test B, perceived input: anneal 0.5270 nominal / 0.3935 +/- 0.146 jittered; GRASP 0.6266 / 0.4176 +/- 0.166; d = +0.024 (95% CI -0.071 to +0.115; 9 of 16 wins). Pre-set bar +0.05: FAIL. Test A: d = 0.000, no window improved, FAIL.
- Finding: the twins' ep13 references were locked single-hand; the left wrist stayed at z = 57.0 cm for 190 frames while the cup rose 9-12 cm before the right hand arrived.
- Verdict: H-grasp falsified at this CPU budget; no GPU step.
- Lesson: reference construction, not the solver, limited this episode.

### docs/research/grasp/audit-boards-ep24-sweeper-rack-ep31.md
- Date: 2026-10-24. CPU, no rentals.
- Question: are ep24 and ep31 losses grasp failures?
- Results: ep24 two boards: grasp-lock 0.202 +/- 0.072 (floor 0.203); 0 of 5 rollouts lift board 1; counterfactual with sim following the reference gives 0.803. ep31 sweeper in rack: 0.767 +/- 0.016; the first control step ejects the sweeper from the rack hulls (11.3 deg / 1.07 cm); fixing only that frame gives 0.840 (+0.074); a perfect grasp, lift and carry gives +0.002 to +0.004.
- Verdict: ep24 is a grasp failure (needs a designed board clamp); ep31 is a start and collision-geometry failure.
- Lesson: the evaluator records the first pose after one step and aligns on slot 0, so the first-step jump predicts lost score.

### docs/research/grasp/audit-plates-ep18-ep39.md
- Date: 2026-10-24. CPU only.
- Question: which plate failures are grasp failures?
- Results: ep18 dust pan (0.302 +/- 0.094): grasp failure; no opposition, thumb 20 mm off, closing flicks the pan 63-80 mm. ep18 sweeper: hold timing (no human contact until f60). ep39 pan (0.174 +/- 0.003): a carrier merge deleted the left-hand pick-up; sim pan moved at most 2.8 mm (zero action 0.1755 vs floor 0.1763). Standard RL on the same references lifts the objects. Fine-tune ep18 fell from 0.446 at 10M to 0.060 at 70M.
- Verdict: one of three object failures is a grasp failure; two are reference-building failures.
- Lesson: broken references hide grasp questions.

### docs/research/grasp/audit-starts-ep21-ep2-ep26.md
- Date: 2026-10-24. CPU counterfactual replays.
- Question: are the start-instability episodes grasp problems?
- Results: ep21 (0.281 +/- 0.012): pitcher mesh misses half its base and falls with no hand; in the one evaluation where a hand caught it, 0.665. ep2 (0.306 +/- 0.115): the lid is flicked out at lift onset (f59-63) in all five zero-action variants; 0.042 AUC directly. ep26 (0.383 +/- 0.131): perceived pot 29 mm too deep [D]; ejected 152 mm by f30. Pre-hold frames hold only 6-15% of the loss directly.
- Verdict: fix classes are support-consistent meshes, a designed lid grasp, and start-pose consistency.
- Lesson: start failures cause much later loss, because the object is lost before the hand arrives and never re-acquired.

### docs/research/grasp/evolution-of-human-grasping.md
- Date: 2026-10-24. Literature and quoted audits; no spend.
- Question: what does human grasp evolution imply for designed grasps and search?
- Results: failed designed grasps lacked an opposed thumb (ep18 20 mm off; ep39 at least 21 mm). Sharpa Wave: thumb/index length ratio 1.27 [M]. One episode: CMA-ES grasp edit reached 0.877 zero-action sim_vs_ref (CPU) vs standard RL 0.826 (about 1.6 GPU-h).
- Verdict: [I] evolve the grasp per hold, then a short RL fine-tune; first GPU tests about $7 (estimate).
- Lesson: one episode is not decisive; the searches were partly contaminated by sim-state leakage and were re-run.

### docs/research/grasp/evolutionary-algorithms-vs-rl.md
- Date: 2026-10-24. CPU and web.
- Question: where do evolutionary methods beat RL?
- Results: ES needed 3.6-8.0x TRPO's timesteps on MuJoCo [L]; estimate at least 10x samples for a policy network [E]. ep39 CMA-ES: 0.176 to 0.877 using 40,640 world-steps (about 14 min on 4 CPUs). Across 18 grasp-lock runs, Spearman rho = 0.73 (p = 0.0007) between zero-action and fine-tuned sim_vs_ref; zero-action >=0.5 ended >=0.73 (8/8); <0.36 ended <=0.43 (10/10).
- Verdict: no edge for the policy network; provisional yes for reference search.
- Lesson: fine-tuning finishes a working reference but does not rescue a broken one.

### docs/research/grasp/flashchord-capabilities-for-grasp-search.md
- Date: 2026-10-24. CPU only; repo aeca669.
- Question: what does FlashCHORD support for designed grasps and evolutionary search?
- Results: zero action reproduces the reference exactly; the untrained actor outputs zero; no torsional friction. One CPU replay of ep39 costs 0.068 s per frame. Fitness is rugged: an ep18 search best of 0.584 replays at 0.374; a 1e-5 jitter moves an ep18 score to 0.18-0.44. Bug: `grasp_search.py` right-hand variants moved the left hand. GPU robust CMA-ES estimated at 3-10 min per hold [I].
- Verdict: recommended primitives plus evolution of low-dimensional parameters.
- Lesson: an evolved network would pass the evaluator mechanically but would break the rule that trajectories come from learned policies.

### docs/research/grasp/human-hand-biomechanics.md
- Date: 2026-10-24; correction 2026-10-25.
- Question: what human grasp and forces does each failing object need?
- Results: friction-LP forces with the 0.3 kg placeholder mass, safety factor 1.5: dust pan 5.0-7.8 N per contact; sweeper neck clamp 1.4-3.7 N; boards 3.0-9.5 N (clamp never acquired); pitcher 3.3-5.3 N; lid side pinch 6.2-15.2 N.
- Correction: contact slots were read in the wrong order, so several palm/thumb assignments changed (pitcher palm share 0.93, not 39%).
- Verdict: robot grasps remain hypotheses.
- Lesson: check index order before building on a contact census.

### docs/research/grasp/learned-grasp-models.md
- Date: 2026-10-24. Literature only.
- Results: GraspGen supports three grippers only (low fit); GraspGen-X zero-shot on Inspire Hand 0.363 (low); DexGraspNet 2.0 (LEAP hand, CC BY-NC) medium, as seeds only; DexEvolve and DemoGrasp (84.6% average on 6 unseen sets) high as methods, code unconfirmed.
- Verdict: per-episode search preferred; pretrained generators only as extra seeds. Licence acceptance is an owner question.

### docs/research/grasp/rl-discovered-grasps.md
- Date: 2026-10-24. CPU, from stored traces.
- Question: what grasp did the successful RL policy (0.889) find on the ep18 plates?
- Results: dust pan: lateral key pinch, thumb and index contact in the same frame (f16); pan moves at most 2.9 mm before lift. Sweeper: clamp at neck and head, 10-13 links, brush moves 4.8 mm. Rollouts track the trace within 0.8-1.8 cm; registered AUC 0.868-0.902 (mean 0.889). Grasp-lock like-for-like: pan slid 62 mm and turned 22 deg before the thumb touched at f54.
- Verdict: a designed grasp must copy contact roles and timing relative to the object, not the human wrist path (policy wrist offset 14 cm / 38 deg).
- Lesson: contact roles and timing matter more than finger shapes.

### docs/research/grasp/robot-thin-object-and-tool-grasping.md
- Date: 2026-10-24. Literature plus our simulator parameters; no ground truth.
- Results: our hands do not collide with the table, so reaching under a board is not the difficulty [C]. A top-only press cannot drag an object. A 15 deg board tilt costs 2.9-3.0 cm ADD. Kinematic replay is weak (ManipTrans 4.6% single-hand; SPIDER ADD-AUC 11.0 and 24.1 vs 48.8-57.7 after physics). DexMachina: performance drops during the curriculum and restrictive wrist bounds did best.
- Verdict: hypotheses H5-H7 (restrict wrist residual during holds); not tested.
- Lesson: copy the human's object path and timing; let physics find the fingers.

### docs/research/mesh-2026-10-26/README.md
- Date: 2026-10-26. CPU, $0; no GPU, no submission.
- Question: how do we make object meshes accurate?
- Results: our board CD-O 0.402 cm vs leaders 0.154 and 0.112. Stereo points lie a median 0.9 mm (cup) and 1.9 mm (pot) from the scan [D], but submitted TSDF meshes are 4-9 mm off because the mesher binarises and blurs. Lathe fit: blue cup 0.523 to 0.291 cm, but not better than the pot mesh. Screened Poisson 0.96-1.11 cm (fails). Sensitivity: 5 mm inflation gives AUC 0.608 vs 0.987 clean [D].
- Verdict: CPU observation-first fits; a generative GPU probe (about $4-8) blocked on owner decisions.
- Lesson: registration controls the whole pose score, not only CD-O.

### docs/research/mesh-2026-10-26/cdo-sprint/C0/README.md
- Date: 2026-10-31. CPU, $0.
- Question: can packed pot, lid, rack (and blue cup) meshes be swapped for better CD-O under a pre-registered AUC guard?
- Results: CD-O pot 0.4371 to 0.3417 (ADD 6.67 to 3.05 mm, 0 of 8 flips); lid 0.4211 to 0.2199; rack 0.5551 to 0.4560; blue cup 0.5233 to 0.2906. Board estimate 0.402 to 0.367 [E].
- Verdict: pack 9a ships pot, lid, rack. Blue cup held back: its selector was written after scoring, a disclosed deviation from PREREG section 5.
- Lesson: pre-registration held, and the deviation was disclosed.

### docs/research/mesh-2026-10-26/cdo-sprint/C0a-diag/README.md
- Date: 2026-10-31. Post-hoc diagnostic.
- Results: aligning C0 onto library_v3 makes registered AUC worse or equal on every object; rack minimum dAUC -0.036 fails the -0.02 guard.
- Verdict: do not align eval-built meshes to library_v3. Lesson: library_v3's frame has its own error.

### docs/research/mesh-2026-10-26/cdo-sprint/C0b/README.md
- Date: 2026-10-31 close; pack 10 built 1 Nov.
- Question: rebuild the C0 methods without scan-derived constants.
- Results: audit found 163 constants (16 scan-derived, 71 of unknown origin). Adopted: white pot (public 0.3924; guard min -0.0107) and beige cup (0.3007; guard +0.0139). Rack (mean -0.1325, min -0.3043) and blue cup (mean -0.5462, min -0.6273) fail the guard. No lid build passed (16 of 16 public builds failed). Pack 10 pot is less accurate than C0 (0.392 vs 0.342).
- Verdict: adopted pot and beige; the rest left to the owner.
- Lesson: pack 9a had scan-derived marker constants, now disclosed; 40 unknown-origin constants remain, so the wording must say so.

### docs/research/mesh-2026-10-26/cdo-sprint/C1/README.md
- Date: 2026-10-31. CPU, $0.
- Results: beige cup (T1 lathe): eval 10 0.85625 to 0.2475; eval 8 0.72995 to 0.2549. Dust pan (T2 pick): 0.3307 to 0.2587. Board [E] 0.367 to 0.333. Guard passes; combined 18 twins mean dAUC +0.0091. Generate-then-fit (T3) won CD-O but failed the guard on pan, pot and cup.
- Verdict: adopted T1 and T2.
- Lesson: a generated mesh can win CD-O and still fail the registration guard.

### docs/research/mesh-2026-10-26/cdo-sprint/C2/README.md
- Date: 2026-10-31. About $0.02.
- Results: pitcher H-P falsified: CD-O 1.1600 vs 0.8942 baseline (gate 0.8742), ADD 11.2 mm vs 9.97 gate. Camera covers only 60-90 deg of azimuth, so the far side is never seen [M]. Rack H-R falsified: CD-O 0.4413 vs gate 0.436; gain 0.0147 below the 0.02 margin. Board stayed at the measured Kaggle 0.33234 (pack 9a+).
- Verdict: nothing adopted.

### docs/research/mesh-2026-10-26/cdo-sprint/C3/README.md
- Date: 2026-11-02, rule written post hoc; no new scoring.
- Context: pack 12c live at CD-O 0.30008 (was 0.33232), rank 11, AUC 0.84738.
- Results: Tier A (pre-registered): white pot T3 fit 0.3417 to 0.3112 (pose guard failed, mean -0.0099, min -0.042); pitcher 0.8942 to 0.7226 (ADD failed, 33.0 mm). Estimated total [E] 0.300 to about 0.290. Tier B, chosen by public-scan score, estimated about 0.267; not recommended without owner approval.
- Lesson: keep GT-selected candidates in a separate, flagged tier.

### docs/research/mesh-2026-10-26/cdo-sprint/C4-audit/README.md
- Date: 2026-11-02. CPU, $0; 50 seeds (3001-3050).
- Results: no candidate qualifies for any object, so pack 13g is empty. Only boards flip: board 2 W30 0.34, board 1 0.06; all other shipped meshes 0 of 50. Board-2 variants fail rule B. Eight predictions held; H5 falsified (graft flips 0.70).
- Verdict: 13f stays; pack 13f1 restores library_v3's board 2.
- Lesson: 50-seed audits catch flips that single seeds miss.

### docs/research/mesh-2026-10-26/cdo-sprint/E0/README.md
- Date: 2026-10-31. Packaged and verified, not scored (no eval ground truth exists).
- Question: rebuild C0's methods on eval episodes, as the owner asked.
- Results: picks by GT-free fidelity (not CD-O): pot 2.922 vs C0 2.914 (reaches E0 only through the 15% margin); rack 6.419 vs C0 6.245; blue cup 2.646 vs C0 2.723. Open ship gates: G1, the scan-derived marker-ball prior (7 mm radius, 5-9.5 mm window measured on scans); G2, no pose-board guard for E0 meshes.
- Verdict: owner decision required.

### docs/research/mesh-2026-10-26/cdo-sprint/E0b/README.md
- Date: 2026-10-31. Vast run 39 min; actual cost $0.49 vs $1.50 planned [E].
- Results: adopted white pot (fidelity 3.275 vs C0b 3.602) and beige cup (3.322 vs 3.277). Flags after verification: 17 of 32 pot marker balls lie below the base (lowest point -60.2 mm vs -43.3 without balls); beige cup has three inside-out shells (net volume 23.5 cm3 vs 157.8 for library_v3). Rack build crashed and was not retried.
- Verdict: both shipped meshes need an owner decision before contact or mass use.
- Lesson: a detector setting was raised after a first run by agents who knew the scan catalogue; the pack wording must disclose it.

### docs/research/mesh-2026-10-26/cdo-sprint/G2/README.md
- Date: not stated (freeze commit 1a3a044).
- Results: 264 generated meshes (SAM 3D, Hunyuan3D-2.1, TRELLIS.2) screened on 6 seeds. Best-of-N stage-1 CD-O vs shipped: white pot 0.2852 vs 0.3107; blue cup 0.2430 vs 0.2646; rack 0.4027 vs 0.4182; pitcher 0.3868 vs 0.3713 (worse). Typical outputs far worse (pitcher SAM 3D median 0.804). Screen cost about $0.2.
- Verdict: candidates go to the C4 audit; none adopted here. The minimum of 72 meshes is optimistic.

### docs/research/mesh-2026-10-26/cdo-sprint/G3/README.md
- Date: not stated (freeze commit 56d4710).
- Results: 468 meshes screened, 0 errors. Stage-1 best vs 13h: white pot 0.2404 vs 0.2861 (-0.046); dust pan 0.2061 vs 0.2291 (-0.023); rack 0.3953 vs 0.4016 (-0.006). Flagged input problems: ep0 lid crops show the table (2,104 observed points); hands visible in several crops.
- Verdict: candidates to audit; none adopted here.

### docs/research/mesh-2026-10-26/cdo-sprint/R/README.md
- Date: not stated.
- Results: 390 rack meshes screened (0 errors) and 39 primitive fits (not scored). Best stage-1 0.3876 vs 0.4016 (-0.014); the pre-set bar (-0.020, <=0.3816) was reached by none of 390. Only five public rack episodes exist.
- Verdict: no rack adoption.
- Lesson: best-of-390 gains are small and below the pre-set bar.

### docs/research/mesh-2026-10-26/cdo-sprint/spoon-diag/README.md
- Date: 2026-10-31. CPU, $0, GT-free.
- Results: packed blue-cup collider does not block the reference spoon in eval 32 (at most 2.6 cm3) or eval 16 (at most 0.64 cm3); in eval 33 it blocks only at the deepest dip (f155-161; spoon 128.7 mm below rim, up to 9.8 cm3). The visual solid fills 38.7% of the cavity; the C0 lathe 5.4%.
- Verdict: collider is not the main cause; the eval 16 release-flip is a hypothesis.

### docs/research/mesh-2026-10-26/ledger-of-past-mesh-work.md
- Date: 2026-10-26. Read-only inventory.
- Results: TSDF v0-v3 weighted 0.491 (submitted); observation-first v5 dust pan 0.251, pot 0.73, rack 0.82; primitive lathes cup 0.307, pot 0.319; interaction carving neutral or worse.
- Integrity finding: library v1-v4 were fused along tracks templated on the public scans ("refsweep"), so they are not inference-legal and are on the deny-list; seven of 11 objects were still submitted as the 21 Oct v1 files.
- Verdict: the ledger flags the submitted library as non-compliant.

### docs/research/novelty-2026-10-22.md
- Date: 2026-10-22. Seven-agent review; primary sources opened.
- Verdict: about 1.5-2 of 5 (integration of off-the-shelf parts). Defensible: a GT-free self-check, sim_vs_ref, Spearman 0.98 on ep18 (9 policies), 0.86 on ep24, 1.0 on ep12 and ep27 [M]. The ep18 physical-validity result (0.368 to 0.715) is confounded by mesh and settling, one seed, and only +0.08 over the 0.637 floor.
- Compliance flags: the room map (18-room-map.md) was registered with ground truth and must not be used at eval inference as built; hand-picked per-episode fixes count as human intervention; the spoon is a template; A-lite provenance needs organiser confirmation.

### docs/research/physics-2026-10-30/README.md
- Date: 2026-10-30. Step 2 CPU; step 3 GPU approved.
- Question: do plausible object masses and centres of mass change the zero-action replay?
- Results: step 2 mean delta +0.021 (ep2 -0.038, ep12 +0.049, ep18 +0.065, ep24 +0.007): neutral, since signal needed +0.03. Human-copy replay does not carry objects (ep12 0.617 vs floor 0.605; ep18 0.331 vs floor 0.619). Step 3 GPU retrain planned at $6.50 per arm (estimate); its results are not in the corpus.
- Verdict: step 2 neutral; step 3 open.
- Lesson: mass is second-order at zero action.

### docs/research/physics-2026-10-30/human-hand-models.md
- Date: 2026-10-30. Literature and CPU on model files; $0.
- Verdict: build an own capsule hand (MediaPipe 21-keypoint topology, Arti-MANO 22 finger DoF), Apache-2.0, with no MANO mesh (licence). MyoHand rejected (muscle actuators skipped; fixed size; thumb MCP 1 DoF).
- Lesson: perceived fingers are about 25-40% too short for the palm [M+I]; this is a perception finding and needs an anthropometric gate.

### docs/research/physics-2026-10-30/physics-fit-literature.md
- Date: 2026-10-30. Literature and a synthetic benchmark; $0.
- Results: reported gains against ground truth are modest (MPJPE -1 to -13 mm); plausibility gains are large (frames with fewer than 2 contacts 54.7% to 2.0%). Synthetic runtime 104 s per object for 300 frames; estimate 2-10 min per episode on 4 CPUs [E].
- Verdict: v1 design (force-feasibility diagnostic, then least-squares fit). Falsification: must not cost mocap AUC and must raise jittered zero-action sim_vs_ref on four episodes. Open.

### docs/research/physics-2026-10-30/physics-solver.md
- Date: 2026-10-30. $0; no ground truth read.
- Results: prototype in FlashCHORD. Public ep12 nominal sim_vs_ref 0.600 (grasp-lock + ILC) to 0.6899 (v3, robust copies and rollback; floor 0.605). Under 0.5 mm / 0.005 rad noise all three score about 0.56 (0.556 / 0.559 / 0.564); the 0.586 bar was not met, so the robustness hypothesis is falsified. ep2 nominal replay 0.141 vs jittered 0.260 +/- 0.071.
- Verdict: GPU step G1 (about $1-1.5) proposed with bar +0.03 on at least 2 of 4 episodes; not in the corpus.
- Lesson: the gains were lucky trajectories of a chaotic system; use jittered means for CPU gates.

### docs/research/port-recipes-2026-10-21.md
- Date: 2026-10-21. Read-only; seven papers; code cloned for three repos.
- Results: CHORD (60 tasks x 3 seeds, clean mocap) AUC 0.918; no contact reward 0.774. FlashCHORD has no relative multi-object reward although RPE is scored; its VOC schedule reaches zero at 122.9M of 250M steps. Possible sign issue: CHORD's relative reward multiplies the two errors, so one perfect term zeroes it [I].
- Verdict: port candidates listed; nothing measured.

### docs/research/seed-race-20261026/README.md
- Date: 2026-10-26. Not adopted; nothing rented.
- Question: train many seeds and keep the ones that start well?
- Results: standard learner: score at 40% predicts final (Pearson 0.89; leader at 40% ends ahead in 30 of 36 pairs). Grasp-lock: leader at 40% ends better in only 22 of 38 (58%), close to a coin flip. Cost estimates: about $12-13 for 8 seeds, $23 for 16.
- Verdict: not adopted; grasp-lock seeds run to the end.
- Lesson: an early-signal rule that works for one recipe can fail for another.

### docs/research/spoon-2026-10-25/README.md
- Date: 2026-10-25. CPU, GT-free.
- Results: the spoon anchors the scene in evals 32, 33, 35, 36 and 37. A 10 deg roll error on the eval 32 anchor drops the ratio to 0.72 (20 deg: 0.34). Random frame-0 roll of 2-6 deg costs about 0.03-0.15 per spoon-anchored episode [E]. Registration flips: 0 in 300. Rest-averaged anchor test: mean +0.001 vs rule +0.01; not adopted.
- Verdict: the inferred 0.12 spoon gap is probably overstated.

### docs/research/track3-requirements.md
- Date: 2026-10-01. Proposed; nothing installed.
- Results: 20 public and 20 eval episodes; six metrics; spoon (10 eval episodes) has no public mesh. FlashCHORD needs a 48 GiB GPU; disk plan 500 GB to 1 TB. Leaderboard had zero submissions on 1 Oct. Organisers offer no compute.
- Rules that matter: Apache-2.0 release and technical report; commit SHA on every row; no hand labelling; leaderboard freeze 2026-11-04.
- Lesson: compute, not method, was the first barrier.

### docs/research/wevisone-2026-10-26/README.md
- Date: 2026-10-26. Verdict: test first; do not build yet.
- Results: author numbers [A]: LVIS F1 55.3 vs 38.8 for Grounding DINO-T; absent-target rejection 67.4% vs 0%. Shipped rule gets 97 of 116 labelled public instances right (CPU replay) [M]. Detection is no longer the main loss: policy loss 0.088-0.117 and hidden-phase tracking 0.063 [E].
- Pre-registered test (not run): pass needs at least 99 of 116 with none of the 97 lost; about $1-1.5.
- Lesson: the model is four days old and its headline rests on an in-house benchmark.

### docs/research/work/26/README.md
- Date: 2026-10-26. CPU only.
- Results: lists carry-model, PID, sensitivity and torque-clamp scripts; records no numbers and the output files are not in the corpus.
- Verdict: no verdict recorded.

### docs/research/work/flipcheck-20261102/README.md
- Date: 2026-11-02. Diagnostic; public scans as stand-ins.
- Question: does pack 13f's wooden_piece_2 flip at eval 25's seed?
- Results: yes; rotation 179.2 deg at the eval seed (library_v3 0.7 deg). An earlier sign-off claimed no flip, which was wrong for the packed payload. Revert of eval 25 slot 1 costs CD-O 0.1642 to 0.2158 (board +0.0014 [E]). Pack 13f1 passes D1 (0 of 10 flips). Board result [M]: AUC 0.87191 vs 13f 0.87225 (-0.0003); the expected +0.02 did not appear, so the hypothesis is falsified.
- Lesson: check the packed payload, not only the base mesh.

### docs/runbook-vast.md
- Date: 2026-10-20. Operating runbook.
- Results: first box verified at $0.01; checkpoints about every 3.7 min make interruptible machines workable; boxes never push to git. Unverified at writing: stall-watchdog destroy path, setup on the Vast image, two trainings per GPU.
- Lesson: boxes get narrow, expiring tokens only. An API key pasted into chat was treated as exposed and must be regenerated.

## Recurring lessons

- Pre-registration worked: several hypotheses were falsified and reported as such (ep13 grasp, C2 pitcher and rack, flipcheck board result).
- Best-of-N picks scored against public scans are optimistic. GT-informed tiers (G2, G3, R, Tier B) were kept separate and flagged.
- Integrity findings recurred: scan-templated tracks (library v1-v4), scan-derived constants in pack 9a, a selector written after scoring, a room map registered with ground truth. Each needed disclosure or a fix.
- A single zero-action replay is noisy; use jittered means (8 to 16 copies) for CPU gates.
- Fine-tuning finishes a working reference but does not rescue a broken one. Extra steps help only curves still rising.
- Early-score races work for standard learners (Pearson 0.89) but not for grasp-lock fine-tunes (58%).
- Registration decides the pose score: 5 mm inflation drops AUC from 0.987 to 0.608, so every mesh that reaches registration needs a pose guard.
- Aligning meshes to the library frame made scores worse.
- Reference construction (locks, carrier merges, timing) caused more failures than grasp design did.
- Check payloads and contact index orders after packing or building; a flip and a swapped index each produced a wrong conclusion.
- CPU-first work was cheap; GPU probes were estimated at $1-8 and most were not run.
