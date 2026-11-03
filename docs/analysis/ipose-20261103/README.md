# Instance-level pot pose network vs our tracker: results (3 Nov 2026)

Lane instance-pose, branch `claude/instance-pose-20261103`. Labels: [M] measured, [D] public vs mocap, [E] estimate,
[I] inference.

## Verdict
**FAIL for both arms**, on the primary gate and on the secondary criterion, so neither arm justifies eval use.
- R: mean pot ΔAUC −0.065.
- R+M: mean pot ΔAUC −0.0085.
- **The rendered-only network is not trustworthy here:** −0.26 AUC on ep27. So a spoon network without public GT
  should not be built this way.

## Setup (all pre-registered: PREREG.md 1058d7ec, Addendum 1 1931d067, before any training)
- **Split:** train 0, 26, 41, 42, 43; test 2, 27, 44, 45.
- **Mesh:** the submitted 13p / 14p TSDF pot.
- **Network:** own GDRN-style correspondence net on 256² grey crops (ResNet-34), with pose from RANSAC Kabsch against
  the FoundationStereo depth.
- **ROI:** the control track's box.
- **Arms:**
  - R: 15k crops from our own point-splat renders over real backgrounds, with hand occluders, 40 epochs.
  - R+M: R + 10 epochs, real : synth 1 : 1. 2,826 real crops from the train episodes, labelled from mocap
    (GT-informed).
- **Scoring:** `score_registered.py --reg_seeds 10`, m13p meshes; the control C reproduces base13p exactly.
- **Run:** box 58930545 (RTX 4090), run `20261103-ipose-1654726` (store `runs/20261103-ipose-1654726/results/ipose/`),
  code c5c3fa56.
- **Training [M]:**
  - render 15k crops ≈ 1.5 min (3 processes × 5k, 87 s each);
  - R training 20 min (18.8k iterations);
  - R+M training ≈ 2 min (1,770 iterations, 115 s);
  - inference ≈ 15 s per episode.

## Results [D] (pot, 10-seed registered; ΔAUC vs control C; median ADD change relative to C)
| Arm / variant | ep2 | ep27 | ep44 | ep45 | mean ΔAUC | median ADD (2 / 27 / 44 / 45) | lost > 3 cm (2 / 27 / 44 / 45) |
|---|---|---|---|---|---|---|---|
| control C (AUC) | 0.9935 | 0.9677 | 0.9979 | 0.9742 | — | 0.44 / 0.76 / 0.32 / 0.64 cm | 2 / 1 / 0 / 0 |
| **R / N (primary)** | −0.0033 | **−0.2573** | +0.0016 | +0.0001 | **−0.0647** | −8 % / +75 % / +22 % / +21 % | 2 / 74 / 0 / 0 |
| R / NP (no depth) | −0.0072 | −0.4311 | −0.0019 | −0.0749 | −0.1288 | +35 / +267 / +45 / +79 % | 2 / 119 / 0 / 35 |
| R / NS | −0.0027 | −0.2586 | +0.0020 | +0.0052 | −0.0635 | | 2 / 81 / 0 / 0 |
| R / NT | −0.0056 | −0.2199 | +0.0018 | +0.0070 | −0.0542 | | 2 / 78 / 0 / 0 |
| **R+M / N (primary)** | −0.0010 | **−0.0350** | +0.0009 | +0.0011 | **−0.0085** | **−39 %** / +16 % / +29 % / −10 % | 2 / 8 / 0 / 3 |
| R+M / NP | −0.0020 | −0.1000 | −0.0130 | −0.0416 | −0.0392 | | 2 / 34 / 0 / 13 |
| R+M / NS | −0.0010 | −0.0252 | +0.0007 | +0.0086 | −0.0042 | | 2 / 6 / 0 / 2 |
| R+M / NT | −0.0049 | −0.0150 | +0.0013 | +0.0096 | −0.0023 | | 2 / 1 / 0 / 0 |

- **Primary gate** (≥ +0.02, none < −0.01): fails for R and R+M. It was unreachable anyway: the control's ceiling
  allows at most +0.017.
- **Secondary** (median ADD −20 %, no episode worse): fails for R and R+M. R+M improves ep2 (−39 %) and ep45 (−10 %)
  but worsens ep27 and ep44.
- **Fallbacks** (fewer than 25 depth inliers): R 8 frames on ep27, 0 elsewhere; R+M none.
- Full numbers: `results/score.json`; per-frame diagnostics: `results/diag_*.json`.

## Reading [I]
1. **The failure is concentrated in ep27 frames ≈ 100–200 [D].** Median ADD in that window is 2–6 cm for R, against
   0.7 cm for the control. This is the hand-held lift: the network's rotation disagrees with the track by 9.7° (median
   over the episode) on ep27, against 1.4–2.9° on the other test episodes.
   - The predicted visible mask also misses much of the pot interior (`results/vis_R_ep27.jpg`). The rendered interior
     shading does not match the real white interior; this is the render-to-real gap.
   - Real labels (R+M) shrink the ep27 loss from −0.26 to −0.035 but do not remove it.
2. **Where the pot is easy, the network roughly matches the tracker.** Episodes 2 / 44 / 45 lie within ±0.01 AUC, and
   R+M's median ADD on ep2 is lower (0.27 vs 0.44 cm). A per-frame method has no temporal prior, so its jitter costs
   about as much as its bias removal gains at this accuracy (0.3–0.8 cm).
3. **Depth is essential:** PnP-only (NP) is much worse in both arms.
4. **Temporal combination helps a little but not enough:** R+M / NT is −0.0023 with 1 lost frame on ep27. It is the
   closest to the control and still not better.
5. **For the spoon:** R is far below the control (−0.065 mean, −0.26 on ep27), while GT-informed fine-tuning recovers
   most of the gap. A rendered-only spoon network would not be trustworthy without real labels, and the spoon has
   none.

## What would have to change (hypotheses, not tested)
- [H] A much larger rendered set with physically based materials (BlenderProc-style) and real hand renders (MANO) for
  the hand-held phases. Falsifier: R on ep27 still below the control by > 0.01.
- [H] Use the network only as a re-detector when the track is lost. The pot track is never lost in these episodes, so
  this has no measurable value on the pot.
- Given the pot's control AUC of 0.98, the pot was a hard proof-of-concept object. Objects with episode-specific bias
  (rack, boards) have more headroom, but their tracks are also limited by mesh shape rather than tracking, per the
  rest-frame oracle.

## Cost
- Box 58930545 (RTX 4090, $0.556/h): rented ≈ 06:58 UTC, self-destroyed ≈ 08:22 UTC. ≈ 1.4 h ≈ **$0.8**, plus ≈ 20 GB
  of downloads at $2.67/TB (≈ $0.05) [E from instance hours].
- The first job attempt failed in 2 min: `*.npz` is git-ignored, so the control tracks were missing. It was restarted
  in place on the same box.
- Scoring was on CPU here ($0).
