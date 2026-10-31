# Eval-10 retrain on the S12 V4p reference (conditional on the ep11 gate PASS): pre-registration

Written 2026-10-31, ~17:31 UTC, before any eval-10 V4p reference, policy, rollout or score exists. At that time the
ep11 rollout gate (`../ep11gate/PREREG.md`, box 58552489, run `20261031-e11g-663b7df`) was still training and the pack-10
comparison set `20261031-h5p7-1a7cdff` was still evaluating; neither result had been read. The only eval-10 V4p output
that existed is mask10's GT-free post-hoc track (`../mask10/README.md` §4; no reference, no policy). The launch commit
must contain this file unchanged; build notes go to `BUILD.md`, the job string and cost to `JOBS.txt`. Labels: [M]
measured, [E] estimate, [H] hypothesis.

## 1. Question, status, what may launch it
- **Question.** Does the packed eval-10 recipe, retrained on eval 10's V4p reference (S12 `--s12_mode support` + MuJoCo
  seat of the beige cup + S2), give a policy that beats the packed eval-10 policy (run `20261026-gl10A2-5e0e100`, the
  only failing eval episode of packs 6–8: packed draw sim_vs_ref 0.4563, GT-free RPE vs our reference 15.76 cm, beige
  cup left behind; 29 Oct H5 0.4495 ± 0.007 over 10 draws) under the agreed pack-10 swap rule (§5), against both our
  references?
- **Launch condition.** Only if the ep11 gate's verdict is **PASS** (its PREREG §3), and only with the owner's go-ahead
  for the spend (§9). FAIL / INCOMPLETE / INVALID of the gate: nothing here launches.
- **V4p is post hoc on eval 10** (designed after seeing eval 10's GT-free track, mask10 §1 item 7). The ep11 gate is its
  pre-registered test on the public twin; this retrain is what a PASS buys (gate PREREG §5). Nothing here is tuned on any
  eval result: there is no eval-10 V4p result yet, and this design copies the gate's chain and recipe unchanged.

## 2. Inputs (eval 10's stored perception, the one behind packs 6–8; single-file store downloads, md5 checked)
Eval 10 has no ground truth. Object names and slot order (blue_cup, beige_cup) come from the track's `cam_T_` keys and
the kit roster.

| input | store path | md5 |
|---|---|---|
| stored track (perc2, library_v3) | `runs/20261026-pack6-5203d42/perc2/ep10/poses.npz` | `4fc5529eb457d706588e9b9fcf703baa` (sha256 `fb9103fa…` = evB's, T1) |
| its VO record | `runs/20261026-pack6-5203d42/perc2/ep10/vo.json` | `64248915f0f480069521e4847da190c3` |
| frame-0 depth source | `runs/20261026-pack6-5203d42/perc2/ep10/det_f0.npz` | `94c63769e568da177406ff6c39317349` |
| refine's frame-0 depth | `depth0.npy` = det_f0 `depth` (half resolution) as float32 repeated 2×2 (T1's construction) | `d1543641b2f20cf024cdf1039631f671` |
| hands (KR inside) | `runs/20261026-pack6-5203d42/refs/perc2mck/ep10/hands_refined.npz` | `419c230800b727240663597916cba59e` |
| hands for the reference folder | `runs/20261026-gl10A2-5e0e100/refs/perc2mck/ep10/{hands.npz, hands_refined.npz}` (the packed base reference's; its hands_refined must equal the row above) | checked in BUILD.md |
| packed reference (P) | `runs/20261026-gl10A2-5e0e100/refs/glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/ref_gl_ilc.parquet` | `1a5003d94852c275519066645a1b9869` (packed_refs.json '10') |
| packed checkpoint (recipe config) | `runs/20261026-gl10A2-5e0e100/results/glock_public/ep10/best/policy.safetensors` | sha256 `76a12265…cbb9` |
| collision pieces | `meshes/carve/ev10` (unchanged) | repo |

These are the inputs mask10 used for eval 10 (`../mask10/eval10/inputs_sha256.txt`, T1's `t1_eval10.sh`).

## 3. Design (fixed)
### 3.1 The V4p track (the exact mask10 eval-10 commands, as `tools/e11g_tracks.sh` arm T)
`refine.py --steps S12 --s12_mode support` → `tools/nest_physics.py --mode inner --pieces meshes/carve/ev10 --hands
<hands_refined>` → `refine.py --steps S2 --hands <hands_refined> --depth <depth0>`, on an input folder holding
`poses.npz`, `vo.json`, `hands_refined.npz`, `depth0.npy` (as mask10's; no `poses_world_vo.npz`). Pinned venvs as the
gate (refine: numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, rtree 1.4.1; physics: numpy 2.4.6, scipy 1.18.0, trimesh 4.12.2,
mujoco 3.8.1).

**B0 on the box (before any reference is built)**: the rebuilt track vs the CPU rebuild committed in `expect/` (whose md5
must equal mask10's `scratchpad/mask10/eval10/posthoc/V4p/poses.npz`, `fa449903…`, or BUILD.md says why not), over every
frame and object, the gate's bands: **IDENTICAL** (md5) / **NUMERIC** (world_T_cam byte-identical, every pose within
0.01 mm and 0.001°) / **DIFFERS** (within 5 mm and 2°: MuJoCo's settle need not be bit-reproducible; go on with the box's
own track, flagged) / otherwise **MISMATCH**: the job stops before any reference (no training).

### 3.2 Reference (variant mck, as the packed eval-10 base reference `20261024-evB-664e5fd` refs/perc2mck/ep10)
- `pipeline/pipeline_ep.sh 10` with `SPLIT=eval PERC=perc2 VARIANT=e10vmck PDIR=<the V4p track folder>`, the stored hands
  copied into the reference folder (hands_mp / hand_refine skipped), `MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1
  CR_ARGS="--rest_settle 1"`, `ASSETS=/content/assets` = `make_assets.py meshes/library_v3 --pieces meshes/carve/ev10`
  (0.3 kg), `STOP_AFTER=reference` → `refs/perc2e10vmck/ep10`.
- **mkref's frame-0 depth** (it reads frame 0 only, for the table plane and disc). The depth behind the packed reference
  was never stored (depth audit MAP §1). Candidates: **D1** = perc2's own frame-0 depth of the stored track (det_f0,
  half resolution, float16; `depth0.npy` above as a 1-frame `depths_fs0.5.npy`), **D2** = frame 0 of
  `cache/depth/eval/ep10/depths_fs0.5.npy` (the 29 Oct recomputation). **Rule:** use the candidate whose mkref stage-(a)
  table plane (mkref's own `fit_table`, its defaults) on the packed reference's own input (the raw stored track) is
  closer to the packed base reference's `table_frame.npz` (smaller angle between plane normals; within 0.05° the smaller
  |Δd|). Measured on CPU before any V4p reference exists; it reads no score. The choice and its md5 go to BUILD.md and
  are fixed in the job.
- Grasp-lock reference stages once, seed 42 (`glock_public.sh REF_ONLY=1`, PERC prefix `perc2e10v`): grasp lock with the
  recipe's GL_ARGS, ILC, zero-action replay, rest check, REPLAN 1 → `refs/perc2e10v_glockt/ep10`. Both seeds train on that
  one file (byte copies `refs/perc2e10vs{42,43}_glockt/ep10`, `REUSE_REF=1 REQUIRE_REUSE=1`), so a seed difference is RL
  noise only. **V** = this trained reference.
- Folders are new names only (`refs/perc2e10v*`, `runs/perc2e10vs*_glock`, `results/perc2e10vs*_glock_public`,
  `results/ev10_v4p`); nothing named `refs/glockt/ep10`, `refs/perc2mck/ep10` or `results/glock_public/ep10` is written.

### 3.3 Recipe: gl10A2's, exactly as the ep11 gate used it (gate PREREG §2.4), with SPLIT=eval
`ops/jobs/glock_public.sh`; `LIB=meshes/library_v3`, `PIECES=meshes/carve/ev10`, `SF=0`, `SETTLE=0`, `REPLAN=1`,
`EVOLVE=0`, ILC default (4 iterations, no `ILC_HOLD`), `CURVE_REP=3`, `STEPS=70004736`, `ES=0`, `CURR_SCALE` unset,
`TRAIN_SLOTS=2`, FDR rewards + VOC fix, default curriculum, kp 400 embodiment, `GL_ARGS="--single_hand 1 --mcp_first 1
--close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15"`; `NREP=10`, `PAR=2`,
`EVAL_TIMEOUT=1200`. **Seeds 42 and 43** on one box, one commit, trained one after the other (one glock_public call per
seed). Deviations from gl10A2 (all as the gate): NREP 10 (gl10A2 5), PAR 2, EVAL_TIMEOUT, reference stages once and
shared by both seeds, current commit, base reference from the stored track + refine instead of the evB box's raw perc2.

### 3.4 Checkpoint, seed and confirmation (no ground truth anywhere)
- **Checkpoint per seed:** glock_public.sh's rule: the curve checkpoint with the best mean sim_vs_ref over 3 official
  evaluations each, against **V** (the training reference); then NREP 10 training-box evaluations (FlashCHORD
  `evaluate_policy.py`, 1 world) of it, scored sim_vs_ref against V.
- **Seed (rule 2 style, as mass_eval_verify.rule2):** over the seeds with ≥ 8 scored training-box rollouts, the higher
  mean sim_vs_ref; if the two means (4 decimals) are within 0.005, the lower sd (ddof 1); still tied, seed 42. Both seeds
  are needed for the choice: a seed without a chosen checkpoint or with < 8 scored rollouts makes the run INCOMPLETE
  (§6) and no confirmation is run.
- **Confirmation: 10 fresh official draws of the chosen checkpoint** on the same box: the kit's
  `examples/run_policy_evaluation.py` on the pristine FlashCHORD worktree (the pack evaluator: submit_pack.sh /
  h5_reeval.sh draws), one invocation per draw, `--checkpoints {"10": <chosen>}`, each cut at 1200 s. Draw order is the
  invocation order; **draw 1 by position is "the new packed draw"**. Training-box rollouts never enter §5.

### 3.5 Scoring of every rollout against BOTH references (`tools/e10v_score.py`; GT-free)
For a rollout parquet (the evaluator's output: achieved = simulated object poses, reference columns = its own training
reference at each `reference_frame`) and a reference parquet X ∈ {V, P}:
- the reference columns are replaced by X's object poses at the same `reference_frame` (check: for X = the rollout's own
  training reference they must equal the stored columns within 1e-6 m / 1e-6, else INVALID);
- **sim_vs_ref(X)**: exactly `pipeline/qa.py policy`'s metric (kit AUC functions, 500 points on a 5 cm sphere, warped to
  the reference start, world 0);
- **RPE(X), MPPE(X), AUC(X)**: the score-status session's GT-free audit method (`docs/analysis/evalaudit-20261031/
  audit.py` on `origin/claude/standings-20261031`, rdlib chain: the kit's metric file, library_v3 meshes as host with
  identity registration, the kit's frame-0 scene alignment), re-implemented in `e10v_score.py` without any
  ground-truth function and checked against audit.py on the packed draw (BUILD.md);
- **failure(X)** = RPE(X) > 5 cm (the agreed rule's definition); audit.py's own flag (keypoint error > 5 cm in ≥ 20 % of
  frames) is reported beside it, not used.
- Scored sets: the 10 confirmation draws (new); **the packed policy's fresh draws: the 10 eval-10 rollouts of run
  `20261031-h5p7-1a7cdff`** (`results/h5/r1..r10/ep10/episode_000010.parquet`; draw 1 = its pack_eval draw, 2..10 =
  run_policy_evaluation.py), scored with the same tool against P and V (on the box if those files can be pulled, else
  on CPU after from the pushed V; the same code either way); the old packed draw (pack 6's
  `results/submission/results/episode_000010.parquet`, sim_vs_ref 0.4563 vs P) against P and V; the training-box rollouts
  (reported only).
- A rollout with any non-finite score is not scored (it counts toward no n).

## 4. Noise and power (stated before any result)
- Packed eval-10 policy [M]: 29 Oct H5 0.4495 ± 0.007 (10 draws), packed draw 0.4563; every packed draw sits at the
  static floor (beige left behind). H5p7 will give the fresh-draw mean, failure rate and median RPE used in §5.
- Public twin [M, orcB / mask10]: the true-motion reference stacks the cups at 0.940 ± 0.034 (one seed); our perceived
  reference stays at the floor (0.595 ± 0.000). [E] If V4p makes the eval-10 nest copyable, the new policy's draws move
  off the floor by a large margin (sim_vs_ref ≳ 0.7 vs V, RPE ≲ 5 cm) and clauses (a)–(c) are decided by a wide margin
  on 10 vs 10 draws; if it does not, the draws stay at the floor (≈ 0.45, RPE ≈ 15 cm) and (a) is a coin flip at a
  ±0.003 SE, which the conjunction of (a)–(c) on both references makes unlikely to pass by chance (≲ 10 % [E]).
- Between-seed spread on one grasp-lock reference [M]: ep2 0.552 / 0.581, eval 32 0.397 / 0.634 / 0.803. The seed
  choice uses the training-box draws only, so the 10 confirmation draws are an unbiased sample of the chosen policy.

## 5. Swap rule (the agreed pack-10 rule, work log 31 Oct ~16:10–16:20 UTC; applied by `tools/e10v_verdict.py`)
**Verbatim (as agreed):** per episode, over >= 10 fresh official draws, all GT-free: (a) mean sim_vs_ref >= the packed
policy's fresh-draw mean, (b) failure rate (GT-free RPE vs our reference > 5 cm; tool: the score-status session's
audit.py on branch origin/claude/standings-20261031 docs/analysis/evalaudit-20261031/) <= the packed policy's, (c) median
GT-free RPE not worse; secondary: the new packed draw (draw 1 by position) >= old packed draw - 0.05; FOR EVAL 10
(reference changed) (a)-(c) are scored against BOTH references (the new V4p one and the packed gl10A2 one) and must hold
on both.

**As applied here (fixed now):** N = the new policy's 10 confirmation draws, K = the packed policy's H5p7 eval-10 draws;
for each reference X ∈ {V, P}:
- (a_X) mean sim_vs_ref_X(N) ≥ mean sim_vs_ref_X(K);
- (b_X) fraction of N with RPE_X > 5 cm ≤ the fraction of K with RPE_X > 5 cm;
- (c_X) median RPE_X(N) ≤ median RPE_X(K);
- (s_X) secondary: sim_vs_ref_X(N draw 1) ≥ sim_vs_ref_X(old packed draw) − 0.05. The rule names no reference for the
  secondary; this PREREG checks it against both (the stricter reading). The literal own-reference reading (draw 1 vs V
  against 0.4563 vs P) is reported beside it.
- Comparisons use a 1e-9 tolerance in favour of "holds" (≥, ≤ are inclusive; float sums of 4-decimal values).
- **SWAP-ELIGIBLE** iff every clause (a_V, b_V, c_V, s_V, a_P, b_P, c_P, s_P) holds, the run is VERIFIED (§6) and
  complete (n(N) ≥ 10 and n(K) ≥ 10 scored draws). A disagreement between the references (a clause holds on one and
  not the other) is **NO-SWAP**, reported as such.
- **NO-SWAP** otherwise (complete, verified, some clause fails). The packed eval-10 policy stays.
- Reported with the label, not gating: per set n / mean / sd / min / max of sim_vs_ref, RPE, MPPE, AUC against each
  reference, the failure counts and audit.py's flag; each clause's two sides and margin; the gate PREREG §5's older
  single clause (mean sim_vs_ref(N) vs V ≥ 0.456) as a cross-check; the training-box summaries per seed and the chosen
  seed; per-object AUC; evaluation timeouts per stage printed right after the label.

## 6. INCOMPLETE / INVALID
- **INVALID** (no reading; fix the defect and re-run): B0 MISMATCH (the job stops), a failed verification: the chosen
  checkpoint's saved config → `task.parquet` → the seed copy whose md5 is V's → `object_urdf_paths` → URDFs under
  `/content/assets`, 0.3 kg, the ev10 pieces; mkref read the B0 track (md5 before = after) and the depth and hands of §2–3
  (md5); identity by content (V's blue cup over the S12 window [53, 161) follows the V4p track, not the stored track:
  the pre-contact-retargeting mkref output is closer to the V4p track mapped by its table frame); the saved config equals
  the packed checkpoint's in every key except `output_dir`, `task.parquet`, `reference.parquet`, `reset.seed`,
  `env.reset.seed`, `training.seed`; `training.total_environment_steps` = 70,004,736; `reset.seed` = the seed; every
  confirmation draw names the chosen checkpoint's sha256; the own-reference check of §3.5 fails for any scored rollout;
  `tools/no_oracle.py` refuses an input; a clause evaluates to NaN.
- **INCOMPLETE** (no reading; only the missing part is re-run, on this run's stored reference and commit, then the rule is
  applied once to the completed set): a seed without a chosen checkpoint or with < 8 scored training-box rollouts (that
  seed is retrained, then rule 2 and the confirmation run); fewer than 10 scored confirmation draws (top-up draws of the
  same chosen checkpoint until 10); fewer than 10 scored H5p7 eval-10 draws (top-up draws of the packed checkpoint with
  `h5_reeval.sh EPS_ONLY=10`, same evaluator); the old packed draw not scored.

## 7. What each outcome buys
- **SWAP-ELIGIBLE:** the chosen policy's draw 1 becomes the eval-10 candidate for pack 10 (its rollout replaces pack 7/8's
  eval-10 rollout; the candidate pack is built and validated offline). **The owner decides any upload; nothing goes to
  Kaggle without the owner's own word in the chat.** The commit of this job is the code commit of that pack.
- **NO-SWAP:** eval 10 stays as packed. No second retrain on V4p without a new pre-registration.
- **INCOMPLETE / INVALID:** no reading (above).

## 8. Integrity
- Eval episode: no ground truth exists or is read anywhere in this job; no score against mocap; nothing is tuned on eval
  results (there are none for V4p). Inference (refine, nest_physics, mkref, contact retargeting, grasp lock, ILC,
  re-plan, training, checkpoint and seed choice) reads our track, our hands, our depth, our meshes and the kit roster.
- New names only (§3.2); no stored reference is overwritten (the store keeps every run under its own run id).
- Run id `<date>-e10v-<sha7>`; the job refuses any other. `tools/no_oracle.py` must accept every input (store paths, the
  V4p track and references, the checkpoints) before training and before the confirmation.
- The packed reference P and the packed checkpoint are read only for scoring and the config diff; P is stored under
  `results/ev10_v4p/packed_ref/`, never under `refs/`.

## 9. Cost (details in JOBS.txt) [E]
One RTX PRO 6000 box: setup + reference ≈ 0.6 h, two trainings one after the other ≈ 2 × 1.2 h, 10 confirmation draws
≈ 0.3 h, scoring + push ≈ 0.1 h → ≈ 3.4–4.5 h, ≈ $4.5–6.5 at $1.3–1.5/h.

## 10. Build amendments (31 Oct ~18:20 UTC; before any eval-10 V4p result; sections 1–9 unchanged, sha256 `15e33e68…`)
No box has run; the only numbers since are CPU rebuilds, the depth-rule check, scorer checks and mock outputs (BUILD.md).
The question, design, rule (section 5) and bars are unchanged.
- **Section 4's "≲ 10 %" was too optimistic [E corrected, mock 'floor'].** When the new policy fails every draw like the
  packed one, (b) ties at 1.0 = 1.0 (ties hold) and (a) / (c) compare two floors within noise on both references, which are
  positively correlated; in the CPU mock such a policy read SWAP-ELIGIBLE (margins 0.001 / 0.03 cm). The agreed rule is
  kept as it is. Reported with the label, not gating: an **EQUAL FLOOR** note when both policies fail ≥ 90 % of their draws
  on both references. Such a swap has an expected leaderboard effect of about 0 (both at the static floor); the
  secondary bounds the packed draw's downside at −0.05. The owner decides any upload in any case (section 7).
- mkref's depth by the section 3.2 rule: **D2** (the eval-10 cache's frame 0 reproduces the packed table frame exactly;
  BUILD.md section 3).
- The identity check of section 6 also runs right after the grasp-lock stages, before any training (the job stops there
  on failure: no training is spent on a wrong reference).
