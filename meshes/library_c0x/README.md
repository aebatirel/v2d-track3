# library_c0x: CD-O sprint candidate C0 (packed-mesh swap), built 2026-10-31

This folder is meshes/library_v3x with four files replaced. The swapped meshes are in the same object frame as library_v3x
(fitted to our stereo points along the same tracks). Use it as the packed (submitted) mesh only; the simulator assets stay
library_v3x. Details, scores, flags and the AUC guard: docs/research/mesh-2026-10-26/cdo-sprint/C0/ (MANIFEST.json, README.md).

| file | source | sha256 (16) | public-scan CD-O [D], library_v3 -> C0 | ADD mm |
|---|---|---|---|---|
| white_pot.glb | results/prim/meshes/white_pot_ep41_fit.glb (kit-of-parts, ep41) | 355ad72e397e1080 | 0.437 -> 0.342 | 6.7 -> 3.05 |
| white_pot_lid.glb | results/prim/meshes/white_pot_lid_ep2_fit_v2.glb (kit-of-parts, ep2, T_LID 2.5) | 0bac47f4b86e9ae3 | 0.421 -> 0.220 | 8.1 -> 4.46 |
| plastic_dish_rack.glb | results/prim/meshes/plastic_dish_rack_joint_v2.glb (kit-of-parts, joint 12/13/27, T_WALL 2.5) | c22f504ccb8855418 | 0.555 -> 0.456 | 6.0 -> 5.37 |
| blue_cup.glb | cdo-sprint/C0/meshes/ep21_blue_cup_g1.glb (obs-lathe, ep21) | 81a201cb23325161 | 0.523 -> 0.291 | 10.0 -> 4.1 |

All other files are byte-identical to meshes/library_v3x. Provenance: same tier as library_v3 (tier P1: our points along
library_v3-anchored tracks); the lid and rack wall thickness 2.5 mm equals values that once leaked from the scans (the
clean-up round passed at 1.5 / 2.5 / 4.0 mm); the blue-cup GT-free selector was written after the lathes were scored.
