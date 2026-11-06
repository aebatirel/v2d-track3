# Lane chat digests (14 sessions)

## Coverage and method (read first)

- Titles, created/updated times and the `get_session` usage cost were read for all 14 sessions.
- `list_events` with `kinds: ["result"]` returns only the result events found in each 100-raw-event page, so a page holds 0 to about 6 results. The full transcripts (many pages each, `has_more` true for every session) were not paged to the start. **Coverage is the newest page per lane: the final 1 to 6 turn summaries, usually covering the last 1 to 3 days of work.** Experiments that ran earlier than those summaries are not in this digest.
- `total_cost_usd` in a result event is the session's cumulative Claude (LLM) cost, not GPU rental. GPU dollars below are only those a lane stated in its own text. The `get_session` usage `cost_usd` differs slightly from the result value (noted per lane).
- Dates are UTC. Quoted numbers are as the lane reported them; "estimate" marks the lane's own estimates.

---

### Policy development review (session_01D9UJC8kwkZnQELxSNreZD1, 2026-10-30 06:46 to 2026-10-30 08:27)

**Goal (from title and turns read):** a review and write-up of the RL policy work: the learner, the grasp lock, and the eval campaign.

**Newest page (3 result events):**
- 08:14: subagent hand-back on the grasp-lock learner. Read-only; nothing edited, run or rented. Covers the recipe stages, the flags, the spoon history and where it fails.
- 08:27 (final, 19 turns, result `total_cost_usd` 26.92; `get_session` usage 26.86): the 10-part learner report is committed on `claude/magical-mccarthy-v8tmyi`. Its appendix lists the learner files, the videos and seven places where its own records disagree.
- Two findings flagged by the lane, not re-measured here:
  - The grasp lock's "fine-tune" is not a continuation of earlier weights. It is a fresh 70M-step run on a reference that already carries the object.
  - A 70M run ends before the training assist is fully switched off, so those policies never train under the exact conditions they are scored in.
- Open item: `main` is one commit behind the branch. The lane offered to bring `main` up to date.

**Experiments with numbers:** none in the newest page beyond the above. The report's section list (learner comparison, eval-10 saga with six failed attempts, variance charts, 14 open hypotheses) was not read in full.

**GPU $:** not stated in the pages read.

**Recommendation (lane):** keep the two-learner comparison as the basis for the technical report, and treat the training-assist mismatch as an open hypothesis.

---

### Embodiment options (session_01D9UJC7MhytodZodnDDAU3z, 2026-10-30 09:00 to 2026-11-01 08:56)

**Goal:** embodiment and contact questions (hand knocks, contact limit, recipe, collision pieces) for the RL policy.

**Newest page (3 result events; final at 08:56, result `total_cost_usd` 348.96; `get_session` usage 340.46).**

*Hand-knock check (CPU replay, six evals, hands moving vs parked):*

| Eval | Object | Hands moving | Hands parked | First touch |
|---|---|---|---|---|
| 5 | pot | 26 mm | 3 mm | fingertip, frame 3 |
| 8 | pot | 42 mm | 9 mm | fingertips, frame 13 |
| 33 | spoon | 87 mm | 11 mm | palm, frame 24 |
| 16 | spoon | 18 deg | 29 deg | none (spoon twists more with hands away) |

- Eval 3: a 65 mm pot motion from the pack run did not reproduce on CPU.
- Evals 5, 8, 33 score 0.94 to 0.97, so a fix could not clear the +0.02 bar. Set aside.
- Bug caught by the lane: its contact log parsed object bodies wrongly (they are named `track3_<obj>_object`). Fixed before reporting.

*Contact limit (a key finding of the night):* training hit the simulator contact limit (njmax). On eval 10 this produced about 8 million overflow warnings. Fixing it lifted tracking from 0.46 to 0.91 in the pack session's own check. Scoring never hit the limit.

*Recipe screen:* no recipe change won. Learning-rate change, start nudges, solver references and the slip-aware policy all failed their rules. Target smoothing failed its rule. GPU spend for the screen was about $30 (lane's estimate).

*Collision pieces checked:*

| Pieces | Result |
|---|---|
| Eval 10 cups, v4 and v5 | clean |
| Eval 14 racks | rejected |
| Eval 20 pitcher | clean, cup stable |
| Eval 24 boards | do not use |

**Open items and decisions (lane's recommendations):**
- Retrain of eval 10 (estimate $3 to 5). Lane's strongest evidence.
- Fix tracked rest poses for evals 3, 16, 1, 14, 30 and the ep2 lid failures (estimate $5 to 10).
- Public ep2/ep12 higher-limit test (about $7). Gain beyond eval 10 probably small.
- Whether a policy trained at the higher contact limit can go into a pack: the pack session asked the owner and was waiting.
- Solver v2 and synergy test B: not done, lane recommends skipping both.

**Crossed message:** the lane listed eval-20 checks as its next item, but had already finished and sent them. It told the coordinator.

**Verdict:** eval-10 retrain is the top item. Contact-limit overflow is the main bug of the period.

---

### Performance vs. NVIDIA methodology (session_01D9UJC9HM6HuNGNhAzddH4G, 2026-10-30 13:44 to 13:52)

**Goal:** a comparison of our pipeline against NVIDIA's default Track 3 pipeline.

**Result (final, `total_cost_usd` 2.35):**
- NVIDIA's default pipeline plays the demonstration at half speed. The submitted file at frame f holds about frame 0.5 x f, so the second half of each motion is dropped.
- Measured on the 20 public episodes, CPU only, $0. Taking true poses and applying only that timing effect, then scoring with the official kit:

| Setting | AUC | SP-SR | MP-SR |
|---|---|---|---|
| NVIDIA default timing, everything else perfect | 0.415 | 0.30 | 0.00 |
| "Nothing moves" (objects never touched) | 0.446 | 0.45 | 0.00 |
| Our leaderboard result (hidden eval episodes) | 0.8146 | 0.85 | 0.65 |

- The 0.415 cap is for NVIDIA's defaults as shipped. Anyone who fixes the timing would score higher. The lane's floor value matches the one logged on 12 Oct, so the scorer is consistent.
- Different episodes: public versus hidden eval. Not a head-to-head.
- Indicative only: NVIDIA's Track 2 posted baselines are 0.510 AUC (multi-view reconstruction input) and 0.002 AUC (own reconstruction from video). Different task and inputs.
- No direct Track 3 baseline exists. Their Track 3 pipeline handles one object per episode and assumes 30 fps. 13 of 20 public episodes have two objects, and the video runs at 20 fps.

**Options given to the owner:** ask the organisers for a Track 3 baseline (free), or run NVIDIA's pipeline with only the fixes it needs (timing, multi-object). Lane's estimate: $15 to 20 for the 7 single-object episodes, or $60 to 70 for all 20, plus setup. Nothing rented; needs go-ahead.

**Verdict:** the 0.415 figure is a cap on NVIDIA's defaults, not a measured Track 3 score.

---

### V2D Challenge team registration (session_01D9UJC6UxWpipwjiLiNaMv1, 2026-10-30 18:26 to 2026-10-31 11:23)

**Goal:** the Kaggle and organiser registration and repository access requirements.

**Findings (final, `total_cost_usd` 5.83; `get_session` usage 5.79):**
- The repository was public from about 11:02 UTC on 31 Oct. The lane scanned every branch and the full history and found no leaked keys or tokens. The 0 forks and 0 stars were as of the lane's check.
- Kaggle Track 3 rules, section 8.d: accepting the rules enters a team on the leaderboard only. A team must also complete the registration form before the end of the competition period. An unregistered team may be excluded from prizes and results "even if it appears on a leaderboard".
- Rules section 9.a: every submission's commit link must point to a repository shared with the organisers' GitHub account.
- Deadline stated in the lane: 4 Nov, 22:00 UTC.

**Actions and advice:**
- Late-registration email: the draft was still unsent in the Gmail draft folder. The lane said it must be sent before any note claims "I've emailed". The lane did not send it.
- Repository: make it private again, then add the organisers' account as a collaborator. Do not rename it. Renaming breaks old commit links if the old name is ever reused; and a rename hides nothing once private.
- The lane was told by the coordinator to leave registration and organiser contact to the owner, and to work only on performance. It recorded that rule in its decisions file.

**Crossed message:** the lane's draft note to the organiser said "I've emailed", while the email was still a draft.

**Verdict (lane):** the leaderboard listing is not registration. Registration and repository sharing are separate requirements and both were open at lane close.

---

### New score status (session_01D9UJC7rdn1DZrNM1rKyE7b, 2026-10-31 14:46 to 2026-11-02 06:43)

**Goal:** tracking the public-leaderboard position and choosing which pack to submit.

**Board numbers (lane's own table, as reported):**

| Board | Pack 10 | Pack 11 | Pack 12b |
|---|---|---|---|
| AUC | 0.8192 | 0.8392 | 0.8441 |
| SP-SR | 0.85 | 0.85 | 0.85 |
| MP-SR | 0.65 | 0.70 | 0.75 |
| RPE (cm) | 3.68 | 3.18 | 3.02 |
| MPPE (cm) | 2.85 | 2.55 | 2.50 |
| CD-O | 0.332 | 0.332 | 0.332 |

- Pack 11: the eval-10 policy follows the lane's reconstructed motion 0.37 better than pack 10's. It fails 0 of 10 runs (before: 10 of 10). Lane's board estimate was about +0.017 AUC; measured board gain +0.020 AUC and -0.5 cm RPE from that one episode.
- Pack 11 was trained at a contact limit of njmax 1024 (standard 512) and scored at standard settings. The owner's scope was disputed in the record. The lane recorded that the owner had given an explicit go-ahead for packing at standard eval settings, and that the training difference must be disclosed in the technical report.
- Pack 12b: fixes to evals 14, 32 and 16. Rank sum 61, 10th overall (up from 11th). AUC gap to 9th place (DSAIL, AUC 0.849 now) is +0.005 on rank sum 60.
- Since 31 Oct: AUC 0.8146 to 0.8441, RPE 3.93 to 3.02 (lane's figures).
- Plan: pack 11 or 12b as the single final submission, keeping the organisers' re-run package to one file.

**Pass or fail:** no gate in this lane; the verdict is ranking.

**Verdict (lane):** pack 12b is the current best on the board. Passing 9th needs +0.005 AUC or -0.18 cm MPPE, or one more successful MP-SR episode.

---

### GRASP physics retargeting sampler (session_01D9UJC8CjzgvbaFYA5wbvPg, 2026-11-01 11:48 to 23:50)

**Goal:** test the GRASP search method inside our FlashCHORD solver on ep13 (eval 14's public twin).

**Setup:** GRASP added as `solve.py --method grasp`, re-implemented from GRASP's own MIT-licensed optimiser. Our existing solver unchanged. Paper widths are narrower than ours; any gain could come partly from width.

**Pre-registered tests (registration frozen in commit d8544cf before any ep13 result):** score is the average over 16 replays with small control noise. Pass = GRASP beats our solver by at least 0.05 on the perceived reference.

| Test | GRASP minus ours (perceived) | GRASP minus ours (true motion) | Verdict |
|---|---|---|---|
| A: references as specified | 0.000 | 0.000 | FAIL |
| B: rebuilt with both hands holding | +0.024 (range -0.07 to +0.12) | -0.027 | FAIL |

- In test A neither solver changed a frame. The left hand is parked the whole clip and the right hand takes the cup only after it has risen.
- Test B: a single-replay +0.10 mostly disappeared under noise.
- With true motion, eval-14-style construction gives followability 0.672 for ep13, against 0.573 for doing nothing. With perceived motion, every construction stays below doing nothing.
- Gap: tracked cup within about 1 cm and 3 to 8 deg of true at pick-up; hand-cup relation off by about 3 to 4 cm.

**Fixes tried (none passed):**
- Removing the cup's invisible spin: the robot followed the cup worse. Cross-check by the physics lane: spin made worse on 5 of 6 cups; ep11 -0.008.
- Track cleaning: failed its pre-registered public test. Accuracy vs true motion +0.002, but followability -0.018.
- "First picker" option (`--single_hand 2`, eval 14's construction): works with true motion, not yet with perceived.

**Later results from the perfect-following session (reported in this lane, not re-measured):**

| ep13, doing nothing about 0.542 | Seed 42 | Seed 43 |
|---|---|---|
| One hand (as packed) | 0.378 | 0.554 |
| Both hands | 0.587 | 0.553 |
| First picker | 0.555 | pending |

- Two-hand average gain +0.104, past its +0.05 bar, but fragile: seed 43 both at do-nothing level.
- Evals: eval 14 two-hand 0.603 and 0.581 vs packed 0.727; eval 16 two-hand 0.713 and 0.696 vs packed 0.850. No swap.
- Eval 14's repaired reference (19 cm perception jump at frame 46 repaired): one-hand policy 0.880 ± 0.054 vs packed 0.727. Confirmation runs pending.

**GPU $:** none (all CPU in this session; $0).

**Verdict (lane):** GRASP does not beat our solver on ep13. Eval 14's limit is the perception jump, not hand assignment. Commits: 83a2230, d8544cf, 660b5af, ff2d078, 5ca1c20 (lane); 33f0a59 (the eval-14 log).

---

### Perfect following of perceived trajectory (session_01D9UJC8Nz9EEFNmz2yzimzN, 2026-11-01 19:56 to 2026-11-03 08:31)

**Goal:** make the policy follow the perceived reference; owns GPU retrains for the pack.

**Newest page (2 to 3 results; final at 08:31, result `total_cost_usd` 104.68; `get_session` usage 104.73):**
- Pack 14p board losses reported by the lane: SP-SR 0.90 and MP-SR 0.80 (these are board numbers as reported; not re-measured).
- Against the lane's own references, pack 14p's submitted rows pass both success criteria on all 20 episodes. So retraining cannot recover a success-rate episode; only more accurate references can.
- Closest objects to the 3 cm limit (share of limit): eval 10 beige cup 1.85 cm (0.62); eval 30 sweeper 1.82 cm and 11 deg (0.61); eval 14 blue cup (0.59); eval 28 pot (0.56).
- Board policies over 10 draws each: every episode passes the per-scene criterion every time. The per-object criterion fails once in 10 on evals 1, 20, 28 and 30.
- Likely cause of board failures: reference error, most likely on the spoon as scene anchor (evals 32, 33, 35 to 37), the boards in eval 25, and eval 30's sweeper.
- The lane corrected a reference map it had given the tracking session: two wrong store paths (evals 1 and 28). Files are byte-identical at the corrected paths. A new scoring tool `tools/sr_vs_ref.py` and results `docs/analysis/sr-vs-ref-20261103/` are pushed. CPU only, $0.

**Earlier (in the same newest page, 06:44 on 3 Nov):** episodes 14 and 32 use pack 12b's repaired references; all others use the standard table. Packs 13f, 13p2 and 14p changed meshes and policies for evals 14, 15 and 20, but no reference.

**Verdict (lane):** board failures point to reference error, not policy. The corrected map is pushed.

---

### Physics-informed perception correction (session_01D9UJC6vSSNiJqaAdzNUn7d, 2026-11-01 19:59 to 2026-11-02 07:34)

**Goal:** use physics to correct perceived object trajectories, on public episodes only.

**Gate (pre-registered):** mean ΔAUC at least +0.003; no episode below -0.01; MPPE and RPE not worse on average. Baseline reproduced exactly on all 20 public episodes: mean AUC 0.8769.

| Idea | What was tested | Public ΔAUC | Gate |
|---|---|---|---|
| 1. Frame-0 tilt | Anchor tilt averaged between tracker and mesh's nearest stable resting pose (P1) | +0.00156 (13 better, 0 worse) | FAIL (too small) |
| 1. Frame-0 tilt | Pot/cup symmetry axis as up prior | +0.00067 | FAIL, below P1 |
| 2. Multi-frame init | Already tested 30 Oct as `refine.py` step S3 | -0.0013 | not repeated |
| 3. Cup twist | GRASP's twist tool, checked vs mocap | worse on 5 of 6 cups; ep11 -0.008 | FAIL |
| 3. Cup twist (hold only while resting) | Exploratory, not pre-registered | AUC unchanged; twist better on 6 of 6 cups | not pre-registered |
| 4. Lower floating objects to table (F1) | "No mover, no motion" | +0.00142 (2 better, 0 worse) | FAIL |
| Stack P1 + F1 | Combined | **+0.00298** (14 better, 0 worse; MPPE -0.028 cm; RPE -0.011 cm; 95% CI +0.0008 to +0.0059) | **fails mean clause by 0.00002** |

- The stack was not rounded into a pass.
- Upper bounds: a perfect anchor tilt is worth +0.0164, of which about 70% is the water pitcher on ep21/22. The pitcher has a consistent 6 deg tilt error because our mesh is missing about half its base. Constant per-object position error: upper bound +0.030, concentrated in ep24, ep31, ep11.
- Board value of the stack: about +0.002 AUC (lane's estimate), only after retraining each affected eval policy (about $3 to 6 each). Lane recommends no GPU money unless references are rebuilt anyway.
- Handover: `qa_physics.py` (read-only, ground-truth-free check for impossible tracks). On public it flags ep0's lid and ep23's board swap, plus one false positive. ep0's lid alone costs -0.025 of the public mean.
- Proposed GPU work, needs owner go-ahead: a complete-base pitcher mesh (upper bound +0.012 public AUC, about $1 to 3) and re-detection of flagged episodes (about $1 to 2 each).
- Hold-filter idea (from the GRASP lane's reply): public accuracy +0.0017 AUC, but followability -0.018 on ep2, 12, 13 and 31. Recorded as failing.

**Verdict (lane):** no pre-registered gate passed. CPU lane closed on 2 Nov; GPU re-runs handed to the tracking session.

---

### Perception accuracy on public episodes (session_01D9UJC9EUCs5sUCbTVZgvcC, 2026-11-02 07:17 to 2026-11-03 10:00)

**Goal:** answer a hand-aware session's questions about the public perception setup.

**Newest page (final at 10:00, result `total_cost_usd` 85.79; `get_session` usage 85.82):**
- Answered five questions: controls, mesh set, scoring, masks, failed approaches.
- Control tracks: 9 episodes from `ptrkA` run's C variant; 10 from `ptrkB` run's C variant; episode 23 from `ptrkD` Cr variant with the board identity fix. Noise floor from the Cr and C2 re-runs in `ptrkD`.
- The lane told the hand-aware session not to use `ptrkF/Ct` as a baseline: Ct is the failed tracking-with-submitted-meshes test.
- Mesh set committed as `meshes/m14p_public/` (14p payloads, with the 13f pitcher swapped in, since 14p's pitcher is placed for eval 20).
- Scoring: `score_registered.py` with 10 seeds. Identity-fix command for ep23 given.
- Public SAM2 masks for all 20 episodes are in `ptrkD/MRr`. Mask locations corrected to all under `ptrkD`.
- No public hand outputs found in the store; the ones seen belong to eval references.
- Failed approaches listed for the hand-aware session. End-of-task board merge in ep23 (frames 240 to 324) suggested as a test for its post-processor.

**GPU $:** none stated in the newest page.

**Verdict (lane):** nothing running. Answers handed over.

---

### 3D mesh generation accuracy research (session_01W8Softjo2xx7o6ofSiheuQ, 2026-10-26 15:15 to 2026-11-03 12:20)

**Goal:** generate and select rack, cup, lid, sweeper and beige-cup meshes for the CD-O board; the lane runs the GPU mesh batches.

**Newest page (final at 12:20, result `total_cost_usd` 2218.71; `get_session` usage 2249.03; the usage is LLM cost, not GPU):**

*Rack round R (run `mesh-20261103-r-63eb2c5`, code at 63eb2c5):*
- Instance: H200 NVL, New Mexico, $3.90/h. Measured cost **$5.95** from the Vast record (1.475 h runtime, $5.75 compute, $0.19 down, $0.01 up). Cap $10. Box destroyed 09:09:37 UTC; nothing rented.
- Freeze commit cf30b25c, pushed before any scan read.
- R-gen (generated / failed): SAM 3D 120 / 0; Hunyuan3D-2.1 120 / 0; TRELLIS.2 at 1536 120 / 0 (1024 fallback never used); Pixal3D-MV 30 / 0 (every view set has one view).
- Stage 1 (6-seed CD-O medians, 390 records, 0 errors): 5 of 390 beat 0.4016; none reached rule A's bar of 0.3816. Six lowest went to stage 2. Best: Hunyuan ep12 k18 s31337 at 0.3876.
- R-prim: 39 primitive fits; `fit.py` requires at least 12000 faces, and the prim fits have 958 to 3568. Midpoint subdivision (same surface) first; 35 of 39 then fitted. Four ep26 prims have no t3fit copy.
- Stage 2: 120 candidates committed (beeee61b). All pass `budget_mesh(4096, 4096)`; no duplicates.
- 50-seed audit of all 120: no errors. Only one new rack qualifies: 0.3775 vs 0.4016 for the current rack 13i. Alignment error 4.3 mm to 3.7 mm. No flip in 50 runs. Best primitive fit 0.4113, does not qualify.
- Pack 13j (built by the pack session on 13i): rack width 161 mm to 129 mm; flip check clean in both scan modes. Expected shape-score board 0.2418 to about 0.2384 (estimate); third place at 0.2390 "a coin toss" (scorer noise about ±0.002, lane's estimate).
- Selection is ground-truth-informed (best-of-N by public-scan CD-O); the lane states this in its README.

*Cost to date (lane's stated GPU spend):* G2 $8.31, G3 $7.47, rack round $5.95 (measured).

*Tooling problems recorded:* hf CLI weight-download bug (fixed by a Python fetch); HF 502 errors after the commit had landed; ledger helper wrote the actual line four times (three duplicates removed); store push returned HTTP 524 but completed with a clean exit code; container restarted twice, which stopped the G3 audit (24 meshes left; queued to resume).

**Verdict (lane):** rack round done. 13j confirmed; beige cup audit still running on the lane's last check.

---

### Room map: drift-free camera tracking (session_01D9UJC6AegGiAjYM6ukSfHj, 2026-11-02 16:03 to 20:07)

**Goal:** a ground-truth-free room map to give drift-free camera poses for the eval and public episodes.

**Gates (pre-registered, be2f920):** G1 build bar 0.01 AUC upper bound; G2 public swap test (no episode below -0.01).

**Results (final, `total_cost_usd` 10.00; no GPU spent):**
- Map built from public videos only (`pipeline/roommap.py`). Full map registers all 370 public images. Relocalises 100% of frames on all 20 eval clips and on the 19 public episodes with control runs (minimum 442 matched points per frame).
- Eval drift (no ground truth): perc2's object positions differ from the map by 2 to 9 mm (p95) on 19 of 20 clips; eval 35 reaches 18 mm. Mean upper-bound AUC gain 0.0029, below the 0.01 bar. **G1 failed.**
- Public leave-out vs mocap, 19 episodes: mean ΔAUC +0.0070, ΔMPPE -0.081 cm. ep24: +0.148 (0.834 to 0.982), ΔMPPE -1.38 cm; the other 18: -0.0008, ΔMPPE -0.008 cm. ep22 lost 0.0164, below the -0.01 floor. **G2 failed.**
- With ep23 added (control replicate from perception-tracking, identity fix on both): map 0.6643 vs control 0.663; all 20 public mean ΔAUC +0.0067, ΔMPPE -0.076 cm.
- By AUC: map closer on 7 episodes, perc2 on 10, 3 ties.
- Option (not pre-registered): use the map camera only where its bound is at least 0.02. On eval this selects eval 35 alone, worth about +0.002 board AUC (lane's estimate). Needs one reference rebuild and retrain (about $3 to 6, estimate) and a new pre-registration. Public support is a single episode (ep24).
- Eval 35 is the one eval clip that resembles ep24 (18 mm off, 16 keyframes vs 17). If ep24's 84% realisation held, about +0.047 on that episode (estimate).
- Camera poses exported for all 20 public and 20 eval clips to the HF store under `runs/20261102-roommap-6438495/world_T_cam/`.
- Stop: the lane was asked by the perception session to build a "camera guard" (switch cameras only where they disagree). The lane argued that the threshold would be chosen after seeing public scores, so the public check would not be independent. The coordinator stopped the work. The lane reports the owner had put steps beyond step 1 on hold pending a credit top-up.

**Verdict (lane):** eval 35 is an optional arm for the perfect-following session after the top-up, needing its own pre-registration. Stopped at f0402c08 with nothing running.

---

### Point tracks: catch and repair lost object tracks (session_01D9UJC72kCbx1mWTB2pwupw, 2026-11-02 17:07 to 20:07)

**Goal:** catch and repair lost object tracks with point tracking (OpenCV KLT on CPU; BootsTAPIR as a possible GPU arm).

**Pre-registration (9203ccd, before scoring):** primary arm repairs only frozen or lagging tracks; report-only arm repairs every flag. Gate: mean AUC gain at least +0.005; no episode worse than -0.01; mean MPPE not worse. Lane expected a fail; ep23 expected not to recover.

**Results (20 public episodes, $0, no GPU):**

| Arm | Mean ΔAUC | Better / worse | Worst episode | Mean ΔMPPE | Frames more than 3 cm off (control to arm) |
|---|---|---|---|---|---|
| Lag-only repair (primary) | -0.058 | 0 / 6 | ep42 -0.366 | +0.27 cm | 955 to 1,115 |
| Repair every flag (report-only) | -0.132 | 2 / 10 | ep42 -0.754 | +0.92 cm | 955 to 1,609 |

- Only gains: ep11 (+0.053) and ep40 (+0.010), both in the report-only arm.
- Why it failed: most flags were false. Of 17 flagged spans only 5 fall where the control's own track is more than 2 cm off, one of them ep23. In most flags FoundationPose was right (0.4 to 1.5 cm) and the point tracks were wrong. KLT points drifted onto the hand or background during grasps and fast motion on white and light-wood objects.
- ep23: the two boards' identities are swapped, and the scorer's frame-0 alignment hides it. `pipeline/identity_fix.py` fixes it on the public control (AUC 0.041 to 0.663). A point-track check cannot fix identity.
- Other finding: perc2's frame-0 detection mask for the ep0 lid sits on the pot handle; FoundationPose still tracks the lid correctly.
- No BootsTAPIR run: the coordinator's condition (real losses that KLT dropouts kept from being repaired) was not met.
- Room-map session's new camera poses were not used: the check compares point motion against the tracker under the same camera, so camera quality cannot change this verdict.

**Verdict (lane):** test failed; closed at $0. Last commit 922365c (and 1745c9f on the branch).

---

### Object-specific pose networks: pot proof of concept (session_01D9UJC5VUFMLYBMNxA8FsXe, 2026-11-03 06:41 to 08:45)

**Goal:** test a pot pose network against the tracker on four held-out pot episodes.

**Gates:** main gate: pot AUC gain at least +0.02 (the lane noted it could never pass: tracker averages 0.983, so the maximum gain was +0.017; told the coordinator before training). Backup criterion, added before training at the coordinator's request: median pot error down 20% with no episode worse.

**Results (scored per frame with depth fitting; pot AUC):**

| Version | Ep 2 | Ep 27 | Ep 44 | Ep 45 | Mean ΔAUC |
|---|---|---|---|---|---|
| Tracker | 0.9935 | 0.9677 | 0.9979 | 0.9742 | — |
| R (rendered images only) | -0.003 | -0.257 | +0.002 | +0.000 | -0.065 |
| R+M (R fine-tuned on training-episode mocap) | -0.001 | -0.035 | +0.001 | +0.001 | -0.0085 |

- Both fail both gates. R+M cut median error 39% on ep2 and 10% on ep45, but got worse on ep27 and ep44.
- Failure is mostly ep27, where the pot is lifted by hand and rotation is about 10 deg off. The rendered pot interior does not match the real one.
- Without depth: worse in both versions. Combined with the track: -0.0023 mean, still not beating the tracker.
- Spoon: render-only loses 0.26 AUC on ep27; the spoon has no public mocap, so a render-only spoon network would not be trustworthy.
- Own PyTorch network trained on the submitted pot mesh with the lane's renderer. GDRNPP not used (its software stack does not run on the image). FoundationStereo and FoundationPose are non-commercial licences; both already in the pipeline.

**Cost:** about $0.8 (one RTX 4090 for about 1.4 h, lane's estimate from instance hours). First attempt died within 2 minutes because `.gitignore` excludes `.npz`; files were force-added and the run restarted on the same box. Box destroyed.

**Verdict:** pot network fails; recommend not extending to other objects and not building a spoon network this way. Commit 5f55ec1f.

---

### Hand-aware object tracking for held phases (session_01D9UJC9SwoRsF13MYzwtVyh, 2026-11-03 09:57 to 11:39)

**Goal:** a tracker that handles the phases where an object is in the hand.

**Pre-registration:** pre-registered holdout gates. Addendum 1 (86a2b94) changed gate 1 to "held-phase mean ADD at least 10% lower, or held-phase AUC +0.01" before any holdout episode was scored. The lane says this was recorded and told to the coordinator; the original gate text is not in the pages read, so this change is a point to check.

**Holdout (13 public episodes, 10-seed registered scoring; settings frozen before scoring; CPU, $0):**

| Gate | Result | Required |
|---|---|---|
| Whole-episode mean AUC change | -0.0042 (run-to-run noise 0.0015) | at least +0.005 |
| Worst episode | ep24 -0.047 | at least -0.01 |
| Held-phase mean ADD | -4.3% | -10%, or held AUC +0.01 |
| Held-phase AUC | -0.0006 | alternative to the line above |

- ep24: board 2 moved about 21 cm while real error along the camera ray was about 2 cm; MP-SR fell from 0.9 to 0.0.
- ep26: rack moved 4 cm though never held (-0.006). ep23: board 2 moved up to 24 cm (-0.0025).
- Other 10 episodes essentially unchanged (only ep40, +0.0004).
- Development episodes: ep18 AUC 0.9246 to 0.9487 (sweeper excursion corrected); ep13 cup +0.007.
- Failure reading (lane's, not separately tested): on thin flat boards the depth check picks up the surface behind the board; the hand-proximity trigger fires on objects nobody holds.

**Other measurements:**
- Errors during handling lie mostly along the camera ray. Removing that component with perfect knowledge: +0.0195 mean AUC on public (ceiling, not a result). About 70% of public AUC loss is in frames where the object is handled.
- Holding the object fixed to the MediaPipe hand frame: -0.01 to -0.8 AUC per episode (measured on the failed control Ct; lane says the conclusion carries over).
- Early diagnostics used the wrong control (Ct). Redone on control C with the 14p public meshes.
- Literature: HOLD, MagicHOI and HaWoR do not transfer (monocular, no template, hours per episode). MANO, WiLoR and HaWoR are non-commercial.

**Verdict (lane):** failed; no phase 2 and no restricted sweeper-and-cups variant. Coordinator agreed. Closed at 7502ccf with $0 spend. Remaining losses are board merge, pitcher template, and errors the stereo depth itself agrees with (ep11).

---

## Cross-lane lessons

- **Almost every pre-registered test failed, by small margins.** Physics stack +0.00298 vs +0.003 gate (missed by 0.00002); GRASP test B +0.024 vs +0.05 bar; room map eval bound 0.0029 vs 0.01; hand-aware -0.0042 vs +0.005. Gate design and noise (run-to-run noise about 0.0015) decide these.
- **Gate edits are a risk.** Hand-aware addendum 1 changed gate 1 before holdout scoring. The lane recorded it, but it should be checked against the original pre-registration.
- **Public gains are small, so eval transfer is uncertain.** Every idea with a public result below +0.005 AUC was closed or left as an optional arm.
- **Reference and control errors masqueraded as policy or perception problems.** Pack 14p's board failures traced to two wrong store paths (evals 1, 28); hand-aware used the failed control Ct; GRASP's ep13 failure was a reference with a parked left hand. Check references and controls first.
- **Frame-0 alignment hides identity swaps.** ep23's board swap is invisible to the scorer's frame-0 alignment; the fix is `pipeline/identity_fix.py`, which had only been run in the eval pipeline.
- **The pitcher mesh is missing about half its base.** It is the largest single bias found (about 6 deg tilt on ep21/22; upper bound +0.012 public AUC). Three lanes found it independently.
- **Contact-limit (njmax) mismatch.** Overflow at 512 caused about 8 million warnings on eval 10 and a 0.46 to 0.91 tracking difference in the lane's check. Pack 11 used njmax 1024 for training and standard settings for scoring. Disclose it in the technical report.
- **Repository exposure and rules.** The repo was public from about 11:02 UTC on 31 Oct. Rules 8.d and 9.a: a leaderboard listing is not registration, and commit links must point to a repo shared with the organisers. The late-registration email was still a draft at lane close. Verify each item.
- **Cost reporting needs GPU and LLM figures apart.** `total_cost_usd` is LLM cost (up to about $2.2k for the mesh lane's session). GPU spend stated in lane text: G2 $8.31, G3 $7.47, rack round $5.95 (measured), pot network about $0.8, others $0.
- **Crossed messages and overlaps.** Two sessions worked on ep13 at once (GRASP and perfect-following). The registration lane's note said "I've emailed" before sending. The room-map lane's camera guard was offered to the coordinator, then stopped. Keep one owner per experiment.
- **Infrastructure problems recur.** HF 502 and 524 errors (the push finished despite 524), an hf CLI weight-download bug, `.gitignore` excluding `.npz` so a GPU job died in 2 minutes, container restarts that stopped a mesh audit, and `fit.py` needing at least 12,000 faces.
- **Coverage caveat.** This digest reads each lane's newest page only. Earlier experiments in each lane (every pack, sweep and failed approach before those final summaries) are not recorded here and need a full paging pass.
