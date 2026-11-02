# Tracking-perception session, 2 Nov 2026: results

Branch `claude/perception-tracking-20261102`, session_01D9UJC9EUCs5sUCbTVZgvcC.
- **Goal:** GT-free changes that bring our perceived object trajectories closer to the real motion on the 20 public
  episodes.
- **Rules:** mocap is read only by scoring and diagnostics; every test was pre-registered before its run.
- **Labels:** [M] measured, [D] public vs mocap, [E] estimate, [I] inference, [H] hypothesis.

## Results (each vs a control from the same code; 20 public episodes unless noted)
| # | Test (PREREG) | ΔAUC mean | better / worse | worst | ΔMPPE / ΔRPE cm | verdict |
|---|---|---|---|---|---|---|
| 1 | Mask-guided tracking: SAM2 video masks → depth mask + re-centre + re-register (PREREG.md) | −0.0009 | 7 / 7 | −0.069 | −0.012 / −0.109 | **FAIL** |
| 1a | Depth restricted to the video mask only (ablation) | −0.0077 | 5 / 9 | −0.069 | +0.041 / +0.174 | harmful |
| 1b | Re-centre + re-register only (ablation; +0.0029 in batch 1) | — | — | ep0 −0.380 | — | **FAIL** on its replication (PREREG_MRrep.md) |
| 2 | Full-resolution stereo depth (PREREG_fs1.md; 19 eps) | −0.0079 | 7 / 10 | −0.098 | +0.105 / −0.013 | **FAIL** |
| 3 | Complete-base (lathe) pitcher as tracking template, ep21 / 22 (PREREG_pitcher.md) | −0.249 | 0 / 2 | −0.261 | +3.9 / +5.6 | **FAIL** |
| 4a | SAM-6D-style detector scores added to our detector rules, frame 0 + re-detection (PREREG_ism.md) | +0.0010 | 6 / 1 | −0.0009 | −0.020 / −0.168 | **FAIL** (mean bar +0.005; > 3 cm frames 1030 → 1032) |
| 4b | SAM-6D-style scores replacing our rules | −0.204 (17 eps; 3 crashes) | 4 / 7 | −0.958 | +19.9 / +31.4 | **FAIL**, harmful |
| 5 | Stage 1 of the offline design: one pose per object per rest segment, trimmed multi-frame depth fit (PREREG_stage1.md) | −0.0088 | 7 / 12 | −0.062 | +0.054 / +0.206 | **FAIL**, falsifier fired (rest-frame ADD lower on 9 / 20) |

Run-to-run noise of the tracker: two identical control runs differ by mean |ΔAUC| 0.0012 per episode, mean −0.00002.

## Findings worth keeping
1. **The half-frame advance (refine S2) is in no packed eval reference [M, code read].**
   - Handed to perfect-following: apply `refine.py --steps S2` only on episodes it retrains anyway.
   - +0.006 public, about +0.004 board [E].
2. **ep23 (AUC 0.041) is a wiring gap [D].**
   - The GT-free board knob rule `pipeline/identity_fix.py` runs only in `eval_idfix.sh`.
   - On the ep23 control it fixes the board swap: 0.041 → 0.663, piece 1 0.08 → 0.96.
   - ep24 is untouched (as-tracked rank 1 / 32).
   - Eval 25 already uses it.
   - Correction: my first reading ("joint freeze") was wrong; the point-track session found the swap.
3. **Public tracks show no drift-then-snap [D].**
   - The frames with more than 3 cm error are the lost lid (ep0 base track), the ep23 swap and bias (pitcher,
     ep24 board).
   - ep18's sweeper track is chaotic: both controls lose part of it, and every perturbation recovers it.
   - So a single-episode gain from a tracker change is weak evidence.
4. **Rest-frame oracle [D]: perfect poses on mocap-rest frames only would add +0.032** (ep24 +0.118, ep31 +0.112,
   ep11 +0.088, ep21 +0.083).
   - Stage 1 shows that depth fitting against our meshes cannot collect it. It helps where the tracker bias is large
     (pitcher +0.05, rack +0.013) and hurts where the tracker is already within our mesh error (pot, cups).
   - [I] The limit is mesh shape; camera drift is ruled out by room-map's p95 of 2–9 mm.
5. **Today's eval tracking defaults** (library_v3 templates + track guard) score 0.945 on 19 public episodes. The
   25 Oct sweep base that earlier public tests used scores 0.921.
6. **Infrastructure [M].**
   - The 32 GB RTX 5090 runs out of memory when the guard re-registers while extra models are loaded.
   - `hf download --include` lists the whole store repo, about 12–15 min per call. Prefetch per file instead.

## Design note
`DESIGN_offline_joint.md`: offline whole-video pose estimation, with the measured oracle, Stage 1's failure and the
SAM-6D / PRISM references.

## Spend [E, from instance hours × $/h]
| Box | Cost |
|---|---|
| ptrkA | ≈ $3.4 |
| ptrkB | ≈ $3.2 |
| ptrkC | ≈ $5.1 |
| ptrkD | ≈ $9–10 (still finishing report-only cells) |
| ptrkE (detector test, $6 cap) | ≈ $4.6 |
| Stage 1 | $0 (CPU) |

Total ≈ $25–26 against $30 + $6 + $4.

## Files
- PREREG*.md: pre-registrations.
- `results/`: gate JSONs, rest oracle, rest-frame ADD, idfix.
- `scripts/`: gate.py, pf_split.py, rest_oracle.py, stage1.py, rest_add.py.
- `stage1/vo/`: sha256 and per-episode fit logs.
- Code: `pipeline/vos_guide.py`, `pipeline/ism_score.py`, and perc2 flags TRACK_VOS / VOS_* / DET_ISM (all default
  off); `ops/jobs/perc_vos.sh`.
- Store runs: `runs/20261102-ptrk{A,B,C,D,E}-*`.
