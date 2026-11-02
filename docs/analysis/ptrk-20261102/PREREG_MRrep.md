# Pre-registration: replication of the re-centre + re-register tracker (MR), public episodes (2 Nov 2026)

Written after the first batch's results and before any run of this replication. Labels as in PREREG.md.

## Why a replication, and its limits
The first batch's primary candidate MG failed its gate (results/gate_MG_fb_vs_C.json). The report-only ablation MR
(VOS_PRIOR + VOS_RECOVER, no depth masking) gave mean ΔAUC +0.0029 over 19 episodes (5 better / 4 worse, worst
−0.008; MPPE −0.040 cm, RPE −0.19 cm; > 3 cm frames 368 → 322), driven by ep18 (+0.062: the sweeper's partial loss
in C is avoided). MR was chosen AFTER seeing scores, so it cannot be adopted from that batch. No fresh public episodes
exist, so this test can only check that MR's effect REPRODUCES across independent tracker runs (another box, another
run of every stochastic step); it cannot remove the selection. That limit is reported with any result.

## Run (one RTX PRO 6000 box, 96 GB: no out-of-memory crashes)
Code 7fbc321's tracker (perc2 + vos_guide unchanged), library_v3, TRACK_GUARD on, cached depth, 20 public episodes:
- **Cr**: control, fresh run;  **MRr**: TRACK_VOS=1, VOS_PRIOR=1, VOS_RECOVER=1 (same defaults: cov 0.6, rec 0.5,
  every 5), fresh run.
Same box also fills the first batch's crashed cells (report-only): C / C2 / MG / MD / MR on ep23, MG / MD / MR on ep0,
MG / MR on ep26, and the pitcher test C / P on ep21 / 22 (PREREG_pitcher.md).

## Gate for MRr vs Cr (fixed now; same as PREREG.md, all 20 episodes)
mean ΔAUC ≥ +0.005 and ≥ 2 × |mean(C2 − C)| of the first batch (0.00002 → bar stays +0.005); no episode < −0.02; mean
ΔMPPE ≤ 0 and ΔRPE ≤ 0; > 3 cm frames not more. Additionally ep18's gain must reproduce (ΔAUC ep18 > +0.02), else the
effect is called not reproducible. Pass → handed to perfect-following as a "replicated, post-hoc-selected" candidate
with the selection caveat; the owner decides. Fail → closed.

## Cost
One PRO 6000 box ≈ $1.1–1.4/h × ≈ 3 h ≈ $3.5–4.5 [E]. Session spend so far ≈ $9 of $30.
