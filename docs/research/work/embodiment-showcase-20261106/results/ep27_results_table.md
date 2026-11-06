# ep27 (pot flipped into the dish rack): one policy per robot, trained in physics from one head-camera video

Measured [M]: 5 official-evaluator runs per policy (help off, VOC 0), scored against motion capture with the kit metric (pipeline/score_sim.py). Reference vs mocap (what every robot was asked to track): AUC 0.997. Static floor (nothing moves): 0.560.

| Robot | Fingers / joints per hand | AUC vs mocap (5 runs) | Pot AUC range | Runs within 3 cm (MP-SR) | In video |
|---|---|---|---|---|---|
| Unitree Dex3-1 | 3 / 7 | 0.982 ± 0.005 | 0.95–0.98 | 5/5 | yes |
| Shadow Hand | 5 / 22 | 0.977 ± 0.003 | 0.95–0.96 | 5/5 | yes |
| Allegro Hand | 4 / 16 | 0.975 ± 0.002 | 0.95–0.95 | 5/5 | yes |
| Inspire RH56 | 5 / 12 | 0.973 ± 0.006 | 0.93–0.96 | 5/5 | yes |
| LEAP Hand | 4 / 16 | 0.970 ± 0.005 | 0.92–0.95 | 5/5 | yes |
| Barrett BH8 | 3 / 8 | 0.969 ± 0.006 | 0.92–0.96 | 5/5 | yes |
| Sharpa Wave | 5 / 22 | 0.966 ± 0.006 | 0.91–0.95 | 5/5 | yes |
| D'Claw | 3 / 9 | 0.958 ± 0.008 | 0.90–0.94 | 5/5 | yes |
| Franka gripper + rubber pads | 2 / 2 | 0.947 ± 0.011 | 0.85–0.92 | 5/5 | yes |
| Franka gripper | 2 / 2 | 0.648 ± 0.066 | 0.16–0.46 | 0/5 | no (failed run, kept for the record) |

Renders use clean closed meshes (meshes/library_c0, ICP-aligned onto the scans); physics used the official scans (convex pieces). Franka + rubber pads = condim-4 pad contacts (torsional friction 0.015 m) and the Franka grip spec.

Franka fix robustness [M]: three independent trainings with pad contacts all pass. panda_pads seed 42: 0.947 ± 0.011
(the one in the video); seed 43: 0.959 ± 0.007; wider pads (torsional 0.03), seed 44: 0.940 ± 0.007. All 5/5 within
3 cm.

Spend for phases 0–1 including the fixes: Vast credit $67.25 → $38.37 (≈ $28.90 for 5 boxes, about 23 GPU-hours).
