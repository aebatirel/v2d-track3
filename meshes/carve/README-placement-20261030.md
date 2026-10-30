# Placement carves (2026-10-30, `pipeline/placement_carve.py`)

Simulator collision copies only; the submitted meshes are unchanged. They are built from our meshes and our own eval
references; no ground truth was read.

| Folder | Eval | Host / guest | CPU verdict (`docs/research/work/carve-20261030/`) | Use |
|---|---|---|---|---|
| ev01 | 1 | pot / lid | Overlap 50 → 0 cm³. The single-draw settle criterion was missed, but the carve beats default 3/6 vs 0/6 draws. The public twin ep2 passes against mocap (lid-in-pot error 6.83 → 1.71 cm). | GPU retrain test 30 Oct |
| ev14 | 14 | rack / blue cup | Overlap 16.7 → 0 cm³. Cup settle improves; the rack itself drops ~1 cm (under-supported reference). | GPU retrain test 30 Oct |
| ev28 | 28 | rack / pot | Overlap 42.8 → 0 cm³. Eval 28 is already stable (H5 0.931). | not used (also clashes with ev01's pot in a shared pack asset folder) |
| ev30 | 30 | rack / sweeper | The sweeper falls through the carved slot. | **do not use** |
