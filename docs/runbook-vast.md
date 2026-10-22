# Runbook: running on Vast.ai so the paid clock only covers real work

Written 2026-10-20. Every script named here is in the repo. They are **written but not yet run on Vast**, except
`ops/vast.sh offers`, which was tested against the live public market. Box 0 and box 1 below are the tests.

## 1. Are we ready?

**Ready (checked today, off the clock):**
- **Dataset size and access.** The whole Track 3 dataset is **1.47 GB**: 20 public and 20 eval episodes with 3 cameras
  each, parquets, meshes, URDFs and calibration. It is public on Hugging Face, so a box fetches all of it in about a
  minute with no token.
- **Image.** `vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16` matches the validated Colab runtime
  (torch 2.11+cu130, Python 3.13). It ships nvcc but not the CUDA library headers; `setup.sh` now installs those.
- **Resume.** FlashCHORD at the evaluator pin can resume. It writes `policy_<step>` and `state_<step>` every
  10,000,384 env steps (about 3.7 min; the Sharpa recipe overrides the 5M default, note 23) and accepts `training.resume=true training.checkpoint_path=<state file>`; the replay buffer is
  not saved by default. `pipeline_ep.sh` now resumes on its own, so interruptible (cheaper) machines are workable.
- **Vast API.** Endpoints and fields come from the API reference:
  - create: `PUT /api/v0/asks/{offer}/` with `image`, `disk`, `env`, `onstart` (≤ 4048 characters), `label`, `price`;
  - list: `GET /api/v1/instances`;
  - logs: `PUT /api/v0/instances/request_logs/{id}/`;
  - label: `PUT /api/v0/instances/{id}/`;
  - destroy: `DELETE /api/v0/instances/{id}/`;
  - SSH keys: `POST /api/v0/ssh/`.
- **Scripts.** Launch, bootstrap, save, watchdog, self-destroy, environment snapshot and restore, data fetch, the
  mocap oracle and the day-1 job. Section 4 shows the flow.

**Unverified until box 0 or box 1 runs:**
- SSH from the Claude cloud session to a Vast box.
- Injection of account-level env vars.
- Whether the instance key `CONTAINER_API_KEY` may set the label and destroy its own instance.
- HF uploads from the box.
- `setup.sh` on the Vast image.
- Throughput of the WS card against the Server Edition we measured.
- Two trainings on one GPU.
- Whether resumed training scores the same as uninterrupted training.

**Not written yet (not needed for day 1):**
- Perception input for eval episodes. They have videos only, no parquet, so object names must come from the kit's
  `track_3_evaluation_objects.json`.
- The submission packing job around the kit's `pack_submission.py`.
- Spoon tracking.

## 2. Where everything lives

| What | Source | On the box | Kept long-term in |
|---|---|---|---|
| Track 3 dataset (1.47 GB) | HF `nvidia/video_to_data_challenge`, public | `/content/t3/…` via `pipeline/fetch_data.sh` | nowhere; refetched per box |
| Wooden-spoon model | `spoon/` in this repo | `/content/t3/mesh/wooden_spoon`, `/content/t3/urdf/` | git |
| Our code | GitHub `aebatirel/v2d-track3`, at one commit per run | `/content/v2d-track3` | git |
| NVIDIA code (pin `8c778f90`) + LFS assets, kit | GitHub, nvidia-isaac.github.io | `/content/v2d`, `/content/kit` | env snapshot |
| Weights: FoundationStereo, FoundationPose | Google Drive (authors) | `/content/Foundation*/…` | HF store `weights/` (mirror, first box) |
| Weights: SAM2, DINOv2-L, MediaPipe hand model | Meta CDN, torch hub, Google storage | `/content/ckpt`, `~/.cache/torch/hub` | env snapshot |
| Built environment (venvs, compiled extensions) | `pipeline/setup.sh` | `/workspace/*`, `/venv/main`, `/.uv` | HF store `env/<name>/` |
| Depth caches (about 0.3–0.6 GB per episode) | FoundationStereo | `/content/perc2/epN/` | HF store `cache/depth/` |
| Run outputs (logs, poses, references, latest policy/state, eval) | jobs | `/content/{perc2,oracle,refs,runs,results}` | HF store `runs/<run_id>/` |
| Scores, summaries, decisions | the agent | — | git (STATUS.md, work log) |

- **Paths.** The scripts use `/content`, as on Colab. On Vast `/content` is a symlink to `/workspace`.
- **The HF store** is one **private Hugging Face dataset repo** (`HF_STORE`, set in `ops/config.env`); the free tier
  includes 100 GB of private storage. Estimated budget (not measured):
  - environment snapshot: 20–35 GB;
  - weights: about 4 GB;
  - depth for all 40 episodes: about 18 GB;
  - runs: a few GB.
- **Commit rate.** HF limits commits to about 100–128 per hour per repo (unofficial figure), so boxes push in batches:
  one commit per push, every 30 min and at the end.
- **Boxes never push to git.** The agent reads results from the store (or over SSH) and commits the summaries. This
  keeps write credentials off third-party machines and avoids push races between 10+ boxes.

## 3. Keys: where each one goes

Vast hosts are third parties who could read a container's env or disk. Boxes therefore get only **narrow, expiring**
tokens and never the Vast account key.

| Secret | Scope | Where it goes | Who sets it |
|---|---|---|---|
| Vast API key (**new**; the one pasted in chat is exposed) | account | Claude cloud environment → **network secret**, host `console.vast.ai`, header `Authorization: Bearer <key>` | owner |
| HF token "v2d-agent" | fine-grained, **read** on the store repo | Claude cloud environment → network secret, host `huggingface.co`, same header | owner |
| HF token "v2d-box" | fine-grained, **write** on the store repo only | Vast → Account → Environment Variables: `HF_TOKEN` (injected into every instance) | owner |
| GitHub PAT "v2d-box" | fine-grained, `aebatirel/v2d-track3` only, Contents **read-only**, expires ~2026-11-30 | Vast → Account → Environment Variables: `GH_TOKEN` | owner |
| GitHub push from the agent | Claude GitHub App on `aebatirel/v2d-track3` | installed once on the repo | owner |
| SSH key of the cloud agent | per session | generated in the session, registered with `ops/vast.sh ssh-key` | agent |
| `CONTAINER_API_KEY`, `CONTAINER_ID` | that one instance | added by Vast automatically; used for the label and self-destroy | Vast |

- The Mac key `~/.ssh/v2d_gpu` stays on the Mac. It is used only if a session runs from the Mac.
- Plain environment variables in the cloud environment hold **no** secrets. Non-secret settings live in
  `ops/config.env`.
- **If the HF network secret does not work for `hf download`:**
  1. read results over SSH; or
  2. put the read-only "v2d-agent" token in the cloud environment as `HF_TOKEN`. It is low risk: read-only, one repo.
- The **prepaid Vast credit is the real hard cap**. At the start, keep about $25–50 on the account and leave
  auto-top-up off.

### Owner checklist (once, before box 0)
1. **Vast:**
   - regenerate the API key and delete the old one;
   - top up about $25–50;
   - add `HF_TOKEN` (v2d-box) and `GH_TOKEN` under Account → Environment Variables.
2. **Hugging Face:**
   - create a private **dataset** repo named `v2d-store`;
   - create the two fine-grained tokens above;
   - tell the agent the HF username, so it can set `HF_STORE` in `ops/config.env`.
3. **GitHub:**
   - create the read-only fine-grained PAT;
   - install the Claude GitHub App on `aebatirel/v2d-track3`.
4. **Claude Code cloud environment:**
   - set network access to **Full**, needed for SSH to changing Vast IPs and for the HF/CDN hosts;
   - add the two network secrets.
5. Give the go-ahead for the day-1 batch (section 5).

## 4. How one run flows

```
agent (cloud session)                         Vast box (image vastai/pytorch …py313)
ops/vast.sh create <offer> <run_id> '<job>' ─▶ onstart.sh (inline, ≤ 4 KB)
   env: RUN_ID V2D_COMMIT JOB_B64 V2D_IMAGE      writes /etc/v2d_env, /content → /workspace,
        [HF_STORE ENV_SNAPSHOT SETUP RESUME_FROM] clones the repo at V2D_COMMIT with GH_TOKEN
                                                 (clone fails → label + self-destroy after 20 min)
                                              run_job.sh
                                                 watchdog.sh in the background
                                                 setup: restore env snapshot from HF, else setup.sh (~20–30 min)
                                                 fetch_data.sh (1.5 GB)
                                                 [RESUME_FROM → pull that run's outputs; finished stages skip]
                                                 job  (label "job running"; push-run every 30 min)
                                                 push-run → HF store runs/<run_id>/
                                                 self-destroy (DELETE with CONTAINER_API_KEY)
ops/vast.sh show / logs / ssh; HF store  ◀──── labels, logs, pushed results
```

- **Stall watchdog (CLAUDE.md).** There is no time limit. The watchdog destroys the box only after **30 min without
  progress**, after saving what exists. Progress means:
  - a new or changed file under the output paths; or
  - GPU utilisation ≥ 10 %.

  Training prints progress at every 1 % (about once a minute) and saves every 10M steps, so a healthy job is never
  idle for that long.
- **HOLD.** `echo $(( $(date +%s) + 3600 )) > /content/HOLD` (sent over SSH) keeps the box for an hour after its job
  ends, for debugging. The watchdog destroys it when HOLD expires.
- **If a push fails,** the box waits 60 min for the agent, then destroys anyway.
- **If a destroy fails,** the label reads `DESTROY-FAILED` and the agent destroys the box from its session.
- **The agent's own guard:** whenever it wakes, it runs `ops/vast.sh show` and destroys anything idle or orphaned.

## 5. Day 1: the first batch to approve

Prices are from the live market on 2026-10-20 and move hourly. Cheapest compliant verified offers:
- RTX PRO 6000 WS on demand: **$1.45–1.65/h** all-in with 150 GB disk;
- RTX PRO 6000 WS interruptible (minimum bid): **$0.54/h**, Texas;
- any GPU (for the plumbing test): **$0.10/h**.

| Step | Box | What | Time | Cost |
|---|---|---|---|---|
| 0 | none | Cloud session: `git pull`; generate an SSH key and `ops/vast.sh ssh-key`; `ops/vast.sh show` (tests the API key header) | 5 min | $0 |
| 1 | **box 0**, cheapest GPU, `SETUP=none DISK=40` | `ops/jobs/smoke.sh`: env injection, clone, HF read speed, HF write, label; SSH test during its 8-min hold; then self-destroy (the destroy test) | ~15 min | ~$0.03 |
| 2 | **box 1**, PRO 6000 WS on demand | `ops/jobs/day1.sh`, five stages: (1) full setup and weight mirror; (2) perc2 on ep 12; (3) env snapshot to HF; (4) resume test (15M steps, killed at 10M, rerun); (5) **two 250M trainings at once** (ep 12 with perception objects, and with the mocap oracle) → official evaluator → `score_sim.py` | 4–5 h | ~$6–8 |
| 3 | **boxes 2–3**, PRO 6000, from the snapshot (optional, once step 2's snapshot is uploaded) | `pipeline_ep.sh 22`, `pipeline_ep.sh 27` | ~2.5 h each, in parallel | ~$7 |

**Expected cost of the batch: about $14–16, ceiling $25.** Step 2 is the first real end-to-end score. Step 2's oracle
run shows how much is lost in the robot and simulator, and how much in tracking.

Clock-time estimates on box 1 (not measured on Vast):
- image pull: 2–5 min;
- setup: 20–30 min;
- perception: about 10 min;
- resume test: about 15 min;
- two concurrent trainings: 2–3.5 h;
- evaluation and scoring: about 10 min;
- push: about 5 min.

### Exact commands (cloud session, repo root)
```bash
ssh-keygen -t ed25519 -N '' -f ~/.ssh/v2d_cloud -C v2d-cloud && ops/vast.sh ssh-key ~/.ssh/v2d_cloud.pub
ops/vast.sh show                                   # expect "0 instance(s)"; an auth error means the secret is wrong
C=$(git rev-parse --short origin/main)

ops/vast.sh offers any                             # box 0
SETUP=none DISK=40 ops/vast.sh create <offer> $(date -u +%Y%m%d)-smoke-$C 'bash ops/jobs/smoke.sh'
ops/vast.sh show                                   # label, ssh host/port
ssh -i ~/.ssh/v2d_cloud -o BatchMode=yes -o StrictHostKeyChecking=accept-new -p <port> root@<host> 'tail -20 /workspace/run_job.log'

ops/vast.sh offers                                 # box 1: RTX PRO 6000 WS on demand
ops/vast.sh create <offer> $(date -u +%Y%m%d)-day1-$C 'bash ops/jobs/day1.sh'

ENV_SNAPSHOT=pt2.11-cu130-py313-<yyyymmdd> ops/vast.sh create <offer> <date>-e2e-ep22-$C 'bash pipeline/pipeline_ep.sh 22'
```
Run IDs follow `<yyyymmdd>-<what>-<commit7>`. Record every launch, with offer, price, run ID and outcome, in
`docs/work-log.md`.

## 6. Monitoring
- `ops/vast.sh show`: each box sets its label to its current stage (`setup`, `job running`, `day1: two trainings ep12`,
  `saving, then destroy: …`).
- `ops/vast.sh logs <id>`: the container log.
- SSH, if step 1 shows it works from the cloud: `tail -f /workspace/run_job.log /content/job.log`, and the
  `train.log` files under `/content/runs/…`.
- HF store `runs/<run_id>/`, pushed every 30 min and at the end. It holds logs, `run_state/` and results.
- The cloud session pauses when idle and does not run background loops. Boxes therefore never depend on the agent;
  the agent checks in when the conversation resumes.

## 7. Failure playbook

| Symptom | Likely cause | Action |
|---|---|---|
| `ops/vast.sh show` gives 401/403 | network secret host or header wrong | fix the secret; test with `VAST_API_KEY` exported locally on the Mac |
| Label `CLONE-FAIL` / `CHECKOUT-FAIL` | `GH_TOKEN` missing or expired; commit not pushed | push the commit; fix the token; the box self-destroys after 20 min |
| `setup.log` has `*-FAIL` | install broke (headers, pip, gdown quota) | SSH in with HOLD, fix, then patch `setup.sh` and commit; if Google Drive refuses, use the HF weight mirror |
| `CUDADEV-FAIL` | apt package name differs on the image | switch to `pytorch/pytorch:2.11.0-cuda13.0-cudnn9-devel` (full toolkit, 11.7 GB) via `IMAGE=` |
| OOM with two trainings | 2 × 40.5 GB peak plus perception | run one training per GPU; record it |
| Label `stalled …` | the job hung | read the pushed logs; never relaunch unchanged |
| Label `PUSH-FAILED` | HF token or store repo | fix it within 60 min (set HOLD over SSH), or accept the loss |
| Label `DESTROY-FAILED` | instance key lacks permission | `ops/vast.sh destroy <id>` from the agent; fall back to agent-side destroys |
| Interruptible box stopped | outbid or preempted | destroy it; relaunch elsewhere with `RESUME_FROM=<run_id>` (training resumes from the last pushed `state_` file) |

## 8. After day 1: scaling out
- **Before any eval-episode run:**
  - finish the eval-mode perception input (object names from the kit JSON; no parquet);
  - write the packing job;
  - commit the exact code (provenance: every submission row references a commit).
- **Twenty eval trainings, one per box:**
  - use interruptible PRO 6000s if the resume test passed and resumed scores match, otherwise on demand;
  - start them from the environment snapshot;
  - estimated cost: about $10–25 for all 20 on interruptibles, or about $35–50 on demand.
- **Get the owner's go-ahead** with a cost estimate before each batch.

## 9. Sources
- Vast API reference: [create instance](https://docs.vast.ai/api-reference/instances/create-instance),
  [destroy](https://docs.vast.ai/api-reference/instances/destroy-instance),
  [logs](https://docs.vast.ai/api-reference/instances/show-logs),
  [manage/label](https://docs.vast.ai/api-reference/instances/manage-instance),
  [attach SSH key](https://docs.vast.ai/api-reference/instances/attach-ssh-key),
  [account env vars](https://docs.vast.ai/cli/reference/create-env-var),
  [instance env vars](https://docs.vast.ai/guides/instances/docker-environment).
- HF: [storage limits](https://huggingface.co/docs/hub/en/storage-limits),
  [rate limits](https://huggingface.co/docs/hub/en/rate-limits).
- FlashCHORD resume: `robotic_grounding/flash_chord/src/flash_chord/training/flash_sac/{config,runner,checkpoint}.py`
  at pin `8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef` (`CheckpointConfig.save_interval_environment_steps = 5_000_000`,
  `TrainingConfig.resume`, `checkpoint_path`).
- Image contents: the Docker Hub config history of `vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16`
  (base `vastai/base-image:cuda-13.2-mini-py313`, apt `cuda-nvcc-13-2` without the `-dev` library packages).
