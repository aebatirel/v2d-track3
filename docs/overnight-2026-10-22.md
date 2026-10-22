# Overnight 2026-10-21 → 22: how robust is contact-anchored retargeting? (draft, filled in as results land)

Owner's ask (01:00 TRT): redo the four validation episodes (ep12, ep27 good; ep18, ep24 bad) with the new approach,
test as much as possible, find what works and what does not, fix it, have a reliable setup by morning. Budget: the
$50 top-up (credit $52.69 at 01:00).

All scores: **registered ADD-AUC with our own meshes vs mocap (the kit's scorer, `pipeline/score_registered.py`), mean
± std (min–max) over 6 official evaluations (`reset_mode=explicit`, 1 world) of one policy.** The base policy of each
episode is the one published on 2026-10-21; its 6-evaluation mean replaces the single rollout we reported then. Raw
rows: `results/e2e/overnight_20261022/`; table: `tools/ab_table.py`; details and commands: `docs/work-log.md`.

## 1. Results

| episode | base | k: contact retargeting | other variants |
|---|---|---|---|
| ep12 (easy) | 0.725 ± 0.067 (0.581–0.777) | **0.790 ± 0.023** (+0.066) | ki: pending |
| ep27 (easy) | 0.942 ± 0.017 (0.908–0.956) | 0.911 ± 0.017 (−0.031) | ki: pending; i: pending |
| ep18 (hard) | 0.345 ± 0.046 (0.275–0.400) | 0.319 ± 0.042 (s42), 0.361 ± 0.038 (s43) | kq **0.381 ± 0.012**; p 0.377 ± 0.021; ki, kri, i: pending |
| ep24 (hard) | 0.297 ± 0.055 (0.228–0.369) | 0.307 ± 0.002 (s42), 0.306 ± 0.018 (s43) | kq 0.313 ± 0.011; p 0.282 ± 0.023; ki, kri: pending |

Variants: k = robot hand re-fitted to the objects (fingertips on the human contacts, no penetration as the simulator
sees it); kq = k + object keypoints 15 cm out in the reward (FlashCHORD: 1 m); p = NVIDIA's primitive-collision
Sharpa hand on the base reference; i = deployment-exact starts in training (patch); kri = k + rest settling + i.

## 2. What we learned (measured)

1. **Contact retargeting cleans the reference physically** (simulator contacts: ep24 frames with the hand > 2 mm inside
   something 242 → 62 of 275, ep18 ~77 % → 11 %; frame-0 object jump ≤ 0.8°) **but changes the score little on average**
   (+0.066, +0.01, ≈ 0, −0.031). Its consistent effect: **far fewer bad rollouts** (spread 3–25× smaller on ep12/ep24).
2. **Evaluation noise is large**: one policy's evaluations spread ±0.02–0.07, two seeds differ by ≈ 0.04. The
   published single-rollout scores of 2026-10-21 were low draws (ep24 0.232 vs a 0.297 mean). Any decision needs
   ≥ 2 seeds × 6 evaluations; single-seed differences below ~0.05 are not evidence.
3. **ep24 failure moved**: with k the slide phase tracks (board 1 within 1–2 cm to f68, base 6–25 cm); every rollout
   now fails where a board is lifted and stood on its edge (board 1 ~f102, board 2 ~f117).
4. **Our ep24 reference has resting boards floating 2–4 cm above the table** (mocap diagnostic on the public episode:
   standing board +8.9 cm vs +6.5 cm, flat board +1.5–2.2 cm vs 0). Fix: `contact_retarget --rest_settle 1` (objects
   that are not being moved rest on the table; median height error 2.4 → 1.6 cm and 2.1 → 0.6 cm). GPU test: kri.
5. **ep18 failure**: the sweeper is knocked over by f8–10 while the reference keeps it still until f40, with or without
   retargeting. **Training never sees the evaluation's start**: FlashCHORD's Sharpa reset opens the fingers (× U(0, 0.7))
   and holds the frame with full object assist for 20 steps every time; the official evaluation starts exact, free,
   unassisted. NVIDIA's humanoid recipe has "deployment-exact" starts for this; the Sharpa one does not. Patch
   `FC_IMMEDIATE_FIRST_FRAME` (opt-in, training only). GPU tests: ki, kri, i.
6. Keypoint scale (kq): best and tightest on both hard episodes, one seed, within noise. Primitive hand (p): +0.03 on
   ep18, −0.015 on ep24: inconclusive.
7. Cost: RTX PRO 6000 Max-Q trains at 76 % of the WS speed (41.7k vs 55.1k env steps/s); worth it below ≈ $1.71/h.

## 3. Recommendation (pending the last results)

(to be written when ki / kri / i / H are in)

## 4. Spend and runs

(to be filled: per box run id, GPU, $/h, hours, result; credit at the end)
