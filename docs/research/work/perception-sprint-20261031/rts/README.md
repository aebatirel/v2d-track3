# rts: zero-lag position smoother after S2 (refine step S13), public gate, 31 Oct 2026

Perception sprint, experiment "rts". Pre-registration: `PREREG.md` (21:17 UTC, before any run; Amendment 1 at
21:26 UTC, before any score). Labels: [M] measured, [E] estimate, [H] hypothesis. CPU only in this cloud container,
$0; no GPU, Vast or Kaggle; nothing committed by this step (the orchestrator commits).

## 1. Verdict: FAIL (pre-registered rule, Po arm) [M]

| arm | mean R_lib S2 → S2+S13 | mean ΔR_lib (bar ≥ +0.005) | min ΔR_lib (bar ≥ −0.02) | better / worse | mean ΔRPE_lib, 13 multi-object eps | rule |
|---|---|---|---|---|---|---|
| **Po (primary)** | 0.8944 → 0.8943 | **−0.00011** | −0.0022 (ep22) | 9 / 7 | −0.007 cm (2.491 → 2.484) | **FAIL** |
| refineP (replication) | 0.8982 → 0.8978 | −0.00046 | −0.0044 (ep31) | 8 / 10 | −0.008 cm (2.440 → 2.433) | FAIL |

- The smoother does nothing measurable at kit-chain level: every episode moves by ≤ 0.0022 (Po) / 0.0044 (refineP)
  AUC, with both signs. The no-harm part holds; the gain part misses by 0.005. X*_geom readings agree (Po mean
  −0.00006, min −0.0052 on ep22).
- RPE improves by ≈ 0.007 cm on average (0.3 %); no episode worsens by more than +0.5 cm (largest gain: ep23, the
  board-swap episode, −0.06 cm). Not gating.
- Matches the pre-registered guess (central +0.0005, range −0.002 to +0.003, P(PASS) ≈ 0.1).
- **What FAIL leaves (PREREG §5):** S13 stays in the code as an opt-in, unused step; default behaviour is byte-identical
  (§3). The positions-only zero-lag smoother is closed at kit-chain level on public data. S2 stays the only adopted
  temporal fix. No pack, reference or job changes. Any other form (rotation smoothing, other σ / q) needs a fresh
  pre-registration, and these 20 episodes are now seen for this family of filters.

## 2. What ran, deviations

- **Step S13** (`pipeline/rts.py`, hook in `pipeline/refine.py`): exactly PREREG §2. Positions are the world-pose
  translation, rotations untouched, the hand gate uses `valid_<side>` joints from `hands_refined.npz` against every
  len(V)//300-th library_v3 vertex posed by S13's input (S2's output). `rts_smooth` equals the reference
  `all20.kf(..., smooth=True)` (keen-heisenberg, 4fc29ef) to < 1e-12 m (unit test).
- **Arms:** control `--steps S2`, treatment `--steps S2,S13`, on Po (`$S/leak/t1/in_Po/ep<N>`) and refineP
  (`$S/refine/in/ep<N>`), 20 public episodes each. All 80 runs finished, no tracebacks. Every input passed
  `refine.assert_inference_input`, and nothing on the inference side reads mocap or a parquet.
- **Deviation 1, Amendment 1 (pre-score, GT-free):** INVALID (c) as first written ("rotations differ by > 1e-4 deg")
  fired at 1.27e-4 deg on the last frame of one object.
  - Cause: S2 holds the last frame, so refine writes its input bytes unchanged. S13 moves that frame's position, and
    refine's shared writer then orthonormalises its rotation (an SVD it applies to every changed frame, for every step).
  - There the treatment rotation equals the orthonormal projection of the control's to ≤ 2.3e-6 deg. The 1.27e-4 deg is
    the float32 input's own non-orthonormality (|RᵀR − I| ≤ 6.1e-6), not a rotation.
  - All other 16918 of 16984 object-frames are byte-identical.
  - (c) was amended before any mocap was read (`PREREG.md` Amendment 1; sha256 of both versions in `results/`).
  - My first check used arccos((tr(R_AᵀR_B) − 1)/2), which reads 0.02–0.1 deg even for identical float32-derived
    matrices. It was replaced by the chordal angle (`rts_bytecheck.py` docstring).
- **Deviation 2 (bookkeeping):** PREREG names HEAD fef059b for the pre-change baseline.
  - The orchestrator committed WIP commits during the run, so `git rev-parse HEAD` read dc4be79 (pre runs), d642821
    (post runs) and 665f7eb (scoring).
  - pipeline/, tests/ and tools/ are identical between fef059b and dc4be79 (`git diff --quiet`). The refine.py that ran
    the baseline has sha256 aae1fb41…, which equals fef059b's.
  - The S13 code that ran inference and scoring (refine.py 3da2a33c…, rts.py 529219b4…; unchanged between the start
    and end of scoring, checked in `rts_score.py`) is exactly commit **fbe5fa6** (also unchanged at HEAD 2ce1872).
- No other deviation. INCOMPLETE: no (80/80 runs, 40/40 Po scores finite). INVALID (a), (b), (c) amended, (d), (e):
  none.

## 3. Default behaviour is byte-identical [M] (`scripts/rts_bytecheck.py` → `results/bytecheck.json`)

- `DEFAULT_STEPS` is unchanged (`'S0,S1,S2,S3,S4'`). `STEP_ORDER` only gains `'S13'` at the end. Without `--steps`
  the parsed step set is unchanged (unit test `test_option`).
- **Before vs after the change, same inputs:** control `--steps S2` and the default chain (no `--steps`; S0 skips
  without a video, S1/S3/S4 run), 2 arms × 20 episodes, 80 runs.
  - The arrays of `poses.npz`, `poses_world_vo.npz` and `pose_opt_aux.npz` are identical in 80 / 80 runs, and even
    the npz files are byte-identical (240 / 240 sha256).
  - `pose_opt.json` is equal in 80 / 80, with time, code, argv and params removed. Params are equal apart from the 6
    new `s13_*` keys.
- **Continuity with the sprint:** the control S2 outputs are array-identical (80 / 80 npz) to heldpose's S2 runs
  (refine 3b353b5f…). The control's R_lib equals the heldpose table's S2 lib column on all 20 episodes.
- **Tests (scoring venv python; pytest is not installed):** `tests/test_refine_s13.py` 7/7 pass.
  `test_refine_s6.py` 3/3, `test_refine_s10.py` 5/5 and `test_refine_s12.py` 7/7 still pass (`results/tests_after.log`).

## 4. Per episode [M] (Δ = S2+S13 − S2; lib = leaderboard convention; RPE in cm, multi-object episodes only)

| ep | objects | S2 R_lib Po | ΔR_lib Po | ΔR_lib refineP | ΔR_* Po | S2 RPE_lib Po | ΔRPE_lib Po | near-frame share | S13 change mean / max (cm), worst object |
|---|---|---|---|---|---|---|---|---|---|
| 0 | pot, lid | 0.9669 | +0.0003 | +0.0000 | +0.0019 | 1.343 | −0.001 | 0.65, 0.31 | 0.033 / 0.19, lid f171 |
| 2 | pot, lid | 0.9911 | −0.0009 | +0.0001 | −0.0002 | 1.379 | −0.001 | 0.77, 0.31 | 0.039 / 0.23, pot f340 |
| 11 | blue cup, beige cup | 0.9012 | +0.0005 | +0.0005 | +0.0016 | 1.717 | −0.001 | 0.69, 0.66 | 0.047 / 0.31, blue f65 |
| 12 | blue cup, rack | 0.9763 | +0.0002 | +0.0005 | −0.0001 | 1.116 | −0.004 | 0.66, 0.01 | 0.065 / 0.73, blue f63 |
| 13 | blue cup, rack | 0.9623 | +0.0015 | +0.0010 | +0.0015 | 1.349 | −0.007 | 0.59, 0.00 | 0.105 / 0.91, blue f166 |
| 18 | sweeper, dust pan | 0.9162 | +0.0000 | −0.0006 | −0.0013 | 4.012 | −0.004 | 0.76, 0.52 | 0.137 / **5.37**, sweeper f153 |
| 21 | blue cup, pitcher | 0.8389 | −0.0005 | −0.0005 | +0.0020 | 1.179 | +0.000 | 0.56, 0.49 | 0.148 / 0.96, pitcher f94 |
| 22 | blue cup, pitcher | 0.8704 | **−0.0022** | −0.0030 | −0.0052 | 1.114 | −0.002 | 0.74, 0.37 | 0.105 / 0.60, pitcher f82 |
| 23 | boards (identity swap) | 0.0425 | +0.0006 | +0.0006 | +0.0005 | 14.152 | −0.059 | 0.45, 0.83 | 0.295 / **8.02**, board 1 f155 |
| 24 | boards | 0.8091 | −0.0011 | −0.0011 | −0.0002 | 0.807 | −0.001 | 0.87, 0.51 | 0.050 / 0.33, board 2 f40 |
| 26 | rack, pot | 0.9717 | +0.0012 | −0.0006 | +0.0006 | 1.180 | −0.008 | 0.06, 0.56 | 0.078 / 0.35, rack f70 |
| 27 | rack, pot | 0.9634 | +0.0000 | −0.0007 | +0.0008 | 1.184 | −0.003 | 0.00, 0.76 | 0.059 / 0.28, rack f61 |
| 31 | sweeper, rack | 0.8239 | −0.0015 | **−0.0044** | −0.0010 | 1.850 | −0.002 | 0.85, 0.90 | 0.029 / 0.16, sweeper f20 |
| 39 | dust pan | 0.9759 | −0.0008 | −0.0008 | −0.0008 | – | – | 0.73 | 0.063 / 0.79, f240 |
| 40 | dust pan | 0.9584 | +0.0000 | +0.0000 | −0.0010 | – | – | 0.82 | 0.036 / 0.23, f121 |
| 41 | pot | 0.9927 | +0.0004 | +0.0004 | −0.0002 | – | – | 0.76 | 0.041 / 0.24, f101 |
| 42 | pot | 0.9990 | +0.0000 | −0.0003 | +0.0003 | – | – | 0.82 | 0.039 / 0.17, f162 |
| 43 | pot | 0.9486 | −0.0011 | −0.0014 | −0.0009 | – | – | 0.87 | 0.033 / 0.15, f321 |
| 44 | pot | 0.9970 | +0.0007 | +0.0007 | +0.0000 | – | – | 0.79 | 0.032 / 0.14, f222 |
| 45 | pot | 0.9823 | +0.0005 | +0.0005 | +0.0004 | – | – | 0.86 | 0.040 / 0.14, f188 |

Near-frame share and change are from the Po run's `pose_opt.json` (GT-free). Per-object ΔAUC: `results/rts_tables.md`.

## 5. Reading (post hoc) [M / E]

- **Why nothing moves [E]:** S13 moves positions by 0.03–0.3 cm on average (Po), and the kit's ADD-AUC steps at
  1–9 cm. The held-out diagnostic gain (−0.5 to −1.2 % of the ADD, keen-heisenberg) is a few hundredths of a
  centimetre, too small to cross a 1 cm threshold step on more than a handful of frames.
- **Where it moves most [M, GT-free]:** the two large changes are known tracker jumps with no hand near.
  - ep18 sweeper f153: 5.4 cm. The track jumps back by 15.6 cm at f155 while the holding hand is unmeasured (heldpose
    §6).
  - ep23 board 1 f155: 8.0 cm.
  - There q = 0.04 rounds the jump over about ±10 frames instead of fixing it. ep18 ΔR_lib: +0.0000 (Po), −0.0006 (refineP).
- Handled objects are "near" on 45–90 % of frames, so they get q = 4.0 (light smoothing) most of the time. Static
  racks get q = 0.04 nearly everywhere.

## 6. Commands, machine, code

- Machine: this Claude cloud container (4 cores, 15 GB), CPU only, $0. S =
  `/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad`;
  PY = `$S/map/scoring/venv/bin/python`.
- Code: inference and scoring ran refine.py `3da2a33c…` and rts.py `529219b4…` = commit **fbe5fa6** (identical at
  HEAD 2ce1872). The pre-change baseline ran refine.py `aae1fb41…` = fef059b. See `results/code_version_{pre,post}.txt`
  and `results/code_sha256_before_scoring.txt`.
- Commands, in order (UTC):
  1. 21:17: `PREREG.md` written; sha256 in `results/PREREG_sha256_before_any_run.txt`.
  2. 21:18–21:19: `bash scripts/rts_run.sh pre` → `$S/rts/runs_pre/<arm>/{S2,DEF}/ep<N>` (`results/jobs_pre.txt`).
  3. Code change (rts.py, refine.py hook, tests/test_refine_s13.py); then
     `$PY tests/test_refine_s{6,10,12,13}.py`.
  4. 21:22–21:24: `bash scripts/rts_run.sh post` → `$S/rts/runs/<arm>/{S2,DEF,S13}/ep<N>` (`results/jobs_post.txt`).
  5. `$PY -I scripts/rts_bytecheck.py $S/rts/bytecheck.json` → `results/bytecheck.json`.
  6. 21:26: Amendment 1; sha256 in `results/PREREG_sha256_amendment1_before_scoring.txt`.
  7. 21:26–21:31: `$PY -I scripts/rts_score.py $S/rts/rts_scores.json` (oracle side, public mocap) → log
     `results/rts_score.log`.
  8. `$PY -I scripts/rts_tables.py $S/rts/rts_scores.json results/rts_tables.md results/rts_scores_slim.json`.
- Outputs: refine runs in the scratchpad only (regenerable). Scores in `results/rts_scores_slim.json` and
  `results/rts_tables.md`.
