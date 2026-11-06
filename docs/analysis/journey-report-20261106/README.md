# Journey report (6 Nov 2026)

The whole V2D Track 3 journey, 20 Oct – 6 Nov 2026, as one long page: `track3-journey-report.html`. It is also
published as a private claude.ai artifact: https://claude.ai/artifact/6pNjoK3xEqi8ry4ceA6jLS

How it was built: cheap extraction, then one synthesis pass, after the first attempt hit the Claude usage limit.
1. Scripts, no model:
   - merged the work logs of all 20 branches (363 unique entries);
   - built compact corpora of the research notes and of 86 reports, plans and READMEs;
   - pulled the Kaggle submission history (26 uploads, 6 boards) and the 6 Nov leaderboards (`build/`).
2. Small extraction agents wrote the digests in `digests/`:
   - 5 work-log slices, the research notes, 2 report slices and the chat sessions;
   - plus 5 cached results from the first attempt (`cached_*`).
3. One synthesis pass wrote the 14 `sections/`.
4. `build/render.py` renders the page. The charts and the submission and leaderboard tables come straight from the
   Kaggle data, not from model text.

Coverage (version 2, 6 Nov ~09:30 UTC):
- Three gaps from version 1 were filled by 5 more small extraction agents and one partial update pass that added
  about 9,400 words:
  - the main early chat session from its start (20 Oct 13:20 UTC);
  - the builder session from its start (26 Oct);
  - the coordinator's own explanations, 30 Oct – 3 Nov (`digests/chats_early*.md`, `chats_builder_*.md`,
    `coordinator_full.md`).
- The early main session and the builder session's 26–31 Oct part were read from turn summaries, not message by
  message.
- Accepted remaining gap: the 14 lane sessions are covered by their newest results and their branches' work logs.
- Version 1 of the sections is kept in git history (commit abd572e4).
