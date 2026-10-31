# Masses transfer check: build notes (31 Oct 2026, CPU only, nothing launched)

**Question.** The physics session found that realistic object masses beat the 0.3 kg placeholder by +0.090 on 4 public
episodes, but with the organiser scans as simulator meshes. Does that gain carry over to our pipeline: library_v3
meshes, our perceived references, and the frozen grasp-lock recipe?

**Job.** `ops/jobs/mass_check.sh`, run as `bash ops/jobs/mass_check.sh` with run id `20261031-mass-<sha7>`.
- One RTX PRO 6000 box.
- ep2 and ep12 × arms M0 (0.3 kg) and M1 (`props_masses_only.json`) × seeds 42 and 43: 8 trainings in 4 waves of 2.
- NREP 10 official evaluations per chosen checkpoint, each scored vs mocap (registered ADD-AUC) and as sim_vs_ref.
- One store push at the end.
- The rule is fixed in `PREREG.md`, written before any result. The launch string and cost are in `JOBS.txt`.

## How the two arms share one reference and differ only in mass
- **The trap is real** [M, local copies of the stored files]. The grasp-lock references name their own asset copy, for
  example `/content/refs/sf/ep12/assets/urdf/blue_cup_rigid.urdf` (0.3 kg). Only `object_mesh_paths` names
  `/content/assets`. So `MA_ARGS` (which only rebuilds `/content/assets`) never reaches what FlashCHORD loads. This job
  does not use `MA_ARGS`.
- **`tools/mass_arm.py`** makes per-arm copies:
  - It copies the reference's asset folder per arm: `refs/mass0_sf/ep<N>/assets`, `refs/mass1_sf/ep<N>/assets`.
  - In M1's copy it rewrites each `<mass>` to the props value and scales the inertia by m / 0.3. The COM is unchanged.
    This is exactly what `make_assets.py --physics` does for a mass-only entry: test T5 shows equal mass and COM, and
    inertia within 8e-9 relative, for all 11 library_v3 objects.
  - It writes the reference parquet once per arm and seed (`refs/mass{0,1}s{42,43}_glockt/ep<N>/<hive>/
    ref_gl_ilc.parquet`, the only `.parquet` in that folder). Only `object_urdf_paths` changes in the copy.
  - It adds the base-reference link and the `rest_check.json` that `glock_public.sh` REUSE_REF needs.
  - It refuses a source whose URDFs are not 0.3 kg (T6), a props entry that is not mass-only, and a copy that differs
    from the source in any other column.
- **How the arms train.** They use the PERC field `glock_public.sh` already has (oracle twins), so each arm × seed gets
  its own folders. The PAIRS entry is `2:local:mck:mass1s42` → `refs/mass1s42_glockt`, `runs/mass1s42_glock`,
  `results/mass1s42_glock_public`.
- **What FlashCHORD and the official evaluator load.** Checked in the local FlashCHORD source (video_to_data 7eb9721):
  - `evaluation/harness.py:360-404` `evaluate_checkpoint` rebuilds the scene from the checkpoint's saved
    `task.parquet`.
  - `data/parquet.py:24-38` needs exactly one `.parquet` in a folder.
  - `data/motion_v1.py` reads `object_urdf_paths`.
  - `assets/registry.py:43-51` `resolve_asset_path` returns the stored path unchanged when it is a file.
  - `scene/objects.py:387-392` `add_urdf(..., ignore_inertial_definitions=False)`.
  - Measured earlier [M]: after `add_urdf` with FlashCHORD's flags the pot body mass is 0.3, the URDF value. The
    collision hulls add none (`docs/research/work/19/c/logs/e2e_pot_S120.log`, line 8).
- **On the box, `tools/mass_verify.py`** follows that chain for every chosen checkpoint, reading the safetensors header
  metadata `user.resolved_config_json` (no safetensors package needed). It checks that:
  - the loaded URDF masses are the arm's, from the arm's own folder;
  - the reference fingerprint (md5 over every column except the asset paths) equals the source's;
  - the two arms' saved configs differ only in `output_dir`, `task.parquet` / `reference.parquet`, or another string
    that differs only by the arm name;
  - `reset.seed` is the seed and `total_environment_steps` is 70,004,736;
  - the evaluated rollouts' `checkpoint_sha256` is the chosen checkpoint's.
  - Any failure makes the run INVALID (PREREG section 3).

## Deviations from the brief (for the orchestrator)
1. **ep2's reference is built on the box, not taken from the store.** The store's ep2 grasp-lock reference (E3,
   23 Oct, which `20261024-ev3-2c1e4dd` re-pushed) is not the frozen recipe. It used approach 6 cm and REPLAN 1, with no
   onset anchor and no evolutionary search; its fingerprint is `1ce86a8f…` and its earlier result vs mocap was
   0.306 ± 0.115.
   - So the job pulls only ev3's base `refs/perc2mck/ep2`. That is ev3's copy of E3's base, the file the physics
     session used; the expected fingerprint `30c9ad1b…` is checked on the box.
   - It builds the frozen-recipe grasp-lock reference once, at 0.3 kg, with `glock_public.sh REF_ONLY=1`. All 4 ep2
     cells train on that one file.
   - ep12 reuses the stored ev2 reference, as recipe arm A did (fingerprint `f7d8bb94…`).
   - To use E3's old reference instead, set `SRC_EP2=20261024-ev3-2c1e4dd:mck:reuse`. This is not recommended: wrong
     recipe.
2. **Cost is higher than the brief's "~3-4 h".** It is about 5.4–7.5 h, about $6.5–11, central about $8.7 [E] (basis
   in JOBS.txt).
   - The measured wave of 2 concurrent 70M trainings is about 72 min. The GPU is saturated by one training, which alone
     takes 36–44 min, so the second slot adds pairing but no throughput.
   - 4 waves plus the ep2 reference build plus setup make up the total.
3. **Three opt-in hooks were added to `glock_public.sh`**, all off by default:
   - `REF_ONLY=1`: stop after the reference stages;
   - `NO_PUSH=1`: so the job pushes once;
   - `EVAL_TIMEOUT=<s>`: cut a stalled evaluation, also in `tools/ckpt_curve.sh`.
   - mass_check sets EVAL_TIMEOUT to 1200 s, after the physics box p3ms1 was lost to a 30-min evaluation stall.
   - Old vs new scripts with the hooks off give identical job logs, audits, files and uploads (`cpu/out/equiv.txt`).
4. **"Pushes once"** means the job pushes once. The platform's 30-min watchdog pushes and its final self-destroy push are
   unchanged.
5. **"Official evaluator"** means FlashCHORD `scripts/evaluate_policy.py` on the training box, as in every
   `glock_public.sh` run. It is not the clean-tree pack evaluator. On 30 Oct the two agreed for eval 1 (0.931 vs 0.924).
6. **Asymmetry, stated in the PREREG.** Both references were built at 0.3 kg: grasp lock, ILC and the evolutionary
   search ran with the placeholder. So M1 tests masses in RL training and evaluation only. That matches an eval retrain
   that reuses stored references. It does not match the physics session's setting, where references were rebuilt per
   arm. A gain here may therefore be smaller.

## CPU evidence (`cpu/`; the mock scores are synthetic, not evidence about masses)
- **Mock of the exact job string** (`cpu/mock`: `setup.sh` + `run_mock.sh`).
  - Real parts: `make_assets.py`, `support_fill.py`, `glock_public.sh`, `ckpt_curve.sh`, `store.sh` and the new tools.
    The fake store is built from local copies of the real store files, with the asset paths remapped.
  - Stubbed parts: grasp lock, ILC, evolve, rollouts, the FlashCHORD trainer and evaluator, qa and scoring. The stubs
    load references as FlashCHORD does and write checkpoints with the resolved config in their metadata.
  - Result: rc 0 in about 5 minutes. `check.py` passed all **38 checks** (`cpu/out/mock_check.json`):
    - 8 trainings (2 episodes × 2 arms × 2 seeds), all 70,004,736 steps, with `reset.seed` equal to the seed.
    - Per episode, all 4 trainings read one reference. For ep12 it is the stored ev2 file (`f7d8bb94…`, the PREREG
      value). For ep2 it is the one built here, not E3's, which was never pulled.
    - Each arm parquet differs from the source only in `object_urdf_paths`.
    - M1 trainings load blue cup 0.128 / rack 0.3865 / pot 0.2771 / lid 0.0882 kg; M0 trainings load 0.3 kg; each
      loads from its own arm folder.
    - All 248 evaluations (7 × 3 curve + 10 per training) loaded their checkpoint's arm URDFs through the checkpoint's
      saved `task.parquet`.
    - The two arms of an episode and seed have identical training arguments and environment. Seeds differ only in
      `reset.seed`.
    - The shared reference and its asset folder are byte-unchanged. `/content/assets` stays at 0.3 kg.
    - Exactly 1 upload. The pulls are exactly the 5 listed in JOBS.txt.
    - `mass_verify` reports VERIFIED, and the summary has 8 cells with n 10 each.
- **`tests.py`: 9 tests** (`cpu/out/tests.json`).
  - `mass_verify` FAILS on a wrong mass (M1 cup reset to 0.3), on a second `.parquet` in an arm folder, on a changed
    reference sample, and on a changed reward weight in one arm's saved config. It is VERIFIED again after each restore.
  - The verdict rule returns ADOPT / NOT ADOPTED (gain +0.02 on one episode) / NOT ADOPTED (seed −0.06 while the mean
    passes) / ADOPT at the boundaries (+0.03, −0.05) / INCOMPLETE (7 rollouts) / INVALID.
  - The `mass_arm` rewrite equals `make_assets.py --physics` (T5), and `mass_arm` refuses a non-placeholder source (T6).
- **`cpu/out/eval_timeout_test.txt`:** with `EVAL_TIMEOUT=3` a hanging evaluation is cut at 3 s, left unscored, and
  MUJOCO_GL / XLA settings still reach it. Without the setting nothing changes.
- **Mock limits.**
  - The stubs copy references, so the mock's ep2 "built" reference has the base's fingerprint. On the box it differs,
    and the job records it in `stored_refs.txt`.
  - The real saved config has about 470 fields. The pair check allows only path-like differences, so an unexpected real
    difference makes the run INVALID rather than passing silently.

## Files
- New: `ops/jobs/mass_check.sh`, `tools/mass_arm.py`, `tools/mass_verify.py`, `tools/mass_verdict.py`, this folder
  (`PREREG.md`, `JOBS.txt`, `BUILD.md`, `cpu/mock/{setup.sh, run_mock.sh, stub.py, check.py, tests.py, equiv.sh}`,
  `cpu/out/*`).
- Changed, opt-in only: `ops/jobs/glock_public.sh` (REF_ONLY, NO_PUSH, EVAL_TIMEOUT), `tools/ckpt_curve.sh`
  (EVAL_TIMEOUT).
- Not done here: no commit, no launch, no Kaggle, no STATUS / work-log entry (the orchestrator's).

## If the verdict is ADOPT (later, owner's go-ahead per batch)
- **Eval grasp-lock references reused with REUSE_REF.** Make the M1 copies with `mass_arm.py` (arm `mass1` only).
  Spoon episodes need the wooden_spoon prior (0.05 kg) that is already in the props. Fresh builds can use `MA_ARGS`
  instead.
- **Pack blocker.**
  - `pack_eval.sh`'s `MA_ARGS` only rebuilds `/content/assets`. A grasp-lock policy trained on an arm copy names
    `/content/refs/mass1_sf/ep<N>/assets` and `refs/mass1s<seed>_glockt`, so the pack must pull those folders as well
    (`RUN@refs` covers them).
  - Before any pack, check this with `tools/mass_verify.py`'s chain: checkpoint → task.parquet → URDF masses.
