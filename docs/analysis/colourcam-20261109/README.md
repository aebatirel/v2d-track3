# Colour-camera tracking test, public episodes (9 Nov 2026): result

Owner's question: would tracking on the colour camera (as Team Purple appears to have done) have made a difference?
Pre-registration: `PREREG.md` (pushed at 4124eec before any run). Labels: [M] measured, [D] public vs mocap, [E]
estimate, [I] inference.

## Answer
**No meaningful difference for our pipeline [D].** Against the tracker we actually used (grey camera c, library_v3
templates), FoundationPose on colour camera a with colour-painted templates changed the mean registered AUC over the
20 public episodes by **+0.0018** (0.8900 → 0.8917), with 9 episodes better and 11 worse (median −0.0017). Without
ep18, whose sweeper track is known to be chaotic (2 Nov lane: every perturbation changes it), the change is −0.0008.
The pre-registered gate (colour vs grey with the same per-episode repainting) **failed** on its "no episode below
−0.02" condition: ep2 at −0.0212. Its mean gain (+0.0144) came mostly from that same chaotic ep18 (+0.19) and from the
grey arm getting worse when repainted.

So colour tracking does not explain the gap to the teams above us on our pipeline (our 1.80 cm against their 1.2 cm on
the board). It is not evidence that colour is useless for other pipelines (Purple's tracker set-up is not public).

## Numbers [D] (registered scorer `score_registered.py`, `--meshes meshes/library_v3`, 20 public episodes)
| Arm | What it is | Mean AUC |
|---|---|---|
| C | today's tracker: grey camera c, library_v3 grey templates | 0.8900 |
| CP | grey camera c, templates repainted in grey per episode along C's track | 0.8773 |
| AP | colour camera a, templates repainted in colour per episode along C's track | 0.8917 |

| Comparison | mean ΔAUC | better / worse | worst episode | mean ΔMPPE / ΔRPE (cm) | > 3 cm frames |
|---|---|---|---|---|---|
| **AP vs CP (gated)** | **+0.0144** | 10 / 7 | ep2 −0.0212 | −0.24 / −0.64 | 1134 → 958 |
| AP vs C (report) | +0.0018 | 9 / 11 | ep11 −0.0337 | +0.91 / +0.15 (ep23 alone +19.0 / +4.1; without ep23 −0.04 / −0.06) | 1035 → 958 |
| CP vs C (report) | −0.0127 | 6 / 13 | ep18 −0.1401 | +1.15 / +0.79 | 1035 → 1134 |

Gate for AP vs CP: mean ≥ +0.005 and ≥ 2 × noise: pass; no episode < −0.02: **fail** (ep2 −0.0212, misses by 0.0012);
mean ΔMPPE ≤ 0 and ΔRPE ≤ 0: pass; > 3 cm frames not more: pass. **Verdict: FAIL** (not falsified: mean > 0).

Per object, AP vs C (mean ΔAUC, number of episodes): pitcher +0.030 (2), sweeper +0.029 (2), wooden pieces +0.009 /
+0.011 (2 each), rack +0.003 (5), white pot +0.002 (9), dust pan +0.001 (3), beige cup +0.005 (1), blue cup −0.011 (5),
lid −0.031 (2).

Post-hoc views (not pre-registered, reported only): without ep18, AP vs CP +0.0051 (9 / 7), AP vs C −0.0008 (8 / 11),
CP vs C −0.0059.

## Reading [I]
- The camera change is small next to episode-level chaos. Against C, 17 of 20 episodes move by less than 0.02 either
  way; the exceptions are ep18 (+0.051, the chaotic sweeper), ep21 (+0.044, pitcher) and ep11 (−0.034, the cups).
  The large AP-vs-CP gains on ep18 (+0.19) and ep39 (+0.069) are the repainted grey arm losing tracks that C kept.
- Repainting the templates per episode from our own track (CP) made the grey tracker worse (−0.013), most of all on the
  sweeper; the library_v3 grey textures, built from several frames and episodes, are the better template here.
- Colour helps a little on the pitcher and sweeper (the objects with the largest grey-tracker errors) and hurts on the
  lid and blue cup. Possible causes on camera a: the one-frame offset, rolling shutter and motion blur (note 12), half
  resolution, depth moved in from another viewpoint. Not tested.
- Purple's lead is therefore more likely to come from elsewhere: cleaner object points (two-view masks with hands
  removed), object-specific fits for the spoon and cups, hand-built collision geometry, and per-episode fixes checked on
  the board (`docs/research/competitors-2026-11-09.md` §6).

## Run record
- Code: 4124eec (job, painting, TRACK_CAM) + 5b79523 (fix: camera-a intrinsics; `K_` is rebound to DET_K in perc2).
  ep12 AP crashed on 4124eec; the box was switched to 5b79523 before ep0 AP, and ep12 AP was re-run on 5b79523.
  C and CP are unaffected by the fix (the grey path did not change).
- Box 59948609 (RTX PRO 6000 S, $1.761/h), store run `20261109-pcol-4124eec`, scored at store revision
  **ad8b49b1c5bf2828da783221b306b0218b729b94** (the run box's final push). AP ran on camera a on all 8,459 tracked
  frames, 0 fallbacks to camera c.
- An unintended duplicate box (59948693) ran the same job on 4124eec and pushed into the same store folder; the pinned
  revision excludes its files (work log 9 Nov 21:36-21:45). Destroyed with the owner's approval.
- Cost [M]: **$3.72** for both boxes (credit $38.37 → $34.65); the run box alone ≈ $1.97 [E].
- Files: `PREREG.md`, `cpu_checks/` (geometry overlay, splat check, dry run), `scripts/score_gate.py`,
  `results/gate.json`, `results/scores/<arm>/ep<N>.json`, `results/score_gate_output.txt`.
