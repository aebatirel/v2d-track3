# Final policy checkpoints (public episodes)

Final FlashCHORD policies (250M environment steps, seed 42) of the runs that were evaluated, kept in git because
each is ~5 MB (CLAUDE.md: final checkpoints up to ~10 MB). Intermediate checkpoints live only in the HF store.
The final checkpoints of the 2026-10-21 hard batch except ep21 default (ep18 both variants, ep21 wrist-cost, ep24
both) were lost: the HF store was full when those boxes uploaded, and the boxes are gone; their rollouts and scores
are in `results/e2e/`. From now on `pipeline/auto_ep.sh` copies the chosen checkpoint next to its rollout.

| run | variant | episode | size | AUC sim vs mocap (old scorer) | sha256 |
|---|---|---|---|---|---|
| 20261020-day1b-cfbff6b | oracle | ep12 | 5.1 MB | 0.8584 | `356cf8c0ca620717…` |
| 20261020-day1b-cfbff6b | perc2 | ep12 | 5.1 MB | 0.8898 | `db095d55ae30f733…` |
| 20261020-day1b-cfbff6b | perc2vc | ep2 | 5.1 MB | 0.9258 | `49bfbe78a8c2544c…` |
| 20261020-day1b-cfbff6b | perc2vc | ep27 | 5.1 MB | 0.9649 | `9832fcc74bfebb54…` |
| 20261020-refsweep-ea14fdf | perc2vc | ep12 | 5.1 MB | 0.6041 | `7c66041372ed92c0…` |
| 20261020-refsweep-ea14fdf | perc2vw | ep12 | 5.1 MB | 0.8595 | `0e027e4948f6142f…` |
| 20261021-hard-ep21-6f2f98a | perc2 | ep21 | 5.1 MB | 0.8261 | `0a6b5fd51223c37c…` |
| 20261021-auto18-966eb96 | perc2mc (own meshes, sweep → 150M) | ep18 | 5.1 MB | 0.3809 (registered, our meshes 0.3962) | `add62ba6230aa7fd…` |
| 20261021-auto24-966eb96 | perc2mc (own meshes, sweep → 150M) | ep24 | 5.1 MB | 0.0958 (registered, our meshes 0.0799) | `a8e1fc72e2551ac9…` |
| 20261021-auto24-966eb96 | perc2mcs (own meshes + hand separation, 250M) | ep24 | 5.1 MB | 0.2307 (registered, our meshes 0.2316) | `ec45fe16e9e51364…` |
