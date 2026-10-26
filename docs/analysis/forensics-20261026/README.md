# Forensics of the third submission (Track 3 AUC 0.789, 4th) — 26 Oct 2026

Owner's request (26 Oct): "get the videos of our current episodes and also do forensics on what went wrong and what
can be improved"; "something more ambitious". No ground truth was read for any eval episode. Public-episode numbers
come from earlier mocap scoring recorded in the repo; sources are cited.

**Inputs:**
- the 20 official rollouts of pack 3 (`20261025-pack3-3758189`, the uploaded file);
- each episode's reference and checkpoint (sha256-checked against the submission);
- FlashCHORD on CPU for the physics tests.

**Files in this folder:**
- `rollout_errors.{png,json}`: object error against our reference, per frame;
- `hull_census/`: our reference against the simulator's collision geometry;
- the videos are listed in section 6.

## 1. Where the score goes

| Quantity | Value | Kind |
|---|---|---|
| Leaderboard AUC | 0.789 (4th; 3rd is 0.865, 1st 0.932) | measured (Kaggle) |
| The same rollouts against OUR reference (sim_vs_ref) | 0.883 | measured |
| Public twins: true AUC ≈ 0.979 × sim_vs_ref when the reference is sound (57 policy means, 10 episodes) | → 0.864 expected | derived |
| Policy loss (simulation against our reference) | 0.117 | measured |
| Eval-specific reference / anchor / mesh loss beyond the public norm | ≈ 0.075 | derived (0.864 − 0.789) |

There are two levers of similar size:
- the policy not following our reference;
- our reference (perception, frame-0 anchor, meshes) not matching the truth on eval episodes.

sim_vs_ref cannot see the second one.

## 2. Policy loss by episode (`rollout_errors.png`)

- Evals 10, 33 and 32 hold 54 % of the policy loss; 10 and 33 alone hold 46 %.
- "Pts" = Track 3 points if the episode tracked our reference perfectly (loss / 20).

| Eval | sim_vs_ref | Pts | What fails, when | Cause (evidence) |
|---|---|---|---|---|
| 10 | 0.344 (5 evals 0.29–0.35) | 0.033 | The beige cup tips over at frame 2 (89°) and lies there; our reference later stacks it into the blue cup | **Collision copy.** Our beige cup is an open shell with no base: it falls 6/6 at rest in FlashCHORD's physics. The blue cup's hulls fill its cavity (stack overlap up to 112 cm³). |
| 33 | 0.602 | 0.020 | Cup and spoon both 4–10 cm off from f90 to f290 | **Two-handed hold.** Left hand on the cup from f15 and right hand on the spoon from f60, both carried for about 270 frames. No geometry conflict (≤ 15 cm³ in 18 of 348 frames). |
| 32 | 0.809 | 0.010 | The cup tips during its grasp (17 cm spike, f13–30); the cup ends 13 cm off | Grasp approach and release; the same two-handed structure; no geometry conflict |
| 25 | 0.833 (5 evals: 4 × 0.80–0.81, 1 × 0.34) | 0.008 | Board 2 is twisted out after the insertion (f171, 115° at the end) | **Collision copy:** no slot. CPU: board 2 at assembly 104° → 0.5° with the cut; GPU rerun running. |
| 16 | 0.843 | 0.008 | The spoon flips when released into the rack's holder (13 cm, 128°) | Release dynamics; no geometry conflict |
| 3 | 0.867 | 0.007 | The pot is 10 cm off during two carries (f69–100, f190–205) | Grip slip during the carry |
| 14 | 0.893 | 0.005 | Blue cup spike when it is set into the rack (9.7 cm, f45–55) | Our reference puts the cup INTO our rack mesh (54 cm³ mesh overlap, 72 cm³ with hulls) |
| 1 | 0.914 | 0.004 | Pot spikes of 9 cm (f150–200) | Carry; the lid sits inside the pot's hulls (up to 51 cm³) |
| 30 | 0.921 | 0.004 | Sweeper 1.9 cm / 11° off from f56 | The sweeper starts inside our rack mesh (≈ 6–10 cm³ for 192 frames) |
| 19 | 0.924 | 0.004 | Sweeper and dust pan 2–4 cm off during the sweep | Contact-rich tool use |
| 28 | 0.927 | 0.004 | Pot 6 cm spike at f52 | The pot is set into the rack mesh (24 cm³) |
| 20 | 0.948 | 0.003 | Pitcher spike at f34 | Pour |
| 15 | 0.960 | 0.002 | The spoon rotates to 46° at the end | Release into the rack |
| 5, 6, 8, 35–38 | 0.967–1.000 | ≤ 0.002 each | — | — |

### What the videos show (replays with the robot hands; `ops/jobs/sub_videos.sh`, run `20261026-subvid2-d9c3f7d`)

**Episodes:**
- **Eval 33:** the person holds the cup in the left hand and scoops with the spoon INSIDE the cup with the right
  hand (f150, f220: the handle sticks out of the cup). In the simulation the spoon stays beside or above the rim.
  This replay scores 0.811; the packed rollout was a low draw, 0.611 against a 5-evaluation mean of 0.773.
- **Eval 32:** the person lifts the cup by its rim from above. The simulated left hand loses the cup during the lift
  (f20–28), and the cup falls back to the table.
- **Eval 16:** the spoon goes into the rack's holder in this replay (0.920), but flipped in the packed rollout (0.843).
  The release is a chance outcome.
- **Eval 25:** the replay lands in the bad mode (0.338, like 1 of its 5 official evaluations). Board 2 is twisted out
  of the joint.
- **Eval 10:** the beige cup tips over at the start in the replay too (0.347).

**How faithful the replays are:**
- Most replays land within ±0.03–0.06 of the packed rollouts.
- Eval 1's replay (0.529) is far below its 5 official evaluations (0.89–0.93). The pot is lifted far too high. The
  replay path (`view_policy.py`) differs from the evaluation harness (work log, 26 Oct), so this replay is illustrative only.
- The CPU renders of the packed rollouts are the exact record of what was submitted.

## 3. Our reference against the simulator's collision geometry (`hull_census/`)

**Method:**
- Each object's solid is posed by our reference in its partner's frame.
- It is tested against the partner's mesh and against the hulls FlashCHORD builds (CoACD 0.05).
- "Hull-only" volume is what the collision copy adds over the mesh: filled cavities, slots and holders.

**Conflicts above 10 cm³:**

| Eval | Conflict | Size |
|---|---|---|
| 10 | Stacked cups | 112 cm³ |
| 14 | Cup into the rack | 72 cm³ from f42 |
| 1 | Lid on the pot | 51 cm³ |
| 28 | Pot into the rack | 39 cm³ |
| 8 | Beige cup in the pot from f0 | 38 cm³; still scores 0.977 |
| 30 | Sweeper in the rack from f0 | 29 cm³ |
| 25 | Boards | 12 cm³ |

**Clean:**
- 3, 5, 6, 15, 16, 19, 20;
- 32 and 33 with their submitted references.

**Note:** the older references of 32 and 33 also showed nothing. My first reading of the frame strips, "the spoon cannot enter the cup", was wrong.

## 4. Hidden losses (not visible in sim_vs_ref)

**About 0.075 of eval-specific reference / anchor / mesh error** (section 1). Recorded evidence of where it can come from:
- **Pitcher (eval 20).** On its public twin (ep21), our reference scores 0.775 vs mocap, with the pitcher at 0.571 using our mesh against 0.95 with the scan. The twin policy tracks our reference at 0.983 but scores 0.772.
- **Spoon-anchored episodes (32, 33, 35, 36, 37).** The scorer aligns the scene on the spoon's frame-0 pose. Our roll uncertainty is 2–6°, which costs about 0.03–0.15 per episode (estimate).
- **Frame-0 detection and identity.** Every public failure started at frame 0 (e.g. eval 25's swapped boards, now fixed).
- **Resting heights.** Boards float 2–2.5 cm on ep24; the pot sits 29 mm too deep in the rack on ep26.

**Checked and cleared:** the 22 Oct claim that our sweeper registers flipped 178° at eval 30's seed does not reproduce
with library_v3 and the current kit. Eval 19 and 30 seeds agree with the majority solution to within 1°; 4 of 40 random seeds flip.

**Where the hidden 0.094 most likely sits (estimate, not a measurement):**

Method:
- Score each eval episode as sim_vs_ref × the mean public perception accuracy of its objects. The midpoints of the
  public ranges are pot 0.97, lid 0.965, blue cup 0.95, beige cup 0.93, rack 0.95, sweeper 0.96, dust pan 0.95,
  pitcher 0.66 and boards 0.82.
- Then solve for the one unknown, the spoon (there is no public spoon mocap), so that the total equals the
  leaderboard's 0.789.

Result:
- **Implied spoon accuracy: about 0.81.**
- The 10 spoon episodes would then hold about 0.063 of the hidden loss, and all other episodes 0.032.
- Spoon accuracy 0.95 would give about +0.045 on the leaderboard: the largest single lever.
- The estimate shifts if the pitcher or the boards are worse on eval than on their public twins.

Background (`docs/research/spoon-2026-10-25/`):
- The spoon anchors evals 32, 33, 35, 36 and 37. A 10° frame-0 roll costs 0.09–0.28 there.
- Our measured random roll is 2–6°. A systematic bias of the template or tracker cannot be measured without ground truth.

**Frame-0 spoon check (videos, camera a, frame 2):** in all five spoon-anchored episodes (32, 33, 35, 36, 37) our
reference spoon's outline lies on the real spoon. Position, direction and the marker knobs on the handle all agree.
No gross frame-0 error is visible. A few degrees of roll would not show from above.

If the inferred ≈ 0.06 spoon loss is real, the likelier sources are:
- tracking while the spoon is hidden inside the pot or cup (stirring in 3, 5, 6; scooping in 33);
- depth along the camera axis.

Neither can be seen in one top-down view; checking them needs a second camera.

## 5. What can be improved, ranked

| # | Lever | Episodes | Evidence | Expected Track 3 gain (estimate) | Cost |
|---|---|---|---|---|---|
| 1 | Hybrid cup collision copy (beige stands; empty blue cavity; 8 mm nest shrink) | 10 | CPU, FlashCHORD physics: beige falls 6/6 → 0/6; stack error 4.45 → 0.44 cm. The pre-registered standing rule failed as written (wrong check frame; work log) | +0.02 to +0.03 | 2 seeds ≈ $8–10 |
| 2 | Board slot carve | 25 | CPU proxy and FlashCHORD: 104° → 0.5°; GPU rerun running | +0.005 to +0.008 | ≈ $9 (running) |
| 3 | Secure two-handed holds: second seeds, the standard learner, the grip portfolio (approach 3, P1) | 33, 32 | Two-handed hold for ~270 frames; no geometry conflict | +0.01 to +0.02, uncertain | ≈ $10–15 |
| 4 | Collision carve for placements into the rack / pot (swept-volume carve, as for the slot) | 14, 28, 30, 1 | Hull census 29–72 cm³ conflicts | +0.005 to +0.012 | CPU 2–3 h + ≈ $15–20 |
| 5 | Spoon perception (frame-0 roll of the anchor; template; depth) | 32, 33, 35–37 (anchor); 3, 5, 6, 15, 16 | Inferred ≈ 0.06 hidden loss; no ground truth to validate | up to +0.045 if solved | CPU research first; re-reference + retrain ≈ $4–5 per episode |
| 6 | Pitcher mesh / track | 20 | Twin: pitcher 0.571 with our mesh vs 0.95 with the scan | ≈ +0.009 | Mesh work + 1 rerun |
| 7 | Release / placement (spoon into the rack holder) | 16, 15 | The spoon flips on release; no geometry conflict | +0.005 to +0.01 | Research |

| 0 | **Packing bug fix:** restore the rule-chosen seed-43 rollouts for 3/5/15/16 | 3, 5, 15, 16 | The third submission packed the first pack's seed-42 rollouts (sha256 check) | ≈ +0.005 | Next pack (≈ $0.7) |

**Projection, all estimates:**
- Items 1–4 together: ≈ +0.04 to +0.07, i.e. about 0.83–0.86.
- 3rd place (0.865) also needs item 5 or 6 to pay off.

## 6. Videos

**Location:**
- HF store: `runs/20261026-subvid2-d9c3f7d/results/sub_videos/ep<N>.mp4` (H.264, 1920×480).
- Panels: the real camera; the simulation drawn on the camera (our reference outline, robot-hand skeletons); a 3-D view.
- Each checkpoint was sha256-checked against the submitted rollout's json.

**Replay sim_vs_ref** (a fresh rollout) against the packed rollout:

| Eval | Replay | Packed | | Eval | Replay | Packed |
|---|---|---|---|---|---|---|
| 1 | 0.529 | 0.920 | | 20 | 0.953 | 0.895 |
| 3 | 0.902 | 0.875 | | 25 | 0.338 | 0.837 |
| 5 | 0.929 | 0.974 | | 28 | 0.921 | 0.929 |
| 6 | 0.944 | 0.971 | | 30 | 0.914 | 0.923 |
| 8 | 0.965 | 0.978 | | 32 | 0.747 | 0.789 |
| 10 | 0.347 | 0.342 | | 33 | 0.811 | 0.611 |
| 14 | 0.895 | 0.909 | | 35 | 0.983 | 0.983 |
| 15 | 0.894 | 0.958 | | 36 | 0.967 | 0.991 |
| 16 | 0.920 | 0.850 | | 37 | 0.976 | 0.998 |
| 19 | 0.893 | 0.928 | | 38 | 0.981 | 1.000 |

"Packed" is the box's qa yardstick from pack 3's summary.

**CPU renders of the packed rollouts** (objects only, exact):
- made with `tools/render_eval_rollout.py`, kept in the session scratch;
- they can be re-made from the pack's `episode_*.parquet`.
