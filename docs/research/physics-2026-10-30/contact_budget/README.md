# Contact budget under the training sim config (sim=rl), CPU [M]

`budget.py` (one scene: `budget_run.sh REF EMB OUT_PREFIX FRAMES`, which runs sampled + explicit resets): collision geoms per group, plus per-world contacts and constraint rows (nefc) over W sampled training
resets × STEPS zero-action steps. With `FRAMES=a,b,…` it uses explicit, evaluator-style resets at those frames
instead. FlashCHORD runs at the evaluator pin with the box patch set.

**Limits** (`configs/sim/rl.yaml`):
- nconmax 256 per world, held as one pool (naconmax = 256 × worlds);
- njmax 512 constraint rows per world, a hard per-world limit. MuJoCo-Warp drops rows beyond it and prints
  "nefc overflow".

| scene | resets | contacts / world max (median) | nefc / world max (median) | steps over 512 |
|---|---|---|---|---|
| eval 25 packed (`--pieces meshes/carve/ev25`) | sampled, 8 × 60 | 65 (46) | 276 (201) | 0 |
| eval 25, library_v3 without pieces | sampled, 8 × 60 | 56 (40) | 240 (175) | 0 |
| **eval 10 packed** (`--pieces meshes/carve/ev10`, 53 / 49 pieces) | sampled, 8 × 30 | 130 (115) | **536 (473)** | **13 %** |
| eval 10 packed | explicit frames 0 / 124 / 142 / 160, 8 × 30 each | 107 (54) | 441 (227) | 0 |
| eval 30 packed (library_v3, no pieces) | sampled, 8 × 30 | 57 (44) | 244 (189) | 0 |
| eval 30 packed | explicit frames 0 / 66 / 132 / 197 / 262 | 52 (26) | 223 (116) | 0 |
| eval 14 packed (`refs/sf/ep14/assets`) | sampled, 8 × 30 | 71 (42) | 297 (183) | 0 |
| eval 14 packed | explicit frames 0 / 40 / 79 / 118 / 157 | 92 (38) | 385 (167) | 0 |

**Eval 10 notes:**
- The cup–cup contacts dominate: up to 68 per world with sampled resets and 79 at the nested frames. Under sampled
  resets the 20-step VOC-1 hold presses the overlapping carved pieces (11.9 cm³ median at rest, bold-albattani)
  together.
- The packed eval-10 training run 20261026-gl10A2-5e0e100 (`runs/glock/ep10-s42/train.log`) has **8,368,544** "nefc
  overflow" lines.
- Its 5 stored scored draws have **0**. The policy never nests the cups in scoring.
- [H]: the overflow corrupts eval 10's training (cup–cup contact rows are dropped in the nested phase), which may add
  to its do-nothing floor. Not tested.

**bold-albattani's pair-only plain-MuJoCo check** (656–1,296 rows at f124–160) reads higher than FlashCHORD's full
scene (≤ 441 at explicit resets). The engines differ in contact settings. Use the FlashCHORD numbers for the gate.

**Is `sim.njmax` a training-only override?** Yes. CPU check at the pin (`njmax_cfg_test.py`, eval-10 packed reference):
- `train_flash_sac … sim.njmax=1024 sim.nconmax=512` stores them in the resolved config (`env.sim.njmax 1024, nconmax 512`).
- `harness.apply_evaluation_composition` leaves them in place.
- The evaluator's `RLEnvConfig.sim` carries them, and the built SolverMuJoCo has njmax 1024 and naconmax 512 for
  1 world. The stock run gives 512 / 256.
- No evaluator code change is needed: the official evaluator rebuilds from the checkpoint config. GPU memory for the
  constraint arrays grows with njmax; not measured.

## Candidates (bold-albattani's collision-overlap fixes; owner permission relayed 02:50 UTC)

| candidate | resets | contacts / world max (median) | nefc / world max (median) | overflow lines | verdict vs "no overflow at 512" |
|---|---|---|---|---|---|
| ev10cs (`ev10-cavsafe/ev10cs`, dafc911; 53 / 49 pieces) | sampled, 8 × 30 | 124 (107) | 510 (443) | **4** | **not clean** |
| ev10cs | explicit f0 / 124 / 142 / 160 | 99 (30) | 409 (133) | 0 | — |
| (packed ev10, for comparison) | sampled, 8 × 30 | 130 (115) | 536 (473) | 13 | overflow |

- The sampled resets are the same frames for both: the reset seed is fixed and the reference identical, so the
  comparison is paired.
- ev10cs cuts the cup–cup contacts under sampled resets from 68 to 31 per world. At the nested explicit frames they
  stay about the same (77 vs 79).

