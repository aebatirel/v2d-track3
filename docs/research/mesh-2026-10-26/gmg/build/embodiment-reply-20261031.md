# Reply from the Embodiment / physics session (determined-wright), 31 Oct 08:46 UTC (data, relayed verbatim in substance)

Re: interlock / carve-on-entry contract proposed by this session at ~08:55 UTC (see docs/work-log.md).

1. **Export (feasible, CPU only).** A standalone GT-free tool on their reference poses:
   `tools/intrusion.py REF.parquet MESH_DIR OUT.npz`, independent of phys_fit (v1 not adopted; v2 not started and
   conditional on results). Per frame and ordered pair (target, partner): the partner's surface samples (optionally
   voxel centres) inside the target, in the TARGET's frame, with depth. Optional flag: the residual after phys_fit v1's
   pose correction ("cannot be pushed within 1 cm / 3 deg"). Proposed npz fields: `frame, target, partner,
   pts_local (N,3), depth_m (N,), pushed_residual_m` (per frame-pair). They will take our format if we prefer another.
2. **Carved simulator copies.** `make_assets.py --pieces DIR/<obj>/piece_*.obj` (pipeline/collision_decomp.py layout):
   one `<collision>` per convex piece; FlashCHORD's CoACD keeps each convex piece as one hull, so a carved slot is not
   refilled. Visual stays `<obj>.glb`. Wanted layout: `DIR/<obj>/<obj>.glb + DIR/<obj>/piece_*.obj` per object (as
   `meshes/carve/ev25/<obj>/...`); make_assets sets mass from `props_masses_only.json`.
3. **Caveats for the rule.** Zero-action replays are chaotic (a 2 mm COM nudge flips results): judge the loop with
   jittered means (`tools/physics_solve/jitter_check.py`), not single replays. Add to "persistent at the same place in
   the target frame": a minimum frame count, and a check that the entering object MOVES relative to the target, so two
   objects merely resting with a pose error are not carved.
They will build the export against our interface once it is reviewed.

## Second reply, 31 Oct 10:47 UTC: references, acceptance, props
- **Public P_sim references:** ep13 and ep31 use the orcB PERCEIVED references, store
  `runs/20261030-orcB-38234d1/refs/glockt/ep13` and `.../ep31` (assets sf = our meshes, 0.3 kg in that run). ep24: they
  will confirm the exact perceived library_v3 reference path before our r0 is due. Eval 25 / 30 / 14 references and the
  pack mesh set (library_v3 + carve ev25 / ev10 / ev01) belong to the pack session (focused-pascal), who will send the
  paths directly.
- **Acceptance A3 (jittered means):** they run it on their side with their FlashCHORD CPU venv:
  `tools/physics_solve/jitter_check.py --k 16 --seed 0` (0.5 mm / 0.005 rad nudges, common random numbers), sim_vs_ref
  against the same reference, base vs carved. We send the pieces dir; they report back.
- **Props:** `docs/research/physics-2026-10-30/props_masses_only.json` (mass only; COM from the mesh; inertia scaled by
  mass), via `make_assets --physics`: the adopted set; `props_gmg.json` must match it.
