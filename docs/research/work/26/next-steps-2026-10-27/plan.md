# Next steps, 27 Oct 2026

**Short answer:** top up $20 now; $75 released in stages is better. Spend it on measuring how much our scores vary between runs, on the eval-10 stack, and on spoon perception. A better mesh mostly helps the CD-O board. On AUC it is worth about +0.00 to +0.02.

**Key.** M = origin/main-bsky37, B = origin/claude/bold-albattani-6qmxsv, C = claude/focused-pascal-2nz9s1 (note 23). WL = M:docs/work-log.md. RC = M:docs/analysis/robustness-review-20261026/refcheck/README.md. Labels: [M] measured, [E] estimate, [D] arithmetic on measured numbers.

**Where we stand**
- AUC is 0.81391, 5th place. DDD is 0.013 ahead of us, 3rd place 0.051, 1st place 0.118 (M:results/submissions/20261026-track3f receipt; M:results/submissions/20261026-track3d/README.md).
- The AUC we lose splits into:
  - 0.0835 because the policy does not follow our reference [M];
  - about 0.10 because our reference differs from the truth [E].
- Our packed rollouts were lucky draws, 0.033 sim_vs_ref above their own 5-run means. A re-run would score about 0.79 [E] (scores report §1, §3).
- 1st place would need 63 % of all remaining loss closed [D]. 4th is realistic. 3rd needs eval 10 and the spoon fixed.

## 1. Ranked plan (AUC first; all gains are [E])

**1. Measure the spread between runs (H5), then re-seed only where it pays.** Continues existing work.
- **Gain:** 0 to +0.005 on the public board. It also protects about 0.02 if the organisers re-run our policies.
- **Evidence:** the packed draws sit well above the 5-run means (M:results/submissions/20261026-track3f/summary.txt; WL 24–26 Oct):
  - eval 14: 0.909 packed vs 0.66 mean;
  - eval 33: 0.932 vs 0.785 ± 0.255;
  - eval 25: 0.894 vs 0.792.
- Replacing a lucky draw loses points in expectation.
- **Cost:** about $2, plus $2–3 per extra seed (M:STATUS.md).

**2. Eval 10 stack, fixed from the task side.** New direction.
- **Gain:** 0 to +0.02. The headroom is 0.0286, enough to pass DDD on its own.
- **Evidence:** seven policy-side tries scored 0.438–0.465 (WL:4303-4450). At kp 400 the cup hits the rim at up to 9,650 N and flies 80–120 cm (M:docs/analysis/ev10-stack-20261026/README.md). That is a clearance and release problem, not a stiffness one.
- **Cost:** CPU screen at $0, then $2–4.

**3. Spoon perception (10 episodes).** Continues existing work.
- **Gain:** 0 to +0.045, if spoon accuracy reached 0.95 (M:docs/analysis/forensics-20261026/README.md §4).
- **Caveat:** the 0.070 hidden spoon loss is what the model leaves over, not a measurement (RC §3).
- **Cost:** proxy check H2 at $0, then repeatability check H1 at about $3, then re-reference at about $4–5 per episode.

**4. "Push to perception": remove biases in our reference.** Continues existing work.
- **Gain:** +0.003 to +0.012.
- **Evidence [M]:**
  - Snapping objects to the table at frame 0 costs −0.016 on average on the public references (refcheck/systematics/README.md).
  - The eval references carry the same snaps (perception report §4): pitcher +1.00 cm (on its public twin the snap cost the pitcher −0.112), racks +0.83 to +1.12 cm, boards +0.93/+1.22 cm.
  - Advancing our paths by half a frame gave +0.003 on rollouts (refcheck/timing/README.md).
- **Cost:** CPU tests are $0. A fix reaches Kaggle only by retraining, at $2–3 per episode, and only 0.74 of the gain transfers [M].
- Note 23's Kalman smoother fits here as a $0 side test. Expect little from it: our errors are mostly bias, not jitter.

**5. Run-to-run spread on the grasp-lock episodes 32, 33, 14 and 16 (note 23).** New work.
- **Gain:** +0.003 to +0.01.
- **Evidence:**
  - These runs end in the curriculum's 0.1 stage (M:ops/box/patch_flashchord_drop.py:9-11).
  - The `CURR_SCALE` setting exists but was never used (M:ops/jobs/glock_public.sh:62-65).
  - The ball-wrist damping (kd) is still 6.
- **Cost:** $1–2 per run.

**6. Mesh: build a registration-stability gate and ship new meshes to CD-O only.** AUC 0 to +0.01; CD-O 0.402 → about 0.31–0.37. Details in §3.

**Other note-23 levers**
- **Stiffer wrist (the G1 batch, $75–100): mostly done already.**
  - 15 of 20 episodes already run at kp 400 (M:flashchord_conf/embodiment/sharpa_hands_mid.yaml).
  - kp 400 hurt the standard learner (WL:551-555).
  - The standard learner's 5 episodes have at most 0.019 of headroom.
  - At most, run a $4–6 kp-100 slice on evals 1 and 28 after the organisers clear stiffer wrists. The email asking them was never sent (M:docs/organiser-email-draft-2026-10-22.md).
- **Already in production:** feed-forward on the wrist target and the zero-action replay screen (M:pipeline/grasp_lock.py, M:pipeline/wrist_ilc.py).
- **Blocked:** the force-closure reward, whose slot is used by FDR.
- **Parked:** the object-velocity observation.
- **Pour hand leaving the camera view:** already bridged in the reference; it costs about 0.003 [M] (perception report §3).
- **Housekeeping:**
  - Run audit_ref.py on its own.
  - Do not merge C's pipeline_ep.sh hook: it conflicts with M.
  - Renumber note 23: the number clashes with M:docs/research/notes/23-grasp-controller-and-rl-handoff.md.

## 2. First GPU test (T1), with rules pre-registered in STATUS.md

| Arm | What | Episodes | On-demand cost |
|---|---|---|---|
| A | H5: 10 more evaluations of all 20 packed checkpoints | eval, scored by sim_vs_ref only (no ground truth) | ≈ $2 |
| B | Eval-10 reference with more clearance, fine-tuned at seeds 42 and 43. CPU screen first: replay ≥ 0.63, no cup flight > 10 cm | eval 10 (the reports name no public twin) | $2–4 |
| C | Grasp lock with `CURR_SCALE=0.4` | public ep12 (scored against mocap); eval 32 at seed 46; eval 33 at seed 43 | $3–6 |
| D (optional) | Arm C plus ball-wrist kd 2 | same three | $3–6 |

**Cost**
- $7–12 for arms A–C, $10–18 with D, plus the $3 safety margin.
- Interruptible boxes: the reports give no price. They were preempted within about 10 minutes (WL:4283), and a fine-tune takes about 19 minutes (WL:2336). Only arm A suits interruptible, saving at most $1 [E].

**Rules, fixed before launch**
- **Arm A:** re-seed an episode only if its 10-run mean is at least 0.05 below its packed score and its sd is at least 0.08. The second final pick is the pack with the highest 10-run mean.
- **Arm B:** adopt if both seeds score ≥ 0.50 and their average is ≥ 0.52 (packed: 0.456). If neither seed reaches 0.47, stop GPU spending on eval 10.
- **Arms C/D:** adopt for an episode only if all three hold:
  - its 5-run mean is at least the old mean + 0.03 (eval 32: 0.803; eval 33: 0.785);
  - its sd is no higher;
  - ep12 drops less than 0.03 from 0.910 (WL:2394-2404).
- To replace a packed policy, the new one must also beat the packed draw (0.866 / 0.932), unless you prefer lower spread.

**What T1 decides:** the final picks and how much re-seeding to buy (A), whether eval 10 gets more money (B), and whether these note-23 changes enter the grasp-lock recipe (C/D).

## 3. Would a better mesh help?

**CD-O board: the mesh is nearly the whole lever.** All [E] (B:docs/research/mesh-2026-10-26/README.md; B:STATUS.md):
- Pot/lid/rack swap: 0.402 → about 0.367.
- Adding the cup lathes: about 0.31.
- Generate-then-fit: 0.20–0.28. This has never been run.
- Leaders are at 0.112 and 0.154. We would move from 11th to about 7th, or about 4th–5th at 0.25 or better.
- CD-O does not rank Track 3.

**AUC, through how our mesh registers to the hidden scan:** ceiling +0.01–0.02, realistic −0.005 to +0.01 [E].
- The only mesh swap we sent to Kaggle (a lathed pitcher) lost 0.0045 [M] (M:results/submissions/20261026-track3f/README.md). Two reasons:
  - its registered yaw wanders from −14° to +7° depending on the seed (refcheck/scorer/README.md §2e);
  - our tracks had absorbed the old mesh's bias, worth +0.02 to +0.07 per object (refcheck/chain/README.md §2).
- Best candidate: the blue cup. It anchors the scene (slot 0) in 6 evals, and its offset shrinks from 10 to 4.1 mm [D].
- The sweeper sometimes registers flipped: on 3 of 24 and 4 of 24 stand-in hosts, −0.034 per flip (RC R3). Today's score already includes whatever Kaggle did, so a fix mainly cuts variance.

**AUC, through the simulator's collision copy:** the largest mesh effects we have measured.
- Eval 10: 0.342 → 0.452. Eval 25: 0.71 → 0.792. Eval 20 public twin: 0.657 → 0.772.
- Placement carves for evals 14, 28, 30 and 1: +0.005–0.012 [E], about $15–20.
- This needs watertight meshes with real cavities and bases.

**Is mesh the best use of effort for AUC? No.** The policy loss (0.0835) and the spoon (up to 0.045) are much bigger than the mesh ceiling (at most 0.02).

**Keep:**
- autokit stages 1–2 on CPU, for CD-O;
- io_gt.py;
- a stability gate: reject a mesh if more than 10 % of 30 seeds land over 5° from the median pose (RC §4.1);
- watertight simulator copies.

**Stop:**
- putting new meshes into the AUC file without the gate and at least 2 public twins (a single A/B is ±0.03 noise);
- generic-only fitters;
- re-tracking all 20 episodes ($30–55);
- the generative probe ($4–8), except for CD-O.

## 4. What you need to do

**Top-up**
- $20 minimum, for T1.
- $75 recommended, released in stages with a report after T1. It covers:
  - T1 including arm D: $18;
  - the spoon repeatability check (H1): $3;
  - retraining about 5 episodes after reference fixes: $10–15;
  - placement carves: $15–20;
  - 3 spoon re-references: $12–15.
- For scale, your professor called $1,000–1,500 reasonable (M:docs/context-and-decisions.md).
- Do not fund G1.

**Decisions**
1. Approve T1.
2. Choose the final-pick rule (lower spread or higher mean) and a tie-break.
3. Adopt the proxy-first spoon rule.
4. Eval 10: may we relax the nest-phase termination?
5. CD-O: does the 22 Oct per-episode mesh rule apply (it adds $2–4), and may the CD-O mesh differ from the mesh in the AUC file?
6. Send the organiser email.
7. Choose the submission repo and how it is shared, and the two final picks.
8. Confirm we will not test a sweeper mesh on Kaggle: that would be tuning on eval results.

**Can run now at $0 (CPU)**
- spoon proxy check H2;
- gated table snap and the table plane under the pitcher;
- anchor tilt;
- the smoother;
- audit_ref.py on the 20 eval and 10 public references;
- the mesh stability gate;
- the eval-10 CPU screen;
- autokit;
- the CD-O pot/lid/rack upload, once decision 5 is made.

**How sure are these numbers?** Every gain above is an estimate. Only 0.74–0.78 of a sim_vs_ref gain shows up in AUC [M]. The spoon and mesh shares are inferred, not measured on eval.

A copy of this text is at /tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/nextsteps/synthesis.md