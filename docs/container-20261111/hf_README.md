---
tags:
- robotics
- reproducibility
- v2d-challenge
---

# Imitation.Tech: NVIDIA V2D Challenge Track 3 verification container (pack 13h)

This is the Docker image archive for the organisers' container check of our counted Track 3 submission, pack 13h.
The same file counts on all six Track 3 boards.

## Files

| File | Size | sha256 |
|---|---|---|
| `Imitation.Tech-v2d-submission.tar.zst` | 9,633,255,804 bytes | `d76096b195d797a5b18654da19eed7f3f4f39a78e44e3076480369f0622f1b36` |
| `Imitation.Tech-v2d-submission.tar.zst.sha256` | | checksum file for `sha256sum -c` |

- Image: `imitation.tech-v2d-submission:final`.
- Image ID: `sha256:f314c838218416fc2fb625ab1fc1f38267ecad3e3dd68be01763581dade8b3ae`.
- OCI manifest digest: `sha256:82aa29cfa722fbd2eb10bc2728b698f7c21613cdb4495e03f999c3171c4139c3`.
- 19.3 GB once loaded.

## Load and run

```bash
sha256sum -c Imitation.Tech-v2d-submission.tar.zst.sha256
zstd -dc Imitation.Tech-v2d-submission.tar.zst | docker load     # needs ~40 GB free disk while loading
IMAGE=imitation.tech-v2d-submission:final

# hashes, commit and re-pack of the stored rollouts (no GPU, no network, no dataset needed for Track 3)
docker run --rm --network none $IMAGE /submission/run.sh verify

# roll out all 20 policies with the evaluator and pack a new file (GPU)
docker run --rm --gpus all --network none -v "$PWD/out:/output" $IMAGE \
    /submission/run.sh reproduce --label track3_13h --output /output --parallel 4
docker run --rm --network none -v "$PWD/out:/output" $IMAGE \
    /submission/run.sh verify --reproduced track3_13h=/output/track3_13h/track3_submission.parquet
```

`/submission/README.md` inside the image describes the contents, and how `reproduce` differs from the kit example.

## Counted submission

| Board | Kaggle submission ID | Score |
|---|---|---|
| AUC (`add_auc`) | 57925185 | 0.88001 |
| SP-SR (`spider_sr`) | 57925189 | 0.90 |
| MP-SR (`maniptrans_sr`) | 57925196 | 0.80 |
| RPE (`rpe_cm`) | 57925202 | 2.28085 |
| MPPE (`mppe_cm`) | 57925211 | 1.85258 |
| CD-O (`cd_o_cm`) | 57925216 | 0.25159 |

- Code: https://github.com/aebatirel/v2d-track3/commit/9610329e1177921827a9b66e38103e746efd8a0c
- Technical report: https://github.com/aebatirel/v2d-track3/blob/7ded292fd74c4f5f26c1a055d3cd431015ac5e7d/docs/paper-arxiv-20261106/main.pdf
- Build record, with the Dockerfile, the logs and every command: https://github.com/aebatirel/v2d-track3/tree/7ded292fd74c4f5f26c1a055d3cd431015ac5e7d/docs/container-20261111

## Checks we ran (11 Nov 2026)

- `run.sh verify --network none`: 11 of 11 checks pass:
  - commit and clean tree;
  - provenance;
  - packer, uploader, evaluator script and evaluator code hashes;
  - all 20 checkpoints;
  - re-packing the stored rollouts gives a byte-identical file.
- `verify --kaggle`: all six Kaggle copies match.
- `reproduce` on one RTX PRO 6000 GPU (same base image and runtime): 20 episodes in 5.5 minutes.
  `verify --reproduced` then passed 13 of 13 checks: same rows and provenance; object positions differ from the
  upload by a median of 0.55 cm (95th percentile 2.67 cm).

## Disclosures carried by 13h

- **Mesh selection.** Some packed meshes were chosen by their score against the public object scans. No eval-episode
  ground truth or leaderboard input was used.
- **Eval 10.** Its policy was trained with `sim.njmax` 1024 and evaluated with the stock limits saved in its
  checkpoint (512 / 256), through a header-only edit of the saved config.
- **Eval 15.** It is packed under the team owner's waiver of one pre-registered swap clause.
