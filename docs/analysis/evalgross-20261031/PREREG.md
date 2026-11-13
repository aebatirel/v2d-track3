# PREREG: GT-free gross-error screen of the pack-7 eval references (H-gross)

**Block 1 written 2026-10-31 16:41 UTC, before any eval indicator value was computed.** Up to this point the eval
files were only downloaded and their key names checked by the fetch log (no pose, depth or video values read).

## Calibration already seen (public only, inference-side indicators; GT used only as the label)

- `screen.py` on the 20 public 25-Oct perception tracks (the tracks the 30 Oct depth audit scored), 33 objects.
  Known gross object tracks: ep23 `wooden_piece_1` and `wooden_piece_2` (frame-0 identity swap; global-alignment
  ADD > 5 cm on 100 % of frames, from `calib_gt/v2/per_frame.csv`). All 31 others: 0–0.5 % of frames > 5 cm.
- Measured separations (`screen_pub.json`, `calib_depth_pub.json`):

| indicator | clean public max (31 objects) | ep23 piece 1 | ep23 piece 2 |
|---|---|---|---|
| largest per-frame COM step | 3.3 cm | **22.3 cm** | 2.4 cm |
| largest per-frame rotation step (cups: axis only) | 28° | **148°** | 11° |
| lowest vertex below the table plane | −2.8 cm, 0 frames < −3 cm | **−4.7 cm, 29 frames** | −2.4 cm |
| penetration between the two objects | 0.9 cm | 0.9 | 0.9 |
| depth-bad share (hidden, or behind > 0.2, or front > 0.5) | 0.155 | **0.342** | 0.132 |
| longest depth-bad run | 36 frames | **73** | 9 |

- So these indicators see a track that has latched onto something else (piece 1 after frame ≈ 26), not a clean
  swap of two look-alike objects (piece 2). A swap needs the identity test (I below).
- Rest float and rest tilt are NOT used as flags: without hands they fire on held-still objects (clean float up to
  22 cm) and on meshes whose hull has no clean base facet (pitcher 55°, beige cup 44° on clean tracks). Reported only.

## Flags (fixed now), per eval episode and object, on the pack-7 policy reference (R) and its feeding perception (P)

- **J (jump):** any per-frame COM step > 5 cm, or any rotation step > 45° (cups: symmetry axis only).
- **U (under table):** lowest mesh vertex < −3 cm below the table plane in ≥ 3 frames.
- **X (penetration):** the two objects interpenetrate by > 2 cm in ≥ 10 % of the sampled frames (every 5th).
  No public positive; this is a physical bound (public clean max 0.9 cm).
- **D (depth):** depth-bad share ≥ 0.25 **or** longest depth-bad run ≥ 50 frames; `pipeline/depth_audit.py`
  thresholds unchanged (τ 1.5 cm, erode 4, hidden < 0.2 visible, min 50 px), perception mode on P and reference mode
  (`--ref --table`) on R, every frame.
- **RP (reference departs from perception):** the reference is > 5 cm (COM) from its feeding perception in ≥ 10
  consecutive frames. Not calibrated on public (no public policy reference here). It does not say which is wrong;
  D on R vs D on P arbitrates.
- **I (identity), for the two look-alike pairs only** (boards eval 25; cups eval 10): rule and threshold fixed in
  block 2 below after the public calibration (ep23/ep24 boards, ep11 cups), before any eval identity value.

**Suspected gross error** = an object of the policy reference flagged by J, U, X or D on R, or by I. A flag on P
only (the reference was repaired downstream) is listed separately and not counted.
**Ranking:** number of flags, then the largest magnitude relative to its threshold.
**Reading rule for H-gross:** no suspected gross error in the 16 two-object episodes weakens H-gross; one or more
supports it only once its evidence (frames, magnitudes, video/depth) is checked and the cause is named. The
calibration has one gross public positive (ep23), so a clean screen bounds only errors of the latched-track kind.

## Block 2, written 2026-10-31 16:43 UTC (clock read 16:42:57 just before the append), after the public identity calibration and before any eval identity value

Public calibration (`identity.py`, 25 Oct perception tracks, every 5th frame; `id_pub/*.json`):
- **Boards, knob rule** (`pipeline/identity_fix.py` scoring, unchanged, but per frame over the whole episode):
  d(t) = score(swapped) − score(as tracked), no flips; negative = the swap explains the knobs better.
  - ep23 (known frame-0 swap): d = −31 … −103 on every sampled frame 0–140 (29 in a row), then positive after the
    track re-latches (frames 145–320).
  - ep24 (clean): d > 0 on 52 of 55 sampled frames; the three negatives are −3.2, −6.8, −6.9 (never in a row).
- **Cups:** ego_cam_c is monochrome (B − R = −1 on every frame), so the cue is the median grey level in each cup's
  projected silhouette. ep11 (clean): blue 55–73 vs beige 147–166 on frames 0–55, while the cups stand apart; once
  they are handled and stacked (frames ≥ 60) the order flips (blue 121–144 vs beige 86–141), so only the frames before
  the first cup motion carry identity.

Flag I (fixed now):
- **Boards (eval 25):** d < −20 on ≥ 5 consecutive sampled frames (step 5), on the reference mapped to the camera
  (and, reported separately, on its feeding perception).
- **Cups (eval 10):** over the sampled frames before either cup first moves in the reference (static mask of
  `screen.py`, capped at frame 50), the median of grey(blue_cup) − grey(beige_cup) > 0. No public cup swap exists, so
  this threshold is set by the ep11 margin (−80 to −105), not by a positive.
