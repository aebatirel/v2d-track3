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
