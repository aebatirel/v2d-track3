# Videos of the lowest-scoring eval episodes (1 Nov 2026): reporting only, no ground truth

Videos are not in git (CLAUDE.md). They were sent to the owner and sit in the session scratchpad (lowvid/out, lowvid/out2).

- **Ranking.** H5p7 fresh-draw means (pack-7 policies = pack 11 except eval 10):
  14 0.727, 16 0.850, 32 0.852, 25 0.878, 20 0.893, 30 0.897.
- **Evals 16 / 20 / 32:** robot-hand videos from 30 Oct (store runs/20261030-vid5-817b135/results/sub_videos/).
- **Evals 14 / 25 / 30, CPU renders of the official rollout parquets.** The parquets have no robot state, so these show
  objects only.
  - Inputs: pack 6's packed rollouts and the H5p7 worst draw r7; the camera is ego_cam_a from
    nvidia/video_to_data_challenge.
  - First version: the library_v3 visual meshes (determined-wright's tools/render_eval_rollout.py).
  - Second version (`render_collision.py`): the simulator's actual collision geometry, each convex piece shaded
    separately.
    - eval 25: the packed carved pieces, meshes/carve/ev25 (21 / 11 pieces);
    - evals 14 / 30: FlashCHORD's default CoACD decomposition, re-created with `coacd_fc.py` (coacd 1.0.11, threshold
      0.05, max_convex_hull −1, preprocess auto, as fc_mesh.py). Eval 14 uses its own refs/sf/ep14 assets from run
      20261025-evb1420-ee7ba8e; eval 30 uses library_v3. Hull counts: sweeper 19 and rack 43, equal to
      bold-albattani's packed_coacd_report; ep14 blue cup 75.
- **`eval25_boards_visual_vs_collision.jpg` (`slot_still.py`):** each board's submitted visual mesh (no slot) next to
  its carved collision pieces, where the slot shows as a notch.
- **[M] Eval 14:**
  - The cup's failure onset (> 3 cm for 8 frames) falls at f42–45 in 7 / 10 H5p7 draws: the hand-over.
  - The cup sags 9–12 cm below the reference in good and bad draws alike; bad draws never recover.
  - In 3 draws the cup is thrown 63–162 cm, and in 2 the rack is thrown too.
- **Robot-hand GPU videos for 14 (×3 replays) / 25 / 30** are pending: run 20261101-vid3-b96ae95 (focused-pascal).
