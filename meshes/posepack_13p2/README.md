# meshes/posepack_13p2 — eval-20 water pitcher placed from depth, for pose pack 13p2 (2 Nov 2026)

`water_pitcher.glb` is a byte copy of claude/perception-tracking-20261102 @ 0b067405:
meshes/pose_pack_13p2/eval20_water_pitcher_placed.glb, md5 fb2cb7eaac66699a33d2ec772732bafd. It goes on eval 20, slot 1 only.
- It is the 13p / 13f pitcher payload (decoded, 4,096 faces) with the placement Δ already applied: 2.89°, 0.47 cm; the
  matrix is in the source README and place_fit_ep20.json. Pack it as is (transform none).
- **GT-free fit** (docs/analysis/ptrk-20261102/scripts/place_fit.py): eval-20 stereo depth inside SAM2 video masks over
  rest segments, in the body frame of the packed eval-20 reference. Trimmed RMS 3.81 → 2.57 mm.
- The procedure was **selected by public pose CV** (PREREG_posemesh.md Part 2; mocap of public episodes, development):
  held-out +0.106 (ep21 +0.133, ep22 +0.080). Nothing on eval was scored.
