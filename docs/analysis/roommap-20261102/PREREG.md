# Pre-registration: room-map camera relocalisation vs perc2's keyframe PnP (2 Nov 2026, room-map session)

Written and pushed before any drift number or score of the map variant exists (the map was not yet built when this
was written). Labels: [M] measured, [E] estimate, [H] hypothesis, [L] literature.

## Hypothesis [H]
perc2's camera tracker (keyframe SIFT + FoundationStereo-depth PnP chained over keyframes, no map, no BA) drifts on
the longer eval clips. Every object's world trajectory inherits that drift (static objects included); the scorer's
single frame-0 rigid alignment does not remove it. Relocalising the c camera at every frame against a public-only
room map (note 18, rewritten GT-free in `pipeline/roommap.py`) removes the drift and raises AUC / lowers MPPE.
Falsifier: the map variant does not beat the control on public episodes (leave-out maps), or perc2's eval drift vs
the map is inside the ~1 cm AUC dead zone.

## Method (fixed now)
- Map: `pipeline/roommap.py` = note 18's run3 recipe on the ego b/c pair only: every 30th frame of the 20 public
  videos, undistorted pinhole f = 420, note-18 masks, SIFT first_octave -1 / 6000, pairs = within-episode + all
  frame-0s + 12 random cross-episode partners (seed 0), incremental SfM with the b/c factory extrinsic as a fixed rig.
  No eval frame enters any map. No GT anywhere (the parquets are never opened by roommap.py).
- Relocalisation: every frame (stride 1), b/c generalized PnP (6 px), >= 30 inliers, 20 candidate map images nearest
  the previous optical axis (retry with 40). Temporal gate (GT-free): a frame whose position deviates > 5 mm from the
  interpolation of trusted neighbours within +-5 frames (and > 2x the local median deviation + 2.5 mm) is replaced
  by interpolation; failed frames likewise.
- Composition (perc2 world kept at frame 0): map_T_rect(t) = map_T_c(t) . rect_T_c^-1 (rect_T_c = perc2's R1);
  W_map(t) = map_T_rect(0)^-1 . map_T_rect(t); world_T_obj(t) = W_map(t) . cam_T_obj(t) (perc2's own object poses).
  Nothing else is changed (detection, tracking, track guard decisions stay as run).
- Public leave-out: 5 fold maps, fold k = PUBLIC[k::5]
  (k0: 0 18 26 41; k1: 2 21 27 42; k2: 11 22 31 43; k3: 12 23 39 44; k4: 13 24 40 45);
  a test episode is relocalised only against the map that excludes all its frames. Eval clips use the full public
  map `run3` (all 20 public episodes).
  PUBLIC = 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45.
- Control: perception-tracking's control C (runs/20261102-ptrkA-7fbc3215 and -ptrkB-7fbc3215, results/ptrk/C,
  commit 7fbc321), its own poses.npz. Variant = the same cam_T_obj recomposed with W_map.
- Scoring (diagnostic, after inference, the only place mocap is read): `pipeline/score_registered.py` with the
  pack 9a+ meshes (md5 = posefix inputs.json, 10/10 checked), public scans, kit metric code. Harness check: control
  ep12 = 0.9584, equal to perception-tracking's gate table [M].

## Measurements
- (a) Eval, GT-free: per clip and object, |W_perc2(t) p(t) - W_map(t) p(t)| (p = perc2's object position in the
  camera, mm) and the camera rotation gap (deg); median / p95 / max over frames. Source: runs/20261025-evperc-4f596df
  (commit 4f596df). Which perception run fed each pack-12c reference is checked and reported separately.
- Camera-term bound, GT-free: 1 - AUC(perc2 world vs map world) with the kit's frame-0 warp, ADD and AUC functions
  (9a+ mesh surface samples; no symmetry, so a slight over-estimate for cups). Mean over clips = the bound on what
  the camera fix can add, if the map were exact. Computed on eval clips and on public episodes.
- (b) Public, vs mocap: ΔAUC, ΔMPPE, ΔRPE per episode (variant - control), 20 episodes (ep23 has no control result
  on the store; it is reported as missing if so).

## Gates (fixed now)
- G0 map quality (GT-free): relocalised (>= 30 inliers) on >= 99 % of frames of every clip; gate-rejected < 2 %.
  A clip failing G0 keeps perc2's camera (fallback) and is reported.
- G1 build bar for step 2: eval camera-term bound, mean over the 20 eval clips, >= 0.01.
- G2 adoption (public, leave-out maps, vs control C):
  1. no episode ΔAUC < -0.01;
  2. mean ΔMPPE <= 0;
  3. mean ΔAUC >= +0.005, or, if the public camera-term bound (mean) is < 0.01, mean ΔAUC >= max(0, 0.3 x public bound).
  Step 2 (eval recomposition, reference rebuild list) proceeds only if G1 and G2 pass.
- Step 2 materiality threshold (fixed now, before any eval drift is seen): an eval episode is listed for a reference
  rebuild only if some object's world trajectory moves by >= 10 mm (p95 over frames) between perc2's camera and the
  map camera. 10 mm = the AUC's dead zone scale (note 18 C5 / note 02) [E].
- Reported regardless of outcome; nothing is tuned after the scores are read. Any change would be a new, versioned
  PREREG.

## Cost
$0: this container (4 CPU). Map build ~1 h, relocalisation ~1 s/frame [E] (~5,200 eval + ~4,900 public frames).
