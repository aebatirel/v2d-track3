# Owner's idea 4: "if the initial estimation score is too low, simply increase the training steps"

2026-10-25, CPU only, no ground truth. Labels: [M] measured from stored sim_vs_ref (our policy vs our own reference),
[I] inference, [H] hypothesis with the test that would falsify it.

## Answer

- **More steps rarely rescue a low start [M].** 29 distinct checkpoint curves from the 21–22 Oct sweeps (standard
  recipe, sim_vs_ref at 100/150/200/250M):
  - 22 start below 0.5 at 100M: median gain to 250M **+0.04**, only **1 of 22** ends ≥ 0.45, and **13 of 22 end below
    the zero-action floor** (doing nothing scores higher than the trained policy).
  - 7 start at ≥ 0.5: median gain **+0.09**, all 7 end ≥ 0.45. The easy episodes are the ones that benefit from steps.
  - A rise from 150M to 200M does not predict another rise (2 of 8 rose again; the flat ones rose by +0.016 median).
- **Same picture on the other recipes [M, work log]:**
  - Spoon (ep3/ep35, 23 Oct): the pick-up is learned by 90–120M, then 160M more steps never move the drop point.
  - Eval fine-tunes (24 Oct): on 19, 14, 28, 10 and 25 the best checkpoint came early and later ones got worse.
  - Eval 25 (boards): all 7 checkpoints sit at 0.14–0.27.
- **Why [I]:** a low early score here usually means a structural blocker that steps cannot remove:
  - the object can't be acquired (boards: no thumb opposition);
  - the mesh makes the motion physically impossible (blue cup interior solid; slots filled);
  - the object falls at frame 0 (pitcher, beige cup);
  - the reference itself is wrong (cup tracks dragged under the table).
  RL then converges to "do little", which is why many curves end under the zero-action floor.
- **Where more steps can help [M]:** short grasp-lock fine-tunes (70M) whose curve is still clearly rising at the end:
  - ep31: 0.36 / 0.51 / 0.56 / 0.71 at 10/30/50/70M;
  - ep12: 0.53 / 0.57 / 0.66 / 0.93.

## Recommended rule (GT-free, fixed before use)

Extend a run only if all three hold:
1. Each checkpoint score is the mean of ≥ 3 official evaluations. Single evaluations are too noisy: ep21's 30M
   checkpoint scored 0.83 once and averaged 0.27 over 5 repeats.
2. The last two checkpoint means each rose by > 0.03.
3. The rollouts acquire the object: lift ≥ 50% of the reference height.

Then extend by 50% of the original steps, once. Otherwise do not add steps. Spend the money on the structural fix,
a second learner or a second seed instead. Measured seed spread is 0.04–0.10 on hard twins, about the same as the
median gain from extra steps on easy ones.

**[H] test:** on the public twins whose grasp-lock curve is still rising at 70M (ep31, ep12), extend to 105M.
- Falsified if the 5-evaluation mean of the extension is not ≥ 0.02 above the 70M mean on both.
- Cost: ≈ 2 × 35M steps ≈ 0.5 GPU-h ≈ $1. It needs the Vast top-up.

Data and script: `training-steps-scripts/curve_gain.py` (output in `curve_gain.out`), input
`docs/research/work/checkpoint-sweeps-2026-10-22.json`.
