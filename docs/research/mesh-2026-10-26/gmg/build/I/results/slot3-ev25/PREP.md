# Eval 25 prep for board slot round 3 (Prep25): board identity, gmg eval bundle, candidates

31 Oct 2026, 21:17-21:56 UTC. Board-slot round-3 workflow, Prep25 step. This step needs no F-I4 rule and makes no
decision. The F-I4 decision was not run, physics was not run, and `meshes/carve/ev25` was not read. CPU only, on this
container. No rental, $0. Labels: [M] measured, [E] estimate, [H] hypothesis.

## Result in short
- **Board identity [M].** Our local eval-25 track is the frozen evperc track (sha256 `e95ccaef...`). Its boards are
  swapped relative to the packed reference:
  - our `wooden_piece_1` is the reference's `wooden_piece_2` (same object frame);
  - our `wooden_piece_2` is the reference's `wooden_piece_1`, rotated **Rx 180 deg**.

  This is the swap the 25 Oct identity rule found. The bundle uses the mapped track.
- **Bundle (use this one):** `<scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f/bundle/eval/ep25`.
  - It is a DEV-tier copy of the clean bundle `<scratch>/gmg/runs/20261031-ev25ext-5bf54bc/bundle/eval/ep25`. The data
    files are byte-identical.
  - The copy exists because a dev consumer can open a tracks file only from its own run (see "Why two bundle folders").
  - Consumers must run with `--run <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f`.
- **Candidates:** `<scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f/cand/eval/ep25/<board>/{shell_t5p36,hull}.glb`. All
  four are watertight after packing.
- **--pick:** `wooden_piece_1=shell_t5p36,wooden_piece_2=shell_t5p36`
- **Hands:** `<scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f/in/hands25/hands.npz`. This is a byte copy of the clean
  run's M1 output, placed the way round 2 placed `in/hands24`.
- **Open risk for the eval-25 run [M + H]:** our mapped track and the pose the simulator replays (the packed parquet)
  disagree at assembly by 9.8 mm and 2.5 deg in board 2's pose relative to board 1. `interlock_dev` builds the slot
  from the bundle track (P_sim = P_sel, flag `sim_pose_fallback`). The slot could therefore sit several mm off where the
  simulator puts the partner. That is more than the 1 mm clearance [H]. Hand-off item 2 has the details.

## Inputs (md5; sha256 where the guard records it)
| Input | Path | md5 | sha256 |
|---|---|---|---|
| Our eval-25 track: frozen evperc (`20261025-evperc-4f596df`); the guard checks it against `gmg/frozen_eval_tracks.json` | `<scratch>/data/eval/ep25/poses.npz` | e15f61bcd127c395faa848553b59bcd0 | e95ccaefa66ccdfb091a4048cf5b7e6f71119c4c7eb22c66b48c1465c81de0c3 |
| Packed reference perception track (store run `20261026-c25s42-feb0407`) | `runs/20261026-c25s42-feb0407/perc2/ep25/poses.npz` | a0a0024f30387b66f6af4b2e9defa563 | 3e0813b8eacb86578cfb98f8c28fa6aa0176ce108f02b4e57133066e796cccaf (= store LFS oid) |
| Its identity check (`as tracked`, rank 1 of 32, applied false) | `.../perc2/ep25/identity_fix.json` (copy: `ref_identity_fix.json`) | cc108e888a7b85d79d399bbf5178d3ff | |
| Packed reference parquet (md5 = `packed_refs.json`, focused-pascal file commit 71bac00) | `runs/20261026-c25s42-feb0407/refs/perc2mcks/ep25/processed/sequence_id=t3_ep025/robot_name=sharpa_wave/2057d9f10b3a421ebbfd847c1219d1a0-0.parquet` | 71ac95f3764170f29f02fa657e7c057c | 201867f73a82de571c6bdecdd77647ba0acec263ae4a7e68224e76d59e3752fd |
| Reference table frame | `.../refs/perc2mcks/ep25/table_frame.npz` | e3e99826ed72dd98e6c268d176e10d8b | |
| Eval depth (store `cache/depth/eval/ep25/`, 2,278,400,128 bytes, deleted after the extraction) | `<scratch>/cache/depth/eval/ep25/depths_fs0.5.npy` | 33e5ce46722060a223abf4fcb2b88755 | f63ac37781539a910298e64f9c6cd35675c487b60f9b92ce6f23a6ac09798dfc (= store LFS oid) |
| Video, cam_a (356 frames, 20 fps, 2028x1520) | `<scratch>/data/eval/ep25_a.mp4` | e8254817da95bc54c4705c594387e89b | e5945e6258963e1a96864ddda9ec43548f0bd3233208cf7780facd384c6cb249 |
| Calibration | `<scratch>/data/calib.json` | 56c32942b0f046272a23fb178d4ec58d | 23e2d9c46369292cdda492a777e7a6083815369a25d1af4bb82560669fde5d52 |
| Kit roster (eval 25 = `wooden_piece_1`, `wooden_piece_2`, reference slot order) | `<scratch>/kit/v2d_submission_kit/data/track_3_evaluation_objects.json` | 8988cf9026b77b5ebad426e2c7803efd | be92ef6db25aa60cefcdfb44f0acfdc6fbdfa26bb249f6890e1963c659b79272 |

All of these are our own perception outputs, our own depth cache and kit-provided names. Nothing reads ground truth: no
scan, mocap, dataset parquet pose, `*_align` file or library mesh.
- The reference parquet is our mkref output. It was read only by the comparison scripts outside the gmg guard, never
  by a gmg process.
- The two strace audits report forbidden 0, unlisted 0, writes outside the run 0 and network 0
  (`provenance/strace_*.audit.json`).

## 1. Board identity mapping [M]
Script: `scripts/map_tracks.py`, output `mapping.json`. It uses all 356 frames. `world_T_cam` is identical in both tracks
(max |diff| 0.0). For each pairing it reports:
- centre distance per frame;
- the constant body offset X, the per-frame mean rotation of A⁻¹B, and its nearest 180-deg symmetry;
- the spread of X over frames;
- the residual after applying X.

| Our board -> reference board | Centre distance median / p90 / max (mm) | Offset, nearest symmetry (deg off) | Offset spread median / p90 (deg) | Residual after offset, t median / p90 (mm), R median (deg) |
|---|---|---|---|---|
| wp1 -> wp1 | 181.5 / 263.4 / 362.1 | (Rz180, 55.9 off: none) | 46.9 / 64.8 | 116.6 / 171.6, 46.9 |
| **wp1 -> wp2** | **4.9 / 6.8 / 16.0** | **I (1.25)** | **1.75 / 2.75** | 3.7 / 6.9, 1.7 |
| **wp2 -> wp1** | **7.3 / 9.9 / 14.7** | **Rx180 (0.96)** | **1.24 / 2.69** | 2.8 / 7.1, 1.2 |
| wp2 -> wp2 | 180.2 / 260.6 / 359.7 | (Ry180, 54.4 off: none) | 48.1 / 66.8 | 200.8 / 249.8, 48.1 |

- Summed median centre distance: identity pairing 361.7 mm, swapped pairing 12.2 mm. The swap is unambiguous.
- The same swap appears in the round-2 log entry of 17:54. There, the 25 Oct identity rule scored the evperc track +50.0
  (rank 21 of 32, `wooden_piece_1 <- old wooden_piece_2 @ Rx 180`).
- The reference's own `identity_fix.json` keeps it as tracked (rank 1, applied false).
- **Map:** `wooden_piece_1=wooden_piece_2:Rx180,wooden_piece_2=wooden_piece_1:I`. The new `cam_T_TARGET` is
  `cam_T_SOURCE @ diag(ROT, 1)`; `world_T_cam` is unchanged.
- Only the exact symmetry is applied. The fitted residual offsets are kept as track differences, not corrected:
  0.96-1.25 deg, plus a body-frame translation of (-0.7, -1.6, 3.6) mm and (0.7, -1.3, 6.3) mm.
- In the candidates' object frame, x is the thin axis (extent about 37-38 mm including noise), y the width (143-145 mm)
  and z the length (234-236 mm), as on ep24. So Rx180 turns the board end over end about its thickness axis. It does
  not swap the two faces.
- **The packed parquet replays the reference track [M]** (`mapping.json` `parquet_vs_tracks`):
  - `object_body_position` in the table frame equals `T_table_from_world · world_T_cam · cam_T_obj` of the reference
    track. The xy difference is 0.000 mm for both boards. Only z differs, by a time-varying mkref shift: board 1 -7.9 to
    +12.2 mm, board 2 +4.7 to +13.5 mm (the snap and depenetration in `mkref_log.txt`).
  - The rotation differs by 0.03 / 0.05 deg median.
  - So the reference's board names and object frames are the simulator's.

## 2. Bundle
Commands (cwd `docs/research/mesh-2026-10-26`, `V=<scratch>/venv/bin/python`):

```bash
# eval depth from the store (curl straight to the cache path, no hub cache), sha256 = LFS oid
curl -sSL --fail -o <scratch>/cache/depth/eval/ep25/depths_fs0.5.npy \
  https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main/cache/depth/eval/ep25/depths_fs0.5.npy
# (a) clean extraction under the strace audit, 21:27:43-21:47:27 (code 5bf54bc; HEAD at launch fc952de, no gmg code change)
GMG_MODE=clean nice -n 5 $V -W ignore gmg/tools/strace_audit.py run \
  --log <scratch>/gmg/audit/ev25-20261031-ev25ext-5bf54bc-ep25.strace \
  --manifest <scratch>/gmg/runs/20261031-ev25ext-5bf54bc/manifests/eval-ep25.json --allow "<scratch>/mpvenv/**" -- \
  $V -W ignore gmg/tools/ev_extract.py --run <scratch>/gmg/runs/20261031-ev25ext-5bf54bc --ep 25 \
  --map wooden_piece_1=wooden_piece_2:Rx180,wooden_piece_2=wooden_piece_1:I
rm <scratch>/cache/depth/eval/ep25/depths_fs0.5.npy
# (b) dev copy for the consumers, 21:50:20-21:50:25 (code 765dc6f), strace audit
GMG_MODE=dev $V -W ignore gmg/tools/strace_audit.py run \
  --log <scratch>/gmg/audit/ev25rehome-20261031-ev25prep-765dc6f.strace \
  --manifest <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f/manifests/eval-ep25-rehome.json -- \
  $V -W ignore gmg/tools/ev_extract.py --run <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f --ep 25 \
  --map wooden_piece_1=wooden_piece_2:Rx180,wooden_piece_2=wooden_piece_1:I \
  --rehome <scratch>/gmg/runs/20261031-ev25ext-5bf54bc/bundle/eval/ep25
# (c) hands for the driver (as round 2's in/hands24)
cp <scratch>/gmg/runs/20261031-ev25ext-5bf54bc/hands/eval/ep25/hands.npz \
   <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f/in/hands25/hands.npz
```

`gmg/tools/ev_extract.py` is new (commits 5bf54bc and 765dc6f). It runs the same steps as `b4_extract` with these
differences:
- split eval;
- the kit roster;
- the frozen eval track read through the guard, with the map applied in-process; the mapped track goes to
  `RUN/tracks/eval/ep25/poses.npz` (sha256 49adcb73...) plus `mapping.json`;
- no frame-0 det seeds (none exist for eval; ep24's public bundle had none either);
- no aux owner file (B.3 is public only).

Hands follow the public recipe: M1 `hands_cpu` and MediaPipe on the cam_a video, `world_T_cam` only.

**Why two bundle folders.**
- The guard opens a tracks file only from `data/sweep/`, from `data/eval/` (frozen sha256) or from the *current* run's
  `tracks/`. Any reader of the clean bundle from another run is therefore refused its mapped track. `interlock_cands`
  failed this way at 21:48 (dev run `20261031-ev25prep-5bf54bc`, marker only, kept).
- `--rehome` handles this in dev mode:
  - it regenerates the mapped track in the dev run from the same frozen source and map. Arrays and bytes are identical:
    sha256 49adcb73... in both runs;
  - it copies the object npz and shell files byte for byte, through role `clean_run` (`cmp` identical);
  - it rewrites only `episode.json`'s `tracks` entry, `tier` (DEV) and a `rehomed_from` record.
- Data files (both folders): `wooden_piece_1.npz` sha256 136918bd..., `wooden_piece_2.npz` 560df4f0...,
  `shell_*.npy`. `episode.json`: clean c4c8741c..., dev 702552e5....

**Counts [M]** (`bundle_summary.json`, `provenance/clean_extract_eval-ep25.log`):
- T 356, stride 2: 178 frames, 9,210,442 pass-0 samples.
- Cube voxels: 112,831 (wp1) / 137,302 (wp2).
- Table plane from frame-0 depth: inlier fraction 0.162 (under wp1).
- Hands: 353 / 356 frames with a hand, 292 with two; 280.6 s.
- Extraction 742.9 s; whole episode 1171.1 s.

| Board (reference names) | Good frames | sigma (mm) | Below table | Block residual median / p90 / max (mm) | Shell | Split test vs the other board |
|---|---|---|---|---|---|---|
| wooden_piece_1 (= our evperc wp2 @ Rx180) | 120 / 178 | 2.03 | 0.157 | 1.05 / 9.87 / 13.29 | 400k points, 283.7 cm², 120 frames | **false** (chamfer h1-h2 3.53 mm) |
| wooden_piece_2 (= our evperc wp1) | 174 / 178 | 0.98 | 0.0 | 1.01 / 1.11 / 5.73 | 400k points, 305.3 cm², 174 frames | true (1.84 mm) |

Board 1 is the noisier board, as on ep24, where board 1's split test was also false (2.43 mm). No sanity flags.

## 3. Candidates [M]
`interlock_cands` was used unchanged except for its output folder. The output folder now follows the bundle's split
(commit 5bf54bc; public runs unchanged). Same producers and `dev_constants.json` t0 as ep24 and ep23.

```bash
GMG_MODE=dev GMG_RUN=<scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f nice -n 5 $V -m gmg.tools.interlock_cands \
  --run <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f \
  --bundle <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f/bundle/eval/ep25 --ep 25      # 21:50:43-21:52:05, rc 0
```

| Candidate | Faces | Watertight (packed) | Volume (cm³) | Extent x / y / z (mm) | md5 |
|---|---|---|---|---|---|
| wooden_piece_1 / shell_t5p36 | 3912 | yes | 288.0 | 38.1 / 144.6 / 233.5 | 0ffd907b4867da5849b1ead43a628660 |
| wooden_piece_1 / hull | 3880 | yes (V1 veto) | 491.2 | 92.0 / 140.0 / 244.0 | a57bdf6db9af1f89dc1abad3a350a535 |
| wooden_piece_2 / shell_t5p36 | 3944 | yes | 166.1 | 36.7 / 142.5 / 235.7 | 1a8690d16a4a59880b97174f917b386f |
| wooden_piece_2 / hull | 3856 | yes | 320.6 | 48.0 / 96.0 / 248.0 | 7140f389e6ff7fd369703afe1fbec278 |

For comparison, the ep24 shells were 42.1 / 146.3 / 234.7 mm (196.8 cm³) and 38.5 / 142.9 / 235.8 mm (158.7 cm³).

## 4. The eval-25 step (not run here: it needs F-I4.16 and its freeze conditions)
This is the ep24 fi4o command with the eval inputs. The tag is the next step's choice.

```bash
GMG_MODE=dev GMG_RUN=<scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f python -m gmg.tools.interlock_dev \
  --run <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f --ep 25 \
  --bundle <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f/bundle/eval/ep25 \
  --cands <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f/cand/eval/ep25 \
  --pick wooden_piece_1=shell_t5p36,wooden_piece_2=shell_t5p36 \
  --video <scratch>/data/eval/ep25_a.mp4 --calib <scratch>/data/calib.json \
  --hands <scratch>/gmg/runs-dev/20261031-ev25prep-765dc6f/in/hands25/hands.npz \
  --proxy-copies 16 --identity eval --waiver-fi4 --no-physcheck --tag <tag>
```

## Hand-offs and caveats
1. **`interlock_dev` hard-codes `split = 'public'`.** For eval 25 its output folder would be `interlock/public/ep25-<tag>`,
   and `write_round` would label the r0 manifest `public`. This is a label error, not a geometry error. A one-line fix
   (`split = b.meta.get('split', 'public')`) is needed in a shared file before the eval run. Not done here.
2. **P_sel vs P_sim at assembly** (report only, f294-355, board 2 in board 1's frame; `rel_assembly.json`,
   `parquet_assembly.json`):

   | Comparison | Median distance (mm) | Median dx / dy / dz (mm) | Rotation median / max (deg) |
   |---|---|---|---|
   | Mapped track vs reference track | 7.9 | 2.1 / -1.3 / -7.3 | 2.5 |
   | Mapped track vs packed parquet | 9.8 (max 13.7) | 2.0 / -6.1 / -7.3 | 2.5 / 3.9 |
   | Reference track vs packed parquet | 5.7 | -0.1 / -5.7 / 0.0 | 0.03 |

   - Reading the axes: z is board 1's length and y its width.
   - The last row comes from the per-board z snaps. In f294-355 mkref lifts board 2 by +4.7 to +7.2 mm and board 1 by
     -1.6 to +6.6 mm (median -0.3).
   - `interlock_dev` uses P_sim = P_sel (the bundle track). By its own record the slot follows the tracked relative pose
     at assembly (slot2_1 N1: ep24 board 2 about 3.5 mm off).
   - [H] On eval 25 the slot may therefore sit about 6-10 mm away from the place where the simulator replays the
     partner. Falsifier: F-I4.16 item 3's P_sel -> P_sim check. Place the delivered pieces at the packed parquet's poses
     (the parquet, not the raw `perc2` track, because of the z snaps) at f294-355, and read the partner-in-body overlap
     (flag > 0.3 cm³).
   - A bundle built on the reference track would remove the in-plane part. It would need an owner or orchestrator
     decision, because SPEC section 17 freezes the eval tracks to evperc. The mkref z snap would remain.
3. **Tier.** The clean bundle is P1, strace-clean and the audited source. Consumers use the DEV copy, which has the same
   data bytes; the interlock outputs are DEV anyway, as on ep24. The shell copy of `hands.npz` into the dev run follows
   round 2's practice; in dev mode there is no provenance check.
4. **Disk.** The container had 2.9 GB free before the 2.28 GB depth file. The minimum during the run was about 0.6 GB,
   shared with other agents. The depth file was deleted at 21:47; the store copy remains.
5. **Not read:** `meshes/carve/ev25`, anything under `meshes/library*`, scans, mocap and dataset parquets.

## Files here
- `mapping.json`: per-pairing statistics, assignment and parquet check.
- `rel_assembly.json` and `parquet_assembly.json`: the assembled-window comparisons.
- `bundle_summary.json`: key fields of the dev bundle's `episode.json`.
- `cands25.json`
- `ref_identity_fix.json`
- `scripts/`:
  - `map_tracks.py`, sha256 3818939a...
  - `rel_assembly.py`, sha256 d9f19919...
  - `parquet_assembly.py`, sha256 b54c16af...
- `provenance/`:
  - clean manifest, rehome manifest and candidates manifest;
  - both strace audit summaries;
  - extraction log and candidates log.

Store downloads are in `<scratch>/slot3ev25/dl_ref/`, the comparison outputs in `<scratch>/slot3ev25/out/`.
`<scratch>` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.

The scripts ran as `$V -I scripts/map_tracks.py <ours> <ref poses> <ref world_vo> <parquet> <table_frame> mapping.json`,
`$V -I scripts/rel_assembly.py <mapped> <ref poses> rel_assembly.json` and
`$V -I scripts/parquet_assembly.py <parquet> <ref poses> <table_frame> <mapped> parquet_assembly.json`.
