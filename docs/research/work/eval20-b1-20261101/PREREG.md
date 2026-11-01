# Eval-20 retrain on the b1 water-pitcher collision pieces: pre-registration (1 Nov 2026; written before any result)

**Status.** CPU build only. Nothing has been launched or rented. No training, rollout, overflow count or score of this test
exists. This file is committed with the code before the launch and must not be edited after it; later notes go to BUILD.md or
to dated amendments appended below section 13.

**Go.** The owner's go, relayed by the orchestrator (focused-pascal, 1 Nov), conditional on determined-wright's contact budget
of b1 against packed at 32 x 60 showing 0 overflow lines. That check read **clean** (section 1, [R] f59c897). The orchestrator
handles the launch. The conditions of the go are built into this rule and the job: the packed learner and recipe (section 2.4),
pack eligibility (2.5), the pieces applied exactly as the mesh lane specified (2.2), two pre-registered seeds (2.6), overflow
as the first check (5.4), the pack-9b seed choice (3.3), the training-box gate (4), the pack-9b swap rule on P (5.1), the
binding pack-10 inclusion bar (5.2), the cost (10).

**Labels.** [M] measured here, [R] read from another lane's committed record, [E] estimate, [H] hypothesis. Eval 20 has no
ground truth. Nothing here reads mocap, scans or `observation.objects` poses. Every score is GT-free, against our packed
reference P.

## 1. Evidence and hypothesis
- **The packed eval-20 policy is the grasp-lock learner, seed 42 [M].** Checkpoint
  `runs/20261025-evb1420-ee7ba8e/results/final_eval/ep20/policy.safetensors`, sha256 `61dcd7a6...` (pack 7's checkpoints.json;
  the local copy is a single-file store download with that sha256). Its stored resolved config (`tools/no_oracle.py` ckpt_config
  reader) has:
  - `output_dir /content/runs/glock/ep20-s42`, `task.parquet` = `refs/glockt/ep20/.../ref_gl_ilc.parquet`;
  - `training.total_environment_steps 70004736`, `reset.seed 42`, algorithm `flash_sac`, 480 keys;
  - sim / env.sim njmax 512, nconmax 256.

  The run's job.log (store, md5 2f3b169d) and `results/final_eval/ep20/choice.json` say the same:
  - `eval_both ep20: {"chosen": "glock", "means": {"std": 0.1461, "glock": 0.8923}}`;
  - the standard learner (runs/perc2mcks/ep20-s42, policy_170008576) scored 0.1461 on its 5 training-box rollouts and lost.

  The recipe is evb1420's `glock_public.sh` call at commit ee7ba8e (eval_both.sh step 2): SF 1, REPLAN 1 (a no-op: "every object
  is where its reference says before its grasp"), EVOLVE 0, GL_ARGS `--single_hand 1 --mcp_first 1 --close 10 --palm_clear
  -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15`, 70M steps, CURVE_REP 3, NREP 5. The curve chose the last checkpoint
  (70M, 0.880); the 5 training-box evaluations of it read 0.8923.
- **The packed side [M]** (`tools/dr_score.py` vs P on CPU, the same files the job pulls):
  - the packed policy's 10 fresh draws (run `20261031-h5p7-1a7cdff`, `results/h5/r1..r10/ep20`, all naming sha256 61dcd7a6):
    mean sim_vs_ref **0.8933** (raw 0.89335; = `h5_summary.json` "20", md5 fe5b4094: n 10, mean 0.8933, sd 0.028, min
    0.8193), **0 of 10 with RPE > 5 cm**, **median RPE 1.67 cm**;
  - the old packed draw: pack 6's eval-20 rollout, sim_vs_ref **0.8948** (= pack 7's summary value), RPE 1.30 cm. It is the board
    pack's eval-20 rollout [R: pack 7 checkpoints.json "pack 6, reused unchanged"; packs 8, 9a+ and 9b changed only eval 1, meshes
    and eval 33];
  - keen-heisenberg's "0.888 +- 0.043" is the earlier H5 set (masses-eval rank: 0.8884 +- 0.0433), not H5p7. This rule uses
    H5p7, the pack-10 comparison set.
- **The packed pitcher does not rest [M, R].**
  - The packed run's own FlashCHORD zero-action rest check (results/glock_public/ep20/rest_check.json): pitcher 10.4 mm /
    3.9 deg off by f8, before the hand arrives at f14 (fails 5 mm / 2 deg); blue cup 0 / 0.
  - The mesh lane [R] (bold-albattani 9c0bc0c, `rebase/README.md`): at the pitcher's rest frames its lowest collision point
    is a CoACD hull corner 1.36 mm below support_fill's arc foot. In a hands-free plain-MuJoCo settle the packed pitcher rocks
    6.4-7.5 deg at f183 / f192 (gate G3 fails), and falls over at f0 (195 mm / 94.6 deg, report only).
  - b1 clips every pitcher piece at the foot's base plane (0.03 cm3 removed from one hull). Plain MuJoCo: f183 / f192
    1.59 mm / 0.38 deg and 1.62 / 0.55 (G3 passes); f0 8.5 mm / 3.2 deg (report only).
- **FlashCHORD contact budget, b1 vs packed [R]** (determined-wright f59c897, `contact_budget/README.md` "Eval 20, b1"; same
  apply method; P md5 4d06d8d4, sim=rl, 32 x 60, explicit f0 / 14 / 152 / 183 / 192):

  | set | overflow lines (sampled / explicit) | sampled hold max (median) | explicit max |
  |---|---|---|---|
  | packed | 0 / 0 | 348 (293) | 317 |
  | b1 | **0 / 0** | 342 (291) | 321 |

  Under b1 the blue cup touches the world-body geom (up to 6 contacts per world sampled, 31 at the explicit frames); packed
  shows none for the cup. The settle check below reads these as the cup resting on the table.
- **FlashCHORD settle, b1 vs packed [R]** (determined-wright 85e8ef8, `ev20_settle/README.md`): section 13.
- **The pitcher is hands-off at f192 [M]** (`cpu/out/h30_ep20.json`; OUR reference's robot hand frames, retargeted from our
  perceived hands; no mocap). The nearest robot hand point is 149 mm from the pitcher's visual surface at f192 (138 mm from the
  cup). The pitcher is hands-off (H30, > 30 mm) from f165 to the last frame f201. The mesh lane's frames.json agrees (H30 at
  f165-f201; T-rest runs 181-186 and 188-197).
- **[H-b1]** The packed pitcher's collision copy cannot rest where P puts it: it rocks off a CoACD corner at the start (f0-f14,
  before the hand) and at its final rest. Training then fights an object that moves on its own. With b1 the start is at rest,
  so the grasp-lock learner tracks P better. Eval 20's fresh-draw mean rises, failures stay at 0.
- **Falsifiers, in order:**
  1. a training log has more than 1,000 overflow lines: the pieces are not clean at 4,096 worlds (5.4);
  2. the reported b1 zero-action rest check still has the pitcher beyond 5 mm / 2 deg before the hand comes (f14): the start
     is not fixed in FlashCHORD (reported, not gating: 5.6);
  3. the training-box gate is not met (4), the swap rule fails (5.1), or the gain is below the inclusion bar (5.2).

## 2. Design (fixed now)
### 2.1 Box and job
- One RTX PRO 6000 (96 GB) on demand, snapshot `pt2.11-cu130-py313-20261020`.
- Job: `ops/jobs/ev20_b1.sh` at the launch commit. Run id `<date>-e20b1-<sha7>`; the job refuses any other.
- Job string: `bash ops/jobs/ev20_b1.sh`. Nothing can be overridden from the job string.

### 2.2 The collision pieces (the one changed input)
- **Set ev20b1** = `meshes/carve/ev20b1/`: a byte copy of the mesh lane's `rebase/sets/ev20/` at origin/claude/bold-albattani-6qmxsv
  83d18d0 (the lane's FROZEN.md, 06:40 UTC). The 41 pieces are byte-identical at the result commit 9c0bc0c [M].
  - `water_pitcher/piece_00..40.obj`: 33 CoACD hulls of the pitcher glb adb315f3 (one cut) + the 8 arc-foot sectors;
  - `MD5SUMS` md5 **fe9aeca079fdcc7524a06f46fcd0a7ae** (= the lane's "folder hashes to fe9aeca0"), FROZEN.md md5 4259a6cf...;
  - `PROVENANCE.md` (source commits, GT-freedom, gates, trades).
- **GT-freedom.** The lane's README: "Ground truth. None read. Inputs: our references (object poses, robot hand frames), our
  support usda, our meshes and the packed pieces. No scan, mocap, parquet object pose or *_align. Nothing tuned on eval
  scores; none exist here." [R]. The b1 rule's inputs are P's poses at its rest frames, the packed foot pieces and the support
  usda. The lane's motivation (posefix, public-episode mocap) produced no offset here: the measured base shift d = +0.01 mm
  was "not needed" [R]. `tools/no_oracle.py` accepts the folder [M].
- **Gates, failed gates and trades** (lane's README and GATES.md A1 [R]):
  - G1, G2 (vacuous: no partner-rest frame), G3, G5, G6 and convexity pass. **G4 is flagged**: plain MuJoCo rows +46-64 % per
    frame (max 316, no overflow). The binding FlashCHORD budget is clean (section 1).
  - **Amendment A1 is post hoc**: it was written after the packed eval-20 settle failed, before b1 was built, for this one set.
  - The lane's settle engine is plain MuJoCo, not MuJoCo-Warp. Hands are absent and the table is a plane.
  - **FlashCHORD settle trade [R, section 13]**: at the hands-off frame f192 the pitcher falls over in both sets, and b1 is
    worse than packed there (12.0 cm / 50 deg vs 6.8 cm / 28 deg). At f183 b1 moves less but turns more (0.37 cm / 3.2 deg vs
    0.62 cm / 2.0 deg). At f152 b1 is better (0.28 cm / 0.3 deg vs 0.39 / 1.5). The blue cup is better under b1 at every frame.

### 2.3 Application (exactly the mesh lane's method, and the one determined-wright's checks used)
- `pipeline/placement_carve.py assets refs/sf/ep20/assets meshes/carve/ev20b1 <out>` on the packed asset copy the reference
  names; `<out>` then replaces `refs/sf/ep20/assets`. SF=0. **Not** `make_assets.py --pieces`, which would rebuild the blue cup
  from the library and drop its 0.5 cm fill.
- [M, CPU on the real packed files] Only `urdf/water_pitcher_rigid.urdf` changes: 6772f954 (9 `<collision>`: the glb + 8 foot
  STLs) -> **77b395a5** (41 `<collision>`, col_00..40.obj, each a byte copy of piece_NN.obj). That is the lane's own route-A
  URDF (`results/ev20_a1/water_pitcher_rigid.route_A.urdf`, md5 77b395a5). Outside `<collision>` the URDF is the packed one:
  the visual and the **inertial are unchanged**. Every other file is byte-identical: the blue cup URDF 31cd001d and glb
  d2be7e3d (with its fill), the pitcher glb adb315f3. So the mass properties do not change; the one changed variable is the
  pitcher's collision geometry.
- The job keeps a pristine copy of the packed asset folder in `/content/e20b1_in` (not pushed) and checks the carve against it
  (`tools/e20b1.py assets`).

### 2.4 Reference and recipe: the packed ones
- **P** = `runs/20261025-evb1420-ee7ba8e/refs/glockt/ep20/.../ref_gl_ilc.parquet`, md5 **4d06d8d42d57d84b1d25a166e8a90adc**,
  trajectory fingerprint c1e09fcc..., support stage 1388703a... (glockt = perc2mck base, checked). It is pulled through
  `docs/research/work/masses-eval-20261031/packed_refs.json`'s eval-20 pull_files (single-file downloads, no store listing) and
  checked against the pinned md5 and the table. Each seed trains on a byte copy, `refs/e20b1s<seed>_glockt/ep20`.
- P was built on the packed collision copy (grasp lock, wrist ILC, the zero-action replay). It is not rebuilt: a rebuild would
  be a second change, and both sides are scored against the same P.
- **Recipe**: the frozen glock_public.sh training path on a stored reference, as the D arm and the eval-10 retrains ran it:
  REUSE_REF=1 REQUIRE_REUSE=1 (no reference stage runs), kp-400 embodiment, FDR rewards + VOC fix (TRAIN_ARGS), 70,004,736
  steps, CURVE_REP 3, checkpoint by sim_vs_ref vs P, NREP 10 training-box evaluations (5 in evb1420; not a config key),
  EVAL_TIMEOUT 1200, PAR 2. GL_ARGS / REPLAN / EVOLVE as evb1420 (logged only). Stock contact limits: no `sim.*` override.
- The opt-in `EVAL_E20B1=1` in glock_public.sh allows the prefix `e20b1s<seed>` for eval 20, RUN local, REQUIRE_REUSE=1 only.

### 2.5 Pack eligibility
- Every stored-config key of a chosen checkpoint must equal the packed eval-20 checkpoint's (sha256 61dcd7a6), except
  `output_dir`, `task.parquet`, `reference.parquet`, `reset.seed`, `env.reset.seed`, `training.seed`. Sim and env.sim must read
  512 / 256. The pieces do not appear in the config; they reach FlashCHORD through P's URDF paths, checked by md5 (3.2).
- [M, CPU] (`cpu/out/config_guard_test.json`, 25 / 25):
  - the REAL packed eval-14 and eval-20 checkpoints of the same run differ only in paths and `reference.num_frames`;
  - [R] the D arm's eval-14 cells (code a1a7e25, this training path) reproduced evb1420's eval-14 config within the allowed
    keys; since a1a7e25 glock_public.sh changed only in PERC-guard lines;
  - a stand-in carrying this job's names gives a diff inside the allowed keys, and no_oracle accepts it;
  - a 1024 stand-in and an extra key are caught.
- The CPU mock compares every training CLI key with the REAL packed eval-20 config, and TRAIN_ARGS with evb1420's own
  job-log line (BUILD.md section 8).

### 2.6 Seeds
- **Seeds 42 and 43**, trained one after the other, one glock_public.sh call each. 42 is the packed policy's seed; 43 is the
  second seed of every earlier two-seed retrain.

## 3. Checks and seed choice
### 3.1 Before training (any failure: STOP, INVALID)
- `tools/e20b1.py pieces`: MD5SUMS and FROZEN.md md5 pinned; file set = MD5SUMS = FROZEN.md; exactly water_pitcher/piece_00..40.
  `tools/no_oracle.py` on the folder.
- `tools/e20b1.py inputs`: P md5 + fingerprint (pinned and = packed_refs.json); the support stage; the packed asset copy (URDF
  and glb md5s, 9 / 1 collisions, 0.3 kg); the packed checkpoint's sha256; the REUSE_REF records.
- The carve, then `tools/e20b1.py assets` (section 2.3's facts, all pinned).
- `tools/e20b1.py arms`: byte copies of P per seed; P names the b1 URDF md5s at 0.3 kg. `tools/no_oracle.py` on every input.

### 3.2 Per-seed verification after training (`tools/e20b1.py cells`, pack 9b PREREG 1.3 style)
- The chosen checkpoint is followed as the official evaluator loads it: saved config -> task.parquet -> this seed's copy
  (md5 = P) -> object_urdf_paths -> URDFs (b1 md5s, 41 / 1 collisions, 0.3 kg, under refs/sf/ep20/assets) and the support stage.
- The config must pass section 2.5's diff at stock limits. Steps must be 70,004,736 and reset.seed the seed.
- best/ must be the curve's choice, and the training-box rollouts must name its sha256.
- Status per seed: VERIFIED, INVALID or MISSING.

### 3.3 Seed choice (pack 9b PREREG section 2)
- Over the two seeds, each needing a VERIFIED cell with at least 8 scored training-box rollouts (sim_vs_ref vs P):
  1. the higher mean wins;
  2. if the means (4 decimals) are within 0.005, the lower sd (ddof 1) wins;
  3. if still tied, seed 42.
- An INVALID cell makes the run INVALID. A missing or thin seed makes it INCOMPLETE. There is no single-seed fallback.

## 4. The training-box gate
- The 10 official confirmation draws run **only if** at least one VERIFIED seed with n >= 8 has a training-box mean sim_vs_ref
  vs P **above 0.8933**: the packed policy's fresh-draw mean, H5p7 `h5_summary.json` (section 1). The comparison is strict,
  with 1e-9 in favour of "not met".
- Otherwise the job reports **NO-SWAP ("training-box gate not met")** and ends without confirmation draws. It still scores the
  training-box draws, the packed side and the old draw, and reports the overflow and the rest check.
- The gate does not pick the seed; section 3.3 does. If one seed meets the gate and the rule picks the other, the rule's pick
  is confirmed.

## 5. Swap rule, labels and reported clauses (`tools/e20b1.py verdict`)
### 5.1 The agreed swap rule (pack 9b PREREG section 4, verbatim)
> Per episode, over >= 10 fresh official draws, GT-free: (a) mean sim_vs_ref >= the packed policy's fresh-draw mean;
> (b) failure rate (GT-free RPE vs our reference > 5 cm, audit.py) <= the packed policy's; (c) median GT-free RPE not
> worse; secondary: new packed draw (draw 1 by position) >= old packed draw - 0.05.

- N = the chosen checkpoint's 10 confirmation draws on the pristine evaluator: the kit's `run_policy_evaluation.py`, one call
  per draw, 1,200 s cap, at most 13 calls, stop after 3 rollout-less calls in a row (ev10_cs.sh confirm(), verbatim but for
  names). Draw 1 is the first call, in order, that produced a scored rollout.
- K = the packed policy's 10 H5p7 eval-20 draws. Old packed draw = pack 6's eval-20 rollout (sha256 61dcd7a6).
- Scorer: `tools/dr_score.py --ep 20`, one reference P, unchanged (e10v_score's chain: sim_vs_ref = qa.py's metric; RPE / MPPE /
  AUC = the GT-free audit; fail = RPE > 5 cm; own-reference check against P). Clause code: `tools/dr_verdict.clauses_of`,
  unchanged. Comparisons use 1e-9 in favour of "holds".
- With K's measured values the clauses read [M]: (a) mean(N) >= 0.89335; (b) **no draw of N with RPE > 5 cm** (K has 0 / 10);
  (c) median RPE(N) <= 1.67 cm; (s) draw 1 >= 0.8948 - 0.05 = **0.8448**.
- **SWAP-ELIGIBLE** iff every clause holds, the run is verified, and n(N) >= 10 and n(K) >= 10. Otherwise **NO-SWAP**.

### 5.2 Binding pack-10 inclusion rule
- A SWAP-ELIGIBLE eval 20 enters pack 10 **only if** (mean sim_vs_ref of N) - (mean sim_vs_ref of K) **>= +0.02 vs P**, on
  raw means, i.e. mean(N) >= 0.91335.
- Otherwise: "SWAP-ELIGIBLE but below the 0.02 inclusion bar: NOT included".
- The lesson behind it [M]: pack 9b's eval-33 swap passed the rule on a GT-free proxy gain of +0.0018, then scored about
  -0.016 vs mocap on the board.

### 5.3 Labels attached to every reading
- **EQUAL FLOOR** note: both sides fail >= 90 % of their draws.
- Per side and metric: n / mean / sd / min / max / median, fail counts, per-object AUC (blue cup, pitcher). The pitcher's AUC
  is reported because of the f192 trade (2.2).

### 5.4 Overflow label (the FIRST check; the rule still applies)
- O = the "nefc overflow", "broadphase overflow" and "narrowphase overflow" lines of each seed's training log
  (`runs/e20b1s<seed>_glock/ep20-s<seed>/train.log`), counted by `tools/e10nj.py overflow`.
- If a training log has **more than 1,000** such lines, the result is labelled **"pieces not clean in training"**. The swap rule
  and the inclusion bar still apply.
- Also reported: the requested-njmax distribution, the counts in OOM-retry, curve, training-box and confirmation logs.

### 5.5 Label order
1. **INVALID**: a STOP; a failed check of section 3; verify failure; an INVALID cell.
2. **INCOMPLETE**: a seed missing or thin.
3. **NO-SWAP ("training-box gate not met")**.
4. The rule of 5.1: SWAP-ELIGIBLE / NO-SWAP / INCOMPLETE (fewer than 10 scored draws on either side, or the old draw not
   scored once) / INVALID (P not the packed reference, a rollout naming another checkpoint, an own-reference failure, NaN).

### 5.6 Reported, never gating
- The b1 zero-action rest check: `tools/trace_rollout.py zero` of P on the b1 copy after training (the FlashCHORD tree patched
  as for training), `tools/trace_score.py`, `tools/rest_check.py` (5 mm / 2 deg until a hand comes), next to the packed run's
  record (pitcher 10.4 mm / 3.9 deg).
- The training-box seed table, the chosen seed, each clause's margin, evaluation return codes, training minutes.

## 6. INVALID and INCOMPLETE
- **INVALID** means no reading: any check of section 3; a confirmation draw naming another checkpoint; a failed own-reference
  check; no_oracle refusing the chosen checkpoint; a non-finite clause.
- **INCOMPLETE** means no reading. This job has no re-run mode; completing it needs a new decision. Causes: a missing or thin
  seed; fewer than 10 scored confirmation draws; the packed side not complete on the box (then scored on CPU after, same tool);
  the old draw not scored.

## 7. What each outcome buys
- **SWAP-ELIGIBLE and included (5.2):** the confirmation's draw-1 rollout becomes eval 20's candidate for pack 10. The pack is
  built and validated on CPU (`tools/pack_swap_rollouts.py`, no_oracle). The commit of this job is that pack's code commit.
  **The owner decides any upload, in the session where he gives the word.**
- **Anything else:** eval 20 stays as packed.

## 8. Integrity
- No ground truth exists for eval 20, and none is read. Inference (training, checkpoint and seed choice) reads P, our meshes,
  the b1 pieces and the kit roster. The H30 check of section 1 reads only P (our perceived and retargeted hands and objects).
- Nothing is tuned on an eval result: the pieces come from the lane's pre-registered gates on P (no scores); the gate bar and
  the old-draw value are the packed side's finished numbers; seeds and rule are fixed here.
- New names only: refs/e20b1s<seed>_glock*, runs/e20b1s<seed>_glock, results/e20b1s<seed>_glock_public, results/ev20_b1.
  The stored run's files are read, never written there. On this box `refs/sf/ep20/assets` holds the b1 copy (the path P names);
  it is pushed under this run id only.
- `tools/no_oracle.py` accepts this run's names and stock checkpoints (packable) and still refuses the njmax diagnostic's and
  oracle names [M, `cpu/out/config_guard_test.json`].

## 9. Expected effect and power [E]
- The packed policy is already good on eval 20 (0.8933, 0 / 10 fails). The rule is strict: no failure allowed, median RPE
  <= 1.67 cm, and +0.02 needs mean(N) >= 0.9134.
- If H-b1 is right, the start no longer drifts and tracking improves by a few hundredths. The training-box gate (0.8933) is
  then likely met.
- The f192 trade (2.2) can cost pitcher tracking in the hands-off end phase (f165-f201).
- Guess: P(SWAP-ELIGIBLE and included) about 0.2; most likely outcome NO-SWAP or below the bar [E, a guess, not computed].
- If included, the board effect is about +0.02 x 0.76 / 20 = **+0.0008 AUC** (0.76 board AUC per sim_vs_ref, rank.py) [E].

## 10. Cost [E]
Basis [M]:
- e10v (`20261031-e10v-caf38fb`; grasp lock, two sequential seeds + 10 draws, the structure of this job, same box type; its
  job.log as read by eval10-cs4-20261101/PREREG.md section 10): 139 min, **$3.25** at $1.375/h. Setup + inputs 10 min; track + reference stages 9.7 min (not run here); seeds 54.2 / 55.6 min;
  choice + 10 draws + scoring 9.6 min.
- One grasp-lock cell alone on the GPU (eval-14 carve `20261030-c14s42-328139c`, REUSE_REF, NREP 10): training 42.4 min, curve
  3.0 min, 10 evaluations 1.7 min; ledger **$1.57** (duration x rate).
- evb1420's eval-20 training itself: 59.7 min, sharing the GPU with eval 14.
- The orchestrator's basis: grasp lock about $1-1.5 a cell.

| stage | low (h) | central (h) | high (h) |
|---|---|---|---|
| boot, snapshot restore, setup, pulls (~40 single files), checks, carve, seed copies | 0.15 | 0.22 | 0.60 |
| 2 trainings (70M) + curves (7 x 3) + 10 training-box evaluations each | 1.55 | 1.85 | 2.40 |
| b1 zero-action rest check (reported) | 0.02 | 0.03 | 0.10 |
| 10 official draws (skipped if the gate is not met) | 0.08 | 0.12 | 0.25 |
| H5p7 / old pulls, scoring (~41 rollouts), verify, verdict, push | 0.05 | 0.10 | 0.25 |
| **total wall** | **1.85** | **2.32** | **3.60** |
| **$ at 1.27 / 1.375 / 1.50 per h** | **$2.3** | **$3.2** | **$5.4** |

- The ledger plans **$3.50**. The high column covers a slower training (+30 %) and slow pulls.
- Tail risks: a failed final push waits 60 min (+~$1.4). A STOP before training ends after setup (~$0.5-1.2, including
  run_job.sh's 30-min FAIL_HOLD).

## 11. Not covered
- A reference rebuilt on the b1 pieces; a pitcher set that also stands at f192 in FlashCHORD; other pieces or masses; njmax
  changes; other eval episodes; a re-run mode.

## 12. Files
Job `ops/jobs/ev20_b1.sh`; tool `tools/e20b1.py`; opt-in `EVAL_E20B1` in `ops/jobs/glock_public.sh`; pieces
`meshes/carve/ev20b1`; build notes `BUILD.md`; launch, ledger and after-box steps `JOBS.txt`; CPU evidence `cpu/`.

## 13. Settle check (the orchestrator's slot)
**Settle check: determined-wright 85e8ef8 (`docs/research/physics-2026-10-30/ev20_settle/README.md`) [R].** FlashCHORD at the
pin, sim=rl, 1 world, hands parked 3 m away with zero gains, P's pose (md5 4d06d8d4) at frame F with zero velocity, 2 s free
settle; packed `refs/sf/ep20/assets` vs b1 (the same placement_carve.py method). Collision shapes: cup 68, pitcher 41, in both.

| frame | set | cup drift at 2 s | cup lowest point vs table: ref / end / min | pitcher drift at 2 s |
|---|---|---|---|---|
| 152 | packed | 0.10 cm / 0.1 deg | -0.9 / -1.8 / -4.2 mm | 0.39 cm / 1.5 deg |
| 152 | b1 | 0.03 cm / 0.2 deg | -0.9 / -1.0 / -4.1 mm | 0.28 cm / 0.3 deg |
| 183 | packed | **4.19 cm / 29.4 deg (tips)** | +0.2 / +0.6 / -2.0 mm | 0.62 cm / 2.0 deg |
| 183 | b1 | 0.17 cm / 0.7 deg | +0.2 / +0.5 / -3.2 mm | 0.37 cm / 3.2 deg |
| 192 | packed | 1.27 cm / 0.5 deg | -0.5 / -0.3 / -2.3 mm | **6.82 cm / 27.6 deg** |
| 192 | b1 | 0.33 cm / 0.7 deg | -0.5 / -0.2 / -1.3 mm | **11.97 cm / 50.1 deg** |

- No overflow lines and no NaN. The budget run's new cup / world-plane contacts are the cup resting on the table; under b1 the
  cup is closer to P than packed at every frame and never sinks through.
- **Disclosed flag.** At f192 the pitcher falls over hands-free in both sets, b1 more than packed. f192 is **hands-off** in our
  reference (section 1: nearest robot hand 149 mm, H30 from f165 to the end), so it is not a pouring or in-hand frame. At this
  hands-off rest frame b1's pitcher is less stable than packed in FlashCHORD, while plain MuJoCo read the opposite (b1 1.62 mm /
  0.55 deg, packed 3.32 mm / 7.54 deg). The engines disagree; MuJoCo-Warp is the training and evaluation engine. A single
  settle draw per set is noisy (the carve verification of 30 Oct measured chaotic re-runs), so this is one draw, not a rate.
- Stop condition: none added. The rule of section 5 judges the outcome; the pitcher's per-object AUC is reported (5.3).
