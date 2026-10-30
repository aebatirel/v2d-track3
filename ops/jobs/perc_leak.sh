#!/bin/bash
# Leak decomposition, Phase 1: GPU perception on PUBLIC episodes (2026-10-30; owner, ~14:50 UTC: "go ahead with
# phase"). Plan and readings: docs/research/work/leak-decomp-20261030/PLAN.md §3 Phase 1, §7 B4; build notes, CPU mock
# and job strings: docs/research/work/leak-decomp-20261030/phase1/{BUILD.md,JOBS.txt}. Per episode, on one box and one
# commit, with ONE depth cache (the store's cache/depth/public/ep<N>/depths_fs0.5.npy, reused, never recomputed here)
# and the refine inputs' hands (phase1/inputs.tsv: store paths, size, frame-0 sha256, md5, fixed 30 Oct), perc2 runs
# once per arm (ARMS, comma list):
#   o   P_o: our templates, MESH_DIR=$LIB (library_v3)                          -> results/leak_p1/ep<N>/perc2/
#   s   P_s: the organiser scans as templates, MESH_DIR unset (perc2 then tracks /content/t3/mesh/<obj>/<obj>.glb, or
#       <obj>_visual.glb). ORACLE input: the scans are the true geometry       -> results/leak_p1/ep<N>/perc2scan/
#   o2  P_o again (GPU noise floor), only for the episodes in REPEAT             -> results/leak_p1/ep<N>/perc2rep/
# perc2 runs with the eval pipeline's settings (pipeline_ep.sh: KF_MIN=120, the rest perc2's defaults), so the template
# is the only difference between o and s; Grounding DINO is downloaded ONCE per box (retried) and every perc2 run loads
# it from that cache (HF_HUB_OFFLINE=1). Before any download the job checks the public files perc2 reads (fetch_data.sh
# once more, else exit 1). tools/leak_p1.py checks the inputs (depth size/shape/frame-0 sha256 and hands md5 vs
# inputs.tsv; writes depth0.npy and hands/) and builds each episode's bundle.json (template files perc2 resolves, depth
# reuse, camera agreement between arms, Grounding DINO loaded, perc_log_inference.txt cut before perc2's mocap-scoring
# lines).
# Store traffic (HF 429, 30 Oct): inputs come as single files (store.sh pull-files: no listing, retried), fetched in the
# background so downloads overlap the GPU; the bundles are pushed ONCE, by run_job.sh's final push-run (plus the
# watchdog's interim pushes every 30 min). This job pushes nothing itself and pulls no earlier run.
# Integrity (CLAUDE.md): public episodes only (SPLIT=public; EPS must be in inputs.tsv); perc2 reads mocap only in its
# final scoring block (result.json, the last lines of log.txt), after its tracks are written. RUN_ID must be refused by
# tools/no_oracle.py (the eval packs' guard in pack_eval.sh, h5_reeval.sh, submit_pack.sh), i.e. <yyyymmdd>-orc<X>-<sha>;
# the guard also refuses the bare perc2scan / perc2gf / leak_p1 folder names (PLAN §7 B8, in tools/no_oracle.py).
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-orcP1a-<sha> \
#     'EPS="11 12" REPEAT="11 12" ARMS=o,s,o2 LIB=/content/v2d-track3/meshes/library_v3 bash ops/jobs/perc_leak.sh'
# Output: /content/results/leak_p1/{summary.json,summary.txt,ep<N>/,bundle_ep<N>_oracle.tar,leak_pull.log}; RESULT
# lines in /content/job.log. The download log sits under results/ so the stall watchdog sees download retries as
# progress. The tar holds ep<N>/ without any result.json or log.txt (perc2's mocap scores; they stay in the folder push
# for diagnostics), so that a later box or this VM fetches an episode's inference inputs with one download; "oracle" in
# its name keeps it out of packs on its own (it contains perc2scan).
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; T=$REPO_DIR/tools; J=${J:-/content/job.log}; B=/content/results/leak_p1; HS=/content/hfstore
EPS=${EPS:?EPS (public episodes) missing}; REPEAT=${REPEAT:-}; ARMS=${ARMS:-o,s,o2}; LIB=${LIB:-$REPO_DIR/meshes/library_v3}
IN=${IN_TSV:-$REPO_DIR/docs/research/work/leak-decomp-20261030/phase1/inputs.tsv}
case $LIB in /*) ;; *) LIB=$REPO_DIR/$LIB ;; esac                     # perc2 chdirs to FoundationPose before loading it
export SPLIT=public COMMIT=$(git -C $REPO_DIR rev-parse HEAD)
col() { awk -F'\t' -v e=$1 -v c=$2 'NR > 1 && $1 == e {print $c}' $IN; }   # inputs.tsv column c of episode e
adir() { case $1 in o) echo perc2 ;; s) echo perc2scan ;; o2) echo perc2rep ;; esac; }
arms() { for a in ${ARMS//,/ }; do [ $a = o2 ] && [[ " $REPEAT " != *" $1 "* ]] && continue; echo -n "$a "; done; }
python $T/no_oracle.py "${RUN_ID:-}" > /dev/null 2>&1 \
  && { log "perc_leak: RUN_ID '${RUN_ID:-}' is not refused by tools/no_oracle.py (use <yyyymmdd>-orc<X>-<sha>)" >> $J; exit 1; }
for a in ${ARMS//,/ }; do
  case $a in o|s|o2) ;; *) log "perc_leak: unknown arm $a (o, s, o2; P_gf is Phase 1b)" >> $J; exit 1 ;; esac
done
for e in $EPS; do
  [ -n "$(col $e 1)" ] || { log "perc_leak: ep$e is not one of the public episodes in $IN" >> $J; exit 1; }
  for o in $(col $e 3 | tr , ' '); do
    [ -s $LIB/$o.glb ] || { log "perc_leak: template $LIB/$o.glb missing (ep$e)" >> $J; exit 1; }
  done
done
for e in $REPEAT; do [[ " $EPS " == *" $e "* ]] || { log "perc_leak: REPEAT ep$e is not in EPS" >> $J; exit 1; }; done
need() {  # $1 episode: the public files perc2 reads (pipeline/fetch_data.sh in setup; run_job.sh ignores its exit status)
  local f o; for f in /content/t3/calib.json /content/t3/ep$1.parquet /content/t3/v/ep$1_{a,b,c}.mp4; do [ -s $f ] || echo $f; done
  for o in $(col $1 3 | tr , ' '); do [ -s /content/t3/mesh/$o/$o.glb ] || [ -s /content/t3/mesh/$o/${o}_visual.glb ] || echo scan:$o; done
}
miss=$(for e in $EPS; do need $e; done)                              # checked before any download or perc2 run
[ -z "$miss" ] || { log "perc_leak: public data incomplete ($(echo $miss | cut -c1-200)): fetch_data.sh again" >> $J
  bash $REPO_DIR/pipeline/fetch_data.sh >> /content/setup.log 2>&1; miss=$(for e in $EPS; do need $e; done); }
[ -z "$miss" ] || { log "perc_leak: public data still incomplete, nothing run: $(echo $miss | cut -c1-300)" >> $J; exit 1; }
log "perc_leak code ${COMMIT:0:7}, episodes [$EPS], repeat [$REPEAT], arms $ARMS, LIB $LIB, inputs $IN, gpu" \
    "$(nvidia-smi --query-gpu=name --format=csv,noheader 2> /dev/null | head -1)" >> $J

prefetch() {  # every episode's inputs in EPS order, one file per download; marks $ST/p1_<ep>.ok or .fail
  for e in $EPS; do
    if bash $OPS/store.sh pull-files $(col $e 4) $(col $e 7)/hands.npz $(col $e 7)/hands_refined.npz >> $B/leak_pull.log 2>&1; then
      touch $ST/p1_$e.ok
    else
      touch $ST/p1_$e.fail
    fi
  done
}

run_arm() {  # $1 episode, $2 arm, $3 depth cache: one perc2 run in the arm's folder, run.json beside its outputs
  local e=$1 a=$2 dep=$3 O=$B/ep$1/$(adir $2) t0 rc s0 s1 md
  mkdir -p $O; ln -sfn $dep $O/depths_fs0.5.npy                     # perc2 reuses OUT/depths_fs0.5.npy if it exists
  s0=$(stat -Lc '%i %s %Y' $dep); t0=$(date +%s)
  if [ $a = s ]; then
    md='<unset>'; env -u MESH_DIR HF_HUB_OFFLINE=1 KF_MIN=120 EP=$e OUT=$O python $P/perc2.py > $O/log.txt 2>&1
  else
    md=$LIB; HF_HUB_OFFLINE=1 MESH_DIR=$LIB KF_MIN=120 EP=$e OUT=$O python $P/perc2.py > $O/log.txt 2>&1
  fi
  rc=$?; s1=$(stat -Lc '%i %s %Y' $dep); rm -f $O/depths_fs0.5.npy
  printf '{"arm": "%s", "episode": %d, "mesh_dir": "%s", "kf_min": 120, "rc": %d, "t0": %d, "t1": %d, "depth": "%s", "depth_stat_before": "%s", "depth_stat_after": "%s"}\n' \
    $a $e "$md" $rc $t0 $(date +%s) $dep "$s0" "$s1" > $O/run.json
  log "perc_leak ep$e $a rc=$rc $(( $(date +%s) - t0 )) s: $(grep -a 'depth ready\|vo keyframes\|tracked ' $O/log.txt | cut -c1-90 | tr '\n' ' ' | cut -c1-400)" >> $J
}

rm -f $ST/p1_*.ok $ST/p1_*.fail; mkdir -p $B
ensure_gdino $J                                                      # perc2's detection grounding term
prefetch &                                                           # after the pip install (it may swap huggingface_hub)
gd=0                     # Grounding DINO ONCE per box (HF 429), retried; perc2 then runs with HF_HUB_OFFLINE=1, so
if python -c "import transformers" 2> /dev/null; then              # every arm loads the same cached files
  for i in 1 2 3 4 5; do
    HF_HUB_DISABLE_PROGRESS_BARS=1 python -c "import sys; sys.path.insert(0, '$P'); from det_rules import GDINO as G; import transformers as t; t.AutoProcessor.from_pretrained(G); t.AutoModelForZeroShotObjectDetection.from_pretrained(G)" >> $J 2>&1 \
      && { gd=1; log "perc_leak: Grounding DINO cached (try $i); perc2 runs offline (HF_HUB_OFFLINE=1)" >> $J; break; }
    log "perc_leak: Grounding DINO download try $i failed" >> $J; [ $i = 5 ] || sleep $(( ${PULL_RETRY_S:-60} * i ))
  done
fi
[ $gd = 1 ] || log "perc_leak: Grounding DINO NOT available: perc2 runs without its grounding term; the bundles mark those arms NO-GDINO (not ok)" >> $J
for e in $EPS; do
  label "leak P1: ep$e inputs"
  while [ ! -e $ST/p1_$e.ok ] && [ ! -e $ST/p1_$e.fail ]; do sleep 10; done
  dep=$HS/$(col $e 4)
  if [ -e $ST/p1_$e.fail ]; then log "perc_leak ep$e: inputs not downloaded ($B/leak_pull.log): skipped" >> $J; continue; fi
  python $T/leak_p1.py inputs $e $IN $dep $HS/$(col $e 7) $B/ep$e >> $J 2>&1
  rc=$?; [ $rc = 0 ] || { log "perc_leak ep$e: depth cache unusable (inputs rc=$rc): perception skipped" >> $J; rm -f $dep; continue; }
  label "leak P1: ep$e arms $(arms $e)"
  for a in $(arms $e); do run_arm $e $a $dep; done
  python $T/leak_p1.py bundle $e $B/ep$e $P/perc2.py >> $J 2>&1 || log "perc_leak ep$e: bundle FAILED" >> $J
  tar -C $B --exclude=result.json --exclude=log.txt -cf $B/bundle_ep${e}_oracle.tar ep$e 2>> $J   # one file per episode
                                                                     # for later pulls (Phase 2), no mocap scores in it
  rm -f $dep                                                         # the store keeps it; frees the disk
done
wait
python $T/leak_p1.py summary $B $EPS > $B/summary.txt 2>&1; src=$?    # 3: an arm failed (run_job.sh then holds the box)
while read -r l; do log "perc_leak RESULT $l"; done < $B/summary.txt >> $J
# guard (tools/no_oracle.py, the eval packs' check): the bundles' store paths carry the -orc run id (checked at the
# start), and the bare P_s folder name is refused on its own (perc2scan, PLAN §7 B8); both are re-checked for the record
e=${EPS%% *}
python $T/no_oracle.py runs/$RUN_ID/results/leak_p1/ep$e/perc2scan/poses.npz > /dev/null 2>&1 \
  && log "perc_leak: GUARD ERROR: tools/no_oracle.py accepts runs/$RUN_ID/... (run id must carry -orc)" >> $J \
  || log "perc_leak: guard refuses runs/$RUN_ID/results/leak_p1/... (run id)" >> $J
python $T/no_oracle.py ep$e/perc2scan/poses.npz > /dev/null 2>&1 \
  && log "perc_leak: GUARD ERROR: tools/no_oracle.py accepts the bare perc2scan folder name (B8 missing)" >> $J \
  || log "perc_leak: guard refuses the bare perc2scan folder name" >> $J
label "leak P1 done: $(tail -1 $B/summary.txt | cut -c1-60)"
log "perc_leak done (rc $src); run_job.sh pushes runs/$RUN_ID once and self-destroys" >> $J
exit $src
