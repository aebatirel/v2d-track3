# Meeting with Roman Klis (30 Oct 2026, 31 min): what he proposed, what we already know, what to do

Source: the owner's Fathom transcript (recording https://fathom.video/share/rtqWcV6T8oqb2eHxMFWDqFZx4Cy_HTTy). Some
speaker labels in the transcript are swapped; lines are attributed here by content. Checked against this repo (`main`
f34da0e) and the live session branches at 12:10 UTC: `claude/determined-wright-3joens` (embodiment / physics study),
`claude/focused-pascal-2nz9s1` (control, packs, oracle twins), `claude/bold-albattani-6qmxsv` (meshes).
Labels: [M] measured, [E] estimate, [I] inference, [H] hypothesis with its falsifier. No ground truth was read for this
note.

## 1. What Roman proposed
1. **Decompose; one problem at a time.** Treat it as a reconstruction problem and solve the layers in order.
2. **Hands first.** The most important thing is accurate finger placement, because fingers define the contact points.
   You do not need the whole hand, only the critical places. Get the hand wireframe to follow the video one-to-one
   before touching objects ("the beginning is good, then the frame is off").
3. **Remove the embodiment gap.** The Sharpa hand looks about twice the human hand. Use a human-sized hand, even an
   abstract or "unrealistic" one, since the contest allows custom embodiments.
4. **Two models.** Model 1: a human-hand digital twin that reproduces the video in simulation. Model 2: the robot hand
   follows model 1, and a policy corrects for the size differences. Compare the errors of the two (four videos side by
   side).
5. **Make the simulation easy first.** For example, make the pot very light, then add realism back.
6. **Avoid two-handed hand-overs.** They add contacts and independent manipulators.
7. **IP caution.** Hackathon-style contests often extract know-how; read the IP terms. Winners must open-source.
8. Offers daily idea ping-pong until the freeze (he will not code).

## 2. The one misreading that matters
The video Roman judged is `tools/sim_vs_real_video.py`. Its middle panel shows the **simulated robot rollout**: robot
hand links at their simulated poses, objects filled at their simulated poses, and our reference object as a white
outline [M, tool docstring]. It is not the hand tracker. The robot policy is trained to move the **objects** along the
reference. It has a residual of ±20 cm / ±1 rad on the wrist, and its object reward outweighs hand imitation (20 vs
0.25 in the stock recipe). So a robot hand that drifts from the human hand is expected, and is not a tracking bug [M].

Two gaps are visible in that panel, and they are the two halves of our loss:
- **Filled object vs white outline:** the robot failing to follow our reference. Policy loss **0.083** of the
  leaderboard AUC [M] (sum of (1 − sim_vs_ref)/20, pack 7).
- **White outline vs the real object in the video:** our reference being wrong. Reference loss **≈ 0.10** [E], of which
  ≈ 0.06–0.07 is the spoon [E].

The scorer never looks at the hands. A hand error costs score only when it makes the robot lose, push or misplace an
object.

## 3. Roman's points against our evidence

| Roman's point | What we already did or measured | Verdict |
|---|---|---|
| Hands first; follow the video one-to-one | In 2-D the MediaPipe landmarks sit on the real hands (ep3 median 11 px on 2028 px; ep24 overlays) [M]. The **3-D lift is wrong**: while gripping, the hand collapses into the held object (ep24: wrist→middle tip 3.8–5.2 cm) [M]. The perceived hand is small (ep12 wrist→middle tip 11.9 cm against an adult template of 18.5 cm) [M]. Fingers look 25–40 % short for the palm (finger:palm ratio 1.2–1.3 against 1.7–2.1 anatomical) [M+I]. During holds, fingertips sit +0.2 to +1.8 cm outside the object [M] (`tools/hold_gap.py`). | **Right that the hand is off, but in depth and scale, not in 2-D.** So "the overlay looks one-to-one" cannot be the test: the 2-D overlay already matches. |
| Contact points, not the whole hand | This is our contact-anchored retargeting (fingertips snapped to surfaces; penetration p95 20 → 6 mm) and the grasp lock: a designed, physics-checked grasp with task-wrench LP forces, locked to the object during holds. The grasp lock is used on 15 of 20 eval policies [M]. | **Already the method.** The grasp lock throws the perceived fingers away during holds because they are unreliable. |
| Sharpa ≈ 2× the human hand | Sharpa index finger 10.45 cm. Our perceived index is 6.25–6.45 cm (1.6×), but an anthropometric adult index is ≈ 9.5 cm (MyoHand 94.8 mm), so the Sharpa is ≈ 1.1× a real hand [M/L]. | **Mostly a perception artefact.** The big size gap is our undersized perceived hand, which brings us back to point 1. |
| Human-hand twin first (model 1) | **Done today** by the determined-wright session: our own Apache-2.0 capsule hand, 22 DoF, in perceived size (P) and adult size (A), plus plausible object masses; a pure copy of the perceived motion. Score (sim_vs_ref) P 0.323 / 0.617 / 0.331 / 0.194 on ep2/12/18/24, against 0.506 / 0.605 / 0.619 / 0.220 for leaving the objects alone. The cup in ep12 drops at frame 37, the same frame as with the Sharpa [M]. | **The kinematic twin does not carry objects with either hand.** The video gives positions, not grip force. Literature agrees: SPIDER's kinematic replay scores 11.0 against 48.8 physics-optimised [L, note 04]. |
| Robot follows the human twin (model 2) | This is our pipeline already: retargeted human reference → RL residual that corrects it. Literature on swapping the hand: after RL, V2P-Manip reports Arti-MANO 82.4 % vs Inspire 78.8 %; DexMachina finds "DoF matters more than size match" [L]. The Sharpa is 22-DoF and isomorphic to the human hand. | **Small expected gain [E]** for a second training stage per episode. |
| Make it easy first (light pot) | FlashCHORD training already pushes objects along the reference with a virtual object controller and anneals it to zero (the same curriculum as DexMachina). Object physics: the owner approved plausible masses today (cup 128 g, lid 88 g, dust pan 44 g, against the 0.3 kg placeholder). Partial RL results: ep12 0.862 → 0.885, ep18 0.573 → 0.625 registered AUC [M, partial, one seed]. | **Already there as a curriculum.** Plausible masses are the legitimate version and are being measured. The evaluator has no assist, so the final objects cannot be "unrealistically light". |
| Avoid hand-overs | Scoring is object-only. The RL already finds one-hand solutions (the 0.98 episode). | **Agree.** Planning one-hand carries in the grasp lock where the human handed over is a cheap option. |
| IP | Winners must release Apache-2.0 code, a technical report and a one-command reproduction (`track3-requirements.md`). MANO's licence forbids redistribution, so the human hand is our own capsule hand, not MANO. | **Valid caution.** Read the Kaggle "winner licence" clause before the final picks (owner). |

## 4. How much of the score is hand-related
Pack 7 per-episode policy loss, from the forensics labels in the 30 Oct briefing [E]:
- **Grasp or hand related:** eval 32 (cup tips in the grasp) 0.0067, eval 16 (spoon flips on release) 0.0046, eval 3
  (pot slips) 0.0029, eval 15 (spoon rotates on release) 0.0027. Together ≈ 0.017.
- **Mesh, collision or reference related:** eval 10 (cup stacking, rim collision, RL avoids the stack) 0.027, then
  14, 30, 20, 1, 28, 25. Together ≈ 0.055.
- **Reference loss ≈ 0.10:** spoon and object perception. Hands do not enter it, except through the spoon (below).

So even a perfect hand would address at most ≈ 0.017 of the 0.185 we lose [E], unless it improves the object
reference.

## 5. Where Roman's "hands first" can pay on the leaderboard
**The spoon.** It is in 10 of 20 eval episodes (32.5 % of the score), often hidden inside the pot or cup, and its
inferred accuracy is 0.73–0.81 [E]. While it is held, its pose can be read from the hand: pose = wrist × grasp
offset. That needs an accurate 3-D wrist, which is exactly Roman's step 1. The next-steps plan already lists it, gated
on public thin objects (ep18/31/39/40: ≥ +0.005, no drop > 0.02). Its earlier gate, the depth audit, failed
(AUROC 0.600), so it was parked. A public validation is CPU-only.

[H-spoon]: a hand-anchored pose during holds beats the tracker on occluded spans of public held objects. Falsified if
the public rule above fails.

## 6. What the other sessions are running now (12:10 UTC)
- **determined-wright** (embodiment / physics):
  - H-squeeze replays running (CPU): human hand plus a 0.3 rad grip squeeze during holds. Pre-registered falsifier:
    must beat the plain copy by ≥ 0.05 on 3 of 4 episodes.
  - GPU arms S0/S1 (placeholder vs plausible mass) finishing; partial numbers in §3.
- **focused-pascal** (control and packs):
  - Eval 1 is confirmed on the official evaluator (0.924 ± 0.017). The pack-8 candidate is not uploaded; the owner
    decides.
  - Oracle-twin experiment: mocap object references on the twins of the hardest evals (ep11/13/31). It measures how
    much perfect object perception would buy, i.e. the decomposition Roman asks for, on the object side. Designed,
    with the build cut by a usage limit. Waiting for the owner's launch choice (≈ $9–10 full, ≈ $5–6 single box).
  - Video box: 4 of 5 worst-episode videos rendered; the push failed (HF 429).
- **bold-albattani** (meshes): design workflow for a generalized mesh generator; SAM 3D placement and sweeper-flip
  diagnosis done. CD-O is our worst board (11th), and the final rank is the sum of six board ranks.

## 7. Recommendation
1. **Keep the Sharpa for submissions.** Treat the human hand as a diagnostic and a report story, unless a public A/B
   says otherwise.
   - If H-squeeze passes: one GPU box running `ops/jobs/physics_arms.sh` with the human hand. Control: the S1 Sharpa
     arm already trained (same episodes, physics and recipe). ≈ $6.5 [E].
   - Rule, to be fixed before launch: adopt only if mean registered-AUC Δ ≥ +0.05 and no twin ≤ −0.05.
   - If H-squeeze fails: stop the human-twin line for the leaderboard.
2. **Show Roman the right layer ($0, CPU).** Render `tools/ref_overlay_video.py` (the hand estimated from video, the
   retargeted robot hand and the reference objects on the colour camera) for the episodes he saw, next to the
   rollout videos. Add the 3-D defect numbers from §3. This answers "is the tracking off?" layer by layer.
3. **Turn "hands first" into the spoon test ($0, CPU).** Run [H-spoon] on public held objects under the plan's
   pre-registered rule. Only if it passes: rebuild the spoon references and retrain the 10 spoon policies,
   ≈ $25–35 [E], owner go-ahead.
4. **Keep the board levers moving** (owner decisions):
   - pack 8;
   - the oracle-twin launch;
   - eval 10;
   - a CD-O upload, if the organisers allow it.
5. **Rules:** "torture the video" is fine on public episodes and through automatic methods on eval. No hand-tuning of
   eval references by looking at overlays: the Kaggle rules forbid hand labelling on test records, CLAUDE.md forbids
   tuning on eval, and the held-out evaluation runs defaults.

## 8. What to send Roman and ask him
- **Send:** the §2 layer explanation, the §4 loss split, today's human-hand result, and the 4-panel video once it
  exists (real video, perception overlay, human-hand sim, Sharpa sim).
- **Ask**, where a physics view helps most:
  - inferring grip force from the object's motion, given that `task_wrench.py` / `grasp_force.py` already solve the
    friction-cone LP;
  - the eval-10 cup nesting, a 6–7 mm rim misalignment that RL learns to avoid;
  - a GT-free sign that a thin spoon's pose is wrong;
  - training for worst-case rather than mean behaviour on a non-deterministic evaluator.

## 9. Follow-up (owner, ~13:30 UTC): "if the simulation's physics is the real world's, it should copy the video"
- **Later results from the determined-wright session:**
  - [H-squeeze] is falsified (12:35 UTC; no episode gains ≥ 0.05).
  - Cause, ep12: around the occluding cup the perceived grip dissolves during the carry. Thumb–finger opposition goes
    145° → 83° → −86° from f36 to f48, and the index tip sits inside the cup wall. In that session's words, "grip force
    cannot fix a grip that is not geometrically there".
  - [H-lock] is running: the human hand with the grip snapped to the surface and locked to the object during holds.
    The first run was void (a URDF naming bug), and the rule is unchanged for the rerun.
  - Oracle twins: the owner chose option B (ep11/13/31, perceived vs mocap-object references, grasp lock, ≈ $5–6).
- **A copy needs every input of the physics, not only the visible motion:**
  - the same shapes: our meshes are ≈ 4 mm off (CD-O 0.40 cm), and nesting clearances are a few mm;
  - the same masses and friction;
  - the same start state: our references are 2–3 cm off;
  - the same forces, which the video does not show.
  Also, the person acts with feedback (touch, vision), and an open-loop copy of a closed-loop act diverges at sensitive
  events. The same checkpoint scores 0.26–0.92 across official draws [M].
- **Proposed "all inputs true" rung** (diagnostic, public episodes only, CPU zero-action, $0):
  - public scans (true shapes);
  - mocap object motion (the oracle-twin reference);
  - plausible masses;
  - the H-lock grip;
  - on one episode both studies can use (ep12 or ep13: cup into rack).
  Reading: if this copy carries the objects, the simulator is good enough and the remaining loss is perception. If it
  fails, the limit is the simulated contact or hand model, which only RL feedback or hand-side contact geometry can
  address. Not started; needs coordination between the two sessions.

## 10. Update, 31 Oct ~05:10 UTC: Roman's ideas, tested overnight by the other sessions
Read from the branches (not re-run here): determined-wright `docs/research/physics-2026-10-30/README.md` (3d37ea2);
focused-pascal `docs/research/work/oracle-twins-20261030/RESULTS.md` and its work log (1d23440).
- **Exact copy, human hand with a snapped, locked grip ([H-lock]):** falsified. With 2–5 fingers on and gaps of
  0–9.5 mm, the objects still leave at the same early frames (ep12 cup f37) [M].
- **Chaos control:** a random 2 mm centre-of-mass nudge moves the zero-action outcome as much as a 1–2 cm correction
  (ep2 +0.109, ep24 +0.151) [M]. Without feedback the replay is chaotic, so tuning the physics until the simulation
  matches the video cannot work.
- **Sampling MPC solver (Do as I Do-style, CPU):** on the exact replay the cup is carried to f84 instead of f37, but the
  gain is gone under 0.5 mm target noise [M]. Single zero-action replays are noisy measures; read them as jittered
  means.
- **Human hand with RL** (Roman's embodiment swap): **worse** by the pre-registered rule. Human 0.527 / 0.563 / 0.622 /
  0.231 vs Sharpa 0.944 / 0.862 / 0.573 / 0.207 on ep2/12/18/24, mean −0.161 [M]. Caveats: one seed, a recipe tuned
  for the Sharpa, untuned human gains. The Sharpa stays.
- **Realistic masses:** adopted by the round-3 rule, mean +0.090 vs mocap on 4 public episodes with scans [M].
  - Next, run by focused-pascal: a transfer check on our meshes (≈ $5–6), then eval retrains. Owner go-ahead needed.
- **Oracle twins (option B):**
  - ep11 / eval 10 is perception-limited: true object motion 0.940 vs ours 0.595 [M]. Upper bound ≈ +0.017 LB [E].
  - ep13 / eval 14 is not: 0.544 with either reference [M]. The left→right hand-over and flip fail even with the true
    object motion, and both arms use our perceived hands.
- **Coordination:** focused-pascal already added the "everything true" replay as rung R5 of its leak plan and asked
  determined-wright to run it on ep12/ep13. No separate message was sent from here.
- **New hypothesis from Roman's "avoid hand-overs" [H-onehand]:**
  - Idea: on ep13, a grasp-lock plan that carries the cup with one hand (no hand-over) beats 0.544 by ≥ 0.05. The
    scorer checks objects only.
  - Falsified if it does not, under the same recipe with one seed per reference and NREP 10.
  - Cost ≈ $3 GPU [E] after a CPU plan check. Not started; owner decision.
