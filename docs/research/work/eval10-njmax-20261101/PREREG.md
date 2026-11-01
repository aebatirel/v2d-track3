# Eval-10 njmax diagnostic: pre-registration (1 Nov 2026; written before any result)

**Status:** CPU build only. Nothing has been launched or rented, and no 1024 policy, overflow count, lift or score from
this test exists yet. This file is committed with the code before any launch. It must not be edited after the launch.
Owner's go, relayed by keen-heisenberg (work log 1 Nov ~02:45 UTC, owner verbatim "Okay go", 02:43 UTC): ONE eval-10
training at njmax 1024 / nconmax 512, about $2–3. Conditions: diagnostic only and never packed; pre-registered and
committed before launch; the same checkpoint also evaluated at njmax 512; the usual box rules.

**Labels used here:** [M] measured, [E] estimate, [H] hypothesis. Eval 10 has no ground truth. Nothing here reads
mocap, scans or `observation.objects`. Every score is GT-free, against our references V (the V4p trained reference) and
P (the packed reference).

## 1. Evidence so far and the hypothesis
- [M] Run `20261031-e10v-caf38fb` (eval-10 V4p retrain, ops/jobs/ev10_v4p.sh, commit caf38fb): NO-SWAP [EQUAL FLOOR].
  Its official confirmation draws score mean sim_vs_ref vs V **0.4593** (10 draws, sd 0.0093) and vs P 0.4486. The packed
  policy scores 0.4632 / 0.4525. Both policies fail every draw (RPE ~15.9 cm).
- [M] The cup the reference moves is the **beige cup**. The reference lifts it about 23.5 cm and nests it into the blue
  cup, which stays on the table (reference lift 1.5 cm). The job log's curve label "blue_cup: lift 0" tracks the resting
  blue cup only (`docs/analysis/ev10-stack-20261026/README.md`). e10v's `curve.json` files (pulled 1 Nov, copied to
  `cpu/out/control/`) give the beige cup's r1 lift at 0.0–0.3 cm at 13 of its 14 checkpoints. The exception is 2.5 cm at
  seed 42's 60M checkpoint, a knock, still "lost at" frame 40. The blue cup reads 0.1 cm at all 14.
- [M] e10v's training logs hold 6,010,501 (s42) and 5,846,480 (s43) lines of "nefc overflow - please increase njmax to
  N". The requested N has median 580, p95 752, p99 808 and max 1,057 / 1,006, against njmax 512. There is no broadphase
  overflow. The first line comes before 1 % of training. The ep11 gate trainings (`20261031-e11g-663b7df`: the same ev10
  pieces and the same V4p method on the public twin) logged only 62 and 123 lines. The packed eval-10 run
  `20261026-gl10A2-5e0e100` logged 8.37 M. The scored draws logged 0.
- [M, determined-wright, CPU at the FlashCHORD pin] The overrides `sim.njmax=1024 sim.nconmax=512` are stored in the
  checkpoint's resolved config. They survive `apply_evaluation_composition`, and the official evaluator builds its
  SolverMuJoCo with njmax 1024 / naconmax 512. This build confirms it on real checkpoint files: `BUILD.md` section 3.
- **[H]** During eval-10 training the cup-in-cup contact needs more than 512 constraint rows, and MuJoCo-Warp drops the
  rest. With the nested-cup physics corrupted, the learner cannot learn to lift and nest the beige cup. This causes the
  "cup never lifted" floor.
- **Falsifier** (this test): one eval-10 training with room for the rows (njmax 1024 / nconmax 512), with everything
  else held equal. If the overflow is gone and the cup is still never lifted, the dropped rows are not the main cause.

## 2. Design (fixed now)
- **Box and job:** one RTX PRO 6000 (96 GB) on demand, snapshot `pt2.11-cu130-py313-20261020`, `ops/jobs/ev10_nj.sh`
  at the launch commit, run id `<date>-e10nj-<sha7>` (the job refuses any other).
- **Reference:** e10v's stored V, pulled through e10v's own re-run manifest (`results/ev10_v4p/rerun_files.txt`), one
  single-file pull each. Its identity is fixed by e10v's `arms.json`: V md5 `5d22fc5782a919f2466988768d0708fa`,
  trajectory fingerprint `8f408d5101f108cda929fd3ee346e970`, base reference md5 `ca4ae8dcbc290d66ce09d6ad69a09410`,
  URDFs 0.3 kg with e10v's COM. The training uses a byte copy, `refs/perc2e10njs43_glockt/ep10`.
- **Recipe:** e10v's, exactly. The recipe lines of ev10_v4p.sh are copied verbatim (CPU check). The only additions are
  the seed choice and the two training overrides `sim.njmax=1024 sim.nconmax=512`, which `fc_patches` appends after the
  FDR overrides: STEPS 70,004,736, SF 0, REPLAN 1 (not used: REUSE_REF), CURVE_REP 3, NREP 10, PAR 2, EVAL_TIMEOUT 1200 s.
- **Seed:** **43 only** (pre-registered here). It was e10v's chosen seed by rule 2 (s43 mean 0.4512 vs s42 0.4524,
  within 0.005, lower sd). Seed 42 is not trained.
- **Checkpoint choice:** the usual glock_public.sh rule. The checkpoint with the highest curve sim_vs_ref vs V (mean of
  3 evaluations per checkpoint) wins, and it then gets 10 training-box evaluations. All of these run at 1024, because the
  evaluator rebuilds sim from the checkpoint's stored config.
- **Identity gate before any official draw:** the chosen checkpoint's stored config may differ from e10v seed 43's chosen
  checkpoint (pulled from the store) only in `output_dir`, `task.parquet`, `reference.parquet` and the four limits
  `sim.njmax`, `sim.nconmax`, `env.sim.njmax`, `env.sim.nconmax`. The limits must read 1024 / 512 against 512 / 256. The
  other conditions are: reset.seed 43 in both, the same total steps, task.parquet resolving to the seed copy (md5 = V),
  and the URDFs present at 0.3 kg. A failure stops the job (INVALID).
- **Official draws:** 10 of the chosen checkpoint at its own config (1024), then 10 of its **512 copy**. Each set runs
  on the kit's `run_policy_evaluation.py` in the pristine evaluator worktree, one call per draw, cut at 1200 s, with up
  to 13 calls per set, stopping after 3 rollout-less calls in a row. A draw is a call that produced a scored rollout
  (e10v's rule).
- **The 512 copy:** a header-only edit of the chosen checkpoint. The stored config gets sim / env.sim njmax 512 and
  nconmax 256, the stock `sim=rl` values. Every other config value, every other header entry and the whole tensor buffer
  stay byte-identical (CPU proof in `BUILD.md` section 3; re-checked on the box, `ck512.json`).
- **Scoring:** `tools/e10v_score.py` (as e10v) scores every rollout against V and P: both official sets, the 10
  training-box draws, and e10v's own 10 official draws re-scored as the control. The verdict tool is `tools/e10nj.py
  verdict`.

## 3. Measured quantities (definitions)
- **O, overflow lines** = the number of lines in the 1024 training's `train.log`
  (`runs/perc2e10njs43_glock/ep10-s43/train.log`, the attempt that produced the checkpoints) containing any of:
  "nefc overflow - please increase njmax to", "broadphase overflow - please increase nconmax" or "narrowphase overflow -
  please increase nconmax". Each kind is reported, with the requested-njmax distribution (median / p95 / p99 / max).
  Also reported, not in O: "njmax_nnz", "CCD" and Newton's "exceeded MJWarp limit" lines; the same counts in any
  out-of-memory retry logs; and the counts in the curve, training-box and official-draw evaluation logs.
- **L, lift** = true when at least one curve checkpoint has a **beige-cup lift ≥ 5.0 cm** in its r1 evaluation. Lift is
  `tools/ckpt_curve_summary.py`'s `lift_cm`: the maximum over frames of the achieved height minus the first-frame height.
  This is the value in `curve.json`, the same repeat the e10v control has. Why the beige cup and 5.0 cm: the beige cup is
  the one the reference lifts (23.5 cm). The blue cup rests, so a blue "lift" would be a knock, not a pick. The e10v
  control's worst knock reached 2.5 cm, so the bar is twice that and about 21 % of the reference lift. Also reported:
  the beige cup's maximum over all 3 repeats, the blue-cup value (the job log label), the within-3-cm share and the
  "lost at" frame, per checkpoint, next to e10v's curves.
- **A, official score** = the mean official sim_vs_ref vs V over the scored 1024 draws (n = 10 needed), compared with
  e10v's **0.4593**. A holds if mean > 0.4593 (tolerance 1e-9 in favour of "not above").

## 4. Labels (applied in this order by `tools/e10nj.py verdict`)
1. **INVALID**: an identity or setup failure. This covers: a STOP (an e10v file missing, the V md5, fingerprint, base
   md5 or URDF inertials differing from e10v's `arms.json`, the clean evaluator worktree failing); no chosen checkpoint
   (the training, curve or evaluations failed); the identity gate above failing (including the overrides not reaching
   the stored config); no training log counted; a scored 1024 draw failing the own-reference check or naming another
   checkpoint's sha256; a non-finite score.
2. **INCONCLUSIVE**: O > 1,000 at 1024. The suspected cause was not removed, so the test says nothing about H.
3. **FALSIFIED**: O ≤ 1,000 and not L (beige-cup lift < 5.0 cm at every checkpoint). The rows are no longer dropped, yet
   the cup is still never lifted, so dropped rows are not the main cause of the floor.
4. **INCOMPLETE**: O ≤ 1,000 and L, but fewer than 10 scored 1024 draws. A cannot be read. A top-up of the official
   draws of the same checkpoint would finish it; that needs a new decision.
5. **SUPPORTED**: O ≤ 1,000 **and** L **and** A (the mean official sim_vs_ref vs V at 1024 > 0.4593).
6. **PARTIAL**: O ≤ 1,000, L, 10 scored draws and mean ≤ 0.4593. The lift returns without an official gain. This is
   not support for H as the fix of eval 10's score; it is reported as is.

The owner's three readings (SUPPORTED, FALSIFIED, INCONCLUSIVE) and INVALID are kept as he stated them. INCOMPLETE and
PARTIAL name two outcomes his wording did not cover. Reported with every label: O by kind, L per checkpoint next to the
control curves, the 1024 set vs V and vs P (n, mean, sd, min, max, median, RPE, fail rate, per-object AUC and travel), the
training-box draws, e10v's re-scored control draws, and the 512 readout (section 5).

## 5. The 512 readout (reported alongside; it never changes the label)
- This is the same checkpoint evaluated at the stock, legal contact limits. It measures how much of any 1024 effect
  survives the setting a pack would be scored under.
- It reports n, the mean vs V and vs P, the difference from the 1024 mean, the fail rate, and the overflow lines in its
  draws' logs.
- Status VALID needs three things: the copy check (`ck512.json`); the evaluator's own config chain on the pristine tree
  reading 512 / 256 for the copy (`solver_check.json`, plus the built solver's njmax when the solver build succeeds); and
  every 512 draw passing the own-reference and checkpoint-sha256 checks. Otherwise the status is INVALID, or MISSING
  when no draw was scored.
- The 512 numbers describe this diagnostic policy under the legal setting. **They do not make it packable** (section 6).

## 6. Never packed
- A checkpoint trained with sim.njmax 1024 takes changed physics into evaluation, because the evaluator rebuilds sim
  from its stored config. The requirements note counts that as manipulating the evaluation unless the organisers agree.
  **Nothing from this run enters any pack:** not the 1024 checkpoint, not its 512 copy, not any rollout of either.
- **Guard:** `tools/no_oracle.py`, which `pack_eval.sh`, `h5_reeval.sh`, `submit_pack.sh` and `pack_swap_rollouts.py`
  run, refuses the following:
  - by name, any word or path containing `e10nj` or `ev10_nj`: the run id `<date>-e10nj-<sha>`, the folders
    `perc2e10njs43_*` and the result folder `results/ev10_nj`;
  - by content, any checkpoint whose stored config names those folders or holds non-stock contact limits (not
    512 / 256), so a renamed copy is caught too.
  `tools/pack_swap_rollouts.py` also passes each swap rollout's stored reference path to the guard. CPU test in
  `BUILD.md` section 4. The box re-runs the refusal on both checkpoints, as is and as neutral-name copies (`guard.json`).
- Any later use of a 1024 policy needs the organisers' written OK, which is not sought here, and the owner's decision.
  A SUPPORTED reading buys only the next pack-legal step, for example collision pieces whose nested rest fits 512 rows
  (falsifier 2, not covered by this go). That needs its own go.

## 7. Expected cost [E]
Basis [M], e10v (`20261031-e10v-caf38fb`, the same box type, its `job.log`):
- seed 43's 70M training took 47.5 min, its curve (7 checkpoints × 3) 5.5 min and its 10 training-box evaluations
  2.5 min, so 0.93 h per seed;
- its 10 official draws took 5.1 min (~30 s per call);
- its whole job took 139 min including setup, for two seeds, billed $3.25 at $1.375/h.

The orchestrator's planning basis is setup ~0.35 h, one training ~1.1–1.2 h and 20 draws ~0.6 h, at $1.27–1.50/h for an
RTX PRO 6000. At 1024 the Newton solver works on more rows in the nested phases, which may slow training. This is not
measured; the high column assumes +35 %.

| stage | low (h) | central (h) | high (h) |
|---|---|---|---|
| setup: boot, snapshot restore, data, make_assets | 0.20 | 0.35 | 0.90 |
| e10v pulls (~45 single files, ~10 MB), seed copy, guard on inputs | 0.03 | 0.08 | 0.25 |
| training 70M at 1024 + curve (7 × 3) + 10 training-box evaluations | 0.95 | 1.20 | 1.60 |
| identity, 512 copy, solver check (3 × 1 world), pack-guard check | 0.03 | 0.08 | 0.25 |
| 20 official draws (10 at 1024, 10 of the 512 copy) | 0.17 | 0.35 | 0.60 |
| scoring (~40 rollouts × 2 references), verdict, push | 0.05 | 0.10 | 0.25 |
| **total wall** | **1.43** | **2.16** | **3.85** |
| **$ at 1.27 / 1.40 / 1.50 per h** | **$1.8** | **$3.0** | **$5.8** |

- Tail risks: a failed final push waits 60 min (+~$1.4). A STOP before training ends after setup (~$0.6–1.3, including
  run_job.sh's 30-min FAIL_HOLD).
- An out-of-memory error at 1024 is unlikely. The estimate is +1–2 GB on a 40.4 GB training (`BUILD.md` section 6).
  glock_public.sh retries twice; a third failure reads INVALID after about the training's cost.
- The ledger line plans $3.50.

## 8. Not covered
- Seed 42 and a second seed. A single seed can show the mechanism but not its spread. e10v's two seeds agreed (both at
  the floor).
- Falsifier 2: pieces without the nested overlap, at 512.
- Any eval episode other than 10.
- A re-run mode. A STOP or INCOMPLETE needs a new decision.
