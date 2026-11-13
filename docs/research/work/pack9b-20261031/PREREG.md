# Pack 9b D arm: pre-registration (written 2026-10-31, finished 21:32 UTC, before any D result)

**When.** Written 31 Oct 2026 21:20–21:32 UTC (clock checked), before any D training was launched. No D training, evaluation or score
exists. The packed side's fresh draws (run `20261031-h5p7-1a7cdff`) were not read for this document; only their location
is named. Sections 1–7 are the rule. Later changes are appended as dated amendments; nothing above them is edited.

**Owner decision** (31 Oct, ~20:40 UTC via the score-status session; the pack-10 plan `../pack10-20261031/PLAN.md`
"Update ~20:55" and "Update ~21:35" record it): retrain five eval episodes with a training-only start-state randomisation
arm "D" on each episode's **current packed configuration**, two seeds each, and confirm each candidate with 10 fresh
official draws. A D policy that passes the agreed swap rule against its packed policy joins pack 9b.

**Integrity.** These are eval episodes. No ground truth exists for them and none is read. Every score is computed against
our own stored reference. Object names and slot order come from the kit roster. Nothing here is tuned on an eval result.

## 1. Design

### 1.1 Episodes, packed configuration, seeds
The configuration of each episode is that of its packed policy, read from
`docs/research/work/masses-eval-20261031/packed_refs.json`. That is the policy in pack 7, and pack 9a+ uses the same
policy and the same packed rollout for these five episodes. The configuration has no masses, no new carves and no new
references.

| eval | learner | objects (kit roster) | packed reference (md5, fingerprint) | assets | env | steps | packed checkpoint (seed, sha256) |
|---|---|---|---|---|---|---|---|
| 14 | grasp lock | blue_cup, plastic_dish_rack | `20261025-evb1420-ee7ba8e` refs/glockt/ep14 (10d5f3ba…, 71fa181b…) | own copy refs/sf/ep14/assets, library_v3 | – | 70,004,736 | evb1420 final_eval/ep14 (42, 05b13510…) |
| 16 | grasp lock | plastic_dish_rack, wooden_spoon | `20261024-pack-31ef267` refs/glockt/ep16 (f7e2ea92…, ade67fc9…) | own copy refs/sf/ep16/assets, library_v3 | – | 70,004,736 | seed43-61101f5 glock_public/ep16/best (43, df4d4473…) |
| 33 | grasp lock | blue_cup, wooden_spoon | `20261026-fr3233s43-6a8a0e2` refs/glockt/ep33 (2a7173ab…, e45b8179…) | own copy refs/sf/ep33/assets, library_v3 | CURR_SCALE=0.4 | 70,004,736 | rcB glock_public/ep33/best (43, df90b216…) |
| 25 | standard | wooden_piece_1, wooden_piece_2 | `20261026-c25s42-feb0407` refs/perc2mck/ep25 → perc2mcks copy (71ac95f3…, 6f709837…) | /content/assets, library_v3 + pieces meshes/carve/ev25 | – | 250,003,456 | c25s42 runs/perc2mcks/ep25-s42/policy_250003456 (42, 7edd445b…) |
| 30 | standard | mini_sweeper, plastic_dish_rack | `20261025-std30-ee7ba8e` refs/perc2mck/ep30 → perc2mcks copy (dd464c96…, c3510178…) | /content/assets, library_v3, no pieces | – | 250,003,456 | std30 final_eval/ep30 (42, bc9fccad…) |

[M, checked 21:29 UTC on local copies] Pack 6's / c33B's packed rollout JSONs of these five episodes name exactly the
table's packed sha256. The pack-6 box copies of the five references have exactly the table's md5.

- **Seeds 42 and 43** for every episode, so 10 cells in all.
- **Recipe = the packed recipe**, unchanged:
  - grasp lock: the glock_public.sh path of ops/jobs/mass_eval.sh MODE=glock (kp 400 embodiment, FDR rewards + VOC fix,
    70,004,736 steps, CURVE_REP 3, checkpoint chosen by sim_vs_ref on our reference, NREP 10, EVAL_TIMEOUT 1200). Eval 33
    runs with its per-episode CURR_SCALE 0.4;
  - standard learner: the hard_ab.sh path of mass_eval.sh MODE=std, i.e. the std_learner / carve_rerun recipe (FDR +
    VOC + FC_IMMEDIATE_FIRST_FRAME 0.25, 250,003,456 steps, sweep 0.4 / 0.6 / 0.8, NREP 10, EVAL_TIMEOUT 1200). Eval 25
    runs with the ev25 pieces.
- **Training reference = a byte copy of the packed reference.** Its md5 and fingerprint are checked against the table
  before any training, and a mismatch drops the episode. Grasp lock: `refs/drs<seed>_glockt/ep<N>`, with the URDF
  paths unchanged, i.e. the packed asset copy. Standard learner: `refs/perc2mckdr/ep<N>`, the hard_ab.sh copy with CR=0.

### 1.2 Arm D (the only change)
- **Patch.** `ops/box/patch_flashchord_dr.py`, ported byte for byte from determined-wright's commit **4e5c8a0**
  (origin/claude/determined-wright-3joens). Checks: md5 `570a7f47793d02ba5b0bf3d5e6fd6eac`, git blob
  `4f7305391b1daffe3d63391031a20a18d1efd4c7`; mass_eval.sh refuses a D run if the file's md5 differs. It includes the
  opt-in FC_DR_SKIP_IMMEDIATE. Determined-wright's CPU test at the evaluator pin passed 17/17
  (`tools/recipe_screen_tests/dr_skip_test_log.txt` on their branch). Two of its checks matter here: with SKIP, the
  deployment-exact starts are bit-identical to no DR; and the evaluator's sequence with DR + SKIP in the process is
  bit-identical to no DR code.
- **Where it is applied.** The patch is applied on every training box after the job's other FlashCHORD patches:
  - glock_public.sh after fc_patches;
  - hard_ab.sh after its FC_IMMEDIATE_FIRST_FRAME / FDR / VOC patches.

  The opt-in is `FC_DR_PATCH=1`. The patched tree is inert unless FC_DR_RESET is set in the process.
- **Environment.**
  - Evals 14, 16, 33: `FC_DR_RESET=1.5,0.015,0.01 FC_DR_SEED=<that training's seed>`, through TRAIN_ENV, so only the
    training process sees it.
  - Evals 25, 30: `FC_DR_RESET=1.5,0.015,0.01 FC_DR_SEED=<seed> FC_DR_SKIP_IMMEDIATE=1`, through ENV_EP<N>. That
    reaches the episode's whole hard_ab.sh subshell, i.e. training plus the training box's own evaluations. Those
    evaluations use explicit resets, which the hook never perturbs (above).
- **The confirmation draws cannot see D.** They run on the pristine kit evaluator (`/content/v2d_clean`, not patched).
  D adds no config field, so a D checkpoint's saved config equals a control's.
- **Required training-log line** (verified by `tools/dr_eval_verify.py`; a D cell without it is INVALID):
  - evals 14 / 16 / 33: `v2d FC_DR_RESET: sampled resets perturbed by +-1.5 mm, +-0.015 rad (rotation vector per
    axis), fingers +-0.01 rad; <k> objects, <j> finger joints, <W> worlds, seed <s>`, ending there, with no
    "; skip immediate starts" tail. `<s>` is the cell's seed and `<k>` the reference's object count (2);
  - evals 25 / 30: the same line followed by `; skip immediate starts (FC_DR_SKIP_IMMEDIATE: deployment-exact starts not
    perturbed)`;
  - the line must be absent from every non-D training log. On the D boxes every training is a D cell, so any training
    log there without the line is a failure. On the mock's default-path boxes (masses jobs, unchanged) no training log
    may contain `v2d FC_DR_RESET`.
- **Not done:** no masses, no new collision carves, no new reference, no recipe key changed, no other arm.

### 1.3 Training-box verification (per cell; `tools/dr_eval_verify.py`)
- **What is checked for each chosen checkpoint.** It is followed the way the official evaluator loads it: saved config →
  task.parquet → the reference (exactly one parquet) → URDFs. It is VERIFIED only if every one of these holds:
  - the reference md5 and fingerprint are the packed ones;
  - every URDF resolves verbatim and carries the 0.3 kg placeholder. Grasp lock: under the table's asset root.
    Standard learner: under /content/assets, with one `<collision>` per piece for the pieces named in the table, and URDF
    and mesh files identical to a fresh build of the same make_assets.py command;
  - the support stage the training read has the packed stage's md5;
  - steps and reset.seed are as listed;
  - every saved-config key equals the packed checkpoint's, except output_dir, task.parquet, reference.parquet and the
    seed keys (eval 33's CURR_SCALE 0.4 thresholds must therefore match);
  - the box's rollouts name the chosen checkpoint (sha256);
  - standard learner: the checkpoint is the sweep's choice;
  - the D log line is right (1.2);
  - the patched tree holds the 4e5c8a0 hook (`lifecycle/v2d_dr.py` written by the ported patch; md5 recorded).
- **INCOMPLETE:** no chosen checkpoint, fewer than 8 scored training-box rollouts, a standard-learner main evaluation
  cut by EVAL_TIMEOUT, or a packed file that could not be read.
- **INVALID:** any other failure above.

## 2. Seed choice (training box, per episode)
Over the two seeds, each with n ≥ 8 scored training-box rollouts (NREP 10, sim_vs_ref against our reference), the seed
with the higher mean is chosen. If the means are within 0.005 (rounded to 4 decimals, as tools/mass_eval_verify.rule2),
the lower sd (ddof 1) is chosen. If those are still tied, seed 42. Both seeds must come from VERIFIED cells. An INVALID
cell takes its episode out (the packed policy stays). A missing or thin seed makes the episode INCOMPLETE (section 6);
there is no single-seed fallback.

## 3. Confirmation (official evaluator, 10 fresh draws per candidate)
- **One box.** `ops/jobs/h5_reeval.sh` with N=10 (KEEP_ROLLOUTS defaults to 1), run after every training box has been
  read. It is built by `tools/dr_eval_merge.py` from the boxes' summaries and uses:
  - PICK_EXTRA: each episode's chosen D checkpoint, after the pack-7 basis `33:20261029-rcB-34bf6ae`;
  - RUNS_EXTRA: each candidate's D reference copy;
  - KEEP_RESULTS = pack 7's rollout sources (`20261026-pack6-5203d42 20261030-c33B-0202139`), so that unchanged episodes
    are not evaluated;
  - EVAL_ONLY = EPS_ONLY = DR_EPS = the candidate episodes;
  - PACKED_TXT = pack 7's summary.
- **Pack-side check** (`tools/dr_pack_check.py`, hooked by DR_EPS in pack_eval.sh before the kit evaluator and in
  h5_reeval.sh before draws 2..N). Every evaluated episode must resolve its URDFs verbatim at 0.3 kg. Each candidate
  must load the packed reference (md5 + fingerprint) and its table pieces, and must not be the packed checkpoint. A
  refusal or a missing check file makes the episode INVALID.
- **Draw 1** = the first confirmation call, by position, that produced a scored rollout of that episode: r1 (pack_eval)
  if scored, else the lowest scored r<i>. A call without a scored rollout is not a draw.
- The eval-1 environment is not involved: eval 1's packed rollout is kept, and only the 5 episodes (or those with a
  candidate) are evaluated. Eval 25's ev25 pieces are already in h5_reeval.sh's ASSET_PIECES (pack 6's environment).

## 4. Swap rule (agreed; verbatim from the pack-10 plan, applied per episode)
> Per episode, over ≥ 10 fresh official draws, GT-free: (a) mean sim_vs_ref ≥ the packed policy's fresh-draw mean;
> (b) failure rate (GT-free RPE vs our reference > 5 cm, audit.py) ≤ the packed policy's; (c) median GT-free RPE not
> worse; secondary: new packed draw (draw 1 by position) ≥ old packed draw − 0.05.

How the rule is applied here:
- **Packed policy's fresh draws:** run `20261031-h5p7-1a7cdff` `results/h5/r1..r10/ep<N>/episode_0000NN.parquet`, the
  10 draws of pack 7's policies with rollouts kept. For these five episodes pack 7's policies are pack 9a+'s. Each
  rollout's checkpoint_sha256 must be the table's packed sha256, else INVALID.
- **Old packed draw:** the board pack's (9a+) packed rollout of the episode. For 14 / 16 / 25 / 30 that is pack 6's
  `runs/20261026-pack6-5203d42/results/submission/results/episode_0000NN.parquet`; for 33 it is c33B's
  (`runs/20261030-c33B-0202139/...`). Its sha256 must be the table's. Its scorer sim_vs_ref is reported next to pack 7's
  summary value (0.9094 / 0.9079 / 0.8937 / 0.9229 / 0.9401) as a cross-check; that comparison is reported only and
  does not gate.
- **Scorer:** `tools/dr_score.py`, the same code for both sides: e10v_score.py's functions with the episode's kit roster
  and library_v3 host meshes.
  - sim_vs_ref = exactly pipeline/qa.py policy's metric;
  - RPE / MPPE / AUC = the score-status session's GT-free audit chain (docs/analysis/evalaudit-20261031/audit.py on
    origin/claude/standings-20261031, which e10v_score.py reproduces);
  - fail = RPE > 5 cm.

  Every rollout is scored against the ONE reference P = the packed reference parquet; the reference is unchanged, so
  one reference is enough. Own-reference check: P's poses at each reference_frame must equal the rollout's stored
  reference columns (|Δpos| ≤ 1e-6 m, |Δq| ≤ 1e-6 up to sign); a failure is INVALID. A rollout with any non-finite score
  is "not scored".
- **Clauses** (N = the candidate's scored confirmation draws, K = the packed policy's scored H5p7 draws), each compared
  with a 1e-9 tolerance in favour of "holds":
  - (a) mean sim_vs_ref(N) ≥ mean sim_vs_ref(K);
  - (b) share of N with RPE > 5 cm ≤ that share of K;
  - (c) median RPE(N) ≤ median RPE(K);
  - (s) sim_vs_ref of N's draw 1 ≥ the old packed draw's sim_vs_ref − 0.05.
- **Labels:**
  - **PASS** (swap-eligible): all four clauses hold, with n(N) ≥ 10 and n(K) ≥ 10;
  - **NO-SWAP**: any clause fails;
  - INCOMPLETE and INVALID: section 6.
- **Arm choice:** only D against packed. There is no other arm, no best-of-seeds on confirmation draws and no
  re-selection after the confirmation.
- **Reported, not gating:** n / mean / sd / min / max / median per side; fail counts; the audit's own flag; per-object
  AUC; each clause's margin; an EQUAL-FLOOR note when both sides fail ≥ 90 % of draws; the training-box seed table; and
  evaluation return codes.

## 5. Expectations and hypothesis (stated before the results)
- **[H-dr]** Small start-state perturbations in training make the policy less sensitive to the draw-to-draw start
  differences that the official evaluator amplifies, so the policy fails less often across draws.
  - Falsified for an episode if its D candidate's fresh-draw failure share (b) is higher than the packed policy's.
  - Not supported if its 10-draw sd is not lower. The sd is reported but does not gate.
- **Prior [M, determined-wright's screen on public episodes]:** D did not steady unstable episodes there (ep2 sd
  0.10 → 0.25, ep18 0.008 → 0.056). The expected gain is small and could be negative; the swap rule protects the pack.
- **D on the standard learner (25, 30) is untested.** It has not been run at 250M steps, with FC_IMMEDIATE_FIRST_FRAME,
  or with FC_DR_SKIP_IMMEDIATE beyond the 17/17 CPU test.
- Determined-wright's CPU reset check (share of worlds whose objects move > 1 cm under D, for 14 / 16 / 25 / 30 / 33;
  ~23:00 UTC) is reported only and does not gate.

## 6. INCOMPLETE and INVALID
- **INCOMPLETE** means no reading and no swap yet. It is completed only with the same commit and the same reference;
  nothing is re-tuned. Its causes and remedies:
  - a training seed is missing or thin, or a standard-learner main evaluation was cut: retrain only that seed on a new
    box (same job string with `SEEDS=<seed>`, run id `<date>-dr<box>r<seed>-<sha7>`), then merge all boxes again;
  - the confirmation has fewer than 10 scored draws: top-up draws of the same checkpoint on a new confirmation box. They
    are copied into the same tree as r11, r12, …, and draw 1 stays the original by position;
  - the packed side has fewer than 10 scored H5p7 draws: top-up draws of the packed checkpoint, added as r11… of the
    packed set and scored with one glob over the whole set;
  - the old packed draw is not scorable, or a packed header or stage could not be read: fetch it and re-run the tool on
    CPU.
- **INVALID** means the packed policy stays and there is no reading. Its causes:
  - verification failed (reference, assets, recipe, steps, seed, rollout identity, or a missing or wrong D log line);
  - the D line is present in a non-D training;
  - the pack-side check refused, or its file is missing;
  - the own-reference check failed;
  - a checkpoint sha256 mismatch on either side;
  - a clause value that is NaN or infinite.

  An INVALID episode is not retried on the same evidence. A code fix is a new commit and a new pre-registered run.

## 7. What a PASS buys
For that episode, its D draw-1 rollout (the confirmation's `results/submission/results/episode_0000NN.{parquet,json}`,
or the r<i> that is draw 1) replaces its packed rollout in pack 9b. Pack 9b is assembled on CPU from pack 9a+ plus the
swapped episodes, and every other episode stays byte-identical. The upload is decided outside this job: the owner's
word, in the session that uploads. NO-SWAP, INCOMPLETE and INVALID leave the packed rollout in place. Accuracy, failures
and cost are reported together. The expected leaderboard effect is not estimated here; the swap rule is the decision.

## Amendment (3 Nov 2026 ~01:50 UTC): two-host confirmation for every FUTURE swap
Adopted by the coordinator (keen-heisenberg) on the evaluator-gap result (docs/research/work/pf-evalgap-20261103/):
the pristine evaluator gave the same checkpoints 0.926 / 0.937 on one host and 0.768 / 0.826 on their training hosts,
so a single host's fresh draws can mislead.
- Section 3 becomes: 10 fresh official draws on the training box AND 10 on a second, different host (a separate box,
  different offer / machine), each on the pristine evaluator; both hosts named in the pre-registration.
- Section 4 (swap rule a / b / c / s) and the +0.02 inclusion bar must hold on EACH host's 10 draws separately; draw 1 of
  the training-box set stays the packed rollout. A failure on either host = NO-SWAP; no host may be dropped or re-run
  after the fact.
- Applies only to swaps pre-registered after this amendment; verdicts already made (incl. eval 30 sm NO-SWAP, eval 14 p0m
  PASS in pack 14p) stand.
