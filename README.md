# v2d-track3

Our entry for **NVIDIA V2D Challenge, Track 3**: head-camera video of a person handling objects → a trained robot
policy per episode (two simulated Sharpa hands in NVIDIA's FlashCHORD simulator) → the official evaluator's simulated
object trajectories → scored against motion capture on Kaggle. Leaderboard freeze: **2026-11-04 17:00 EST**.

This repository holds our code, research notes and status. The dataset, NVIDIA's code and kit, model
weights and run outputs are downloaded or produced by scripts and are git-ignored.

**Start here:** read [`STATUS.md`](STATUS.md) for where things stand and what to do next, then [`CLAUDE.md`](CLAUDE.md)
for the working rules.

## Layout

| Path | What it is |
|---|---|
| `STATUS.md` | Current state, results, gotchas, next actions. Keep it current. |
| `CLAUDE.md` | Working rules for any agent continuing this work. |
| `docs/runbook-vast.md` | **How to run on Vast.ai:** readiness, where data and keys live, the run flow, the day-1 batch, the failure playbook. |
| `ops/` | Vast control (`vast.sh`, `config.env`), box scripts (`box/`: on-start, bootstrap, HF store, watchdog, self-destroy) and jobs (`jobs/`). Written, not yet run on Vast. |
| `pipeline/setup.sh` | One-shot machine setup (FlashCHORD venv at the evaluator pin, hand venvs, kit, SAM2, DINOv2, FoundationStereo, FoundationPose; calls `fetch_data.sh`). |
| `pipeline/fetch_data.sh` | Fetches the whole Track 3 dataset (1.47 GB) into the `/content/t3` layout, plus the spoon model. |
| `pipeline/oracle_poses.py` | Evaluation-only oracle: mocap object poses on perc2's camera track (public episodes only). |
| `pipeline/perc2.py` | **Validated perception** (mean AUC 0.809 on 20 public episodes): stereo depth → scan-matching detection → FoundationPose tracking → visual odometry → kit metrics. |
| `pipeline/perc.py` | perc4 = perc2 + render-and-compare detection check + reworked visual odometry. Built, **not validated**. |
| `pipeline/diag.py`, `summ.py` | Per-frame error diagnostics with overlay montage; batch summary table. |
| `pipeline/hands_mp.py` | MediaPipe hands on the colour camera, lifted to 3-D with stereo depth. Written, not run. |
| `pipeline/mkref.py` | Builds the FlashCHORD reference (table frame, Sharpa IK via NVIDIA's unchanged retargeter, contacts, validation). Written, not run. |
| `pipeline/score_sim.py` | Scores an official-evaluator rollout of a public episode against mocap. Written, not run. |
| `pipeline/pipeline_ep.sh` | One episode end to end: perception (`PERC=perc2`, `perc4` or `oracle`) → hands → reference → train (auto-resume) → evaluate → score. Written, not run. |
| `pipeline/run_public.sh` | Fetches all 20 public episodes and runs perception on each. |
| `pipeline/README_ref.md` | Exact commands and conventions for the reference / train / evaluate steps. |
| `pipeline/archive/` | Superseded experiments (OWLv2 text-prompt detector, first single-episode script). |
| `spoon/` | Parametric wooden-spoon model (no public scan exists), frame-convention analysis, fitting skeleton. |
| `notebooks/` | Plain-language explained notebook of the Colab experiments, plus its builder. |
| `docs/research/` | 22 research notes (`notes/`), the Track 3 requirements digest, and supporting scripts. Notes cite paths as `reports/v2d-challenge/research/...`, which map to `docs/research/notes/...` here. |
| `docs/research/work/` | Scripts, logs and text outputs of the research rounds (folders 11–20 match notes 11–20; `-verify` folders are the independent checks). Binaries and third-party copies were left out. |
| `docs/professor-package/` | The summary package sent to the professor. |
| `docs/gpu-rental/` | Research on the cheapest GPU rental (report, notes, live Vast market snapshot). |
| `docs/context-and-decisions.md` | The owner's goals, preferences and decisions from the original chats. Read this too. |
| `docs/work-log.md` | Dated chronological log of the work so far (from the original handoff file). |

## Running on a rented GPU (Vast.ai)

Follow [`docs/runbook-vast.md`](docs/runbook-vast.md). `ops/vast.sh create` starts a box that sets itself up, runs one
job, saves to the HF store and destroys itself. The scripts use `/content` as their root, as on Colab; on Vast,
`/content` is a symlink to `/workspace`. To set up a box by hand (root user):

```bash
ln -s /workspace /content
git clone https://github.com/aebatirel/v2d-track3.git /workspace/v2d-track3
cp /workspace/v2d-track3/pipeline/setup.sh /content/
DEBIAN_FRONTEND=noninteractive setsid nohup bash /content/setup.sh > /content/setup.log 2>&1 < /dev/null &
grep -aE '[A-Z0-9]+-(OK|FAIL)|DONE' /content/setup.log      # wait for SETUP-DONE (~20-30 min)
```

Requirements: one NVIDIA GPU with ≥ 48 GB (RTX PRO 6000 96 GB recommended), driver ≥ 580 (CUDA 13), ≥ 16 vCPU,
≥ 64 GB RAM, ~200 GB disk. See `STATUS.md` for the GPU plan and costs.

## Links (private to the owner unless shared)

- Explained Colab notebook: https://colab.research.google.com/drive/1rSlDlcC91UggWeCsDS0H8KFrp_C6ygX5
- Visual explainer page: https://claude.ai/artifact/GJegn8ZZHnb7PFDTnCDpgd
- Challenge: https://nvidia-isaac.github.io/video_to_data/v2d_challenge/
- Dataset: https://huggingface.co/datasets/nvidia/video_to_data_challenge (track_3)
- NVIDIA code (evaluator pin `8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef`): https://github.com/nvidia-isaac/video_to_data
