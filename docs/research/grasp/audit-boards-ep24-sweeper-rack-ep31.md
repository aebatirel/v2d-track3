# Root-cause audit: ep24 (two flat boards) and ep31 (sweeper in the dish rack) under the grasp-lock recipe

2026-10-24. Analysis only: CPU, no rentals, no commits. Workflow `wf_cdd41283-528` asked one question: are these
failures really grasp failures?

Evidence labels:
- **[M]** measured by us from simulator traces, rollouts or our reference. No ground truth.
- **[M-GT]** measured with mocap ground truth. Diagnostic only, after inference; never used for a choice.
- **[C]** checked in code or config.
- **[L]** literature, opened at the URL given.
- **[I]** inference.
- **[H]** hypothesis, with the experiment that would falsify it.

Scripts are in `docs/research/grasp/audit-boards-rack-scripts/` (commands in §5). Downloads and outputs are in the
scratchpad: `grasp_work/audit-boards-rack/{dl,out,vid}`.

## 0. Answer

| episode (eval twin) | grasp-lock score (registered, mean of 5) | where the loss is | grasp problem? | needed fix |
|---|---|---|---|---|
| **ep24** two boards (eval 25) | **0.202 ± 0.072**. Floor 0.203; our reference vs mocap 0.816 | **Neither board is ever acquired or carried** by the locked grasp: 0 of 5 rollouts lift board 1; board 2 is carried in 1 of 5 rollouts. Making the sim follow the reference from board 1's lift and board 2's slide would give **0.803** (counterfactual). Fixing only the start transient gives +0.03. | **Yes** (primary). Contributing causes: perception floats of 2–4 cm, the sim table disc off-centre, and approach knocks. | A **designed board clamp**: parallel extension, thumb on the top face, fingers under the board, which in this sim passes through the table. Lock it from the slide; allow a grasp change inside a hold. Snap resting boards to the table. Centre or enlarge the support disc. |
| **ep31** sweeper + rack (eval 30) | **0.767 ± 0.016**. Reference vs mocap 0.8525 | **The start, not the grasp.** In the first control step the sweeper is ejected from the rack's collision hulls: 11.3° / 1.07 cm, identical in zero-action and in all 5 rollouts. The scorer aligns the whole scene on slot 0 (the sweeper) at that frame. Fixing only that frame gives **0.840 (+0.074)**. A perfect scrub phase gives +0.039. A perfect grasp, lift and carry gives +0.002 to +0.004. | **No.** The fine-tuned policy acquires, lifts (9.4–9.7 cm vs 10.4 cm) and carries the sweeper in 5 of 5 rollouts. | **Collision geometry that is consistent at the start.** Split the rack hulls (note 19: rack S120), or remove the start overlap (depenetrate or settle). Secondary: keep the reference brush out of the rack during the strokes (today up to 7.5 mm inside). No new grasp design. |

The ep31 finding generalises: **slot 0's first-step jump is a GT-free predictor of lost score** (§4).

## 1. Data used

| what | run / path (HF store `aebatirel/v2d-store`) |
|---|---|
| ep24 grasp-lock | `runs/20261023-glockpub-0f7e3a7`. Code 0f7e3a7: no approach, re-plan or support fill. Base reference `perc2mcs` from `20261021-auto24-966eb96`. Our meshes are library v1–v3; the board files are identical md5 in all three. |
| ep24 standard RL | `runs/20261022-r5ks-72ecb2f` (s42, 250M) and `r5ks43` (s43, 200M), `results/hard_ab/ep24/mcsks-s4x`. The simulation used the **organisers' collision meshes**; the scores are against our meshes and against the scans. |
| ep31 grasp-lock | `runs/20261024-e2-e49e83d`. `--approach_cm 6`, SF=1, REPLAN=1 (re-plan not kept), library_v3, 70M fine-tune. |
| ground truth | Public `track_3/public/data/chunk-000/episode_0000{24,31}.parquet`, public scans `track_3/public/mesh/*`, colour videos `ego_cam_a` (`nvidia/video_to_data_challenge`). |

Method:
- **Zero-action traces** (`zero.npz`): our scripts give per-object error against the reference, lift, link-origin
  proximity and signed distance.
- **Rollouts**: read with the kit's `read_trajectory`.
- **Official-style registered scoring**: the kit's `v2dlb.track3_pose`, exactly as `pipeline/score_registered.py`, with
  the public scans as hidden geometry. It reproduces the stored per-rollout numbers to 4 decimals, e.g. ep31 r1 0.7615
  and ep24 r1 0.2218.
- **Counterfactuals**: the same scorer, with parts of the simulated trajectory replaced by our reference.
- **Per-phase GT proxy**: per frame clip((9 cm − ADD)/8 cm), after a frame-0 warp on slot 0. It agrees with the
  official per-object AUC to within ±0.03 on the boards and the sweeper. It is not reliable for the rack, because it
  skips the rack's registration.

Two code facts that drive the conclusions:
- **[C] The evaluator records the first pose after one control step.**
  `flash_chord/evaluation/rollout.py` (`record_object_pose_rollout`) runs `action → jax_env.step(action) → record`.
  The scorer then aligns the whole scene once at that frame, on slot 0 (`_align_registered_scene`, kit
  `metric_code/track_3`, as used by `score_registered.py`).
- **[C] The robot hands do not collide with the table.** `configs/experiment/sharpa_flash_sac.yaml` overrides
  `/collision: training`, and `configs/collision/training.yaml` sets `robot_support_collision: false`. This agrees
  with note 23.

## 2. ep24: two flat boards (planter-stand assembly)

### 2.1 Board geometry

| | public scan (collision glb) | ours (library v1–v3, identical) |
|---|---|---|
| size | 22.7 × 13.85 cm, both boards | board 1: 22.9 × 13.3 cm; board 2: 22.9 × 13.8 cm |
| solid thickness [M] (ray cast over the footprint) | board 1: median 7.5 mm (p10–p90 6.3–8.6) | board 1: median 7.8 mm (p10 2.8, slot edges) |
| | board 2: median 9.1 mm (8.6–9.6) | board 2: **median 12.0 mm (3 mm thicker than the scan)** |
| features | Cross-lap slot from the middle to one long edge; feet and pegs make the bounding box 2.6 cm thick | Same slot; bounding box 3.05 / 2.66 cm; volume 203 / 323 cm³ |
| simulated mass | 0.3 kg placeholder in the kit URDF. A real board is about 0.15 kg [I: 250 cm³ × ~0.6 g/cm³]. | same |

### 2.2 What the human does

Sources: video (`ego_cam_a`, contact sheets in `out/ep24_sheet{1,2,3}.jpg`), mocap [M-GT], and our MANO contact
labels and finger positions [M].

**The table is a small round table, and the two boards start near its opposite edges.**

**Board 1, left hand:**
- **f0–8:** flat (tilt 0.9°).
- **f8–17: palm-on-top drag** outward. Mocap: 4.6 cm by f15, 7.6 cm by f20, lowest point ≤ 0.1 cm, tilt ≤ 1°. The
  video shows the board pushed past the table edge: it overhangs.
- **f18–30: lift by the overhanging part, tilting** (mocap: 2.2 cm / 5.8° at f20, 9.9 cm / 14° at f25, 15.6 cm / 26°
  at f30). The fingers are under the protruding part and the thumb is on top (video f22–30).
- **f30–60:** carried at 15–18 cm.
- **f40–58:** both hands on the board.
- **f55–80: the right hand turns it to vertical** (tilt 30° → 88°).
- **f85–90:** set standing on its 8 mm edge.
- **f85–240:** held standing by the left hand.

**Board 2, right hand:**
- **until f112:** still.
- **f113–125: drag to the near-right table edge.** Mocap 8.9 cm, lowest point ≤ 0.3 cm, tilt ≤ 3°. The board
  overhangs (video f122–128).
- **f125–130: fingers under the overhanging corner, thumb on top, lift with tilt** (mocap: 8.8 cm / 23° at f130).
- **f135–155:** rotated to 82°.
- **f170–220:** lowered into board 1's slot. At the end both boards stand at 88–90°, with origins within 0.1 cm in xy:
  the cross-lap joint is assembled.

**Contact pattern per phase [M].** Fraction of contact frames in which each MANO link touches the board.

> **Correction, 2026-10-25 [M].** The link names in this table are wrong: they read the slots in MANO link order. The
> table is kept as written; the corrected one follows it.

| board / hand / phase | frames | dominant links |
|---|---|---|
| b1 / L / drag f4–18 | 14/14 | palm 0.79, index2 0.43, index3/middle3 0.36, thumb1/2 0.29 |
| b1 / L / lift f18–40 | 22/22 | pinky3 0.91, palm 0.86, index2 0.86, index3 0.77, thumb1 0.68 |
| b1 / R / two-hand f40–60 | 20/20 | index3 0.80, thumb1/2 0.65, palm 0.65 |
| b1 / R / rotate f60–85 | 18/25 | pinky2 0.72, middle2 0.67, pinky3 0.67, thumb3 0.61 |
| b1 / L / standing f85–240 | 155/155 | middle1 1.00, middle2 0.99, index3 0.98, ring3 0.96, pinky1 0.95 |
| b2 / R / drag f110–126 | 16/16 | ring2 0.56, thumb3 0.50, palm 0.50, index3 0.44 |
| b2 / R / lift f126–140 | 14/14 | palm 1.00, ring3 0.86, thumb1 0.64, index3 0.64 |
| b2 / R / carry and insert f140–222 | 80/82 | thumb2/3 0.96–1.00, middle1 0.94–1.00, middle2 0.80–0.88 |

**Correction, 2026-10-25: contact pattern with the right slot labels [M].** The table above read the reference's
`mano_link_names` (palm, thumb1 … pinky3) as slot labels (`human_board.py` via `refload.py`). `pipeline/mkref.py` fills
the 16 slots in its probe order: thumb, index, middle, ring and pinky tips, then their DP sites, then the thumb MCP and
the finger MP sites, and the palm last (`approach3-grasp-taxonomy.md` §9). So "palm" was the thumb tip, "thumb1–3" the
index, middle and ring tips, and "pinky3" the palm.
- Reproduction: `tools/contact_slots.py --mano` on our `perc2mcs` ep24 reference (`runs/20261021-auto24-966eb96`,
  b1 = wooden_piece_1) reproduces every row above. Without `--mano` it gives the table below.
- Output: `audit-boards-rack-scripts/out/ep24_contacts_slotfix-20261025.txt`.
- Shares are over contact frames, as above.

| board / hand / phase | frames | digit shares: thumb / index / middle / ring / pinky / palm | dominant slots (≥ 0.5) |
|---|---|---|---|
| b1 / L / drag f4–18 | 14/14 | 0.86 / 0.36 / 0.29 / 0.14 / 0.36 / **0.14** | thumb tip 0.79 (thumb DP 0.43, index and pinky DPs 0.36) |
| b1 / L / lift f18–40 | 22/22 | 0.86 / 0.95 / 0.09 / 0.14 / 0.14 / 0.91 | palm 0.91, thumb tip and DP 0.86, index DP 0.77, index tip 0.68, index MP 0.50 |
| b1 / R / two-hand f40–60 | 20/20 | 0.65 / 0.90 / 0.65 / 0.40 / 0.35 / 0.40 | index DP 0.80; thumb, index and middle tips 0.65; thumb DP 0.50 |
| b1 / R / rotate f60–85 | 18/25 | 0.44 / 0.67 / 0.39 / 0.72 / 0.72 / 0.67 | pinky MP 0.72, ring DP 0.67, palm 0.67, ring tip and MP 0.61, index tip 0.56 |
| b1 / L / standing f85–240 | 155/155 | **0.00** / 1.00 / 1.00 / 0.99 / 0.06 / 0.00 | middle, ring and index DPs 0.98–1.00; their MPs 0.90–0.96; index and ring tips 0.74–0.79 |
| b2 / R / drag f110–126 | 16/16 | 0.50 / 0.69 / 0.38 / 0.62 / 0.12 / 0.12 | index MP 0.56, thumb tip 0.50, ring tip 0.50 |
| b2 / R / lift f126–140 | 14/14 | 1.00 / 0.79 / 0.86 / 0.36 / 0.00 / 0.29 | thumb tip 1.00, middle MP 0.86, index tip and DP 0.64, middle DP 0.50 |
| b2 / R / carry and insert f140–222 | 80/82 | 0.23 / 0.91 / 0.97 / 0.97 / 0.00 / 0.03 | middle and ring tips 0.97, middle DP 0.96, index tip 0.91, ring DP 0.85 |

What changes [M]:
- The contact labels do not show a palm-on-top drag of board 1 (palm 0.14; the old "palm 0.79" is the thumb tip). The
  drag reading still rests on the video and the mocap, which are unaffected.
- The palm does touch during board 1's lift (0.91) and rotation (0.67).
- The perceived thumb is absent while board 1 stands (0.00) and mostly absent during board 2's carry and insertion
  (0.23). It is present in board 2's lift (1.00).

Unaffected: the fingertip heights below (MANO joints, not slots) and the conclusions drawn from the video.

**Fingers relative to the board [M].** Our reference, board frame. Our hand joints are noisy to about ±1–2 cm, which is
larger than the 8 mm board, so the sign is reliable only beyond about 1 cm.
- Board 2 at f128: the thumb is 2.0 cm above the top face, index 0.6 cm above; middle, ring and pinky are 2.0–3.8 cm
  below the bottom face, inside the footprint. This is the **fingers-under, thumb-on-top pinch**.
- Board 1 during the carry (f22–40): middle and ring are 2.2–3.9 cm below the board, with palm contact. This is an
  underhand support.

**Conclusions on the human:**
- The human uses a **multi-stage** strategy: drag (palm on top) → slide past the table edge → edge pinch with the
  fingers under and the thumb on top (Feix "parallel extension", #22 [L4]) → hand-over or two hands → hold standing on
  edge.
- This is the textbook **slide-to-edge grasp** [L1, L2]. Bimbo et al. quote humans as grasping flat objects "with a flip
  or a slide-to-edge grasp".
- **No flip, tilt against the table or other board, or lateral pinch is used.**

### 2.3 What the grasp-lock reference asked

Facts [M] (`ref_gl_grasp_lock.json`, `glock_ep24.log`):
- **Board 1:** the left hand holds it f4–240, as one phase merged from 2. The grasp is snapped from **f12, during the
  palm-on-top drag** (4 fingers on, gap 3.1 mm). Closing fractions: index 0.025, middle 0.475, ring 0.05, pinky 0.825,
  thumb 0.2. Squeeze 0.4 rad; 6 joints at their limit.
- **Board 2:** the right hand holds it f103–244, with the grasp from f124 (gap 5.1 mm). Closing: index 0.025, middle
  0.025, ring 0.35, thumb 0.05.
- `single_hand=1` drops the human's right-hand phases on board 1. `pipeline/hold_phases.py` on the same reference finds
  "right holds wooden_piece_1 f37–78, two-handed f37–78"; that is where the right hand turns the board vertical. The
  left hand must therefore do the 90° turn alone.
- Each hold is **one static locked grasp**, but the human changes grasp 3–4 times within these frames.

**Robot reference fingers at the locked grasp** (distal-phalanx and C_MC link origins; DP origins sit 2–3 cm behind the
fingertip):
- **Board 1:** the palm is 4.6 cm above the board and 2.6 cm outside its edge. The thumb DP is 0.3 cm *inside* the board
  (the squeeze target). Index, middle and ring DPs are 0.9–1.4 cm *below* the bottom face, which is inside the table.
  That is legal here because the hands do not collide with the table. **Geometrically it is an edge clamp.**
- **Board 2:** thumb, index and middle DPs are 0.2–0.4 cm inside the board.

### 2.4 Zero-action replay

Measured [M] with `trace_audit.py`, `robot_sd.py` and `wrist_err.py` on `zero.npz`.

- **Board 1. Grasp never acquired.**
  - After the first step it is rotated 5.5° (9–11° at f2–4) by the reference hand, which is already at and under the
    board at frame 0.
  - From f12 to f24 the simulated **thumb DP stays 2.2–2.8 cm from the board surface**. Index and middle DPs are
    0.7–2.0 cm away; ring and palm 3–6 cm.
  - **The left wrist lags the reference by 3.0, 4.1, 7.0 and 11.4 cm** at f12, f16, f20 and f24 (dz −1.5 to −6.5 cm).
  - The board is dragged and spun (14.2 cm and 50° by f30). Maximum lift is 5.4 cm. The hand leaves it at f30 (28.6 cm
    away).
- **Board 2. Grasp never acquired.**
  - At the grasp (f116–124) the **thumb DP is 4.3–4.8 cm from the board** and index and middle DPs 4.0–4.9 cm. The
    palm is 11.3–12.6 cm from the board, against 8.3 cm in the reference. Only the ring MP touches (0.6–0.9 cm).
  - The wrist lags 5.2–6.4 cm horizontally. Maximum lift is 0.5 cm. The hand leaves at f130.
  - Before that, at f30, the *parked* right hand's fast reference swing (6.8 cm per frame toward board 1) passes through
    board 2: ring and pinky links come within 2 cm and the board tilts 5.9°.
- Zero-action sim_vs_ref is 0.2186, equal to the floor (0.2199).

### 2.5 Policy rollouts

**Grasp-lock 30M** (chosen by sim_vs_ref; 5 evaluations; per-object registered AUC [M-GT]):

| rollout | board 1: what happens [M] | b1 AUC | board 2: what happens [M] | b2 AUC |
|---|---|---|---|---|
| r1 | 3.0 cm / 16° off at f5; max lift 4.6 cm; off the table at f274 | 0.072 | bumped at f30 (17–20°); lifted 4.7 cm at f131, then dropped | 0.372 |
| r2 | max lift 3.3 cm; dragged 14 cm / 38°; off the table at f274 | 0.050 | **carried**: max 27.3 cm (ref 26.1) at f144, 3.8–10 cm error f126–240, rotation 61–99° off | 0.541 |
| r3 | max lift 1.7 cm | 0.061 | never moved | 0.351 |
| r4 | max lift 4.6 cm (at f264) | 0.066 | lifted 6.2 cm at f132, then **fell off the table** (−59 cm) by f140 | 0.363 |
| r5 | max lift 1.7 cm | 0.060 | **knocked off the table** at f30–60 | 0.089 |

| per-phase proxy [M-GT] | board 1: rest / drag / lift / carry / rotate / stand | board 2: rest / drag / lift / carry / insert / stand |
|---|---|---|
| grasp-lock sim (5 rollouts) | 0.88–0.89 / 0.46–0.85 / 0.11–0.24 / 0 / 0 / 0 | 0.23–0.89 / 0–0.59 / 0–0.10 / 0–0.05 / 0–0.41 / 0–0.50 |
| our reference | 1.00 / 1.00 / 0.97 / 0.89 / 0.75 / 0.71 | 0.88 / 0.76 / 0.82 / 0.81 / 0.81 / 0.80 |
| standard s42 (6 rollouts, organisers' meshes) | 1.00 / 0.65–0.75 / 0.02–0.52 / 0.36–0.46 / 0.07–0.58 / 0–0.52 | 1.00 / 0.52–0.55 / 0–0.08 / 0 / 0 / 0 |

Other runs:
- **Standard s43:** both boards stay at the floor in all 6 rollouts (0.0573 / 0.4305), i.e. nothing moves.
- **Fine-tune curve:** 0.095 / 0.165 / 0.072 / 0.078 at 10/30/50/70M. At 70M the policy lifts the boards 14–16 cm but
  loses them (in-3-cm 0.05 / 0.10).

**Reading [I]:**
- Plain RL learns a board-1 pick-up in 4 of 6 rollouts (s42). The grasp-lock recipe, which starts from a locked grasp
  that never closes, does not.
- **Board 2 is never lifted by the standard RL either.** It is the harder of the two: the grasp lands on a floating
  reference board (§2.7) and its slide puts it at the simulated table edge.

### 2.6 Where ep24's score is lost

Counterfactuals with the official-style scorer, mean of the 5 grasp-lock rollouts [M-GT]:

| simulated trajectory with … replaced by our reference | AUC |
|---|---|
| nothing (as evaluated) | 0.202 |
| board 1 at frame 0 only (the first-step transient, 5.3°) | 0.232 (+0.03) |
| board 1 from its lift (f18 on) | **0.552 (+0.35)** |
| board 1, all frames | 0.590 |
| board 2 from its slide (f112 on) | **0.418 (+0.22)** |
| board 1 all + board 2 from its slide | **0.803** |
| the whole reference (perception ceiling) | 0.816 |

About 0.6 of AUC is lost in acquiring and carrying the boards. The start transient costs 0.03.

### 2.7 Contributing problems on ep24 (not grasp design)

1. **The perceived boards float [M] (reference) / [M-GT] (mocap).**
   - Board 2 sits 1.4–2.4 cm above the table from f40 to f126 in our reference; mocap says 0.1–0.3 cm.
   - The standing board 1 sits 3.8–4.1 cm above the table from f100 on; mocap says 0.2–0.3 cm.
   - The contact-retargeted `mcsks` reference has the same object path.
   - So board 2's copied grasp is placed on a board 2 cm higher than the simulated one. This explains part of the
     4.3–4.8 cm thumb gap.
   - The floats also cap the reference at 0.816 (board 1 0.776, board 2 0.856).
2. **The simulated table disc is off-centre [M].**
   - It is a disc of radius 30.05 cm centred at (1.0, 5.0) cm (`t3_ep024_support.usda`, fitted from frame-0 depth). The
     boards start symmetric at y = ±15.3 cm.
   - Board 1's slide ends 2.6 cm *inside* the simulated edge (max r 27.4 cm), so it never overhangs. In the video it
     clearly does.
   - Board 2's slide ends with 49% of its area beyond the disc and its **centre at r = 29.3 cm (edge 30.05 cm)**. Any
     drop or push sends it off the table: r4 and r5 fell 59–60 cm. Board 1 left the table at the last frame in r1 and
     r2.
3. **Start disturbance [M].**
   - The board-1 hand starts at and under the board, giving 5.3° and 0.77 cm at the evaluator's frame 0 and 16–18° by
     f5 in all rollouts.
   - The parked right hand's fast swing hits board 2 at f30: 5.9° at zero action, 17° in r1, knocked off in r5.
4. **Wrist lag [M]:** 7–11 cm at f20–24 during the board-1 lift, and 16–21 cm for the right hand at f20–24, despite kp
   400 and 4 ILC iterations.

### 2.8 Evaluating the board primitive and its alternatives

Physics of the carry [M from our reference, no GT; rules from notes 24]:
- Peak load m|a − g| is 3.5–3.8 N against a weight of 2.94 N (|a| p95 1.0–1.2 m/s²).
- Carrying a horizontal board by one edge needs a **moment couple**. Gravity moment × SF 1.5 is 0.24 N·m for a
  long-edge grip (lever 5.4 cm) and 0.44 N·m for a short-end grip (lever 9.9 cm).
- With the thumb and fingers offset 3–5 cm along the board, that is **4.8–7.9 N per side** (long edge) or 8.7–14.6 N
  (short end).
- At finger kp 1.7 N·m/rad and a 5 cm lever: about **0.23 rad of squeeze past contact** (long edge) or 0.43 rad (short
  end, at or above the current 0.4 rad squeeze and near the joint limits).
- A vertical board held by friction only needs N ≥ m g SF / (2 μ_d) = **4.7 N per side** (μ_d 0.47 for the pyramidal
  cone, notes 24).

| option | matches the human? | in our simulator | verdict |
|---|---|---|---|
| **A. Slide to the table edge, then grip under** (Bimbo's "Continuous Slide and Grasp" [L1]; Hang et al. [L2]) | **Yes**, exactly (video, mocap, contacts) | (i) The overhang is **unnecessary**: the hands pass through the table [C], so fingers can go under a flat board anywhere. (ii) The simulated edge is in the wrong place: board 1 never overhangs and board 2 balances on the edge. (iii) It needs a **grasp change** mid-hold (drag → pinch), which the lock does not support. | Keep the human's *object path* (the reference already contains the slide). Use the slide-end frame only as the moment the grasp switches. Do **not** require an overhang. |
| **B. Parallel-extension edge clamp, fingers under through the table** (thumb pad on the top face 2–3 cm from the edge; index–ring pads 4–6 cm deep on the underside) | Yes: the human's lift grasp, Feix #22 [L4] | Physically valid here. One grasp can serve drag, lift and carry: during the drag the internal squeeze has zero net vertical force. A long-edge grip needs about 0.23 rad squeeze (feasible). Two conditions: the fingers must **enter edge-on below the board** (now they start under it and tip it 5–18°), and **the thumb must really oppose** (now it stops 2.2–4.8 cm short; "thumb opposition not built" in notes 24). | **Recommended** primitive for flat plates in this simulator. |
| **C. Tilt against the table or the other board (pivot), then edge pinch** (Bimbo's "Pivot and Re-Grasp"; "flip" [L1]; extrinsic dexterity [L5]) | No: not used in ep24 | Adds a rotation that is not in the reference, a tracking cost. Unnecessary because B is available. | Reject for ep24-type tasks. |
| **D. Lateral pinch** (side opposition, thumb against the side of the index, Feix #16 [L4]) at one edge point | No | The two contacts are nearly collinear with the board normal. They cannot resist the 0.16–0.29 N·m gravity moment about the edge axis without torsional friction, which condim 3 does not give (notes 24). | Reject as the carry grasp. Possible only for the vertical standing hold, where the load is in-plane friction. |

### 2.9 Verdict for ep24

- **It is a grasp problem.**
  - The locked grasp is copied once from the drag phase (f12 / f124) and never achieves opposition: the thumb is
    2.2–4.8 cm off the face and the wrist lags 3–11 cm.
  - The human uses a multi-stage strategy that one static lock cannot represent.
  - Neither board is carried in 5 of 5 rollouts for board 1, nor in 4 of 5 for board 2.
- Perception (floats), the support geometry (disc) and approach knocks make it worse but are not the main loss.

**Needed fix, in order:**
1. Designed parallel-extension clamp (option B) with statics-designed squeeze and real thumb opposition, entering
   edge-on. Lock it from the drag start, or switch to it at the human's contact-pattern change.
2. Snap resting and standing objects to the table in the reference, a GT-free support rule. Then the grasp is placed on
   the simulated board, or re-plan against the simulated board (`grasp_lock --sim_trace`, which this run did not have).
3. Centre or enlarge the support disc.
4. Keep the parked hand off the other board (approach and clearance rule).
5. Optional: two-hand phases for the 90° turn of board 1.

### 2.10 Hypotheses for ep24

- **H24-1: the designed clamp holds both boards.** Zero-action replay of option B, locked from the slide start, lifts
  each board ≥ 15 cm with in-hand drift < 2 cm / 10° through f60 (board 1) and f170 (board 2).
  - Falsified if lift < 5 cm or drift > 3 cm on either board.
  - CPU-testable with FlashCHORD (fcvenv, 1 world).
- **H24-2: support snap fixes the board-2 grasp.** Snapping resting and standing boards to the table raises our
  reference's AUC vs mocap above 0.816 (GT diagnostic, public only) and brings the zero-action thumb gap at the board-2
  grasp below 0.5 cm.
  - Falsified if the reference AUC does not rise or the thumb gap stays > 1 cm.
- **H24-3: staged holds are needed.** Splitting the board-1 hold at the contact-pattern change (palm-dominant drag →
  pinch at f18) is needed only if the single clamp from H24-1 cannot drag the board.
  - Falsified (staging unnecessary) if the single clamp reaches zero-action sim_vs_ref ≥ 0.6.
- **H24-4: support geometry stops the falls.** Centring the disc between the objects, or enlarging it by 10 cm, removes
  the off-table falls (r1, r2, r4, r5 today).
  - Falsified if any fall remains in 5 evaluations.
- **H24-5: an edge-on approach removes the start knock.** Board 1's first-step offset falls from 5.3° to < 1°.
  - Falsified otherwise.

## 3. ep31: sweeper standing in the rack dividers, plus the rack

### 3.1 Scene and human

Sources: video (`out/ep31_sheet1.jpg`), mocap [M-GT], MANO [M].

- At f0 the brush stands on its bristles on the table between the rack's dividers: lowest point 60.3 cm, table 60.0
  cm, tilt 0.0–0.1° until f20.
- The left hand steadies the rack's left end (cup tower) from about f20. Our MANO labels miss this contact.
- **Right hand:** a thumb–middle pinch on the wooden knob, f25–264. Link shares: thumb2 1.00, thumb3 0.97, thumb1 0.70,
  middle2 0.66, index3 0.10.
- **Motion:**
  - small closing motion f25–45 (≤ 0.5 cm, 4–8°);
  - lift f48–60 (+9.4 cm);
  - scrubbing strokes along the dividers f60–185, with the bristles back at table height at f90–110, f125–140 and
    f160–180;
  - second lift f185–225 (+10.4 cm);
  - put back standing at f235, 9.2 cm from the start.
- The rack does not move (≤ 0.2 cm, ≤ 0.9°).

### 3.2 The start transient

All [M] except where noted.

- **First control step:** the sweeper moves **1.07 cm and rotates 11.3°**.
  - The same values appear in the zero-action trace (f1) and in **all 5** policy rollouts (frame 0), so it is physics,
    not the policy.
  - No hand is within 26 cm. The rack moves 0.09 cm / 0.7°.
- **Overlap at the reference's frame 0** (`f0_overlap.py`):
  - **3.3% of the sweeper's surface samples are inside the rack's true mesh** (max 6.1 mm);
  - **6.8% are inside the rack's CoACD hulls** (Newton settings; max 7.7 mm, p95 5.5 mm);
  - at f20, 6.4% / 7.3 mm (mesh) and 8.2% / 10.9 mm (hulls).
  - Note 19 measured the same pair on ground-truth states: 10.4–15.3 mm, with a 1 s jolt of 12.9 mm / 14°.
- **Zero action** (`trace_audit.py`):
  - The tilt grows to 15° at f12 and 24° at f18 (rest check 26.1 mm / 24.2°), then 32° at f24 and 38–44° from f33.
  - The copied pinch arrives at f18–27 on a brush already tilted 24–36° and never lifts it (max 2.0 cm). The hand leaves
    at f54.
  - Zero-action sim_vs_ref is 0.607 (floor 0.587). The re-plan from f11 gave 0.562 and was not kept.
- **Why it matters [C]:**
  - The evaluator's frame 0 is the post-step state.
  - The scorer aligns the scene once, on slot 0 (the sweeper), at that frame.
  - So the 11.3° error becomes a rotation of the whole simulated scene. It costs the sweeper *and* the rack for all 290
    frames.

### 3.3 Grasp and carry under the fine-tuned policy

Policy at 70M, 5 rollouts, all [M]:
- **Acquisition:** 5 of 5 rollouts acquire, lift and carry the sweeper. Lift is 8.1–8.9 cm at f55–60 (reference 8.6–9.5)
  and 9.4–9.7 cm at f195 (reference 10.4). There are no drops.

Mean error against our reference, per phase (`seg_err.py`):

| phase | dz | horizontal error | rotation |
|---|---|---|---|
| rest | +0.6 cm | 1.4–1.5 cm | 9–12° |
| grasp | +1.1–1.7 cm | 1.6–2.1 cm | 13–14° |
| lift | — | 0.8–2.7 cm | 8–11° |
| **scrub** | **+1.4 to +1.7 cm** (the sim brush rides higher than the reference) | 0.7–1.3 cm | 3–7° |
| second lift | — | 0.5–0.8 cm | 2–6° |
| place | — | 1.0–2.1 cm | — |
| end | — | 1.2–2.5 cm | 10–12° |

- **Rack:** it moves ≤ 1.9 cm in the sim; the reference rack rises 1.2–1.7 cm during the strokes (a perception
  artefact).
- **Per-phase proxy [M-GT]** for the sweeper:

| phase | rest | grasp | lift | scrub | second lift | place | end |
|---|---|---|---|---|---|---|---|
| sim | 0.96–0.97 | 0.81–0.85 | 0.56–0.79 | **0.62–0.68** | 0.75–0.84 | 0.88–0.97 | 0.81–0.95 |
| reference | 1.00 | 0.99 | 1.00 | 0.98 | 0.98 | 0.98 | 0.93 |

### 3.4 Where ep31's score is lost

Counterfactuals with the official-style scorer, mean of 5 rollouts [M-GT]:

| simulated trajectory with … replaced by our reference | AUC | sweeper / rack |
|---|---|---|
| nothing (as evaluated) | **0.767** | 0.784 / 0.750 |
| **the sweeper at frame 0 only** (removes the first-step tip from the alignment) | **0.840 (+0.074)** | 0.870 / 0.811 |
| sweeper f0–25 (perfect rest) | 0.843 | — |
| sweeper grasp window f25–48 | 0.770 (+0.004) | — |
| sweeper lift f48–62 | 0.769 (+0.003) | — |
| **sweeper scrub f62–185** | 0.805 (+0.039) | — |
| sweeper second lift and place f185–245 | 0.766 (−0.001) | — |
| sweeper end f245–290 | 0.758 (−0.009) | — |
| frame 0 + scrub | 0.852 (+0.085) | — |
| sweeper, all frames | 0.872 | — |
| rack, all frames | 0.791 | — |
| the whole reference | 0.8525 | 0.9325 / 0.7724 |

**About 85% of the recoverable loss is the start transient.** The scrub contact phase takes about 0.04. Grasp, lift,
carry and place take ≤ 0.004. The rack's own loss (reference 0.772, floor 0.758) is perception and registration, not
simulation.

### 3.5 Scrub offset

Measured [M]:
- During the strokes the simulated brush rides 1.4–1.7 cm higher than our reference.
- At the reference's frame 0 the brush already overlaps the rack hulls (§3.2). During the strokes the brush is down
  among the dividers again, where the rack's hulls fill the gaps up to their CoACD tolerance of 12.7 mm (note 19).
- At the bottom of the strokes **our reference itself puts the brush into the rack** (`f0_overlap.py`):

  | frame | inside the rack's true mesh | inside the rack's CoACD hulls | brush lowest point |
  |---|---|---|---|
  | f100 | 8.3% of brush samples, max 7.3 mm | 12.6%, max 9.6 mm | 3 mm below the table top |
  | f135 | 13.4%, max 7.5 mm | 16.6%, max 10.1 mm | 3 mm below |
  | f165 | 7.5%, max 6.5 mm | 11.3%, max 8.9 mm | 3 mm below |
  | f250 (put back) | 9.2%, max 9.0 mm | 12.2%, max 7.9 mm | 3 mm below |

- [I] A rigid brush cannot follow this; it rides on top. Two causes, in about equal parts:
  - **The reference and mesh:** real bristles are compliant and enter the divider gaps. Our rigid mesh and perceived pose
    put about 7 mm of the brush inside the true rack.
  - **Hull inflation:** the hulls add about 2–3 mm depth and 4% more surface.
- So a better rack collision geometry removes only part of the scrub offset.

### 3.6 Verdict and hypotheses for ep31

- **It is not a grasp problem.** The grasp-lock reference plus fine-tune acquires and carries the sweeper in 5 of 5
  rollouts. The loss is the **frame-0 collision overlap between the sweeper and the rack's convex hulls**. It ejects the
  sweeper 11.3° in the first control step, and the scorer turns that into a scene rotation.
- **Needed fix:** collision geometry and start state consistent with the observed pose. Options:
  - the rack split into ≤ 120 mm parts (note 19: sweeper-in-rack 2.4–3.1 mm instead of 10.4–15.3 mm);
  - or a start-pose depenetration that keeps the observed pose.

  Settling the sweeper to wherever the hulls push it would not help: the scorer would then align on a wrong pose. No
  designed grasp is needed. The left-hand rack hold is not needed either: the simulated rack moves ≤ 1.9 cm.
- **Secondary fix (≤ +0.04):** keep the reference brush out of the rack's true mesh during the strokes. Today it is up
  to 7.5 mm inside (§3.5).

Hypotheses:
- **H31-1: consistent start geometry recovers most of the loss.** With split rack hulls (or another start-consistent
  geometry), the sweeper's first-step rotation is < 3° and the 5-evaluation mean of ep31 is ≥ 0.82 (counterfactual
  0.840).
  - Falsified if the rotation stays > 3° or the mean is < 0.80.
- **H31-2: the scrub offset comes from reference–rack interpenetration.** The +1.4–1.7 cm offset comes from our
  reference putting the brush up to 7.5 mm inside the true rack (and 10 mm inside its hulls) at the bottom of the
  strokes. Projecting the brush's reference path out of the rack's true mesh (a GT-free contact constraint on the
  reference), together with split hulls, brings the scrub-phase dz below 0.5 cm.
  - Falsified if dz stays > 1 cm.
  - Expected gain ≤ +0.04 (counterfactual).
- **H31-3: the grasp needs no change.** Under H31-1, the grasp/lift/carry phase scores stay within 0.01 of today's.
  - Falsified if they drop: that would show the tip was hiding a grasp weakness.

## 4. Cross-episode finding: slot 0's first-step jump

Measured [M], first recorded frame vs our reference, slot 0 (r1 of every public run in the store):

| run | slot 0 | first-step jump |
|---|---|---|
| ep31 grasp-lock | mini_sweeper | **1.07 cm / 11.3°** |
| ep24 grasp-lock | wooden_piece_1 | 0.77 cm / 5.3° |
| ep18 grasp-lock, `mc` reference (rounded sweeper) | mini_sweeper | 0.56 cm / 3.8° |
| ep18 settled `mckfid` / E1 | mini_sweeper | ≤ 0.06 cm / 0.1° |
| ep27 / ep26 | plastic_dish_rack | 0.9–1.07 cm / 1.7–2.6° |
| ep12 | blue_cup | 0.06–0.24 cm / 0–1.3° |
| ep2, ep21, ep39 | — | ≤ 0.10 cm / ≤ 0.6° |
| ep24 standard (organisers' meshes) | wooden_piece_1 | 1.0 cm / 0.4° (a 1 cm drop) |

[I] The jump can be measured without ground truth from any zero-action trace, so it can be a **pre-training gate**.

## 5. Commands

Scripts are in `docs/research/grasp/audit-boards-rack-scripts/`. Run them with the scratchpad venv (`python -I`). KIT is
the local kit.

```
trace_audit.py <ref_gl_ilc.parquet> <zero.npz> meshes/library_v3 --every 5 --json out/ep24_zero_audit.json
human_board.py <perc2mcs processed parquet> meshes/library_v3 2 0:60          # human fingertips vs board
robot_board.py / robot_sd.py <ref_gl_ilc> <zero.npz> meshes/library_v3 wooden_piece_1 left 0,4,12,20,24
wrist_err.py <ref_gl_ilc> <zero.npz> 0,4,...
ref_low.py <ref> meshes/library_v3 <frames> 0.600                             # reference float above table
overhang.py <ref> meshes/library_v3 0.01,0.05,0.3005 <frames>                 # vs simulated table disc
rollout_tl.py KIT <frames> <rollout parquets>; seg_err.py KIT 0 '<windows>' <rollouts>
rollout_gt.py KIT <public ep parquet> meshes/library_v3 '<windows>' <rollouts> # [GT] per-phase proxy
cf_score.py KIT t3 31 meshes/library_v3 '<specs>' <rollout dirs>             # [GT] official-style counterfactuals
f0_overlap.py <ref_gl_ilc ep31> meshes/library_v3 audit/hulls/plastic_dish_rack.npz 0,10,20
board_wrench.py <ref_gl_ilc ep24>; mocap_tl.py / mocap_tl2.py (GT timelines); thick.py (board thickness)
```

`t3/` is the public scans plus `ep{24,31}.parquet` (symlinks). The CoACD hulls in `scratchpad/audit/hulls/` were built
earlier with Newton's settings (`audit/hulls.py`). The simulator's own hulls can differ by platform (note 19).

## 6. Overlap measurements, ep31 (our reference, no GT)

Sweeper surface samples (4000) inside the rack:

| frame | inside true mesh (%, max mm) | inside CoACD hulls (%, max mm, p95 mm) | sweeper lowest z (table 0.600) |
|---|---|---|---|
| f0 | 3.3%, 6.1 | 6.8%, 7.7, 5.5 | 0.6003 |
| f10 | 3.4%, 4.8 | 6.7%, 7.9, 5.5 | 0.5992 |
| f20 | 6.4%, 7.3 | 8.2%, 10.9, 7.1 | 0.6002 |
| f100 | 8.3%, 7.3 | 12.6%, 9.6, 7.1 | 0.5970 |
| f135 | 13.4%, 7.5 | 16.6%, 10.1, 8.2 | 0.5969 |
| f165 | 7.5%, 6.5 | 11.3%, 8.9, 6.7 | 0.5973 |
| f250 | 9.2%, 9.0 | 12.2%, 7.9, 6.8 | 0.5968 |

## Sources

- [L1] Bimbo et al., "Exploiting Robot Hand Compliance and Environmental Constraints for Edge Grasps", Frontiers in
  Robotics and AI 6:135, 2019. https://www.frontiersin.org/articles/10.3389/frobt.2019.00135/pdf (opened).
  - Two slide-to-edge strategies; 320 trials with 16 objects.
  - The object should protrude about one third of its length.
  - Continuous Slide and Grasp suits small objects (credit card); Pivot and Re-Grasp suits large ones (big book).
  - Mean success is 86% with the classifier-chosen strategy.
  - It quotes humans as grasping flat objects "with a flip or a slide-to-edge grasp (Puhlmann et al., 2016)".
  - It quotes Eppner et al. (2015) that "humans increase their use of an environmental constraint in response to
    perceptual uncertainty".
- [L2] Hang, Morgan, Dollar, "Pre-Grasp Sliding Manipulation of Thin Objects Using Soft, Compliant, or Underactuated
  Hands", IEEE RA-L 4(2):662–669, 2019. https://www.eng.yale.edu/grablab/pubs/Hang_RAL2019.pdf (opened). A thin object
  is slid to a table edge and grasped from the side; planning success > 90% within 20 s and 99% at 60 s.
- [L3] Eppner, Deimel, Álvarez-Ruiz, Maertens, Brock, "Exploitation of environmental constraints in human and robotic
  grasping", IJRR 34(7):1021–1038, 2015. https://depositonce.tu-berlin.de/items/ec161341-6477-4b57-927f-43fb98fa3942.
  **The full text could not be opened** (host unreachable from this session). It is cited only through [L1]'s quotation.
- [L4] Feix, Romero, Schmiedmayer, Dollar, Kragic, "The GRASP Taxonomy of Human Grasp Types", IEEE THMS 46(1):66–77,
  2016. https://www.eng.yale.edu/grablab/pubs/Feix_THMS2016.pdf (opened). 33 grasp types; Parallel Extension (#22) is
  pad opposition with the thumb between abduction and adduction; Lateral (#16) is side opposition.
- [L5] Zhou, Held, "Learning to Grasp the Ungraspable with Emergent Extrinsic Dexterity", CoRL 2022.
  https://arxiv.org/abs/2211.01500 (opened). Model-free RL learns to push the object against a wall before grasping;
  78% real-world success.
- In-repo:
  - `docs/research/notes/24-physics-aware-grasp-design.md` (condim 3, μ_d, finger kp);
  - `19-collision-hulls.md` (rack hull tolerance, sweeper/rack depths, S120);
  - `23-grasp-controller-and-rl-handoff.md`;
  - `25-support-consistent-meshes.md`.
