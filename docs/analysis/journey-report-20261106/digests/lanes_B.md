# Lanes B digest: four whole Claude Code cloud lanes (30 Oct – 2 Nov 2026)

Method: `list_events` with `kinds: ["result"]`, limit 100, paged with `before_id` = the previous page's `first_id`. Only each result's own final text and metadata (cumulative cost, turn count) were read. Machine IDs, keys and URLs are left out. Some timestamps are the agents' own clock labels, which they corrected mid-lane (5–35 min slips, per their notes); those are marked as such. Pages that could not be read in full were parsed from the tool's saved output file. Progress notes are in `/tmp/claude-0/-home-user-v2d-track3/40ae8bef-a6ac-5623-abee-9e3e721c7845/scratchpad/report/digests/lanesB_progress.md`.

---

### Perfect following of perceived trajectory (session_01D9UJC8Nz9EEFNmz2yzimzN, 1–3 Nov)

Coverage: read back to 2026-11-01 21:06 UTC. Start of lane **not reached**. Cursor for the next page: `before_id=2af9da5e-32f3-4723-870f-d356a95b0e52`.

**Early Nov 1, two-hand reference test (about 21:06–00:03).** Four boxes ran from 21:22 UTC: a bridged single-hand arm and a two-hand arm on evals 14, 15, 16 and 32, plus a public-episode test on ep13.
- Eval 16 two-hand, seed 42: 0.713 on the training box (packed 0.850). Seed 43: 0.696. Both below packed, so NO-SWAP.
- Eval 14 bridged two-hand, seed 42: 0.680. The single-hand bridged arm scored 0.880. Unbridged two-hand, seed 43: 0.581. Two-hand hurts eval 14 in both references.
- Eval 15 two-hand, seed 42: 0.943 (packed 0.906). Seed 43: 0.913 ± 0.097. Seed 42 was chosen and sent to confirmation.
- Eval 32 bridged, seed 42: 0.877 against its bridged reference (packed 0.852 against P; the agent said these use different yardsticks).
- Public ep13: single-hand AUC 0.378 (seed 42), 0.554 (seed 43); first-picker AUC 0.555 (seed 42; two-hand 0.587). Batch 1 closed at 23:48.
- Eval 14 bridged single-hand, seed 43: 0.892 ± 0.052 (seed 42: 0.880). Seed 43 was chosen.
- Eval 33 bridged, seed 43: 0.898 (seed 42: 0.406). Eval 32 seed 43: 0.895, chosen for confirmation.

**Frozen-hand test (Nov 2, 01:38–06:42).** Idea: keep the robot hand on the object after release. This was run on the packed reference of eval 16.
- The frozen-hand arm, seed 43: 0.972 ± 0.003, against seed 42 at 0.975 (the arm was pfG; this is the ep16 test).
- Control seed 43: 0.787. Packed-reference control seed 42: 0.769.
- A separate frozen-hand arm on another episode (pfF): control seed 43 0.719; hold-to-end 0.792 (+0.07). Both below the packed 0.850, so NO-SWAP.
- The 06:31 morning report calls the ep16 fix "robot hand keeps holding the spoon after release".

**Morning report and pack 12b (Nov 2, 06:31–07:12).** Pack 12b = pack 11 with evals 14, 16 and 32 replaced by policies retrained on corrected reference trajectories. The agent's 10-draw official means were:
- ep14: 0.727 → 0.861 (old reference) / 0.875 (corrected), 1/10 failed.
- ep16: 0.850 → 0.974, 0 failed.
- ep32: 0.852 → 0.867 / 0.890.
- Not packed: ep33 0.923 → 0.935 (+0.0196, under the +0.02 bar); ep15 0.906 → 0.947 with a two-hand reference, failed the median-error check.
- Mean over the 20 evals: 0.921 → 0.934 (agent's estimate).
- Causes found: perception lost the cup and re-found it; the tracked cup drifted 3–14 cm out of the hand, then jumped 11–20 cm in one frame. In ep32 the cup was upside down for 13 frames. The new `tools/guard_bridge.py` smooths the drift without ground truth.
- Failed: two-hand references; reference rebuilds with today's grasp-lock code (ep16 0.69–0.79 against packed); the GRASP session's hold filter (public test failed); cup twist correction.
- Caveat: the leaderboard scores the stored trajectories. Pack 11's ep14 draw was lucky (0.909); the new one scores 0.882.
- 06:42 UTC: keen-heisenberg uploaded pack 12b. AUC 0.84405 (+0.0048 over pack 11; ahead of DSAIL's 0.84391); MP-SR 0.75; RPE 3.023 cm; MPPE 2.495 cm.
- Spend at that point: $31.48 of a $102 budget.

**Lift-window test (Nov 2, 07:18–11:34).** The agent found that the "keep the hand on after release" fix does not match evals 25, 30, 1 and 3. Their errors start about 10 frames after the grasp, during the lift.
- Change: during training only, 30% of practice runs start in the frames around each grasp and lift. Evaluation is unaffected. Pre-registered at `docs/research/work/pf-lift-20261102/PREREG.md`.
- Public test on ep31 (twin of eval 30), two seeds. Lift arm: 0.730 and 0.704. Control: 0.589 and 0.707. Differences +0.141 and −0.002; mean +0.069 against the +0.02 bar. **Pass** (11:34). The whole gain came from seed 42, where the control had failed draws; the worst draw rose from 0.25 and 0.40 to 0.69 and 0.62.
- Retrain of evals 3, 14 and 32. The first box (11:51) had a bug: lift windows were keyed by arm and seed, not episode, so all three episodes used eval 32's windows. Stopped after 20 min (about $0.50 lost). Fixed and rerun. The next box stalled during setup on a Japan machine and was destroyed by the 30-minute watchdog (about $0.90 lost). Relaunched in Croatia.
- Standard-learner lift windows (evals 25, 28, 30, 1). Pre-registered as addendum C (commit 0f695c94). Five boxes started on seed 42 at about 13:16 UTC. Budget: credit $70.53 at 15:56 TRT; the $50 window ends at $41.35.
- Eval 30's original box ran at a third of normal speed (14.4k against about 50k env steps/s; GPU at a 500 W cap but reaching only 840 MHz). It was replaced by pfL2 (about $1.45 for the bad box).

**Seed results (Nov 2, 14:49–16:31).** Seed 42 box means against gate:
- ep14 0.923 (gate 0.875, +0.048). Seed 43: 0.908. Both pass.
- ep15 0.953 (0.906, +0.047). Seed 43: 0.945 ± 0.029.
- ep32 0.888 (0.890, −0.002). Seed 43: 0.876 ± 0.112 (one draw 0.549) → NO-SWAP.
- ep3 0.888 (0.933, −0.045). Seed 43: 0.886 → NO-SWAP.
- ep28 0.864 (0.919, −0.055). Seed 43: 0.651 → NO-SWAP.
- ep25 0.529 (0.878). Seed 43: 0.541 → NO-SWAP. Both lift seeds fell into eval 25's low mode; earlier seed 42 runs without lift windows reached the high mode (0.79, 0.82). The agent says two seeds cannot separate lift windows from the usual seed split.
- ep30 seed 42 0.787 ± 0.158 (gate 0.897); seed 43 0.932 ± 0.014 (lowest 0.901) on the replacement box (per the later note).
- ep20 seed 42 0.297 (gate 0.893); seed 43 0.921 ± 0.019 (min 0.885), clears the gate by +0.028. Agent's guess [H]: lift window 1–35 covers the episode start.

**Confirmations and pack 13 (Nov 2, 16:33–18:51).**
- ep14 confirmation FAILED: 0.826 fresh against 0.875 (box 0.923). Agent hypothesis, untested: lift-window policies look better on the training box than on the clean evaluator. Earlier swaps had matched closely (ep14 without lift windows 0.880–0.892 box, 0.875 fresh; ep16 0.975 box, 0.974 fresh).
- ep20 passed on fresh draws: 0.926 against 0.893 (+0.033); median error 1.67 → 1.38 cm. Pack 13 = pack 12c with ep20 swapped. Dry build passed (403 pose rows; checkpoint 61dcd7a6 → 1e08b92f).
- ep15 near-miss: fresh 0.958 against 0.906, no failed draws, but the median error was 1.346 cm against 1.299 cm. The first write-up said "0.05 mm worse"; the correct figure is 0.47 mm (corrected at 19:02). This failed a clause, so the owner was asked.
- Pack 13 uploaded at 18:51: AUC 0.84924 (+0.00186 vs 12c); MPPE 2.45263 (−0.0147, better); RPE 3.00841 (about the same); SP-SR 0.85, MP-SR 0.75, CD-O 0.30008 (unchanged). Rank sum 54, tied with DSAIL.
- Pack 13b (ep15 added, owner waived the failed clause) built at 19:02. Not uploaded in this lane's record.
- Budget: credit $33.41 (stated at "17:00 UTC"), later $29.29 (18:02 UTC; clock labels disagree). Box batch of Nov 2 cost about $28 across six boxes.
- Owner top-up: $127.77 at 20:21 UTC, lane limit ≤ $45 (agent's note at 20:23).

**Spoon-anchor test (Nov 2, 20:14–20:23).** Built and pre-registered (commit 27c43cf4), not launched. The spoon starting orientation was rebuilt for evals 32, 33, 35, 36, 37 (by 2.0°, 1.8°, 3.2°, 6.1°, 5.2°). Each policy replays unchanged on its new reference, 10 fresh draws, about $2. Swap rule: no more than 0.01 below the board average, no more failures, first draw within 0.05. The keen-heisenberg go/no-go was no-go; the test was not run. Public data: the same correction gained +0.001 on other objects. Agent's estimate: each episode moves 0.03–0.15 on the board in an unpredictable direction.

**Four retrains and pfH (Nov 2, 20:23–21:22).** Four boxes launched after the top-up, each pre-registered, 2 seeds, then 10 fresh draws: ep20 with the Tier B pitcher; ep28 with the rack; ep30 with sweeper and rack; ep14 with rack and blue cup (replaced ep1, which the owner asked to skip). Ground-truth flag: Tier B shapes were chosen by comparing against the organisers' object scans; used as physics shapes, labelled, and approved under the owner's "permission for all". Each box first runs the board policy once on the new shapes and drops the episode if the simulator overflows. Three of the four failed their first step because the zero-shot check did not copy the scene-support folder (commit b0b4a31); relaunched, about $1.50 lost.

**Zero-shot checks (Nov 2, 21:05–21:19).** Board policy on new shapes, one draw each: ep28 rack 0.906 (10-draw mean 0.919); ep30 sweeper+rack 0.829 (0.897); ep14 rack+blue cup 0.878 (0.875); ep20 pitcher 0.451 (0.926). Only ep20 broke on its new shape. Agent's reading [I]: the grasp was built for the old pitcher, which differs by up to 2.5 cm.

**Where the lane stops (Nov 2, 22:11 back to 21:06).** The page at 22:11 is the last read: public ep13 single-hand seed 42 AUC 0.378; two-hand arm pending. Lane spend by 22:11 about $20 on this session's cumulative counter.

---

### Embodiment options (session_01D9UJC7MhytodZodnDDAU3z, 30 Oct – 1 Nov)

Coverage: read back to 2026-10-31 16:29 UTC. Start of lane **not reached** (several recent pages empty; more history exists). Cursor for the next page: `before_id=6733a144-eb4b-470c-9a55-6616e46de531`.

**Recipe screen (Oct 31, 16:29–20:37).** The screen has three arms: C (current), K (higher learning rate) and D ("random starts": small object nudges at the start of each training attempt). Four episodes, two seeds. Results as avg ± spread over 10 runs (seed 43 box, 18:27 UTC):

| Episode | C | K | D |
|---|---|---|---|
| ep2 | 0.87 ± 0.17 | 0.96 ± 0.02 | 0.86 ± 0.24 |
| ep12 | 0.61 ± 0.01 | 0.58 ± 0.02 | 0.92 ± 0.02 |
| ep18 | 0.62 ± 0.00 | 0.62 ± 0.01 | 0.60 ± 0.06 |
| ep24 | 0.24 ± 0.00 | 0.25 ± 0.01 | 0.23 ± 0.00 |

Seed 42 at 16:35: ep12 C 0.58, K 0.52, D 0.92. D on ep12 kept improving late in training.
- Final verdicts (20:34): K no overall gain (average change −0.002). D inconclusive: large gain on ep12, hurt ep2. ep24 seed 43 cell "incomplete" (lost 6 of 10 runs to a machine resource limit).
- Agent's explanation (19:06): D changes only the start of each attempt: objects nudged up to 1.5 mm and turned up to about 1°, fingers about 0.5°, then 20 settle steps. Motivation: official re-runs drift about 5 mm in the first second and about 2 cm once the hands touch; ep2 scores ranged 0.17–0.98. Scoring is untouched (CPU check: identical scores with or without). Framed as domain randomisation, limited to start positions.
- Decisions: the scores session approved D for evals 14, 16, 25, 30, 33 at about $6–10 (20:55). The agent warned about the ep2 result (spread 0.10 → 0.25; average 0.91 → 0.80), about standard-learner evals 25 and 30, and about objects starting touching (lid on pot, cup in cup). On 20:29 the owner said "No D" and the proposal was withdrawn. The pack-10 session kept the current recipe.

**Solver re-test (Oct 31, 17:21–20:34).** Physics-solved reference motions, two seeds, each episode compared to the current recipe. Solver result: ep2 0.78 against 0.91 (−0.13, both seeds); ep12 0.82 against 0.59 (+0.22); ep18 0.58 against 0.62 (−0.04); ep24 0.24 against 0.24. A pre-set rule stops the solver if any episode drops by 0.05 or more, so it stays out of evals. Cost $23.13 across four machines (estimates). Agent's note: ep18's solved reference was identical to the normal one, so the 0.07 spread between its runs is training noise.

**Solver arm S and eval-solve job (Oct 31, 17:01–17:32).** Subagents built and CPU-tested two pieces, neither launched by the lane at that time:
- Arm S (recipe screen with the solved references): 41/41 checks pass; plan two boxes, about $6.5–11.5, worst ≤ $15. The solver's references are the exact files the solver trained on; object columns identical on the four episodes; only the robot wrist and finger targets differ.
- Eval-solve job (`ops/jobs/eval_solve.sh`): solves 15 grasp-lock eval references at G2 scale on two boxes, $9–14 expected. Caveats: not run on GPU at eval scale; the solver plans at 0.3 kg, which mismatches if realistic masses are adopted. A commit (a710b43) was pushed because a repo check flagged uncommitted files; marked unreviewed and not for launch.

**Arm V, slip-aware recipe (Oct 31, 19:06–Nov 1 00:06).** Object velocities given to the robot; two machines, about $7–9 approved. Results on four public episodes: ep2 −0.05, ep12 −0.03, ep18 −0.01, ep24 −0.01; average −0.024 (inconclusive, no gain). Six test machines finished. Spend on these tests about $30.15 (estimate), arm V $7.02.

**Boards, carved pieces and the P1 check (Oct 31, 22:13–22:25).**
- P1 check on ep24 boards (CPU, $0): the physS1 reference holds the assembled boards about 3 cm above the table. Carved and default pieces both fail drift (carved 3.71 and 3.23 cm; default 3.18 and 3.20 cm). Carved pieces need up to about 2030 constraint rows per world; default needs 416–425. Under the training sim setting (512 rows) the carved scene overflows in 16 of 16 copies. Recommendation: do not use the carved boards as delivered. Mesh session then marked them do-not-use and added a contact check for all future pieces.
- Mesh session then adopted a hard limit of at most 380 constraint rows per world for future pieces (22:25).
- Control cell re-scored (10 fresh runs): 0.233.

**Realistic masses and pack-10 results (Oct 31, 23:35 – Nov 1 00:06).** The pack-10 session tested realistic masses: not adopted. Eval-10 cup-nest retrain: no swap (cup never lifted). Re-track: failed. Board-piece test: failed (see above). Target smoothing (test A, CPU): failed its pre-set rule (at most +0.014 for normal plans, mostly worse for solver plans).

**Open decisions at Nov 1 00:06 (agent's list):** (1) solver v2, recommend skip; (2) solver-synergy test B, not done, hours of CPU and after the 17:00 TRT reference cut-off; (3) higher constraint-row limit test on ep2 and ep12, two seeds, about $7 (estimate). Lead for (3): ep2 training exceeds the 512-row limit about 600,000 times per run in the current recipe; scored runs never do.

**Eval-10 overflow chain (Nov 1, 02:40–05:49).**
- 02:40: packed ep10 cup pieces overlap at rest. Random training starts reach 536 rows; 13% of steps over the 512 limit. The packed ep10 training log shows 8.4 million overflow warnings. Its five scored runs had none.
- 03:08–03:43 (paired, 32 worlds; share = steps where at least one world is over 512 rows): random starts during hold, max / share: packed 661 / 100%; v1 (ev10cs) 598 / 75%; v3 (ev10cs3) 534 / 15%. Scoring-style nested starts: packed 918 / 33%; v1 699 / 19%; v3 477 / 0%. Overflow warnings (scoring-style): packed 9,723; v1 7,086; v3 576.
- 04:26–04:47: final contact checks, none cleared: ep14 rack candidates 12 / 5 warnings (packed rack 0); ep30 packed setup 0; ep10 ev10cs3 110 + 576 against packed 380 + 9,723.
- 05:09: ev10cs4 passes the first checks: peak 459 of 512 rows; beige cup error against blue 0.14 cm (ev10cs4) against 1.02 cm (packed). Retrain of ev10cs4 needs owner go-ahead (about $2–3).
- 05:11–05:23: ev10cs5 (8 mm cup floor, from the mesh session): zero overflow warnings; peak 503–504 of 512 rows; floor margin 4 mm (against 0.5 mm). Cup mass centre moved 12.8 mm (the pack session asked whether this confounds the test).
- 05:47: diagnostic: raising the row limit in training only (sim.njmax=1024, sim.nconmax=512) → no overflow, the robot lifts the cup for the first time; GT-free tracking score 0.459 → 0.913. Scoring at the normal limit: 0.903. The diagnostic policy was not packed.
- 05:49: pack session estimated overflow for all packed evals from log sizes. Only ep10 heavily affected (about 8.4 million). Evals 33 and 32 at most about 21,000; 15 of 20 none. Pack session keeps the owner's earlier rule: no policy trained with the higher limit goes into a pack until the organisers agree.

**Where the lane stops (Oct 31 16:29, lowest read).** Earlier pages not yet read.

---

### Policy development review (session_01D9UJC8kwkZnQELxSNreZD1, 30 Oct)

Coverage: start **reached** as far as the tool shows. Results before 2026-10-30 07:03:01 do not exist (the 07:03 turn is process turn 0), and later empty pages were returned with no cursor.

- **07:03 (briefing page, human, 39 turns, cumulative $4.03).** A private briefing artefact (also in `docs/briefing/`, branch claude/magical-mccarthy-v8tmyi) was built from the focused-pascal branch (612 commits), other session branches, the Vast billing records and the store listing.
  - Pipeline: stereo depth, object detection/tracking, hand tracking; NVIDIA's retargeter maps hands to robot hands; one policy per episode in FlashCHORD (two floating Sharpa hands, 4,096 worlds); the official evaluator replays it once and that rollout is uploaded.
  - Three policy kinds: stock recipe (dropped: failed on tools, boards, spoon); "standard learner" (RL from scratch 250M steps, improved rewards, physics fix; used on 5 evals: tools and boards); "grasp lock" (grasp designed into the motion, fine-tune 40–70M steps with a stiffer wrist; used on the other 15 including all spoon evals, which reach 0.97–0.98).
  - Scores (7 submissions): first upload 0.575 (9th); pack 3 0.789 (4th); since then 0.811 → 0.814 → 0.8146 (best), now 7th; 5th needs +0.046.
  - Cost (Vast billing): $376.41 spent 20–30 Oct; 135 rented machines, 246 GPU-hours; at least 158 trainings in the store. Net deposits $445, $68.58 left (including a $1,050 deposit on 21 Oct, of which $1,000 was refunded).
  - Stuck on: policies do not follow our reference (0.083 measured; eval 10 accounts for 0.027; seven attempts failed); our reference differs from the truth (about 0.10, estimated; mostly spoon, which is in 10 of 20 episodes); score rests on lucky draws (organisers re-running could give about 0.78); small swaps barely move the board (about +0.0005 each); CD-O (mesh quality) is worst at 11th.
  - Operational note: the control-research session logged a video machine launch at about 06:48 UTC; Vast showed nothing running when checked.
- **07:xx – 08:06 (human, 14 turns, cumulative $18.61).** Assistant reply on where the learner code lives: the algorithm is NVIDIA's FlashCHORD (FlashSAC), not in our repo; `pipeline/setup.sh` clones it at evaluator pin 8c778f9; recipe `configs/experiment/sharpa_flash_sac.yaml`. Our repo has the patches (FlashDexRetarget-style rewards, full-inertia object-assist fix, deployment-exact starts), configs, reference scripts and job scripts. Standard learner: `ops/jobs/hard_ab.sh` (250M steps, checkpoint scoring, repeat evals) and `std_learner.sh`. Grasp lock: `ops/jobs/glock_public.sh`, grasp design in `pipeline/grasp_lock.py`, wrist ILC `pipeline/wrist_ilc.py`, CMA-ES grasp search `tools/grasp_evolve.py`. Choice: `tools/choose_learner.py` keeps the learner with the higher mean `sim_vs_ref` over official evals. Three readers were then started for the explainer.
- **08:04–08:10 (human, 10 turns, $6.06 then $14.6; 14 turns, $18.61).** The agent **merged all session branches into `main`** and pushed it, so GitHub's default view shows the whole project: focused-pascal (control-research session incl. packs 1–6 and the contact-slot fix), bold-albattani (mesh session, 57 commits never merged), modest-davinci (training-budget note), the briefing page, and every commit the seven submissions point to. Code merged without conflicts; STATUS.md and work-log conflicts kept both sides. The control-research and mesh branches keep working and will need re-merging. Also: the depth check meant to show where the reference goes wrong failed its pre-set test (0.600 against 0.65), so no spending on reference or spoon fixes on its strength.
- **08:11–08:13 (reader and human).** Selection/variance/eval-campaign reader back. Videos are not in git (`*.mp4` excluded); they live in the private HF store (392 video files across 70 runs). Named sets: the 20 submitted eval episodes with hands (26 Oct); the 20 eval videos (24 Oct); spoon-recipe development (23 Oct); 22 Oct overnight rounds on public eps 12, 18, 24, 27; today's worst-5 replays (not yet uploaded).
- **08:14 and 08:27 (peer).** Grasp-lock reader done (stages, flags, spoon saga, failure points). The detailed learner explainer was published as a private artefact and committed to the branch. Ten parts: training setup; ten-day timeline (first 0.009 score to 0.8146); stock vs standard vs grasp lock; standard learner details; grasp-lock stages; "use both" rule and per-episode variant; eval campaign (carves, eval-10 saga with six failed attempts); variance; eight lessons; 14 open hypotheses with the test and falsifier for each. Two findings from checking: the grasp lock's "fine-tune" is actually a fresh 70M-step run on a reference that already carries the object; and a 70M run ends before the training assist is fully switched off, so those policies never train under scoring conditions. Offer to merge `main` again pending owner decision.

Lane cumulative cost at 08:27: $26.92.

---

### Performance vs. NVIDIA methodology (session_01D9UJC9HM6HuNGNhAzddH4G, 30 Oct)

Coverage: one result visible (2026-10-30 13:52:01). Later pages returned no further results; the start of the lane is **not confirmed** (the tool returned no data beyond this one result).

- Answer to the owner: there is no true head-to-head number. NVIDIA never posted a Track 3 baseline, and our team never ran NVIDIA's Track 3 pipeline.
- Measured (CPU, $0): NVIDIA's pipeline as shipped cannot score above **0.415 AUC** on the 20 public episodes. Its default training plays the demonstration at half speed, so the submitted frame at f holds about frame 0.5·f and the second half of every motion is dropped without warning. With true poses and only that timing effect, the official kit gives AUC 0.415, SP-SR 0.30, MP-SR 0.00. "Nothing moves" baseline: AUC 0.446, SP-SR 0.45, MP-SR 0.00. Ours on the leaderboard: AUC 0.8146, SP-SR 0.85, MP-SR 0.65 (hidden evals). The floor value matches one logged on 12 Oct.
- Caveat: this is a ceiling for NVIDIA's defaults, not for a fixed pipeline. Public episodes, not the hidden evals.
- NVIDIA's posted Track 2 baselines (indicative only, different episodes and inputs): 0.510 AUC with its multi-view reconstruction; 0.002 AUC with its own reconstruction from video.
- Why no direct number: NVIDIA's Track 3 pipeline handles one object per episode and assumes 30 fps; 13 of 20 public episodes have two objects and the video runs at 20 fps.
- Options offered: ask the organisers for a Track 3 baseline (free); or run NVIDIA's pipeline with only the fixes needed to run it (timing, multi-object) on public episodes, about $15–20 for the 7 single-object episodes or $60–70 for all 20, plus setup. Needs owner go-ahead.
- Write-up: `docs/analysis/nvidia-default-timing-20261030/README.md`, on branch `claude/funny-shannon-6863f9`.

---

## Lessons

- A cloud job's first step must check its own inputs. Three failures came from missing files or wrong keys (support folder not copied; mesh folder looked up from the wrong place; lift windows keyed by arm and seed, not episode). Each was caught only after a box had started.
- Box-to-fresh drops are real. Eval 14's lift-window policy scored 0.923 on its training box and 0.826 on fresh official draws; eval 30's new-shape policy scored 0.938 and 0.768. The agents disagreed on the cause; keep the two-machine confirmation rule.
- Single-seed and two-seed results on a 10-draw box are noisy. Ep2 spreads from 0.17 to 0.98 across runs; ep18 solved-vs-normal runs differ by 0.07 with identical inputs.
- Contact-row overflow in training is a hidden cause: ep10 had 8.4 million overflow warnings with a cup that never lifted; raising the limit in training alone moved the tracking score from 0.459 to 0.913, with scoring unaffected. The fix was not packed while the organisers' view was pending.
- Collision shapes are not free. Carved or nested pieces raise the row count (2030 rows for carved boards vs 425 default); the simulator's limit then drops contacts and boards fall through the table.
- The best policies are often the ones whose draws are lucky. The agent's own estimate for the official re-run is about 0.78 against 0.8146 on the board.
- Two-hand references hurt on the tested episodes (ep14 0.680 and 0.581 against 0.880 single-hand bridged), and rebuilt references from today's grasp-lock code lose to packed ones (ep16 0.69–0.79).
- Keep the record straight: several clock labels and one arithmetic figure (0.05 mm for 0.47 mm) were wrong and corrected later. Read the corrected line.

## Coverage

| Session | Lane | Oldest timestamp reached | Start reached? |
|---|---|---|---|
| session_01D9UJC8Nz9EEFNmz2yzimzN | Perfect following of perceived trajectory | 2026-11-01 21:06:19 UTC (page 31; next cursor 2af9da5e-32f3-4723-870f-d356a95b0e52) | No |
| session_01D9UJC7MhytodZodnDDAU3z | Embodiment options | 2026-10-31 16:29:40 UTC (page 31; next cursor 6733a144-eb4b-470c-9a55-6616e46de531) | No |
| session_01D9UJC8kwkZnQELxSNreZD1 | Policy development review | 2026-10-30 07:03:01 UTC (process turn 0; later pages empty with no cursor) | Yes, per tool |
| session_01D9UJC9HM6HuNGNhAzddH4G | Performance vs. NVIDIA methodology | 2026-10-30 13:52:01 UTC (only result returned) | Not confirmed |
