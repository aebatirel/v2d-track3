[← Index](../README.md) · [Summary](../00-summary.md) · [← 19](19-collision-hulls.md) · [21 →](21-synthesis-round4.md)

# DIG 20 — camera sync, spoon frame, first-contact detector

Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/20/
Labels: [V] verified by measurement, [E] estimate/inference from evidence, [H] hypothesis.

## DIG 20 bottom line (all three stages complete, 2026-10-07)
**A. Camera timing.**
- [V] b and c are hardware-synchronous at the same index: -0.01 +- 0.09 ms over 39 clips.
- [V] Cam a is NOT same-index. a[k+1] ~ b[k] in 36/39 clips. The exceptions: p21 a[k+2]; a cam-a drop in p22 and a
  b/c drop in e20 switch the pairing mid-clip.
- [V] Cam a is rolling shutter, 31.6 ms/height, top first:
  t(a[k+n], row y) - t(b[k]) = -9.8 + 31.6 y ms (sd 0.56 ms per episode).
- [E] GT row k ~ b[k] + 25 ms.
- Consequence: "match frames by frame_index" holds only for b<->c. Table: `work/20/out/sync_table.json`.

**B. Spoon frame.**
- [V] Measured automatically on 10 eval clips: marker triangle 53.0 / 153.2 / 194.2 mm, a round handle of ~10 mm
  radius, and all three markers 6-11 mm above the handle axis toward the concave face (M3 is not on the axis).
- [V model] P(frame B) is 0.33 under the mid-axis rule (0.13-0.65 with the bend) and 0.93-1.00 under x-skew rules.
- [E] Overall ~0.45-0.5: still an organiser question. No leaderboard A/B.
- [V] Rectified b/c stereo needs a vertical-misalignment FIELD (3.8 px room .. 0.8-1.5 px table), not one dy.
- Stage B re-run (2026-10-07, section "Stage B re-run" below): the verdict is unchanged.
  - [V] The handle bulges (19 -> 21 -> 19 mm) around a straight midline, so the axis must come from row midpoints, not
    per-limb lines.
  - [V] Raw bowl offset = bend + dH * cot(alpha) over 8 rest/end-rest views gives bend +1.5 +- 0.6 mm toward M1
    ([E] +1.3 +- 0.8 overall). The asymmetry is +3.2..+4.2 mm.
  - [V model] Mid-axis P(B) 0.34 (0.47 at the low-bend end); x-skew rules 0.88-1.00.
  - [V] The held "near-frontal" frames are an artefact of an unreliable free-sweep M1 depth. A truly frontal view is still
    the open falsifier.

**C. Slot-0 anchor window.**
- [V] An automatic, causal detector on cam a. Rule: window = rows [0, min(object-motion onset, contact + 10)
  - pairing - 3]. It gives oracle-level anchor bias on 19 public eps: 0.14 deg / 0.13 mm median, 0.59 deg / 2.2 mm
  max. It holds up under leave-one-out and under 10 px frame-0 mask errors.
- [V] Contact alone fires a median 8 frames before the first 1 mm perturbation (hands rest on objects first).
  Motion alone misses in-hand tilts, slides during head sweeps, and thin objects with a poor mask.
- [V/E] The stake is small: averaging up to the 1 cm onset costs only 0.33 deg median (2.0 max), i.e. ~0.001 board
  AUC (<= 0.003 per clip). Note 15's "1-8.6 deg" are single-frame maxima, not window means.
- Stage C re-run (2026-10-07, section "Stage C re-run"): the detector now runs end to end with no GT in the loop.
  - [V] A GT-free frame-0 slot-0 mask comes from b/c stereo plus a 2.5-D template search of the slot-0 mesh on the
    table height map (`r_pose0.py`). It finds the right object in 19/20 public clips (after a twin-plank side rule)
    with IoU median 0.85 and slot-0 origin error ~1 cm, and in 17/20 eval clips by eye.
  - [V] With these masks the frozen detector reproduces the GT-mask results: dR 0.15/0.32/0.58 deg, dt
    0.14/0.46/2.03 mm (median/p90/max), with the same two robust-late cases.
  - [V] Fresh holdout p45: the window ends 24 rows before the perturbation, with 0.17 deg bias.
  - [E] On eval, every right-object clip ends at or before the viewed first motion. e20 (cup in the air at f0) correctly
    returns EMPTY, and e32 (hand on the cup at f0) gets a 5-row window.
  - [V] A wrong slot-0 IDENTITY is the one dangerous case: before the side rule, p23 gave 24 mm / 2.9 deg and an exact
    tracker's AUC of 0.73.
  - [V sim] H4 holds but buys nothing visible: a pose-track changepoint reaches oracle-level error at 0.5-3 deg
    per-frame noise, 0.03-0.12 deg better than the image detector in the median.
- Stage C round 3 (2026-10-07, section "Stage C round 3"): the re-run's open items.
  - [V] Flat slot-0 objects get their frame-0 mask from 2-D colour on the stereo table (hue for planks, local brightness
    for the spoon) plus a metric footprint test (`r3_flat.py`): public planks IoU 0.87/0.88 (p23 was 0.73). On eval
    this fixes e25 (left plank; window end row 32 vs viewed slide f48-56, was 77) and e36 (the spoon, not the hand;
    row 24 vs lift f40). Public statistics are unchanged.
  - [V/E] Final pipeline, public 20: onset error vs the raw first perturbation median -2 frames (p10/p90 -22/+15),
    robust -4; contact alone -10 (it leads), motion alone +2 with a late tail to +108; anchor bias dR 0.15/0.32/0.58
    deg, dt 0.14/0.46/2.03 mm. Eval: no window ends after the viewed first motion; e20 is EMPTY by design.
  - [V] A class-relative confidence flag flags 0/20 public and only e20 on eval.
  - [V, negative] An automatic ego/non-ego test was tried and fails: the ROI-local approach direction mislabels 7 ego
    hands that reach in from the side; skin colour misses forearms. [V visual] All 40 triggers are the wearer's hands
    or non-hand change, so ego-arm rejection cannot change any window in this data.


## Stage A — time offsets between ego_cam_a, ego_cam_b, ego_cam_c

(status: Stage A COMPLETE 2026-10-06; see "Stage A summary" at the end of this section. Stages B and C were completed later; see below.)

### A0. Container and metadata evidence (script `work/20/scripts/a_pts.py`, out `work/20/out/a_pts.json`)
- [V] All 20 public and all 20 eval episodes now have ego_cam_a/b/c locally. Every stream was re-encoded by
  Lavf62.12 at constant `r_frame_rate=20/1`, time_base 1/10240, start_time 0. Packet PTS are exactly uniform
  50 ms (min = max dt) in all 120 clips. In every episode, a, b and c have the same frame count, and on public
  episodes this count equals the parquet row count.
  => **The containers carry no per-camera timing information.** Any a/b/c offset must be measured from image content.
- [V] The parquet has ONE `capture_time` per row (not per camera) plus a synthetic `timestamp` (uniform
  1/20.2541 s, as in info.json `fps` 20.254). `capture_time` starts at 14-70 ms, has mean dt 50.00 ms and jitter
  1 ms rms. Outlier pairs occur: ep 13 dt 12.4/91.3 ms, ep 41 13.7/92.9 ms, ep 22 24.4/80.0 ms. Each pair sums to
  about 100 ms, i.e. one row's time is displaced by 26-38 ms (checked below for a frame slip).
- [V] `camera_calibration.json` provides `devices.ego.master_socket=cam_a`, `is_clock_master=false` (the exo
  device is clock master), `rotation_deg=180`, and `cross_device_skew_ms.ego = {mean 7.39, max 7.41}`. Its
  `note` says that separate devices are NOT hardware synchronised. This skew is exo-vs-ego (between devices),
  not between sockets of the ego device. There is no exo video in Track 3. The note says nothing about
  a/b/c within the ego device.
- [E] Hardware context: an OAK device with CAM_A 2028x1520 (IMX378-class binned colour, **rolling shutter**) and
  CAM_B/C 1280x800 (OV9282-class mono, global shutter). On OAK devices the two mono sockets normally share
  a hardware frame sync, and the colour socket is matched by host/device timestamps. Expect b-c ~0 and
  a-b = a few ms plus a row-dependent rolling-shutter term. This is unverified; measured below.

### A1. Method: angular-velocity cross-correlation (scripts `a_motion.py`, `a_sync.py`; outputs `out/motion/*.npz`, `out/sync_*.json`)
- a/b/c are rigid on one head, so every stream sees the same head angular velocity. It appears in each camera
  frame through a fixed rotation. Per stream and per consecutive frame pair: Shi-Tomasi + pyramidal KLT with a
  forward-backward check (<0.5 px). Cam a is decoded at half resolution (fx~575), b/c at full (fx~565).
  Points are undistorted with the given K and 14-coefficient model to unit bearings. A robust Kabsch fit
  (iterative MAD rejection, which drops the hands and other movers) gives R_k: f_{k+1} = R_k f_k. The stream is
  w[k] = rotvec(R_k), the mean angular velocity over interval k.
- Offset model: w_X[k] = R_XY w_Y(k+s). w_Y is cubic-spline-interpolated over the interval index. s is searched
  over +-3 frames in 0.01-frame steps, then refined parabolically. R_XY is re-fitted by Kabsch at each s, so the
  method does not depend on the extrinsic convention. It is cross-checked against the calibration rotation.
  Reported offset = o_X - o_Y = 50 ms * s. **Positive means frame k of X was captured LATER than frame k of Y.**
  Cost = normalised residual sum((w_X - R w_Y)^2)/sum(w_X^2). Uncertainty comes from four contiguous
  quarters of the episode. This follows the standard gyro/camera temporal-calibration idea (angular-rate
  cross-correlation, e.g. Mair et al. 2011; Karpenko et al. 2011; Kalibr/Furgale et al. 2013 estimates the
  same offset in continuous time) [literature from memory, not re-read for this note].
- [V] **Public ep 11 (slow head motion, median 2.8 deg/s):**
  - b-c: **+0.01 ms** (quarters -0.22..+0.19). Cost 0.0003 at the optimum, the same at s=0. Mono pair in sync.
  - a-b: **-52.1 ms** (quarters -53.8, -52.1, -52.0, -50.5). Cost 0.0041 vs 0.4035 at s=0. With the
    calibration rotation fixed: -51.8 ms. a-c: -52.1 ms.
  - Fitted R vs calibration rotation: 0.9 deg (c-b), 2.1 deg (a-b).
  => **Cam a frame k is ~1 frame (52 ms) EARLIER than b/c frame k.** The same physical instant is
  a[k+1] ~ b[k] = c[k], with a[k+1] ~2 ms earlier than b[k].
  Note 12 needed a 2-3 px shift off the a/b epipolar curve at ep 11 f0. At 0.14 deg/frame that equals
  0.14 deg x fx 1150 / 57.3 = 2.8 px, which fits a same-index a/b pairing that is one frame apart [E].

### A2. All 39 local episodes (19 public with a/b/c, 20 eval) — `out/sync_all.log`, `out/sync_<key>.json`
- [V] **b-c = -0.01 +- 0.09 ms** (n=39; max |.| 0.37 ms on eval 28). Each optimum cost equals the cost at s=0.
  **The mono pair is synchronous at the same frame_index** (hardware sync), in every public and eval clip.
- [V] **a-b whole-episode fit, excluding 3 episodes with slips:** mean **-49.5 ms**, std 1.6, range -52.5..-46.4 (n=36;
  public -49.9 +- 1.4, eval -49.1 +- 1.6). The cost at s=0 is 20-100x the optimum in every episode. With the
  calibration rotation fixed instead of re-fitted, the results agree within ~1 ms. The fitted a-b rotation is
  2-6 deg from the calibration rotation (c-b 0.4-2.2 deg). The a<->b calibration rotation may be a few deg off,
  or rolling shutter/translation bias the fit [H, see A4].
- [V] **The integer frame pairing is NOT constant:**
  - public 21: **-99.9 ms** over the whole episode (quarters -100.1..-98.9), i.e. a[k+2] ~ b[k].
  - public 22: quarters -97.1 | -51.8 | -47.4 | -47.8. A slip from 2 frames to 1 frame inside quarter 1. This
    coincides with its capture_time glitch at rows 48-49 (dt 80.0/24.4 ms).
  - eval 20: quarters -55.0 | -94.3 | -100.0 | -99.8. A slip from 1 to 2 frames during quarter 2.
  => For a/b/c stereo or triangulation, use b[k] with c[k] (always). Pair a with b/c only through a
  per-episode, time-resolved offset estimate: nominally a[k+1] <-> b[k], but sometimes a[k+2], and it can
  change mid-clip. Never assume a[k] <-> b[k].

### A3. Slips are dropped frames (scripts `a_slide.py` sliding +-15-interval window, `a_slip.py` changepoint)
- [V] public 22: the change point is interval 48->49 (gain 0.92). There **cam_a** shows one doubled interval
  (|w| 0.68 deg vs 0.13-0.31 around it; MAD 23 vs 10-14), while b/c are smooth. Cam a dropped one sensor frame
  between its indices 48 and 49. The pairing goes from a[k+2]~b[k] (rows 0-48) to a[k+1]~b[k] (rows 49+).
- [V] eval 20: the change point is interval 48->49 (gain 0.95). There **b and c together** show a doubled interval
  (|w| 0.59 deg vs 0.15-0.24; MAD 16.7/14.4 vs 8-10), while a is smooth. The mono pair dropped one frame, and
  the pairing goes from a[k+1]~b[k] (rows 0-48) to a[k+2]~b[k] (rows 49+).
- [V] public 21 is a[k+2]~b[k] for the whole clip, with no drop inside. So the offset at the clip start already
  differs by one frame. Because a, b and c always have equal frame counts, the recorder must trim or pad the
  ends. The integer pairing at frame 0 is not fixed.
- [V] capture_time glitches vs video: public 22's glitch (rows 48->49->50, dt 80.0/24.4 ms) is at the same interval
  as cam_a's drop. Public 13 row 141 (dt 91.3/12.4) and public 41 row 193 (92.9/13.7) show NO doubled or zero
  interval in any stream (motion is smooth across them). So the glitches are not reliable drop markers. Two of
  three are timestamp-only anomalies [V for these 3 cases].
- Detection rule for a pipeline [E]: run the sliding-window a-b offset (window +-15 intervals, fixed rig R). A
  change in the rounded integer pairing marks a slip. Localise it with the change-point test on the per-interval
  residuals of the two candidate pairings. Confirm it by a ~2x |w| and MAD spike in the stream that dropped. The
  b/c pair always drops together, so a b-vs-c slip is impossible.

### A4. Cam a is rolling shutter; with a row model the a-b offset is constant (`a_rs.py`; logs `out/rs_a_b_pantilt.log`)
- Method: re-fit the offset using only cam a features inside each stored-image third (top/mid/bottom; mean
  normalised rows ~0.12/0.52/0.83) against cam b's full-frame series, with the rig R fixed from the full fit.
  Slip episodes are restricted to a constant segment (p22 rows 60-188, e20 rows 50-201).
- [V] **Every one of 39 episodes shows the same row dependence:** top -56.5, mid -43.6, bottom -33.6 ms (1-frame
  pairing). The slope is **+31.5 +- 1.3 ms per image height** using pan/tilt components only, and +33.8 +- 1.3
  using roll only. Stored-image top rows are exposed first.
- [V] Control: cam b bands vs cam c full give a slope of -1.1 +- 4.1 ms/height and bands within +-0.6 ms of 0. The
  mono pair is global shutter, so the cam a slope is not a method artefact.
- [V] **Pooled timing model** (pan/tilt, 39 episodes x 3 bands; the integer pairing is removed per episode):
  `t(a[k+n], stored row y in [0,1]) - t(b[k]) = -9.8 + 31.6*y ms`. Here n = 1 normally and 2 in the slip
  segments of A3. Residual sd 0.75 ms (max 2.7). The per-episode mean residual has sd 0.56 ms (range -1.2..+1.3).
  Public mean +0.04 and eval mean -0.04 ms. So: top row -9.8 ms, image centre +6.0 ms, last row +21.8 ms relative to b[k].
  The whole-frame estimates of A2 (-46.4..-52.5) spread only because each episode weights the rows by where
  its features fall (more texture high in the image gives an effective y ~0.37).
- [E] Consequence for a+b/c triangulation of a moving point: use a[k+n] with b[k]/c[k] and correct by the row
  time (-9.8 + 31.6*y ms) x image velocity, or interpolate b/c tracks to that time. A residual pairing error of
  one frame costs about speed x 50 ms (2.5 cm at 0.5 m/s). Ignoring rolling shutter costs up to ~22 ms (1.1 cm at
  0.5 m/s) at the bottom of the image.

### A5. Geometric check: b/c epipolar residual vs time shift (`a_epi.py`; `out/epi_all.log`, `out/epi_<key>.npz`)
- Method: stereoRectify(c=left, b=right, `left_to_right`, 14-coefficient distortion). 40 frames per episode with the
  most head motion. Features in rect-c[k] are matched to rect-b[k] by pyramidal LK (forward-backward <0.5 px,
  |dy|<8 px). Each c feature is also tracked to k-1 and k+1, and c is interpolated quadratically to k+delta.
  Residual = y_b(k) - y_c(k+delta), the perpendicular-to-epipolar error in rectified pixels. Fast features have
  |v_y| > 3 px/frame. The grid search removes a constant; an LS fit dy = const + delta*v_y uses trimming.
- [V] 7 episodes (eval 5, 6, 19, 20; public 21, 24, 39; ~12-24k fast features each, median |v_y| 5-7 px/frame):
  **LS b-c offset = -0.33..+0.32 ms**. The grid optimum is 0 +- 0.04 frames. The median |residual| is 0.48-0.64 px
  at delta=0 and rises to 2.8-7.8 px at delta=+-1 frame. This independently confirms the hardware-synchronous mono pair.
- [V] Side finding: a **constant rectified vertical offset of +0.66..+2.09 px** (b lower than c) remains after
  calibration rectification. It differs by episode: e5 +2.09, e6 +2.03, p39 +1.87, p24 +0.96, e20 +0.82,
  e19 +0.78, p21 +0.66. The factory b/c extrinsic is slightly off and/or drifts between sessions (thermal or
  mechanical) [H]. For SGBM or any epipolar search on b/c, estimate and remove this per episode (median dy of
  matched static features) or allow a +-3 px vertical search. Not checked: within-episode stability, or whether it
  is a constant rather than a small rotation (dy linear in x/y).

### A6. Which stream do parquet rows (mocap GT) align with? (analysis only, public GT; `a_gtalign2.py`, `out/gtalign2.log`)
- Why: A2-A4 fix a/b/c relative timing. The GT row k must also be placed on that time axis, or every GT-trained
  detector, GT-fitted camera and output trajectory carries a hidden lag. A 75 ms lag is about 3.8 cm at 0.5 m/s.
- Method: the camera is work/11's s25 frame-0 cam_a fit (mocap world, K as given), propagated by our integrated
  cam_a rotations with the centre C held fixed (head translation ignored). For cam b, the a->b calibration
  rotation is applied. For each moving object:
  - G[k] = image displacement of the projected GT mesh centre between rows k and k+1.
  - V[k] = median rotation-compensated KLT residual flow of moving features (>3 px full-res) in a generous ROI
    around the projected object, frames k->k+1 of that stream.
  - The lag maximises the 2D normalised correlation of V[k] with G(k+s) (spline).
  - If rows align with stream X, then s_X = 0.
  - A first attempt with scalar ROI frame-difference energy (`a_gtalign.py`) could not resolve 50 ms (broad peak:
    E_a vs E_b peaks at -32 ms; corr 0.956 vs 0.942 at -1 vs 0 frames). Abandoned.
- Consistency gate: an object-episode counts only if lag_a - lag_b equals the known A2 pairing offset within 15 ms.
- [V] Gate passed (lag_b ms, lag_a ms): p12 blue cup (-24.5, -75.5), p13 blue cup (-25.4, -74.8), p0 lid
  (-25.2, -75.4), p26 pot (-24.5, -73.5), p22 blue cup (-26.6, -72.6).
  **lag_b = -25.2 +- 0.8 ms (n=5).** Peak correlations are 0.47-0.78.
- Gate failed (excluded): p21 cup (b +23.5 with a flat peak; a-b -148 vs known -100), p21 pitcher, p22 pitcher,
  p0 pot (a-b -3), and the static dish racks.
- [E] **Reading: GT row k is the pose at about t_b(k) + 25 ms, half-way between b[k] and b[k+1]. On cam a
  (pairing n=1) that is t_a(k+1, row y) + (25 + 9.8 - 31.6*y) ms: +35 ms at the top row, +19 ms at the centre,
  +3 ms at the bottom row.** So row k does not match a[k] (about -75 ms) or b[k] (-25 ms). The nearest images are
  b/c interpolated to k+0.5 and cam a frame k+1.
  Caveats:
  - Only 5 object-episodes from 5 episodes (all with s25 cameras).
  - C is held fixed.
  - Image-side position is the mid-exposure of a possibly blurred frame.
  - A half-frame value could come from a mocap/camera timestamp convention (exposure start/end, host
    receive time). The method has no half-interval index shift: V[k] and G[k] both span k->k+1.
- [H] Practical rule (to be validated on more episodes, then used in DIG 20 stages B/C):
  - Place inference outputs for row k at t_b(k) + 25 ms: average the b/c-based poses of frames k and k+1, or use
    cam a frame k+1.
  - Any GT-supervised use of images (detector training, camera fits on moving scenes) should pair GT row k with
    b/c frame k+0.5 or cam a frame k+1, never with a[k].
  - Static scenes (frame-0 anchors) are unaffected.

- [V] More episodes (s24 camera fallback where s25 is missing): p31 sweeper passes the gate (b -24.2, a -73.5).
  p11 beige cup fails (a-b -100 vs known -52). p23 planks and p18 sweeper/dust pan fail (corr <0.15; poor s24
  cameras, as note 11 says). **Gate-passed total: lag_b = -25.1 +- 0.85 ms (n=6), lag_a = -74.2 +- 1.1 ms.**
- [V] Camera-free variant (`a_gtalign3.py`: whole-image mover flow vs GT dp with a per-window 2x3 Jacobian)
  FAILED validation: p12 gives b +71.9 ms and a-b -40; p13 gives a-b -101; costs ~0.7. Hands dominate the
  whole-image mover flow. Not usable.
- [V] **Time-resolved lags in the n=2 segments (ROI method, per row segment) separate the two clocks:**
  - p21 blue cup, rows 0-60 and 60-120 (main motion, corr 0.64-0.77, a-b -99.5/-98 passes the n=2 gate):
    a -76.0/-73.5 (typical), **b +23.5/+24.5**. So b is one frame NEWER than typical w.r.t. GT rows, and a is typical.
    Rows 120-186 (53 px of motion, corr ~0.4) say the opposite (a -126, b -26.5). Weak, not trusted.
  - p22 blue cup, rows 0-48 (the n=2 segment before cam a's drop; 64 px, corr 0.68/0.50, a-b -104.5): **a -134**
    (one frame OLDER than typical), b -29.5 (typical). Rows 49-188: a -73.5, b -23.5 (both typical).
  - The pitchers fail the gate in both episodes.
- [E] **Model consistent with every gate-passing segment:**
  - The GT rows follow a third reference clock (most likely the capture_time/mocap side), not cam a or cam b.
  - Typically b[k] = c[k] is exposed ~25 ms before row k's GT instant. a[k] at stored row y is exposed
    ~(84.8 - 31.6*y) ms before it: 85 ms at the top, 69 ms at the centre, 53 ms at the bottom. So the nearest a
    image is a[k+1].
  - Each stream can sit an integer frame off this typical state:
    - from the clip start: p21 b/c +1 (newer); p22 a -1 (older);
    - after a drop: a drop in stream X makes X one frame newer from then on (p22: a -1 -> 0 at row 49).
  - A hypothesis to mind [H]: arrival-time grouping, with colour ISP/USB latency ~50 ms above mono, makes a[k]
    the older frame. That would explain the ~1-frame a-b pairing, the occasional 2-frame pairing, and the
    lead of GT rows over both streams if rows are stamped at host arrival. Unverified.
- [E] Consequences:
  1. In typical segments, place an output for row k at b/c k+0.5. Equivalently, use cam a frame k+1 with its
     row time.
  2. From video alone, eval clips give the RELATIVE pairing and which stream dropped (doubled-interval spike).
     They do not give the absolute stream-vs-row offset when a clip starts non-typical. Public rate: in 2/19
     clips one stream sits +-1 frame off over all or part of the clip.
  3. Eval 20 starts typical (a-b -50). b/c drop at 48->49, so per the model b/c are +1 newer after row 49: GT
     row k ~ b[k-1] + 25 ms. Cam a stays typical.

### A7. Extra checks and pairing bookkeeping
- [V] Sign convention validated by the drops themselves. A drop in stream X makes X newer, so the a-drop in p22
  must raise o_a - o_b and the b/c-drop in e20 must lower it. Observed: -100 -> -50 (p22) and -50 -> -100 (e20).
- [V] Drop detector: |w[k]| / median of the 4 neighbouring intervals. Natural head saccades make joint ratio-2
  spikes in all streams many times per clip, so drops shared by all streams cannot be seen this way. The two real
  single-stream drops stand out: the stream ratio is >3 (p22 a 3.23, e20 b/c 3.05) while the other stream is
  <1.5. No other clip has such a single-stream spike, consistent with the sliding-window table (A3).
  Public capture_time has no ~100 ms gap, so no row-level drop is visible in public [E].
- [V] Image-level pairing check (`a_pairimg.py`, `out/pairimg.log`). Undistorted a[k+j] is warped into b by the
  infinity homography (calibration rotation) and scored against b[k] by blurred-gradient NCC on the upper 45%
  (distant room), on fast frames. It is weak: the peaks are broad (colour vs mono, rolling-shutter skew, 37 mm
  parallax). The best mean j matches the expected pairing in 6/8 segments (e5 1, e6 1, p24 1, p22 rows 0-47 2,
  p22 rows 50+ 1 by 0.008, e20 rows 50+ 2). In p21 (expect 2) and e20 rows 0-47 (expect 1) it is off by one,
  with differences <0.04. Supporting evidence only; A1-A5 are decisive (cost ratios 20-100x).
- Pairing in b-row terms:
  - p22: a[k+2]~b[k] for b rows 0-46, then a[k+1]~b[k] from b row 48 (a[49]~b[48]). b[47] has no time-matched
    a frame (a[48] is -50 ms, a[49] +50 ms).
  - e20: a[k+1]~b[k] for rows 0-48, then a[k+2]~b[k] from row 49. a[50] has no b counterpart.
- Machine-readable table for stages B/C: `work/20/out/sync_table.json`. It holds the per-episode whole-fit
  offsets, sliding-window segments, pairing per b row, drops, the b/c epipolar offset and rectified dy, the cam a
  row-time model, and the [E] GT-row model.

### A8. Impact estimate
- [V] Public GT object speeds (central difference over 2 rows, 8426 object-rows): 28% of rows move >5 cm/s.
  Moving speed median 0.14, p90 0.35, max 0.81 m/s.
  Position error from a pure timing slip:

  | slip | moving rows median | moving rows p90 | all rows >1 cm | all rows >2 cm |
  |---|---|---|---|---|
  | 25 ms (b[k] for row k) | 0.35 cm | 0.87 cm | 1.7% | 0.0% |
  | 50 ms | 0.69 cm | 1.74 cm | 9.1% | 1.7% |
  | 75 ms (a[k] for row k) | 1.04 cm | 2.61 cm | 14.8% | 5.9% |

- [E] Direct ADD-AUC effect: AUC.py uses thresholds 1..9 cm (9 points, trapezoid), so a frame loses about e/8 cm
  of credit. A 75 ms output lag costs ~0.005 board AUC and 25 ms ~0.002. Small, but free to remove.
- [E] The larger effects are indirect:
  1. **a+b/c triangulation or stereo of anything that moves relative to the head, including head rotation.**
     A same-index a/b pair is 50 ms apart, which is 2-3 px at typical head speed and 13-32 mm of depth at
     37 mm baseline (note 12). Use a[k+n] with the row-time model.
  2. **GT-supervised training or labels on moving frames** (marker detector D16, pose fitting): pair GT row k
     with b/c k+0.5 or a[k+1], never a[k].
  3. Stage C's contact/onset detector should report times in the b/c timeline. A cam-a-based onset at index k
     corresponds to b/c index ~k-1.
- The VERIFIED camera fact "match frames by frame_index" holds for b<->c only. **For cam a vs b/c it is wrong
  by 1 frame (sometimes 2).** The synthesis should correct this.

### Stage A summary (2026-10-06)
| quantity | result | label |
|---|---|---|
| b-c | 0.0 ms (-0.01 +- 0.09; epipolar LS +-0.33), same index always, hardware sync | [V] 39 clips |
| a-b (= a-c) integer pairing | a[k+1] ~ b[k] in 36/39 clips. p21: a[k+2] whole clip. p22: a drop (a[k+2] -> a[k+1] at b row 48). e20: b/c drop (a[k+1] -> a[k+2] at b row 49) | [V] |
| a-b sub-frame | cam a rolling shutter, 31.6 ms/height (top first). t(a[k+n], row y) - t(b[k]) = -9.8 + 31.6*y ms; per-episode sd 0.56 ms | [V] 39 clips; mono control flat |
| containers / capture_time | constant 20 fps PTS, equal counts, no per-camera timing. One capture_time per row; 3 public glitches, 1 coincides with a cam a drop | [V] |
| b/c rectification | residual constant vertical offset +0.66..+2.09 px, varies per episode | [V] 7 clips |
| GT rows vs streams | typical: GT instant = t(b[k]) + 25 ms (sd 0.85, n=6) = a[k+1] + (35 - 31.6*y) ms. Third reference clock; streams can sit +-1 frame off (p21 b +1, p22 a -1 before its drop) | [E] |

Open items / limitations:
- The GT-row model rests on 6 gate-passed objects from 6 episodes with GT-fitted frame-0 cameras and fixed C.
- Not tested: sub-frame b/c exposure-time effects, within-episode stability of the rectified dy, and drops
  shared by all streams in eval clips. The latter are invisible to video-only sync.
- The cause of the ~1-frame colour lag (arrival-time grouping vs ISP latency) is a hypothesis.

Reusable scripts are in `work/20/scripts/`:
- `a_motion.py` per-stream angular velocity
- `a_sync.py` offset fit
- `a_slide.py` slip localisation
- `a_slip.py` change point
- `a_rs.py` rolling shutter
- `a_epi.py` b/c epipolar
- `a_gtalign2.py` GT-row timing, analysis only
- `a_pairimg.py` image pairing check

Run any of them with `/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python work/20/scripts/<s>.py ...` from
`/Users/aebatirel/Documents/Code/v2d-research`. Runtime is ~5 s per stream per clip for `a_motion.py`.

Next (stages B/C, not started):
- B: spoon M1/M2/M3 marker positions. Use b/c stereo at the same index after the per-episode dy correction,
  and a[k+n] with the row-time model only if needed.
- C: automatic first-contact detector in the b/c timeline.


## Stage B — spoon marker stations from automatic stereo at rest (started 2026-10-06)
- Resume marker. Inputs: note 13 (Stage A ruler stations; Stage B/C frame-sign MC), 13-verify `v2_measured.py`
  (P(B) model with hand-read M1/M2 offsets: M1 lat 19-26 mm in-plane; M2 lat 13-20 mm, raised 6-15 mm toward the
  concave face -> P(B | mid-axis rule) 0.09-0.14), Stage A of this note (b/c same index; per-episode rectified dy;
  a[k+1] ~ b[k]). All 10 spoon eval clips (3,5,6,15,16,32,33,35,36,37) have a, b and c locally.
  New scripts `work/20/scripts/b_*.py`, outputs `work/20/out/b_*`.

### B1. Measurement pipeline and its validation on public GT (analysis-only use of GT)
- Pipeline (`work/20/scripts/b_lib.py`, `b_meas.py`; no GT, no hand labels; one generic threshold set for all clips):
  - Spheres are detected in cam a at frame a[k+1] (Stage A pairing; all 10 spoon clips have n=1 and no drops). Mask: S<45,
    60<V<235, next to a dark (V<60) base, inside the dilated hull of the saturated orange table. A trimmed algebraic circle
    fit gives the centre (r ~11-15 px).
  - Depth along each cam-a ray comes from a b/c NCC sweep. The pair is rectified as given (left = c) at 1600x1000 (rectified
    focal 600, above the native 565), and the per-frame rectified dy (+1.1..+2.8 px) is removed. The sweep is limited to
    heights -10..+60 mm above the table.
  - Table plane: corner matches give a rough plane, then SGBM disparities inside the table mask, then a RANSAC plane
    (3 mm threshold) within 16 cm of the spoon. About 10k inliers, rms 1.5 mm.
  - The spoon triple is chosen by 3-D distances: M1-M2 25-90 mm, M3 >100 mm from both, M1 = the one farther from M3.
- [V] Failed variants:
  - A full wood-colour mask: table glare (RGB 224/178/163) is colour-identical to the wood (234/198/173).
  - Corner-only or LK-grid table planes: ~120-200 points, and LK drifts along the grain (15% pass forward-backward), so
    marker heights jumped ~15 mm between frames.
  - 1-D SGBM fixed it: e37 heights are stable to ~1-2 mm over 5 frames.
- [V] Validation on public 23, frame 0 (wooden_piece_1/2: 7 scan-catalogue markers placed by GT; `b_valid.py`, `b_nccexp.py`):
  - 6/6 good detections matched. 3-D residual after the rigid fit: rms 2.5 mm (2.9 mm at frame 1).
  - Plank top surfaces by SGBM vs GT thickness: -1.7 and -0.9 mm. The table plane is sound.
  - Marker centre heights above the table vs GT, by depth estimator:
    - 21x21 NCC patch: -4.4 mm mean (biased; the patch is dominated by the base and the plank below the sphere).
    - Disc-weighted NCC (sphere disc r=6.5 mm, 1.5 px falloff): -2.0 +- 1.0 mm.
    - Same with r=5.5 mm: -1.4 +- 1.2 mm.
    - 11x11 and 9x9 patches: unstable (+-6 mm).
    That is ~-0.7 mm relative to the SGBM surface reference, which itself reads -1.3 mm vs GT; GT/catalogue error is
    ~1 mm. Adopted: disc-weighted NCC, r=6.0 mm.
- [V] More validation of the sideways case. Public 41: the white_pot wall marker #2 reads 43.8 mm vs GT 43.7. Public 11:
  cup-rim markers read 159.6-163.4 vs GT 150-159 (NCC only 0.57-0.81, near the clutter limit).
- [V] Spoon run, frames 0-3 of all 10 clips (`out/b/meas_e*.json`):
  - The triangle is rigid across 8 clips: M1-M2 53.5-57.7, M2-M3 151-156, M1-M3 194-199 mm. The +-2 mm spread is
    view-dependent (e5/e32/e37 ~57, e15/16/33/35/36 ~54).
  - M3 is missed in e3 and e6 (handle end at the table rim). In e15 one frame took a wrong third marker (rack sphere,
    rejected by its distances). M1 is weak in mono in e36 (NCC 0.88 vs 0.87 second peak).
  - Heights above the table:
    - Stable within each clip (+-1-1.5 mm over 4 frames).
    - M3 23-27 mm in every clip, so the handle end is raised. A tilted long axis matches cam a, which shows a gap between
      the handle and its shadow near M3.
    - M1 13.7-18.8 mm in the radial views (3, 5, 6, 32, 35, 37) and 19-25 mm in 15/16/36.
    - M2-M1 varies by clip from -3 to +8.6 mm (e5 +6..+9, e32 +8, e37 +5, e3/e6/e35 +1..+4, e33/e15/e16 ~0, e36 -2).
    So either the spoon rests at a clip-dependent roll about its long axis, or there is a view-dependent bias.
- [V] Cam-a profile midline (`b_geom.py`): cam a is sampled on table-parallel planes at height h, the wood edges are found,
  and a line is fitted to the edge midpoints. M3 lateral comes out 0 +- 3 mm (e33 fails at +15). BUT in all 10 clips the
  view ray points toward M1's side (M1 is always the far marker, as note 13 says). The cross-section view elevation is
  57-69 deg, so the measured asymmetry lat1-|lat2| moves by +0.8..1.3 mm per mm of the assumed centreline height
  (e5: -3.2 at h=8, +3.4 at h=16). At h=12 the clips give e5 +1.6, e32 +0.7, e16 +0.8, e37 +2.0, e35 +4.3, e36 -4
  (bad fit) and e33 +11 (bad fit).
  This is the parallax confound the 13-verify hand-read could not exclude. The view diversity is too small to solve it
  jointly. Next: measure the neck centreline height directly by row-wise stereo of the silhouette edges in the radial
  clips, and the roll from the bowl-rim edge heights.
- [V] Row-wise stereo of the silhouette edges (`b_estereo.py`, `b_edgevis.py`; works only where the spoon is >= 25 deg from
  the image rows, i.e. the radial clips 5, 32, 33, 35):
  - Handle (s = +95..+170 mm from the M1/M2 midpoint), e5/e32: far (M1-side) limb at h 11-13.5 mm, near limb at 4-7 mm.
    The centreline (mean) is 7.3-10.4 mm, the half-width 9.1-10.2 mm, and the limb split matches a round section seen at
    ~65 deg. So the handle is a ~19-20 mm round rod lying on the table (hc ~ rho).
  - The handle axis sits +2..+3.6 mm toward M1's side of the line mid(M1,M2)-M3. The bowl's silhouette centre is at
    -0.3..+1.8.
  - M3's centre is 23-27 mm above the table in all 8 clips, i.e. ~14-15 mm above the handle axis at the end. Laterally it is
    ~0-3 mm. So M3 is NOT on the long axis (note 13's model assumed it was): it sits on the upper (concave-side) part of the
    end face [V visual, `out/b/m3_views.jpg`].
  - Bowl edges, e5/e32/e33/e35 at s -85..-55: far (M1) side 14.5-18.8 mm, near (M2) side -1.3..+3.8 mm. Their mean is
    ~9-10 mm, which equals the handle-axis height.
- [E] Two readings of the rest pose, which matter for the sign question:
  - (R0) No roll. Relative to the handle axis, the horizontal lateral offsets in e5/e32 (robust here: the cam-a ray runs
    along the spoon, so depth error moves points along s/h, not w) are M1 17.4-18.0 and M2 19.4-20.0 mm. M2 is 1.4-2.1 mm
    further out. The heights above the axis are M1 +6..+8 and M2 +14..+15.
  - (R20) The spoon lies rolled 17-26 deg onto its M2 side. This is supported by the bowl edges straddling the axis height
    symmetrically. A round handle rolls freely, so the roll is set by where the bowl touches. Un-rolling gives, in the body
    frame: M1 lat ~19.5, x ~+1.5 mm (in-plane), and M2 lat ~12.4-13.7, raised ~14-21 mm toward the concave face (e5, e35).
    This matches the 13-verify frontal held-view reading (M1 in-plane, M2 on the concave-side shoulder).
  - Roll-invariant check: M1's distance from the axis is 18.5-20.0 mm in 5 clips. M2's is 18.6-24.9, so M2's height is
    the noisy measurement (mono NCC 0.68-0.79 in the radial views).
  The roll must be measured independently: held frames where the spoon faces the camera show the bowl plane directly.

### B2. Correction: the rectified vertical misalignment is a field, not a constant
- [V] `b_dyfield.py`: a quadratic dy(x, y) fitted to 2-D-localisable LK corner matches (rms 0.3-0.4 px) explains
  y_b - y_c far better than a constant (rms 0.6-1.0 px). Adding disparity barely helps.
  - In the spoon clips dy falls from 3.8 px (top-left, the room) to 0.8-1.5 px over the table. The global median Stage A
    reported (+2.4..+2.8 px for eval clips) is set by the room features, so the table/spoon region was mis-corrected by
    ~1-1.5 px.
  - Direct 2-D NCC on table patches (`b_dytable.py`, p23) gives 0.5-0.75 px, matching the field (0.5-0.7) and not the global
    1.09.
  - Effect: an oblique edge gets a disparity error of dy/tan(theta). The bowl's two sides lean opposite ways, so this made
    a spurious far/near height "cross" (tip: near side 22-27 mm, far 6-9; neck: reversed). It also biased the M2 NCC
    (M2's patch contains the oblique handle edge).
- `b_lib.rect_pair` now resamples b by the fitted field (residual dy ~0 everywhere). It is used by `b_meas.py` and
  `b_estereo.py`.
  - p23 re-validation: marker-vs-plank-top heights are unchanged (-0.4..-0.7 mm). The SGBM table plane moved up ~2.2 mm
    relative to both, so the absolute table offset is uncertain by ~2 mm. Only the plane normal and axis-relative
    quantities matter for the spoon.
- [V] Re-run (`out/b/run2_meas.log`, `b_sum1.py`, 28 frames in 8 clips; e3/e6 lack M3):
  - Triangle M1-M2 53.0 +- 1.6, M2-M3 153.2 +- 0.6, M1-M3 194.2 +- 1.5 mm. M1-M2 is view-dependent: e33/e35 50.5-50.9,
    others 52.6-54.7.
  - Heights h1 16.5 +- 3.7, h2 16.5 +- 2.3, h3 20.4 +- 2.1 mm.
  - h2-h1 per clip (within-clip sd 0.4-1.2): e5 +4.1, e32 +3.8, e36 +0.3, e15 -0.2, e16 -0.3, e35 -2.4, e33 -2.8,
    e37 -3.5. A clip-to-clip roll of ~+-5 deg, or a view-dependent M1 depth bias (M1's sphere is nearly invisible in mono;
    NCC depth width 4-10 mm vs 3-4 for M2).
- [V] Edge stereo with the field (e5, e32):
  - Handle limbs: far 10.5-12.0, near 4.1-6.2 mm; centreline 7.4-9.0 mm. A split of +-3.1 mm for rho ~9.8 implies
    alpha ~71 deg, matching cam a (68 deg). So the round handle lies on the table.
  - Bowl, far (M1) side: 13-16.5 mm along the bowl, ~11-12 mm toward the neck. Near side: 8.7-15 mm at the tip half,
    falling to 1.5-5 mm toward the neck. No tip crossing remains.
- [E] Rest views cannot fix the roll. On a convex bowl wall seen from above-near, the near silhouette is the wall point
  whose normal is perpendicular to the view, below the rim; the far silhouette is the rim. So far > near is expected from
  bowl curvature alone, and the far/near difference does not scale with the half-width as a planar roll would. The rest
  views fix the triangle, the handle axis and the heights, but not the body x direction. Next: held frames with the bowl
  facing the camera, where the rim plane is seen directly.

### B3. Body-frame offsets: what the rest views fix, and the roll they do not
- [V] Marker offsets relative to the stereo handle axis (`b_axisrel.py`; axis = line through paired handle-limb midpoints,
  s +100..+160 mm, extrapolated to the stations). Only e5 frames 0-2 are clean (71-72 rows, residual w/h 0.2-0.4/0.7 mm).
  e5 frame 3 and e32 have 11-34 rows with h-residuals of 1.3-2.8 mm: unusable.
  - e5 frames 0-2, table frame (w horizontal toward M1's side, h up), mm:
    - M1: w +19.4..+19.7, h +5.4..+6.6
    - M2: w -16.1..-17.5, h +8.4..+11.7
    - M3: w -1.3..-1.5, h +10.1..+11.2
    - handle radius 9.8-9.9; axis h(s=0) 7.1-7.2
  - The asymmetry depends on the axis definition. The handle line alone gives M1 further out by ~2.8 mm. A joint line
    through the handle midpoints and the bowl silhouette centre (-1.0 at s -90 after the dy fix) gives ~0.4 mm.
    [E] Table-frame lat1 - lat2 is between 0 and +3 mm.
- [V] All three markers sit ABOVE the handle axis at rest, toward the concave face if roll ~0: M1 ~+6, M2 ~+10, M3 ~+11 mm.
  M3 is not on the long axis.
- [V] Held-frame route (`b_held.py`): whole-image cam-a detection, a free b/c depth sweep, the triple matched to the rest
  triangle, and a wood/skin check. In ep36, frames 196/202 are near-frontal (triangle normal . view 0.87-0.92), held
  horizontal over the table with the concave face toward the camera. The first pass found false triples on background
  shelving (frames 226/256); a wood-fraction test now rejects them. The full ep36 scan is running.
- [V] `b_heldgeom.py` on rest frames is roll-biased: the rim-pair lateral direction uses the near-side wall silhouette. It
  gives M1 lat 18.9-20.0 and M2 15.3-16.7, but the out-of-plane values drift ~10 mm across frames because the handle line is
  extrapolated ~120 mm to the neck.
- [V] Rest roll from the FAR rim only (`b_rimfit.py`). The far silhouette is the true rim. Fitting h = a + b s + c w to
  far-side bowl points (s -132..-40 mm) separates roll from pitch, because w follows the oval.
  - e5 frames 0-3: roll +1.5, -2.0, -1.0, -4.1 deg (bootstrap +-2.4-3.4 each), pitch -2.0..-3.9 deg (bowl tip up), residual
    0.9-1.2 mm.
  - e32 frames 0-3: -9.4, +2.8, -5.4, -4.9 deg (+-2.5-4.6).
  - e33/e35: garbage (-52 deg, a = 18-20 mm), from few and contaminated far-side rows; excluded.
  - [E] Rest roll ~ -2.5 +- 3 deg (M1's side, if anything, slightly down). That is physically expected for a spoon resting
    on its convex bowl back. So the R20 reading is rejected, and the large far-near bowl difference is the wall effect, not
    roll. Rim plane at the neck: 0-4 mm above the handle axis.
  - Body frame ~ table frame. In model terms (x to the convex back):
    - M1: lat ~19.5, x ~ -6 (raised 6 mm toward the concave face)
    - M2: lat ~16.8, x ~ -10
    - M3: lat ~ -1.4 (toward M2's side), x ~ -11
    - lat1 - lat2 ~ +2.8 mm (handle-axis line) or ~+0.4 (joint handle+bowl line, which the bowl wall biases). Roll
      correction (h1 + h2) sin(phi) ~ -0.7 mm.
- [V] Cross-check: cam-a profile midline at the measured centreline height (`b_geom.py`, plane h = 7.2 mm in the
  dy-field table frame, where the midline is unbiased for a round section).
  - Excluded: e33 (M3 lateral +15, fit broken) and e32 frame 3 (bad heights).
  - lat1 - lat2 per clip (frame means): e5 +1.2, e35 +0.7, e16 -0.8, e32 -1.2, e36 -1.5 (fit rms 1.3-2.7), e37 -1.9
    (fit rms 2.3). Across clips: -0.6 +- 1.25 mm.
  - M3 lateral across clips +0.5 +- 1.5 mm.
  - Stations from the bowl tip (h 7.2; e32's tip is wrong): M1 116-125, M2 159-167 (M2-M1 = 40-43 mm), M3 311-319 mm.
  - Per-clip plane offsets of +-2 mm bias each clip by +-(1.6-2.6) mm, which explains the spread.
- [E] Combined lateral asymmetry lat1 - lat2 = +0.5 +- 1.5 mm. The handle-line extrapolation (e5) says +2.8; cam-a
  midlines in 6 clips say -0.6. It is NOT the +4..+9 mm that the 13-verify hand-read (rest views with parallax, held
  frames) used to flip the verdict to frame A.
  - lat1 ~ 19.0 +- 0.6 mm, lat2 ~ 18.5 +- 1.5 mm.
  - Out-of-plane, all toward the concave face: M1 +6 +- 1.5, M2 +10 +- 2, M3 +11 +- 1.5 mm.
  - Roll -2.5 +- 3 deg.
  - Absolute heights in the dy-field frame read ~2.5 mm low (axis at 7.2 mm vs handle radius 9.8, the same offset as the
    p23 re-validation). Relative values are unaffected.

### B4. Frame-B probability with the measured layout (`b_pb.py`, summary `b_pbsum.py`; running)
- Model: note 13 round-handle bodies (handle radius tightened to the measured 9.5-10.5 mm, L 295-312 mm), stations M1
  113-125 and M2 = M1 + 41-44 mm from the tip. Table-frame offsets relative to the handle axis are rotated by the rest roll
  phi into the body frame. M3 is raised 9.5-12 mm toward the concave face, 2-10 mm beyond the end face.
- Rules: note 13 `b_spoon.rules` (note-07 x and y skew, hybrid(0.02), larger-|skew| cascade, noisy single-statistic models,
  15 F2, F2b, 154 F3 hybrids) plus the noisy mid-axis rule with the c_noisy posterior over n (13-verify method).
- [V model] Layout 'meas' (handle-line asymmetry, lat1 - lat2 ~ +1.9 +- 1 mm), 13 bodies per roll:

  | roll phi | toM2 skew mean | P(toM2>0) | noisy mid-axis P(B) | x-skew | larger-abs | hybrid .02 | F2 share | F2b | F3 |
  |---|---|---|---|---|---|---|---|---|---|
  | -10 | +0.035 | 1.00 | 0.86 | 1.00 | 1.00 | 1.00 | 0.86 | 0.46 | 0.93 |
  | 0 | +0.003 | 0.46 | 0.53 | 1.00 | 1.00 | 0.92 | 0.68 | 0.46 | 0.68 |
  | +10 | -0.027 | 0.08 | 0.20 | 1.00 | 1.00 | 0.31 | 0.78 | 0.38 | 0.32 |
  | +20 | -0.049 | 0.00 | 0.08 | 1.00 | 1.00 | 0.08 | 0.93 | 0.31 | 0.17 |

  - Every x-based rule says B at every roll: x skew toward the concave face is +0.10..+0.33, because the raised M2 and M3 add
    concave-side mass. That includes far3d_x, which note 13 called a coin flip: the farthest vertex is now M3's concave-side
    cap.
  - The mid-axis (y) rule is a coin flip at roll 0 for this layout, and turns A for phi > +5 deg.
- [V] The handle and the bowl are not collinear in plan. With a HANDLE-ONLY midline (cam-a profile at h = 7.2, stations
  M2+20 .. M3-12 mm, extrapolated), radial e35 and transverse e16/e36/e37 agree. Relative to the handle line:
  - M1 lateral 16.3-19.4 (~18.5), M2 14.4-16.7 (~15.4), so lat1 - lat2 ~ +3.1.
  - M3 -2..-5 (toward M2).
  - The bowl silhouette centre is +4.4..+6.2 mm toward M1.
  3-D stereo (`b_bend.py`, no plane projection) on e5 frames 0-2 and e32 frames 0-1:
  - bowl centre vs the handle line +0.9, +1.3, +1.5, +3.3, +0.4 mm
  - lat1 - lat2 +3.5, +1.9, +2.9, +3.7, -0.1
  - M3 -1.3..-3.0
  The cam-a bowl value carries an estimated +1..+2 mm parallax bias (the far rim lies 6-9 mm above the projection plane).
  The near-wall artefact would push the other way (toward M2), so it does not explain the offset. Same sign in radial and
  transverse views. [E] A real in-plane bend/offset of the bowl toward M1 of +2.5 +- 1.5 mm at the bowl centre (~1 deg).
  The whole-body midline (-0.6 asymmetry) is a compromise between two non-collinear parts.
- [E] Final measured layout relative to the handle axis (body frame ~ table frame, roll -2.5 +- 3 deg), mm:
  - M1: lat 18.9 +- 0.6, raised 6 +- 1.5 toward the concave face
  - M2: lat 15.9 +- 0.7, raised 10 +- 2
  - M3: lat -1.9 +- 1.2 (toward M2), raised 11 +- 1.5, 2-10 mm beyond the end face
  - Bowl offset toward M1: +2.5 +- 1.5
  - Stations from the bowl tip: M1 116-125, M2 = M1 + 40-43 mm
  - Triangle: 53.0 / 153.2 / 194.2 mm
- Smoke test [V model, 1 body]: a 5 mm bowl offset toward M1 drives toM2 to -0.028 (frame A) even at roll -5 deg. So the
  bend is a sign-relevant asymmetry of the body itself, as strong as the markers.
  Running: `b_pb.py` layouts hl_bend0 / hl_bend3 / hl_bend5 (40 bodies each).
- [V] Bowl tip (`b_geom.py` tip_vs_handleline; median midline 6-14 mm in from the tip): +8.1..+9.4 (e35), +6.4..+7.5
  (e16, e37), +13 (e36, one frame) mm toward M1 relative to the handle line. That is more than the bowl centre
  (+4.4..+6.2), so the bowl is angled toward M1 rather than shifted. Tip/bowl ratio 1.4-1.5: a pure shift gives 1.0, a
  pure extrapolation-angle error 1.2, a rotation about the neck 1.56.
- [E] Parallax correction. All clips view the cross-section at alpha 57-70 deg, so a cam-a point h mm above the
  projection plane shifts (h - 7.2) cot(alpha) ~ 0.36-0.65 mm/mm toward the far (M1) side.
  - The tip is raised (rim pitch ~3 deg tip-up), giving +3..+4.5 mm of bias: tip corrected ~ +4 +- 1.5 mm.
  - The bowl centre has +1.5..+2.5 mm of bias: corrected ~ +3 +- 1 mm.
  - 3-D stereo (no parallax) gives ~ +1.2; a near-wall bias of 0.5-1.5 mm toward M1 could push that toward 0..+1.
  - [E] Bowl offset toward M1: +2 +- 1.5 mm at the bowl centre (bend ~0.5-1.5 deg). The sign agrees across methods; the
    size is uncertain at the level that matters for the y rule.
- [V] Held near-frontal frames (`b_heldgeom.py`, ep36 cam-a frames 191-195; fingers on the handle make the axis fits poor,
  rms 2.9-4.5 mm):
  - lat1 - lat2 +8.1, +4.4, +3.8 mm
  - M3 -1.5..-2.4
  - bowl centre +2.5, +0.1, -1.5
  They agree in sign with the rest handle-line values. Frame 189 was a broken fit.
- [V] End-of-clip rests (`out/b/meas_e{37,35,3}_end.json`, `geom_e*_end.json`; spoon released per note 13):
  - Triangle 53.3-55.5 / 152.7-154.0 / 194.2-196.5 mm.
  - Relative to the handle line: lat1 - lat2 +3.7, +2.5 (e37); +1.5, +4.2 (e35); +2.4 (e3 frame 306); M3 -0.5..-3.9.
  - Bowl vs line: +5.0..+6.3 (e37, e35), +1.6 (radial e3, frame 306; frame 310 inconsistent). Tip +7.2..+12.8 (e37/e35),
    +3.3 (e3).
  - So the asymmetry and M3 are stable over 9 clips. The bend size is view-dependent (+1.6 radial .. +6 diagonal and
    transverse), i.e. partly parallax.

### B4 results (`b_pbsum.py`, `b_pbreg.py`; 40 bodies per layout unless noted)
Layouts (markers relative to the handle axis; roll ~ N(-2.5, 3) deg drawn per body):
- hl_bend0/2/3/5: lat1 18.9 +- 0.6, lat2 15.9 +- 0.7, M3 lat -2.5 +- 1.2, with a bowl offset toward M1 of 0 / N(2, 1.5) /
  U(1.5, 4.5) / U(4, 6.5) mm.
- final: whole-body-midline asymmetry +0.5 +- 1.5, no bend.

| layout | toM2 mean [p10, p90] | noisy mid-axis P(B) | y-skew | x-skew | hybrid .02 | larger-abs | q10_y | -shalf_x | far3d_x | F2 | F2b | F3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **hl_bend2 (central)** | -0.015 [-0.049, +0.011] | **0.33** | 0.23 | 0.97 | 0.60 | 0.82 | 0.30 | 0.38 | 1.00 | 0.32 | 0.20 | 0.47 |
| hl_bend0 | +0.012 [-0.009, +0.034] | 0.65 | 0.75 | 0.97 | 0.93 | 0.97 | 1.00 | 0.45 | 1.00 | 0.40 | 0.35 | 0.73 |
| hl_bend3 | -0.023 | 0.24 | 0.15 | 0.95 | 0.40 | 0.80 | 0.12 | 0.50 | 1.00 | 0.41 | 0.17 | 0.39 |
| hl_bend5 | -0.040 | 0.13 | 0.03 | 0.97 | 0.23 | 0.78 | 0.00 | 0.60 | 1.00 | 0.49 | 0.15 | 0.35 |
| final (asym +0.5, no bend; 100) | +0.035 | 0.83 | 0.95 | 0.98 | 0.99 | 0.98 | 0.97 | 0.47 | 1.00 | 0.57 | 0.47 | 0.79 |
| scan WITHOUT markers, bend 2 | -0.039 | 0.16 | 0.07 | 0.93 | 0.15 | 0.65 | 0.07 | 0.95 | - | 0.70 | 0.82 | 0.22 |
| scan without markers, no bend | 0 (exact tie) | 0.50 | tie | 0.95 | - | - | - | - | - | - | - | - |

- z: bowl -> handle in 100% of bodies (no z flips). The mid axis is the lateral axis in 100%.
- [V model] Sensitivity of toM2 (pooled regression, n 160, R2 0.92, residual sd 0.008):
  - -0.0152 per mm of lateral asymmetry (M1 further out)
  - -0.0088 per mm of bowl offset toward M1
  - -0.0028 per deg of roll (M1 side up)
  - +0.0040 per mm of M2 height toward the concave face
  - -0.0011 per mm of M1 height
  - M3 lateral -0.0012/mm; bowl depth, handle offset and stations < 0.002 per sd
  At the central values toM2 ~ -0.012, with combined uncertainty sd ~0.025 (asym +-1, bend +-1.5, roll +-3, h2 +-2,
  body). P(toM2 > 0) ~ 0.32. The zero crossing needs the asymmetry 0.8 mm smaller or the bend 1.4 mm smaller than the
  central values: well inside the measurement uncertainty.
- [E] Reading:
  1. Under note 13's best-supported convention (largest and middle axes signed by positive skew, Track 2 holdout), the
     measured spoon gives P(B) ~ 0.33 (bracket 0.13-0.65 over the bend uncertainty). It is a near-tie leaning A, driven
     by (a) M1 sitting ~3 mm further out than M2 relative to the round handle and (b) the bowl angled ~1 deg toward M1.
     It is NOT the confident A of 13-verify (0.09-0.14). That rested on a +4..+9 mm asymmetry read with parallax, and
     treated M3 as on-axis.
  2. Every x-skew-based rule gives B (0.93-1.00), because the measured layout has all three markers raised toward the
     concave face (M3 by ~11 mm, new). That makes x skew toward the concave face strongly positive (+0.06..+0.08), and
     far3d_x becomes informative (B).
  3. If the organisers' scan lacks the markers, the bend alone sets the y bit: P(B) ~ 0.16 (bend 2 mm) .. 0.5 (no bend).
  4. Overall, mixing rule classes (e.g. 0.6 mid-axis, 0.2 x-skew, 0.2 unknown/random): P(B) ~ 0.45-0.5, a coin flip.
     The spoon frame remains an organiser question. The cheapest falsifier of the bend is a direct top-down or frontal
     measurement, for example a stereo fit of the full rim in a frame with the bowl normal within ~10 deg of the view.

### Stage B summary (2026-10-07)
| quantity | result | label |
|---|---|---|
| Pipeline | cam-a sphere detection (generic thresholds) + disc-weighted b/c NCC depth along the cam-a ray (a[k+1] pairing) + SGBM table plane + dy-field rectification + row-wise edge stereo | [V] public validation: p23 marker 3-D rms 1.8 mm; heights vs GT -1.7 mm (global dy) / -4.1 mm (dy field, table-offset shift); sideways pot marker 0.1 mm |
| Rectification | b/c vertical misalignment is a smooth field: 3.8 px (room) to 0.8-1.5 px (table). The Stage A global dy mis-corrects the table region by 1-1.5 px | [V] field rms 0.3 px; direct table NCC agrees |
| Triangle | M1-M2 53.0 +- 1.6, M2-M3 153.2 +- 0.6, M1-M3 194.2 +- 1.5 mm (28 frames, 8 clips; +3 end rests) | [V] |
| Handle | round, radius 9.8-10 mm, lying on the table at rest | [V] edge stereo; limb split matches the view angle |
| Rest roll | -2.5 +- 3 deg from the far-rim plane fit; bowl pitched ~3 deg tip-up. The R20 "rolled" reading is rejected | [E] e5/e32, 8 frames |
| Marker offsets vs the handle axis | M1 lat 18.9 +- 0.6, +6 up; M2 lat 15.9 +- 0.7, +10 up; M3 lat -2 +- 1.2, +11 up (toward the concave face), 2-10 mm past the end | [V] lateral (9 clips); [E] heights (e5; all-clip mean M1 ~ M2 ~ +9) |
| Lateral asymmetry lat1 - lat2 | +2.5..+3.5 vs the handle line (stable over 9 clips; stereo +2.4); ~0 vs the whole-body midline | [V] |
| Bowl vs handle (in-plane) | bowl centre +2 +- 1.5 mm toward M1 (tip further), ~1 deg bend; size view-dependent (+1.6 radial .. +6 transverse, partly parallax) | [E] |
| P(B), mid-axis noisy rule | 0.33 central (0.13-0.65 over the bend; 0.83 if no bend and asymmetry 0.5) | [V model] [E] inputs |
| P(B), x-skew rules (note 07, larger-abs, far3d_x) | 0.93-1.00 | [V model] |
| P(B), F2 / F2b / F3 families | 0.32 / 0.20 / 0.47 (central) | [V model] |
| P(B), scan without markers | 0.16 (bend 2) .. 0.5 (no bend), mid-axis rule | [V model] |
| Overall | ~0.45-0.5 across plausible rule classes; mid-axis convention leans A (~2:1) | [E] |

Corrections to earlier notes:
- 13-verify's "measured layout -> P(B | mid-axis) 0.09-0.14" overstated the asymmetry. Its +4..+9 mm hand-read was
  parallax-confounded: in all 10 rest views M1 is the far marker. The automatic, axis-referenced asymmetry is ~+3 mm vs the
  round handle.
- Note 13's model ("M3 on the axis", "M1/M2 in-plane at the edge") is wrong in a sign-relevant way. All three markers sit
  above the handle axis toward the concave face, which fixes the x bit as B under x-skew rules.
- The new decisive unknown for the y bit is the bowl-vs-handle in-plane alignment (bend, +2 +- 1.5 mm).
- Stage A's "rectified dy constant per episode" must be replaced by a dy field for any stereo below the horizon (table,
  hands, objects).

Open items:
- Bend size. A near-frontal view of the full rim (bowl normal within ~10 deg of the view) with the dy field would settle it.
  The held frontal frames in ep36 (cam-a frames 191-209) have fingers over the handle (axis rms 3-4.5 mm), so they were not
  decisive.
- M1/M2 heights differ by clip (h2-h1 from -3.5 to +4.1 mm, within-clip sd ~1). This is either per-clip roll noise or M1's
  weak mono contrast (NCC depth width 4-10 mm); the model sensitivity to it is small (+0.004/mm on h2).
- The organisers' rule and whether their spoon scan includes the markers. Unchanged: ask them; no leaderboard A/B.

Scripts (`work/20/scripts/`):
- `b_lib.py`: calibration, rectification, dy field, `rect_pair`
- `b_meas.py`: markers + table plane per frame
- `b_valid.py`, `b_nccexp.py`, `b_dyfield.py`, `b_dytable.py`: validation
- `b_estereo.py`, `b_edgevis.py`, `b_axisrel.py`, `b_bend.py`, `b_rimfit.py`: edge stereo
- `b_geom.py`: cam-a profile midline, stations, tip
- `b_held.py`, `b_heldgeom.py`: held frames
- `b_pb.py`, `b_pbsum.py`, `b_pbreg.py`: P(B)
- `b_sum1.py`: summary

Outputs are in `work/20/out/b/` (meas_*.json, estereo_*.json, geom_*.json, held_e36*.jsonl, heldgeom_*.jsonl,
pb_*.jsonl, run2_meas.log). Run them with `/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python` from `work/20/scripts`.
Stage B status: COMPLETE except the pending 'model' reproduction run, appended below when done.
- [V model] Reproduction check, 'model' layout (note 13 placement: M1/M2 in-plane at the edge, M3 on the axis), 20 bodies:
  noisy mid-axis P(B) 0.88, y-skew 1.00, x-skew 0.85, F2 0.96, F2b 0.90, F3 0.78. These match note 13 (0.90; x 0.90; F2
  0.94-1.00; F2b 0.97) and 13-verify (0.92). So the P(B) machinery is consistent, and the differences above come from the
  measured layout.
- [V model] Layout 'meas_jointaxis' (asymmetry ~0 vs the whole-body midline, no bend, roll grid; 30 bodies): mid-axis
  P(B) 0.97 / 0.90 / 0.63 at roll -10 / 0 / +10 deg. So the "no asymmetry, no bend" end of the range is a confident B.
Stage B status: COMPLETE (2026-10-07). Background jobs: none left running.

## Stage C — automatic first-contact detector for the slot-0 anchor window (started 2026-10-07)

(status: COMPLETE 2026-10-07; see "Stage C summary". Scripts `work/20/scripts/c_*.py`, outputs `work/20/out/c/`.
The re-run section "Stage C re-run" further down replaces the GT-rendered validation masks with GT-free ones and adds
p45 plus all 20 eval clips; scripts `r_*.py`, outputs `out/c2/`.)

### C0. Setup and reference
- Reference ("truth") = public GT first perturbation of slot 0: first row with >1 mm or >1 deg change from row 0
  (`work/15/c2/preonset.py` -> `preonset.out`), plus the 1 cm onset. Detector frames are reported in the b/c
  index timeline; GT row k is ~25 ms after b[k] (Stage A6), so b/c index k ~ GT row k (half-frame bias ignored).
- Frame-0 slot-0 mask for validation = GT mesh rendered with the DIG 18 map camera of frame 0 (a8 registration +
  a10 per-episode offset, residual ~0.2-0.3 cm median; 19 public eps, p45 not in the map). This stands in for the
  perception stack's frame-0 segmentation; the detector itself never reads GT after frame 0 (analysis-only harness).
- Images: D18 undistorted pinhole cam a (1014x760, f=500) and b/c (1280x800, f=420).
- [V] GT reference check (`c_lib.gt_ref`): slot 0 = first object of the parquet row (as preonset.py; the schema
  metadata order differs in p11 and p18, which would give the wrong object). Mocap frame-to-frame jitter of slot 0
  in static frames is 0.01-0.15 mm (median 0.03), so the 1 mm / 1 deg first-perturbation reference is not noise.
  Several anchors drift 0.4-0.8 mm / 0.2-0.7 deg before it (light touches; p0, p12, p27, p44), and p26's rack is
  bumped at f3 (1.3 mm, 0.5 deg) with no hand near it (not a hand contact).
- [V] Visual check of frame-0 masks (D18 camera) on p0, p11, p12, p22, p24, p26, p31, p44 (`c_sheet.py`,
  `out/c/sheet_p*.jpg`): outlines sit on the objects at f0; the head moves enough by f9-f12 (tens of px) that the
  mask must be tracked. Typical sequence: hand enters the object's neighbourhood 5-20 frames before the GT
  perturbation, fingers rest on/around the object for 2-12 frames (p11: ~12; p44: both hands around the pot ~10),
  then the 1 mm / 1 deg perturbation.

### C1. Detector v2 (`c_detect.py` features, `c_eval.py` rules; no GT read after frame 0)
- Cam a colour, D18 pinhole. ROI = frame-0 mask bbox + 0.6 x size + 40 px.
- Registration frame 0 -> k: KLT from frame 0 (prediction from the previous homography), forward-backward check
  (<1 px), RANSAC homography (2.5 px) on the static neighbourhood; the hand is an outlier.
- Change: per-channel exposure gain, then colour |I_k - warp(I_0)| minimised over +-3 px shifts (absorbs the
  object-vs-table parallax of a few px), threshold 28, 3x3 opening, undistortion border excluded.
- Per frame: `touch` = area within 8 px of the object of changed components that also extend >=30 px outside it
  (an intruder); `overlap` = intruder area inside the eroded object; `inside` = change confined to the object
  (object motion or self-occlusion); `dmin` = intruder distance; registration inliers and residual.
- Decision (tuned below): first frame of a 2-frame run above threshold, cam-a index -> b/c index with the Stage A
  pairing (a[k+n] ~ b[k]); anchor window = rows [0, c_bc - 3].
- [V] Two GT-reference problems (found on the first runs). (1) Single-row mocap spikes and ~1 deg marker-fit steps
  pass the 1 mm / 1 deg test: p2 row 26 is a 2.9 mm one-row spike with both hands far from the pot; p18's sweeper
  shows a 1.0-1.1 deg plateau at rows 20-26 that returns to 0 at row 27 with no hand near it. (2) A perturbation is
  not a hand contact: p26's rack is bumped at row 3 and p0's pot moves when the LID is lifted. So a robust reference
  is added: >1.5 mm or >1.5 deg sustained for 3 rows (`pert_r`). Raw / robust: p0 64/109, p2 26/112, p12 31/33,
  p18 20/33, p22 15/17, p40 31/40, p44 63/74; equal or +1-2 elsewhere. Both are reported.
- [V] Early 2-D proximity is common. With the v2 `touch` rule (120 px, 2 frames) on the first 8 eps the contact
  fires 5-32 frames before the raw perturbation in 6/8 cases. It fires at f1 in p24 (the hand slides along the
  table next to the board from f0), which leaves an EMPTY window. The two "late" cases (p2 +10, p18 +11) are the
  GT artefacts above: the detector fires 2 frames before p18's real contact (row 33).

### C2. Object-motion detector (`c_motion.py`; no GT after frame 0)
- Per step k-1 -> k: KLT points in a ring around the object -> RANSAC background homography (cancels head
  motion); KLT points inside the eroded object -> RANSAC similarity of the background-predicted points to their
  tracked positions = object motion relative to its surroundings. Step magnitude = centroid shift + rotation x
  object radius (px; ~1 px per mm at 0.5 m in the f=500 pinhole). Short steps keep parallax sub-pixel. The masks
  are carried by the background homography.
- [V] Static noise is 0.6-1.0 px per step (larger on the big pots, where rotation noise x r0 ~ 200 px dominates).
  Onsets are abrupt and match the robust GT reference in most clips. Cam-a index -> b/c index (n = 1):
  p13 a22 vs pert 21, p23 a19-20 vs 18/19, p24 a9 vs 8, p31 a26 vs 26/28, p39 a47-48 vs 46, p40 a32 (single
  2.9 px step = the real 1.7 mm step at row 31), p41 a29 vs 26/27, p42 a33-36 vs 32/34, p43 a27 vs 23/25,
  p44 a75-77 vs 74, p12 a34-36 vs 31/33, p18 a34/a38 vs 33.
- [V] Failure modes: p11 misses the 2.9 mm / 3.7 deg tilt at row 30 (steps <=1.3 px: hand covers the cup, and a
  tilt is out of plane for a similarity). p0/p2 fire when the LID (inside the pot's silhouette) is lifted, 8-50
  frames before the pot itself moves (early = safe). p21/p22 have 2-4 px spurious steps from hand occlusion
  before their onsets (early = safe).
- [V] Head-motion gate: the spurious steps happen during fast head motion (p21 a3-6 and a23-27, p22 a12-13 and
  a19-23: background flow 5-20 px/step; the ring mixes the table with the floor behind, so parallax leaks in).
  Real onsets have background flow 0-4 px. Rule: a step counts if mm >= T + kappa * flow_px
  (T = 2 mm, kappa = 0.15). This removes all of them but also hides p22's real 2.5 mm slide at rows 15-18
  (it happens during a 13-20 px head sweep), so motion alone would be 25 frames late there.

### C3. Combined rule and validation on 19 public eps (`c_eval2.py`, out `out/c/eval2_MC_A120_T2_L10_m3.json`)
- Rule MC: c_a = min(M, C + 10). M = first object-motion step >= 2 mm + 0.15 x flow; C = first frame of a
  2-frame run with touch >= 120 px. Then c_bc = c_a - n (Stage A pairing) and window = rows [0, c_bc - 3].
- [V] Onset error c_bc - GT, 19 eps:
  - vs raw perturbation: median 0, p10/p90 -20/+17, range [-44, +20]; the window end reaches the raw pert in 3
    eps (p2 and p18 are the GT artefacts; p26 is the no-hand rack bump at row 3);
  - vs robust perturbation: median -4, p10/p90 -57/+1.6, range [-67, +16]; late in 2 (p18 window end 34 vs
    33 = +1 row; p26 rack +16).
  - Within +-2 frames of the raw reference in 9/19 (p12 p13 p21 p22 p23 p24 p31 p40 p42); of the robust one in
    6/19. Otherwise early by 3-67: lid lifts in p0/p2; the contact bound in p11 p27 p41 p43 p44; a hand pause in
    p39. The exceptions are p18 (+4 vs robust, window end 1 row late) and p26.
  - No empty windows. Median window 23 rows (oracle 26 raw / 33 robust).
- [V] Anchor bias of the averaging window (GT mean pose over the window vs GT row 0; induced shift = mean
  displacement of all object centres when the scorer aligns on the biased anchor):

  | window | rows (median) | dt mm med/p90/max | dR deg med/p90/max | induced shift mm med/p90/max |
  |---|---|---|---|---|
  | detector MC [0, c_bc-3] | 23 | 0.13/0.46/2.20 | 0.14/0.34/0.59 | 0.28/0.65/1.76 |
  | oracle [0, pert-1] | 26 | 0.14/0.37/0.58 | 0.10/0.23/0.49 | 0.35/0.54/1.06 |
  | oracle robust [0, pert_r-1] | 33 | 0.19/0.36/0.58 | 0.15/0.28/0.47 | 0.33/0.56/1.18 |
  | up to 1 cm onset [0, on-1] | 41 | 0.57/1.61/3.67 | 0.33/1.18/2.02 | 0.94/2.55/3.56 |

  The detector window is at oracle level; its worst case is the p26 rack (bumped at row 3 with nobody near:
  2.2 mm / 0.59 deg). The up-to-1 cm window is worse by >=1 deg only in p11 (1.71 -> 0.21), p13 (1.04 -> 0.06),
  p31 (2.02 -> 0.03); p22 1.05 -> 0.49. Averaging dilutes the 1-8.6 deg pre-onset maxima of note 15 to a median of
  0.33 deg. Against note 15's falsification test (pre-contact better by >=1 deg) the fix matters in 3/19 clips only.
- [V] Official AUC (kit `score()` via `work/11/sc11.py`) of an otherwise exact tracker whose anchor is the window mean:
  exactly 1.0 for every window (all induced errors < 1 cm, the first threshold). With a 3 cm random base error on
  every other row/object (base AUC ~0.80; 4 seeds), dAUC vs an exact anchor is: detector mean +0.0000 (min
  -0.0008), oracle -0.0000 (min -0.0007), up-to-1 cm -0.0008 (min -0.0031). [E] The anchor window is worth
  ~0.001 board AUC on average and up to ~0.003 per clip: a hygiene item, not a lever. The fixed 15-frame window is
  the dangerous one where the onset is early (p24: 9.2 mm, 2.3 deg).
- [V] Sensitivity and over-fitting check (`c_grid.py`, `out/c/grid.log`). Grid: T 1.5-3 mm, kappa 0-0.25, L 5-40,
  A 60-240 px.
  - With L = 10: 1-2 late windows, max dR 0.59 deg, mean induced shift 0.33-0.41 mm, flat in T / kappa / A.
  - L = 20: 2-5 late; L = 40: 4-7 late, max dR ~1.1 deg. The contact bound is what keeps the tail small.
  - Leave-one-episode-out (params chosen on 18 eps by mean shift + 0.002 x slack, scored on the held-out ep): late 2,
    empty 0, median window 18 rows, max dR 0.54 deg, p90 0.30 deg, mean shift 0.31 mm. Picks: L = 5, T 1.5-2,
    kappa 0 (14/19 identical). Not over-fitted.
- [V] Contact-only detector (C, `touch` >= A px for 2 frames), onset error vs GT perturbation:
  - A = 120: raw median -8 frames, p10/p90 -30/+8; robust median -14, p10/p90 -67/-5. 1 late (p26 rack bump), 1
    empty window (p24). The flat range A = 60-240 gives the same results.
  - Per ep (raw): p0 -32, p2 +10*, p11 -22, p12 -12, p13 -6, p18 +11*, p21 -5, p22 -8, p23 -6, p24 -7, p26 +7*,
    p27 -30, p31 -4, p39 -16, p40 -8, p41 -16, p42 -9, p43 -17, p44 -54. * = GT artefact or no-hand bump.
  - Contact precedes the >1 mm perturbation by a median ~8 frames (0.4 s): hands rest on or around the object before
    moving it. This is why the motion signal, not contact, should end the window.
- Motion-only (M) robust-onset error: median 0 to +1; within +-2 frames in 10/19 (11 within +-3). It is late in p11 (+76, tilt in
  hand), p22 (+25, slide hidden by the head-motion gate), p26/p27 (racks; no motion seen), and p18 by +4.
- [E] Bias-variance. Per-frame anchor-estimate noise sigma_f, N_eff = N/3 (correlated frames); total rotation
  error = hypot(bias, sigma_f / sqrt(N_eff)):

  | sigma_f | detector med/p90/max | oracle robust med/p90/max | up to 1 cm med/p90/max |
  |---|---|---|---|
  | 0.5 deg | 0.22/0.39/0.63 | 0.22/0.38/0.52 | 0.39/1.19/2.02 |
  | 1 deg | 0.41/0.67/0.72 | 0.35/0.62/0.87 | 0.45/1.22/2.04 |
  | 2 deg | 0.72/1.01/1.41 | 0.66/1.02/1.74 | 0.69/1.35/2.08 |
  | 3 deg | 1.08/1.40/2.12 | 0.96/1.44/2.60 | 0.93/1.69/2.16 |

  The detector window pays off when per-frame poses are good (<=1-2 deg, e.g. marker-based) and in the tail.
  With noisy per-frame poses (>=3 deg) the extra frames of a long window are worth as much as the bias removed.
- [V] What triggers the contact signal (`c_trig.py`, `out/c/trig_p*.jpg`, montage `out/c/trig_C_sheet.jpg`).
  - The ego hand approaching or resting next to the object: p11 p12 p13 p18 p21 p22 p23 p24 p31 p39 p40 p42 p43 p44.
  - Changes on the table surface next to the pot: shadows or reflections, no hand within ~5 cm (p0, p2, p41).
  - A held second object brought near the rack: p27, the pot.
  - The left hand far from a wide rack whose 2-D neighbourhood is large: p26.
  - All of these are early, so the "ego/non-ego arm rejection" does not matter for the bias. A wrong intruder only
    shortens the window, and only to C + 10. No public clip has a non-ego arm near slot 0.
  - [E] Eval clips with the second person in view (8, 14, 15, 16, 19, 25, 28, 30; note 15) have him at the left
    border. At worst he shortens a window. Ego/non-ego labelling (bottom-border connectivity, white watch) is still
    needed for hand tracking. It is not needed for the anchor window.
- [E] Correction to note 15 / 16-synthesis ("never average up to the 1 cm onset: 1-8.6 deg bias"). Those are
  single-frame maxima before the onset. The window MEAN up to the 1 cm onset is biased by 0.33 deg median, 1.2 deg
  p90 and 2.0 deg max (0.57 / 1.6 / 3.7 mm). The large figure applies only to an anchor taken from the last
  pre-onset frame, e.g. a track initialised at the onset and propagated backward.
- [H] Conceptual point: the anchor window needs "object not yet moved", not "no hand contact". Hands rest on the
  object for a median ~8 frames before the first 1 mm. So for the eval special cases:
  - eval 32 (hand on the resting cup at f0, lift ~f10-16): contact is present from f0, so a contact detector gives
    an empty window. The motion rule gives about [0, lift - 3].
  - eval 20 (cup in hand mid-air at f0): M fires as soon as the cup moves >= 2 mm/frame. A still mid-air hold is a
    valid frame-0 pose anyway.
  - The contact signal (vs frame 0) cannot fire while the hand is already present at f0; only M or the fallback
    (static end propagated backward) bounds the window there.

### C4. Robustness to a worse frame-0 mask (`MASKPERT=dil10|ero6|shx10 c_motion.py`, `c_maskrob.py`)
- Motion features re-run with the frame-0 mask dilated by 10 px, eroded by 6 px or shifted by 10 px (~1 cm). The
  contact features keep the original mask.
- [V] MC (L = 10) is stable:

  | frame-0 mask | late | max dR | p90 dR | mean shift |
  |---|---|---|---|---|
  | dilated | 3 | 0.59 deg | 0.34 deg | 0.40 mm |
  | eroded | 3 | 0.49 deg | 0.34 deg | 0.37 mm |
  | shifted | 3 | 0.59 deg | 0.34 deg | 0.41 mm |

  The extra late case is p31's window end, 1 row late.
- [V] Motion alone is NOT robust. With the eroded mask the thin sweeper (p31) loses its interior points and M never
  fires: +260 frames, 12.6 deg, 42 mm induced shift. The contact bound (C + 10) is essential.

### C5. End-to-end entry point
- `c_anchor.py <split> <ep> <mask.png> [n_pair]` takes the video plus a frame-0 slot-0 mask (D18 pinhole cam a,
  1014x760, f=500) and returns {C_a, M_a, c_a, c_bc, window_end_row, empty}.
  - Object depth for the px->mm conversion comes from `DEPTH_M` (stereo or prior; 0.55 m typical).
  - `c_anchor.py selftest 13` reproduces the evaluation numbers (C a16, M a22 -> bc 21, window end row 18; GT 21).
- [V] Cost: ~17 s per clip on CPU for 160 cam-a frames, of which decoding plus the shift-tolerant change maps is
  most. ~0.4 GB holds 160 decoded colour frames; streaming would remove that. Causal: the decision at frame k uses
  frames 0..k only.

### Stage C summary (2026-10-07)
| quantity | result | label |
|---|---|---|
| Reference | public GT slot-0 first perturbation (>1 mm or >1 deg; preonset.out) plus a robust version (>1.5 mm / 1.5 deg for 3 rows). Raw has artefacts: p2 one-row 2.9 mm spike, p18 1 deg marker-fit plateau, p26 no-hand bump at row 3 | [V] mocap jitter 0.01-0.15 mm |
| Contact detector C (2-D intruder touching the tracked frame-0 mask, cam a, change vs warped frame 0) | onset error vs raw pert: median -8 frames, p10/p90 -30/+8; vs robust: median -14, p10/p90 -67/-5. Fires on hand approach / rest-before-move, table shadows/reflections, objects brought near. 1 empty window (p24) | [V] 19 eps |
| Object-motion detector M (object vs ring, short-step similarity, head-flow gate) | vs robust pert: median 0..+1, within +-2 frames in 10/19; misses in-hand tilt (p11), a slide during a head sweep (p22), racks (p26/p27) | [V] |
| Combined MC = min(M, C+10), window [0, c_bc-3] | vs raw: median 0, p10/p90 -20/+17; vs robust: median -4, late 2 (p18 by 1 row; p26 no-hand bump). No empty windows; median 23 rows | [V]; LOEO held-out the same |
| Anchor bias (window mean vs GT row 0) | MC: 0.13 mm / 0.14 deg median, 2.2 mm / 0.59 deg max. Oracle 0.14-0.19 mm / 0.10-0.15 deg. Up to 1 cm onset: 0.57 mm / 0.33 deg median, 3.7 mm / 2.0 deg max | [V] |
| Board effect | official AUC with a 3 cm base error: MC +0.0000 mean (min -0.0008/clip); up to 1 cm -0.0008 mean (min -0.0031). An otherwise exact tracker scores 1.0 with any of these windows | [V] scorer; [E] base-error model |
| Robustness | frame-0 mask dilated 10 / eroded 6 / shifted 10 px: late 3, max dR <= 0.59 deg. Motion alone with the eroded mask: p31 +260 frames, 12.6 deg | [V] |
| Bias-variance | the detector window wins when per-frame anchor noise is <= 1-2 deg; at >= 3 deg the longer window's averaging matters as much | [E] |

Conclusions:
1. [V] The detector works (oracle-level bias, robust to the mask). It is cheap, causal and GT-free at inference.
   What ends the window should be OBJECT MOTION, bounded by CONTACT + 10 frames. Contact alone fires a median 8
   frames (raw) before the first 1 mm, because hands rest on objects before moving them.
2. [V/E] The stake is small: ~0.001 board AUC on average, up to 0.003 for single clips (p11/p13/p22/p31-like:
   tilts or slides in hand before the lift). Rank-3 lever "contact-gated window" in 16-synthesis is worth far less
   than the markers/priors that share its row.
3. [E] Correction: "1-8.6 deg bias up to the 1 cm onset" (note 15) are single-frame maxima; the averaged bias is a
   median 0.33 deg (max 2.0). The danger is a fixed-length window (p24: 9 mm, 2.3 deg at 15 frames) or an anchor
   taken from the last pre-onset frame.
4. [H] Better than any image detector: run the same changepoint on the per-frame anchor POSE estimates (once the
   tracker exists). Fit the mean up to the first step >2 mm or >2 deg and use C+10 as a bound. That uses the full
   static prefix with no image heuristics.

Limitations:
- Masks: validation used GT-rendered frame-0 masks; eval masks will come from perception.
- No eval GT: eval behaviour is argued, not measured (20/32 special cases).
- The robust reference is my definition; contact itself has no GT (hand-audited frames were not used).
- The spoon (slot 0 in 35-37) has no public analogue. It is thin like the sweeper, which needed the contact bound
  under an eroded mask.

Scripts (`work/20/scripts/`):
- `c_lib.py`: frames, D18 frame-0 cameras, GT reference, silhouettes
- `c_sheet.py`: visual check
- `c_detect.py`: contact features
- `c_motion.py`: object-motion features
- `c_eval.py`, `c_eval2.py`: rules, bias, AUC
- `c_auc.py`: official AUC wrapper
- `c_grid.py`: sensitivity and LOEO
- `c_trig.py`: trigger crops
- `c_maskrob.py`: mask robustness
- `c_anchor.py`: end-to-end

Outputs are in `work/20/out/c/`: feat_v2_p*.npz, mot_t2*_p*.npz, eval2_MC_A120_T2_L10_m3.json, grid.log,
sheet_p*.jpg, trig_*.jpg.
Stage C status: COMPLETE (2026-10-07). Background jobs: none left running.

## Verification (skeptical verifier, 2026-10-07; scripts and outputs in `work/20-verify/`)
- [V] C1/C2 window-bias numbers re-derived with independent code (`work/20-verify/v_c12.py`: parquet read directly,
  Karcher rotation mean instead of scipy's chordal mean, the MC decision re-implemented from the stored
  `feat_v2`/`mot_t2` npz files). Every figure reproduces: detector n med 23 (min 6), dt 0.13/0.46/2.20 mm,
  dR 0.14/0.34/0.59 deg; oracle [0,pert-1] 0.14/0.37/0.58 mm, 0.10/0.23/0.49 deg; up to 1 cm 0.57/1.61/3.67 mm,
  0.33/1.18/2.02 deg. Max of both dt and dR is p26 (rack). Window end reaches the raw pert in p2, p18, p26 and the
  robust one in p18, p26. Max single-frame rotation before the 1 cm onset is 1.03-8.64 deg (median 3.53), so note 15's
  "1-8.6 deg" is indeed a per-frame maximum, not a window mean.
- [V] Stage C features reproduce bit-exactly from video + code (`v_feat_repro.py`, p13/p22/p26: max |d touch| 0,
  max |d step| 0). The detector reads no GT after frame 0, but the validation harness feeds it a GT-rendered mask
  (D18 a10 camera, itself fitted per episode on GT edges) and the GT-rendered object depth `z` for px->mm.
  Replacing `z` by a constant 0.45/0.55/0.65 m leaves the bias stats unchanged (`v_c1grid.py`; 0.45 m adds p21 to
  the late-vs-raw list). The grid is flat in A (60-240), T (1.5-3), kappa (0-0.25); kappa 0 gives a 1-row window
  (min n 1). L and margin matter: margin 0 -> 10 windows reach the raw pert; L 30 -> max dR 0.96 deg.
  Ignoring the Stage A pairing (n=0) changes max dR 0.59 -> 0.60. Parameters were chosen on these 19 eps
  (in-sample), LOEO in grid.log is the only held-out evidence.
- [V] C2 official-AUC check with independent code (`v_c2auc.py`: kit AUC.py internals, own 1000-pt vertex sampling,
  own seeds). Exact tracker + window-mean anchor: AUC 1.0000 for det/orc/orr/cm1 in all 19 eps (max ADD 7.3 mm, p22
  cm1). Fixed 15-frame window: p24 0.952; anchor = last pre-onset frame: down to 0.83 (p13). With |N(0,3 cm)| iid base
  error, 4 seeds: det -0.0001 mean (min -0.0025), cm1 -0.0007 (min -0.0052) vs the note's +0.0000 (min -0.0008) and
  -0.0008 (min -0.0031). Means reproduce; per-clip worst cases do not (seed/vertex-sample dependent). Other base
  models (iid 1-2 cm, constant 1-2 cm per-object offset + 3 mm jitter, 2 cm random walk): det mean -0.0003..+0.0002,
  cm1 mean -0.0007..-0.0020, cm1 per-clip worst down to -0.0116 (const 2 cm). The original script reproduces its own
  printed numbers (`orig_c_eval2.py`, output redirected to work/20-verify).
- [V] C2 per-clip stability (`v_c2seeds.py`, 24 seeds, iid 3 cm): det mean -0.0002, worst p26 -0.0019 +- 0.0003;
  robust oracle mean -0.0000, worst -0.0003; up-to-1 cm mean -0.0008, worst p26 -0.0032 +- 0.0005 (p31 -0.0030,
  p13 -0.0022). So the cm1 figures (-0.0008 / -0.0031) hold; the detector's "+0.0000 (worst -0.0008)" is slightly
  optimistic (converged: -0.0002 mean, worst -0.0019, the p26 rack bump).
- [V] Independent sync method (`v_sync.py`: RANSAC homography on undistorted normalised points -> nearest rotation,
  |w| correlation and Kabsch-vector residual, 0.5 ms grid) on p11: b-c 0.0 ms, a-b -50.0 ms (|w| method -50.0),
  cost 0.020 vs 0.412 at s=0; cam-a bands -55.5 / -46.0 / -36.0 ms at mean rows 0.13 / 0.53 / 0.82 -> RS slope
  +28.1 ms/height, intercept -59.8 (i.e. -9.8 ms vs b[k] for a[k+1] at the top row). All-clip run in progress
  (`work/20-verify/sync_pub.log`, `sync_eval.log`, per-clip `sync/<key>.json`).
- [V] Source of the C2 worst-case discrepancy: Monte-Carlo seed set, not vertices or code. p26, 24 seeds each, iid 3 cm:
  seed base A det -0.0019 / cm1 -0.0032; seed base B det -0.0007 / cm1 -0.0021, identical with either vertex set
  (own 1000-pt or sc11 500-pt). The original code at 24 seeds gives p26 det -0.0007, cm1 -0.0021; p31 det 0.0000,
  cm1 -0.0030. So per-clip worst cases carry ~+-0.001 MC noise; the 19-ep means (det ~-0.0001..-0.0002, cm1 -0.0008)
  are stable. C2's conclusion (anchor window worth ~0.001 board AUC) stands.
- [V] p26 "no hand near": cam a frames a0-a8 (`work/20-verify/p26_a0_8.jpg`) show the left hand raised 5-15 cm left of
  the rack, not touching, while GT moves 1.3 -> 3.8 mm over rows 3-8 and stays (rows 25-150: 1.6-4.3 mm).
- [V] b-band global-shutter control with the independent method (`v_rsctrl.py`): b bands vs c full give slopes
  +5.3 (p11, bottom band noisy) and -1.4 ms/height (p0), vs cam a +28..+33 ms/height on the same clips.
- [V] Independent slip check (`v_slide.py`, +-15-interval windows, rig R fixed): p21 -97..-100 ms in every window
  (a[k+2] whole clip, no single-stream |w| spike). p22 -96 ms up to centre 35, -44..-47 ms from centre 65, and the only
  single-stream spike is cam a at interval 48 (ratio 2.92 vs b 0.75): a cam-a drop at a48->49, as claimed.
- [V] e20 (independent): -50..-52 ms for window centres 15-30, -95..-99 ms from centre 70; the only single-stream spike
  is b AND c together at interval 48 (ratios 2.99 / 3.15, a 0.95): a b/c drop at 48->49, as claimed.
- [V] Independent all-clip sync (`v_sync.py`, 40 clips incl. fresh p45; logs `work/20-verify/sync_pub.log`,
  `sync_eval.log`): b-c mean +0.10 ms, sd 0.34, max |.| 1.0 ms (0.5 ms grid, no sub-grid refinement): same-index
  b/c sync confirmed within ~1 ms (the note's +-0.09 ms precision is not tested by this grid). a-b whole fit outside
  the 3 slip clips: -47.4 +- 1.2 ms (range -50.0..-45.0, n=37; note: -49.5 +- 1.6), cost at s=0 7-58x the optimum.
  p21 -100.0 (quarters -97.5..-100), p22 quarters -95.5 | -49.5 | -45 | -46, e20 -49.5 | -95.5 | -97 | -97.5.
  So a[k+1] ~ b[k] holds in 36/39 (37/40 with p45) and the three exceptions are as claimed.
- [!] Rolling-shutter SLOPE does not reproduce with the band method. Independent band offsets (homography-derived
  band rotations): full-vector residual gives 20-34 ms/height per clip (mean ~27); pan/tilt components only
  (`v_rs2.py`, 40 clips) give pooled t(a[k+n], y) - t(b[k]) = -4.5 + 21.6 y ms (per-clip slope 21.7 +- 3.4,
  resid sd 1.9 ms) vs the claimed -9.8 + 31.6 y. Centre-row time agrees (+6.3 vs +6.0 ms); the slope and top/bottom
  row times differ by ~5 ms. Band rotation estimators may shrink the slope (homography from a strip is
  ill-conditioned). A feature-level RS fit (no band rotations) is run next to adjudicate.
- [V] Feature-level RS fit (`v_rsfeat.py`: every cam-a KLT track predicted from the cam-b orientation track at row
  times t0 = k + d + tau*y0, t1 = k + 1 + d + tau*y1; robust 1.5 px angular loss; tau profile). Result depends on the
  b-velocity interpolation: piecewise-linear slerp gives 23-26 ms/height (p11, e5, e6, e19; shallow profiles), while a
  cubic spline of the cumulative b rotation gives e19 31.6 ms/height (-9.1 + 31.6 y) and e5 29.2 (-7.1 + 29.2 y), with
  clearly lower cost (e19 0.161 vs 0.192). The linear interpolation smooths angular acceleration, which is what
  identifies tau, so it biases tau low; the band-rotation results above are likely biased the same way or by strip
  conditioning. The claimed ~31.6 ms/height is supported by the better-fitting model.
- [V] Cubic feature-level RS fit on 9 clips (e19 e5 e6 e36 e33 p0 p21 p11 + fresh p45): tau 31.4 +- 1.9 ms/height
  (28.4-34.2), top-row intercept -8.6 +- 0.8 ms (p21 with n=2: -8.6 + 34.2 y). Pooled: t(a[k+n], y) - t(b[k]) ~
  -8.6 + 31.4 y ms (centre +7.1, bottom +22.8) vs claimed -9.8 + 31.6 y. A1's timing model reproduces within ~1 ms.

### Verifier verdicts (2026-10-07)
- C1 NOT refuted: all bias numbers, the empty-window and median-length claims reproduce exactly with independent
  code; robust to GT depth, A, T, kappa and the pairing. Caveats: thresholds chosen in-sample on the same 19 eps
  (only LOEO is held out); validation masks are GT-rendered through a GT-fitted camera; "oracle-level" holds for the
  median, but the tail is worse than the oracle (max dt 2.20 vs 0.58 mm, p90 dR 0.34 vs 0.23 deg; p26).
- C2 NOT refuted, minor correction: the 1 cm-window bias numbers, AUC = 1.0 for an exact tracker, and the cm1 dAUC
  (-0.0008 mean, worst ~-0.003) reproduce. The detector's "+0.0000 (worst -0.0008)" is MC-noisy: converged -0.0001..
  -0.0002 mean, worst p26 -0.0007..-0.0019 depending on the seed set. With systematic base errors (constant 2 cm
  per object) cm1 costs up to -0.012 on one clip (mean -0.0015): still small at board level.
- A1 NOT refuted: b/c same-index sync (within the 0.5 ms grid), a[k+1] ~ b[k] in 36/39, p21 a[k+2], the p22 cam-a and
  e20 b/c drops at interval 48, and the RS model (-8.6 + 31.4 y vs -9.8 + 31.6 y) all reproduce independently.
  Caveat: the RS slope depends on the interpolation model (piecewise-linear gives 23-26 ms/height); the claimed
  sub-0.1 ms b-c precision was not re-tested.

## Stage B re-run (2026-10-07, workflow "try again"; resume marker)
- State on resume: Stage B (B1-B4 and summary above) was already complete from the earlier cut-off run. This re-run (a)
  re-checks the stored B4 numbers and (b) attacks the open item: the bowl-vs-handle bend, measured in near-frontal held
  frames. New scripts are `work/20/scripts/b2_*.py`; outputs go to `work/20/out/b2/`. Earlier `out/b/` files are untouched.
- [V] B4 table reproduces exactly from the stored `out/b/pb_*.jsonl` (`b_pbsum.py` re-run). Examples: hl_bend2 toM2
  -0.015, noisy mid-axis P(B) 0.33, x-skew 0.97; final 0.83; model 0.88. The 'final' regression zero is at asym +2.46 mm
  (roll 0).
- Lead: the e36 held scan has near-frontal triples early in the clip that `b_heldgeom.py` never analysed: k30-33,
  triangle normal . view 0.87-0.98; k48 (1.00) is motion-blurred and vertical. At k30-33 the spoon is held roughly
  horizontally over the table (contact sheet `out/b2/e36_early.jpg`). Cam a sees the concave face top-down, and the full
  rim outline stands out sharply against the table. The hand covers the mid-handle; the neck (M2 side) and the M3 end are
  visible.
- [V] Tools. `b2_scan.py` reproduces `b_held.py` per frame (e36 k33 is bit-identical: d 53.1/153.7/196.6, front 0.98) but
  decodes each clip once. All 10 spoon clips are being scanned at step 2 into `out/b2/held_e*.jsonl`.
  `b2_front.py` builds a straightened image in UNDISTORTED normalised cam-a coordinates: rows are stations along
  mid(M1,M2)->M3 at 0.5 px steps, columns are perpendicular offsets. It finds the outline at 50% crossings in the saturation
  channel (wood S ~70, table S > 150). Each handle limb gets a RANSAC line (0.4 mm gate). Axis variants: 'mid' = mean of
  the two limb lines; 'R-hw' / 'L+hw' = one limb offset by the near-segment half-width.
- [V] e36 k30-34 (held, concave face toward cam a, hand on the mid-handle). Visible: the neck segment s +30..+50 mm (both
  limbs) and the M3 end s +150..+165 (top/M1-side limb only; fingers cover the bottom limb). Handle half-width 9.5-10.0
  mm (round rod, as at rest). Limb residual 0.14-0.18 mm.
  - The bottom limb has only the 20-mm neck segment, so its direction is poor: the two limb lines disagree by 0.5-1.9
    deg, and 'mid' and 'L+hw' scatter (bowl offset -0.2..+5.5 mm).
  - 'R-hw' (top limb over ~115 mm, both segments) is stable over 5 frames, in mm toward M1 relative to the handle axis:
    bowl area-centroid offset +0.83, +0.88, +0.78, +1.00, +1.08 (mean +0.91 +- 0.12); tip (3-15 mm in) +1.08..+1.44.
  - [E] So the near-frontal view gives an in-plane bowl offset of ~+1 mm toward M1 (a small bend). Same sign as rest
    (+2 +- 1.5) but smaller. Caveat: the rim's height above the axis times sin(roll) adds parallax (see the next item).
- [V] The same frames give marker image offsets from the handle axis ('R-hw') of M1 +19.4..+20.4, M2 -9.4..-11.9,
  M3 +3.3..+6.5 mm. o1 + o2 = +8.5..+10.0 in all 5 frames. At zero roll this is the lateral asymmetry: ~3x the rest
  value (+2.5..+3.5) and close to the 13-verify hand-read (+4..+9).
- [!] Conflict between the held-frontal and rest layouts:
  - The stereo marker depths (b/c disc-NCC along the cam-a ray) put M1 and M2 at nearly the same depth. After removing the
    axis pitch (M3 is 29 mm deeper than mid(M1,M2) at k33), M2 is 3-4 mm nearer the camera. That matches the rest heights
    (+6/+10) at roll ~0, and then the frontal offsets ARE the lateral offsets (asym ~+8.5).
  - Rotating the rest (w, h) pairs to match the frontal laterals needs ~23-35 deg, which would make M2 ~20 mm nearer than
    M1. That is excluded by the depths.
  - The rigid triangle favours the frontal layout. Both the frontal projection and the rest stations give M1-M2 ~43 mm
    along the axis, so the cross-section separation must be sqrt(53.0^2 - 43^2) = 31 mm. Frontal (31.1 lateral, ~4 depth)
    fits; rest (36.3 lateral, 4 height) would need only ~38 mm along the axis.
  - [H] The rest lateral values for M2 (and M3) are biased outward by ~4-6 mm; cause not yet identified. Next: a 3-D
    frontal analysis (SGBM bowl plane for the roll, handle surface depth for the axis) to fix the roll independently of
    the rest layout.
- [V] CORRECTION to the two items above: the e36 k30-34 held frames are NOT near-frontal, and the "+8.5 asymmetry" is an
  artefact.
  - The 'front' value (triangle normal . view, 0.95-0.98) and the depth-based roll both rest on M1's free-sweep depth, which
    is unreliable. On the SAME rest frame e36 k0, the free sweep (`b2_scan`) and Stage B's table-constrained sweep
    (`meas_e36.json`) put M1 10 mm apart in depth; M2 agrees. M1's sphere has weak mono contrast (B1: NCC 0.88 vs 0.87
    second peak), and the triangle search can pick a secondary peak.
  - The held marker image offsets equal the oblique REST-view offsets: e36 rest k0-3 gives M1 +18.6..+20.3, M2 -8.6..-9.6,
    M3 +5.5..+6.8. Projecting the Stage B rest layout through each clip's viewing geometry reproduces them to ~1 mm (e35,
    e36, e37), so the held frames sit at ~20-30 deg roll.
  - M2's distance from the 3-D handle axis (SGBM front surface + r along the ray; M2 NCC 0.98) is 18-23.5 mm in held
    frames vs 19.6 at rest: same rigid layout.
- [V] Roll from an SGBM bowl-interior plane (`b2_roll.py`): reliable only when the plane inlier fraction is >= ~0.6.
  - e35 rest: bowl-vs-table roll 0.0 +- 1.0 deg (4 frames, inliers 0.58-0.67).
  - e36 rest: -1.7 +- 4.8.
  - e36 k0/k1 view roll 31.7/36.5 vs 32.8 deg expected from the view geometry.
  - It fails in transverse e37/e16 (inliers 0.31-0.46, readings -24..+9 deg) and in the held frames (inliers 0.45-0.50;
    29 -> 4 deg over k30-34, contradicted by the image offsets). It confirms rest roll ~0 (e35), as B3 found.
- [V] NEW: the handle BULGES. At rest (e36 k0) the image width runs 18.8 (s +32) -> 21.3 (s +82..+92) -> 18.8 mm (s +142),
  while the midline is straight to +-0.15 mm (`b2_limbs.py`).
  - Each limb is therefore curved. A RANSAC line per limb (0.4 mm gate) covers only 60-85 mm, and the axis built from
    them (or one limb +- half-width) is tilted. That biased my earlier 'mid'/'R-hw' values: the rest bowl offset came out
    ~0 instead of +2.3.
  - The correct axis is a trimmed LSQ line through row midpoints over the full handle ('midpts' in `b2_front.py`:
    rms 0.07-0.25 mm, span 60-139 mm at rest). In held frames the hand blocks the full span, so no clean axis is available
    there.
- [V] Rest frames, 'midpts' axis back-projected to Stage B's table frame at h = 7.2 mm (`b2_cmpgeom.py`; markers are the
  table-constrained 3-D points, so there is no marker parallax):
  - Marker asymmetry lat1 - lat2: e36 +3.3/+3.4, e35 +4.6/+3.4, e37 +0.5/+2.0, e16 +2.8/+1.7. Mean +2.7 +- 1.2 mm.
    It rises ~1.2 mm per mm of assumed axis height (h 8.5: ~+4). This confirms B3/B4 (+2.5..+3.5).
  - Raw bowl midline offset (projection plane at the axis height, so it includes silhouette parallax): e36 +3.6/+3.9,
    e35 +5.3/+5.3, e37 +3.0/+3.2, e16 +2.3/+2.6. Fed my own edges, `b_geom`'s statistic gives +3.6 against `b_geom`'s
    +4.4. Stage B's raw cam-a bowl numbers stand.
  - Bend = raw - dH_eff * cot(alpha), with cot 0.38 (e16) .. 0.64 (e36), where dH_eff is the mean height of the two
    bowl-silhouette points above the axis. A fit across clips: dH_eff ~4.5, bend ~+0.7 mm without e35 (bend ~+2.4 with
    it). The B2 edge-stereo heights (far rim +5..+9, near wall -6..+8 above the axis) give dH_eff ~3.3-4.7, so
    bend ~+0.9..+1.8.
  - [E] Bowl in-plane offset toward M1: +1.2 +- 1.2 mm. Same sign as Stage B (+2 +- 1.5), slightly smaller; consistent.
    The held frames cannot add a parallax-free view (roll ~25 deg, and no full-handle axis).
- [V] More views for the bend. `b2_cmpgeom.py` (straight-midline axis, table plane h = 7.2) over all usable rest and end-rest
  views. Values are raw bowl offset at cot(alpha):
  - e3 end (k306/310, nearly radial, az 153 deg): +3.24/+2.91 at 0.30
  - e5: +2.46/+3.05/+1.60 at 0.35
  - e16: +2.25/+2.64 at 0.38
  - e35: +5.28/+5.30 at 0.49
  - e37: +3.04/+3.18 at 0.59
  - e37 end: +3.16/+3.33 at 0.59
  - e36: +3.57/+3.94 at 0.64
  - e35 end: +4.07/+3.80 at 0.65
  - e32 fails (bottom limb missing); e33, e15 and e6 have no handle rows.
  - Every rest view has M1 on the far side (end rests included), so the parallax never changes sign.
  - LSQ on clip means, raw = bend + dH_eff * cot: bend +1.57 +- 0.53 mm, dH_eff 3.1 mm, residual sd 0.37 mm, 7 clip-views
    without the e35 outlier (+1.9 with it). dH_eff matches the B2 edge-stereo silhouette heights (~3.3).
  - Caveat [E]: dH_eff is probably larger in radial views, where the near silhouette approaches the rim; that would push the
    bend toward +1.
  - [E] Bend +1.3 +- 0.8 mm toward M1. This confirms Stage B's sign and centre (+2 +- 1.5) with a tighter band.
- [V] Marker asymmetry vs the straight midline (table-constrained 3-D markers, 17 rest/end-rest frames, 8 clip-views):
  mean +3.2 (clip sd 1.3) with the axis at 7.2 mm in the dy-field frame. Radial views (e3 end +5.2, e5 +4.4) read higher
  than transverse ones (e37 +1.25, e16 +2.25), as expected if the true axis sits higher than 7.2: each mm adds 2 cot(alpha)
  per clip. At 8.2 mm (bulge radius 10.6 minus the dy-field table offset ~2.4) the mean is +4.2 (sd 1.1).
  - [E] Asym +3.7 +- 1.0 mm. Stage B used +3.0 +- 0.9.
- [V model] P(B) re-run (`b2_pb.py` = `b_pb.py` with 2 added layouts; 40 bodies each; `out/b2/pb_*.jsonl`, `b2_pbsum.py`):

  | layout | asym, bend (mm) | toM2 mean [p10,p90] | noisy mid-axis P(B) | y-skew | x-skew | hybrid .02 | larger-abs | q10_y | -shalf_x | far3d_x | F2 | F2b | F3 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | hl_r2 (re-run best estimate) | 3.7+-1.0, 1.6+-0.7 | -0.014 [-0.044,+0.015] | **0.34** | 0.25 | 0.93 | 0.65 | 0.88 | 0.53 | 0.47 | 1.00 | 0.38 | 0.20 | 0.52 |
  | hl_bend12 (smaller bend) | 3.0+-1.2, 1.2+-1.2 | -0.004 [-0.035,+0.022] | 0.47 | 0.53 | 0.97 | 0.78 | 0.93 | 0.62 | 0.55 | 1.00 | 0.47 | 0.38 | 0.60 |
  | Stage B hl_bend2 (for reference) | 3.0+-0.9, 2.0+-1.5 | -0.015 | 0.33 | 0.23 | 0.97 | 0.60 | 0.82 | 0.30 | 0.38 | 1.00 | 0.32 | 0.20 | 0.47 |

  Roll N(-2.5, 3) deg and all other inputs as in Stage B.
- [E] Re-run verdict: the Stage B conclusion is unchanged. Under the mid-axis skew rule P(B) ~0.34 (0.47 if the bend is at
  the low end). Every x-skew rule gives B (0.88-1.00). Mixing rule classes as in Stage B still gives P(B) ~0.45-0.5:
  no confident call; ask the organisers.
- [V] Failed: geometric repair of M1's held-frame depth (`b2_m1fix.py`: M1 on its cam-a ray at |M1-M2| = 53.0 mm, root
  chosen by |M1-M3|).
  - Validated on rest frames against the table-constrained M1, it is off by 3-31 mm (e35, e37); in e36 it agrees with
    the WRONG free-sweep value.
  - The M1-M2 chord is nearly perpendicular to M1's ray, so the constraint is ill-conditioned.
  - At e36 rest the table-constrained triangle gives frontalness 0.842 (expected cos(34 +- 5 deg) = 0.78-0.87); the free
    sweep's 0.932 is wrong.
  - So 'front' from the held scan cannot select near-frontal frames. The parallax-free falsifier (a truly frontal bowl
    view) is still open: it needs a reliable M1 depth (e.g. a joint 3-marker sweep with the triangle as a constraint)
    plus an occlusion-tolerant, bulge-aware handle axis.

### Stage B re-run summary (2026-10-07)
| quantity | re-run result | Stage B (above) | label |
|---|---|---|---|
| P(B) table reproduction | exact from stored `out/b/pb_*.jsonl` | - | [V] |
| Handle shape | round, straight midline (+-0.15 mm), BULGES 18.8 -> 21.3 -> 18.8 mm along s +32..+142 | round, r 9.8-9.9 | [V] (`b2_limbs.py`) |
| Handle-axis estimator | trimmed LSQ line through row midpoints over the full handle (rest only); per-limb lines are biased by the bulge | cam-a midline on table-parallel planes (`b_geom`) | [V] |
| Bowl in-plane offset toward M1 (bend) | +1.54 +- 0.59 mm (regression over 7 clip-views; dH_eff 3.2 +- 1.2); +1.94 +- 1.33 with e35; [E] +1.3 +- 0.8 allowing view-dependent dH_eff | +2 +- 1.5 | [V] fit, [E] model |
| Marker asymmetry lat1 - lat2 (vs the straight midline) | +3.2 (axis at 7.2 mm) .. +4.2 (8.2 mm), clip sd 1.1-1.3 | +2.5..+3.5 | [V] / [E] axis height |
| Held e36 k30-34 | roll ~20-30 deg, not frontal; the 'front' 0.95-0.98 comes from a wrong free-sweep M1 depth (10 mm at e36 k0) | k30-33 noted as near-frontal lead | [V] |
| SGBM bowl-plane roll | works only at inlier fraction >= 0.6 (e35 rest: 0.0 +- 1.0 deg vs table); fails transverse/held | far-rim roll -2.5 +- 3 | [V] |
| P(B), noisy mid-axis rule | 0.34 (hl_r2: asym 3.7 +- 1.0, bend 1.6 +- 0.7); 0.47 (hl_bend12) | 0.33 (0.13-0.65) | [V model] |
| P(B), x-skew rules (n07 x, larger-abs, far3d_x) | 0.88-1.00 | 0.82-1.00 | [V model] |
| P(B), F2 / F2b / F3 | 0.38 / 0.20 / 0.52 (hl_r2) | 0.32 / 0.20 / 0.47 | [V model] |
| Overall | unchanged, ~0.45-0.5 across rule classes; mid-axis convention leans A ~2:1 | same | [E] |

Re-run files:
- Scripts (`work/20/scripts/`):
  - `b2_scan.py` (sequential held/rest triple scan; logic of `b_held.py`), `b2_view.py`
  - `b2_front.py` (straightened-image outline/limb/marker offsets; `--rest`, `--end`, `--span=`)
  - `b2_rows.py`, `b2_limbs.py`, `b2_vcheck.py` (diagnostics)
  - `b2_roll.py` (SGBM bowl-plane roll; markers vs 3-D axis)
  - `b2_cmpgeom.py` (back-projection to Stage B's table frame)
  - `b2_m1fix.py` (failed M1 repair)
  - `b2_pb.py`, `b2_pbsum.py` (P(B))
  - `b2_summary.py`
- Outputs (`work/20/out/b2/`): `held_e*.jsonl`, `scan_e*.log`, `front_e36.jsonl`, `frontrest_e*.jsonl`, `roll_e*.jsonl`,
  `pb_hl_bend12_41.jsonl`, `pb_hl_r2_42.jsonl`, `rerun_summary.json`, and debug images.

Open (unchanged in substance): the organisers' sign rule and whether their scan includes the markers. A frontal bowl view
would remove the dH_eff model dependence of the bend. It needs (a) a joint 3-marker depth sweep with the triangle as a
constraint, to choose frames, and (b) a bulge-aware axis that tolerates the hand covering the handle.
- [V] Held/rest triple scan complete (`b2_scan.py`, step 2, all 10 spoon clips, no errors; `out/b2/held_e*.jsonl`,
  `scan_e*.log`). Frames with a triangle-consistent marker triple / frames scanned: e3 26/156, e5 9/143, e6 28/121,
  e15 7/82, e16 10/86, e32 38/129, e33 24/173, e35 58/210, e36 31/200, e37 46/75.
  Caveat: M1's depth (hence 'front') in these records is unreliable (see above). M2/M3 and the image positions are fine.
  Stage B re-run status: COMPLETE (2026-10-07). Background jobs: none left running.

## Stage C re-run (2026-10-07, workflow "try again"; resume marker)
- State on resume: Stage C (C0-C5, summary) and its independent verification were already complete from the earlier
  cut-off run. This re-run (a) re-checks the stored C3 numbers, then (b) attacks the main open items: the validation
  masks were GT-rendered through a GT-fitted camera, p45 (the only unused public GT clip) was never run, and the eval
  special cases (e20 cup mid-air, e32 hand on cup at f0, early onsets) were argued, not run. New scripts are
  `work/20/scripts/r_*.py`; outputs go to `work/20/out/c2/`. Earlier `out/c/` files are untouched.
- [V] R0. C3 reproduces exactly from the stored `out/c/feat_v2_*`/`mot_t2_*` npz (`r_repro.py`, `out/c2/repro.log`):
  19/19 eps give the same C/M/c_bc/window end and dR as the stored json; raw onset error median +0 (p10/p90 -20/+17),
  robust median -4, dt 0.13/0.46/2.20 mm, dR 0.14/0.34/0.59 deg, median window 23 rows. M never fires on p27 (rack).
- R1 (in progress). GT-free frame-0 slot-0 mask, attempt 1 (`r_mask.py`, `r_prior.py`): b/c SGBM at index 0, table plane
  by RANSAC, above-table points clustered by their FOOTPRINT on the table (1 cm grid), slot-0 blob chosen by a public-GT
  size/colour prior (LOO), blob points projected into cam a. [V] Works when slot 0 stands alone (p0 pot IoU 0.78 vs
  the GT-rendered mask, centroid 7 px), fails when objects touch (p13 cup against the rack merges, p31 sweeper in the
  rack) or are flat (p24 planks, 2 cm). Two fixes found on the way: the table support must be the largest component on
  a plane grid (an image-space component covered only half the table on p0), and SGBM density is NOT the problem on
  white objects (dense on the p0 pot at every setting tried, `out/c2/dbg/sgbm_p0.jpg`). Next: model-based 2.5-D
  template search of the slot-0 mesh on the table height map (x, y, yaw; tilt from public rest poses).
- R1 attempt 2 (`r_pose0.py`): model-based 2.5-D template search. Observed = per 1 cm table cell the 90th-percentile
  height of the b/c SGBM points whose foot falls in it (object / table / unknown). Template = slot-0 mesh in each public
  rest tilt of that object (other episodes' GT = prior), yaw in 5 deg steps, per cell the height of the VISIBLE surface
  (z-buffer along the camera->table direction, so cup interiors look as seen). Score = mean height agreement minus
  table cells under the template; colour tie-break (cam-a Lab of the rendered mask vs the public colour prior) among
  the top peaks; the pot-with-lid task uses a pot+lid composite (relative pose from the other lid episode). The mesh
  silhouette at the found (x, y, yaw) is rendered into cam a at a[n] and warped to a[0].
  - [V] Bugs found and fixed on the way: the template returned z-min after zeroing it (object sunk by its origin
    offset: 8.6 cm error on p13 although the search cell was 1 cm from GT); the pot template without the lid scored the
    GT pose at -0.05 on p0 (the lid, not the pot interior, is seen).
  - [V] First five: p13 cup next to rack IoU 0.80 (origin error 0.9 cm), p12 0.80 (1.0 cm), p31 sweeper standing in the
    rack 0.65 (1.1 cm), p0/p2 pot+lid 0.88/0.92 (1.0/0.6 cm), p24 plank 0.89 (1.0 cm; chosen over the twin plank by
    the colour tie-break, the height score alone tied).
  - [V] Flat objects are weak in height: p24 plank tops read +3.5 mm above the fitted plane (ring around them -1.8 mm),
    versus ~+20 mm expected; GT placed through the D18 a[0] camera puts the plank base 9.8 mm below our plane. The b0 vs
    a0 time offset (50 ms of head motion) limits GT-side checks at the ~1 cm level.
  - [V] Three more fixes from the 20-clip public run: (1) height agreement made one-sided: observed HIGHER than the
    template (lid on the pot, pot in the rack, a hand on top) is neutral, lower is evidence against (p26 rack under
    the pot went 0.01 -> 0.86 IoU); (2) colour tie-break weight 0.004 -> 0.01 per Lab-ab unit (p11 picked the beige
    cup instead of the blue one); (3) table-plane candidates limited to < 0.85 m (the floor is >= ~1 m away), with
    inliers area-weighted (Z^2) and planes with many points 1-4 cm below them penalised (p27: the RANSAC plane had
    run through the floor and the table). Wooden spoon (no scan) falls back to the blob method of attempt 1.
- [V] R1 result, final settings, 19 public eps with a GT-rendered reference mask (`out/c2/pose0_pub.log`,
  `pose0_pub_summary.txt`, debug overlays `mask0_p*_dbg.jpg`): IoU vs the GT-rendered mask median 0.85, >= 0.66 in
  17/19; slot-0 origin error median 1.0 cm (0.5-1.4 cm on the 18 right-object picks; this includes the ~50 ms a[0]/b[0]
  head-motion offset of the GT check); mask centroid median 6 px. Failures: p23 picks the TWIN plank (wooden_piece_2,
  23 cm away; identical shape, colour tie-break too weak: dcol 0 vs 6) and p18's thin sweeper is right but partial
  (IoU 0.45, origin 1.3 cm). Stereo depth of slot 0 matches the GT depth to ~1 cm (0.39-0.65 m). p45 (no D18 camera)
  has a mask but no reference. Cost ~5-8 s per clip (CPU). Reads no GT of the episode; public GT enters only as
  priors (rest tilts, colour, lid-on-pot relative pose; leave-own-episode-out).
- [V sim] R2. Test of C-[H]4, a changepoint on the per-frame anchor POSE track (`r_cpsim.py`, `out/c2/cpsim.log`,
  `cpsim.json`; public GT + AR(1) pose noise, rho 0.7, sigma_f deg and 2 mm/deg; 24 seeds x 19 eps). Rule: first k
  where 3 consecutive frames leave the running mean of [0, k) by > max(2 deg, 3 sigma_f) or > max(2 mm, 6 sigma_f mm).
  Anchor rotation error (per-episode mean over seeds; median / p90 / max, deg):

  | sigma_f | pose changepoint | + contact bound | image detector MC | oracle robust | up to 1 cm | fixed 15 |
  |---|---|---|---|---|---|---|
  | 0.5 | 0.36/0.59/0.79 | 0.39/0.60/0.73 | 0.41/0.64/0.69 | 0.36/0.59/0.76 | 0.42/1.24/2.02 | 0.45/0.68/2.35 |
  | 1 | 0.71/0.91/1.12 | 0.79/1.06/1.10 | 0.74/0.97/1.26 | 0.67/1.03/1.49 | 0.71/1.35/2.05 | 0.89/1.03/2.44 |
  | 2 | 1.39/1.74/2.10 | 1.46/1.93/2.10 | 1.45/1.87/2.51 | 1.34/1.89/2.96 | 1.32/1.93/2.23 | 1.79/1.96/2.81 |
  | 3 | 2.05/2.48/3.12 | 2.19/2.85/3.09 | 2.17/2.76/3.77 | 1.98/2.78/4.43 | 1.93/2.28/3.09 | 2.67/2.93/3.33 |

  The changepoint fires at the robust perturbation (median +0..+4 frames; p90 +3 at 0.5 deg, +10..+38 at >= 1 deg) and
  reaches oracle-level error at every noise level. It is 0.03-0.12 deg better than the image detector in the median
  and better in the tail at >= 1 deg. The contact bound adds nothing here. [V sim / E] H4 holds, but the gain is far
  below anything the scorer resolves (C3: the whole window question is ~0.001 AUC). Translation behaves the same way
  (fixed 15 frames is the only bad arm: 9-10 mm max, p24).
- Jobs (2026-10-07 ~08:50): `r_run.py public <20 eps>` -> `out/c2/run_pub.log`, `run_p*.npz` (running, orphaned
  python pid 61170); `r_pose0.py evaluation <20 eps>` -> `pose0_eval.log`, then `r_run.py evaluation` in two halves ->
  `run_eval_a.log`, `run_eval_b.log` (nohup). Evaluate with `r_eval.py`; eval viewing reference (note 15, approximate,
  design only) in `out/c2/eval_view_ref.json`.
- [V visual / E] R3. GT-free frame-0 masks on the 20 EVAL clips (`out/c2/pose0_eval.log`, sheet
  `out/c2/mask0_eval_sheet.jpg`; checked by eye for method design only, nothing fed back): right object in 17/20 (pots
  e1/e3/e5/e6 incl. lid, cups e8/e10/e14/e32/e33, racks e15/e16/e28, sweepers e19/e30 incl. in the rack, dust pan
  e38, spoon blobs e35/e37). Wrong in 3, each a known mode:
  - e20: the cup is in the hand in mid-air at f0, so there is nothing on the table to find. The best "cup" is a patch on
    the pitcher with the weakest cup score of all clips (final 0.17 vs 0.57-0.62 for resting cups).
  - e25: the twin plank (piece_2, right) is picked over piece_1 (final 0.29 vs 0.25; same failure as public p23).
  - e36: the spoon blob fallback picks the left hand/forearm (blob score 1.95 vs 1.1-1.2 on e35/e37).
  [H] A low final score (< ~0.25 for cups/pots) or a near-tie between distinct peaks is an automatic "slot 0 not
  found resting at f0 / identity ambiguous" flag; racks score low (0.14-0.21) because the pot or spoon covers them,
  so the threshold must be per class.
- [V] R4. Frozen MC detector (A 120, T 2 mm, kappa 0.15, L 10, margin 3; nothing retuned) on the GT-FREE masks with
  the stereo depth, 19 Stage C eps + fresh p45 (`r_run.py`, `r_eval.py`; `out/c2/run_pub.log`, `eval_gtfree.log`,
  `eval_gtfree.json`):

  | set | onset err raw med (p10/p90) | robust med | late raw/robust | empty | window med | dt mm med/p90/max | dR deg med/p90/max |
  |---|---|---|---|---|---|---|---|
  | GT-rendered masks (C3, stored) | 0 (-20/+17) | -4 | 3/2 | 0 | 23 | 0.13/0.46/2.20 | 0.14/0.34/0.59 |
  | GT-free, 18 right-object picks | -2 (-20/+16) | -4 | 4/2 | 0 | 24 | 0.14/0.47/2.03 | 0.14/0.36/0.58 |
  | GT-free, all 20 (incl. p23 twin, p45) | -2 (-22/+17) | -4 | 5/3 | 0 | 24 | 0.16/0.66/23.97 | 0.15/0.49/2.88 |

  - Window end within +-2 rows of the GT-mask run in 15/19 (identical in 6). The two robust-late cases are the
    same as before (p18 one row; the p26 no-hand rack bump).
  - Fresh holdout p45 (Pan_Solo; never used for any Stage C or re-run choice): C a13, M a48 -> window [0, 19],
    GT pert 46/47, i.e. 24 rows early (contact bound). dt 0.21 mm, dR 0.17 deg; official AUC of an exact tracker 1.0.
  - The p23 identity error is the one dangerous case: the mask sits on the twin plank, so C (a28) and M (a113) watch the
    wrong object; the window ends at row 34 while piece_1 moved at row 18 -> anchor bias 24 mm / 2.9 deg, official AUC
    of an otherwise exact tracker 0.73 (0.62 vs 0.81 with a 3 cm base error). [E] On eval this is e25 (same twin
    planks, same wrong pick). In practice a wrong slot-0 identity also ruins the whole slot-0 track, so the
    window is not the main loss there; identity must be resolved first (note 15: marker-ball layout; note 11
    staging side rule: piece_2 at +y = image right).
- [V run / E reference] R5. Frozen detector on all 20 EVAL clips with the GT-free masks (`run_eval_a.log`,
  `run_eval_b.log`, `r_evalsum.py` -> `out/c2/eval_summary.log`, `eval_summary.json`). There is no eval GT; the reference is
  note 15's viewing of contact sheets (every ~8 frames, so +-8 f).

  | ep | slot 0 | C a | M a | window end (cam-a idx c_a; b/c row) | viewed contact / motion | reading |
  |---|---|---|---|---|---|---|
  | 1 | pot+lid | 28 | 45 | a38; row 34 | 24-32 / 48 (lift 127) | before the first nudge |
  | 3 | pot | 15 | 14 | a14; row 10 | 50-56 / none | early (M at a14: a spurious step), safe |
  | 5 | pot | 13 | 25 | a23; row 19 | 16-20 / 24-40 | at the onset (tight) |
  | 6 | pot | 12 | 22 | a22; row 18 | 8-16 / 24-32 | before |
  | 8 | beige cup | 33 | 45 | a43; row 39 | 40-44 / 52-56 | before |
  | 10 | blue cup | 17 | 39 | a27; row 23 | 16-24 / none | C+10 bound |
  | 14 | blue cup | 14 | 25 | a24; row 20 | 16 / 24-32 | at the onset (tight) |
  | 15 | rack | 34 | - | a44; row 40 | 60-105 / static | early (hand at the spoon next to the rack), safe |
  | 16 | rack | 14 | 75 | a24; row 20 | 75-120 / static | early, safe |
  | 19 | sweeper | 16 | 20 | a20; row 16 | 12-16 / 16-24 | at the onset |
  | 20 | cup in hand | 29 | 3 | a3; EMPTY | 0 / 0 | correct: empty -> static-end fallback |
  | 25 | plank (twin picked) | 71 | 99 | a81; row 77 | 32 / 48-56 | LATE: wrong identity |
  | 28 | rack | 11 | - | a21; row 17 | none / static | early, safe |
  | 30 | sweeper | 29 | 38 | a38; row 34 | 32 / 40-56 | before |
  | 32 | cup, hand at f0 | 6 | 8 | a8; row 4 | 0 / 10-16 | M catches the lift start: 5-row window |
  | 33 | cup | 12 | 24 | a22; row 18 | 16 / 24-40 | before |
  | 35 | spoon (blob) | 11 | 24 | a21; row 17 | 16-24 / 32 | before |
  | 36 | spoon (blob on the hand) | 19 | 11 | a11; row 7 | 24-32 / 40 | early by luck (wrong mask) |
  | 37 | spoon (blob) | 11 | 32 | a21; row 17 | 16-32 / 40 | before |
  | 38 | dust pan | 33 | 36 | a36; row 32 | 40 / 40-56 | before |

  - [E] 17/18 clips with a resting slot 0 and the right object end the window at or before the viewed first motion
    (within the +-8 f viewing resolution; e5, e14, e19 are tight). e20 returns EMPTY, as designed. e32 (hand on the cup
    at f0) gets a 5-row window from M, not an empty one: the contact signal cannot see a hand that is there at f0, and
    the motion signal ends the window at the lift.
  - [E] The only late eval window is e25, the identity error. Median window 18 rows.
- [V visual] R6. What triggered C and ended the window on eval (`r_trig.py`, sheet `out/c2/trig_sheet_evaluation.jpg`;
  e3 e8 e14 e15 e16 e19 e25 e28 e30 e32 e36). Every C trigger is the EGO hand: reaching for slot 0 (e8, e14, e19,
  e30), reaching for the spoon lying against the rack (e15, e16), gripping the pot handle next to the rack (e28), or
  the hand that already holds the cup at f0 starting to move (e32, C a6, M a8). The second person at the left border
  (e8, e14, e15, e16, e19, e25, e28, e30) shows up as change at the image edge but never touches a slot-0 mask, so
  ego/non-ego arm rejection is still not needed for the anchor window. e3's early end (M a14, C a15) is a thin
  registration edge along the pot rim during head motion, with no hand near: early, safe, but only 11 rows.
- [V] R7. Twin-plank identity: a staging side rule (note 11 s2.2: piece_2 at +y = image right of piece_1; derived from
  public 23/24, so in-sample) applied among peaks within 0.08 of the best, with 8 instead of 4 peaks kept
  (`SIDE=1`, `NPEAK=8`; v1 masks kept in `out/c2/v1/`). Only p23 and e25 masks change (all 38 others identical).
  - p23 now takes the left plank (IoU 0.73, origin 1.5 cm). Window [0, 15], the same as the GT-mask run; dt 0.13 mm,
    dR 0.15 deg (was 24 mm / 2.9 deg).
  - Public, all 20 with GT-free masks (`eval_gtfree_v2.log`): onset err raw median -2 (p10/p90 -22/+15), robust -4,
    late raw/robust 4/2 (p2/p18 GT artefacts, p26 no-hand bump), empty 0, median window 22. dt 0.14/0.46/2.03 mm,
    dR 0.15/0.32/0.58 deg: the GT-mask numbers. Window end within +-2 rows of the GT-mask run in 16/19.
  - e25 is NOT fixed: no candidate on the left plank reaches the top 8 (flat 2 cm planks read only a few mm above the
    stereo table). The window now ends at a48 (C a38), level with the viewed slide at f48-56: borderline, by luck.
    Flat-object detection (planks, and the spoon) needs a non-height cue (colour/texture segmentation against the
    table, or the marker-ball layout).

### Stage C re-run summary (2026-10-07)
| quantity | re-run result | Stage C (above) | label |
|---|---|---|---|
| C3 reproduction | exact from stored npz: 19/19 identical windows, same stats | - | [V] (`r_repro.py`) |
| Frame-0 slot-0 mask | GT-FREE: b/c SGBM, table plane + quadratic level, 2.5-D visible-surface template search of the slot-0 mesh (public rest tilts, yaw 5 deg), one-sided height score, colour tie-break, pot+lid composite, twin side rule; spoon -> blob fallback | GT mesh rendered through a GT-fitted D18 camera | [V] (`r_pose0.py`, `r_mask.py`) |
| Mask accuracy, public | right object 19/20 (p23 needs the side rule); IoU median 0.85 (>= 0.66 in 17/19, p18 thin sweeper 0.45); origin ~1 cm; ~5-8 s/clip | - | [V] |
| Mask accuracy, eval | right object 17/20 by eye; wrong: e20 (cup in the air: nothing on the table, lowest cup score), e25 (twin plank), e36 (spoon blob on the hand) | - | [V visual] |
| Detector on GT-free masks, public 20 | onset err raw median -2 (p10/p90 -22/+15), robust -4; late raw/robust 4/2; empty 0; window median 22; dt 0.14/0.46/2.03 mm; dR 0.15/0.32/0.58 deg | raw 0 (-20/+17), robust -4; late 3/2; dt 0.13/0.46/2.20; dR 0.14/0.34/0.59 | [V] |
| Fresh holdout p45 | window [0, 19] vs pert 46/47; dR 0.17 deg, dt 0.21 mm; exact-tracker AUC 1.0 | not run (no D18 camera) | [V] |
| Wrong identity (p23 before the side rule) | window ends 16 rows after the slide: 24 mm / 2.9 deg; exact-tracker AUC 0.73 | - | [V] |
| Eval windows (20) | 17/18 right-object resting clips end at or before the viewed motion (+-8 f; e5/e14/e19 tight); e20 EMPTY (correct); e32 5 rows; e25 borderline (wrong plank); median 18 rows | argued, not run | [E] vs note-15 viewing |
| Ego/non-ego | all eval C triggers are the ego hand; second person never touches a slot-0 mask | public: no non-ego arm near slot 0 | [V visual] |
| Pose-track changepoint (H4) | oracle-level at sigma_f 0.5-3 deg; 0.03-0.12 deg better than MC in the median; contact bound adds nothing | [H] | [V sim] |

Conclusions of the re-run:
1. [V] The verifier's main caveat is removed. With masks from stereo + mesh search instead of GT-rendered masks, the
   frozen detector gives the same windows (+-2 rows in 16/19) and the same bias. The pipeline needs video, the slot-0
   name and mesh, and public priors only.
2. [V] Identity, not timing, is the risk. A mask on the wrong object (twin planks) gives a late window and a
   centimetre-level anchor bias. The same identity error would also ruin the slot-0 track itself.
3. [E] On eval the rule behaves as designed on all argued special cases: e20 empty, e32 short window ended by the
   lift, early-onset clips (5, 6, 14, 19, 33, 35) bounded at or before the viewed onset.
4. [V sim] H4 confirmed at simulation level, but the gain (< 0.15 deg) is invisible to the scorer. Keep the image
   detector (it needs no tracker) and add the pose changepoint only as a cross-check once per-frame poses exist.

Open:
- e25 twin-plank identity: flat objects (2 cm planks, the spoon) are weak in stereo height. They need a colour/texture
  segmentation against the wooden table or the marker-ball layout.
- e36: the spoon blob fallback picks the hand. A spoon template (Stage B marker layout + note 13 dimensions) or
  rejecting bottom-border skin blobs would fix it.
- A per-class confidence flag (low score, or a near-tie between distinct peaks) should switch to the static-end
  fallback. It is untested beyond the 3 eval failures.

Re-run files:
- Scripts (`work/20/scripts/`):
  - `r_repro.py` (C3 reproduction)
  - `r_prior.py` (size/colour priors)
  - `r_mask.py` (stereo/plane/blob mask; spoon fallback)
  - `r_sgbmtest.py` (SGBM density debug)
  - `r_pose0.py` (2.5-D template search -> mask, depth, pose; `RGT=1` prints GT-pose debug, validation only)
  - `r_run.py` (frozen detector on a given mask)
  - `r_eval.py` (public evaluation)
  - `r_evalsum.py` (eval summary vs note-15 viewing)
  - `r_trig.py` (trigger crops and sheets)
  - `r_cpsim.py` (pose-changepoint simulation)
- Outputs (`work/20/out/c2/`):
  - `repro.log`
  - `prior_obj.json`
  - `pose0_<key>.json`, `mask0_<key>.png`, `mask0_<key>_dbg.jpg`
  - `mask0_pub_sheet.jpg`, `mask0_eval_sheet.jpg`
  - `pose0_pub_summary.txt`
  - `run_<key>.npz`
  - `eval_gtfree.json` (v2 = with the side rule), `eval_gtfree_v2.log`
  - `eval_summary.json`, `eval_summary_v2.log`
  - `eval_view_ref.json`
  - `trig_e*.jpg`, `trig_sheet_evaluation.jpg`
  - `cpsim.json`, `cpsim.log`
  - `v1/` (masks before the side rule), `side/`, `dbg/`
Stage C re-run status: COMPLETE (2026-10-07). Background jobs: none left running.

## Stage C round 3 (2026-10-07 ~12:30, workflow re-run; resume marker)
- State on resume: Stage C and the Stage C re-run are complete (sections above); no jobs running. This round attacks the
  re-run's open items only: (1) flat slot-0 objects (twin planks e25, spoon e36) need a non-height cue for the frame-0
  mask; (2) an AUTOMATIC ego/non-ego label for every contact trigger (replacing the visual check); (3) a per-class
  confidence flag that switches to the static-end fallback. Scripts `work/20/scripts/r3_*.py`, outputs `out/c3/`.
  Earlier `out/c/`, `out/c2/` files are untouched.
- [V] R3-1. Flat-object frame-0 mask by 2-D colour on the stereo table (`r3_flat.py`; sheet `out/c3/flat_sheet.jpg`,
  per clip `out/c3/mask0_<key>.png`, `pose0_<key>.json`, `_dbg.jpg`). Table plane and table region from b/c SGBM (as
  `r_pose0.py`), projected into cam a at a[n]; object cue = (bright, L > 160, and hue angle atan2(a*, b*) < 18 deg,
  i.e. yellower than the orange table: the planks) OR (L more than 35 above the 101-px local median: the pale spoon, whose
  hue equals the table's); open/close/fill holes; components back-projected through cam a onto the table plane; size
  score |ln(l1/L1)| + |ln(l2/L2)| vs planks 22.7 x 13.9 cm (public mesh) or spoon 30 x 5.2 cm (note 13); twin planks by
  the side rule; components connected to the image bottom border = ego arm, never candidates. Masks warped a[n] -> a[0].
  - [V] A global Lab distance to the table median FAILED first: table shading (L 66-155 across one table) and the
    specular highlight on the right of the table dominate. Colour statistics with GT-rendered masks (p23/p24, design
    only): planks L 199-252, a* 123-135, S 14-94; table L 97-148, a* 152-159, S 112-224; spoon and skin share the
    table's hue (a*/b* ratio ~0.5), so only brightness contrast separates the spoon.
  - [V] Public planks vs GT-rendered mask: p23 IoU 0.87 (centroid 3 px; was 0.73 from the height template + side rule,
    and 0.0 = wrong plank before it), p24 0.88 (6 px; was 0.90). Footprints 22 x 12 and 24 x 13 cm (expected 22.7 x 13.9).
  - [V visual] Eval (design check by eye only, nothing fed back): e25 now takes the LEFT plank (piece_1 under the side
    rule; both planks segmented, 22 x 12 cm each). e35 and e36 give the whole spoon (29 x 5 cm, size score 0.11); e36 no
    longer picks the hand. e37 gives the spoon minus the last ~6 cm of handle (23 x 5 cm; the handle end lies in the
    specular highlight). Cost ~6 s per clip.
  - Limits: the cue assumes a pale object on this orange table (true for all flat slot-0 objects in this dataset). The
    side rule is in-sample (public 23/24). The spoon size is from note 13 (no scan). No public spoon clip exists, so
    spoon masks are checked by eye only.
- [V] R3-2. Frozen MC detector (nothing retuned; `r3_run.py`, logs `out/c3/run_pub.log`, `run_eval.log`) on the round-3
  flat masks, then the final pipeline = round-3 masks for planks/spoon, re-run template masks otherwise (`r3_eval.py`,
  `out/c3/final_eval.log`, `final_eval.json`):
  - Public: p23 window [0, 15] (C a21, M a19; pert 18/19), p24 [0, 5] (pert 8): the same window ends as the GT-mask run.
    All-20 statistics are unchanged from the re-run v2: onset error raw median -2 (p10/p90 -22/+15, range -40..+20,
    within +-2 in 7/20), robust median -4 (p10/p90 -52/+1); late raw/robust 4/2 (p2, p18 GT artefacts; p26 no-hand
    bump; p18 one row vs robust); empty 0; window median 22 rows; anchor bias dt 0.14/0.46/2.03 mm, dR
    0.15/0.32/0.58 deg (median/p90/max).
  - [E vs note-15 viewing, +-8 f] Eval flat clips now end before the viewed motion with the RIGHT object: e25 C a29,
    M a36 -> row 32 (viewed grip f32, slide f48-56; was row 77 with the wrong plank, row 44 borderline after the side
    rule); e35 row 20 (grip f16-24, lift f32); e36 row 24 (grip f24-32, lift f40; was row 7 on the HAND mask); e37 row 20
    (touch f16, lift f40). Across all 20 eval clips: no window ends after the viewed first motion + 8 f; 1 empty (e20);
    median window end row 20.
- [V] R3-3. Confidence flag (`r3_eval.py`, inference-safe): template classes are flagged when the final score is below
  half the public median of their class family (leave-own-episode-out; cups pooled because beige_cup is never public
  slot 0) or the colour distance dcol > 12; flat classes when fewer than 1 (spoon) / 2 (twin planks) footprints have
  size score < 0.5. Result: 0/20 public flagged (no false alarm), 1/20 eval flagged = e20 (final 0.17 vs threshold
  0.27, dcol 19: the cup in the air at f0), which is exactly the clip whose window is EMPTY and needs the static-end
  fallback. The other two former failures (e25, e36) are no longer failures after R3-1. [E] The flag has one true
  positive and no false positive, so its recall on other failure modes is untested. Racks score 0.14-0.21 (covered by
  the pot or spoon) and need their own low threshold (0.07-0.10); the class-relative rule handles that.
- [V, negative] R3-4. Automatic ego / non-ego label of the contact trigger (`r3_ego.py`; `out/c3/ego_all.log`,
  `ego.json`, sheet `out/c3/ego_sheet.jpg` = all 40 triggers, `ego_other_sheet.jpg`).
  - Cue 1 (ROI-local): the touching intruder, joined across fragments by a 21-px closing; its far end (farthest 5 % of
    pixels from the object centroid) gives the approach direction; ego if within 60 deg of image-down. It labels 30/40
    triggers ego and 10 'other'. By eye all 10 'other' are wrong or meaningless: 7 are the wearer's own hand reaching
    in from the side (p12 64 deg, p24 -63, p42 61, e16 63, e33 148, e35 -111, e36 108), e32 is the hand already on the
    cup at f0 (far end only 69 px), e3 is a pot-rim registration edge, e20 is the wrong (pitcher) mask. A half-plane
    rule (far end below the object) still mislabels 4 ego hands. The change map inside the ROI rarely contains the
    forearm (the top intruder reaches the 10-px ROI border band in only 11/40), so the direction is that of the
    fingers, not of the arm.
  - Cue 2 (full frame, `out/c3/skin_try.jpg`, 8 trigger frames): skin by Lab (L > 90, chroma 8-40, hue angle 33-65
    deg) plus connectivity to the bottom border. Palms are found, forearms are not (lower chroma), so no hand connects to
    the border; and the table's specular highlight passes as skin. Not pursued.
  - [V visual] All 40 triggers (20 public incl. p45, 20 eval, round-3 masks) checked on `ego_sheet.jpg`: each is the
    wearer's bare hand/forearm (white watch visible in several) or non-hand change (table reflections p0/p2, pot rim
    e3, the wrong-object mask e20). No trigger comes from the second person, who appears only at the left border in
    e8, e14, e15, e16, e19, e25, e28, e30. So, as before, ego/non-ego rejection cannot change any anchor window in this
    data; an automatic ego test is still unbuilt. [H] If one is needed (hand tracking), seed the two ego hands from the
    f0 "open hands" pose present in most clips and track them, or use a learned hand segmenter; a colour or local-change
    rule is not enough.
- [V] R3-5. Onset error by signal on the final GT-free pipeline, public 20 (frames, detector b/c index minus GT row;
  `final_eval.json`):

  | signal | raw pert: median (p10/p90) [min, max], within +-2 | robust pert: median (p10/p90), within +-2 | onset after robust pert |
  |---|---|---|---|
  | contact C (2 frames, touch >= 120 px) | -10 (-32/+5) [-50, +10], 1/20 | -14 (-62/-3), 1/20 | 2/20 |
  | object motion M (>= 2 mm + 0.15 x head flow) | +2 (0/+33) [-10, +108], 9/19 (p27 never fires) | +1 (-18/+27), 11/19 | 11/19 |
  | combined MC = min(M, C + 10) | -2 (-22/+15) [-40, +20], 7/20 | -4 (-52/+1), 6/20 | 4/20 (window end late: 2) |

  Contact leads the first 1 mm perturbation by a median 10 frames (0.5 s): hands rest on the object first. Motion is
  on time in about half the clips but has a long late tail. The combination is what makes the window safe.

### Stage C round 3 summary (2026-10-07)
| item | result | label |
|---|---|---|
| Flat slot-0 masks (planks, spoon) | 2-D colour cue on the stereo table (hue for planks, local brightness for the spoon), metric footprint on the plane, size score, side rule, bottom-border ego rejection. Public p23/p24 IoU 0.87/0.88; e25 left plank, e35/e36 whole spoon, e37 spoon minus ~6 cm of handle | [V] public; [V visual] eval |
| Detector on the final masks, public 20 | unchanged from re-run v2: onset err raw median -2 (p10/p90 -22/+15), robust -4; late windows 2 (p18 by 1 row, p26 no-hand bump; 4 vs raw incl. GT artefacts p2/p18); empty 0; dt 0.14/0.46/2.03 mm, dR 0.15/0.32/0.58 deg | [V] |
| Eval windows | no window ends after the viewed first motion (+8 f); e25 32 (was 77/44), e36 24 (was 7 on the hand), e35/e37 20; e20 EMPTY; median end row 20 | [E] vs note-15 viewing |
| Confidence flag | class-relative score + colour (template) or footprint count (flat): public 0/20 flagged; eval flags e20 only (the one clip that needs the fallback) | [V] public; [E] eval |
| Automatic ego/non-ego | ROI-local approach direction mislabels 7 ego hands that reach in from the side; full-frame skin connectivity misses forearms. Visual: all 40 triggers are the wearer or non-hand change; no non-ego trigger exists | [V, negative]; [V visual] |

Round-3 files: scripts `work/20/scripts/r3_peek.py`, `r3_flat.py`, `r3_run.py`, `r3_eval.py`, `r3_ego.py`; outputs in
`work/20/out/c3/`: `f0_<key>.jpg`, `f0_sheet.jpg`, `seg_try1.jpg`, `seg_try2.jpg`, `mask0_<key>.png`,
`mask0_<key>_dbg.jpg`, `pose0_<key>.json`, `flat_sheet.jpg`, `run_<key>.npz`, `run_pub.log`, `run_eval.log`,
`final_eval.json`, `final_eval.log`, `ego.json`, `ego_all.log`, `ego_<key>.jpg`, `ego_sheet.jpg`, `ego_other_sheet.jpg`,
`skin_try.jpg`, `other_person_sheet.jpg`, `dbg_p13_ch.jpg`. Earlier `out/c/` and `out/c2/` are untouched.
Stage C round 3 status: COMPLETE (2026-10-07). Background jobs: none left running.

## Verification round 2 (skeptical verifier, 2026-10-07, claims A1 and B1; scripts `work/20-verify/v2_*.py`)
- Resume marker. Scope: A1 (a/b/c frame pairing) and B1 (spoon frame layout, P(B)). Earlier verifier outputs in
  `work/20-verify/` are reused only as cross-references; load-bearing numbers are re-derived with new code.
- [V] A1, decode artefact excluded: ffprobe on p11/p21/p22/e20 shows identical a/b/c containers (h264 with B-frames,
  one edit list with media time 1024 = 2 frames, identical durations and nb_frames, first frame PTS 0). Any
  decoder applies the same leading-frame handling to all three streams, so the a-vs-b index offset is in the content.
- [V] A1, geometric pairing test with NO motion model (`v2_abepi.py`): SIFT matches a[k+j] -> b[k] (and c[k+j] -> b[k])
  on the 30 fastest-tilt b frames, signed distance to the CALIBRATION epipolar line (a->b extrinsic as given; c->b
  left_to_right), regressed on b's vertical image speed. The true pairing is the j whose slope is ~0 and whose
  residual scatter is minimal. p21: a j+2 slope -0.10 (sd 0.36 px) vs j+1 +1.24 (sd 0.71) and j+3 -1.24 (sd 0.88);
  c j0 slope -0.007 (sd 0.07 px) vs j+-1 +-1.3. So a[k+2] ~ b[k] in p21 and c[k] ~ b[k], as claimed.


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 19](19-collision-hulls.md) · [21 →](21-synthesis-round4.md)
