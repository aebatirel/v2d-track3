#!/bin/bash
# Writes rA1.job / rA2.job (reward A/B, 2026-11-13). Each box: two public episodes from test A (gate-testA-20261113),
# where test A's standard learner followed its reference (sim_vs_ref 0.89-0.97). The control is test A's own chosen
# checkpoint (FDR top-k point match, sigma 0.1 m); the treatment retrains the same reference, seed and recipe with the
# winner's centroid reward (FC_FDR_OBJ_MODE=centroid, lever 0.1 m, FC_FDR_OBJ_SIGMA=0.03). hard_ab.sh then gives both
# chosen checkpoints NREP=5 fresh official draws on this box and scores every draw against mocap.
set -e
cd "$(dirname "$0")"
mk() {  # $1 job name, then pairs RUN:EP:SHA256(reference parquet of test A)
  local name=$1; shift
  {
    echo "# reward A/B box $name: $(for x in "$@"; do echo -n "ep$(echo $x | cut -d: -f2) "; done)(training order). Plan + PREREG: docs/research/work/reward-ab-20261113/README.md"
    echo 'R0=20261020-refsweep-ea14fdf'
    for x in "$@"; do
      r=$(echo $x | cut -d: -f1); e=$(echo $x | cut -d: -f2)
      echo "for i in 1 2 3; do PULL_SUB=\"perc2/ep$e\" bash ops/box/store.sh pull-run \$R0 >> /content/prepull.log 2>&1 && PULL_SUB=\"refs/perc2s/ep$e\" bash ops/box/store.sh pull-run $r >> /content/prepull.log 2>&1 && break; echo \"[\$(date -u +%FT%TZ)] reward A/B: pull for ep$e failed (try \$i)\" >> /content/job.log; sleep 120; done"
      echo "bash ops/box/store.sh pull-files runs/$r/results/perc2s/ep$e-s42/selection.json >> /content/prepull.log 2>&1"
      echo "CK=\$(python3 -c \"import json; print(json.load(open('/content/hfstore/runs/$r/results/perc2s/ep$e-s42/selection.json'))['chosen'])\")"
      echo "bash ops/box/store.sh pull-files runs/$r/runs/perc2s/ep$e-s42/\$(basename \$CK) >> /content/prepull.log 2>&1"
      echo "mkdir -p /content/results/perc2s/ep$e-s42 /content/runs/perc2s/ep$e-s42 && cp /content/hfstore/runs/$r/results/perc2s/ep$e-s42/selection.json /content/results/perc2s/ep$e-s42/ && cp /content/hfstore/runs/$r/runs/perc2s/ep$e-s42/\$(basename \$CK) \$CK"
    done
    echo 'for x in '"$(for x in "$@"; do echo -n "$(echo $x | cut -d: -f2):$(echo $x | cut -d: -f3) "; done)"'; do'
    echo '  e=${x%%:*}; f=$(ls /content/refs/perc2s/ep$e/processed/*/*/*.parquet 2> /dev/null | head -1)'
    echo '  [ -n "$f" ] && [ "$(sha256sum < $f | cut -c1-64)" = "${x#*:}" ] && [ -s /content/perc2/ep$e/poses.npz ] && [ -s "$(python3 -c "import json; print(json.load(open(\"/content/results/perc2s/ep$e-s42/selection.json\"))[\"chosen\"])")" ] \'
    echo '    || { echo "[$(date -u +%FT%TZ)] reward A/B: ep$e reference, perception or control checkpoint missing, or reference sha256 mismatch" >> /content/job.log; exit 1; }'
    echo '  echo "[$(date -u +%FT%TZ)] reward A/B: ep$e reference $f sha256 OK (test A input); control checkpoint present" >> /content/job.log'
    echo 'done'
    echo '. /content/v2d-track3/ops/box/lib.sh'
    echo 'export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS" \'
    echo '  FC_FDR_OBJ_MODE=centroid FC_FDR_OBJ_LEVER=0.1 FC_FDR_OBJ_SIGMA=0.03 \'
    echo '  SPLIT=public PDIR_ROOT=/content/perc2 SUF=c CR=0 BASE_EVAL=1 NREP=5 SEED=42 LIB=/content/v2d-track3/meshes/library_v3 \'
    echo "  PAIRS=\"$(for x in "$@"; do echo -n "$(echo $x | cut -d: -f2):local:s "; done | sed 's/ $//')\""
    echo 'bash ops/jobs/hard_ab.sh'
    echo '# arm 2 (13 Nov amendment): the same centroid reward + reward centring (FC_RC=1); control already evaluated above'
    echo 'FC_RC=1 FC_RC_GAMMA=0.99 FC_RC_BETA=1e-3 SUF=cr BASE_EVAL=0 bash ops/jobs/hard_ab.sh'
  } > $name.job
}
# reference sha256 = the parquet test A trained on (refs/perc2s/ep<N>/processed in its run; same file as the gate input)
mk rA1 20261113-gA1b-25cb421:12:86316dcedab00803ab79347e63dd71982c60ca5c606f3790ebcbb19e0ff24955 20261113-gA3-25cb421:2:a35dc7069a6a2980acacd106a2c42f32054fdd21502c2390db8b0fec00494d4f
mk rA2 20261113-gA2-25cb421:40:26b969a60c506fefe076b1a3ce1a3b628f2da0297b5b0c0b6e372c974752c121 20261113-gA3-25cb421:23:4ad4020ceabd333a21988693a9bc90074c7714ce25bcc9913174c1f86e4f98d2
sha256sum rA1.job rA2.job make_jobs.sh > SHA256SUMS
