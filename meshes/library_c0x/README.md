# library_c0x: CD-O sprint candidate C0 (packed-mesh swap), built 2026-10-31

This folder is meshes/library_v3x with four files replaced. Use it as the packed (submitted) mesh only; the simulator assets
and rollouts stay library_v3x. Details, scores, flags and the AUC guard: docs/research/mesh-2026-10-26/cdo-sprint/C0/README.md
and MANIFEST.json (status and flags updated 2026-10-31, stage 4).

**What ships (pack 9a, focused-pascal 50004a7): pot, lid and rack only.** The blue cup passed the AUC guard but is held
back (its GT-free selector was written after its lathes were scored against the scan); pack 9a keeps the library_v3x blue cup
unless the owner includes this one.

| file | source | sha256 (16) | public-scan CD-O cm [D], library_v3 -> C0 | ADD mm [D] | in pack 9a |
|---|---|---|---|---|---|
| white_pot.glb | results/prim/meshes/white_pot_ep41_fit.glb (kit-of-parts, ep41) | 355ad72e397e1080 | 0.437 -> 0.342 | 6.7 -> 3.05 | yes |
| white_pot_lid.glb | results/prim/meshes/white_pot_lid_ep2_fit_v2.glb (kit-of-parts, ep2, T_LID 2.5) | 0bac47f4b86e9ae3 | 0.421 -> 0.220 | 8.1 -> 4.46 | yes |
| plastic_dish_rack.glb | results/prim/meshes/plastic_dish_rack_joint_v2.glb (kit-of-parts, joint 12/13/27, T_WALL 2.5) | c22f504ccb885541 | 0.555 -> 0.456 | 6.0 -> 5.37 | yes |
| blue_cup.glb | cdo-sprint/C0/meshes/ep21_blue_cup_g1.glb (obs-lathe, ep21) | 81a201cb23325161 | 0.523 -> 0.291 | 10.0 -> 4.1 | no (held back) |

All other files are byte-identical to meshes/library_v3x. Repo paths are relative to docs/research/mesh-2026-10-26/.

**Frame.** All four were fitted to our stereo points along the same library_v3-anchored tracks. Rigid ICP onto
library_v3 moves pot 1.9-2.5 mm / ~1 deg, lid 2.5-3.0 mm / ~1.3 deg, rack ~2.1 mm with a real ~2.3 deg rotation, and
blue cup 6.7 mm / 2.6 deg (mostly along the cup axis), so "same frame as library_v3" holds for pot, lid and rack within
a few mm, not for the blue cup. Aligning them onto library_v3 lowers registered AUC (cdo-sprint/C0a-diag), so they are
shipped as fitted.

**Flags (read before using):**
- **Marker balls (pot, lid, rack):** the ball radius prior MK_R0 = 7 mm and the free-fit window 5-9.5 mm in
  prim_potlid.py (also used by prim_rack.py) are scan-derived (marker catalogue fitted on the public scans; audit in
  the work log, 27 Oct ~17:20 UTC). These meshes carry 7.00 mm balls; their 27 Oct scan passes are provisional until
  rebuilt with a generic ball rule.
- **Thickness:** lid T_LID and rack T_WALL 2.5 mm equal values that once leaked from the scans (the clean-up round
  passed at 1.5 / 2.5 / 4.0 mm; 2.5 was the pre-registered default).
- **Blue cup:** GT-free selector written after the lathes were scored; not watertight after the kit budget (11 bodies).
- **Provenance:** same tier as library_v3 (our points along library_v3-anchored tracks); library_v3 itself was fused
  along scan-templated tracks (open organiser question). The C0 object set was chosen using public-scan scores.
