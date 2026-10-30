# Generative 3-D probe (batch 2), 2026-10-29/30

## Question

Do modern image-to-3D generators give better object meshes than ours? "Better" means the kit's CD-O, measured on the
public scans (`scripts/mesh_metric.py`). All scan numbers here are diagnostic **[D]**: none is used to pick anything
for submission.

## What ran

All runs were on one Vast box: instance 58314388, H100 NVL 94 GB, Czechia, interruptible, run id
`mesh-20261029-gen-f3fbeb0`.

- **Run time.** Created 22:09 UTC and destroyed 23:35:15 UTC; 84.3 min running in total.
- **Interruption.** The box was outbid at 22:52 and restarted at a bid of $1.30/h.
- **Cost: $4.36 measured** (cap $12), from the Vast instance record:
  - 43 min at $0.898/h;
  - 41 min at $1.398/h;
  - 71.6 GB download at $37.3/TB, which cost $2.61;
  - upload and storage.

Code is in `../../gen/` and the full log is in `docs/work-log.md` (29 Oct, 22:15 onwards).

| Model | Input | Output frame | Generated |
|---|---|---|---|
| Pixal3D multi-view (TencentARC/Pixal3D main, MIT) | posed RGBA views from our video, our tracks and our calibration (`gen/mv_views.py`); view 0 is placed at the canonical front pose | **our object frame**; checked GT-free by reprojection IoU against our masks | 10 objects × seeds 42/7; plus view 0 alone for the 2 sets with >1 view |
| TRELLIS.2-4B (MIT) | `crops.py` RGBA crop | canonical frame | 20 crops × 2 seeds, shape only, 1536 cascade; 3 blue-cup pairs at 1024 (OOM) |
| TripoSG (MIT) | same crops | canonical | 40, skimage extractor (diso does not build) |
| Hunyuan3D-2.1 shape (Tencent community licence, research use) | same crops | canonical | 40 |
| SAM 3D Objects (SAM Licence; access approved during the run) | first-ranked crop + its mask; MoGe pointmap from the crop | canonical | 10 × 2 seeds |

- **Views.** The view sets are mostly a single view: 8 of 10 objects have 1 view, board 2 has 2 and the dust pan
  has 3 (`views/selection.json`).
  - The views are at-rest frames, plus held frames gated by a skin test. Views with mask/silhouette IoU < 0.75 were
    dropped.
  - Egocentric viewpoints at rest barely differ, and in held frames a hand is on the object.
- **Single-image models.** Each output was registered to our observed points by a GT-free multi-start Sim(3) ICP
  (`gen/sim3_fit.py`), so that ADD and flips can be read. CD-O is similarity-invariant, so it equals the raw
  output's CD-O. The raw outputs were not scored separately (one scoring per mesh).

## Integrity

- **Generation inputs** were our crops, poses, calibration, library_v3 mesh (silhouette seed and box, as in
  crops.py) and our observed points (Sim(3) fit). No scan, mocap or parquet pose reached the box or any input.
- **Freeze.** All 312 generated files were hashed (`SHA256SUMS`, commit 243b854) before any scan read.
- **Scoring.** The scoring set was pre-registered in the work log (~22:55 UTC): Pixal3D-MV, all of it; the other
  models, first-ranked crop × 2 seeds.
- **Scan scorings: 104**, one per mesh (`scores.jsonl`, `scores.log`), run with `--workers 1`.
- **Library baselines** come from the existing `../baseline_library.jsonl`. No new library scoring was done.

## Results [D]

Full tables are in `table.md`; per-mesh values are in `rows.json`.

**Mean CD-O over the 10 objects.** library_v3 averages 0.477 cm (median 0.429).

| Model | Seed mean | Median | Objects with seed mean < library | Objects ≤ 0.35 |
|---|---|---|---|---|
| SAM 3D | 0.501 | 0.383 | 6 | 5 |
| Pixal3D-MV | 0.490 | 0.399 | 5 | 4 |
| Hunyuan3D-2.1 | 0.602 | 0.451 | 5 | 2 |
| TRELLIS.2 | 0.594 | 0.583 | 3 | 2 |
| TripoSG | 0.984 | 1.079 | 0 | 1 |

**No generator beats library_v3 on average as it comes out.** SAM 3D and Pixal3D-MV are close and win on about half
the objects.

**Seed variance is large.** Examples:
- Hunyuan3D-2.1 on the blue cup: 0.298 vs 1.252;
- TRELLIS.2 on the rack: 1.262 vs 0.636;
- SAM 3D on the sweeper: 0.706 vs 0.437.

**Oracle best-of-all generated meshes per object.** This is an upper bound, not a method:
- **mean 0.315**;
- it beats library_v3 on 8/10 objects; it loses on the rack (0.604) and the sweeper (0.437);
- it beats our best hand-built meshes on the pot (TRELLIS.2 0.318 vs 0.342) and the blue cup (SAM 3D 0.268 vs
  0.291);
- it does not beat them on the lid (0.253 vs 0.220) or the rack.

**Pose side (ADD, flips).**
- Pixal3D-MV, in our frame without registration: median ADD 10.3 mm. 6/20 meshes flip, all of them boards or the
  sweeper.
- Single-image models after the GT-free Sim(3) fit: median ADD 26–29 mm, with 6–7/20 meshes flipping.
- library_v3: ADD 2.4–10 mm (sweeper 25.6); flips only on the sweeper (1/6).

So these meshes as they stand would hurt the pose metrics. The weak link is the registration of a canonical-frame
mesh to partial observations (hypothesis [I]).

**Multi-view vs single view (Pixal3D).**
- Dust pan, 3 views: 0.240/0.236. View 0 alone: 0.628/0.528.
- Board 2, 2 views: 0.274/0.247. View 0 alone: 0.255/0.758.
- GT-free: views the model did not see reproject at IoU 0.44–0.67 with view 0 alone, and 0.88–0.97 with all views.

## Would the GT-free metric have picked the winner?

The GT-free metric is the median distance from our observed points to the mesh plus the median distance from the
mesh to our points (`gtfree_scored.jsonl`). Results are in `selection.json`:
- **Spearman with CD-O:** 0.46 over all 104 meshes; per object, median 0.58 (range −0.21 to 0.72).
- **Picking the CD-O best:** the GT-free argmin was the CD-O best on 2/10 objects. Its CD-O rank was
  [2, 4, 6, 6, 6, 9, 1, 1, 4, 5]. Mean regret 0.120 cm.
- **A GT-free choice between library_v3 and the GT-free-best generated mesh**:
  - it picks generated on 9/10 objects;
  - mean CD-O 0.429 vs 0.477 [D];
  - better on 6 objects, worse on 3 (both boards and the sweeper), the same on the rack;
  - every generated pick has a much larger ADD than library_v3 (Sim(3) registration).

The GT-free metric is informative but too weak to choose seeds and models safely. It does not see unobserved
surfaces, or walls that are too thick or too thin.

## Verdict

- **Hypothesis P1** (README §6), "the best model is ≤ 0.35 cm on ≥ 5 objects": met only at the edge. SAM 3D
  reaches 5 of 10.
- **Falsifier** "median not better than library_v3": not falsified for SAM 3D (0.383) or Pixal3D-MV (0.399), against
  0.429.
- **Pixal3D falsifier** (lit §8A), "median CD-O not ≥ 0.08 cm below 0.40": **falsified**. Its median is 0.399.

So generators are a useful candidate source per object, especially SAM 3D and Pixal3D. They need:
- a GT-free selection that works;
- a pose-safe registration into our tracked frame.

Neither exists yet. Nothing here changes the submission.

## Files

| Path | Contents |
|---|---|
| `table.md` | per-object CD-O by model and seed; every scored mesh with ADD, flips and GT-free metrics; selection analysis |
| `rows.json`, `selection.json` | the data behind `table.md` |
| `scores.jsonl`, `scores.log` | the 104 one-shot scorings |
| `score_manifest.tsv`, `SHA256SUMS` | the scoring set and the frozen hashes |
| `gtfree_*.jsonl`, `mv_check_final.jsonl` | GT-free metrics: observed-point distances; Pixal3D view IoU |
| `sim3_fits/*.jsonl` | GT-free Sim(3) fits: scale, R, t, residuals |
| `gen_logs/` | generation logs (timing, faces, failures) and the setup logs |
| `views/` | Pixal3D view sets: `transforms.json`, `probe_meta.json`, selection |

**Meshes are not in git:**
- HF store: `runs/mesh-20261029-gen-f3fbeb0/results/results_gen.tar` (2.19 GB, sha256 56986e13…), which holds all
  outputs and logs;
- inputs: `runs/mesh-20261029-gen-f3fbeb0/inputs/`;
- SAM 3D checkpoints (gated): `runs/mesh-20261029-gen-f3fbeb0/weights/sam-3d-objects/`, 12.4 GB, which can be
  deleted;
- scratchpad copy: `gen/mesh-20261029-gen-f3fbeb0/results/gen/`.
