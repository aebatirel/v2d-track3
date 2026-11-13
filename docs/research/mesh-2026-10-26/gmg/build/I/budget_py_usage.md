# determined-wright budget.py: how to run it on our pieces (relayed 31 Oct 22:26 UTC; their branch claude/determined-wright-3joens)

`budget.py` has **no `--pieces` flag** (the orchestrator's 22:40 decision text says "via its --pieces option"; that is wrong;
use the steps below). Script: `docs/research/physics-2026-10-30/contact_budget/budget.py` (9c1d100).

Usage (run from the flash_chord dir):

    USE_COPY=<patched flash_chord copy> FC_VOC_INERTIA=1 FC_FDR_OBJ=1 FC_FDR_TIPS=1 W=8 STEPS=60 \
      <flash_chord venv python> budget.py REF.parquet OUT.json

- `EMB=sharpa_hands_mid` for grasp-lock episodes; leave it unset for the standard learner (evals 25 / 30).
- It reads the reference's `object_urdf_paths`, so our pieces enter through the assets:
  1. `pipeline/make_assets.py meshes/library_v3 OUT --pieces <our r0 pieces dir>`
  2. copy the reference tree, keeping `processed/sequence_id=.../robot_name=sharpa_wave/` and `reconstructed_stage/`, and
     rewrite `object_urdf_paths` to `OUT/urdf/<obj>_rigid.urdf` (their `docs/research/physics-2026-10-30/d_reset_check/scripts/prep.py`
     shows the remap);
  3. run budget.py on that copy.
- `USE_COPY` must point at a FlashCHORD tree with the box patch set (VOC + FDR); stock also works if the FC_* variables are
  dropped.
- The number for the <= 380 bound is the JSON's `max_nefc_per_world`.
- If it cannot run in this container, record why and send the r0 path to determined-wright (they offered to run it).
