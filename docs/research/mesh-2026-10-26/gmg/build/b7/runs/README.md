# B7 dev runs

- `20261031-b7deva-3f7f661`, `20261031-b7devb-3f7f661`: dev run 1 (marker settings v1, code 3f7f661), STOPPED at
  05:57 UTC after ep2 showed robust fits growing into the host surface (DEVIATIONS 82). Kept as a failed experiment:
  logs, ep2 output (group B), strace logs and an audit analysed WITHOUT a manifest (the processes were killed before
  writing one, so the auditor cannot exempt the dev-role obs_all reads or reconcile the det_f0 opens with the guard's
  count; every flagged path is an obs_all file of the episode or its det_f0.npz, no GT path).
