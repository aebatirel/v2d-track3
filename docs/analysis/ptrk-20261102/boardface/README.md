# Board-face check: the cue fails public validation, so there is no eval-25 verdict

Pre-registered in `../PREREG_boardface.md` (commit 785cbc93) before scoring.
- Scripts: `../scripts/board_face.py` (per-frame scores) and `../scripts/board_face_cal.py` (calibration).
- Per-frame scores: `pub23.npz`, `pub24.npz`. Calibration table: `calibration.txt`.

## Calibration on public [M]

The cue is the identity_fix knob score per frame: REF vs ROLL (180° about the long axis), median over 5 frames, spans of
≥ 5 frames. Truth comes from mocap: orientation error > 135°, which is ep23 board 2 at f168–199 and f226–324.

| τ (grey) | false-flag frames (bar ≤ 5 %) | recall of flipped frames (bar ≥ 50 %) |
|---|---|---|
| 3 | 16.4 % | 24.6 % |
| 8 | 10.5 % | 24.6 % |
| 12 | 6.7 % | 24.6 % |
| 20 | 5.2 % | 23.8 % |

- **No τ passes, so per the pre-registration no eval-25 verdict is given and eval 25 was not scored.**
- The cue does find ep23 board 2's flip at f172–194 and f231–239.
- It misses f240–324: REF scores darker than ROLL there.
- It false-flags:
  - ep24 board 2 at f178–274, where mocap says the board is correct;
  - parts of ep23 board 1.

## Why it fails [M], then [I]

The error rotation of ep23 board 2's track against mocap (seed 0, scan frame, which is aligned with our mesh frame
to within 2°):

| frames | error angle | error axis (abs. cos to thin / mid / long) |
|---|---|---|
| 172–194 | 175° | 0.55 / 0.65 / 0.52 (mixed) |
| 231–239 | 141° | 0.20 / 0.22 / **0.96**: long-axis roll |
| 240–280 | 174° | **0.72** / 0.05 / **0.69** |
| 281–324 | 175° | **0.72** / 0.03 / **0.69** |

- Only f231–239 is the long-axis roll this test looks for.
- For f240–324, the longest part, the error is a ~180° turn about the axis halfway between the board's thickness and
  long axes. That turn exchanges the long and thickness directions.
- [I] So the tracked board there is not "the same outline, wrong face". It is a different, possibly perpendicular,
  placement that happens to stay within 3 cm of the true position. This is plausibly the end state of the
  two-board task, with the pieces stacked or slotted.
- A face test with ROLL / Ry alternatives cannot express this error. The knob score is also unreliable while the board
  is in the hand: it false-flags ep24 board 2.

Correction to `../srpublic/README.md`: its description of ep23 board 2 as "a 180° roll about the long axis" is
imprecise. The pooled axis was 33° off the long axis. The per-span breakdown above replaces it.

## Next steps (proposals, not run) [H]

1. **Look first (public, diagnostic).** Overlay public ep23 board 2 at f250 and f300, track vs mocap, to see the true
   configuration. If the pieces are assembled perpendicular, this one diagnostic shows what failure mode eval 25 can
   have.
2. **v2 rule (public-validated first).** Alternatives: the 180° turns about the thin, mid and long axes and the
   thin–long diagonal. Score: silhouette IoU against the board mask, plus depth, restricted to frames with the hand
   away from the board.
   - Falsifier: it must flag ep23 f240–324 and stay quiet on ep24.
   - Only if it passes, apply it frozen to eval 25.
3. **Revisit the eval-25 audit.** The audit put eval 25 board 2 at the top by severity and called it a mask failure.
   Re-read that call against (1).
