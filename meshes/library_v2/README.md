# Mesh library v2 (2026-10-21)

Our reconstructed meshes (route A), one per object, built from public episodes by `pipeline/recon_mesh.py` and
coloured from video by `pipeline/mesh_color.py`. Same as `library_v1` except:

- `mini_dust_pan` (episodes 39, 40, 18) and `white_pot` (41, 44, 2, 27) rebuilt with `--below_carve 0.004` (space under
  each frame's table plane is free) and the 65° table-plane cone. v1 filled the never-seen undersides: the pot reached
  5.5 cm and the dust pan 3.5 cm under the table (scans ≤ 0.5 cm), so mkref rejected the table (ep18). v2: lowest point
  −0.2…−0.6 cm (scan −0.1…+0.2), pot extents 13.1 × 19.0 × 36.2 cm (scan 13.2 × 18.9 × 35.7).
- Registered AUC vs the public scan, dust pan: ep39 0.992 → 0.982, ep40 0.971 → 0.963, ep18 0.920 → 0.917 (CD-O
  0.52 → 0.33 cm). The small drop is accepted: v1 cannot be simulated.

The simulator gets colourless copies (`pipeline/make_assets.py`): Newton splits coloured meshes into one shape per
colour (174 fragments per board), which killed the 4096-world training build.
