# Eval-20 b1 retrain: build notes (1 Nov 2026, CPU only, nothing launched)

**Question.** Does the packed eval-20 learner and recipe (grasp lock), retrained at the stock contact limits on the packed
reference with the b1 water-pitcher collision pieces, beat the packed policy under the agreed swap rule and the pack-10
inclusion bar?
- Rule and labels: `PREREG.md` (written before any result).
- Launch string, ledger line and after-box steps: `JOBS.txt`.
- Labels: [M] measured here, [R] read from another lane's commit, [E] estimate, [H] hypothesis.
- Machine: this Claude cloud VM (4 CPU), 1 Nov ~06:45-08:00 UTC, $0. No GPU, Vast or Kaggle. Nothing pushed.
- Eval 20 has no ground truth; nothing here reads mocap, scans or `observation.objects` poses.
- **PACKABLE if it passes** (stock limits; `tools/no_oracle.py` accepts it, section 5).

## 1. What is built
| file | what |
|---|---|
| `meshes/carve/ev20b1/` | Byte copy of bold-albattani's frozen `rebase/sets/ev20/` (83d18d0; pieces = 9c0bc0c), with `MD5SUMS` (md5 fe9aeca0..., = the lane's folder hash), the lane's `FROZEN.md` (byte copy) and `PROVENANCE.md` (source commits, GT-freedom, gates, trades, how it is applied). |
| `tools/e20b1.py` | `import`, `pieces`, `inputs`, `assets`, `arms`, `cells`, `choose`, `gate`, `verify`, `verdict` (PREREG sections 2-6). Pins the set's md5s, P's md5 / fingerprint / stage, the packed and b1 URDF / glb md5s, the packed sha256, the gate 0.8933. Reuses `e10cs.config_diff / choose / stats / training_overflow`, `dr_verdict.scored / side / clauses_of`, `mass_verify`, `e11g_verify.urdfs_of`, `e10cs_pieces` helpers, unchanged. |
| `ops/jobs/ev20_b1.sh` | The job. Run id `<date>-e20b1-<sha7>`; nothing overridable. |
| `ops/jobs/glock_public.sh` | Opt-in `EVAL_E20B1=1`: allows the PERC prefix `e20b1s<seed>` with SPLIT=eval, episode 20, RUN local and REQUIRE_REUSE=1. 1 code line plus 4 comment lines; the default path is unchanged (section 6). |
| `docs/research/work/eval20-b1-20261101/` | PREREG.md, BUILD.md, JOBS.txt, `cpu/scripts/` (tests), `cpu/mock/` (end-to-end mock), `cpu/out/` (outputs). |

- **Reused unchanged:** `pipeline/placement_carve.py` (the carve), `tools/dr_score.py` (scoring), `tools/dr_verdict.py` (clause
  code), `tools/e10nj.py` (overflow), `tools/no_oracle.py`, `tools/trace_rollout.py` / `trace_score.py` / `rest_check.py`, the
  ev10_cs.sh `confirm()` draw loop (verbatim but for names, static check), mass_eval.sh's pull-files pattern (packed_refs.json).
- **A wrapper job, not a knob in mass_eval.sh.** mass_eval.sh's glock path always applies masses (or, with ARM=dr, the DR patch),
  scores and verifies per its own tables, and has no gate, confirmation or verdict. ev10_cs.sh is eval-10 specific (V, make_assets
  --pieces). A thin new job keeps both byte-identical.

## 2. Which learner the packed eval-20 policy is [M]
- `runs/20261025-evb1420-ee7ba8e/results/final_eval/ep20/policy.safetensors`, sha256 61dcd7a6 (pack 7 checkpoints.json; the
  local copy is a single-file store download, `.cache/huggingface/download/...metadata` names that sha256).
- Stored resolved config (`cpu/out/packed_ep20_cfg.json`, `cpu/scripts/ckcfg.py`): `output_dir /content/runs/glock/ep20-s42`,
  task / reference `refs/glockt/ep20/.../ref_gl_ilc.parquet`, 70,004,736 steps, reset / training seed 42, `user.algorithm
  flash_sac`, sim 512 / 256, 480 keys. That is the grasp-lock learner's output dir, reference and step count. The standard
  learner writes `runs/perc2mcks/...` and trains 250M steps.
- evb1420's job.log (store, md5 2f3b169d; the lines in `cpu/out/evb1420_job_log_lines.txt`):
  - `glock_public code ee7ba8e, pairs [14:new:mck 20:new:mck ], seed 42, steps 70004736, NREP 5, SPLIT eval, SETTLE 0, SF 1,
    REPLAN 1, EVOLVE 0 ... GL_ARGS [... --approach_cm 15]`;
  - TRAIN_ARGS `curriculum=tracking_250m_mixed_reset_v2d objective.force_closure.enabled=true ...weight=6 ...contact_wrench_support.weight=3 ...unintended_contact.weight=-2`;
  - `glock ep20 RESULT (policy_70004736.safetensors): n 5 sim_vs_ref mean 0.8923`;
  - `ab ep20 mcks-s42 (policy_170008576.safetensors): n 5 sim_vs_ref mean 0.1461`;
  - `eval_both ep20: {"ep": 20, "chosen": "glock", "means": {"std": 0.1461, "glock": 0.8923}}`.
- `results/final_eval/ep20/choice.json` (store; `cpu/out/evb1420_ep20_choice.json`): chosen glock,
  `/content/runs/glock/ep20-s42/policy_70004736.safetensors`, rule "max mean sim_vs_ref".
- The code at ee7ba8e: `ops/jobs/eval_both.sh` runs glock_public.sh (learner A) for every episode, then hard_ab.sh (learner B)
  where A's mean is below GATE 0.9 (0.8923 < 0.9, so both trained), then `tools/choose_learner.py` (max mean sim_vs_ref).

## 3. The pieces and how they are applied
- **Import [M].** `tools/e20b1.py import --rev 83d18d09 --also 9c0bc0c9 --src docs/research/mesh-2026-10-26/rebase/sets/ev20
  --dst meshes/carve/ev20b1`: 41 input files, md5 list = FROZEN.md; byte-identical at 9c0bc0c; MD5SUMS md5 fe9aeca0...
- **GT-freedom.** What the mesh lane says [R], quoted in PROVENANCE.md: no scan, mocap, dataset pose field or `*_align` read;
  inputs are our references, support usda, meshes and the packed pieces; nothing tuned on eval scores. The b1 rule's parameters
  (u, m_foot) come from P and the packed foot pieces. The lane's posefix motivation (public mocap) gave d = +0.01 mm on eval 20
  ("not needed"), so nothing from it enters b1. `tools/no_oracle.py` accepts the folder [M].
- **The carve on CPU, on the real packed files [M]** (`cpu/out/carve_cpu/`; the 38 eval-20 pull_files of packed_refs.json and
  the packed checkpoint downloaded single-file): `placement_carve.py assets` -> `{"carved": [["water_pitcher", 41]]}`;
  `tools/e20b1.py inputs` OK; `assets` OK: changed only `urdf/water_pitcher_rigid.urdf` (6772f954, 9 collisions -> 77b395a5,
  41), 41 col_NN.obj added, 0 removed, inertial and visual equal, blue cup URDF 31cd001d unchanged; `arms` OK.
  77b395a5 is the lane's own route-A URDF (`results/ev20_a1/water_pitcher_rigid.route_A.urdf`).
- **Why not make_assets --pieces.** It would rebuild the blue cup from the library and drop its 0.5 cm fill (the lane, the
  orchestrator). The job unsets PIECES, so `/content/assets` is the plain library build and nothing names it.
- **Same method as determined-wright's checks [R]:** budget f59c897 and settle 85e8ef8 both used `placement_carve.py assets` on
  the packed refs/sf/ep20/assets with the 9c0bc0c set.

## 4. Pack eligibility (`cpu/out/config_guard_test.json`, 25 / 25) [M]
- The packed checkpoint is the grasp-lock seed-42 one (section 2).
- REAL packed eval-14 vs REAL packed eval-20 checkpoint (same run, same call): diff `output_dir, reference.num_frames,
  reference.parquet, task.parquet`. The recipe is per run; eval 20's `reference.num_frames` (202) is P's and does not change here.
- [R] The D arm's eval-14 cells (code a1a7e25, the same glock_public.sh training path on evb1420's reference) differ from the
  packed eval-14 config only in the allowed keys (`pack9b-20261031/results/drG/verify.json`). Since a1a7e25 the only code changes
  to glock_public.sh are PERC-guard lines; ops/box, flashchord_conf, ckpt_curve.sh and qa.py are unchanged.
- A stand-in of this job's seed-43 checkpoint (the packed one with this job's paths and seed): diff = the six allowed keys,
  stock limits; no_oracle accepts it. Negative controls (njmax 1024, an extra key) are caught; no_oracle refuses the 1024 one.
- The mock (section 8) checks the training command key by key against the REAL packed eval-20 config, and TRAIN_ARGS against
  evb1420's REAL job-log line.

## 5. The pack guard accepts this run [M]
- Accepted: the run id `20261101-e20b1-abc1234` and its store paths; `refs/e20b1s42_glockt/ep20`, `runs/e20b1s43_glock/ep20-s43`,
  `results/e20b1s42_glock_public/ep20`, `results/ev20_b1`; `ev20_b1.sh`, `e20b1.py`, this folder; the piece folder (name and
  content, also as an `EP:DIR` word); the stock stand-in checkpoint and a kit checkpoints JSON naming it.
- Still refused: the njmax diagnostic's run id, `results/ev10_nj`, `perc2e10njs43`, an oracle run id, the 1024 stand-in.
- On the box no_oracle runs on the piece folder, every input and, before any official draw, the chosen checkpoint.

## 6. Default paths unchanged [M]
- **glock_public.sh** (`cpu/scripts/guard_equiv.sh` -> `cpu/out/guard_equiv/summary.txt`): the PERC guard block of one() cut
  from the base 7bac1b5 and from the working tree, run over **15,552 cases** (SPLIT x 12 prefixes x RUN x REQUIRE_REUSE x episode
  x EVAL_LOCAL_REF x FC_DR_PATCH x EVAL_CS_REF x EVAL_E20B1).
  - With EVAL_E20B1 unset or 0: **0 differences**.
  - With EVAL_E20B1 = 1: exactly 16 cases change, all newly ALLOWED, all `e20b1s42|43` / eval / episode 20 / local /
    REQUIRE_REUSE=1.
- `cpu/out/static_checks.txt`: ALL PASS (33). It covers:
  - only glock_public.sh, the new job, the new tool, the piece folder and this folder differ from 7bac1b5;
  - 20 files / folders unchanged, among them placement_carve.py, make_assets.py, no_oracle.py, dr_score.py, dr_verdict.py,
    e10cs.py, ev10_cs.sh, mass_eval.sh, lib.sh, store.sh, run_job.sh, library_v3 and packed_refs.json;
  - glock_public.sh: 1 code line added, 0 removed, and it is the EVAL_E20B1 guard;
  - bash -n / py_compile; no sim limit or TRAIN_ARGS in the job; no make_assets call, PIECES unset;
  - the carve command and its target; SF 0 and the packed recipe values;
  - confirm() = ev10_cs.sh's verbatim but for names;
  - the piece set passes `pieces` and no_oracle, and is byte-identical at 9c0bc0c and 83d18d0.

## 7. Verdict fixtures (`cpu/out/verdict_tests.json`, 23 / 23) [M]
Synthetic result folders, the packed side shaped like the real H5p7 draws:
- **Gate:** packed-like seeds -> NO-SWAP "training-box gate not met"; a mean exactly 0.8933 does not meet the strict gate; a thin
  (n 7) or INVALID seed does not count.
- **Labels:** missing seed -> INCOMPLETE; INVALID cell -> INVALID; verify failure and STOPPED -> INVALID; 9 confirmation draws ->
  INCOMPLETE; a P of another md5 or a packed rollout naming another checkpoint -> INVALID.
- **Swap rule on P:** mean below 0.8933 -> NO-SWAP (a); one draw with RPE > 5 cm against K's 0 / 10 -> NO-SWAP (b) even with a
  higher mean; median RPE 1.8 > 1.67 cm -> NO-SWAP (c); draw 1 at 0.84 < 0.8448 -> NO-SWAP (s).
- **Inclusion bar:** gain +0.0267 -> INCLUDE; +0.0116 -> SWAP-ELIGIBLE, NOT included; exactly +0.02 over the raw packed mean
  0.89335 -> included; +0.0199 -> not.
- **Overflow:** 1,001 lines -> "pieces not clean in training" attached, rule still applied; 1,000 -> no label.
- **Seed choice:** within 0.005 -> lower sd; 0.006 apart -> higher mean; full tie -> 42.

## 8. CPU mock of the whole job (`cpu/mock/`, outputs `cpu/out/`)
- **Harness:** the eval-10 mocks' pattern (repo copy with /content -> MR/content, stub `hf` serving single files and refusing
  listings, stub git / curl / pip), this folder's `stub.py` (eval10-cs4's stub; e20b1.py, dr_score.py, dr_verdict.py and
  placement_carve.py REAL), `setup.sh`, `make_store.py`, `check.py`, `run_all.sh`.
- **The fake store holds REAL store files** (single-file downloads, scratch): evb1420's 38 eval-20 pull / result files and the
  packed checkpoint, the H5p7 eval-20 draws and h5_summary.json, pack 6's eval-20 rollout.
- **Test-only edits (`test_edits.json` per scenario):** the packed run's parquets name `/content/...` asset paths; the mock
  rewrites them to MR/content (fingerprint asserted unchanged), so the repo COPY's REF_MD5 and packed_refs.json's eval-20 md5 are
  set to the rewritten P's md5. Every other pin is real.
- **REAL:** ev20_b1.sh, glock_public.sh, ckpt_curve.sh, store.sh, lib.sh, placement_carve.py (on the real packed assets),
  make_assets.py, qa.py with the real kit, no_oracle.py, e20b1.py, e10nj.py, dr_score.py with the real kit.
- The packed side (K, old) is real data in every scenario; the new side is synthetic. Mock numbers of the new side are NOT
  evidence about b1.

Final runs on the final code, 1 Nov ~07:07-07:55 UTC (`cpu/out/mock_checks.txt`, `mock_check_<n>.txt`, `mock_<n>/`):

| scenario | injected | outcome (mock numbers; K and old are the REAL packed files) | checks |
|---|---|---|---|
| pass | policy tracks P; 0 overflow lines | gate met (0.9988 / 0.9997 > 0.8933); 10 official draws; **SWAP-ELIGIBLE, INCLUDE** (gain +0.107 vs P; b 0 vs 0 fails; c 0.35 vs 1.67 cm); chosen s43 | 37/37 |
| floor | objects left at frame 0 | **NO-SWAP, training-box gate not met** (0.3653 / 0.3652); no official draw | 36/36 |
| unclean | policy tracks P; 5,000 overflow lines per training log | **SWAP-ELIGIBLE [pieces not clean in training]**, INCLUDE (the rule still applies) | 37/37 |
| invalid | one extra config key in seed 43's training | **INVALID** (cells: s43 config differs in training.mock_extra_setting); no choice, no official draw | 30/30 |
| tamper | one pitcher piece edited in the box's repo copy | STOP at the piece check ("md5 differs from MD5SUMS: water_pitcher/piece_07.obj") -> INVALID; nothing pulled, trained or evaluated; verdict and push still written | 10/10 |
| badrun | RUN_ID `20261101-e20x-mocksha` | refused at the start (exit 1); nothing pulled, run or pushed | 3/3 |

**153 / 153 checks.** Every full scenario checks:
- no store listing; every download is a single file of the packed run, the H5p7 draws or pack 6's eval-20 rollout; exactly one
  upload, into this run id;
- the pieces (pinned md5s, 41 pieces) and the packed inputs (P fingerprint, stage, packed URDF / glb md5s, packed sha256);
- the REAL placement_carve.py carve: only the pitcher URDF changes (-> 77b395a5, 41 collisions), 41 byte copies added, visual and
  inertial unchanged, blue cup untouched; on the box refs/sf/ep20/assets is the b1 copy and the pristine copy sits in e20b1_in;
  the push holds the b1 copy, not the pristine copy; the packed run's store files are unchanged;
- arms (byte copies of P naming the b1 URDFs at 0.3 kg); no_oracle on the pieces and every input;
- **two trainings** (seeds 42 / 43, 70,004,736 steps, on the seed copies, loading the b1 URDFs at 0.3 kg from refs/sf/ep20/assets);
- **no sim.* override; saved sim / env.sim 512 / 256**;
- **every CLI training key equal to the REAL packed eval-20 config; TRAIN_ARGS byte-identical to evb1420's REAL job-log line;
  the CLI key set = the glock_public.sh template + TRAIN_ARGS**;
- REUSE_REF twice, SF 0, no reference stage; no make_assets --pieces;
- overflow counts = the injected counts, and the label;
- the b1 zero-action rest check ran and is reported;
- cells (VERIFIED, config diff within the allowed keys, stock limits, stage md5); the choice = the pack 9b rule; the gate;
- 10 official calls at stock 512 on the pristine worktree only when the gate is met, and no_oracle accepting the chosen
  checkpoint;
- scored counts (conf 10 / 0, packed 10, old 1, train 10 + 10) with every own-reference check ok;
- **the packed side scored from the REAL H5p7 files: mean 0.8933 (raw 0.89335), 0 / 10 fails, median RPE 1.67 cm**, as the
  stand-alone CPU score;
- the clauses, the inclusion reading, the summary's piece manifest (41 lines) and the URDFs used.

Two fixes during the build (both found by the mock, both before the final runs):
- `tools/e20b1.py cells` looked for the support stage one folder too deep (`<RD>/processed/reconstructed_stage`); it is
  `<RD>/reconstructed_stage` (as the D arm's verify reads it).
- check.py compared the packed mean with 0.8933 exactly; the scorer's rounding of the raw 0.89335 prints 0.8934 (a check bug).

## 9. Commit and PREREG
- Branch `worktree-agent-ad5ea562458c54efd`, based on `origin/claude/focused-pascal-2nz9s1` 7bac1b5.
- Commits:
  - 36f255a: the piece import, tools/e20b1.py, ops/jobs/ev20_b1.sh, the glock_public.sh opt-in, PREREG.md, JOBS.txt, the CPU
    scripts and the mock (no result of this test existed: nothing was launched);
  - then BUILD.md and the CPU outputs (`cpu/out/`).
- **PREREG.md sha256 `d13c9116aa5fcf0b1ae6a71b1536fcdd823f9d91685187c153f1a14368075a70`**, committed in 36f255a before any result
  and unchanged since.
- The launch commit must contain PREREG.md unchanged.

## 10. Risks and open points
1. **The f192 trade.** In FlashCHORD (determined-wright 85e8ef8, one settle draw per set) the pitcher falls over hands-free at
   f192 in both sets, b1 more than packed (12.0 cm / 50 deg vs 6.8 cm / 28 deg). f192 is hands-off in our reference (149 mm to
   the nearest robot hand; hands-off f165-f201). So b1's pitcher is less stable than packed at that hands-off rest frame, even
   though plain MuJoCo read the opposite. The end phase (f165-f201) could cost pitcher tracking; the pitcher's per-object AUC is
   reported. At f183 b1 also turns more (3.2 vs 2.0 deg).
2. **P was built on the packed collision copy** (grasp lock, ILC, the zero-action replay). Not rebuilt.
3. **The b1 copy lives at the packed path name** `refs/sf/ep20/assets` (the path P names; the mesh lane's method). It is pushed
   under this run id only. Any later re-run of this checkpoint must pull refs/sf/ep20 from this run and never put evb1420's copy
   into the same /content (`store.sh pull-run` copies with `cp -n`: the first copy wins). JOBS.txt says so.
4. **Contact rows.** Plain MuJoCo G4 flagged (+46-64 %); FlashCHORD 32 x 60 is clean (342 max). 4,096 worlds are first measured
   by this job's overflow count (> 1,000 lines labels the result).
5. **The rule is strict here.** K has 0 / 10 fails and median RPE 1.67 cm; a single failed draw (RPE > 5 cm) gives NO-SWAP, and
   inclusion needs mean(N) >= 0.9134 on the official evaluator. Expected outcome NO-SWAP or below the bar [E, guess].
6. **Training box vs official evaluator.** The gate uses training-box draws (patched tree, explicit resets); the confirmation is
   the official test.
7. **Recipe drift ee7ba8e -> now** is covered by the config diff (cells) and the mock's CLI check; the D arm verified the same
   path on evb1420's eval 14.
8. **The gate bar** 0.8933 is the summary value; K's raw mean is 0.89335. Immaterial (5e-5); the clauses and the inclusion bar
   use the raw means.
9. **A1 is a post-hoc amendment** of the mesh lane, for this one set.
10. **No re-run mode.** INCOMPLETE needs a new decision.

## 11. Re-running the CPU evidence (S = the session scratchpad, R = the repo)
- Downloads: `docs/research/work/perception-sprint-20261031/ev10retrain/cpu/scripts/dl.py S/e20b1/dl <the 38 eval-20 pull_files +
  result_files of packed_refs.json>`, the H5p7 r1..r10 ep20 files, h5_summary.json, pack 6's eval-20 rollout; the packed
  checkpoint `runs/20261025-evb1420-ee7ba8e/results/final_eval/ep20/policy.safetensors`.
- Packed side: `S/map/scoring/venv/bin/python -I tools/dr_score.py --kit <kit> --lib meshes/library_v3 --ep 20 --ref P=<P> --set
  "packed:P:<dl>/runs/20261031-h5p7-1a7cdff/results/h5/r*/ep20/episode_000020.parquet" --set "old:P:<pack 6 ep20 parquet>"`
  -> `cpu/out/packed_side_score.json`.
- H30: `python -I cpu/scripts/h30_check.py <P> <dl>/.../refs/sf/ep20/assets cpu/out/h30_ep20.json`.
- Carve: `python -I pipeline/placement_carve.py assets <content>/refs/sf/ep20/assets meshes/carve/ev20b1 <out>`, then
  `tools/e20b1.py inputs / assets / arms` as in the job -> `cpu/out/carve_cpu/`.
- `python -I cpu/scripts/config_guard_test.py --repo R --packed <ep20 ck> --packed14 <ep14 ck> --dr_verify
  docs/research/work/pack9b-20261031/results/drG/verify.json --work <dir> --out cpu/out/config_guard_test.json`.
- `bash cpu/scripts/guard_equiv.sh R cpu/out/guard_equiv` (~5 min); `bash cpu/scripts/static_checks.sh R cpu/out/static_checks.txt`;
  `python -I cpu/scripts/verdict_tests.py --repo R --work <dir> --out cpu/out/verdict_tests.json`.
- `bash cpu/mock/run_all.sh [scenario ...]` (~10-15 min per full scenario on 4 cores, mostly scoring).
