# Spoon flip check on the eval references (report-only)

Pre-registered rule: `../PREREG_spoonflip.md`. Script: `../scripts/spoon_flip.py`. Overlays: `../scripts/spoon_overlay.py`.
Ground truth: none was read (these are eval episodes). Inputs are the packed reference poses, our stereo depth, our video
masks and our hand joints. Nothing was changed: this is a report only.

For each frame, the packed reference spoon pose (REF) is compared with two 180° alternatives about the template's
bounding-box centre:
- ROLL: rotation about the long axis;
- YAW: rotation about the face normal, which swaps the bowl and handle ends.

An alternative "wins" a frame when it beats REF on IoU against the spoon mask (+0.10) without being worse on the depth
residual by more than 0.3 cm, or when it beats REF on the depth residual (−0.5 cm) without losing more than 0.05 IoU.
Spans need at least 5 winning frames; gaps of up to 2 frames are bridged.

## Result [M]

| eval | scored frames | REF IoU (median) | REF depth residual, cm (median) | ROLL win frames | YAW win frames | flagged spans |
|---|---|---|---|---|---|---|
| 3 | 313 | 0.763 | 0.72 | 2 | 0 | none |
| 5 | 288 | 0.727 | 0.79 | 0 | 0 | none |
| 6 | 243 | 0.746 | 0.77 | 0 | 0 | none |
| 15 | 166 | 0.707 | 0.53 | 0 | 0 | none |
| 16 | 173 | 0.705 | 0.57 | 2 | 0 | none |
| 32 | 259 | 0.633 | 0.87 | 10 | 2 | ROLL f104–110 (7) |
| 33 | 348 | 0.615 | 0.99 | 7 | 16 | YAW f184–190 (7), f268–272 (5) |
| 35 | 421 | 0.735 | 0.72 | 1 | 0 | none |
| 36 | 407 | 0.731 | 0.80 | 26 | 7 | ROLL f73–87 (15), f112–122 (11), f295–299 (5) |
| 37 | 151 | 0.749 | 0.79 | 0 | 0 | none |

Over whole episodes the alternatives are worse than REF in every episode:
- YAW median ΔIoU is −0.13 to −0.28;
- ROLL median ΔIoU is −0.003 to −0.053.

The flags cover 50 of 2,769 scored frames (1.8 %).

### Means inside each flagged span [M]

| eval | span | alternative | REF IoU | alternative IoU | REF residual, cm | alternative residual, cm |
|---|---|---|---|---|---|---|
| 33 | f184–190 | YAW | 0.44 | 0.45 | 114.2 | 105.2 |
| 33 | f268–272 | YAW | 0.31 | 0.33 | 79.6 | 53.5 |
| 32 | f104–110 | ROLL | 0.25 | 0.25 | 81.4 | 76.4 |
| 36 | f73–87 | ROLL | 0.38 | 0.46 | 7.0 | 3.3 |
| 36 | f112–122 | ROLL | 0.23 | 0.31 | 11.4 | 8.5 |
| 36 | f295–299 | ROLL | 0.58 | 0.59 | 4.2 | 1.2 |

## Reading the overlays [I]

In the overlays, green is the REF outline, red is the alternative, the tint is our spoon mask, and the dot marks the
template's +long-axis end.

- **Eval 33, YAW (`overlays/eval33_YAW.jpg`, f182/187/190/270).** Not a flip.
  - The mask's wide bowl is at the end where REF puts it.
  - The REF spoon is displaced along the handle: the mask extends one handle or bowl length beyond REF, past the hand
    (f187, f190) and up-left (f270).
  - Depth residuals of 50–110 cm show that both poses project onto the background. Both are wrong by the same
    translation, and YAW only wins on noise.
  - This is the along-handle offset already reported in the eval audit (`../audit/README.md`).
- **Eval 32, ROLL (`overlays/eval32_ROLL.jpg`, f100/104/107/110).** Not a flip.
  - REF and ROLL silhouettes almost coincide.
  - Both are smaller than the mask, and the mask's handle continues past the hand. The residuals (~80 cm) show the
    reference sits off the spoon.
  - This is a position or depth offset (the eval 32 moderate offset from the audit), not a flip.
- **Eval 36, ROLL (`overlays/eval36_ROLL.jpg`, f75/80/85/118).** Possibly a partial roll error; weak evidence.
  - The silhouettes almost coincide and both follow the mask.
  - ROLL is ~3 cm closer in depth and +0.08 IoU better.
  - A 180° roll of a shallow spoon mostly moves the bowl's concavity, which is near our stereo-depth noise on a thin
    object. Two of the three spans (f77–85, f112–122) also coincide with gaps in our mask found in the audit.
  - At f118 the mask extends past both ends of REF, so there is also some translation.

## Verdict

- No span shows a clear 180° flip of the reference spoon.
- The two strong-looking flags (evals 32 and 33) are translation offsets where both REF and the alternative miss the
  spoon.
- Eval 36 ROLL f73–87 / f112–122 / f295–299 (31 frames) is the only candidate. The evidence is weak and comes from
  depth only, so it is not actionable without an independent check, such as a texture-based bowl-side test.

Hypothesis [H]: eval 36's spans are a real roll error, not depth noise. The falsification run I first proposed (the
same rule on public episodes with known spoon poses) is not possible: no public episode has a spoon (coordinator,
08:26 UTC). The coordinator closed this: 31 weak frames (~10 % of the episode) cannot fail SP-SR on their own.
