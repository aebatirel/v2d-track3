# Work for note 26 (carry-aware control, force feedback, Kalman filtering), 2026-10-26

All runs: Claude cloud VM (CPU), on the 20 public Track 3 parquets (ground truth, diagnostics only), downloaded with
`huggingface_hub.snapshot_download("nvidia/video_to_data_challenge", repo_type="dataset",
allow_patterns=["track_3/public/data/*", ...])`.

| file | what | command |
|---|---|---|
| `carry_model.py` → `carry_model.txt`, `carry_model.csv` | Wrist-residual demand per variant (gains, reference advance, gravity offset), rotation, grip/load factor | `python3 carry_model.py <public data dir> > carry_model.txt` |
| `pid_model.py` → `pid_model.txt`, `pid_model.csv` | Controller-only carry sim (no policy): PD vs PID (FlashCHORD JointPositionIntegral) vs feed-forward, release jump, Routh stability bound | `python3 pid_model.py <public data dir> > pid_model.txt` |
| `verify/sens.py`, `verify/sens2.py` → `verify/sens_sweep.txt`, `verify/sens2.txt` | Sensitivity reruns: SG window, thresholds, hand mass, usable clip, pivot offsets, wrist-to-reference gap | `python3 verify/sens.py carry_model.py <data dir>` (sens2 likewise) |
| `verify/torque.py` | Ball-wrist torque clamp (`action.wrist_tau_max`) effect | see script header |
| `verify/rotdamp.py` → `verify/rotdamp.txt` | Ball-wrist damping sweep (critic) | `python3 verify/rotdamp.py <data dir>` |
| `verify/coupling.py`, `verify/noise.py`, `verify/test_angvel.py`, `verify/urdf_inertia.py` | Hand-COM coupling, noise check, angular-velocity unit test, URDF inertia | see script headers |
| `verify/verdicts.json`, `verify/critic-report.md` | Structured verdicts of the six checkers and the critic's report | — |
| `toy/smooth_sim2.py` | Synthetic 1-D causal vs offline smoother comparison (not our data) | `python3 toy/smooth_sim2.py` |

The FlashCHORD source was read at nvidia-isaac/video_to_data 8c778f905cb3 (and 7eb9721, identical flash_chord tree).
It was cloned to the session scratchpad and is not committed.
