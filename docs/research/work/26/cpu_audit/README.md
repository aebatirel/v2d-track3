# CPU audit (note 26 §C3), 2026-10-27

Machine: Claude cloud VM (4 vCPU, CPU only). Public episodes only. Ground truth is used for diagnostics (carry
segments, frame-0 support) and never by the reference audit tool.

| file | what | command |
|---|---|---|
| `hand_detect.py` → `hand_detect_log.txt` | MediaPipe 0.10.14 on colour cam_a, `hands_mp.py` detector settings; per-frame counts, labels, 2-D landmarks (npz kept in the session scratchpad, ~10 s/episode) | `<mediapipe venv>/bin/python -I hand_detect.py <episode_*.mp4> <out.npz>` |
| `gt_objects.py` → `gt_objects.txt`, `gt_objects.json` | Frame-0 support (table / stacked / unsupported), carry segments, simultaneous carries (GT) | `python3 gt_objects.py <public data dir> <public mesh dir> gt_objects.json` |
| `carry_coverage.py` → `carry_coverage.txt` | Hand detection during carry segments, longest gaps, handedness label changes, bimanual two-hand coverage | `python3 carry_coverage.py gt_objects.json <det dir>` |
| `ep21_pour_hand_out_of_view.jpg` | Visual check: ep 21 frames 45/53/61/69, pitcher hand outside the colour view | — |
| `nvidia_tissue_box_audit.json` | `pipeline/audit_ref.py` on NVIDIA's `tissue_box_simple` egocentric reference (test + healthy baseline) | `python3 pipeline/audit_ref.py <parquet> --mesh tissue_box_simple=<obj> --table_z 1.0` |

The MediaPipe venv: `uv venv --python 3.11 mpvenv; uv pip install mediapipe==0.10.14 opencv-python-headless numpy`.
The colour videos come from `nvidia/video_to_data_challenge` (`track_3/public/videos/chunk-000/observation.images.ego_cam_a/`).
