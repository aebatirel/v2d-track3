# E0: C0's mesh methods rebuilt on the eval episodes (CD-O sprint)

Status (2026-10-31 ~17:00 UTC): **packaged, not scored** (there is no eval ground truth). By the pre-registered rule
(PREREG.md sections 4 and 6), the recommendation is **E0 for all four objects** with no rule flags. The owner decides what
ships. This is a stub; MANIFEST.json holds the full record.

Why: owner, 31 Oct 15:50 UTC: "if the method of mesh creation better just recreate the meshes in the eval and use that";
16:40 UTC: get it faster with Vast machines.

## What was done
- PREREG.md (written before any eval candidate existed) fixes the inputs, the frozen code (public commit 2971a10,
  `jobs/frozen`), the commands, the exclusions, the pick and the recommendation rule.
- One Vast CPU box (run `mesh-20261031-e0-b05f001`, code b05f001, 96 cores, about 15 min, about $0.13 [E]) built 49
  candidates for the 17 eval pairs of pot (6), lid (1), rack (5) and blue cup (5), with obs_fidelity and frame/budget
  checks. Report: BOX.md. Small results: box/. Bulk results: HF store `aebatirel/v2d-store`
  `runs/mesh-20261031-e0-b05f001/results/e0/`.
- `scripts/e0_package.py` (run with `python -I`) applied sections 4 and 6 again, independently of the box's
  `jobs/e0_select.py`, from the raw fidelity and check rows. It recomputed nothing and agrees with the box
  `selection.json` on every object. Output: `selection_final.json`, `MANIFEST.json`, `meshes/`,
  `meshes/library_e0`, `meshes/library_e0x`.

## Picks [M; fidelity is obs_fidelity sum_mm on all eval points of the object, in-sample for E0]

| object (pairs) | E0 pick | fid E0 / C0 / library_v3 | runner-up | eligible | rec | md5 |
|---|---|---|---|---|---|---|
| white_pot (6) | pot/ep3/fit -> `meshes/white_pot_eval3_fit.glb` | 2.922 / 2.914 / 3.881 | pot/ep3/nostem (byte-identical to the pick); first different mesh pot/ep3/thick 3.077 | 18/24 (6 tsdf not watertight) | E0 | 858fc4c64b147eb2245bdcced9a29f73 |
| white_pot_lid (1) | lid/ep1/t2.5_fit -> `meshes/white_pot_lid_eval1_t2.5_fit.glb` | 1.675 / 1.772 / 5.186 | none eligible (t2.5_tsdf 1.787 not watertight) | 1/2 | E0 | 08b65d4f7080e55c6ee81be9fa19cf8f |
| plastic_dish_rack (5) | rack/joint/joint (eval 14, 15, 16, 28, 30) -> `meshes/plastic_dish_rack_eval_joint_joint.glb` | 6.419 / 6.245 / 5.881 | rack/joint/joint_nomk 6.432 | 12/12 | E0 | 9b8adbe3bbdf09666f604436aa4cade4 |
| blue_cup (5) | cup/ep32/g1 -> `meshes/blue_cup_eval32_g1.glb` | 2.646 / 2.723 / 2.906 | cup/ep32/g0 2.664 | 11/11 | E0 | b479269e3ee21266db84df8a17bfdc1c |

Section 6: pot, lid, rack go to E0 unless C0 < 0.85 x pick. C0/pick is 0.997, 1.058 and 0.973. Blue cup goes to E0 unless
library_v3 < 0.85 x pick. library_v3/pick is 1.098, and C0/pick is 1.029 (reported only).

## Packaging
- `meshes/library_e0` = `meshes/library_c0` with blue_cup.glb reset to library_v3, then the four E0 picks. This is the
  same as library_v3 with pot, lid, rack and blue cup replaced. `meshes/library_e0x` is the same over library_c0x and
  library_v3x, for eval 8.
- MANIFEST.json covers the 36 eval pairs. 17 pairs carry an E0 mesh; the other 19 are byte-identical to library_c0 and
  pack 7. All 17 E0 pairs differ from both C0 and pack 7.

## Read before using (details in MANIFEST.json flags)
- **Not scored.** Fidelity is GT-free and is not CD-O (public Spearman 0.85 for pot, 0.5 for cup). Each pick is
  in-sample. **Pot and rack do not beat C0 even in-sample**; they fall within the 15 % margin, so they are E0 by rule.
  **On the rack, library_v3 has the lowest fidelity of all 14 meshes** (on all points and on eval 14, 15, 16, 28). The
  rack rule compares only C0, so this is a reviewer note, not a rule flag.
- **Marker balls (pot, lid, rack):** the frozen prim_potlid.py uses the scan-derived MK_R0 = 7 mm prior and the 5-9.5 mm
  window, the same flag as C0. **Thickness:** lid and rack use 2.5 mm, the grid midpoint, flagged.
- **Method qualifier:** the object set and the methods come from C0, which was chosen with public-scan scores.
- Eval hands were made on the box (MediaPipe, as for the public G1 refs). Eval 10 (blue cup nesting the beige cup) is the
  cup pick's worst episode (7.748 mm; own-episode build 5.624 mm).
