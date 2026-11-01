# C1 / T2 already-scored generated picks, placed in the library frame: results (2026-10-31)

Pre-registration: `PREREG.md`, commit `6f71234`, pushed before any scan read. Step log: `NOTES.md`.

Labels: [D] public scan or mocap as stand-in, after inference; [M] measured without ground truth; [E] estimate;
[H] hypothesis.

Cost: CPU only, $0. Scan reads: three `mesh_metric` scorings (one per placed mesh: 386, 420 and 396 s) and six
`score_registered` runs (dust-pan twins ep18, ep39, ep40: our own base and the single swap, about 10-20 s each). C0's
base JSONs were not needed and were never opened.

## Verdict
**One win: the mini dust pan.** The SAM 3D pick placed in the library_v3 frame wins both eval pairs and passes the AUC
guard. **H-T2 survives for the dust pan and is falsified for the pitcher and the beige cup**: placing those two on the
library surface cuts their registration ADD by a quarter to a third, but it stays 2-3.5 times the library's. This is
what the GT-free prediction said before scoring.

| object | eval pair | CD-O (probe) [D] | CD-O gate | add_med (placed) [D] | add_med gate | flips | AUC guard | result |
|---|---|---|---|---|---|---|---|---|
| mini_dust_pan | ep19 | **0.2619** | <= 0.311 pass | **4.83 mm** | <= 7.65 pass | 0 / 32 | **PASS** | **adopted** |
| mini_dust_pan | ep38 | **0.2592** | <= 0.311 pass | 4.83 mm | <= 7.65 pass | 0 / 32 | PASS | **adopted** |
| water_pitcher | ep20 | 0.771 | <= 0.874 pass | 28.41 mm | <= 9.97 **fail** | 0 / 31 | not run | rejected |
| beige_cup | ep10 | 0.5191 | <= 0.836 pass | 15.03 mm | <= 8.97 **fail** | 0 / 32 | not run | rejected |
| beige_cup | ep8 | 0.5326 | <= 0.710 pass | 15.03 mm | <= 8.97 **fail** | 0 / 32 | not run | rejected |

- add_med is the median ADD over the baseline record's 6 seeds (eval seeds, then 11, 22, 33, 44, plus 55 for the
  pitcher), from the placed copy's single scoring (`results/score_t2.jsonl`, `results/score_t2.log`).
- The placed copy's own CD-O, re-measured as a consistency check, matches the probe within the kit's seed noise:
  dust pan 0.2587 / 0.2601, pitcher 0.7496, beige 0.527 / 0.540.
- Secondary checks against the per-seed library baselines (dust pan 0.3274 / 0.334; pitcher 0.8942; beige 0.8705 /
  0.7251) all pass on CD-O.

**Board effect of the dust-pan swap** [E, public-scan proxy]:
- the two pairs drop by 0.069 and 0.072 cm;
- the 36-pair mean falls by about 0.004 cm (0.402 to about 0.398 alone);
- this adds to C0 and T1, since they swap other objects.

## Details
**Registration of the placed copies** [D], 30 extra seeds plus the eval seeds, compared with the probe pose and with
library_v3:

| object | probe add_med | placed add_med6 / all seeds / max | library add_med | placed rot max | self-ambiguity |
|---|---|---|---|---|---|
| mini_dust_pan | 7.47 mm | **4.83 / 4.92 / 5.96 mm** | 5.65 mm | 1.6 deg | 6.12 mm |
| water_pitcher | 33.4 mm | 28.41 / 28.33 / 31.96 mm | 7.97 mm | 10.9 deg | 9.67 mm |
| beige_cup | 21.8 mm | 15.03 / 15.19 / 18.31 mm | 6.97 mm | 7.7 deg (axis tilt) | 7.88 mm |

The placed dust pan registers better than library_v3 itself (4.83 against 5.65 mm).

**Dust-pan AUC guard** [D] (`results/auc/`, `results/guard_t2_dust_pan.json`):
- track: our perception track for each twin, converted by `scripts/auc_prep.py`;
- `base` = library_v3 for all 10 objects, run by us on all three twins;
- `single` = base with the placed dust pan.

| twin | base AUC | single AUC | dAUC | dMPPE cm | dRPE cm | dust-pan AUC | dust-pan registration rot |
|---|---|---|---|---|---|---|---|
| ep18 (with the sweeper) | 0.9642 | 0.9628 | -0.0014 | +0.041 | +0.005 | 0.9333 -> 0.9304 | 2.44 -> 1.15 deg |
| ep39 | 0.9602 | 0.9755 | +0.0153 | -0.172 | 0.000 | 0.9602 -> 0.9755 | 2.41 -> 1.15 deg |
| ep40 | 0.9570 | 0.9803 | +0.0233 | -0.252 | 0.000 | 0.9570 -> 0.9803 | 2.47 -> 0.85 deg |
| **mean** | | | **+0.0124** (min -0.0014) | **-0.128** | **+0.0015** | | |

- The rule passes: mean dAUC >= -0.005, min >= -0.02, and mean dMPPE and mean dRPE <= +0.2 cm.
- SP-SR and MP-SR are unchanged.
- RPE is 0 on the single-object episodes 39 and 40.

## What was built
**Placement** (`scripts/place.py`, `results/place/`, GT-free):
- **Method:** Sim(3) with free scale, symmetric trimmed ICP (keep 0.9) of the probe-scored SAM 3D mesh onto the
  library_v3 surface of the same object. There were 25 starts (24 PCA cube starts plus the probe pose), and the one with
  the smallest residual was picked.
- **Result:** every placement moved the mesh only 3-4 deg and 6-9 mm from the probe's point-fit pose. The scale changed
  by 0.02 % to 2 %.
- **Residuals:**
  - dust pan 2.77 mm;
  - pitcher 6.13 mm;
  - beige 5.30 mm.
- **Margin to the next distinct start:** 1.7 to 4.7 mm.
- **Reproducibility:** the placement rebuilds bit-for-bit (verified on the dust pan).
- **Same shape for the packer:** the kit packer sees the same shape as the probe mesh. Vertex NN median 0.0 mm; surface
  distance at the sampling floor.

**The adopted mesh:**
- in git: `meshes/mini_dust_pan_k297_s42_lib.glb`, 5.6 MB;
- sha256 `2fb147b535c9f8b863b56ec80239f28809b10fe9ca881a10a5c724f209777d02`;
- in the HF store with the other two placed copies: `aebatirel/v2d-store` `runs/cdo-c1-t2-20261031/place/` (commit
  3f4e98b).

To use it, pack this file as the mini_dust_pan mesh of eval 19 (slot 1) and eval 38 (slot 0). The rollouts stay as
they are.

## Failures and surprises
- **H-T2 falsified for the pitcher and the beige cup** [D].
  - The placed copies lie on the library surface (residuals 6.1 and 5.3 mm), yet the kit's registration (scan onto our
    mesh, scale-normalised) still lands 15-28 mm off.
  - The likely reason [H]: with a shape this far from the scan (CD-O 0.75 and 0.53 cm, against 0.26 for the dust pan),
    the registration offset is set by the shape mismatch (pitcher spout and handle, a beige cup 14 cm tall where the
    library is 17 cm), not by where the mesh sits.
  - Falsifier for the next attempt: a better-shaped generated pitcher or cup placed the same way should come within
    +2 mm of the library's ADD.
- **The GT-free observation-fidelity check pointed the wrong way again** [M] vs [D].
  - On all six twin pairs it preferred the probe's point-fit pose over the library-frame placement (by 0.5-2.0 mm).
  - Yet the placement lowered the kit ADD for all three objects: 33.4 -> 28.4, 21.8 -> 15.0, 7.47 -> 4.83 mm.
  - This is the same bias the diag found. Do not use observation fidelity to choose a frame.
- **Not verified:** the packed dust-pan rows of evals 19 and 38. The brief gives library_v3 (= v2 = v3x for this
  object) as the packed baseline, and no pack check like T1's was run.
- **Not measured:** the joint effect with C0's and T1's swaps on shared twins. The dust pan shares ep18 with the
  sweeper only, and neither C0 nor T1 swaps the sweeper.

## Integrity
- **GT-free steps:** placement, every check and every choice. `place.py` reads the probe mesh and our library_v3
  mesh only.
- **Provenance:** the placement inherits library_v3's frame, which is on the provenance denylist. That is the same
  tier as the current submission and C0, and it is the owner's call.
- **Already-known [D] numbers, disclosed in PREREG section 1:**
  - the probe's CD-O for these meshes;
  - the diag README's statement on `lib` placement.
  - The objects were chosen for T2 post hoc on the probe's [D] CD-O. The mesh per object was the probe's GT-free pick.
- **Scan, mocap and parquet reads** happened only after the PREREG push:
  - `score_t2.py`, once per placed mesh;
  - `score_registered.py` on the dust-pan twins, once per run.
- No mesh was re-scored or tuned on a score.
- **Bulk:** `SCR/cdo_c1/t2/` (placed meshes, tracks, mesh dirs, staged parquets, run JSONs and logs).
