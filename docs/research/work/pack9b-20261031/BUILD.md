# Pack 9b D arm: build notes (31 Oct 2026, CPU only; nothing launched, downloaded or committed by this build)

**What this prepares.** Pre-registered in `PREREG.md`: the owner-approved targeted D arm, i.e. training-only start-state
randomisation on evals 14, 16 and 33 (grasp lock) and 25 and 30 (standard learner). Each episode keeps its **current
packed configuration** (packed reference, packed assets / pieces, packed recipe), with no masses and no new carves. The
build has three parts:
- seeds 42 and 43 on 5 training boxes;
- one 10-draw official confirmation box;
- a CPU verdict under the agreed swap rule against the packed policy's fresh draws (H5p7).

The job strings in launch order and the costs are in `JOBS.txt`. No ground truth exists for these episodes and none is
read. Markers: [M] measured, [E] estimate, [H] hypothesis.

## Files
- **Ported byte for byte:** `ops/box/patch_flashchord_dr.py`, from determined-wright **4e5c8a0**
  (origin/claude/determined-wright-3joens; md5 570a7f47793d02ba5b0bf3d5e6fd6eac, blob 4f7305391b1d…). It includes the
  opt-in `FC_DR_SKIP_IMMEDIATE`. Their CPU test at the evaluator pin passed 17/17 (`tools/recipe_screen_tests/
  dr_skip_test_log.txt` on their branch).
- **New:**
  - `tools/dr_arm.py`: per-seed byte copies of a packed grasp-lock reference;
  - `tools/dr_eval_verify.py`: training-box verification, the D-line check and the seed choice;
  - `tools/dr_eval_merge.py`: joins the boxes into the confirmation job string;
  - `tools/dr_pack_check.py`: pack-side check;
  - `tools/dr_score.py`: e10v_score.py for any roster episode;
  - `tools/dr_verdict.py`: the swap rule;
  - this folder: PREREG, JOBS, BUILD, `cpu/mock/*`, `cpu/rule_tests/test_verdict.py`, `cpu/out/*`.
- **Changed, opt-in only (unset = old behaviour; proven below):**
  - `ops/jobs/mass_eval.sh`: `ARM=dr`. The same pulls and packed-reference checks, then D instead of masses. It refuses a
    run id without `-dr`, a patch file with any other md5, and an unknown ARM. FC_DR_* / TRAIN_ENV / FC_DR_PATCH coming
    from the environment are logged and unset. The folder is `results/dr_eval`.
  - `ops/jobs/glock_public.sh`: `FC_DR_PATCH=1` applies the DR patch right after `fc_patches`. With it, a PERC prefix
    `drs<seed>` is accepted on SPLIT=eval, but only with RUN local + REQUIRE_REUSE=1 + FC_DR_PATCH=1 (else that pair is
    refused).
  - `ops/jobs/hard_ab.sh`: `FC_DR_PATCH=1` applies the DR patch after its FC_IMMEDIATE_FIRST_FRAME / FDR / VOC patches.
  - `ops/jobs/pack_eval.sh` and `ops/jobs/h5_reeval.sh`: `DR_EPS` runs `tools/dr_pack_check.py` before the kit evaluator
    (draw 1) and before draws 2..N.

## How D is put into the packed recipe
- **Grasp lock (14, 16, 33).**
  - Inputs and copies: pull and check exactly as the masses retrain (the table's pull_files, single-file downloads, md5
    + fingerprint + support stage); `/content/assets` at 0.3 kg. `dr_arm.py` then writes per seed
    `refs/drs<seed>_glockt/ep<N>`, a BYTE copy of the packed `ref_gl_ilc.parquet` (md5 asserted). Its URDF paths are
    unchanged, so the training loads the packed asset copy `refs/sf/ep<N>/assets`. The copy comes with the base link and
    the REUSE_REF result files.
  - Training: per seed, one `glock_public.sh SPLIT=eval REUSE_REF=1 REQUIRE_REUSE=1 NO_PUSH=1 FC_DR_PATCH=1` with
    `TRAIN_ENV="FC_DR_RESET=1.5,0.015,0.01 FC_DR_SEED=<seed>"`. glock_public.sh passes TRAIN_ENV only to the training
    process (`env ${TRAIN_ENV}`), so no curve or NREP evaluation sees FC_DR_* [M, mock T3]. The recipe is the packed
    one, including eval 33's per-episode CURR_SCALE 0.4 (ENV_EP33 from the table).
- **Standard learner (25, 30).**
  - Training: per box, one seed: `hard_ab.sh SPLIT=eval CR=0 SUF=dr FC_DR_PATCH=1 MA_ARGS=` with the packed pieces
    (eval 25: meshes/carve/ev25; eval 30: none) and
    `ENV_EP<N>="FC_DR_RESET=1.5,0.015,0.01 FC_DR_SEED=<seed> FC_DR_SKIP_IMMEDIATE=1"`. The recipe is the carve_rerun /
    std_learner one: FDR + VOC + FC_IMMEDIATE_FIRST_FRAME 0.25, 250,003,456 steps, sweep 0.4 / 0.6 / 0.8.
    `refs/perc2mckdr` is hard_ab.sh's CR=0 byte copy of the pulled base (md5 = the packed perc2mcks file).
  - ENV_EP<N> reaches the episode's whole hard_ab.sh subshell, so the training box's own evaluations also carry FC_DR_*
    [M, mock: 14 evaluation processes per std cell]. They use explicit resets, which the hook never perturbs:
    determined-wright's 17/17 test includes "evaluator's sequence with DR + SKIP in the process: bit-identical to no DR
    code". These draws only choose the seed; the confirmation runs on the pristine, unpatched kit evaluator.
- **Folder names.** Every D folder is new: refs/drs*, runs/drs*_glock, results/drs*_glock_public, refs/perc2mckdr,
  runs/perc2mckdr, results/perc2mckdr, results/hard_ab/ep<N>/mckdr-s<seed>, results/dr_eval. Pack and eval jobs pull
  `runs/<run>/<sub>/*` by run id and sub-folder, so no default pull can reach them. The mock asserts that no default
  folder (refs/mass1*, results/mass_eval, results/glock_public/ep<N>/best, refs/perc2mcks, mcks-s*) was written on a D
  box (T8).

## Verification, merge, confirmation, verdict
- **`dr_eval_verify.py`.** The checks of mass_eval_verify.py with "masses" replaced by "nothing changed": reference md5
  and fingerprint = the packed one; 0.3 kg URDFs, verbatim, under the packed asset copy (unchanged since dr_arm recorded
  it) or under `/content/assets` (= a fresh build with the same make_assets.py command, table pieces); support stage;
  steps; seed; the rollouts' checkpoint; saved config = the packed checkpoint's except paths and seed keys. Added on top:
  - the **D line** in the cell's training log, the exact text of PREREG 1.2: seed, object count, bounds; the skip tail
    present for 25 / 30 and absent for 14 / 16 / 33;
  - **no non-D training** on the box;
  - the **installed hook** = what the repo patch writes (re-run on a scratch tree).

  The seed choice is PREREG 2 = `mass_eval_verify.rule2` (n ≥ 8; higher mean; within 0.005 the lower sd; still tied 42).
- **`dr_eval_merge.py`** joins the boxes (any INVALID box takes the episode out; both seeds required) and prints the
  `h5_reeval.sh` string: N 10, KEEP_RESULTS = pack 7's sources, PICK_EXTRA after `33:rcB`, RUNS_EXTRA = the D reference
  copies, DR_EPS = EVAL_ONLY = EPS_ONLY = the candidates, PACKED_TXT = pack 7's summary. It records each candidate's
  sha256 and the packed sha256 for the verdict.
- **`dr_pack_check.py`** (DR_EPS) runs before the kit evaluator and again before draws 2..N. It requires every
  evaluated episode verbatim at 0.3 kg; for each candidate, the packed reference (md5 + fingerprint) and its table
  pieces; and that the checkpoint is not the packed one.
- **`dr_score.py`.** tools/e10v_score.py unchanged, with its roster set to the episode's kit roster (also in every
  worker). It gives sim_vs_ref = qa.py's metric, and RPE / MPPE / AUC / fail = the score-status session's GT-free audit
  chain. Every rollout is scored against the ONE packed reference P, with the own-reference check.
- **`dr_verdict.py`** applies PREREG 4 and 6 (e10v_verdict.py's logic on one reference):
  - clauses (a) mean, (b) RPE > 5 cm share, (c) median RPE, (s) draw 1 ≥ old − 0.05, with a 1e-9 tolerance;
  - INVALID / INCOMPLETE as pre-registered;
  - draw 1 = the lowest r<i> with a scored rollout;
  - identity of every rollout: conf = the candidate's sha, packed / old = the table's packed sha;
  - P's md5 = the table's;
  - both pack-check files present and passing;
  - `pack9b` = the PASS episodes' draw-1 files.

## CPU evidence (all in `cpu/out/`; mock scores are synthetic, not evidence about D)
1. **The scorer reproduces both reference scorers exactly on the real packed rollouts** [M]
   (`cpu/out/score_real/ep*.json`). This uses dr_score.py on pack 6's (14, 16, 25, 30) and c33B's (33) packed rollouts
   against the pack-6 box copies of the packed references (md5 = the table's).
   - sim_vs_ref 0.9094 / 0.9079 / 0.8937 / 0.9229 / 0.9401 equals pack 7's summary.txt.
   - RPE 3.3857 / 1.5763 / 2.7849 / 2.7902 / 1.9032, MPPE and AUC equal the score-status audit's evalaudit.json to the
     4th decimal (max |Δ| = 0.0). The fail flag is equal too (none fail).
   - Every own-reference check passes, and the checkpoint sha256s are the table's.
2. **Verdict and D-line fixtures:** `cpu/rule_tests/test_verdict.py`, **45 / 45 pass** (`cpu/out/rule_tests.json`).
   - pass; each clause failing (a, a alone, b, c, s); the s bar and an a-tie at the boundary;
   - INCOMPLETE: 9 confirmation draws, 9 packed draws, no old draw, a merge INCOMPLETE, no merge entry;
   - INVALID: training OUT, one pack-check file, a refused check, a check of another sha, an episode not checked as a
     candidate, conf / packed / old sha mismatch, a failed own-reference check, P md5 wrong or mixed;
   - NaN in a draw (with 10 draws → INCOMPLETE, with 11 → decided on 10), inf in the old draw, a NaN clause value →
     INVALID;
   - draw-1 failed call: r1 unscored, so draw 1 = r2; the same with r2 below the bar → NO-SWAP; a missing r1 file → 9 →
     INCOMPLETE;
   - equal floor; and the CLI end to end;
   - the D line: ok glock / std, two builds, missing, wrong seed, std without the tail, glock with the tail, wrong
     bounds, wrong object count, the 609582a format on std, no log;
   - the expected-hook re-run.
3. **End-to-end mock** (`cpu/mock/run_all.sh`; the masses-eval mock pattern). The real job strings run on fresh boxes
   that share one fake store: G, S25a, S25b, S30a, S30b, then the CPU merge, the merge's confirmation string on box C
   (N 10), the CPU scoring and the verdict.
   - The real ported patch runs on a stand-in `lifecycle/reset.py` carrying its anchors.
   - The stub trainer imports the **installed** `v2d_dr.py` and calls its own `install()` and the wrapped `build()`
     (with a stand-in warp module). The D lines in the mock training logs are therefore the hook's own output:
     `cpu/out/mock/mock_dline_{G,S25a}.txt`.
   - Kit evaluations write real-format rollouts (perturbed real packed rollouts), so dr_score.py and dr_verdict.py run
     on the box's actual outputs.
   - `check_train.py` **134 / 134** across 5 boxes, 5 episodes and 10 cells. Each training ran on the byte copy of the
     packed reference with 0.3 kg URDFs from the packed asset copy (unchanged) or from `/content/assets` (= its twin;
     ev25 21 / 11 pieces). The training env was exact (SKIP only for 25 / 30, IMMEDIATE 0.25 only for std), and grasp-lock
     evaluations carried no FC_DR_*. The D line was exact in every training log. The DR patch ran after the other
     patches in every invocation, and the tree is tagged once. Steps and seeds were right, eval 33 used the rcB
     thresholds, and other episodes the defaults. Store traffic: exactly one upload, 0 listings, downloads ⊆ the
     table's (G 93, S25 28, S30 26). No default folder was written. VERIFIED, with config differences only in allowed
     keys. Candidates and strings were produced, and the candidates' checkpoints and reference copies are in the pushed
     run.
   - `check_pack.py` **27 / 27** on box C:
     - the kit evaluator ran exactly the 5 candidates, 10 times each, each with the candidate's sha, its D reference
       copy (packed md5) and 0.3 kg, with no FC_DR_* in the process;
     - dr_pack_check passed before draw 1 and before draws 2..10;
     - the 15 unchanged packed rollouts are byte-identical to pack 6's real files and name pack 7's checkpoints;
     - r1..r10 hold each candidate's rollout, and h5_summary has n 10;
     - the verdict decided all 5 on 10 vs 10, and the old draw re-scored to pack 7's values;
     - pack9b = the PASS set; the job string is as pre-registered.
   - In the mock merge, eval 30 chose seed 43 by the lower-sd tie-break (means within 0.005). The synthetic verdict reads
     14 NO-SWAP, 16 PASS, 25 PASS, 30 NO-SWAP, 33 PASS (`cpu/out/mock/mock_verdict.txt`); this says nothing about D.
4. **Negative tests** `cpu/mock/neg.sh`: **12 / 12 as expected** (`cpu/out/neg/neg.txt`, `neg.json`).
   - Training side:
     - N1 a run id without `-dr`, N2 a patch file that is not the 4e5c8a0 port, N3 an unknown ARM: each refused before
       any pull, with no training;
     - N4 a hook that prints nothing, N5 a hook that reads seed + 1, N6 std without the skip flag reaching the hook,
       N7 a non-D training log on the D box: each trains, and dr_eval_verify then reads INVALID with the right reason;
     - N8 `glock_public.sh` PERC drs42 on SPLIT=eval without FC_DR_PATCH: that pair is refused, with no training and no
       DR patch.
   - Confirmation side:
     - C1 a D reference copy not pulled, and C2 the packed eval-14 checkpoint left in place of the D pick: dr_pack_check
       refuses before the kit evaluator (0 kit evaluations). In C2 the packed rollout is kept by KEEP_RESULTS, so the
       check reads "in DR_EPS but not evaluated here";
     - C3 the verdict without the pack-check files: 5 / 5 INVALID;
     - C4 one H5p7 draw naming another checkpoint: that episode INVALID, and only that one.
5. **Default paths unchanged** `cpu/mock/equiv.sh`. Old = 880db25 (before any D change to these files), new = the working
   tree, on existing-caller job strings with every hook unset (`cpu/out/equiv/equiv.txt`). The cases:
   - EG: the masses G2 box (mass_eval.sh + glock_public.sh), 4 trainings, 124 evaluations;
   - ES: the masses S1a box (mass_eval.sh + hard_ab.sh), 1 training, 14 evaluations;
   - E2: the hard_ab.sh + pipeline_ep.sh carve path;
   - E3: pack_eval.sh + h5_reeval.sh rebuilding pack 7.

   Results:
   - exit code, job log, audits (what each trainer / evaluator loaded and which patches ran) and store traffic are
     **IDENTICAL** in all four;
   - files: the first run (`cpu/out/equiv_run1/equiv.txt`) differed only in EG's `results/mass_eval/arms_ep{15,33}.json`,
     and only in their `"created"` timestamp (tools/mass_arm.py, unchanged; checked by diff). The re-run normalises
     that line and reads IDENTICAL in every respect;
   - no training log of these default boxes holds a "v2d FC_DR_RESET" line (EG 4 / 4, ES 1 / 1, E2 1 / 1).

   glock_public.sh's public path (SPLIT=public) is not re-run here. Its diff is the FC_DR_PATCH block, run only when
   FC_DR_PATCH=1, and the drs-prefix branch, reached only by a `drs<seed>` PERC (which no existing caller passes), plus
   comments.
6. `bash -n` passes on the 10 changed or new shell scripts, and py_compile on 12 Python files (the 6 new tools, the
   ported patch, the 4 mock scripts and the fixture test)
   (`cpu/out/syntax.txt`).

## Findings, deviations and risks (for the orchestrator)
1. **FC_DR_SKIP_IMMEDIATE is ported (4e5c8a0).** The standard-learner boxes can launch with the grasp-lock box. The
   md5 pin in mass_eval.sh makes any other patch version refuse before the first pull.
2. **Standard-learner D env reaches that box's own evaluations.** This is through ENV_EP<N>, as specified, and is
   harmless by determined-wright's evaluator-sequence test. Those draws only choose the seed. The confirmation (the
   rule's evidence) runs on the pristine evaluator, and the mock shows no FC_DR_* there.
3. **D on the standard learner is untested** (250M steps, FC_IMMEDIATE_FIRST_FRAME); this is stated in PREREG 5. The
   public screen showed no steadying (ep2 sd 0.10 → 0.25, ep18 0.008 → 0.056) [M, determined-wright].
   - Expected effect: small, sign unknown [E].
   - The rule keeps the packed policy unless every clause holds.
   - With 10 vs 10 draws, a PASS on (a) can be noise: a 0.002 margin read PASS in the mock. The rule has no margin
     because none was agreed. Read the sd and the per-draw table next to the label.
4. **The confirmation waits for all five training boxes.** The grasp-lock box is the long one (~3.5–5.5 h [E]); the
   standard boxes take ~2.0–2.3 h. A dead or INCOMPLETE box delays C, or C can be built without that episode: the
   merge drops it, and the remaining candidates can be confirmed first.
5. **H5p7, the packed side, is complete for these episodes** [M, 22:38 UTC, two single-file downloads]. Its
   `results/h5/h5_summary.json` has n = 10 for each of 14, 16, 25, 30 and 33. `r10/ep33/episode_000033.json` names
   rcB's sha256 df90b216…, the table's packed checkpoint. Only the n values and that sha were read, not the means. The
   rollout parquets are fetched at verdict time; the verdict reads INCOMPLETE if fewer than 10 score.
6. **Store listings remain only on C:** 47 = pack 6's base 36 + RUNS_EXTRA 5 + PICK_EXTRA 6 [M, mock hf log], as the
   masses C1 / H5p7 boxes ran them. The training boxes list nothing.
7. **Mock limits.** Physics and scores are stubbed. The stand-in reset.py carries only the patch's anchors, so the
   hook's effect on real resets is covered by determined-wright's tests at the evaluator pin, not here. The trainer
   template config is a real packed one. The hf stub has no 429.
8. **Draw 1 of C is not pack 9b.** C's `results/submission` is "pack 7 + candidates" (eval 1 = pack 6's std0116
   rollout kept, the pack-6 meshes). Pack 9b is assembled on CPU from pack 9a+ plus the PASS episodes' draw-1 rollout
   files (`verdict.json` pack9b[N].path), with every other episode byte-identical. That CPU repack (pack 9a's B7 method)
   is not built here.

## Pack 9b CPU repack (added 1 Nov 2026 ~01:20 UTC, orchestrator; closes item 8)
- Tool: `tools/pack_swap_rollouts.py` (sibling of pack_swap_meshes.py: swaps rollouts, refuses any mesh change).
  Inputs = pack 9a+'s own packer inputs (scratchpad `pack9ap/pack9ap2/results` + `meshes`), base = build_9aplus parquet.
- Per PASS episode N: `--swap N=<verdict.json pack9b[N].path>` (the .json beside it) and `--expect-checkpoint N=<the
  candidate's sha256 from verdict.json / c_merge.json>`. Every other episode's rollout stays byte-identical.
- Checks: rows / row_id / schema as base; only pose columns + checkpoint_sha256 on swapped episodes and code_commit_url
  may differ; object_mesh_b64 identical; swap metadata (flash_chord.*) carries the .json's checkpoint and the base
  rollout's evaluator hashes; uploader offline validation; CD-O file equal to the base-derived one row for row.
- CPU tests (`cpu/rollout_swap_tests.txt`): a pure repack with 9a+'s commit URL rebuilds 9a+ byte for byte (e02736ea…);
  a synthetic ep14 swap passes with exactly 316 pose rows + 316 checkpoint rows changed; 7 refusal cases behave.
- Command (after the verdict; packing venv; code commit = the pushed commit holding this tool):
  PY -I tools/pack_swap_rollouts.py --kit KIT --results $S/pack9ap/pack9ap2/results --meshes $S/pack9ap/pack9ap2/meshes \
    --base results/submissions/20261031-track3i-candidate/build_9aplus/track3_submission.parquet \
    --code-commit https://github.com/aebatirel/v2d-track3/commit/<sha> --python PY \
    --swap N=<path> --expect-checkpoint N=<sha256> [...] -o $S/pack9b/build_9b
  then copy track3_submission.parquet, .cd-o.parquet, swap_manifest.json, summary.txt, pack.log into
  results/submissions/<date>-track3j-candidate/build_9b/ with a README (NOT UPLOADED; the owner's word decides).
