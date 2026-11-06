# ep24 board slot, round 3 (PREREG F-I4.17, T-I11 tag `fi4q`)

Public episode 24, dev run `runs-dev/20261031-i2probe-626ce13`, code a130449 (platebody identical to dc4a2a4), launched
31 Oct 23:01:02 UTC on the shared 4-core container (`launch.txt`), done 23:14:53 (828 s). GT-free: our clean bundle
`b4ext4-b61e8aa`, our picks (`shell_t5p36`), tracks, hands and video.

## Result [M]

| | board 1 (`wooden_piece_1`) | board 2 (`wooden_piece_2`) |
|---|---|---|
| decision | CARVE (T1, owner waiver) | CARVE (T1, owner waiver) |
| body | low-piece, 3 rectangles, IoU 0.958 | low-piece, 3 rectangles, IoU 0.952 |
| boxes slotted / default | 5 / 3 | 5 / 3 |
| t (all points) | 7.401 mm | 7.401 mm (partner prior) |
| slot w / D | 9.40 / 67.55 mm | 9.40 / 54.56 mm |
| keep-out | 0.0 cm3 | 0.0 cm3 |

- Cross-lap: D sum 122.11 mm vs W_x 120.52 mm (diff 1.59 mm, window 10 mm).
- P2-P7 on 16 copies: all pass (P3 carved lag 0.074 cm / 0.68 deg; overlap 0.039 cm3).
- **Contact-budget gate part 1 (F-I4.17.1): FAIL.** Plain MuJoCo 3.17.0, sim=rl options and limits (njmax 512, nconmax
  256, from `docs/research/work/15-verify/cfg_sim_rl.yaml`, sha256 695536b7...). Settle scene at S1 = f246 and S2 = f218,
  16 jittered copies, 2 s each:

  | pieces | max nefc | max ncon | overflow copies |
  |---|---|---|---|
  | delivered (5 + 5 slotted boxes) | 124 | 31 | 0 / 32 |
  | default (3 + 3 boxes) | 112 | 28 | 0 / 32 |
  | control (1 + 1 rectangle-frame box) | 32 | 8 | 0 / 32 |

  Ratio delivered / control = 3.875, above the 2.0 limit. There is no overflow. At the max-nefc step almost all
  contacts are board-table (27-28), with 0-3 board-board.
- Part 2 (determined-wright's `budget.py`, at most 380 rows per world in the full eval scene) was **not run**. This
  container has no FlashCHORD source and no warp, newton or mujoco_warp.

## Delivery status

`fi4q/r0/` carries **`DO_NOT_USE.json`** (both boards, reason `contact_budget`), with `p1_pending: false` and
`contact_budget_pending: true`. F-I4.17.6 step 8 sends the r0 to determined-wright for P1 and part 2 only when P2-P7
and part 1 both pass. Part 1 failed, so the r0 is a record and is **not** handed off. Freeze condition (a) fails, the
round stops, and eval 25 is not run under F-I4.17. Any further use of these pieces (for example, asking
determined-wright for part 2 or for P1 at their reference and at the lowered 1 mm pose anyway) needs a new dated
decision.

If such a decision is made, the request to determined-wright would be: (i) P1 at their reference; (ii) P1 at the
lowered (1 mm) diagnostic pose; (iii) the sim=rl contact check (overflow lines and max nefc per copy, as in their
Evidence (b)); (iv) part 2 with budget.py on the glockt ep24 reference. The path to send is
`docs/research/mesh-2026-10-26/gmg/build/I/results/slot3-ep24/fi4q/r0`.

## Files

`fi4q/`: decisions, report, `physics_*.json`, `contact_gate_*.json` (per copy, per scene, lowered, P3 replay counts),
`summary_fi417.json` (compact), `driver.log`, `r0/` (pieces, `_default/`, manifest with the `owner_waiver` F-I4.17
block).
