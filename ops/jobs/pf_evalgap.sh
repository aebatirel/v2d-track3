#!/bin/bash
# Evaluator-gap test (2026-11-03; docs/research/work/pf-evalgap-20261103/PREREG.md, written before any draw). Two stored
# checkpoints, each with its own reference / assets at the paths its config names; per round one draw of
#   A = patched training tree + repo scripts/evaluate_policy.py + that job's evaluating-process env (the box path),
#   B = pristine kit run_policy_evaluation.py on a clean worktree (the confirmation path),
#   C = patched tree + repo script, every switch off.
# Scored by pipeline/qa.py; summary + reading by inline python. Nothing is trained, packed or uploaded.
. /content/v2d-track3/ops/box/lib.sh
T=$REPO_DIR/tools; P=$REPO_DIR/pipeline; J=${J:-/content/job.log}; HS=/content/hfstore; G=/content/results/pf_evalgap; I=/content/eg_in
mkdir -p $G $I; NR=${NR:-10}; EVAL_TIMEOUT=1200
case "${RUN_ID:-}" in *-pfg*) ;; *) log "pf_evalgap: RUN_ID must contain -pfg" >> $J; exit 1 ;; esac
CLEAN=/content/v2d_clean; KIT=/content/kit/v2d_submission_kit; FC=/content/v2d/robotic_grounding/flash_chord; FCV=$FC/.venv/bin/python
pull1() { bash $OPS/store.sh pull-files $1 >> $J 2>&1; }
log "pf_evalgap code $(git -C $REPO_DIR rev-parse --short HEAD), NR $NR" >> $J

prep() {  # $1 tag, $2 table, $3 ep, $4 checkpoint store path: pull the table's inputs, place the reference + stage at the config path
  local tag=$1 tab=$2 e=$3 ckf=$4 src ref f r rp rr
  tabl() { python -c "import json, sys; v = json.load(open(sys.argv[1]))['episodes'][sys.argv[2]][sys.argv[3]]; print(' '.join(v) if isinstance(v, list) else v)" $tab $e $1; }
  src=$(tabl source_run)
  for f in $(tabl pull_files); do pull1 $f || continue; r=${f#runs/$src/}; mkdir -p /content/$(dirname $r); [ -e /content/$r ] || cp $HS/$f /content/$r; done
  ref=/content/$(tabl reference); case $(tabl mode) in std) ref=$(ls /content/refs/perc2mck/ep$e/processed/*/*/*.parquet | head -1) ;; esac
  [ "$(md5sum < $ref | cut -c1-32)" = "$(tabl md5)" ] || { log "pf_evalgap $tag: reference md5 mismatch" >> $J; return 1; }
  pull1 $ckf || { log "pf_evalgap $tag: checkpoint pull FAILED" >> $J; return 1; }; mkdir -p $I/$tag; cp $HS/$ckf $I/$tag/policy.safetensors
  rp=$(python -c "
import json, struct, sys
b = open(sys.argv[1], 'rb'); n = struct.unpack('<Q', b.read(8))[0]; c = json.loads(json.loads(b.read(n))['__metadata__']['user.resolved_config_json'])
def find(d):
    if isinstance(d, dict):
        if isinstance(d.get('reference'), dict) and 'parquet' in d['reference']: return d['reference']['parquet']
        for v in d.values():
            r = find(v)
            if r: return r
print(find(c) or '')" $I/$tag/policy.safetensors)
  [ -s "$rp" ] || { mkdir -p $(dirname $rp); cp $ref $rp; }
  rr=${rp%%/processed/*}; [ -d $rr/reconstructed_stage ] || cp -r $(dirname $(dirname $(dirname $ref)))/reconstructed_stage $rr/ 2> /dev/null \
    || cp -r /content/refs/perc2mck/ep$e/reconstructed_stage $rr/
  [ "$(md5sum < $rp | cut -c1-32)" = "$(tabl md5)" ] || { log "pf_evalgap $tag: $rp is not the reference (md5)" >> $J; return 1; }
  log "pf_evalgap $tag: ep$e checkpoint $(sha256sum < $I/$tag/policy.safetensors | cut -c1-12), reference $rp, stage $(ls $rr/reconstructed_stage | tr '\n' ' ')" >> $J
}
drawA() {  # $1 ckpt $2 dir $3 ep $4 env-string
  mkdir -p $2; ( cd $FC && env $4 MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false timeout -k 60 $EVAL_TIMEOUT .venv/bin/python scripts/evaluate_policy.py \
    evaluation.checkpoint=$1 evaluation.world_count=1 evaluation.reset_mode=explicit evaluation.metrics_output=$2/episode_$(printf %06d $3).json \
    evaluation.object_trajectories_output=$2/episode_$(printf %06d $3).parquet hydra.run.dir=$2/hydra logging.mode=disabled ) > $2/eval.log 2>&1
  echo $? > $2/eval_rc.txt; python $P/qa.py policy $2 $3 > /dev/null 2>&1 || true
}
drawB() {  # $1 ckpt $2 dir $3 ep
  local E6=$(printf %06d $3); mkdir -p $2/results
  python -c "import json, sys; json.dump({sys.argv[2]: sys.argv[3]}, open(sys.argv[1], 'w'))" $2/ck.json $3 $1
  ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false \
      timeout -k 60 $EVAL_TIMEOUT $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $2/ck.json --results $2/results \
      --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $2/eval.log 2>&1
  echo $? > $2/eval_rc.txt; cp $2/results/episode_$E6.* $2/ 2> /dev/null; rm -rf $2/results; python $P/qa.py policy $2 $3 > /dev/null 2>&1 || true
}

# --- inputs
label "evalgap: inputs"
prep K30 $REPO_DIR/docs/research/work/pf-mesh-20261102/packed_refs_13f.json 30 runs/20261102-pfP2-b0b4a31/results/pfsms42_glock_public/ep30/best/policy.safetensors || exit 1
prep K14 $REPO_DIR/docs/research/work/pf-lift-20261102/packed_refs_12b.json 14 runs/20261102-pfI-6c80007/results/pfplws42_glock_public/ep14/best/policy.safetensors || exit 1
# K30's collision: /content/assets from library_v3 + Tier B sweeper / rack (as pfP2); K14's: refs/pfss43_sf/ep14/assets as pulled
rm -rf /content/lib_tb; cp -r $REPO_DIR/meshes/library_v3 /content/lib_tb
for o in mini_sweeper plastic_dish_rack; do cp $REPO_DIR/meshes/tierB_collision/$o.glb /content/lib_tb/$o.glb; done
python $P/make_assets.py /content/lib_tb /content/assets >> $J 2>&1 || { log "pf_evalgap: make_assets FAILED" >> $J; exit 1; }
# --- the patched training tree (as hard_ab.sh / glock_public.sh) and the clean worktree
python $REPO_DIR/ops/box/patch_flashchord.py $FC >> $J 2>&1 && python $REPO_DIR/ops/box/patch_flashchord_fdr.py $FC >> $J 2>&1 \
  && python $REPO_DIR/ops/box/patch_flashchord_voc.py $FC >> $J 2>&1 && python $REPO_DIR/ops/box/patch_flashchord_lift.py $FC >> $J 2>&1 \
  || { log "pf_evalgap: patching FAILED" >> $J; exit 1; }
[ -d $CLEAN ] || git -C /content/v2d worktree add --detach $CLEAN HEAD >> $J 2>&1 || { log "pf_evalgap: clean worktree FAILED" >> $J; exit 1; }
{ echo "== training tree status"; git -C /content/v2d status --short | head -40; echo "== clean tree status"; git -C $CLEAN status --short | head
  echo "== diff kit vs repo evaluate_policy.py"; diff $KIT/flash_chord/scripts/evaluate_policy.py $FC/scripts/evaluate_policy.py | head -80; } > $G/trees.txt 2>&1
log "pf_evalgap: trees: $(grep -c . $G/trees.txt) lines (results/pf_evalgap/trees.txt); diff kit vs repo script lines $(diff $KIT/flash_chord/scripts/evaluate_policy.py $FC/scripts/evaluate_policy.py | grep -c '^[<>]')" >> $J
ENV_K30="FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25"; ENV_K14="FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1"
# --- rounds: A, B, C interleaved
for i in $(seq 1 $NR); do
  for tag in K30 K14; do
    e=${tag#K}; ev=ENV_$tag; ck=$I/$tag/policy.safetensors
    label "evalgap: $tag round $i"
    drawA $ck $G/$tag/A/r$i $e "${!ev}"; drawB $ck $G/$tag/B/r$i $e; drawA $ck $G/$tag/C/r$i $e "FC_VOC_INERTIA=0"
    log "pf_evalgap $tag r$i: A $(python -c "import json,sys;print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $G/$tag/A/r$i/qa_policy.json 2>/dev/null || echo none) B $(python -c "import json,sys;print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $G/$tag/B/r$i/qa_policy.json 2>/dev/null || echo none) C $(python -c "import json,sys;print(json.load(open(sys.argv[1]))['sim_vs_ref'])" $G/$tag/C/r$i/qa_policy.json 2>/dev/null || echo none)" >> $J
  done
done
python - $G << 'EOF' > $G/summary.json
import glob, json, sys
import numpy as np
G = sys.argv[1]; out = {}
for tag in ('K30', 'K14'):
    v = {}
    for c in 'ABC':
        v[c] = [json.load(open(f))['sim_vs_ref'] for f in sorted(glob.glob(f'{G}/{tag}/{c}/r*/qa_policy.json'))]
    s = {c: dict(n=len(x), mean=round(float(np.mean(x)), 4) if x else None, sd=round(float(np.std(x, ddof=1)), 4) if len(x) > 1 else None,
                 min=round(float(min(x)), 4) if x else None) for c, x in v.items()}
    r = dict(cond=s)
    if all(len(v[c]) >= 8 for c in 'ABC'):
        a, b, cc = (np.array(v[c]) for c in 'ABC'); gap = a.mean() - b.mean()
        t = gap / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b) + 1e-12)
        r.update(gap=round(float(gap), 4), welch_t=round(float(t), 2), c_minus_b=round(float(cc.mean() - b.mean()), 4), a_minus_c=round(float(a.mean() - cc.mean()), 4))
        if gap >= 0.05 and t >= 2:
            r['reading'] = 'REPRODUCED: ' + ('env-switched patches' if cc.mean() - b.mean() < 0.02 else
                                             'tree / script' if (a.mean() - cc.mean() < 0.02 and cc.mean() - b.mean() >= 0.05) else 'mixed')
        elif abs(gap) < 0.02: r['reading'] = 'NOT REPRODUCED'
        else: r['reading'] = 'INCONCLUSIVE'
    else: r['reading'] = 'INCOMPLETE'
    out[tag] = r
out['box_gates_trustworthy'] = all(out[t].get('reading') == 'NOT REPRODUCED' for t in ('K30', 'K14'))
print(json.dumps(out, indent=1))
EOF
log "pf_evalgap RESULT: $(tr -d '\n ' < $G/summary.json | cut -c1-1500)" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || log "pf_evalgap: push FAILED" >> $J
