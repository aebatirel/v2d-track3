# Perception and reference state, 27 Oct 2026

Main branch is `origin/main-bsky37` at 2bb20e3. Labels: **[M]** measured in a repo doc; **[M-new]** measured by me today on CPU from files already in the HF store, $0; **[E]** estimate; **[D]** derived from [M] numbers.

## 0. What matters most

**Note 23 was written against old code.**
- Its branch `claude/focused-pascal-2nz9s1` forks from 4d1d7ee (2026-10-20, before the first GPU day). It assumes kp 25 wrists and missing perception outputs.
- Main has since built several of its levers:
  - a kp 400 wrist for the grasp-lock learner (`main:ops/jobs/glock_public.sh` l.66/174/227, `main:flashchord_conf/embodiment/sharpa_hands_mid.yaml`);
  - the hand locked to the object during carries, plus a gravity feed-forward on the wrist target (`main:pipeline/grasp_lock.py` docstring);
  - wrist iterative learning control (`main:pipeline/wrist_ilc.py`);
  - per-frame rest settling of objects (`main:pipeline/contact_retarget.py` l.340, `--rest_settle`).
- Note 23 also says the perception outputs "need regenerating on the first box". That is wrong: the HF store holds them (§5).
- File-name clash: main already has `docs/research/notes/23-grasp-controller-and-rl-handoff.md`.
- Merge risk: this branch's `pipeline/pipeline_ep.sh` edit is made against the 20 Oct file, so it would conflict with main.

**The pour hand gap is already handled** in the eval-20 reference that was packed (§3, [M-new]).

**Most of what we lose against public mocap is bias, not jitter.** The verified review (`main:docs/analysis/robustness-review-20261026/refcheck/README.md`) lists seven problems:
- R1: the table snap moves objects that rest on other objects;
- R2: frame-0 anchor tilt;
- R3/R4: how our meshes register to the hidden scans;
- R5: resting objects creep in our tracks;
- R6: our paths run half a frame late;
- R7: resting heights are off by centimetres.

**Any reference change reaches the leaderboard only by retraining.** Submitted rows must be official rollouts, so a fix costs about $2–3 per episode and seed [E]. Only part of a sim_vs_ref gain transfers: 0.74 from pack 3 to pack 4 [M].

## 1. The perception and reference pipeline behind the submissions

**Chain.** `main:ops/jobs/eval_both.sh` → `glock_public.sh` → `pipeline/pipeline_ep.sh`:
- **`perc2.py`:** FoundationStereo at half resolution; SAM2 × DINOv2 detection with the compact prior, the reach/size/Grounding DINO rules, gated re-proposal and the on-table rule; FoundationPose with 5 register / 2 track iterations; track guard on; library_v3/v3x meshes as tracking templates. There is no temporal smoothing of object poses (`main:pipeline/perc2.py` l.35–437).
- **`hands_mp.py`:** greedy linker, gaps of 15 frames or fewer interpolated, Savitzky-Golay smoothing over 7 frames. Then `hand_refine.py`.
- **`mkref.py`:**
  - `--wrist_cost 3.0`;
  - a constant per-object z snap of up to ±2 cm, based on frame 0 (l.959–968);
  - hand gaps filled by attaching the hand to the object it touches (`--gap_fill attach`, 3 cm);
  - 18 mm contact threshold.
- **`contact_retarget.py --rest_settle 1`** (variant "mck").
- **`support_fill.py`** with the arc-foot fallback (SF=1; SF=0 on carved runs).
- **`grasp_lock.py`** with the eval_both `GL_ARGS`, then `wrist_ilc.py` at kp 400.
- **`identity_fix.py`** runs only in `eval_idfix.sh` (eval 25).

**Which eval references were rebuilt when:**
- With the 25 Oct defaults (guard on): 8, 14, 20, 32, 33. A full eval perception check showed the guard changes only these (`main:docs/work-log.md` l.3680).
- From 24 Oct runs: the other references. The Grounding DINO term was off on those boxes (comment in `glock_public.sh`).

**Accuracy on public episodes** (registered kit AUC vs mocap, our meshes):

| What | Score | Old perc2 (scans as templates, unregistered) |
|---|---|---|
| 25 Oct detection, base arm, 20 episodes (library_v2) | **0.868** [M] (work log l.3655) | 0.809 [M] (`main:STATUS.md` "What works") |
| Same, with library_v3 and the guard arm for ep0 | **0.892** [D], **0.937** without ep23 (board swap, 0.041) | |
| Track guard, 8 episodes | 0.724 → 0.782 [M] (l.3581) | |
| 10 canonical episodes: perception → final reference | 0.915 → 0.902 [M] (`refcheck/chain/README.md` §1) | |

Per-object reference accuracy [M] (chain §3):

| Object | AUC | Object | AUC |
|---|---|---|---|
| Pot | 0.922 | Sweeper | 0.952 |
| Lid | 0.974 | Dust pan | 0.948 |
| Blue cup | 0.925 | Pitcher | **0.575** |
| Beige cup | 0.905 | Boards | 0.816 |
| Rack | 0.916 | | |

## 2. Note 23's reference levers: what exists on main

**Temporal smoothing of object paths (Kalman or RTS smoother): none.**
- Only the hands are smoothed.
- At rest, our tracks move at 1.9 cm/s and 13°/s (p95), against 0.27 cm/s and 2.8°/s for mocap [M] (`refcheck/timing/README.md`).

**Snapping objects to the table: exists, and it costs us.**
- mkref's frame-0 z snap costs **−0.016** mean (ep26 −0.062, ep21 −0.056, ep12 −0.031) [M] (`refcheck/systematics/README.md`).
- The gated version (R1 / H-snap) is proposed and not tested.

**Per-frame rest settling: exists.**
- `contact_retarget --rest_settle` puts objects nobody moves onto the table and tilts them onto a stable pose (up to 15°).
- Effect on the object path: +0.004 mean (−0.007 to +0.057) [M] (chain §1).
- Earlier policy test: ep12 0.740 vs 0.790 without it, one seed [M] (work log l.1464).

**Upper bounds from oracle corrections (they use mocap, so they cannot be deployed):**
- height +0.022 on references / +0.017 on perception;
- tilt +0.016;
- all together +0.048 / +0.032 [M] (systematics).

**Deployable timing fix:** advancing our path by +0.5 frame gives +0.005 to +0.007 on references and +0.003 on rollouts [M].

**Already tried and rejected:**
- rest-averaged anchor frame 0: +0.001 [M] (work log l.3790ff);
- freezing objects no hand touches, as a general rule [M] (refcheck R5).

**Locking the hand to the object during carries: exists.** [M-new]
- In the training references (`ref_gl_ilc.parquet`) of eval 20, eval 8 and ep21, the hand frame used for rewards (C_MC) is rigid to the carried object: **0.0 mm / 0.0°** spread. In mkref's earlier output it slid 10–25 mm and turned 16–30° (median), up to 59–87 mm / 30–94° (p95).
- Contact labels are active in 100 % of hold frames.
- The wrist **target** column deliberately differs from that frame, by 1.6–3.8 cm median, because it carries the feed-forward and ILC corrections. Any audit should check the frame, not the target.
- Script: `scratchpad/nextsteps/scripts/relframe.py`.

**Reference audit:**
- `pipeline/audit_ref.py` exists only on this branch.
- Main has partial checks: `qa.py ref`, `ref_report` WRIST-JUMP, `tools/hull_census.py`, and the refcheck timing tools.

**Other note-23 levers on main:**
- kp ≥ 100: done for the grasp-lock learner (kp 400). The standard learner, used for evals 1, 19, 25, 28 and 30, runs at kp 25 (`main:ops/jobs/hard_ab.sh`).
- Ball-wrist damping: not applied; the kp 400 config keeps the rotation drive at kp 25 / kd 6.

## 3. Pours: eval 20 and eval 8, public twins ep21 and ep22

**Hand gaps** [M-new, from stored `mkref_log.txt` and `hands_log.txt`]:

| Episode | Right-hand invalid frames | How it is filled |
|---|---|---|
| ep21 (public twin) | 42–98 (56 frames, 2.8 s) | both ends attached to the pitcher |
| eval 20 | **27–107 (80 frames, 4.0 s)** | both ends attached to the pitcher |
| eval 8 | none (both hands valid 218/219) | — |

- These gaps are longer than note 23's raw-detection runs of 34 and 30 frames.
- In eval 20 the grasp lock then holds the pitcher in the right hand from frame 20 to 146 as one hold (grasp frame 34, inside the gap) and the cup in the left hand from frame 0 to 159 (`ref_gl_grasp_lock.json`).
- Measured cost of an untracked hand on the object path: about 0.003 AUC (object ADD 1.67 vs 1.21 cm) [M] (timing §5).
- **Conclusion: the gap is handled. It is not the eval-20 lever.**

**Twin ep21 history** [M] (work log l.3951–3953 and l.4357):

| Step | Registered AUC vs mocap |
|---|---|
| Base (no arc foot) | 0.657 ± 0.093 |
| Arc foot (pitcher stands) | 0.772 ± 0.009 |
| Same rollouts, lathe pitcher mesh | 0.874 |

- The lathe pitcher cost −0.0045 on Kaggle (pack 5) and was reverted in pack 6. Its registration is unstable in yaw: −14° to +7° over 30 seeds [M].

**Current scores:**
- eval 20: packed sim_vs_ref 0.8948, mean over 5 evaluations 0.8923;
- eval 8: packed 0.9783, mean 0.9705.
- Sources: `main:results/submissions/20261026-track3f/summary.txt` and the stored `best/summary.json`.

**Where eval 20 loses, which our sim_vs_ref cannot see:**
- The twin reference scores 0.778, the pitcher alone 0.575.
- About half is the blue cup's registration: it is slot 0 and sits about 1 cm off along its axis. The other half is the pitcher's own registration: 2.65–3.19° and 0.65 cm [M] (chain §2).
- The pitcher is the rotation anchor, and its frame-0 tilt is 5.7–6°. The tilt oracle is worth +0.110 on ep21 [M].
- mkref's snap lifted the twin's pitcher 0.93 cm, costing −0.112 on the pitcher [M]. The eval-20 reference got the **same +1.00 cm pitcher snap** [M-new].

## 4. Spoon and other perception problems still open

**Spoon (10 of 20 eval episodes; it anchors the scene in 32, 33, 35, 36 and 37):**
- Implied accuracy about 0.80–0.81 [E]; corrected to 0.73–0.76 [E] (refcheck §3).
- Frame-0 roll noise of 2–6° costs about 0.03–0.15 per anchored episode [E].
- Registration flips: 0 of 300 [M].
- Frame-0 video overlays agree with the real spoon [doc].
- Phases where the spoon is hidden inside the pot or cup (3, 5, 6, 33) cannot be measured.
- The proxy measurement H2 is still pending (`main:STATUS.md` 27 Oct).

**Other open problems:**
- R3: the submitted sweeper flips at Kaggle's seeds for eval 30 (3 of 24 stand-in hosts) and eval 19 (4 of 24); about −0.034 each.
- ep23 board identity swap; identity_fix is not a default step.
- R5: the ep11 blue cup drifts 5.4 cm in our track (affects evals 10 and 8).
- Eval 33 reference about 0.62 ± 0.15 [E].
- GPU nondeterminism: two perception runs named eval 25's boards oppositely.
- Only 10 of 20 public episodes have a reference, and ep22 is missing one.
- The mesh review panel's wall-hole defects (blue cup, pot, rack, beige cup, pitcher) were found on the mesh branch: `origin/claude/bold-albattani-6qmxsv:docs/work-log.md` l.4429ff.

**Census of mkref snap shifts on the eval references** [M-new; relative shifts are what get scored]:
- racks +0.83 to +1.12 cm in evals 14, 15, 16, 28, 30;
- pitcher +1.00 cm in eval 20;
- boards +0.93 / +1.22 cm in eval 25;
- everything else 0.5 cm or less.

## 5. CPU experiments on saved data ($0)

**What is saved in the HF store `aebatirel/v2d-store`:**
- `cache/depth/public/ep*/depths_fs0.5.npy`: depth for all 20 public episodes, 33.6 GB. There is **no eval depth**.
- `runs/20261025-sweep-a894083`: perception for 20 public episodes × 3 variants (`poses.npz`, `poses_world_vo.npz`, `det_f0.npz`, `per_frame.npz`, `score_registered.json`).
- `runs/20261025-guard-fe3f407`: the 8-episode guard arm.
- `runs/20261025-evperc-4f596df`: perception for all 20 eval episodes, plus `track_guard.json`.
- References with `hands.npz`, `e2s_reference.parquet`, `table_frame.npz`, mkref logs and the grasp-lock parquet:
  - the 10 canonical public episodes, with rollouts r1–r5 (`refcheck/resolve/canonical_refs.json`);
  - every eval episode (runs `evb0810`, `evb1420`, `evb3233`, `evA`–`G`, …).

**Tools in the repo:** `pipeline/score_registered.py`, `refcheck/{chain,systematics,timing}/*.py` (including `ref2npz.py` and `fixed_shift.py`), and `tools/sim_settle.py`. The earlier refcheck ran 146 scoring jobs in 1.5 CPU-hours.

**Proposed experiments, in priority order:**

1. **Gated snap (R1), plus a check of the table plane under the pitcher (H3).**
   - Rebuild the object paths of the 10 canonical references with a snap that skips objects resting on other objects or sitting above the lowest object. Score lib and scan.
   - Fit separate depth planes under the pitcher and under the cup on ep21/ep22 depth.
   - Falsified if: the ep26 pot stays below 0.93, the mean does not rise, or the two planes agree within 0.3 cm.
   - Eval episodes exposed: 20, 28, 1, 14, and the five rack episodes.
2. **Offline robust SE(3) smoother** (note 23 lever 3; Student-t smoother, holds only where our own speed says "rest", ± the +0.5-frame advance).
   - Run on the 20 sweep-base and 8 guard tracks.
   - Falsified if: the mean gain is +0.005 or less, or more than a third of episodes get worse.
   - My prior: small [E], because the losses are dominated by bias.
3. **Settle the anchor's frame-0 orientation (R2 / H-anchor).**
   - Snap only the tilt, onto a stable pose, on the 20 public tracks.
   - Caveat: our pitcher mesh's base axis is 38° off its observed rest. Use the arc-foot geometry for the pitcher, not the raw mesh.
4. **Run `audit_ref.py` standalone** on the 20 packed eval references and the 10 public ones.
   - Check the C_MC frames, not the wrist targets.
   - Rank its flags against the per-episode sim_vs_ref of pack 6 (10, 32, 20, 16, 25).
5. **Spoon proxy (H2).** Frame-0 roll and tilt error of the sweeper and dust-pan handles against mocap, from the stored tracks.
6. **Mesh branch's per-frame refinement as pose corrections.** Apply `autokit/refine.py` corrections, built from the public depth caches, to the object paths and score them. Falsified if the gain is +0.005 or less.

**GPU costs for the perception side:**

| Item | Cost |
|---|---|
| Perception on 20 public episodes | ≈ $3.7 measured (3 variants) |
| Eval perception | ≈ $1.9 measured |
| Eval depth cache | ≈ $2–4 [E] |
| Perception repeatability check (H1) | ≈ $3 [E] |
| Retraining each changed episode | ≈ $2–3 [E] |

The credit is currently $3.52 (STATUS).

**Would a better mesh help?**
- Tracking with exact scan templates scored 0.966–1.000, against 0.87–0.96 with our meshes on the same episodes [M] (chain §4). Registration costs us −0.19 to −0.24 on the pitcher [M]. So yes.
- But swapping only the submitted mesh can backfire: pack 5 lost −0.0045, because our tracks had absorbed the old mesh's bias.
- A new mesh has to go through re-tracking, a registration-stability gate and retraining.

Files are in `/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/nextsteps/`:
- `store_dl/`
- `scripts/relpose.py`
- `scripts/relframe.py`