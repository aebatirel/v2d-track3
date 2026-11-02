# meshes/tierB_pack12e — Tier B meshes for pack 12e (2 Nov 2026)

**Ground truth entered the selection.** Each mesh was chosen as the best of many candidates by its CD-O against the
organisers' public object scans. Those scans are ground-truth geometry of the same physical objects that appear in the
eval episodes. For the sweeper, two of its construction rules were also changed after a comparison with the scan.
- No mesh was built from a scan, and none is a byte copy (md5 checked against all 10 public scans).
  `tools/no_oracle.py` accepts all five.
- Eval episodes were never scored or used for tuning.
- The owner approved this tier ("Okay I give you permission for all"), relayed by keen-heisenberg at 19:00 UTC on 2 Nov.
- Source and full record: docs/research/mesh-2026-10-26/cdo-sprint/C3/tierB/README.md at commit 332eb5b (branch
  claude/bold-albattani-6qmxsv).

These are byte copies of the source files, renamed to the object names. Transform none.

| File | Source file (C3/tierB/meshes/) | md5 | Replaces in pack 12d | Eval (slot) |
|---|---|---|---|---|
| water_pitcher.glb | water_pitcher_hy21_ep22_k174_s42_lib.glb | e59c15a3e4a442ebc52e7cd72ab73124 | T3 fit 61503a91… | 20 (1) |
| mini_sweeper.glb | mini_sweeper_P1_partprog.glb | 55fe1682f09721ca5d4e98477bfef150 | library_v3 c126a8ff… | 19 (0), 30 (0) |
| plastic_dish_rack.glb | plastic_dish_rack_dev1_ep31_full.glb | 1176443c748ece893ffdb64a1cc82c9a | C0 rack bbca8ec0… | 14 (1), 15 (0), 16 (0), 28 (0), 30 (1) |
| wooden_piece_1.glb | wooden_piece_1_ep24_occ_d2.glb | 015aaae3183760cd8a48d82b5599d32c | library_v3 d152b2b5… | 25 (0) |
| wooden_piece_2.glb | wooden_piece_2_ep24_occ.glb | bf82e385cac24a586168b4f14bf5b245 | library_v3 825a7fe3… | 25 (1) |

- The pitcher file has 400,000 faces (7.2 MB). At packing, the kit's budget_mesh (fast_simplification 0.2.0) cuts it to
  the face budget.
- The pitcher is the same git blob as the source file on bold-albattani's branch, so this copy adds no new object to
  the repository.
