# Pre-registration: full-resolution stereo depth for tracking (2 Nov 2026, tracking-perception session)

Written before any run of this test. [H]: perc2 computes FoundationStereo depth at half resolution (FS_SCALE 0.5) and
upsamples it. Thin or small structures (rack wires, board edges, cup rims) get smoothed and fattened, which biases the
depth FoundationPose fits along the camera ray. Evidence: physperc D4 [D]: the constant offsets after the kit alignment
lie mostly along the frame-0 camera ray (+0.020 of the +0.030 oracle), concentrated in ep24 (boards), ep31 (rack),
ep11 (cups). Half-resolution disparity also has half the depth precision (≈ 2× the depth step at 0.5 m).

- Variant **FS1**: FS_SCALE=1.0 (FoundationStereo on the full 1600 × 1000 rectified pair), everything else the eval
  defaults (library_v3 templates, TRACK_GUARD, REG 5 / TRACK 2), 20 public episodes. If FS_SCALE 1.0 runs out of GPU
  memory on an episode, that episode is re-run at 0.75 and reported as such.
- Control: variant C of the main batch (same code 7fbc321 + this job change, same GPU model, other boxes); the C vs C2
  run-to-run noise is stated next to the result. Plus a same-box C on ep21 / 22 (pitcher test) as a cross-box check.
- Scoring and **gate**: exactly as PREREG.md (mean ΔAUC ≥ +0.005 and ≥ 2 × |C2 − C|; no episode < −0.02; mean MPPE and
  RPE not worse; > 3 cm frames not more). Falsifier: mean ΔAUC ≤ 0, or the along-ray component of the constant offset
  (physperc d4_offset.py) not smaller.
- Eval cost if it passes: full-resolution depth for the 20 eval episodes (≈ $2–4 GPU) plus retrains; the decision is
  the owner's / perfect-following's.
- Cost of this test: one RTX 5090 box, ≈ 3 h, ≈ $2–2.5 [E].
