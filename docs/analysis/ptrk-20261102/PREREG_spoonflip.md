# Pre-registration: spoon 180° flip check on the packed eval references (3 Nov 2026, 08:25 UTC)

Coordinator's hypothesis [H-spoon] (keen-heisenberg, 08:19 UTC). Report-only, GT-free, CPU, $0. Written before any
run.

## Inputs
As in the eval audit:
- the 14p packed references (refs_14p.json);
- box H's SAM2 masks (`runs/20261103-ptrkH-ad13d06`);
- eval stereo depth;
- library_v3 `wooden_spoon` template.

Episodes: every eval episode with a wooden_spoon: 3, 5, 6, 15, 16, 32, 33, 35, 36, 37.

## Alternatives
Spoon body axes from the template's principal axes:
- long axis L (largest extent);
- normal N (smallest extent, the bowl's face normal);
- centre c (bounding-box centre).

For a reference pose X:
- **ROLL** = X · F_L, a 180° rotation about L through c (the bowl faces the other way);
- **YAW** = X · F_N, a 180° rotation about N through c (bowl and handle ends swap).

## Per-frame scores (frames where the spoon mask has ≥ 150 px, hand pixels removed)
For each pose P ∈ {REF, ROLL, YAW}:
- IoU(P) = IoU of the projected template silhouette with the spoon mask;
- RES(P) = median |z_obs − z_point| (cm) over template surface points visible in depth (z_obs > z_point − 2 cm).

## Flag rule (fixed now)
- An alternative A **wins** at a frame if either
  - IoU(A) ≥ IoU(REF) + 0.10 and RES(A) ≤ RES(REF) + 0.3, or
  - RES(A) ≤ RES(REF) − 0.5 and IoU(A) ≥ IoU(REF) − 0.05.
- A **flip span** is ≥ 5 consecutive frames where the same alternative wins (gaps ≤ 2 frames are bridged).

## Report
- Per episode: spans, lengths and the alternative, plus the share of the episode flagged.
- Overlays (REF vs alternative outline over the mask) for every span.
- [I] Expected sensitivity: a YAW flip moves the bowl to the other end and should show in IoU. A ROLL flip changes only
  the bowl's concavity (≈ 1–2 cm deep), near our stereo depth noise, so a ROLL "no flag" is weak evidence.
