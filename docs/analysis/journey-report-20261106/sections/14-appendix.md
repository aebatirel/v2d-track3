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
- Chat digests, in three groups. (1) The **main early session** from its first message (20 Oct 13:20 UTC) to 24 Oct 11:09 UTC, and the **builder session** from its start (26 Oct) to 31 Oct 19:34 UTC, both read from turn summaries and, where present, owner messages. (2) The **coordinator session** (30 Oct - 3 Nov) through the owner's messages plus its own explanations, decisions and worker reports. (3) Earlier digests: the main early session (24-27 Oct), the builder session (from 31 Oct), the Rust-rewrite evaluation (22 Oct), the contact-slot and pack-3 session (25-27 Oct), the robustness review (26-27 Oct), 14 lane sessions, and the two advisor meetings with Roman Klis and Prof. Arda Inceoglu's feedback.

### Coverage and gaps (honest list)

All three gaps named in the first version of this report are now covered, with the limits below.

- **Main early session, 20 Oct 13:20 - 24 Oct 11:09 UTC.** Covered from the first message. It was read from turn summaries, not message by message: the owner's own messages were mostly not in the summaries, so owner wording appears only where the agent quoted it (a few typed messages of 24 Oct, 06:53 - 09:47, are verbatim). Between 23 Oct 23:01 and 24 Oct 00:33 only results were read, so typed owner messages in that window, if any, were not captured. Cost and timing figures are the agent's own statements or estimates.
- **Builder session, 26 Oct - 31 Oct 19:34 UTC.** The span 26 Oct 15:34 to 31 Oct 16:27 was read from turn summaries only (the session began at 15:16 on 26 Oct and the first 18 minutes have no result events); 31 Oct 16:28 - 19:34 was read with user and result events. Day labels for events after about 13:00 on 30 Oct are less certain than the times. Owner decisions in this session mostly arrive as quotes relayed by other sessions. The 19:11 - 19:34 stretch of 31 Oct was not checked separately. Costs are self-reported or ledger figures, because the per-result cost field is not monotone across restarts.
- **Coordinator session, 30 Oct - 3 Nov.** Covered through the owner's messages plus the coordinator's own explanations, decisions and worker reports, not turn by turn. Some of its figures conflict with later or more specific records: the 09:11 approval time of pack 11 (section 7.4), the coordinator's clock running about an hour ahead on 31 Oct, and the final timing of pack 13j (Kaggle record used).
- **The 14 lane sessions** are still covered only through their newest results plus their branches' work logs. This is an accepted gap: earlier experiments in each lane are covered only where the work logs and reports record them.
- **How conflicts were resolved.** The digests were written by a cheaper model from summaries and sometimes disagree. Where they did, this report used the Kaggle table for board scores and otherwise the more specific, later-dated measurement, and named the conflict (for example realistic masses "adopted" vs "not adopted", section 7; the spoon loss estimate, section 3; the GPU total, section 12; the early-checkpoint study of 29 runs against the larger one, sections 4 and 7.6; the static-freeze test, section 5.7). Where the new chat material gave a different figure for something the report had already cited from the Kaggle table or a later measurement, the report's figure was kept.
- Some figures exist only as estimates in the sources (most GPU totals, several per-lane costs, the spoon's share of the loss, the agent's own score projections). They are marked [E] and were not recomputed.
- No new measurement was made for this report.
