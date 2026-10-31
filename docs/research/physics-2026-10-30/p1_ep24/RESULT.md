# P1 settle on gmg r0 (public ep24 boards), our reference poses: RESULT

Run 31 Oct 2026, 21:33-22:15 UTC (00:33-01:15 TRT, 1 Nov), by a determined-wright helper agent for bold-albattani.
Machine: this cloud container (Linux, 4 CPU, no GPU), CPU Warp / MuJoCo-Warp. No rental, cost $0. Nothing committed.
Markers: [M] measured here, [E] estimate, [H] hypothesis. No ground truth was read (no mocap, no `pose` field).

## 1. Verdict

| P1 at frame 246, 16 jittered copies | carved (r0, 57 / 77 pieces) | default (r0/_default, 50 / 71) | default_inertia (same pieces, own COM) |
|---|---|---|---|
| host (board 1) mean drift / tilt at 2 s | **3.707 cm FAIL** / 3.08 deg pass | 3.184 cm FAIL / 13.14 deg FAIL | 3.257 cm FAIL / 13.69 deg FAIL |
| guest (board 2) mean drift / tilt at 2 s | **3.230 cm FAIL** / 1.96 deg pass | 3.201 cm FAIL / 7.71 deg FAIL | 3.282 cm FAIL / 8.52 deg FAIL |
| mean relative sink (signed, + = guest down) | -4.74 mm pass | +1.12 mm pass | +1.08 mm pass |
| NaN copies | 0 pass | 0 pass | 0 pass |
| fall-through, reading A (clause not applicable) | pass | pass | pass |
| fall-through, reading B (conservative) | 16/16 guest ends on table: FAIL | 16/16: FAIL | 16/16: FAIL |
| **P1** | **FAIL** | **FAIL** | **FAIL** |

- **P1 as specified fails for the carved pieces** [M]. The failing criterion is drift: both boards fall about 3 cm.
  The default control fails the same way, and it also fails tilt.
- **Why they fall** [M]: at every assembled frame, our reference holds the whole cross 27-36 mm above the table top.
  At f246 the lowest piece vertex is 35.0 mm up for board 1 and 30.7 mm up for board 2, and no hand keypoint is within
  94 mm. At f260-274 no hand keypoint is within 262 mm, yet the cross stays 29-33 mm up.
- **The cause is the reference height** [M]. The reference adds a constant world-z shift per object (+12.90 / +10.99
  mm, from `table_frame.npz`). That shift puts the library_v3 boards (2.7-3.1 cm thick) exactly on the table at frame 0
  (lowest point 0.0 mm). It does not fit 7.4 mm plates standing on edge.
- [H] In the video the free-standing cross rests on the table, and our track places it about 3 cm too high. Falsifier:
  a GT-free depth check of the board bottom edges against the table plane at f260-274.
- **Carved pieces with the hover removed (diagnostic, not the spec)** [M]: the pair is lowered rigidly so its lowest
  vertex is 1 mm above the table, with the relative pose unchanged. The carved pieces then pass every numeric P1
  criterion at f246, f258 and f270. The default fails tilt (section 5).
- **Contact-budget hazard** [M]. With the training sim config's buffers (`sim=rl`: nconmax 256, njmax 512 per world;
  this is `settle_at.py` exactly as written, 1 world):
  - The carved scene overflows MuJoCo-Warp's broadphase in 16/16 copies (it asks for 500-670).
  - Contacts are dropped, and both boards fall through the table: the guest ends about 10-46 cm below the table top
    in 16/16 copies, with mean tilt about 90 deg.
  - The default pieces never overflow.
  - With large buffers the carved scene needs up to about 2030 constraint rows per world (njmax 512 in `sim=rl`); the
    default needs 416-425.
  - What this does to 4096-world GPU training or to the evaluator is not tested [unknown]. Falsifier: count the
    `broadphase overflow` / `nefc overflow` warnings in a 1-world rollout with the packed config on these pieces.

Under F-I4.8, a P1 fail marks r0 do-not-use. That decision is not taken here. Note that the failing criterion does not
separate carved from default at this reference.

## 2. Inputs (all hashes checked)

- **r0** from `origin/claude/bold-albattani-6qmxsv`, commit `cdc8b4016a207653fad83f0d21fe55b406d52d99`, path
  `docs/research/mesh-2026-10-26/gmg/build/I/results/slot2-ep24/fi4o/r0`, extracted with `git archive` to
  `src/`.
  - `manifest.json` sha256 `271f9899d464eaf64eaa8737c518c7fc613d8d04e091f221334df237b964f600` (as in the hand-off).
  - `props_gmg.json` sha256 `367dd86a...`.
  - The visual `<obj>.glb` is not in git (gitignored). It does not matter here: `make_assets.py` takes the visual from
    `meshes/library_v3`, and visuals do not collide.
- **Reference** (our perception, not GT): HF store `aebatirel/v2d-store`,
  `runs/20261030-physS1-6a814df/refs/glockt/ep24/processed/sequence_id=t3_ep024/robot_name=sharpa_wave/ref_gl_ilc.parquet`.
  - **md5 `699fe4266a0a965aaf4472a1bfcc8828` (matches).**
  - Support stage `t3_ep024_support.usda` md5 `debb7ad950590b91738f141a7f73310b`: table cylinder top at z = 0.600 m.
- **Relation to the gmg's P_sim** [M]: the reference object poses equal the gmg P_sel tracks plus a constant world-z
  shift per object (max residual 0.0 mm / 0.0 deg over 275 frames).
  - P_sel is `poses.npz` sha256 `e694dae3...`, the file named in the r0 manifest's `p_sim`. It is mapped by
    `T_table_from_world`.
  - The z shift is board 1 +12.904 mm, board 2 +10.989 mm.
  - So our relative pose differs from the gmg's P_sim by 1.92 mm along world z (board 1 higher). That is along the
    insertion direction.

## 3. Frames and roles

- **Frame 246 (primary).** decisions.json gives an INSERTION run of 164-274 (travel 122 mm, straightness 0.91). The
  spec takes the median frame of the assembled stretch for INSERTION.
  - The gmg's assembled stretch on P_sim (= P_sel, `sim_pose_fallback`) is f218-274: 29 frames at stride 2, for both
    ordered pairs.
  - Its median `asm[len//2]` = 246. The gmg used the same frame for P2 and for its own P1 pre-check.
  - On our reference, the gmg rule (`_static_stretches`: < 2 mm/frame, >= 5 frames) gives the same stretch for
    board 2 <- board 1.
  - For board 1 <- board 2 the stretch splits at 238->240: 2.018 mm/frame here against 1.995 on P_sel, a result of
    the z shift. That gives 240-274, median **258**. At stride 1 it gives 265-274, median **270**. Both were also run.
  - Frame 0 does not apply: the boards are 30 cm apart there.
- **Host = wooden_piece_1 (board 1), guest = wooden_piece_2 (board 2).**
  - The gmg's pair key is `wooden_piece_1|wooden_piece_2`, meaning target o = host and partner p = guest. Their P1
    pre-check uses the same roles.
  - Our reference agrees. Board 2 descends onto board 1: its lowest point goes from 150 mm at f160 to 27 mm at f218,
    while board 1 stays at 26-37 mm. Its path in board 1's frame is d = (0.04, -1.00, -0.05), which is world-down at
    assembly.

## 4. Collision geometry actually loaded [M]

`make_assets.py LIB OUT --pieces DIR` writes one `<collision>` per `piece_*.obj`. FlashCHORD (`decompose_objects=True`)
runs CoACD on each piece and keeps one hull per piece.

| config | board 1 collide shapes (hull / piece volume cm3) | board 2 collide shapes (hull / piece volume cm3) |
|---|---|---|
| carved | **57** (215.825 / 215.853) | **77** (208.373 / 208.385) |
| default, default_inertia | **50** (220.516 / 220.525) | **71** (212.516 / 212.532) |

- These counts come from the built model: shapes with the COLLIDE flag on each object body.
- Sorted per-hull volumes match the pieces within 0.008 cm3.
- The visual GLB and the original piece meshes are non-colliding: carved 58 / 78 non-colliding shapes per body.
- Totals: 134 shapes carved, 121 default.
- COM / inertia:
  - carved: r0's `inertia.json`.
  - default: no `inertia.json` exists, so `make_assets` keeps the library_v3 surface estimate, with the COM 3-4 mm
    away from the pieces' solid.
  - default_inertia: the exact uniform-solid COM / inertia of the default pieces (`scripts/piece_props.py`; it
    reproduces r0's carved `inertia.json` within 1 mm).
  - Mass is 0.3 kg in every config.

## 5. All results (means over 16 jittered copies; drift cm / tilt deg at 2 s)

| run | host drift / tilt | guest drift / tilt | rel sink mm | NaN | guest on table end | guest low < host low end | start low host / guest mm | fails |
|---|---|---|---|---|---|---|---|---|
| f246 lit carved | 3.707 / 3.08 | 3.230 / 1.96 | -4.74 | 0 | 16/16 | 3/16 | 35.0 / 30.7 | drift x2 |
| f246 lit default | 3.184 / 13.14 | 3.201 / 7.71 | +1.12 | 0 | 16/16 | 14/16 | 35.0 / 30.7 | drift x2, tilt x2 |
| f246 lit default_inertia | 3.257 / 13.69 | 3.282 / 8.52 | +1.08 | 0 | 16/16 | 11/16 | 35.0 / 30.7 | drift x2, tilt x2 |
| f258 lit carved | 3.357 / 2.84 | 3.045 / 1.94 | -3.08 | 0 | 16/16 | 7/16 | 32.4 / 29.5 | drift x2 |
| f258 lit default | 3.140 / 12.66 | 3.074 / 10.06 | +0.04 | 0 | 16/16 | 9/16 | 32.4 / 29.5 | drift x2, tilt x2 |
| f258 lit default_inertia | 3.121 / 13.24 | 3.074 / 9.83 | +0.12 | 0 | 16/16 | 9/16 | 32.4 / 29.5 | drift x2, tilt x2 |
| f270 lit carved | 3.428 / 2.71 | 3.055 / 1.93 | -3.77 | 0 | 16/16 | 7/16 | 33.2 / 29.5 | drift x2 |
| f270 lit default | 3.024 / 14.78 | 3.115 / 6.11 | +1.81 | 0 | 16/16 | 13/16 | 33.2 / 29.5 | drift x2, tilt x2 |
| f270 lit default_inertia | 2.997 / 12.61 | 3.102 / 8.60 | +1.95 | 0 | 16/16 | 13/16 | 33.2 / 29.5 | drift x2, tilt x2 |
| f246 snap1 carved (diag.) | 0.787 / 3.00 | 0.379 / 2.21 | -4.80 | 0 | 16/16 | 4/16 | 5.3 / 1.0 | none |
| f246 snap1 default (diag.) | 0.921 / 15.90 | 0.598 / 5.71 | +1.24 | 0 | 16/16 | 11/16 | 5.3 / 1.0 | tilt x2 |
| f246 snap1 default_inertia (diag.) | 0.806 / 17.76 | 0.517 / 5.05 | +1.17 | 0 | 16/16 | 16/16 | 5.3 / 1.0 | tilt x2 |
| f258 snap1 carved (diag.) | 0.589 / 2.70 | 0.333 / 1.95 | -3.25 | 0 | 16/16 | 5/16 | 3.9 / 1.0 | none |
| f258 snap1 default (diag.) | 1.032 / 18.12 | 0.799 / 7.52 | +0.34 | 0 | 16/16 | 10/16 | 3.9 / 1.0 | host drift, tilt x2 |
| f258 snap1 default_inertia (diag.) | 0.911 / 17.89 | 0.660 / 6.75 | +0.19 | 0 | 16/16 | 9/16 | 3.9 / 1.0 | tilt x2 |
| f270 snap1 carved (diag.) | 0.683 / 2.93 | 0.372 / 2.23 | -3.83 | 0 | 16/16 | 4/16 | 4.7 / 1.0 | none |
| f270 snap1 default (diag.) | 0.945 / 19.14 | 0.611 / 4.55 | +1.81 | 0 | 16/16 | 13/16 | 4.7 / 1.0 | host tilt |
| f270 snap1 default_inertia (diag.) | 0.719 / 19.54 | 0.374 / 4.50 | +2.05 | 0 | 16/16 | 15/16 | 4.7 / 1.0 | host tilt |

**Reading the table.**
- **Sign of the relative sink.** It is negative for the carved pieces: the host ends lower relative to the guest by
  3-5 mm. Board 2's bottom edge starts 2.9-4.3 mm below board 1's, so board 2 lands first. Board 1 then slides down
  the slot until it reaches the table.
  - The signed criterion passes (the gmg's `simphys.settle` is also signed).
  - |sink| is 4.7-4.8 mm at f246, above 4 mm. A reader who takes the criterion as unsigned should count that as a fail.
- **Relative pose change** (guest in host frame, mean): 0.50 cm / 3.3 deg carved, 0.66 cm / 19 deg default.
- **Fall-through.**
  - Reading A: at P_sim the guest is not on top of the host. Its lowest point is already below the host's lowest
    point, because the cross stands on both edges. On that reading the clause does not apply.
  - Reading B: P_sim has the guest off the table and engaged in the host, so the clause applies. Then every copy
    fails, in every config, because the whole cross lands on the table.
- **Per-copy maxima, carved literal f246:** host tilt 5.38 deg (copy 7) and guest tilt 3.79 deg; drift sd is 0.08 cm.

**As-is recipe buffers** (`sim=rl`: nconmax 256 / njmax 512, one world per copy, same 16 draws, f246):

| run | copies with overflow warnings | host drift / tilt | guest drift / tilt | guest ends > 10 mm below table |
|---|---|---|---|---|
| lit carved | 16/16 (200-231 lines each) | 15.89 / 92.8 | 14.43 / 94.6 | 16/16 (to -458 mm) |
| lit default | 0/16 | 3.184 / 13.14 | 3.201 / 7.71 | 0/16 |
| snap1 carved | 16/16 | 11.41 / 90.2 | 9.59 / 85.8 | 16/16 |
| snap1 default | 0/16 | 0.921 / 15.90 | 0.598 / 5.71 | 0/16 |

The default rows match the large-buffer runs per copy, to the stored 3 decimals. That shows the buffer size changes nothing when there is
no overflow.

**Intrusion at the P1 frames** [M]: guest pieces inside host pieces, at our reference, 0.7 mm grid.
- Carved: f218 0.75 cm3 (deepest 1.37 mm); f246 0.14 cm3 (0.58 mm); f274 0.10 cm3 (0.49 mm).
- Default: 6.83-7.02 cm3 (3.7 mm deep, the plate half-thickness).
- Board 2's slot is about 3.5 mm off the real slot (the gmg's own caveat). It does not show at our relative pose, since
  the slot was centred on the same track.

## 6. Per-copy values, f246 literal (all other runs: `result.json`, key `per_copy`)

carved: copy | host drift cm | host tilt | guest drift cm | guest tilt | rel sink mm
```
 1 3.853 4.85 3.292 2.98 -5.38 |  2 3.613 0.99 3.192 1.28 -4.11 |  3 3.594 4.57 3.123 1.84 -4.61 |  4 3.698 4.12 3.205 2.34 -5.03
 5 3.727 1.82 3.281 0.55 -4.54 |  6 3.745 4.95 3.233 1.77 -5.12 |  7 3.746 5.38 3.159 2.09 -5.97 |  8 3.681 3.21 3.181 2.72 -4.91
 9 3.746 2.63 3.333 2.96 -3.96 | 10 3.735 2.20 3.315 2.63 -4.14 | 11 3.814 3.96 3.272 2.15 -5.23 | 12 3.804 2.04 3.357 3.79 -4.45
13 3.599 0.95 3.158 0.32 -4.39 | 14 3.576 3.95 3.242 0.80 -3.39 | 15 3.694 1.89 3.100 2.10 -6.06 | 16 3.679 1.77 3.235 0.99 -4.48
nominal (unjittered) 3.676 2.92 3.163 2.19 -5.09
```
default (literal build):
```
 1 3.201 20.10 3.156  2.35 +0.14 |  2 3.226  5.12 3.222 12.29 +0.77 |  3 3.156 13.44 3.201  9.22 +0.97 |  4 3.110 14.51 3.197  6.33 +1.65
 5 3.314 15.05 3.260 10.70 +0.67 |  6 3.388 14.75 3.378  7.38 +1.55 |  7 3.258 12.35 3.154 13.18 +0.03 |  8 3.008 11.55 2.993  6.22 +1.39
 9 3.433  5.59 3.337 10.46 +0.85 | 10 3.193  7.74 3.274  6.44 +1.27 | 11 3.174 14.96 3.156  7.55 +0.58 | 12 3.171 19.86 3.267  5.16 +1.83
13 3.039 15.04 3.138  7.71 +1.73 | 14 3.126 14.60 3.275  5.98 +2.34 | 15 3.044  8.35 3.087  8.79 +1.47 | 16 3.101 17.25 3.127  3.59 +0.78
nominal 3.205 19.05 3.249 4.72 +1.61
```
default_inertia:
```
 1 3.173 18.60 3.156  2.33 +0.14 |  2 3.173  5.59 3.197 11.02 +0.78 |  3 3.251 16.18 3.373 12.26 +1.56 |  4 3.244 15.66 3.296  3.81 +1.46
 5 3.357 19.52 3.370  5.31 +1.04 |  6 3.106 12.38 3.180  6.85 +1.78 |  7 3.658 12.04 3.613 12.52 +0.39 |  8 3.249 14.83 3.228  9.95 +0.31
 9 3.141  9.20 3.237  7.81 +1.46 | 10 3.264  8.49 3.277  5.20 +0.96 | 11 3.289 15.77 3.221 11.83 +0.94 | 12 3.338 19.57 3.375  5.97 +1.50
13 3.024 11.05 3.140 13.05 +1.16 | 14 3.174 13.86 3.253 10.55 +2.16 | 15 3.174 11.07 3.136 12.37 +1.06 | 16 3.490 15.30 3.460  5.46 +0.66
nominal 3.062 18.30 3.209 6.03 +2.07
```

## 7. Deviations from the spec / recipe (each stated, none tuned on results)

1. **Contact buffers:** `sim.nconmax=4096, sim.njmax=16384` per world (FlashCHORD `SimConfig` defaults and
   `configs/sim/replay.yaml`) instead of `sim=rl` (256 / 512). Without this, contacts are dropped (section 5). Every
   reported large-buffer run has 0 overflow lines.
2. **Worlds:** 17 worlds per env (world 0 nominal, worlds 1-16 jittered) instead of 1. Copies 1 and 7 re-run in 1
   world gave identical numbers.
3. **Jitter:** applied to both objects' start poses, as the task asked; the gmg pre-check jitters the guest only.
   - Draws: `default_rng(0).normal((16, 2, 6))`, with 0.5 mm per axis and a 0.005 rad rotation vector per axis.
   - The rotation is applied about the mesh origin, in the world frame.
   - All configs use the same draws (common random numbers).
4. **Drift / tilt definitions:** measured from each copy's own start pose (gmg `simphys.settle`); tilt is the full
   rotation angle. The drift from the unjittered pose is also stored and differs by at most 0.13 cm.
5. **Default control:** run twice, as the literal build and with the pieces' own inertia (section 4).
6. **snap1:** diagnostic only, not the spec's P1.
7. **Script version:** `settle_p1.py` gained `--only_copy` after the K-world runs, to run single copies for the as-is
   runs and the check. The K-world path is unchanged; the copy 1 / 7 re-runs reproduce it exactly.

## 8. Exact commands (all in `logs/commands.txt` with timestamps, exit codes and wall times)

```
P=/tmp/claude-0/-home-user-v2d-track3/9bee9e08-a3b0-5c25-ae4f-3db987cc25f2/scratchpad/p1ep24
S=/tmp/claude-0/-home-user-v2d-track3/9bee9e08-a3b0-5c25-ae4f-3db987cc25f2/scratchpad
R0=$P/src/docs/research/mesh-2026-10-26/gmg/build/I/results/slot2-ep24/fi4o/r0
git -C /home/user/v2d-track3 archive cdc8b4016a207653fad83f0d21fe55b406d52d99 docs/research/mesh-2026-10-26/gmg/build/I/results/slot2-ep24/fi4o/r0 | tar -x -C $P/src
cd $P/store && HF_TOKEN=hf_dummy $S/venv/bin/python -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('aebatirel/v2d-store', '<path>', repo_type='dataset', local_dir='.'))"   # ref parquet + support usda
$S/venv/bin/python -I $P/scripts/piece_props.py $R0/_default $P/pieces/default_own_inertia --mass 0.3
$S/venv/bin/python /home/user/v2d-track3/pipeline/make_assets.py /home/user/v2d-track3/meshes/library_v3 $P/assets/carved --pieces $R0
$S/venv/bin/python /home/user/v2d-track3/pipeline/make_assets.py /home/user/v2d-track3/meshes/library_v3 $P/assets/default --pieces $R0/_default
$S/venv/bin/python /home/user/v2d-track3/pipeline/make_assets.py /home/user/v2d-track3/meshes/library_v3 $P/assets/default_inertia --pieces $P/pieces/default_own_inertia
# one settle run (scripts/run_one.sh NAME CONFIG FRAME [args]) expands to:
cd $S/src/video_to_data/robotic_grounding/flash_chord && FC=$PWD EMB=sharpa_hands_mid FLASH_CHORD_CACHE_DIR=$P/fccache \
  $S/fcvenv/bin/python $P/scripts/settle_p1.py --tree $P/store/runs/20261030-physS1-6a814df/refs/glockt/ep24 \
  --assets $P/assets/carved --frame 246 --k 16 --seed 0 --sig_pos 0.0005 --sig_rot 0.005 --steps 40 \
  --host wooden_piece_1 --guest wooden_piece_2 --out $P/runs/f246_lit_carved.json --sim_over sim.nconmax=4096,sim.njmax=16384
#   snap1 adds: --snap_mm 1 --snap_pieces $R0/_default ; as-is runs drop --sim_over and add --only_copy c (c = 1..16)
$S/venv/bin/python -I $P/scripts/frames_overlap.py <ref parquet> $R0 --frames 218,246,274 --pitch 0.0007 --json $P/runs/frames_overlap.json
$S/venv/bin/python -I $P/scripts/aggregate.py $P        # -> result.json
```

Code:
- Repo HEAD (read-only) `1511616a7f34b565a1f202d46430ae8ecfde8882`.
- `make_assets.py` md5 `d1edd116...`; `settle_at.py` md5 `ad437da3...`, copied and extended to
  `scripts/settle_p1.py` (final md5 `f485420a...`).
- FlashCHORD source `video_to_data` at `8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef`, venv `fcvenv` (newton 1.2.0, warp
  1.14.0, mujoco 3.8.1).
- Sim settings: fps 20, 5 substeps (dt 0.01 s), Newton solver, pyramidal cone, implicitfast, 100 iterations, 40
  control frames = 2 s.

Failures along the way (kept in `logs/`):
- One run crashed on a CoACD cache race (two configs with identical pieces built in parallel) and was re-run.
- The as-is batch failed twice before it ran: a missing log directory, then xargs joining lines that had trailing
  blanks. It was re-run; no results were affected.

Wall time: about 40 min, CPU only.

## 9. Files

- `result.json`: everything above, including per-copy values for all 18 large-buffer runs and the 64 as-is copies.
- `runs/*.json`, `runs/*_series.npz`, `runs/asis/`: raw outputs, including pose series.
- `logs/`: run logs and `commands.txt`.
- `scripts/`: all code used.
- `assets/{carved,default,default_inertia}`: the built URDFs.
