# B7 dev runs

- `20261031-b7deva-3f7f661`, `20261031-b7devb-3f7f661`: dev run 1 (marker settings v1, code 3f7f661), STOPPED at
  05:57 UTC after ep2 showed robust fits growing into the host surface (DEVIATIONS 82). Kept as a failed experiment:
  logs, ep2 output (group B), strace logs and an audit analysed WITHOUT a manifest (the processes were killed before
  writing one, so the auditor cannot exempt the dev-role obs_all reads or reconcile the det_f0 opens with the guard's
  count; every flagged path is an obs_all file of the episode or its det_f0.npz, no GT path).
- `20261031-b7mkchk-a1bc5f7`: ep2 marker check on settings v2 (full episode, both objects), audited with its manifest:
  0 forbidden, 0 unlisted, 0 unrecorded, 0 writes outside the run.
- `20261031-b7struct-0eb8016`: structure hypotheses for 8 of the 10 anchors (ep2, 11, 23, 24, 18, 40, 21, 12; ep27
  and ep31 missing), KILLED at about 07:00 UTC when the machine stopped (no manifest). The audit was analysed WITHOUT
  a manifest (`strace_audit_no_manifest.json`): every flagged item is a dev-role `obs_all` read of the episode's
  objects (4 opens each), a `det_f0.npz` open (guard key filter, cannot be reconciled without the manifest's count)
  or a write into this run folder (the run folder is known only from the manifest); no GT path, no network.
  Structure code is unchanged since f286e79; the anchors are rerun under a full audit (B7 notes).
- `20261031-b7struct2-c56d473`: structure for the two anchors missing above (ep27 white_pot, ep31 plastic_dish_rack),
  audited with its manifest: 0 forbidden, 0 unlisted, 0 unrecorded, 0 writes outside the run, no network. Manifest
  commit 7cd51b7 (HEAD at the end), `code_dirty` only because of another agent's notes file (`build/I.md`);
  `b7_summary.json` records c56d473 clean at the start.
