# Refine-stage inputs and baseline (public episodes), 2026-10-29

Labels: [M] measured in this session, [E] estimate.

- **Machine:** CPU VM (cloud session, 4 cores). Cost $0.
- **Code:** repo `/home/user/v2d-track3`, branch `claude/focused-pascal-2nz9s1`, commit `1972dcb`, clean tree. `pipeline/score_registered.py` and `meshes/library_v3` were last changed at `46b8389`.
- **Kit:** `.../scratchpad/map/scoring/kit/kit.zip`, sha256 8d2bce64…
- **Root:** `R=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/refine`. Disk used is 162 MB.

## 1. Layout

| Path | Contents | May inference read it? |
|---|---|---|
| `$R/in/store/` | Raw mirror of the HF store `aebatirel/v2d-store` (store paths kept as they are). Holds pull set (a) without the GT-derived files, the ep11/ep21 swap-ins, and pull set (b). Manifests with sha256: `list_a_safe_manifest.json`, `list_alt_safe_manifest.json`, `list_b_manifest.json` | yes |
| `$R/in/ep<N>/` | One folder per episode for the 20 public episodes. Store files are linked in as relative symlinks; `depth0.npy` is a real file. See §2 | yes |
| `$R/in/alt/ep11`, `$R/in/alt/ep21` | The current-recipe swap-in tracks (twin11v3x / twin21arc). They are **not** the baseline (§4). `depth0.npy` links to `in/ep<N>/` | yes |
| `$R/in/depth0_manifest.jsonl` | Per episode: store path, store size, full shape, frame-0 valid fraction, frame-0 depth percentiles, sha256 of the frame | yes |
| `$R/quarantine_gt/store/` | `log.txt` and `result.json` from the same perception dirs. **They hold mocap scores** (see §5.1) | **NO** |
| `$R/baseline/` | Scores against mocap: `ep<N>.json`, `summary.json`, `raw/*_{lib,scan}.json`, `raw/*_pf.npz` (per-frame errors), `logs/`, `jobs.txt` | **NO** (scorer output) |
| `$R/scripts/` | `pull_lists.py`, `pull.py`, `depth0.py`, `assemble.py`, `combine.py` | – |

Never pulled at all: `score_registered.*`, `per_frame.npz`, `summary.json`, and any dataset parquet.

## 2. What is in each episode folder `$R/in/ep<N>/`

**Perception** (from perc2 at the store run shown in the table below):
- `poses.npz`
  - `world_T_cam` (T,4,4) float64. The world frame is the rectified-left camera at frame 0, OpenCV axes.
  - `cam_T_<obj>` (T,4,4) float32: object template frame → rectified camera t.
  - The templates are `meshes/library_v2`, which is byte-identical to `library_v3` except `mini_sweeper.glb`. The v2 and v3 sweeper share the same frame: same vertex and face counts, bounding boxes within 2.2 mm [M]. The difference only matters for eps 18 and 31.
- `poses_world_vo.npz`: `<obj>` = `world_T_cam @ cam_T_<obj>`. Checked [M]: the maximum difference is ≤ 2.2e-16 on every episode.
- `vo.json`: keyframes, per-frame inliers, fails.
- `det_f0.npz` (plus `det_f155/168/200/245.npz` on ep23, from guard re-detections) and `masks_f0.jpg`: frame-0 detection dump.
- `track_guard.json`: guard-arm episodes only (0, 11, 12, 18, 21, 23, 24, 31). Per-object guard counters.
- `perc_log_inference.txt`: perc2's timestamped log lines, cut **before** the first mocap-scoring line (`AUC`, `anchor:` or `DONE`). FoundationPose chatter is dropped. It keeps the `det …`, `reproposal …`, `track guard …` and `tracked … guard {…}` lines. Checked [M]: no AUC or score lines remain.

**Hands**:
- `hands.npz` and `hands_refined.npz` (key list in `inputs.json`). They include:
  - `joints_left/right` (T,21,3), world frame, same as above;
  - `valid_*`, `measured_*`, `uv_a_*`, `rms_px_*`;
  - `KR` (rectified K);
  - `world_frame` = "rectified-left camera at frame 0 (OpenCV axes)".
- Hands depend only on `world_T_cam`. That camera track matches across the hands runs and these tracks to ≤ 5.2e-8 (map_data §1).

**Depth**: `depth0.npy` is frame 0 of `cache/depth/public/ep<N>/depths_fs0.5.npy`.
- Format: (1000,1600) float32, metres, 0 = invalid. The same rectified-left frame as perc2 and mkref (`mkref.py:908` reads frame 0 only).

**`inputs.json`**: provenance (store paths for perception, hands and depth), the file map, and the checks below.

**Checks** [M]: on every episode, `T(poses)` equals the depth cache N and the hands T.

| ep | objects (slot order) | T | perception (store dir) | hands (store dir) | extra files |
|---|---|---|---|---|---|
| 0 | white_pot, white_pot_lid | 373 | `runs/20261025-guard-fe3f407/results/sweep/guard/ep0/` | `runs/20261025-g1-022fece/refs/perc2m/ep0/` | track_guard.json |
| 2 | white_pot, white_pot_lid | 343 | `runs/20261025-sweep-a894083/results/sweep/base/ep2/` | `runs/20261025-g1-022fece/refs/perc2m/ep2/` | - |
| 11 | blue_cup, beige_cup | 137 | `runs/20261025-guard-fe3f407/results/sweep/guard/ep11/` | `runs/20261025-g1-022fece/refs/perc2m/ep11/` | track_guard.json |
| 12 | blue_cup, plastic_dish_rack | 181 | `runs/20261025-guard-fe3f407/results/sweep/guard/ep12/` | `runs/20261021-auto18-966eb96/refs/perc2m/ep12/` | track_guard.json |
| 13 | blue_cup, plastic_dish_rack | 190 | `runs/20261025-sweep-a894083/results/sweep/base/ep13/` | `runs/20261025-g1-022fece/refs/perc2m/ep13/` | - |
| 18 | mini_sweeper, mini_dust_pan | 353 | `runs/20261025-guard-fe3f407/results/sweep/guard/ep18/` | `runs/20261021-auto18-966eb96/refs/perc2m/ep18/` | track_guard.json |
| 21 | blue_cup, water_pitcher | 186 | `runs/20261025-guard-fe3f407/results/sweep/guard/ep21/` | `runs/20261025-g1-022fece/refs/perc2m/ep21/` | track_guard.json |
| 22 | blue_cup, water_pitcher | 189 | `runs/20261025-sweep-a894083/results/sweep/base/ep22/` | `runs/20261025-g1-022fece/refs/perc2m/ep22/` | - |
| 23 | wooden_piece_1, wooden_piece_2 | 325 | `runs/20261025-guard-fe3f407/results/sweep/guard/ep23/` | `runs/20261025-g1-022fece/refs/perc2m/ep23/` | det_f155/168/200/245.npz, track_guard.json |
| 24 | wooden_piece_1, wooden_piece_2 | 275 | `runs/20261025-guard-fe3f407/results/sweep/guard/ep24/` | `runs/20261021-auto24-966eb96/refs/perc2m/ep24/` | track_guard.json |
| 26 | plastic_dish_rack, white_pot | 158 | `runs/20261025-sweep-a894083/results/sweep/base/ep26/` | `runs/20261025-g1-022fece/refs/perc2m/ep26/` | - |
| 27 | plastic_dish_rack, white_pot | 246 | `runs/20261025-sweep-a894083/results/sweep/base/ep27/` | `runs/20261021-auto18-966eb96/refs/perc2m/ep27/` | - |
| 31 | mini_sweeper, plastic_dish_rack | 290 | `runs/20261025-guard-fe3f407/results/sweep/guard/ep31/` | `runs/20261025-g1-022fece/refs/perc2m/ep31/` | track_guard.json |
| 39 | mini_dust_pan | 319 | `runs/20261025-sweep-a894083/results/sweep/base/ep39/` | `runs/20261025-g1-022fece/refs/perc2m/ep39/` | - |
| 40 | mini_dust_pan | 260 | `runs/20261025-sweep-a894083/results/sweep/base/ep40/` | `runs/20261025-g1-022fece/refs/perc2m/ep40/` | - |
| 41 | white_pot | 299 | `runs/20261025-sweep-a894083/results/sweep/base/ep41/` | `runs/20261025-g1-022fece/refs/perc2m/ep41/` | - |
| 42 | white_pot | 257 | `runs/20261025-sweep-a894083/results/sweep/base/ep42/` | `runs/20261025-g1-022fece/refs/perc2m/ep42/` | - |
| 43 | white_pot | 326 | `runs/20261025-sweep-a894083/results/sweep/base/ep43/` | `runs/20261025-g1-022fece/refs/perc2m/ep43/` | - |
| 44 | white_pot | 249 | `runs/20261025-sweep-a894083/results/sweep/base/ep44/` | `runs/20261025-g1-022fece/refs/perc2m/ep44/` | - |
| 45 | white_pot | 290 | `runs/20261025-sweep-a894083/results/sweep/base/ep45/` | `runs/20261025-g1-022fece/refs/perc2m/ep45/` | - |
| alt/11 | blue_cup, beige_cup | 137 | `runs/20261025-twin11v3x-0e8aebb/perc2/ep11/` (template library_v3x, v5 beige cup) | g1 ep11 | track_guard.json |
| alt/21 | blue_cup, water_pitcher | 186 | `runs/20261025-twin21arc-ee7ba8e/perc2/ep21/` (library_v3, SF_ARC=1) | g1 ep21 | track_guard.json |

**Other inputs** (not copied; they already exist locally):
- **Our meshes:** `/home/user/v2d-track3/meshes/library_v3/<obj>.glb`. Use `library_v3x` for alt/ep11.
- **Public asset hulls:** `.../scratchpad/hfds/track_3/public/mesh/<obj>/<obj>_collision.glb`. Only `mini_sweeper`, `wooden_piece_1` and `wooden_piece_2` have one. For the rest, `mkref.contact_mesh_path` falls back to the visual mesh. The visual meshes in that folder are the **public scans**, which the scorer also uses as the stand-in for the hidden geometry. Prefer our own meshes and hulls in refine.
- **URDFs:** `.../hfds/track_3/public/urdf/<obj>_rigid.urdf`.
- **Calibration:** `.../hfds/track_3/public/meta/camera_calibration.json` (OAK factory calibration; `mkref.rectified_K`). The rectified K is also stored as `KR` in `hands_refined.npz`.
- **Object names and slot order:** the `cam_T_` key order in `poses.npz`, which matches the episode roster. Do not open the parquet for this in refine.

## 3. Exact commands used

```
R=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/refine
W=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/map/scoring
REPO=/home/user/v2d-track3
# (1) explicit path lists from the store listing (the glob `hf download --include ... --dry-run` walks 135k files and
#     timed out at 120 s); excludes score_registered.*, per_frame.npz, summary.json; routes log.txt/result.json to quarantine
python3 -I $R/scripts/pull_lists.py $R/../store_files.txt $R/scripts      # -> list_{a,alt}_{safe,gt}.txt, list_b.txt
# (2) pulls (hf_hub_download per path; auth comes via the session proxy, `hf auth whoami` says not logged in)
for L in a_safe alt_safe b; do python3 -I $R/scripts/pull.py $R/scripts/list_$L.txt $R/in/store; done
for L in a_gt alt_gt;      do python3 -I $R/scripts/pull.py $R/scripts/list_$L.txt $R/quarantine_gt/store; done
#   a_safe 112 files 19.21 MB; alt_safe 12 / 1.69 MB; b 40 / 7.55 MB; quarantine 44 / 8.69 MB   [M]
# (3) frame-0 depth by HTTP range read (header + 6.4 MB), no full download
for e in 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45; do
  mkdir -p $R/in/ep$e; python3 -I $R/scripts/depth0.py $e $R/in/ep$e/depth0.npy >> $R/in/depth0_manifest.jsonl; done
#   ~4.5 s per episode. Verified on ep11: byte-identical to frame 0 of the fully downloaded 0.88 GB cache
#   (full file deleted afterwards).   [M]
# (4) per-episode folders + sanitized logs + checks
$W/venv/bin/python -I $R/scripts/assemble.py $R
# (5) baseline scoring (44 jobs, 4 in parallel, 2 min 33 s wall): see $R/baseline/jobs.txt for every command line; pattern:
$W/venv/bin/python -I $REPO/pipeline/score_registered.py $e $R/in/ep$e/poses_world_vo.npz --t3 $W/t3 \
  --kit $W/kit/v2d_submission_kit --meshes $REPO/meshes/library_v3 --out $R/baseline/raw/ep${e}_lib.json \
  --per_frame $R/baseline/raw/ep${e}_lib_pf.npz          # and the same without --meshes -> ep${e}_scan.json
python3 -I $R/scripts/combine.py $R                     # -> baseline/ep<N>.json, baseline/summary.json
```

To score a refine arm the same way, replace `$R/in/ep$e/poses_world_vo.npz` with the arm's output. `$W/t3/ep<N>.parquet` (the mocap) is read only by `score_registered.py`.

## 4. Baseline [M]: current perception, registered ADD-AUC vs public mocap

| ep | arm | lib (library_v3) | scan | lib − scan | per-object lib | per-object scan |
|---|---|---|---|---|---|---|
| 0 | guard | 0.9641 | 0.9945 | -0.030 | pot 0.992, lid 0.936 | 0.994, 0.996 |
| 2 | base | 0.9823 | 0.9786 | +0.004 | pot 0.992, lid 0.972 | 0.992, 0.965 |
| 11 | guard | 0.8978 | 0.9259 | -0.028 | blue 0.862, beige 0.933 | 0.860, 0.992 |
| 12 | guard | 0.9662 | 0.9634 | +0.003 | blue 0.933, rack 1.000 | 0.988, 0.939 |
| 13 | base | 0.9605 | 0.9013 | +0.059 | blue 0.933, rack 0.988 | 0.865, 0.938 |
| 18 | guard | 0.9642 | 0.9707 | -0.007 | sweeper 0.995, pan 0.933 | 0.996, 0.946 |
| 21 | guard | 0.8325 | 0.9543 | -0.122 | blue 0.982, pitcher 0.683 | 0.995, 0.913 |
| 22 | base | 0.8710 | 0.9821 | -0.111 | blue 0.992, pitcher 0.750 | 1.000, 0.965 |
| 23 | guard | 0.0414 | 0.0418 | -0.000 | board1 0.083, board2 0.000 | 0.084, 0.000 |
| 24 | guard | 0.8117 | 0.7902 | +0.021 | board1 0.776, board2 0.847 | 0.757, 0.823 |
| 26 | base | 0.9652 | 0.9484 | +0.017 | rack 0.994, pot 0.937 | 0.993, 0.903 |
| 27 | base | 0.9611 | 0.9416 | +0.019 | rack 1.000, pot 0.922 | 1.000, 0.883 |
| 31 | guard | 0.7999 | 0.8907 | -0.091 | sweeper 0.912, rack 0.688 | 0.950, 0.832 |
| 39 | base | 0.9602 | 0.9765 | -0.016 | pan 0.960 | 0.977 |
| 40 | base | 0.9570 | 0.9796 | -0.023 | pan 0.957 | 0.980 |
| 41 | base | 0.9910 | 0.9885 | +0.002 | pot 0.991 | 0.989 |
| 42 | base | 0.9915 | 0.9861 | +0.005 | pot 0.992 | 0.986 |
| 43 | base | 0.9482 | 0.9808 | -0.033 | pot 0.948 | 0.981 |
| 44 | base | 0.9967 | 0.9982 | -0.001 | pot 0.997 | 0.998 |
| 45 | base | 0.9795 | 0.9741 | +0.005 | pot 0.980 | 0.974 |
| **mean (20)** | | **0.8921** | **0.9084** | | | |
| **mean without ep23 (19)** | | **0.9369** | **0.9540** | | | |

**Reproduction.** I compared the scene AUC, the per-object AUC and the registration parameters with `refcheck/chain/results.json` (keys `guard` / `sweep`): 106 numbers, maximum |difference| 0.0 [M]. The ≤ 0.0005 differences against `tables.md`, and scan 0.9084 vs 0.9085, come only from that table's 3-decimal rounding.

**Swap-in tracks** (not in the baseline):

| track | lib | scan | vs the baseline track |
|---|---|---|---|
| ep11 twin11v3x (scored with library_v3x) | 0.8964 | 0.9161 | -0.0014 |
| ep21 twin21arc | 0.8372 | 0.9575 | +0.0047 |

Using both would move the 20-episode mean by +0.0002 [M].

## 5. Problems and cautions

1. **The data map's pull set (a) brings in GT-derived files.** On the public split, perc2 scores against mocap at the end (`pipeline/perc2.py:502-542`).
   - `result.json` holds AUC and SP/MP values per variant and `gt_motion_extent_cm`.
   - The last lines of `log.txt` are `vo AUC …` and `anchor:… AUC …`.
   - The map excluded only `score_registered.*` and `per_frame.npz`. I moved both files to `quarantine_gt/` and give refine `perc_log_inference.txt`, cut before those lines.
   - Refine must not open `quarantine_gt/` or `baseline/`.
2. **ep23** is a frame-0 identity swap (0.041). It drags the mean down by 0.045. Always report the mean without ep23 as well.
3. **The lib score depends on the frame-0 registration draw.** One seed per mesh moves an episode by about ±0.01–0.03, and any frame-0 change moves it by ±0.02–0.07 (map_harness §1). A/B tests should keep frame 0 fixed, or report its effect separately.
4. **Eps 18 and 31** were tracked with the library_v2 sweeper and scored with library_v3. The two meshes share a frame (checked above), so this is consistent, but it is not the eval configuration.
5. Hands for 12, 18 and 27 come from auto18 (21 Oct) and for 24 from auto24. They are valid because hands depend only on `world_T_cam`, which matches to ≤ 5.2e-8 (map_data §1).
