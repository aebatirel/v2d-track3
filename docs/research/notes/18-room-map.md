# 18 — Persistent room map registered to mocap (DIG 18)

Status: ALL STAGES COMPLETE. A and B ran 2026-10-06/07; B was extended on 2026-10-07 morning (B11-B19). C ran
2026-10-07 01:30-02:05; its re-run finished C8 and added C9-C12 at 07:55-08:10, and a resumed run added C13 (the
default module end to end) at 12:25-12:45. Agent 18. Research and analysis only: nothing was submitted, nothing was
downloaded, and no evaluator, physics or SlamDunk code was touched. This notes file is the only SlamDunk file edited.
Work dir: `/Users/aebatirel/Documents/Code/v2d-research/work/18/` (map/relocaliser venv `venv18`: pycolmap 4.2.1,
opencv 5.0.0; GT-reading analysis runs in the shared venv). No jobs are left running.
Tags: [V] verified numerically here, [E] estimate, [H] hypothesis.

Goal: a persistent 3-D room map, made metric by the b/c stereo baseline and registered to the mocap world, so that
every frame of every clip is relocalised in mocap coordinates: drift-free head pose, gravity, height and W.
Stages: A = build, scale and register the map. B = relocalise every frame of public clips and validate with GT.
C = relocalise all 20 eval clips automatically, design the inference module, value it with the error budget.

## DIG 18 bottom line (whole dig)
1. [V] It works on every eval clip, from public data alone.
   - The public-only map `run3` (CPU SfM, 21.5 min, 525 images) relocalises all 20 eval clips with 100 % coverage
     at every 5th frame (1,045 keyframes) and >= 500 rig inliers (30 needed) (C13).
   - The pooled map `run1` (adds the eval frame 0s) gives 100 % coverage at every 5th frame (1,045 keyframes,
     >= 554 inliers). It reaches head pitch 57.8 deg.
   - Both maps agree on eval poses to 0.009 deg / 0.4 mm median (C8, C13). Pooling eval frames buys nothing, so
     the policy question (note 16 §5 Q6) is moot for the room map: use run3.
   - The default module (run3 + C10 gravity + C9 gate + per-clip lag) runs end to end. Per-frame mocap camera
     tracks for all 20 eval clips are in `c6_tracks_v2/` (C13).
2. [V] Accuracy, public held-out frames (stage B): GT-object edge residual 0.10-0.18 cm median on six clips (five
   tasks); no drift. Held-out poses agree with bundle-adjusted poses to ~2 mm / 0.02-0.03 deg, and with note 17's
   marker-registered cameras to 2-5 mm / 0.06-0.18 deg.
   Eval frames never used for the map (GT-free, C4): the table stays level in mocap to 0.34 deg median, and its height
   is 0.6017 m (GT 0.6012) over 116 frames.
3. [V] Failure modes, measured (C9, C11, C12):
   - Rare single-keyframe glitches of 7-11 mm / 0.15 deg occur at normal inlier counts (0.2 % of keyframes on
     run1, 0.1 % on run3). A GT-free VO consistency gate catches them.
   - A central occluder covering >= 75 % of the width degrades poses to cm level; 90 % defeats PnP. Hands and
     objects in the lower two-thirds, the operator at the left, and global exposure/gamma changes cost <= 2 mm.
   - Real eval clips keep a margin of ~5x in inliers before degradation and ~18x before failure (lowest keyframe).
4. [V sim / E transfer] AUC value (C5: official scorer functions on public GT, eval-measured camera error profiles).
   The map makes the camera term ~0 (AUC 1.000 in isolation). The gain depends on what it replaces:

   | replaced tracker | board AUC gain |
   |---|---|
   | the factory-extrinsic stereo VO I measured on eval clips (drift 20-83 mm on 12/20 clips) | +0.10 |
   | a ~3x better VO | +0.01 |
   | a ~3x worse, mono-like tracker | +0.42 |
   | note 02's 5 cm linear drift | +0.19 (note 02 itself: -0.20) |

5. [V] By-products:
   - per-clip GT-free cam_a vs mono lag: -1.05..-1.20 frames; e20 switches to -2.1 at frame 50, at DIG 20's drop;
   - self-calibrated a<-c extrinsic: the factory one is off by ~0.27 deg;
   - per-session b/c extrinsic change, seen as a 0.04-0.14 deg c-only vs rig gap;
   - refined W (A13; 0.58 deg rms per episode);
   - per-frame mocap camera tracks for all 20 eval clips (`c6_tracks_v2/` default, C13; `c6_tracks/` prototype).
6. [V numbers / E reading] Absolute gravity (C10, all 20 public sessions): GT's resting objects lean (+0.30, -0.45)
   deg (0.54 deg) from GT +z. a13 assumes the table is level in GT (lean 0). Leave-session-out prediction error is
   0.50 deg rms, against 0.72 for a13. Ship up_GT = a13 tilted by that lean (applied in C13 about the work-area
   pivot). Scoring impact: none; it matters for physics/priors at the
   ~4 mm-across-the-table level.
7. Task indices 12-13 (e32, e33 cup + spoon; e35-e37 spoon solo; no public GT session of either task): covered.
   - [V] 100 % coverage on both maps, rig inliers >= 629 (run1) / >= 590 (run3), pitch up to 56.3 deg, table tilt
     0.18-0.38 deg median. The occluder/photometric stress tests
     used e35.
   - [E] The task indices come from recording order: public 31 = task 11, public 39 = task 14, and eval 32-38 lie in
     the gap.

## Stage C bottom line
- [V] Coverage: 100 % rig and cam_a at every 5th frame of all 20 eval clips, with both run1 (pooled) and run3
  (public-only, C13). Inliers: rig min 554 (run1) / 500 (run3); cam_a min 80 (one e33 frame). Envelope: pitch
  34-58 deg, roll -7..+16 deg, heading excursions -15..+13 deg, height 1.09-1.15 m.
- [V] Public-only vs pooled map (C8): eval poses agree to 0.010 deg / 0.51 mm median (p90 0.028 deg / 1.3 mm). The
  only >= 8 mm differences are one single-keyframe glitch in each map.
- [V] Eval-side validity without GT (C4): table-normal tilt 0.34 deg median (p90 0.83) and table height 0.6017 m on
  frames t >= 50. Both stay flat over time, while VO-chained poses tilt by up to 2.7 deg.
- [V] Time: the a<-mono lag is -1.15 frames (19 clips); e20 goes from -1.2 to -2.1, with a pairing changepoint at
  frame 50 (DIG 20 drop at rows 48-49).
- [V] Robustness (C9, C11, C12):
  - keyframe glitch rate 0.1-0.2 % at 5 mm (run3 / run1), caught by the VO gate (C9, C13);
  - >= 100 rig inliers => <= 1.1 cm max error (p90 4 mm);
  - a central 50 % occluder still gives 1.4 mm median, 75 % up to 4.4 cm, 90 % fails;
  - gamma 0.6/1.6 and 30 % exposure + noise: <= 0.6 mm median.
- [V/E] AUC: +0.10 vs the measured factory-extrinsic VO, +0.01 vs a 3x better VO, +0.42 vs a 3x worse tracker.
- [V] Cost (C13): keyframes every 5 frames at 1.24 s each plus VO at 0.057 s/frame = 0.31 CPU-s per frame. All 20
  eval clips take ~9.5 min wall with 3 processes on the 14-core Mac, ~1.3 GB RAM per process. Map build is 21.5 min
  once.
- [V] Default module end to end (C13): `c6_tracks_v2/` = run3 + a13 + C10 tilt + C9 gate. It matches the run1
  prototype to 0.008 deg / 0.37 mm median (p90 0.94 mm). The gate rejects one keyframe of 1,045 (e10 t100, 10 mm).
- [V] Task indices 12-13 (e32, e33, e35, e36, e37): covered, see whole-dig item 7. Their slot lies between map
  sessions 31 and 39-44.
  - A11's independent per-episode headings for the later sessions 41-44 (+1.68..+2.96, median ~2.2, the same as the
    early sessions) show that the room-mocap link holds after them.
  - Late sessions (e30-e38, and public 39-44 in A9) show a +3..+5 mm table-height offset vs the registration. This
    is a mm-level session effect that the scorer absorbs; use per-clip stereo table height for physics.

## Relocalisation module for inference (design)  [V components and offline integration (C13) / E causal online use]
Inputs: the clip's three videos, the persisted map assets and the factory calibration. It reads no GT and no
per-episode labels; public GT is used only offline, once, for the map-to-mocap registration.

Offline, once (automatic):
1. Frame pool:
   - every 30th frame of every public clip (a/b/c), undistorted to pinhole (a1), with a bottom-centre hand/table
     mask;
   - default = public frames only (run3, `c0_pubonly_map.py`);
   - optional: eval frame 0s (run1). C8 shows they add nothing.
2. SfM: SIFT (first_octave -1, 6k) -> pairs (within-clip, all frame-0 pairs, 12 random cross-clip partners) ->
   incremental mapping with the b/c pair as a fixed rig (factory c->b), which makes the map metric. 21.5 min CPU.
3. Registration to mocap, from public data only:
   - gravity = mean dense-stereo table normal (GT-free), then tilted by the GT support-plane lean (+0.30, -0.45) deg
     (C10);
   - height = GT table top 0.6012 m;
   - heading = median per-episode edge-chamfer fit over 19 public clips (A11/A13).
   Persist the map (`run3/sparse/0` + descriptor bank `bank.npz`, 0.82M x 128 uint8, 115 MB) and the registration:
   run3 -> run1 (`b2_align_run3.json`), then a13, then the C10 tilt about the work-area pivot (C13). Re-running
   A8/A13 directly on run3 would remove the run1 hop; it is not needed (0.58 mm / 0.011 deg alignment).

Per eval clip (online-capable; causal except the bridge blend and the per-clip lag/T_ac fit, which the C13
prototype runs offline over the whole clip):
1. Keyframe every 5 frames:
   - SIFT (first_octave 0) on b, c and a;
   - candidates = the 20 map images nearest the previous optical axis (start: the mean public axis);
   - Lowe 0.8 vs the best different 3D point;
   - generalized rig PnP (c->b factory, 6 px, LO-RANSAC + refinement), plus cam_a's own PnP.
2. Keyframe acceptance (C9/C11):
   - >= 100 rig inliers AND consistent with the VO prediction from both neighbouring keyframes (< 5 mm unless the two
     predictions disagree) => trusted;
   - 30-100 inliers => used only if the VO gate agrees;
   - otherwise retry with doubled candidates, then all map images, then a VO-only bridge with a flag.
   Never join pieces by GT or reference alignment.
   As run (C13): `c1_reloc` retries with doubled candidates below 30 inliers (never triggered on eval);
   `c13_export` applies the acceptance rule and bridges rejected keyframes by VO. The all-images retry is not
   implemented.
3. Frames between keyframes: stereo VO v2 (reference-ray-exact triangulation), with a forward/backward blend between
   the bracketing trusted keyframes. 5-frame bridge error: median 0.6-3.5 mm, p95 <= 13 mm on the worst VO clips. Use
   a stride of 1-2 there, or per-frame relocalisation at ~1.1 s/frame, if mm matter.
4. Per clip: self-calibrate T_a_from_c (median over keyframes) and the a/mono lag (-n + frac, with one optional
   changepoint for frame drops). cam_a pose at its own capture time = T_ac x c(t + lag(t)).
5. Outputs per frame:
   - T_mocap_from_cam for c (mono time base) and a (colour time base);
   - gravity = mocap +z (C10-corrected);
   - table height (per-clip stereo);
   - W = heading of cam_a;
   - quality flags: inliers, gate verdict, bridge length, c-only vs rig gap, VO-map divergence.
6. Consumers: object poses estimated in any camera frame are composed with T_mocap_from_cam(t) of THAT camera's
   capture time, so world trajectories carry no camera drift. Physics gets gravity and table support; note 11's
   priors get W.
7. Implementation as run (C13, all reading no GT): `c13_batch.sh run3/sparse/0 5 r3s5 <eps>` (c1_reloc) and
   `c3_vo_batch.sh` (VO v2) -> `c13_to_run1.py` -> `c2_stats.py` (lag) -> `c13_export.py` (gate, bridge, lag,
   T_ac, registration) -> `c6_tracks_v2/e*.json`. This is a research prototype in `work/18`, not SlamDunk code.

Monitors (GT-free):
- table-plane tilt in mocap every N frames (> 1.5 deg flags a bad pose or plane);
- rig vs cam_a consensus after lag (> 0.2 deg flags sync or pose trouble);
- keyframe inliers and the C9 gate rate (> 2 % flags an unusual clip).

## Expected AUC gain via the error budget (note 02; C5)  [V simulation, E transfer]
- Note 02: a 5 cm common linear drift costs 0.20 AUC on its own. Removing drift is the largest leave-one-out gain in
  both combined scenarios: +0.040 for "careful stereo" (2 cm drift) and +0.135 for "sloppy" (5 cm). Note 16 ranks
  world drift 4th.
- C5 replays the camera drift actually measured on the 20 eval clips through public GT with the kit's functions.
  Board gains: +0.10 vs that factory-extrinsic VO (+0.24 on e5, +0.13-0.14 on e1/e6/e35, +0.12 on e32, ~0 on 8
  benign clips), +0.01 vs a 3x better VO, and +0.42 vs a 3x worse tracker.
- Map noise: iid 0.015 deg + 0.7 mm per axis, and 0.2 % glitches of < 1 cm. Both sit inside the 1 cm AUC dead
  zone, so the camera term is ~0 whatever object estimator is used.
- Indirect value, not in the AUC number [E]: W for note 11's priors, gravity/height for the rest and tilt snaps and
  physics, per-clip lag calibration (in ep 21, whose lag is -2.15 frames, the uncompensated rig track has a 1.0 cm
  median GT edge residual and a fixed -1.15 still costs 0.35 deg), and frame-drop detection.

## Risks and limits (stage C view)
- Dynamic occluders. An operator stands at the left of every b/c view, and hands/objects fill the lower centre.
  - Measured (C11): lower 67 % masked => 519 median inliers, ~2 mm; left half masked => 378, ~1.5 mm.
  - The dangerous case is a large occluder right in front of the cameras: 50 % central => 209 inliers, 1.4 mm
    median / 9 mm max; 75 % => 30-64 inliers, up to 44 mm; 90 % => failure. The acceptance rule and the VO bridge
    cover it.
  - Not observed in any eval clip (min 554 inliers on run1, 500 on run3).
- Lighting and appearance.
  - Global gamma 0.6/1.6 and 30 % exposure + noise are harmless (C12).
  - Per-clip median rig inliers (636-899) do not decline over the recording order (Spearman vs episode number +0.36,
    p 0.12; lowest in e3-e8).
  - Local lighting changes (lamps, shadows, sunlight) and rearranged furniture are untested; a changed room would
    need a map refresh [H].
- Head pose: validated up to 57.8 deg pitch on eval (>= 689 inliers there). Looking straight down at the table
  (> ~65 deg) is untested. [H] It is probably still fine: with the lower 67 % masked, the upper third of the
  normal view alone still gave 519 median inliers. A steeper view, though, shifts the image down rather than masking
  it.
- Keyframe glitches (C9, C13): 0.1-0.2 % of keyframes, 7-11 mm, at normal inlier counts. Inlier count cannot catch them;
  the VO gate does.
- Per-session b/c extrinsic change (note 20): costs the map ~0.1 deg (constant), and is the main source of VO drift.
- Time sync: cam_a lags are measured per clip. A frame drop with no head motion around it would leave the
  changepoint undetermined, but then there is also little pose change.
- Registration:
  - heading 0.58 deg rms per episode (CV);
  - gravity ~0.3 deg per-frame consistency; absolute vs the GT world ~0.5 deg after the C10 correction (a13 alone
    ~0.7 deg, B17/B19/C10);
  - height ~2-3 mm (+3..5 mm in late sessions).
  All of these matter only for physics and absolute priors; the scorer absorbs constant offsets.
- Policy: the default map uses public frames only (C8). Eval videos are only processed automatically at inference.
- Compute: CPU only, ~0.3 s/frame; pycolmap 4.2.1 and opencv 5.0.0 pinned in `venv18`. The keyframe SIFT
  dominates.

## Stage A bottom line
1. [V] One pycolmap SfM model (CPU, 21 min) holds the room. It is built from 585 undistorted images: every 1.5 s of
   all 19 local public clips (a/b/c) plus the a/b/c frame 0 of all 20 eval clips.
   - Every image registered: 29.9k points, 1.11 px mean reprojection error, >= 586 map points per image (eval
     frame-0 min 901 on cam_a).
   - Cross-session matching is easy: every sampled pair has hundreds of inliers.
   - The geometry is low-parallax (one seat, few-cm head motion). Depth comes from the b/c rig and in-clip head
     motion.
2. [V] Metric scale comes from the fixed b/c rig (7.55 cm factory extrinsic). Independent checks:
   - free cam_a vs cam_b: 3.81 vs 3.74 cm, lateral component 0.5 %, rotation vs calibration 0.33 deg;
   - per-frame SGBM stereo depth vs map depth at 69k points: ratio 0.993-1.006 at every depth from 0.3 to 3 m.
3. [V] Gravity: the map's sparse table-point plane is biased by ~2 deg (only a far-edge band is unmasked), so it is
   NOT used.
   - Instead, the dense b/c stereo table plane is measured per frame and brought into the map. The 193 frames agree
     to 0.32 deg median; per session to 0.17 deg.
   - That plane is within 0.7 deg of the map floor.
   - Public GT shows the table is level in mocap to 0.4 deg (a4).
   - => the per-frame camera-vs-gravity CONSISTENCY from map relocalisation is ~0.3 deg. The absolute error vs the GT
     world is ~0.7 deg for a13 and ~0.5 deg after the C10 correction (B17/B19/C10).
4. [V] Height: the table plane is mapped to the GT table top (0.6012 m). Per-episode GT-edge fits confirm it:
   dz = +0.2..+0.3 cm median, sd 0.3-0.4 cm over 19 sessions.
5. [V] Within-clip accuracy on the map frames:
   - public GT objects are projected with map poses plus ONE rigid offset per session (needed because the dataset
     re-centres x,y per episode);
   - residual: median 0.2-0.3 cm, p90 1.3 cm over 175 frames / 19 clips, with no drift;
   - caveat: these frames built the map; new-frame relocalisation is stage B.
6. [V/E] Heading (W):
   - The A8 map W agrees with note 11's W table to 0.2 deg sd. It inherits note 11's ~1.2-1.5 deg LOO limit
     because both use the same 4 frame-0 fits.
   - Two independent multi-frame refits find that those fits carry a roll bias (~2.2 deg) that leaked into their
     heading. With gravity fixed by stereo, the best heading is +2.24 deg (A11 edge chamfer, 19 eps, sd 0.52) and
     +1.97 deg (A12 note-11 IoU machinery, 6 eps).
   - Refined W = note 11 W + ~2.2 deg (`a13_registration_refined.json`) [E: ~0.5 deg; held-out test done in B8: within ±0.7 deg on 3 held-out sessions, 10/9 CV 0.58 deg rms].
   - Scoring impact is small: cup anchors are flat within ±5 deg.
7. Consequences for DIG 17/18 next stages [E]:
   - The room map can deliver drift-free head poses in a gravity-aligned, metric, mocap-yawed frame for all frames
     where enough room is visible.
   - The open question is coverage when the head looks down at the table and hands/objects fill the view. The b/c
     wide-FOV mono cameras (more room visible; 1.5-2k map points each) should be the relocalisation sensors, with
     cam_a tied in through its calibrated extrinsic.

## Stage B bottom line (relocalise every 20 fps frame; held-out validation)
1. [V] Coverage 100 %. All 694 frames of public 26, 27 and 31 (20 fps, 8-14.5 s) were localised against a
   HELD-OUT map (`run2`: those sessions' frames removed except frame 0, as for eval clips).
   - b/c rig: >= 584 inliers per frame. cam_a own PnP: >= 210.
   - No failure from hand occlusion or motion blur (inliers barely track blur): the room above the table stays
     visible.
   - Frames with a GT residual > 1 cm (1-4 %) were inspected; all are metric artifacts (pot or hand covering
     the rack edges), not pose errors (B7).
2. [V] Accuracy, from the cam_a projection of static GT objects (rack + pre-onset objects) on every frame:
   - median 0.11-0.13 cm, p90 0.28-0.42 cm, the same as the bundle-adjusted map frames (0.11-0.19 cm);
   - flat over each clip (no drift);
   - truly held-out poses vs run1 BA poses: ~2 mm / 0.02-0.03 deg median (max 4 mm / 0.07 deg);
   - per-frame noise (increments vs VO): p90 0.016-0.022 deg, 0.7-0.8 mm.
3. [V] Frame-to-frame stereo VO, correctly implemented (see the DLT-bias bug in B3), is as smooth as the map but
   drifts ~1 mm/s and ~0.05 deg/s: 15 mm / 0.77 deg at 14.5 s. Its GT residual is 0.24-0.45 cm median, rising
   to 0.55 cm in the last third of ep 31. The map gives drift-free, absolute (gravity, height, W) poses.
4. [V] Runtime ~1.0-1.1 s per frame on CPU: pycolmap SIFT on a/b/c is 2/3 of it, matching 0.2 s, PnP 0.05 s.
   Keyframes every 10 frames + VO reproduce per-frame relocalisation to < 2.5 mm / 0.06 deg (p95) at ~0.18 s per
   frame. All 20 eval clips (~5k frames [E]) need ~20 CPU-min with keyframes, or ~1.5 CPU-h (~30 min wall
   with 3-4 processes) per frame.
5. [V] Factory a<-c extrinsic is off by 0.25-0.29 deg and ~0.8 cm along the optical axis. Self-calibrate it from
   the map (automatic, consistent across clips).
6. [V measurement, E meaning] TIMING:
   - cam_a frame t is captured ~1.15 frames (~57 ms) BEFORE the mono frame with the same index. This is
     constant within a clip: compensating it cuts a<-c rotation scatter 10x. It is not the same in every clip:
     ep 21 is ~2.15 (item 11).
   - Mocap GT at index t matches the cam_a image at ~t+1.4 and the mono image at ~t+0.55 (moving-object chamfer,
     3 eps).
   - Implication: ~1.4-3.5 cm ADD bias during carries for a cam_a-based pipeline unless predictions are
     time-shifted. This contradicts "match frames by frame_index" at the sub-100 ms level, and needs D19
     confirmation.
7. [V] Falsifier from stage A ("residual on unseen frames > ~1 cm median or head-down coverage < ~80 %"): NOT met
   on these clips (0.11-0.18 cm median, 100 %). The map alone suffices; VO is only a speed bridge.
   - Held-out heading: the a13 registration is within ±0.7 deg on all 3 held-out sessions.
   - 10/9 split CV of per-episode headings gives 0.58 deg rms.
8. Scope [E]: 3 clips, 2 tasks (dish rack), head pitch 41-55 deg. That matches the 38-55 deg range of all 39
   sessions' map frames, so eval clips are probably inside the validated envelope. Stage C must measure it.
9. [V] Re-run additions (B11-B19, 2026-10-07 morning): six public clips now, five tasks (0 pot/lid, 12 cup + rack,
   21 water can + cup, 26/27 pot + rack, 31 sweeper + rack), 1,434 frames at 20 fps.
   - Coverage 100 % for rig and cam_a. Rig >= 584 inliers.
   - cam_a dips to 112 inliers only in ep 21's 40 deg/s head turn with motion blur, still ~4x the floor.
   - cam_a GT edge residual 0.10-0.16 cm median on every clip.
   - Runtime 0.96-1.22 s per frame (median).
10. [V] Independent per-frame check against note 17's marker-registered cameras (VO + drift knots fitted to GT
    marker detections), after one rigid transform per clip:
    - 2.0-4.7 mm and 0.06-0.18 deg median on 5 clips;
    - worst in the fast turn (ep 21 f20-32: 11.6 mm / 0.21 deg);
    - no growth over the clip, except ep 0's last third (7 mm), where VO-type drift is the likely source.
    The map poses reproduce note 17's rack marker detections as well as cameras fitted to them (ep 26: 1.37 vs 1.74
    px median).
11. [V] The a/mono lag varies by clip: ep 21 is -2.15 frames, against -1.10..-1.20 elsewhere. Self-calibrate it per
    clip; a fixed -1.15 costs 0.35 deg there.
12. [V] Frame-to-frame stereo VO drifts 5-35 mm over 8-19 s on these clips (ep 21: 20 mm while a pitcher is lifted
    in view). The map has no growth term.
13. [V facts / E reading] Absolute tilt: a13 is ~0.5-1.5 deg off GT (best guess ~0.8 deg), in a known direction
    (B17, B19).
    - The stereo table plane in the map world is level to 0.31-0.54 deg in every clip (by construction of a13).
    - Correcting the measured stereo disparity bias moves it by only 0.28 deg.
    - But GT's own resting objects (rack support plane 0.5-0.85 deg, pot, cup) and GT contact heights (0.40 deg)
      lean toward (+x, -y). a13 should set up := that GT table normal, ~(+0.3, -0.6) deg (B19).
    - The GT marker detections on two-object clips prefer the same direction, larger: ~1.4 deg typical, up to 2.9.
      Note 17's cameras sit there.
    - GT silhouette tilt profiles (B17): 0.2 deg (ep 26) and 1.6 deg (ep 12), same direction, shallow.
    - So all GT evidence leans one way, by 0.4-2.9 deg depending on the cue. Proposed fix: re-register gravity on GT
      objects across the 19 sessions [H]. The leftover marker excess is [H: marker/scan systematics, orbit
      ambiguity].
    - Single-object marker fits are degenerate (orbit ambiguity). Not a scoring issue (one rigid alignment); it
      matters for gravity priors and physics.

## Log (appended per finding)

### A0. Inputs and conventions (2026-10-06)
- Clips local: public a 18 eps (no 44), public b/c 19 eps (0,2,11,12,13,18,21-24,26,27,31,39-44), eval a/b/c all 20. [V]
- Reference cameras: `s25_refine_native.json` holds psi/th/ph/C for public eps 12, 13, 21, 0 (best4) plus 26, 22
  (flat heading profiles). R_wc = s24_campose.Rwc(psi, th, ph): columns = (image right, image down, optical
  axis) in mocap; colour K AS GIVEN, distortion = 14-coef OpenCV rational+thin-prism+tilt. C is in the
  parquet's world coordinates for that episode. [V code read]
- [V] Dataset x,y are re-centred PER EPISODE (all-frame all-object mean = 0.0000 exactly in eps 0,2,11,12,13,21,22,26,
  39,44); z is physical. Consequence: the mocap world shares rotation (gravity + yaw) and z across episodes, but its
  x,y origin differs per episode by an unknown offset. A room map can therefore be registered to mocap in rotation,
  scale and z; x,y offsets are per-episode constants. These are harmless for the scorer (one rigid slot-0
  alignment per episode). For each reference episode the offset follows from its fitted frame-0 camera.
- Tooling: own venv `work/18/venv18` (uv; pycolmap 4.2.1 CPU wheel, opencv 5.0.0). No `timeout` binary on this
  Mac; bounded runs use `perl -e 'alarm N; exec @ARGV' ...`.

### A1. Frame pool (`a1_extract.py 30 all all`)  [V]
- Every 30th frame (1.5 s) of all 19 local public eps (a/b/c), plus frame 0 of a/b/c in all 20 eval eps:
  195 images per camera, 585 in total (`work/18/imgs/{a,b,c}/<p|e><ep>_<frame>.jpg`).
- Each image is undistorted to PINHOLE with the 14-coefficient calibration AS GIVEN, with no rotation (R=None), so
  any pose fitted to a raw frame holds for the undistorted one. cam_a is halved to 1014x760 with f=500 at the image
  centre. b/c are 1280x800 with f=420.
- The masks (`work/18/masks/`) exclude the bottom-centre table/objects/hands/own-body region:
  - a: normalised y>0.20 within |x|<0.9, or y>0.42;
  - b/c: y>0.30 within |x|<0.9, or y>0.55.
  Moving people at the left of b/c are left to RANSAC.

### A2. SfM run1 (`a2_sfm.py run1 feat,rig,pairs` / `match` / `map`)  [V]
- SIFT (CPU, max 6000 per image, masks); PINHOLE intrinsics fixed.
- The b/c pair is a COLMAP rig: c is the reference sensor and b = c->b factory extrinsic (`stereo_pairs` ego
  `left_to_right`, 7.55 cm). Rig extrinsics and intrinsics are fixed in BA, so the model is metric by construction.
  cam_a is its own single-camera rig because a/b/c sync is not assumed; it is checked afterwards against the
  calibrated a->b extrinsic.
- Pairs: 20,783 = all within-episode pairs + all frame-0 pairs (public+eval, all cams) + 12 random cross-episode
  partners per image. Matching took 1.3 min on CPU.
- Verified pairs: every pair has >= 15 inliers. Medians: cross-episode a-a 460, b-b 964, a-b 371; within-episode a-a 718.
  Cross-session room matching is therefore easy.
- The geometry is weak: 86 % of pairs are classified PLANAR_OR_PANORAMIC (6), and only 2,813 are CALIBRATED with
  enough parallax. The camera stays at one seat (head motion of a few cm, room depth 1-5 m). Depth comes mostly
  from the 7.5 cm rig baseline and from head translation within a clip.
- [V] Mapping: ONE model with ALL 390 frames / 585 images registered (175 public + 20 eval per camera), 29,900
  points, mean track length 31.7, mean reprojection error 1.11 px. Took 21 min CPU (`run1/sparse/0`,
  log `a2_run1_map.log`). Ceres reported "Matrix not positive definite" warnings during global BA, which points
  to poorly constrained low-parallax points; the result is still consistent (checks below).

### A3. Scale, planes, registration to mocap (`a3_register.py run1/sparse/0` -> `a3_register_run1.{out,json}`)  [V]
- Scale check, independent of the b/c rig constraint:
  - cam_a is not in the rig, so the free a-b distance on the same frame index is an independent check:
    - distance: median 3.81 cm vs calibrated 3.74 (+1.9 %), p10-p90 3.68-3.92;
    - lateral component: -3.76 vs -3.74 cm (0.5 %);
    - along-axis component: -0.53 cm vs -0.02 cm, which is the weakest-determined direction;
    - relative rotation vs calibrated: median 0.33 deg, p90 0.65.
  - So the map is metric to about 0.5-2 %. cam_a and the mono pair also look effectively synchronised on matching
    frame_index, at least on these 1.5 s-spaced samples.
- The point cloud has two height peaks along gravity, the floor (~1.10 m below the head) and the table top (~0.52 m
  below). The first floor RANSAC (normal prior = median image-down) locked onto a wrong slanted plane, so plane
  search now uses the reference-fit average up as the prior, within 15 deg.
  - Floor: 814 inliers, rms 5.9 mm. Table: 1,296 inliers, rms 3.4 mm.
  - Angles: floor-table 1.51 deg, table vs ref-fit average 1.78 deg, floor vs ref-fit average 2.21 deg.
  - Camera height above the floor: median 1.103 m (p10-p90 1.090-1.114). Table top above the floor: 0.579 m.
  - The head position is very repeatable across all 39 sessions: within ±1.5 cm vertically and 1.4-3.5 cm
    horizontally (sd).
- [V] GT table tilt in mocap (`a4_table_tilt_gt.py` -> `a4_table_tilt_gt.json`):
  - data: 104 on-table rest contacts in 20 public episodes (lowest scan vertices, |zmin - 0.6012| < 6 mm);
  - fit: shared slope with a per-episode intercept;
  - result: the table top is level in mocap to 0.40 deg (bootstrap p5-p95 0.21-0.89), residual 1.16 mm.
  So mocap +z = the table normal within ~0.4 deg, and the table plane is the natural gravity and height reference
  for the map. Table height is 0.6012 in every episode (intercepts 0.5995-0.6031).
- Registration, with three gravity choices and yaw = median over the refs {12, 13, 21, 0} in each case:

  | gravity from | heading LOO rms (deg) | eval W map - note 11 (mean / sd / max, deg) | refs pitch d (mean / sd) | refs roll d (mean / sd) | t_z: table plane vs refs' C_z |
  |---|---|---|---|---|---|
  | table plane | 1.47 | +0.01 / 0.20 / 0.40 | +0.26 / 2.88 | +2.35 / 1.17 | +0.4 mm |
  | floor plane | 1.36 | -0.01 / 0.18 / 0.47 | +1.73 / 2.87 | +1.85 / 1.19 | -8.8 mm |
  | refs' rotation average | 1.18 | -0.21 / 0.15 / 0.52 | 0 / 2.87 | 0 / 1.13 | +3.4 mm |

  - Eval W: all 20 eval frame-0s localise in the one map. The map-derived camera heading agrees with note 11's
    pure-rotation W table to 0.2 deg sd (max 0.5). Both use the same 4 GT fits, so this checks map coherence across
    the 39 sessions, not absolute accuracy. Absolute heading accuracy stays limited by the GT fits (LOO 1.2-1.5 deg).
  - Height: with table gravity, the table plane mapped to 0.6012 and the refs' fitted C_z agree to 0.4 mm in the
    median (per-ref -2.6..+3.0 cm). Table-based z registration is preferred (3.4 mm plane rms vs ~2 cm fit noise).
    The floor then sits at mocap z = +0.043 m (table gravity) / +0.022 (floor gravity), so the mocap origin is
    ~2-4 cm above the visible floor plane, or the floor is uneven [E].
  - Open discrepancy: with table gravity the refs' fitted roll is lower than the map by +2.35 ± 1.17 deg (n=4, ~4
    SE). Either the map is bent so camera-vs-plane angles are off by ~2 deg, or the silhouette fits have a roll
    bias. Next: an arbiter that uses no map, the b/c stereo table plane per frame.

### A5. Map-free gravity arbiter: per-frame b/c stereo table plane (`a5_stereo_table.py` -> `a5_stereo_table.{out,json}`)  [V]
- Method: the undistorted c|b pair is rectified with the factory extrinsic, then SGBM. The table plane comes from a
  RANSAC fit (4 mm threshold) in the lower-centre region and is expressed in the cam_c frame.
  - Result: 193/195 frames, 20-60k inliers each, 2.0 mm rms, half-split stability 0.1-0.3 deg.
  - Sparse SIFT stereo on the table failed first: the wood grain gives only 25-110 points.
- Stereo vs map: the table normal differs CONSISTENTLY by 2.09 deg median.
  - About cam-x (pitch): -2.05 deg, sd 0.36. About cam-z (roll): +0.27, sd 0.49.
  - Identical on public (n=173) and eval frame-0s (n=20).
  - So one systematic ~2 deg pitch offset exists between the per-frame stereo planes and the map's
    camera-vs-table geometry; it is not session noise.
- Stereo vs GT silhouette fits, by ref:
  - pitch: +0.9 (0), -6.6 (12), -3.1 (13), -0.6 (21), +0.5 (22), +5.8 (26);
  - roll: -4.9, -1.7, -1.4, -2.1, -5.7, -0.4.
  The fits are too noisy (pitch sd ~3-4 deg) to say which side the 2 deg error is on.
- Competing explanations:
  - (a) A small factory c->b yaw error or disparity offset: ~0.8 px gives ~2 deg plane tilt at 0.45-0.9 m; this
    biases stereo planes and depth.
  - (b) Map bending in low-parallax SfM.
  - (c) The table normal in the map is biased by where the table points are (far edge only, because the near
    table is masked).
  Tests next: a depth ratio stereo/map vs depth (a disparity offset predicts a ratio linear in Z), and a rig-refined
  BA (does freeing c->b remove the offset?).

### A6/A7. Resolution of the 2 deg offset  [V]
- A6 (`a6_depth_ratio.py run1/sparse/0 3` -> `a6_depth_ratio.{out,json}`): at 69k map points seen in 65 c images,
  SGBM stereo disparity vs map-predicted disparity fits as d_stereo = 1.0020 d_map - 0.05 px (MAD 0.8 px).
  - Depth ratio stereo/map per depth bin 0.3-3 m: 0.993-1.006, with no trend in Z.
  - So there is no disparity offset or scale mismatch between per-frame stereo and the map. Explanation (a) is out.
- A7 (`a7_stereo_normals_in_map.py` -> `.out/.json`): each frame's stereo table normal was brought into the map
  with that frame's map pose.
  - The 193 normals agree: median spread 0.32 deg (p90 0.73); per-session means within 0.17 deg (max 0.62).
  - Public and eval frames agree to 0.1 deg.
  - The mean stereo table normal is 0.71 deg from the map FLOOR plane and 2.13 deg from the map's sparse TABLE
    plane.
  - => (c): the map's sparse table-point plane is biased. Its points are only a far-edge band (the near table is
    masked), possibly rim/edge or object points. Neither the map poses nor the stereo are biased.
  - The real table top (dense stereo) is within 0.7 deg of parallel to the floor. Both are level, consistent with
    GT (table level in mocap to 0.4 deg).
  - Gravity for the map := the mean dense-stereo table normal (A8 below).
- Side result [V]: map camera poses x per-frame dense stereo agree on gravity to ~0.3 deg per frame across all 39
  sessions. This is a first sign that map relocalisation yields per-frame gravity at the ~0.3 deg level.

### A8. Final registration (`a8_register_final.py run1/sparse/0 a5_stereo_table.json 12,13,21,0` -> `a8_registration.json`, `.out`)  [V]
- Transform: X_mocap = R_mocap_from_map X_map + [dx_ep, dy_ep, t_z], with scale 1 (metric rig).
  - Gravity: the mean dense-stereo table normal (193 frames).
  - Yaw: median over refs {12, 13, 21, 0} of psi_fit - psi_map; yaw0 = 97.45 deg.
  - Height: t_z = 1.1251 m, from the median stereo table-plane offset (sd 3.1 mm over 193 frames) mapped to the
    GT table top 0.6012.
  - The json also holds the camera pose (R_wc, C with dx=dy=0, psi/th/ph) of all 585 map images in this frame.
- Heading LOO over refs: +0.97 / +1.56 / -0.97 / -1.86 deg (rms 1.39). This is the same level as note 11 (1.18 /
  1.55) and is limited by the GT silhouette fits.
- Eval frame-0 W from the map minus note 11's W table: mean +0.04, sd 0.22, max 0.63 deg. The two methods agree.
- Eval frame-0 cam_a in mocap:
  - pitch: 38.9-54.2 deg;
  - roll: 1.7-10.6 deg;
  - height: 1.101-1.137 m;
  - stereo camera height above the table: 0.529 m median, p10-p90 0.510-0.540.
- Check vs the GT fits at the refs (fit values are noisy):
  - pitch d +2.39 ± 2.88 deg;
  - roll d +2.19 ± 1.21 deg;
  - C_z d +1.1 ± 2.1 cm.
  The ~2.2 deg roll offset also shows map-free (a5: stereo table normal vs fit gravity, roll-like component -4.9 /
  -1.7 / -1.4 / -2.1 deg). The table is level in mocap (a4, 0.4 deg), and the dense-stereo table agrees with the
  map floor to 0.7 deg, so the bias is attributed to the silhouette fits' roll [E]. Heading is unaffected, because
  roll and pitch errors do not move the optical-axis azimuth. This confirms note 11's advice to take gravity from
  the table, not from the transfer.

### A9. Registration validated on non-frame-0 frames by projecting public GT objects (`a9_overlay_check.py`)
- First pass (dx,dy from the frame-0 fit's C; output superseded):
  - Projecting GT objects with the map poses of frames 0..360 (every 30th) of the refs gives a 2-D misalignment
    vs Canny edges that is nearly CONSTANT within each episode. Examples:
    - ep 13: (+2..+10, +20..+28) px;
    - ep 0: (-14..-30, -12..+14) px;
    - ep 21: (~0, +8) px on 5/7 frames;
    - ep 12 / 22 / 26: hit the ±30 px search bound.
  - This shows up even at frame 0, where it is an offset: the fit's C was estimated jointly with the fit's
    (pitch/roll-biased) rotation, so keeping C while swapping in the map rotation shifts the projection by about
    depth x angle (0.53 m x 4 deg ~ 3.7 cm).
  - Fix: fit one 3-D translation offset per episode from all its frames, then measure the per-frame residual.
    The residual is the drift/jitter test.
- Second pass: done; results two bullets below (all 19 public eps; per-episode (dx,dy,dz) by grid + Nelder-Mead on the edge chamfer;
  per-frame residual = best 2-D shift within ±20 px at the fitted offset).
- [V] Map support per image (`run1/sparse/0`): map points observed per image.
  - cam_a: median 1,197, min 586 (p24 f150); eval frame-0 min 901 (ev35).
  - b: median 1,979 / eval min 1,527. c: median 1,740 / eval min 1,315.
  - Point track length median 5, point reprojection error median 1.0 px.
- [V] Second pass (`a9_overlay_check.py <19 public eps>` -> `a9_overlay_check.{out,json}`, overlays `ov/`): one
  (dx,dy,dz) per episode is fitted on the edge chamfer, with rotation fixed to the A8 registration, over all 175
  public map frames (every 1.5 s, all 19 public eps).
  - Per-frame residual (best extra 2-D shift, converted to cm at object depth): median 0.33 cm, p90 1.36 cm.
    The largest values (1.5-2.4 cm) are frames with hand occlusion, motion blur or an object in flight.
    Chamfer median 3.07 px.
  - Per-episode dz: median +0.3 cm, sd 0.3 cm. The table-based t_z is right to ~3 mm in every session.
  - Per-episode dx 0.286-0.342 m, dy -0.064..+0.023 m. This is the dataset's per-episode re-centring: the objects'
    mean location differs by task. Frame-0 fit C differed from these by up to 5.5 cm, which explains the first
    pass.
  - Overlays (e.g. `ov_montage1.jpg`: ep 12 f0/f90 with a cup in flight, ep 13 f60, ep 21 f60) show the rack and
    cups outlined correctly.
  - Meaning: with one rigid offset per session, the map's camera poses of the MAPPING frames place GT objects to
    ~3 mm median / 1.4 cm p90 over 6-18 s clips, with no visible drift.
  - Caveat: these frames were used to BUILD the map. New-frame relocalisation (stage B) still needs to be measured.

### A10. Independent yaw check: per-episode 4-DoF fit (dx,dy,dz,dpsi) on GT edges (`a10_yaw_per_episode.py` -> `.out/.json`, `ov10/`)  [V, E for interpretation]
- Setup: the A9 translation is the start, then Nelder-Mead over (dx, dy, dz, dpsi). dpsi rotates the episode's map
  cameras about the vertical through their mean centre.
- Residual: per-frame median 0.22 cm, p90 1.31; dz median +0.2 cm, sd 0.4.
- The per-episode yaw correction dpsi is SYSTEMATICALLY positive: median +1.69 deg, mean +1.67, sd 0.77 (n=19).
  - By episode: 12 +2.5, 13 +2.4, 21 +1.5, 0 +1.5, 22 +1.7, 26 +1.6, 2 +1.7, 11 +0.0, 18 +2.2, 23 +2.2, 24 +2.4,
    27 +2.0, 31 +2.7, 39 +0.0, 40 +0.6, 41 +2.2, 42 +2.1, 43 +1.7, 44 +0.7.
  - The 4 reference episodes give +1.5..+2.5 on their own clips. The multi-frame edge fit and the single frame-0
    silhouette fits therefore disagree for the same sessions.
- Candidate explanation [H]: the frame-0 fits' roll bias (~-2.2 deg, A8) coupled into their heading. With objects
  ~0.3 f below the image centre and a pitch of ~40 deg, roll and heading/lateral shift trade off.
- Competing explanation: the chamfer fit's yaw is degenerate with lateral translation. Pan vs lateral shift at
  near-equal depth: 1.7 deg ~ 1.5 cm at 0.5 m.
- Test: a yaw profile with translation re-fitted at each fixed yaw (done, next bullet).
- [V] Yaw profile (`a11_yaw_profile.py` -> `a11_yaw_profile.{out,json}`): per episode, fixed dpsi in -2..+5 deg
  (1-deg grid), translation re-fitted by Nelder-Mead at each yaw, then a parabola around the minimum.
  - The profiles are convex with a clear minimum in 15/19 episodes. Weak ones: ep 11 (two spin-symmetric cups,
    curvature 0.025), 39, 40, 41 (~0.05).
  - Best yaw correction: median +2.24 deg, mean +2.15, sd 0.52 (n=19). SE ~0.12, so it is not translation
    degeneracy.
  - The refs' own clips: 12 +2.54, 13 +2.34, 21 +1.99, 0 +1.76.
  - Interpretation [E]: A8 / note 11 headings (and so note 11's W table) are probably ~2.2 deg too small, and the
    likely cause is the frame-0 silhouette fits' heading (coupled to their ~2.2 deg roll bias).
  - Impact is small for scoring: cup anchors are flat within ±5 deg (note 11: 0.871 -> ~0.86 at 2-3 deg) and
    two-fold branches are unaffected. A map registration refined over 19 eps x ~10 frames would replace 4
    single-frame fits.
  - Cross-check (done in A12): an IoU/GrabCut cost (note 11's machinery) with gravity from the map, on the 4 ref
    frame-0s.

### A12. Cross-check with note 11's own IoU/GrabCut machinery (`a12_iou_check.py` -> `a12_iou_check.{out,json}`)  [V]
- Setup: for each ref frame-0 (raw cam_a, K as given), the GrabCut mask is seeded by the s25 fit rendering (as in
  s25; this biases toward d=0). Pitch/roll are fixed to the map's gravity-correct values, the heading is the A8
  heading + d, and the camera centre is re-fitted by IoU.
- Best d by parabola, with peak IoU in brackets:

  | ep | best d (deg) | peak IoU |
  |---|---|---|
  | 12 | +1.42 | 0.933 |
  | 13 | +2.20 | 0.958 |
  | 21 | +2.01 | 0.879 |
  | 0 | +1.20 | 0.951 |
  | 22 | +1.93 | 0.880 |
  | 26 | +3.07 | 0.928 |

  Mean +1.97, sd 0.60. The free-gravity s25 fits reach IoU 0.951-0.969 on 12/13/0 by trading pitch/roll.
- Two different costs agree (edge chamfer over 19 eps x ~10 frames; IoU on 6 frame-0s): once gravity is right, the
  heading is ~+2 deg from note 11's.

### A13. Refined registration (`a13_refine_yaw.py` -> `a13_registration_refined.json`, `.out`)  [V arithmetic, E accuracy]
- yaw0 is corrected by +2.24 deg, the A11 median (n=19; A12 mean +1.97, n=6).
- Refined eval W = note 11 W + 2.0..2.9 deg:

  | ev | W (deg) | ev | W (deg) | ev | W (deg) | ev | W (deg) |
  |---|---|---|---|---|---|---|---|
  | 1 | 186.5 | 10 | 182.4 | 20 | 180.8 | 33 | 179.4 |
  | 3 | 181.6 | 14 | 184.0 | 25 | 184.6 | 35 | 176.2 |
  | 5 | 181.5 | 15 | 183.0 | 28 | 182.0 | 36 | 180.1 |
  | 6 | 180.6 | 16 | 185.0 | 30 | 185.5 | 37 | 178.2 |
  | 8 | 186.3 | 19 | 181.7 | 32 | 187.5 | 38 | 179.6 |

- Estimated absolute heading error after refinement [E]: ~0.5 deg. This is the per-episode sd of A11 and the
  spread between the two costs. It is not validated on held-out data. A leave-episodes-out test (fit the yaw on 10
  public eps, test on 9) is the stage-B falsification test.
- For note 11's priors, y_ours = y_m - W shifts by -2.2 deg. This is within the flat region of every anchor
  budget, so only a tiny score change is expected [E].

## Stage A limitations
- Validation is in-sample for poses: every validated frame (A9-A12) was a mapping frame. Not yet measured:
  relocalising unseen frames (all 20 fps frames, including head-down/occluded views), and the latency and
  coverage of that relocalisation.
- Eval clips contribute only their frame 0 to the map. Per-episode accuracy on eval clips is projected from public
  sessions [E]. Same room and seat: eval frame-0 heads sit within the public spread (height 1.10-1.14 m, pitch
  39-54 deg).
- Heading refinement (A11/A12) uses public GT edges/silhouettes with chamfer/IoU costs that hands and clutter can
  bias. Two costs agree to ~0.3 deg, but there is no held-out test yet. Absolute yaw matters only for world priors,
  because the scorer aligns one rigid transform.
- The map table plane (sparse) is biased. Use the dense-stereo table normal. The floor is level to ~0.7 deg vs the
  table, so it is a secondary check only.
- Per-episode x,y offsets: the dataset re-centres x,y, so they are unknowable for eval and irrelevant to the score.
  In public they are fitted only for validation.
- a/b/c sync: consistent with frame_index matching on the 1.5 s samples (a-b relative rotation 0.33 deg median,
  p90 0.65). This was not tested at the 20 fps level during fast head motion.
- Ceres reported non-positive-definite warnings in global BA (low-parallax points). Reprojection and the checks are
  fine, but the far-point depths (>3 m) are weak. They do not matter for rotation and matter little for
  translation, which the floor and table pin.
- No external literature/web review in this stage. The design rests on standard SfM practice:
  - COLMAP incremental mapping with rig constraints (COLMAP >= 3.12 rig support; pycolmap 4.2.1 wheel used);
  - OpenCV 5.0.0 SGBM stereo;
  - note 11's GT-silhouette fits.
  A focused review (relocalisation pipelines such as hloc/COLMAP image registration, and map-based localisation
  under occlusion) belongs to stage B.

## Stage A artifacts (`/Users/aebatirel/Documents/Code/v2d-research/work/18/`)
- Environment: `venv18/` (uv; pycolmap 4.2.1, opencv 5.0.0) for COLMAP steps. The shared venv
  (`../../venv/bin/python`) runs the GT overlay scripts a4, a9-a13 (they import `work/11/c11.py`, `s24_campose.py`,
  `s23_mask.py`).
- `a1_extract.py` -> `imgs/{a,b,c}/*.jpg`, `masks/` (585 undistorted PINHOLE images + masks).
- `a2_sfm.py` -> `run1/db.db`, `run1/pairs.txt`, `run1/sparse/0` (THE MAP). Logs: `a2_run1_{prep,match,map}.log`.
- `a3_register.py` -> `a3_register_run1.{out,json}` (scale checks, planes, three gravity variants).
- `a3b_floor_probe.py` (point-height histogram).
- `a4_table_tilt_gt.py` -> `a4_table_tilt_gt.json` (GT table level in mocap).
- `a5_stereo_table.py` -> `a5_stereo_table.{out,json}` (per-frame dense stereo table planes).
- `a6_depth_ratio.py` -> `a6_depth_ratio.{out,json}`.
- `a7_stereo_normals_in_map.py` -> `.out/.json`.
- `a8_register_final.py` -> `a8_registration.{out,json}`: transform plus all 585 camera poses. Convention:
  X_mocap = R X_map + [dx_ep, dy_ep, t_z]; R_wc columns = right/down/forward.
- `a9_overlay_check.py` -> `a9_overlay_check.{out,json}`, `ov/`, `ov_montage1.jpg`.
- `a10_yaw_per_episode.py` -> `.out/.json`, `ov10/`.
- `a11_yaw_profile.py` -> `a11_yaw_profile.{out,json}`.
- `a12_iou_check.py` -> `a12_iou_check.{out,json}`.
- `a13_refine_yaw.py` -> `a13_registration_refined.{json}`, `a13_refine_yaw.out`: the registration TO USE
  (yaw +2.24 deg vs A8).
- Commands (all bounded with `perl -e 'alarm N; exec @ARGV'`):
  - `venv18/bin/python a1_extract.py 30 all all`
  - `venv18/bin/python a2_sfm.py run1 feat,rig,pairs` then `... run1 match` then `... run1 map` (21 min)
  - `venv18/bin/python a3_register.py run1/sparse/0`
  - `venv18/bin/python a5_stereo_table.py run1/sparse/0 a3_register_run1.json`
  - `venv18/bin/python a6_depth_ratio.py run1/sparse/0 3`
  - `venv18/bin/python a7_stereo_normals_in_map.py run1/sparse/0 a3_register_run1.json a5_stereo_table.json`
  - `venv18/bin/python a8_register_final.py run1/sparse/0 a5_stereo_table.json 12,13,21,0`
  - `../../venv/bin/python a9_overlay_check.py <eps>` (same for a10, a11, a12 with eps)
  - `../../venv/bin/python a13_refine_yaw.py`
- No downloads were made. All clips used were already local.

## Proposed stage B (as planned at the end of stage A; executed, see "Stage B log" and the bottom line)
1. Relocalise every frame (20 fps) of a set of public clips:
   - SIFT on b and c (wide FOV), matched to the k nearest map images by pose/time;
   - generalized-PnP on the b/c rig, with cam_a through its extrinsic.
   Measure:
   - coverage (fraction localised);
   - inliers;
   - jitter (frame-to-frame, vs a smoothed track);
   - latency per frame;
   - GT-object reprojection residual on NON-map frames (A9 metric).
   Falsifier: if the residual on unseen frames is > ~1 cm median, or coverage on head-down frames is < ~80 %, the
   map alone is not enough, and a VO bridge is needed.
2. Held-out yaw test:
   - refit the A11 yaw on 10 public sessions and predict the other 9;
   - also on a fresh map built WITHOUT the test sessions, to test map persistence without in-map frames.
3. Then run eval clips (automatic relocalisation only): coverage and jitter per eval episode, and the gravity
   per frame.

## Stage B log (relocalise every frame; appended per finding)

### B0. Setup (2026-10-07)
- Test sessions: public 26, 27 (Pan_In_Dishrack) and 31 (Brush_Dishrack). The dish rack is static in mocap for the
  whole clip (GT max displacement < 0.5 cm), and the moving object is static before its onset (26: f52, 27: f26,
  31: f47). Clip lengths 158 / 246 / 290 frames at 20 fps. [V]
- Held-out map (completed 00:50; see "B0 result"): `b0_heldout_map.py run2 26,27,31` reuses run1's features and matches
  (copied `run1/db.db`). It restricts the incremental mapper (`IncrementalPipelineOptions.image_names`) to all
  images EXCEPT the test sessions' non-zero frames, so only their frame 0 stays in the map, as for eval clips.
  Output `work/18/run2/sparse/`, log `b0_run2_map.log`, pid in `b0.pid`. Command:
  `nohup perl -e 'alarm 4800; exec @ARGV' venv18/bin/python b0_heldout_map.py run2 26,27,31 > b0_run2_map.log 2>&1 &`

### B1. Relocaliser design (`b1_reloc.py`; reads no GT)  [V code, V timing]
- Focused review (light, fits the blocker):
  - hloc (`cvg/Hierarchical-Localization`, `hloc/localize_sfm.py`, master as fetched 2026-10-07) localises a query
    from the 3D-observing keypoints of retrieved DB images, deduplicates 3D points, then calls
    `pycolmap.estimate_and_refine_absolute_pose`. Default RANSAC max_error is 12 px, with optional covisibility
    clustering and no rig model.
  - pycolmap 4.2.1 (local docstrings) also exposes `estimate_and_refine_generalized_absolute_pose` (LO-RANSAC +
    refinement over a multi-camera rig), which is used here for the c/b pair.
  - The idea of reusing a persistent multi-session map for drift-free relocalisation is standard. Examples:
    ORB-SLAM3 Atlas (Campos et al., T-RO 2021) and COLMAP image registration. Those two are cited from memory, not
    re-read.
  - The new element here is registering the map to the mocap world (stage A) so relocalised poses ARE mocap poses.
- Pipeline per 20 fps frame t (a/b/c matched by frame index):
  - undistort exactly as a1;
  - pycolmap SIFT with first_octave 0 and peak 0.004: ~2.1k features per b/c image in 0.21 s, versus 7.4k in
    0.86 s for the map's first_octave -1 setting;
  - candidate map images: the 20 b/c images (12 for cam_a) whose optical axis is closest to the previous
    successful pose. The first frame uses the clip's frame-0 map image, which exists for eval clips too.
  - bank = their 3D-observing descriptors (uint8 = 512 x RootSIFT, same as the DB). Matching is cv2 BF kNN-6 with
    a Lowe ratio of 0.8 against the best DIFFERENT 3D point, keeping one query per 3D point.
  - b/c: generalized PnP of the c-referenced rig (c->b factory extrinsic, 6 px);
  - cam_a: its own single-camera PnP (6 px);
  - success = >= 30 inliers. On failure the candidate set is retried at double size.
- Smoke test (run1, own session's non-zero frames excluded, ep 27, 5 frames): rig 700-950 inliers, cam_a 310-560.
  first_octave -1 doubles the inliers (1.8-2.1k), but SIFT costs 2.5 s per frame for 3 images.
- Matching speed: numpy argpartition took 0.7 s per frame and cv2 BFMatcher kNN takes 0.1 s.

### B3. Frame-to-frame stereo VO baseline (`b3_vo.py <split> <ep> <out> [mask]`; no map, no GT)  [V]
- Method:
  - GFTT corners in c_t, then stereo KLT c->b with a forward-backward check (< 0.7 px);
  - triangulation with the factory extrinsic (depth 0.15-8 m, b reprojection < 1 px);
  - temporal KLT c_t -> c_{t+1};
  - EPnP RANSAC (1.5 px) + LM, chained as c_from_c0.
  - The validator anchors the chain to the relocalised frame-0 pose.
- Runs: 26 / 27 / 31 have 158 / 246 / 290 frames with zero PnP failures. Median inliers are 857 / 726 / 493
  unmasked and 814 / 631 / 429 with the bottom-centre mask (`b3/vo_p*.json`, `b3/vom_p*.json`).
- Cost: ~13 ms per temporal step, ~70-80 ms per frame including decode and stereo.
- [V] VO bug found and fixed (my implementation, not inherent VO drift):
  - v1 (`b3_vo_v1_dltbias.py`, outputs `b3/v1/`) took DLT-triangulated points, which split c/b epipolar
    inconsistency between both views. Result: a CONSTANT per-frame pitch bias of +0.058 deg/frame (sd 0.009),
    i.e. 9.3 deg / 4.7 cm drift over 158 frames on ep 26. Per-frame VO vs relocalised rotation increments
    otherwise agree (slope 1.005, corr 0.999).
  - v2 (current `b3_vo.py`, `B3_RAY_EXACT=1`) keeps the c ray exact and takes only depth from stereo. Bias:
    0.0006 deg/frame. End rotation vs map relocalisation after 158 frames: 0.13 deg unmasked, 0.05 deg masked.
  - Lesson [V]: ~0.85 px of c/b vertical inconsistency exists with the factory extrinsic. Any stereo VO here must
    use reference-ray-exact (rectified-style) triangulation.
  - v2 runs (26 / 27 / 31): 0 failures; median inliers 876 / 739 / 496 unmasked, 828 / 644 / 432 masked.

### B1 runs on run1 with own-session images excluded except frame 0 (`b1/run1lso_p{26,27,31}.{json,log}`)  [V]
- Command: `venv18/bin/python b1_reloc.py run1/sparse/0 public <ep> b1/run1lso_p<ep>.json 1 1`. The 3 clips ran in
  parallel with the run2 mapper.
- Coverage: 100 % of frames for both the rig (>= 30 inliers) and cam_a, in all three clips (158 / 246 / 290
  frames). Ep 26: rig inliers p0 / p5 / p50 = 672 / 725 / 786; cam_a 350 / 375 / 416.
- Caveat: the run1 3D points were triangulated partly from own-session images. This mode tests the matching
  restriction only; the held-out map run2 is the clean test.

### B2. GT validation of every frame, run1 with own session excluded except frame 0 (`b2_validate.py`, `b4_stats.py` -> `b4_run1lso.{out,json}`)  [V]
- Metric: the A9 GT-static-object metric on EVERY frame in cam_a.
  - Objects: the rack all clip, plus the moving object before onset-3.
  - One 3-D offset per episode and track (dataset x,y re-centring), fitted on every 10th frame.
  - Residual = best 2-D shift of the projected contour vs Canny edges, in cm at object depth.
- Tracks:
  - `rig` = b/c generalized PnP -> cam_a via the factory extrinsics;
  - `rigS` = the same with an a<-c extrinsic self-calibrated from the clip's own relocalisations (no GT);
  - `a` = cam_a's own PnP;
  - `vo` = b3 v2 chained from the frame-0 rig pose, using the rig offset;
  - `map` = run1 BA poses of the map frames (every 30th).

  | ep (frames) | coverage rig / a | GT residual median / p90 (cm): map BA | rigS | a | rig (factory ext.) | VO |
  |---|---|---|---|---|---|---|
  | 26 (158) | 100 % / 100 % | 0.19 / 0.38 | 0.18 / 0.45 | 0.13 / 0.29 | 0.41 / 0.76 | 0.51 / 0.87 |
  | 27 (246) | 100 % / 100 % | 0.13 / 0.17 | 0.18 / 0.39 | 0.25 / 0.35 | 0.17 / 0.40 | 0.40 / 0.63 |
  | 31 (290) | 100 % / 100 % | 0.11 / 0.48 | 0.15 / 0.34 | 0.11 / 0.22 | 0.15 / 0.35 | 0.24 / 0.78 |

- Map relocalisation is flat over the clip (median by thirds: rigS 0.28 / 0.18 / 0.18 (26), 0.25 / 0.18 / 0.12 (27),
  0.15 / 0.11 / 0.15 (31)). VO grows: ep 31 thirds 0.22 / 0.15 / 0.55 cm.
- Pose vs run1 BA pose at the map frames (n = 6 / 9 / 10):
  - cam_a own PnP: 1.3-2.4 mm median, 0.015-0.028 deg. This is not fully independent, because the map frame's own
    image helped triangulate the points.
  - rigS: 1.6-2.8 mm, 0.17-0.26 deg.
- Factory extrinsic error: the a<-c self-calibration is consistent across clips. Rotation is 0.25-0.29 deg off the
  factory value; translation is within 1.5 mm in x/y with +0.7-0.8 cm along the optical axis (cf. stage A a-b
  along-axis -0.5 cm). Using it cuts ep 26's rig residual from 0.41 to 0.18 cm.
- Noise, from per-frame increments vs VO (the c-camera rig and VO measure the same physical motion):
  - rig vs VO rotation increment sd 0.005-0.011 deg per axis (p90 norm 0.016-0.022 deg); translation sd 0.24-0.33
    mm (p90 0.75-0.78 mm). These bound the per-frame noise of BOTH methods. Map relocalisation is as smooth as VO
    frame-to-frame.
  - Savgol-residual "jitter" (0.3 mm / 0.07-0.08 deg rms) is the same for rig and VO, so it measures real
    high-frequency head motion, not noise.
- VO drift vs map relocalisation (rig), from frame 0:
  - 26 (8 s): 4.4 mm / 0.13 deg at the end;
  - 27 (12 s): 6.8 mm / 0.36 deg;
  - 31 (14.5 s): 14.2 mm / 0.75 deg, i.e. ~1 mm/s and ~0.05 deg/s.
  - Even well-implemented stereo VO accumulates a ~1 cm / ~0.75 deg error over a 15 s clip. The map does not.
- Failures: none. Every frame of the 694 localised with >= 613 rig inliers and >= 214 cam_a inliers (min over
  clips). Inliers barely track blur (corr -0.11..0.58).
  - The few > 1 cm GT-residual frames (1-5 % per clip; e.g. 26 f67-77, 31 f59/91/119/157) appear in ALL tracks
    at once, including VO and (31 f60) the map BA frame. That points to metric artifacts (hand/object occluding
    the rack edges) rather than pose errors. Visual check: done in B7 (confirmed occlusion artifacts).
- Runtime per frame (3 parallel clips + the run2 mapper on 14 cores): 1.7-1.8 s median, 2.3-2.7 s p90.
  SIFT on 3 images takes 1.2 s, b/c matching 0.25-0.33 s, rig PnP 0.09 s, cam_a match+PnP 0.05 s.
  Uncontended (smoke test): ~1.1 s/frame. VO: ~0.07 s/frame.

### B5. cam_a vs mono-pair time offset (`b5_sync.py` -> `b5_sync_run1lso.out`)  [V measurement; interpretation E]
- Method: compare world-frame angular increments of the relocalised cam_a track with the c track, interpolated at
  sub-frame lag tau. Rigidly attached cameras share world angular velocity, so no extrinsic is needed.
- Result: cam_a frame t matches mono frame t-1.15 / t-1.15 / t-1.20 (eps 26 / 27 / 31), i.e. the colour frame
  is ~57-60 ms EARLIER than the mono frame with the same frame_index.
  - The rms increment mismatch drops from 0.142-0.159 deg/frame at tau = 0 to 0.019-0.025 at the best tau, with a
    sharp V-shaped profile.
  - Frame counts are equal (a = b = c = parquet rows). The parquet's `capture_time - timestamp` drifts from 45 to
    228 ms within ep 31, consistent with info.json fps 20.254 vs the actual 20.0. That is a separate clock-rate
    issue.
- Consequence: frame-index matching of a with b/c is off by ~1.15 frames during head motion (~0.2-0.3 deg/frame
  here). This contradicts "match frames by frame_index" for a<->b/c fusion. A rig pose carried to cam_a must use
  c(t-1.15), or cam_a's own PnP. The rig vs cam_a 0.34 deg rotation spread and the 0.17-0.26 deg rigS vs map gap
  are partly this lag [E].
- Which camera mocap GT is synchronous with is not yet tested (next: GT moving-object time alignment).
- [V] The lag is constant within the clips: every 50-frame window gives -1.15 to -1.20, so there are no frame drops.

### B6. Which stream is mocap GT synchronous with? (`b6_gt_sync.py` -> `b6/gt_sync_p{26,27,31}.json`; public GT, analysis only)  [V measurement, E interpretation]
- Method: in the fast frames of the moving object (> 0.15 m/s; n = 26 / 32 / 49), its GT pose is interpolated at
  t+delta (linear + slerp) and projected into:
  - cam_a with the cam_a own-PnP pose at t, or
  - cam_c with the rig pose at t (world offsets from B2).
  The truncated chamfer to Canny edges at zero shift is averaged, the best delta comes from a parabola, and the
  frames are bootstrapped.

  | ep (object) | cam_a best delta (p5-p95) | cam_c best delta (p5-p95) | a - c |
  |---|---|---|---|
  | 26 (pot) | -1.48 (-1.57..-1.41) | -0.72 (-0.84..-0.56) | -0.76 |
  | 27 (pot) | -1.19 (-1.35..-1.07) | -0.29 (-0.57..-0.21) | -0.90 |
  | 31 (sweeper) | -1.57 (-1.81..-1.44) | -0.64 (-0.70..-0.58) | -0.93 |

- Reading: the cam_a image at frame_index t shows the object where GT puts it at ~t-1.4 (~70 ms earlier); cam_c
  shows it at ~t-0.55.
  - The a-c difference (-0.76..-0.93) agrees in sign and roughly in size with the camera-only B5 estimate (-1.15).
    The chamfer method may carry a common bias of a few tenths of a frame (hands lead/occlude the object).
- Implication [E, important beyond the room map]:
  - A perception pipeline that estimates object pose from cam_a frame t produces the object pose of GT time
    ~t-1.4.
  - At carry speeds of 0.2-0.5 m/s, that is a systematic ~1.4-3.5 cm ADD error during motion. It vanishes at rest.
  - Shifting the predicted trajectory by ~+1.4 frames (prediction at t := estimate from cam_a frame t+1.4,
    interpolated) would remove it.
  - Stereo/mono-based estimates need ~+0.55 frames.
- This contradicts the context fact "match frames by frame_index" at the sub-100 ms level. It belongs to the
  planned D19 (camera time sync) dig, which should confirm it on more episodes and objects, using marker-level
  evidence, before any submission change.

### B0 result: held-out map run2 (`run2/sparse/0`, log `b0_run2_map.log`)  [V]
- One model holds all 346 frames / 519 images (the test sessions' non-zero frames left out): 25,892 points, mean
  track 31.4, mean reprojection 1.12 px. It took 47 min with the CPU shared by the 3 relocalisation runs + validation.
- Alignment to run1 (`b2_align.py run2/sparse/0 b2_align_run2.json`) over the 519 shared images:
  - centre residual 0.51 mm median (p90 1.15);
  - rotation residual 0.009 deg median (p90 0.024);
  - scale (centre-spread ratio) 1.0011.
  So removing 3 sessions changes the shared camera poses by < 1 mm / 0.01 deg, and the map is reproducible. run2
  inherits the a13 mocap registration through this alignment.
- Relocalisation against run2 (completed; see "B8 results"): `venv18/bin/python b1_reloc.py run2/sparse/0 public <ep> b1/run2_p<ep>.json 0 1`
  for 26, 27, 31 (pids in `b1/run2.pids`).

### B7. Visual check of the worst-residual frames (`b7_overlay.py` -> `b7_worst_p26.jpg`, `b7_worst_p31.jpg`; cam_a own-PnP track)  [V]
- Ep 26 f67 / f72 / f77 (A9 residual 2.1 / 1.3 / 2.0 cm): the rack outline sits on the rack. The pot is carried
  over the rack, and its strong edges pull the best-shift search.
- Ep 31 f59 / f119 (2.3 / 2.2 cm): the rack outline is correct. The right hand + sweeper cover the right end of
  the rack, and the left hand holds its left end.
- => All > 1 cm frames inspected are metric artifacts of occlusion, not relocalisation errors. The relocalisation
  itself never failed: hands and objects occlude the table region, while the room above it stays visible.
- Side observation: in ep 26 f60 the in-flight pot's GT outline (same frame_index) visibly trails the image pot,
  consistent with B6's ~1.4-frame GT lag vs cam_a.

### B8. Held-out map relocalisation (`b1/run2_p{26,27,31}.{json,log}`) and yaw falsification  [V]
- Coverage against run2, which contains only the test sessions' frame 0: 100 % rig and 100 % cam_a on all 694
  frames (26 / 27 / 31). Wall time 185 / 262 / 293 s with 3 clips in parallel and no mapper, i.e. 1.0-1.2 s per
  frame per process.
- Yaw split-half CV of the stage A A11 per-episode headings (2,000 random 10/9 splits): a 10-episode median
  predicts a held-out episode's best heading with rms 0.58 deg (mean abs 0.47, p90 0.94, bias -0.04).
  - The leave-26/27/31-out median is +2.29 deg vs the +2.24 used in a13, so a13 is essentially unchanged by
    excluding the test sessions.
  - A11 test-session values relative to a13: 26 -0.81, 27 -0.34, 31 +0.77 deg.
  - => The absolute heading (W) error per episode is ~0.6 deg rms [V CV]. It is now validated rather than
    estimated, though still from the same 19-episode chamfer cost.

### B9. Keyframe relocalisation + VO bridge (`b9_hybrid.py` -> `b9_hybrid_run2.out`; simulated from the run2 rig track + VO v2)  [V]
- pose(t) = VO(t <- k) x reloc(k), where k is the last keyframe, every N frames. Compared with per-frame
  relocalisation, as median / p95 over 26 / 27 / 31:

  | N | position (mm) | rotation (deg) | cost (s/frame) |
  |---|---|---|---|
  | 5 | 0.40-0.44 / 1.05-1.55 | 0.008-0.013 / 0.019-0.038 | ~0.28 |
  | 10 | 0.60-0.68 / 1.47-2.50 | 0.012-0.020 / 0.025-0.055 | ~0.18 |
  | 20 | 0.87-1.11 / 1.92-3.54 | 0.015-0.026 / 0.035-0.081 | ~0.12 |
  | 40 | 1.10-1.70 / 3.15-6.83 | 0.031-0.038 / 0.067-0.138 | ~0.10 |

- => For stage C, keyframes every 10 frames plus VO give the per-frame map accuracy to < 2.5 mm / 0.06 deg (p95)
  at ~6x lower CPU: 20 eval clips x ~300 frames x 0.18 s ~ 18 min of CPU.

### B5b. Lag-compensated rig -> cam_a (`b5b_lagfix.py` -> `b5b_lagfix_run2.out`; held-out run2 tracks, no GT)  [V]
- Spread of the per-frame relative pose a <- c(t+lag) about its clip mean (c pose interpolated by slerp/lerp):

  | lag (frames) | 26 rot median / p90 (deg) | 27 | 31 | translation median (mm) |
  |---|---|---|---|---|
  | 0 | 0.243 / 0.392 | 0.161 / 0.349 | 0.218 / 0.435 | 1.4-1.7 |
  | -1.00 | 0.038 / 0.075 | 0.030 / 0.063 | 0.043 / 0.086 | 1.25-1.35 |
  | -1.15 | 0.022 / 0.041 | 0.018 / 0.036 | 0.026 / 0.053 | 1.2-1.4 |
  | -1.50 | 0.076 / 0.120 | 0.055 / 0.112 | 0.065 / 0.129 | 1.2-1.5 |

- => The a/mono time offset (~-1.15 frames) is real and is the dominant cause of rig-vs-cam_a rotation
  disagreement. Recipe: cam_a pose(t) = T_ac_self x c_pose(t-1.15). This reproduces cam_a's own PnP to ~0.02 deg
  / ~1.3 mm, so cam_a's own PnP is optional.

### B10. Head-pose range covered vs the dataset  [V]
- Test clips (run2 cam_a, mocap): pitch below horizon 41.2-48.3 (26), 47.6-52.0 (27), 49.6-54.9 (31) deg; roll
  -5.8..+5.7 deg.
- Inliers drop with pitch where pitch is steep: ep 31 corr(pitch, rig inliers) = -0.84, with a median of 605 at
  the steepest 10 % vs 730 overall. Still >= 613 at the minimum.
- Map frames of all 39 sessions (public every 1.5 s, eval frame 0): cam_a pitch 37.9-55.4 deg (b 36.6-53.8,
  c 36.1-53.5). Map points per image fall ~20/deg (a) and ~14/deg (c) with pitch. So the test clips span the
  dataset's sampled head-down range up to ~1 deg of its maximum.
- [E] Eval clips should therefore stay inside the validated envelope. Frames steeper than ~55 deg (if any) are
  untested, and stage C must report per-frame coverage. Extrapolating the c slope gives ~1,000 map points per
  image still at 65 deg [H].

### B8 results: GT validation against the held-out map run2 (`b2/run2_p*.{json,log}` with `B2_YAW=1`, `b4_run2.{out,json}`)  [V]
- Command: `B2_YAW=1 ../../venv/bin/python b2_validate.py b1/run2_p<ep>.json b2/run2_p<ep>.json b2_align_run2.json b3/vo_p<ep>.json 10`,
  then `../../venv/bin/python b4_stats.py run2 b1/run2_p26.json b2/run2_p26.json ...`.

  | ep | rig / cam_a inliers min | GT residual median / p90 (cm): cam_a | rigS | rig (factory) | VO | map BA |
  |---|---|---|---|---|---|---|
  | 26 | 635 / 345 | 0.13 / 0.42 | 0.18 / 0.47 | 0.29 / 0.77 | 0.39 / 0.91 | 0.19 / 0.38 |
  | 27 | 627 / 291 | 0.12 / 0.28 | 0.18 / 0.37 | 0.13 / 0.40 | 0.45 / 0.64 | 0.13 / 0.17 |
  | 31 | 584 / 210 | 0.11 / 0.30 | 0.15 / 0.34 | 0.15 / 0.35 | 0.24 / 0.70 | 0.11 / 0.48 |

- Same as run1 with own-session images excluded (B2), to within ~0.05 cm. Having the session's own frames in the
  map is not needed.
- Truly held-out pose accuracy: run2-relocalised poses at the 25 run1 map frames (not in run2), compared with
  run1's BA poses of those frames.
  - cam_a own PnP: position 1.8-2.4 mm median (p90 <= 3.2, max 4.1); rotation 0.020-0.029 deg median (max 0.07).
    The mean vector is ~[+1.2..+1.8, -0.4..-0.7, +0.6..+0.8] mm, so ~1.5-2 mm of it is a common offset absorbed by
    the per-episode offset.
  - rigS: 2.2-2.5 mm, 0.17-0.26 deg. The rotation is mostly the a/mono time lag (B5b), not map error.
- Per-frame noise bound (increments vs VO): rotation p90 0.016-0.022 deg, translation p90 0.70-0.81 mm.
- Runtime (3 clips in parallel, no mapper; M-series 14-core CPU): 1.00-1.13 s per frame median (p90 1.23-1.31).
  - Breakdown: SIFT a+b+c 0.64-0.76 s, b/c matching 0.16-0.25 s, rig PnP 0.05 s, cam_a match+PnP 0.03 s.
  - Map bank load ~10 s per process. Memory ~1.3 GB RSS per process (bank 0.95M x 128 uint8 + model).
- VO drift vs map (run2): 26 4.7 mm / 0.15 deg max (8 s); 27 9.2 mm / 0.41 deg (12 s); 31 14.7 mm / 0.77 deg
  (14.5 s).
- Held-out yaw profile (static GT objects, every 10th frame, translation re-fitted per yaw), best d relative to the
  a13 registration:

  | ep | cam_a | rigS | A11 in-sample (all objects, map frames) |
  |---|---|---|---|
  | 26 | +0.34 | +0.19 | -0.81 |
  | 27 | +0.35 | +0.37 | -0.34 |
  | 31 | +0.67 | +0.69 | +0.77 |

  - All held-out values are within ±0.7 deg of a13 and inside the 0.58 deg rms CV (B8 above). The registration's
    heading is not falsified.
  - The per-episode estimate changes by up to ~1.1 deg between cost variants (object set, frames), so
    per-episode chamfer yaw has ~0.5-0.8 deg method noise.
  - The mean held-out offset of +0.45 deg (n = 3) hints that a13 may be a few tenths low [E]. That is
    inconsequential for scoring (flat anchors within ±5 deg).

### B11. Stage B re-run (2026-10-07 07:25): resume state and additions
- Resumed after a cut-off. All B0-B10 artifacts listed below exist; no jobs were running (load 3.2). The stage C
  entries further down were written by the earlier run and are left as they are.
- Gaps against the stage B brief, now being filled:
  - "marker reprojection error": B2 used only the edge-chamfer metric. Note 17 holds automatic marker-sphere
    detections (HoughCircles, `work/17/out/reg2_<ep>.json` `obs`) on GT-static objects, plus independent per-frame
    mocap cameras fitted to them (VO + drift knots, LOMO 1.2 mm), for eps 0, 12, 21, 26 and 31.
  - Tasks beyond the dish rack: relocalise 0 (pot/lid), 12 (blue cup + rack) and 21 (water can + blue cup, the
    largest head motion in note 17: 9.7 deg / 66 mm) against run1 with own-session images excluded except frame 0.
- Re-run finished 2026-10-07 ~07:58 (B12-B19 below). No jobs left running. The a4 script was re-run only to print
  its bootstrap; its json is unchanged (backup `b11/a4_backup.json`).

### B12. Cross-check against note 17's marker-registered cameras and marker detections (`b11_marker_check.py` -> `b11/run2_p{26,31}.json`)  [V]
- Script: `../../venv/bin/python b11_marker_check.py <ep> b1/run2_p<ep>.json b2_align_run2.json b2/run2_p<ep>.json b11/run2_p<ep>.json`.
  It reads public GT and note 17 outputs only for validation. Env `B11_OBJ=<name>` / `B11_TRACKS=a,rigL` restrict
  the run.
- Inputs:
  - Note 17's cameras (`work/17/out/reg2_<ep>.json`) are stereo VO with drift knots every 15 frames, fitted to
    automatically detected marker spheres on GT-static objects. Their in-sample residual is 2.2-2.5 px; their LOMO
    accuracy is ~1.2 mm. They share no data with the map relocalisation.
  - My tracks are from the HELD-OUT map run2: cam_a own PnP (`a`), and rig c(t-1.15) -> cam_a with a self-calibrated
    extrinsic (`rigL`, the B5b recipe).
- Direct per-frame camera comparison. One rigid 6-DoF transform per clip is fitted, then the per-frame residual is:

  | ep (frames) | track | position mm median / p90 / max | rotation deg median / p90 / max | position by thirds (mm) |
  |---|---|---|---|---|
  | 26 (158) | a | 2.06 / 3.20 / 5.5 | 0.077 / 0.139 / 0.31 | 1.9 / 2.1 / 2.3 |
  | 26 | rigL | 2.01 / 3.23 / 5.3 | 0.078 / 0.133 / 0.17 | 1.7 / 1.9 / 2.3 |
  | 31 (290) | a | 3.42 / 5.98 / 14.8 | 0.149 / 0.297 / 0.55 | 3.1 / 3.7 / 3.0 |
  | 31 | rigL | 3.14 / 5.82 / 13.6 | 0.142 / 0.283 / 0.53 | 2.9 / 3.7 / 2.5 |

  - Two independent methods (room map vs object markers + VO) agree on the head trajectory to 2-3.4 mm and
    0.08-0.15 deg per frame, with no growth over the clip. That bounds the sum of both errors.
  - The rig without lag compensation (`rigS`) gives 0.24 deg, the a/mono time lag of B5 seen once more.
- Marker reprojection of the map poses on note 17's detections (a-eq px; one world translation per clip fitted on the
  markers, because the dataset re-centres x,y):

  | ep | objects | map `a` median / p90 | map `rigL` | note 17 in-sample (its own fit to these markers) |
  |---|---|---|---|---|
  | 26 | rack (125 obs) | 1.37 / 3.27 | - | 1.74 / 3.94 |
  | 26 | rack + pot (222 cam_a obs) | 2.41 / 13.0 | 3.34 / 12.2 | 2.09 / 4.33 |
  | 31 | rack (363) | 2.90 / 4.97 | 2.59 / 4.39 | 2.04 / 4.87 (rack, cam a) |
  | 31 | rack + sweeper (418) | 3.31 / 7.47 | 2.79 / 6.43 | 2.11 / 4.84 |

  - On the rack alone, the map poses (which never saw a marker) reproduce the detections as well as cameras fitted to
    them.
  - The 13 px p90 in ep 26 is the pot's pre-onset position only: first third 9.5 px, versus 2.8 px for the pot in
    the rack at the end. A translation-only offset cannot fit both pot positions and the rack at once.
  - With the offset from B2 (edge chamfer, not marker-fitted) instead, the median is 5.1-5.6 px. The B2 and marker
    offsets differ by 4-7 mm, mostly in depth/z, which the edge-chamfer metric constrains weakly (B2 limitation).
- Absolute orientation: the markers do not decide tilt (orbit ambiguity).
  - The rigid transform between my cameras and note 17's has a tilt of 1.17 deg (ep 26) and 4.39 deg (ep 31).
  - A free 6-DoF marker fit of my cameras prefers rotations of 1.3 deg (26) and 2.2-2.9 deg (31). These are about
    the same camera-frame axis in both clips (+x and +y by similar amounts).
  - It is ill-conditioned:
    - rack-only in ep 26 is degenerate (rotation standard error 12.7 deg; rotation-translation correlation 1.000;
      the fit drifts to 24.7 deg for a 0.06 px gain);
    - other subsets show rotation-translation correlation 0.997.
    A compact marker cluster seen from one side cannot separate a camera rotation from a camera orbit about the
    cluster.
- Arbiter (`b12_table_arbiter.py <ep> b1/run2_p<ep>.json b2_align_run2.json` -> `b11/b12_table_p<ep>.json`):
  - Method: the dense b/c stereo table normal measured in the cam_c frame (a5, map-free) at every 30th frame is
    expressed in each world.
  - Map (a13): the table is level to 0.37 deg (26) / 0.54 deg (31) median.
  - Note 17 cameras: tilted 1.21 deg (26) / 4.12 deg (31), consistently at every frame.
  - Public GT says the table is level (a4: 0.40 deg).
  - New check (`b13_rack_up.py` -> `b11/b13_rack_up.out`; public GT only): the rack's up-vector in its own frame is identical across
    eps 12, 13, 26, 27, 31 to 0.07-0.37 deg, so the GT world does not tilt per episode.
  - => The map's absolute tilt is right to ~0.5 deg. Note 17's absolute orientation carries a 1-4 deg orbit error,
    harmless to its relative accuracy.
    - Correction, B19: GT's table actually leans ~0.4-0.75 deg, so a13 is off by about that much, in the
      direction note 17 leans. Note 17's 1.2-1.9 deg (4.1 in ep 31) is still 2-5x larger.
  - Extended to eps 0, 12 and 21 (run1, own session excluded, `b11/b12_table_p{0,12,21}.json`). Median table tilt:

    | world | ep 0 | ep 12 | ep 21 | ep 26 | ep 31 |
    |---|---|---|---|---|---|
    | map | 0.31 | 0.33 | 0.44 | 0.37 | 0.54 |
    | note 17 | 1.93 | 1.19 | 1.31 | 1.21 | 4.12 |

    - Note 17's world table normal leans toward +x/-y by (+0.3..+1.1, -0.6..-1.8) deg in eps 0, 12, 21 and 26, and
      by (-0.5, +4.0) in ep 31 (the one that started 11.5 deg off). So the marker orbit is partly systematic.
    - GT's own table normal (a4 rerun: 104 rest contacts, contact sd 5 cm in x and 10 cm in y) is 0.40 deg toward
      (+x, -y) = (+0.19, -0.36) deg, with bootstrap p5-p95 0.21-0.89 deg. It points the same way as note 17's, but
      is 3-5x smaller.
    - Reading [E]: the map's a13 gravity (table normal := +z) is ~0.4 deg from GT's best table normal, inside GT's
      own uncertainty. Note 17's 1.2-4.1 deg is outside GT's p95.
    - Possible refinement [H]: set the registration's up to GT's table normal, not to +z. That is a 0.4 deg change,
      below every scoring sensitivity.

### B14. Three more public clips, other tasks (`b1/run1lso_p{0,12,21}.{json,log}`; summary `b14_reloc_summary.py` -> `b11/b14_reloc_summary.out`)  [V]
- Command (3 in parallel, 07:22-07:30): `venv18/bin/python b1_reloc.py run1/sparse/0 public <ep> b1/run1lso_p<ep>.json 1 1`.
  This is run1 with the clip's own images excluded except frame 0. B8 showed it matches the held-out map run2 to
  ~0.05 cm.
- Tasks: ep 0 = pot + lid (373 frames, 18.6 s, the longest public clip here); ep 12 = blue cup + rack; ep 21 =
  water can + blue cup (fastest head turn).

  | ep | coverage rig / a | rig inliers min / p5 / median | cam_a inliers min / p5 / median | s/frame median / p90 | pitch (deg) | heading excursion (deg) | head extent (cm) |
  |---|---|---|---|---|---|---|---|
  | 0 | 100 / 100 % | 595 / 633 / 810 | 257 / 341 / 408 | 0.96 / 1.29 | 36.9-47.6 | -1.5..+7.9 | 7.9 |
  | 12 | 100 / 100 % | 748 / 788 / 873 | 363 / 459 / 528 | 1.22 / 1.46 | 37.1-42.5 | -3.1..+1.2 | 2.6 |
  | 21 | 100 / 100 % | 602 / 628 / 757 | 112 / 328 / 375 | 1.18 / 1.47 | 43.8-48.7 | -5.9..+8.5 | 5.4 |
  | 26* | 100 / 100 % | 635 / 684 / 744 | 345 / 362 / 407 | 1.13 / 1.31 | 41.2-48.3 | -3.7..+0.8 | 2.2 |
  | 27* | 100 / 100 % | 627 / 651 / 702 | 291 / 317 / 350 | 1.06 / 1.24 | 47.6-52.0 | -6.2..0.0 | 2.1 |
  | 31* | 100 / 100 % | 584 / 605 / 730 | 210 / 232 / 346 | 1.00 / 1.23 | 49.6-54.9 | -13.2..+3.0 | 8.6 |

  (* = held-out map run2, from B8.)
- Hardest frames: ep 21 f21-27 is a fast head turn, with c rotating up to 2.0 deg/frame (40 deg/s). cam_a peaks
  ~1 frame later, as the a/mono lag predicts, at 1.7-1.9 deg/frame.
  - cam_a sharpness (variance of Laplacian) falls from 400-900 to ~200, and its inliers from ~375 to 112-157 (f24-26).
  - The rig keeps >= 690 inliers. Nothing fails: the floor is 30 inliers.
  - So motion blur at ~40 deg/s costs cam_a ~70 % of its inliers, while the wide-FOV mono rig is barely affected.
- Inliers vs sharpness: Spearman -0.37..+0.60 across clips. No consistent sign, so blur matters only at extremes
  like ep 21 f24.

### B12b. Note 17 cross-check on all five clips (`b11/run1lso_p{0,12,21}.json`, `b11/run1lso_p21_lag213.json`)  [V]
- Command: `../../venv/bin/python b11_marker_check.py <ep> b1/run1lso_p<ep>.json - - b11/run1lso_p<ep>.json [lag]`.
  With `-` in place of the B2 json, the translation is initialised from note 17's camera centres, then fitted on the
  markers.
- Per-frame camera agreement with note 17 after one rigid transform per clip (cam_a own PnP `a` / lag-compensated
  rig `rigL`):

  | ep | frames | `a` position mm median / p90 | `a` rotation deg median / p90 | `rigL` position mm | `rigL` rotation deg | position by thirds, `a` (mm) |
  |---|---|---|---|---|---|---|
  | 0 | 373 | 4.74 / 10.4 | 0.181 / 0.288 | 4.32 / 9.37 | 0.167 / 0.291 | 3.7 / 4.4 / 7.1 |
  | 12 | 181 | 2.27 / 3.42 | 0.065 / 0.105 | 1.97 / 2.61 | 0.059 / 0.095 | 2.1 / 2.6 / 2.1 |
  | 21 | 186 | 4.14 / 8.36 | 0.082 / 0.175 | 3.50 / 6.65 (lag -2.13) | 0.073 / 0.170 | 5.0 / 4.8 / 3.2 |
  | 26 | 158 | 2.06 / 3.20 | 0.077 / 0.139 | 2.01 / 3.23 | 0.078 / 0.133 | 1.9 / 2.1 / 2.3 |
  | 31 | 290 | 3.42 / 5.98 | 0.149 / 0.297 | 3.14 / 5.82 | 0.142 / 0.283 | 3.1 / 3.7 / 3.0 |

  - The largest disagreements fall in the fastest motion: ep 21 f20-32 (the 40 deg/s turn) has 11.6 mm / 0.21 deg,
    versus 3-5 mm elsewhere.
  - Ep 0 grows to 7 mm in its last third. Whether that is note 17's VO + knots or the map is checked against B2's
    GT edges below.
- The a/mono lag is NOT always -1.15 frames. Ep 21 is -2.15. This comes GT-free from `b5_sync.py b1/run1lso_p21.json`
  (rms 0.036 vs 0.43 deg/frame at lag 0), and note 17 found 2.13 independently.
  - With the fixed -1.15 lag, `rigL` in ep 21 disagrees with note 17 by 0.35 deg and the unlagged rig by 0.68 deg
    (1.56 deg during the turn). With the self-calibrated lag it is 0.073 deg.
  - Eps 0 and 12 measure -1.15 / -1.10.
  - So the lag must be self-calibrated per clip (as stage C's design does), never fixed.
- Marker reprojection, cam_a obs, `a` track, translation fitted on the markers (a-eq px, median / p90). Note 17's
  in-sample value is its own fit to these detections:

  | ep | map `a`, translation only | map `a`, + free world rotation (6-DoF) | rotation it prefers | note 17 in-sample |
  |---|---|---|---|---|
  | 0 (pot, lid) | 3.06 / 6.63 | 1.83 / 5.01 | 1.77 deg | 2.66 / 5.03 |
  | 12 (rack, cup) | 2.92 / 10.1 (cup 10.6) | 2.54 / 6.58 | 1.44 deg | 2.03 / 4.43 |
  | 21 (pitcher, cup) | 4.08 / 9.88 | 2.35 / 4.28 | 2.05 deg | 2.36 / 5.12 |
  | 26 (rack, pot) | 2.41 / 13.0 | 1.49 / 3.53 | 1.27 deg | 2.09 / 4.33 |
  | 31 (rack, sweeper) | 3.31 / 7.47 | 2.89 / 5.75 | 2.91 deg | 2.11 / 4.84 |

  - In every clip the markers prefer the same extra world rotation, 1.3-2.9 deg about a horizontal axis at azimuth
    ~35-55 deg. Its standard error is 0.1-0.25 deg on two-object clips, with rotation-translation correlation
    0.94-0.98.
  - The b/c detections alone, with the rig poses (no cam_a involved, ep 0), want the same rotation (1.23 deg, same
    axis). So the cause is not cam_a-specific.
- Is the map's gravity (the stereo table plane) biased? Two checks.
  - B15 (`b15_disp_rowgrad.py run1/sparse/0 3` -> `b11/b15_disp_rowgrad.out`): stereo-minus-map disparity at
    69k map points, regressed on rectified image position.
    - Row gradient -1.16e-3 px/px (se 0.02e-3, a roll-equivalent of -0.067 deg). Column gradient -0.82e-3.
    - Consistent in all 26 sessions (row -0.6..-1.7e-3).
    - So the factory b/c extrinsic carries a small projective disparity bias relative to the multi-session map.
  - B16 (`b16_table_corr.py run1/sparse/0 b11/b15_gmodel.json 6` -> `b11/b16_table_corr.{out,json}`): the table
    plane recomputed from bias-corrected disparity (33 map frames) moves by only (-0.08, -0.27) deg in mocap x/y (sd
    0.14 / 0.13).
  - The map's floor plane is 0.71 deg from the stereo table, toward (-0.67, +0.22) deg. That is the opposite x
    direction to the markers' (+0.9, -0.9).
  - => Neither stereo bias (<= 0.3 deg) nor floor/table disagreement explains a 1.3-2.9 deg rotation.
- Status [V facts, H cause]: the room geometry (stereo table, map floor) and GT (table level to 0.4 deg, rack
  equally flat in all sessions) put the map's absolute tilt within ~0.5 deg. The GT marker detections
  consistently want 1.3-2.9 deg more, about one axis.
  - Candidate causes [H]:
    - a systematic depth-dependent bias of the Hough sphere centre (the black mounts);
    - a common rotation between the scan meshes' marker layout and the mocap rigid-body frames;
    - a GT-object vs table inconsistency that a4's 104 contacts do not see.
  - Falsifier for the map: a GT-silhouette tilt profile (B17, running) or a third tilt reference.
  - Scoring impact: none (one rigid alignment per clip). For physics/gravity priors, treat absolute tilt as
    uncertain at ~1-2 deg until resolved.

### B19. GT objects at rest lean the same way: part of the tilt gap is the registration (`b19_support_plane.py` -> `b11/b19_support_plane.out`; public GT only)  [V]
- Method: each GT-posed scan's convex-hull support plane (facets within 3 deg of the most downward one,
  area-weighted), at the first and last frame.
- Objects resting on the table (z_min 0.598-0.601) lean consistently toward (+x, -y):
  - rack, eps 12, 13, 26, 27, 31: 0.49-0.85 deg; mean lean (+0.23, -0.65) deg; support facet 625 cm2;
  - pot on the table: 0.66-1.02 deg, (+0.40..+0.88, -0.52..-0.79), plus 1.98 deg in ep 0 f372;
  - blue cup: 0.93-1.04 deg, (+0.38..+0.63, -0.68..-0.95), except ep 21 f0 (-0.10, +0.56);
  - pitcher: 0.20-0.84 deg, mixed.
- GT's own contact-height fit (a4) leans the same way: (+0.19, -0.36) deg, 0.40 deg.
- The markers-preferred table normal (fit6 rotation applied to the map world) is also (+x, -y), only larger:

  | ep | 0 | 12 | 21 | 26 | 31 |
  |---|---|---|---|---|---|
  | lean (x, y) deg, track `a` | (+1.28, -1.21) | (+1.05, -0.99) | (+1.82, -0.96) | (+0.92, -0.87) | (+1.67, -2.37) |

  - Typical: (+1.1, -1.0) = ~1.4 deg. `rigL` gives the same within 0.3 deg.
- Reading:
  - [V] In the GT frame, the table (or the GT world) leans ~0.4-0.75 deg toward azimuth ~-60 deg. a13 forces the
    stereo table normal to +z, so the map world is tilted by that much against GT, in the direction the markers
    point. This explains about half of the marker preference.
  - [E] A better registration would set up := the GT table normal, ~(+0.3, -0.6) deg (rack support plane and
    contacts). The remaining ~0.7 deg (1-2 deg in eps 21 and 31) is within the marker orbit-ambiguity and
    systematics.
  - [E] Absolute tilt error of a13 vs GT: ~0.6 deg, now with a known direction. Scoring impact: none.

### B17. GT-silhouette tilt profile (`b17_tilt_profile.py` -> `b11/b17_tilt_p{26,12}.{json,log}`)  [V]
- Command: `B17_AX=50 ../../venv/bin/python b17_tilt_profile.py <reloc> b11/b17_tilt_p<ep>.json <align|-> - 10`.
- Method: the cam_a own-PnP track is rotated about horizontal world axes at azimuth 50 deg (the marker-preferred
  axis) and 140 deg, through its mean centre, in -3..+3 deg steps. The translation is re-fitted at each step. The cost
  is the A9 edge chamfer of GT-posed static objects on every 10th frame.

  | ep | best about az 50 | best about az 140 | implied table-normal lean (x, y) | markers' lean (B19 table) |
  |---|---|---|---|---|
  | 26 (rack + pot pre-onset, 16 frames) | +0.09 deg (curv 0.28) | -0.20 (0.14) | (-0.06, -0.21) | (+0.92, -0.87) |
  | 12 (rack + cup, 19 frames) | +1.08 (0.13) | -1.16 (0.13) | (+0.08, -1.58) | (+1.05, -0.99) |

- The silhouettes give 0.2 deg (26) and 1.6 deg (12). The profiles are shallow (chamfer changes 0.1-0.2 px per
  deg), so each is uncertain by roughly ±0.5-1 deg.
- Summary of the absolute-tilt evidence. Every GT-based estimate leans the map world the same way, toward -y and
  mostly +x:

  | evidence | lean |
  |---|---|
  | contacts (a4) | 0.40 deg |
  | resting-object support planes (B19) | 0.5-1.0 deg |
  | silhouettes (B17) | 0.2-1.6 deg |
  | marker detections (B12b) | 1.3-2.9 deg |

- [E] So a13's gravity (stereo table := +z) is off the GT world's up by ~0.5-1.5 deg (best guess ~0.8 deg).
  Stage A's "~0.3 deg" was the per-frame consistency, not the absolute error. The per-frame consistency (0.3 deg)
  and all relative accuracy numbers stand.
- [H, proposed] Re-register gravity jointly on GT objects across the 19 public sessions (support planes + edges +
  markers, two tilt parameters, leave-session-out). Do not assume the table is level in the GT frame.
  - Falsifier: if the leave-session-out tilt scatters by more than its mean, keep a13.
  - Scoring impact: none (the scorer's rigid alignment absorbs it). Physics/priors: 1 deg = ~9 mm of height
    across a 0.5 m table.

### B14b. GT edge validation and VO drift on eps 0, 12, 21 (`b2/run1lso_p{0,12,21}.{json,log}`, `b4_run1lso_b14.out`, `b11/b18_vo_drift.out`)  [V]
- Commands:
  - `../../venv/bin/python b2_validate.py b1/run1lso_p<ep>.json b2/run1lso_p<ep>.json - b3/vo_p<ep>.json 10`
  - `b4_stats.py run1lso_b14 ...`
  - `b18_vo_drift.py <reloc> <vo> ...` (new; GT-free VO-vs-map divergence over every frame)
  - VO: `b3_vo.py public <ep> b3/vo_p<ep>.json 0`, masked `b3/vom_p<ep>.json 1`
- A9 edge-chamfer GT residual (cm, median / p90), on frames with GT-static objects only:

  | ep (frames with static objects) | cam_a own PnP | rigS (lag 0) | VO | worst frames |
  |---|---|---|---|---|
  | 0 (109 of 373; pot/lid before onset) | 0.16 / 0.49 | 0.16 / 0.68 | 0.22 / 0.71 | f57-62, 2.3 cm in ALL tracks: the lid is lifted over the pot |
  | 12 (181; rack static all clip) | 0.16 / 0.34 | 0.23 / 0.42 | 0.40 / 0.63 | f91 0.8 cm |
  | 21 (35; pitcher/cup before onset 37) | 0.10 / 0.22 | 1.02 / 1.95 | 0.75 / 1.98 | f22-24 = the 40 deg/s turn, rig only |

  - cam_a own-PnP relocalisation is 0.10-0.16 cm median on all three new tasks, the same level as 26/27/31.
  - Ep 21's rig error (1.0 cm, 2.1 cm in the turn) is the uncompensated 2.15-frame a/mono lag (B12b), not a pose
    failure.
- VO (v2, factory extrinsic) vs per-frame map relocalisation over EVERY frame (camera centre / rotation divergence):

  | ep | duration | unmasked VO end (max) | masked VO end |
  |---|---|---|---|
  | 0 | 18.6 s | 16.0 mm / 0.35 deg | 35.3 mm / 0.59 deg |
  | 12 | 9.1 s | 5.9 mm / 0.10 deg (6.4) | - |
  | 21 | 9.3 s | 22.4 mm / 0.38 deg (24.8) | 19.4 mm / 0.39 deg |
  | 26 | 7.9 s | 4.7 mm / 0.15 deg | - |
  | 27 | 12.3 s | 6.9 mm / 0.36 deg (9.1) | - |
  | 31 | 14.5 s | 14.0 mm / 0.73 deg (14.7) | - |

  - Ep 21's VO gains 2-3 mm per frame over f48-65, while the head moves only ~1 mm/frame. The rig then sees
    602-690 inliers, and the pitcher is lifted (onset f38).
  - Over f32-60 the map and note 17's marker-corrected cameras agree to ~4 mm (B12b). So the 20 mm is VO error
    (dynamic content / scale), not map error.
  - Masking the bottom-centre does not cure it, and makes ep 0 worse.
  - So VO drift on public clips spans 5-35 mm over 8-19 s (0.6-2.4 mm/s). The map has no growth term.
- Jitter (Savitzky-Golay residual; it includes real high-frequency head motion): rig 0.30-0.50 mm / 0.07-0.18 deg
  rms, identical to VO. cam_a own PnP is 0.6-1.3 mm (narrower FOV, fewer inliers).
  - [H, unresolved] The consistent ~1.3-2.9 deg orbit that the markers prefer would come from a small systematic in
    the marker chain, of a few px across the cluster: GT object orientation or marker layout vs scan, or cam_a
    lower-image distortion. A constant rotation per clip is absorbed by the scorer's one rigid alignment.

## Stage B limitations
- Only 3 public clips (2 tasks; all with the static dish rack), 694 frames, head pitch 41-55 deg. Eval clips have
  not been relocalised yet (stage C). Other tasks may have more occlusion or steeper views.
- GT metric:
  - It is the A9 edge-chamfer best shift. Its floor is ~0.1-0.2 cm, it saturates at ±20 px, and it measures
    image-plane error at object depth; the depth direction is weakly tested.
  - The per-episode offset (needed for the dataset's x,y re-centring) also absorbs any constant pose bias, by
    design.
  - Occlusion inflates it (B7).
  The held-out BA-pose comparison (~2 mm / 0.02-0.03 deg) is the complementary direct check, at 25 frames.
- run2 is registered to mocap through its alignment to run1 (shared images), not independently. run1's
  registration (gravity from stereo, yaw from 19-episode GT edges) used frames of 26/27/31 among the 19 sessions.
  The leave-3-out yaw median moves by only +0.05 deg.
- Timing findings (B5/B6) rest on 3 episodes. The GT-vs-camera lag uses a moving-object chamfer that hands may
  bias by a few tenths of a frame. They must be confirmed (D19) before changing any submission timing.
- Runtime was measured on this Mac (14 cores, 3 processes in parallel). No GPU, no learned features: SIFT
  sufficed here, and hloc-style learned matching was not needed or tested.
- VO baseline: one implementation (KLT + EPnP, c-referenced). A better VO (bundle-adjusted windows, both cameras)
  would drift less. The map's advantage is then mainly absolute registration and bounded error over long clips.
- Re-run additions (B11-B18):
  - Eps 0, 12, 21 were localised against run1 with own-session images excluded except frame 0, not against a
    held-out map. Their map points were partly triangulated from own-session frames (every 30th). B8 showed this
    changes results by < 0.05 cm on 26/27/31.
  - For eps 0 and 21, the GT edge metric covers only the pre-onset frames (109 and 35). Later frames are covered
    only by the marker / note-17 comparisons.
  - Note 17's cameras are not GT. They are VO + knots fitted to GT marker detections, with their own orbit error
    (1-4 deg) and possible VO drift between knots. The agreement numbers bound the SUM of both errors.
  - The marker detections were associated within 6 a-eq px of note 17's own predictions. This selection window
    truncates large residuals for any camera.
  - Absolute tilt: a13 levels the stereo table, while GT's table leans ~0.4-0.75 deg (B19). GT marker
    detections prefer ~1.4 deg (up to 2.9) in the same direction (B12b). The remaining ~0.7 deg is unresolved; no
    scoring impact.

## Stage B artifacts (`/Users/aebatirel/Documents/Code/v2d-research/work/18/`)
- Held-out map:
  - `b0_heldout_map.py` -> `run2/{db.db,sparse/0}` (log `b0_run2_map.log`);
  - `b2_align.py` -> `b2_align_run2.json` (X_run1 = Ra X_run2 + ta).
- Relocaliser `b1_reloc.py` (venv18; no GT): `b1/run1lso_p{26,27,31}.{json,log}` (run1, own-session images
  excluded except frame 0) and `b1/run2_p{26,27,31}.{json,log}` (held-out map). The descriptor bank cache is
  `run{1,2}/sparse/0/bank.npz{,.json}`.
  - json per frame: c_from_world (rig, map frame), a_from_world, inliers, matches, timings, blur.
- VO: `b3_vo.py` (v2 ray-exact) -> `b3/vo_p*.json` (unmasked), `b3/vom_p*.json` (masked). v1 with the DLT bias is
  `b3_vo_v1_dltbias.py` -> `b3/v1/`.
- Validation (shared venv; the only GT reader): `b2_validate.py` -> `b2/run1lso_p*.{json,log}`,
  `b2/run2_p*.{json,log}` (incl. yaw profiles), and overlays `b2ov/`.
- Statistics: `b4_stats.py` -> `b4_run1lso.{out,json}`, `b4_run2.{out,json}`.
- Timing:
  - `b5_sync.py` -> `b5_sync_run1lso.out` (a vs mono lag);
  - `b5b_lagfix.py` -> `b5b_lagfix_run2.out`;
  - `b6_gt_sync.py` -> `b6/gt_sync_p{26,27,31}.json` (GT vs camera lag; public GT, analysis only).
- `b7_overlay.py` -> `b7_worst_p26.jpg`, `b7_worst_p31.jpg` (worst-frame visual check).
- `b9_hybrid.py` -> `b9_hybrid_run2.out` (keyframe + VO).
- Commands (from `work/18`; long runs bounded with `perl -e 'alarm N; exec @ARGV'`):
  - `venv18/bin/python b0_heldout_map.py run2 26,27,31`
  - `venv18/bin/python b2_align.py run2/sparse/0 b2_align_run2.json`
  - `venv18/bin/python b1_reloc.py run2/sparse/0 public <ep> b1/run2_p<ep>.json 0 1` (first run builds the bank;
    run one process first before running in parallel)
  - `../../venv/bin/python b3_vo.py public <ep> b3/vo_p<ep>.json 0`
  - `B2_YAW=1 ../../venv/bin/python b2_validate.py b1/run2_p<ep>.json b2/run2_p<ep>.json b2_align_run2.json b3/vo_p<ep>.json 10`
  - `../../venv/bin/python b4_stats.py run2 b1/run2_p26.json b2/run2_p26.json b1/run2_p27.json b2/run2_p27.json b1/run2_p31.json b2/run2_p31.json`
  - `../../venv/bin/python b5_sync.py b1/run1lso_p*.json`; `b5b_lagfix.py b1/run2_p*.json`;
    `b6_gt_sync.py <ep> b1/run1lso_p<ep>.json b2/run1lso_p<ep>.json`; `b9_hybrid.py <reloc> <vo> ...`
- No downloads. No SlamDunk code read or edited except this notes file. No jobs are left running.
- Re-run additions (2026-10-07 morning; all in `work/18`):
  - Relocalisation of other tasks: `b1/run1lso_p{0,12,21}.{json,log}` (pids in `b1/run1lso_b11.pids`).
  - VO: `b3/vo_p{0,12,21}.json`, masked `b3/vom_p{0,21}.json`.
  - GT edges: `b2/run1lso_p{0,12,21}.{json,log}`; stats `b4_run1lso_b14.{out,json}`.
  - `b11_marker_check.py` -> `b11/run2_p{26,31}.json`, `b11/run1lso_p{0,12,21}.json`, `b11/run1lso_p21_lag213.json`
    (marker reprojection + per-frame comparison with note 17's cameras; env `B11_OBJ`, `B11_CAMS`, `B11_TRACKS`).
  - `b12_table_arbiter.py` -> `b11/b12_table_p{0,12,21,26,31}.json` (stereo table normal in the map world vs note 17's
    world).
  - `b13_rack_up.py` -> `b11/b13_rack_up.out` (GT rack flatness across sessions). `b13_gt_base_tilt.py` is a
    superseded first attempt.
  - `b14_reloc_summary.py` -> `b11/b14_reloc_summary.out` (coverage, inliers, time, head envelope; no GT).
  - `b15_disp_rowgrad.py` -> `b11/b15_disp_rowgrad.out` (stereo-vs-map disparity gradient). Its model is
    transcribed to `b11/b15_gmodel.json`.
  - `b16_table_corr.py` -> `b11/b16_table_corr.{out,json}` (table plane with bias-corrected disparity).
  - `b17_tilt_profile.py` -> `b11/b17_tilt_p{26,12}.{json,log}` (GT edge-chamfer world-tilt profile).
  - `b18_vo_drift.py` -> `b11/b18_vo_drift.out` (VO vs map over every frame; no GT).
  - `b19_support_plane.py` -> `b11/b19_support_plane.out` (support-plane tilt of GT-posed resting objects).

## Proposed stage C (as planned at the end of stage B; executed, see "Stage C log")
1. Relocalise all 20 eval clips against run1:
   - automatic only;
   - frame 0 is in the map;
   - keyframes every 5-10 frames + VO v2 (~20 CPU-min), or per-frame (~1.5 CPU-h).
   Report per clip:
   - coverage and inlier minima;
   - pitch range vs the validated 38-55 deg envelope;
   - VO-vs-map divergence;
   - per-frame gravity (camera tilt) and height;
   - the lag-compensated cam_a poses (T_ac_self x c(t-1.15)).
2. Export per eval episode a mocap-frame camera track for cam_a, as R_wc and C with x,y in map coordinates. A
   per-episode x,y constant is irrelevant to the scorer.
3. Feed D19 with the timing findings: confirm the a/mono/GT lags on all 19 public episodes. Then estimate the AUC
   effect of time-shifting predictions on public GT with a cam_a-based estimate (simulated).
4. Optional robustness: add a public clip from a different task (e.g. 39/40 dust pan with more motion, 18) and an
   eval clip with a steep head-down segment, if any exists.

## Stage C log (eval clips, inference design; appended per finding)

### C0. Setup (2026-10-07 01:30)  [V]
- Eval clips: all 20 have a/b/c locally (equal frame counts per camera): 1:335 3:313 5:288 6:243 8:219 10:161
  14:158 15:166 16:173 19:235 20:202 25:356 28:220 30:263 32:259 33:348 35:421 36:407 37:151 38:263 = 5,181 frames.
- Relocaliser `c1_reloc.py` = `b1_reloc.py` plus: env `C1_PUBONLY=1` (match only against PUBLIC map images; the first
  frame then starts from the mean public optical axis instead of the clip's frame-0 map image), a c-only PnP per
  frame (rig-extrinsic-free check), and partial dumps every 40 frames (`<out>.part`). Reads no GT.
- Smoke test e10 (3 frames): rig 804 inliers / cam_a 535 (pooled map), 628 / 334 (public-only images).
- Running: `sh c1_batch.sh 5 s5 0 <20 eps>` (stride 5, run1, 3 workers, logs `c1log/s5_e*.log`, outputs
  `c1/s5_e*.json`; batch pid in `c1log/batch_s5.pid`). The host is shared with another agent's CoACD jobs (load ~14).
- Recording order (public parquet global `index`): public 31 (task 11) ends at 7,897 and public 39 (task 14) starts
  at 10,077; the 2,180-frame gap holds eval 32, 33, 35, 36, 37, 38 and withheld 34. So the eval task 12-13 sessions
  (ev32-37) were recorded between map sessions 31 and 39-44, which are both in the map.

### C1 interim (9/20 eval clips done, stride 5; `c2_stats.py` without VO)  [V]
- e1, e3, e5, e25, e30, e33, e35, e36, e38: coverage 100 % rig and 100 % cam_a at every 5th frame. Rig inliers min
  573 (e3), cam_a min 80 (one e33 frame; next lowest 228). Head pitch reaches 57.8 deg (e38) and 56.3 (e35), up to
  ~2.5 deg beyond the stage-B envelope, with rig inliers still >= 689-810 there.

### C1. All 20 eval clips relocalised (stride 5, run1 map; `c1/s5_e*.json`, logs `c1log/`; stats `c2_novo.{out,json}`)  [V]
- Wall time 7.5 min for 1,045 keyframes with 3 workers (~1.1-1.3 s per keyframe per process, shared host).
- Coverage: 100 % rig and 100 % cam_a on all 1,045 keyframes of all 20 clips (every 5th frame = 4 Hz, all head
  poses seen). No retry with the doubled candidate set was needed for a failure.
- Inliers: rig min 554 (e16), per-clip min 554-810, per-clip median 636-899. cam_a min 80 (one e33 frame), next
  lowest per-clip minima 171 (e6) and 219 (e8).
- Head envelope (cam_a, mocap): pitch 34.2-57.8 deg below horizon (stage B validated 41-55; map frames 38-55),
  roll -7.0..+16.1, heading excursions up to -15/+13 deg from frame 0, height 1.089-1.150 m.
  Rig inliers stay >= 689-810 at the steepest frames (e35 56.3, e38 57.8 deg). corr(pitch, inliers) ranges -0.94..+0.77,
  i.e. steep pitch costs inliers in some clips but never approaches the 30-inlier floor (margin ~20x).
- Task-index 12-13 sessions (e32, e33, e35, e36, e37): 100 % coverage, rig min 629-741, i.e. no different from the others.
- c-only PnP vs rig solve (rig-extrinsic-free check): 0.04-0.06 deg for e10-e25 and 0.09-0.14 deg for e1-e8 and
  e28-e38, 0.5-1.5 mm. This tracks note 20's per-episode rectified b/c vertical offset (e5 2.09 / e6 2.03 px -> 0.10 deg;
  e19 0.78 / e20 0.82 px -> 0.05 deg), so it is the per-session b/c extrinsic change, seen GT-free. Size: ~0.1 deg
  x 0.5 m ~ 1 mm at the objects, negligible for AUC.

### C2. GT-free consistency checks on eval clips with VO v2 (`c2_stats.py s5 c2_stats.json` -> `c2_stats.{out,json}`; VO `c3/vo_e*.json`)  [V]
- cam_a vs mono time offset, per clip from the relocalised poses (cam_a own PnP vs c rig, c interpolated at t+lag by
  VO): best lag -1.05..-1.20 frames in 19/20 clips (median a-c rotation spread 0.022-0.045 deg at the best lag vs
  0.12-0.52 deg at lag 0). e20: -1.2 in rows 0-59, then -2.1 from row 60 on. This independently reproduces DIG 20's
  sync table (a[k+1] ~ b[k]; e20 b/c drop at row 48-49 switching to a[k+2]) with a different method.
  => the relocaliser gives a GT-free per-window lag estimate; cam_a poses must be taken as T_ac x c(t + lag).
- VO v2 vs map on eval clips (keyframes every 5 frames):
  - max drift per clip: 4.4-9.1 mm / 0.10-0.50 deg in e10, e14, e15, e16, e28, e30, e37, e38 (7.5-13 s);
    20-83 mm / 0.29-2.40 deg in e1, e3, e5, e6, e8, e19, e20, e25, e32, e33, e35, e36 (worst e35: 82.6 mm / 2.40 deg
    over 21 s; e36 59 mm / 1.21 deg).
  - 5-frame VO bridge vs map: median 0.6-3.5 mm, p95 1.7-12.9 mm; 0.013-0.074 deg (p95 0.035-0.244).
  - Mechanism [V for e35/e1/e5/e10/e14]: (1) VO under-scales head translation by 5-14 % (VO/map translation ratio 0.86-0.95,
    e5 1.02) over head paths of 8-41 cm; (2) a constant VO rotation-rate bias of up to 0.0046 deg/frame (e35, about
    cam x) where note 20 finds a large per-session b/c vertical offset; ~0.0003 deg/frame in e10/e14. Both are VO
    errors that grow with time or path length. The map's absolute 2D-3D solve is immune: the same extrinsic error
    costs it only a constant ~0.1 deg c-only-vs-rig compromise (C1).
  - So the 3 public test clips of stage B (VO drift 5-15 mm) were benign. On eval clips a factory-extrinsic stereo VO
    drifts up to ~8 cm. This is MY VO implementation; a windowed-BA VO with per-session extrinsic self-calibration would
    drift less [E].
- Coverage of the per-frame bridge: keyframes every 5 frames + VO give the c pose at every frame with a bridge error
  <= the 5-frame bridge numbers above (forward/backward blend halves the worst case [E]).

### C4. GT-free gravity and height on eval frames NOT used for the map (`c4_gravity.py s5 c4_gravity.json 50` -> `c4_gravity.{out,json}`; `c4b_map_vs_vo_tilt.py` -> `.out`)  [V]
- Dense SGBM b/c table plane at every 50th frame (t >= 50 never entered the map or the registration), put into mocap
  with that frame's map pose: 116 frames / 20 clips.
  - Tilt of the table normal from mocap +z: median 0.34 deg, p90 0.83, max 2.32 (e6 t150, where a hand/object on
    the table also tilts the VO-based value: a plane-measurement outlier). Per-clip medians 0.18-0.83 deg.
  - Implied table-top height: median 0.6017 m vs GT 0.6012 (public), p10-p90 0.598-0.605; per-clip sd 0.3-2.8 mm.
- Arbiter map vs VO (same camera-frame normals, VO-chained pose instead of the map pose): second half of each clip
  map tilt median 0.32 / p90 0.88 deg vs VO 0.64 / 1.43; VO tilt grows with time in the drifting clips (e35 0.38 ->
  2.71 deg at t400; e5 0.26 -> 2.04; e32 0.32 -> 1.39), while the map tilt stays flat (e35 0.11-0.95).
  => On eval clips the map keeps gravity to ~0.3 deg median and height to ~2 mm throughout, and the C2 VO-vs-map
  divergence is VO drift, not map error. This is the eval-side counterpart of stage B's GT validation.

### C6. Prototype output: per-frame mocap camera tracks for all 20 eval clips (`c6_export.py s5 c2_stats.json c6_tracks` -> `c6_tracks/e*.json`, `c6_export.out`)  [V arithmetic; reads no GT]
- c (mono time base) at every frame: map keyframes every 5 frames, VO v2 bridging with a forward/backward blend.
- a (colour, its own capture time): T_a_from_c (self-calibrated per clip; |t| 3.71-3.92 cm) x c(t + lag(t)), where
  lag(t) = -n + frac. frac -0.05..-0.20 per clip; n chosen per keyframe by a<-c rotation consensus with one optional
  changepoint. Result: n = 1 in 19 clips; e20 switches n 1 -> 2 at frame 50 (field `switch_keyframe` holds a frame index), matching DIG 20's b/c drop at rows
  48-49 without using its table.
- Convention in each file: mocap rotation, gravity and z; x,y in map coordinates (a per-episode constant vs the
  dataset, irrelevant to the slot-0-aligned scorer); R_wc columns = right/down/forward of the undistorted pinhole
  image (a1). 3.1 MB in total.

### C5. AUC value of drift-free camera poses, official scorer functions on public GT (`c5_auc.py s5 c5_auc.json` -> `c5_auc.{out,json}`)  [V simulation; E transfer]
- Method: camera-frame error profiles Delta(t) measured on the 20 EVAL clips (VO v2 vs map, keyframes, Delta(0) = I)
  are applied to the PUBLIC GT trajectories through each public episode's frame-0 map camera:
  X_est(t) = T_wc0 Delta(t) T_wc0^-1 X_gt(t) (lever arm = real camera-object geometry). Scored with the kit's
  `_warp_to_reference_start`, `_object_add`, `_add_auc` (500 surface points per public mesh). 19 public eps x every
  eval profile at least as long as the episode x 2 seeds; episode means, then the board mean.
- Arms: map = iid camera noise 0.015 deg + 0.7 mm per axis (stage B bound); VO = measured eval VO drift; VO/3 and VOx3 =
  the same profiles scaled (a ~3x better VO, about the stage-B public-clip level; a ~3x worse, mono-SLAM-like
  tracker); lin5 = note 02's 5 cm linear common drift (sanity check).
- Contexts: iso = objects otherwise perfect; stackA = note 02's 'careful stereo' errors without drift (anchor 0.5 cm +
  2 deg, 0.5 cm/axis jitter with exact anchor, 2 deg rotation jitter, 1 % scale, slot-1 body 5 deg).

  | arm | AUC iso | AUC stackA | map gain iso | map gain stackA |
  |---|---|---|---|---|
  | map | 1.000 | 0.953 | - | - |
  | VO/3 | 0.991 | 0.942 | +0.009 | +0.011 |
  | VO (measured, factory-extrinsic stereo VO) | 0.896 | 0.856 | +0.104 | +0.098 |
  | VOx3 | 0.557 | 0.537 | +0.443 | +0.416 |
  | lin5 (note 02) | 0.800 | 0.766 | +0.200 | +0.187 |

- Sanity: lin5 iso = 0.7997, matching note 02's 0.799, so this re-implementation agrees with the error budget.
- By drift profile (stackA): +0.00-0.01 for the benign clips (e10, e14, e15, e16, e28, e30, e37, e38) and +0.035-0.24
  for the drifting ones (e5 +0.24, e35 +0.14, e1 +0.13, e6 +0.13, e32 +0.12).
- Reading [E]: the map's AUC gain depends on what it replaces. Against a well-calibrated stereo VO it is ~+0.01
  (inside the 1 cm AUC dead zone). Against the factory-extrinsic VO I actually measured on eval clips it is ~+0.10.
  Against a mono/learned tracker with ~3x that drift it is ~+0.4. The map makes the camera term ~0 by construction
  (iso AUC 1.000), so camera drift drops out of the budget whatever else is used. The map costs ~0.3 CPU-s per frame.

### C8. Public-only map (policy-safe variant; started 01:38, map done 01:59, compared 2026-10-07 08:00)
- `c0_pubonly_map.py run3 6` (copy of b0 with every eval image excluded, 6 threads; log `c0_run3_map.log`, pid in
  `c0_run3.pid`; started 01:38). Next: `venv18/bin/python b2_align.py run3/sparse/0 b2_align_run3.json`, then
  `c1_reloc.py run3/sparse/0 evaluation <ep> c1/r3s25_e<ep>.json 0 25` for all 20 clips (frame 0 is NOT in run3, so
  start-up uses the mean public axis), then `../../venv/bin/python c8_compare.py b2_align_run3.json r3s25 s5`.

### C8 result. Public-only map run3 vs pooled run1 on all 20 eval clips (`c8_compare.py b2_align_run3.json r3s25 s5` -> `c8_compare.out`; `c8b_outliers.py` -> `c8b_outliers.out`)  [V; reads no GT]
- run3 = run1's recipe with all 60 eval images removed: 525/525 images registered, 26.8k points, 1.10 px, 21.5 min.
  It aligns to run1 through the shared public images to 0.58 mm / 0.011 deg median (`b2_align_run3.json`).
- Eval relocalisation against run3 at every 25th frame (217 keyframes; frame 0 is not in the map, start-up from
  the mean public optical axis): coverage 100 %, rig inliers min 527 / median 715 (run1 at the same frames: min
  554). Per-clip wall 15-30 s.
- run3 vs run1 poses at the same frames (run3 mapped into run1): rig rotation median 0.010 deg (p90 0.028, max 0.169),
  position median 0.51 mm (p90 1.33, max 10.4); cam_a median 0.012 deg / 0.77 mm (max 8.1 mm). After removing a
  per-clip constant the time-varying part is 0.1-1.7 mm median per clip.
- The two >= 8 mm disagreements are single-keyframe glitches, one in EACH map (`c8b_outliers.out`): e10 t100 run3
  is 10.7 mm off the midpoint of its run1 neighbours (run1 0.5 mm); e35 t175 run1 is 7.8 mm off (run3 1.4 mm). Both
  have >= 750 inliers, so inlier count does not flag them.
- => Pooling eval frame 0s into the map buys nothing measurable: the policy-safe public-only map gives the same
  eval poses to ~0.5 mm / 0.01 deg and the same coverage. Use run3 as the default (no organiser question needed). Rare
  ~1 cm single-keyframe glitches exist in both maps; the module needs a temporal consistency gate (C9).

### C9. GT-free keyframe consistency gate (`c9_glitch.py s5 5` -> `c9_glitch_s5.out`)  [V; reads no GT]
- For every keyframe t with map neighbours t-5 and t+5, the c pose at t is predicted from each neighbour with VO v2
  relative motion. A glitch = the map pose disagrees with both predictions by > 5 mm while the predictions agree with
  each other to < half that.
- 1,005 keyframes of the 20 eval clips (run1, stride 5): min(dL, dR) median 0.96 mm, p90 3.6, p99 7.9, max 12.4 mm.
  Glitches at 5 mm: 2 (0.20 %): e3 t85 (9.5/7.4 mm, 0.14 deg, 675 inliers) and e35 t175 (8.4/8.4 mm, 0.16 deg, 829
  inliers; the same frame C8 found against run3). At 3 mm: 6 (0.6 %).
- Glitches are 7-10 mm / 0.15 deg with normal inlier counts, so the gate must use geometry, not inlier count. In the
  module: replace a flagged keyframe by the forward/backward VO blend of its neighbours (or re-solve with doubled
  candidates). AUC impact even ungated is negligible (0.2 % of keyframes, < 1 cm, inside the 1 cm dead zone) [E].

### C10. Absolute gravity: B19's proposed leave-session-out test on all 20 public sessions (`c10_gt_up.py` -> `c10_gt_up.{out,json}`; public GT, registration analysis only)  [V numbers, E reading]
- Method: B19's support plane (hull facets within 3 deg of the most downward, area-weighted) of every GT-posed
  object resting on the table (z_min within 2.5 mm of 0.6012, support >= 25 cm2, tilt < 3 deg), every 20th frame:
  151 samples, all 20 sessions. "Lean" = xy of the up normal in deg (GT/mocap axes; a13 shares them).
- Per object: rack (+0.20, -0.60) sd (0.18, 0.08), 4 eps; pot (+0.48, -0.73), 9 eps; blue cup (+0.47, -0.37);
  lid (+0.16, -0.35); wooden piece (+0.13, -0.32); dust pan (-0.15, -0.04); pitcher (+0.05, +0.16). The large
  flat-based scans agree on ~(+0.3, -0.65); small or uneven bases scatter and lean less.
- Per-session medians: mean (+0.30, -0.45) = 0.54 deg; scatter rms 0.48 deg about the mean. Leave-session-out:
  predicting a held-out session by the mean of the others errs 0.38 median / 0.50 rms deg, vs 0.63 / 0.72 for a13's
  "table level in GT" (lean 0). Without the rack: (+0.39, -0.55).
- Verdict on B19's falsifier ("keep a13 if the LSO scatter exceeds the mean"): not met, narrowly (0.48 < 0.54), and
  the LSO error favours the correction by ~0.2 deg rms. => Ship up_GT = a13 up tilted by (+0.30, -0.45) deg, i.e.
  rotate the a13 world by 0.54 deg about the horizontal axis z x n (n = the lean direction). Expected absolute tilt
  error vs the GT world ~0.5 deg per session (was ~0.7 for a13) [E]. Contact-height (a4, 0.40 deg) and this agree in
  direction. The marker-preferred 1.3-2.9 deg (B12b) is not supported by the support planes and stays [H: marker
  chain systematics].
- Scoring impact none (rigid alignment). For physics, the residual ~0.5 deg is ~4 mm across a 0.5 m table; per-clip
  stereo table height and a local plane fit remain the better contact reference.

### C11. Synthetic occluder stress test (`c11_occl.py` = c1_reloc + env `C11_OCC`; `c11_compare.py 35 10 38` -> `c11_occl.out`; `c11b_bins.py` -> `c11b_bins.out`)  [V; reads no GT]
- Grey (128) occluder painted into a, b and c after undistortion, every 25th frame of e35 (task 13, 421 frames), e10
  and e38 (steepest pitch), 35 keyframes, public-only map run3. Reference = the same frames unoccluded (C8 run).
  Runs were serial on a host at load ~40 (another agent's jobs); 5-13 s per clip.

  | occluder | rig ok | rig inliers min / median (unoccluded median 767) | rig dpos median / max mm | drot median / max deg | cam_a ok |
  |---|---|---|---|---|---|
  | central band 50 % width (person in front) | 100 % | 137 / 209 | 1.4 / 9.1 | 0.04 / 0.13 | 100 % |
  | central band 75 % | 100 % | 30 / 64 | 5.2 / 43.6 | 0.10 / 0.55 | 94 % |
  | central band 90 % | 0 % | 0 | - | - | 0 % |
  | lower 67 % of height (hands, objects, table) | 100 % | 349 / 519 | 1.8 / 10.7 | 0.03 / 0.16 | 100 % |
  | left half (operator side) | 100 % | 302 / 378 | 1.5 / 10.1 | 0.05 / 0.14 | 100 % |

- Error vs rig inliers (all occluded runs): >= 100 inliers -> dpos median 1.4-2.4 mm, p90 <= 4.2, max 10.7 mm (the
  max includes C8's run3 glitch at e10 t100 in the REFERENCE); 60-100 -> median 7.3, max 15 mm; 30-60 -> median 6.1,
  p90 28, max 44 mm.
- Reading: the map features live in the upper part and the periphery of the wide b/c views (shelves, walls), so the
  usual occluders (hands and objects in the lower centre; the operator at the left) cost little. The failure mode
  is a large occluder right in front of the cameras covering >= 75 % of the width: inliers collapse and poses
  degrade to cm level before PnP fails outright.
- Design consequence: trust a keyframe only at >= 100 rig inliers (all 1,045 real eval keyframes have >= 554). At
  30-100, use it only if the C9 VO gate agrees. Below 30, bridge with VO and flag the gap. Real eval clips never come
  near this (C1); the test only sizes the margin: the lowest real keyframe (554 inliers) is ~5x the 100-inlier trust
  level and ~18x the 30-inlier PnP floor (median keyframe ~770: ~8x and ~25x).

### C12. Global photometric stress test (`c11_occl.py` with `C11_OCC=g60|g160|s30`; `c11_compare.py g60,g160,s30 35 10` -> `c11_light.out`)  [V; reads no GT]
- e35 + e10, every 25th frame (24 keyframes), run3. g60/g160 = gamma 0.6 (brighter) / 1.6 (darker); s30 = 30 %
  exposure, requantised to 8 bit, plus read noise sigma 2 DN.

  | variant | rig ok | rig inliers min / median (reference 748) | rig dpos median mm | drot median deg | cam_a dpos median / max mm |
  |---|---|---|---|---|---|
  | gamma 0.6 | 100 % | 597 / 718 | 0.30 | 0.01 | 0.48 / 2.0 |
  | gamma 1.6 | 100 % | 572 / 690 | 0.41 | 0.01 | 0.53 / 2.1 |
  | 30 % exposure + noise | 100 % | 487 / 584 | 0.59 | 0.02 | 1.34 / 3.1 |

  (The rig maxima of 10-10.5 mm are the e10 t100 glitch in the run3 REFERENCE, C8.)
- Reading: global exposure/gamma changes are harmless (SIFT normalisation). Not tested: local lighting changes
  (moved lamps, cast shadows, sunlight) and rearranged furniture. The interleaved recording order (C0) and flat
  per-clip inlier counts over the sessions (stage C risk list) suggest the eval sessions share the map's appearance.
  A different room or a rearranged lab would need a new map [H].

### C13. Default module end to end: public-only map run3 at stride 5 + a13 + C10 tilt + C9 gate (`c13_batch.sh`, `c13_to_run1.py`, `c2_stats.py r3s5r1`, `c9_glitch.py r3s5r1`, `c13_export.py` -> `c6_tracks_v2/`; checks `c13_compare.py`, `c8_compare.py b2_align_run3.json r3s5 s5`)  [V; reads no GT]
- Run 2026-10-07 12:26:39-12:34:10 (7.5 min wall, 3 workers, `OMP_NUM_THREADS=2`, host otherwise light): all 20
  eval clips against run3 at every 5th frame, 1,045 keyframes. No eval image is in the map; start-up uses the mean
  public optical axis.
  - Coverage 100 % rig and cam_a. Rig inliers min 500, median 726 (run1 at the same frames: min 554).
  - Cost: 1.24 s per keyframe per process (1,291 s in total) plus VO v2 at 0.057 s per frame (294 s for 5,181
    frames) = 0.31 CPU-s per frame. All 20 clips take ~9.5 min wall with 3 workers.
- run3 vs run1 at the same 1,045 keyframes (`c13_c8_r3s5.out`): rig 0.009 deg / 0.40 mm median, p90 0.020 deg /
  1.0 mm. The only rig difference > 6 mm is the run3 glitch at e10 t100 (10.4 mm).
  - cam_a own PnP disagrees once by 16.6 mm / 0.31 deg (e28). This is why the module derives cam_a from the rig
    (T_ac x c(t + lag)) and uses cam_a's own PnP only for robust per-clip calibration (median/mean).
- C9 gate on run3 (`c13_glitch.out`): 1,005 keyframes tested; min(dL, dR) median 0.95 mm, p99 8.0, max 11.9.
  - At 5 mm: one glitch (0.10 %), e10 t100: 10.7 / 10.2 mm, 0.16 deg, 755 inliers. It is the one C8 found.
  - At 3 mm: 5 (0.5 %), all others 3.4-5.6 mm.
  - `c13_export` rejects e10 t100 and bridges f96-104 by VO (max bridge 5 frames). No other keyframe is rejected
    or needs the gate to be trusted: every keyframe has >= 500 inliers.
- Lag (`c2_stats` on the converted run3 poses, `c13_stats.{out,json}`):
  - The integer pairing equals the run1 prototype in all 20 clips: n = 1, and e20 switches 1 -> 2 at frame 50.
  - The sub-frame part differs by 0.05-0.10 frames (2.5-5 ms) in 8 clips; the lag grid is 0.05 frames.
  - a<-c rotation spread at the chosen lag: 0.019-0.043 deg median. |t_ac| 3.70-3.91 cm.
- Registration actually applied: X = R_tilt (R_a13 X_run1 + [0, 0, t_z] - p) + p.
  - R_tilt = 0.535 deg about z x n, taking +z to the C10 GT up (lean (+0.297, -0.445) deg; checked).
  - Pivot p = the mean gaze point of the 175 public cam_a map images on the table plane (map x,y (-0.500, -0.010),
    z 0.6012), so the table height at the work area is unchanged. A rotation about the map origin (near the head)
    would shift the work-area table height by ~5 mm.
- Default tracks vs the C6 prototype (run1 + a13, no gate) at all 5,181 frames, after undoing the known tilt
  (`c13_compare.out`):
  - c: 0.008 deg / 0.37 mm median, p90 0.018 deg / 0.94 mm, p99 2.5 mm;
  - cam_a: 0.010 deg / 0.47 mm median, p90 0.025 deg / 1.1 mm;
  - the maxima (8.3 mm / 0.17 deg) are at e35 t175, the run1 glitch the prototype had no gate for.
- => The default module (public-only map, C10 gravity, C9 gate, per-clip lag and T_ac) now runs end to end on all
  20 eval clips: `c6_tracks_v2/e*.json` (3.3 MB). Each frame carries c and a poses plus flags: keyframe verdict,
  gate distance, bridge length and rig inliers. It reproduces the pooled-map prototype to ~1 mm p90 without any
  eval image in the map.

## Stage C limitations
- No eval GT. Eval accuracy is inferred from:
  - stage B's public held-out validation (six clips, five tasks);
  - GT-free eval checks: the stereo table plane (C4), map-vs-map agreement (C8) and VO consistency (C9).
  Tasks 12-13 (spoon) have no public GT session at all.
- C5's AUC values are simulations: eval camera-error profiles replayed through public GT with the kit's functions.
  The "VO" arm is MY factory-extrinsic stereo VO. The real gain depends on the tracker the pipeline would otherwise
  use, and on whether its object estimates are camera-relative (drift enters) or anchored to static scene objects
  (drift partly cancels) [E].
- The default module (C13) is exported end to end, but it is a prototype: the VO bridge and lag estimation run as
  separate offline passes over the whole clip (the forward/backward blend and the per-clip lag are not causal).
  `c6_tracks/` (run1 + a13, no gate, no C10 tilt) is kept as the earlier prototype.
- The C9 gate threshold (5 mm) was set from the run1 distribution itself, not tuned on GT.
- Stress tests (C11/C12) are synthetic: uniform grey occluders and global photometric maps on 2-3 clips at stride
  25. A real occluder adds texture and its own spurious matches. Local lighting and furniture changes are untested.
- C10's tilt correction rests on GT-posed scan support planes (scan base flatness and mocap marker-fit errors mix in;
  session scatter 0.48 deg is about as large as the 0.54 deg mean). It is a modest, direction-consistent improvement,
  not a precise gravity.
- Single shared Mac at load ~40 during the re-run; timings are indicative.

## Stage C artifacts (`/Users/aebatirel/Documents/Code/v2d-research/work/18/`)
- Maps:
  - pooled `run1/sparse/0` (A2; bank 133 MB);
  - public-only `run3/sparse/0` (`c0_pubonly_map.py run3 6`, log `c0_run3_map.log`; bank 115 MB) and its alignment
    to run1, `b2_align_run3.json`.
- Relocaliser `c1_reloc.py` (venv18; reads no GT) + `c1_batch.sh <stride> <prefix> <pubonly> <eps>`. The batch script
  hard-codes run1; the run3 runs were launched directly with `run3/sparse/0`. Outputs:
  - `c1/s5_e*.json` (run1, stride 5, logs `c1log/s5_e*.log`);
  - `c1/r3s25_e*.json` (run3, stride 25, logs `c1log/r3s25_e*.log`).
- VO: `c3/vo_e*.json` (`c3_vo_batch.sh`; b3_vo v2).
- Stats and checks:
  - `c2_stats.py` -> `c2_stats.{out,json}`, `c2_novo.{out,json}`;
  - `c4_gravity.py` -> `c4_gravity.{out,json}`; `c4b_map_vs_vo_tilt.py` -> `.out`;
  - `c5_auc.py` -> `c5_auc.{out,json}` (kit scorer functions on public GT).
- Tracks: `c6_export.py` -> `c6_tracks/e*.json` (run1 + a13), `c6_export.out`. `c7/eval_views.jpg` is a montage of
  eval views.
- Re-run additions (2026-10-07 07:55-08:10):
  - `c8_compare.py` -> `c8_compare.out`; `c8b_outliers.py` -> `c8b_outliers.out`;
  - `c9_glitch.py s5 5` -> `c9_glitch_s5.out`;
  - `c10_gt_up.py` -> `c10_gt_up.{out,json}` (public GT);
  - `c11_occl.py` (env `C11_OCC` = c50|c75|c90|b67|l50|g60|g160|s30) -> `c11/<occ>_e{35,10,38}.{json,log}`;
    `c11_compare.py` -> `c11_occl.out`, `c11_light.out`; `c11b_bins.py` -> `c11b_bins.out`.
  - The pre-rewrite copy of this notes file is `notes_backup_before_stageC_rewrite.md`.
- C13 additions (2026-10-07 12:25-12:45):
  - `c13_batch.sh` -> `c1/r3s5_e*.json` (run3, stride 5; logs `c1log/r3s5_e*.log`, `c1log/batch_r3s5.{log,pid}`);
  - `c13_to_run1.py` -> `c1/r3s5r1_e*.json` (`c13_convert.out`); `c2_stats.py r3s5r1` -> `c13_stats.{out,json}`;
  - `c9_glitch.py r3s5r1 5|3` -> `c13_glitch.out`; `c8_compare.py b2_align_run3.json r3s5 s5` -> `c13_c8_r3s5.out`;
  - `c13_export.py r3s5r1 c13_stats.json c10_gt_up.json c6_tracks_v2 5` -> `c6_tracks_v2/e*.json`,
    `c6_tracks_v2/summary.json`, `c13_export.out`; `c13_compare.py c6_tracks_v2 c6_tracks` -> `c13_compare.out`;
  - test outputs on 3 clips: `c13_stats_test.json`, `c13_test_tracks/`; notes copy `notes_backup_before_C13.md`.
- Commands (from `work/18`; bounded with `perl -e 'alarm N; exec @ARGV'`):
  - `venv18/bin/python c0_pubonly_map.py run3 6`
  - `venv18/bin/python b2_align.py run3/sparse/0 b2_align_run3.json`
  - `venv18/bin/python c1_reloc.py run3/sparse/0 evaluation <ep> c1/r3s25_e<ep>.json 0 25`
  - `../../venv/bin/python c8_compare.py b2_align_run3.json r3s25 s5`
  - `../../venv/bin/python c9_glitch.py s5 5`
  - `../../venv/bin/python c10_gt_up.py c10_gt_up.json`
  - `OMP_NUM_THREADS=2 C11_OCC=<occ> venv18/bin/python c11_occl.py run3/sparse/0 evaluation <ep> c11/<occ>_e<ep>.json 0 25`
  - `../../venv/bin/python c11_compare.py [g60,g160,s30] <eps>`
- No downloads. No jobs are left running.

## Next steps (after DIG 18)
1. Plug the tracks into the object pipeline and measure on public held-out clips the end-to-end AUC change against
   the pipeline's own camera tracker. That is the real gain, in place of C5's simulation. For public clips, run the
   C13 chain with each test session's own frames held out of the map (as run2), never with the full run1/run3.
2. Make the module causal if the pipeline needs live poses: forward-only VO from the last trusted keyframe, and a lag
   estimate from the first ~2 s, updated by window. The offline blend stays the final-trajectory variant.
3. D19/D20: use the per-clip lag (C2/C6) for cam_a-time-based predictions. Confirm the GT-vs-camera lag (B6) before
   shifting submission timing.
4. Optional: a stride-1 relocalisation of the drifting clips (e5, e35, e36, e1, e6, e32), if bridge mm matter. Also a
   real-occluder test on a public clip with a person close to the camera, if one exists.

