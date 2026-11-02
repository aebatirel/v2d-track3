# meshes/posepack_13f1p — the pose-pack meshes on 13f1 (2 Nov 2026)

Byte copies, renamed to the object names; transform none. **Chosen for the pose boards by public cross-validation**
(tracking-perception, docs/analysis/ptrk-20261102/PREREG_posemesh.md + addendum 1, branch claude/perception-tracking-20261102
@ 029145e). The CV is a 10-seed, leave-one-episode-out pose score on public episodes. It reads public mocap, which is
development; no eval result is read.

| File | Source | md5 | Evals (slot) | Origin |
|---|---|---|---|---|
| white_pot.glb | claude/bold-albattani-6qmxsv @ 30186bb, docs/research/mesh-2026-10-26/cdo-sprint/C4-audit/meshes/white_pot_potlid_tsdf_ep43.glb | 3591440e2dbf2029be908d46b29bfc96 | 1, 3, 5, 6 (0); 8, 28 (1) | Primitive pot fit to our own public-ep43 points (GT-free), library_v3 body frame. **Its candidacy was GT-informed:** it was the best existing pot by public scan-registration ADD. Adopted by the public pose CV: held-out mean ΔAUC +0.0206, min +0.0008 over 9 pot episodes. |
| plastic_dish_rack.glb | meshes/library_c0/plastic_dish_rack.glb (@ 30186bb; same as 12c's payload source) | bbca8ec0c26e6e37baaa145cef4e48e5 | 14 (1), 15 (0), 16 (0), 28 (0), 30 (1) | Our earlier GT-free library_c0 rack (packs 9a+ to 13b). Adopted by the same CV: held-out mean +0.0234, min 0.0 over 5 episodes. Reverts the Tier B rack. |
