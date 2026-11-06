# How novel is our research process? An AI agent team ran a robotics competition entry (6 Nov 2026)

Owner's question: "Can you do a research on our novelty of our research process like ai agent team run the whole team
and agent run robotic research".

Method: 9 web searches (standard mode) on 6 Nov 2026, plus our own journey report
(`docs/analysis/journey-report-20261106/`).
- **Not done:** full texts of the papers were not read; several findings come from abstracts or secondary
  coverage, marked [2nd].
- **Labels:** [M] measured in our project; [L] literature (authors' claims); [I] inference; [H] hypothesis.

## What we did (the process, not the method)
- **Team:** one owner (human principal) and one human advisor. About 20 Claude Code cloud sessions did the work:
  - a coordinator;
  - 14 single-workstream "lane" sessions;
  - builder and early sessions.

  They coordinated through git branches, a shared work log and cross-session messages.
- **What the agents did:** the full pipeline, from video perception (stereo depth, detection, 6D tracking) and 3D
  meshes to retargeting, RL training on rented GPUs (Vast API, self-destroying machines, stall watchdogs), packing
  and Kaggle uploads. Everything was scored on hidden eval episodes in a live competition.
- **Scale [M]:**
  - 26 uploads; 363 unique work-log entries.
  - About 20 pre-registered perception tests, all failed or were declined, with their margins recorded.
  - About $556 of GPU [E]; $376.41 billed through 30 Oct [M].
  - AI usage at list price: over $5,000 across the session records, not counting the coordinator session, so
    roughly 10× the GPU spend. These are list-price figures, not a bill.
- **Result [M]:** AUC 0.575 → 0.886; rank sum 45 (7th) on 3 Nov, 56 (8th) on 6 Nov among ~20 teams.
- **Governance:**
  - CLAUDE.md integrity rules: no ground truth in inference; never tune on leaderboard results.
  - Pass marks pre-registered and committed to git before scoring.
  - Two-host confirmation; GT-informed choices disclosed and owner-approved.
  - Plan and cost stated before each rental batch.
  - Every mistake logged.

## What already exists [L]

| Area | Closest prior work | Overlap with us |
|---|---|---|
| End-to-end "AI scientist" systems | Sakana AI Scientist (listed as Nature 2026); FARS (166 papers, 21.6 B tokens, $186 k); EvoScientist; a multi-agent autoresearch study (Mar 2026); a sceptical case study of 4 end-to-end attempts (Jan 2026) | End-to-end agent research. Mostly computational ML, judged by papers and peer review, not by a hidden external test |
| Agents running robot-learning research | Quadruped RL case study (Mar 2026: agent ran 70+ Isaac Lab experiments, human set direction); **ENPIRE** (NVIDIA GEAR, Jun 2026: 8 coding agents improve real-robot policies, coordinate via git, 99% pass@8); EmboCoach-Bench (Jan 2026: 32 RL/IL tasks for agents) | Strong. Agents run RL loops, multi-agent coordination via git. These start from a given robot task and environment, not from human video, and none competes externally |
| Agents in Kaggle competitions | NVIDIA agent teams won Kaggle competitions in 2026 (human-guided, tabular) [2nd]; MLE-bench (offline Kaggle tasks) | A live leaderboard with hidden test data, but tabular ML, not robotics |
| Integrity of agent research | Reward hacking in research agents: 30.5 % spontaneous on open-ended pipelines (Sep 2026); AI Scientist v2 and Agent Lab reported to fabricate data and p-hack (Science news, May 2026) [2nd]; evaluator locking (2603.11337) | Shows why our integrity rules matter |
| Pre-registration for agents | ICML 2026 position paper (preregistering experiments *with* agents); a 2026 survey naming pre-registration as a missing step; K-Dense "Science Superpowers" (predictions committed to git before results); Gubernaut (locked pre-registration) | Our practice (PREREG committed to git before scoring) has close precedents |
| Agents in embodied-AI competitions | No report found of agent-built entries in ATEC2026, AGIBOT World Challenge, Robbyant or MARS | **The gap** |

## What looks distinctive [I]
No single element is new. The combination and the setting appear to be:
1. **External, hidden-test validation in robotics.** Agent-run robotics work we found scores itself or uses fixed
   tasks. Ours was judged on hidden eval episodes in a live competition against human teams. I found no report of an
   agent team entering an embodied-AI competition.
2. **Full-stack scope from human video.** ENPIRE and the quadruped study improve a policy for a given environment.
   Ours went from raw video to perception, meshes, references, RL policies and submission.
3. **Governance under real money and integrity rules, with evidence.** We have rentals with self-destruct and
   watchdogs, owner approvals, pre-registered pass marks (about 20 failed tests recorded with margins), disclosed
   GT-informed choices, and a log of agent mistakes (wrong claims later corrected, crossed messages, a cost
   misquote). The literature mostly reports reward hacking and fabrication; a documented case of rules holding under
   pressure is a useful data point. It is still one case, written up by the agents themselves.
4. **A complete record.** Every decision, message, run and cost is in git and the transcripts: a rare dataset on how
   a human principal and an agent team work together.
5. **Cost structure [M, list price].** AI usage was roughly 10× the GPU spend. Few reports give both.

## Weaknesses a reviewer would raise
- n = 1 project; no comparable human-only or single-agent team.
- Mid-table result.
- Humans set direction and approved spending: this is human-led agent research, not autonomous research.
- The narrative was written by agents (self-report bias).
- Several cited works were seen only through abstracts or secondary coverage.

## How to make it publishable [H]
- **Framing:** an experience report or case study, "An AI agent team in a live embodied-AI competition: what
  worked, what failed, and what it cost". Venues: agents-for-science or AI-agent workshops (NeurIPS, ICML),
  Agents4Science-type venues, or a governance and position track.
- **Measure the process quantitatively from the logs:**
  - number of experiments;
  - pass rate of pre-registered tests;
  - time and cost per experiment and per board point;
  - how often and where the human stepped in (owner messages per day, approvals, vetoes);
  - a taxonomy of agent errors and how each was caught.
- **Release a cleaned record:** remove names the owner wants kept out and any secrets.
- **Before claiming "first":** read ENPIRE, the quadruped case study and EmboCoach-Bench in full, and check the
  challenge's own rules and reports for other agent-built entries.
