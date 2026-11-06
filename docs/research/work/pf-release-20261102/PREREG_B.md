# Eval 16 on the PACKED reference: hold the spoon to the end, pre-registered 2 Nov 2026 ~02:15 UTC, before any GPU result

## Evidence [M] (GT-free)
- pfF seed 42 (training box): the rebuilt reference with the current grasp-lock code scores 0.687 (packed construction)
  and 0.769 (hold to end), far below the packed policy (0.850). The D arm of 31 Oct trained the current recipe on a byte
  copy of the PACKED reference and got 0.82–0.84 (+ start-state randomisation). So the rebuild, not the training, loses.
- In the packed reference the robot hand leaves the spoon at ~f130 (fingertips 1–3 cm until f126, 6 cm at f132, 48 cm by
  f156) while the spoon stays still (≤ 1 cm per 4 frames); H5p7 spoon onsets f112–120 in 10 / 10 draws.
- CPU zero-action (one replay each): packed reference 0.839; with the right hand frozen from f107 (tools/hold_freeze.py)
  **0.929** (floor 0.597); fingertips stay within 1.3 cm of the spoon to the end.

## Box pfG (ops/jobs/pf_arms.sh, eval 16, current recipe, stock limits, REUSE_REF on copies of the packed reference)
- `p0` = byte copy of the packed reference P (control: the current recipe on P, no randomisation);
- `pz` = P with the right hand's wrist / fingers / frames held at f106 from f107 to the end (FREEZE_EP16=right:107).
Seeds 42 / 43. Per arm: seed choice, training-box gate (> 0.8498), 10 fresh official draws, the pack-9b swap rule on P
(object poses unchanged) and the +0.02 inclusion bar. If both pass, the larger confirmation mean is taken. If pfF (rebuilt
`se`) also passes, the larger confirmation mean of the two is taken. Cost [E] ≈ $4.5.
