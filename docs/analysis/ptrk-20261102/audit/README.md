# Eval gross-failure audit of the pack-14p references (3 Nov 2026; PREREG_round3_audit.md part 2)

- **Method:** GT-free. For every eval episode, the PACKED reference's object poses (perfect-following's refs_14p.json;
  14 / 32 from the 12b bridged table) were rendered with our library_v3 templates and compared per frame with:
  - SAM2 video masks (box 20261103-ptrkH-ad13d06, ≈ $1.5);
  - the eval stereo depth;
  - the hand joints.
- **Code:** `scripts/eval_audit.py` (flags), `scripts/audit_overlay.py` (images in `overlays/`: outline = reference,
  tint = mask, same colour per object).

## Ranked by the pre-registered severity (frames flagged), with each flag checked on the overlays
| Eval | Severity | Flags | Overlay verdict |
|---|---|---|---|
| 8 | 219 | beige cup LOST f0–218 (IoU 0) | **Audit false positive.** The reference sits on the cup in every frame; the SAM2 mask failed (no beige-cup mask). Depth residual 0.86 cm agrees with the reference. |
| 25 | 178 | piece 2 LOST f0–115, 146–202, 325–329 | **Audit false positive.** Both board references sit on the boards; the mask of the white board is missing. |
| 32 | 35 | cup LOST f18–25; spoon LOST f92–111, 205–211 | **Real, moderate:** cup reference offset ≈ 1 cup radius (≈ 4 cm) at f18–25. Spoon reference follows the mask at f100 / f150 / f208. |
| 33 | 24 | cup LOST f84–90; spoon LOST f184–190, 261–265, 268–272 | **Real, moderate:** cup offset ≈ 4–5 cm around f87 (the known f91 guard re-acquisition region); spoon reference lags or offsets by ≈ 5–8 cm along the handle at f186 and f263. |
| 10 | 22 | blue cup SWAP f92–113 | **Audit false positive:** the cups are nested, and both references follow the right cups. |
| 36 | 20 | spoon LOST f77–85, 112–122 | Mostly mask gaps (no spoon mask at f80); a small offset at f115. |
| 19 | 13 | sweeper LOST f222–234 (last frames) | Not inspected (end of episode, 13 frames). |
| 14 | 5 | cup LOST f36–40 | The known guard-bridge span (pack 12b). |

**Clean (no flags):** 1, 3, 5, 6, 15, 16, 20, 28, 30, 35, 37, 38. Median mask IoU 0.70–0.89, depth residual
0.6–0.9 cm.

## Reading [I]
- No eval reference shows a gross failure: no object lost for a long span, no identity swap, no flip, nothing below the
  table or on the wrist.
- The real flags are short, moderate offsets (≈ 4–8 cm for 5–20 frames) on evals 32 and 33, cup and spoon. Those are
  the episodes where SP-SR / MP-SR (> 10 cm or > 29° mean error) could be touched by perception, and only through
  short spans.
- Episodes that fail SP-SR / MP-SR on the board are therefore more likely robot-rollout failures (dropped or displaced
  objects) than reference failures.
- **Audit limitation:** SAM2 masks failed on the beige cup (eval 8) and the white board (eval 25). The audit's "LOST"
  flag needs the overlay check before it is believed.
