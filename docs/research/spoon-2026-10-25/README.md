# Spoon diagnosis, 25 Oct 2026 (CPU, GT-free)

The spoon is in 10 of the 20 eval episodes; its truth gap (≈ 0.12 of the 20-episode AUC, inferred in
`docs/analysis/eval-20261024-low-scores.md` §5) is the largest single loss. No public episode has the spoon with mocap,
so nothing here can be checked against ground truth.

## How the kit scores it [C, `metric_code/track_3/AUC.py`]
- Our mesh is registered to the hidden scan geometrically (`_register_object_body`: scale by surface radius, PCA starts,
  ICP), so our template's frame convention does not matter.
- `_align_registered_scene` then rotates and shifts the WHOLE achieved scene so that the anchor object's frame-0 pose
  matches the truth exactly. Anchor = the lowest slot without a symmetry axis (cups and the lid have axes).
- The spoon anchors **evals 32, 33, 35, 36, 37**; the pot or rack anchors 3, 5, 6, 15, 16.

## Sensitivity [M, kit functions, `spoon_anchor.py`, output `spoon_anchor.out`]
Truth := our reference with the spoon rotated in its body frame by ε for all frames; achieved := our reference.

| episodes | roll about the handle 10° / 20° / 30° | tilt of the handle axis 10° / 20° / 30° |
|---|---|---|
| 3, 5, 6, 15, 16 (pot/rack anchor) | 1.00 / 1.00 / 1.00 | 0.97 / 0.91 / 0.78 |
| 32 (spoon anchor) | 0.72 / 0.34 / 0.11 | 0.73 / 0.34 / 0.11 |
| 33 | 0.75 / 0.39 / 0.19 | 0.74 / 0.41 / 0.21 |
| 35 | 0.77 / 0.43 / 0.19 | 0.95 / 0.81 / 0.67 |
| 36 | 0.83 / 0.55 / 0.31 | 0.87 / 0.61 / 0.37 |
| 37 | 0.91 / 0.81 / 0.78 | 0.99 / 0.97 / 0.94 |

A roll error is harmless to the spoon itself (it is thin) but, when the spoon anchors the scene, the frame-0 roll
rotates every later position of the trajectory.

## How large is our frame-0 error likely to be [M]
- Physics: our reference spoon at frame 0 lies within 0.4–0.7° (median over rest frames) of a statically stable rest
  of our mesh. But the mesh has three nearly equal stable rests ~14° apart in roll (margins 0.3–2.3 mm), so the
  physics cannot pick the roll.
- Raw tracker (perc2) during the rest before the first motion: roll jitter sd 1.4–2.4°, range 7–12°; the raw frame 0
  is often the outlier (+7.5, +2.8, +9.6, −3.5, −3.1° from the rest mean for 32, 33, 35, 36, 37).
- Reference frame 0 vs the raw rest mean: roll +1.1, +0.6, +2.8, −6.0, −5.2° (36 and 37 likely snapped to another
  stable facet). So the random part is ~2–6°, costing ≈ 0.03–0.15 per spoon-anchored episode; a systematic roll bias
  of the tracker or of the template is not measurable without ground truth.

## Next (proposed)
1. **Public validation of a rest-averaged anchor pose** (CPU, uses mocap only to score): on public twins, re-score the
   stored rollouts with the achieved frame-0 orientation of the ANCHOR replaced by (a) the reference's, (b) the raw
   tracker's rest-averaged orientation. If (b) scores higher on most public episodes, rest-averaging becomes the rule for
   every anchor (all 20 eval episodes) and the eval policies are re-evaluated on the updated references (GPU minutes, no
   retraining). Rule to be written before the run.
2. Spoon position/depth (H2): stereo depth of the spoon pixels vs our track depth, on eval frames (no GT).
