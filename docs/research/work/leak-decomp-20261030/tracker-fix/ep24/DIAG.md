# ep24 tracker diagnosis: the boards are tracked well, the camera (VO) jumps (30 Oct 2026, ~22:45–23:45 UTC)

ep24 is the public twin of eval 25: two near-identical wooden boards. One is slid off the table edge, stood on edge,
and the other is slotted into it to form a standing cross. This is a public-episode oracle diagnostic: mocap and scans
are read only to score and diagnose, and every proposed fix is GT-free. CPU only on this VM, $0, no GPU, no Kaggle,
no commit. Labels: [M] measured, [E] estimate, [H] hypothesis.

## Verdict
- **The starting hypothesis is refuted [M].** It said the error comes from 180° flips and identity swaps of the
  near-identical boards, especially while they are slotted together. Neither happens in either arm:
  - A 180° flip about any of the three board axes never fits better than the track, in any frame, for either board,
    P_o or P_s (0 of 275 frames). Flipped poses sit 6.5–14.8 cm (median ADD) from mocap; the tracks sit 0.4–1.0 cm
    away after one world alignment.
  - The rotation error stays ≤ 5.5° (board 1) and ≤ 6.6° (board 2) in every frame, median 1.9–3.0° (P_o and P_s).
  - There is no identity swap. Board 2 is tracked at 0.34 cm before anything moves, and the slot-0 board at 0.09 cm.
    In the slotted phase (f164–274, surfaces touching) both boards are as accurate as anywhere else: 0.26–1.05 cm
    after a world alignment.
- **The error is the camera, not the object tracker [M].** At f33–51 our visual odometry (VO) moves the perception
  world by about 2.4 cm (mocap axes ≈ +1.1 x, +0.4 y, +2.1 z, mostly upward), and that offset is held to the end.
  - Both boards shift by the same vector at the same frames, and so do P_o and P_s, which share one camera.
  - Board 2 is untouched and static in mocap until f110 (≤ 0.2 cm). Yet in our world it moves 2.0–2.5 cm, starting
    exactly at the VO keyframe switches f36, f38, f40 and f49 (steps 0.41, 0.28, 0.66 and 1.05 cm).
  - The VO-free relative pose of board 2 in board 1's frame matches mocap to a median 0.94 cm (P_o) and 0.50 cm (P_s).
    The camera implied by each board separately (mocap pose × our camera-frame track) agrees between the two boards to
    a median 0.5–0.9 cm, and both differ from our VO by about (1.0–1.2, 0.0–0.5, 1.9–2.6) cm from f50 on.
  - With one rigid world transform fitted over all frames (oracle), the episode scores 0.962 (P_o) and 0.973 (P_s).
    With the common-mode translation removed per frame (oracle), it scores 0.999 for both. The kit's frame-0
    alignment gives 0.8105 and 0.8495.
  - ep24's VO is unusual: 17 keyframes, 7 switches within 25 frames (f27–49) and a minimum gap of 2 frames. On the
    other 19 public episodes there are 2–16 keyframes and at most 4 switches per 25 frames.
  - Overlays: `ep24_board2_static_zoom.png` (the static board 2: the green mocap outline seen through our VO camera
    drifts off the real board at f45–100, while the track (red) and the corrected camera (cyan) stay on it) and
    `ep24_vo_overlay_grid.png` (both boards, f0–270).
- **Error source, in the task's terms:** a jump at an event (the VO keyframe burst while board 1 is lifted and tilted
  close to the camera, f33–51), then a held offset. It is not frame-0 initialisation, not slow drift, not a flip or a
  swap, and not occlusion or nesting. The static object "wanders" only because the camera does.
- **What this changes in the leak readings [M]:**
  - L3 ("tracker given a true template") on ep24 (0.151) is almost all camera: 0.149 of it is common-mode translation.
    It is shared by every arm on that camera, including the eval-like P_o.
  - Phase-1 H1 ("frame-0/init error on near-static objects") is refuted for ep24. X\*_trk recovers 0.986 only because
    a 1.7–1.8 cm constant body offset on slot 0 shifts the kit's frame-0 pin, so the 225 post-jump frames land on target.
    It is not a frame-0 error.
  - Two older observations are the same camera error seen per object:
    - 21 Oct: "boards 2–2.5 cm too high whenever not moved";
    - Tier A A3: rest settle gives +0.055 on ep24.
- **Fixes (§4):**
  - F1: a robust VO in perc2 (the root cause). Untested here: it needs the depth caches or the b/c videos.
  - F2: a GT-free keyframe-gated anchor correction, tested on CPU here.
    - On ep24, P_o goes 0.8105 → **0.9939** \* and 0.8117 → **0.9936** lib (P_s 0.8494 → 0.9835).
    - As an always-on step it is **falsified** by its own no-harm rule on the 20 public episodes: ep21 −0.043,
      ep12 −0.022 lib, ep13 −0.017.
    - Applied only when the correction reaches ≥ 1 cm (a post-hoc gate), it changes nothing but ep24: +0.009 mean.
    - It also depends on a hand-distance threshold (3 cm works, 5 cm does not).
    - So it is a fallback and a detector, not the fix.
  - F3: a table-plane camera constraint at VO keyframes. Untested; proxy: the height-only part of the F2 correction
    gives 0.9475.
  - Order: F1 + F3 public test on one CPU box (≈ $0.3–1, owner go-ahead), with F2-gated as cross-check and fallback.
    Expected LB ≈ +0.002 to +0.008, central +0.004 [E] (§4.3).

## 1. Inputs and commands (this VM, repo a960523 + `scripts/` here)
- Tracks: `runs/20261030-orcP1c-87fc869/results/leak_p1/ep24/{perc2,perc2rep,perc2scan}/poses_world_vo.npz` plus
  `perc2/poses.npz`.
  - These were already downloaded to `$S/leak/p1/runs/...` (`S` = the session scratchpad); nothing new was downloaded.
  - P_o and its repeat P_o2 are bit-identical (md5 9c40fe26…), so the repeat noise is 0. P_s is f83e3c55….
  - The refine-input track `refine/in/ep24` (25 Oct, library_v2 boards = v3) scores identically to P_o.
- The other inputs:
  - VO keyframes: `$S/refine/in/ep24/vo.json`. The cameras of all arms are identical (Phase-1 `camera maxdiff 0.0`).
  - Hands: `$S/refine/in/ep24/hands_refined.npz`; the GT-free rules use our own joints.
  - Mocap: `$S/map/scoring/t3/ep24.parquet`.
  - X\*_geom: `../../tierA/xstar_geom.json`.
  - Video: cam a, `$S/hfds/.../episode_000024.mp4`.
- Scoring: the kit chain of `tools/xstar_fit.py` (`score_track`). \* = X\*_geom with scan points, lib = X_kit.
  - Boards have no symmetry axis, so the kit pins the whole scene to slot 0's (board 1) full frame-0 pose.
  - Reproduces Phase 1 [M]: P_o \* 0.8105, lib 0.8117; P_s \* 0.8494.
- Commands (`PY=$S/map/scoring/venv/bin/python`, from `$S/leak/diag_24`; script copies in `scripts/`):
  1. `$PY -I scripts/diag24.py out/diag24.json`: per-frame errors (kit and best-world), flips, swaps, phases, hands,
     contact. Compact copy: `diag24_summary.json`.
  2. `$PY -I scripts/camcheck24.py out/camcheck24.json`: VO-free relative pose; implied camera per board.
  3. `$PY -I scripts/vo_oracle_screen.py out/vo_oracle_screen.json`: common-mode screen of the 13 two-object episodes.
  4. Rule v1 (falsified): `$PY -I scripts/vo_anchor_test.py OUT [eps]`, log `vo_anchor_v1_partial.log`.
     Rule K on all 20 episodes, three processes:
     `$PY -I scripts/vo_anchor_test2.py out/vo_k_A.json 0,2,11,18,23,26,27` (likewise B = 12,13,21,39,40,41 and
     C = 22,24,31,42,43,44,45; about 12 min). Then `python3 -I scripts/k_table.py` merges them into `vo_k_all.json`.
     On ep24 alone: `vo_k_ep24.json`.
  5. `$PY -I scripts/normal_proxy24.py` (F3 proxy); `$PY -I scripts/seg_fixed24.py` (per-phase errors after F2).
  6. `$PY -I scripts/overlay24.py png` and `scripts/overlay24_zoom.py png` (overlays).

## 2. Error per object and phase [M]
What happens, from mocap and cam a:
- Board 1 (slot 0) is gripped and slid toward the table edge from f8, lifted and tilted from f20 (+19 cm, 25°), turned
  on edge by f75–85, and set down standing at f85–97. A hand steadies it until about f240.
- Board 2 rests untouched until about f105; a forearm lies over it at f40–80, but no hand joint comes nearer than 9 cm
  in f33–100. It is lifted and turned at f111–163, slotted into board 1 at f164–219 (surfaces in contact,
  gap < 0.5 cm), and the cross stands from f220. The hands leave at about f240.

Kit view (the scorer's own frame-0 alignment). Cells: ADD median/max cm, median translation cm and rotation °, AUC.
"bw" = ADD median after one rigid world transform fitted over all frames (oracle).

| phase | board 1: hand cm, moving frames | board 1 P_o | board 1 P_s | b1 bw | board 2: hand, moving | board 2 P_o | board 2 P_s | b2 bw |
|---|---|---|---|---|---|---|---|---|
| A f0–32, before the jump | 1, 25/33 | 0.59/2.13, 0.6 cm 1.2°, 0.975 | 0.49/2.04, 0.985 | 2.52 | 27, 0/33 | 0.34/0.38, 0.3 cm 1.0°, 1.000 | 0.41/0.57, 1.000 | 2.10 |
| **B f33–51, VO keyframe burst** | 0, 19/19 | 1.85/2.26, 1.8 cm 1.1°, 0.914 | 1.75/2.16, 0.938 | 1.06 | 15, 0/19 | **1.52/2.17**, 1.5 cm 2.3°, 0.938 | 1.22/1.79, 0.961 | 1.03 |
| C f52–110, b1 stood on edge, b2 static | 1, 42/59 | 2.83/4.29, 2.8 cm 2.3°, 0.779 | 2.32/3.71, 0.810 | 0.61 | 14, 0/59 | **2.35/2.85**, 2.4 cm 1.9°, 0.817 | 2.05/2.46, 0.865 | 0.36 |
| D f111–163, b2 lifted and turned | 1, 7/53 | 3.08/3.38, 3.1 cm 2.5°, 0.735 | 2.58/2.91, 0.812 | 0.83 | 1, 53/53 | 2.45/2.91, 2.4 cm 1.8°, 0.824 | 2.32/2.97, 0.834 | 0.51 |
| E f164–219, slotting (contact) | 1, 0/56 | 3.30/3.67, 3.3 cm 1.7°, 0.721 | 2.75/3.06, 0.808 | 1.05 | 1, 33/56 | 2.29/2.65, 2.3 cm 2.1°, 0.815 | 2.36/2.72, 0.812 | 0.26 |
| F f220–274, cross stands, release | 17, 0/55 | 3.25/3.55, 3.2 cm 2.6°, 0.690 | 2.82/3.10, 0.801 | 1.04 | 11, 0/55 | 2.37/2.60, 2.4 cm 2.9°, 0.812 | 2.51/2.72, 0.812 | 0.44 |
| whole episode | | 0.7736 | 0.8382 | 0.962 (both) | | 0.8473 | 0.8607 | 0.973 (P_s) |

- Hand distance is the nearest hand joint (`hands_refined`, mapped to mocap) to the board's surface. It is the
  occlusion proxy.
- The bw column is high in phase A because one world transform has to split the 2.4 cm step: it moves the
  pre-jump frames off by about 2 cm.

After the GT-free camera correction F2 (rule K, the same scoring), the per-phase median ADD is:
- P_o: 0.59 / 0.71 / 0.77 / 0.63 / 0.82 / 0.71 cm (board 1) and 0.34 / 0.40 / 0.46 / 0.83 / 0.68 / 0.41 cm (board 2);
- P_s: board 1 0.49–0.88 cm and board 2 0.41–1.26 cm;
- per-board AUC: P_o 0.992 / 0.996, P_s 0.992 / 0.975 (`seg_fixed24.py`).

In the slotting phase E, P_o's maximum is 1.14 cm. The tracker loses nothing measurable to the slotting, the
occlusion or the edge-on views.

Where the error comes from [M]:
- **Board 2 static: a jump at the VO keyframe burst, then a held offset.**
  - The kit-view error is 0.34 cm until f33, 1.5 cm by f42 and 2.1 cm by f50. It then stays 2.0–2.9 cm to the end,
    whatever board 2 does (rest, lift, slotting, release).
  - In our world, board 2's centroid steps by 0.41 / 0.28 / 0.66 / 1.05 cm exactly at the keyframe frames
    36 / 38 / 40 / 49 (`vo.json` keyframes 0, 27, 32, 36, 38, 40, 44, 49, 61, 76, 89, …).
  - Between keyframes it moves ≤ 0.48 cm per frame.
- **Board 1: the same jump.** Its kit error is ≤ 0.5 cm at f0–17 and 0.6–1.3 cm while it is slid and lifted
  (f18–35). It then rises to 1.8 cm (f40) and about 3 cm (f60 on).
  - The error vectors of the two boards agree. At f100 they are (1.20, −0.02, 2.57) and (1.09, 0.19, 2.20) cm; at
    f270, (1.66, 0.17, 2.68) and (1.35, 0.23, 1.89) cm.
  - [H] The extra ~0.6 cm on board 1 comes from its distance to the frame-0 pin combined with a 0.5–1° camera
    rotation error (kit pin vs best world: 0.49° P_o, 1.24° P_s).
- **Frame-0 initialisation is fine:** board 2 is at 0.30 cm (P_o) and 0.39 cm (P_s) at frame 0, rotation 1.4° and 1.6°.
  Board 1 is exact by construction (slot 0 is the pin). The only pre-jump excursion is board 1 at f18–25 (1.2–1.3 cm
  while it is slid fast toward the edge).
- **Repeat noise:** none. P_o2 is bit-identical to P_o.

## 3. The hypothesis against the evidence
| claim of the hypothesis | test | result [M] |
|---|---|---|
| a 180° flip of a board | per frame, ADD of the track turned 180° about each board PCA axis (long / mid / normal) vs as tracked | flipped better in **0/275** frames, both boards, both arms. Median as tracked 0.42–0.96 cm (bw) vs flipped 6.5 / 11.8–12.3 / 14.2–14.6 cm |
| an identity swap | centre of each track vs each mocap board; board-2 error at rest | no swap. "Other board closer" happens only in the slotted cross (f164+), where the two centres coincide within 0.3–6 cm, and there the track's own error is 0.26–1.05 cm (bw). Board 2 is 0.34 cm off at f0–32 |
| errors grow when the boards are slotted and occlude each other | phase E/F vs others; bw and after-F2 errors | no. Slotting is as accurate as rest: P_o after F2 0.82 / 0.68 cm median (E) vs 0.59 / 0.34 cm (A). The kit-view rise sits at f33–51, 110 frames before the slotting |
| the scans (P_s) would fix a template-dependent flip | P_s vs P_o | P_s carries the same jump (it shares the camera). L2 here is only +0.039 |

Two side facts, not causes:
- A forearm lies over board 2 at f40–80 (`ep24_board2_static_zoom.png`), and the board track stays on the board.
- Eval 25's known identity risk (note 15) is real for the stored 25 Oct eval track. It is already handled by
  `pipeline/identity_fix.py` (refine S0), which keeps both public ep24 tracks as they are.

Mechanism [H]:
- perc2's camera is a chain of keyframe SIFT + depth PnP (`perc2.py:141–175`). There are no masks, and a frame is
  matched only to the latest keyframe.
- In f27–49 the head turns while board 1 (a large, textured, close object) is lifted and tilted through the view, and
  hands fill the lower image. Inliers drop below `KF_MIN=120` again and again: 7 keyframe switches in 23 frames.
- Each switch re-bases the chain on a pose estimated partly from features on moving surfaces (board 1, hands, the
  forearm). The step errors (0.3–1.0 cm each) accumulate and are never closed back to frame 0.
- What would falsify this: re-running only the VO with object and hand masks and earliest-keyframe matching (F1). If
  the board-2 step at f33–51 persists (≥ 1.5 cm), the cause is elsewhere: depth scale at those keyframes, or rolling
  shutter.

## 4. Fixes (GT-free), the public tests that would falsify them, eval exposure and value

### F1 — a robust camera in `pipeline/perc2.py` (root cause) [H, untested]
- **What** (camera block `perc2.py:141–175` and the world composition at `:495`):
  1. Match each frame first against the earliest keyframes that still give ≥ `KF_MIN` inliers (frame 0 first), and
     open a new keyframe only when none does. This is the "earliest usable keyframe" VO of the 13 Oct perc4. It
     closes the loop whenever the view returns.
  2. Run the VO after tracking. Drop SIFT keypoints inside our own tracked objects' rendered silhouettes (nvdiffrast
     is loaded; dilate 15 px) and inside the hands' 2-D hulls (`uv_a` from `hands_refined`, mapped to rectified c).
     Keep a first VO pass only for TRACK_GUARD's plane test.
  3. Optional: replace the chain with the stereo keyframe-map VO of `docs/research/work/17/vo17.py`. It is CPU only,
     25–60 s per episode, and needs only the b/c videos. Its measured drift on ep12 was 3.8 mm median.
- **Public test** (CPU only, no GPU):
  - Re-run only the VO on all 20 public episodes, with the Phase-1 depth caches (`cache/depth/public/ep<N>/`, one
    single-file pull each) or with vo17 on the b/c videos.
  - Recompose `poses_world_vo = W_C' · cam_T_obj` from the Phase-1 `poses.npz` (P_o) and from P_s, then score \* and
    lib.
  - **Pass:** ep24 P_o \* ≥ 0.95 (now 0.8105); the oracle common-mode error (`vo_oracle_screen.py`) on ep24 ≤ 0.8 cm
    median (now 2.72); no episode's common-mode error up by more than 0.3 cm; no episode below −0.02 in \* or lib.
  - **Falsified if** ep24 P_o \* < 0.90 with masks and earliest-keyframe matching.
  - Cost [E]: about $0.3–1 on a Vast CPU box (20 depth caches ≈ 20 GB of pulls; HF 429 risk), or about $0.3 for vo17
    with 40 public video pulls. 1–2 h. Needs the owner's go-ahead.
- **Eval exposure:** every eval episode runs the same VO. A GT-free pre-screen of the existing eval outputs, to run
  after the public gate:
  - a keyframe burst in perc2's own `vo.json` (≥ 4 switches within 25 frames: public ep24 7, ep22 4, ep41 4, the rest
    ≤ 3);
  - plus F2's correction magnitude (> 1 cm).

  Candidates from note 15, where large objects move close to the camera during head motion: 25 (boards lifted toward
  the camera), 5 (pot fills a third of the image), 1 (pot waved with blur, f132–182), 28 (pot rolled about 140°/s), 20
  (pitcher at the image border) and 19 (dust-pan dump).
- **LB [E]:**
  - If eval 25 has ep24's jump: ΔR ≈ +0.18, so ΔT ≈ a·S·ΔR = 1.025 × 0.850 × 0.18 ≈ 0.157, which is
    **+0.0058 to +0.0078 LB** (c 0.74–1.0). Eval 25's S_e is 0.850 in H5, so the plan's conversion applies.
  - Whether eval 25 has it is unknown. The other twin of the same script, ep23, has a clean camera (4 keyframes,
    common-mode 0.33 cm with P_s), so p ≈ 0.2–0.5 [E], an expected +0.001 to +0.004.
  - Across all evals, the public base rate is 1 clear case in 13 two-object episodes, so about 1–2 of 20 evals
    [E, weak]. **Expected total +0.002 to +0.008 LB, central ≈ +0.004** [E].
  - Upside: F1 also removes the sub-cm VO wobble seen as common-mode 0.4–1.6 cm on other episodes (ep11, ep13, ep18,
    ep26, ep27; partly tracker, so not separable here).

### F2 — keyframe-gated anchor correction, gated to gross jumps (post-processing; new refine step S6) [M on public; always-on form falsified]
**Rule K** (`scripts/vo_anchor_test2.py`). It reads only our tracks, `world_T_cam`, perc2's `vo.json` keyframes, our
`hands_refined` joints and our meshes:
- **Anchor windows.** An object is an anchor:
  - from frame 0 while no hand joint is within D_H of our mesh at our pose;
  - and in later rest windows, which start after REST_MIN untouched frames with apparent step < 0.15 cm per frame
    and continue while untouched;
  - but not while it is within 1 cm of a non-anchored object.
- **Camera correction.** Only within ±KW frames of a VO keyframe switch, the anchors' mean displacement from their
  window-start position is absorbed into a camera translation c(t), when 0.2 cm < |r| ≤ 1.5 cm. Two or more anchors
  must agree within 0.5 cm, and |r| > 1.5 cm ends the window as real motion.
- **Away from switches** an anchor's drift is booked to the object (its reference follows it).
- **Output.** All objects' world positions get + c(t). Translation only: the rigid variant was worse.
- **Episode gate (added after the 20-episode run, §4.2).** Apply c(t) only if max |c| ≥ 1 cm; otherwise leave the
  episode untouched. Small corrections were net harmful, and a VO jump worth fixing is ≥ 1 cm.

Why the keyframe gate (v1 → v2), all [M]:
- v1 corrected continuously and was falsified on ep2 (−0.087 \*). There a lid slides 4 cm while no hand is detected
  near it, and v1 read that as camera motion.
- v1 also showed that sub-mm corrections move threshold-clustered scores by ±0.01–0.02. A 0.5 mm shift after f40
  moves ep0's P_o lid AUC by +0.009 to −0.013 (episode +0.004 to −0.006), because its error sits near a threshold.
  Hence the 2 mm dead-band.

**ep24 [M]** (`vo_k_ep24.json`; D_H 3 cm, REST_MIN 5, KW 2):
- P_o \* 0.8105 → 0.9939 and lib 0.8117 → 0.9936; P_s \* 0.8494 → 0.9835.
- This is above X\*_trk (0.986), the best constant-offset oracle.
- The correction is 15 increments, from f34 to f97, ending at 2.6 cm. 2.1 cm of it lies along our table normal.

**Threshold sensitivity on ep24 [M]** (`vo_k_ep24.json`; R\* after the rule, Δ vs 0.8105 / 0.8494):

| D_H | REST_MIN | KW | P_o \* (lib) | P_s \* | correction at the end |
|---|---|---|---|---|---|
| **3 cm** | **5** | **2** (primary) | **0.9939 (0.9936), +0.183** | 0.9835, +0.134 | 2.63 cm (P_o) |
| 3 cm | 5 | 1 | 0.9385 (0.9420), +0.128 | 0.9485, +0.099 | 1.59 cm |
| 3 cm | 8 | 2 | 0.9939 (0.9936), +0.183 | 0.8494, 0 (no window before the jump) | 2.63 cm / 0 |
| 5 cm | 5 | 2 | 0.8227 (0.8260), +0.012 | 0.8540, +0.005 | 0.28 cm |
| 5 cm | 8 | 2 | 0.8105, 0 | 0.8494, 0 | 0 |

- With D_H = 5 cm, a hand passing at 3.4–4.2 cm (f25–30, not touching: mocap board 2 is static) ends board 2's
  window just before the jump. So the rule's success hinges on one threshold. That is why F1 is the primary fix.

**20 public episodes [M]** (all arms; `vo_k_all.json`): see the table in §4.2 below.

**Where:** a new step S6 in `pipeline/refine.py`, run first (before S1/S2), logged in `pose_opt.json` with every
absorbed step.
- It differs from the existing S4 "pre-contact drift hold". S4 holds only the anchor object at its frame-0 pose; on
  ep24 that would fix board 2 but leave board 1's 3 cm error. S6 corrects the camera for every object and every later
  frame.

**Public test that would falsify it** (pre-register before the run; CPU for references, GPU for rollouts):
- Reference level, all 20 public episodes, P_o and refine P, with the committed code. **Pass:** ep24 Δ\* ≥ +0.10;
  mean Δ ≥ +0.005 in \* and in lib; no episode < −0.01.
  - **Falsified if** any episode loses more than 0.01 in lib, or ep24 gains less than +0.10.
  - **Run here [M]:**
    - the always-on rule **fails** (ep21, ep12, ep13; §4.2);
    - the ≥ 1 cm episode gate passes (ep24 +0.183 / +0.182, all others 0, mean +0.009), but that gate was set after
      seeing these data.
  - The independent check is F1: if a masked, loop-closed VO also shows ep24's 2–2.6 cm step and no ≥ 1 cm step on
    the other 19 episodes, the gate is consistent with the camera. If F1 finds ≥ 1 cm jumps that F2 misses or invents,
    F2 is dropped.
- Rollout: twin ep24, eval 25's packed recipe (c25s42 standard learner as Phase 3, or grasp lock as Phase-2 c1),
  seeds 42 and 43, NREP 10, with vs without S6 on the same Phase-1 bundle.
  - **Pass:** seed-mean rollout ADD-AUC vs mocap +0.05 or more.
  - Cost [E]: about $6–7 for two standard-learner trainings, or about $2.6 for grasp lock.
- **Before eval use:** run S6 on the stored eval tracks (GT-free). List every absorbed step with its keyframe and
  anchor. Overlay-QA every corrected episode with `pipeline/track_overlay.py` (the static anchor must stay on its
  image). Retrain only episodes with |c| ≥ 1 cm.

**Eval exposure / LB:** the same episodes and value as F1, but only where an untouched object exists during the jump.
On eval 25, board 2 is untouched until about f161 (note 15), which is favourable. Expected +0.001 to +0.004 LB [E].

### F3 — a table-plane camera constraint at keyframes (`perc2.py` VO block) [H; proxy M]
- **What:** at every new keyframe, fit the support plane on that keyframe's own depth (`det_rules.table_plane`, as
  TRACK_GUARD does at frame 0). Correct the keyframe's world pose by the minimal rotation and translation that puts
  that plane onto the frame-0 plane. This fixes 3 DoF: height and tilt.
  - It needs no hands, no anchors and no thresholds tuned on ep24. The table is in view in every public frame.
- **Proxy [M]:** projecting F2's ep24 correction onto our frame-0 table normal (height only) gives P_o \*
  0.8105 → **0.9475** and lib → 0.9461 (`normal_proxy24.py`). That is 75 % of F2's gain. The in-plane part alone gives
  0.857. The real table fit adds tilt, which the proxy does not.
- **Public test:** as F1 (CPU, depth caches). **Pass:** ep24 \* ≥ 0.93 and no episode < −0.01. **Falsified if** ep24
  \* < 0.88, which would mean the keyframe planes do not register the jump (e.g. the table is mostly occluded at
  f33–51).
- **Eval exposure / LB:** as F1. It is the cheapest robust part; the in-plane 25 % remains for F1/F2.

### 4.2 Rule K on all 20 public episodes [M]
Per episode, primary setting (D_H 3 cm, REST_MIN 5, KW 2), from `vo_k_all.json` (`scripts/k_table.py`):

| ep | VO keyframes | P_o \* base | P_o Δ\* / Δlib | absorbed steps, correction at end (cm) | P_s \* base | P_s Δ\* | refine P Δ\* / Δlib |
|---|---|---|---|---|---|---|---|
| 0 | 9 | 0.9476 | +0.0014 / +0.0000 | 2, 0.11 | 0.0783 | +0.0000 | +0.0003 / +0.0000 |
| 2 | 5 | 0.9805 | +0.0000 / +0.0000 | 0, 0.00 | 0.9933 | +0.0000 | +0.0000 / +0.0000 |
| 11 | 4 | 0.8739 | +0.0000 / +0.0000 | 0, 0.00 | 0.9081 | +0.0000 | +0.0000 / +0.0000 |
| 12 | 3 | 0.9734 | -0.0055 / -0.0216 | 3, 0.58 | 0.9382 | -0.0292 | -0.0059 / -0.0239 |
| 13 | 3 | 0.9039 | -0.0171 / -0.0116 | 4, 0.41 | 0.9974 | -0.0092 | +0.0003 / -0.0146 |
| 18 | 2 | 0.9168 | +0.0000 / +0.0000 | 0, 0.00 | 0.9622 | +0.0000 | +0.0000 / +0.0000 |
| 21 | 6 | 0.8313 | -0.0427 / -0.0313 | 1, 0.44 | 0.9755 | -0.0131 | -0.0427 / -0.0313 |
| 22 | 7 | 0.8684 | +0.0167 / +0.0084 | 9, 0.37 | 0.9929 | -0.0040 | +0.0156 / +0.0100 |
| 23 | 4 | 0.0418 | +0.0000 / +0.0000 | 4, 0.45 | 0.9980 | +0.0009 | +0.0000 / +0.0000 |
| 24 | 17 | 0.8105 | +0.1834 / +0.1819 | 15, 2.63 | 0.8494 | +0.1341 | +0.1834 / +0.1819 |
| 26 | 4 | 0.9602 | +0.0000 / +0.0000 | 0, 0.00 | 0.9836 | -0.0109 | -0.0069 / +0.0008 |
| 27 | 5 | 0.9378 | -0.0089 / -0.0094 | 4, 0.30 | 0.9963 | -0.0227 | -0.0092 / -0.0087 |
| 31 | 6 | 0.8351 | +0.0000 / +0.0000 | 0, 0.00 | 0.8685 | +0.0000 | +0.0000 / +0.0000 |
| 39 | 8 | 0.9804 | +0.0000 / +0.0000 | 0, 0.00 | 0.9978 | +0.0000 | +0.0000 / +0.0000 |
| 40 | 3 | 0.9740 | +0.0000 / +0.0000 | 0, 0.00 | 0.9971 | +0.0000 | +0.0000 / +0.0000 |
| 41 | 16 | 0.9881 | +0.0000 / +0.0000 | 0, 0.00 | 0.9981 | +0.0000 | +0.0000 / +0.0000 |
| 42 | 8 | 0.9638 | +0.0000 / +0.0000 | 0, 0.00 | 0.9893 | +0.0000 | +0.0000 / +0.0000 |
| 43 | 10 | 0.9425 | +0.0000 / +0.0000 | 0, 0.00 | 0.9921 | +0.0000 | +0.0000 / +0.0000 |
| 44 | 7 | 0.9982 | +0.0000 / +0.0000 | 0, 0.00 | 0.9990 | +0.0000 | +0.0000 / +0.0000 |
| 45 | 13 | 0.9789 | +0.0000 / +0.0000 | 0, 0.00 | 0.9666 | +0.0000 | +0.0000 / +0.0000 |

Summary over the configurations (Δ = after − before):

| config | arm | conv | mean Δ (20) | w/o ep24 | min | max | up / down (by > 0.0005) | episodes < −0.01 |
|---|---|---|---|---|---|---|---|---|
| h3_r5_w2 | Po | \* | +0.0064 | -0.0030 | -0.0427 | +0.1834 | 3 / 4 | 13 -0.017, 21 -0.043 |
| h3_r5_w2 | Po | lib | +0.0058 | -0.0034 | -0.0313 | +0.1819 | 2 / 4 | 12 -0.022, 13 -0.012, 21 -0.031 |
| h3_r5_w2 | Pr | \* | +0.0067 | -0.0026 | -0.0427 | +0.1834 | 2 / 4 | 21 -0.043 |
| h3_r5_w2 | Pr | lib | +0.0057 | -0.0036 | -0.0313 | +0.1819 | 3 / 4 | 12 -0.024, 13 -0.015, 21 -0.031 |
| h3_r5_w2 | Ps | \* | +0.0023 | -0.0046 | -0.0292 | +0.1341 | 2 / 6 | 12 -0.029, 21 -0.013, 26 -0.011, 27 -0.023 |
| h3_r5_w1 | Po | \* | +0.0046 | -0.0019 | -0.0233 | +0.1280 | 4 / 2 | 13 -0.023, 22 -0.019 |
| h3_r5_w1 | Po | lib | +0.0058 | -0.0008 | -0.0152 | +0.1303 | 3 / 2 | 22 -0.015 |
| h3_r5_w1 | Pr | \* | +0.0049 | -0.0016 | -0.0185 | +0.1280 | 1 / 3 | 13 -0.011, 22 -0.018 |
| h3_r5_w1 | Pr | lib | +0.0058 | -0.0008 | -0.0120 | +0.1303 | 2 / 3 | 22 -0.012 |
| h3_r5_w1 | Ps | \* | +0.0018 | -0.0034 | -0.0384 | +0.0991 | 2 / 6 | 13 -0.038, 27 -0.016 |
| h3_r8_w2 | Po | \* | +0.0063 | -0.0030 | -0.0427 | +0.1834 | 2 / 4 | 13 -0.017, 21 -0.043 |
| h3_r8_w2 | Po | lib | +0.0058 | -0.0034 | -0.0313 | +0.1819 | 2 / 4 | 12 -0.022, 13 -0.012, 21 -0.031 |
| h3_r8_w2 | Pr | \* | +0.0067 | -0.0026 | -0.0427 | +0.1834 | 2 / 4 | 21 -0.043 |
| h3_r8_w2 | Pr | lib | +0.0057 | -0.0036 | -0.0313 | +0.1819 | 3 / 4 | 12 -0.024, 13 -0.015, 21 -0.031 |
| h3_r8_w2 | Ps | \* | -0.0044 | -0.0046 | -0.0292 | +0.0009 | 1 / 6 | 12 -0.029, 21 -0.013, 26 -0.011, 27 -0.023 |
| h5_r5_w2 | Po | \* | -0.0015 | -0.0022 | -0.0427 | +0.0167 | 3 / 4 | 21 -0.043 |
| h5_r5_w2 | Po | lib | -0.0020 | -0.0028 | -0.0313 | +0.0143 | 2 / 3 | 12 -0.022, 21 -0.031 |
| h5_r5_w2 | Pr | \* | -0.0015 | -0.0022 | -0.0427 | +0.0156 | 2 / 3 | 21 -0.043 |
| h5_r5_w2 | Pr | lib | -0.0020 | -0.0028 | -0.0313 | +0.0143 | 2 / 3 | 12 -0.024, 21 -0.031 |
| h5_r5_w2 | Ps | \* | -0.0030 | -0.0034 | -0.0292 | +0.0046 | 3 / 4 | 12 -0.029, 21 -0.013, 27 -0.023 |
| h5_r8_w2 | Po | \* | -0.0020 | -0.0021 | -0.0427 | +0.0167 | 1 / 3 | 21 -0.043 |
| h5_r8_w2 | Po | lib | -0.0027 | -0.0028 | -0.0313 | +0.0084 | 1 / 3 | 12 -0.022, 21 -0.031 |
| h5_r8_w2 | Pr | \* | -0.0021 | -0.0022 | -0.0427 | +0.0156 | 1 / 3 | 21 -0.043 |
| h5_r8_w2 | Pr | lib | -0.0027 | -0.0028 | -0.0313 | +0.0100 | 1 / 3 | 12 -0.024, 21 -0.031 |
| h5_r8_w2 | Ps | \* | -0.0034 | -0.0036 | -0.0292 | +0.0000 | 0 / 4 | 12 -0.029, 21 -0.013, 27 -0.023 |

Reading [M]:
- **Rule K as an always-on step fails its own no-harm rule.**
  - Primary setting: ep21 −0.043 \*; ep12 −0.022 lib; ep13 −0.017 \* / −0.012 lib. Without ep24 the mean is −0.003.
  - The losses come from small absorbed corrections (0.3–0.6 cm). Two causes [H]:
    - the anchor's own tracking error is read as camera motion;
    - threshold churn: on ep0 a 0.5 mm shift moves the lid's AUC by ±0.01, and on ep21 one absorbed 0.44 cm step
      costs −0.043.
  - With D_H 5 cm the rule mostly does nothing (ep24 +0.012) and still loses ep21 −0.043.
- **An episode-level gate, applied post hoc, separates ep24 cleanly:** apply the correction only when it reaches
  ≥ 1 cm.
  - ep24 reaches 2.63 cm (P_s 3.08). The next largest are 0.84 (ep27 P_s), 0.71–0.73 (ep22) and 0.62 (ep12 refine P).
  - Gated, the primary setting gives P_o +0.0092 \* / +0.0091 lib mean over 20, P_s +0.0067. Every non-ep24 episode
    is exactly 0. With KW 1: +0.0064 / +0.0065.
  - This gate was chosen after seeing all 20 episodes, so it is a public fit, not a validation.


### 4.3 Eval exposure and value, all three fixes (they overlap, so they do not add up) [E]
| eval | objects | why it could share ep24's camera jump (note 15) | F1/F3 apply | F2 applies (an untouched object while the head moves) |
|---|---|---|---|---|
| **25** | boards | the same script as ep24: a board lifted and tilted toward the camera, edge-on views, head motion | yes | yes: board 2 untouched until about f161 |
| 5, 1 | pot + spoon / lid | the pot fills a third of the image (5); the pot is waved with blur f132–182 (1) | yes | partly (the lid or spoon is often held) |
| 28 | rack, pot | the pot is rolled about 140°/s near the image border | yes | yes (the rack is static) |
| 20 | cup, pitcher | the pitcher is cut by the image border during the pour | yes | partly (the cup is static before the pour) |
| 19, 38 | sweeper, dust pan | the dust-pan dump: 0.14–0.5× of its area visible for about 12 frames | yes | 19 partly; 38 no (one object) |
| 10, 14, 15, 16, 30 | static rack or cup plus a moved object | head motion within the public range | yes | yes (a static container) |
| 35, 36, 37 | spoon alone | one object | yes | no |

- Which evals actually jump is unknown until the GT-free screen runs on the stored eval outputs. The screen is a
  `vo.json` keyframe burst (≥ 4 switches in 25 frames) plus F2's correction (≥ 1 cm).
- Public base rate: 1 of 13 two-object episodes has a clear jump (`vo_oracle_screen.json`: ep24 common mode 2.72 cm
  against 0.78 cm differential; every other episode has common ≤ differential or < 1 cm with P_s).
- Value:
  - per jumped eval with S_e ≥ 0.8: ΔT ≈ 1.025 × S_e × 0.18, i.e. +0.005 to +0.008 LB at c 0.74–1.0;
  - expected number of jumped evals ≈ 0.5–1.5 [E];
  - **total ≈ +0.002 to +0.008 LB, central +0.004** [E]. Eval 25 alone: +0.001 to +0.004 (p ≈ 0.2–0.5 that it
    jumps).
- By the plan's acting thresholds (PLAN §4) this is "worth eval work" (≥ 0.005) only at the upper end. F1 and F3 are
  cheap CPU checks, so run their public test first. They also bound the sub-cm common-mode wobble on other episodes,
  which this file cannot separate from tracker error.

## 5. Not done / caveats
- F1 and F3 are not run: they need the depth caches or the b/c videos, which were not downloaded (the task allows only
  pose files from the store). The VO mechanism stays [H] until F1's test.
- The oracle common-mode screen measures the camera in mocap axes only for two-object episodes. Single-object episodes
  (ep39–45) cannot separate camera from tracker this way.
- Eval tracks were not inspected (public-only step). The eval-side screen is listed under F1/F2.
- Rule K's thresholds (and its ≥ 1 cm episode gate) were chosen after seeing the public data, and the D_H
  sensitivity is large. Its always-on form failed the no-harm rule. No fresh public holdout exists.
- The LB numbers assume the plan's conversion T ≈ a·S·R at eval 25's S_e 0.850, and an [E] probability that eval 25
  has a jump. No rollout was run.
