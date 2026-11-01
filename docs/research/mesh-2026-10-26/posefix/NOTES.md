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
