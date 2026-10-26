# Submitted-mesh swap test (26 Oct 2026; development on public twins, scored against public mocap)

The kit scores each object only after registering our SUBMITTED mesh to the scan. A badly reconstructed mesh
mis-registers and costs score even when the simulated motion is right.

**Method:**
- Stored public rollouts made with library_v3 (episodes 2, 11, 12, 21, 27; 3 rollouts each) were re-scored with
  `pipeline/score_registered.py`.
- One object's mesh is swapped at a time, for one of OUR alternative reconstructions: the approach-2 lathe fit, and
  the appendage-only faces. Both are derived from our own mesh, in its frame.
- `run.py` → `results.json`, `summary.txt`.

| Object | Lathe variant (Δ episode AUC) | Appendage-only (Δ) | Decision |
|---|---|---|---|
| water_pitcher (ep21) | **+0.098** | +0.163 | **switch to the lathe** (eval 20) |
| blue_cup (ep11 / 12 / 21) | −0.022 / −0.044 / +0.023 | −0.010 / −0.019 / +0.046 | keep |
| beige_cup v3 (ep11) | −0.013 | +0.007 | keep |
| white_pot (ep2 / 27) | −0.003 / +0.002 | −0.175 / −0.463 | keep |

**Why not the appendage-only pitcher:**
- It scores above the scan itself (0.940 vs 0.907). It cannot register better than the true shape, so the excess is
  most likely compensation of this rollout's errors and would not transfer.
- It is also a partial mesh.
- The lathe variant stays below the scan, as a genuine registration improvement should.

**Expected (estimate):** ≈ +0.1 on eval 20's AUC, i.e. ≈ +0.005 Track 3 AUC, if eval 20 behaves like its twin.

## Test 2: our other library versions (`test2/`)

Rollouts: ep24 and ep18 from `20261024-ev3-2c1e4dd`, ep31 from `20261024-ev30rp-07eef1a`, all library_v3. The
script's "base" is library_v2's meshes; for the sweeper, v3 is what the rollouts used.

| Object | Swap | Δ episode AUC |
|---|---|---|
| boards (ep24) | v4 flattened vs v3 | ±0.000 |
| sweeper (ep18 / ep31) | v3 vs v2 | +0.007 / −0.005 |
| dust pan (ep18) | v1 vs v3 | −0.001 |

No other swap is worth making; only the pitcher changes.
