# refcheck/timing: when things happen in our reference, against public mocap (26 Oct 2026)

Part of the owner's question "can't we first make sure our calculation of the reference is correct with public data?".
This check asks **when**, not where: when each object starts and stops moving, when a robot hand reaches it and lets
it go, and what happens while the object or the hand is hidden. It covers the 20 public episodes and the canonical
references in `../resolve/canonical_refs.json`.

Everything ran on CPU in this container. No GPU, Vast or Kaggle was used, and the cost was $0. Mocap is read only by
these diagnostics, after inference.

Labels:
- **[M]** measured here; the command is in `commands.log`.
- **[D]** derived from [M] numbers by arithmetic.
- **[doc]** taken from a doc, a box record or a sibling check, not recomputed.
- **[H]** a hypothesis, with the experiment that would falsify it.

1 frame = 49.37 ms (the 20.254 Hz video and mocap grid).

## Bottom line

1. **Onset timing is right to within a frame, but our object path is about half a frame late everywhere [M].**
   - Measured at the moment each object first moves 1 cm from rest, ours lags mocap by a median of:
     - +0.54 frames (27 ms) in the perception, IQR +0.28 to +0.65, 22 of 25 objects within ±1 frame;
     - +0.59 frames in mkref's output and in the final reference.
   - mkref and contact retarget neither add nor remove lag.
   - The lag does not change with FoundationPose tracking iterations: 2, 4 and 8 iterations give +0.55, +0.56 and
     +0.55 frames. So it is not the tracker failing to converge.
   - Advancing our path by one constant 0.545 frames raises the registered AUC against mocap:
     - perception: +0.0055 mean, 16 of 19 episodes improve;
     - reference: +0.0068 mean, 9 of 10 improve.
   - CPU proxy for the policy score: advancing the 50 stored **simulated** paths by the same constant gains less,
     +0.0029 mean. 31 of 50 rollouts and 7 of 10 episodes improve; ep21 gains +0.019. The simulated object already
     leads our reference by about 0.3 frames (section 5; H4).
2. **Stop times are noisier than start times [M].** Two different causes:
   - Late settling from track jitter after the object is put down: ep11 beige cup +17 frames, ep13 cup +28, ep24
     board 1 +30, ep31 sweeper +33.
   - Early settling created by contact retarget's rest settle, in the reference only: ep2 pot −7.7 frames, ep26 pot
     −4.2, ep18 pan −3.1.
3. **The largest timing errors are not clock errors. Our path moves objects that are truly at rest [M].**

   | ep | object | true state | our path | AUC at stake (oracle that freezes our object at rest) |
   |---|---|---|---|---|
   | 11 | blue cup | static (0.49 cm) | moves 5.4 cm from f43, 75 frames | **+0.069** |
   | 24 | board 2 | at rest until f111 | creeps 2.7 cm from f39, no hand within 8 cm | +0.011 to +0.014 |
   | 31 | sweeper | true onset f35 | 1.8 cm / 17° early | mixed: +0.006 perc, −0.017 ref (see section 2) |

   Downstream effects:
   - In ep24 and ep31 the grasp-lock onset anchor locked the hand onto this false motion: 82 and 21 frames before the
     true onset.
   - The simulated objects move early in the same way: board 2 at −90 frames, sweeper at −22 to −29.
4. **Hand arrival is early or on time in the references the policy uses [M].**
   - With a robot hand within 2 cm counted as contact, after contact retarget the hand arrives a median of 9 frames
     before the true onset. None of 14 objects arrives late.
   - Late arrivals:
     - mkref/E2S output, ep18 sweeper: 28 frames late (the robot hand hovers 2.1–3.5 cm away while the human hand
       holds it). Contact retarget fixes it.
     - grasp-lock training reference, ep26 pot: 10 frames late. Its re-plan sends the hand to where the pot lies in
       the simulation.
   - Release is late: a median of 23 frames (1.1 s) after the object settles; in the grasp-lock plan, 9–127 frames.
   - The grasp-lock plan locks every hold 1–82 frames **before** the true onset (median −5).
5. **Hidden phases [M].**
   - The track guard intervened only in ep23 (board 1: 4 re-acquisitions and 1 held frame), and that episode is
     broken anyway (identity swap).
   - Hands are invisible far more often. In ep21 the pouring hand is invisible for 56 of the pitcher's 76 moving
     frames, and in ep2 the lid hand for 47 of 117.
   - mkref's fill keeps the robot hand on the object in most episodes. In ep2 it drifts up to 11 cm off the moving
     lid (20 unheld frames); the grasp-lock reference repairs this.
   - The object error is about 0.5 cm higher while the hand at the object is not tracked: 1.67 vs 1.21 cm ADD. That
     costs about 0.003 AUC [D].

## Method

**Sources.**
- Mocap: the public parquet's `observation.objects` pose, at the scan's surface centroid.
- perc: the canonical perception.
- pre: `e2s_reference.parquet`.
- ref: the final reference.
- glockt: the grasp-lock reference that the rollouts name in their metadata. Its object path equals ref (0.0 mm) [M].
- stale: the 20 Oct refsweep, used where no canonical reference exists. Its perception was templated on the public
  scans.
- sim: rollouts r1–r5.

Our poses are taken at the kit's registration anchor: the point of our mesh that corresponds to the scan's centroid.
Axis-symmetric cups use the swing of their axis as rotation, because the spin about the axis cannot be observed.

**Thresholds** (from `noise_floor.json` [M]; speeds measured in frames where mocap is at rest):

| source | speed p95 | rotation-rate p95 |
|---|---|---|
| mocap | 0.27 cm/s (max over objects 0.55) | 2.8 deg/s (max 6.8) |
| our tracks (median over objects) | 1.9 cm/s | 13 deg/s |

Thresholds chosen from these:
- **Crossings** use the same rule for every source: the first frame of ≥ 3 frames more than 1 cm or 2 cm (or 10°) from
  the start rest pose (median of the first 5 frames). Sub-frame times come from linear interpolation. Offsets use the
  same rule against the end rest pose.
- **True physical onset and offset** (mocap only) walk back or forward from the crossing while speed ≥ 1 cm/s or
  rotation rate ≥ 10 deg/s. 5 deg/s is inside mocap's own rest noise.
- **Speed edges**: every bout at 5 cm/s.

**Hand contact.**
- Robot: the 15 probe sites plus the palm centre that mkref uses, against our mesh posed by the same reference.
  - Contact at < 2 cm, the main threshold, close to mkref's 1.8 cm.
  - Also < 1 cm. Site points sit inside the finger, so at 1 cm a locked grasp on a thin pan reads as "off".
- Human: the perceived MANO joints (5 tips and 5 palm joints) at < 2 cm.
- Labels: the reference's contact labels.
- Runs: gaps of ≤ 2 frames bridged, runs of ≥ 3 frames kept.
- Grasp-lock plans come from the `ref_gl[_r1]_grasp_lock.json` whose robot frames match glockt (0.0 m).

**Cost.** In-process kit scoring, the systematics check's `kit_prepare` plus the kit's own alignment, error and AUC
functions.
- Checked against `pipeline/score_registered.py` on ep39 and ep21 paths shifted by 0.59 frames: 0.9702 / 0.9702 and
  0.7812 / 0.7812.
- Unshifted ep39: 0.9559, the same as the chain check.
- Rollout r1 of ep2: 0.4513, the same as the box's `score_registered_ep2.json`.

## Results

Full per-object tables are in `tables.md`; machine-readable versions are in `summary.json`, `timing.json`,
`cost.json`, `creep.json`, `iters_lag.json` and `sim_shift.json`.

### 1. Object onset and offset vs mocap [M] (pooled, excluding ep23; lag = ours − mocap)

| source | 1 cm onset | 2 cm onset | 10° onset | 1 cm offset | 2 cm offset |
|---|---|---|---|---|---|
| perc (25 objects) | +0.54 [+0.28, +0.65] | +0.54 | +0.46 | +1.30 [−0.18, +2.38] | +0.72 |
| pre (14) | +0.59 [+0.47, +0.72] | +0.59 | +0.54 | +1.56 | +0.88 |
| ref (14) | +0.59 [+0.32, +0.68] | +0.59 | +0.44 | −0.08 [−2.11, +3.46] | +0.40 |
| stale (11) | +0.39 | +0.37 | +0.57 | +0.32 | +0.25 |

- Cells are medians in frames, with the IQR in brackets.
- Speed edges (5 cm/s) of every bout give a median of +1 frame, IQR 0 to +1 (integer frames), for perc, pre and ref
  (103, 48 and 46 starts).
- Static objects (mocap < 1 cm): the ep12, 13, 26, 27 and 31 racks and the ep11 blue cup.
- Cross-check [doc]: `../systematics` finds the same lag by speed cross-correlation (0.48 frames, no drift over the
  episode).

**H1: the lag is a constant offset between video frame i and mocap row i, not an estimation lag.**
- The tracker-convergence variant is already falsified: on the 25 Oct sweep, base, t4 and t8 differ by −0.003 and
  −0.001 frames, paired, n = 67 (`iters_lag.py`).
- Remaining falsifier (GPU): register every frame of 2–3 public episodes independently (no temporal prior). A lag
  near 0 there would point to the tracker's temporal prior instead.

### 2. Our object moving while the true object rests [M] (`creep.json`)

| ep / object | what ours does | consequence downstream |
|---|---|---|
| 11 blue cup (truly static, ≤ 0.49 cm) | 5.4 cm / 6.8° from f43 (when the beige cup is stacked), 75 frames > 1 cm, perc = ref | Freezing it (oracle): ep11 +0.069 (perc and ref). The grasp-lock onset anchor fired on it (f33, hold from f23) |
| 24 board 2 (true onset f111) | creeps 2.7 cm from f39, 72 frames > 1 cm; no hand within 8 cm in f38–94 (sampled every 8 frames) | Onset anchor: hold from f29 (82 frames before the truth). The simulated board moves at −90 (2 of 5 rollouts) |
| 31 sweeper (true onset f35) | 1.8 cm / 17° before onset (1 cm at f26), 2 cm / 17° after offset | Onset anchor f24. Simulated sweeper onset −22 to −29 frames, like ours (−21.5) |
| 13 blue cup | 3.1 cm / 13.5° tail after the true offset (perc), 22 frames | Freezing: +0.014 |
| 31 rack (static) | ref 1.8 cm for 82 frames (rest settle), perc 1.2 cm | – |

- The ep11 beige cup's onset anchor fired at **f1**, 21 frames before the true onset. The anchor rule
  (`grasp_lock.py`, rotation > 8° from rest) counts the cup's **spin about its axis**. Our beige cup jumps 17–22° in
  spin between f0 and f1, but only 3.4° in swing [M].
- **H2:** measuring onset by swing only for axis-symmetric objects removes these false anchors:
  - ep11 beige f1 → about f30;
  - ep11 blue cup: never;
  - ep12 cup f30 → f39.
  Falsifier: replay the ep11 / eval-10 grasp lock with the swing-only rule and check hold_from against mocap and
  sim_vs_ref.
- **H3:** a GT-free rule (no robot or human hand within 2 cm and no supporting object moving → hold the object at its
  rest pose) removes the creep without removing true motions.
  - Falsifier: apply it to the public references. Then (a) score against mocap; it should recover most of the
    rest-hold gain (ep11, ep24, ep13); and (b) list the true motions it freezes: lid on the pot, pushes, slides.
  - Caution: the oracle also *loses* on ep18 perc (−0.011) and ep31 ref (−0.017), where our end-rest pose is worse
    than the moving track.

### 3. Hand contact against the TRUE motion window [M]

Lead = true onset − hand arrival (> 0: the hand is there first). Release = hand release − true offset. Unheld = true
moving frames with no contact.

| hand (14 objects with a canonical ref) | lead median [IQR] | late arrivals | release median | unheld / true moving frames |
|---|---|---|---|---|
| pre (E2S robot, 2 cm) | +10 [6, 13.5] | ep18 sweeper −28, ep27 pot −2 | +23 | 64 / 1804 |
| ref (after contact retarget) | +9 [4.5, 13.5] | none | +23 | 20 / 1804 (ep2 lid) |
| glockt (policy's reference) | +7.5 [4, 19] | ep26 pot −10 (re-plan to the simulated pot) | +31.5 | 16 / 1804 (ep26) |
| human (perceived MANO) | +7 [4, 12] | none | +19.5 | 54 / 1804 |
| contact labels | +10 [6, 11] | ep18 sweeper −28, ep27 −2 (copied from pre) | +19 | 75 / 1804 |
| stale references (10 objects) | +12.5 | none | +19 | 166 / 1591; most is the ep0 pot, whose stale track is wrong, and the ep22 pitcher (45) |

- **Grasp-lock plan** (14 holds): hold_from − true onset has a median of −5 frames, range −82 to −1. Every hold
  locks before the object truly moves. The extremes are the three false anchors in section 2.
  - end − true offset: median +20 frames, range +9 to +127.
  - The ep2 pot is held until f337; the episode ends at f342.
- **Lead-in** (`mkref --lead_in`): hands first seen at f1–6 (ep2, 11, 26: lead-ins of 1–6 cm). None is near an
  object's true onset.
  - ep24 predates the lead-in: its right hand, first seen at f17, is attached to board 1 for f0–16, which includes
    11 frames of board 1's true motion.
- **Held or interpolated hand frames** (mkref fill of invalid hand runs; `tables.md` section 3) that overlap true
  motion:

  | ep | invalid hand frames | effect |
  |---|---|---|
  | ep2 | right f77–223 (lid) | With attach→hold blending, the hand drifts 1 → 11 cm off the moving lid in f140–220: the 20 unheld frames above. The grasp-lock reference holds the lid throughout |
  | ep21 | right f42–97 (pitcher: 56 of 76 moving frames) | Attached, so the robot hand stays on it (0 unheld) |
  | ep12 | left f60–84 | |
  | ep18 | right f153–175 | |
  | ep27 | right f2–34 | |
  | ep39 | right f219–248 | |

  - The hand tracker also interpolates a further 0–85 frames per side during motion.

### 4. Hidden / occluded phases [M]

- **Track guard** (guard arm, 8 episodes):
  - ep0 lid: one frame-0 retry, which gave the good lid track.
  - ep23 board 1: re-acquired at f155, 168, 200 and 245, and held at f169 (the object was at rest then). ADD in those
    5 frames is 31 cm, but ep23's boards are identity-swapped, so it says nothing about the guard.
  - No other interventions.
  - The tracker writes no per-frame visibility or confidence (`poses.npz` holds only poses), so object occlusion is
    not observable in our outputs.
- **Per-frame error by phase** (`cost.json`, excluding ep23 and ep0; frame-weighted medians of per-object ADD):

  | phase | perc ADD | perc AUC share | ref ADD | ref AUC share |
  |---|---|---|---|---|
  | rest | 1.27 cm | 0.923 | 1.45 cm | 0.903 |
  | moving, hand at the object and tracked | 1.21 cm | 0.942 | 1.43 cm | 0.920 |
  | moving, hand at the object **not** tracked (occlusion proxy; 425 frames = 6 %) | **1.67 cm** | **0.893** | **1.95 cm** | **0.857** |
  | moving with no hand near | 2.27 cm | 0.839 | 1.55 cm | 0.928 |

  - At the tracked-hand share, the occlusion-proxy frames would add about 0.003 AUC [D].

### 5. Cost

**Re-scored with the kit's registered AUC [M]** (`cost.json`; means over 19 perception episodes and 10 references;
ep23 excluded):

| variant | perc mean Δ | improved | ref mean Δ | improved |
|---|---|---|---|---|
| advance by the pooled lag, 0.545 frames (one constant: inference-legal) | **+0.0055** | 16 / 19 | **+0.0068** | 9 / 10 |
| advance by each episode's own lag (oracle) | +0.0077 | 16 | +0.0070 | 8 |
| advance each object by its own lag (oracle) | +0.0075 | 17 | +0.0067 | 9 |
| hold our object at rest outside the true moving window (oracle) | +0.0054 | 10 | +0.0071 | 6 |

- Largest gains from the constant shift: ep31 +0.022, ep18 perc +0.022, ep39 +0.015, ep11 ref +0.013, ep12 +0.011.
- It loses on ep24 (−0.003 / −0.004), ep22 (−0.0006) and ep43 (−0.0003).
- The systematics check's fixed 0.5-frame shift gives +0.0052 / +0.0069 [doc, read from its `fixed_shift.json`].
- A piecewise onset+offset time warp (oracle) was tried first and dropped: ep2 ref 0.9798 → 0.9402 and ep11 perc
  0.8964 → 0.8547. Offset crossings move with spatial settling errors, not with time (numbers in `commands.log`).

**Simulated object (CPU proxy) [M]:** `sim_shift.json`, 50 stored rollouts, the simulated path advanced by the same
0.545 frames.

| ep | 2 | 11 | 12 | 18 | 21 | 24 | 26 | 27 | 31 | 39 | mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sim AUC, stored (mean of 5) | 0.306 | 0.570 | 0.868 | 0.957 | 0.772 | 0.241 | 0.383 | 0.949 | 0.695 | 0.958 | |
| Δ when advanced 0.545 frames | −0.0004 | −0.0006 | +0.0036 | +0.0004 | **+0.0194** | +0.0020 | +0.0011 | +0.0018 | −0.0022 | +0.0042 | **+0.0029** |
| rollouts improved | 1/5 | 0/5 | 4/5 | 4/5 | 5/5 | 4/5 | 3/5 | 4/5 | 1/5 | 5/5 | 31/50 |

The stored-rollout scores reproduce the box records: ep2 r1 0.4513 = `score_registered_ep2.json`, and all 10
episode means equal the box-recorded means in `canonical_refs.json` [doc].

- The simulated object already leads our reference: median sim − ref crossing of −0.28 frames (1 cm) and −0.78 (10°),
  IQR about ±1, over 36 rollout-object pairs [M].
- **H4:** a reference advanced by 0.545 frames moves the trained policy's object by about the same amount. Falsifier:
  retrain or evaluate one public twin on a shifted reference (GPU). Until then, the gain on the policy score is
  unproven.

**Hand timing:** cannot be priced on CPU without the simulator. The grasp-lock training references put a hand on every
moving object except ep26, where the re-plan deliberately sends the hand to the simulated pot instead.

## Caveats

- 1 cm / 10° crossings measure the timing of the motion's start, not the first contact. The physical onset uses mocap
  only.
- Our ~1–2 cm rest jitter makes the crossings unusable for 4 objects; they are listed as outliers rather than lags.
- Hand contact is measured against our own object path and our own mesh. Robot sites are joint or site points, not the
  skin.
- The 2 cm threshold can turn a 2–3 cm near miss into a "late" hand: ep18 pre.
- ep23 (identity swap) is excluded from pooling. The ep0 stale pot path is wrong (stale perception), so ep0's stale hand
  rows are not usable.
- The no-reference episodes (0, 13, 22, 40–45) have hand timing only from the stale 20 Oct references.
- Importing `../systematics` rewrote its gitignored `__pycache__` (16:46 UTC); nothing else there was touched.
- Up to four `cost.py` processes ran at once for about 6 minutes (16:57–17:03 UTC). This broke the
  one-heavy-process rule, after a `pkill` that did not match (`commands.log`). The results are unaffected.

## Files

| file | contents |
|---|---|
| `tload.py` | loaders; reuses `../systematics` read-only |
| `noise_floor.py` | rest-noise floors → thresholds |
| `timing.py` | events, hands, plan, mkref bookkeeping, guard → `timing.json` |
| `creep.py` | `creep.json` |
| `cost.py` | `cost.json`, `cost.log` |
| `sim_shift.py` | `sim_shift.json` |
| `iters_lag.py` | `iters_lag.json` |
| `verify_scorer.py` | scorer check |
| `summarize.py` | `tables.md`, `summary.json` |
| `commands.log` | every command, with timings |

Repo HEAD at run time: 8724a24. These files are new and uncommitted.
