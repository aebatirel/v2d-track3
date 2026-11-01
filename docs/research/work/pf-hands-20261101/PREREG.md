# Hand-assignment arms (perfect-following lane), pre-registered 1 Nov 2026 ~20:55 UTC, before any GPU result

Session: perfect-following (session_01D9UJC8Nz9EEFNmz2yzimzN). Job: `ops/jobs/pf_arms.sh`; verdicts: `tools/pf_verdict.py`.
Evidence that motivates it (docs/analysis/perfect-following-20261101/README.md) [M]:
- eval 14: the human hands the cup over L18–51 → R35–77 → L78–118; the packed `--single_hand 1` reference keeps the left
  hand on it throughout (robot right grips 0 % of its phase); cup error onset f42–46 in 9 / 10 H5p7 draws.
- public ep13 (eval 14's twin): the single-hand lock picks the RIGHT hand (most hold frames, from f46, after the cup has
  risen); orcB's P and O arms both end at the static floor (AUC 0.543 vs floor 0.542; sim_vs_ref 0.556 / 0.573).
- CPU zero-action replay of eval 14 (one replay each, this container): single-hand 0.293, two-hand 0.586 (floor 0.588).

## 1. Hypothesis [H]
Keeping every human hold phase as a robot hold (no `--single_hand`), so hand-overs and two-hand holds are kept, makes the
reference physically followable and raises the tracking score where the human uses both hands.
Falsified on the public twin if section 3's rule fails.

## 2. Arms (only GL_ARGS differ; same box, commit, recipe, base reference, seeds)
- common: `--mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15`
- `s`  = common + `--single_hand 1` (the packed construction);
- `2h` = common only.
Recipe = the packed grasp-lock recipe: glock_public.sh SF 1, REPLAN 1, EVOLVE 0, 70,004,736 steps, CURVE_REP 3, NREP 10,
library_v3, stock sim=rl limits 512 / 256, checkpoint chosen by sim_vs_ref (GT-free). Seeds 42 and 43.

## 3. Public test (box pfA): ep13, arms s and 2h, base = the stored perceived reference of run 20261030-orcB-38234d1
(refs/perc2mck/ep13, the P side only; no oracle input).
- Metric: registered AUC vs mocap (pipeline/score_registered.py, public evaluation only, after training), mean of each
  cell's NREP 10 rollouts of its chosen checkpoint.
- **Rule:** 2h passes if mean over seeds of (AUC_2h − AUC_s), paired by seed, ≥ +0.05 and no seed's difference < −0.05.
  INCOMPLETE if a cell has < 8 scored rollouts. Reported, not gating: sim_vs_ref plain and symmetric per cell.

## 4. Eval retrains (box pfB): evals 14 and 16, arm 2h only (the packed policy is the control), seeds 42 / 43
Base = the packed episode's own perceived base reference refs/perc2mck/ep<N> (packed_refs.json pull_files). GT-free.
Run in parallel with section 3 to save wall time. **Eval adoption needs BOTH** the section-3 public PASS and this
episode's swap rule; if the public test fails, nothing from pfB enters a pack, whatever its score.
Per episode:
1. Seed choice (pack-9b PREREG §2): each seed ≥ 8 scored training-box rollouts; higher mean sim_vs_ref vs our reference;
   within 0.005 the lower sd (ddof 1); then seed 42. Missing seed = INCOMPLETE.
2. Training-box gate: chosen mean > the packed policy's H5p7 fresh-draw mean (14: 0.7269, 16: 0.8498 [M]); else NO-SWAP.
3. Confirmation: 10 fresh official draws on the pristine evaluator (kit run_policy_evaluation.py, clean worktree).
4. Swap rule (pack-9b PREREG §4, verbatim): (a) mean sim_vs_ref ≥ packed H5p7 mean; (b) share RPE > 5 cm ≤ packed;
   (c) median RPE ≤ packed; (s) draw 1 ≥ old packed draw (pack 6) − 0.05; scored by tools/dr_score.py vs P (the packed
   reference; the arm changes robot-hand tracks only, object poses equal P's, checked per rollout).
5. Inclusion bar (binding): confirmation mean − packed H5p7 mean ≥ +0.02.
Reported, not gating: symmetric sim_vs_ref of every confirmation draw (tools/simref_timeline.py), onsets.

## 5. Cost [E]
pfA: 2 waves of 2 trainings ≈ 3 h + setup ≈ $4.5–5. pfB: same ≈ 3 h + confirmations ≈ 0.7 h ≈ $5–6. Total ≈ $10–11.
