# ep23: the board loss is an identity swap hidden by the frame-0 scene alignment (2 Nov 2026, point-track session)

Diagnostic of the public control ptrkD "Cr" (code 95cecd7; tracker 7fbc321). Mocap read after inference, for diagnosis
only. Labels: [M] measured, [D] public vs mocap, [I] inference.

## Evidence
- Control score [D]: AUC 0.0418 (piece_1 0.084, piece_2 0.000), MPPE 16.4 cm (score_registered.py, public scans).
- Displacement from frame 0, cm, every 10 frames [D]:
  - ours piece_2: 0, 0.1, 0.6, 7.7, 8.0, 10.8, 12.8, 10.2, 11.2, 13.4 …
  - mocap piece_1: 0, 0.0, 0.8, 7.7, 8.1, 11.6, 11.9, 9.9, 10.8, 13.2 …
  - ours piece_1: ≈ 1 cm until f120, then 3.8, 11.0, 13.1, 22.1
  - mocap piece_2: ≈ 0 until f120, then 3.3, 10.3, 22.6, 22.9
- All-frame rigid fit of our positions to mocap (diagnostic) [D]: names as tracked, median residual 7.8 / 7.4 cm;
  names swapped, 3.2 / 5.0 cm.
- GT-free [M]: KLT point tracks on our depth agree with FoundationPose's motion for both boards while they hold (piece_2
  7.6 / 10.8 / 12.9 cm at f30 / 50 / 60). The tracker follows the physical boards; the names are crossed.
- Separation alone cannot show this: it is symmetric under a swap (ours 26.6 cm, mocap 27.9 cm at f0). The scorer's
  frame-0 scene alignment on the first object makes the swapped scene look right at f0 (errors 0.0 / 2.5 cm).
- A plain name swap scores 0.036: each pose carries its own mesh's orientation (slot side), so a relabel is not a fix.

## Consequence
- [I] A point-track second opinion cannot repair identity; ep23 is not a target of the point-track test.
- perception-tracking (18:12 UTC) found that the existing GT-free knob rule `pipeline/identity_fix.py` fixes this
  control: 0.041 → 0.663 (swapped + Rx flip); ep24 untouched. It ran only in the eval pipeline (eval 25 already uses
  it), never on the public controls: a wiring gap, not a new failure.
