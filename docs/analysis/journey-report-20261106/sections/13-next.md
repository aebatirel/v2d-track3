## 13. Open questions and what we would do next

Ranked by the strength of the evidence behind each. Each is labelled as a hypothesis [H] or an estimate [E], with the experiment that would test it.

| # | Idea | Evidence | Label | Experiment that would test it |
|---|---|---|---|---|
| 1 | The last 2 SP-SR and 4 MP-SR failures are reference-vs-truth errors on a few objects: the spoon as scene anchor (evals 32, 33, 35-37), the eval 25 boards, and the eval 30 sweeper | all 20 14p rollouts pass both thresholds against our references; tightest margins eval 10 beige 1.85 cm, eval 30 sweeper 1.82 cm | [I]/[H] | a GT-free per-episode audit of just those objects (mask + depth + knob cue), then a targeted reference fix with retrain and two-host confirmation; success = one more SR episode on the board |
| 2 | A complete-base pitcher that is both a good shape and a good tracking template | pitcher bias is the one systematic bias (spread/mean 0.14); upper bound +0.012 public AUC; depth placement gave +0.106 public but only +0.0015 board | [E] | rebuild the base from depth on rest frames, test as template and as payload under the public LOO CV; falsified if tracking drops (the lathe template lost 0.249) |
| 3 | Wire the half-frame advance (S2) and identity_fix into the default eval pipeline | S2 +0.0061 public (17/20 better), never in a packed reference; identity_fix fixed ep23 0.041 -> 0.663 but was only in the eval-25 job | [E] about +0.004 board | rebuild references with S2 and retrain the affected evals; two-host swap rule |
| 4 | Retrains with new meshes work if the grasp is rebuilt for the new shape, not only the collision copy | 6 of 7 failed zero-shot; eval 14 (zero-shot near control) passed | [H] | for eval 20, rebuild the grasp lock on the new pitcher, then retrain; entry rule "zero-shot within 0.02" |
| 5 | Domain randomisation reduces draw variance on contact-sensitive episodes | professor's feedback; sd 0.20-0.26 on evals 1, 14, 30; geometry fixes cut sd to 0.008-0.017 | [H] | falsifier written on 31 Oct: 10-draw sd falls by 40 % or more on 2 of 3 contact-sensitive episodes, or the mean falls by over 0.02 (GPU check about $1.5-2) |
| 6 | 250M steps are not the right budget; failure-weighted reset sampling could halve it | no source measured a plateau; BeyondMimic's 2x saving came from failure-weighted resets; lift-window resets helped 2 evals | [H] | {250M, 125M} x 2 seeds on public eps 12, 22, 27 (18 GPU-h, $9-29); then a failure-weighted reset arm |
| 7 | A stiffer wrist (kp 100-400) removes carry saturation | soft wrist saturates on 23 of 27 moving public tracks; kp 400 was essential for the spoon | [H] | the planned 16-30 run wrist-gain study ($35-100); needs an organiser answer on embodiment |
| 8 | Joint shape and pose estimation (BundleSDF / Any6D style) closes the gap to the leaders | leaders track 2-4x more accurately; rest-frame oracle +0.032, constant-offset oracle +0.030 to +0.050 | [H] | days of work and $100+ with all retrains [E]; first a public-only test on 3 episodes against the +0.032 rest oracle |
| 9 | Forward-backward tracking fixes drift-then-snap errors (eval 14 cup, ep0 lid) | no public drift-then-snap seen; eval 14 had one | [E] about $10 per episode | run on the flagged eval episodes only, after a public no-harm check |
| 10 | Room-map camera for eval 35 only | eval 35 18 mm gap, bound 0.056; ep24 analogue +0.148 | [E] about +0.002 board | needs a fresh pre-registration, since the threshold was formed after seeing public scores |

Open questions that only the organisers can answer:

- Will the PR #215 container reproduction accept the counted files (14p for five boards, 13j for CD-O), given the disclosed choices (njmax 1024 in training, the eval-15 waiver, GT-informed mesh selection, the early mesh provenance)?
- How do "2 final picks" map onto per-board selection, and did our late registration (email drafted 31 Oct) and repository sharing go through? The sources do not record confirmation.
- What is the spoon's frame convention? Our estimates of P(frame B) ranged from 0.09 to 0.87.
- Why did some competitors' CD-O values change (SoySauceChicken 0.065 -> 0.25339; richchentw 0.154 -> 0.2128)? Possibly a rescoring; not recorded.
- Why do fresh draws drop on some hosts (eval 30 0.938 -> 0.768)? The evaluator-gap test did not reproduce it.
