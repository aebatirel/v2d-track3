#!/bin/bash
# Perception precision sweep (2026-10-25; rule pre-registered in docs/work-log.md before any run): perc2 on the public
# episodes once per variant (env settings, e.g. FoundationPose refiner iterations), each track scored afterwards against
# mocap with library_v2 meshes (score_registered.py: registered AUC + per-frame errors; diagnostic, after inference).
# Today's detection (on-table rule, gated re-proposal) applies to every variant; tracking seeds = library_v2 as in G1.
#   ops/vast.sh create <offer> <run> 'VARIANTS="base: t4:TRACK_ITERS=4 t8:REG_ITERS=10,TRACK_ITERS=8" bash ops/jobs/perc_sweep.sh'
# Output /content/results/sweep/<variant>/ep<N>/ (poses, logs, score_registered.json, per-frame npz) and
# /content/results/sweep/summary.json (mean registered AUC per variant, per-episode table).
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; O=/content/results/sweep; mkdir -p $O
EPS=${EPS:-"0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45"}
VARIANTS=${VARIANTS:-"base: t4:TRACK_ITERS=4 t8:REG_ITERS=10,TRACK_ITERS=8"}
log "perc_sweep code $(git -C $REPO_DIR rev-parse --short HEAD), episodes [$EPS], variants [$VARIANTS]" >> $J
ensure_gdino $J
pip install -q fast_simplification manifold3d >> $J 2>&1 || true
for ep in $EPS; do
  bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1 || log "sweep ep$ep: no cached depth (computed here)" >> $J
  for v in $VARIANTS; do
    name=${v%%:*}; envs=${v#*:}; D=$O/$name/ep$ep; mkdir -p $D
    [ -s /content/cache/depth/ep$ep/depths_fs0.5.npy ] && [ ! -e $D/depths_fs0.5.npy ] && ln -sf /content/cache/depth/ep$ep/depths_fs0.5.npy $D/
    label "sweep ep$ep $name"
    ( [ -n "$envs" ] && export $(echo "$envs" | tr ',' ' ')
      KF_MIN=120 EP=$ep OUT=$D SPLIT=public MESH_DIR=$REPO_DIR/meshes/library_v2 python $P/perc2.py > $D/log.txt 2>&1 )
    rc=$?
    python $P/score_registered.py $ep $D/poses_world_vo.npz --meshes $REPO_DIR/meshes/library_v2 --out $D/score_registered.json \
      --per_frame $D/per_frame.npz > $D/score_registered.log 2>&1
    log "sweep ep$ep $name rc=$rc: $(python -c "import json; d = json.load(open('$D/score_registered.json'))['perception']; print('AUC', d['AUC'], d['per_obj_AUC'])" 2>&1 | tail -1 | cut -c1-200)" >> $J
    rm -f $D/depths_fs0.5.npy
  done
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true
done
python - $O "$VARIANTS" << 'EOF' > $O/summary.json
import glob, json, os, sys
O, variants = sys.argv[1], [v.split(':')[0] for v in sys.argv[2].split()]
tab = {}
for v in variants:
    for f in glob.glob(f'{O}/{v}/ep*/score_registered.json'):
        ep = int(f.split('/ep')[-1].split('/')[0]); p = json.load(open(f))['perception']
        tab.setdefault(ep, {})[v] = dict(AUC=p['AUC'], per_obj=p['per_obj_AUC'])
eps = sorted(e for e in tab if all(v in tab[e] for v in variants))
mean = {v: round(sum(tab[e][v]['AUC'] for e in eps) / max(1, len(eps)), 4) for v in variants}
print(json.dumps(dict(episodes=eps, mean_AUC=mean, table={str(e): tab[e] for e in sorted(tab)}), indent=1))
EOF
log "perc_sweep done: $(python -c "import json; d = json.load(open('$O/summary.json')); print(len(d['episodes']), 'episodes', d['mean_AUC'])")" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
