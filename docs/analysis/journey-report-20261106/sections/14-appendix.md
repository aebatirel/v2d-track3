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

### Lane sessions at a glance

Fourteen lane sessions each ran one workstream for the coordinator. Dates are UTC. Costs are GPU only, agent-reported or estimated; the sessions' own model-usage figures are in section 12.1. "Gate" means the pre-registered pass rule.

| Lane | Dates | Goal | Outcome (key number) | GPU cost | Covered in |
|---|---|---|---|---|---|
| 3D mesh generation accuracy research | 26 Oct - 3 Nov | lower CD-O with better submitted meshes | CD-O 0.402 -> 0.239 cm (rank 18th -> 4th on 3 Nov); packs 9a+ to 13j; most picks chosen against public scans and disclosed | about $29.5 (unreconciled) | 8.3, 8.7, 12.1 |
| Perfect following of perceived trajectory | 1 - 3 Nov | make the robot follow our reference fully | pack 12b (AUC 0.84405, +0.0048) and pack 13 (+0.00186); two-hand references failed and 1 of 8 lift-window retrains passed on its merits | about $31 by 12b, about $28 for the 2 Nov box batch | 7.7, 7.10 |
| Embodiment options | 30 Oct - 1 Nov | test hands, masses, solver, recipe screens | nothing adopted into the recipe; eval 10 contact fix (+0.020, with the pack session) | about $30 screens, $23 solver re-test, smaller runs (estimates) | 7.4, 7.5, 7.10 |
| Policy development review | 30 Oct | brief the owner; explain the learner code | briefing and 14-hypothesis explainer; all branches merged to `main`; Vast billing $376.41 for 20-30 Oct | $0 | 7.10, 12.1 |
| Performance vs NVIDIA's method | 30 Oct | compare with NVIDIA's pipeline | no head-to-head exists; NVIDIA defaults cap public AUC at 0.415 (do-nothing 0.446; ours 0.8146 then) | $0 | 3.3, 11 |
| New score status | 31 Oct - 2 Nov | run packs, uploads and per-episode audits | AUC 0.8146 -> 0.8441 over packs 9a+ to 12b; marker layer and third camera failed | about $24 (DR runs, eval 10 retrain, re-track) | 2, 5.8, 7.5 |
| Perception accuracy on public episodes | 2 - 3 Nov | pre-registered tracker and detector tests | every gate failed (closest +0.0010 against +0.005); pitcher placement kept, board +0.00146 | about $25-26 [E] of $40 | 5.8, 9.1 |
| GRASP physics sampler | 1 Nov | does GRASP beat our solver on ep13 | +0.024 against a +0.05 bar: fail | $0 | 6.6, 9.2 |
| Team registration | 30 - 31 Oct | check registration and rules | Kaggle team renamed by the owner on six pages; form and email drafts; repo advice | $0 | 12.4 |
| Physics-informed perception | 1 - 2 Nov | physics priors on tracked poses | +0.00298 against +0.003: fail by 0.00002; `qa_physics.py` | $0 | 5.8, 9.1 |
| Room map | 2 Nov | drift-free camera from a public-only map | bound 0.0029 against 0.01 (G1); public +0.0070 but ep22 -0.0164 (G2): fail | $0 | 5.6, 5.8 |
| Point tracks | 2 Nov | catch and repair lost tracks | -0.058 (repair) and -0.132 (every flag): fail; ep23 was a board swap | $0 | 5.8, 9.1 |
| Pot pose network | 3 Nov | object-specific network beats the tracker | -0.065 (rendered), -0.0085 (mocap fine-tune): fail | about $0.8 [E] | 5.8, 9.1 |
| Hand-aware tracking | 3 Nov | correct held objects along the camera ray | -0.0042 against +0.005; ep24 -0.047: fail | $0 | 5.8, 9.1 |

### Coverage and gaps (honest list)

All gaps named in earlier versions of this report are now covered, with the limits below.

- **Main early session, 20 Oct 13:20 - 24 Oct 11:09 UTC.** Covered from the first message. It was read from turn summaries, not message by message: the owner's own messages were mostly not in the summaries, so owner wording appears only where the agent quoted it (a few typed messages of 24 Oct, 06:53 - 09:47, are verbatim). Between 23 Oct 23:01 and 24 Oct 00:33 only results were read, so typed owner messages in that window, if any, were not captured. Cost and timing figures are the agent's own statements or estimates.
- **Builder session, 26 Oct - 31 Oct 19:34 UTC.** The span 26 Oct 15:34 to 31 Oct 16:27 was read from turn summaries only (the session began at 15:16 on 26 Oct and the first 18 minutes have no result events); 31 Oct 16:28 - 19:34 was read with user and result events. Day labels for events after about 13:00 on 30 Oct are less certain than the times. Owner decisions in this session mostly arrive as quotes relayed by other sessions. The 19:11 - 19:34 stretch of 31 Oct was not checked separately. Costs are self-reported or ledger figures, because the per-result cost field is not monotone across restarts.
- **Coordinator session, 30 Oct - 3 Nov.** Covered through the owner's messages plus the coordinator's own explanations, decisions and worker reports, not turn by turn. Some of its figures conflict with later or more specific records: the 09:11 approval time of pack 11 (section 7.4), the coordinator's clock running about an hour ahead on 31 Oct, and the final timing of pack 13j (Kaggle record used).
- **The 14 lane sessions** have now all been read back to their starts from per-turn summaries (see the table above). Intermediate steps, dead ends and costs from these reads are in sections 4, 5.8, 6.6, 7.10, 8.7, 10.4 and 12. The only remaining limit is the same as for the early main session and the builder session: they were read from per-turn summaries, not every message verbatim, so owner wording appears only where an agent quoted it and cost figures are the agents' own. Board scores still come from the Kaggle record; the mesh lane's GPU spend list was not reconciled with the credit balances.
- **How conflicts were resolved.** The digests were written by a cheaper model from summaries and sometimes disagree. Where they did, this report used the Kaggle table for board scores and otherwise the more specific, later-dated measurement, and named the conflict (for example realistic masses "adopted" vs "not adopted", section 7; the spoon loss estimate, section 3; the GPU total, section 12; the early-checkpoint study of 29 runs against the larger one, sections 4 and 7.6; the static-freeze test, section 5.7). Where the new chat material gave a different figure for something the report had already cited from the Kaggle table or a later measurement, the report's figure was kept.
- Some figures exist only as estimates in the sources (most GPU totals, several per-lane costs, the spoon's share of the loss, the agent's own score projections). They are marked [E] and were not recomputed.
- No new measurement was made for this report.
