# Masses transfer check on our meshes: pre-registration

Written 2026-10-31 ~05:15 UTC, before any result of this check. No GPU box has run it; the CPU mock (stub trainer and
evaluator, `cpu/`) produces no evidence about masses. The rule below was proposed to and agreed with the physics session
(work log 31 Oct 04:55 UTC) and is fixed now. The launch commit must contain this file unchanged.

Markers: [M] measured, [E] estimate, [H] hypothesis.

## 1. Question and hypothesis
- **H-mass [H]:** realistic per-object masses (`docs/research/physics-2026-10-30/props_masses_only.json`, mass only)
  instead of the kit's 0.3 kg placeholder raise the frozen grasp-lock recipe's rollout AUC vs mocap on OUR pipeline
  (library_v3 meshes, our perceived references) by ≥ +0.03 on each of ep2 and ep12.
- Evidence behind it [M]: physics Round 3 (branch `claude/determined-wright-3joens`,
  `docs/research/physics-2026-10-30/README.md`). Seed-mean gains of +0.160 on ep2 and +0.103 on ep12 (ep12's mass arm had
  one seed). Those runs used the organiser scans as simulator meshes, and each arm rebuilt its references under its own
  masses.
- The experiment that can falsify H-mass for our pipeline is this job. The rule is in section 3.

## 2. Design (fixed)
| | ep2 (pot + lid; public twin of eval 1) | ep12 (cup into rack) |
|---|---|---|
| reference the arms train on | grasp-lock reference **built on the box once**, frozen recipe, 0.3 kg (`glock_public.sh REF_ONLY=1`), from base `20261024-ev3-2c1e4dd` `refs/perc2mck/ep2` | **stored** grasp-lock reference `20261024-ev2-2c1e4dd` `refs/glockt/ep12/.../ref_gl_ilc.parquet` (the one recipe arm A trained on, 29 Oct: 0.912 ± 0.033, seed 42) |
| expected file [M, local store copies] | base md5 `ec1a2e785591319877a10fad32d00ae1`, fingerprint `30c9ad1bcfce850ed3a2cf578a290477` (e3-e49e83d's file, which ev3 pulled) | md5 `c08eaf3f581ee9b405408b9bb91a14d4`, fingerprint `f7d8bb94a6087baa06e2f262e47118e9`; asset copy `refs/sf/ep12/assets`: `blue_cup_rigid.urdf` 31cd001d… (0.3 kg), `plastic_dish_rack_rigid.urdf` ae549ee0… (0.3 kg) |
| objects, M1 masses | white_pot 0.2771 kg, white_pot_lid 0.0882 kg | blue_cup 0.128 kg, plastic_dish_rack 0.3865 kg |

- **Why ep2's reference is built on the box.** The store's grasp-lock reference for ep2 is E3's of 23 Oct. It used
  approach 6 cm and REPLAN 1, with no onset anchor and no evolutionary search (fingerprint `1ce86a8f…`), so it is not
  the frozen recipe. It is built once here, and every arm and seed trains on that one file.
  - The fingerprint (md5 over every column except the asset paths) is written to `results/mass_check/stored_refs.txt`.
    A mismatch with the expected values above is reported. It does not change the design, because both arms still
    share the file.
- **Arms.**
  - M0 = `mass0`: the 0.3 kg placeholder (control).
  - M1 = `mass1`: the masses above. Each COM is unchanged. Each inertia is scaled by m / 0.3, so the gyration radii are
    unchanged. This is what `make_assets.py --physics` does for a mass-only entry.
- **The only difference between M0 and M1.**
  - `tools/mass_arm.py` gives each arm its own copy of the reference's asset folder and its own copy of the reference
    parquet. In the parquet copy, only `object_urdf_paths` changes: it points at the arm's asset folder.
  - The two arms' URDFs differ only in the `<mass>` and `<inertia>` lines (plus a comment). Meshes are byte-identical.
  - MA_ARGS is not used. A grasp-lock reference names its own asset copy (`refs/sf/ep<N>/assets`), which
    `make_assets.py` never writes.
- **Recipe (frozen; `ops/jobs/recipe_arms_launch.sh` GLOCK_COMMON):**
  - SF 1, REPLAN 0, EVOLVE 1 (reference build only), GL_ARGS of the recipe arms (approach 15, onset anchor);
  - FDR rewards and the VOC fix, the default curriculum, the kp 400 embodiment, 70,004,736 steps, REUSE_REF 1.
- **Checkpoint choice** uses no ground truth: the best mean sim_vs_ref over 3 official evaluations per checkpoint.
- **Scoring:** NREP 10 official evaluations of the chosen checkpoint (FlashCHORD `scripts/evaluate_policy.py` on the
  training box, as `glock_public.sh`). Each evaluation is scored as registered ADD-AUC vs mocap (`score_registered.py
  --meshes library_v3`) and as sim_vs_ref.
- **Seeds and pairing.** Seeds 42 and 43, one box, one commit. Per seed the two arms of an episode train in the same
  wave (TRAIN_SLOTS 2).
- **Known asymmetry, stated now.**
  - Both references were made at 0.3 kg: grasp lock, ILC and the evolutionary search ran with the placeholder. So M1
    changes the masses only in RL training and evaluation.
  - This is the situation of an eval retrain that reuses the stored eval references. It is not the physics session's
    situation, where each arm rebuilt its references under its own masses.
  - [H] The effect here may therefore be smaller than Round 3's.
- **Verification before the verdict** (`tools/mass_verify.py`; any failure makes the run INVALID). For each chosen
  checkpoint, it follows the chain the official evaluator uses: the saved config's `task.parquet` → the parquet →
  `object_urdf_paths` → the URDFs. It checks that:
  - those URDFs carry the arm's masses;
  - the reference fingerprint equals the source's;
  - the two arms' saved configs differ only in `output_dir` and `task.parquet` / `reference.parquet`;
  - `reset.seed` is the seed and the step count is 70,004,736;
  - the evaluated rollouts' `checkpoint_sha256` equals the chosen checkpoint's.

## 3. Rule (fixed; `tools/mass_verdict.py` applies it)
- **Definitions.**
  - Cell = episode × arm × seed.
  - Cell mean = the mean registered AUC vs mocap of its 10 rollouts (unrounded).
  - Seed mean = the mean of an arm's two cell means.
  - Δ(ep) = seed mean(M1) − seed mean(M0).
  - Δ(ep, s) = cell mean(M1, s) − cell mean(M0, s): same reference, same seed, same box.
- **ADOPT** realistic masses for eval retrains **iff** Δ(ep2) ≥ +0.03 **and** Δ(ep12) ≥ +0.03 **and** no Δ(ep, s)
  < −0.05 (no single seed drops by more than 0.05).
- **NOT ADOPTED** otherwise. The eval pipeline keeps the 0.3 kg placeholder.
- **INVALID** if `mass_verify.py` fails: no reading.
- **INCOMPLETE** if any of the 8 cells is missing or has fewer than 8 scored rollouts. There is no reading from partial
  results. The missing cells are re-run on a new box on this run's stored arm references (same files, REUSE_REF), and
  then the rule is applied once to the completed set.
- **Reported with the verdict**, not part of the rule:
  - every cell (mean, sd, min, n, the 10 AUCs, the chosen checkpoint step);
  - per seed and per reference;
  - the sim_vs_ref Δ and the SE of Δ;
  - each cell's reference vs mocap (ref_auc), which should be the same in both arms;
  - the static floor and the masses each arm loaded.
  - A harm reading is flagged if Δ(ep) ≤ −0.03 on an episode.
- **What ADOPT buys.**
  - Masses go into the eval retrains: `mass_arm.py` copies for reused eval references, `MA_ARGS` for fresh builds.
  - Each eval policy is swapped only by its own per-episode rule: the multi-draw mean must be ≥ the packed draw.
  - Every retrain batch needs the owner's go-ahead. Nothing goes to Kaggle without the owner.
- **What NOT ADOPTED leaves open** (proposal only): the physics session's condition, references rebuilt under the
  masses, as its own pre-registered test.

## 4. Noise and power (stated before the result)
- Same reference, separate RL runs [M]:
  - ep12, recipe arms A/B/C (different settings, seed 42): 0.912 / 0.892 / 0.909;
  - ep2 S0, physics session, seeds 43 and 44: 0.635 / 0.636.
- Separate references (another box) [M]: differences of 0.24–0.31. That is why every cell of an episode uses one file.
- [E] With 2 seeds × 10 evaluations, a +0.03 bar on one episode can be crossed by noise. The rule needs both episodes and
  no seed drop. This was accepted as agreed.

## 5. Integrity
- Public episodes only. No eval episode, no Kaggle, no pack.
- Mocap is read only by `score_registered.py`, after each rollout.
- The masses were fixed by the physics session before this check, never fitted to mocap or eval results, and are not
  changed after any result.
- Run ids carry `-mass-`. Arm folders are `refs/mass{0,1}*` and `results/mass{0,1}s*_glock_public`, apart from
  everything an eval pack pulls.
