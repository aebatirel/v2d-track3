# Plan: follow the perceived trajectory perfectly on all 20 eval episodes (1 Nov 2026)

Owner's goal (1 Nov): "I want the full score from the perceived trajectory".
- The metric is **sim_vs_ref**, our ground-truth-free tracking score: the official evaluator's rollout against our own
  reference (pipeline/qa.py), averaged over 10 official draws.
- Target: 1.0 on every eval episode.
- No ground truth is involved anywhere in this plan.

Labels: [M] measured, [E] estimate, [H] hypothesis, [I] inference.

## Why it matters for the board [E]
- On the public episodes, AUC loss splits about evenly between tracking our reference (≈ 0.083) and the reference
  itself (≈ 0.10) [M, 30 Oct]. Perfect following removes the first half.
- Failed draws dominate RPE / MPPE. Without them, eval RPE would be ≈ 1.6–2.4 cm [E]; the top six sit at 1.10–1.73.
- Today's standings: rank sum 60, 11th. One rank point would pass DSAIL; AUC needs +0.0047 to pass them.

## Where we are: per-episode sim_vs_ref [M]
Source: H5p7 10-draw means, run 20261031-h5p7-1a7cdff. Eval 10 uses pack 11's ck512. Mean 0.921.

| Eval | sim_vs_ref | Gap | Known cause |
|---|---|---|---|
| 14 | 0.727 (bimodal: 5 / 10 fail) | 0.273 | Hand-over at f42–45. The reference was locked single-hand (left carries f18–118, right parked) [M, grasp-ep13 branch] |
| 16 | 0.850 | 0.150 | Spoon flips on release; it rotates 29° even hands-free [M] |
| 32 | 0.852 | 0.148 | Cup tips in the grasp; two-handed hold |
| 25 | 0.878 | 0.122 | Board 2 twists after insertion; the carved slot is 16–20 mm, wider than the real one |
| 20 | 0.893 | 0.107 | Pitcher falls hands-free at f0 (195 mm). The b1 clip fixes it; the retrain missed its gate by 0.0004 |
| 30 | 0.897 | 0.103 | Sweeper starts inside the rack (12 cm³); one failed draw in 10 |
| 10 | 0.903 | 0.097 | Fixed by training at njmax 1024 (in pack 11). Residual overflow on the stock route |
| 15 | 0.906 (one draw at 0.62) | 0.094 | Spoon, contact-sensitive |
| 1 | 0.912 | 0.088 | Lid in the pot's hulls, carved (sd 0.010) |
| 28 | 0.919 (one draw at 0.70) | 0.081 | Pot touches the rack throughout |
| 33 | 0.923 | 0.077 | Two-handed hold; CURR_SCALE 0.4; robot palm pushes the spoon at f24 |
| 19 | 0.929 | 0.071 | Sweeper falls hands-free at f0 (89°). support_fill never ran in std mode; certified on CPU (4fa6ec4) |
| 3 | 0.933 | 0.067 | Pot slips in two carries |
| 5 / 6 / 8 / 35–38 | 0.965–0.998 | ≤ 0.035 | Near-perfect |

## What we already tried (don't repeat without a new reason)
- **Big wins: making the reference or simulation physically possible.**
  - eval 1: carve, sd 0.239 → 0.010;
  - eval 10: training-time contact overflow, 0.46 → 0.90;
  - eval 25: slot carve, 0.23 → 0.88;
  - eval 33: CURR_SCALE 0.4, 0.854 → 0.934;
  - eval 8: v5 beige cup with track guard;
  - TRACK_GUARD on perception.
- **Negative or inconclusive:**
  - start-state randomisation (D arm, worse on 4 / 5);
  - actor sees object velocity (−0.024);
  - command / target smoothing (fail);
  - recipe screen K / D / S (no signal);
  - masses: v1 mixed (ep2 +0.157, ep12 −0.013), v2 not adopted;
  - our physics solver: arm S no signal; its gain vanished under 0.5 mm target noise;
  - the solver–RL loop barely acted;
  - the GRASP optimiser: no gain on ep13 (branch claude/grasp-ep13-20261101);
  - human capsule hand (−0.161);
  - snapped / locked grasp in a zero-action replay (falsified);
  - public pose projection (perception side, falsified).
- **Diagnostics available, all CPU:**
  - drawdiv (docs/analysis/drawdiv-20261031): draws split in frames 1–11 and are decided at contact moments;
  - f0 settle survey and rest probe (bold-albattani a6923c5, determined-wright 2a809d6);
  - contact budget (determined-wright budget.py, 32×60);
  - CPU rollout renders (docs/analysis/lowvid-20261101).

## Work plan, in order of expected gain per dollar
1. **CPU preflight on all 20 eval references** ($0). For each, flag:
   - (a) single-hand locks that dropped a hand-over or two-hand hold: compare refs/sf (before the lock) with the locked
     reference;
   - (b) object motion requested with no robot hand within reach (as on ep13 f30–40);
   - (c) f0 and rest instability (settle survey);
   - (d) training contact overflow (budget.py, plus the "nefc overflow" lines in the packed train.log files);
   - (e) release stability (does the object stay put after the hand leaves?);
   - (f) target jitter: wrist / finger accelerations.

   Output: one table, episode × problem, with a proposed fix per flag.
2. **Error timeline per episode** ($0). From the stored H5p7 draws (10 per episode), find where the error builds up
   (onset frames, objects, contact events). Link each to a flag from step 1. Any loss with no explanation is a finding
   in itself.
3. **Public validation of the two main new levers** (GPU, pre-registered, ≈ $10–14 [E]):
   - (i) two-hand vs single-hand reference on public ep13 (eval 14's twin): grasp-lock RL, 2 seeds;
   - (ii) training at njmax 1024 (checkpoint saved at stock 512 / 256) vs stock, on 2–3 public episodes with moderate
     overflow (e.g. ep2 had 0.6 M lines);
   - gate per test: mean sim_vs_ref ≥ +0.02 and no seed worse than −0.03.
4. **Eval retrains with the fixes that apply** (GPU, ≈ $35–50 [E]).
   - 2 seeds each. Grasp lock ≈ $1.7 per seed; standard learner ≈ $2.9 per seed.
   - Candidates: 14 (two-hand), 19 (support_fill), 20 (b1 + 1024), 32 / 33 (two-hand if flagged), 16, 25, 30, 15, 28
     (as step 1 finds).
   - Each goes through the standing swap rule (pack-9b PREREG §4) plus the ≥ +0.02 inclusion bar, with 10 fresh
     official draws (≈ $2 per confirmation box).
5. **Contact-moment training** (GPU, only if steps 1–2 show losses at moments the fixes don't cover; ≈ $10–15 [E]). A
   reset-state bank that starts more training episodes just before hand-overs, releases and placements, from states the
   policy actually reaches. Public test first.
6. **Final H5 fresh draws for the new pack** (≈ $6) and the pack record. The owner or the uploader session uploads.

## Budget [E]
- Steps 1–2: CPU only, $0.
- Steps 3–6: **≈ $75–95 of GPU**, about 55–70 GPU-hours on RTX PRO 6000 class at ~$1.35–1.45/h. With a 20 %
  contingency the ceiling is **~$115**.
- Wall clock: about 1–2 days of work blocks with up to 5 boxes in parallel.
- Credit on 1 Nov at 18:57 UTC: $23.56, so an owner top-up of ~$100 is needed before step 4.
