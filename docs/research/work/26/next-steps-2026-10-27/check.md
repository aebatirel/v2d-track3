**Corrections** (M = origin/main-bsky37; WL = M:docs/work-log.md; RC = M:docs/analysis/robustness-review-20261026/refcheck)

1. **"Interruptible: the reports give no price."** Wrong. The work log records $0.67–0.91/h interruptible against $1.21–1.69/h on demand (WL:4209, 4268-4269, 4290, 4426). The 19 min is training alone (WL:2336). A full grasp-lock job takes about 1.2–1.4 h (WL:3970, 4426), and the restart after a pause is "not pause-safe" (M:docs/analysis/robustness-review-20261026.md:405). So arm A is not safe on interruptible boxes either.
2. **Arm B "names no public twin."** Wrong. Public ep11 (blue and beige cup) is the twin of eval 10, and grasp-lock rollouts for it are stored (M:STATUS.md:210; RC/chain/commands.log:13; M:docs/research/work/simvalid-2026-10-22/simvalid_inventory.json:16). Validate arm B on ep11 against mocap first.
3. **Arm B "more clearance" is presented as new.** A 15 mm beige-cup shrink was already tried on CPU: ≤0.517 with a weaker grip. The 0.632 replay already exists and falls to 0.42–0.54 under ±3–6 mm jitter (M:docs/analysis/ev10-stack-20261026/README.md). The screen "replay ≥0.63" is that same knife-edge; it should require a jittered-replay mean.
4. **"Seven tries 0.438–0.465 (WL:4303-4450)."** Five of them fall in that range, B′ is incomplete, and e10Z's curve went down to 0.436 (WL:4441). The two carve runs are at WL:4212-4213.
5. **"kp 400 hurt the standard learner (WL:551-555)."** Those lines only show no gain on ep12 (0.860 vs 0.890). The harm is at WL:1058-1074: ep18 0.193 vs 0.381 and ep24 0.050 vs 0.096, one seed each, on 21 Oct references.
6. **"Pitcher snap cost −0.112 on the twin."** That figure is for the pitcher object alone and includes its frame-0 orientation (RC/chain/README.md:100). The verified review lists "the ep21 snap is wrong" under "Killed in verification" and puts the loss on the frame-0 tilt (R2) (RC/README.md). The snap's measured cost on ep21 as a whole is −0.056 (RC/systematics/README.md:24). For eval 20 the lever is the anchor-tilt fix, not the gated snap. R1 lists evals 28, 1 and 14 as exposed.
7. **"Pour-hand gap costs 0.003 [M]."** It is [D], pooled over all untracked-hand frames on public episodes, not pours only (RC/timing/README.md:68-69).
8. **"Blue cup is slot 0 in 6 evals."** It is 5: evals 10, 14, 20, 32 and 33. Eval 8's slot 0 is the beige cup (simvalid_inventory.json:16).
9. **"Eval 25: 0.71 → 0.792" from the carve.** That is one seed; the same carve at s43 scored 0.474 (WL:4187-4189). Eval 10's 0.342 → 0.452 is a raised floor (the cups now stand; zero action 0.448), not a learned stack (WL:4214).
10. **AUC registration ceiling "+0.01–0.02."** The scores reader extrapolates the twin costs (R4) to about 0.034–0.038 [E]. Report 0.01–0.04 [E] and say that the readers disagree.
11. **G1 "$75–100."** That was priced with a 20 Oct snapshot of $2.2–3.3/h (C:docs/research/notes/23-carry-control-force.md:505-531). At today's $1.2–1.7/h it is about $45–60 [D]. The verdict "do not fund" stands.
12. **Arm C baseline "ep12 0.910."** It comes from 23 Oct, one seed, with the curve "still rising" (WL:2373-2375). That is before the 24 Oct recipe (EVOLVE, onset anchor; WL:2862-2866), so arm C needs a control run on the same code. Eval 32's 0.803 is the best of five seeds, which ranged 0.397–0.803 (WL:4311), so it is a winner's-curse baseline. A +0.03 threshold on one seed cannot be told apart from that noise. Arm C also tests only 32 and 33, not 14 and 16. CURR_SCALE comes from M:ops/jobs/glock_public.sh:32,62-64, not from note 23.
13. **"Retraining about 5 episodes $10–15."** Evals 28 and 1, both exposed to R1, use the standard learner at about $3–5 each (WL:3968-3989). With 2 seeds that is about $15–30 [E]. Placement carves first need the manifest-driven pack (review:487,490).
14. **"CD-O does not rank Track 3."** How the boards combine is unpublished (M:docs/research/track3-requirements.md:26,148). "Ranked by AUC" is the owner's goal (M:STATUS.md:623), not a published rule. The CD-O rank estimates use the stale 25 Oct snapshot.

**Integrity**
- **Arm D (ball-wrist kd).** This is an embodiment change in the same class as kp 400. The unsent email's question 5 covers only the translation servo (M:docs/organiser-email-draft-2026-10-22.md:40-45), and note 23 flags rules exposure (C:...:494). The plan gates a kp-100 slice on the organisers but not arm D, which is inconsistent.
- **Arm B clearance and the placement carves.** Both depend on email question 1 (a collision copy that differs from the submitted mesh), which was never sent.
- **Pack 6.** It was itself an owner-approved exception to "never tune on eval results" (WL:4388). Disclose this when choosing the final picks.
- **Arm A.** It must not pack the best of its 10 new rollouts; that is best-of-N cherry-picking and an open owner decision (WL:1068-1071).
- **Omission.** The sponsor's held-out evaluation (track3-requirements.md:25) and review item 5 (H6, $5–8) are absent from the plan and the budget.

**Confirmed**
- Leaderboard: AUC 0.81391, 5th; gaps to DDD, 3rd and 1st are 0.013, 0.051 and 0.118.
- Loss split: policy loss 0.0836; draws +0.033 above their means [D]; a re-run would score about 0.789 [E]; 1st needs 63 % of the remaining loss.
- Costs and budget: H5 about $1.5–2 (review:386-388, 485); credit $3.52, so a $20 top-up covers arms A–D plus the margin; professor's $1,000–1,500 (M:docs/context-and-decisions.md:14).
- Eval 10: 9,650 N at the rim and an 80–120 cm flight.
- Training settings: CURR_SCALE never used; the 70M runs end in the 0.1 stage; ball-wrist kd is 6.
- Reference biases: snap −0.016 on average; half-frame advance +0.003.
- Transfer and meshes: 0.74 transfer, which is one measurement 2.3–2.7σ below the public pairs (RC/README §3); pitcher swap −0.0045; sweeper flips on 3/24 and 4/24 hosts; the stability gate as specified (RC §4.1).
- Housekeeping: the organiser email is unsent; the note-23 filename clashes with M; the pipeline_ep.sh hook conflicts (+3 lines on C vs +98/−10 on M since the fork point).

**Verdict:** the order holds only at the ends. H5 first is right, and mesh last is right for AUC. The middle should change:
- **Eval 10 (#2)** has the weakest evidence: about 8 failures, including the clearance test on CPU. It should run only after a robust CPU screen and the ep11 twin, and spoon H2 (#3) and the $0 CPU tests in #4 should move ahead of it.
- **Arm D** should come out of T1 until the organisers clear it.
- **Arm C** should run as a pilot with a control on the same code, not as an adoption test.

Scratch copy of the work log: /tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/nextsteps/chk/wl.md