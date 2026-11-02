# meshes/tierBplus_pack13f — Tier B+ meshes for pack 13f (2 Nov 2026)

**Ground truth entered the selection**, as for meshes/tierB_pack12e.
- Each mesh is the best generator output by CD-O against the organisers' public object scans. Those scans are
  ground-truth geometry of the same physical objects that appear in the eval episodes.
- Each was then placed in the library_v3 frame without ground truth (C1/T2 place.py) and scored once [D].
- Both were generated from public-episode video frames. Neither is a byte copy of a scan (md5 checked) or a scan template.
  `tools/no_oracle.py` accepts both.
- Same owner approval as Tier B ("Okay I give you permission for all", relayed by keen-heisenberg at 19:00 UTC on 2 Nov).
- **Inclusion timing:** at 19:12 UTC the mesh lane held these back, because they would not change a CD-O rank. The
  coordinator (keen-heisenberg) reversed the hold at 19:22 UTC, after pack 12e's board result showed that meshes also move
  the pose boards. That board result decided whether to include these meshes, not which variant to pick; each variant was
  chosen by public-scan CD-O.
- Source and full record: docs/research/mesh-2026-10-26/cdo-sprint/C3/tierB/README.md, section "Added for pack 13f (B+)",
  at commit 4a3b67f (branch claude/bold-albattani-6qmxsv).

These are byte copies of the source files, renamed to the object names. Transform none.

| File | Source file (C3/tierB/meshes/) | md5 | Replaces | Eval (slot) |
|---|---|---|---|---|
| blue_cup.glb | blue_cup_sam3d_ep22_k156_s7_lib.glb | 672c4048e11afe9b2b9a7eafebbefe58 | C0 cup 9e3a74fd… | 10, 14, 20, 32, 33 (0) |
| mini_dust_pan.glb | mini_dust_pan_hy21_ep39_k297_s42_lib.glb | 1530b1d3be77507730b00e1c5047cad1 | C1 T2 pick 19765405… | 19 (1), 38 (0) |

Both files have 400,000 faces (7.2 MB each). At packing, the kit's budget_mesh (fast_simplification 0.2.0) cuts them to
the face budget. They are the same git blobs as the source files, so these copies add no new objects to the repository.
