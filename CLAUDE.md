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

## Spending and accounts
- The owner set no hard spending cap. Before each rental batch, state the plan and its expected cost and get the
  owner's go-ahead. Then rent through the Vast API (`VAST_API_KEY` secret), and give every machine:
  - a self-destroy at the end of its job;
  - a hard time limit as a safety net.

  Pay only while working: destroy instances at the end of a work block or before any idle gap over ~30 minutes.
  A stopped Vast instance keeps billing storage. Copy results off (git, backup) before destroying.
- Never commit secrets (SSH private keys, API keys, tokens). Keep keys in the environment or the provider's key store.
- The owner does all account actions: sign-ups, payments, challenge registration, accepting Kaggle rules, uploading
  submissions, and emailing the organisers. Prepare files and drafts for them.
- Downloads on rented GPU or cloud machines (dataset, model weights, Python packages the pipeline needs) are fine.
  Ask before installing anything on the owner's personal computer.

## Code
- Clean-room: write our own code. Do not copy code from the owner's older SlamDunk project.
- Never commit data, videos, depth caches, checkpoints or other large outputs (see `.gitignore`).
- Submissions must reference a commit of this repository shared with the organisers' GitHub account, so commit the
  exact code used for every submitted run.
