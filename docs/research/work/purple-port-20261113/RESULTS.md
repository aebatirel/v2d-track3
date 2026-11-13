# Purple port (cups) results, 13 Nov 2026: FALSIFIED by the 9 Nov rule

Purple's model-to-cloud registration (their `spoon_register.py`, ported in `purple_track.py`) on our public cup episodes.
Scored with the registered scorer against mocap (scoring only); controls = our FoundationPose tracks C.

| Variant | Mean cup-object ΔAUC (eps 11, 12, 21, 22) | Worst episode ΔAUC | Verdict |
|---|---|---|---|
| PU (Purple's algorithm as published) | **−0.198** | −0.236 (ep11) | FALSIFIED |
| PUT (exploratory: + our tracker pose as a start) | −0.061 | −0.071 (ep11) | FALSIFIED |

| ep | C | PU | PUT | cup ΔAUC (PU) | ΔRPE cm (PU) |
|---|---|---|---|---|---|
| 11 | 0.8999 | 0.6635 | 0.8285 | blue −0.21, beige −0.27 | +5.47 |
| 12 | 0.9584 | 0.8460 | 0.9035 | blue −0.20 | +2.85 |
| 21 | 0.8375 | 0.7440 | 0.8083 | blue −0.20 | +10.34 |
| 22 | 0.8704 | 0.8161 | 0.8623 | blue −0.12 | +1.47 |
| 13 (reported, not in rule) | 0.9628 | 0.8507 | 0.9484 | blue −0.18 | +4.30 |

## Why [D]
- **Up-down flips.** Per-frame registration with PCA starts cannot tell a cup's top from its bottom from a one-sided
  cloud. On ep11 the fitted axis is > 90° from our tracker's in 23/104 (blue) and 39/137 (beige) frames.
- **No temporal model.** RPE rises 1.5–10 cm: poses jump between frames.
- **Their cup method is not public.** Purple's cup method (parametric frustum, "a world-frame cup track next to the
  hands") is not in the repository. What is public is the spoon registration, and it does not transfer to cups as
  published.
- **Possible input effects, not separated:** our SAM2 masks at 400 × 250 and a joint-hull hand mask, in place of
  their SAM 3 masks with a hand class and two-camera mask agreement.

## What this does and does not show
- Shows: their published registration, run on our inputs, is worse than our FoundationPose tracks on public cups.
- Does not show: anything about Purple's full system, whose tracker driver, masks and camera tracks are unpublished.
- Their board history (competitors note §6.4) puts about half of their 0.047 lead over us in clearing failed eval
  episodes (collision geometry, retrains, two row-level scorer fixes) rather than in perception.
