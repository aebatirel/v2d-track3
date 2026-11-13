# Pack 9a+ upload (31 Oct 2026, 18:13–18:18 UTC)

- Owner, verbatim, in the "New score status" session: "Upload which you think of the highest score potential".
  Uploaded by that session (focused-pascal was told first and did not upload).
- File: `track3_submission.parquet` from `claude/focused-pascal-2nz9s1` at this path (build_9aplus), sha256
  `e02736ea3c7e33ffcee5ada4a6a1dbc8ad4e72cd2889abdaa9968b8d3af6a7d8`, 9,120 rows. Code commit URL d7ecaef (on origin).
  Recorded script hashes: eval 160d24f5…, eval code b1b3ebe3…, packer 49b13052…, uploader d31d4a7c…. The packer and
  uploader hashes match the PR #215 kit's `tools/pack_submission.py` and `submit/v2d_submit.py`.
- Contents: pack 8 rollouts unchanged. Packed meshes swapped: C0 pot, lid, rack (flagged: scan-derived 7 mm marker
  balls, 2.5 mm walls); C1 beige cup T1 (evals 8 and 10); C1 dust pan T2 (evals 19, 38). See the README of this
  candidate on focused-pascal's branch for provenance.
- Tool: kit `submit/v2d_submit.py` via `tools/kaggle_upload.py` (kaggle 2.2.5); dry run first (valid, 5 uploads left
  per board). The CD-O file the uploader derived matches the staged one in content (pandas equals; bytes differ only
  in encoding).
- Scores (Kaggle, all six boards, 18:18 UTC), vs the previous best:
  - AUC 0.81757 (0.81460)
  - SP-SR 0.85 (0.85)
  - MP-SR 0.65 (0.65)
  - RPE 3.87853 cm (3.93179)
  - MPPE 2.89663 cm (2.92126)
  - CD-O 0.33234 cm (0.40188)
