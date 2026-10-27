# VERIFY: independent check of refcheck/timing (27 Oct 2026)

Check name: `verify_timing`. I tried to refute the timing check (`README.md` here). My own code is in
`../verify_timing/` and my scratch is in `$SP/work/verify_timing/`. I did not import or re-run `timing.py`, `cost.py`
or `../systematics`.

Labels:
- **[M]** measured here, with the command given in the last section.
- **[doc]** read from a file or a note.
- **[H]** a hypothesis, with the experiment that would falsify it.

Run on CPU only. Every scoring call was the official `pipeline/score_registered.py`, run one at a time. No commit, no
push, no GPU, no Vast, no Kaggle. The repo HEAD is now e2f0a6b. `score_registered.py`, `perc2.py` and `grasp_lock.py`
are unchanged since 8724a24, the HEAD the timing check ran on.

## Verdict: partly confirmed

- **The lag is real and reproduces [M].**
  - Our object path is about half a frame late. I find +0.53 frames by my own threshold crossings and +0.47 by a
    curve fit that uses no threshold.
  - The lag is the same in perception, mkref output and the final reference, and the same for 2, 4 or 8 tracker
    iterations.
  - It does not drift within an episode.
- **The false-motion numbers reproduce [M].** These are the ep11 blue cup (including the +0.069 freeze oracle), the
  ep24 board-2 creep, the ep31 sweeper, the grasp-lock anchors and the ep18 E2S late hand.
- **The cost attribution is refuted in large part [M].** "Advancing by 0.545 frames gives +0.0055 / +0.0068" is
  measured correctly, and I reproduce it exactly. But most of that gain is not timing.
  - The kit aligns the scene **once, at frame 0**, on the frame-0 orientation of one object
    (`track3_pose._align_registered_scene`).
  - Our frame-0 orientation is an outlier: about twice the error of the tracked frames.
  - Shifting the path changes frame 0, so it changes the alignment of the whole episode.
  - With frame 0 held fixed, the pure timing advance gains **+0.0027 (perc, 18/19) and +0.0034 (ref, 10/10)**.
    That is about half the claimed gain.
  - The remaining +0.0023 / +0.0030 is a per-episode alignment lottery: −0.006 to +0.020, driven by ep18, ep31 and
    ep39.
  - The stored-rollout proxy behaves the same way: ep21's +0.019 is about +0.004 timing.
- **One key number rests on a filtered sample [M].** "Sim − ref −0.28 frames, IQR ±1, 36 pairs" uses only pairs
  within ±3 frames. 28 of 67 pairs have the simulated object moving more than 3 (up to 77) frames **early**.
- **H1 already has prior evidence [doc].** Note 20 (§A6, 6 Oct) measured from image motion that GT row k sits about
  25 ms after cam b/c frame k (n = 5–6). Perception uses that mono pair. The timing check does not cite this.

## 1. Re-derived numbers

### 1a. Onset lag [M] (`vt_lag.py` → `../verify_timing/vt_lag.json`)

Differences from their method:
- Tracked point: mine is OUR mesh's own surface centroid; theirs is the kit registration anchor.
- Rest pose: mean of frames 0–4; theirs is the median.
- Rotation: cups use the swing of the vertex-PCA axis.
- I add a threshold-free estimator: a least-squares shift τ with free amplitude, d_ours(t) ≈ k·d_gt(t−τ), over frames
  t_gt−10 to t_gt+25.

| quantity | theirs | mine |
|---|---|---|
| perc 1 cm onset lag, median (25 objects, ep23 excluded) | +0.54 [+0.28, +0.65], 22/25 within ±1 | **+0.525 [+0.31, +0.73], 22/25** |
| perc 2 cm / 10° | +0.54 / +0.46 | +0.49 / +0.55 |
| pre 1 cm / 2 cm / 10° (14 objects) | +0.59 / +0.59 / +0.54 | +0.54 / +0.57 / +0.54 |
| ref 1 cm / 2 cm / 10° (14 objects) | +0.59 / +0.59 / +0.44 | +0.52 / +0.57 / +0.44 |
| pooled perc crossings with \|lag\| ≤ 3 | 0.545 (n = 70) | 0.537 (n = 70) |
| threshold-free τ, perc / pre / ref | – | **+0.47 / +0.47 / +0.47** (25 / 14 / 14 objects; mean 0.45 ± 0.07 se) |
| sweep base / t4 / t8 (TRACK_ITERS 2 / 4 / 8) | +0.546 / +0.558 / +0.551; paired −0.003 / −0.001 (n = 67) | +0.560 / +0.557 / +0.553; paired −0.004 / +0.002 (n = 67) |
| lag vs onset frame (drift) | systematics: −0.11 ± 0.03 frames per 100 frames | +0.09 frames per 100 frames, r = 0.06 (n = 23) |

Two notes:
- mkref copies the perception path through a rigid transform; `../resolve` measured this to 0.001 mm. So "mkref adds
  no lag" holds by construction. Contact retarget's rest settle changes the lag only in ep18 (sweeper +0.53 → +0.31,
  pan +0.91 → +0.65) and the ep11 beige cup (+0.45 → +0.40).
- The t8 arm is `REG_ITERS=10,TRACK_ITERS=8` (sweep `job.log`), not only TRACK_ITERS. This does not change the
  conclusion.

### 1b. Offset lag [M] (`vt_offset.py`)

| quantity | theirs | mine |
|---|---|---|
| perc 1 cm offset, median [IQR] | +1.30 [−0.18, +2.38] | +1.26 [+0.43, +2.38] |
| ref 1 cm offset | −0.08 [−2.11, +3.46] | +0.76 [−2.08, +3.74] |
| early settling created by rest settle, ref (perc) | ep2 pot −7.7 (+0.9), ep26 pot −4.2 (+1.5), ep18 pan −3.1 (+0.6) | −7.67 (+1.04), −4.11 (+1.60), −3.13 (+0.50); also ep39 pan −2.53 (+1.57) |
| late tails, 1 cm | ep11 beige +17, ep13 cup +28, ep24 board 1 +30, ep31 sweeper +33 | +16.8, +27.5, +29.3, +33.1. At 2 cm they shrink to +3.3, +43 (ep13), +0.15, +1.3, so they are 1 cm jitter |

The ref median differs (+0.76 against −0.08). With 14 values in two clusters the median is unstable. Per object we
agree.

### 1c. False motion of resting objects [M] (`vt_checks.py` → `vt_checks.json`)

| item | theirs | mine |
|---|---|---|
| ep11 blue cup, mocap max displacement | 0.49 cm | 0.50 cm (2.2°) |
| ep11 blue cup, ours | 5.4 cm from f43, 75 frames > 1 cm | 5.41 (perc) / 5.38 (ref) cm, peak f67. Ours steps to about 1 cm at f43, hovers there, then jumps f63–67 when the beige cup is stacked. Ours puts the cups 1.5–2 cm apart, mocap 4–5 cm. 75 frames > 1 cm (ref, median rest); 83 with my mean rest |
| ep11 freeze blue cup (oracle) | +0.069 (0.8964 → 0.9653) | **+0.0694 (0.8964 → 0.9658)**, official scorer. Blue cup 0.862 → 1.0, beige 0.931 → 0.932 |
| ep24 board 2 creep | 2.7 cm from f39, 72 frames, true onset f111 | 2.73 cm, first 3-frame 1 cm crossing f38.0, 74 frames > 1 cm before onset, my true onset f112 |
| ep31 sweeper early | 1.8 cm / 17° before onset f35, 1 cm at f26 | 1.66–1.67 cm / 16.8–17.5°, 1 cm at f25.5, my onset f36 |
| ep31 rack (static) | ref 1.8 cm / 82 frames, perc 1.2 cm | ref 1.70 cm / 80 frames, perc 1.14 cm |
| ep13 cup tail | 3.1 cm / 13.5°, 22 frames | 2.7 cm, 11 frames (different end-rest definition) |
| ep11 beige f0 → f1 | spin 17–22°, swing 3.4° | full rotation f0 → f1 **17.35°** (21.9° from f0 by f4), swing 4.7° (my axis), mocap 0.02° |
| grasp-lock anchors (`ref_gl_grasp_lock.json`, read by me) | ep24 board 2 hold f29 / anchor f39; ep31 sweeper anchor f24 (−21); ep11 beige anchor f1; blue cup f33, hold f23 | identical in the stored JSONs. The rule (`grasp_lock.py` l. 206–212) uses the full rotation from the frame-`pe` pose, 8°, so cup spin counts |

### 1d. Hands [M] (`vt_hand.py` → `vt_hand.json`; 15 probe sites + palm centre, both hands, OUR mesh, 2 cm)

| item | theirs | mine |
|---|---|---|
| ep18 sweeper, pre (E2S) | −28 (hovers 2.1–3.5 cm) | **−28**; hand 2.0–3.1 cm from it over f31–58 |
| ep18 sweeper / pan, ref | +3 / +4 | +5 / +5 |
| ep2 lid, ref: lead / unheld moving frames | +3 / 20 | +4 / 22 of 114 moving frames |
| ep26 pot ref / ep39 pan ref | +12 / +11 | +11 / +11 |
| ep21 right hand invalid during pitcher motion | 56 of 76 | 56 (run f42–97 in `mkref_log.txt`) inside the true window f35–110 |
| guard interventions (guard arm, 8 episodes) | only ep23 board 1 and the ep0 lid f0 retry | identical (`track_guard.json` of all 8) |

Caution: the guard arm is 8 episodes. Most canonical perceptions (ep2, 12, 18, 24, 26, 27, 39) ran **without** the
guard, so this is not a statement about the canonical tracks.

### 1e. Noise floor [M]

- Theirs, mocap rest p95: 0.27 cm/s (max 0.55) and 2.8 deg/s (max 6.8), with a σ = 1 smoothed derivative.
- Mine, raw central difference, rest = ≥ 5 frames from any motion, 33 objects: 0.35 cm/s (max 0.78) and 3.0 deg/s
  (max 7.3).
- They agree, given the smoothing.

## 2. Classic errors checked

| suspected error | result |
|---|---|
| quaternion order | Mocap w-first is right: a resting cup's axis is vertical with w-first, \|axis·z\| = 0.999–1.000 in 6 cup episodes, and 0.29–0.76 if read as xyzw (`vt_quat.py`). (The beige cup is degenerate for this test.) Reference `object_body_wxyz` is right: R_ref·R_percᵀ is constant within 0.0–0.05°, and in ep39 within 4.8°, from rest settle. Note: angles from frame 0 cannot test the order, because a fixed permutation leaves them unchanged. I first used that test and discarded it |
| frame origins | Lags use displacement and rotation from each source's own rest, which no world transform changes. My tracked point (our mesh centroid, not the kit anchor) gives the same lags |
| wrong run / copy | My paths come from `canonical_refs.json`; I parsed the mesh library from its text field myself. The official-scorer bases equal theirs exactly in 19/19 perception and 10/10 reference episodes (section 3) |
| mesh library (v2 / v3 / v3x) | Same mapping as theirs; ep18 uses perc v2 and ref v3. Each score used that source's library |
| frame indexing / off-by-one | `frame_index` = 0..T−1 in every parquet. Perception, pre and ref have exactly the mocap row count in all 20 / 10 episodes. Video-vs-mocap clock: section 4 |
| per-object vs per-episode averaging | Lags are per object (25 / 14). Costs are per-episode registered AUC means, as stated |
| symmetric objects | Cups use swing for crossings. **The grasp-lock anchor does not**, which confirms their H2 premise |
| selection bias | 1. The "sim − ref −0.28" number: 38 of 67 pairs are within ±3 frames, median −0.34 (mine). 28 pairs are < −3 frames: ep2 pot −56 to −77, lid −49, ep11 beige −20, ep26 pot −47, ep24 board 2 about −15, ep31 sweeper −2 to −8, ep12 cup in 2/5 rollouts −8 / −12. 2. The headline AUC means cover all episodes (19 / 10), so they are fine |
| claims without measurement | "Contact retarget adds no lag": measured and true, but trivial for mkref. "Not tracker under-convergence": measured. The 0.003 occlusion figure is labelled derived. I did not re-derive it |

## 3. The cost numbers: mostly frame-0 alignment, not timing [M]

The mechanism, read from the kit:
- `_align_registered_scene` takes one world rotation from the frame-0 orientation of the first object without a
  symmetry axis. The pot, rack, sweeper, dust pan and boards qualify; with two cups it uses object 0's axis and the
  direction to object 1.
- It takes the offset from object 0's frame-0 centre.
- Any operation that changes our frame 0 therefore rotates and translates the whole episode.

Our frame 0 is special:
- It is the FoundationPose `register` output. Every later frame comes from `track_one` (`perc2.py` l. 461 / 473).
- Orientation deviation from the mean of frames 5–15 (29 objects at rest at the start, `vt_checks`-style ad-hoc run):

  | frame | 0 | 1 | 2 | 3 | 4 |
  |---|---|---|---|---|---|
  | median (°) | **1.07** | 0.54 | 0.48 | 0.44 | 0.49 |
  | mean (°) | **2.77** | 1.60 | 1.42 | 1.30 | 1.13 |

- Position deviation is not elevated: 1.04 mm at frame 0 against 0.97–1.18 mm at frames 1–4.
- Mocap's frame-0 → frame-1 change is about 0.01°.

Decomposition with the official scorer. My variants (`vt_shift.py`):
- `sp545`: their operation, a linear-interpolated advance of 0.545 frames, frame 0 included.
- `k0sp545`: the same with frame 0 restored, so the alignment is identical to the base.
- `k0fsh545`: a band-limited (FFT, pure phase) advance with frame 0 restored. This is pure timing, with no smoothing
  and no alignment change.
- `k0fsm545`: zero-phase smoothing with exactly the magnitude response of the linear interpolation, frame 0
  restored. I checked that linear = fsmooth ∘ fshift to 0.2 mm / 0.12°.

Results:
- All 29 sources were scored with the official scorer (`../verify_timing/vt_scores.json`).
- Base and `sp545` equal the timing check's `cost.json` **exactly in 29 of 29**. The measurement itself is right.

| ep:src | base (= theirs) | sp545 (= theirs) | k0sp545 | k0fsh545 (pure timing) | k0fsm545 (pure smoothing) | alignment part (sp545 − k0sp545) |
|---|---|---|---|---|---|---|
| 0:perc | 0.9641 | +0.0031 | +0.0031 | +0.0029 | +0.0001 | +0.0000 |
| 2:perc | 0.9866 | +0.0045 | +0.0026 | +0.0020 | +0.0003 | +0.0019 |
| 2:ref | 0.9798 | +0.0037 | +0.0031 | +0.0029 | +0.0006 | +0.0006 |
| 11:perc | 0.8964 | +0.0039 | +0.0039 | +0.0030 | +0.0021 | +0.0000 |
| 11:ref | 0.8844 | +0.0127 | +0.0123 | +0.0111 | +0.0015 | +0.0004 |
| 12:perc | 0.9662 | +0.0101 | +0.0079 | +0.0065 | −0.0004 | +0.0022 |
| 12:ref | 0.9354 | +0.0109 | +0.0080 | +0.0066 | −0.0005 | +0.0029 |
| 13:perc | 0.9605 | +0.0043 | +0.0033 | +0.0025 | +0.0027 | +0.0010 |
| 18:perc | 0.9380 | **+0.0216** | +0.0026 | +0.0014 | −0.0001 | **+0.0190** |
| 18:ref | 0.9657 | +0.0024 | +0.0014 | +0.0012 | +0.0006 | +0.0010 |
| 21:perc | 0.8372 | +0.0035 | +0.0010 | −0.0003 | +0.0007 | +0.0025 |
| 21:ref | 0.7776 | +0.0031 | +0.0005 | +0.0005 | −0.0016 | +0.0026 |
| 22:perc | 0.8710 | −0.0006 | +0.0017 | +0.0017 | +0.0005 | −0.0023 |
| 24:perc | 0.8117 | −0.0026 | +0.0011 | +0.0027 | −0.0003 | −0.0037 |
| 24:ref | 0.8163 | −0.0036 | +0.0021 | +0.0032 | −0.0019 | −0.0057 |
| 26:perc | 0.9723 | +0.0022 | +0.0059 | +0.0050 | +0.0016 | −0.0037 |
| 26:ref | 0.9229 | +0.0008 | +0.0033 | +0.0012 | +0.0027 | −0.0025 |
| 27:perc | 0.9593 | +0.0026 | +0.0008 | +0.0008 | +0.0000 | +0.0018 |
| 27:ref | 0.9621 | +0.0023 | +0.0019 | +0.0016 | +0.0007 | +0.0004 |
| 31:perc | 0.7998 | **+0.0222** | +0.0019 | +0.0022 | +0.0004 | **+0.0203** |
| 31:ref | 0.8233 | **+0.0214** | +0.0020 | +0.0028 | +0.0005 | **+0.0194** |
| 39:perc | 0.9602 | **+0.0157** | +0.0051 | +0.0036 | +0.0020 | **+0.0106** |
| 39:ref | 0.9559 | **+0.0147** | +0.0033 | +0.0026 | +0.0008 | **+0.0114** |
| 40:perc | 0.9570 | +0.0014 | +0.0009 | +0.0007 | −0.0017 | +0.0005 |
| 41:perc | 0.9910 | +0.0017 | +0.0017 | +0.0013 | +0.0004 | +0.0000 |
| 42:perc | 0.9915 | +0.0075 | +0.0078 | +0.0075 | −0.0003 | −0.0003 |
| 43:perc | 0.9482 | −0.0003 | +0.0033 | +0.0029 | +0.0006 | −0.0036 |
| 44:perc | 0.9967 | +0.0003 | +0.0015 | +0.0015 | +0.0008 | −0.0012 |
| 45:perc | 0.9795 | +0.0028 | +0.0033 | +0.0028 | −0.0002 | −0.0005 |

| mean Δ (episodes improved) | sp545 (their operation) | k0sp545 | **k0fsh545 = timing** | k0fsm545 | alignment part |
|---|---|---|---|---|---|
| perc (19 episodes, ep23 excluded) | +0.0055 (16) | +0.0031 (19) | **+0.0027 (18)** | +0.0005 (12) | +0.0023 (> 0 in 9, range −0.0037 to +0.0203) |
| ref (10 episodes) | +0.0068 (9) | +0.0038 (10) | **+0.0034 (10)** | +0.0003 (7) | +0.0030 (> 0 in 8, range −0.0057 to +0.0194) |

Reading:
- The timing effect is real, consistent and about half the stated size: **+0.0027 perc and +0.0034 ref**, and
  positive in 18 of 19 and 10 of 10 episodes.
- The other half is a change of the frame-0 alignment. It is large in ep18, ep31 and ep39, and negative in ep22,
  ep24, ep26 and ep43.
- The "largest gains" the check quotes, ep31 +0.022, ep18 +0.022 and ep39 +0.015, are 70–90 % alignment. Their
  timing parts are +0.0022, +0.0014 and +0.0036.
- The "losses" on ep24, ep22 and ep43 are alignment too. With frame 0 fixed, timing gains there.

Supporting controls [M] (integer shifts do not smooth):

| perc | sp1 | sm1 | sp0.5 | sm0.5 | sm0.545 |
|---|---|---|---|---|---|
| ep39 | +0.0094 | −0.0319 | +0.0145 | −0.0104 | −0.0123 |
| ep12 | +0.0110 | −0.0149 | +0.0091 | −0.0059 | −0.0063 |
| ep18 | +0.0229 | −0.0199 | +0.0209 | −0.0065 | – |
| ep31 | +0.0667 | −0.0122 | +0.0177 | −0.0034 | – |
| ep21 | +0.0076 | −0.0118 | +0.0037 | −0.0044 | – |

Points from the controls:
- Retarding always loses, so the direction is right.
- ep31's integer +1 shift gains +0.067, and almost all of it is on the **static** rack (0.688 → 0.808). A time shift
  can only do that through the alignment, which ep31 takes from the sweeper's frame 0.
- Symmetric smoothing [0.25 0.5 0.25] alone gives +0.0053 on these 5 episodes, all positive. So light smoothing is a
  separate small lever, mostly through frame 0 again; k0fsm is +0.0005.

Is the alignment part a reliable, inference-legal gain? No [M]:
- Frame 0 := mean of frames 0–4 (`f0m5`, rest of the path untouched): perc +0.0005 (8 of 19 improve), ref +0.0034
  (7 of 10).
- Frame 0 := frame 1 (`f0f11`): perc +0.0043 (9 of 19), ref +0.0056 (8 of 10). Per episode it ranges from −0.011
  (ep24 ref, ep26 perc) to +0.065 (ep31 perc).
- So it is a per-episode lottery of ±0.01–0.07 from a sub-degree change at frame 0, not a fix.
- Consequence for the whole review: **any variant that changes our frame 0 can move a single episode's registered
  AUC by up to ±0.02–0.07 for reasons unrelated to its purpose.** Comparisons should hold frame 0 fixed, or report the
  frame-0 effect separately.

The sim proxy has the same confound [M] (`vt_sim.py`, the kit's `read_trajectory`):
- Base scores equal the box records: ep21 r1 0.7903; r2 0.7712 and ep39 r1/r2 0.9579/0.9575 equal theirs.

| rollout | sp545 (theirs) | k0sp545 | k0fsh545 (timing) |
|---|---|---|---|
| ep21 r1 | +0.0215 (0.8118 = theirs) | +0.0037 | +0.0037 |
| ep21 r2 | +0.0258 (0.7970 = theirs) | +0.0033 | +0.0052 |
| ep39 r1 | +0.0035 | +0.0004 | −0.0004 |
| ep39 r2 | +0.0049 | +0.0002 | −0.0010 |

- The simulated objects settle at f0 → f1 (z −0.6 to −0.9 mm, 0.1–0.5°).
- The sim's frame 0 inherits the reference's frame 0 to 0.0–0.7° (11° for the ep31 sweeper).
- So the +0.0029 sim proxy (H4) is probably mostly alignment. I re-scored only 4 of 50 rollouts; the other 46 are
  not re-measured.

Other oracles that change frame 0 carry the same confound and were not re-measured with frame 0 fixed: the
per-episode / per-object shift (+0.0077 / +0.0075) and rest-hold (+0.0054 / +0.0071, "hurts ep18 perc −0.011,
ep31 ref −0.017").

Two oracles are not affected:
- **ep11 blue-cup freeze.** Beige-cup per-object AUC moved only 0.931 → 0.932, so the +0.069 is the blue cup itself.
- **ep24 board 2.** It is not the alignment anchor; k0 gives an identical result. My pre-onset hold (frames < 111 at
  the mean of frames 0–30; an oracle, since it uses the true onset) gives **+0.0217 perc / +0.0189 ref**. That is
  more than their +0.011 to +0.014.

[H-f0] Our frame-0 orientation (the `register` output, about 2× the tracked-frame deviation) degrades the frame-0
scene alignment.
- A better frame-0 estimate would remove the lottery: for example, refine frame 0 with the tracker run backwards
  from frame 5, or re-register with more iterations.
- The plain replacements above do not do this reliably, so the frame-0 error relative to the truth is not simply the
  deviation from our own later rest.
- Falsifier (GPU): re-run perception with a backward-tracked or longer-refined frame 0 on the 19 public episodes. If
  the registered AUC does not improve on average, with frame 0 as the only change, the hypothesis is falsified.

## 4. H1 already has independent support [doc]

`docs/research/notes/20-sync-spoon-contact.md` §A6 (6 Oct):
- An image-flow method compared each camera with the projected GT motion: **lag_b = −25.2 ± 0.8 ms (n = 5)**,
  −25.1 ± 0.85 (n = 6). In words: GT row k is the pose at about t_b(k) + 25 ms, halfway between b[k] and b[k+1].
- Its practical rule: "Place inference outputs for row k at t_b(k) + 25 ms: average the b/c-based poses of frames k
  and k+1." That is the timing check's 0.5-frame advance.
- Perception tracks on the rectified c/b mono pair (`perc2.py` l. 65–70).

So the measured lag (my pure-timing τ = 0.47 frames = 23 ms) matches a camera-to-mocap clock offset found three weeks
earlier by a different method. It is not a tracker effect.

The same note flags ep21 and ep22 as possibly one frame off, with low-confidence, gate-failed segments. My lags show
no such episode: ep21 cup τ 0.61, pitcher 0.39; ep22 0.47 / 0.27.

The remaining GPU falsifier the timing check proposes (independent per-frame registration) is therefore lower value
than stated.

## 5. Problems the timing check reported: survive or not

| # | their problem | verdict | why |
|---|---|---|---|
| 1 | Systematic lag of +0.54 to +0.59 frames, the same in every stage and at every iteration count. Advance gains +0.0055 / +0.0068, rollouts +0.0029 | **lag survives; cost does not** | Lag: +0.53 (crossings) and +0.47 (threshold-free), iterations paired −0.004 / +0.002 [M]. Timing is worth **+0.0027 / +0.0034**; the rest is frame-0 alignment (section 3). The sim proxy is mostly alignment on the 4 rollouts I re-scored |
| 2 | False motion of resting objects (ep11 blue cup, ep24 board 2, ep31 sweeper, ep13 tail, ep31 rack) | **survives** | All reproduced [M]. ep13 tail: 2.7 cm / 11 frames with my end-rest definition, against 3.1 / 22. Freezing the ep11 cup gives +0.0694; holding ep24 board 2 gives +0.019 to +0.022 |
| 3 | False motion feeds the grasp-lock anchors (ep24 −82, ep31 −21) | **survives** | Stored `ref_gl_grasp_lock.json`: hold f29 / anchor f39 and anchor f24 / hold f14. Sim board 2 is about −15 frames relative to ours, and ours is −75 relative to mocap |
| 4 | The anchor counts cup spin (ep11 beige f1, blue f33) | **survives** | Rule read at `grasp_lock.py` l. 206–212. Beige f0 → f1: 17.35° full rotation, 4.7° swing (theirs 3.4°). **Addition:** the jump is our frame-0 `register` outlier (22.4° from the later rest; frames 1–4: 5.2 / 0.6 / 0.3 / 0.6°). A rest pose taken from frames ≥ 1 would also avoid it |
| 5 | Rest settle makes reference offsets early (ep2 −7.7, ep26 −4.2, ep18 −3.1) | **survives** | −7.67 / −4.11 / −3.13 [M]; ep39 −2.53 too |
| 6 | Noisy late offsets (+17 / +28 / +30 / +33) | **survives, with a caveat** | Reproduced at 1 cm. At 2 cm only ep13 stays large (+43); the others fall to +0.15 to +3.3. This is 1 cm jitter |
| 7 | E2S hand late on the ep18 sweeper (−28), fixed by contact retarget | **survives** | −28 pre, +5 ref [M]. The labels copied from pre were not checked |
| 8 | ep2 lid hand drifts off during the invisible-hand fill (20 unheld) | **survives in part** | 22 unheld moving frames [M]. The 1–11 cm drift profile and the glockt repair were not checked |
| 9 | glockt ep26 re-plan arrives 10 frames late | **not checked** | glockt hands not analysed |
| 10 | Holding hand untracked (ep21 56 / 76) and the occlusion-proxy cost of 0.003 | **56 / 76 survives; 0.003 not checked** | `mkref_log.txt` invalid run f42–97 |
| 11 | No visibility output; guard intervened only in ep23 and ep0 | **survives, but scope is narrow** | Applies to the 8-episode guard arm only. Most canonical perceptions ran without the guard |
| 12 | Release late, +23 median | **not checked independently** | My contact runs end late too (ep18 sweeper to f352), but my offset definition differs |
| – | Key number "sim − ref −0.28, IQR ±1, 36 pairs" | **selection-biased** | Only pairs within ±3 frames. 28 of 67 pairs are more than 3 (up to 77) frames early (ep2 pot / lid, ep11 beige, ep26 pot, ep24 board 2, ep31, ep12 in 2/5 rollouts) |
| – | H1 "remaining falsifier (GPU)" | **already supported** | Note 20 §A6: GT row k = t_b(k) + 25 ms (n = 5–6, different method) |

Surprises to pass on:
1. **The frame-0 alignment lottery.** It is the biggest correction to the timing check. It is also relevant to every
   other check that compares variants differing at frame 0.
2. **Smoothing.** With frame 0 fixed, smoothing is worth about 0 (+0.0005 / +0.0003). Our per-frame jitter costs
   little under this metric.
3. **The ep24 board-2 creep costs more than stated:** +0.019 to +0.022 (my hold oracle) against +0.011 to +0.014.

Integrity:
- Mocap was read only by these diagnostics.
- `hold` (uses the true onset) and `freeze` are oracles.
- `fshift`, `k0` and `f0mean` / `f0from` are GT-free operations, but I chose to test them on public data after seeing
  the decomposition. They are diagnostics, not tuned methods.
- Nothing here touches eval episodes.

## 6. Commands (cwd `../verify_timing/`; `source $SP/venv/bin/activate`; `SP=$RC = …/scratchpad/refcheck`, `W=$SP/work/verify_timing`)

```
python -I vt_lag.py $W/lag_v1.json perc pre ref                 # 6 s -> copied to vt_lag.json
python -I vt_lag.py $W/lag_sweep.json sweep_base sweep_t4 sweep_t8   # -> vt_lag_sweep.json
python -I vt_checks.py vt_checks.json                            # 6 s (false motion, spin, noise floor; its quaternion test A is uninformative, see section 2)
python -I vt_quat.py                                             # decisive quaternion-order test (stdout only)
python -I vt_offset.py vt_offset.json
python -I vt_hand.py vt_hand.json 18:mini_sweeper:pre 18:mini_sweeper:ref 18:mini_dust_pan:ref 2:white_pot_lid:ref 2:white_pot_lid:pre 26:white_pot:ref 39:mini_dust_pan:ref   # 96 s
python -I vt_simlag.py vt_simlag.json                            # 10 s
python -I vt_frame0.py vt_frame0.json
bash run_scores.sh $W/jobs1.txt ; bash run_scores.sh $W/jobs2.txt ; bash run_scores.sh $W/jobs3.txt ; bash run_scores.sh $W/jobs4.txt
bash run_sim.sh $W/simjobs.txt ; bash run_scores.sh $W/jobs5.txt
#   each job: python -I vt_shift.py EP SRC VARIANT $W/scores/epEP_SRC_TAG.npz   (or vt_sim.py ROLLOUT EP VARIANT ...)
#             python -I /home/user/v2d-track3/pipeline/score_registered.py EP that.npz --meshes meshes/LIB --t3 $SP/t3 \
#                    --kit $SP/kit/v2d_submission_kit --out ....json [--per_frame ....pf.npz]
#   strictly sequential, 04:33-05:19 UTC, 0 failures (logs $W/jobs*.log, $W/simjobs.log)
python -I vt_summarize.py vt_scores.json                         # tabulates every score, compares with ../timing/cost.json
```

Outputs, all under `../verify_timing/`:
- `vt_lag.json`, `vt_lag_sweep.json`, `vt_offset.json`, `vt_checks.json`, `vt_hand.json`, `vt_simlag.json`,
  `vt_frame0.json`, `vt_scores.json`.
- Shifted npz files, scorer JSONs and per-frame npz files are in `$W/scores/` and `$W/sim/` (scratch).

Process notes:
- One background waiter used `pgrep -f`, which matched its own command line, so it never started its job. I killed
  it by PID; nothing had run.
- I briefly started a second waiter that could have overlapped a scorer. I stopped it before it started anything.
- No two scorers ran at once.
