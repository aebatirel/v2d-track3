# Pre-registration: GRASP-mode vs our annealed solver on public ep13 (CPU, $0)

Written 1 Nov 2026, before any ep13 solve by either method. Branch `claude/grasp-ep13-20261101`. Nothing below is
changed after an ep13 result. Labels: [M] measured, [E] estimate, [H] hypothesis, [L] literature.

## 1. Question and hypothesis
Public ep13 (blue cup, dish rack: left-hand grasp, left→right hand-over, 180° flip, cup placed in the rack) is the
public twin of eval 14. Eval 14 is our weakest remaining eval: packed sim_vs_ref 0.727, 4 / 10 official draws fail.
The oracle twins showed it is not perception-limited [M]: the grasp-lock learner on the TRUE object motion scores
0.544 ± 0.002, the same as on our perceived motion (0.543); both sit at the static floor. Both twin references, however,
drop the left-hand pick (§2), so "control-limited" may be "construction-limited" [I].

**[H-grasp]** At an equal CPU rollout budget, GRASP's window optimiser (Liu, Wang, Bao, Yang, Harvard 2026 [L]: an
archive of every rollout, local quadratic cost models fitted to it, gradient-guided MALA proposals, Metropolis–Hastings
acceptance on the true simulator cost, warm-started receding horizon) finds ep13 plans that the scored simulator copies
more robustly than our annealed sampling MPC does.
Falsified if the gate in §4 fails.

## 2. What is compared
Two solvers, one code base: `tools/physics_solve/solve.py --method anneal` (our Do-as-I-Do/SPIDER-style solver,
unchanged; regression-tested bit-identical to md5 fa511432) and `--method grasp` (`tools/physics_solve/grasp_window.py`).
They share everything except the window optimiser: FlashCHORD at the evaluator pin as the rollout simulator (condim 3,
finger kp 1.7, our `sharpa_hands_mid` embodiment, VOC 0), the cost (kit ADD on 64 sphere points, clipped at 10 cm per
object, + the offset regulariser, terminal ×3, mean over K robust copies), the decision variables (wrist / finger
residual offsets on knots every 4 frames), the hand gate, the commit (4 frames), the rollbacks, and the **budget: 8
rollout batches of 32 candidates × 4 robust copies (128 worlds) per replan**, with the same (1 + boost) multiplier on a
rollback.

Two input references, both the ones the oracle-twins box trained on (store run `20261030-orcB-38234d1`):
- (a) **oracle** O: `refs/oracle_glockt/ep13/.../ref_gl_ilc.parquet` (md5 455173ec): mocap object motion, our pipeline.
  A diagnostic on a public episode only; it never feeds an eval artifact.
- (b) **perceived** P: `refs/glockt/ep13/.../ref_gl_ilc.parquet` (md5 414d0200): our perception, the eval-like input.
Local copies by `scripts/prep_inputs.py` (only `object_urdf_paths` changed, checked). Assets `refs/{sf,oracle_sf}/ep13`.

**Added before any ep13 solve (work log 12:33 UTC):** both twin references park the left hand for all 190 frames
(`--single_hand 1` kept the right hand, which holds only from f46, while the cup's reference rises from ~f20), so the
hand-over is not in them and the solver's hand gate never enables the left hand. Therefore two tests:
- **Test A (as specified by the owner):** inputs O and P above.
- **Test B (two-hand rebuild):** O2 / P2 = the same support-filled inputs before the lock (`refs/{oracle_sf,sf}/ep13/
  .../ref_sf.parquet`) re-locked with the box's GL_ARGS minus `--single_hand 1` (`--mcp_first 1 --close 10 --palm_clear
  -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15`, GL_WRIST_KP 400), then `wrist_ilc.py --iters 4` (kp 400),
  through `tools/cpu_glock_zero.sh` on CPU (no REPLAN stage). Holds: P2 left f19–61 and right f46–104; O2 left f17–61
  and right f46–99 (overlap = the hand-over). No ground truth is read to build P2; O2 is a public diagnostic like O.

Eight solves, seed 0 each: {anneal, grasp} × {O, P, O2, P2}; Test B runs first. One seed per arm (CPU time); labelled
as such.

### 2.1 Settings (frozen)
Common (both methods): `--workers 4 --worlds 32 --robust 4 --horizon 16 --knot 4 --ctrl 4 --iters 8 --ramp 1 4
--sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.80 --retries 4 --retry 0.05 --back 3 --rob_pos 0.0005
--rob_fin 0.005 --seed 0`, no deadline. `--anneal 0.80` applies to the annealed sampler only: 0.80⁷ ≈ 0.21, the final
noise factor of G1/G2 (0.6³ = 0.216), so no new tuning of our solver.

GRASP mode: `GRASP_ARGS` = **`--g_sig_abs 0.0044 0.0044 0.044 --g_ess 0.5 --g_moves 2`** (dev config G5, chosen by the §6
rule), with the other GRASP options at their defaults: `--g_rho 0.9 --g_beta 100 --g_step 0.59 --g_acc 0.05 --g_rate 3
--g_step_min 0.1 --g_rank 2 --g_quad diag --g_ridge 1e-3 --g_window 3 --g_carry 0.5`.

GRASP settings taken from the paper's hand configuration (`experiments/paper.py` HAND) [L]: AR(1) ρ 0.9, prior widening
×4 across the window (our `--ramp 1 4`), DCT surrogate rank 2, MALA step 0.0026 / 0.0044 = 0.59 prior widths with the
prior-covariance preconditioner, adaptive step (target acceptance 0.05, rate 3, min ×0.1), warm start on the previous
plan, ridge 1e-3, window 3. Adapted to the CPU budget and to solve.py (deviations, all labelled in
`grasp_window.py`): the budget stops tempering before λ = 1; the commit takes the lowest-cost plan evaluated in the window
(the annealed sampler's rule); β = G_BETA / J(warm start); a diagonal quadratic in the DCT basis (the archive per window,
≤ 256 points, is far smaller than the full model); half of each window's initial particles are the previous window's
final population shifted by the commit (GRASP's light-window library, simplified); no joint start, no pinned first knot.

## 3. Measurements
Per arm (`scripts/run_ep13.sh REF METHOD`):
1. the solve; its committed truth trajectory and output parquet;
2. **exactness:** the official zero-action replay (`tools/trace_rollout.py zero`) of the written parquet vs the
   solver's truth trajectory: bit-identical (max |Δq| 0.0) expected, as for our solver; and the fresh-load target-buffer
   check inside solve.py;
3. **metric:** `tools/physics_solve/jitter_check.py OUT.parquet --k 17 --seed 0`: copy 0 = the nominal zero-action
   replay, copies 1–16 = the same replay with N(0, 0.5 mm) wrist-position and N(0, 0.005 rad) finger target noise on
   every frame. Score = sim_vs_ref against the input reference's object track (the solver changes only robot targets,
   so this equals the input reference). **Jittered mean = mean of copies 1–16.** Seed 0 and k 17 for every arm and both
   inputs: common noise draws, so per-copy differences are paired.
Also measured (report only): the four inputs' own jittered means (`scripts/jitter_inputs.sh`), the floors (0.5561 P,
0.5727 O; P2 / O2 share P / O's object tracks), wall time, rollbacks, GRASP stage diagnostics (λ reached, acceptance,
surrogate R²). Two-hand rebuild vs the twins' reference (P2 − P, O2 − O, jittered, the anneal and grasp outputs and the
inputs): report only, it answers whether the construction is the lever.

## 4. Gate (primary; decides the next step)
Per test: d_b = jittered mean(grasp, perceived) − jittered mean(anneal, perceived); d_a = the same on the oracle input
(test A: P and O; test B: P2 and O2).

**A test PASSES iff d_b ≥ +0.05, and neither d_a nor d_b is below −0.05** ("no copy-mean worse than ours by more than
0.05"). An arm with no result (crash, missing output) counts as FAIL. Computed by `scripts/gate.py`.

- Test A is the owner's gate. Test B is the same rule on the rebuilt inputs; it is reported as its own verdict, with
  the caveat that two tests double the chance of a lucky pass (one seed each).
- Either test PASSES → propose (not launch) the GPU step: RL from the GRASP-solved perceived reference of the passing
  test on ep13, then eval 14 under the standing pack swap rule plus the ≥ +0.02 inclusion bar, with cost; **wait for the
  owner's explicit go**. (If only test B passes, eval 14 would also need its own two-hand or first-picker lock; eval 14's
  packed lock already gives the whole carry to the left hand, its first picker [M].)
- Both FAIL → no GPU spend on GRASP-mode as it stands. The write-up records [H-grasp] as falsified **at this CPU
  budget** on ep13.

Report-only (no decision attached): the paired per-copy Δ with a bootstrap 95 % interval and its win count; Δ on copy 0;
each arm vs its input and vs the floor; the cup's tracking per copy (share of frames within 3 cm, first lasting loss,
ADD at f110 and f189).

## 5. Expected cost and time [E]
$0 (this container, 4 CPUs). Dev arm on ep31: 8 batches of 32 × 4 worlds × 16 frames ≈ 45 s per active replan [M]. An
ep13 solve: 48 replans, 37 active on A (+ rollbacks) ≈ 30–75 min; eight solves ≈ 5–9 h, one after another; jitter
checks ≈ 2 min each.

## 6. Development (ep31 only, before this file was frozen)
Public ep31 (sweeper + rack, `refs/glockt/ep31`), frames 16–48, the §2.1 scale without rollbacks
(`scripts/dev_ep31.sh`). Dev metric: per-replan J_best / J_warm (the solver's own predicted improvement), not the gate
metric. **Selection rule (written 12:35 UTC, before G2–G5 finished):** the ep13 GRASP configuration is the dev config with
the lowest mean J_best / J_warm; a tie within 0.002 goes to the config closer to the paper (G4 > G1 > others).
Configs: G1 ESS 0.9, 2 moves, widths 0.8 × our noise; G2 ESS 0.5, 2 moves; G3 ESS 0.5, 1 move; G4 GRASP's own widths
(σ 0.0044 m / rad, fingers ×10) ESS 0.9, 2 moves; G5 G4 with ESS 0.5. All β_rel 100, ρ 0.9, rank 2, diag, carry 0.5.
Results [M] (8 active windows each; code 3d511983 / 8b630e61 + the solve.py of this commit; md5 39e9307f or the
behaviour-identical e73b4b89):

| config | settings | mean J_best / J_warm | windows improved | mean realised object cost | wall |
|---|---|---|---|---|---|
| anneal | iters 8, anneal 0.80 | 0.9853 | 2 / 8 | 0.02713 | 459 s |
| G1 | ESS 0.9, 2 moves, widths 0.8 × our noise | 1.0000 | 0 / 8 | 0.04469 | 462 s |
| G2 | ESS 0.5, 2 moves, 0.8 × our noise | 0.9892 | 3 / 8 | 0.03669 | 530 s |
| G3 | ESS 0.5, 1 move, 0.8 × our noise | 0.9759 | 2 / 8 | 0.03161 | 533 s |
| G4 | ESS 0.9, 2 moves, GRASP widths | 0.9668 | 3 / 8 | 0.02948 | 463 s |
| **G5** | ESS 0.5, 2 moves, GRASP widths | **0.9582** | **5 / 8** | 0.02274 | 411 s |

Selected: G5 (lowest ratio; G4 is 0.0086 behind, outside the 0.002 tie margin). Diagnostics: with our noise widths the
tempering either stays near the prior (ESS 0.9) or jumps to λ = 1 and then rejects every move (ESS 0.5); with GRASP's
narrower widths acceptance stays 0.5–0.8 and the surrogate's R² falls from 1.0 to 0.7–0.9 as the archive grows.

**Known confound (stated before any ep13 result):** G5 differs from the annealed arm in two ways, the optimiser and the
exploration widths (GRASP's σ 0.0044 m / rad and 0.044 rad for fingers vs our 0.01 m, 0.05 rad, 0.15 rad). The gate
compares the two solvers as configured. **Conditional attribution control (pre-registered, report only):** if a test
passes, the annealed sampler is re-run on that test's perceived input with `--sig_pos 0.0044 --sig_rot 0.0044 --sig_fin
0.044` (else as §2.1) and jitter-checked the same way; the write-up then says whether GRASP's edge survives equal widths.

Frozen at the commit that adds this table; the ep13 runs start after it (`scripts/run_all.sh`).
