# Eval 16: hold the spoon to the end (perfect-following lane), pre-registered 2 Nov 2026 ~00:40 UTC, before any GPU result

## Evidence [M] (GT-free)
- H5p7 (10 draws of the packed eval-16 policy): the spoon's error takes off at f112–120 in 10 / 10 draws, 4–13 frames after
  the right hand's last release (f107), and grows to 7–8 cm by f130; the rack stays within 1–2 cm.
- Our reference keeps the spoon still after the release (≤ 1 cm per 4 frames, f107–173), so the simulated spoon falls
  or slides where our reference says it rests; nothing in the reference asks it to move.
- CPU zero-action (one replay each): packed construction 0.539; with the hold extended to the end 0.581 (floor 0.597).

## Change
pipeline/grasp_lock.py `--hold_to_end wooden_spoon`: the carrier's last hold on the spoon runs to the end of the
reference (the robot hand never releases it). Robot-hand tracks are not scored; object tracks are. GT-free.

## Box pfF (ops/jobs/pf_arms.sh, eval mode, no bridge): eval 16, arms
- `s`  = the packed construction rebuilt on this box with the current recipe (control for "fresh retrain");
- `se` = `s` + `--hold_to_end wooden_spoon`;
seeds 42 / 43; recipe = pf-hands PREREG §2. Per arm: seed choice, training-box gate (> 0.8498), 10 fresh official draws,
pack-9b swap rule on P (object poses unchanged, so P is every arm's own reference) + inclusion bar ≥ +0.02 vs the packed
H5p7 mean. If both arms pass, the larger confirmation mean is taken. Reported: se − s on the training box.
No public twin with a spoon-in-rack release was identified tonight; the eval swap rule decides.
Cost [E]: 2 pairs per seed wave ≈ 3 h + confirmations ≈ $4.5–5.
