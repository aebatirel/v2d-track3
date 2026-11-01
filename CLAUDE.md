# Working rules for this repository

These carry over the rules the owner set while this work ran locally. Follow them unless the owner says otherwise.

## Resume and hand off
- Start every session by reading `STATUS.md`, then this file.
- After each meaningful result, decision, failed experiment or change of direction, update `STATUS.md` and append a
  dated entry to `docs/work-log.md`. Do not let more than about ten minutes of new state go unsaved, and save before
  long runs. Abrupt termination gives no chance for a final save.
- Commit and push to `origin` regularly. This repository is the durable store; the GPU machines are disposable.
- Record for every run: exact command, machine, output paths, the code version (commit) and the result, including
  failures.

## Talking to the owner
- Give times to the owner in Turkish time (TRT, UTC+3), e.g. "01:30 TRT" (owner, 31 Oct 2026). Logs and ledger may stay
  in UTC; say which zone a time is in.

## Experimental integrity
- Inference must never read ground truth: mocap poses, the `pose` field of `observation.objects` in the public episode
  parquets, or anything derived from them. Ground truth is read only by scoring and diagnostics, after inference.
  Object names and slot order from the episode are allowed (the kit provides them for eval episodes too).
- Keep public-episode development and eval-episode inference separate. Never tune on eval results.
- Preserve existing runs and failed experiments; add new versions instead of overwriting.
- Report accuracy, failures and cost together. Distinguish measured numbers from estimates and guesses.
- Before choosing a fix for a new technical blocker, look at the measured evidence and do a focused literature and
  open-source review: primary papers, author repositories, official docs. Label new ideas as hypotheses and
  name the experiment that would falsify them.

## Spending
- The owner set no hard spending cap. Before each rental batch, state the plan and its expected cost and get the
  owner's go-ahead. Then rent through the Vast API (`VAST_API_KEY` secret).
- Every machine destroys itself when its job finishes. There is **no fixed time limit**: never cut a job that is
  still making progress. A stall watchdog destroys a machine only when its job has stopped making progress (no new
  log lines or checkpoints for ~30 minutes), after saving what exists.
- Pay only while working: destroy instances at the end of a work block or before any idle gap over ~30 minutes.
  A stopped Vast instance keeps billing storage. Copy results off (git, backup) before destroying.
- Never commit secrets (SSH private keys, API keys, tokens). Keep keys in the environment or the provider's key store.

## Code and data
- Git holds code, results and small artifacts: scores, summaries, logs, final policy checkpoints up to ~10 MB each.
- Keep large or regenerable data out of git: the dataset and videos, depth caches, model weights, and bulk or
  intermediate checkpoints (see `.gitignore`).
  - GPU machines download the public dataset and weights with the setup scripts.
  - Large artifacts worth keeping go to the HF store, not git. The store is a private Hugging Face dataset repo
    (`HF_STORE` in `ops/config.env`; proposed 2026-10-20, active once the owner creates it). See
    `docs/runbook-vast.md`.
  - GPU boxes write only to the HF store, never to git. The agent commits summaries and scores.
  - Reasons: GitHub rejects files over 100 MB, binaries bloat the history forever, and every cloud session clones the
    whole repo.
- Each submission must reference a commit of the repo shared with the organisers (this one or a cleaned copy), so
  commit the exact code used for every submitted run.
