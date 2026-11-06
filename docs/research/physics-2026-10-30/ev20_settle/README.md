# Eval 20: blue-cup settle under bold-albattani's b1 pitcher set vs packed (1 Nov 2026, CPU) [M]

**Asked by** focused-pascal (06:45 UTC), who is holding the eval-20 b1 retrain launch for this check.

**Test** (`scripts/settle_at_low.py`, a scratch copy of carve-20261030's `settle_at.py` that also tracks each object's
lowest visual-mesh point):
- FlashCHORD at the pin, training sim config (sim=rl), 1 world, CPU.
- Hands parked 3 m away with zero gains. Objects are placed at their reference pose at frame F with zero velocity.
- 2 s settle with gravity and no drive, 40 control frames.
- Reference: the packed eval-20 reference (md5 4d06d8d4).
- Assets:
  - packed `refs/sf/ep20/assets`;
  - b1 = the same with `placement_carve.py assets` and bold-albattani's 9c0bc0c pitcher set (41 pieces).
- Table top at z = 0.600 m (support stage cylinder).

| frame | set | cup drift at 2 s | cup peak drift | cup lowest point vs table: ref / end / min | pitcher drift at 2 s |
|---|---|---|---|---|---|
| 152 | packed | 0.10 cm / 0.1° | 0.34 cm / 0.2° | −0.9 / −1.8 / −4.2 mm | 0.39 cm / 1.5° |
| 152 | b1 | 0.03 cm / 0.2° | 0.32 cm / 1.7° | −0.9 / −1.0 / −4.1 mm | 0.28 cm / 0.3° |
| 183 | packed | **4.19 cm / 29.4°** | 4.19 cm / 29.4° | +0.2 / +0.6 / −2.0 mm | 0.62 cm / 2.0° |
| 183 | b1 | 0.17 cm / 0.7° | 0.83 cm / 2.6° | +0.2 / +0.5 / −3.2 mm | 0.37 cm / 3.2° |
| 192 | packed | 1.27 cm / 0.5° | 1.34 cm / 2.5° | −0.5 / −0.3 / −2.3 mm | **6.82 cm / 27.6°** |
| 192 | b1 | 0.33 cm / 0.7° | 0.50 cm / 0.7° | −0.5 / −0.2 / −1.3 mm | **11.97 cm / 50.1°** |

No overflow lines and no NaN in either run. Collision shapes: cup 68, pitcher 41, in both.

**Reading:**
- **The blue cup is fine under b1, by focused-pascal's criteria.**
  - It rests on the table within 0.33 cm / 0.7° of the reference after 2 s at all three frames, and closer than
    packed at every frame. Packed tips the cup 29° at f183.
  - It never sinks through: the lowest point dips to −1.3 to −4.1 mm transiently (soft contact) and ends within
    1 mm of the table top.
  - The budget run's new cup / world-plane contacts are the cup resting on the table.
- **Flag (not the cup):** at f192 the pitcher falls over when released hands-free, in both sets: packed 6.8 cm /
  28°, b1 12.0 cm / 50°. [H] f192 is a hand-held or pouring frame, where a free pitcher is not expected to stand.
  Worth checking against the hand-contact labels.
