# Masses eval retrain: build notes (31 Oct 2026, CPU only; nothing launched, downloaded or committed here)

**What this prepares.** The eval retrain of `PLAN.md`, ready to launch the moment the transfer check
(`20261031-mass-2ed46ea`) ADOPTs and the owner says go: one job per training box, the confirmation box, and the pack side,
so that a later pack evaluates each retrained episode with the masses it trained with and leaves every other episode as
packed. No ground truth exists for eval episodes and none is read: every score is sim_vs_ref against our own stored
reference. Markers: [M] measured, [E] estimate, [H] hypothesis.

## Files
- **New:** `ops/jobs/mass_eval.sh` (one box: `MODE=glock|std EPS=... SEEDS=...`), `tools/mass_eval_verify.py` (B3: verification,
  training-box summary, rule-2 candidate, confirmation strings), `tools/mass_pack_check.py` (pack-side mass check),
  `tools/mass_eval_merge.py` (CPU: the boxes' summaries -> one confirmation job, rule 2 across boxes),
  this folder's `packed_refs.json` + `packed_refs_make.py` (per-episode facts the box reads), `JOBS.txt` (job strings per
  box, gates, costs), `cpu/mock/*`, `cpu/out/*`.
- **Changed, opt-in only (off by default, old = new when unset: `cpu/out/equiv*.txt`):**
  - `ops/jobs/glock_public.sh`: a PERC prefix `mass<A>s<seed>` is allowed with SPLIT=eval only with RUN local and
    REQUIRE_REUSE=1 (B2); CURR_SCALE in ENV_EP<N> now scales that episode's curriculum (finding 1).
  - `ops/jobs/hard_ab.sh` + `pipeline/pipeline_ep.sh`: EVAL_TIMEOUT (timeout -k 60, eval_rc.txt; B4) on the NREP rollouts,
    the main evaluation and the sweep; `NO_PUSH=1` in hard_ab.sh.
  - `ops/jobs/pack_eval.sh`: `MASS_EPS` runs `tools/mass_pack_check.py` before the kit evaluator; without MASS_EPS a PICK
    of a `-mev` run or `--physics` in MA_ARGS is refused.
  - `ops/jobs/h5_reeval.sh` (B5): `RUNS_EXTRA` (appended to pack 6's RUNS, so pack 6's files win every path),
    `PACKED_TXT` (default pack 6's summary, as before), the mass check again before draws 2..N, and MA_ARGS `--physics`
    refused without KEEP_RESULTS, EVAL_ONLY and MASS_EPS.

## How each episode trains on the packed reference with the realistic masses
- **The table** (`packed_refs.json`, generated from `rank/motion.json` and pack 7's `checkpoints.json`): per episode the
  mode, the source run of its stored reference, the sub-folders and single files to pull, the reference md5 and
  `mass_arm.traj_fingerprint`, its asset root, pieces, library, per-episode env (eval 33: `CURR_SCALE=0.4`), steps and the
  packed checkpoint whose saved config the retrain must reproduce (eval 1: the c01s43 carve recipe).
  - [M] Every rewritten local copy of the 16 references the mock uses has the table's real fingerprint (setup asserts it).
    Eval 1's base `refs/perc2mck/ep1` (c01s43's pull of pack-31ef267) has md5 7f230466, the packed `refs/perc2mcks` file's.
  - [M] The 29 Oct store listing has every pulled sub-folder and result file (gl10A2 ep10 has no support_fill.json; eval 30's
    packed reference is std30's / ev30rp's, not pack-31ef267's older one).
- **Grasp lock (15 evals).** Pull → md5 + fingerprint must be the packed ones (else the episode is dropped, nothing
  trains) → `/content/assets` at 0.3 kg → `tools/mass_arm.py --arms "mass1:<props>"` → per seed one
  `glock_public.sh SPLIT=eval REUSE_REF=1 REQUIRE_REUSE=1 NO_PUSH=1` over the box's episodes (waves of TRAIN_SLOTS 2),
  70,004,736 steps, CURVE_REP 3, NREP 10, EVAL_TIMEOUT 1200. Nothing of the reference stages can run.
  - Eval 10's reference names `/content/assets` (library_v3 + ev10, SF 0): the box builds it at 0.3 kg, mass_arm copies
    it to `refs/mass1_sf/ep10/assets`, so eval 10's copy is independent of any shared folder (mock box G4).
- **Standard learner (5 evals).** Pull `refs/perc2mck/ep<N>` + `perc2/ep<N>` (md5 = the packed perc2mcks file), then
  per seed `hard_ab.sh SPLIT=eval CR=0 SUF=s` with the std_learner / carve_rerun environment, `MA_ARGS="--physics <props>"`,
  the packed PIECES, NREP 10, EVAL_TIMEOUT 1200, NO_PUSH. A 0.3 kg twin of `/content/assets` is built for verification.
  The episodes of one std box must share library and pieces (eval 1's ev01 pot vs eval 28's default pot is refused).
- **B3 (`mass_eval_verify.py`).** For each chosen checkpoint: saved config → task.parquet → reference → URDFs, as the
  official evaluator loads them. Failures (episode INVALID, packed policy stays): not the packed reference (fingerprint;
  std also md5; glock also mass_arm's seed copy), a URDF not verbatim or not in the arm folder / `/content/assets`, a
  mass ≠ props, a COM change, inertia ≠ source × m / 0.3, mesh files or collision-piece counts ≠ the 0.3 kg source (ev01:
  53 / 107), steps or seed wrong, rollouts naming another checkpoint, a std checkpoint that is not the sweep's choice, and
  any saved-config key that differs from the packed checkpoint's except `output_dir`, `task.parquet`,
  `reference.parquet` and the seed keys. Missing cells or an unread packed header → INCOMPLETE.
  - [M] The 22 packed and recipe checkpoint headers on this machine (16 grasp lock, 6 standard learner; 24-30 Oct
    commits) differ within each learner only in paths, seed keys, `reference.num_frames` and, for rcB, the curriculum:
    the strict recipe check is feasible.

## How a later pack evaluates them with the same masses (verified in the source)
- [M] Kit `examples/run_policy_evaluation.py` → `evaluate_policy.py` → `evaluation/harness.py` `evaluate_checkpoint`:
  the scene is rebuilt from the checkpoint's saved `task.parquet` (`Path(...).resolve()`; the packed configs store
  `/workspace/refs/...`, and the boxes link `/content` → `/workspace`, `ops/box/onstart.sh`) → `data/parquet.py`
  `resolve_parquet` → `object_urdf_paths` → `assets/registry.py` `resolve_asset_path`: **the stored path verbatim when it
  is a file, otherwise silently re-rooted onto FlashCHORD's own assets**. With per-body URDFs, `object_mesh_paths` is not
  used for the simulation (`resolve_object_asset_specs`).
- So a pack must (a) pull a grasp-lock retrain's `refs/mass1_sf/ep<N>` and `refs/mass1s<seed>_glockt/ep<N>`
  (`RUNS_EXTRA RUN@...`, printed by B3), and (b) build the shared `/content/assets` with MA_ARGS and the pieces for a
  std retrain, with no unchanged std episode evaluated beside it (KEEP_RESULTS + EVAL_ONLY).
- `tools/mass_pack_check.py` enforces both right before the kit evaluator: every evaluated episode's URDFs resolve
  verbatim; MASS_EPS episodes load the props masses, the packed reference (fingerprint) and, where the table names
  pieces, one `<collision>` per piece (a pack without ASSET_PIECES_EXTRA ev01 would evaluate eval 1 on the plain pot);
  every other evaluated episode loads 0.3 kg. Kept episodes are not evaluated, so their submitted rollouts are reused
  byte for byte.

## Findings and deviations from the plan (for the orchestrator)
1. **The plan's `ENV_EP33="CURR_SCALE=0.4"` would have trained eval 33 with the default curriculum.** glock_public.sh read
   CURR_SCALE once, job-wide, before ENV_EP<N> is applied (arm B had it job-wide). Fixed by the opt-in per-episode hook;
   the table supplies it. The mock shows both sides: G2's eval 33 saves rcB's scaled thresholds, and negative test N12
   (ENV cleared) gives `ep33 INVALID ... recipe differs ... curriculum.thresholds` [M, mock].
2. **Cost: eval 8 trains about 1.8× slower** [M basis: evb0810 ep8 70M at 6.5k steps/s with two trainings on the GPU,
   the v5 beige cup's 32 pieces; ep11 v3x twin 1.6 h vs 0.9 h]. G1 is re-estimated at 4.5-6.5 h, $6.3-9.6 (central
   ~$7.5, plan $4.7) [E]; O2 ≈ $20 ($15.5-24.8) instead of $17.2. Eval 10's 24-26 Oct trainings ran at 2.4-8.9k steps/s
   (nefc overflow): G4's cost is unknown.
3. **New gate before any launch** (JOBS.txt gate 1, one targeted download): diff the saved config of one checkpoint the
   transfer box trained today against a packed one. If the box's FlashCHORD resolves any extra key, B3 would make every
   retrained episode INVALID after the spend [H: unlikely, same snapshot as rcB (29 Oct) and c01s43 (30 Oct)].
4. **The mock caught a brittle box-settings test** (`cpu/out/finding_s1_without_pieces_verify.txt`): the first S1 run
   built `/content/assets` without ev01 because a literal-path comparison was rewritten by the mock. On a real box it
   would have matched, but the table now has an explicit `shared_assets` field. B3's piece count made that run INVALID
   (white_pot 1 collision vs 53 pieces), not silently wrong.
5. **Pack-side defaults kept**: `pack_eval.sh`'s `PICK ck=` and `KEEP_RESULTS` downloads still use `--include` (a store
   listing each), as before; the confirmation of 6 candidates adds about 12 listings for RUNS_EXTRA + 6 for PICK.
6. **LIB is cosmetic for grasp-lock episodes** (their URDFs are their own copies; mesh paths are unused, pack section), so
   G1's library_v3x changes nothing for eval 20; it matters only for `/content/assets` (std, eval 10).
7. **Rule 2 across boxes.** The plan runs eval 1's two seeds on two boxes (S1a, S1b), so neither box can apply rule 2;
   `tools/mass_eval_merge.py` does it when C1 is built (and drops any episode with an INVALID box). Mock: P7.
8. **The confirmation's rule application (rules 4-9) and the pack-9 CPU repack (B7) are not built.** h5_summary.json
   carries n, mean, sd (ddof 1), min and the packed draw (PACKED_TXT) per candidate; the rule is a few lines on CPU.

## CPU evidence (`cpu/`; mock scores are synthetic, not evidence about masses)
- **Mock** (`cpu/mock`): one fake store shared by fresh boxes at the same `/content` path (`setup.sh`, `run_box.sh`).
  Real: every ops/tools script, make_assets, mass_arm, the new tools, store.sh, no_oracle. Stubbed: the FlashCHORD
  trainer (it starts from a real packed resolved config and applies the command-line overrides, so the recipe check is
  meaningful), the evaluators (scene rebuilt from the checkpoint's saved config, `/workspace` read as `/content`), the kit
  evaluator and packer, qa. Store: the 20 real packed reference parquets and 20 real packed checkpoints, pack 6's and
  c33B's real submitted rollouts; synthetic sf asset folders (make_assets, 0.3 kg), base folders and result files.
- **`run_all.sh`**: G1 (20 + 8), G2 (33 + 15), G4 (10), S1a (1, s42), S1b (1, s43), then `tools/mass_eval_merge.py` over
  the five pushed `summary.json` files and the confirmation box C1 it specifies (h5_reeval.sh, N 3, KEEP_RESULTS = pack
  7's sources, all six candidates).
  - `check_train.py`: **112 / 112 checks pass** (`cpu/out/mock_check_train.json`), 6 episodes, 11 trainings, 5 boxes:
    per episode and seed one training on the packed reference (real fingerprint; glock only `object_urdf_paths`
    differs, std byte-identical), props masses loaded at training and in
    every one of the box's evaluations, from `refs/mass1_sf/ep<N>/` or `/content/assets`; steps and seeds; eval 33 on
    rcB's thresholds; references and asset folders unchanged; `/content/assets` 0.3 kg on glock boxes, props + 53 / 107
    ev01 pieces on S1a / S1b; one push per box; downloads exactly the table's; no reference stage; VERIFIED with only allowed
    config differences against the real packed configs; candidates and strings.
  - `check_pack.py`: **26 / 26 checks pass** (`cpu/out/mock_check_pack.json`): the 14 unchanged episodes' packed
    rollouts byte-identical to pack 6's real files and naming pack 7's checkpoint sha256; the kit evaluator ran
    exactly the 6 candidates in each of
    the 3 draws; each loaded its training box's checkpoint, the real fingerprint and the props masses from its own folder
    (eval 1 from `/content/assets` with ev01); mass_pack_check passed before draw 1 and before draws 2..3; h5_summary's
    packed column = pack 7's summary; the merge chose eval 1's seed by rule 2 over S1a / S1b (P7; mock: s42 0.902 ± 0.011
    vs s43 0.893 ± 0.012, synthetic).
- **`neg.sh`**: **14 / 14 refused as expected** (`cpu/out/neg.txt`, `neg.json`). Pack side, each refused before the kit
  evaluator ran: N1 MA_ARGS left out (eval 1 would load 0.3 kg), N2 a `refs/mass1_sf` folder not pulled (URDF not a file),
  N3 MASS_EPS left out (h5's `--physics` guard), N3b MASS_EPS and MA_ARGS left out (pack_eval's `-mev` guard), N4 eval 1
  missing from MASS_EPS (would load props), N5 KEEP_RESULTS left out, N6 an unchanged std episode (19) in the masses
  `/content/assets`, N13 ASSET_PIECES_EXTRA ev01 left out (eval 1 on the plain pot). Training side: N7 eval 8 with 10,
  N8 eval 1 with 28, N9 wrong mode, N10 run id without `-mev`, N11 a stored reference that is not the packed one
  (dropped, nothing trained), N12 eval 33 without its curriculum
  (INVALID).
- **Equivalence, hooks off** (old = 14ae515, the last commit before this build; `cpu/out/equiv*.txt`): **identical** job
  logs, loads (audits), written files (names + md5), exit codes and store traffic for
  - E2 `hard_ab.sh` + `pipeline_ep.sh` on the eval-1 carve path (1 training, 7 evaluations, 1 upload);
  - E3 `pack_eval.sh` + `h5_reeval.sh` rebuilding pack 7 (all 20 rollouts kept, draws 2..3 for evals 3 and 19, 4 uploads);
  - `glock_public.sh` + `ckpt_curve.sh` with the transfer check's own equivalence job strings
    (`masses-transfer-20261031/cpu/mock/equiv.sh BASE=14ae515`: 2 trainings, 52 evaluations, 2 uploads).
- `bash -n` passes on every script; the new Python compiles.
- **Mock limits.** Stub physics and scores; synthetic sf assets, so the 0.3 kg-source check of real support-filled URDFs
  is exercised only on the box (mass_arm refuses a non-placeholder source); the real resolved config may hold keys the
  template does not (finding 3, JOBS.txt gate 1); the hf stub copies files but has no HF 429.

## Not done here
No commit, launch, download or Kaggle action; no STATUS / work-log entry (the orchestrator's). Reviews pending.
