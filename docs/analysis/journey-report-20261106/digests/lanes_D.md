# Lanes D: perception-experiment sessions (1-5 Nov 2026 to 3 Nov 2026)

Source: `list_events` with kind `result` only, read from each session's newest page backwards to the transcript start. Each entry below is the session's own final summary for one turn, plus `total_cost_usd` deltas. Costs are agent model usage at list price, not GPU rental, unless stated. Measured numbers are the agent's own; "est." marks estimates. Public-episode work only unless stated.

### Physics-informed perception correction (session_01D9UJC6vSSNiJqaAdzNUn7d, 1-2 Nov 2026)

Six result turns, 2026-11-01 21:21 to 2026-11-02 07:34 UTC.

- **Turn 1 (1 Nov 21:21, 4,869 s, 116 turns).** Asked to test physics-based corrections of perceived object trajectories on the 20 public episodes. Everything ran on CPU, $0 rental. Pre-registered gate: mean dAUC >= +0.003, no episode below -0.01, MPPE and RPE not worse on average. The scorer reproduced the stored baseline exactly (mean AUC 0.8769 on 20 episodes). Mocap was read only by the scorer and diagnostics.
  - Idea 1, frame-0 tilt anchored to the tracker and the mesh's stable rest pose (P1): +0.00156 (13 better, 0 worse). Fail, too small.
  - Idea 1 variant, pot/cup symmetry axis as "up" prior: +0.00067, below P1; its failure test fired.
  - Idea 2, multi-frame initialisation: already tested 30 Oct as refine.py step S3, -0.0013. Not repeated.
  - Idea 3, cup twist from GRASP's twist tool checked against mocap: twist worse on 5 of 6 cups; ep11 -0.008. Fail. Holding the twist only while the cup rests: AUC unchanged, twist better on 6 of 6 cups. Exploratory, not pre-registered.
  - Idea 4, lower static and floating objects onto the table (F1): +0.00142 (2 better, 0 worse). Fail.
  - Stack P1 + F1: +0.00298 (14 better, 0 worse; MPPE -0.028 cm; RPE -0.011 cm; 95% CI +0.0008 to +0.0059). **Fails the mean clause by 0.00002.** Not rounded to a pass.
  - Upper bounds (mocap oracles): perfect anchor tilt +0.0164, 70% of it from the water pitcher on ep21/22; constant per-object position offset +0.030, concentrated in ep24, ep31, ep11. The pitcher carries a consistent ~6 deg tilt error because the mesh lacks half its base.
  - Board value: stack adds ~+0.002 AUC, but needs retraining every affected eval policy (~$3-6 each, est.). Not worth GPU money unless references are rebuilt anyway.
  - Handover: `qa_physics.py`, a ground-truth-free check for impossible tracks. On public it flags exactly the two catastrophic failures (ep0 lid; ep23 board swap) plus one false positive.
  - Next GPU asks proposed (need owner go-ahead): a pitcher mesh with a full base (up to +0.012 public AUC, upper bound; ~$1-3 est.); re-detection on episodes `qa_physics` flags (~$1-2 each est.; ep0's lid alone costs -0.025 of the mean).
  - Verdict: no reference change. Branch `claude/physics-perception-20261101`; report `docs/analysis/physperc-20261101/README.md`.
- **Turn 2 (1 Nov 21:21, 16 s).** A GRASP session replied on overlapping tests. Cup twist harmful on ep13 when it follows the hand; only the rest-hold version is worth keeping. Hold filter ("no mover, no motion") passed AUC by +0.0017 but dropped simulated robot tracking by 0.018 on ep2, 12, 13 and 31. Public gate failed.
- **Turn 3 (2 Nov 07:12, 26 s).** The owner asked for a method name to be removed from STATUS.md and from the report heading; done and pushed (history still carries it). The name is not reproduced here.
- **Turn 4 (2 Nov 07:18, 36 s).** Handover to a new GPU session ("Perception accuracy on public episodes"): reproduction steps, the pitcher as top GPU item, the two catastrophic failures, and a list of tests not to repeat.
- **Turn 5 (2 Nov 07:18, 13 s).** A new tracking session (`claude/perception-tracking-20261102`) introduced itself. This lane closed its CPU work and offered CPU diagnostics on request.
- **Turn 6 (2 Nov 07:34, 18 s).** The tracking session took the complete-base pitcher as a tracker template. Its pass test: AUC on ep21/22 up by at least +0.010 and frame-0 tilt error down on both. Pre-registration at `docs/analysis/ptrack-20261102/PREREG_pitcher.md` on its branch.

Cost: list-price agent usage ~$13.47 cumulative. GPU $0 (no rentals).

### Room map: drift-free camera tracking (session_01D9UJC6AegGiAjYM6ukSfHj, 2 Nov 2026)

Four result turns, 2026-11-02 20:04 to 20:07 UTC; run length of the first turn was 14,449 s over 140 turns.

- **Turn 1 (20:04, 140 turns).** Step 1 of a rebuild of note 18's room map without ground truth, as `pipeline/roommap.py`, mapped from public videos only and relocalising the camera per frame. Gates committed before results (be2f920). The full map registered all 370 public images and relocalised 100% of frames on the 20 eval clips and 19 public episodes with a control run (minimum 442 matched points per frame).
  - G1, eval drift upper bound on AUC gain must reach the 0.01 build bar: **failed.** Object positions differ from the map by 2-9 mm (p95) on 19 of 20 eval clips; eval 35 reaches 18 mm. Mean upper bound on AUC gain ~0.0029. Note 18's +0.10 estimate does not apply to the current camera tracker (perc2).
  - G2, public leave-out vs mocap: **failed.** All 19 episodes: mean dAUC +0.0070, dMPPE -0.081 cm. ep24: +0.148 (0.834 to 0.982), dMPPE -1.38 cm; perc2's camera was 37 mm off there and the map recovered 84% of the bound. The other 18: mean -0.0008, dMPPE -0.008 cm. ep22 lost 0.0164, below the -0.01 floor.
  - Option raised, not pre-registered: use the map camera only where the bound is >= 0.02. On eval this picks eval 35 alone, worth ~+0.002 board AUC (est.), needs one reference rebuild and retrain (~$3-6 est.) and a new pre-registration. Public support is a single episode (ep24).
  - Artifacts: HF store `runs/20261102-roommap-6438495/`; report `docs/analysis/roommap-20261102/README.md`.
- **Turn 2 (20:07, 148 s, 13 turns).** Six queued messages handled. ep23 scored with a replacement control run from perception-tracking: control 0.663 reproduced; map version 0.6643 (+0.0013). perc2's camera within 8.5 mm of the map, so ep23's frozen track is not a camera problem. All 20 public: mean dAUC +0.0067, dMPPE -0.076 cm. By AUC the map wins 7 episodes, perc2 wins 10, 3 ties. Exported ground-truth-free map camera poses for all 20 public episodes (each from a map that never saw that episode) and all 20 eval clips, in perc2's convention, under `runs/20261102-roommap-6438495/world_T_cam/{public,eval}/`.
- **Turn 3 (20:07, 29 s).** Perception-tracking asked for a "camera guard" (switch to the map camera only where it strongly disagrees with perc2). Not started. The agent flagged that a threshold chosen after seeing public scores makes the public "no harm" check non-independent. Options given to the coordinator: (A) pre-register the rule (switch where bound >= 0.02) and test on unseen public data, $0, ~2 h CPU; (B) stop. The owner had put everything beyond step 1 on hold until a credit top-up.
- **Turn 4 (20:07, 16 s).** Coordinator chose (B). Eval 35 stays an optional arm for the perfect-following session after the top-up; it needs its own pre-registration with a caveat. The point-track session won't use map cameras. Commit f0402c08. No machines rented.

Cost: list-price ~$10.00 cumulative. GPU $0.

### Point tracks: catch and repair lost object tracks (session_01D9UJC72kCbx1mWTB2pwupw, 2 Nov 2026)

Eight result turns, 2026-11-02 17:37 to 20:07 UTC.

- **Turn 1 (17:37, 1,791 s, 103 turns).** Task: catch and repair lost object tracks. Finding: ep23 is not a frozen track. Its two boards' names are swapped and the scorer's frame-0 alignment hides it; point tracks cannot repair identity. The existing `pipeline/identity_fix.py` fixes it on the public control (AUC 0.041 to 0.663), which perception-tracking confirmed; that step had never been run on public controls, and eval 25 already uses it.
  - Tracker: OpenCV KLT frame-to-frame, CPU, $0. Seeded from the tracking template drawn at FoundationPose's frame-0 pose, because perc2's frame-0 mask for the ep0 lid sits on the pot handle. Checked by eye on ep0 and ep18 (no mocap).
  - Pre-registration pushed before scoring (commit 9203ccd, `docs/analysis/ptrack-20261102/PREREG.md`). Primary arm repairs only frozen or lagging tracks; report-only arm repairs every flag. **Gate: mean AUC gain >= +0.005, no episode worse than -0.01, mean MPPE not worse.** The agent expected failure.
  - Plan: both arms on all 20 public episodes; BootsTAPIR GPU arm (~$3 or less, est.) only if losses were caught but KLT dropouts blocked repair.
  - A denied Bash command appears in this turn's permission record (a venv/dependency install and a timing script). No effect is recorded.
- **Turns 2-5 (17:38 to 17:48).** Progress only: ep0 and ep18 done, then ep23, then ep13; control scored on all 20 by 17:43.
- **Turn 6 (18:08, 66 s).** 16 of 20 episodes done for both arms through ep41; remaining 42-45.
- **Turn 7 (18:21, 380 s, verdict). Gate FAILED on all 20 public episodes; not adopted.**

  | Arm | Mean dAUC | Better / worse | Worst episode | Mean dMPPE | Frames > 3 cm off (control to arm) |
  |---|---|---|---|---|---|
  | Lag-only repair (primary) | -0.058 | 0 / 6 | ep42 -0.366 | +0.27 cm | 955 to 1,115 |
  | Repair every flag (report-only) | -0.132 | 2 / 10 | ep42 -0.754 | +0.92 cm | 955 to 1,609 |

  - Why: most flags are false. Of 17 flagged spans, only 5 fall where the control's own track is more than 2 cm off (one of them ep23). In most flags FoundationPose was right (0.4-1.5 cm) and the point tracks were wrong.
  - Mechanism: KLT points drift onto the hand or background during grasps and fast motion on white and light-wood objects; repairs rarely hand back to FoundationPose, so one false flag replaces the rest of a clip.
  - Only gains: ep11 (+0.053) and ep40 (+0.010), both in the report-only arm.
  - BootsTAPIR not run: its trigger condition (real losses blocked only by KLT dropouts) did not hold.
  - Branch `claude/point-track-20261102` (latest 1745c9f); `docs/analysis/ptrack-20261102/` (RESULT.md, PREREG.md, ep23_identity.md, results/).
- **Turn 8 (20:07, 23 s).** The room-map session sent new camera poses. The agent declined the extra test it had been allowed, because a camera swap cannot change a verdict driven by false point flags. Closed; commit 922365c; nothing rented, $0.

Cost: list-price ~$9.56 cumulative. GPU $0.

### Object-specific pose networks: pot proof of concept (session_01D9UJC5VUFMLYBMNxA8FsXe, 3 Nov 2026)

Twenty-two result events across the run, 2026-11-03 07:02 to 08:45 UTC. The longest turn was ~1,264 s at the start. Key turns below; control and box-status turns are summarised.

- **Turn 0 (07:02, 1,264 s, 100 turns).** Pre-registration pushed (1058d7ec) before any training.
  - Pot episodes: 0, 2, 26, 27, 41-45. Split: train 0, 26, 41, 42, 43; test 2, 27, 44, 45.
  - **Primary gate: mean pot AUC gain >= +0.02 over the tracker on the test episodes and no episode below -0.01**, using 10-seed registered scoring with the 13p meshes.
  - Method: an own GDRN-style network in plain PyTorch predicts the pot mask and dense object coordinates; pose is a robust fit to stereo depth. Trained on the submitted TSDF pot mesh with an own renderer.
  - Licences: GDRNPP (Apache-2.0) not used because its CUDA/detectron2 stack did not match the image. FoundationStereo and FoundationPose flagged non-commercial, both already in the pipeline. Licence notes in `docs/analysis/ipose-20261103/METHOD_LICENCES.md`.
  - Self-test: geometry check with perfect correspondences gave 0.22 cm / 1.2 deg median from the track; local scoring reproduced the control on ep44 (pot AUC 0.9979).
  - Box: one RTX 4090 at $0.56/h (rate as given in the transcript), estimated $2.5-3 against a $15 cap. Pass chance ~25% (agent estimate).
  - A denied Bash command in this turn probed environment variable names; no values are recorded here.
- **Turn 1 (07:03, 49 s).** Addendum 1931d067 pushed before training: a secondary criterion added at the coordinator's request. **Median pot ADD down by at least 20% with no episode worse; lost frames (>3 cm) reported.** The agent noted the primary gate could never pass: the tracker already averages pot AUC 0.983 on the test episodes, so the maximum gain is +0.017 < 0.02.
- **Turns 2-4 (07:03 to 07:05).** The 13p rack mesh md5 checked out for ep27 alignment; box 58930545 pulled its image, then ran environment setup.
- **Turn 5 (07:08).** Control reproduces base13p on the four test episodes:

  | Test episode | Pot AUC | Median ADD (cm) | Lost frames (>3 cm) |
  |---|---|---|---|
  | 2 | 0.9935 | 0.44 | 2 |
  | 27 | 0.9677 | 0.76 | 1 |
  | 44 | 0.9979 | 0.32 | 0 |
  | 45 | 0.9742 | 0.64 | 0 |

  The secondary criterion needs median ADD cut by ~0.1-0.15 cm, which the agent called demanding.
- **Turns 6-7 (07:19).** The host went offline mid-setup; the monitor was to report recovery, with a 10-minute rule to destroy and re-rent. Then the job ran (depth prefetch, then synthetic rendering).
- **Turn 8 (07:22, 105 s).** The first job attempt died after ~2 minutes: `.gitignore` excludes `*.npz`, so control tracks and mocap labels never reached the box. The agent force-added them and restarted on the same box (c5c3fa56), so no second setup cost.
- **Turns 9-10 (07:22 to 07:24).** Synthetic rendering, then training R at ~15 it/s for 18,750 iterations (~21 min).
- **Turns 11-18 (07:44 to 07:52).** R trained (synthetic loss 0.042). On ep2, R gives 0.48 cm / 2.1 deg medians against the track. ep27: predicted visible mask has holes inside the pot (rendered-to-real gap). R+M (R fine-tuned on training-episode mocap) trained from 07:47; scoring of R took ~55 s per run over 16 runs. Box finished and self-destroyed at 07:52.
- **Turn 19 (07:54).** R's ep27 failure is concentrated in frames ~100-200, where median ADD rises to 2-6 cm; likely hand-held frames, with a 9.7 deg rotation disagreement.
- **Turns 20-22 (08:08 to 08:34).** Waiting; then a scoring-script fix committed and pushed (08:34).
- **Turn 23 (08:45, 80 s). Verdict: FAILED.** Pot AUC, four test episodes (per-frame scoring with depth fitting):

  | Version | Ep 2 | Ep 27 | Ep 44 | Ep 45 | Mean change in pot AUC |
  |---|---|---|---|---|---|
  | Tracker | 0.9935 | 0.9677 | 0.9979 | 0.9742 | - |
  | R (rendered only) | -0.003 | -0.257 | +0.002 | +0.000 | -0.065 |
  | R+M (R fine-tuned on mocap) | -0.001 | -0.035 | +0.001 | +0.001 | -0.0085 |

  - Primary gate could not pass (max +0.017 vs +0.02 required).
  - Secondary criterion (median pot ADD -20%, no episode worse): both versions fail. R+M cut ADD by 39% on ep2 and 10% on ep45, but was worse on ep27 and ep44.
  - Failure is almost entirely ep27, while the pot is lifted by hand; rotation about 10 deg off. The rendered pot interior does not look like the real one.
  - Without depth both are much worse. Combining the network with the track came closest (-0.0023 mean) but still did not beat the tracker.
  - Spoon: rendered-only loses 0.26 AUC on ep27; only real mocap labels close most of the gap. The spoon has no public mocap, so an all-render spoon network would not be trustworthy.
  - Recommendation: do not extend to other objects; do not build a spoon network this way.
  - Cost: one RTX 4090 for ~1.4 h, est. ~$0.8 from instance hours (the agent's estimate, plus <$0.1 download est.). The box destroyed itself; nothing running.
  - No eval runs. Branch `claude/instance-pose-20261103` (last 5f55ec1f); report `docs/analysis/ipose-20261103/README.md`.

Cost: list-price ~$11.23 cumulative. GPU ~$0.8 (est.).

### Hand-aware object tracking for held phases (session_01D9UJC9SwoRsF13MYzwtVyh, 3 Nov 2026)

Six result turns, 2026-11-03 10:27 to 11:39 UTC. (The result payloads for this lane carry inner session id `08bcdd62-0693-5fd9-81fc-60b3d2f1a863`; the pot-network payloads carry `8cee5016-f5b9-58f1-a2a8-bbf4a26bc17c`.)

- **Turn 0 (10:27, 1,751 s, 70 turns).** Literature review: HOnnotate is the closest precedent (known meshes, RGB-D). The agent adopted its objective for the object only: hand-masked depth and silhouette, contact, penetration, and a motion prior. HOLD, MagicHOI and HaWoR do not fit (monocular, template-free, hours per sequence, they solve shape and scale already available). Licences: MANO, WiLoR and HaWoR non-commercial; HOnnotate GPL. Review at `docs/analysis/hand-aware-20261103/LITERATURE.md`.
  - Per-object control scores match the kit exactly. Excluding ep23 (identity_fix wiring gap), ~61% of AUC loss falls in frames where the object moves in mocap.
  - Rigid-in-grasp with MediaPipe hands fails: replacing the track by the hand frame times a constant loses -0.12 to -0.79 AUC per episode (ep12, 18, 24, 27); a 50/50 translation blend still loses -0.014 to -0.08. Hand estimates are noisier than the FoundationPose track.
  - Timing is not the cause: half-frame shift gives +0.005.
  - Held-phase errors run along the camera ray in both directions: ep13 cup +3.5 to +4.4 cm; ep11 cup -3.4 cm (still -2.2 cm after release); ep18 sweeper up to +14 cm; ep21 pitcher -2.5 cm. Removing that component in held frames would be worth +0.018 mean AUC as an oracle (+0.0125 if applied only where error exceeds 1.5 cm). Oracle, not measured.
  - Step in progress: check whether a GT-free signal (hand-masked stereo depth vs. template drawn at the tracked pose) tracks that error. Used control run Ct (store run `20261102-ptrkF-58a0f37`) because the exact control paths had not yet been provided.
  - Pushed e574beb; a stray `p.html` (a GitHub access-error page from the literature search) was removed.
- **Turn 1 (10:50, 1,376 s, 37 turns).** Dev grid (12 configs x 4 episodes) running in background.
- **Turn 2 (10:50, 25 s).** PREREG addendum 1 (86a2b94), recorded before any holdout scoring: **gate 1 now reads "held-phase mean ADD at least 10 % lower, or held-phase AUC +0.01"; the other two gates unchanged.** The result text does not show the prior gate-1 wording; check the PREREG history before relying on this.
  - Earlier diagnostics had used the wrong control (Ct, perception-tracking's failed Test-B variant). Redone on the real control C with the 14p public meshes: 70% of public AUC loss in frames where the object moves in mocap; rigid-in-grasp still fails; oracle +0.0195.
  - Method `pipeline/hrc.py`: correction along the camera ray in hand-contact frames, gated on hand-masked stereo depth disagreeing with the tracked object. Dev: ep18 AUC 0.9246 to 0.9487 (14 cm sweeper excursion corrected over 47 frames, shifts up to 11.5 cm). ep11: depth agrees with the track while mocap says 2 cm off, so nothing depth-based can fix it. Pitcher: depth residual has the wrong sign because of its incomplete template.
  - Cost $0 (CPU, MediaPipe fits). Next: finish dev grid (eps 0, 41, 43 prepared), freeze parameters in addendum 2, then the 13 holdout episodes with 10-seed scoring and a noise replica.
- **Turn 3 (10:55, 278 s, 12 turns).** Holdout running on CPU, two episodes at a time.
- **Turn 4 (11:38, 84 s, 6 turns). Verdict: FAILED the pre-registered holdout** (commit 31fd618). 13 public episodes, 10-seed registered scoring, settings frozen before scoring.

  | Gate | Result | Required |
  |---|---|---|
  | Whole-episode mean AUC change | -0.0042 (run-to-run noise 0.0015) | >= +0.005 |
  | Worst episode | ep24 -0.047 | >= -0.01 |
  | Held-phase mean ADD | -4.3% | -10%, or held-phase AUC +0.01 |
  | Held-phase AUC | -0.0006 | alternative to the line above |

  - ep24: method moved board 2 by ~21 cm, while its real error along the ray was ~2 cm; MP-SR fell from 0.9 to 0.0.
  - ep26: moved the rack by 4 cm although the rack is never held (-0.006).
  - ep23: moved board 2 by up to 24 cm (-0.0025).
  - Other 10 episodes essentially unchanged (only ep40, +0.0004).
  - Agent's reading (not a new test): on thin, flat boards the depth check picks up surfaces behind the board; the dev episodes had no board, so tuning could not reveal this. The hand-proximity trigger also fires on objects nobody is holding.
  - Where the depth correction was right, gains were real but rare: ep18 sweeper +0.024 and ep13 cup +0.007, both dev episodes.
  - Recommendation: **no phase 2.** Remaining handling losses are the board merge and its thin margin, the pitcher's incomplete template, and errors that stereo depth itself agrees with (ep11). Levers: better meshes and templates, board-identity logic. A sweeper-and-cups variant would change only ep40, +0.0004 on this holdout, so the agent did not propose it.
- **Turn 5 (11:39, 16 s).** Coordinator agreed: no phase 2 and no restricted sweeper-and-cups variant. Closure recorded; commit 7502ccf. Hand fits and depth caches exist only in the container; `scripts/prep_ep.sh` regenerates them.

Cost: list-price ~$13.46 cumulative. GPU $0.

## Lessons

- **Pre-registered gates held up and were applied strictly in every lane.** Several pure-public tests missed a gate by a hair (stack +0.00298 vs +0.003) or failed outright (hand-aware -0.0042 vs +0.005); none were rounded up.
- **Mid-test gate edits happened and were recorded before scoring.** Pot-network addendum 1931d067 (secondary criterion) and hand-aware addendum 1 (86a2b94, gate 1 reworded) were both committed before results. The hand-aware wording change should be checked against the PREREG history.
- **A primary gate that cannot pass is itself a finding.** The pot tracker already averages 0.983 pot AUC on its test episodes, so a +0.02 gain was impossible; the session still ran and reported it, which avoided a silent redesign.
- **Oracle ceilings are not gains.** Physics-tilt (+0.0164), position-offset (+0.030), hand-ray removal (+0.0195 / +0.018) were all oracles; measured results were far smaller or negative.
- **Point-track repair and hand-frame fusion failed on false flags.** Most flagged spans were ones where the tracker was right; repairs that never hand back to FoundationPose cost more than they fix.
- **Depth-based corrections fail on thin flat objects.** The hand-aware depth gate moved a board 21-24 cm; the dev set contained no boards, so tuning could not reveal it. Holdout composition matters.
- **Ground-truth-free checks worked as diagnostics.** `qa_physics.py` flagged the two catastrophic failures on public data; the room map's no-GT drift bound predicted ep24's gain (84% realised).
- **Infrastructure:** a `.gitignore` rule (`*.npz`) silently blocked the GPU job's inputs; a force-add fixed it. Host-offline events occurred mid-setup. Both are worth a preflight check.
- **Cost discipline:** only one GPU rental across the five lanes (pot network, ~1.4 h RTX 4090, est. ~$0.8). Others ran on CPU at $0. Agent usage at list price was $6-13 per session, which is not GPU spend.

## Coverage

| Session | Oldest result timestamp reached (UTC) | Start reached? |
|---|---|---|
| 1. Physics-informed perception correction (session_01D9UJC6vSSNiJqaAdzNUn7d) | 2026-11-01 21:21:10 | Yes: no older result events; last page had no `has_more`. |
| 2. Room map: drift-free camera tracking (session_01D9UJC6AegGiAjYM6ukSfHj) | 2026-11-02 20:04:43 | Yes: same condition. |
| 3. Point tracks: catch and repair lost object tracks (session_01D9UJC72kCbx1mWTB2pwupw) | 2026-11-02 17:37:55 | Yes: same condition. |
| 4. Object-specific pose networks: pot proof of concept (session_01D9UJC5VUFMLYBMNxA8FsXe) | 2026-11-03 07:02:50 | Yes: same condition. A few pages were large and were read from a saved tool-result file. |
| 5. Hand-aware object tracking for held phases (session_01D9UJC9SwoRsF13MYzwtVyh) | 2026-11-03 10:27:20 | Yes: same condition. |

Notes on coverage: "start reached" means the `result`-kind filter returned no further events before the given timestamp. Non-result events were excluded by design and were not read. Attribution above follows each requested session id; the inner session ids in the payloads differ from the lane ids and are listed in the session sections.
