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

## Step 1: what ep23 board 2's error is (public, diagnostic) [M]

Overlay: `overlays/public23_track_vs_mocap.jpg`. It shows the tracked board 1 (blue) and board 2 (red), and the mocap
board 2 (green, the scan mesh), placed relative to tracked board 1 through the mocap 1→2 pose. It covers f100, 180,
235, 250, 300 and 324.

- f100: the board-2 track matches mocap.
- f180 and f235: the board-2 track is lost in the hand area while the real board 2 is elsewhere. This is the
  position-error span f146–244.
- f250–324: the task's end state is a **cross**. Board 1 stands on its edge, and board 2 lies flat across it,
  perpendicular.
  - **Our board-2 track collapses onto board 1**, so both tracks sit on the standing board.
  - The two centres coincide at the joint. That is why the position error stays under 3 cm while the orientation is
    ~180° off about the thickness–long diagonal.
- So ep23's SP/MP failure is a **track merge onto the partner board at assembly**, not a face flip.

## Step 3: eval 25's audit flag, re-read [I] (from overlays; no GT exists)

Overlays: `overlays/eval25_ref_f150-355.jpg` (f150, 200, 230, 260, 330, 355) and `../audit/overlays/eval25.jpg`
(f20, 100, 170, 300). The outline is the packed 14p reference; the tint is our mask.

- The reference board 2 (blue outline) sits on the real white board in every frame checked:
  - on the table (f20 and f150);
  - in the hand (f100, f170, f200, f230 and f260), with the knob dots inside the outline;
  - **in the final cross (f300, f330 and f355), lying flat across the upright board 1**.
- At f355 the mask finally covers board 2, and the reference matches it.
- The audit's LOST spans (f0–115, f146–202, f325–329) are frames where our board-2 mask is empty or partial. The
  original call (mask failure) stands.
- The ep23 merge-at-assembly failure **does not recur in the eval-25 reference**.
- Face orientation cannot be confirmed without GT. The knobs visible at f150 and f200 fall inside the reference
  outline on the expected side; there is no sign of a flip.

## Step 2: v2 rule, not run

By the coordinator's condition, the v2 rule runs only if steps 1 and 3 suggest a recurring failure, and they do not:
- ep23's failure is a merge onto board 1 at assembly;
- eval 25's reference keeps the two boards apart through the assembly.

The v2 rule is therefore not run. The 2 SP / 4 MP eval losses are not explained by a gross board-reference failure
visible in the video. Board error below the visible level, about 2–3 cm (see the thin ep24 MP margin in
`../srpublic/`), remains possible.
