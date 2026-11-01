# Eval-10 njmax diagnostic: build notes (1 Nov 2026, CPU only, nothing launched)

**Question.** Is eval 10's "cup never lifted" floor caused by constraint rows dropped during training? The e10v run
logged ~6.0 M "nefc overflow" lines per seed against njmax 512. The test is one diagnostic training at njmax 1024 /
nconmax 512, reusing e10v's stored V4p reference, with the same checkpoint also evaluated at 512.
- Rule and labels: `PREREG.md` (written before any result; sha256 `33add65e…` at writing, commit `086de63`).
- Launch string and cost: `JOBS.txt`.
- Labels: [M] measured here, [E] estimate, [H] hypothesis.
- Machine: this Claude cloud VM (4 CPU), 1 Nov ~02:50–04:30 UTC, $0. No GPU, Vast or Kaggle. Nothing pushed.
- Eval 10 has no ground truth; nothing here reads mocap, scans or `observation.objects`. Store reads: ~10 single-file
  downloads of e10v's run (its manifests, curves, V, its support usda, seed 43's checkpoint).
- **DIAGNOSTIC ONLY, NEVER PACKED** (PREREG section 6).

## 1. What is built
| file | what |
|---|---|
| `ops/jobs/ev10_nj.sh` | New job, run id `<date>-e10nj-<sha7>`. It pulls e10v's V through e10v's own re-run manifest (`rerun_files.txt`; from `rerun_results.txt` only the control), makes a seed copy, runs ONE glock_public.sh training (seed 43, `TRAIN_ARGS="sim.njmax=1024 sim.nconmax=512"`), then: overflow and lift JSONs; identity vs e10v s43 (STOP on failure); the 512 copy; the evaluator-side solver check; the pack-guard check; 10 official draws at 1024 and 10 of the copy; scoring vs V and P; verdict; one push. |
| `tools/e10nj.py` | `arms`, `overflow`, `lift`, `cksim` (the 512 copy), `identity`, `guard`, `verdict` (PREREG section 4). |
| `tools/e10nj_solver_check.py` | FlashCHORD's evaluation code path on a checkpoint, up to the built SolverMuJoCo (config chain; with `--solver` also njmax / naconmax / nv / Data bytes). Run with the FlashCHORD venv from the pristine evaluator tree. |
| `ops/jobs/glock_public.sh` | Opt-in `EVAL_NJ_DIAG=1`. It allows the PERC prefix `perc2e10njs<seed>` with SPLIT=eval, episode 10, RUN local and REQUIRE_REUSE=1. That is 1 code line plus 6 comment lines; the default path is unchanged (section 5). |
| `tools/no_oracle.py` | Refuses `e10nj` / `ev10_nj` in any word or path, and any checkpoint whose stored config has non-stock sim limits (section 4). |
| `tools/pack_swap_rollouts.py` | Also hands each swap parquet's `flash_chord.reference_parquet` to no_oracle (1 code line). |
| `docs/research/work/eval10-njmax-20261101/` | PREREG.md, BUILD.md, JOBS.txt, `cpu/scripts/` (tests), `cpu/mock/` (end-to-end mock), `cpu/out/` (outputs, e10v control files). |

Not changed (checked: `cpu/out/static_checks.txt`):
- `ops/jobs/ev10_v4p.sh`;
- `tools/e10v_{score,verify,verdict}.py`, `tools/e10v_track.sh`;
- `ops/box/*`, `tools/ckpt_curve*`, `pipeline/qa.py`;
- the pack jobs (`h5_reeval.sh`, `pack_eval.sh`, `submit_pack.sh`), `mass_eval.sh`, `ep11_gate.sh`.

## 2. Design choices
- **A wrapper job, not a knob in ev10_v4p.sh.** Almost every stage of ev10_v4p.sh would need a branch: run-id tag, result
  folder, prefix, seed list, rule 2, two official sets, scoring sets, verify, verdict. ev10_v4p.sh therefore stays
  byte-identical, and the new job reuses its mechanisms instead:
  - the stored manifest `rerun_files.txt` and the single-file pulls with short retries for optional files;
  - the seed-copy idea of `e10v_verify.py arms` (`tools/e10nj.py arms`, same checks plus equality with e10v's
    `arms.json`);
  - glock_public.sh with REUSE_REF / REQUIRE_REUSE;
  - the confirm() loop, verbatim but parameterised by set and checkpoint;
  - `tools/e10v_score.py` unchanged.
- **Recipe identity:** the 8 recipe lines (export / unset) are ev10_v4p.sh's, verbatim (static check). They are then
  enforced on the box by the config diff against e10v seed 43's own checkpoint. Only `output_dir`, `task.parquet`,
  `reference.parquet` and the four sim limits may differ, and reset.seed 43 and the steps must match. The rest of the
  e10v recipe (the gl10A2 config) was verified by e10v's own `verify.json` against the packed checkpoint.
- **Seed 43 only**, e10v's chosen seed (rule 2). Pre-registered in PREREG section 2.
- **Names:** `perc2e10njs43_*` (refs / runs / results), `results/ev10_nj`. e10v's files keep their own names
  (`refs/perc2e10vmck/ep10`, `refs/perc2e10v_glockt/ep10`, `results/perc2e10v_glock_public/ep10`) because the seed copy
  and its base link point at them. The control files (e10v s43's checkpoint, e10v's 10 draws, its arms.json, P, the
  curves) go to `/content/e10v_in`, which store.sh does not push. Nothing named `perc2e10vs*` or `results/ev10_v4p` is
  written on the box (mock check).
- **Lift (correction to the brief).** The brief says "the blue cup is never lifted ('lift 0')". The job log's curve
  label shows only the first object of the curve line, which is the blue cup (`docs/analysis/ev10-stack-20261026/README.md`).
  The reference keeps the blue cup on the table (reference lift 1.5 cm) and lifts the **beige** cup 23.5 cm into it.
  [M] e10v's `curve.json` (pulled 1 Nov, `cpu/out/control/`):

  | cup | e10v r1 lift at its 14 checkpoints | reference lift |
  |---|---|---|
  | beige | 0.0–0.3 cm at 13; 2.5 cm once (s42 60M, a knock, still "lost at" f40) | 23.5 cm |
  | blue | 0.1 cm at all 14 | 1.5 cm |

  PREREG clause L is therefore set on the beige cup at ≥ 5.0 cm in r1 (twice the control's worst knock; 21 % of the
  reference lift). The blue value is reported as the log-label equivalent. **The orchestrator should confirm this
  reading of the owner's "lift > 0" before the launch**; the PREREG is unpublished until then.
- **Box hygiene:**
  - The GPU-memory sampler writes under `$TMPDIR`, not a watchdog path, so a stalled training still trips the 30-min
    watchdog.
  - The guard's neutral copies also go under `$TMPDIR`.
  - The solver check runs twice: the config chain alone first, then with the solver build (900 s cap each), so a crash
    in the build cannot lose the config reading.
  - The official draws, the solver check and the guard run before scoring.
  - There is one store push. On a STOP, `stop()` writes the verdict (INVALID) and pushes.

## 3. The 512 copy: how the config is stored, and the CPU proof [M]
- A FlashCHORD checkpoint is a safetensors file. Its header `__metadata__` holds `user.resolved_config_json`
  (`training/checkpoint_metadata.py build_checkpoint_metadata`): the fully resolved hydra config as canonical JSON
  (`sort_keys`, compact). The limits sit at `sim.njmax / sim.nconmax` and, resolved from `env.sim: ${sim}`, at
  `env.sim.njmax / env.sim.nconmax`.
- The official evaluator (kit `evaluate_policy.py` → `harness.evaluate_checkpoint`) reads that config, applies
  `apply_evaluation_composition`, which does not touch sim, and builds `RLEnvConfig` and the SolverMuJoCo from `cfg.env`.
- On 5 real checkpoints (packed gl10A2, e10v s43, the ep11 gate, pack checkpoints) both the outer header and the inner
  config re-serialise byte for byte. `cksim` relies on that and refuses otherwise.

**3.1 `cpu/out/cksim_test.json`, 9/9 pass**:
- The FlashCHORD configs at the pin were composed with hydra (`train_flash_sac`, `experiment=sharpa_flash_sac`, our
  `sharpa_hands_mid`), with and without `sim.njmax=1024 sim.nconmax=512`. The 475-key resolved configs differ in exactly
  `sim.njmax, sim.nconmax, env.sim.njmax, env.sim.nconmax`, so that is all a training override changes in the stored
  config.
- On the REAL packed gl10A2 checkpoint (sha256 `76a12265…`, 32 tensors), cksim 512/256 → 1024/512 makes a stand-in of a
  1024 checkpoint. cksim 1024/512 → 512/256 on the stand-in makes the copy. **The copy is byte-identical to the original**
  (sha256 `76a12265…` both). In each step the buffer is identical, the config diff is exactly the four keys, and no other
  header or metadata entry differs.
- Refusals: a wrong `--from` and a non-canonical header.
- FlashCHORD's own `read_checkpoint_metadata`, `checkpoint_config` and `_read_checkpoint` load all three files, with
  every tensor identical in dtype, shape and bytes.
- The evaluator's config chain (`tools/e10nj_solver_check.py`) gives RLEnvConfig.sim **512/256 → 1024/512 → 512/256**.
- Python: FlashCHORD source at commit 7eb9721, whose `flash_chord/src` has an empty diff to the evaluator pin
  `8c778f9`, in the scratch venv `carve/fcvenv` (mujoco / mujoco-warp 3.8.1, newton 1.2.0, warp 1.14.0 = uv.lock). A CPU
  overlay adds jax / jaxlib 0.10.2, flax 0.12.7, optax 0.2.8, safetensors 0.8.0, distrax 0.1.9, chex 0.1.92 and
  tfp-nightly (the uv.lock pins).

**3.2 `cpu/out/solver_cpu_test.json`, the built solver** (warp device cpu, 1 world). Inputs: e10v's REAL stored V (md5
`5d22fc57…`) and its support usda, the eval-10 assets (make_assets library_v3 + carve/ev10; URDF md5 = e10v's
arms.json), and e10v seed 43's REAL chosen checkpoint (sha256 `bcc51063…`). The test-only edits are the asset paths in
the V copy and the task / reference paths in the checkpoint copy.

| file | stored limits | RLEnvConfig.sim | built SolverMuJoCo njmax / naconmax | njmax_nnz | Data bytes, 1 world |
|---|---|---|---|---|---|
| e10v s43 (real) | 512 / 256 | 512 / 256 | **512 / 256** | 11,320 | 204,564 |
| 1024 stand-in | 1024 / 512 | 1024 / 512 | **1024 / 512** | 22,584 | 364,308 |
| its 512 copy | 512 / 256 | 512 / 256 | **512 / 256** | 11,320 | 204,564 |

The model has nv 74 (sparse Jacobian), 156 geoms and 56 bodies.

**So the kit evaluator honours the copy's 512 config** [M on CPU at the pin]. The box repeats both checks on its own
pristine tree with cuda (`solver_check.json`, `solver_build.json`), and the 512 readout is VALID only if the copy reads
512/256 there. The copy has its own sha256, so the draws name it and the verdict checks that.

## 4. The pack guard (`cpu/out/guard_test.json`, 15/15 pass) [M]
- **no_oracle by name:** `e10nj|ev10_nj` was added to BAD. Refused: 11 names, including the run id, its store paths,
  `perc2e10njs43`, the refs / runs / results folders, `results/ev10_nj/...`, `EP:DIR`, `ck=` and `RUN@sub` words. The old
  guard (68f1421) accepted all of them.
- **no_oracle by content:** a `.safetensors` is refused when its stored config names a BAD folder (already the rule) or
  holds non-stock limits (new: sim / env.sim njmax or nconmax ≠ 512 / 256). All 6 neutral-name cases are refused and the
  old guard accepted each:
  - a 1024 stand-in of e10v's real s43 checkpoint (limits only);
  - a diagnostic-like checkpoint (`perc2e10njs43` paths + 1024);
  - its 512 copy (stock limits; caught by its paths);
  - a kit checkpoints JSON naming the stand-in;
  - a neutral symlink onto `results/ev10_nj/conf1024`;
  - an evaluator episode JSON naming the diagnostic checkpoint.
- **No regression:**
  - 24 distinct REAL checkpoints found locally (all 20 of pack 7, e10v s43, gl10A2, the ep11 gate, …) are accepted as
    words and as one kit JSON, and all store the stock 512 / 256;
  - 14 e10v names and look-alikes are accepted (`ev10_v4p`, `e10v`, `njmax`, `eval10-njmax-20261101`, …);
  - on the store listing of 29 Oct (134,909 paths), the old and new rule both refuse 789, with 0 newly refused.
- **pack_swap_rollouts:**
  - A legit ep14 swap (pack 9b's U1 fixture, guard ON) builds byte-identically with the old and the new tool (sha256
    `094d650fa306…`, as U1 on 1 Nov).
  - A swap whose `.json` names `results/ev10_nj` is refused, and nothing is built.
  - A renamed swap (neutral `.json`) whose parquet metadata names `refs/perc2e10njs43_glockt` is refused by the new tool.
    The old tool, even with the new guard, built it, which is why the metadata word was added.
- **Box:** `tools/e10nj.py guard` requires no_oracle to refuse both checkpoints as is, as neutral byte copies and via a
  kit JSON (`guard.json`, reported in the RESULT line).
- **Residual gap [H]:** a rollout whose `.json` and parquet metadata were both scrubbed of every path is not caught. Its
  `checkpoint_sha256` stays. After the box, the two diagnostic sha256s could be added to a denylist (not built; an
  `ops/provenance` change for the orchestrator).

## 5. Default paths unchanged [M]
- **glock_public.sh** (`cpu/scripts/guard_equiv.sh`, `cpu/out/guard_equiv/summary.txt`): the PERC guard block of `one()`
  was cut from 68f1421 and from the working tree and run over 5,184 cases (SPLIT × 12 prefixes × RUN × REQUIRE_REUSE ×
  episode × EVAL_LOCAL_REF × FC_DR_PATCH × EVAL_NJ_DIAG).
  - With EVAL_NJ_DIAG unset or 0: **0 differences**.
  - With EVAL_NJ_DIAG = 1: exactly 8 cases change, all newly ALLOWED and all `perc2e10njs42|43` / eval / episode 10 /
    local / REQUIRE_REUSE=1.
  - The rest of glock_public.sh is unchanged except 6 comment lines (static check: 1 code line added, 0 removed).
- **ev10_v4p.sh** is byte-identical (static check). Its end-to-end mock 'pass' (31 Oct's harness, unchanged) was re-run
  on this build's code (new glock_public.sh and no_oracle.py): **SWAP-ELIGIBLE, 28/28 checks**, as on 31 Oct (section 7).
- `bash -n` / `py_compile` are clean on every changed script (`cpu/out/static_checks.txt`).

## 6. GPU memory at 1024 rows × 4096 worlds [M on CPU + E]
- [M] The MuJoCo-Warp Data arrays of the real eval-10 scene (section 3.2) take 204,564 B per world at 512 / 256 and
  364,308 B at 1024 / 512. At 4096 worlds that is 0.84 → 1.49 GB, **+0.65 GB**. Data includes the constraint arrays,
  the sparse Jacobian (njmax_nnz 11,320 → 22,584) and the contact arrays sized by naconmax.
- [E] Not in Data:
  - the Newton solver's per-row context (Jaref, jv, quad, changed_efc_ids; ~24 B per row → +0.05 GB);
  - Newton's force-contact buffer sized by `get_max_contact_count()` (naconmax 1.05 M → 2.1 M contacts; ~+0.1–0.3 GB).
- [M, glock_public.sh's note of 24 Oct] One FlashSAC training at 4096 worlds peaks at 40.4 GB. **Expected peak ≈ 41–42 GB
  of 96 GB**, so OOM is unlikely. Only one training runs; the curve and draws use 1 world. glock_public.sh retries an OOM
  twice. The box samples memory every 60 s (`gpu_mem.csv`; peak in the job log).
- [E, not measured] Speed: the Newton solve and line search scale with the active rows (up to ~1,050 instead of being
  cut at 512) in nested phases. Training may be slower; the cost table's high column assumes +35 %.

## 7. CPU mock of the whole job (`cpu/mock/`, outputs `cpu/out/`)
- Harness: the e10v mock's setup.sh, run_mock.sh and hf_stub.py, plus this folder's `stub.py`, a copy of e10v's stub
  with these changes:
  - the trainer writes the `sim.*` CLI overrides into sim and env.sim, prints MuJoCo-Warp overflow lines
    (MOCK_OVF_1024 / MOCK_OVF_512) and writes checkpoints in FlashCHORD's canonical format;
  - the evaluators read the evaluated checkpoint's stored njmax (MOCK_POLICY_512 for a checkpoint stored at 512) and
    audit it;
  - `ckpt_curve_summary.py` runs REAL;
  - `e10nj_solver_check.py` runs REAL FlashCHORD (pin, CPU overlay).
- The fake store is the e10v mock run's own push, renamed to `20261031-e10v-caf38fb`, with e10v's REAL curve.json files.
- REAL code: ev10_nj.sh, glock_public.sh, ckpt_curve.sh, store.sh, make_assets.py, qa.py with the real kit,
  no_oracle.py, e10nj.py, e10v_score.py.
- Mock numbers are NOT evidence about H.

Final run on the final code, 1 Nov 03:20–04:12 UTC (`cpu/out/mock_checks.txt`, `mock_check_<n>.txt`, `mock_<n>/`; 6 scenarios,
181 checks, all pass):

| scenario | injected | outcome (mock numbers) | checks |
|---|---|---|---|
| e10v | the DEFAULT path: `bash ops/jobs/ev10_v4p.sh`, e10v's mock 'pass' (MOCK_POLICY=copy) | SWAP-ELIGIBLE, VERIFIED | 28/28 |
| supported | policy tracks V; 40 overflow lines at 1024; the 512 copy rolls out as the floor | **SUPPORTED**: O 40; L beige r1 max 23.8 cm; A 0.9995 (n 10). 512 readout VALID, 0.4567 (−0.543) | 32/32 |
| falsified | cups left at frame 0; 0 overflow lines | **FALSIFIED**: O 0; L 0.2 cm; A 0.456 | 32/32 |
| inconclusive | policy tracks V; 5,000 overflow lines at 1024 | **INCONCLUSIVE**: O 5,000 (L 23.7 cm, A 0.9999 do not matter) | 32/32 |
| partial | beige lifted 8 cm at f30–60 and put back; 40 lines | **PARTIAL**: O 40; L 8.2 cm; A 0.4428 ≤ 0.4593 | 32/32 |
| invalid | one extra key in the 1024 training's config | **INVALID**: STOP at identity ("stored config differs … training.mock_extra_setting"); no official draw; verdict and push still written | 25/25 |

Every diagnostic scenario checks the following:
- no store listing; every download a single file of `runs/20261031-e10v-caf38fb`; exactly one upload;
- nothing written under e10v's names (`perc2e10vs*`, `results/ev10_v4p`) or the packed names;
- arms equal to e10v's `arms.json`, and no_oracle accepting e10v's inputs;
- **one training**: seed 43, 70,004,736 steps, on the seed copy;
- the trainer received `sim.njmax=1024 sim.nconmax=512`, and the saved config holds 1024 / 512 in sim and env.sim;
- every other CLI training key equals the packed config (10+ keys);
- TRAIN_ARGS is the FDR overrides followed by the two sim keys;
- REUSE_REF holds, and no reference stage ran;
- the overflow count equals the injected count;
- lift has 7 checkpoints × 3 repeats, with e10v's REAL controls read (2.5 / 0.3 cm);
- identity diff = the paths + the four limits;
- the 512 copy is header-only;
- the **REAL FlashCHORD evaluator config chain** reads ck1024 [1024, 512] and ck512 [512, 256];
- the guard refuses 6/6;
- 10 official calls of the 1024 checkpoint, each rebuilt at **njmax 1024** from its stored config, and 10 of the copy,
  each rebuilt at **njmax 512** (the stub reads the evaluated file's stored config, as the evaluator does), all on the
  pristine worktree;
- the curve plus training-box evaluations are 31, all of 1024 checkpoints;
- 10 + 10 + 10 + 10 rollouts scored, with every own-reference check ok;
- the 512 readout is VALID.

The solver build itself fails on the mock's minimal reference parquet. That is expected and reported only; the CPU
solver test of section 3.2 covers it on the real scene.

## 8. Risks and open points
1. **Lift reading** (section 2): PREREG L is the beige cup at ≥ 5.0 cm. The orchestrator should confirm it against the
   owner's "lift > 0" before the launch. If the owner meant the label as printed, the blue value is reported too.
2. **Overflow may not vanish at 1024.** e10v's requested njmax reached max 1,057 / 1,006 (p99 808), so a few lines above
   1024 are expected. A policy that starts nesting may also need more rows. O > 1,000 reads INCONCLUSIVE, which is
   pre-registered.
3. **A is weak on its own:** e10v's sd is 0.0093 over 10 draws, so a +0.003 gain passes A by noise. L carries the
   mechanism evidence and A only guards against "lift but worse". PARTIAL names "lift without a gain".
4. **Speed at 1024** is not measured; see section 6 and the cost table's high column.
5. **Store dependence:** the job needs e10v's run in the store, including rerun_files / rerun_results, V, the seed-43
   checkpoint (sha256 bcc51063…, checked by the identity step through its config) and arms.json. All were read
   successfully here on 1 Nov.
6. **cksim needs a canonical header.** All 5 real checkpoints checked are canonical. A non-canonical box file leaves the
   512 readout MISSING, not the main label.
7. **The solver build on the box** uses cuda:0 from the pristine tree. If it fails, the config chain still decides the
   512 status. CPU built it in 18 s here.
8. **Never packed:** see section 4 and its residual gap. JOBS.txt "After the box" says never to copy anything of this run
   into `results/submissions/`.
9. **One seed:** this shows the mechanism, not its spread.

## 9. Re-running the CPU evidence (scratch paths of this VM; S = the session scratchpad)
- FlashCHORD-capable python: `S/carve/fcvenv/bin/python` (FlashCHORD source at the pin, editable) with
  `PYTHONPATH=S/nj/fcextra JAX_PLATFORMS=cpu`. The overlay is `uv pip install --target` of the uv.lock pins listed in
  section 3.1, with packages already in fcvenv removed from it.
- `cpu/scripts/cksim_test.py --repo R --ck <packed gl10A2 policy.safetensors> --py S/map/scoring/venv/bin/python --fc
  <flash_chord dir> --emb R/flashchord_conf/embodiment/sharpa_hands_mid.yaml --work <dir> --out cpu/out/cksim_test.json`
  (FlashCHORD python).
- `cpu/scripts/solver_cpu_test.py --repo R --ck <e10v s43 policy> --ref <e10v V> --usda <its support usda> --assets
  <make_assets output> --py ... --fc ... --work <dir> --out cpu/out/solver_cpu_test.json` (FlashCHORD python; ~30 s).
- `python -I cpu/scripts/guard_test.py --repo R --scratch S --fix <dir> --py <py> --packpy S/pack9a_venv306/bin/python
  --kit <kit> --standin <cksim stand-in> --out cpu/out/guard_test.json` (~30 s).
- `bash cpu/scripts/guard_equiv.sh R <dir>` (~40 s); `bash cpu/scripts/static_checks.sh R cpu/out/static_checks.txt`;
  `python -I cpu/scripts/verdict_tests.py --repo R --work <dir> --out cpu/out/verdict_tests.json`.
- `bash cpu/mock/run_all.sh [scenario ...]`. Run e10v first; the others each take ~7–15 min on 2 cores, mostly scoring.
