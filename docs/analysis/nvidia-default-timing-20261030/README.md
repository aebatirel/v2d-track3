# How far ahead of NVIDIA's method are we? (2026-10-30)

Owner's question: "how much are we outperforming NVIDIA's methodology? can we get a number".

## Short answer
There is **no measured head-to-head number** for Track 3.
- NVIDIA posts baseline rows on the Track 1 and Track 2 leaderboards, but **none on Track 3**. Source: the live
  leaderboard (`leaderboard-20261030T0851Z.json`, `is_baseline` flag).
- The FAQ says the Track 3 tissue-box example is "not necessarily an optimized baseline".
- We never ran NVIDIA's stock Track 3 chain. As shipped it handles one object and assumes 30 fps (note 01). 13 of
  the 20 public episodes have two objects.

## New measured number: NVIDIA's default timing alone [measured, public episodes]
NVIDIA's default Sharpa recipe uses `motion_speed 0.5`, so the packer silently submits source frame ≈ 0.508 f at frame
f (note 06, case A). Assume perfect perception and a perfect robot, apply only that timing, and score with the kit's
Track 3 functions on all 20 public episodes:

| | AUC | SP-SR | MP-SR | MPPE |
|---|---|---|---|---|
| NVIDIA default timing, everything else perfect | **0.415** | 0.30 | 0.00 | 9.5 cm |
| "Nothing moves" floor | 0.446 | 0.45 | 0.00 | 9.3 cm |

- The floor matches the value logged on 12 Oct (0.446 / 0.45 / 9.3 cm), so the scoring code checks out.
- So the chain as shipped is capped **below the nothing-moves floor**, whatever its perception does.
- This is a **ceiling for unmodified defaults**, not a score for the method with the timing fixed. That needs a GPU
  run.
- Per-episode values are in `timing_ceiling.json`.

## Indicative only (different track, episodes and inputs)
NVIDIA's own posted baselines on Track 2 use the same metric family:

| Track 2 board | NVIDIA baseline | AUC | SP-SR | MP-SR | MPPE |
|---|---|---|---|---|---|
| Tier 1 (multi-view input) | CHORD Baseline | 0.510 | 0.70 | 0.20 | 17.7 cm |
| Tier 3 (bring your own reconstruction) | CHORD Baseline (CARI4D Reconstruction) | 0.002 | 0.00 | 0.00 | 70.2 cm |

Our Track 3 board score is **0.8146** (SP-SR 0.85, MP-SR 0.65, MPPE 2.92 cm), +0.30 AUC over the Tier 1 baseline. The
episodes differ, so this is not a measurement against us.

## What a real number would take (not run; needs the owner's go-ahead)
1. **Ask the organisers** whether a Track 3 baseline score exists. Free.
2. **Run a "minimally fixed NVIDIA chain" on public episodes**: their monocular reconstruction, retargeter and default
   recipe, changing only what it needs to run (timing, a loop over objects). Then score it next to our pipeline on the
   same episodes. Rough cost:
   - about 2–2.5 GPU-h per episode: their reconstruction ~10–15 min per segment, plus a 250M-step training of
     ~1.5–2 h;
   - so ≈ $15–20 for the 7 single-object public episodes, or ≈ $60–70 for all 20 [estimate];
   - plus the work of installing their container pipeline module by module (no Docker on Vast).
   For a clean comparison, our own end-to-end runs on the same episodes are also needed. Our public reference score is
   0.892, but that is before the robot.

## Run record
- **Command:** `python -I timing_ceiling.py <kit>/v2d_submission_kit <hf>/track_3/public`
- **Machine:** Claude cloud VM (CPU), $0.
- **Kit:** `v2d_submission_kit.zip` from the challenge site, downloaded 2026-10-30 (sha256 prefix 8d2bce64ecab6da4).
- **Data:** `nvidia/video_to_data_challenge` `track_3/public/{data,mesh}`.
- **GT use:** mocap poses are read only for scoring (this is a diagnostic; no inference).
