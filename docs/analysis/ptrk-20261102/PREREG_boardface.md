# PREREG: board-face check on eval 25 (GT-free), calibrated on public ep23 / ep24

Written 2026-11-03 08:58 UTC, before any score below was computed. The coordinator asked for it at 08:50 UTC, after the
public SP/MP-SR diagnostic (`srpublic/`) found ep23 board 2 rolled 180° about its long axis.

## Cue

The cue is the existing identity_fix knob score (`pipeline/identity_fix.py`, unchanged).
- The library_v3 board meshes carry the mocap marker knobs on one face: piece 1 has four on +x, piece 2 three on −x.
  x is the thickness axis; z (23 cm) is the long axis.
- For a camera-frame pose X, the knob vertices on the camera-facing side are projected into the rectified ego_cam_c
  frame. The score is s(X) = mean knob grey − mean plate grey (darker knobs: more negative). It is 0 when fewer than
  5 knob vertices face the camera.
- Alternatives:
  - **ROLL = X·Rz**: 180° about the long axis, which flips the face. This is the main test.
  - **Ry**: the other face flip; reported only.
- Per-frame difference d(t) = s(ALT) − s(REF), median-filtered over 5 frames.
- A frame is flagged when d(t) < −τ.
- Spans: flagged frames bridged over gaps of ≤ 2 frames, kept when they have ≥ 5 frames.

## Calibration on public (diagnostic; mocap labels only)

- Tracks: the tracksT control. ep23 is identity-fixed; its camera-frame poses come from `poses.npz`.
- Truth: from `srpublic` seed 0, a frame is FLIPPED when the orientation error is > 135°. These are ep23 board 2
  f168–199 and f226–324.
- Grid τ ∈ {3, 5, 8, 12, 16, 20} grey levels. τ* is the smallest τ where:
  - false-flag frames are ≤ 5 % of non-flipped frames, pooled over ep23 board 1, ep23 board 2 (non-flipped frames)
    and ep24 boards 1 and 2; and
  - recall is ≥ 50 % of ep23 board 2's flipped frames, counted at the span level after the span rule.
- If no τ passes, the cue fails validation. Then no eval verdict is given, and that is reported.

## Eval 25 (frozen τ*)

- Reference: the packed 14p reference (refs_14p, md5 71ac95f3…), mapped to the camera frame as in the audit:
  inv(world_T_cam) · inv(T_table) · ref.
- Report the flagged ROLL spans per board, with lengths and overlays (REF vs ROLL knob projections over the frame).
- A real flip means a span flagged under τ*, with overlays showing the knobs where ROLL puts them.
- A real flip leads to a fix proposal: flip those spans in the reference, with a ramp at contacts. It is handed to
  perfect-following for a pre-registered eval-25 re-evaluation. No pack or reference is changed here.
- No τ or rule change after the eval result.
