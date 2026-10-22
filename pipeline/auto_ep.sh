#!/bin/bash
# One episode with automatic QA and retries (2026-10-21, owner: "a good retry to that QA based on where it got stuck,
# automatic"). No ground truth is read; every decision uses our own reference (pipeline/qa.py).
#   1) references: the base variant BV (default E2S wrist cost) and BV+"c" (wrist cost 3.0), built up to the
#      reference stage; ranked by qa_ref (robot wrist IK p95, wrist jumps). 2026-10-21 evidence: wrist cost 3.0 cut
#      the wrist IK error 5-10x (ep18 right 247 -> 51 mm median) but the policy outcome was mixed, so both stay.
#   2) train the best-ranked reference (checkpoint sweep CK_SWEEP) -> qa_policy verdict (ok / weak / harmful).
#   3) not ok and RETRIES >= 1: train the other reference; still not ok and RETRIES >= 2: the first again, SEED+1.
#   4) the attempt that tracks our reference best (sim_vs_ref) is copied to /content/results/final/ep<EP>/ with
#      its exact checkpoint (policy.safetensors) and final.json listing every attempt and the checkpoint sha256.
# Usage (env as for pipeline_ep.sh: SPLIT, PERC, PDIR, STEPS, ASSETS, MESH_DIR ...):
#   BV=m RETRIES=2 bash pipeline/auto_ep.sh 1
set -u
EP=$1; S=${REPO_DIR:-/content/v2d-track3}/pipeline; BV=${BV:-}; PERC=${PERC:-perc2}; SEED0=${SEED:-42}
export CK_SWEEP=${CK_SWEEP:-"0.4 0.6 0.8"} PERC
log() { echo "[$(date +%T)] auto ep$EP: $*"; }
mk() { [ "${1:-}" = c ] && echo "--wrist_cost 3.0" || echo ""; }          # variant suffix -> mkref args
# 1) both references, ranked by the reference QA
cands=()
for suf in "" c; do
  V=$BV$suf
  VARIANT=$V MKREF_ARGS="$(mk "$suf")" STEPS=0 STOP_AFTER=reference bash $S/pipeline_ep.sh $EP > /content/auto_ref_${PERC}${V}_ep$EP.log 2>&1 \
    || { log "reference $V FAILED: $(tail -2 /content/auto_ref_${PERC}${V}_ep$EP.log | tr '\n' ' ')"; continue; }
  q=/content/refs/$PERC$V/ep$EP/qa_ref.json
  sc=$(python -c "import json; d=json.load(open('$q')); print(d['score'] + (0 if d['pass'] else 1000))" 2>/dev/null || echo 9999)
  log "reference $V: qa_ref $(cat $q 2>/dev/null | tr -d '\n ')"
  cands+=("$sc:$suf")
done
[ ${#cands[@]} -gt 0 ] || { log "no reference could be built"; exit 1; }
order=(); okref=()                                    # suffixes best first; okref: 1 if that reference passed its QA
for c in $(printf '%s\n' "${cands[@]}" | sort -t: -k1,1g); do
  s=${c%%:*}; f=${c#*:}; order+=("${f:-_}"); [ "${s%%.*}" -lt 1000 ] && okref+=(1) || okref+=(0)
done
# 2) + 3) attempts. A reference that failed its QA is trained only after the passing one has had a second seed
# (2026-10-21 ep24: the retry trained the reference with wrist p95 176 mm).
plan=("${order[0]}:$SEED0")
if [ ${#order[@]} -gt 1 ] && [ "${okref[1]}" = 1 ]; then
  plan+=("${order[1]}:$SEED0" "${order[0]}:$((SEED0 + 1))")
else
  plan+=("${order[0]}:$((SEED0 + 1))"); [ ${#order[@]} -gt 1 ] && plan+=("${order[1]}:$SEED0")
fi
n_max=$(( 1 + ${RETRIES:-2} )); att=(); best=-1; bestres=""; bestck=""
for k in "${!plan[@]}"; do
  [ $k -ge $n_max ] && break
  IFS=: read -r suf sd <<< "${plan[$k]}"; [ "$suf" = _ ] && suf=""; V=$BV$suf
  log "attempt $((k + 1)): variant '$V' seed $sd"
  VARIANT=$V MKREF_ARGS="$(mk "$suf")" SEED=$sd bash $S/pipeline_ep.sh $EP > /content/auto_${PERC}${V}_ep$EP-s$sd.log 2>&1
  rc=$?; RES=/content/results/$PERC$V/ep$EP-s$sd
  v=$(python -c "import json; d=json.load(open('$RES/qa_policy.json')); print(d['sim_vs_ref'], d['floor_vs_ref'], d['verdict'])" 2>/dev/null || echo "nan nan failed")
  read -r sim floor verdict <<< "$v"; log "attempt $((k + 1)) rc=$rc: sim_vs_ref $sim floor $floor -> $verdict"
  # the checkpoint behind this rollout: the sweep's choice, else the newest policy of the run
  ck=$(python -c "import json; print(json.load(open('$RES/selection.json'))['chosen'])" 2>/dev/null || ls -v /content/runs/$PERC$V/ep$EP-s$sd/policy_*.safetensors 2>/dev/null | tail -1)
  att+=("{\"variant\": \"$V\", \"seed\": $sd, \"rc\": $rc, \"sim_vs_ref\": \"$sim\", \"floor_vs_ref\": \"$floor\", \"verdict\": \"$verdict\", \"res\": \"$RES\", \"checkpoint\": \"$ck\"}")
  if [ "$verdict" != failed ] && python -c "import sys; sys.exit(0 if float('$sim') > float('$best') else 1)"; then best=$sim; bestfloor=$floor; bestres=$RES; bestck=$ck; fi
  [ "$verdict" = ok ] && break
done
# 4) publish the best attempt
[ -n "$bestres" ] || { log "no attempt produced a rollout"; exit 1; }
F=/content/results/final/ep$EP; mkdir -p $F; E6=$(printf %06d $EP)
cp $bestres/episode_$E6.parquet $bestres/episode_$E6.json $bestres/qa_policy.json $F/
# the exact checkpoint of the published rollout (submission provenance: its sha256 goes into the packed rows)
sha=""; [ -s "${bestck:-}" ] && cp $bestck $F/policy.safetensors && sha=$(sha256sum $F/policy.safetensors | cut -d' ' -f1)
# harmful: even the best attempt tracks our reference worse than the static floor (flag it; it is still a learned policy)
harm=$(python -c "import sys; print('true' if float('$best') < float('${bestfloor:-nan}') else 'false')" 2>/dev/null || echo false)
( IFS=,; echo "{\"episode\": $EP, \"chosen\": \"$bestres\", \"checkpoint\": \"${bestck:-}\", \"checkpoint_sha256\": \"$sha\", \"sim_vs_ref\": $best, \"floor_vs_ref\": \"${bestfloor:-nan}\", \"harmful\": $harm, \"attempts\": [${att[*]}]}" ) > $F/final.json
log "final: $bestres (sim_vs_ref $best)"
