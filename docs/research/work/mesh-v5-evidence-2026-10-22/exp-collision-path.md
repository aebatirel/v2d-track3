## S5 collision geometry: findings

**Bottom line:** S5 needs no change on the evaluator side. Our runs already simulate our own URDFs, and FlashCHORD passes each convex piece through unchanged. But none of the decompositions keeps the ep24 boards assembled within 2 mm, and none gets hull overlap to ≤ 1 cm³. That is not the decomposition's fault: our meshes already overlap at the tracked poses, and the simulator itself lets resting objects sink several mm into the table.

The repo was not modified. All outputs are in `/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/v5/s5coll/` (written `$W` below). Exact commands and versions are in `$W/COMMANDS.txt` and all numbers in `$W/results.json`. No depth was fetched.

Labels: [M] measured with method inputs only, [D] diagnostic, [E] estimate, [H] hypothesis, [code] read from source. The Design O boards and the `loc/perc` tracks have contaminated inputs (critique 10), so ep24 numbers support global method choices only. The `perc2m` tracks are our own.

### 1. How our objects reach the simulator [code, plus M where stated]
- **Which URDF the evaluator loads:** the kit's `run_policy_evaluation.py` runs `evaluate_policy.py`, which reloads the checkpoint's saved config. Its `task.parquet` is our reference, and `object_urdf_paths` in it were written by `mkref --assets`/`ASSETS`, i.e. `make_assets.py OUT/urdf/<n>_rigid.urdf`. `decompose_objects` is true in `scene/{train,eval}.yaml`. Kaggle scores the trajectories we submit and does not re-simulate. The only requirement: the URDF and piece files must exist at the paths stored in the parquet when we run the evaluator.
- **FlashCHORD version:** the local checkout is 7eb9721; `scene/objects.py`, `assets/mesh.py` and `scene/builder.py` are byte-identical to the kit pin 8c778f9 [M].
- **Several `<collision>` meshes per link:** Newton `add_urdf` makes one shape per `<collision>` mesh. A multi-node GLB is merged into one mesh by `trimesh.load(force='mesh')`, so it would become one shape. Pieces must therefore be separate `<collision>` elements, one file each. Measured: 32 `<collision>` elements gave 32 collision shapes and 32 MuJoCo geoms per board [M].
- **Re-decomposition:** FlashCHORD runs CoACD (threshold 0.05) on every collidable mesh shape. An already-convex piece comes back as one hull; geometry changed by at most 0.024 mm [M]. All 256 of our pieces (all objects, every run) came back as exactly one hull each [M].
- **64-vertex cap:** MuJoCo collides with hulls of at most 64 vertices. Our pieces are reduced to ≤ 64 vertices beforehand; CoACD's own hulls (up to 256 vertices) get truncated by MuJoCo.

### 2. ep24 boards (frames 213–273 every 4th frame; f274 end state)

| Collision set | Hulls (board 1 / board 2) | Hull union of board 1 (cm³) | Hull overlap, median (max), `loc/perc` | Same, `perc2m` |
|---|---|---|---|---|
| v4, default CoACD | 18 / 9 | 322 (mesh 202) | 16.8 (17.1) | 16.7 |
| O 4096-face submitted mesh, default CoACD | 9 / 12 | 266 (mesh 149) | 13.5 (13.9) | – |
| O full-res watertight, default CoACD | 10 / 20 | 208 | 6.7 (7.3) | 7.0 |
| O full-res, our pieces | 32 / 32 | 178.5 | 4.1 (5.4) | 4.6 |
| O full-res, our pieces, interaction-weighted | 32 / 32 | 176 | 3.0 (4.7) | 3.6 |
| Same, 16 pieces | 16 / 16 | 185 | 3.95 (5.3) | – |
| Mesh–mesh overlap (the floor) | | | 1.2 (1.1–1.7) | 1.5 |

- **Why ≤ 1 cm³ is out of reach [M]:** the O meshes themselves interpenetrate at the tracked assembled pose, with a median point depth of 2.5–2.7 mm. O board 2 is 12.0 mm thick (median), but board 1's slot is only 9.5 mm wide (10th percentile 7.1 mm), so the assembled state cannot exist without about 2.5 mm interference. MuJoCo's initial contact depth is 6.3–7.6 mm for every O variant and 11.0 mm for v4.
- **Replay setup:** I stepped Newton/MuJoCo Warp on the CPU device exactly as `RLEnv` does: dt 0.01 s, no object assist, hands parked 3 m away with actuators off, boards lowered as a group onto the table, 2 s.

  | Variant | Relative drift max / mean (mm), `loc/perc` | Same, `perc2m` | Tilt (°) |
  |---|---|---|---|
  | v4 default | 8.9 / 5.3 | 18.5 / 7.9 | 18 / 6–11 |
  | O full-res default | 10.0 / 6.3 | 10.1 / 8.0 | 11–12 / 22 |
  | O pieces | 46 / 22 | 11.4 / 5.4 | 15–34 / 4 |
  | O weighted pieces | 8.6 / 5.1 | 10.7 / 6.7 | 4–5 / 6 |
  | O 4096-face default | 14.3 / 8.3 | 5.3 / 2.3 | 8–21 |

  No variant stays within 2 mm. Results swing by up to 4× between the two track sources, so two poses cannot rank the variants. The weighted pieces are the only variant that stays upright (≤ 6°) from both poses.
- **Control [M]:** a single box resting on the table sinks 9.6 mm and tilts 1° in 2 s. That comes from FlashCHORD's contact settings (solref 0.02/1.58, dt 0.01, one contact point per convex pair because multi-contact is disabled). The pot resting on many pieces sinks only 0.4 mm. So a 2 mm criterion is below the simulator's own resting error for objects with few contact points.

### 3. ep2 lid on pot, ep18 sweeper standing
- **Lid at the tracked seated pose [D]:** the meshes overlap by 25 cm³ (median depth 8 mm). Hull overlap is 43.0 cm³ with default CoACD and 31.4 with our pieces (64-piece pot, 32-piece lid). In the replay the lid pops off: mean relative drift 33.6 mm (default) vs 22.7 mm (pieces).
- **Lid lifted 15.3 mm until the meshes no longer overlap:** hull overlap is 0.098 cm³ (default) vs 0.027 (pieces).
  - At +0 mm: default stays seated (2.8 mm mean drift, 2.6° tilt); with our pieces the lid tips 74° after 0.8 s.
  - At +1, +2, +4 mm: default 6.7 / 7.8 / 8.8 mm, pieces 6.4 / 8.5 / 8.5 mm mean drift, tilt 3–7° for both.
  - So neither collision set is consistently better.
- **Pot alone:** stable with both (0.5 mm, 0.2°).
- **Pot decomposition:** default CoACD gives 31 hulls with a union 1.39× the solid volume. Ours needs 64 pieces to reach 1.20×.
- **ep2 setup caveat:** the replay assumes the pot rests upright. Its flat base sits 11.8° off its x axis, so I placed it on that base.
- **ep18 sweeper (library_v3):** its flat base is 9.75 cm² with the centre of mass 3.7 mm inside the edge, about 3.4° from tipping [M].
  - At the tracked pose, which is 4.4° off the flat base, both collision sets fall over.
  - Set exactly on its flat base: default CoACD (19 hulls, 3 touching the base plane) topples at 0.6 s and the simulation goes to NaN at 1.64 s. Our 30 pieces (4 at the base) stay standing: 3.6° tilt, ≤ 4 mm in 2 s [M].
  - [H] Standing depends on how many pieces touch the table, because each piece gets only one contact point. Test that would falsify it: rerun with `enable_multiccd=True`; if default then stands too, contact count is the cause.

### 4. Scene build cost (CPU, CoACD cache warm, ep24 scene)

| Worlds | v4 default (27 hulls) | Weighted pieces (64) |
|---|---|---|
| 1 | 2.8 s / 617 MB | 3.3 s / 635 MB |
| 64 | 3.6–3.7 s / 693 MB | 4.6–4.7 s / 769 MB |
| 256 | 6.5–7.4 s / 927 MB | 8.7–9.0 s / 1270 MB |
| 1024 | 22.4 s / 1.92 GB | 41.1 s / 3.32 GB |

- At 64 worlds that is 1.25× the time and 1.11× the memory, which passes the plan's "≤ 2×" gate. I could not reproduce the plan's "4.2 s, 0.61 GB" baseline; the v4 numbers above are my own baseline.
- Memory per world doubles (1.27 → 2.63 MB), so 4096 worlds would need about 5.8 vs 11.4 GB of host memory [E]. I did not measure this on a GPU box.
- First (uncached) CoACD on the full-res O boards takes 20–35 s per board. My decomposition prototype takes 2.4–5.9 min of CPU per object.

### Build recipe (S5)
1. Build collision from the full-res watertight mesh, in the submitted mesh's body frame. Never use the 4096-face packer output: CoACD refills the slot (13.5 vs 6.7 cm³).
2. Decompose (`$W/scripts/decomp.py`):
   - Solid from winding number; free space = more than 0.5–0.75 mm outside the mesh.
   - Split recursively with planes along the piece's, the mesh's and the excess region's principal axes, 19 offset quantiles, 1 mm overlap between cells.
   - Stop when every piece holds ≤ 0.3 cm³ of free space, or at 32 pieces (64 for the pot).
   - Each hull reduced to ≤ 64 vertices.
   - Optional weighting: λ = 10 on free space the partner object occupies (within 1 mm) under our own tracks.
3. `make_assets`: one OBJ and one `<collision>` element per piece; visual = full mesh; inertia as today.
4. `mkref` and FlashCHORD unchanged. `check_urdf` will warn "differs from the pose mesh"; that is expected.

### What to port
- `pipeline/collision_decomp.py` from `decomp.py` (keep the chunked inside-test: without it, the lid run was killed for memory).
- A `--pieces` option in `make_assets.py`.
- `tools/replay_rest.py`, Newton engine only, plus `hullovl.py`, as the S5 acceptance test.
- Do not port the CPU-MuJoCo replay: there the pot alone drifted 15–28 mm, against 0.5 mm in MuJoCo Warp. Do not port `--hold` either: holding is invalid with the Newton engine because resetting Newton's state does not move MuJoCo Warp's copy. These runs are kept but marked superseded in `rep/{old_*,dt002,cpu_dt01,nt_actuators_on}`.

### Corrections to the plan
- Replace "hull overlap ≤ 1 cm³" and "ep2 ≤ 2 cm³" with "hull overlap minus mesh overlap ≤ 1 cm³". The actual blockers are mesh fixes in S1/S3: board 2's thickness and the lid–pot interference.
- At 32 pieces the "union ≤ 1.15× solid" gate fails for board 1 (1.18–1.19), the lid (1.18) and the pot (1.20). The "≤ 32 hulls" gate fails for the pot.
- S5(d)'s falsification test ("boards separate > 2 mm") fails for every variant, including default CoACD. So it does not argue for changing FlashCHORD's decomposition config.