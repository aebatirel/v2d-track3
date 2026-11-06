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

Coverage gaps (also stated in section 14):
- The main early chat session for 20–24 Oct was not read from the chat itself. The work logs and
  `docs/context-and-decisions.md` cover that period.
- For the 14 lane sessions, only their newest results were read.
- The builder session was read from 31 Oct on.
