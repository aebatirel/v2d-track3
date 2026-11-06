# Mini sweeper: why every route fails, and a GT-free fix (2026-10-30)

Labels: [M] measured without ground truth; [D] diagnostic, uses the public scan; [E] estimate; [H] hypothesis.
Nothing here changes a submission. Repo files were not edited. All scan use is diagnostic.

## Short answer
1. **The real sweeper is almost perfectly symmetric under a 180° turn about its long axis.** [D]
   - The scan maps onto itself under this turn to within 1.15 mm mean.
   - The only asymmetric parts are the mocap marker balls: two on the +x face, one on the -x face. They are about
     4 % of the surface.
   - The kit does not declare the sweeper symmetric. Its config lists only the two cups (axial) and the lid
     (half-turn).
   - So the kit's registration (25 PCA starts, trimmed ICP) must tell "right" from "flipped" by the markers alone.
2. **library_v3 has almost no correct asymmetry left, so its registration is a coin toss.** [D]
   - The flipped basin scores only −0.003 to 0.09 mm worse than the right one. The scan registered to itself gives
     0.31–0.39 mm.
   - At eval 30's kit seed it flips: 177.7° about the long axis (axis 0.011, 0.014, 1.000), ADD 45.7 mm.
   - Over 30 seeds it flips 3 times.
3. **GT-free fix: make the body symmetric by construction and add only the two observed +x marker balls.** All four
   such builds have 0 flips (6 seeds each; 0/24 more for M2). Margins are 0.10–0.26 mm [D].
   - The part program P1 also gives the lowest sweeper CD-O we have: 0.2225 vs 0.317, ADD median 3.3 mm. That
     number is optimistic, because two of its rules changed after I compared with the scan (see §6).
4. **ep18's "contamination" is a hand, not another object.** [M] + [H]
   - ep18's observed points were built with `hands: null`. 25 % of the points form a blob that is rigidly attached
     at the top +y side of the ring, which is where a hand grips the ring.
   - The blob is 197 mm (median) from the dust pan.
   - Frames 48–110 also have bad tracks.
5. **Generators fail because their input crop shows the sweeper edge-on.** [M] + [D]
   - Single-image models produce a "brush on a stick": width/length 0.19–0.51, against 0.80 for the real one.
   - Some fill the ring or add a long handle.
   - Pixal3D-MV had only that one view, and its mesh sits 49–53° off our long axis.

## 1. The real object [D] (scan, `scan_parts.json`, `scan_views.jpg`)

Box: 4.76 (x, thin, balls included) × 11.39 (y) × 14.16 (z) cm. Parts, segmented by texture colour:

| Part | Size |
|---|---|
| Wooden ring | outer radius 3.51 cm, centre z 4.60, hole radius ≈ 2.1, tube ≈ 2.0 cm thick in x |
| Green head (fan sector) | z −1.2…2.1 cm, ≈ 5.1 cm wide at the top to ≈ 7 cm at the bottom, ≈ 1.5 cm thick |
| Bristle fan | z −6.0…−1.2 cm; width 7.1 → 11.4 cm at the tips; only ≈ 0.8 cm thick (x −0.42…0.39); fuzzy separate tufts |
| Marker balls | r ≈ 7 mm on dark posts. +x face: (1.64, −1.57, 0.31) and (1.64, 1.67, 0.26) cm. −x face: (−1.75, −1.42, 0.22) cm |

Near-symmetries, scan against its own transform (mean / p90 mm):

| Transform | All parts | Markers removed |
|---|---|---|
| 180° about the long axis z | 1.15 / 1.95 | 0.99 / 1.83 |
| 180° about x or y | 5.5 / 13.7 | |
| Mirror front/back or left/right (not rotations, so not reachable by registration) | 0.8–0.97 | |

## 2. Why registration flips [D] (`scores_diag.jsonl`, `margins.jsonl`, `flipseeds.json`)

The kit's `_align_rigid` keeps the start with the lowest untrimmed symmetric mean distance. One of its 24 PCA starts
is the long-axis flip, so both basins are always tried.

The "margin" below is the flipped basin's distance minus the right basin's distance, per seed:

| Mesh | Margin per seed (mm) | Flips |
|---|---|---|
| scan vs itself (best possible) | 0.31–0.39 | – |
| library_v3 | 0.088 (eval 19), −0.003 (eval 30), 0.042, 0.006, 0.060, 0.036 | 1/6 (eval 30's seed 30000090); 2/24 more seeds |
| M2 / M2b / P1 / P1v0 | 0.12–0.26 / 0.13–0.19 / 0.13–0.18 / 0.10–0.16 | 0/6 each; M2 0/24 more seeds |

- library_v3 is asymmetric in the wrong places [M]: GT-free self-ambiguity 3.25 mm against a 1.44 mm floor.
  - The lump inside the ring is on one side.
  - The −x side is hallucinated out to x −1.74.
  - The ball bumps are smeared.
  - The base is flattened along ep18's tilted "up".
  - These errors outweigh the faint marker signal.
- Older numbers disagree. The 26 Oct note says eval 19 and 30 sit 0.7–0.9° from the majority, while this replica
  says eval 30 flips. A margin of 0.003 mm explains the disagreement: any change in budgeting or sampling decides
  the outcome.
- **[E] Expect about 10 % flips per eval pair on the hidden scan with library_v3.** A flip costs about 45 mm ADD
  for the whole episode.
- Generators flip on 1–6 of 6 seeds for the same reason [M + earlier D].
  - Their self-ambiguity solution is a 170–180° turn (amb 1.8–4.8 mm).
  - Their marker balls are missing, or appear as random pins.
  - [H] Their flips are also about the long axis. Falsifier: the axis of a flipped seed's rotation is more than 20°
    from the long axis. This was not run, to save scorings.

## 3. What our points cover [M] (`a4_obs.py`, `a5_ep18.py`, `ep18_perframe.json`, `fig1`, `fig4`)

**ep31** (hand masks on; 500k points, 144 frames):
- Seen from: +x for 85 % of the points; +y edge; top.
- Never seen from −x (0 %) or from below (0 %).
- The −y flank of the ring and head is seen only at grazing angles.
- Distance to library_v3: p50 1.44 mm, p90 3.65 mm. To the scan [D, earlier obs_diag]: p50 1.37, p90 3.85.
- Contamination: 0.5 % of points are more than 10 mm out, near x ≈ −3.5 cm (rack pegs [H]).
- Both +x balls are seen: protrusion apex at x = 2.26 cm, free sphere fits 7.4 / 5.9 mm. The −x ball is never seen.

**ep18** (built with `hands: null`; 1.1M points, 177 frames):
- 25.2 % of points are more than 10 mm from library_v3.
- Far-point centroid (0.7, 5.2, 8.5) cm; box y 0.6…7.2, z −5…10 cm. That is above and beside the ring's +y top,
  outside the object.
- 67 of 177 frames have more than 30 % far points: frames 44–204 (while the sweeper moves 5–22 mm/frame) and
  296–352 (sweeper still).
- Per-frame ICP to library_v3 leaves the far share at 0.29, so the cause is not a bad track.
- The blob is 197 mm (median) from the tracked dust pan, so it is not the dust pan.
- The blob sits at a fixed place in the object frame while the sweeper moves, so it is attached to it.
- **[H] It is the hand gripping the ring.** Eval 19's crop shows exactly that grip.
  - Falsifier: re-run `obs_points.py` for ep18 with MediaPipe `hands.npz`. If the blob keeps more than 10 % of the
    points, the hypothesis is wrong. This needs the ep18 video, which is not on this box.
- Frames 48–110 also have track errors: per-frame ICP shifts 12–81 mm and 4–47°. Those are the fast sweeping
  frames.

The 32 mm centroid shift is therefore the hand blob (25 % of points, about 5 cm away), plus the bad sweeping
frames.

## 4. Why generators misjudge it [M] (`gen_stats.json`, `fig2`, `fig3`)

- **The view is the problem.** The generator input `crops/ep31/mini_sweeper_k270.png` shows the sweeper edge-on in
  the rack: the ring as a narrow ellipse, the head as a green cylinder, the bristles as a strip. The fan's width
  cannot be seen.
- **Intrinsic PCA proportions** (width/length, thickness/length), against the scan's 0.80 / 0.34:

  | Mesh | W/L | T/L |
  |---|---|---|
  | library_v3 | 0.76 | 0.23 |
  | SAM 3D s7 / s42 | 0.51 / 0.37 | – |
  | TRELLIS.2 | 0.24–0.36 | – |
  | TripoSG | 0.32–0.43 | – |
  | Hunyuan | 0.19–0.23 | – |
  | Pixal3D-MV | 0.58–0.70 | – |

- **The shapes generators produce:**
  - Hunyuan s7 and TripoSG add a long stick handle (28.6 / 19 cm long).
  - SAM 3D s42 fills the ring into a disc.
  - The marker posts become pins.
- **The bristles are thin and fuzzy:** an 8 mm see-through fan of separate tufts. The models turn them into a
  narrow solid paddle.
- **Placement:**
  - `sim3_fit` scales and turns the mesh to match our one-sided points. On a long, narrow, near-symmetric object
    this fixes the length and leaves width, roll and flip free, so the overlay looks narrow and twisted.
  - Pixal3D-MV ("posed") had a single view (`views_final/ep31_mini_sweeper` has only `view00_k270`). Its long axis
    is 49–53° from ours; that is the 51–55° rotation seen in its scores.
- **Eval crops (`fig3`):**
  - Eval 19 (k168) shows the +x face with both balls, held by the ring. A face-on view would give a generator the
    width.
  - Eval 30 (k224) shows the sweeper edge-on in the rack, mostly covered by the hand. It is as bad as ep31, or
    worse.

## 5. Why library_v3 still beat every earlier route

It is fused from our depth over two episodes, so it has the full fan width (11.0 cm) and the ring (CD-O 0.317).

Its errors (`fig1`, `fig5`) are:
- the ring hole is partly filled on one side;
- there is a through-hole in the head;
- the flattened base sits 5 mm below the bristle tips (anchor offset −4.6 to −5.0 mm in z in every right-basin seed);
- the fan corners are missing;
- the −x side is hallucinated.

The shells failed G_CONN because of the marker and bristle islands. Generators fail for the reasons in §4.

## 6. GT-free candidates tested (meshes in `meshes/`, code in `scripts/`)

None of them reads the scan, mocap, `*_align.npz` or parquet pose. Inputs are library_v3 (ours) and the ep31
observed points (ours).

- **M2** (`c1_symballs.py`):
  - library_v3 intersected with its own long-axis C2 image (the axis comes from ICP of the mesh to itself);
  - then the two +x balls found as protrusion peaks in ep31 points: r 7 mm, centre = apex − r, plus posts.
- **M2b** (`c3_keepbase.py`): M2 plus library_v3's bottom 8 mm along its own flatten "up". This keeps the 9.8 cm²
  resting face; M2 had cut it to 3.6–4.8 cm².
- **P1** (`c4_partprog.py`), a part program fitted to ep31 points:
  - parts: elliptic-section torus ring, trapezoid head slab, trapezoid fan slab, the two observed balls;
  - one mid-plane (from the see-through bristles and the ring top) and a left/right mirror plane (from slice
    mid-points);
  - round tube prior for the ring;
  - **leak:** I chose the mid-plane rule and the ring-section rule after seeing that the first build was thicker
    than the scan.
- **P1v0** (`c4_partprog_v0.py`): P1 with the rules as first written, before any scan comparison. It shows how much
  that leak is worth.

| Mesh | CD-O eval [D] | ADD med / max mm [D] | Flips [D] | Margin mm [D] | obs→mesh p50 / p90 [M] | mesh→obs p50, >10 mm [M] | Watertight, footprint |
|---|---|---|---|---|---|---|---|
| library_v3 | 0.317 | 5.2 / 45.7 | 1/6 (+2/24) | −0.003…0.09 | 1.47 / 3.66 | 2.85, 0.100 | yes, 9.7 cm² |
| M2 | 0.283 | 3.4 / 3.8 | 0/6 (+0/24) | 0.12…0.26 | 2.02 / 5.98 | 2.76, 0.027 | yes, 3.6–4.8 cm² |
| M2b | 0.291 | 4.1 / 4.8 | 0/6 | 0.13…0.19 | 2.02 / 5.98 | 2.86, 0.043 | **no**, 9.8 cm² |
| **P1** | **0.2225** | 3.3 / 4.0 | 0/6 | 0.13…0.18 | 2.08 / 4.38 | 2.05, 0.050 | yes, flat base |
| P1v0 | 0.413 | 3.6 / 3.8 | 0/6 | 0.10…0.16 | 2.61 / 6.21 | 4.30, 0.201 | yes, flat base |

Pre-registered checks, logged in `scorings.log` before each scoring:
- S04 (P1): "0/6 flips, margin ≥ 0.1, CD-O ≤ 0.35". **Met.**
- S05 (P1v0): "0 flips, CD-O ≤ 0.317". The flip part held. **The CD-O part is falsified (0.413).**
- M2, threshold stated in my working notes before S02 (not logged in `scorings.log`): "margin ≥ 0.15 on all seeds". Met on 5 of 6 (eval 30's seed 0.119).
  The falsifier (< 0.1 or any flip) did not fire.

Readings:
- **The flip fix is robust:** 4 of 4 symmetric-body + marker builds have 0 flips and a margin ≥ 0.10 mm. This does
  not depend on the leak.
- **The CD-O gain is not robust:** it depends on the rule changes (0.2225 vs 0.413). The GT-free metrics also
  prefer P1 over P1v0 by a wide margin (mesh→obs 2.05 vs 4.30 mm, far share 0.05 vs 0.20). A GT-free selector
  would therefore have made the same choice, but the rules were not frozen in advance.

## 7. Recommendation

1. **Sweeper route: part program with a symmetric body and observed markers, in our frame (P1 family).**
   - Before any use:
     - freeze P1's rules as they are now;
     - check them GT-free on a second observation set (ep18 rebuilt with hand masks);
     - repair or decimate (P1 is watertight; M2b is not);
     - build the simulator copy and re-check the resting pose (P1 has a flat bristle base).
   - Do not pick it by the scan numbers above.
   - **Fallback, if the owner wants the smallest change:** M2 or M2b. Same frame as library_v3, so this is a pack swap
     at $0. M2b keeps the v3 resting face but needs a watertight repair.
   - Both routes need the owner's existing decision: packed mesh only, or also the simulator copy (GPU re-run of
     evals 19 and 30).
2. **Keep the markers in every future sweeper mesh,** and keep the body symmetric. [H] Markers are the only thing
   that tells the two basins apart. Falsifier: a symmetric body without balls registered on the same 6 + 24 seeds
   shows margins clearly above 0.05 mm. That is a one-scoring control I did not run.
3. **ep18:** rebuild its observed points with hand masks before using it as a hold-out (falsifier in §3).
4. **Generators:** not for this object from edge-on crops.
   - [H] A face-on crop (like eval 19 k168) gives SAM 3D a width/length within 0.1 of 0.80. Falsifier: W/L < 0.6 on
     a face-on input; that costs one GPU generation.
   - Even then, orientation and scale must come from our frame and the observed markers, not from a scale-free Sim(3)
     fit to one-sided points.
5. **Eval-time caveat:** under the 22 Oct per-episode rule, P1 would need eval depth.
   - Eval 19 is face-on and held by the ring, so a fit is feasible.
   - Eval 30 is edge-on in the rack under the hand, so it would probably fall back to the public-built mesh.

## Scan-touching runs (limit 12 mesh_metric scorings)

All are listed in `scorings.log`, with times. There were 5 full mesh_metric evaluations: S01–S05, one per mesh.
There were also 7 registration-only diagnostics on the same meshes: basin margins for all 5, and 24 extra seeds for
library_v3 and M2.

| Run | Mesh | What |
|---|---|---|
| S01 / S01b / S01c | library_v3 | replay with flip axes / margins / 24 seeds |
| S02 / S02b / S02c | M2 | evaluate / margins / 24 seeds |
| S03 / S03b | M2b | evaluate / margins |
| S04 / S04b | P1 | evaluate / margins |
| S05 / S05b | P1v0 | evaluate / margins |

Also scan-based, but not candidate scorings: scan self-symmetry, scan-vs-scan margin, scan part dimensions.

No submission mesh was selected by these numbers.

## Files

Figures:
- `fig1_scan_vs_library_v3_vs_obs.jpg`: scan, library, overlay, mismatch, ep31 and ep18 points.
- `fig2_meshes_in_our_frame_vs_scan.jpg`: library, M2 and six generator meshes, as placed, against the scan in our
  frame.
- `fig3_generator_input_and_eval_crops.jpg`
- `fig4_ep18_contamination.jpg`
- `fig5_candidates_vs_scan_and_obs.jpg`
- `scan_views.jpg`

Data: `scores_diag.jsonl`, `margins.jsonl`, `flipseeds.json`, `gen_stats.json`, `gtfree_fit.txt`,
`ep18_perframe.json`, `scan_parts.json`, `balls_obs.json`.

Meshes: `meshes/*.glb`, with fit parameters in `meshes/*.json`.
