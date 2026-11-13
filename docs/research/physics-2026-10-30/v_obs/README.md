# Arm V check: the actor sees object velocity (31 Oct 2026, CPU)

**Request.** keen-heisenberg relayed it (21:01 UTC): the owner wants a slip-aware policy. Item 1 is to turn on object
body velocity in the actor's observation. The critic already sees it (`env.critic_context.object_body_velocity: true`
in `train_flash_sac.yaml`); the actor does not (`observation/policy.yaml`: `object_body_velocity.enabled: false`).

**Override:** `observation.object_body_velocity.enabled=true` (Hydra; `env.observation` interpolates `${observation}`).

## CPU check [M]
- Setup:
  - FlashCHORD at the evaluator pin, video_to_data 8c778f9 (`pipeline/setup.sh`).
  - Scratchpad `fcvenv`; `embodiment=sharpa_hands_mid`.
  - Reference: our ep12 S1 grasp-lock reference, 2 objects.
  - Script: `v_obs_test.py`, run from the FlashCHORD dir.
- The evaluator path read at the pin:
  - `harness.evaluate_checkpoint` takes the checkpoint's saved resolved config, applies
    `apply_evaluation_composition` and instantiates `cfg.env`.
  - `apply_evaluation_composition` touches only the world count, auto-reset, VOC, reset and termination. It never
    touches the observation.

| check | C (stock) | V (override) |
|---|---|---|
| resolved config stores `env.observation.object_body_velocity.enabled` | False | True |
| still set after the evaluator's composition → `RLEnvConfig` | False | True |
| actor observation dim | 722 | 734 (+12 = 2 objects × [linear, angular] world velocity) |
| V's observation with the 12-value block removed equals C's | — | yes, at the explicit frame-0 reset and after 30 zero-action steps |
| velocity block | — | 0 at frame 0; max abs 0.27 after 30 steps (live) |

- Not checked: a full train → save → official-evaluate round trip. The policy's input size follows
  `env.observation_dim`, which the evaluator rebuilds from the same config.
- The organisers' re-run container must use the same harness behaviour, i.e. rebuilding the env from the
  checkpoint's resolved config. That is true at the pin [M] and assumed for their container [H].
