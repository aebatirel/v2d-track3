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

## Large-sample standard (1 Nov ~04:46 UTC): 32 worlds × 60 steps, hold window reported separately

**Why.** At 8 × 30, ev10cs3 read clean: max 443, 0 lines. At 32 × 60 it overflows. The per-step worst world grows with
the number of worlds, and steps 21–60 include the zero-action collapse after the hold. Controls show that 32 × 60 is
a fair absolute test: the non-overlapping packed scenes (evals 30 and 14) have **0 overflow lines** there.

Hold window = steps < 20, the VOC-1 settling hold of every training reset. Share = the share of steps in which the
worst of the 32 worlds exceeds 512 rows. Runs are in `runs_32x60/` and `runs_8x30/`.

| scene | sampled hold: max / median / share | sampled after hold: max | explicit frames: max | overflow lines (sampled / explicit) | verdict |
|---|---|---|---|---|---|
| eval 30 packed (control) | 270 / 204 / 0 % | 287 | 221 | **0 / 0** | clean |
| eval 14 packed (control) | 407 / 307 / 0 % | 357 | 505 | **0 / 0** | clean |
| eval 14 + rack c1-ev14 (62 pieces) | 571 / 313 / 10 % | 477 | 291 | 12 / 0 | **not clean** (worse than packed) |
| eval 14 + rack c2-ev14 (54 pieces) | 499 / 337 / 0 % | 356 | 216 | 5 / 0 | **not clean** (worse than packed) |
| eval 10 packed (`meshes/carve/ev10`) | 661 / 599 / 100 % | 654 | 1,680 | 380 / 9,723 | overflow |
| eval 10 + ev10cs (v1) | 598 / 548 / 75 % | 566 | 699 | 104 / 7,086 | overflow |
| eval 10 + ev10cs3 (v3, 32 / 33 pieces) | 534 / 495 / 15 % | 603 | 533 | 110 / 576 | **not clean** (best eval-10 set) |

- Explicit frames: eval 10 f0/111/116/124/142/160; eval 14 f0/140/144/149/153/157; eval 30 f0/66/132/197/262.
- The eval-14 rack candidates were built from the packed eval-14 assets: the refs/sf rack mesh plus the candidate
  pieces, the blue cup as packed, 0.3 kg.
- **Verdicts (rule "no overflow at 512" at 32 × 60):**
  - eval 14: keep the packed rack; c1 and c2 add overflow.
  - eval 30: keep the packed configuration; it is clean.
  - eval 10: no candidate is clean. ev10cs3 cuts the overflow lines 3–17× vs packed but is not a retrain candidate
    by the rule.

