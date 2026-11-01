# posefix NOTES (timestamped; read first on restart)

Scratch: /tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/posefix (= SP below)

- 2026-11-01T04:12:29Z start. Read CLAUDE.md, STATUS.md, INTERLOCK 21.15, collcarve2-eval/precheck_H30_tables.md,
  collcarve2-public/README.md, C0 run_auc_guard.sh + AUC_RESULTS.md. No posefix folder existed.
- 2026-11-01T04:12:29Z inputs found (GT-free): tracks data/sweep/ep*/poses.npz for 20 public eps
  (0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45); stored converted tracks cdo_c0/tracks (15),
  cdo_c1/t2/auc/tracks (18 39 40), cdo_c1/t3/auc/tracks (23 24). Hands: gmg v6 M1 MediaPipe hands
  gmg/runs/20261031-b4ext6-90c8cce/hands/public/ep*/hands.npz (world = camera frame 0 = world_vo, since
  world_T_cam[0] = I). Table: v6 bundle episode.json 'table' (frame-0 depth RANSAC, recon_mesh.table_plane, camera
  frame 0 = world_vo). Parquets staged for 18 eps (cdo_c0/t3, cdo_c1/t3/auc/t3); ep23/24 not staged yet.
- 2026-11-01T04:26:09Z staged (GT-free): SP/mesh9a (10 meshes, md5 in SP/inputs.json), SP/tracks/ep*/ (20 stored
  converted tracks, each array-equal to data/sweep conversion). Video 20 fps. SDF grids of the budget_mesh(4096)
  meshes: 1.5 mm, sign = |median signed-crossing winding over 3 axes| >= 0.5, distance two-tier KD (3 mm coarse,
  0.5 mm dense within 8 mm). First KD-only build too slow (3.8M nodes x 630k samples); replaced, rebuild running.
- 2026-11-01T04:26:09Z GT-free look at ep11 (our poses, our meshes): end rest f~104-136 both cups float above our table
  (blue 20-24 mm, beige 34-35 mm), visual overlap ~97 cm3; start f0-30 blue on table (0 to -2.4 mm), beige 6-7 mm up.
- 2026-11-01T04:53:30Z GT-free measurement of all 20 eps -> gtfree_measure_summary.txt (table penetration at rest is
  pervasive: pots -6..-13 mm, racks -3..-11, dust pan -5..-12; pair overlaps: ep11 ~93 cm3, ep24 10.5, ep31 5.8, ep2
  4.6, ep13 4.1, ep12 2.4 cm3 median).
- 2026-11-01T04:53:30Z dev transform runs (GT-free, not scored) on 0 2 11 12 13 24 31 41: q90 success overshoots on
  jittery segments -> median frame (Q_OK 0.5); lid-on-pot needs inheritance; GN stalls on thin shells -> lift stage 1b.
- 2026-11-01T04:53:30Z PREREG.md written (variants A gated; B, C, D report only). Committing before any scoring.
- 2026-11-01T04:53:49Z PREREG pushed df60ff2 (04:53:42 UTC). Launching transform A B C D (code df60ff2).
- 2026-11-01T05:05:29Z transform running (4 variants in parallel, load ~8); A at 4/20 eps after 11 min. pf_report.py written (formats only).
- 2026-11-01T05:14:39Z transform done (C 05:08, D 05:10, A 05:13:58, B 05:14:03; code df60ff2). sha256 of all outputs -> out_sha256/; committing before stage0/scoring.
