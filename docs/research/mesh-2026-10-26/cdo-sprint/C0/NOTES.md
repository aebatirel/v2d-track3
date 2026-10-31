# C0 notes (CD-O sprint, candidate C0, stage 1)

Times UTC. Each line: what ran, command, output path, result.

- 2026-10-31T15:23:12Z created C0 dir and NOTES.md; read STATUS.md and CLAUDE.md.
- 2026-10-31T15:25:01Z step 1 (mesh identity): matched by sha1[:16] (mesh_metric.py sha()) to score records: pot results/prim/meshes/white_pot_ep41_fit.glb = potlid/metric_all potlid/fit/ep41 4bf2135570c1da26 (0.3417/3.047/0 flips); lid results/prim/meshes/white_pot_lid_ep2_fit_v2.glb = clean/lid_scores clean/lid/t2.5_fit 67632273f5723dc9 (0.2199/4.46/0); rack results/prim/meshes/plastic_dish_rack_joint_v2.glb = clean/rack_scores clean/rack/t2.5_lean1 b855279b68ecb432 (0.4560/5.368/0); blue cup scratchpad lathe/ep21_blue_cup_g1.glb = lathe_obs.jsonl lathe_obs_g/a1/ep21/blue_cup 1bd4c8f5f475596f (0.2906/4.088/0). Library_v3 files match baseline_library.jsonl sha1 (all 11 + v3x beige). Flags: lid 2.5 leaked value; blue-cup obs_fidelity selector was written after the 5 lathe scorings (work log 26 Oct 16:40), not pre-registered.
