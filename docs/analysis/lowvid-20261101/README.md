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
- **Robot-hand GPU videos** (run 20261101-vid3-b96ae95, $0.70): eval 14 replays r1 0.560 / r2 0.285 / r3 0.749 (all
  in the failing hand-over mode); eval 25 0.897; eval 30 0.901. In the eval-14 3-D view, one robot hand carries the cup
  through the hand-over while the other stays parked: the single-hand lock (claude/grasp-ep13-20261101).

## Sim-vs-reference offsets in the packed rollouts (GT-free) [M], 1 Nov ~19:20 UTC
- Columns:
  - mean |d| = mean distance between the simulated object and our reference;
  - const % = share of the squared error that one constant shift would remove;
  - dz = mean vertical offset (sim minus reference);
  - rot = mean orientation error (cups spin freely in scoring).

| Eval | Object | mean \|d\| cm | const % | dz cm | rot ° |
|---|---|---|---|---|---|
| 14 | blue_cup | 2.00 | 13 | +0.43 | 15.1 |
| 14 | rack | 0.64 | 40 | −0.43 | 2.3 |
| 16 | rack | 0.86 | 48 | −0.23 | 3.4 |
| 16 | wooden_spoon | 1.32 | 28 | −0.39 | 21.5 |
| 20 | blue_cup | 0.90 | 17 | −0.18 | 6.0 |
| 20 | water_pitcher | 1.16 | 5 | +0.08 | 5.1 |
| 25 | wooden_piece_1 | 1.48 | 15 | −0.53 | 8.4 |
| 25 | wooden_piece_2 | 1.53 | 13 | −0.59 | 7.9 |
| 30 | mini_sweeper | 1.82 | 24 | +0.94 | 11.1 |
| 30 | rack | 0.87 | 45 | −0.57 | 1.1 |
| 32 | blue_cup | 2.71 | 11 | −0.26 | 16.4 |
| 32 | wooden_spoon | 1.09 | 1 | +0.04 | 6.6 |

- **Reading:**
  - For moving objects only 1–28 % of the sim-vs-reference error is a constant shift, so it is tracking error that
    varies with motion and contact.
  - The static racks are the exception (40–48 % constant): they sit 0.2–0.6 cm lower in the simulation than in our
    reference.
  - The score is computed against mocap, not against our reference. On the 20 public episodes, by ground-truth
    substitution (diagnostic, 31 Oct), a constant per-object offset in our reference is worth AUC +0.050 and the frame-0
    scene tilt +0.040 (overlapping).
