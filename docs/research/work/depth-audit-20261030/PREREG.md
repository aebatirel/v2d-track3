# Depth audit: pre-registered calibration rule (written 2026-10-30 07:02 UTC, before any ground truth was read)

Written while the public audits were running and before `score_registered.py` was run for this study. No mocap file,
no `observation.objects` pose, no `refine/baseline/` or `refine/quarantine_gt/` file had been opened by this work.
Audit code: `pipeline/depth_audit.py`, sha256 `dafbcce4…` (repo HEAD d41382e plus the uncommitted audit files).

## Score (inference side, fixed now)
- **Primary:** `behind` per object-frame: over pixels where the object is the front-most rendered surface, eroded 4 px,
  with valid depth and outside our hand mask (MediaPipe joints, 1.2 cm capsules), the fraction where the observed
  depth lies more than 1.5 cm beyond our rendered surface.
- An object-frame is scored only if it is **valid**: vis_frac ≥ 0.20 (not hidden) and ≥ 50 selected pixels.
- Exploratory scores (reported, never used for the verdict): `front`, `behind + front`, `|med_r|`, `behind_any` and
  `front_any` (the same fractions without the hidden gate), and rest height `|rest_h|` on rest frames.

## Label (ground-truth side, computed only after all public audits exist)
- `perception_adds_cm` from `pipeline/score_registered.py EP IN/poses_world_vo.npz --meshes meshes/library_v3
  --per_frame ...`: the registered ADD of frame i against mocap row i, with the kit's symmetries (cups: spin about the
  axis; lid: 180°), after the kit's frame-0 scene alignment. The key is new and only written with `--per_frame`.
- Positive: ADD > 2 cm. Negative: ADD ≤ 2 cm.
- Secondary labels (reported, not for the verdict): the plain point-to-point ADD (`perception_add_cm`), the same
  symmetric ADD of the S2-shifted track (`refine.py --steps S2`, 0.545 frame; removes the tracker lag that depth
  cannot see), and thresholds 1, 3 and 5 cm.

## Episodes
- Primary set (19): 0, 2, 11, 12, 13, 18, 21, 22, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45.
- ep23 (frame-0 identity swap of two near-identical boards) is reported separately and is not pooled: the swap agrees
  with depth by construction, so it is an expected false negative [H].

## Statistic
- Pooled AUROC over all valid object-frames of the primary set (Mann-Whitney U with average ranks for ties).
- 95 % CI: episode-cluster bootstrap, 2000 draws (episodes resampled with replacement, seed 0), percentile interval.
- Also reported: mean within-episode AUROC (episodes with ≥ 10 positive and ≥ 10 negative valid frames), per-episode
  AUROC, per-object-class AUROC with n_pos/n_neg (no rule applied to a class with < 30 positives; thin objects:
  mini_sweeper, mini_dust_pan), the number of hidden or too-small object-frames and their share of the positives.

## Rule
- **Informative** iff pooled AUROC ≥ 0.75 and ≥ 8 episodes of the primary set contribute at least one valid positive.
- **Falsified** iff pooled AUROC < 0.65.
- Otherwise **inconclusive**: no reference or spoon spend on the strength of this audit.
- The verdict uses the point estimate; the CI is reported beside it.

## Only if informative (later step, thresholds fixed here on public data)
- Eval audit in perception and reference mode; no eval number is used to change any threshold above.
- Spoon test: the public thin-object range is the min..max over the thin-object episodes (sweeper 18/31, dust pan
  18/39/40) of the per-episode mean `behind` over valid frames. A spoon eval episode (3, 5, 6, 15, 16, 32, 33, 35, 36,
  37) inside that range is read as "depth shows no spoon tracking error beyond the public thin-object level".

## Amendment 1 (2026-10-30 07:10 UTC, still before any ground truth was read)
- The first full audit pass (v1, 07:00–07:08 UTC, depth_audit.py sha256 `dafbcce4…`) showed rest heights of ≈ 60 cm
  for the pitcher and the dish rack on eps 21, 22, 26 and 27: the local ring plane was the floor beyond the table edge.
- Fix (exploratory metric only): the local plane must also lie within 5 cm of the global table plane mapped to camera t
  (`--rest_dmax 0.05`). depth_audit.py sha256 `e337ac7f…`. All 20 public episodes are re-audited with it (v2); the v1
  outputs are kept in the scratchpad (`daudit/work/v1/`).
- The primary score's code path is unchanged; v2 `behind` must equal v1 `behind` exactly (checked before scoring).
- Nothing else changes: score, label, episodes, statistic and rule above stand as written.
