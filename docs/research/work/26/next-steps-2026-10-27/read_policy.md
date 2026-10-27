**Policy and control recipe on main-bsky37, and how note 23's levers map onto it (read-only audit, 2026-10-27)**

Notation:
- **M** = `origin/main-bsky37` @ 2bb20e3.
- **C** = current checkout `claude/focused-pascal-2nz9s1` @ c5e8c14.
- **WL:n** = line n of `M:docs/work-log.md`.
- Tags: [M] measured, [V] read in code, [E] estimate, [H] hypothesis.

Scratch copies used for line numbers: `/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/nextsteps/worklog.md` and `.../STATUS_main.md`.

**Read first: note 23 was written without main's history.**
- C forks from 4d1d7ee (20 Oct, the day-1 commit): `git merge-base HEAD origin/main-bsky37` = 4d1d7ee. M has 573 commits; C has 18.
- So `C:docs/research/notes/23-carry-control-force.md` assumes the default kp 25 wrist and no feed-forward or replay screen. Most of that is already in production on M.
- **Name clash:** M already has `docs/research/notes/23-grasp-controller-and-rl-handoff.md`, plus notes 24 and 25.
- **Merge conflict:** C adds 3 lines to `pipeline/pipeline_ep.sh` (the audit_ref hook). M has changed that file by +98/−10 since 4d1d7ee.
- **Code-patch rule:** note 23 §F treats code-level levers as off-limits. M already trains with four training-only FlashCHORD patches whose checkpoints load in the unpatched evaluator:
  - FDR rewards;
  - the VOC inertia fix;
  - deployment-exact starts;
  - drop starts.
  
  Source: `M:ops/box/lib.sh:41-68`.

## 1. Training recipes used for the submissions

Pack 6 (Kaggle AUC 0.81391) uses two learners plus a choice rule (`M:results/submissions/20261026-track3f/checkpoints.json`, `summary.txt`).

**A. Grasp-lock learner: 15 of 20 eval episodes** (3, 5, 6, 8, 10, 14, 15, 16, 20, 32, 33, 35, 36, 37, 38)

Reference stages (`M:ops/jobs/glock_public.sh`):
- **Base reference:** perc2 → hands → mkref `--wrist_cost 3.0` → contact retargeting with `--rest_settle 1` (variant `mck`) (lines 135-136).
- **Support fill** SF=1 (lines 158-166).
- **Grasp lock** `grasp_lock.py` (lines 46, 174):
  - GL_ARGS `--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15`;
  - `GL_WRIST_KP=400`, which sizes the lift feed-forward.
- **Wrist ILC:** `wrist_ilc.py`, 4 iterations, `EMB=sharpa_hands_mid` (line 176).
- **Optional:** `grasp_evolve` CMA-ES (lines 179-189) and REPLAN.
- **Zero-action replay and rest check** (lines 192-195).

Training (lines 226-228):
- `experiment=sharpa_flash_sac embodiment=sharpa_hands_mid task.motion_speed=1.0 reset.seed=$SEED training.total_environment_steps=70004736 $TRAIN_ARGS`.

Embodiment (`M:flashchord_conf/embodiment/sharpa_hands_mid.yaml`):
- Wrist translation: kp 400 / kd 20 / 150 N.
- Ball wrist: unchanged at effort kp 25 / kd 6 / 45 N·m. `action.wrist_kp` and `wrist_tau_max` stay at their defaults.

Rewards (`M:ops/box/lib.sh:41-45`, `M:ops/box/fc_v2d_fdr.py:1-25`):
- `curriculum=tracking_250m_mixed_reset_v2d`.
- `objective.force_closure` enabled with weight 6. That slot holds FDR's fingertip bound, not stock force closure.
- contact_wrench_support 3, unintended_contact −2.
- FDR point-match in the object_keypoints slot.
- The VOC full-inertia fix is on.

Curriculum [V]:
- Thresholds are the stock absolute ones, so a 70M run "ends in the 0.1 stage" (`M:ops/box/patch_flashchord_drop.py:9-11`; stage table in `M:docs/research/notes/01-baseline-dissection.md:305-307`).
- So grasp-lock policies never train unassisted and never get frame-0 starts. `FC_IMMEDIATE_FIRST_FRAME` is not set for this learner (`M:ops/jobs/eval_both.sh:27-28`).
- `CURR_SCALE` exists (glock_public.sh:62-65), but no run in WL uses it.

Action, observation and exploration (`M:docs/research/grasp/flashchord-capabilities-for-grasp-search.md` §1.1–1.2):
- Stock `residual_hand_pose`: scales 0.05 m / 0.15 rad, clips 0.2 m / 1 rad, EMA 0.3, rational mapping.
- Stock actor observation: no object velocity.
- Upstream actor head; exploration target σ 0.1.
- M:ops/pipeline/tools contains no `action.`, `observation.` or `termination.` training overrides (grep).

Checkpoint selection and seeds:
- Every checkpoint (10M apart) gets 3 official evaluations; the best gets 5 more (glock_public.sh:244-259).
- Seeds: 42 by default. 3, 5, 15, 16 and 33 use s43; 32 uses s46.

Two variants are in use:
- **"Frozen recipe"** (24 Oct): SF=1, REPLAN=0, EVOLVE=1 (256 worlds, 20 generations), CURVE_REP=3, NREP=5, plus `--onset_anchor 1` (WL:2862-2866, 3753-3755). Used for 3, 5, 6, 15, 16, 32, 33, 35-38.
- **eval_both variant:** REPLAN=1, no EVOLVE, no onset anchor (WL:3936). Used for 8, 14, 20 and 10 (gl10A2).

**B. Standard learner: 5 of 20 eval episodes** (1, 19, 25, 28, 30)

Source: `M:ops/jobs/std_learner.sh:17-19`, `hard_ab.sh:32,149`, `carve_rerun.sh:18-20`, `pipeline/pipeline_ep.sh:100-147`.
- Default `sharpa_hands` (kp 25 / kd 6 / 45 N), motion_speed 1.0, 250,003,456 steps.
- FDR rewards + VOC fix + `FC_IMMEDIATE_FIRST_FRAME=0.25`.
- Trained on the `mck` reference with CR=0.
- Checkpoint sweep at 0.4 / 0.6 / 0.8 plus the final one, with a floor-guard extra sweep; 5 evaluations of the chosen checkpoint.
- Eval 25 uses carved collision pieces.

**C. Choice and cost**
- Choice: `tools/choose_learner.py` keeps the highest mean sim_vs_ref over 5 evaluations; gate 0.9 (`M:ops/jobs/eval_both.sh`).
- Cost [M]: a 70M fine-tune takes 18.7 min alone at 62.5k steps/s (WL:2336), about $1–2 per episode (e.g. fr25 ≈ $1.6). A standard learner run is about $3–5 per episode (WL:3968-3989).

## 2. Control and policy ideas tried so far

Results are 5–6 official evaluations unless stated. Scores are registered AUC on public episodes and sim_vs_ref on eval episodes.

| Idea | Result [M] | Source |
|---|---|---|
| kp 400 wrist + standard learner (21 Oct references) | ep12 0.860 vs 0.890; ep18 0.193 vs 0.381; ep24 0.050 vs 0.096. Falsified | WL:551-555, 1058-1074; `M:docs/forensics-2026-10-21.md:49` |
| kp 400 + grasp lock + ILC | eval 3 zero action 0.462 → 0.658, spoon within 3 cm 16.9 → 87.5 % of frames. Fine-tune: kp 25 gives 0.23–0.42; kp 400 gives 0.965–0.981 ("essential") | WL:2243-2247, 2315-2333 |
| kp 400 on eval 35 | 0.104 / 0.084 vs 0.15–0.185 at kp 25: in-hand slip up to 10 cm (bowl tips up to 50°). Fixed by anatomy closing: zero action 0.412, fine-tune 0.979 | WL:2258-2263, 2330-2340 |
| Wrist ILC (kp 25) | wrist error 11.4 → 4.3 cm; wrap 0.377 → 0.462 | WL:2160, 2198 |
| Object-level ILC (`--hold`), eval 10 | CPU best 0.632, but 0.42–0.54 under jitter; GPU run trained to 0.4528 | `M:docs/analysis/ev10-stack-20261026/README.md`; WL:4392-4400 |
| FDR rewards | 4-run mean 0.753 → 0.830 (adopted) | `M:STATUS.md` 23 Oct; WL:1884 |
| Deployment-exact starts 0.25 | ep18 0.351 vs 0.345 (ep18 hypothesis falsified); ep24 0.318 vs 0.307; ep12 0.763 vs 0.790; ep27 0.897 vs 0.911. Kept in the standard learner | WL:1290, 1387-1437 |
| Drop starts (recovery training) | ep18 0.220 vs 0.405 with replan; ep12 0.869 vs 0.910. Not adopted | WL:2540-2547 |
| Primitive-collision hand | ep24 0.282 vs 0.297; ep18 0.377 vs 0.345 | WL:1307-1323, 1347 |
| Object keypoints at 0.15 m | ep24 0.313, ep18 0.381 (within noise) | WL:1326, 1374 |
| Three learners on the same reference (25 Oct) | ep32 frozen 0.779 / eval_both 0.497 / std 0.299; ep33 0.773 / 0.486 / 0.249; ep25 0.297 / 0.376 / std 0.712; eval 1 std 0.912 vs grasp lock 0.297 | WL:3968-3989 |
| Grasp lock on carved cups, eval 10 | 0.4539 / 0.4377; the cup is never lifted | WL:4303-4310 |
| Early checkpoints every 1M steps, eval 10 | 0.446–0.465. Falsified | WL:4392-4400 |
| Zero-init residual head (`zero_dense`) + σ 0.05, eval 10 | 0.4459 < 0.4539. Falsified | WL:4439-4450 |
| Extra seeds, eval 32 | s42 0.779, s43 0.702, s44 0.397, s45 0.634, s46 0.803 | WL:4311 |
| Seed race | Analysis only: 40 % score predicts the final, R² 0.79 (standard learner); grasp lock does not. Interruptible boxes were preempted within ≈10 min | WL:4192-4205, 4283; `M:docs/research/seed-race-20261026/` |
| More steps | 13 of 22 low-start curves end below the zero-action floor | `M:docs/research/approaches-2026-10-25/training-steps.md` |
| Early stopping | Built; switched off by the owner | WL:2551-2553 |
| `sim_settle` (SETTLE=1) | Never run: the box was destroyed in setup | WL:3251-3268 |

What has changed on wrist gains and observations:
- Only the wrist translation gain (to kp 400) has changed.
- The ball wrist, action scales, terminations and actor observations were never changed.
- The actor head and exploration σ changed only in the falsified e10Z test.

## 3. Note 23 levers: new, tried or obsolete

**(a) Wrist translation gain (note proposes kp 100 with companion settings): TRIED, as kp 400 / kd 20 / 150 N.**
- The yaml lists all five override entries and raises the effort limit, so note 23's traps are already handled.
- Results: it hurt the standard learner on 21 Oct references, and it is essential for the grasp lock (table above).
- Still new:
  - kp 100 has never been run.
  - kp 400 has never been retested with the current standard learner and current references on 1, 19, 25, 28, 30.
- Headroom on those 5 episodes [E]: their 5-evaluation means are 0.79–0.935. Making them perfect would gain at most ≈0.025 sim_vs_ref, ≈0.019 AUC at the 76 % transfer rate (WL:4245).
- Rules: kp 400 is not cleared with the organisers. Question 5 of `M:docs/organiser-email-draft-2026-10-22.md` was never sent.

**(b) Ball-wrist damping to 1.5–3: NEW.**
- The rotation drive is identical in both embodiments and is listed as untested (capabilities doc §2.1).
- H8 (`wrist_kp` 100–200) was proposed and never run.
- ILC already corrects rotation in grasp-lock references (`--cap_rot 0.6`), which partly covers the same lag.
- It is a one-line change to the `wrist_rotvec$` entry in `sharpa_hands_mid.yaml`.

**(c) Actor object-velocity observation: NEW.** No override exists and it is not mentioned anywhere in M.

**(d) Start alignment: TRIED for the standard learner; NEW for the grasp lock.**
- The `FC_IMMEDIATE_FIRST_FRAME` patch is stronger than note 23's config-only version: frame 0, exact fingers, no hold. It gave no measurable gain but stays in the recipe.
- Drop starts (no hold, no assist) gave a negative result.
- Reference-side start fixes were adopted: rest settling, support fill, hand separation, lead-in cap.
- The grasp-lock learner never trains on exact starts or at VOC 0, because its 70M run ends in the 0.1 stage. The lever there is `CURR_SCALE`, which is NEW.
- [H] Exposing the grasp lock to VOC 0 and exact starts would improve 32 / 33 / 14. Falsified if `CURR_SCALE=0.4` does not raise the 5-evaluation mean.

**(e) Reference-side feed-forward (time advance + gravity offset): TRIED, in a stronger empirical form.**
- The lift feed-forward m·g/kp goes into the target columns (`M:pipeline/grasp_lock.py:13-17,378`).
- ILC adds an advance and offset learned from physics replays (`M:pipeline/wrist_ilc.py:1-9,47-50`).
- Measured gain: +0.085 at kp 25.
- Caveat: hand rewards use forward kinematics of the shifted target columns. H6 (how far this moves the reward targets) is untested (capabilities doc §1.2, R9).
- The analytic kp-25 version only makes sense for standard-learner references.

**(f) Force-closure reward: effectively NEW, but blocked.**
- The `force_closure` slot is occupied by FDR's fingertip bound (weight 6) in every run since 23 Oct. The stock term would need a new slot (code) or dropping FDR tips.
- The wrench-support weight went the opposite way (10 → 3) inside the winning FDR bundle (confounded).

**(g) Physics replay screen (zero-residual replay at VOC 0): TRIED and in production.**
- Every grasp-lock run includes it: 64 results, training beats zero action by +0.175 on average, and is below zero action in 15 of 64 (`M:docs/analysis/ev10-stack-20261026/zero_vs_trained.md`).
- Stiff and default wrist replays were done on 21–22 Oct (WL:1001-1004, 1255).
- Still new: a kp 100 arm, and using the replay to decide where to train.
- Training cannot be skipped: submissions must be learned policies (22 Oct rule, `M:STATUS.md` 26 Oct 15:25). On eval 10, RL leaves a good plan within 1M steps.

**(h) Compressed schedule / warm start: PARTLY TRIED.**
- The 70M fine-tune is the production grasp-lock recipe. Public ep27 0.972 and ep12 0.910 vs 0.942–0.956 / 0.891 at 250M (WL:2394-2404).
- Early stopping, seed race, early checkpoints and zero-init all ran or were analysed (table above).
- Still new: `CURR_SCALE`, and warm starts from another episode's policy (idea only, WL:1723).
- This contradicts note 23 §E's claim that runs must reach the unassisted phase: grasp-lock policies score 0.97–1.0 without it.

## 4. Measured evidence on drops, saturation, lag and the soft wrist

- **Wrist terminations (kp 25):** 21 Oct ep18 and ep24 rollouts ended on wrist termination (cause fraction 1) (WL:994).
- **Wrist can't keep up (kp 25):** with no policy, the ep18 wrist cannot follow a 0.6 m/s reach. kd 6 needs a ≈20 cm target offset against the 0.2 m clip (WL:1063).
- **Reference is feasible:** stiff kp 6000 tracks within ≈1 cm (3.8 cm in the fast reach) (WL:1001-1004).
- **Fast lead-in, eval 35:** the wrist ran 16 cm behind by step 10 (wrist limit 15 cm). Fixed with `--lead_in_speed 0.2` (`M:STATUS.md` 23 Oct).
- **Learned avoidance:**
  - spoon policies with the stock VOC pulled the wrist 35–43 cm away (`M:STATUS.md` 23 Oct);
  - the ep18 fine-tune moves its hands off the table (WL:2421);
  - eval 10: from the first checkpoint, no rollout touches the cups (WL:4325, 4444).
- **"The cup is flung after release," eval 10 at kp 400:**
  - the beige cup hits the blue cup's rim at up to 9,650 N;
  - the wrist stalls up to 14 cm behind;
  - the hand opens at ≈f120 and the cup flies 80–120 cm (`M:docs/analysis/ev10-stack-20261026/README.md`).
- **Stiffness trade-off:** kp 400 increased in-hand slip and bowl tipping on eval 35 until the grip was redesigned (WL:2258-2263).
- **Per-episode carry failures** (`M:docs/analysis/forensics-20261026/README.md` §2):
  - eval 3: pot 10 cm off in two carries (grip slip);
  - eval 1 (kp 25): pot spikes of 9 cm;
  - eval 32: cup lost during the lift at f20–28;
  - eval 33: two-handed carry 4–10 cm off for 270 frames;
  - eval 16: spoon flips on release.
- **Where the loss is:** most of today's policy loss sits in kp 400 episodes (evals 10, 33, 32 hold 54 %). The stiff-wrist lever is already applied there. What is left is two-handed holds, releases and the stack, not wrist saturation [E].