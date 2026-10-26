# library_v3p (26 Oct 2026): library_v3 with a lathe-completed water pitcher (NOT USED from pack 6 on)

> Used in pack 5 only. Leaderboard 0.80941 vs pack 4 0.81056, while evals 10 and 32 predicted ≈ +0.003, so
> the swap most likely cost ≈ −0.004 on eval 20. Reverted by owner decision (work log, 26 Oct ~16:15 UTC).

Every file equals `meshes/library_v3` except `water_pitcher.glb`.

**The pitcher is OUR reconstruction, shape-completed.** It is the approach-2 lathe fit of library_v3's pitcher, in its
frame: the body is replaced by the rotationally symmetric lathe body fitted to our mesh, and the appendage faces
(handle, spout) are kept.
- Built with `docs/research/approaches-2026-10-25/approach2-scripts/lathe_fit.py`.
- Fit parameters: `water_pitcher.lathe.json`.
- No scan or ground truth is used to build it.

**Why it was chosen (development, public data only; `docs/analysis/meshswap-20261026/`):**
- Registered score vs public mocap of the same three stored ep21 rollouts: episode AUC 0.776 → 0.874 (pitcher
  0.595 → 0.773).
- The public scan as the mesh gives 0.907 (the upper bound).

**Use:** the policies were simulated with library_v3's collision copy. Only the SUBMITTED mesh of eval 20 changes
(`pack_eval.sh EP_LIB 20:meshes/library_v3p`), so the kept rollout stays valid: same body frame.
