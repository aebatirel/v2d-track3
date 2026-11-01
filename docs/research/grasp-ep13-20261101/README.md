# GRASP-mode solver on public ep13 (eval 14's twin): build, checks, pre-registered test (1 Nov 2026, CPU, $0)

Branch `claude/grasp-ep13-20261101` (off determined-wright 5bab5c6). Pre-registration: `PREREG.md` (frozen at d8544cf
before any ep13 solve). Labels: [M] measured, [E] estimate, [H] hypothesis, [I] inference, [L] literature.
No ground truth was read by any solver or reference build (the oracle reference O is a stored public diagnostic input).
Nothing rented, nothing sent to Kaggle.

## 1. What was built
- `tools/physics_solve/grasp_window.py`: a numpy re-write of GRASP's window optimiser (Liu, Wang, Bao, Yang, Harvard
  2026; github.com/ComputationalRobotics/GRASP_code @ 992c737, MIT) from GRASP's own optimiser files
  (`grasp/optim/{surrogate,sampler,prior_ar1}.py`, `grasp/mpc/grasp_mpc.py`), with the MIT notice:
  - AR(1) prior over control knots centred on the previous window's plan (warm start), widening ×4 across the window;
  - tempered SMC with an adaptive ESS schedule and systematic resampling;
  - a locally weighted ridge quadratic fitted, at every stage, to the archive of every rollout evaluated in the window
    (rejected proposals included), in a rank-2 temporal DCT basis;
  - Langevin (MALA) proposals along that model's gradient, preconditioned by the prior covariance (MALA in whitened
    coordinates); **Metropolis–Hastings acceptance on the true simulator cost**, so the model only steers proposals;
  - adaptive step size; half of each window's initial particles carried from the previous window's final population.
  - No SPIDER-derived file was used: GRASP's THIRD_PARTY_NOTICES.md lists them (`grasp/sim/*`, `grasp/config.py`,
    `grasp/utils/*`, most of `grasp/pipeline/*`, CC BY-NC 4.0).
- `tools/physics_solve/solve.py --method grasp`: the same FlashCHORD solver (condim 3, finger kp 1.7, our
  `sharpa_hands_mid` embodiment, VOC 0) with GRASP's window optimiser instead of the annealed sampler. Same cost (kit
  ADD + regulariser, mean over robust copies), decision variables, hand gate, commit, rollbacks and rollout budget. The
  robust copies' target noise is fixed per window, so the cost is deterministic and the MH test exact.
  New options: `--method`, `--g_*` (see `--help`); `--g_sig_abs` sets GRASP's own prior widths.
- Scripts in `scripts/`: `prep_inputs.py` (local reference trees), `dev_ep31.sh` (development), `run_ep13.sh` (one arm:
  solve → official replay → exactness → jitter check), `jitter_inputs.sh`, `run_all.sh`, `gate.py`.

## 2. Checks [M]
| check | result |
|---|---|
| unit tests `tools/physics_solve/tests/grasp/test_grasp_window.py` (AR(1) inverse and adjoint, DCT orthonormal, surrogate exact on a quadratic, toy window, carry rows, MALA/MH samples the exact Gaussian posterior) | all PASS |
| default path (`--method anneal`) of the new solve.py vs the original (md5 fa511432), ep31 f0–44, same seed | identical output parquet (md5 bfecffd6), offsets and truth trajectory |
| GRASP mode: fresh load of the written parquet vs the patched truth env | target buffers bit-identical |
| GRASP mode: official zero-action replay (`tools/trace_rollout.py zero`) of its output vs its committed trajectory (ep31 smoke, 45 frames; dry run, 29 frames) | **bit-identical** (max \|Δq\| 0.0), as for our solver |
| CPU replay determinism (ep13 P, two replays) | bit-identical |

## 3. Finding: the ep13 twin references have no hand-over [M]
- The oracle-twins box locked both ep13 references with `--single_hand 1`. `pipeline/grasp_lock.py` then keeps one
  carrier per object, the hand with the most hold frames (right, f46–104), drops the other hand's holds and parks it.
- In `refs/glockt/ep13` (P) and `refs/oracle_glockt/ep13` (O) the left wrist stays at z = 57.0 cm for all 190 frames;
  its frames never come within 15.7 cm of the cup's bounding sphere. Before the lock (`refs/sf/ep13`) the left hand is
  on the cup over f20–60 and the right hand from ~f40.
- The cup's reference rises 9–12 cm by f30–40, before the right hand arrives (1.6 cm at f40) and holds (f46). The
  robot reference asks for a lift with no hand near the cup.
- So the oracle twin's O ≈ P at the floor shows ep13 is not perception-limited, but both arms shared this
  construction: "control-limited" may be "construction-limited" [I].
- Eval 14's packed reference (`20261025-evb1420-ee7ba8e`, our perception only) was also locked single-hand, but there
  the lock chose the LEFT hand, its first picker (f18–118, merged from 3 holds), and parked the right. The twins' ep13
  references are therefore not built like eval 14's.
- Hence test B in the pre-registration: the same `ref_sf` inputs re-locked without `--single_hand` (two-hand holds:
  P2 left f19–61 + right f46–104; O2 left f17–61 + right f46–99), then wrist ILC. Nominal zero-action sim_vs_ref:
  P2 0.5268, O2 0.6474 (floors 0.5561 / 0.5727; the twins' P / O give 0.5406 / 0.5724 on CPU).

## 4. Development on ep31 (before freezing; dev metric = the solver's own J_best / J_warm)
See `PREREG.md` §6. Selected G5: GRASP's own prior widths (σ 0.0044 m / rad, fingers ×10), ESS 0.5, 2 moves per stage:
0.958 (5/8 windows improved) vs our annealed sampler's 0.985 (2/8). With our wider noise, GRASP's tempering either stayed
near the prior (ESS 0.9, 0/8 improved) or reached λ = 1 and rejected every move (ESS 0.5).

## 5. ep13 results
(pending; filled in from `scripts/gate.py` output)
