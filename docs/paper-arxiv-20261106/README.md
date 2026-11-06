# arXiv version of the case study (6 Nov 2026)

"An AI Agent Team in a Robot-Learning Challenge: A Case Study": 29 pages, 11 figures, 12 tables, 56 references.

- `main.pdf`: compiled paper.
- `arxiv_submission.zip`: what arXiv needs (`main.tex` + `figures/`). It rebuilds cleanly with pdflatex, run twice.
- `main.tex`: generated from the Claude Docs case study (https://claude.ai/artifact/XyF2LbdbMZT5tgE9Qufz1b) by
  `convert.py`. Edit `main.tex` directly for paper-only changes.
- `figures/`:
  - charts 6, 7, 10 and 11 are vector PDFs drawn from the exact data in
    `docs/analysis/case-study-20261106/data/`;
  - figures 1 and 2 are renders of the doc's diagrams;
  - figures 3, 4, 5, 8 and 9 are images from our runs.

Before submitting:
- check the author block (name, affiliation, email) and the "Statement on AI assistance";
- choose an arXiv category (for example cs.RO, with cs.AI cross-listed);
- arXiv expects authors to take responsibility for the content, so read it through once.
