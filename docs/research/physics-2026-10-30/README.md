# Object physics study (30 Oct 2026): public scans first

Owner's goal: understand the physics of the episodes before choosing a robot embodiment. Keep the simulator's own world
(solver, contact model, global friction 1.0); give each object plausible physical properties instead of NVIDIA's
placeholder ("Track 3 supplies no measured physical properties. 0.3 kg is a placeholder mass", public URDF comment).
Owner, 30 Oct: "first try it with the public given meshes, later we go to the generated meshes"; centre of gravity first.

Markers: [M] measured here, [E] estimate, [H] hypothesis with its falsification test. No ground truth is read except by
the final scoring of public rollouts against mocap (registered AUC), after inference.

## Rules we keep (owner accepted 30 Oct)
- One value set per object, shared by every episode; physically plausible; never fitted to mocap or to eval results;
  declared in the technical report.
- Only object properties change (mass, centre of mass, inertia). Global friction (`scene.contact_friction` 1.0), object
  damping (0) and every `sim` setting stay at the recipe defaults.

## Step 1: mass properties [M/E]
`pipeline/object_physics.py` on the meshes the simulator uses (`scanlib2`: NVIDIA's public scans; the boards and the
sweeper use NVIDIA's `_collision.glb`, as their public URDFs do). Material model per object:
`materials_public_scans.json` (materials from the public videos; masses are estimates, plausibly ×0.6–×1.6).
Output: `props_public_scans.json`. Asset build: `pipeline/make_assets.py LIB OUT --physics props_public_scans.json`.

## Step 2: CPU zero-action test (pre-registered 30 Oct ~10:20 UTC, before any result)
- Episodes (public; stored base references of the 24 Oct recipe validation): ep2 pot + lid (`20261024-ev3-2c1e4dd`
  perc2mck), ep12 cup into rack (`20261024-ev2-2c1e4dd` perc2mc), ep18 sweeper + dust pan (ev3 perc2mc), ep24 boards
  (ev3 perc2mc).
- Arms: **S0** = scans with the placeholder (0.3 kg, shell inertia) — the control; **S1** = scans with
  `props_public_scans.json`. Everything else identical.
- Per arm and episode, on this container's CPU (FlashCHORD at the evaluator pin, 1 world): `grasp_lock.py` (frozen
  GL_ARGS of the recipe arms) → `wrist_ilc.py` (4 iterations, kp 400 embodiment) → zero-action replay
  (`trace_rollout.py zero`) → `trace_score.py` (sim_vs_ref, our reference, no ground truth) and `rest_check.py`.
  No evolutionary refinement (GPU only).
- Reading, fixed now: Δ = S1 − S0 zero-action sim_vs_ref per episode.
  - **signal:** mean Δ ≥ +0.03 and no episode Δ ≤ −0.05;
  - **harm:** mean Δ ≤ −0.03 or any episode Δ ≤ −0.10;
  - otherwise **neutral**.
  CPU physics is deterministic, so one replay per arm. This is a no-policy test: it says whether the hand reference
  holds and moves lighter / heavier objects better, not what RL makes of it.

## Step 3: GPU retrain (owner approved 30 Oct; pre-registered 09:50 UTC, before any result)
- Job `ops/jobs/physics_arms.sh` (commit 6a814df): the frozen grasp-lock recipe of the 29 Oct recipe arms (GL_ARGS,
  EVOLVE=1, kp 400 wrist, FDR + VOC fix, 70M steps, seed 42, CURVE_REP 3, NREP 5) with REUSE_REF off (grasp lock, ILC
  and the evolutionary refinement are rebuilt under each arm's physics) and SF=0 (scans), on ep2, ep12, ep18, ep24.
- Boxes: S0 `20261030-physS0-6a814df` (instance 58386066, RTX PRO 6000 S, UK, $1.348/h); S1
  `20261030-physS1-6a814df` (58386069, RTX PRO 6000 WS, KR, $1.177/h). Ledger: $6.50 planned each [E].
- Reading, fixed now (registered AUC vs mocap of the chosen checkpoint, mean of 5 official evaluations; the checkpoint is
  chosen by sim_vs_ref only): Δ = S1 − S0 per episode.
  - **signal:** mean Δ ≥ +0.03 and no episode Δ ≤ −0.05;
  - **harm:** mean Δ ≤ −0.03 or any episode Δ ≤ −0.10;
  - otherwise **inconclusive**.
  One seed per arm and a rollout sd up to ~0.12 (ep24) make this weak: a signal buys a second seed, not adoption.
- Understanding readouts (no decision attached): zero-action sim_vs_ref and rest check per arm (with EVOLVE), the
  per-checkpoint curves, which objects slip or drop, and where.

## Results
(below, appended as they come; nothing above is edited after a result)

### Step 2 result (CPU zero-action, 30 Oct 09:45–10:20 UTC, code 299274e / fc75ac4) [M]
Machine: this cloud container (4 CPU), FlashCHORD at the evaluator pin, 1 world, CPU. Outputs: scratchpad
`phys/{S0,S1}/out/ep*/` (run.log, zero.npz, gl.log). Per-object detail: `tools/trace_objects.py`.

| episode | floor | S0 (0.3 kg) | S1 (plausible) | Δ |
|---|---|---|---|---|
| ep2 pot + lid | 0.506 | 0.179 | 0.141 | −0.038 |
| ep12 cup → rack | 0.605 | 0.551 | 0.600 | +0.049 |
| ep18 sweeper + dust pan | 0.619 | 0.214 | 0.279 | +0.065 |
| ep24 boards | 0.220 | 0.196 | 0.203 | +0.007 |

Mean Δ +0.021 → **neutral** by the pre-registered rule (signal needs ≥ +0.03; no episode ≤ −0.05, none ≤ −0.10).
Readings [M]:
- Every arm leaves the reference early (first object > 3 cm off at frames 11–61) and all but ep24 score below the
  do-nothing floor: grasp holds and contact geometry dominate, mass is second order at zero action.
- ep12: the copied human grip loses the cup ~1 cm into the lift (f37) at 128 g and at 300 g; S1's gain is the heavier
  rack (387 g) not being knocked by the dropped cup (S0: 12 cm at the end).
- ep2: pot and lid are off 13–17 cm / ~70° from f44–61, before the pot's hold starts (f105): the lid–pot collision
  shapes overlap (as the 30 Oct carve study found on our meshes), not a mass effect.
- ep24: S0 throws board 1 ≈ 80 cm (f137); S1 ≈ 23 cm.
No GPU decision depends on this (the GPU arms were approved regardless); it says the no-policy replay is limited by
contacts, so RL is where a mass effect could show.

## Human capsule hand, first pass (30 Oct ~10:40–11:20 UTC, CPU, code 232ca35) — exploratory [M]
Hand: `pipeline/human_hand.py` (review recommendation (b); Sharpa joint/link names so FlashCHORD's SharpaHands loads
it; graded human finger gains/efforts; wrist kp 400; no self-contacts inside a hand). Variants: **A** adult template
(mkref.TEMPLATE_RIGHT: index 8.5 cm, wrist→middle tip 18.5 cm); **P** perceived bone lengths per episode and side
(index 5.4–7.0 cm). Joint angles fitted per frame to the perceived keypoints (`ref`; median bone-direction error
9–36° per digit, 10–27 % of joint-frames at a limit, mostly finger spread and DIP hyperextension). Replay = pure copy of
the perceived human motion (zero action), S1 object physics, scans, no grasp lock, no ILC, no policy.

| episode | floor | human P | human A |
|---|---|---|---|
| ep2 pot + lid | 0.506 | 0.323 | 0.325 |
| ep12 cup → rack | 0.605 | 0.617 | 0.596 |
| ep18 sweeper + dust pan | 0.619 | 0.331 | 0.133 |
| ep24 boards | 0.220 | 0.194 | 0.103 (NaN: the simulation diverged) |

Readings:
- **A copy of the perceived motion does not carry the objects, with either hand size.** ep12: the cup is lost at
  f37, the same frame as with the Sharpa grasp-lock reference. The simulated wrist follows the perceived wrist to
  1–2 cm (median), so the simulation does what the reference says.
- `tools/hold_gap.py` on the base references (scans, our object poses): over every grasp-lock hold phase the nearest
  perceived fingertip keypoint sits a median +0.2 to +1.8 cm outside the held object (a finger pad is 0.6–0.9 cm
  outside its keypoint), and ≥ 2 tips are within 1.5 cm in 26–94 % of hold frames (ep24 board 1: 33 %). The perceived
  hand is near the object but does not squeeze it: video gives positions, not grip force, and a light touch loses to
  gravity.
- [H-size] (review): "A no better than P on the median" → **falsified here** (P ≥ A on all four; A diverged on ep24 because
  adult-length fingers at the perceived angles go deep into the board). In a pure copy the hand that matches the
  perceived geometry wins; this does not tell us the person's true hand size.
- Next hypothesis [H-squeeze]: the missing ingredient is the invisible grip force. Test: add a human-plausible squeeze
  (flexion offsets so the PD gives a few newtons per contact) on the holding hand during grasp-lock hold phases;
  falsified if zero-action sim_vs_ref with squeeze does not beat the plain copy by ≥ 0.05 on at least 3 of 4 episodes.
- [H-squeeze] details fixed before running (30 Oct ~12:15 UTC): hand = variant P (it beat A in the plain copy);
  holds = each episode's S1 CPU grasp-lock JSON (hand, hold_from..end); primary squeeze **0.3 rad** on finger MCP_FE /
  PIP / DIP and thumb MCP_FE / IP of the holding hand, ramped over 5 frames; 0.15 rad is run as a secondary readout and
  not used for the rule. Baseline = the plain P copy above (0.323 / 0.617 / 0.331 / 0.194).

### [H-squeeze] result (30 Oct ~12:35 UTC, CPU) [M] — falsified
Squeeze 0.3 rad vs the plain P copy: ep2 0.332 vs 0.323 (+0.009), ep12 0.597 vs 0.617 (−0.019), ep18 0.351 vs 0.331
(+0.019), ep24 0.196 vs 0.194 (+0.002) → no episode gains ≥ 0.05: **falsified**. Secondary 0.15 rad: 0.312 / 0.619 /
0.180 / 0.201. Objects still leave at the same frames. Why (ep12, `mano_right_joints` around the cup axis, our
reference): at f30–36 the perceived thumb is ~145–148° from the fingers around the cup (opposition) with the tips at the
cup's 5 cm radius, but during the carry the perceived grip dissolves (f39 117°, f42 83°, f48 −86°; ring/pinky tips 7–8
cm from the axis) and the index tip sits inside the cup's wall radius: hand-tracking error around an occluding
object. Grip force cannot fix a grip that is not geometrically there.

- [H-lock] (pre-registered 12:40 UTC, before running): the same P human hand with `pipeline/grasp_lock.py` (EMB = the
  human hand; frozen GL_ARGS of the recipe arms; the copied human grasp snapped to the surface and held rigidly in the
  object frame during each hold; no ILC) carries the objects: falsified unless zero-action sim_vs_ref beats the plain P
  copy by ≥ 0.05 on at least 3 of 4 episodes. Also compared (no rule) with the Sharpa grasp-lock S1 CPU numbers
  (0.141 / 0.600 / 0.279 / 0.203).
- [H-lock] first run (12:45–13:20 UTC) **void**: `grasp_lock.py` reported "0 fingers on, mean gap 69–91 mm" and no
  closing on every hold, because `contact_retarget.hand_geometry` finds hand bodies by the `<side>_sharpa_wave/` label
  prefix and the human URDF was named `<side>_human` (no hand geometry found). Scores of that run (0.223 / 0.596 /
  0.353 / 0.194) are not a test of the hypothesis. Fix: the human URDF now carries the Sharpa's robot name; rerun with the
  rule unchanged.
- [H-lock] runs 2 and 3 also **void**: `grasp_lock.py` built its scene with FlashCHORD's default Sharpa and ignored the
  hand config, so it computed the grasps on a Sharpa posed with the human hand's joint angles (constant "0 fingers on,
  mean gap 79.4 mm"). Fixed with `GL_EMB` (default unchanged). The `contact_retarget.hand_geometry` primitive-shape
  sampling (103e1ba) is needed too: the human hand has no mesh shapes. Rerun with the rule unchanged.

### Step 3 result (GPU, 30 Oct; S1 box self-destroyed 12:36 UTC, S0 finished before 13:40 UTC with its push to the store
### failing on HF 429s — summaries copied off the box: `gpu/S0_summary.json`, `gpu/S1_summary.json`) [M]

| episode | S0 AUC vs mocap (5 evals) | S1 AUC vs mocap | Δ | S0 / S1 chosen checkpoint |
|---|---|---|---|---|
| ep2 pot + lid | 0.944 ± 0.036 | 0.736 ± 0.228 | **−0.208** | 60M / 20M |
| ep12 cup → rack | 0.862 ± 0.021 | 0.885 ± 0.030 | +0.022 | 70M / 70M |
| ep18 sweeper + dust pan | 0.573 ± 0.060 | 0.625 ± 0.001 | +0.051 | 30M / 10M |
| ep24 boards | 0.207 ± 0.025 | 0.232 ± 0.002 | +0.025 | 60M / 40M |

Mean Δ −0.027; ep2 Δ ≤ −0.10 → **harm** by the pre-registered rule: plausible masses are not adopted.
Reading [H]: S1's ep2 training collapsed after 20M (curve 0.487 / 0.862 / 0.483 / 0.495 / 0.497 / 0.468 / 0.467; the pot
is no longer lifted from 30M) while S0 climbed to 0.977 at 60M; the other three episodes lean S1 (+0.02 to +0.05). With
one seed per arm the ep2 collapse cannot be separated from seed noise; telling them apart needs ≥ 2 more seeds per arm
on ep2 (not run). Zero-action sim_vs_ref on the box (with EVOLVE) S1: 0.601 / 0.604 / 0.542 / 0.194.

### [H-lock] result (30 Oct ~13:40 UTC, CPU, code 9731c7b + 103e1ba) [M] — falsified
Human hand P + `grasp_lock.py` (GL_EMB = the human hand, frozen GL_ARGS, no ILC, no EVOLVE), zero action, S1 physics:
| episode | plain P copy | P + grasp lock | Δ | grasps found |
|---|---|---|---|---|
| ep2 | 0.323 | 0.440 | +0.117 | pot 5 fingers, gap 0.0 mm; lid 2 fingers, 9.5 mm |
| ep12 | 0.617 | 0.578 | −0.039 | cup 5 fingers, 0.7 mm |
| ep18 | 0.331 | 0.276 | −0.055 | dust pan 3 fingers, 4.5 mm; sweeper 4, 1.6 mm |
| ep24 | 0.194 | 0.102 | −0.092 | board 1 5 fingers, 1.3 mm; board 2 4, 2.4 mm |
1 of 4 episodes ≥ +0.05 → **falsified**. With a snapped, locked human grasp (2–5 fingers on, gaps 0–9.5 mm) the objects
still leave the reference at the same early frames (ep12 cup f37, ep18 dust pan f18, ep24 board 1 f11). The Sharpa
grasp-lock reference behaves the same at zero action (CPU S1: cup lost f37) and only RL takes it to 0.885 (GPU S1).

## Summary of the study so far (30 Oct)
- **Mass:** plausible per-object masses change little at zero action (neutral) and, after RL, lean +0.02–0.05 on three
  episodes but count as **harm** on the pre-registered rule because S1's ep2 training collapsed (one seed). Not adopted.
- **Centre of mass:** on NVIDIA's scans the surface-centroid COM is already right for these thin-walled objects
  (≤ 4 mm change). On our generated meshes the COM sits 2–25 mm off the scans' (next step, as the owner asked).
- **A copy of the video does not reproduce the episode in physics,** with the robot or a human-shaped hand, with or
  without extra squeeze or a locked grasp: the perceived hand is near the objects but not gripping them, the perceived
  grip dissolves during carries (ep12: thumb–finger opposition 148° → −86° in 12 frames), and in this simulator even a
  snapped grasp loses the object within frames when nothing adapts. Something must adapt to the physics: RL (what our
  recipe does), a sampling optimiser (SPIDER / Do as I Do) or ILC.
- Not run (would need decisions/budget): second and third seeds on ep2 for the mass question; RL with the human hand
  (GPU); the MANO-vs-capsule head-to-head (needs the owner's MANO download).

## Round 2 (owner 30 Oct ~13:50 UTC: "go nuts with all") — pre-registered before any result
**(2) ep2 seeds for the mass question.** Boxes S0 and S1 (`ARM=S0|S1 PAIRS=2:20261024-ev3-2c1e4dd:mck SEEDS="43 44"`,
`ops/jobs/physics_arms.sh`): each builds its ep2 reference once (seed 43), then seed 44 reuses it. Readout: registered
AUC vs mocap, 5 evaluations per seed. With seed 42 from round 1, 3 seeds per arm. Δ2 = mean over S1's 3 seeds − mean
over S0's 3 seeds on ep2.
- Δ2 ≤ −0.10: the ep2 harm is **confirmed**;
- Δ2 > −0.05: the round-1 ep2 drop is attributed to seed noise, and the round-1 rule is recomputed with ep2's
  3-seed means (other episodes one seed);
- otherwise **inconclusive**.

**(4) Human hand with RL.** Box `ARM=S0 HUMAN=1` (all four episodes, seed 42): the perceived-size human capsule hand
(`glock_public.sh` HUMAN mode: `human_hand.py` P hand and reference, grasp lock with GL_EMB, ILC, EVOLVE, FlashSAC with
embodiment human_P<ep>), placeholder physics, scans, frozen recipe. Compared with the Sharpa S0 seed-42 results
(0.944 / 0.862 / 0.573 / 0.207). Δh = human − Sharpa per episode (AUC vs mocap, 5 evaluations).
- **human better:** mean Δh ≥ +0.03 and no episode ≤ −0.05;
- **human worse:** mean Δh ≤ −0.03 or any episode ≤ −0.10;
- otherwise **inconclusive**. One seed; FlashSAC's recipe is tuned for the Sharpa.

**(1) Centre of gravity on our meshes** and **(3) physics-based motion solving**: separate entries below when they run.

### (1) Centre of gravity on our generated meshes (30 Oct ~14:00 UTC, CPU) [M]
COM estimators on `meshes/library_v3` (the simulator meshes of our packs) against the scans' surface-centroid COM
(same object frames; scans used only as a development diagnostic): our thin-shell centroid (what make_assets writes
today) errs by median **8.3 mm** (beige cup 16.1, rack 13.4, pitcher 24.5, pot/lid 9.7, dust pan 7.0, boards 2.6–3.5,
blue cup 1.9, sweeper 2.4); a solid voxel fill is worse (median 12.7 mm). So the current estimator stays.
- **[H-com]** (pre-registered now, before running): a COM error of this size matters at zero action. Test: CPU grasp-lock
  zero-action replays (frozen GL_ARGS, ILC 4, as step 2) on ep2/12/18/24 with OUR meshes (library_v3, make_assets,
  placeholder 0.3 kg, our shell inertia) in two arms that differ only in the COM: **O0** our shell COM, **Oc** the scan's
  COM transplanted into our mesh frame (diagnostic oracle). Falsified if |sim_vs_ref(Oc) − sim_vs_ref(O0)| < 0.03 on all
  four episodes.
- **[H-com] result [M]:** zero-action sim_vs_ref O0 / Oc: ep2 0.150 / 0.365 (+0.215), ep12 0.542 / 0.518 (−0.024),
  ep18 0.230 / 0.171 (−0.060), ep24 0.188 / 0.209 (+0.021) → two episodes move ≥ 0.03: **not falsified** — a 1–2 cm COM
  change changes the outcome, but in both directions (ep2: the pot holds better, the lid leaves at f7 instead of f43).
- **Chaos control (pre-registered 14:15 UTC, before running):** arm **Op** = O0 with each object's COM moved 2 mm in a
  random direction (seed 0). If |Op − O0| ≥ 0.10 on ep2, the [H-com] effect is attributed to chaotic sensitivity of the
  zero-action replay, not to COM accuracy.
