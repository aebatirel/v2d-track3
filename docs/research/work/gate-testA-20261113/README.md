# Test A GPU batch: plan, launch commands, CPU dry run, cost, risks (PREPARED, NOT LAUNCHED)

Prepared 2026-11-12/13 (container clock 2026-11-12 23:30 to 2026-11-13 00:20 UTC; the work-log entries this follows
are stamped about 3.5 h later, on the coordinator's clock). No Vast instance was created. Nothing was committed or
pushed by the preparing agent. Vast reads only: offers, instances (0), credit ($33.98).

Labels: [M] measured, [E] estimate, [H] hypothesis.

## 1. Verdict

**Mechanically ready.** All four job strings run end to end in the CPU dry run, from `onstart.sh` to the
self-destroy call. The reused `ops/jobs/hard_ab.sh` needs no code change and there is no new job script.

**Before launch, three decisions (section 7) must go in the work log**, because they change what the test means:
- **D1, simulator meshes.** The 20 Oct references name the organisers' public scan URDFs (`/content/t3/urdf/*`), so
  physics runs on the scans and their collision meshes, not on `library_v3`. `LIB=library_v3` does not reach the
  simulator. This matches the gate's input and tests C/C2, but the plan text says "library_v3 meshes".
- **D2, label rollout.** The recipe evaluates 4 or more checkpoints and keeps the one that tracks our reference best,
  which is the same quantity the label measures. The rollout that should count as "the first official draw" must be
  fixed in advance. Recommended: the fresh NREP=1 draw.
- **D3, evaluator.** Box draws run `evaluate_policy.py` on the training box's patched FlashCHORD tree. The pristine kit
  evaluator is not used. The 3 Nov evaluator-gap test found no gap.

Cost [E], 4 boxes:
- at the 23:31 UTC prices: about $21–27, central $23.5, bad case about $29 (one slow container start);
- at the 00:16 UTC prices: $22–28, central $24.8, bad case about $30.6, just over the cap.

The cap is $30 and the credit $33.98. Ledger planned lines: 4 × $7.00 = $28.00.

## 2. Plan (work log 2026-11-13 ~02:30 and ~03:00 UTC amendment)

| Box | Episodes (training order) | Objects | Gate infeasible share | Ref frames [M] |
|---|---|---|---|---|
| gA1 | ep12, ep31 | blue cup + rack; sweeper + rack | 0.00; 0.639 | 181; 290 |
| gA2 | ep40, ep21 | dust pan; blue cup + pitcher | 0.00; 0.304 | 260; 186 |
| gA3 | ep23, ep2 | wooden pieces 1+2; pot + lid | 0.017; 0.195 | 325; 343 |
| gA4 | ep18, ep24 | sweeper + dust pan; wooden pieces 1+2 | 0.064; 0.269 | 353; 275 |

- **References:** `runs/20261020-refsweep-ea14fdf/refs/perc2/ep<N>` and its perception `perc2/ep<N>`, as stored.
  - Each processed parquet's sha256 equals the file the gate was scored on [M] (`dryrun/ref_sha256.json`; the store's
    LFS oids match the gate's local copies).
  - The job refuses to train if a sha256 differs.
- **Recipe:** `std_learner.sh`'s environment for `hard_ab.sh`, on public data:
  - `FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS"`;
  - `SPLIT=public PDIR_ROOT=/content/perc2 SUF=s CR=0 BASE_EVAL=0 NREP=1 SEED=42 LIB=meshes/library_v3`;
  - 250,003,456 steps (the hard_ab default).
- **Pairs:** `"<a>:local: <b>:local:"`. BASE is empty, so the base reference is `refs/perc2/ep<N>` and SUF=s puts the
  training copy in `refs/perc2s/ep<N>`.
  - With BASE empty, SUF must not be empty. Otherwise `R1 == R0`, and hard_ab's `rm -rf $R1` deletes the reference
    before copying it.
  - RUN is `local` because the job pulls the pair itself first: with retries and the sha256 check, and only those
    four sub-folders (`PULL_SUB`). hard_ab therefore does not pull the store a second time.
- **Per box:** two trainings, one after the other, on one GPU (hard_ab `TRAIN_LOCK`).
  - Each training is followed by the recipe's evaluation and checkpoint sweep (0.4 / 0.6 / 0.8), then one fresh
    official draw of the chosen checkpoint (NREP=1).
  - Then push to the store and self-destroy. The stall watchdog stays on (`STALL_MIN` 30).

## 3. Launch commands

[`JOBS.txt`](JOBS.txt): preconditions, checks, offer rule, 4 ledger `planned` lines, 4 `ops/vast.sh create` calls, and
the result paths.
- Run ids are `$(date -u +%Y%m%d)-gA<k>-<sha7>`, where sha7 is the pushed commit that holds this folder.
- That commit must equal the dry-run code (`ee653b38`) under `ops pipeline meshes/library_v3 spoon flashchord_conf`.
  JOBS.txt checks this with `git diff --quiet`.
- Jobs: [`jobs/gA1.job`](jobs/gA1.job) to `gA4.job` (sha256 in `jobs/SHA256SUMS`; generator `jobs/make_jobs.sh`),
  passed as `"$(cat jobs/gA<k>.job)"`.
- Image and snapshot: `IMAGE` is the `ops/config.env` default `vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16`.
  `ENV_SNAPSHOT=pt2.11-cu130-py313-20261020` (16.27 GB in 2 parts [M]; huggingface_hub 2.2.0 inside [M]). Every launch
  in the work logs that names a snapshot names this one (20 Oct to 30 Oct). The image tag was last used on 30 Oct;
  if Docker Hub had dropped it, the box would fail at start, which costs minutes, not the batch.

Example, box 1, at commit `C` on 13 Nov:
`bash ops/vast.sh V2D_COMMIT=$C ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> 20261113-gA1-${C:0:7} "$(cat docs/research/work/gate-testA-20261113/jobs/gA1.job)"`

## 4. CPU dry run (what was run and what it showed)

### 4.1 Method
- **Sandbox:** each box ran in a private mount namespace with an overlay over `/` and a chroot (`dryrun/harness/box.sh`).
  - `/content`, `/workspace`, `/etc/v2d_env` and `/venv/main` exist only inside it; the host was not changed (checked).
  - All writes land in the scratchpad.
  - Network and the session proxy are the real ones.
- **Inside** (`dryrun/harness/inner.sh`):
  - the real `pipeline/fetch_data.sh` (DATA-OK: 60 + 60 videos, 20 parquets, 11 meshes, 11 URDFs);
  - then the real `ops/box/onstart.sh` with the instance environment that `ops/vast.sh create` builds (`JOB_B64` = the
    exact job file);
  - onstart cloned the repo from GitHub at `ee653b38` and started the real `run_job.sh` and `watchdog.sh`.
- **Stand-ins (dry run only):**

  | Real box | Dry run |
  |---|---|
  | `ENV_SNAPSHOT` restore (CUDA builds, 16 GB) | `SETUP=none`; venv with numpy / pyarrow / trimesh / scipy / huggingface_hub 2.4.0; the scratchpad's FlashCHORD checkout at the evaluator pin `8c778f9` (overlay copy, so the patches applied for real); the kit from its public zip |
  | `scripts/train_flash_sac.py` (GPU, JAX) | `harness/fakes/fake_train.py`: records argv and environment, composes the Hydra config with FlashCHORD's own venv on the patched tree, checks every asset path the reference names, writes `policy_*` / `state_*` files every 10,000,384 steps |
  | `scripts/evaluate_policy.py` | `harness/fakes/fake_eval.py`: writes the metrics JSON and an object-trajectory parquet with the evaluator's schema (`flash_chord_object_trajectories_v1`); reference poses from the trained reference, achieved poses = reference + a synthetic 0–6 cm drift |
  | `view_policy.py` (render) | not run (exit 3; the recipe treats render failure as non-fatal) |
  | Vast API (labels, DELETE) | `harness/fakes/curl`: every `console.vast.ai` call is logged and never sent |
  | `hf upload` to the store | `harness/fakes/hf`: copied to a local fake store; downloads went to the real store (read-only) |
  | Cloudflare tunnel | `REXEC=0` |

### 4.2 Commands
- `bash dryrun/harness/box.sh gA<k> dry-20261113-gA<k>-ee653b3 ee653b3882516b0838e4be75fd8e292c9198f6be`, for k = 1–4.
  Run in parallel from 2026-11-12 23:55 to 2026-11-13 00:00 UTC (container clock); each box took 242–263 s.
- A stall test: `box.sh stall` with `harness/stall.job` (a job that only sleeps) and `STALL_MIN=2`.
- The CPU training-environment build: `envcheck.sh` → `envcheck_inner.sh` → `cpu_env_check.py`, on all 8 references.
- An earlier gA1 run used a first version of the job string, which made hard_ab pull a second time. It also passed.
  Its first full-store listing took 7 min; the job was then hardened (section 6, R6). It is not kept.

### 4.3 Results [M] (evidence in `dryrun/gA1` to `gA4`, `dryrun/stall`, `dryrun/envcheck`)

1. **References download and resolve, all 8.**
   - `prepull.log` shows the pulls; `job.log` has one `test A: ep<N> reference … sha256 OK (the gate's input)` line
     per episode.
   - Inside the trainer stub, every `object_urdf_paths` / `object_mesh_paths` entry and every mesh named inside those
     URDFs exists (`assets_all_resolve: true`; `train_call_ep*.json`).
   - All of them are `/content/t3/{urdf,mesh}/…`, which `fetch_data.sh` creates from the dataset's
     `track_3/public/{urdf,mesh}` (the kit's public scans).
   - The support stage `refs/perc2s/ep<N>/reconstructed_stage/t3_ep0NN_support.usda` is present, and `fps` = 20.0.
   - hard_ab's `fix_assets` therefore links nothing.
2. **library_v3 has every object of these episodes.** `make_assets.py` built all 11 library meshes (watertight) into
   `/content/assets` (`job.log`). No reference points there (D1).
3. **The training command line is exactly the std_learner recipe** (`train_calls.jsonl`, `train_call_ep*.json`):

       scripts/train_flash_sac.py experiment=sharpa_flash_sac task.parquet='/content/refs/perc2s/ep12/processed/sequence_id=t3_ep012/robot_name=sharpa_wave'
         task.motion_speed=1.0 reset.seed=42 logging.mode=disabled output_dir=/content/runs/perc2s/ep12-s42
         training.total_environment_steps=250003456 curriculum=tracking_250m_mixed_reset_v2d objective.force_closure.enabled=true
         objective.force_closure.weight=6 objective.contact_wrench_support.weight=3 objective.unintended_contact.weight=-2
       env: FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false

   - It is identical, apart from the episode, to the 25 Oct std_learner boxes and the 30 Oct carve boxes (same
     `TRAIN_ARGS` in their job logs). Since the 30 Oct boxes (`328139c`), `pipeline_ep.sh` changed only in a
     comment. Between the 25 Oct boxes (`ee7ba8e`) and 30 Oct, `hard_ab.sh` gained a `PIECES` option (unused here)
     and `store.sh` started keeping checkpoints that results name.
   - The three patches applied cleanly to the pin, as on those boxes: `patch_flashchord.py`, `_fdr.py` (writes the v2d
     curriculum) and `_voc.py`.
   - The config composes with rc 0: curriculum 11 stages; `sim.njmax` 512; embodiment `SharpaHands` (wrist kp 25,
     the default std_learner embodiment); force_closure on, weight 6; contact_wrench_support 3; unintended_contact −2.
4. **The training environment builds on CPU for all 8 references** (`dryrun/envcheck/env_ep*.json`). This is the
   patched tree, the exact overrides and the FDR variables, with `setup_scene` + `RLEnv`, reset at frame 0 and 5
   zero-residual steps.
   - Setup took 4.3–5.4 s and 5 finite rewards were produced for each episode.
   - The FDR objective module `v2d_fdr` was compiled and loaded.
   - This extends test C/C2's CPU replays (stock tree) to the patched training configuration. JAX training itself
     cannot run here.
5. **Outputs land where the store push expects them.** Each box pushed `runs/dry-…/` twice, once at the end of
   hard_ab and once in self-destroy (18–24 MB with stub checkpoints). Per episode it contained:
   - `results/hard_ab/ep<N>/s-s42/r1/episode_<E6>.parquet`: the fresh draw, with achieved and reference poses per
     step; its metadata names the reference parquet;
   - `results/hard_ab/ep<N>/s-s42/summary.json`;
   - the recipe's selection draws `results/perc2s/ep<N>-s42/{episode_<E6>.parquet, sweep/policy_*/…, selection.json}`;
   - `runs/perc2s/ep<N>-s42/policy_*.safetensors`: the chosen checkpoint is always kept, including when it was not the
     newest (ep40, ep21, ep23, ep18 chose an earlier one with the stub's random drift); state_ files are dropped after
     `.done`;
   - `train.log`;
   - `refs/perc2s/ep<N>/`: the reference used, its parquet byte-identical to the gate's input;
   - `job.log`, `run_job.log`, `prepull.log`, `hard_ab_ep<N>s-s42.log`, `watchdog.log`, `COMMIT`, `run_state/`
     (`fakestore_files.tsv`).
6. **The box self-destroys at the end.**
   - Labels: `setup` → `job running` → `hard A/B: …` → `saving, then destroy: job finished rc=0`.
   - The push came before the destroy, then `DELETE https://console.vast.ai/api/v0/instances/<id>/` was issued, and
     `run_job.log` reads `destroy requested` (`vast_calls.log`, all 4 boxes).
7. **The stall watchdog works.** With `STALL_MIN=2` and a job that makes no progress, the watchdog logged
   `stalled: no progress for 2 min` 4 min after the start, pushed, labelled the box and sent the DELETE
   (`dryrun/stall/`). Real boxes use 30 min.
8. **Per-episode evaluator calls:** 5 (final + 3 sweep checkpoints + the fresh draw; `eval_calls.jsonl`). The floor
   guard (5 more draws) did not trigger with the stub.

Not proven by the dry run:
- GPU training speed;
- the real evaluator;
- the env-snapshot restore on the box;
- the HF upload with the box's write token.

All four ran on the 25–30 Oct boxes with the same scripts.

## 5. Cost

Prices [M]: `ops/vast.sh offers`, on-demand, 2026-11-12 23:31 UTC (container clock), all-in with a 150 GB disk.
Qualifying offers (WS or S; download cost per the offer rule below):

| Offer | GPU / place | All-in $/h | $/TB down |
|---|---|---|---|
| 59926095 | PRO 6000 S, Oregon | 1.513 | 2.46 |
| 42702277 | PRO 6000 S, New York | 1.541 | 2.73 |
| 56857401 | PRO 6000 WS, Alberta | 1.610 | 2.67 |
| 48845069 | PRO 6000 S, New York | 1.640 | 2.73 |

Excluded:
- Max-Q, the cheapest at $1.462, is excluded: it trains at 51–76 % of WS speed [M, 22 Oct], so it costs more per
  policy. It also charges $30.6/TB download.
- The other compliant offers (24 in all) ran up to $1.87/h.

Durations [M] from earlier boxes running the same scripts:
- Two-episode `std_learner` boxes, 25 Oct (NREP 5, same snapshot): `run_job.sh` 197 min (WS, 16 CPU) and 230 min (S).
- Setup with snapshot restore: 5–6 min (4 boxes).
- One-episode pipeline, train + sweep + render: 107–115 min.
- 250M training ≈ 75–90 min on WS / S. The brief's 1.6 GPU-h per policy is close.
- The store pull took 1 min in the parallel dry run and 7 min in the first run.

Assumptions [E]:
- container start before `run_job.sh` 5–15 min (one start took about 1.5 h on 29 Oct);
- NREP 1 instead of 5 saves about 5 min;
- the two trainings run one after the other, as `hard_ab` does.

Box time: low 3.3 h, central 3.7 h, high 4.2 h.

| Box | $/h | Low 3.3 h | Central 3.7 h | High 4.2 h |
|---|---|---|---|---|
| gA1 | 1.513 | 4.99 | 5.60 | 6.35 |
| gA2 | 1.541 | 5.09 | 5.70 | 6.47 |
| gA3 | 1.610 | 5.31 | 5.96 | 6.76 |
| gA4 | 1.640 | 5.41 | 6.07 | 6.89 |
| **Total** | | **20.80** | **23.33** | **26.48** |

Additions and bounds:
- Download: about 18 GB per box (snapshot + dataset + references) × $2.5–2.7/TB ≈ $0.05 per box, so the totals are
  about $21.0 / 23.5 / 26.7.
- Bad case: one box with a 1.5 h container start or a slow host adds about $2.5, ≈ $29.
- Ledger planned: $7.00 per box, $28.00 in total. Cap $30, credit $33.98.
- GPU-hours: about 8 × 1.4–1.5 h of training plus about 40 evaluator calls.
- Wall time: about 3.5–4 h after the last create.
- **Second price read, 45 min later [M]** (2026-11-13 00:16 UTC container clock): the four offers above were gone.
  - The cheapest qualifying set was 57962402 WS Virginia $1.577, 59405105 S Romania $1.596, 57838530 S Spain $1.636
    ($20/TB, +$0.10/h effective) and 47972964 S New York $1.662.
  - Effective sum ≈ $6.70/h, so low / central / high ≈ $22.1 / 24.8 / 28.1, and the bad case ≈ $30.6.
  - **At those prices only the bad case breaks the $30 cap.** Prices move by the hour; re-read before the launch.
- **Offer rule:** RTX PRO 6000 WS or S, effective rate ≤ $1.75/h, where effective = all-in + 18 GB × $/TB-down /
  1000 / 3.7 h (≤ $10/TB adds < $0.05/h). One offer per box.
- **Stop rule:** if fewer than 4 offers meet the rule, do not launch the remainder at a higher price; ask. If the sum
  of the 4 effective rates exceeds $7.1/h, the high estimate (4.2 h) exceeds $30; ask before launching.

## 6. Risks and blockers

| # | Risk | Evidence | Handling |
|---|---|---|---|
| R1 | **Scan meshes in the simulator, not library_v3** (D1). The references name `/content/t3/urdf/<obj>_rigid.urdf` (organisers' public scan + collision mesh, 0.3 kg placeholder). | `train_call_ep*.json` [M]; tests C/C2 and the gate used the same files (wrench-gate README §10, "objects are the kit's public scans"). | Consistent with the gate's input. A library_v3 run would need rewritten references, which are not the gate's input; the gate would then have to be re-scored on them. Not done silently. Public data only; scans are not mocap poses. On 22 Oct the project called the scan simulator an oracle-mesh condition, so the result transfers to our library_v3 pipeline only in part [H]. |
| R2 | **Selection draws vs the label** (D2). `hard_ab.sh` hard-codes `CK_SWEEP="0.4 0.6 0.8"`, so `pipeline_ep.sh` evaluates 4 checkpoints (9 if the floor guard fires) and keeps the best sim_vs_ref against our reference. | `hard_ab_ep*.log`, `fc_python_calls.log` [M] | Use `results/hard_ab/ep<N>/s-s42/r1/episode_<E6>.parquet` (the fresh draw) as THE label rollout; do not use the selection draws. Only one evaluator call per policy would need a recipe change. |
| R3 | **Box evaluator, not the pristine kit** (D3). | 3 Nov evaluator-gap test, NOT REPRODUCED: A / B / C 0.935 / 0.926 / 0.930 and 0.925 / 0.937 / 0.938 [M] | State it in the record. |
| R4 | **All 8 references fail today's reference QA** (`qa.py ref`: wrist IK p95 > 60 mm and/or a wrist step > 10 cm). Policies may track poorly, so more than 90 % of frames could be positive, which makes the result inconclusive by the pre-registered share rule (C2 reached 98.6 %). | Left / right p95 mm: ep12 171 / 82, ep31 62 / 64, ep40 81 / 94, ep21 84 / 90, ep23 144 / 93, ep2 81 / 72, ep18 44 / 68, ep24 95 / 133 [M] | A property of the pre-registered references. hard_ab does not gate on qa_ref. |
| R5 | The 20 Oct references are **not rebuilt**. `pipeline_ep.sh` skips perception, hands and mkref because their outputs exist. Today's code would build different references (viterbi hand linker, detection rules, track guard, wrist cost 3.0, our meshes). Only stage 2b `hand_refine` runs; it writes an unused `hands_refined.npz`. | processed parquet sha256 unchanged after the run [M] | By design: the test is about these references. They load in the pinned FlashCHORD with today's patches (§4.3 items 3–4). The trainer's own load is first exercised on the GPU. |
| R6 | **HF store listing.** `hf download --include` lists the whole store tree (more than 100,000 files) before each first pull. This took 7 min through the session proxy and 1 min in the parallel run. 4 boxes at once could hit HTTP 429 (seen 25 Oct). | `hf_calls.log` [M] | Job: 3 pull tries 2 min apart, the sha256 + perception check, and no second pull in hard_ab. Stagger creates by about 2 min. A failed check exits 1, which costs about 30 min of hold (≈ $0.8), and the box then self-destroys. |
| R7 | The store's `repo_info` sibling list is **truncated at 100,000** (sorted; it ends at `runs/20261026-pack4-…`). hub 2.x lists the tree, so the boxes are fine. The refsweep files are inside the list. | `api/datasets/…/revision/main` [M] | To collect results, use the paginated tree API, not `siblings`. |
| R8 | Cost spread: host speed, a slow container start, price moves, Max-Q. | §5 | Offer rule and stop rule. Check `ops/vast.sh show` at about 4 h; never cut a box that is still making progress. |
| R9 | **Credit margin**: $33.98 against a bad case of about $29. | | If the credit nears $0, Vast may stop instances before they push [H]. Watch the credit. |
| R10 | GT-derived scores are computed on the box: `score_sim.py` and `score_registered.py` against mocap (SPLIT=public), after inference. | `hard_ab_ep*.log`, summary `auc` [M] | Allowed by CLAUDE.md (scoring after inference). Not part of the test-A label; keep them out of the label analysis. |
| R11 | Misleading log line: `reference: … (code ee653b38)` prints today's commit, while the reference was built at `ea14fdf` (20 Oct). | | Provenance is the sha256 line in `job.log`. |
| R12 | **Disk per box** [E]. Peak ≈ 70 GB of `DISK=150`: snapshot parts 16.3 GB plus the extracted env (est. 30–45 GB), dataset 1.5 GB, and per training 25 state files (~165 MB each [M, 21 Oct: 44 GB / 266 files]) + 25 policies × 5.1 MB [M] + train.log ~110 MB [M]. | Earlier two-episode boxes on 150 GB ran fine [M]. | Store growth ≈ 0.3 GB per box (state files are not pushed after `.done`). |
| R13 | Render: `view_policy.py` runs once per episode. It is part of the recipe, adds a few minutes and is not needed by test A. | | Keep it (recipe unchanged). |
| R14 | Clocks: the container clock and the work-log stamps differ by about 3.5 h. | | Run ids use `date -u` at launch. |

## 7. Decisions needed before launch (record in the work log before any result)

- **D1, assets:** train and evaluate on the assets the references name (the organisers' public scans). This is
  recommended, because it is what the gate scored and what C/C2 replayed. Also correct the plan text "library_v3
  meshes" to "LIB=library_v3 set, but unused by these references". The alternative is to rebuild the references on
  library_v3 and re-score the gate on them: a different test, new pre-registration.
- **D2, label rollout:** the label rollout is `results/hard_ab/ep<N>/s-s42/r1/episode_<E6>.parquet`, the one fresh
  official draw of the checkpoint the recipe chose. The selection draws in `results/perc2s/…` are not used. If the
  owner wants exactly one evaluator call per policy, the recipe must change, because `CK_SWEEP` is hard-coded in
  `hard_ab.sh`.
- **D3, evaluator:** accept the training box's `evaluate_policy.py` (patched tree) as the "official evaluator", on
  the basis of the 3 Nov gap test.
- Plus the owner's go-ahead for about $21–27 (cap $30).

## 8. Files

- `JOBS.txt`: launch commands.
- `jobs/`: `gA1.job` … `gA4.job`, `SHA256SUMS`, `make_jobs.sh`.
- `dryrun/gA1` … `gA4`: per-box evidence.
  - logs: `run_job.log`, `job.log`, `prepull.log`, `hard_ab_ep*.log`, `onstart.log`, `fetch_data.log`;
  - calls: `vast_calls.log`, `hf_calls.log`, `hf_uploads.log`, `fc_python_calls.log`, `train_calls.jsonl`,
    `eval_calls.jsonl`;
  - training: `train_call_ep*.json`, `compose_ep*.yaml`;
  - store and tree: `fakestore_files.tsv`, `content_tree.txt`, `results_hard_ab/`, `results_pipeline/`;
  - checks: `qa_ref_ep*.json`, `flashchord_patched_files.txt`, `v2d_env.txt` (fake instance key), `box_commit.txt`.
- `dryrun/stall/`: the watchdog stall test.
- `dryrun/envcheck/`: the CPU training-environment build, 8 episodes.
- `dryrun/harness/`: sandbox scripts and stubs (dry-run only; never for a box).
- `dryrun/ref_sha256.json`: the 8 reference parquets' sha256 and store paths.
- The stub's schema template was the store rollout `runs/20261024-ev3-2c1e4dd/results/final/ep12/episode_000012.parquet`
  (not copied).
