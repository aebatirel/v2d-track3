# Case study article (6 Nov 2026)

"An AI Agent Team in a Robot-Learning Challenge: A Case Study". It is a live Claude Docs document (private until
shared): https://claude.ai/artifact/XyF2LbdbMZT5tgE9Qufz1b

What it contains:
- 11 sections plus the abstract and references, about 8.5 k words;
- 56 references, each checked against its primary page (`data/bib_verified.md`);
- 11 figures:
  - live charts: AUC per upload, the AUC bridge by lever, activity per day, AI cost by workstream;
  - diagrams: the team and the pipeline;
  - key-moment images in `img/`.

Data and method:
- `data/process_metrics.md`: counts from git and the logs (2,359 commits, 65 pre-registration files, 362 work-log
  entries, about 117 owner messages to the coordinator, 26 uploads).
- `data/tokens_turns_*.jsonl`: per-turn list-price usage records from all 20 Claude Code sessions, read from each
  session's `result` events by small extraction agents.
- `data/aggregate_tokens.py` turns them into `tokens_by_session.json` and `tokens_by_group.json`:
  - total = first recorded running total + every later increase, because restarts can resume the counter from an
    earlier saved value;
  - turns after 3 Nov 12:11 UTC in the coordinator session count as report writing.
- Result [M, list-price equivalent]: about $7,108 in total, of which $6,962 was competition work and $146 was
  report writing (to 6 Nov 16:20 UTC). For 8 lanes only later turns were read, so those totals are lower bounds.
- Actual AI cost (owner, 6 Nov): a $200 Claude Code subscription plus $250 of cloud credit gifted by Anthropic. In cash,
  AI cost less than the GPU rental (about $556 [E]). The binding limit was the weekly usage cap.
