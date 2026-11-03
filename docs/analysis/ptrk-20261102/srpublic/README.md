# SP-SR / MP-SR of public tracks against mocap, per object (diagnostic, report-only)

Pre-registered in `../PREREG_srpublic.md` (commit b4f5c1e6) before scoring. Script: `../scripts/sr_public.py`.

| | |
|---|---|
| Tracks | eval-default control C, with identity_fix on ep23 |
| Meshes | 14p choice for public objects (`m14pub`) |
| Scoring | kit registration, conversion and frame-0 alignment; kit symmetry-aware orientation error; all frames; 10 registration seeds |
| Ground truth | mocap, read by scoring only |

Per-episode JSONs are `ep*.json`; the table is `summary.txt`.

## Result [M]

17 of 20 public episodes pass both SP and MP in all 10 seeds. Of 40 object-episode pairs, 37 pass MP; the failures are:

| ep | object | mean pos (cm) | mean ori (°) | MP seeds | SP seeds | dominant term | type |
|---|---|---|---|---|---|---|---|
| 23 | wooden_piece_2 | 7.6 | 86.0 | 0/10 | 0/10 | orientation | **FLIP** |
| 21 | water_pitcher | 3.4 | 3.0 | 0/10 | 10/10 | position | STEADY |
| 22 | water_pitcher | 2.9 | 2.8 | 7/10 | 10/10 | position | STEADY |
| 24 | both boards | 2.3 / 2.1 | 2.5 / 2.8 | 9/10 | 9/10 | registration seed | see below |

Notes on the failures:

- **ep23 wooden_piece_2: FLIP.**
  - Orientation error is above 135° on f168–199 and f226–324, 41 % of frames.
  - The error rotation is about the board's long axis; the median error is 174°.
  - It is a 180° roll of a near-symmetric flat board: the tracker keeps the outline and loses which face is up.
  - Frame 0 is correct (1.8°), and the identity fix had already removed the swap.
  - The same 180° flip shows up in all 10 seeds, so it is in the track, not the registration.
- **Pitcher (ep21, ep22): STEADY.**
  - The track carries a steady body-frame position bias of 3–3.4 cm, just over the MP 3 cm limit.
  - Orientation is fine (3°).
  - This is the bias that the eval-20 depth placement (pack 13p2) addresses.
- **ep24 boards: registration seed.**
  - In 9 seeds both boards pass, with position about 2.0–2.4 cm: about 75 % of the MP limit, the thinnest margin of
    any object.
  - In seed 6 the registration of piece 1 turns 180°. The frame-0 scene alignment uses object 0, so both objects then
    fail (135° / 178°).
  - This is a scorer-side registration flip. The D1 check covers it for the pack meshes at the eval seed.
- **Every other object type passes MP on every public episode**, with position 0.3–2.0 cm and orientation 1–12°:
  - white_pot (9 episodes);
  - lid (2);
  - blue_cup (5);
  - beige_cup (1);
  - dish rack (5);
  - sweeper (2);
  - dust pan (3);
  - wooden_piece_1 (2).

## Mapping to eval (GT-free prior) [I]

The eval losses are 2 SP and 4 MP worlds or episodes (coordinator). SP fails only when the per-object mean
orientation reaches 0.5 rad or the mean position reaches 10 cm. On public, only a FLIP-type error produced that.

| failure type seen on public | object | eval episodes with that object | prior |
|---|---|---|---|
| 180° roll flip of a near-symmetric flat board (masks and depth cannot see it) | wooden_piece_2 (and _1 by shape) | **25** | most likely SP and MP loss |
| Board registration flip at some seeds / thin MP position margin | wooden pieces | **25** | MP risk; D1 covers the eval seed |
| Steady 3 cm position bias | water_pitcher | **20** | MP risk; 13p2 placement aims at it |
| No public data | wooden_spoon | 3, 5, 6, 15, 16, 32, 33, 35, 36, 37 | unknown; the audit saw 4–8 cm offsets on 32 / 33 |
| Passes on public | pot, lid, cups, rack, sweeper, dust pan | 1, 8, 10, 14, 19, 28, 30, 38 | low |

Reading: the public tracks fail only on the boards (flip), the pitcher (bias) and the boards' registration margin.

- Evals 25 and 20 are the strongest priors.
- The ten spoon evals are the main unknown: there is no public spoon episode, so the prior cannot be measured.
- An unseen 180° roll of a board is exactly the kind of error our eval audit could not detect: the outline is the
  same and the face depth is near-planar.

Hypothesis [H]: eval 25 carries a board roll flip in at least one span. A check that would falsify it without GT:
compare the faces of the board in the video (texture or knob side) with the face the reference shows. The knob is
already used by identity_fix to tell the pieces apart.
