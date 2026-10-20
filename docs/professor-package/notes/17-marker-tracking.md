[← Index](../README.md) · [Summary](../00-summary.md) · [← 16](16-synthesis-round3.md) · [18 →](18-room-map.md)

# 17 — Marker tracking feasibility (DIG 17)

Agent 17, started 2026-10-06. Research/analysis only. Markers: [V] verified, [E] estimate, [H] hypothesis.
Work dir: `/Users/aebatirel/Documents/Code/v2d-research/work/17/` (all scripts and outputs below are relative to it
unless a full path is given). Python: `/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python`.

Goal: decide whether mocap marker spheres (modelled in the scans; GT = rigid-body fit to them) can be the PRIMARY
6-DoF tracker, or only a spin/identity cue. Three stages; this file is appended stage by stage.

- Stage A (done 2026-10-07): marker sphere catalogue from the scans; per-frame mocap-world cameras for public eps
  (12, 21, 26, 0) with a stated accuracy.
- Stage B (done 2026-10-07; log below, summary in B12): visibility census per object/segment/camera, marker size and
  contrast, automatic sphere detectors with recall/precision, GT-video timing. Detector scripts use `work/17/venv17`
  (scikit-learn); the rest use the shared venv. Stage-B resume run (07:25): B13-B20 are appended AFTER the stage-C log
  (fresh holdout eps 13/22 census + detector, per-object timing, sweeper in-hand GT offset); current summary = B20.
- Stage C (done 2026-10-07 08:15): marker-based 6-DoF tracker prototype with real detections, errors vs GT, verdict.
  Log C1-C6 (first session) sits before the stage-B resume; C7-C10 (resume run) are at the end of the file.
  **The final verdict is in the next section.** It supersedes the stage summaries (A9, B12, B20) where they differ.

## Final summary and verdict (2026-10-07, all three stages)

**Verdict: HYBRID.** Markers are not a primary tracker for the cups, pot, pitcher, sweeper or dust pan. They should be a
correction layer on a model-based tracker. The pot lid is the only moving object a stand-alone marker tracker follows.
Static racks are also held by it (AUC 0.96-0.99), but they do not need a tracker. The sweeper and dust pan are excluded
by the census and detector results (B), not by tracker runs. Beige cup and wooden pieces are untested (no marker-registered
cameras).

What the evidence says (details and file paths in the sections cited):
1. **Stand-alone marker tracking fails except for the lid [V, real detections, 6 public eps incl. 2 unseen; C3, C4, C8].**
   The tracker starts from a coarse init (20 mm / 5 deg), uses VO cameras, and its detector was trained on other episodes.
   - Lid: full (>= 3 marker) fixes in 0.98-1.00 of frames, ADD ~9 mm, AUC 0.977.
   - Cups, pot and pitcher are lost at the first grasp or carry in all 6 eps (AUC 0.15-0.76). That includes ep 22, where
     all four cup markers face the head.
   - Two causes. Per-view detection recall in hand is 0.26-0.45 (B19), so association breaks. 2-marker fixes leave one
     rotation free and lock in biased poses (cup at rest: 27-33 mm / 12-21 deg).
   - Prior-free acquisition from inter-marker distances is rare. Cup, pot, rack and pitcher: 0 acquisitions. Lid: 4/24
     frames, 1 of them a 177 deg flip (C4).
2. **Markers correcting a model-based prior work well [V for the marker side; the prior is EMULATED as GT + AR(1) noise;
   6 eps incl. 2 unseen; C5, C7, C7b, C8].** With a 10 mm / 5 deg prior:
   - The cup gets fixes from >= 2 markers in 0.22-1.00 of rest frames, 0.64-1.00 held and 0.53-0.98 carried. In ep 22 it
     gets full fixes in 0.86-0.99 of frames.
   - On fix frames, ADD falls from 16-24 mm (prior) to 6-18 mm. 3-marker fixes: t 5-8 mm, r 1.6-5 deg. 2-marker fixes:
     t 6-12 mm, r 3-14 deg.
   - Trajectory AUC rises by +0.03 to +0.10 when each frame uses its own fix (fused). It rises by +0.05 to +0.11 with
     offline interpolation of the corrections (carry); the robust K=2 carry reaches up to +0.12. The lid gains +0.09.
   - The two unseen eps match the in-sample ones. Ep 13 cup: 0.879 -> 0.932 -> 0.946. Ep 22 cup: 0.874 -> 0.973 -> 0.975.
   - With a 20 mm / 10 deg prior, carry gains are +0.01 to +0.26 (mean +0.17), but single fixes become unreliable.
3. **Spin and identity: the most valuable use, but only through a temporal vote [V, emulated prior; C6, C7a, C8, C10].**
   - A model-based tracker cannot see the cup's spin. A constant 90/180 deg spin error drops the cup's AUC to 0.19-0.44.
   - The carry recovers 0.81-0.95, and 0.90-0.98 when it uses 3-marker fixes only.
   - Single-frame spin choices are unreliable. One cause is the blue cup's rim pair: a 180 deg turn maps it to within
     9.5 mm of itself, so at rest in ep 13 only 13/27 choices were right. The other is prior tilt (10/62 right at 20 mm / 10 deg).
   - A vote over fix frames fixes this: 9/10 runs correct. With an abstain rule (winner >= 4 votes and >= 2x the runner-up),
     every decision is correct or abstains, including over frames 0-39 only.
4. **Slot-0 anchor [V, emulated prior; C7, C7d].** A single marker fix at frame 0 can be wrong and then corrupts the
   scorer alignment (episode mean 0.380 -> 0.152). Pooling all fixes over the static prefix fixes this when the prefix
   has enough fixes:
   - pot ep 0 at 20 mm / 10 deg: 0.355 -> 0.620;
   - cup ep 12 with a spin error: 0.567 -> 0.889;
   - cup ep 13 (unseen) at 10 mm / 5 deg: 0.833 -> 0.897.
   When the prefix has 0-1 fixes, the pooled anchor should take only the voted spin from markers.
5. **Error floors and failure modes [V; A, B, C1, C2, B14-B16].**
   - Camera error is 1-1.4 mm median.
   - Scan-vs-image marker offsets are 1-3 mm for large markers and 3-6 mm for small ones, and are not consistent across
     episodes. They put a 7 mm / 7 deg bias on the lid.
   - The sweeper's in-hand GT is offset 5-10 mm from its own markers.
   - Small markers have recall < 0.13.
   - The pitcher and the resting rack show only 2 markers to the head.
   - Some wrong fixes pass the prior-consistency gate: 3-18 % of fix frames are worse than the prior (20-30 % for the
     ep-0 pot). They need quality weighting in the smoother.
6. **Timing [V; C9, A4, B20.3].** The half-frame b/c offset costs only 0.002 AUC per object, so ignore it. Using cam-a
   frames without the per-episode delta (1.1-2.1 frames) costs 0.017-0.045 (worst 0.109), so apply the delta.
7. **Runtime [V].** 0.4-1.4 s/frame for 2 objects x 3 cameras in single-process Python on CPU (host load 6-28). That is
   about 1-2 CPU-hours for the 20 eval episodes, with no GPU.

**Expected AUC impact [E].** These are perception-level numbers before the policy.
- Objects that can use markers: pot (6 eval eps), blue cup (5), beige cup (2, untested: assumed like the blue cup [H]),
  lid (1), pitcher (1); the rack (5) is mostly static. Excluding the rack, they make up 0.375 of the episode-weighted
  object slots.
- Accuracy refinement alone: +0.08 per object with a 10 mm / 5 deg prior and +0.17 with a 20 mm / 10 deg prior. That is
  **+0.03 to +0.065 mean AUC at the perception level**, roughly **+0.02 to +0.04 on the board** after policy dilution (x0.5-0.8).
- Spin and anchor: each cup or pot whose spin the main pipeline gets wrong gains +0.4-0.75 per object (about +0.01-0.02 on
  the board per object). Each slot-0 anchor rescued gains about +0.3-0.8 per episode (+0.015-0.04 on the board per episode).
  The ten eval episodes with a cup or pot in slot 0 are 1, 3, 5, 6, 8, 10, 14, 20, 32 and 33.
- **Total: about +0.02 to +0.10 board AUC, central about +0.04.** The upper end applies if the model-based pipeline often
  gets cup or pot spin wrong; note 11's placement priors may already fix some of that.
- This is conditional. Markers add nothing for objects the model-based tracker has lost (no prior-free re-acquisition),
  or for the spoon (10 eval eps; no public GT or marker layout), sweeper and dust pan; by the coarse census [E], the
  wooden pieces are also unlikely to gain.

**What a hybrid needs (recommended design, from what worked here):**
- prior-guided detection in 3-sigma windows with the z-buffer marker prediction, on cams b and c, plus cam a with the
  per-episode delta and its 0.28 deg rotation fix;
- robust 2/3-marker fits that keep the prior's rotation about a 2-marker axis;
- an offline smoother weighting 3-marker fixes above 2-marker ones (K=2 medoid carry was a net gain);
- a spin vote per static or grasp segment with an abstain rule;
- a pooled static-prefix slot-0 anchor;
- the lid tracked by markers directly.
Detector models are trained on automatic public labels only. Inference reads no GT (the evaluator alone maps VO to mocap).

**Main limitation.** The model-based prior was emulated (GT + AR(1) noise, optionally a constant spin error). The size of
the hybrid gain depends on the real tracker's error structure (bias, losses, spin changes at regrasps), which was not
measured here. That is the next experiment.

## Stage A log (append-only)

- 2026-10-06 start. Fresh start (no partial notes or work files existed). Inputs reused: note 12 marker scripts
  (`work/12/markers.py`, `out/markers_raw.json`: 5 kitchen objects, dark-mount + RANSAC, with false positives), note 13
  grey-blob sphere fits (`work/13/out/markers.log`, all 10 public scans, noisy for pot/lid/rack/pitcher), note 11
  frame-0 GT-silhouette cameras (`work/11/s25_refine_native.json`, eps 12/13/21/0/26/22; heading ~1-2 deg, pitch 2-5 deg
  per note 11 §8.3) and the 14-term cam_a distortion model (cv2 rational + thin prism + tilt).

### A1. Marker sphere catalogue from the scans [V]
Method (`markers_cat.py`, `final_cat.py`; out `out/marker_catalogue.json`, logs `out/markers_cand_all.log`,
`out/markers_small.log`, `out/markers_small_rest.log`): 2-3 M area-weighted surface samples with outward face normals; each
sample votes for a sphere centre c = p - r n for r = 2.5..9 mm (normal Hough, 1.5 mm voxels); peaks refined by LSQ
sphere fit on samples within r+1.5 mm (|d-r| < 0.6 mm, normal agreement > 0.7), 6 iterations. Kept: angular coverage
>= 0.6, rms <= 0.3 mm, sphere brighter than its 1.5-6 mm ring (black mount) by > 0.1. Cross-checks: dark-cluster scan
(`dark_check.py`) for mounts without a sphere, zoom renders (`render_zoom.py`, `out/zoom_*.png`). Runtime ~3 s/object.
- The large spheres are modelled almost completely (coverage 0.86-0.99, fit rms 0.14-0.28 mm): they are clean CAD-like
  spheres, not photogrammetry blobs. Fitted r 6.6-7.8 mm (one physical size, ~14 mm, with ~+-0.5 mm scan scatter [E]).
- **Small markers exist** (r 3.5-4.1 mm, ~7-8 mm diameter) and were missed by notes 12/13: 5 on mini_dust_pan (its only
  markers; note 13 reported "0 markers"), 2 on white_pot, 2 on white_pot_lid (one only in texture).

| object | markers | radii mm | pairwise spread mm | notes |
|---|---|---|---|---|
| beige_cup | 3 large | 7.25-7.36 | 85-100 | near-equilateral (note 12); closest pair-distance difference 6.5 mm |
| blue_cup | 4 large | 7.38-7.80 | 90-163 | |
| white_pot | 4 large + 2 small | 7.1-7.3 / 3.7 | 76-217 | small at (41,-81,-52), (-6,-90,7) mm; note 12's 7th was a mount double-count |
| white_pot_lid | 3 large + 2 small | 7.2-7.7 / 4.1, ~4 | 46-129 | small #2 at ~(5.6,-12.8,-47.3) is texture-only (flattened), centre [E +-3 mm] |
| water_pitcher | 4 large | 7.1-7.3 | 82-152 | |
| plastic_dish_rack | 4 large | 6.6-7.6 | 147-497 | static in eps 12/13/26 -> camera anchor; 40 rack-wire false candidates rejected by contrast/coverage |
| mini_sweeper | 3 large | 6.8-7.1 | **32-46** | very compact triangle: weak rotation lever arm |
| mini_dust_pan | 5 small | 3.5-3.8 | 50-148 | grey spheres on yellow, no black mount |
| wooden_piece_1 | 4 large | 6.7-7.1 | 79-230 | all on +x face |
| wooden_piece_2 | 3 large | 6.9-7.0 | 66-207 | all on -x face |
| wooden_spoon | (3, video only) | - | - | no public scan (note 13) |

- Expected image sizes at 0.5 m [E]: large sphere ~33 px in cam a (f 1150), ~16 px in cam b/c (f ~567); small
  ~17 px (a) / ~8 px (b/c). Small markers in the mono pair are near the detection limit.
- Geometric minimum for 6-DoF from markers alone is 3 non-collinear visible markers; every object except the spoon
  (unknown layout precision) has >= 3, but the sweeper's lever arm is only 32-46 mm.

### A2. Frame-0 cameras: first attempts (ep 12) [V]
- Overlay of GT-placed markers through the note 11 s25 camera (`overlay.py`, `cropsheet.py`, `out/ov_12_0_a.jpg`,
  `out/cs_12_0_{a,bc}.jpg`): far rack markers land within ~5-10 px (cam a), but the near blue-cup rim marker is ~50 px off
  in all three cameras. Consistent with a ~1-2 cm camera-position plus ~1-2 deg rotation error of the silhouette fit
  (note 11 reports heading 1-2 deg, pitch 2-5 deg). s25 is a usable search prior, not a measurement-grade camera.
- Single-frame PnP on detected marker blobs fails at f0: only 3-5 markers are visible across two objects; with a
  generic LoG blob detector the scene clutter (rack pegs, edges) out-scores the spheres (`dbg_det.py`), and a
  3-point solution moved 6-10 deg / 5-10 cm (`f0_refine.py`, `f0_fit.py`). Masked NCC against textured scan patches
  (`rend17.py`, `tm_test.py`) also fails (scores 0.3-0.6, baked scan lighting differs from video). z-buffer
  visibility is unreliable near edges while the camera is several px off (rack markers predicted hidden are visible).
- Decision: estimate camera MOTION from the static room background (stereo VO on the global-shutter mono pair b/c,
  metric from the 75 mm baseline), then fit ONE 6-DoF registration per episode (VO frame -> mocap world) from marker
  observations pooled over all frames. Per-frame marker evidence is weak; pooled over ~100-300 frames it is not.

### A3. Stereo VO on the mono pair (camera motion, metric) [V]
`vo17.py <ep>` -> `out/vo_public_<ep>.npy` (T x 4x4, pose of cam b in the b@f0 frame), `out/vo_public_<ep>.json` (log).
SIFT (4000) in b and c, b-c matches gated by the calibrated epipolar constraint (< 1.5 px), triangulated (75 mm
baseline, reproj < 1 px both views, depth 0.2-12 m); tracking = PnP (AP3P RANSAC 2.5 px, LM refine on < 1.5 px) of b_t
against the current keyframe map (fallback: last 4 keyframes); new keyframe when inliers < 45 % of its map or every
40 frames. 25-60 s per episode on CPU. (A first version kept stale poses after failures and lost 110 frames on ep 0;
fixed.)

| ep | frames | failed | keyframes | min PnP inliers | max med reproj px (b) | max head rotation from f0 | max translation |
|---|---|---|---|---|---|---|---|
| 12 | 181 | 0 | 5 | 218 | 0.55 | 3.4 deg | 22 mm |
| 21 | 186 | 0 | 8 | 140 | 0.74 | 9.7 deg | 52 mm |
| 26 | 158 | 0 | 5 | 147 | 0.69 | 6.3 deg | 22 mm |
| 0 | 373 | 0 | 16 | 69 | 0.82 | 9.5 deg | 70 mm |

- Head motion is small but not negligible: 3-10 deg and 2-7 cm; at 0.5 m, 3 deg is ~2.6 cm of apparent object motion.
  A frame-0-only camera is therefore not enough for per-frame marker analysis.
- VO jitter (white-noise bound from 2nd differences, ep 12, first VO version): <= 0.5 mm and <= 0.04 deg per frame.
  Drift (chained vs direct PnP to the f0 map, `vo_check.py`, first VO version, ep 12): rotation median 0.07 deg (max
  0.20), translation median 3.8 mm (max 12.6). Translation is the weak part (background mostly 1-5 m away).

### A4. cam a vs mono pair: time offset and extrinsic bias [V] (relevant to D19)
`a_pnp.py <ep>` (per frame: SIFT on half-res cam a matched to the b_t/c_t stereo points of the SAME frame index -> PnP
gives the measured a->b_t transform; ~1.1 px reprojection, 80-170 inliers), `sync_fit.py <ep>` (fit
T_meas(t) = VO(t)^-1 VO(t - delta) T_ext with VO slerp-interpolated; outputs `out/sync_<ep>.json`), `shift_test.py`.
- **The colour camera and the mono pair are NOT frame-synchronous, and the offset differs per episode:**

  | ep | delta (frames; cam a frame t was exposed delta earlier than b/c frame t) | ms | corr(deviation, angular velocity) |
  |---|---|---|---|
  | 12 | +1.140 +- 0.012 | +57.0 | -0.91 |
  | 26 | +1.148 +- 0.018 | +57.4 | -0.87 |
  | 21 | +2.135 +- 0.013 | +106.7 | -0.88 |

  Integer part varies (1 or 2 frames), fractional part is stable (~0.14 frame = 7 ms). The integer shift test
  (`shift_test.py 12`) agrees (b frame t-1 matches a frame t best). Ep 0 pending. The "match frames by frame_index"
  rule holds only up to 1-2 frames between a and b/c; at typical head rates (0.2-0.5 deg/frame) this is 0.2-1 deg.
- With delta fitted, the residual per-frame a-vs-b rotation is 0.03-0.09 deg (vs 0.22-0.54 deg without) and
  translation sd 2.4-5 mm (PnP noise against a 75 mm-baseline map).
- **Constant extrinsic bias** (same on all three eps): rotation correction (-0.06..-0.08, +0.15..+0.18, -0.20..-0.22) deg
  (|.| ~0.28 deg, ~5 px at f 1150) and translation (~0, +0.6..+1.5, -5.2) mm (the -5 mm along the optical axis may be a
  stereo-depth-scale artefact, not a real offset [H]). The ~0.28 deg rotation is reproducible to 0.01 deg [V]; apply it
  when fusing cam a with b/c.
- Which stream is synchronised with the mocap GT is not yet determined (needs a moving object with markers seen in
  both a and b/c after registration).
- Ep 0 (`out/sync_0.log`): delta = +1.102 +- 0.022 frames (55 ms); rotation correction (-0.09, +0.18, -0.19) deg (same as
  the other eps); translation correction (-1.2, +0.5, -0.9) mm, i.e. the -5 mm of eps 12/21/26 is NOT reproducible ->
  only the rotation correction is applied downstream.

### A5. Registration VO -> mocap world, per-frame cameras [V for ep 12; others running]
Stage 1 (`reg17.py <ep> 3`, `out/reg_<ep>.{json,log}`): one 6-DoF transform from GT-placed markers of GT-static objects
(centre < 5 mm/s, rotation < 0.5 deg/s over +-2 frames), every 3rd frame, cams a/b/c, HoughCircles (ALT) candidates at
the predicted sphere radius, nearest association, Cauchy LSQ, windows 90 -> 8 px. Init = note 11 s25 frame-0 camera.
- **The s25 silhouette cameras are off by ~6-7 deg and 5-8 cm** (ep 12: 5.9 deg, dC (-52, +1, +39) mm; ep 26: 6.9 deg,
  dC (+56, -15, -52) mm). Mostly pitch (ep 12 pitch 32.4 -> 38.3 deg) traded against position along the view ray; the
  heading changes only ~0.5 deg, so note 11's W table is unaffected [V ep 12/26], but s25 must not be used as a metric
  camera. After registration the GT-posed rack/cup/pot silhouettes and markers sit on the video
  (`out/sil_12_0_a_reg.jpg`, `out/sil_26_0_a_s.jpg`).
- Stage-1 residuals ~3.8 px (cam-a equivalent) median; within-frame scatter only ~1.1 px but frame-mean sd ~3 px ->
  per-frame camera error dominated (cause: the a-vs-b time offset of A4 and slow VO drift).

Stage 2 (`reg2.py <ep> 15 1`, `out/reg2_<ep>.{json,log}`): b-pose(t) = Treg D(t) VO(t); c = b * T_b<-c;
a-pose(t) = Treg D(t-delta) VO(t-delta) T_b<-a with delta and the extrinsic rotation correction from A4; D(t) = slow
drift correction (6-DoF knots every 15 frames, D(0) = I, random-walk prior 0.05 deg / 2 mm per knot); all frames,
windows 12 -> 6 px. Validation: leave-one-marker-out (LOMO) refits, held-out marker residuals.
- Ep 12: 305 observations (a 241, b 19, c 45) of 7 markers (rack 3, cup 4) on static objects; in-sample residual
  median 1.98 px, p90 4.2 (cam-a eq.); drift knots stay small (max 0.06 deg, 2.9 mm).
  **LOMO held-out residual median 2.6 px, p75 3.7, p90 4.8 (cam-a eq.) = 1.1 mm median / 2.2 mm p90 lateral at the
  marker depth (0.35-0.65 m)**. Detection noise alone is ~1.1 px, so the camera error is ~2 px ~0.9 mm [E].
- Camera files: `out/reg2_<ep>.json` keys `cams` (cam a, per frame: Rwc columns = x right, y down, z forward in mocap
  world; C = centre), `cams_b`, `cams_c` (own poses), `Treg`, `delta`, `obs`, `lomo`.

### A6. Side findings while building cameras
- [V] Parquet metadata `pose_note`: "Object xy is centred per episode on the mean of its visible object positions; z is not
  centred. The offset is baked into the pose values and is not recorded." So the GT "world" is the mocap world up to an
  unknown per-episode xy translation (one offset per episode: in ep 12 the static rack is at (-0.038, -0.062), not at
  the origin). Our per-episode registration absorbs it; any cross-episode room map needs a per-episode xy offset.
- [V] `timestamp` advances at 20.254 Hz (= info.json fps) while `capture_time` advances at ~20.0 Hz; capture_time -
  timestamp grows from 33 ms to 146 ms over ep 12 (181 frames). What each clock means is undocumented.
- [E, weak] GT-vs-video time offset (`gt_sync.py 12`, `out/gtsync_raw_12.npy`): predicting markers of GT-MOVING objects
  with GT at t+s and the stage-2 cameras, the most < 4 px matches occur at s ~ -0.5 frame for cams b/c and s ~ -1.25..-1.5
  for cam a, i.e. video frame t shows the scene ~0.5 (b/c) / ~1.3 (a) frames BEFORE GT row t, with no clear growth
  over the episode. Evidence is thin (moving-marker detections: 9-15 matches per shift; blur and hands) -> repeat in
  stage B with a proper detector and more episodes before acting on it. If it holds, a cam-a tracker lags GT by
  ~65 ms (~3 cm at 0.5 m/s) on eps like 12, and more on eps where delta(a,b) = 2 frames (ep 21).
- Stage-1 for ep 21 without the sync model was poor (29 obs, 5 px, formal sd 1.2-1.7 deg / 17-20 mm): its 2.1-frame
  a-b offset corrupts cam-a predictions. `reg17.py` now uses delta and the extrinsic rotation correction when
  `out/sync_<ep>.json` exists (env NOSYNC=1 restores the old behaviour); rerunning 21 and 0 (chain2.sh, running).

### A7. Ep 12 camera accuracy, detailed [V] (`reg2_anal.py 12`, `reg2_lobo.py 12 15 0 30`, `out/lobo_12.log`)
- Per-marker MEAN offsets after stage 2 are 0.13-1.03 mm (rack m2, cam a only, 15 obs, is the largest): the catalogue
  sphere centres agree with the GT rigid-body poses to <= ~1 mm in the video. So scan markers ARE the mocap markers
  in the GT body frame to ~1 mm [V on blue_cup x4 and rack x3; other objects pending].
- cam a residual split: within-frame scatter sd ~1.1 px (detector + marker model), frame-mean sd ~1.5 px over 75 frames
  (= remaining per-frame camera error, ~0.6-0.7 mm or ~0.07 deg at 0.5 m).
- Leave-one-block-out (all static observations of a 30-frame block held out, refit, predict): median 2.36 px (1.0 mm),
  p90 4.5 px (2.0 mm); per block 0.87-1.28 mm median for gaps of 15-30 frames. Same as LOMO (1.1 / 2.2 mm), so VO plus
  the drift prior bridges >= 1.5 s without visible degradation.
- **Ep 12 per-frame camera accuracy statement: ~1 mm median, ~2 mm p90 lateral at 0.35-0.65 m (2-2.5 px cam-a
  equivalent including ~1 px detector noise); rotation ~0.05-0.1 deg; head path 25/15/21 mm, max 3.4 deg.**

### A8. Ep 26 and stage-1 results for 21/0 [V]
- Ep 26 stage 2 (`out/reg2_26.log`): 307 obs (a 222, b 51, c 34) of rack m1/m3 + pot m0-m3; in-sample 2.22 px;
  **LOMO median 2.82 px = 1.20 mm, p90 4.95 px = 2.18 mm**; per-marker mean offsets 0.15-0.44 mm (pot markers in the
  GT body frame to < 0.5 mm); drift knots max 0.08 deg / 2.3 mm; frames with >= 1 / >= 3 observations 0.68 / 0.23,
  longest gap 19 frames; head max 6.3 deg.
- Stage 1 with the sync model: ep 21 2.88 px median, 74 % < 4 px (vs 5.2 px / 31 % without sync); ep 0 3.53 px (279 obs).
- Frame-0 heading/pitch vs note 11 s25 (deg): ep 12 dpsi +0.61, dth +6.10; ep 26 dpsi -1.78, dth -6.75; ep 21 dpsi +0.79,
  dth -0.72; ep 0 heading 182.83 (s25 181.4, dpsi ~+1.4), rot 1.17 deg total. So s25 headings carry ~0.6-1.8 deg errors
  and pitches up to ~7 deg; note 11's W LOO (1.2-1.6 deg) is consistent with this. The marker-registered frame-0
  cameras (`out/reg2_<ep>.json` cams[0]) could serve as better W references [H: would tighten W to ~0.1-0.3 deg].
- Ep 21 stage 2 (`out/reg2_21.log`): 185 obs (a 156, b 12, c 17) of cup m0/m1/m3 + pitcher m1/m3; in-sample 2.55 px;
  **LOMO median 2.93 px = 1.38 mm, p90 5.50 px = 2.46 mm**; per-marker mean offsets 0.07-0.41 mm (cup and pitcher markers in
  the GT body frame to < 0.5 mm); drift knots max 0.09 deg / 3.0 mm. BUT coverage is poor: only 35 % of frames have any
  static-object marker, longest gap 103 frames (both objects moving, f~40-140); head max 9.7 deg, path 33/66/22 mm. Inside
  that gap the camera is VO + drift prior only; LOMO/LOBO-30 do not measure it (long-gap LOBO test pending).
- Ep 0 stage 2 (`out/reg2_0.log`): 914 obs (a 428, b 226, c 260) of pot m0/m2 + lid m0-m4; in-sample 2.51 px;
  **LOMO median 3.29 px = 1.40 mm, p90 5.78 px = 2.44 mm**; per-marker mean offsets 0.07-0.58 mm except pot m2 1.19 mm
  (+2.5 px vertical, cam a only) and the texture-only lid m4 2.5 mm (1 obs; consistent with its +-3 mm estimate); drift
  knots max 0.12 deg / 4.9 mm; coverage 42 % of frames (38 % with >= 3 obs), longest gap 60 frames; head max 9.6 deg,
  path 42/91/31 mm.
- Long-gap test (`reg2_lobo.py <ep> 15 0 <block>`, `out/lobo_{12_90,26_60,0_60}.log`): holding out 60-90-frame blocks
  (gaps to the nearest kept observation up to 102 frames) still gives median 0.84-1.74 mm, p90 1.8-2.6 mm per block;
  all-block medians 0.96 mm (ep 12, 90-frame blocks), 0.96 mm (ep 26, 60), 1.15 mm (ep 0, 60). So VO + drift prior
  bridges 3-5 s; ep 21's 103-frame gap is expected at ~1-2 mm [E, by analogy].

### A9. Stage A summary: cameras and their accuracy
| ep | task | static-marker obs (a/b/c) | LOMO median / p90 (mm, lateral at 0.35-0.65 m) | long-block LOBO median | frames with >= 1 obs | longest gap | delta a vs b (frames) | head max rot / path |
|---|---|---|---|---|---|---|---|---|
| 12 | Cup_In_Dish_Rack | 305 (241/19/45) | 1.12 / 2.22 | 0.96 (90-frame blocks) | 0.69 | 17 | 1.14 | 3.4 deg / 25 mm |
| 26 | Pan_In_Dishrack | 307 (222/51/34) | 1.20 / 2.18 | 0.96 (60) | 0.68 | 19 | 1.15 | 6.3 deg / 24 mm |
| 21 | Water_Can_Blue_Cup | 185 (156/12/17) | 1.38 / 2.46 | not run | 0.35 | **103** | **2.14** | 9.7 deg / 66 mm |
| 0 | Pot_with_lid | 914 (428/226/260) | 1.40 / 2.44 | 1.15 (60) | 0.42 | 60 | 1.10 | 9.6 deg / 91 mm |

- [V] Per-frame cams a, b, c in the mocap world for public eps 0, 12, 21, 26: `work/17/out/reg2_<ep>.json`
  (`cams` = cam a, `cams_b`, `cams_c`; each frame: `Rwc` columns = camera x right / y down / z forward in world, `C` =
  centre; project with `lib17.project(Xw, R, C, cam, own=True)`). Built without any per-episode hand labels: GT object
  poses of static objects + automatic circle detections + stereo VO.
- [V] Accuracy: ~1.1-1.4 mm median, ~2.2-2.5 mm p90 lateral at the object depth on held-out markers (2.6-3.3 px cam-a
  equivalent, of which ~1.1-1.4 px is detector + marker-model scatter); equivalently ~0.1 deg / ~1 mm. Depth-axis
  error is not separately measured (b/c observations constrain it weakly) [E: a few mm].
- [V] Scan marker centres agree with the GT rigid-body poses to 0.1-0.6 mm (1.2 mm worst large marker) on cups, rack,
  pot, lid and pitcher: markers in the scans are the mocap markers in the GT body frame. This is the precondition for a
  marker-based tracker to output poses directly in the GT body frame.
- Limitations: the camera is only as good as the GT static objects and the VO between static periods; the cam-a time
  offset (delta) must be estimated per episode (1 or 2 frames); the GT-vs-video time offset is unresolved [E, A6]; small
  markers (dust pan, pot/lid small) are rarely detected by the circle detector at 6-10 px radius; ep 21's camera inside
  its 103-frame motion gap is unvalidated.
- Next (stage B): per-frame marker visibility census (z-buffer + these cameras) by segment type (static / carried /
  in-hand / occluded), per object and camera; resolve the GT-vs-video time offset with a better moving-sphere detector.
- Visual check [V]: `out/sil_0_330_a_s.jpg` (ep 0 frame 330, after ~10 deg of head motion): GT-posed pot/lid outlines
  and all five lid markers (3 large, 2 small incl. the texture-only one) fall on the video spheres.
- Stage A complete (2026-10-07). Key scripts: `markers_cat.py`, `final_cat.py`, `lib17.py`, `vo17.py`, `vo_check.py`,
  `a_pnp.py`, `sync_fit.py`, `shift_test.py`, `reg17.py`, `reg2.py`, `reg2_lobo.py`, `reg2_anal.py`, `gt_sync.py`,
  `overlay.py`, `cropsheet.py`, `sil_overlay.py`. No background jobs left running.

## Stage B log (append-only)

- 2026-10-07 start (fresh: no stage-B notes or files existed). Plan: (1) z-buffer census of GT-posed markers per frame,
  object, camera and segment type (static / held / carried from GT kinematics) on eps 0, 12, 21, 26 (stage-A cameras)
  plus more eps for objects not yet covered; (2) marker apparent size, image speed, contrast; (3) an automatic sphere
  detector (no pose prior) with recall/precision against projected visible markers.
- Cameras for more eps (beige cup, sweeper, dust pan, wooden pieces): `chain3.sh 31 11 23 18` (background, PID 59774,
  log `out/chain3.progress`, per-step logs `out/{vo,apnp,sync,reg,reg2}_<ep>.log`), same stage-A pipeline; reg2 without
  LOMO. `lib17.s25_cam` now falls back to note 11's coarser `s24_campose_native.json` frame-0 camera (iou ~0.74) as the
  reg17 init for eps not in s25 (backup of the stage-A lib: `lib17_stageA_backup.py`). Convergence from s24 is untested.

### B1. Segment labels from GT kinematics (`seg17.py`) [V definition]
Per object and frame: v, w over +-3 frames; quiet = v < 10 mm/s and w < 3 deg/s; **rest** = quiet run >= 10 frames (0.5 s)
and height within 15 mm of the object's frame-0 or last-frame height; **carried** = not rest and v >= 0.05 m/s;
**held** = not rest and v < 0.05 m/s (slow in-hand motion, held still in the air, nudged, grasp/release). The stage-A
strict "static" (5 mm/s, 0.5 deg/s) wrongly labels nudged/jittering objects (e.g. the ep-12 rack after f 90) as moving,
hence the relaxed v2. GT has no hand data, so "held" is a kinematic proxy (a resting object being touched is "rest").

### B2. z-buffer census, eps 12/26/21/0 (`census17.py <ep>` -> `out/census_<ep>.npz`; `summ17.py 12 26 21 0`) [V, upper bound]
Visible = marker centre inside the image by >= 1 radius AND >= 34 % of 9 disc probes (centre + 8 at 0.7 r) not behind
the splat z-buffer of all GT-posed scans (tol 4 mm). **Hands, arms, table and room are NOT in the z-buffer**, and GT is
taken at row t (no time shift); this is therefore an upper bound on what a detector can see. Fractions of (frame, object)
with >= 3 / 2 / 1 / 0 visible markers ("a|b|c" = distinct markers seen in any of the three cameras):

| object (eps) | seg | frames | cam a >=3 / 2 / 1 / 0 | cam b | cam c | b or c | a, b or c |
|---|---|---|---|---|---|---|---|
| blue_cup (12, 21) | rest | 135 | 0.78 / 0.13 / 0.10 / 0 | 0.78 / 0.22 / 0 / 0 | 0.71 / 0.29 / 0 / 0 | 0.78 / 0.22 | 0.78 / 0.22 |
| blue_cup | held | 98 | 0.98 / 0.02 / 0 / 0 | 0.98 / 0.02 | 0.88 / 0.12 | 0.98 | 0.98 |
| blue_cup | carried | 134 | 0.87 / 0.13 / 0 / 0 | 0.80 / 0.20 | 0.87 / 0.13 | 0.90 | 0.90 |
| plastic_dish_rack (12, 26) | rest | 299 | 0.15 / 0.71 / 0.13 / 0 | 0 / 0.68 / 0.32 / 0 | 0 / 0.86 / 0.11 / 0.03 | 0 / 0.92 | 0.15 / 0.77 |
| plastic_dish_rack | held (nudged) | 40 | 0 / 0.93 / 0.07 / 0 | 0 / 1.0 | 0 / 0.85 | 0 / 1.0 | 0 / 1.0 |
| water_pitcher (21) | rest | 86 | 0 / 1.0 / 0 / 0 | 0 / 1.0 | 0 / 1.0 | 0 / 1.0 | 0 / 1.0 |
| water_pitcher | held | 39 | 0 / 1.0 / 0 / 0 | 0.13 / 0.87 | 0.28 / 0.72 | 0.28 | 0.28 |
| water_pitcher | carried | 61 | 0.56 / 0.44 / 0 / 0 | 0.21 / 0.79 | 0.48 / 0.52 | 0.48 | 0.66 |
| white_pot (0, 26) | rest | 341 | 0.95 / 0.05 / 0 / 0 | 0.63 / 0.37 | 0.74 / 0.26 | 0.97 | 0.98 |
| white_pot | held | 55 | 0.84 / 0.16 / 0 / 0 | 0.44 / 0.56 | 0.64 / 0.36 | 0.89 | 0.93 |
| white_pot | carried | 135 | 0.83 / 0.16 / 0.01 / 0 | 0.63 / 0.36 | 0.78 / 0.21 | 0.96 | 0.96 |
| white_pot_lid (0) | all | 373 | 1.0 (all segs) | 1.0 | 1.0 | 1.0 | 1.0 |

- Geometry alone rarely limits cups, pot and lid: >= 3 markers face the head cameras in 83-100 % of carried/held frames.
  The pitcher (4 markers, 2 facing the user at rest) and the rack (4 markers spread over 0.5 m, often partly out of the
  frame or behind the rack body) mostly show only 2.
- Apparent radius (visible markers, median [p10, p90]): large markers cam a 17.2 px [13.9, 22.0], cam b/c 8.5 [6.9, 11.0];
  small markers cam a 8.4 [7.6, 9.4], cam b/c 4.1-4.2 [3.8, 4.7].
- Image speed (px/frame, own camera, includes head motion; median [p75, p90]): carried cam a 20 [35, 49], b/c 9 [17, 24];
  held a 4.6 [7.2, 10.6], b/c 2.2 [3.6, 5.4]; rest a 3.8 [6.5, 10.3], b/c 1.9 [3.2, 5.1]. Carried markers move by >= 1 own
  radius per frame in the median case, so exposure blur and the GT-video time offset matter for carried objects.
- Visual crop sheets (`crops17.py <ep> <cam> <seg> <n> <seed> <gtshift>`, e.g. `out/crops_12_a_carried_1.jpg`, GT shifted by
  -0.5 frame (b/c clock) and -0.5 - delta (cam a)): most carried blue-cup markers are clearly visible grey spheres on a black
  mount with moderate blur; several are covered by fingers/palm, and at speeds > ~15 px/frame the projection misses by
  up to one radius (time offset / blur) [V, visual, 32 crops].

### B3. Cameras for more eps [V ep 31; eps 11/23 failed from s24, and the multi-start retry failed too (B12)]
- Ep 31 (sweeper + rack): s24 init was 11.5 deg / ~14 cm off but reg17 converged; reg2 (no LOMO) in-sample 2.48 px median
  (491 obs, a 418 / b 37 / c 36), drift knots max 0.14 deg / 5.0 mm -> similar to eps 12/26 [V in-sample only].
  cam-a sync from only 4 a-PnP frames (SIFT a-vs-b matching mostly failed): delta 0.99 +- 0.07 [E].
- Ep 11 (beige + blue cup; s24 iou 0.53) and ep 23 (wooden pieces; iou 0.62): reg17 from s24 diverged (ep 23 ended 28 deg
  from s24 with 10 obs; ep 11 crashed with 3 obs). Kept as `out/reg_23_s24fail.*`. Retrying with `reg17ms.py` (reg17 +
  multi-start grid: heading +-16 deg, pitch +-12 deg, +-15 cm along the axis; best = most residuals < 5 px), chain
  `chain4.sh 23 18` (eps 23, 18) and a separate run for ep 11.

### B4. Marker contrast in the video (`contrast17.py <ep> 2`, `contrast_summ.py`; eps 12/26/21) [V]
At z-visible projected markers (GT shifted -0.5 frame, cam a also -delta), every 2nd frame, 3752 marker-views:
- **Polarity is not fixed**: disc (r < 0.6 R) minus ring (1.3-2.0 R) is spread around zero, median -2..+10 grey levels,
  p10 about -55..-77, p90 about +27..+41 (8-bit). The grey sphere is darker than the white pot, brighter than the blue
  cup, rack shadow and floor; |difference| median 20-32 for large markers, 8-27 for small. A bright-blob (or dark-blob)
  detector cannot work alone; the ring around a sphere is inhomogeneous (ring sd 32-52 grey levels: black mount on one
  side, object surface on the other).
- **The rim edge is the robust cue**: radial gradient at the projected rim (grey levels/px after 0.7 px blur) median 7.7
  (cam a, rest), 4.4 (held), 3.6 (carried) vs 1.2-1.5 on a null ring 3 R away; cam b 12.4 / 6.9 / 7.0 vs 1.6-1.9.
  Fraction with rim edge > 2 x null: cam a 0.79 rest, 0.65 held/carried; cam b 0.86 / 0.76 / 0.78; cam c 0.72 / 0.70 /
  0.75. Motion halves the edge in cam a (rolling/longer exposure blur); the global-shutter b/c lose less.
- Cam-a disc saturation median 11-16 / 255 (markers are achromatic); usable to reject skin/blue/wood candidates.
- Candidate generators tried on ep 12 (every 10th frame, `candrec.py`, `candrec2.py`): DoG blobs (both polarities, 11
  scales) find only 26-70 % of z-visible markers even with ~10-16 k candidates per image -> rejected. Full-frame
  `HoughCircles(HOUGH_GRADIENT_ALT, param2 0.5)` finds 79-96 % in cam a at full res (~3.7 k circles/image) but only 42-65 %
  in b/c at native res; 2x-upsampled b/c gives 71-87 % (~3.4-4.1 k circles/image). These recalls include chance hits
  (a 3 px radius, scale-matched window catches a random circle often at these densities), so they are upper bounds on
  candidate recall; the classifier stage below is evaluated with the same matching rule.
- Eps 0 (pot/lid) and 31 (sweeper/rack), same measure (`contrast_summ.py 0 31`): cam a carried rim edge falls to 3.2
  (large) / 1.9 (small) vs null 1.9 / 1.1, rim > 2 x null only 0.44 (large) / 0.35 (small); cam b/c carried 0.43-0.50.
  Carried small-marker discs in cam a have median saturation 108 (vs 11-28 otherwise) -> mostly something other than the
  grey sphere (fingers or a misprojection).
- **Visual check, ep 0 carried (`out/crops_0_a_carried_3.jpg` vs `out/crops_0_b_carried_3.jpg`, 32 random z-visible
  markers each) [V, visual]: cam a frames are heavily motion-blurred while the pot/lid is carried (markers smeared over
  ~20-40 px at 20-60 px/frame; several unrecognisable), whereas the global-shutter mono cams b/c show the same markers as
  crisp spheres at 20-28 px/frame.** The b/c exposure is much shorter than cam a's. Hand/finger occlusion is visible in
  ~3-5 of 32 tiles in each sheet. With GT shifted by -0.5 frame the b projections sit on the spheres; in cam a some fast
  ones are off by up to ~1 radius.
  -> For carried objects, the mono pair (b/c, r ~8 px for large markers) is the better marker sensor despite half the
  resolution; cam a is the better sensor for rest/held (2x resolution, rim edge 6x the texture baseline).
- Ep 11 multi-start (`reg17ms.py 11 3`, `out/reg_11.log`) also failed: best start kept only 5 residuals < 5 px, formal sd
  3-5 deg / 5-6 cm -> no usable ep-11 camera (beige cup not censused yet). Cause [H]: few GT-static marker views (cups
  static in 26 / 47 % of frames, 3-4 markers each, partly hidden) and an s24 init (iou 0.53) outside the grid basin.
- Detector pass 1 restarted at 00:55 after a profile showed full-frame `HoughCirclesAlt` dominating (9-10 s per cam-a
  image and per 2x-upsampled b/c image under the shared-host load of ~60-90): now Hough runs on the union of the
  (GT-projected, analysis-only) object ROIs, and full-frame only on every 4th sampled frame (`FF=4`, flag in column 9).
- Census ep 31 (`summ17.py 31`) [V, upper bound]: **mini_sweeper** rest (41 frames) >= 3 visible in cam a 1.00 (b 0.05,
  c 0.00, b or c 1.00); **held (112) cam a 0.33 / 2 markers 0.67, any cam 0.48; carried (137) cam a 0.01 / 2 markers
  0.99, any cam 0.06**. With its compact 3-marker triangle one marker is nearly always self-occluded (handle/body) while
  the sweeper is in use, so even a perfect detector sees only 2 markers. Rack (rest, 290) >= 3 in cam a 0.96 here (it
  is fully in view in ep 31). Large-marker radius in ep 31: cam a 14.8 px [12.6, 16.4], b/c 7.4 [6.3, 8.2].

### B5. Coarse census for eps without a marker registration (`mkcams_s24.py`, `CAMSRC=reg2s24 census17.py`) [E, weak]
Cameras = note 11 s24 frame-0 pose carried by the stereo VO (no marker registration; s24 is 5-15 deg / 5-15 cm off).
Validation on ep 31, where both exist: the rack agrees (>= 3 in cam a 0.97 vs 0.96) but the compact **sweeper flips**
(rest >= 3 in cam a 0.00 vs 1.00; held 0.00 vs 0.33): self-occlusion of a compact marker set depends on the view
direction at the 10-deg level, so these numbers are indicative only.
- beige_cup (ep 11; rest 51 / held 39 / carried 47 frames): >= 3 in cam a 0.82 / 1.00 / 0.74; any camera the same.
  (b vs c differ strongly, 0.5-0.8 vs 0-0.06, i.e. near the image border / camera error.)
- blue_cup in ep 11: >= 3 in ~0 % (2 visible in 95-100 %) [E: inconsistent with eps 12/21 where >= 3 is 78-98 %; likely
  camera error and/or the cup's pose in this task].
- wooden_piece_1 (ep 23): >= 3 in cam a 0.10 rest / 0.09 held / 0.41 carried; 0-1 visible in most rest/held frames
  (all 4 markers sit on its +x face, which usually faces away). wooden_piece_2 rest: >= 3 in any camera 0.56.

### B6. Automatic sphere detector prototype (design; results in B7-B10)
Design (`det17lib.py`, `det17run.py`, `det17score.py`, `det17eval.py`, `missed17.py`; Python env with scikit-learn:
`work/17/venv17`, created with uv, not the shared venv):
1. Candidates: `HoughCircles(HOUGH_GRADIENT_ALT, param1 40, param2 0.5)`, radius 5-40 px (cam a, full res) / 3-20 px
   (b, c, run on the 2x-upsampled image). No pose prior: inside the union of object ROIs on most sampled frames, on the
   full frame every 4th sampled frame (full-frame precision is measured only there).
2. Classifier: 12x12 normalised patch at 2 r half-size + disc/ring/outer means, contrasts, radius and (cam a) disc HSV
   statistics (155 features) -> HistGradientBoosting, one model for cam a and one for b/c, trained leave-one-episode-out
   on positives + 30 % of in-ROI and 3 % of other negatives (re-weighted by inverse sampling rate).
3. Detections = score >= thr, greedy NMS; matching rule = centre within max(0.5 r, 3 px a / 2 px b,c) and radius ratio
   0.6-1.6 of a z-visible projected marker (GT shifted -0.5 frame, cam a also -delta); candidates near a projected but not
   matched marker are ignored in precision.
Pass-1 sample: every 3rd frame (eps 12, 26, 21), every 4th (eps 0, 31). Candidate-stage recall (distinct z-visible markers
with a matching Hough circle; includes chance hits): ep 12 a 0.84 / b 0.83 / c 0.80 (~1.6 k candidates per image in the
ROI frames); ep 26 a 0.75 / b 0.62 / c 0.62.

### B7. Full-frame (prior-free) detector results, LOEO over eps 12/26/21/0/31 (`out/det_eval_v2_thr05.txt`) [V]
v1 features (12x12 patch + disc/ring stats) generalised poorly (held-out AP 0.18-0.68, train AP 0.99). v2 features
(`det17lib.features2`: patch + 9-radius radial profile mean/sd over 24 angles + rim radial-gradient strength/coherence/
tangential ratio at 0.85/1.0/1.15 r + 8-sector ring min/max (mount) + HSV disc stats; 188 dims; `featpass.py`,
`det17score2.py`) raise held-out AP to 0.49-0.86 (cam a) / 0.41-0.68 (b/c), AUC 0.94-0.996.
Recall of z-visible markers at thr 0.5 (large markers): **cam a rest 0.49, held 0.38, carried 0.17; cam b 0.41 / 0.31 /
0.14; cam c 0.40 / 0.29 / 0.14; small markers 0.00-0.10 everywhere.** Precision (detections near hidden/unmatched
projections ignored) 0.63-0.70 full-frame, 0.70 in object ROIs; 0.7-1.0 false detections per image (full frame),
0.7-0.8 in ROIs. At thr 0.9: precision 0.74-0.80, recall a rest 0.40 / carried 0.13.
Per frame, distinct markers DETECTED per object (thr 0.5, any of a/b/c), >= 3: **lid 0.54-0.77; blue cup 0.00-0.03;
pot 0.00-0.04; pitcher, rack, sweeper 0.00**; >= 2: cup 0.23-0.27, pot 0.11-0.51, rack 0.47 (rest). With this prototype,
markers would be a sparse cue, not a primary tracker, for everything except the lid.

Why it misses (visual cause labels on 48 missed z-visible markers, cam a rest, `out/missed_12_a_rest_0.jpg`,
`out/missed_26_a_rest_0.jpg`) [V, visual]: clearly visible sphere not detected ~26 (54 %); Hough circle fitted to the
sphere + black mount blob (centre offset / radius 1.5-2.5x) ~14 (29 %); arm/hand occlusion 4 (8 %, all ep-12 rack m3
under the arm); partly hidden behind the rack edge 4 (8 %). **So for resting objects the losses are mostly detector
immaturity (candidate geometry + a small, hand-crafted classifier trained on 4 episodes), not lack of image evidence.**
GT-video time offset (recall of moving-object markers vs GT shift, thr 0.5): b/c carried peaks at -0.50 frame (0.12 vs
0.09 at -0.25 / -0.75; n 820); cam a carried peaks at -0.25 frame in the b/c clock (0.18 vs 0.15 / 0.17; n 422), i.e.
**b/c frame t shows GT time t - 0.5 and cam a frame t shows GT time ~t - 0.25 - delta (~t - 1.35 for delta 1.1)** [E;
consistent with stage A's weak estimate -0.5 / -1.25..-1.5; resolution 0.25 frame, peaks are broad].

### B8. Visual visibility of markers in moving segments (cam b, random z-visible samples) [V, visual]
- Ep 21 cam b held/carried (`out/crops_21_b_moving_5.jpg`, 32 random z-visible markers: blue cup + pitcher): ~29-30 / 32
  show a recognisable sphere at or within ~0.5 r of the projection; 1 empty background (pitcher m0), 1 dark/unclear.
  Fingers touch the cup body above the markers; **hand occlusion of the cup's lower-side markers is rare (<= 1/32)**.
- Ep 0 cam b carried (B4 sheet): hand occlusion ~3-5 / 32; ep 12 cam a moving misses (`out/missed_12_a_moving_0.jpg`,
  24 detector misses): ~18 clearly visible spheres, 2-3 under the hand, 2 blurred beyond recognition, 1 Hough offset.
- Ep 31 sweeper (`out/crops_31_b_moving_5.jpg`): in most held/carried tiles the projection sits 1-2 r beside two visible
  spheres. At rest the same markers sit on the spheres (`out/ov_31_10_a_z.jpg`); while held (`out/ov_31_86_a.jpg`,
  t 86) the projections are about 1 r off. Cause not resolved [H]: residual GT-video time offset during fast rotation,
  sweeper body-frame or catalogue error (stage A did not verify the sweeper's markers against GT), or camera error.
  Sweeper detection numbers in moving segments are therefore unreliable (labels may be wrong). The sweeper's markers
  look dark violet in cam a, not grey.
- So the main unmodelled factor (hands) removes roughly 0-15 % of z-visible markers in these samples, not the majority.
  The z-buffer census (B2) is a fair, slightly optimistic ceiling for what a good detector could see.

### B9. Guided (tracking-mode) detection (`guided17.py <ep>`, `guided_summ.py`, `out/guided_summ_all.txt`) [V]
Per z-visible marker in the det sample (eps 12/26/21/0/31; 5797 marker-views): stage-A-style HoughCircles in a window
around a predicted centre (radius 0.7-1.4 r, crop = window + 2.5 r, b/c crops upsampled 2x), prediction = projection at the
best GT shift plus a random offset of 0.6 x window. Hit = nearest circle within max(0.5 r, 3/2 px) of the true centre.
Null = same search 3 r away (false-alarm rate 0-3 % with the 6 px window, 1-6 % with 15 px).

| large markers, window 6 px a-eq (offset 4 px) | rest | held | carried |
|---|---|---|---|
| cam a | 0.51 (oracle-centred 0.64) | 0.22 (0.29) | 0.11 (0.14) |
| cam b | 0.43 (0.52) | 0.25 (0.31) | 0.18 (0.18) |
| cam c | 0.42 (0.51) | 0.21 (0.29) | 0.15 (0.18) |
| window 15 px a-eq (offset 9 px): cam a / b / c | 0.67 / 0.59 / 0.58 | 0.42 / 0.44 / 0.37 | 0.23 / 0.27 / 0.25 |

Small markers: 0-9 % in every setting. Per frame, distinct markers hit per object (6 px window, any camera), >= 3 / >= 2:
blue cup rest 0.13 / 0.57, held 0.06 / 0.30, carried 0.07 / 0.34; pot rest 0.01 / 0.58, held 0.12 / 0.41, carried 0.03 /
0.25; pitcher 0 / 0.29-0.62; rack (rest) 0.10 / 0.64; lid rest 0.66 / 0.87, held 0.53 / 0.72, carried 0.31 / 0.62;
sweeper held/carried 0 / 0.
- Both detectors agree: off-the-shelf circle evidence is good for large markers at rest (50-70 % of views) and degrades
  2-4x once the object is in the hand. The guided search is no better than the learned full-frame classifier for moving
  objects (both ~0.15-0.30 per view). Hand occlusion (B8) explains only a small part of that gap. Blur (cam a), small
  apparent size (b/c, r ~8 px), oblique views of spheres on mounts, and Hough geometry explain the rest.

### B10. Guided + learned (best prototype; `guided_learned.py 15 <thr> 12 26 21 0 31`, `out/guided_learned.txt`) [V]
Among the pass-1 Hough candidates within 15 px (cam-a eq.) of a prediction (true + 9 px random offset), take the highest
LOEO v2 score; hit if score >= thr and it matches the true centre. Null false-pick rate 0-2 % (large markers).
- thr 0.05, large markers: cam a rest 0.62 / held 0.46 / carried 0.30; cam b 0.49 / 0.37 / 0.24; cam c 0.47 / 0.36 / 0.24.
  Small markers 0.01-0.13.
- Per frame, distinct markers found per object in any camera (>= 3 / >= 2; z-visible >= 3 in brackets): blue cup rest
  0.18 / 0.67 [0.78], held 0.12 / 0.41 [0.97], carried 0.14 / 0.52 [0.91]; pot rest 0.10 / 0.71 [0.99], held 0.12 / 0.65
  [0.94], carried 0.08 / 0.33 [0.94]; pitcher 0.00 / 0.38-0.67; rack (rest) 0.05 / 0.57; **lid rest 0.79 / 0.89, held
  0.79 / 0.84, carried 0.69 / 0.77**; sweeper held/carried 0 / 0 (labels doubtful, B8).
- At thr 0.3 the >= 3 fractions drop to 0.00-0.06 for cups/pot (lid 0.62-0.79).

### B11. More cam-a sync offsets and the coarse ep-18 census
- cam-a delta (frames, a exposed earlier than b/c frame t; `out/sync_<ep>.json`): ep 11 1.081 +- 0.032, ep 18 1.141 +-
  0.020, ep 23 1.087 +- 0.016, ep 31 0.99 +- 0.07 (4 frames only), plus stage A's 12 / 26 / 21 / 0 = 1.140 / 1.148 / 2.135 /
  1.102. **Integer part 1 in 7 of 8 eps, 2 in ep 21**; fractional part 0.08-0.15. The extrinsic rotation correction is
  the same in all 8 (about (-0.06..-0.09, +0.15..+0.19, -0.19..-0.22) deg; ep 31 outlier (-0.21, +0.14, -0.16) from 4
  frames) [V].
- Ep 18 coarse census (s24 + VO cameras, [E, weak]): **mini_dust_pan (5 small markers) >= 3 visible in any camera 1.00 rest
  / 1.00 held / 0.81 carried**; mini_sweeper 2 visible in 95-100 % of frames in every segment (never >= 3).

### B12. Stage B summary (2026-10-07). Inputs for stage C's primary-tracker vs cue decision
1. **Geometric ceiling [V, z-buffer upper bound, no hands]: markers are rarely the limit for cups, pot, lid and dust pan.**
   For held and carried frames, 3 or more markers face at least one head camera in 0.90-0.98 of frames for the blue cup,
   0.93-0.96 for the pot, 1.00 for the lid, 0.74-1.00 for the beige cup [E, coarse cameras] and 0.81-1.00 for the dust pan
   [E, coarse]. The exceptions are the pitcher (0.28-0.66; 2 markers face the user), the sweeper (0.06 carried, 0.48 held;
   its compact triangle shows 2) and the wooden pieces (all markers on one face, often 0-1 visible [E]). The rack shows 2
   in most frames. Hands remove roughly 0-15 % of these views in the visual samples (B8).
2. **Image quality [V]:** large markers have radius ~16 px in cam a and ~8 px in b/c; small markers ~8 px (a) and ~4 px
   (b/c). Their polarity varies (grey sphere on a black mount against white, blue, wood or floor), so the rim edge is
   the cue. Cam a smears carried markers over 20-40 px, while the global-shutter b/c stay sharp. So b/c are the
   carried-object sensor.
3. **Automatic detectors (no per-episode labels; LOEO over 5 public eps) [V]:**
   - Full-frame learned detector: precision ~0.65-0.80. Recall for large markers 0.4-0.5 at rest, 0.3-0.4 held, 0.14-0.17
     carried.
   - Guided + learned: 0.47-0.62 at rest, 0.36-0.46 held, 0.24-0.30 carried, with false-pick rates of 0-2 %.
   - Small markers: below 0.13 in every setting.
   - Per frame, 3 or more markers are found for the lid in 0.69-0.79 of frames, but only for 0.08-0.18 of cup and pot
     frames. Two or more are found in 0.33-0.71 of cup, pot and pitcher frames.
   - Visual labels of misses show that most are clearly visible spheres. The gap to the ceiling is mainly detector
     quality (Hough geometry on the sphere-plus-mount blob, a small hand-crafted classifier, 8 px spheres in b/c, cam-a
     blur), not missing evidence.
4. **Timing [E]:** b/c frame t shows GT row t - 0.5, and cam a frame t shows GT row ~t - 0.25 - delta, where delta is 1
   (7 of 8 eps) or 2 (ep 21) plus 0.08-0.15 frames. A tracker that reports video-frame poses at GT row t without this
   shift is ~25 ms late on b/c, which is 0.75-2.5 cm at carried speeds of 0.3-1 m/s. That error is comparable to the 1-9 cm
   ADD thresholds. This is a cheap fix, independent of markers [H: verify on full trajectories in stage C].
5. **Stage-B reading [E]:** with the current prototypes, markers are a strong intermittent cue but not a primary
   tracker, except for the lid. Useful uses: identity/spin and drift resets whenever 2+ markers are found (a third to
   two-thirds of frames for cups and pot), plus mm-level anchors at rest. Whether a better detector can lift the
   3-or-more fraction toward the 0.9 geometric ceiling for cups and pot is open [H]. A candidate is a small CNN on
   b/c (and cam a at rest), trained on these automatic public labels (~10 k positive views available).
   A falsification test: per-view recall of large markers in held/carried b/c frames on a held-out episode. Primary
   tracking needs roughly >= 0.8 per view to give 3 of 4 markers in most frames; < 0.6 would settle "cue only". Small-marker
   objects (dust pan) and the sweeper are unlikely to be marker-tracked.
6. Not done / limitations: no marker-registered cameras for eps 11, 23, 18 (s24 init failed even with multi-start), so
   the beige cup, wooden pieces and dust pan have only a coarse geometric census and no detector evaluation. The sweeper's
   in-hand projections are ~1 r off (cause unresolved). The census uses GT at row t (no time shift) and the detector labels
   use the -0.5 / -0.25-delta shifts. Detector frames are sampled every 3rd-4th frame. The machine was shared (load
   60-90) during these runs.
Key files (work/17): census17.py, seg17.py, summ17.py, contrast17.py, contrast_summ.py, crops17.py, det17lib.py,
det17run.py, featpass.py, det17score2.py, det17eval.py, missed17.py, guided17.py, guided_summ.py, guided_learned.py,
reg17ms.py, mkcams_s24.py, ov31.py; outputs out/census_<ep>.npz, out/census_reg2s24_<ep>.npz, out/contrast_<ep>.npz,
out/det_<ep>.npz, out/feat2_<ep>.npy, out/score_<ep>.npy (v2 LOEO), out/guided_<ep>.npz, out/det_eval_v2_thr05.txt,
out/guided_summ_all.txt, out/guided_learned.txt, out/reg2_31.json (new camera), out/reg2s24_{11,23,18,31}.json (coarse).
No background jobs left running.

## Stage C log (append-only)

- 2026-10-07 01:15 start (fresh: no stage-C notes or files existed). Plan: tracker `trk17.py` on public eps with
  stage-A/B inputs only where they are inference-legal: cameras = stereo VO of b/c (no GT) + measured cam-a delta and
  extrinsic rotation correction (video-only); detections = Hough candidates in windows around the tracker's OWN
  predicted marker positions, scored by the stage-B v2 classifier retrained leave-one-episode-out (target episode never in
  training); pose = robust multi-camera reprojection fit of the catalogue layout (cams a/b/c) with a constant-velocity
  prior; acquisition/re-acquisition by identity from inter-marker geometry (P3P hypotheses over detected triplets, verified
  in the other cameras). GT is read only by the evaluator (VO frame -> mocap via the stage-A registration Treg, applied
  after inference) and by the scorer-style frame-0 alignment.

### C1. Tracker prototype v1 (`c/trk17.py`, evaluator `c/ev17.py`, LOEO models `c/train_loeo.py` -> `c/clf_<ep>.pkl`)
Inference inputs: video a/b/c, stereo VO (`out/vo_public_<ep>.npy`), video-only cam-a sync (`out/sync_<ep>.json`), scan marker
catalogue, detector models trained on the other 4 public eps. World = VO frame (cam b at frame 0). Per frame (b/c clock;
cam a frame t + round(delta), with the residual exposure offset applied through the motion model):
1. predict each object's pose (constant velocity; hold after 6 coasting frames);
2. predicted visible markers = z-buffer of all tracked objects' scan surfaces under the predicted poses (hands not modelled);
3. HoughCircles (stage-B settings) in one crop per object and camera, kept if within the gate of a predicted marker and
   radius ratio 0.6-1.6; v2 features; LOEO score >= 0.05;
4. association: exclusive nearest-candidate (score-weighted) in gates shrinking 1.0 -> 0.5 -> 0.3 x window, robust (Cauchy)
   multi-camera reprojection fit of the 6-DoF pose with a pose prior (sigma 4 mm + 0.5 |v|, 1.5 deg + 0.5 |w|, growing
   while coasting); inliers < 4 sigma (6 px a, 3 px b/c);
5. status 3 = >= 3 distinct markers (full fix), 2 = 2 markers + prior, 1 = 1 marker (translation nudge, only right after
   a fix), 0 = coast. Window 8 px a-eq + speed terms + 12 px per coasting frame (cap 90).
Initial pose (the only GT access in the inference script, `init_pose`): GT frame-0 pose in the VO frame (through Treg)
perturbed by 20 mm and 5 deg in random directions, to emulate a coarse model-based initialiser; the tracker starts in
acquisition mode (wide gates). Evaluation (after inference): VO -> mocap by Treg (MODE=reg, VO drift included) or by
Treg D(t) (MODE=regD, stage-A drift-corrected, GT-informed, diagnosis only); GT at t - 0.5 (b/c clock, B7); errors =
origin translation, geodesic rotation, ADD over 3000 scan vertices; AUC of ADD as in the kit (1-9 cm, trapezoid).
- First test, ep 12 frames 0-40 [V]: rack full fixes (14 frames) 1.9-2.4 mm median / 6.4-6.6 mm p90 translation, 1.06 deg
  median rotation, ADD 2.3-2.7 mm median; 2-marker fixes 2.3-2.8 mm / 1.5 deg. Runtime ~1.0 s/frame for 2 objects x 3
  cameras (Python, 2 CV threads, host load ~6-10).
- **The blue cup in ep 12 never got a 3-marker fix in frames 0-40 because only 2 of its 4 markers (m0, m2) are
  geometrically visible from the head in that rest pose** (stage-B z-buffer census rows for t 0-36: cam a [1,0,1,0] or
  [1,0,0,0]). With a 3-marker acquisition rule the cup was never acquired (coast, error = the 20 mm / 5 deg init).
  So "3 markers at rest" is not guaranteed even for a 4-marker object: a resting cup typically shows the two
  head-facing markers, and 6-DoF then needs a second cue for the rotation about the m0-m2 axis (a model-based
  silhouette/edge term, a support-plane/upright prior, or the init). v1 run (`c/run1.sh`, eps 12 0 21 26) accepts 2
  markers in acquisition when they are seen in >= 3 views.
- v1 full runs (`c/trk_<ep>_v1.npz`, `c/ev_<ep>_v1.txt`) [V]: free-running v1 lost the blue cup (ep 12) and the pot (ep 0)
  within ~10-40 frames (2-marker / 1-marker updates with wrong associations, then velocity-driven spin; errors 100-200 mm,
  100-175 deg) and dragged the ep-12 rack 30 deg off through 1-marker nudges. The lid (ep 0) was tracked with 3+ markers in
  0.64 of frames (held 0.93) but with a **systematic 7-8 mm / 3-8 deg error even at rest**. Hence v2 (same file; v1 frozen
  as `c/trk17_v1_frozen.py`): hypothesis-and-verify association, velocity only from full fixes, no 1-marker updates,
  2-marker acquisition only with >= 4 views and a prior-consistent fit, obs logging; plus `PRIOR=gt` hybrid emulation.
- **Lid bias diagnosis (`c/dbg_obs.py`, `c/dbg_lid_offsets.jpg`, ep 0 t 5/20, stage-A cameras) [V, visual]:** lid markers k0, k1
  are detected within ~1 px of their GT projections, but large marker k2 is consistently ~4-7 px (cam a) / ~3 px (b) away
  (~1.5-2.7 mm), the small dark-texture marker k3 is detected on its black mount (centre bias toward the mount), and the
  texture-only k4's catalogue centre is ~3-4 mm from the visible small sphere (its +-3 mm estimate). Because these three
  markers sit close to the k0-k1 axis, mm-level layout/detection errors become a ~7 deg rotation about that axis and
  ~7 mm at the lid origin. So stage A's "scan markers = GT body markers to <= 0.6 mm" does not hold for every lid marker
  at this pose, and **small markers bias a marker fit**. Next: calibrate every marker's body-frame position from public
  rest-frame detections (training use of public GT), check consistency across episodes, and re-test.

### C2. Marker layout calibration from public rest frames (`c/calib17.py` detections -> `c/calib_obs_<ep>.npy`; `c/calfit.py` fit with a 1.5 mm prior toward the scan catalogue -> `c/calib_<ep>.json`) [V]
Guided detection (+-14 px a-eq around GT projections with the stage-A cameras, LOEO score >= 0.3) on rest frames (every
2nd), then each marker's body-frame position fitted to all its observations (GT pose + stage-A camera).
- An unregularised fit is ill-conditioned: the head cameras look along nearly parallel rays, so offsets along the view
  ray (up to 15-80 mm with few observations) barely change the reprojection error. With the prior:
- **Rack** (static, large): k1 offset (-1.3, +0.3, 0.0) mm in ep 12 vs (-1.1, -0.8, 0.0) in ep 26; k3 0.9 vs 0.5 mm ->
  consistent, about 1 mm. **Pot**: k0 (-2.2, +0.1, -1.5) mm in ep 0 vs (-8.4, -0.9, -1.5) in ep 26; k2 6.3 vs 1.2 mm ->
  NOT consistent across episodes. **Blue cup** (ep 12, only 8-12 rest observations per marker): 0.5-3.5 mm. **Lid** (ep 0 only,
  no cross-episode test): 1.9-6.4 mm, mean 2-D offsets 1-5 px a-eq for the detected large/dark-small markers and 11 px for
  the texture-only k4.
- Reading [E]: scan-vs-image marker discrepancies of ~1-3 mm (large markers) and 3-6 mm (small markers) exist and are
  partly pose/episode dependent (camera depth error, detection bias toward the mount, GT timing), so a public
  calibration does not reliably remove them. They are irrelevant for ADD-AUC at the 1-9 cm thresholds when the layout is
  wide, but on compact layouts (lid: three markers near one axis) they become several degrees.

### C3. E1: free-running marker-only tracker v2, coarse init (20 mm / 5 deg), scan catalogue [V]
- Ep 12 (`c/ev_12_v2.txt`): **blue cup never acquired** (1 marker found in 0.91 of frames, 0 full or 2-marker fixes); its
  pose stays at the init while the cup is carried and rotated ~180 deg into the rack -> ADD 180-205 mm, AUC 0.18.
  Rack: 2-marker fixes in 0.65 of rest frames (7.4 mm / 4.5 deg median, p90 21 mm), full fixes 0.03; AUC 0.96 (static
  object). Scorer-style (slot 0 = blue cup at frame 0): 0.21 / 0.70.
- Runtime v2: 1.3 s/frame at host load ~6 rising to 3.4 s/frame at load ~23 (Python hypothesis scoring; 2 objects x 3 cams).
- Ep 0 (`c/ev_0_v2.txt`): **lid: full (>= 3 marker) fixes in 0.98-1.00 of rest, held and carried frames; error vs GT
  ADD median 8.5-10.7 mm (p90 13-14 mm), translation 6.8-9.2 mm, rotation 3.7-7.4 deg; AUC 0.977 for this
  trajectory.** The lid is marker-trackable as a primary tracker; its error is the ~7 deg layout/detection bias of C1/C2,
  not loss of track. **Pot**: no full fixes (its 4 large markers show 2 at a time; small ones not found), 2-marker fixes
  0.54 rest / 0.48 held / 0.05 carried (ADD 8-13 mm when fixed); while carried it is lost (ADD 80 mm median) -> AUC 0.74.
  Scorer-style (slot 0 = pot, whose frame-0 pose is the 20 mm / 5 deg init): pot 0.66, lid 0.87.

### C4. Prior-free acquisition by marker identity (`c/acq17.py`) [V]
No pose prior and no ROI: stage-B FULL-FRAME candidates only (frames with the full-frame flag; every 12th-16th frame) with
LOEO scores >= 0.5 (0.2 gives the same), NMS, b/c epipolar matching (< 2 px) and triangulation (depth 0.2-1.5 m), then every
triple of 3-D points whose three distances match a catalogue marker triple within 4 mm -> Kabsch pose (rms < 3 mm), ranked
by support (other markers within 6 mm in 3-D, cam-a detections within 6 px).
- Per frame only 1-5 triangulated points exist (a marker must be detected in BOTH b and c).
- **Lid (ep 0): acquired in 4/24 frames, 3 correct (4.5 mm, 9.3 deg median) and 1 wrong (177 deg flip from a near-symmetric
  triple that included both small markers). Pot, blue cup (eps 12/21), rack (12/26), pitcher (21): 0 acquisitions.**
- So identity from inter-marker distances works in principle, but single-frame prior-free acquisition is rare and can flip
  on compact/small-marker triples; acquisition and re-acquisition must come from a model-based estimate (or from pooling
  a static object over many frames [H, not tested]).
- Ep 21 E1 (`c/ev_21_v2.txt`) [V]: **blue cup**: full fixes 0.04, 2-marker fixes 0.47 (rest 0.77 but biased: 27 mm / 12.6 deg
  median, i.e. 2-marker fixes inherit and lock in a wrong rotation about the marker axis; held 0.58 with 6.7 mm / 5.4 deg;
  carried 0.17) -> lost while carried (ADD 85 mm median), AUC 0.60. **Pitcher**: 2 markers face the user; fixes 0.10, lost
  from the first carry (ADD 115-180 mm), AUC 0.23.
- Ep 26 E1 (`c/ev_26_v2.txt`) [V]: rack (static) 2-marker fixes 0.57, ADD 5.8 mm median, AUC 0.985; **pot: fixes only in the
  first rest period (15 mm, 2 markers), lost when grasped; carried into the rack with a ~170 deg turn -> ADD 200-240 mm,
  AUC 0.33**.
- **E1 summary [V, 4 public eps, coarse init, real detections]: as a primary (stand-alone) tracker, markers work only
  for the lid** (full fixes in 0.98-1.00 of rest/held/carried frames, ADD ~9 mm, AUC 0.98). Blue cup, pot and pitcher are
  lost at the first grasp or carry in all four episodes (AUC 0.18-0.74 for the trajectory, i.e. near "object left behind"),
  because full fixes are 0-4 % of frames and 2-marker fixes leave one rotation free and lock in biased poses (cup ep 21 rest:
  27 mm / 12.6 deg). Static racks are fine but do not need a tracker. Runtime 0.4-0.6 s/frame (load ~6-10), 3.4 s at load 23.

### C5. E2: hybrid emulation - markers correcting a model-based prior (`PRIOR=gt`, `c/ev_<ep>_h10.txt`, `c/ev_carry.py`) [V, emulated prior]
The per-frame prior is GT(t - 0.5) in the VO frame with an AR(1) pose error (sd 10 mm and 5 deg per axis, rho 0.95 per frame,
i.e. ~1 s correlation; "h20" = 20 mm / 10 deg), standing in for a model-based tracker's output (analysis only; no claim
that a real model-based tracker has this error structure). Markers are searched in 3-sigma windows of that prior,
hypothesis-and-verify + robust fit as in E1. Outputs: prior-only, fused (marker fix where >= 2 markers, else prior) and
carry (the marker correction prior^-1 * fix interpolated between fix frames and applied to the prior everywhere).
Note: run2 kept E1's acceptance rule (2-marker fixes need >= 4 views after 6 frames without a fix), which is conservative
in this mode; `GTFRESH=1` (used in E3) drops it.
- Ep 12, h10: **blue cup fixes (>= 2 markers) in 0.22 rest / 0.76 held / 0.53 carried frames (>= 3: 0.01 / 0.45 / 0.19)**;
  on fix frames ADD drops from 16-18 mm (prior) to 6.5-8.6 mm (fused), fused worse than prior in 4-15 % of fix frames.
  Trajectory AUC: **cup prior 0.885 -> fused 0.911 -> carry 0.940; rack 0.809 -> 0.852 -> 0.902**. Scorer-style mean (slot 0 =
  cup): 0.756 -> 0.846 (fused).
- With a decent prior the cup is found while carried in about half of the frames, versus ~0 when the tracker relies on
  its own markers (E1): the marker evidence is there, the stand-alone tracker cannot keep the association alive.
- Ep 12, h20 (20 mm / 10 deg prior): cup fixes 0.08 rest / 0.33 held / 0.38 carried; AUC prior 0.647 -> fused 0.693 -> carry
  0.759; rack 0.498 -> 0.538 -> 0.631. The fix rate falls as the prior worsens (wider windows, more ambiguity).
- The scorer-style numbers swing with the single slot-0 frame-0 pose (e.g. h20 fused 0.15 vs prior 0.38 because the
  frame-0 fused pose differed); they measure the anchor, not tracking, so the registered AUCs above are the tracking
  measure.

### C6. E3: spin recovery (`PRIOR=gt PN=5,3,0.95 SPIN=<deg> SPINHYP=1 GTFRESH=1`, `c/ev_<ep>_s<deg>.txt`) [V, emulated prior]
Prior = GT + small AR(1) noise (5 mm, 3 deg) + a CONSTANT spin error about the scan symmetry axis (cups/pot: body z,
lid: body x; scan PCA), i.e. what a model-based tracker cannot observe on a rotationally symmetric object. The tracker
scores 24 spin hypotheses (15 deg grid) by matched candidates (visibility recomputed per hypothesis; candidates
collected around the markers of every 30-deg hypothesis), then fits from the best one.
- Ep 21, blue cup, spin error 90 deg: **fixes (>= 2 markers) in 0.84 rest / 0.40 held / 0.20 carried frames; on 86 of 89 fix
  frames the chosen spin is the correct 270 +- 15 deg (3 frames picked 75 deg, wrong)**. Fix-frame ADD 10-12 mm vs 56 mm
  for the prior; 3-marker fixes 2 deg rotation error, 2-marker fixes 13-14 deg (rotation about the marker axis left to the
  prior). **Trajectory AUC: prior 0.438 -> fused 0.677 -> carry 0.938** (a constant spin error is fixed everywhere by any
  correct fix). Pitcher (no spin error, 5 mm / 3 deg prior): 2-marker fixes 0.85-1.00, AUC 0.950 -> 0.966 (fused) -> 0.970
  (carry).
- E2 ep 0, h10 (`c/ev_0_h10.txt`): **pot fixes 0.71 rest / 0.94 held / 0.70 carried** (mostly 2-marker; carried fix ADD 16.5 mm
  vs prior 21 mm, fused worse than prior on 20-30 % of fix frames); AUC 0.864 -> 0.895 (fused) -> 0.914 (carry). **Lid: fixes
  1.00 everywhere, AUC 0.896 -> 0.983**. Scorer-style mean 0.917.

## Stage B resume (2026-10-07 07:25, "try again" run; appended after the stage-C log, which is untouched)
- Read state: stage B was complete in B1-B12 (summary B12); a stage-C session ran 01:15-02:10 and was cut off (C1-C6;
  no jobs running, last file `c/run2.done` 02:10). This run adds stage-B items only, closing the B12.6 gaps that matter:
  all 20 public eps now have a/b/c clips (downloader DONE), so eps **13 (blue_cup + rack) and 22 (blue_cup + pitcher)**,
  never used in stage B and with note-11 s25 frame-0 inits, serve as a **fresh holdout** for the census and for the
  detector (models trained on all 5 stage-B eps; no retuning on 13/22).
- Eval object frequency (kit `track_3_evaluation_objects.json`): wooden_spoon 10 eps (no public GT or scan -> no GT
  census possible), white_pot 6, blue_cup 5, plastic_dish_rack 5, beige_cup 2, mini_sweeper 2, mini_dust_pan 2,
  water_pitcher 1, wooden pieces 1, lid 1.
- Running: `chain5.sh 13 22` (nohup, PID 95298; vo17 -> a_pnp -> sync_fit -> reg17 (s25 init) -> reg2 (no LOMO) ->
  census17; logs `out/{vo,apnp,sync,reg,reg2,census}_<ep>.log`, progress `out/chain5.progress`).

### B13. Per-object GT-video time offset (`shift_obj.py 31 12 21 0 26`, THR 0.3, no NMS) [V]
Hit rate of z-visible MOVING-object marker views vs absolute GT shift (b/c clock; cam a also -delta), per object:
- Carried, b/c peaks: blue cup ep 21 -0.25 (0.19; flat -0.75..0), ep 12 flat -1.0..-0.25 (0.06); pitcher -0.75 (0.24);
  pot ep 0 -0.75 (0.13), ep 26 -0.5/-0.25 (0.29); lid -0.5 (0.35). Cam a peaks: blue cup 0.0 / +0.25, pitcher -0.5, pot
  -0.25 / 0.0, lid -0.25. Held segments are flat (slow motion). So the B7 pooled estimate (b/c -0.5, cam a ~-0.25 after
  delta) holds per object to +-0.25-0.5 frame [V]; no object needs a different shift, except:
- **mini_sweeper (ep 31): 0.00-0.01 hits at every shift in -1.25..-0.25 for both a and b/c, and no shift in -10..+10 frames
  rescues it (max 0.06)** -> its in-hand miss (B8) is NOT a time offset.

### B14. The sweeper's GT and the rack's GT are mutually inconsistent in ep 31 (`bodyx_test.py`, `bodyx_blocks.py`, `out/ovx_31_mini_sweeper.jpg`) [V for ep 31]
- A constant body-frame correction X of the sweeper's markers (fitted on in-hand views to the nearest scored candidate,
  gates 3 -> 1 r) raises the in-hand hit rate from 0.00 to 0.46 (n 392) but drops rest-1 (t 0-22) from 0.23 to 0.00.
  X ~ 4.5 deg about body -y plus (-4, -1, +10) mm; its rotation and z part are poorly conditioned (the 3 markers lie in
  the body xy plane at z 2-3 mm, 32-46 mm apart), so only the image-plane shift (~15-20 px cam a, ~1 marker radius,
  ~5-7 mm lateral) is reliable.
- Per block (hit rate X = 0 / X(all) | rack with X-independent camera): t 0-22 rest 0.42 / 0.00 | **rack 0.02**;
  23-77 0.00 / 0.24 | 0.52; 78-133 0.00 / 0.88 | 0.34; 134-179 0.00 / 0.72 | 0.35; 180-247 0.00 / 0.20 | 0.54;
  248-265 rest-2 0.00 / 0.00 | 0.56 (thumb on the sweeper); 266-289 0.02 / 0.31 | 0.63.
- Visual (t 10/100/160/255, cams a and b): in hand the corrected markers sit on the dark spheres and the GT-posed ones
  are ~1 r off in a constant image direction; at t 10 the GT-posed ones fit.
- Reading [E]: no single camera fits both objects' GT. The stage-A registration of ep 31 used the resting sweeper as an
  anchor, so in t 0-22 the camera bent toward the sweeper (rack misses there) and elsewhere the rack dominates (sweeper
  misses). Its sweeper anchor residuals were already high (3.9 px median vs 2.5 overall, `out/reg2_31.log`). The
  likely cause is a ~5-10 mm, constant body-frame offset between the sweeper's scan markers and its mocap (GT) body
  markers, i.e. the stage-A "scan markers = GT body markers to <= 0.6 mm" does not hold for the sweeper. A GT error that
  appears only in hand cannot be excluded yet. Test running: `EXCL=mini_sweeper SUF=xsw reg2x.py 31 15 0` (rack-only
  anchors, `out/reg2xsw_31.{json,log}`); then one X for ALL sweeper frames incl. rest.
- Jobs (07:30, host load ~22 on 14 cores from other work): `chain5.sh 13 22` (PID 95298, cameras + census);
  `chain6.sh` (PID 99976; waits for census_13/22, then `det17run.py <ep> 3`, `featpass.py`, `det17score_hold.py "12 26 21 0
  31" 13 22` (venv17), `det17eval.py 13 22` -> `out/det_eval_hold_thr05.txt`, `guided_learned.py 15 0.05 13 22` ->
  `out/guided_learned_hold.txt`, `shift_obj.py 13 22` -> `out/shift_obj_hold.txt`; progress `out/chain6.progress`);
  `chain7.sh 41` (PID 631; pot-only ep 41 with the s24 init after chain5; progress `out/chain7.progress`);
  `reg2x.py 31` rack-only (PID 99432). Ep 13 reg17 converged (res 2.2 px median; delta 1.128; extrinsic rotation
  correction (-0.07, +0.17, -0.22) deg, same as the other 8 eps) [V].

### B15. Fresh-holdout census, ep 13 (blue_cup + rack; `chain5.sh`, `summ17.py 13`) [V camera in-sample, upper bound]
- Camera: reg17 from s25 converged; reg2 (no LOMO) in-sample 1.73 px median / 3.68 p90 (316 obs: a 263, b 29, c 24), drift
  knots max 0.06 deg / 3.3 mm -> as good as eps 12/26.
- Census (>= 3 / 2 visible; same definitions as B2): **blue_cup rest (48 frames) cam a 0.38 / 0.62, any camera 0.38;
  held (66) a 0.59 / 0.41, b|c 0.56, any 0.61; carried (76) a 0.68, b 0.74, c 0.61, b|c 0.75, any 0.76.** Rack rest (190):
  cam a 0.35 / 0.59, b|c 0.00 / 0.89.
- The blue cup's geometric ceiling for >= 3 markers is task/pose dependent: eps 12+21 gave held 0.98 / carried 0.90,
  ep 13 gives 0.61 / 0.76 (and ep 12 alone rest 0.59). Even with a perfect detector, a cup tracker would need a second
  cue in ~25-40 % of in-hand frames in this episode.
- Radii: large cam a 16.3 px [13.3, 22.4], b/c 8.1 [6.7-6.8, 11.3] (same as B2).

### B16. Sweeper test with rack-only cameras (`EXCL=mini_sweeper SUF=xsw reg2x.py 31 15 0` -> `out/reg2xsw_31.json`; `CAM=reg2xsw [ALLX=1] bodyx_blocks.py`; `out/ov_31_rackcheck.jpg`) [V for ep 31]
- Rack-only registration (sweeper removed from the anchors): 414 obs, 2.32 px median / 5.14 p90, drift knots max 0.14 deg /
  4.3 mm. Full-frame overlay at t 10/20/60 (cams a, b): rack markers sit on the rack edge, so this camera is sound in
  t 0-22 as well. The rack's low hit rate there (0.02) is a detector shortfall, not a camera error.
- With this sweeper-independent camera the pattern is unchanged: **rest-1 (t 0-22) GT-posed sweeper markers hit 0.40
  uncorrected; every in-hand block 0.00-0.02 uncorrected and 0.21-0.88 with one near-constant correction (~5 deg about
  body -y, (-4, -1, +9) mm; image shift ~1 marker radius). A single correction fitted on ALL views still fails rest-1
  (0.07).** A world-axes correction fits the in-hand blocks equally well (0.83 / 0.71), so the two parametrisations cannot
  be separated here (the in-hand orientation varies too little).
- Conclusion [V for ep 31]: the sweeper's GT agrees with its visible markers at the initial rest, but in the hand it is
  offset from them by ~5-10 mm (about one marker radius in the image). The offset is near-constant across in-hand blocks.
  A fixed scan-catalogue error cannot do this, because it would also show at rest-1. A time offset cannot either:
  -10..+10 frames gives no hits (B13).
- Cause [H]: the mocap rigid-body solution of a compact 3-marker body (32-46 mm) changes when the hand occludes or
  relabels markers in the external mocap cameras. Not tested on ep 18 (coarse cameras only).
- Implications: (a) the sweeper's in-hand GT carries a ~0.5-1 cm error relative to the physical object (at least in ep
  31). Any tracker, marker-based or not, has that floor against GT. That is small against the 1-9 cm ADD band but not
  zero. (b) The B7-B10 detector numbers for the sweeper's moving segments were scored against offset labels, so they
  understate the evidence. With the correction applied, a real sphere is found near 0.46 of in-hand views (THR 0.3).
  Even so, only 2 markers face the camera in 94-99 % of carried frames (B2), so the sweeper stays a cue, not a
  marker-tracked object. (c) Stage A's "scan markers = GT body markers to <= 0.6 mm" holds at rest. For the sweeper it
  does not hold in hand; other objects' in-hand GT was not tested this way (B13's per-object shift peaks are clean, so
  any such offset there is well below one marker radius).
- Ep 22 (blue_cup + pitcher) cameras, caution [E]: reg17 from s25 ended at 3.74 px median with 0.56 inliers < 4 px (ep 13:
  2.23 px, 0.85), formal sd 6.7 / 7.5 / 1.8 mm, 5.4 deg / 54 mm from s25. Static anchors are few: cup static 29 %, pitcher
  36 % with 2 head-facing markers. Cam-a sync: delta 1.597 +- 0.061 frames (fractional part 0.6, vs 0.08-0.15 in the other 8 eps;
  per-frame residual sd 0.13 deg / 3.5-3.9 mm, 3-4x the others). Rotation correction (-0.07, +0.16, -0.20) deg, same
  as the other eps. Ep 22 is used only if reg2 reaches the eps-12/13/26 level (<= 2.5 px median).

### B17. Fresh-holdout detector, ep 13 (models trained on eps 12/26/21/0/31, no retuning; `det17run.py 13 3`, `featpass.py 13`, `det17score_hold.py "12 26 21 0 31" 13`, `det17eval.py 13` -> `out/det_eval_hold13_thr05.txt`) [V]
- Classifier on the held-out sampled rows: cam a AUC 0.987 / AP 0.856; b/c AUC 0.958 / AP 0.679 (LOEO range was a 0.49-0.86,
  b/c 0.41-0.68 AP).
- Recall of z-visible LARGE markers at thr 0.5 (rest / held / carried): **cam a 0.59 / 0.32 / 0.31; cam b 0.55 / 0.06 /
  0.38; cam c 0.45 / 0.17 / 0.32** (n 53-186 per cell; the cup and rack have no small markers). LOEO (B7): a 0.49 / 0.38 / 0.17, b
  0.41 / 0.31 / 0.14. The holdout is in the same band, better for carried and worse for held b/c. Precision at thr 0.5:
  full frame 0.81-0.84 (0.3-0.4 false detections per image), object ROIs 0.92-1.00 (0.0-0.2 per image). This is higher
  than LOEO (0.63-0.70), plausibly because ep 13's scene (cup + rack) resembles training ep 12 [E].
- Per frame, distinct blue-cup markers DETECTED in any camera (>= 3 / exactly 2): rest 0.00 / 0.12, held 0.00 / 0.17,
  carried 0.00 / 0.68 (z-visible >= 3: 0.38 / 0.61 / 0.72). Rack rest 0.03 / 0.53. As in B7, the full-frame detector
  never yields 3 markers on the cup. With 2 markers it does so in two-thirds of the carried frames of this episode.
- GT-video offset on the holdout (moving objects): **b/c carried peaks at -0.50 frame (0.35 vs 0.26 / 0.30 at -0.75 / -0.25);
  cam a carried at 0.00 / -0.25 (0.36 / 0.34)** -> B7's timing (b/c t - 0.5; cam a ~t - 0.25 - delta) holds on an unseen
  episode [V].

### B18. Fresh-holdout census, ep 22 (blue_cup + pitcher; `summ17.py 22`) [V camera in-sample for b/c; cam a weaker]
- Camera: reg2 (no LOMO) 2.49 px median / 5.00 p90 on 290 obs (a 186, b 54, c 50); per camera: b 1.3-2.0 px, c 1.7-2.8 px,
  a 2.4-3.0 px; drift knots max 0.11 deg / 7.7 mm. Meets the <= 2.5 px bar; cam a is the weak part, matching its odd
  sync (delta 1.60).
- Census (>= 3 / 2 visible): **blue_cup rest (75) / held (70) / carried (44): >= 3 in 1.00 / 1.00 / 1.00 (any camera; cam c
  0.77-0.97)**. Water_pitcher rest (102): 2 markers in 1.00 of frames; held (21): >= 3 in 0.05; carried (66): cam a 0.64, b|c 0.42,
  any 0.68 (ep 21: 0 / 0.28 / 0.66).
- Across the 4 cup episodes (12, 13, 21, 22), the >= 3 ceiling in hand ranges from 0.61 (ep 13 held) to 1.00 (ep 22), so it is
  episode (grasp/pose) dependent. The pitcher's "2 markers face the user" pattern repeats exactly in ep 22.
- Ep 41 (pot only, 299 frames; pot static 18 %): reg17 from s24 crashed with 0 observations (`out/reg_41_s24fail.log`). The
  a-vs-b PnP matched only 1 frame (`out/apnp_41.log`), so there is no sync estimate (`out/sync_41_1frame.json`). I
  replaced it with a cross-episode prior: delta = median 1.128 and rotation correction = mean (-0.073, +0.174, -0.208)
  deg over eps 12/26/0/11/18/23/13 (sd 0.024 frame, <= 0.01 deg). No translation correction. This uses video-only sync
  fits of other eps and no ep-41 GT. The integer part (1 vs 2) is a risk (ep 21 was 2). Running `chain8.sh` (reg17ms
  multi-start -> reg2 -> census; `out/chain8.progress`).

### B19. Fresh-holdout detector, eps 13 + 22 pooled (`det17score_hold.py`, `out/score_hold.log`, `out/det_eval_hold_thr05.txt`, `out/det_eval_hold22_thr05.txt`, `out/guided_learned_hold.txt`, `out/shift_obj_hold.txt`) [V]
Models trained once on eps 12/26/21/0/31 (cam a 73,950 sampled rows, 2,435 positive; b/c 107,235, 4,166 positive) and applied
unchanged. Held-out sampled AUC / AP: ep 13 a 0.987 / 0.856, b/c 0.958 / 0.679; ep 22 a 0.994 / 0.848, b/c 0.987 / 0.769.
- **Full-frame (prior-free) detector, thr 0.5, large markers, recall rest / held / carried: cam a 0.62 / 0.44 / 0.27; cam b
  0.55 / 0.32 / 0.38; cam c 0.43 / 0.26 / 0.32** (n 139-326 per cell). Precision: full frame a 0.74 / b 0.81 / c 0.78
  (0.4-0.8 false detections per image); object ROIs 0.83 / 0.94 / 0.93 (0.1-0.5 per image). Holdout recall is at or a
  little above the LOEO band (B7); precision is higher.
- **Guided + learned (15 px a-eq window, thr 0.05): cam a 0.71 / 0.53 / 0.40; cam b 0.67 / 0.45 / 0.43; cam c 0.52 / 0.37 /
  0.41**, null false-pick rate 0.00-0.01 (LOEO B10: a 0.62 / 0.46 / 0.30, b 0.49 / 0.37 / 0.24).
- Per frame, blue-cup markers found in any camera (>= 3 / >= 2): full-frame rest 0.53 / 0.60, held 0.23 / 0.49, carried 0.07 /
  0.67; guided rest 0.57 / 0.90, held 0.32 / 0.62, carried 0.15 / 0.72 (z-visible >= 3: 0.75 / 0.81 / 0.82). **Ep 22 alone
  (all 4 cup markers geometrically visible in every frame): full-frame >= 3 in 0.88 rest, 0.46 held, 0.20 carried.** Pitcher
  >= 3: 0.00 everywhere; >= 2 (guided) 0.68-0.82.
- **B12's falsification test, answered:** per-view recall of large markers in held/carried b/c frames on unseen episodes is
  0.26-0.38 (full frame) and 0.37-0.45 (guided), against the >= 0.8 needed for 3-of-4 in most frames and the < 0.6 line
  set in B12 for "cue only". **With this detector family (Hough candidates + boosted classifier on hand-crafted features)
  markers are a cue, not the primary tracker, for cups, pot and pitcher.** A stronger learned detector (e.g. a CNN on b/c
  crops trained on these automatic labels) remains untested [H]. Its upside is capped by the per-episode geometric
  ceiling (B18: 0.61-1.00 in hand for the cup).
- Timing on the holdouts, per object (shift with max hits, b/c clock): carried b/c -0.50 (ep 13 cup), -0.25 (ep 22 cup),
  -0.50 (ep 22 pitcher); cam a (after -delta) -0.50 / +0.25 / 0.00. This agrees with B7 (b/c t - 0.5, cam a ~t - 0.25 -
  delta) to +-0.25-0.5 frame. Ep 22's later cam-a peak fits its unusual delta of 1.60.
- Check that the sweeper is the exception (large markers, THR 0.3, GT at the B7 shifts, hit rate in hand vs at rest; inline
  script, eps 12/13/21/22/26/0/31) [V]: blue cup 0.16 vs 0.13 (ep 12), 0.35 vs 0.34 (13), 0.24 vs 0.27 (21), 0.51 vs 0.65 (22);
  pitcher 0.26 vs 0.43 (21), 0.55 vs 0.60 (22); pot 0.48 vs 0.52 (26), 0.21 vs 0.62 (0, carried cam-a blur, B4); lid 0.69 vs
  0.82; rack (nudged) 0.52 vs 0.67, 0.49 vs 0.48; **sweeper 0.00 vs 0.23**. Only the sweeper's in-hand evidence collapses,
  so no other object shows an in-hand GT offset of the sweeper's size (~1 marker radius).

### B20. Stage B resume summary (2026-10-07 07:45; supersedes B12 where they differ)
1. **Geometric ceiling [V, z-buffer, no hands; 7 marker-registered eps 12/13/21/22/26/0/31]:** fraction of frames with
   >= 3 markers facing at least one head camera, rest / held / carried: blue_cup 0.77 / 0.88 / 0.88 (per episode in hand 0.61
   (ep 13) to 1.00 (ep 22)); white_pot 0.98 / 0.93 / 0.96; white_pot_lid 1.00 / 1.00 / 1.00; water_pitcher 0.00 / 0.20 / 0.67
   (2 markers face the user at rest in both eps); mini_sweeper 1.00 / 0.48 / 0.06; plastic_dish_rack 0.50 at rest. With
   b/c only, the cup is 0.77 / 0.87 / 0.87. Beige cup, wooden pieces and dust pan stay at the coarse [E] level (B5/B11).
   Large-marker radius: cam a 16.7 px [13.4, 21.5], b/c 8.3-8.4 [6.7, 10.8]; small markers a 8.4, b/c 4.1-4.2 px.
   Image speed carried: a 17 px/frame median (p90 45), b/c 7.7 (p90 22).
2. **Detector on two unseen episodes [V]:** full-frame recall (large markers, thr 0.5) a 0.62 / 0.44 / 0.27, b 0.55 /
   0.32 / 0.38, c 0.43 / 0.26 / 0.32. Precision is 0.74-0.81 on the full frame and 0.83-0.94 in object ROIs. Guided +
   learned reaches a 0.71 / 0.53 / 0.40, b 0.67 / 0.45 / 0.43, with ~0 false picks. Small markers stay < 0.13 (B7).
   Per frame, 3 or more cup markers are found in 0.07-0.53 (full frame) or 0.15-0.57 (guided) of frames, highest at rest.
   **B12's falsification test fails for "primary" (held/carried b/c per view 0.26-0.45 < 0.6): markers are a cue, not the
   primary tracker, for cups, pot and pitcher. The lid (5 markers, 3 large, all facing up) is the exception (B10, C3).**
3. **Timing [V on 2 unseen eps]:** b/c frame t shows GT row t - 0.5; cam a frame t shows GT row ~t - 0.25 - delta (+-0.25-0.5
   per object). Cam-a delta was measured in 10 eps: 1.08-1.15 in 7, 0.99 in ep 31 (4 frames only), 2.14 in ep 21 and 1.60
   in ep 22. Ep 41 failed (1 PnP frame), so a per-episode estimate can fail and needs a fallback.
4. **GT quality, sweeper [V ep 31, cause H]:** the sweeper's GT is offset from its visible markers by ~5-10 mm (one marker
   radius) whenever it is in the hand. It agrees at the initial rest. Rack-only cameras give the same result, and no time
   shift explains it. No other public object shows this. Earlier sweeper detector numbers (B7-B10) were scored against
   these offset labels.
5. For stage C (already run 01:15-02:10, C1-C6; not changed here): the stage-B inputs are unchanged in direction and
   stronger in evidence. A stand-alone marker tracker is viable only for the lid. For cups/pot/pitcher markers should
   correct a model-based prior (spin/identity, drift resets at 2+ markers, mm anchors at rest). The sweeper and dust pan
   are not marker-trackable (2 visible / small markers). The spoon (10 eval eps, 3 large markers, no public GT) has no
   census.
Files (work/17): `chain5.sh`, `chain6.sh`, `chain7.sh`, `chain8.sh`, `det17score_hold.py`, `shift_obj.py`, `bodyx_test.py`,
`bodyx_blocks.py`, `ov_bodyx.py`, `reg2x.py`; outputs `out/reg2_{13,22}.json`, `out/census_{13,22}.npz`, `out/det_{13,22}.npz`,
`out/feat2_{13,22}.npy`, `out/score_{13,22}.npy` (trained on the 5 stage-B eps), `out/det_eval_hold*_thr05.txt`,
`out/guided_learned_hold.txt`, `out/shift_obj_hold.txt`, `out/reg2xsw_31.json`, `out/bodyx_31_mini_sweeper.json`,
`out/ovx_31_mini_sweeper.jpg`, `out/ov_31_rackcheck.jpg`, `out/sync_41.json` (cross-episode prior; original
`out/sync_41_1frame.json`).
- Ep 41 result (07:44) [V failure]: reg17ms multi-start from s24 with the prior sync failed. The best start had 1
  observation < 5 px (`out/reg_41.log`, `out/chain8.progress`; no reg2/census). This is the same failure as eps 11/23: a
  coarse s24 init plus few static anchors (pot static 18 %) is outside the grid basin. The pot census stays on eps 0/26
  [V]. The camera for unregistered eps would need another init, e.g. a registration from pooled triangulated b/c
  detections against GT markers of moving objects [H, not built].
- End of the stage-B resume run (07:45). No background jobs left running. Stage-C files (`c/`) untouched.

## Stage C resume (2026-10-07 07:50, "try again" run; appended after B20)
- Read state: C1-C6 complete from the 01:15-02:10 session; all its runs finished (`c/run2.done`, `c/run3.done`). Several
  finished outputs were never written up (E2 h10/h20 for eps 21/26/0, E3 s90/s180 for ep 12 and s180 for ep 21). The "carry"
  AUCs quoted in C5/C6 came from an unsaved inline script (`c/ev_carry.py` does not exist); they are recomputed below with a
  saved script.
- This run: (1) C7 write-up of all finished stage-C runs; (2) C8 fresh-holdout tracker runs on eps 13 and 22, with detector
  models trained once on the 5 stage-B eps (`c/run4.sh`, nohup PID 16452, progress `c/run4.progress`; order: E2 h10, E3 s90,
  E1 v2 for each ep; train log `c/train_hold.log`); (3) a saved carry/smoothing evaluator; (4) a GT-only check of the
  half-frame timing shift on full trajectories; (5) verdict and expected AUC impact.

### C7. Write-up of all finished stage-C runs (outputs `c/ev_<ep>_<tag>.txt`, run 01:15-02:10) [V; prior = emulated]
Trajectory AUC (kit ADD thresholds 1-9 cm, cameras = VO + Treg, GT at t - 0.5; "this trajectory" = no policy, no slot-0 anchor).
| ep | object | E1 free (coarse init) | E2 h10 prior -> fused | E2 h20 prior -> fused | fix >= 2 rest/held/carried (h10) |
|---|---|---|---|---|---|
| 12 | blue_cup | 0.179 | 0.885 -> 0.911 | 0.647 -> 0.693 | 0.22 / 0.76 / 0.53 |
| 12 | rack | 0.958 | 0.809 -> 0.852 | 0.498 -> 0.538 | 0.42 / 0.05 / - |
| 21 | blue_cup | 0.597 | 0.875 -> 0.947 | 0.631 -> 0.738 | 0.93 / 0.92 / 0.77 |
| 21 | water_pitcher | 0.226 | 0.830 -> 0.907 | 0.544 -> 0.643 | 0.90 / 1.00 / 0.87 (all 2-marker) |
| 26 | rack | 0.985 | 0.860 -> 0.921 | 0.590 -> 0.683 | status>=2 0.71 |
| 26 | white_pot | 0.325 | 0.849 -> 0.934 | 0.585 -> 0.685 | status>=2 0.78 |
| 0 | white_pot | 0.743 | 0.864 -> 0.895 | 0.619 -> 0.622 | 0.71 / 0.94 / 0.70 |
| 0 | white_pot_lid | 0.977 | 0.896 -> 0.983 | 0.665 -> 0.920 | 1.00 everywhere |
- Fused (marker fix where >= 2 markers, else prior) never lowers the trajectory AUC: +0.03 to +0.09 at h10 for cup/pot/
  pitcher/rack, +0.09 for the lid; +0.00 to +0.11 at h20 (lid +0.26). On fix frames, fused ADD is 5.9-15 mm vs 15.6-24.5 mm
  for the prior (h10); fused is worse than the prior on 3-15 % of fix frames (pitcher rest 9 %, ep-0 pot 20-30 %).
- Per-frame errors on fix frames at h10 (median / p90): 3-marker fixes t 5.2-8.5 / 11-18 mm, r 1.6-4.8 / 3.0-7.5 deg,
  ADD 5.5-9.3 / 9.8-18.6 mm; 2-marker fixes t 6.0-11.8 / 12-16 mm, r 3.3-14 / 6-15 deg (rotation about the marker axis
  is left to the prior), ADD 7.6-15 / 15-28 mm. These include ~1-2 mm camera error and the +-0.25-0.5 frame timing jitter.
- Scorer-style (slot-0 frame-0 alignment) numbers swing with the single frame-0 pose: h10 fused raises the episode mean
  in all 4 eps (0.756 -> 0.846, 0.708 -> 0.888, 0.782 -> 0.912, 0.835 -> 0.917), but at h20 it lowers it in eps 12 and 0
  (0.380 -> 0.152, 0.547 -> 0.324) because the frame-0 fused pose was a wrong 2-marker fix. So **the slot-0 frame-0 pose
  must not be taken from a single marker fix**; it needs pooling over the static prefix (see C7b carry).
- Runtime: 0.39-1.43 s/frame for 2 objects x 3 cameras in Python (host load 6-23 from other jobs); E1 up to 3.4 s/frame.

### C7a. Spin choice in the E3 runs (`c/spin_stats.py`) [V; prior 5 mm / 3 deg + constant spin error]
Chosen spin hypothesis vs the correct one (+-15 deg) on fix frames:
- ep 21 s90: 86/89 (rest 51/51, held 24/26, carried 11/12); s180: 109/112 (rest 56/56, held 32/32, carried 21/24).
- ep 12 s90: 47/56 (rest 19/19, held 8/14, carried 20/23); s180: 52/61 (rest 19/19, held 10/15, carried 23/27).
- The first fix is at t = 0 and correct in all 4 runs. **At rest the spin is right in 145/145 fix frames**, including ep 12
  where only 2 cup markers face the head. In hand, 8-43 % of the fix frames pick a wrong spin (mostly +-30-90 deg
  neighbours or the 180 deg twin), so in-hand spin decisions need pooling over frames, not single-frame acceptance.

### C7b. Offline "carry" of marker corrections (`c/ev_carry2.py`, saved; `c/carry_all.txt`) [V; prior = emulated]
The marker correction (body-frame rotation Rp^T R, world translation t - tp) at fix frames (status >= 2) is interpolated
between fixes and applied to the prior everywhere. It uses later fixes, so it is offline smoothing (allowed: the whole
video is available). The saved script reproduces the unsaved C5/C6 numbers exactly (ep 12 h10 cup 0.940 / rack 0.902,
ep 21 s90 cup 0.938 / pitcher 0.970). Trajectory AUC prior -> fused -> carry:
| run | object: prior / fused / carry |
|---|---|
| 12 h10 | cup 0.885 / 0.911 / 0.940; rack 0.809 / 0.852 / 0.902 |
| 21 h10 | cup 0.875 / 0.947 / 0.975; pitcher 0.830 / 0.907 / 0.917 |
| 26 h10 | rack 0.860 / 0.921 / 0.932; pot 0.849 / 0.934 / 0.954 |
| 0 h10 | pot 0.864 / 0.895 / 0.914; lid 0.896 / 0.983 / 0.983 |
| 12 h20 | cup 0.647 / 0.693 / 0.759; rack 0.498 / 0.538 / 0.631 |
| 21 h20 | cup 0.631 / 0.738 / 0.886; pitcher 0.544 / 0.643 / 0.738 |
| 26 h20 | rack 0.590 / 0.683 / 0.815; pot 0.585 / 0.685 / 0.774 |
| 0 h20 | pot 0.619 / 0.622 / 0.632; lid 0.665 / 0.920 / 0.923 |
| 12 s90 / s180 | cup 0.434 / 0.565 / 0.842; 0.188 / 0.416 / 0.806 (rack 0.938 -> 0.965) |
| 21 s90 / s180 | cup 0.438 / 0.677 / 0.938; 0.188 / 0.643 / 0.933 (pitcher 0.950 -> 0.970) |
- Carry adds +0.01 to +0.15 over fused at h10/h20 and +0.26 to +0.39 when the prior has a constant spin error. Mean gain over
  the prior (carry, in-sample eps): **h10 +0.08 (cup/pot/pitcher/rack +0.05 to +0.105; lid +0.09); h20 +0.17 (0.01 to 0.26; fused alone +0.09); spin error +0.41 to
  +0.75 on the cup**. The exception is the ep-0 pot at h20 (+0.01): 2-marker fixes with a 20 mm / 10 deg prior are noisy.
- The scorer-style mean still drops at h20 in eps 12 and 0 (0.380 -> 0.159 and 0.547 -> 0.355) because the frame-0 pose
  comes from one bad fix at t = 0 (cup ep 12: f0 ADD 14 mm prior -> 43 mm). A robust version (running medoid over +-2
  fixes, `K=2`) is in `c/carry_k2.txt` (C7c).

### C7c. Carry variants (`K=2 c/ev_carry2.py` -> `c/carry_k2.txt`; `SMIN=3` -> `c/carry_s3.txt`) [V; prior = emulated]
- Running medoid over +-2 fixes (K=2) rejects isolated wrong fixes: cup ep 12 h10 0.940 -> 0.952, ep 21 s90 0.938 -> 0.956,
  ep 12 s90 0.842 -> 0.873, pot ep 0 h20 0.632 -> 0.719; small losses elsewhere (rack ep 12 h10 0.902 -> 0.888, ep 26 h20
  0.815 -> 0.797 / pot 0.774 -> 0.763). Net small positive.
- 3-marker fixes only (SMIN=3): best when the prior error is a constant (spin) — cup ep 21 s90 0.978, ep 12 s90 0.963 from
  only 12-37 fixes — but worse than fused when the prior error wanders (ep 12 h10 cup 0.890, rack 0.743; pot ep 0 0.873),
  because 3-marker fixes are too sparse to follow an error that decorrelates in ~1 s. A real hybrid should weight fixes by
  quality (3-marker > 2-marker) inside a smoother, rather than choosing one rule.
- Neither variant fixes the bad frame-0 pose at h20 (cup ep 12 f0 ADD 37 mm, pot ep 0 49 mm). See C7d (static-prefix pooling).

### C9. AUC cost of a pure time lag (`c/lag_auc.py`, GT only, 33 objects in all 20 public eps; `c/lag_auc.txt`) [V]
A perfect tracker whose video-frame-t pose is scored against GT row t, while the frame actually shows GT row t - L:
- **L = 0.5 frame (b/c): mean AUC loss 0.0017 per object (worst 0.005, ep-0 pot).** Negligible; B12.4's "0.75-2.5 cm
  at carried speeds" is right for peak frames but carried frames are too few to move the AUC.
- L = 1.0: 0.010 (worst 0.025, ep-21 pitcher). **L = 1.35 (cam-a frames used without the per-episode delta, typical ep):
  0.017 (worst 0.042). L = 2.4 (ep-21-like delta 2.14 ignored): 0.045 (worst 0.109, ep-42 pot).**
- Reading: the half-frame b/c offset is not worth engineering for AUC. The cam-a offset (1-2 frames, per episode) is:
  any pipeline that fuses cam a with b/c (or tracks on cam a) must apply the per-episode delta (stage A4/B20.3), or lose
  ~0.02-0.05 AUC per object, more on fast episodes.

### C7d. Slot-0 frame-0 pose from pooled static-prefix fixes (`c/static0.py` -> `c/static0_only.txt`) [V; prior = emulated; prefix from GT segments = diagnostic stand-in for an automatic contact detector]
The slot-0 object's poses over its static prefix are replaced by the rotation medoid and median translation of all its
fixes (status >= 2) in that prefix; the rest is the carry trajectory. f0 ADD and scorer-style mean (carry -> pooled):
- ep 0 pot (105-frame prefix, 53-65 fixes): h10 7.1 -> 3.7 mm, mean 0.925 -> 0.964; **h20 54 -> 30 mm, 0.355 -> 0.620**.
- ep 12 cup with spin error (30-frame prefix, 5 fixes): s90 / s180 10.7 -> 2.6 mm, **mean 0.567 -> 0.889 and 0.547 -> 0.865**.
- ep 21 cup (29-frame prefix, 20-28 fixes): f0 8.3 -> 7.7 (h10), 13.1 -> 8.0 mm (s90), but the mean is flat or lower
  (0.904 -> 0.902, 0.785 -> 0.763, 0.893 -> 0.883): the pitcher, aligned through the cup's frame-0 rotation, lost 0.05-0.07.
  Lower f0 ADD does not guarantee a better anchor for the other object (rotation lever arm).
- ep 12 cup h10 / h20: only 1 fix in the 30-frame prefix (2 head-facing markers, rest fix rate 0.22), so nothing to pool;
  at h20 that single fix is wrong (f0 ADD 43 mm vs 14 mm for the prior) and the scorer-style mean drops 0.380 -> 0.191.
- Reading: pooling the static prefix is the right estimator for the slot-0 anchor when it has many fixes (pot, lid,
  cups with 3+ facing markers), and it fixes spin errors at frame 0. When the prefix has 0-2 fixes, a lone 2-marker fix must
  not override the model-based pose unless it agrees in spin only (use the marker fix for the spin, keep the prior's
  tilt/translation) [H, not tested].

### C8. Fresh-holdout tracker runs, eps 13 and 22 (detector trained once on eps 12/26/21/0/31, `c/train_hold.log`; `c/run4.sh`) [V; prior = emulated]
- **Ep 13 E2 h10 (`c/ev_13_h10.txt`, `c/carry_13_h10.txt`): blue cup fixes (>= 2 markers) 0.75 rest / 0.64 held / 0.84 carried
  (>= 3: 0.17 / 0.00 / 0.09). On fix frames ADD 20.4 -> 8.6 mm (rest), 17.8 -> 10.1 (held), 18.2 -> 8.9 (carried); fused worse
  than prior on 11-17 % of fix frames. Trajectory AUC prior 0.879 -> fused 0.932 -> carry 0.946 (K=2: 0.958). Rack (static)
  0.812 -> 0.858 -> 0.864.** Scorer-style mean 0.767 -> 0.803 (fused) -> 0.833 (carry) -> 0.906 (carry K=2).
- Per-frame errors, cup on fix frames: 2-marker t 6.1-8.1 / 11.8-21 mm (median / p90), r 4.0-5.6 / 6.8-14 deg; 3-marker t
  7.1-7.6 mm, r 2.5-5.4 deg, with one bad carried 3-marker cluster (p90 r 60 deg, ADD 67 mm: a wrong 3-marker association,
  n 7). Runtime 0.69 s/frame.
- Same direction and size as the in-sample eps (C7: cup +0.03 to +0.07 fused, +0.06 to +0.10 carry at h10), with a HIGHER
  fix rate than ep 12 at rest (0.75 vs 0.22) because ep 13's resting cup shows 3 markers in 0.38 of frames (B15).
- **Ep 22 E2 h10 (`c/ev_22_h10.txt`, `c/carry_22_h10.txt`): blue cup FULL (>= 3 marker) fixes in 0.99 rest / 0.94 held / 0.86
  carried frames** (>= 2: 1.00 / 1.00 / 0.98). 3-marker fix errors (median / p90): t 6.9-7.6 / 12-15 mm, r 2.2-4.0 / 3.6-7.0
  deg, ADD 7.2-8.9 / 12-17 mm. Trajectory AUC prior 0.874 -> fused 0.973 -> carry 0.975 (K=2 0.989). Pitcher (2-marker only)
  0.829 -> 0.892 -> 0.902 (K=2 0.914); fused worse than prior on 10-18 % of its fix frames. Scorer-style mean 0.760 -> 0.892
  -> 0.913. Runtime 0.64 s/frame.
- So on an episode where all four cup markers face the head (B18 ceiling 1.00), a prior-guided marker tracker reaches
  near-continuous 6-DoF fixes at ~7 mm / 2-4 deg, even while carried. With a decent prior, the guided detector clearly beats
  the per-view recall of B19 (0.40-0.53 held/carried), because the 3-sigma window, z-buffer prediction and 3 cameras make
  every weak candidate count. Whether this works without the prior is tested by the E1 run on ep 22 (below).
- **Fresh-holdout spin recovery, E3 s90 (`c/ev_{13,22}_s90.txt`, `c/carry_hold_s90.txt`, `c/spin_stats.py`)** [V; prior 5 mm /
  3 deg + constant 90 deg spin]:
  - ep 22: correct spin on 105/108 fix frames (rest 56/57, held 37/38, carried 12/13). Cup AUC prior 0.438 -> fused 0.735 ->
    carry 0.946 (K=2 0.977, 3-marker-only 0.962).
  - **ep 13: correct spin on only 74/99 fix frames, and at REST on only 13/27** (13 rest frames chose the 180 deg twin; held
    25/36, carried 36/36). Cup AUC 0.438 -> 0.618 -> carry 0.815 (K=2 0.828; 3-marker-only 0.898). The first fix (t = 0) was
    right, so f0 ADD is 3 mm; pooling the 18-frame static prefix (6 fixes) gives 5.9 mm and a scorer-style mean of 0.891.
  - Cause [V geometry]: the blue cup's 4 markers are 2 near the rim (z +64 / +73 mm) and 2 near the base (z -71 / -51 mm).
    Under a 180 deg turn about the cup axis the two RIM markers land within 9.5 mm of each other's positions (~1.3 marker
    radii), whereas the base pair is 39 mm off. When a resting cup shows only its rim pair (ep 13), the 180 deg spin twin
    is nearly as good as the truth. Ep 12's resting cup shows one rim and one base marker (m0, m2), which is not ambiguous.
  - **Correction to C7a:** "rest spin right in 145/145 fix frames" holds for eps 12/21 and 22 (201/202), not for ep 13.
    The cup spin from markers has a 180 deg ambiguity whenever only the rim pair is seen. A spin decision needs a
    base marker, a 3-marker fix, or pooling that tests both twins explicitly. Note 12 found the same kind of 2-detection
    flip (120 deg) for the beige cup.
- Holdout static-prefix pooling (`c/static0_only.txt`): ep 13 h10 scorer-style mean 0.833 (carry) -> 0.897 (pooled, 14
  fixes); ep 22 has no static prefix for the cup (it is moving from frame 0), so there is nothing to pool.
- **Fresh-holdout E1, free-running marker-only tracker with a 20 mm / 5 deg init (`c/ev_{13,22}_v2.txt`)** [V]:
  - ep 13: the cup is lost at the first grasp (fix >= 2 in 0.23 rest / 0.02 held / 0.03 carried); AUC 0.148. The static rack
    gets 2-marker fixes in 0.50 of frames, ADD 9 mm, AUC 0.978.
  - ep 22, where all 4 cup markers face the head: cup fix >= 2 in 0.89 rest / 0.69 held / 0.18 carried, AUC 0.761. Its
    3-marker fixes are accurate (ADD 4.5-5.9 mm), but its 2-marker rest fixes lock in a biased pose (ADD 33 mm, r 21 deg),
    and it coasts away while carried (ADD 47 mm median). Pitcher: lost at the first carry, AUC 0.371.
  - The same cup in ep 22 with an h10 prior (above) had full fixes in 0.86-0.99 of frames and AUC 0.973. **The gap between
    E1 and E2 on the same video and the same detector is the value of the model-based prior**: it keeps association alive
    through blur, occlusion and fast motion, and it supplies the rotation that 2-marker fixes leave free. The stage-C
    verdict therefore holds on two unseen episodes: markers do not work stand-alone for cups or pitcher, and a prior-guided
    marker layer works well.
- Runtime on the holdouts: 0.64-0.73 s/frame (2 objects x 3 cameras, Python, host load 17-28 from other agents' jobs).

### C10. Spin recovery under noisier priors, and a temporal spin vote (`c/run5.sh`; `c/ev_21_s90n{10,20}.txt`, `c/carry_s90n.txt`, `c/spin_vote.py` -> `c/spin_vote.txt`) [V; prior = emulated]
- Per-frame spin choice degrades fast with prior noise (ep 21 cup, constant 90 deg spin error): correct on 86/89 fix frames at
  5 mm / 3 deg, **57/107 at 10 mm / 5 deg, 10/62 at 20 mm / 10 deg** (near random). Carry AUC 0.938 -> 0.675 (K=2 0.780) ->
  0.427 (prior 0.415 / 0.294). Cause [E]: the hypotheses are scored at the prior's tilt and translation, so a 5-10 deg tilt
  error moves every hypothesis' markers by 5-15 mm and wrong spins match as well as the right one. A per-hypothesis 6-DoF
  fit before scoring is the obvious fix [H, not built].
- **Temporal vote** (each fix frame votes for its chosen spin, 3-marker fixes count double, +-15 deg window; the spin error
  is constant): **correct in 8/8 runs** (eps 12 s90/s180, 21 s90/s180, 13 s90, 22 s90, 21 s90n10, 21 s90n20), with
  winner / runner-up margins 59/5 to 171/2 at 5 mm / 3 deg, 83/23 for ep 13 (the 180 deg rim-pair twin of C8), 94/21 at
  10 mm / 5 deg and 26/12 at 20 mm / 10 deg. **Restricted to frames 0-39 (slot-0 anchor use) it is also 8/8 correct**
  (6-37 fix frames; margins 6/0 to 54/0, 19/1 at 20 mm / 10 deg).
- Reading: a single-frame marker spin is unreliable (rim-pair twin, prior tilt), but **a vote over a static prefix or a
  grasp segment gives the cup spin reliably on 4 episodes (2 unseen)**, with priors up to 20 mm / 10 deg. This is the
  marker cue most worth building. Limitation: the emulated spin error is constant. A real tracker's spin error can
  change at each grasp (the cup turns in the hand), so votes must be per segment (between contact events).
- Ep 12 (resting cup shows 2 markers; `c/ev_12_s90n{10,20}.txt`): per-frame spin correct 34/61 at 10 mm / 5 deg and 5/25 at
  20 mm / 10 deg. **Vote: correct at 10 mm / 5 deg (47/13; frames 0-39: 4/0), but WRONG at 20 mm / 10 deg (25 fixes, tie
  7/7; no fix at all in frames 0-39)**. Carry AUC 0.413 -> 0.637 and 0.312 -> 0.229 (worse than the prior).
- **Vote totals: 9/10 runs correct; the failure is the low-fix case (ep 12, 20 mm / 10 deg prior).** With an abstain rule
  (winner >= 4 votes and >= 2x the runner-up outside +-30 deg), all 10 decisions are correct or abstain (1 abstention), and in
  frames 0-39, 9 decide correctly and ep 12 at 20 mm / 10 deg abstains. Acting on wrong spin fixes is costly (the carry
  of ep 12 at 20 mm / 10 deg drops the cup from 0.312 to 0.229, below the prior), so an abstain rule is required.
- All stage-C jobs finished at 08:11 (`c/run4.done`, `c/run5.done`); nothing is running.

### C11. Stage C close (2026-10-07 08:15)
- Verdict and expected AUC impact: see "Final summary and verdict" at the top of this file.
- Stage-C files (work/17/c): tracker `trk17.py` (v1 and v2 frozen copies), evaluator `ev17.py`, LOEO and holdout detector
  models `train_loeo.py` -> `clf_<ep>.pkl` (clf_13/22 trained on all 5 stage-B eps), acquisition `acq17.py`, layout
  calibration `calib17.py` / `calfit.py`, carry `ev_carry2.py`, static-prefix anchor `static0.py`, spin `spin_stats.py` /
  `spin_vote.py`, lag `lag_auc.py`; run scripts `run1-5.sh`. Outputs: `trk_<ep>_<tag>.npz`, `ev_<ep>_<tag>.txt` (tags v2, h10,
  h20, s90, s180, s90n10, s90n20), `carry_all.txt`, `carry_k2.txt`, `carry_s3.txt`, `carry_{13,22}_h10.txt`,
  `carry_hold_s90.txt`, `carry_s90n.txt`, `static0_only.txt`, `spin_vote.txt`, `lag_auc.txt`.
- Open items:
  - a real model-based prior in place of the emulation;
  - a per-hypothesis 6-DoF fit for spin;
  - a CNN detector on b/c [H];
  - cameras for eps 11/23/18/41, to test the beige cup, dust pan and wooden pieces;
  - the spoon's marker layout, self-calibrated from eval video at rest [H].
- No jobs running. No SlamDunk file other than this note was edited.

## Verification (skeptical verifier, 2026-10-07 08:15-; claims C1/C3/C4/C5 of the stage-C verdict; scripts and outputs in `work/17-verify/`)
- Fresh start (17-verify was empty). Re-run setup: `work/17-verify/run/` (symlinks `out` -> work/17/out, `c/clf_*.pkl`),
  `chain_v.sh` (background PID 47688; progress `chain_v.progress`): E1 v2 ep 22 (TAG _vfy) and E2 h10 ep 13 (TAG _h10vfy) with the
  unmodified `work/17/c/trk17.py`, then ev17 / ev_carry2. Code read: trk17.py (current = v2 frozen + SPIN/SPINHYP/GTFRESH options
  only), ev17.py, ev_carry2.py, train_loeo.py; kit AUC.py (plain ADD over vertex samples, thresholds 1-9 cm, trapezoid: ev17 matches).
- [V] Detector models for eps 13/22 (`c/clf_13.pkl` == `c/clf_22.pkl`, byte-identical) come from `train_loeo.py` with POOL 12/26/21/0/31;
  the target never enters training.
- V1 (C1) [V] E1 ep 22 re-run (`run/c/ev_22_vfy.txt`, 0.40 s/frame) reproduces `c/ev_22_v2.txt` line for line (cup AUC 0.761, fix
  rates, errors; pitcher 0.371). Per-block timelines from the saved error arrays (`17-verify/timeline.py` on `c/trk_<ep>_v2_err*_reg.npy`):
  every cup/pot/pitcher run loses track in the first carry (ADD 53-233 mm block medians), confirming "lost at the first carry".
  But 3 of 8 object runs RE-ACQUIRE later: ep 0 pot (rest after carry ADD 5-7 mm, fix>=2 0.79), ep 21 cup (t 100-153 ADD 7-12 mm,
  then a biased final rest ADD 50 mm), ep 22 cup (t 89-116 ADD 6-9 mm with 3-marker fixes, then 19-34 mm). "Near object left
  behind" fits eps 12/13/26 and both pitchers, not pot 0 / cup 21 / cup 22.
- V1b (C1 details) [V]: 3-marker fixes in hand are 0-2 % except ep 21 cup held 0.09 and ep 22 cup held 0.24 / carried 0.07; the
  "0-4 %" is the whole-trajectory status-3 fraction. "27 mm / 12.6 deg" (ep 21) is translation (ADD 28.6 mm) and is a mix of a
  good first rest (ADD 11 mm) and a biased final rest (ADD 50 mm); ep 22's 33 mm is ADD (t 31.8 mm, r 20.6 deg), final rest.
- V2 (C5) [V] Independent re-derivation from the saved E3 npz files (`17-verify/spin_check.py`, own vote code): per-frame spin
  correct (+-15 deg) 86/89, 57/107, 10/62 (ep 21 at 5/3, 10/5, 20/10) and every vote outcome/margin of `c/spin_vote.txt` reproduce
  exactly (9/10 correct; ep 12 20/10 = 7/7 tie; abstain rule -> 9 correct + 1 abstain, t<40: 9 + 1). Fragility: the one correct
  20 mm / 10 deg vote (ep 21) wins with 26/12 (2.17x, just over the 2x bar) and lands 15 deg off (255); its voters are mostly
  30 deg off (13 frames) and with exact-bin voting (no +-15 window) it would pick 240 and abstain. So at 20/10 the vote is 1
  marginal success + 1 abstention out of 2, not "reliable". Ep 12 10/5 t<40 decides on exactly 4 votes.
- V3 (C5 extension) [V, emulated prior] Applying the VOTED constant spin to the prior (`17-verify/vote_auc.py`) gives the oracle-spin
  AUC in 8 of 9 deciding runs (5/3: 0.965-0.969; 10/5: 0.875 / 0.885; 21 s90n20 0.617 vs oracle 0.631; the 15-deg-off t<40
  winners cost 0.03). This beats the per-frame carry (0.81-0.95 at 5/3, 0.64-0.68 at 10/5, 0.23-0.43 at 20/10). The carry
  numbers quoted in C5 are 5 mm / 3 deg prior numbers only.
- V4 (C3/C4) [V, emulated prior] Where the hybrid correction acts (`17-verify/depth_split.py`, h10 runs, fix frames, translation
  error split along the cam-b viewing ray vs lateral; slope = regression of fused error on prior error): lateral error is
  removed almost fully (median 10-15 -> 2.6-8 mm, slope -0.02..0.25), but the DEPTH error largely survives on 2-marker-dominated
  fixes: slope 0.85 (cup ep 12), 0.94 (cup ep 13, unseen), 0.59-0.69 (racks), 0.30-0.55 (cup 21, pot, pitcher, lid 0.24); only
  ep 22's cup (178/188 3-marker fixes) reaches 0.10. The emulated AR(1) noise is isotropic (about 1/3 of its variance along the
  ray: prior depth |err| median 5-12 mm vs lateral 10-15 mm). A real monocular model-based tracker errs mostly in depth [E], so
  on 2-marker objects the hybrid would remove a smaller share of a real prior's error than the C3 numbers show [E]. This is a
  concrete instance of the C4 caveat.
- V5 (C3) [V] E2 h10 ep 13 re-run end to end (`run/c/ev_13_h10vfy.txt`, `run/c/carry_13_h10vfy.txt`): identical to `c/ev_13_h10.txt`;
  cup prior 0.879 -> fused 0.932 -> carry 0.946, fix>=2 0.75 / 0.64 / 0.84. All C3 ranges re-read from `c/ev_*_h10.txt`,
  `c/carry_*.txt`: cup fix>=2 rest 0.22-1.00 / held 0.64-1.00 / carried 0.53-0.98; fused gains +0.026..+0.099, carry +0.050..+0.105
  (K=2 up to +0.115, ep 22 cup). The "ADD 16-24 -> 6-18 mm" range spans all objects (cup alone: 15.6-20.4 -> 5.9-10.1 mm).
- V6 (C1 robustness) [V] E1 ep 22 with another init draw (SEED=1, `run/c/ev_22_v2s1.txt`): cup AUC 0.742 (vs 0.761), pitcher
  0.375 (vs 0.371). Same pattern: 3-marker fixes and ADD 4-6 mm until t 41, lost in the first carry (t 42-88 ADD 73-83 mm),
  re-acquired from t 89 (ADD 7-14 mm). The 2-marker "biased lock" at rest (33 mm / 21 deg) is init-draw dependent: with SEED=1
  the t 21-38 rest keeps 3-marker fixes (ADD 6 mm) and the final rest is 14 mm.
- V7 (C1 cause) [V, from saved outputs] B19's per-view recall (b/c held/carried 0.26-0.38 full frame, 0.37-0.45 guided;
  `out/det_eval_hold_thr05.txt`, `out/guided_learned_hold.txt`) reproduces, but it is not the binding limit on ep 22: the same
  detector with the h10 prior gives 3-marker fixes in 0.94 held / 0.86 carried frames there (`c/ev_22_h10.txt`). On ep 22 the E1
  loss is an association/prediction failure (no velocity from 2-marker fixes, 8 px gate vs ~8-17 px/frame carried motion), not
  missing detections. On eps 12/13/21 the geometric/2-marker limit also applies.
- V8 (C5 premise) [V] Blue-cup catalogue (`out/marker_catalogue.json`): under a 180 deg turn about body z the rim markers m1/m2 map
  to within 9.5 mm of each other, the base pair to 39 mm (C8's rim-pair twin reproduces). Note 12 (row blue_cup) confirms the body
  is a featureless surface of revolution (spin unobservable without markers, except the base inscription when tipped).
- V7 wording fix: the E1 gate is not a fixed 8 px; it grows 12 px per coasting frame, but the pose prediction stops following the
  object (velocity only from 3-marker fixes, decays while coasting), so the gate grows around a stale position.
- V9 (C1 robustness) [V] The loss is not caused by the coarse init: with a FINE init (IP=5,2: 5 mm / 2 deg) E1 still loses the cup
  in the first carry (ep 13 AUC 0.149, t 22-45 ADD 123 mm, never re-acquired; ep 22 AUC 0.699, t 42-88 ADD 58-79 mm, slow
  re-acquisition, final rest 35 mm / 23 deg). Ep 13 SEED=1: cup timeline identical to SEED=0 (AUC 0.148; it converges at t 0),
  rack 0.962. Files `run/c/ev_{22,13}_v2{s1,ip5}.txt`. C1's conclusion holds for this tracker/detector design.
- V10 (C3 robustness) [V, emulated prior] Second AR(1) noise draw (SEED=1, h10; `run/c/ev_{13,22}_h10s1.txt`, `run/c/carry_{13,22}_h10s1.txt`).
  The realised prior error differs a lot between draws (rho 0.95 over ~190 frames is only ~10 independent samples): cup prior AUC
  0.931 / 0.930 (vs 0.879 / 0.874 with SEED=0). Gains shrink with it: ep 13 cup prior 0.931 -> fused 0.954 (+0.023) -> carry
  0.962 (+0.031); ep 22 cup 0.930 -> 0.984 -> 0.984 (+0.054); rack 13 +0.040 / +0.115; pitcher 22 +0.092 / +0.109. Fix rates hold
  (cup 13 fix>=2 0.94 / 0.82 / 0.88; ep 22 >= 3-marker 0.95-0.99). So C3's "+0.03..+0.10 fused / +0.05..+0.12 carry" is a one-draw
  range; with a smaller realised prior error the cup gain is +0.02 / +0.03. Fused worse than the prior on 26-29 % of ep-13 cup rest/held
  fix frames (4 held 3-marker fixes at 44 mm ADD = wrong associations), vs the 3-18 % quoted. Slot-0 risk at h10 too: ep 13
  SEED=1 frame-0 cup fix is wrong (f0 ADD 41 mm / 17 deg) and the scorer-style mean drops 0.763 (prior) -> 0.090 (fused) / 0.095
  (carry), so C7's "h10 fused raises the episode mean in all eps" does not survive a second draw; pooled anchors are required.

### Verifier verdicts (2026-10-07 08:35)
- C1 NOT refuted, corrected: E1 numbers reproduce exactly (ep 22 re-run); the loss at the first carry is robust to the init draw and
  to a fine 5 mm / 2 deg init. Corrections: 3 of 8 object runs re-acquire after the carry (pot 0, cup 21, cup 22); in-hand
  3-marker fixes reach 9 % (ep 21 held), the 0-4 % is the whole-trajectory rate; scope is this detector family + v2 tracker
  design (on ep 22 the binding limit is prediction/association, not per-view recall).
- C3 NOT refuted, corrected: numbers reproduce exactly (ep 13 re-run, ep 12 carry 0.940 recomputed), but the gain range is a single
  noise draw (second draw: cup 13 +0.02 / +0.03); markers remove the lateral error but leave 50-94 % of the depth error on
  2-marker-dominated fixes (V4), so the isotropic emulation flatters the hybrid relative to a depth-dominated real prior [E].
- C4 NOT refuted, strengthened: also the fix rates and relative gains are conditional (prior noise level known to the tracker, isotropic
  noise, no object loss, one seed; V4, V10).
- C5 NOT refuted, qualified: all spin numbers reproduce from the saved runs (independent vote code); the voted constant spin reaches
  oracle-spin AUC (V3). But it is 1 object, 4 eps, constant on-grid spin errors, one draw, and the abstain rule was set after
  seeing these 10 runs; at 20 mm / 10 deg it is 1 marginal success (15 deg off, 2.17x margin) + 1 tie, not "reliable".
- No background jobs left running (chain_v / chain_v2 finished 08:29).

### Verification resume (2026-10-07 12:25-, same claims C1/C3/C4/C5; earlier verifier outputs in `work/17-verify/` re-read, not re-run)
- R1 [V] Earlier verifier re-runs still match the originals byte-for-byte apart from the header (`diff` of `c/ev_22_v2.txt` vs
  `17-verify/run/c/ev_22_vfy.txt`, `c/ev_13_h10.txt` vs `run/c/ev_13_h10vfy.txt`). `c/clf_13.pkl` == `c/clf_22.pkl` (cmp). Spin votes
  re-derived again with `17-verify/spin_check.py`: same 9 OK + 1 tie (ep 12 20/10, 7/7), t<40 same; PN fields in the npz files confirm
  s90/s180 = 5/3, s90n10 = 10/5, s90n20 = 20/10.
- R2 [V, new] C1/B19 wording "all four cup markers face the head in ep 22" is wrong: the z-buffer census (`out/census_22.npz`, VIS and
  ZV) has EXACTLY 3 of the 4 blue-cup markers visible in every frame (marker index 2 is never z-visible in any camera; all 4 are only
  inside the image, INI). The tracker agrees: `c/trk_22_h10.npz` npred is 3 in 185/187/137 frames (a/b/c), never 4, and marker 2 is
  used in 0 fix frames. Ep 22 is still the best cup case (>= 3 visible in 1.00 of frames), so C1's point holds; "all 4" -> "3 of 4".
- R3 [V] E1 per-block timelines re-read (`17-verify/timeline.py` on `c/trk_<ep>_v2_err*_reg.npy`): ep 12's cup is never acquired
  (fix>=2 0.00 in every block, status 1 in 0.91 of frames; ADD 21 mm = the init error until the first carry, then 53-205 mm), so
  for ep 12 "lost at the first grasp or carry" is an acquisition failure that becomes visible when the cup moves. Other runs as in V1.
  In-hand 3-marker rates (E1): cup 12 0/0, pot 0 0/0.01, cup 21 0.09/0.02, pot 26 0/0, cup 13 0/0, cup 22 0.24/0.07, pitchers 0 ->
  outside ep 22 the in-hand range is 0-9 %, not 0-4 % (0-4 % is the whole-trajectory status-3 fraction). B19 recalls reproduce from
  `out/det_eval_hold_thr05.txt` (b/c held/carried 0.26-0.38) and `out/guided_learned_hold.txt` (0.37-0.45).
- R4 [V] C3 ranges re-read from `c/ev_*_h10.txt` and `c/carry_*.txt` (cup fix>=2 0.22-1.00 / 0.64-1.00 / 0.53-0.98; fused gain
  +0.026..+0.099; K0 carry +0.050..+0.105, K2 to +0.115). Depth split re-run (`17-verify/depth_split.py`, eps 12/13/22) reproduces V4
  exactly (cup depth slope 0.85 / 0.94 / 0.10). V3 re-run (`vote_auc.py`) reproduces (21 s90n20 voted 0.617 vs oracle 0.631; 12 s90n10
  0.885; 13 s90 0.968; 21 s90n10 t<40 0.849 vs 0.875). Note: "10 mm / 5 deg" is the per-axis AR(1) sigma; the realised prior error is
  ~16-17 mm / ~9-10 deg median (3-D norm), and its AUC varies 0.87-0.93 between noise draws (V10).
- Verdicts of 08:35 unchanged, plus R2 (ep 22: 3 of 4 cup markers visible, not 4) and R3 (ep 12 cup never acquired; in-hand
  3-marker 0-9 %). No background jobs started in this resume.


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 16](16-synthesis-round3.md) · [18 →](18-room-map.md)
