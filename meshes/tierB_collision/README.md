# meshes/tierB_collision — Tier B meshes as SIMULATOR COLLISION geometry (2 Nov 2026, pf-mesh lane)

**Ground truth entered the selection of these shapes** (CD-O against the organisers' public object scans; see
meshes/tierB_pack12e/README.md on claude/focused-pascal-2nz9s1). Used here as collision geometry in training and rollouts,
so the arms that use them (docs/research/work/pf-mesh-20261102/PREREG.md) depend on GT-selected geometry; owner approval
"Okay I give you permission for all" (19:00 UTC, relayed by keen-heisenberg); coordinator's task 20:13 UTC.
In our template frame already (transform none; vs library_v3: centroid shift ≤ 14 mm, Chamfer mean 3–9 mm).

| file | source (meshes/tierB_pack12e/, focused-pascal) | md5 here | note |
|---|---|---|---|
| blue_cup.glb | meshes/tierBplus_pack13f/blue_cup.glb 672c4048… (400k faces) | 95248a76… | quadric decimation to 20k faces; vs source Chamfer mean 0.90 mm, p99 2.07 mm |
| water_pitcher.glb | water_pitcher.glb e59c15a3… (400k faces) | d75b168b… | quadric decimation to 20k faces (trimesh); vs source Chamfer mean 1.40 mm, p99 3.30 mm, centroid 0.2 mm |
| mini_sweeper.glb | mini_sweeper.glb | 55fe1682… | byte copy |
| plastic_dish_rack.glb | plastic_dish_rack.glb | 1176443c… | byte copy |
