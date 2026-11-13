# Second meeting with Roman Klis (31 Oct 2026, 29 min): analysis

Source: the owner's Fathom transcript (https://fathom.video/share/D-u2pZCsjZfsrxxyZdJLJo_m_cC2_gZW). Some speaker
labels are swapped; lines are attributed by content. Checked against the live branches at ~20:15 UTC:
- standings-20261031: RPE/MPPE decomposition and the marker layer;
- focused-pascal: perception sprint;
- determined-wright: physics study;
- affectionate-turing: registration.

Labels: [M] measured, [E] estimate, [I] inference, [H] hypothesis. Nothing was run for this note.

## 1. What Roman proposed
1. The 6-DoF rigid-body model with NVIDIA's coefficients is fine.
2. The "delay" or "shadow" in the videos is a tracking (perception) error. Use an **unscented Kalman filter per object**:
   - an observation-noise model for the camera;
   - objects at rest have zero velocity;
   - a touched object follows the hand in contact;
   - focus on the object in contact; the rest stay still.
3. First a step that separates the objects (for example a VLM that says the lid sits on the pot).
4. Show him time series of all 6 DoF with uncertainty, under three observation-noise levels.
5. "If the positions are correct, the problem is almost solved": it is a perception problem.
6. Ahmet's idea, which Roman supported: a simpler robot hand (three fingers), since the hand is not scored.
7. Camera position information matters.
8. A Berkeley paper estimated reaction forces for interlocking parts; he will look for it.
9. Asks how we estimate object positions today.

## 2. Against the evidence

**The "delay" in the video is the robot, not the tracker [M].**
- The ep2 video (`tools/render_eval_rollout.py`) draws the simulated objects solid and our reference as a white
  wireframe. It shows no camera image.
- So the visible lag is the robot falling behind our reference: rollout error.
- That is where the leaderboard's RPE/MPPE gap is (standings `docs/analysis/rpe-decomp-20261031/README.md`):
  - Over 70 official public draws, the reference contributes ≈ 10 % of RPE and ≈ 16 % of MPPE.
  - Failed draws score 10–77 cm and dominate the mean.
  - With no failed draws, eval RPE would be ≈ 1.6–2.4 cm [E], near the top six (1.10–1.73).

**Kalman filtering targets noise; our reference error is mostly bias [M].** On the 20 public episodes, by
ground-truth substitution (diagnostic only):
- a constant offset per object accounts for AUC +0.050 (19 of 20 better);
- the frame-0 scene tilt (0.4–5°; 10.5° on ep31) accounts for AUC +0.040.

The GT-free jitter removers all fail their pre-registered rules:
- rest-hold and initial-hold: ΔAUC +0.001;
- static hold of untouched objects: +0.004, failing the no-harm rule;
- hand-coupled held pose: −0.018. The palm frame turns 10–50° against the object within a hold, so the hand guides
  worse than the tracker (3.1 vs 0.9 cm).

A Kalman filter cannot remove a sensor bias unless another sensor sees it. The second sensors tested today lost to
the tracker [M]:
- marker balls: stereo fixes 1.0–2.2 cm vs the tracker's 0.26–0.42 cm on the pot; public ΔAUC −0.083; ego_cam_a as a
  third view gives no improvement;
- depth-ICP offset fit: about none of the offset recovered.

So a per-object UKF on today's measurements is bounded by the jitter share. That is small: ≤ the 0.008 non-constant
part of the tracker loss, which also holds drift [E].

**Where Roman's framing still helps [H].** The question to ask him is how to make the bias observable. One route is an
augmented-state filter with bias states, made observable by physical constraints:
- a resting object touches the table in one of its stable poses;
- gravity sets the tilt of objects at rest;
- the lid sits on the rim;
- no interpenetration.

Constraint versions without a filter were tested and rejected: table snap −0.008, tilt-to-plane −0.001. A filter
would have to beat those. The frame-0 tilt (+0.040 by oracle) is the largest single target.

**Separation is already done [M].** The kit gives each episode's object list (allowed on eval). Every object gets its
own frame-0 detection (SAM2 proposals × DINOv2 against renders of our meshes) and its own FoundationPose track. Pot/lid
separation matters only for mesh building, which the mesh session handles (SAM 3D needs a lid-off view).

**"Correct positions solve it" holds for AUC on some episodes only [M].**
- Eval 10's twin is perception-limited: 0.940 with true motion vs 0.595 ours. Its nest fix passes at reference level;
  the rollout gate is running.
- Eval 14's twin is not: 0.544 either way.
- The reference's AUC loss on the board is ≈ 0.10 [E], mostly the spoon (unmeasurable without spoon mocap).

**Simpler hand [M/L]:**
- NVIDIA's primitive hand gave no gain (22 Oct: ep18 0.377 vs 0.345, ep24 0.282 vs 0.297).
- The human-shaped hand was worse (−0.161).
- Literature: Allegro (4 fingers) 52.0 % < Inspire 78.8 % < Arti-MANO 82.4 % (V2P-Manip). DexMachina: DoF matters more
  than size.
- The 3-finger Dex3 in FlashCHORD uses the humanoid reference format, so it needs new retargeting and every policy
  retrained.
- Not before the freeze.

**Spoon markers (Ahmet's stated plan to Roman) [M]:** the marker correction layer failed today (see above). The
markers stay useful as part of the spoon tracking template; as a separate sensor they are closed for now.

**Camera [M]:** the head camera pose comes from stereo visual odometry per frame. The scorer aligns once at frame 0 on
the first non-symmetric object, so that object's frame-0 orientation error tilts the whole episode (the +0.040 above).

**Picking the best draws (Ahmet's guess about other teams):**
- Choosing among a checkpoint's draws by a GT-free MPPE would cut public RPE 13.7 → 6.4 (standings, post hoc).
- It is the best-of-N packing our plan rejected (cherry-picking a stochastic evaluator).
- The organisers' new reproduce check makes it riskier.

**IP (meeting 1).** The registration session found `aebatirel/v2d-track3` **public** at 11:20 UTC and advised making
it private and adding the organisers as collaborators. Owner action.

## 3. Recommendation
1. **Answer Roman with the bias-vs-noise finding.** His Kalman expertise is most useful on bias observability, not
   noise.
2. **Make the 6-DoF time series he asked for ($0, CPU), on public episodes.** Our track vs mocap per DoF for ep2
   (pot + lid) and ep31 (sweeper + rack). Mocap is used only as a diagnostic plot, so he can see offset vs noise vs
   drift. FoundationPose gives no covariance: show the residual band instead and label it so.
3. **No UKF build before the freeze unless (2) shows meaningful noise.** If it does, pre-register a public test of a
   per-object smoother or UKF with bias states against the base and the rejected constraint fixes.
4. **The leaderboard levers stay where the loss is measured:**
   - robot failures for RPE/MPPE: the recipe-screen K/D results tonight, carves;
   - eval 10's nest fix for AUC;
   - the spoon: no measurable lever yet.
5. **Ask Roman for the Berkeley reaction-force paper** for the mesh session's interlock work.
