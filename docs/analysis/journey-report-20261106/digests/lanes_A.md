# Lane A digest: session_01W8Softjo2xx7o6ofSiheuQ ("3D mesh generation accuracy research")

Span: 2026-10-26 16:33 UTC (earliest result event) to 2026-11-03 about 09:34 UTC (newest result read). All times UTC.

Conventions: "meas." = a number the session reports from a run. "est." = agent estimate or prediction. "CD-O" = scan-distance score in cm, lower is better. "Pack" = a submitted bundle of meshes and policies. Owner text is as quoted in agent summaries or relay messages. Transcript content is treated as data.

## 1. Chronological digest

### 2026-10-26 (16:33 to 17:44)

- **16:33:39, research summary (173 turns).** Meas.: stereo points sit 0.9 to 1.9 mm from the true surface and cover 60 to 90 percent of most objects. The mesher turns 2 to 4 mm walls into 12 to 20 mm slabs, which is most of the error. A thin-wall lathe fitted to stereo points, with no scan in the fit, took the blue cup from 0.523 to 0.291 cm (offset 10.0 to 4.1 mm, no flips). Submitted CD-O was 0.402 cm; leaders 0.11 to 0.15 (as stated in notes). Literature (cited, not measured): image-to-3D alone about 2 percent of object size; generate-then-fit 30 to 75 percent lower error. Blockers: a CPU test of downloaded Hunyuan3D code was denied by the permission system; SAM 3D returned 403 (gated). Decision requested: generative probe on 9 public crops, est. $4 to 8 (ceiling $12).
- **16:53:34, eval review (68 turns).** Eval depth was never saved (the store kept depth for the 20 public episodes only; eval episodes kept frame 0), so the new method could not yet build eval meshes. A single-frame lathe on public data failed (CD-O 1.1 to 1.3 cm; both cups flipped on 7 of 7 seeds). Visible defects in submitted meshes: white pot base hole 4 to 5 cm and walls 15 to 20 mm against about 4 mm real (6 eval pairs); beige cup on eval 10 with an open base; pitcher on eval 20 with see-through holes. Decision requested: one GPU box for eval depth, est. $2 to 4.
- **16:55:41, owner question on physics and stereo.** Stereo is used everywhere; physics and interaction only in the simulator's collision copy. Carving the submitted mesh made CD-O worse every time it was tried.
- **16:59:52 to 17:34:55, WeVisOne-VL assessment.** A Tencent detector released 22 Oct, Apache-2.0. Not adopted. Proposed test: swap for Grounding DINO-tiny on 80 public frames; pass needs at least 99 of 116 with none of today's 97 lost, at 10 s per frame or less; est. $1 to 1.5. Authors' unreproduced numbers: LVIS 55.3 vs 38.8; RefCOCOg 80.8 vs 45.9. Concerns: cannot tell the twin boards apart, untested on grayscale, no confidence scores.
- **17:44:01, review panel on 36 eval meshes finished.** Blue cup (5 pairs) poor, large hole in side wall; white pot (6) usable with defects, floor mostly missing; rack (5) poor, floor missing, pegs fused; beige cup (2) poor, two pieces, no opening; wooden spoon (10) good. Verdicts are visual, one frame per pair.

### 2026-10-27

- **04:00:58, owner question "primitives?".** Lathe on current stereo points: blue cup 0.523 to 0.291. Lathe on the older fused mesh: cup 0.307, pot 0.319, beige 0.292 (never submitted). Box board with slot: board 1 0.222 to 0.177, board 2 flipped on 2 of 6 seeds. Sim-only primitives: eval 25 0.71 to 0.79 (simulator only). Four lessons recorded: keep symmetry-breaking details (marker balls cut the cup offset from 10 to 4 mm); fit raw stereo points; include only surfaces the scanner saw; choose by a ground-truth-free score, do not merge episodes (merged 0.396 vs 0.291).
- **04:06:25, kit-of-parts build started** (owner go-ahead implied by the start). Rule committed before results: at least 0.03 cm better, offset at most 1 mm worse, no flips.
- **07:13:13, kit-of-parts results (CPU, $0).** Submitted to new CD-O (meas.): pot 0.437 to 0.342 (6 pairs; offset 6.7 to 3.1 mm; 0 of 8 flips) PASS; lid 0.421 to 0.220 (1 pair; offset 8.1 to 4.5 mm) PASS; rack 0.555 to 0.456 (5 pairs; offset 6.0 to 5.4 mm) PASS; board 1 0.222 to 0.189 (1 of 6 flips) FAIL; board 2 0.216 to 0.229 (offset 3.6 to 78.7 mm; 3 of 6 flips) FAIL. A scan leak was admitted: lid and rack wall thicknesses came from scan measurements. Re-run at 1.5, 2.5 and 4 mm, both passed (lid 0.220 to 0.224; rack 0.449 to 0.458). The fit score rejected the rack's upright cup holder, which had been adopted after looking at a scan. Est. board effect 0.402 to about 0.367. Owner options: submitted mesh only ($0), or simulator copy too (about $3 to 5 per affected episode, roughly 10 episodes).
- **10:13:32, owner "are they case by case?".** Hand-designed once per object type (rack = tray, cup holder, two rows of pegs; pot treats a cluster more than 6 cm out as handle). The real gap is coverage: cups, pitcher, sweeper, dust pan and spoon had no parts model.
- **13:06:48, blue-cup lathe.** It lines up with the library mesh within 2.7 to 3.4 mm, so cups do not need eval depth. Two routes on one engine: (A) automatic structure search, no AI; (B) AI-written parts programs that see only colour photos and renders of our own points. Est. projection on 36 eval pairs: 0.402 now, about 0.366 with pot, lid and rack, about 0.334 with the blue cup (hypothesis).
- **13:17:28.** A alone does not work yet (pot body found, handle missing; dust pan approved with a wall missing). Eval depth is needed after all: the owner's 22 Oct rule is to rebuild each eval mesh from that episode's own video. Leaderboard freeze is 4 Nov.
- **17:23:34, stage 1 done, two blockers.** (1) Ground-truth leak, admitted: the 7 mm marker-ball radius described as "from our own stereo" was measured on public scans; pot, lid and rack passes provisional. (2) The quality check judges only surfaces the cameras saw, so incomplete shells always win.
- **18:31:16, weekly usage limit** ("resets Oct 29, 9pm UTC").

### 2026-10-28

- No result events in the notes (weekly-limit pause).

### 2026-10-29

- **21:06:15,** stage 1b restarted after the weekly limit.
- **21:45:27, plan to owner.** Batch 1: eval depth on one self-destroying GPU, est. $2 to 4. Batch 2: generative probe, est. $4 to 8, needing permission to run third-party model code and SAM 3D access. Reply requested as "go batch 1" / "go batch 2". Another owner session relayed that up to $25 of Vast credit was approved for mesh work. Later reports show both under way (approval implied).
- **21:52:39, batch 1** on RTX PRO 6000 at $1.51 per hour; depth for the 20 eval episodes "per your 22 Oct rule".
- **21:57:46,** SAM 3D access request; Meta review pending.
- **22:09 to 23:35, batch 2 generative probe** on an H100 NVL interruptible bid (outbid at 22:52, rebid at $1.30). Meas. $4.36 (cap $12; plan $6).
- **22:21:05,** shared spend-ledger script fixed; the old one could erase lines when two sessions wrote at once.
- **23:17,** SAM 3D access reported approved (per summary).

### 2026-10-30

- **Usage-limit errors** at 01:13 and 23:51 (10-29), resets 2am.
- **06:33, generative probe final (run mesh-20261029-gen-f3fbeb0).** Five generators, 10 public objects, own camera crops, scored against public scans. Mean CD-O: library_v3 0.477; Pixal3D-MV 0.490 (beats library on 5); SAM 3D 0.501 (6); TRELLIS.2 0.594 (3); Hunyuan3D-2.1 0.602 (5); TripoSG 0.984 (0). Oracle best-of-all 0.315 (not a method). Registration: Pixal3D-MV median ADD 10.3 mm, 6 of 20 meshes flipping (boards, sweeper); single-image 26 to 29 mm; library about 6 mm. Ground-truth-free metric vs CD-O: Spearman 0.46 over 104 meshes. Verdict: no submission change. The interim "big win" framing (06:23) was corrected here. Meas. cost $4.36; spend stated at $7.31 of $25. Owner asked whether to delete 12.4 GB of SAM 3D weights (default: keep).
- **06:57:46, kit-of-parts status.** Pot, lid and rack rebuilt as short parts programs; lid reproduced within 0.003 mm. Earlier pot, lid and rack wins were provisional (marker balls used the 7 mm scan value). Table, submitted vs best candidate: pot 0.437 vs 0.342 (provisional); blue cup 0.523 vs 0.291; rack 0.555 vs 0.456 (provisional); beige 0.856 vs 0.274 (generator best-of-runs, not pickable without scan); pitcher 0.894 vs 0.378 (same); dust pan 0.331 vs 0.231 (same).
- **09:09:31, SAM 3D placement diagnosis.** SAM shapes mostly good; the agent's placement step fits one-sided depth points, and on 17 of 20 meshes the wrong placement fits better. Fitting to the library mesh cut median placement error 26 to 14 mm (blue cup 30 to 5 mm), but library_v3 is on the provenance blocklist. Sweeper: about 3 of 30 seeds flip; with two observed marker balls, 0 flips in 30 seeds (ball size from scan measurements, not scored). Decision requested: rebuild sweeper with balls sized from own points, one pre-registered 30-seed check.
- **09:32:24,** generalized mesh generator started (four designs, three judges, frozen predictions, denylisted libraries excluded).
- **12:08:43, lid failure.** SAM was given a frame with the lid on the pot and rebuilt the pair as "the lid" (0.7 times too narrow, 1.6 times too thick). New rule: prefer frames where objects are visibly apart.
- **13:21:20, owner: "GPU rentals from now on go ahead without asking."** (quoted in agent summary). Differs from the repo rule of a per-batch go-ahead with plan and cost. Flagged, not judged.
- **14:23:06,** generator design frozen.
- **15:13 and 19:40,** usage-limit pauses. Work resumed 17:08; the independent review found two guard leaks, both fixed.

### 2026-10-31

- **04:46,** first end-to-end builds (ep2 pot, ep2 lid, ep11 beige cup) passed an independent check; no scoring yet.
- **05:10,** eval-10 cup pieces v4: 0 overflow events in the large contact test, peak 459 of 512 rows (current pieces 9,723 events). Retrain approved under the owner's "permission for everything" (relayed). Conditions: overflow drops; inner cup lifted at least 5 cm; replace only if expected gain is at least 0.02.
- **05:48:22, POSEFIX test FAILED its gate.** Mean delta AUC -0.0107 (gate at least +0.002); 17 of 20 episodes worse.
- **05:48:45, eval-10 cause.** Cup collision pieces overloaded the simulator contact limit. Diagnostic with raised limit (not packable): 0.913; standard limit: 0.459, about 6 million overflows per seed (simulator scores as reported).
- **07:03,** eval-19 sweeper certified by fill at frame 0 (tip 5.0 deg, was 1.3; margin 5.5 mm, was 1.4).
- **08:08, board 2 chooser error.** The automatic chooser picked a 6.8 cm solid box on ep24; the points show a 1 to 2 cm board. Cause: a flip-prone rule. Not tweaked (rule fixed before scoring); planned fix: flat-plate candidates and marker balls.
- **08:34:23, owner: "Mostly yes."** (placement design and per-frame checks.)
- **08:42:22, owner clarified "slot"** as the notch cut into the wooden boards; the agent had read it as placement.
- **13:53,** first generator run on ep2 pot and lid: SAM 3D meshes 4 to 6 cm too close to camera; lid 10 to 17 percent too small.
- **15:26:40,** score session adopted the C0 plan (pot, lid, rack, blue cup) for interim pack 9.
- **15:44:28,** one Bash copy of library_c0 GLBs denied by the permission system.
- **15:48:32, pack 9a** takes pot, lid and rack. Blue cup held because its selection rule was written after scoring. Pack builder needs yes/no per object by 19:00.
- **16:08 and 16:11, hand-off and pose checks.** Blue cup offset 6.67 mm / 2.67 deg from library, not watertight (11 bodies). Pose check of four swapped meshes (51 runs, no failures): pot +0.003 mean AUC (worst -0.016); lid +0.006; rack +0.016; blue cup +0.024; mean +0.015 over 15 public episodes. Replacements in eval: pot on eps 1, 3, 5, 6, 8, 28; lid ep1; rack eps 14, 15, 16, 28, 30.
- **16:16:26,** rotation check (C0 vs old library, 0.3 to 2.1 deg). Rule: keep original fits unless the pose check is worse; pack 9a keeps original fits.
- **16:37, owner decision, relayed: "Ship 9a, flagged."** Score session asked that future eval builds use no values taken from scans.
- **17:09:17, beige cup and dust pan.** Beige CD-O 0.856 to 0.248 (eval 8: 0.730 to 0.255; one public episode for pose). Dust pan 0.331 to 0.260 (SAM 3D). The same message says the three accuracy wins (pot, blue cup, dust pan) all failed the pose check; this conflicts with the 16:11 passes and is recorded as stated, not resolved.
- **21:57:25, pitcher and rack rebuild: nothing packed.** Pitcher 1.160 vs 0.894; rack 0.441 vs 0.456 (below the 0.02 bar).
- **22:20:14, board-slot blocker.** Slotted boards on ep24 split into 57 and 77 pieces, overflowing the contact limit in all 16 runs; ep24 marked do-not-use. Hard cap then set at 380 of 512 rows per scene (22:23).
- **22:57:09, re-track test FAILED.** Own-video meshes as tracking templates: average AUC change -0.170 (pass +0.01); 3 of 20 improved; four of eight pots collapsed.
- **23:55:33, scan-free rebuild** (rented GPU about $0.49). Pot 0.392 vs 0.342 pack; beige 0.30 vs 0.25. Lid, rack and blue cup failed the rebuild; current ones stay.

### 2026-11-01

- **00:48, board slot round 3.** Firm no on the eval-25 board slot; pack 10 keeps the existing carve (contact rule judged a design error; not re-tuned).
- **02:43:16, review artifact v1 (human turn).** Pack 8 at 0.402 (rank 18); pack 9a+ at 0.332 (rank 14); about 0.300 with the C0 blue cup.
- **02:54:47, generator answer.** Generated pitcher and beige rejected (pose error 28 to 33 mm vs 10 mm limit). Generate-then-fit: 3 shape wins, all rejected (tracking worse). Hindsight best-of mean 0.315; honest selection barely agrees.
- **03:03 and 03:06, review page.** 595 meshes across 11 objects; 234 with a public-scan score. Ten public-scan copies found in scoring folders and removed. Public-scan outline added to both views, labelled "ground truth shown for comparison only" (owner request).
- **03:21:08, collision carve round 2: no pieces shipped.** Cup walls about 1 mm rough; the eval-14 and eval-32 "in table" readings came from frames with a hand within 3 mm (worst true 3.9 mm).
- **06:53:35, start-frame survey.** Falls over at frame 0: eval-20 pitcher (195 mm, 94.6 deg); eval-19 sweeper (90 mm, 89 deg); eval-30 sweeper 13 of 16.
- **08:57:02, "done for tonight".** Eval-10 diagnostic sim score 0.459 to 0.913 with overload removed. Decisions waiting: (1) C0 blue cup as a separate submission (0.332 to about 0.300, about 11th); (2) best public-scan mesh per object, about 0.263 (agent: optimistic upper bound); (3) scan-free pot and beige cup; (4) grey-template tracking test, about $1.

### 2026-11-02

- **08:34 to 08:37, blue cup for pack 12c.** Owner approved the "minimal variant" (method name withheld at owner request). Public error 0.523 to 0.291 on five pairs. Swap check flagged 6.6 and 9.9 mm vs a 5 mm limit. Owner asked ship-as-is or shift to current frame; agent chose as-is.
- **08:49:03, pack 12c live.** Board 0.332 to 0.300 (matched estimate); rank 11th; AUC 0.847. Option A (pot, pitcher) recommended; option B (est. 0.267, GT-selected) not recommended by agent.
- **08:49 and 08:52, owner-approved (A under standing permission, relayed; both for pack 12d).** Pot 0.342 to 0.311; pitcher 0.894 to 0.723. Pose drop on 7 pairs.
- **19:08 to 19:24, option B and pack 12e.** Pitcher 0.723 to 0.372 (no flips in 31 runs); sweeper 0.317 to 0.223 (2 pairs; agent says partly designed after comparing with the scan); rack 0.456 to 0.419; board 1 0.222 to 0.189; board 2 0.216 to 0.164. **Pack 12e scored CD-O 0.26775** (est. 0.268); AUC 0.869; MPPE 1.95; single-object success 0.90; multi-object 0.80; rank sum 47 (7th). Held extras: blue cup 0.290 to 0.266; dust pan 0.259 to 0.230.
- **19:29:45, pack 13f approved** (no position adjustment; blue cup flagged for size, up to 16 percent wider on the handle side).
- **20:01:28, 50-run flip audit.** Only the boards flip: board 2 in 34 percent of runs, board 1 in 6 percent. Eval episode 25 loses pose if board 2 flips. Pose-only pack keeps original boards (about 0.0014 shape cost).
- **20:10:14, board-2 variants.** Shipped: flip 34 percent, CD-O 0.1649. V1 (two marker balls): flip 18 percent, CD-O 0.1628. V2: flip 70 percent, CD-O 0.2035. Neither adopted.
- **20:26:33, correction.** Option-B board 2 does flip at scorer settings on eval 25 (179.2 deg on the raw scan). New adoption rule: never flip at scorer settings in either sampling mode, and at most 10 percent of 50 runs.
- **20:36,** first GPU box preempted about 4 minutes in; replaced by on-demand H200 at $4.03 per hour.
- **21:49 to 21:59, pack 13f1** (older pot fit plus original boards), owner-approved.
- **22:12:50, G2 batch done (run mesh-20261102-g2-ff63482 and g2b).** 264 meshes, none lost; SHA256 of 528 files committed before any scan read. Stage-1 best vs shipped (meas.): pot 0.2852 vs 0.3107 (-0.026); blue cup 0.2430 vs 0.2646 (-0.022); rack 0.4027 vs 0.4182 (-0.016); pitcher 0.3868 vs 0.3713 (+0.016, worse). Cost: box 1 est. $2.80 (preempted); box 2 meas. $5.50; total about $8.31 of a $25 cap. Tooling bug: hf CLI 2.2.0 --include dropped Hunyuan weights and TRELLIS.2 pipeline files; fetched via Python API.
- **23:13:28, 50-seed audit of 32 G2 candidates.** Pot, blue cup, rack qualify under pre-set rules; no pitcher.
- **23:44, pack 13h.** Best of 264 meshes chosen with public scans (disclosed in README). Pot 0.311 to 0.286 (offset 6.3 to 2.7 mm); blue cup 0.265 to 0.234; rack 0.418 to 0.402 (offset 10.0 to 4.3 mm).

### 2026-11-03

- **00:09:48, trimmed rack did not qualify.** 0.402 to 0.386 = 0.016 vs 0.02 bar.
- **00:10:15, pack 13h scored CD-O 0.25159** (predicted about 0.252); shape board 5th; rank sum 45. Board history: 0.332 (14th), 0.300 (12c), 0.268 (12e), 0.252 (13h). Pose board AUC 0.883.
- **01:28:48, pitcher** (G2 candidate 29) passes flip check: 6.4 mm off scan vs 14.0 shipped; CD-O 0.474 vs 0.371 (pose packs only).
- **01:49:27 to 01:49:41, G3 pre-registered and approved (relayed)**: dust pan, beige, lid, sweeper, boards (incl. Pixal3D multi-view); pot and rack added by agent. Est. $7 to 11; cap $15; on-demand only; stop if credit falls below $15 (credit $94.58).
- **04:32, G3 handback (run mesh-20261103-g3-2417282; H200 NVL at $4.033 per hour, 1.802 h).** Meas. $7.47 ($7.27 compute, $0.20 transfer). 468 stage-1 meshes, 0 errors. Stage-1 best vs CD-O: pot 0.2404 vs 0.2861 (-0.046); dust pan 0.2061 vs 0.2291 (-0.023); board 1 0.1629 vs 0.1872 (-0.024); board 2 0.1600 vs 0.1649; rack 0.3953 vs 0.4016; beige and lid and sweeper worse. Stage-1 is best-of-N and GT-informed (stated in README).
- **05:24 to 05:50, part-1 results and pack 13i.** Pot 0.286 to 0.240 (TRELLIS.2), dust pan 0.229 to 0.206 (Pixal3D-MV), board 1 0.187 to 0.159 (Hunyuan; never flipped in 50 runs) qualify pending flip check; no flips in 6 runs per mode. Rack best only 0.008 (not adopted). Owner approval relayed at 05:50.
- **06:44, owner "go in all" (relayed).** 79 G3 meshes queued for audit; container restart at 52 of 79, relaunched.
- **07:15, board 2 for pose pack 14p1.** Generated board 2 was hollow (surface area doubled); pose test used one episode that was the generation episode (caveat).
- **07:18, pack 13i scored CD-O 0.24177** (matched prediction); 4th; 3rd at 0.23900. Pack 14p1 on hold. Outer-shell cleanup: no copy passes.
- **07:33, rack outer-shell round.** Rack 0.4016 to 0.3844 (0.017 vs 0.02 bar; not adopted).
- **07:35, rack round R pre-registered.** Target CD-O at most 0.3816; GPU up to $10; four generators, six seeds; est. $5 to 8, est. 40 percent chance.
- **About 09:09 (from the 09:34 result), round R completed** (run mesh-20261103-r-63eb2c5; H200 NVL at $3.90 per hour, 1.475 h). Meas. $5.95 (cap $10). The round R outcome is not in the notes read.

## 2. Spend (agent-reported; not reconciled)

| Run | When (UTC) | Figure | Basis |
|---|---|---|---|
| Eval depth, batch 1 (RTX PRO 6000) | 10-29 21:52, self-destroy | about $2.95 | agent report, 10-30 |
| Generative probe, batch 2 (H100 NVL) | 10-29 22:09 to 10-30 23:35 | $4.36 | measured (cap $12) |
| Scan-free rebuild | 10-31 | about $0.49 | measured; eval-build box at $0.60/h, end cost not recorded |
| G2 batch (two boxes) | 11-02 | about $8.31 | box 1 est. $2.80; box 2 measured $5.50 |
| G3 batch | 11-03 01:59 to 03:47 | $7.47 | measured (cap $15) |
| Rack round R | 11-03 | $5.95 | measured (cap $10) |

The listed figures sum to about $29.5. That exceeds the up-to-$25 credit relayed on 10-29, and the notes do not reconcile it. Credit balances in notes: $123.65 (10-29), $127.84 (11-02), $94.58 (11-03 01:49). Result-event total_cost_usd fields are cumulative and were not summed per turn.

## 3. Owner decisions and approvals (as quoted or relayed)

- 10-27, "do all the improvements" (relayed): read as go-ahead for C0.
- 10-29, "go batch 1" / "go batch 2": requested; approval implied by later reports.
- 10-29, up to $25 Vast credit for mesh work (relayed from another owner session).
- 10-30 13:21, "GPU rentals from now on go ahead without asking." Conflicts with the repo's per-batch rule; flagged.
- 10-31 05:10, "permission for everything" (relayed; covered the eval-10 retrain).
- 10-31 08:34, "Mostly yes." 08:42, "slot" = notch cut into the boards.
- 10-31 16:37, "Ship 9a, flagged."
- 11-02 08:34, "minimal variant" approved for blue cup; 08:37, as-is chosen.
- 11-02 08:49, option A approved (relayed).
- 11-03 01:49, G3 approved as pre-registered ($15 cap). 05:50 and 06:44, pack 13i approval and "go in all" (relayed).

Open at last read: eval-25 board slot (firm no given 11-01); deletion of 12.4 GB SAM 3D weights (default keep); WeVisOne test; sweeper rebuild with two balls; C0 blue cup as separate submission; pack 14p1 (on hold); scan-free pot and beige choice; grey-template tracking test. The 10-27 04:00 question "Do you want me to build it, and in this order?" was followed by a build start at 04:06 (go-ahead implied, not quoted).

## 4. Failures and corrections

- Ground-truth leaks: 7 mm marker-ball radius from public scans (admitted 10-27 17:23); lid and rack wall thicknesses (re-run 10-27 07:13); pot, lid and rack values in eval builds (replaced 10-31); public-scan copies in scoring folders (removed 11-01).
- Gate failures: POSEFIX (10-31, -0.0107 vs +0.002); own-video re-track (10-31, -0.170 vs +0.01); pitcher and rack rebuilds (10-31, nothing packed); collision carve rounds (none shipped); board slot (eval 25 firm no).
- Claims corrected: "big win" generator framing (10-30 06:23, corrected 06:33); lid-on-pot SAM failure (10-30 12:08); eval-14 and eval-32 "in table" readings (11-01, hand-contact frames); board 2 flip at scorer settings (11-02 20:26).
- Chooser error: 6.8 cm solid box for board 2 (10-31 08:08); flip-prone rule not tweaked after scoring.
- Ground-truth selection (disclosed): pack 13h (best of 264) and pack 13i (best of 79).
- Recorded conflict: 10-31 17:09 says the three accuracy wins failed the pose check; the 16:11 pose checks passed for pot, lid, rack and blue cup.
- Simulator contact limit: cup pieces overflowed (about 6 million per seed); board pieces 57 and 77 overflowed in all runs; a 256 vs 512 contact unit discrepancy is flagged.
- Permission denials: CPU Hunyuan3D test (10-26; sandbox "code from external"); Bash copy of library_c0 GLBs (10-31 15:44). Recorded, not judged.
- Tooling and ledger: hf CLI 2.2.0 --include bug (11-02); shared-ledger script could erase lines on concurrent writes, fixed 10-29; one helper duplicated an actual-cost line five times (G3; four removed).

## 5. Usage-limit pauses

- Weekly limit: 10-27 18:31 to about 10-29 21:00.
- 5-hour limits: 10-29 23:51 and 23:58 (reset 2am); 10-30 10:20, 11:12 (reset 12pm), 15:13 (5pm), 19:40 (10pm); 10-31 00:13 (3am), 06:51 to 07:04 (8am).
- Effects: partial runs restarted (stage 1b on 10-29 21:06 and 10-31 08:08); WIP snapshot commits preserved work.

## Lessons

- Measure the mesher, not just the observations. Stereo points were about 1 mm accurate; the mesher's 12 to 20 mm slabs were most of the error, and a thin-wall fit to points recovered much of it on the blue cup.
- Rule-first gating worked in both directions: the blue cup was held because its rule came after scoring (10-31 15:48); a trimmed rack was rejected at 0.016 against a 0.02 bar.
- Scan leakage recurred and was found by review, not by a gate. Keep a per-constant provenance list before each build.
- Best-of-N selection against public scans inflates scores (oracle best-of-all 0.315 vs library 0.477; the ground-truth-free metric agreed weakly, Spearman 0.46). Mark every GT-selected pick.
- Plain shapes flip under registration; marker balls and slots broke symmetry. Even so, the shipped board 2 flipped in 34 percent of audit runs.
- The simulator's contact budget (512 rows; 380 used as a hard cap here) rules out many physically plausible fixes. Check the budget before building pieces.
- Shape gains did not always carry to pose (pack 12d dropped pose on 7 pairs). Track shape and pose boards separately.
- Generative models: multi-view (Pixal3D-MV) beat single-image models on registration (median ADD 10.3 vs 26 to 29 mm) but flipped boards and the sweeper. The $4.36 probe was cheap; the largest cost was time lost to usage limits.
- Ledger and credit: reconcile per-run costs against the credit balance before the next batch.
- The 10-30 standing GPU go-ahead differs from the repo's per-batch rule; settle which governs before the next rental.

## Coverage

- Oldest result event reached: 2026-10-26 16:33:39 UTC. Paging continued until the list returned no further pages (no has_more), so session start is reached.
- Newest result read: 2026-11-03 about 09:34 UTC.
- Pages: roughly 200 list pages (pre-compaction pages 1 to 165 plus later pages). Pages with no result events were counted as empty.
- Gap check: 10-27 04:00 to 10:13 was read in full this pass (results at 04:00, 04:06, 07:13).
- Pre-compaction notes (pages 1 to 165) were carried over from the progress file and not re-read from the API in this pass. The 10-26 17:44 page was re-read to confirm its content.
