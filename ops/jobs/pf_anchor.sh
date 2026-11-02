#!/bin/bash
# Spoon-anchor re-evaluation (2026-11-02, perfect-following lane; docs/research/work/pf-anchor-20261102/PREREG.md, written
# before any draw). EVAL episodes, GT-free, NO training. Per episode: the board policy's own reference P (the table's
# packed inputs, md5-checked) is replaced AT ITS PATH by the committed R' (docs/research/work/pf-anchor-20261102/refs/
# ep<N>.parquet: P with the spoon's initial rest orientation set to the raw tracker's rest-averaged orientation,
# tools/anchor_rest.py; md5 from refs/MD5SUMS), so the board checkpoint (unchanged; its config names that path, no
# content hash) is rolled out on R'. NCONF fresh official draws on the pristine evaluator (kit run_policy_evaluation.py,
# clean worktree), tools/dr_score.py vs P and R, tools/anchor_verdict.py. Nothing is packed or uploaded here.
# Env: EP (episodes), NCONF (10), PACKED_DRAWS_EP<N> / OLD_EP<N> (store paths of the board policy's control draws /
# the board's row when they are not the H5p7 run / pack 6), TAB_EP<N> (table json, default packed_refs.json).
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-pfaA-<sha7> 'EP="32 33 35 36 37" ... bash ops/jobs/pf_anchor.sh'
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; HS=/content/hfstore; G=/content/results/pf_anchor; I=/content/pfa_in
W=$REPO_DIR/docs/research/work/pf-anchor-20261102; mkdir -p $G $I
case "${RUN_ID:-}" in *-pfa*) ;; *) log "pf_anchor: RUN_ID '${RUN_ID:-}' must contain -pfa" >> $J; exit 1 ;; esac
EPS=${EP:?EP}; NCONF=${NCONF:-10}; H5P7_RUN=20261031-h5p7-1a7cdff; EVAL_TIMEOUT=1200
LIB=$REPO_DIR/meshes/library_v3; CLEAN=/content/v2d_clean; KIT=/content/kit/v2d_submission_kit
FC=/content/v2d/robotic_grounding/flash_chord; FCV=$FC/.venv/bin/python
log "pf_anchor code $(git -C $REPO_DIR rev-parse --short HEAD), EP [$EPS], NCONF $NCONF" >> $J
pull1() { bash $OPS/store.sh pull-files $1 >> $J 2>&1; }
tab_of() { local v=TAB_EP$1; echo ${!v:-$REPO_DIR/docs/research/work/masses-eval-20261031/packed_refs.json}; }
tabl() { python -c "import json, sys; v = json.load(open(sys.argv[1]))['episodes'][sys.argv[2]][sys.argv[3]]; print(' '.join(v) if isinstance(v, list) else v)" $(tab_of $1) $1 $2; }

confirm() {  # as ops/jobs/pf_arms.sh: $1 ep, $2 checkpoint, $3 out dir; draws on the pristine evaluator until NCONF have a qa
  local ep=$1 ck=$2 D=$3 CK n O tries=0 fails=0 E6
  E6=$(printf %06d $ep); CK=$D/conf_checkpoints.json; mkdir -p $D
  python -c "import json, sys; json.dump({sys.argv[2]: sys.argv[3]}, open(sys.argv[1], 'w'))" $CK $ep $ck
  [ -d $CLEAN ] || git -C /content/v2d worktree add --detach $CLEAN HEAD >> $J 2>&1 || { log "pf_anchor: clean evaluator worktree FAILED" >> $J; return 1; }
  log "pf_anchor ep$ep: draws of $ck (sha256 $(sha256sum < $ck | cut -c1-12)) on the clean evaluator $(git -C $CLEAN rev-parse --short HEAD), modified files $(git -C $CLEAN status --short | wc -l)" >> $J
  have() { ls $D/r*/ep$ep/qa_policy.json 2> /dev/null | wc -l; }
  while [ "$(have)" -lt $NCONF ] && [ $tries -lt $((NCONF + 3)) ]; do
    n=$(( $(ls -d $D/r* 2> /dev/null | sed 's#.*/r##' | sort -n | tail -1 || echo 0) + 1 )); O=$D/r$n; tries=$((tries + 1))
    label "pf anchor: ep$ep draw $n"; mkdir -p $O/results $O/ep$ep
    ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
        timeout -k 60 $EVAL_TIMEOUT $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $CK --results $O/results \
        --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $O/eval.log 2>&1
    echo $? > $O/eval_rc.txt
    cp $O/results/episode_$E6.* $O/ep$ep/ 2> /dev/null && python $P/qa.py policy $O/ep$ep $ep > /dev/null 2>&1 || true
    rm -rf $O/results
    log "pf_anchor ep$ep: draw $n rc $(cat $O/eval_rc.txt) sim_vs_ref $(python -c "import json, sys; print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $O/ep$ep/qa_policy.json 2>/dev/null || echo none) overflow lines $(grep -ac 'overflow - please' $O/eval.log)" >> $J
    if [ -s $O/ep$ep/qa_policy.json ]; then fails=0; else fails=$((fails + 1)); fi
    [ $fails -lt 3 ] || { log "pf_anchor ep$ep: 3 draws in a row gave no rollout: stopped (INCOMPLETE)" >> $J; break; }
  done
}

for e in $EPS; do
  E6=$(printf %06d $e); src=$(tabl $e source_run); miss=""
  [ "$(tabl $e mode)" = glock ] || { log "pf_anchor ep$e: not a grasp-lock episode in $(tab_of $e)" >> $J; continue; }
  for f in $(tabl $e pull_files); do
    if ! pull1 $f; then case $f in *.txt|*.jpg|*_log.json) continue ;; esac; miss="$miss $f"; continue; fi
    r=${f#runs/$src/}; mkdir -p /content/$(dirname $r); [ -e /content/$r ] || cp $HS/$f /content/$r
  done
  [ -z "$miss" ] || { log "pf_anchor ep$e: pull FAILED [${miss# }]" >> $J; continue; }
  ref=/content/$(tabl $e reference)
  [ "$(md5sum < $ref | cut -c1-32)" = "$(tabl $e md5)" ] || { log "pf_anchor ep$e: board reference md5 mismatch" >> $J; continue; }
  mkdir -p $I/ep$e; cp $ref $I/ep$e/P.parquet
  want=$(grep " ep$e.parquet\$" $W/refs/MD5SUMS | cut -c1-32)
  [ -n "$want" ] && [ "$(md5sum < $W/refs/ep$e.parquet | cut -c1-32)" = "$want" ] || { log "pf_anchor ep$e: R' md5 mismatch" >> $J; continue; }
  cp $W/refs/ep$e.parquet $ref; cp $ref $I/ep$e/R.parquet      # R' at the path the checkpoint's config names
  ckf=$(tabl $e packed_checkpoint); pull1 $ckf || { log "pf_anchor ep$e: checkpoint pull FAILED" >> $J; continue; }
  ck=$I/ep$e/policy.safetensors; cp $HS/$ckf $ck; sha=$(sha256sum < $ck | cut -c1-64)
  [ "$sha" = "$(tabl $e packed_sha256)" ] || { log "pf_anchor ep$e: checkpoint sha256 $sha is not the board's" >> $J; continue; }
  python $T/no_oracle.py $ref $ck /content/refs/sf/ep$e > $G/no_oracle_ep$e.txt 2>&1 || { log "pf_anchor ep$e: no_oracle refused ($(tail -1 $G/no_oracle_ep$e.txt))" >> $J; continue; }
  log "pf_anchor ep$e: board checkpoint ${sha:0:12}; P md5 $(md5sum < $I/ep$e/P.parquet | cut -c1-12) -> R' md5 $(md5sum < $ref | cut -c1-12) at $ref; $(cut -c1-300 $W/refs/ep$e.json | tr -d '\n ')" >> $J
  confirm $e $ck $G/conf_ep$e
  for i in $(seq 1 10); do for x in parquet json; do              # the board policy's control draws on P
    pdv=PACKED_DRAWS_EP$e; f=runs/$H5P7_RUN/results/h5/r$i/ep$e/episode_$E6.$x; [ -n "${!pdv:-}" ] && f=${!pdv}/r$i/ep$e/episode_$E6.$x
    PULL_RETRY_S=5 pull1 $f && mkdir -p $I/ep$e/packed/r$i && cp $HS/$f $I/ep$e/packed/r$i/
  done; done
  OLD=runs/20261026-pack6-5203d42/results/submission/results/episode_$E6; odv=OLD_EP$e; [ -n "${!odv:-}" ] && OLD=${!odv}
  for x in parquet json; do PULL_RETRY_S=5 pull1 $OLD.$x && mkdir -p $I/ep$e/old/r1 && cp $HS/$OLD.$x $I/ep$e/old/r1/; done
  python $T/dr_score.py --kit $KIT --lib $LIB --ep $e --ref P=$I/ep$e/P.parquet --ref R=$I/ep$e/R.parquet --out $G/score_ep$e.json \
    --set "conf:R:$G/conf_ep$e/r*/ep$e/episode_$E6.parquet" --set "packed:P:$I/ep$e/packed/r*/episode_$E6.parquet" \
    --set "old:P:$I/ep$e/old/r1/episode_$E6.parquet" > $G/score_ep$e.txt 2>&1 || log "pf_anchor ep$e: scoring FAILED ($(tail -2 $G/score_ep$e.txt | tr '\n' ' ' | cut -c1-300))" >> $J
  python $T/anchor_verdict.py --score $G/score_ep$e.json --ep $e --checkpoint $sha --nconf $NCONF --out $G/verdict_ep$e.json > $G/verdict_ep$e.txt 2>&1
  log "pf_anchor ep$e RESULT: $(cut -c1-1500 $G/verdict_ep$e.txt)" >> $J; label "pf anchor ep$e: $(head -c 50 $G/verdict_ep$e.txt)"
  bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_anchor: interim push FAILED" >> $J
done
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_anchor: push FAILED (self_destroy retries)" >> $J
