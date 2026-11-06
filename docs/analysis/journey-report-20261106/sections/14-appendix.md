## 14. Appendix: every submission, and coverage of this report

### Every submission

All 26 Kaggle uploads, from the Kaggle API (authoritative for board scores):

{{TABLE_SUBS}}

Packs built but not uploaded: pack 8 (pack 7 + a fresh eval-1 draw, about +0.0002 [E]), 9a (superseded by 9a+), pack 14 on 13f (superseded by 14p), 14p1 (held for CV leakage, about +0.0003 [E]). Planned but empty: 13g (no mesh passed rule A or B), the first 13j attempt (rack outer shell -0.017 vs the -0.020 bar), 10b (eval 20 gate missed by 0.0004) and pack 15 (no retrain passed). Naming note: the board-2 revert pack is "13f1" on Kaggle and in the work logs and "13f2" in one chat; they are the same file. One chat says 13j was final at 12:21 UTC on 3 Nov, while Kaggle lists the upload at 10:30 UTC with commit 3a933d1d; the Kaggle record is used here.

### Sources used

- The exact Kaggle submission history and the 6 Nov leaderboard reading (top 20 per board).
- Digests of the merged work logs of all 20 git branches (5 slices, 1 Oct - 3 Nov).
- Digests of 86 analysis reports and plans (two parts), including the loss budgets, forensics, H5, overnight reports, mesh sprint rounds C0-C4, E0, G2, G3 and R, grasp audits and plans.
- A digest of 26 deep-research notes (notes 01-26, 4-30 Oct).
- Chat digests: the main early session (24-27 Oct), the builder session (from 31 Oct), the Rust-rewrite evaluation (22 Oct), the contact-slot and pack-3 session (25-27 Oct), the robustness review (26-27 Oct), 14 lane sessions, and the coordinator session's owner and cross-session messages (30 Oct - 3 Nov), including the two advisor meetings with Roman Klis and Prof. Arda Inceoglu's feedback.

### Coverage gaps (honest list)

- The main early chat session for **20-24 Oct** was not read from the chat itself. The work logs and the decisions record cover that period, so owner messages from those days appear only where the logs quote them.
- For the **14 lane sessions**, only their newest results were read. Earlier experiments in each lane are covered only where the work logs and reports record them.
- The **builder session** was read only from 31 Oct 21:07 UTC on.
- The **coordinator's own chat** is covered through the owner's messages and the work log, not turn by turn.
- The digests were written by a cheaper model and sometimes disagree. Where they did, this report used the Kaggle table for board scores and otherwise the more specific, later-dated measurement, and named the conflict (for example realistic masses "adopted" vs "not adopted", section 7; the spoon loss estimate, section 3; the GPU total, section 12).
- Some figures exist only as estimates in the sources (most GPU totals, several per-lane costs, the spoon's share of the loss). They are marked [E] and were not recomputed.
- No new measurement was made for this report.
