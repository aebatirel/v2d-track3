# C0a post-hoc diagnostic (31 Oct 2026): does aligning C0 onto library_v3 help registered AUC?

The owner asked "Cant you fix the rotation and scale error". focused-pascal built C0a: C0's meshes rigidly ICP-aligned
onto library_v3 (meshes/c0a_20261031 on claude/focused-pascal-2nz9s1, 9c2d00e). Scale does not matter: the kit
rescales.

This is a **post-hoc diagnostic**: it is not in the C0 PREREG, and it did not choose anything (focused-pascal's
pre-registered MESH_RULE picked as-fitted C0 for pack 9a).

Runs: `run_c0a.sh`. Same public twins, tracks, base runs (`cdo-sprint/C0` guard) and `score_registered.py` call; only
the mesh dir changes. 21/21 OK. JSONs in `runs/`, mesh hashes in `mesh_sha256.txt`.

| Object | n | C0 mean / min dAUC | C0a mean / min dAUC | dMPPE C0 / C0a (cm) | dRPE C0 / C0a (cm) |
|---|---|---|---|---|---|
| pot | 9 | +0.0030 / -0.0159 | +0.0006 / -0.0176 | -0.057 / -0.027 | -0.108 / -0.076 |
| lid | 2 | +0.0055 / 0.0000 | +0.0055 / 0.0000 | -0.079 / -0.083 | -0.121 / -0.146 |
| rack | 5 | +0.0158 / -0.0092 | -0.0046 / -0.0356 | -0.043 / +0.070 | -0.097 / -0.085 |
| blue cup | 5 | +0.0241 / -0.0049 | +0.0097 / -0.0004 | -0.249 / -0.156 | +0.163 / -0.056 |

**Reading [D]:**
- Aligning onto library_v3 makes registered AUC worse or equal on every object.
- The rack would fail the C0 guard (min -0.036 < -0.02).
- The few-degree "rotation" of C0 against library_v3 is mostly library_v3's own frame error. Meshes fitted to our
  observations land closer to the real object frame.
- Consequence for E0 and later eval-built meshes: do not align them to library_v3.

**Caveats:** n = 2-9 public twins per object; public scans stand in for the hidden ones; perception tracks, not
rollouts.
