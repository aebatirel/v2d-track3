# MetricTrail (the owner's SLAM recipe) vs our camera: result (19 Nov 2026)

PREREG: `PREREG.md` (pushed at 63d3f262, before any run; cost section changed before any run at the owner's machine
question). Labels: [M] measured, [D] public vs mocap, [E] estimate, [H] hypothesis. All inference GT-free; mocap read
only by `tools/cam_arms_score.py` after every output existed. Raw: `results/score.json`, `results/score.log`,
`results/job.log`; store run `runs/20261119-camarms-d32a7a8/`.

## Verdict
**The owner's recipe (VD: MetricTrail mono + DA3METRIC-LARGE, known K, window 12) does not improve our perception.**
Gate: **FAIL** on all four conditions and **falsified** (mean ΔAUC ≤ 0).

| Arm (camera only; same object tracks, public scans) | mean AUC | ΔAUC vs C | better / worse | ΔMPPE cm | frames > 3 cm |
|---|---|---|---|---|---|
| **C** our camera (perc2 keyframe PnP on FoundationStereo depth) | **0.9285** | — | — | — | 554 |
| **VD** owner's recipe (mono, DA3 metric) | 0.9099 | **−0.0186** | 2 / 18 | +0.272 | 682 |
| VD2 same again (noise) | 0.9105 | −0.0180 | 2 / 18 | +0.243 | 682 |
| VM MoGe-2 depth (owner's earlier version) | 0.9073 | −0.0212 | 1 / 19 | +0.313 | 694 |
| VDH VD + hand/person masking | 0.9125 | −0.0160 | 1 / 18 | +0.224 | 579 |
| VS MetricTrail stereo (c/b), DA3 | 0.9228 | −0.0057 | 2 / 18 | +0.091 | 585 |
| M room map (2 Nov, drift-free reference) | **0.9333** | **+0.0048** | 7 / 6 | −0.069 | 556 |

[D] 20 public episodes. MetricTrail's own noise (VD2 vs VD): mean |ΔAUC| 0.0007, so the differences are real. Worst VD
episode: ep12 −0.206 (a late translation failure: camera 162 mm off the map at p95, path 3× the map's; the stereo arm
VS does not fail there). Best: ep24 +0.081 (VS +0.118, M +0.112): the one episode where our camera drifts (35 mm /
1.5° at p95 vs the map), as on 2 Nov.

Side arm SD (perc2's object tracker and camera on MetricTrail's per-frame DA3 metric depth instead of stereo):
mean AUC **0.194** vs 0.9285, worse on 20 / 20, 7,343 frames > 3 cm vs 554 [D]. Monocular metric depth cannot replace
our stereo depth for object tracking.

## Why: a start-up transient, not drift [M, GT-free: camera vs the room map]
Median rotation / translation gap to the map camera, 18 episodes (ep12 and ep24 excluded), by frame range:

| frames | C (ours) | VD | VS |
|---|---|---|---|
| 1–5 | 0.03° / 0.8 mm | 0.47° / 1.9 mm | 0.47° / 1.9 mm |
| 6–20 | 0.03° / 1.1 mm | 0.91° / 3.9 mm | 0.90° / 3.9 mm |
| 21–40 | 0.04° / 1.5 mm | 0.77° / 4.1 mm | 0.78° / 3.7 mm |
| 41–80 | 0.07° / 2.2 mm | 0.63° / 4.2 mm | 0.63° / 3.5 mm |
| 81–end | 0.10° / 3.2 mm | 0.08° / 2.1 mm | 0.05° / 1.7 mm |

- After about 4 s (80 frames at 20 fps) MetricTrail is as good as our camera or slightly better (less drift by the end).
- In the first ~4 s it is off by 0.5–0.9°, identically for mono and stereo, so the cause is its start-up, not the depth
  model [I]. The scorer anchors each episode at frame 0, so that early error lands directly on the objects (≈ 4–8 mm
  at 0.5 m), which on top of tracker error pushes frames past the AUC's 1 cm threshold; our camera adds < 1 mm there.
- [H] Mechanism: DPVO's initialisation and metric-prior warm-up on a low-parallax start (the wearer looks at the
  table before acting) leaves the first keyframes' rotation poorly constrained; the local window later moves on
  without correcting them (no loop closure). Falsifier: a pre-rolled run (e.g. MetricTrail seeded with our first
  80 frames' poses, or run on the reversed clip) whose first-80-frame gap to the map stays ≤ 0.1°. Not run.
- For long trajectories (the owner's other project) a few-second start-up error is negligible; on 7–18 s clips
  scored from frame 0 it dominates.

## What this means
- Our camera is not the weak point: it matches a drift-free map to ≈ 0.1° on 19 of 20 public episodes. The only camera
  failure is ep24, which the room map (or MetricTrail stereo) fixes; a GT-free "switch to the map where perc2 and the
  map disagree by > 1 cm" rule would capture it (proposed 2 Nov, still unregistered).
- Room map on public with scans: +0.0048 (7 / 6), almost all ep24 (+0.112): replicates 2 Nov (+0.0070 with library
  meshes).
- Stereo depth matters far more than the camera tracker: replacing it with monocular metric depth collapses tracking.

## Runs, cost, failures
- Box 1: 61417362 (RTX 5090): host image pull failed twice; destroyed, nothing ran (≈ $0).
- Box 2: 61419634 (RTX 5090, 32 GB, 09:38–10:28): perc2 ran out of GPU memory in FoundationPose register at full
  resolution (also after welding the scans' duplicate vertices, `MESH_WELD=1`); ViPE build failed on the image's
  system Python (fixed: `UV_PYTHON_PREFERENCE=only-managed`); the MetricTrail install was verified end to end there.
  ≈ $0.53 [E].
- Box 3: 61427848 (RTX PRO 5000, 48 GB, 10:31–13:39), code cd170210: everything ran. S 20/20, MetricTrail 100/100,
  SD 20/20, scored 13:38. ≈ $2.28 [E].
- Total ≈ $2.9 [E] (duration × $/h; credit deltas include other instances on the account), cap $5.
- Code: `ops/jobs/cam_arms.sh`, `ops/box/vipe_setup.sh`, `pipeline/vipe_prep.py`, `pipeline/vipe_cam.py`,
  `tools/cam_arms_score.py`, perc2 `MESH_WELD` (default off). ViPE ead2e008; MetricTrail `dino_dpvo.pth` sha256
  d0aa57e1…; DINOv3 ViT-S/16 sha256 08c60483bc63c04f… (verified by MetricTrail's loader).
- Also seen (not in the gate): ep0 scores 0.076 under every camera arm, so its loss is object tracking (the known
  lid flip), not the camera.
