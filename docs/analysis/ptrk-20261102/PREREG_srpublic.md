# PREREG: SP-SR / MP-SR of public tracks against mocap, per object (diagnostic, report-only)

Written 2026-11-03 08:35 UTC, before any number below was computed. The coordinator asked for this on 3 Nov, 08:31 UTC.

**Why.** All 20 stored 14p rollouts pass SP-SR and MP-SR against our own references (perfect-following,
`docs/analysis/sr-vs-ref-20261103`). So the eval failures (board: 2 SP, 4 MP) come from the references' error against
the truth. Public tracks show which object and situation types produce that error.

**Inputs.**
- Tracks: `tracksT`, the eval-default control C (library_v3, TRACK_GUARD), with the identity_fix applied on ep23.
  These are the tracks behind CV round 3.
- Meshes: `m14pub`, the 14p mesh choice for public objects.
- Episodes: all 20 public episodes.
- Mocap is read by the scorer only.

**Scoring.**
- The same path as `pipeline/score_registered.py`:
  - kit `_register_object_body` and `_convert_object_body`;
  - scan-anchor stand-in;
  - `_align_registered_scene` at frame 0;
  - the kit's symmetry-aware orientation error (cups: axial; lid: order 2).
- All tracked frames, 10 registration seeds (seed + 7919·k), one world.
- Per seed, per episode: mean-over-frames position error p (m) and orientation error o (rad) per object.
- SP pass: mean over objects of p ≤ 0.10 and mean over objects of o ≤ 0.5.
- MP pass: every object has p < 0.03 and o < 30°.
- Reported per episode and object: p and o (seed means), SP and MP pass rate over seeds, and the per-object MP pass
  rate.

**Classification (fixed now), for each object that fails MP in at least half the seeds (seed-0 frames used).**
- Dominant term: whichever of p / 0.03 and o / 30° is larger.
- Orientation failure type:
  - FLIP if at least 20 % of frames have o > 135°;
  - SPAN if more than half of the summed o comes from at most 25 % of frames;
  - else STEADY (a gradual or constant error).
- Position failure type: SPAN by the same rule; else STEADY.
- For FLIP and orientation failures: the scan principal axis closest to the median error-rotation axis (in the scan
  body frame) and its angle.

**Mapping to eval (GT-free prior).**
- For each failing object type and failure type, list the eval episodes that contain the object (kit
  `track_3_evaluation_objects.json`).
- No eval data is read beyond object names.
- No threshold is tuned. Report-only: nothing changes in packs or references.
