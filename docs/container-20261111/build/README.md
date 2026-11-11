# Imitation.Tech: V2D Challenge Track 3 submission container (pack 13h)

This container reproduces our counted Track 3 submission, pack 13h. The same file counts on all six Track 3 boards.

| Board | Kaggle submission ID | Public score |
|---|---|---|
| AUC (`add_auc`) | 57925185 | 0.88001 |
| SP-SR (`spider_sr`) | 57925189 | 0.90000 |
| MP-SR (`maniptrans_sr`) | 57925196 | 0.80000 |
| RPE (`rpe_cm`) | 57925202 | 2.28085 |
| MPPE (`mppe_cm`) | 57925211 | 1.85258 |
| CD-O (`cd_o_cm`) | 57925216 | 0.25159 |

- Uploaded file: `submitted/track3_submission.parquet` (sha256 `d917b0022336d5c9b7037052df32949705a9fc0e3199aab36a6760c794ae5a4e`).
- The CD-O board received `submitted/track3_submission.cd-o.parquet`, which the kit's uploader derives from the main file.
- Upload receipt: `submitted/track3_submission.parquet.kaggle-receipt.json`.
- Code: https://github.com/aebatirel/v2d-track3/commit/9610329e1177921827a9b66e38103e746efd8a0c, checked out in `code/`.

## Commands

```bash
# hashes, commit and re-pack of the stored rollouts (no GPU, no network, no dataset needed for Track 3)
docker run --rm --network none IMAGE /submission/run.sh verify

# roll out all 20 policies with the evaluator and pack a new file (GPU; Track 3 needs no dataset)
docker run --rm --gpus all --network none -v "$PWD/out:/output" IMAGE \
    /submission/run.sh reproduce --label track3_13h --output /output --parallel 4
docker run --rm --network none -v "$PWD/out:/output" IMAGE \
    /submission/run.sh verify --reproduced track3_13h=/output/track3_13h/track3_submission.parquet
```

`--dataset-root /data` is accepted, but Track 3 does not read the dataset: the evaluator reads only the per-episode
inputs shipped here, and the packer reads only the rollouts, the meshes and the kit's own data files.

## What is inside

| Path | Contents |
|---|---|
| `submission.json` | The counted submission and what it was made from (`label` `track3_13h`). |
| `run.sh` | Entry point, from the kit's `examples/container/run.sh` (changes listed below). |
| `code/` | Our repository at the recorded commit, with `.git`, no modified tracked files. |
| `kit/` | The kit copy that packed and uploaded 13h (packer `49b13052…`, uploader `d31d4a7c…`, evaluator script `160d24f5…`). |
| `verifier_kit/` | The current kit (differs from `kit/` only in `requirements.txt`). |
| `weights/track3_13h/` | The 20 evaluated policy checkpoints, byte copies (sha256 = the file's `checkpoint_sha256`). |
| `outputs/track3_13h/rollouts/` | The 40 evaluator outputs (`episode_XXXXXX.parquet` / `.json`) packed into 13h. |
| `meshes/track3_13h/` | The 36 meshes packed into 13h (`episode_XXXXXX/<object>.glb`). |
| `eval_inputs/track3_13h/` | Per episode, the evaluator inputs: the reference, its support surface and its object URDF closure. |
| `/opt/v2d` | FlashCHORD at the pinned evaluator commit `8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef` with its venv (`.venv`, Python 3.11.17). |
| `/opt/kit-venv` | The kit Python (Python 3.13.16 with the library versions that packed 13h). |
| `/opt/install_runtime.sh` | How `/opt/v2d` and `/opt/kit-venv` were installed (the steps of our evaluation boxes). |

The image is built from `vastai/pytorch:2.11.0-cu130-cuda-13.2-mini-py313-2026-10-16`
(index digest `sha256:77121a430d4243ca661ae26ec3f0c0f03bd45b07679d20e61e4f756ea3104204`, amd64 manifest
`sha256:2edbaecbb5816c3e134abf8c72de9e47ac7dcace88eeb5db8d227ae0c358f2da`), the image of the GPU boxes that ran our
evaluations. Its entry point is cleared, so `docker run IMAGE CMD` runs `CMD`.

## How reproduce differs from the kit example

The evaluator rebuilds each episode from its checkpoint. The saved config names the reference as `/workspace/refs/...`,
and the reference names its object URDFs under `/content/...`: these are the paths of the box that evaluated it. Two
episodes name the same `/content/assets/urdf/white_pot_rigid.urdf` with different contents (eval 1 has carved collision
pieces, eval 28 does not), so the inputs cannot share one tree at the original paths.

`eval_inputs/track3_13h/episode_XXXXXX/assets/` holds the files of one episode:
- `refs/...`: the reference parquet the checkpoint names, at its path below `/workspace/`, with `reconstructed_stage/`;
- `urdf/`, `mesh/`: the object URDFs and their meshes and collision pieces.

All are byte copies of what the evaluating box loaded.

`run.sh reproduce` therefore runs the kit's `examples/run_policy_evaluation.py` once per episode, with
`--source-root` set to that episode's tree. The evaluator option maps `/workspace/<p>` to `<tree>/<p>`. The image has no
`/content`, so FlashCHORD's asset resolver re-roots each `.../assets/urdf/X` onto the reference's own `assets/`
ancestor, which is the episode's tree. The evaluator, its arguments (`--world-count 1`, explicit reset) and the packer
call are as in the kit example.

Other changes:
- `FLASH_CHORD_CACHE_DIR` points the CoACD cache at the output directory, so a non-root user can run it.
- `PYTHONPATH` is the pinned checkout's `src`, as on our boxes.
- After packing, the CD-O companion file is derived the way the kit's uploader derives it.

## Hardware and run time

- `verify` needs no GPU and takes under a minute.
- `reproduce` needs one NVIDIA GPU with a driver for CUDA 13. We used an RTX PRO 6000 Blackwell Workstation Edition
  (96 GB, driver 595.71). Memory use is small: one world per episode, a few GB of GPU memory in all.
- `reproduce` takes about 1 minute per episode, mostly scene build and JIT compilation. On our box (128 CPU cores)
  `--parallel 4` ran all 20 episodes in 5.5 minutes, packing included. Sequentially it takes about 20 to 25 minutes.
- The image is about 19 GB uncompressed (base image 10.2 GB, runtime 8.3 GB, /submission 0.8 GB).

## Expected differences

The simulator is not bitwise deterministic, so reproduced poses differ slightly from the submitted ones, while rows and
provenance are identical. Track 3 ground truth is held out, so the packer cannot score a reproduced file locally. Only a
Kaggle submission scores it. The evaluator's own JSON reports metrics against our reference, which is not the
leaderboard metric.

Our own run on 11 Nov 2026 used the same `/submission` tree and the same `/opt/install_runtime.sh` on a Vast.ai
RTX PRO 6000 box of the same base image. Then `run.sh verify --reproduced` in this image, with no network, gave
13 pass, 0 fail:
- rows and provenance identical;
- object positions vs the submitted file: median 0.55 cm, 95th percentile 2.67 cm;
- the CD-O companion file has the same content as the uploaded one, because CD-O depends only on the packed meshes.

Against our reference, the evaluator's mean ADD-AUC over the 20 episodes was 0.936. The submitted rollouts gave 0.948.
Our stored repeat evaluations of the same 20 checkpoints span 0.904 to 0.950 (2.5 to 97.5 %, one draw per episode).

Eval 30 is bimodal: 4 of 21 stored draws lose the object. Our reproduced draw of eval 30 was one of those.

## Disclosures carried by 13h

These are recorded in the repository under `results/submissions/` on branch `claude/focused-pascal-2nz9s1`:
- **Mesh selection used public-episode ground truth.** Some packed meshes (Tier B / B+ and the G2 pot, blue cup and
  rack) were chosen by score against the public object scans. No eval-episode ground truth or leaderboard input was
  used.
- **Eval 10's policy was trained with `sim.njmax` 1024** and evaluated with the stock limits saved in its checkpoint
  (512 / 256): a header-only edit of the saved config.
- **Eval 15 is packed under the owner's waiver** of one pre-registered swap clause.
