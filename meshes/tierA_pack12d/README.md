# Tier A meshes for pack 12d (2 Nov 2026)
Byte copies of bold-albattani's CD-O sprint C1 track T3 (generate-then-fit) outputs. Branch
claude/bold-albattani-6qmxsv, commit 25b0c54; recommendation in docs/research/mesh-2026-10-26/cdo-sprint/C3/README.md.
PREREG 2d2a8ee was pushed before scoring, with one fitted mesh per object, so these are the single pre-registered outputs
of that track (Tier A, "clean"). Tier B (GT-informed selection) is NOT used.
- `white_pot.glb` = C1/T3-gen-fit/meshes/white_pot_t3fit.glb, md5 b19b2e2876945cba4d932ad531f049ce, 72,852 B.
  - For evals 1, 3, 5, 6, 8, 28; it replaces the C0 / C0x white_pot (md5 0264da83…). Transform none.
  - T3 CD-O gate: WIN. The mesh lane's pose guard FAILED (mean dAUC −0.0099, min −0.042 on ep45).
- `water_pitcher.glb` = C1/T3-gen-fit/meshes/water_pitcher_t3fit.glb, md5 61503a91d787ed0643ef40699805d1d0, 72,920 B.
  - For eval 20, slot 1; it replaces library_v3 water_pitcher (md5 fc824fc5…). Transform none.
  - CD-O ok; the ADD check FAILED (add_med 33.0 mm): pose boards on eval 20 are at risk.
- Both have 4,000 faces (within the kit budget) and were scored at transform none. Submitted-mesh payload swap only;
  rollouts and simulator assets are unchanged. Approved under the owner's standing go (relayed by keen-heisenberg,
  08:50 UTC 2 Nov).
