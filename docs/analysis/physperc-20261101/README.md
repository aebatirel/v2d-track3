# Physics as a second sensor for perception (KURSAD perception half), public episodes, 1 Nov 2026

Session physics-perception (branch `claude/physics-perception-20261101`), owner's ask: "attempt to correct the
perception with the help of physics". CPU only (this container), **$0**. 20 public episodes only.

Labels: [M] measured, [D] measured on public data against mocap (development), [E] estimate, [H] hypothesis.
Mocap is read only by the scorer (`pipeline/score_registered.py`) and by the scripts named `d*` / `o1_oracle.py`
(diagnostics and oracles, never inputs to a transform). Every gated test was pre-registered and pushed before scoring.

## Bottom line
- **No test passed its pre-registered gate.** Gate: mean ΔAUC ≥ +0.003 over 20 episodes, no episode < −0.010, mean
  MPPE and RPE not worse.
- **Best result:** the stack F1P1 gives **+0.00298**.
  - It combines the physics-fused anchor tilt (P1) with "resting objects do not float" (F1).
  - 14 episodes better, 0 worse, min 0.0000; MPPE −0.028 cm, RPE −0.011 cm.
  - Bootstrap 95 % CI over episodes: [+0.0008, +0.0059].
  - It misses the mean clause by 0.00002, and is not rounded into a pass.
  - Nothing was handed to the perfect-following session as a pass.
- **Physics is a real second sensor, but a weak one** on our meshes.
  - Tilt: a stable facet of our mesh is about as accurate as the tracker (~2°).
  - Fusing the two beats either alone. Snapping to the prior (what refine.py S3 did) does not.
  - The scored effect is small: the ceiling for an exact anchor tilt is +0.016, and 70 % of that sits in two pitcher
    episodes whose mesh lacks half its base.
- **The biggest physics-observable bias is the pitcher anchor's systematic 6° tilt** (ep21 / ep22): about +0.012 public
  mean at most [D, oracle]. No GT-free prior from our meshes recovers it. It needs a complete-base pitcher geometry.
- **Useful by-product: `scripts/qa_physics.py`**, a GT-free physics audit.
  - On public it flags both catastrophic track failures (ep0 lid under the table; ep23 board swap) and one false
    positive.
  - Offered to perfect-following as a read-only QA of eval references.

## Results table (all [D], 20 public episodes, vs `runs/before`, which equals posefix runs/before 20 / 20)
| test | rule (GT-free) | ΔAUC mean | better / worse | min | ΔMPPE / ΔRPE cm | gate |
|---|---|---|---|---|---|---|
| T1 P1 | fused frame-0 tilt of the scorer anchor: slerp(tracker down, nearest stable facet of our 9a+ mesh on our depth table, 0.5), one body-frame correction | +0.00156 | 13 / 0 | 0.0000 | −0.013 / −0.007 | fail (mean) |
| T1 P2 | same, every gated object | +0.00132 | 13 / 3 | −0.0016 | −0.011 / −0.034 | fail (mean) |
| T1 R1 | snap W = 1, anchor (S3-like control) | +0.00031 | 9 / 4 | −0.0115 | +0.005 / −0.004 | report |
| T2 Q1 | revolution-axis prior (W 0.75) else facet, all gated | +0.00067 | 11 / 3 | −0.0029 | −0.004 / −0.028 | fail; falsifier fired |
| T2 Q2 | same, anchor only | +0.00091 | 11 / 1 | −0.0007 | −0.007 / −0.003 | fail (mean) |
| T2 R2 | axis W 1.0, all | +0.00031 | 11 / 4 | −0.0041 | +0.002 / −0.029 | report |
| T3 F1 | resting objects do not float: static, low, unsupported, hand-free runs lowered to our table | +0.00142 | 2 / 0 | 0.0000 | −0.015 / −0.003 | fail (mean) |
| **T3 F1P1** | P1 then F1 | **+0.00298** | **14 / 0** | 0.0000 | −0.028 / −0.011 | **fail (mean, by 0.00002)** |
| W1 (idea 3) | GRASP twist_canon (41383b4), palm-frame holds, 5 cup episodes | ep11 −0.0084, ep21 −0.003 | | | | twist vs mocap worse 5 / 6: falsified |
| W2 (idea 3) | rest-only twist hold (exploratory, not pre-registered) | ±0.0003 (neutral) | | | | twist vs mocap better 6 / 6 |

Earlier public tests of the same ideas, not repeated:
- refine.py S3, tilt-to-plane snap + prefix mean (ideas 1 + 2): −0.0013;
- S4 pre-contact hold: +0.0003;
- rest-hold: +0.001;
- static hold: +0.004, failing no-harm;
- hand-coupled hold: −0.018.

## Diagnostics and oracles (mocap)
- **D1 (`diag/d1_tilt_9a.json`).** Per object at f0, tilt error vs the truth:
  - Tracker vs stable-facet prior: about 2° each.
  - The prior is wrong where the object does not sit on a facet of our mesh: dust pan 13°, pitcher 60°, ep31 sweeper
    10°.
  - Fusion error by weight W, on 14 gated anchors: 1.96 / 1.56 / 1.78° for W = 0 / 0.5 / 1.
- **D2 (`diag/d2_axis.json`).** Revolution-axis prior (line-complex fit of our mesh): tilt error on 17 objects
  2.47 → 0.89° (W = 1). It does not reach the score (T2).
- **O1 (`diag/o1_tilt_oracle.json`).** Exact anchor tilt relative to our table: **+0.0164**.
  - ep21 +0.135 and ep22 +0.098 (pitcher).
  - ep24 +0.050, ep18 +0.029, ep12 +0.017.
  - Without the pitcher episodes, about +0.004.
- **D3 (`scripts/d3_pitcher*.py`).** No usable pitcher prior: v3 stable / contact facets 64 / 32° off; candidate
  meshes 6–10° off, against the tracker's 6.1–6.3°.
- **D4 (`diag/d4_offset*.json`).** Constant translation offset after the kit alignment:
  - **+0.030** (vertical +0.019, along the f0 camera ray +0.020, lateral +0.009, overlapping);
  - +0.0195 after the tilt oracle;
  - concentrated in ep24 (+0.099), ep31 (+0.061) and ep11 (+0.060). Our big offsets lie along the viewing ray.
- **D5 (`diag/d5_float.json`).** 10 "floating, no hand, no support" runs:
  - 7 are real holds that MediaPipe missed (54–280 mm high);
  - 3 are false floats, 16–23 mm high and static;
  - the scans rest 0–2 mm above the table at f0 in every episode.
- **D7 (`scripts/d7_twist.py`).** The tracker observes cup twist well on several cups (2–5° mean error).

## What it would be worth on the board [E]
- Perception changes reach the board only through rebuilt references and retrained policies. Measured transfer for
  S2 is about 0.74 of a sim_vs_ref gain.
- F1P1 is therefore about **+0.002 board AUC** [E], and only after retraining every affected eval policy
  (~$3–6 each [E]). That is not worth the GPU spend unless it rides along with retrains that happen anyway.
- P1 alone touches the anchor of most episodes, so it would need all of them retrained.
- The pitcher fix would be worth up to about +0.01 on public perception [D, oracle]. Its board value depends on which
  eval episodes use the pitcher as anchor; not checked here (eval is out of scope).

## What to test next
1. **A complete-base pitcher** [H], as the tracker template or as the rest prior.
   - Route: SAM 3D / Pixal3D lid-off-style generation of the pitcher, aligned to the v3 frame.
   - Gate: D1-style tilt error on ep21 / 22 below 3°, then a T1-style public gate.
   - GPU ≈ $1–3 [E] for generation. No retrain is needed to test on public.
2. **qa_physics on the eval base tracks** (perfect-following, $0): flagged episodes are re-detection candidates.
3. **Re-detection at f0 for flagged failures** (ep0 lid class): GPU tracker re-run, ≈ $1–2 per episode [E].
   - Public falsifier: ep0 lid AUC 0 → > 0.5 after re-detection.
4. **If references are rebuilt anyway:** add F1P1 (+0.003 public, never negative) and W2 (twist, AUC-neutral) at the
   object-track stage, before guard_bridge. That is the owner's call, since F1P1 misses the gate by 0.00002.

## Run record
- **Machine:** this cloud container (4 cores), CPU, $0.
- **Inputs (all GT-free for transforms):**
  - tracks: HF store `runs/20261025-sweep-a894083`, sha256 equal to posefix `inputs.json` 20 / 20;
  - hands and episode bundles (table plane from frame-0 depth): `runs/mesh-20261031-b4ext4-b61e8aa`, hands sha256
    equal 20 / 20;
  - 9a+ meshes: md5 equal;
  - scoring inputs (parquets, scans): `nvidia/video_to_data_challenge`, sha256 equal to posefix
    `t3_inputs_sha256.txt`;
  - kit: the organisers' zip.
- **Code:** `scripts/`.
  - `stage.py`: tracks to world poses.
  - `score.sh`: scorer loop.
  - `pp_tilt.py`: T1 / T2.
  - `pp_drop.py`: T3.
  - `pp_twist*.py`: W1 / W2.
  - `qa_physics.py`.
  - `compare.py`: gate.
  - `physlib.py`.
- **Commits:**

  | step | commit |
  |---|---|
  | PREREG T1 | 66d31116 |
  | T1 sha | 23af20cc |
  | PREREG T2 | 56c05c6e |
  | T2 sha | ac36ee29 |
  | PREREG T3 | 46268f69 |
  | T3 sha + scores | 770e4b60 |

- **Outputs:**
  - `runs/<arm>/ep<e>.json`: scorer;
  - `results_T{1,2,3}.json`;
  - `bootstrap_ci.json`;
  - `transform/<arm>/`: per-episode transform logs;
  - `out_sha256/`.
- Transformed tracks are regenerable from the commands above and are not in git.
