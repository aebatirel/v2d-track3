# library_e0: CD-O sprint candidate E0 (C0's methods rebuilt on the eval episodes), packaged 2026-10-31

This folder is meshes/library_c0 with blue_cup.glb first reset to meshes/library_v3/blue_cup.glb, then every object whose
PREREG section 6 recommendation is E0 replaced by its E0 pick. All four (pot, lid, rack, blue cup) are E0, so it is
meshes/library_v3 with those four files replaced. Use it as the packed (submitted) mesh only; the simulator assets and
rollouts stay library_v3. Eval 8 uses meshes/library_e0x (as library_v3x).

**Open ship gates (2026-10-31 report step; details in cdo-sprint/E0/README.md section 3 and MANIFEST.json `ship_gates`):**
- **G1 (pot, lid, rack):** the marker balls use the scan-derived 7 mm prior and 5-9.5 mm window (verify_0 B1). The
  owner's "Ship 9a, flagged" covers the C0 meshes only, so these three need an explicit owner decision, or the
  scan-free E0b rebuild instead. The blue cup is not affected.
- **G2 (all four):** the packed mesh also drives the five pose boards (the kit registers it), and E0 has no public-twin
  AUC guard (verify_1 B1). Either use these meshes for the CD-O submission only, or run C0's guard with them first.
- **Not a drop-in for pack 9a+:** this folder keeps library_v3 for beige_cup and mini_dust_pan, which pack 9a+ replaced
  (C1). Merge the four E0 objects one by one into the current pack library; do not pack this folder whole.

Details, flags and per-pair records: docs/research/mesh-2026-10-26/cdo-sprint/E0/MANIFEST.json and README.md.
Built on Vast run mesh-20261031-e0-b05f001 (code b05f001) with the frozen public code of commit 2971a10.

| file | source | md5 | sha256 (16) | obs fidelity on ALL eval points, mm: E0 / C0 / library_v3 [M, in-sample for E0] | eligible / candidates |
|---|---|---|---|---|---|
| white_pot.glb | E0 pick `pot/ep3/fit` (cdo-sprint/E0/meshes/white_pot_eval3_fit.glb) | 858fc4c64b147eb2245bdcced9a29f73 | af321725727cb1d5 | 2.922 / 2.914 / 3.881 | 18/24 |
| white_pot_lid.glb | E0 pick `lid/ep1/t2.5_fit` (cdo-sprint/E0/meshes/white_pot_lid_eval1_t2.5_fit.glb) | 08b65d4f7080e55c6ee81be9fa19cf8f | e3dd5861a5081e44 | 1.675 / 1.772 / 5.186 | 1/2 |
| plastic_dish_rack.glb | E0 pick `rack/joint/joint` (cdo-sprint/E0/meshes/plastic_dish_rack_eval_joint_joint.glb) | 9b8adbe3bbdf09666f604436aa4cade4 | fc67c59baa1cab06 | 6.419 / 6.245 / 5.881 | 12/12 |
| blue_cup.glb | E0 pick `cup/ep32/g1` (cdo-sprint/E0/meshes/blue_cup_eval32_g1.glb) | b479269e3ee21266db84df8a17bfdc1c | e6c18b2ae40dcdeb | 2.646 / 2.723 / 2.906 | 11/11 |

All other files are byte-identical to meshes/library_c0 and meshes/library_v3.

**Not scored**: there is no eval ground truth. Fidelity is GT-free and is not CD-O.

**Flags (read before using):**
- **Marker balls (pot, lid, rack):** built with the frozen prim_potlid.py (c2627630), whose ball radius prior MK_R0 = 7 mm
  and free-fit window 5-9.5 mm are scan-derived (same flag as C0).
- **Thickness (lid, rack):** T_LID and T_WALL 2.5 mm = grid midpoint of the public clean-up round (passed at 1.5 / 2.5 /
  4.0 mm); equals a value that once leaked from the scans; not chosen by any eval number.
- **In-sample pick:** each E0 pick was chosen by fidelity on the same eval points it was fitted to. Pot and rack do not
  beat C0 even in-sample (within the pre-registered 15 % margin, so E0 by rule). On the rack, library_v3 has the lowest
  fidelity of all 14 meshes (reviewer note; the rack rule compares C0 only).
- **Method qualifier:** the object set and the methods come from C0, which was chosen with public-scan scores.
