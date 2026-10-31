# C1 / T1 beige-cup observed-point lathe: results (2026-10-31)

Pre-registration: `PREREG.md`, commit `4c757ea`, pushed before any scan read. Step log: `NOTES.md`.

Labels:
- [D] = public scan or mocap used as a stand-in, after inference;
- [M] = measured without ground truth;
- [E] = estimate;
- [H] = hypothesis.

Cost: CPU only, $0. Scan scorings: one `mesh_metric` scoring (32 seeds, 738 s) and two `score_registered` runs on
ep11.

## Verdict
**H-BL survives.** The adopted blue-cup lathe method, run on the beige cup's ep11 points, is a WIN on both eval
pairs. The ep11 AUC guard passes.

| Gate | Threshold | Lathe M_sep [D] | Result |
|---|---|---|---|
| CD-O eval 10 (seed 10000131) | <= 0.836 (library_v3 0.856 - 0.02) | **0.2475** | WIN |
| CD-O eval 8 (seed 8000024) | <= 0.710 (library_v3x 0.730 - 0.02) | **0.2549** | WIN |
| add_med (6 baseline seeds) | <= 8.97 mm (6.97 + 2.0) | **5.70 mm** | pass |
| flips, symmetry-aware | 0 of 32 seeds | **0 / 32** (rot max 3.5 deg) | pass |
| AUC guard, twin ep11 | dAUC >= -0.005, dMPPE and dRPE <= +0.2 cm | dAUC **+0.0080**, dMPPE -0.064 cm, dRPE -0.044 cm | PASS |

All secondary checks pass:
- per-seed baselines: 0.8705 - 0.02 for eval 10 and 0.7251 - 0.02 for eval 8;
- add_med 5.70 <= 5.51 + 2.0 against v3x;
- add_med over all 32 seeds 5.75 mm.

## Details
**Scoring** [D] (`results/score_t1.jsonl`):
- CD-O over 32 seeds: mean 0.2502 cm, sd 0.0027, range 0.2459-0.2584.
- ADD: range 5.21-7.74 mm.
- Self-ambiguity: 5.18 mm (floor 2.69).
- Library baselines for comparison: v3 0.856 / ADD 6.97, and v3x 0.730 / 5.51 (`results/baseline_library.jsonl`).

**AUC guard** [D] (`results/auc/`):
- ep11 perception track, episode-level registered score;
- `base` = library_v3 for all objects, `single` = base plus the lathe as the beige cup.

| | AUC | SP-SR | MP-SR | MPPE cm | RPE cm | beige per-object AUC | beige registration rot |
|---|---|---|---|---|---|---|---|
| base | 0.8978 | 1.0 | 1.0 | 1.6375 | 1.7390 | 0.9334 | 145.3 deg (spin about the axis) |
| single | 0.9058 | 1.0 | 1.0 | 1.5737 | 1.6954 | 0.9494 | 4.0 deg |

- Our own base was run because our track npz did not match C0's byte for byte (the values match to 1e-16).
- It equals C0's `base/ep11` exactly; that check was a cross-check only.

**Eval 10 packing** [M] (`results/pack_check.txt`):
- In packs 3 and 4, eval 10's beige rows equal `budget_mesh(library_v3)` (max 0.000 mm), and eval 8's equal
  library_v3x.
- So STATUS 25 Oct ("v3x adopted for evals 10, 8") is wrong for the pack; the eval lane ("only eval 8") is right.

**Board effect, if the packed mesh is swapped on both pairs** [E, public-scan proxy]:
- the two pairs drop by 0.609 and 0.475 cm;
- the 36-pair mean falls by about 0.030 cm: 0.402 to about 0.372 alone, before C0.

## What was built, and why
- **Method:** `lathe_obs.py` at its defaults, which are exactly the adopted blue-cup settings (the blue-cup g1 mesh
  rebuilt byte-identically). The input is our ep11 observed points: sweep base track, G1 hands, blue cup removed with
  `--others`.
- **Not transferable: nesting.** `lathe_obs.py` has no frame option, so the mask was applied as an npz pre-filter
  (`scripts/mask_obs.py`) from a GT-free census (`scripts/frame_census.py`).
  - The nested frames (t >= 68) put 5,891 points about 30 mm below the cup's base seen in all other frames.
  - The no-mask lathe was therefore 191 mm tall with a narrow tail.
  - M_sep keeps the 32 separated frames (t 0-62, 507 k points). Hand-held frames are kept, with capsules, as in the
    blue-cup method.
- **Variants, never scored:** M_all (no mask) and M_sephf (t 0-12 only, hand-free). They were built for GT-free
  comparison only.
  - M_sephf came out very close to M_sep: height 160 vs 162 mm, wall 3.06 vs 3.15 mm.

## Failures and surprises
- **My GT-free prediction was wrong.** On `obs_fidelity.py`:
  - both library meshes (3.41 mm) and the no-mask lathe (4.14) explained our points better than the scored M_sep
    (5.82);
  - I predicted H-BL would likely fail.
  - It is the third time this selector has disagreed with the scan (blue cup Spearman about 0.5; gen-probe 0.46).
  - Its mesh-to-observation term penalises any completed, unobserved surface. Do not use it to choose between a
    lathe and a library mesh.
- **Known flaws of the scored mesh** [M], which it won with anyway:
  - Its axis is 4.3 deg from the M_all axis, which is more self-consistent on the same points (2.42 vs 2.66 mm).
    The likely cause [H] is `fit_axis`'s opening tie-break: the camera sees the cup from one side all episode
    (elevation about 50 deg, a 31 deg azimuth band).
  - 19 % of the points lie more than 4 mm outside the outer profile. They are splatted into a 92 x 104 x 93 mm
    appendage shell.
  - A cleaner build might score better, but every further build counts as a new scoring.
- **Not measured:**
  - whether the mask mattered (M_all and M_sephf unscored);
  - the joint effect with C0's blue-cup lathe on ep11 (both cups swapped).
- **Flag for eval 8** [H]: eval 8's rollouts were tracked with library_v3x, and the AUC guard tested only
  library_v3-frame tracks.
  - v3x was fused along the same ep11 track, so the frames should agree within millimetres. The lathe's ADD of
    5.7 mm vs v3x's 5.5 supports this.
  - A v3x-frame twin was not run.
  - GT-free surface-centroid offsets: 8.8 mm to v3, 9.6 mm to v3x. These include the shape difference, and the
    PCA axis angles in `results/frame_check.txt` are not meaningful for the library cups.

## Integrity
- Construction, masking and the choice of M_sep were GT-free. The choice was declared in `NOTES.md` before any
  variant was compared.
- Disclosure: the README's scan-extents table had been read beforehand (PREREG section 8).
- Scan, mocap and parquet poses were read only by `score_t1.py` (once) and `score_registered.py` (ep11 base and
  single, once each), after the PREREG push.
- No mesh was re-scored or tuned on a score.
- Bulk outputs are in scratchpad `cdo_c1/t1/`. In git: the scored mesh (`meshes/`, 654 KB), scripts, and the JSON
  and log results.
