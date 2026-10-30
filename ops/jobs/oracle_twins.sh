#!/bin/bash
# Oracle twins (2026-10-30; owner, ~09:35 UTC: "maybe we can try the public episode real refs to see if we can really
# copy them. intentionally go for the hard ones"). A DIAGNOSTIC on PUBLIC episodes only, never an input to eval
# inference: can the simulated robot copy the TRUE object motion of the public twins of the hardest eval episodes?
# Design and fixed readings: docs/research/work/oracle-twins-20261030/{DESIGN,PREREG}.md. Two arms per episode, on the
# same box, commit, seed and learner:
#   P  our perceived reference, built as for an eval episode: perc2 (our library LIB) -> hands -> mkref (wrist cost
#      3.0) -> contact retargeting with rest settling = refs/perc2mck/ep<N>;
#   O  the same build on the mocap object motion: pipeline/oracle_poses.py (mocap converted to LIB's mesh body frames
#      with the scorer's registration, aligned to the perceived table by gravity) on P's perception (same camera
#      trajectory and depth), P's hands copied byte for byte, the same mkref + contact retargeting = refs/oraclemck/ep<N>.
# G0, before any training: O's reference vs mocap (tools/ref_vs_mocap.py, registered ADD-AUC with LIB) >= G0_MIN (0.95),
#   mkref's support check passed without the fallback lift, frame-0 centres within 3 cm of perception (oracle.json);
#   otherwise O is not trained for that episode (P still is). P's reference vs mocap is recorded beside it.
# Then both arms train with the same learner; PAIRS entries EP:local:mck (P) and EP:local:mck:oracle (O: the PERC field
# keeps every folder of O under oracle names, see the learner scripts):
#   LEARNER=glock  ops/jobs/glock_public.sh, the grasp-lock recipe (GL_ARGS, SF, REPLAN, EVOLVE, CURVE_REP, NREP, SEED,
#                  STEPS from the environment; TRAIN_SLOTS (2) trainings share the GPU, the others wait);
#   LEARNER=std    ops/jobs/hard_ab.sh with std_learner.sh's settings (FDR + VOC + deployment-exact starts 0.25, 250M,
#                  checkpoint sweep 0.4/0.6/0.8, floor guard), SPLIT=public; the two arms take turns on the GPU.
#   Each arm's checkpoint is chosen by the recipe's own rule (sim_vs_ref against the arm's own reference); its NREP
#   official evaluations are scored with qa.py (sim_vs_ref) and score_registered.py --meshes LIB (registered ADD-AUC vs
#   mocap, as the leaderboard; also the rollout's reference and the static floor vs mocap).
# ENV_EP<N>: VAR=value settings for episode N in both arms (passed on to the learner), e.g. ENV_EP13="SF=1". PIECES=<dir>
#   in it builds that episode's references against its own asset root /content/assets_<basename DIR> with those
#   collision pieces (ep11: the eval-10 carve meshes/carve/ev10, whose blue cup must not reach ep13); a job-wide PIECES
#   is refused for that reason.
# Integrity (CLAUDE.md): mocap is read only by oracle_poses.py (arm O), ref_vs_mocap.py (G0, summary) and
#   score_registered.py (scoring), all after or outside inference of arm P. SPLIT is public (oracle_poses.py and
#   pipeline_ep.sh refuse eval episodes). RUN_ID must contain "-orc", and O never writes under refs/perc2mck*, glockt or sf:
#   eval packs refuse such runs and paths (tools/no_oracle.py in pack_eval.sh, h5_reeval.sh, submit_pack.sh).
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <date>-orcG-<sha> \
#     'LEARNER=glock EPS="11 13" ENV_EP11="SF=0 PIECES=meshes/carve/ev10" ENV_EP13="SF=1" bash ops/jobs/oracle_twins.sh'
# Output: /content/results/oracle_twins/summary.json, ep<N>/{g0.json,oracle.json,ref_vs_mocap_*.json}; RESULT lines in
# /content/job.log. Reference logs /content/ref_ep<N>.log (P), /content/oracle_ref_ep<N>.log (O).
. /content/v2d-track3/ops/box/lib.sh
P=$REPO_DIR/pipeline; T=$REPO_DIR/tools; J=${J:-/content/job.log}; OT=/content/results/oracle_twins; mkdir -p $OT
LEARNER=${LEARNER:-glock}; EPS=${EPS:?EPS (public twins) missing}; G0_MIN=${G0_MIN:-0.95}; SEED=${SEED:-42}
export SPLIT=public LIB=${LIB:-$REPO_DIR/meshes/library_v3} SEED; export MESH_DIR=$LIB
case "${RUN_ID:-}" in *-orc*) ;; *) log "oracle_twins: RUN_ID '${RUN_ID:-}' must contain -orc (eval packs refuse such runs)" >> $J; exit 1 ;; esac
case $LEARNER in glock|std) ;; *) log "oracle_twins: LEARNER $LEARNER is not glock or std" >> $J; exit 1 ;; esac
[ -n "${PIECES:-}" ] && { log "oracle_twins: put PIECES in ENV_EP<N> (per-episode asset roots), not job-wide" >> $J; exit 1; }
log "oracle_twins code $(git -C $REPO_DIR rev-parse --short HEAD), learner $LEARNER, episodes [$EPS], LIB $LIB, seed $SEED, G0 >= $G0_MIN, $(for e in $EPS; do v=ENV_EP$e; printf 'ENV_EP%s [%s] ' $e "${!v:-}"; done)" >> $J
pip install -q fast_simplification manifold3d >> $J 2>&1 || true   # kit budget_mesh (oracle_poses, ref_vs_mocap, scoring)
ensure_gdino $J                                                     # perception runs here (detection grounding term)

declare -A ROOT; made=" "                                           # per-episode asset roots (collision pieces)
for e in $EPS; do
  pc=$(v=ENV_EP$e; eval "${!v:-}"; echo "${PIECES:-}"); case $pc in /*|"") ;; *) pc=$REPO_DIR/$pc ;; esac
  r=/content/assets${pc:+_$(basename $pc)}; ROOT[$e]=$r
  case "$made" in *" $r "*) continue ;; esac
  python $P/make_assets.py $MESH_DIR $r ${pc:+--pieces $pc} >> $J 2>&1 || { log "oracle_twins: make_assets $r FAILED" >> $J; exit 1; }
  made="$made$r "; log "oracle_twins: assets $r from $MESH_DIR${pc:+, collision pieces $pc ($(ls $pc | tr '\n' ' '))}" >> $J
done

g0() {  # $1 episode: gate G0 on O's finished reference -> $OT/ep<N>/g0.json; prints PASS/FAIL and the numbers
  python - $OT/ep$1 $1 $G0_MIN /content/refs/perc2mck/ep$1 /content/refs/oraclemck/ep$1 << 'EOF'
import json, os, sys
d, ep, gmin, RP, RO = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5]
def js(f):
    try:
        return json.load(open(f))
    except Exception:
        return None
o = js(f'{d}/oracle.json') or {}; ref = {a: (js(f'{d}/ref_vs_mocap_{a}.json') or {}).get('ref_vs_mocap') for a in 'PO'}
tab = {a: (js(f'{R}/ref_summary.json') or {}).get('table', {}) for a, R in (('P', RP), ('O', RO))}
crs = {a: (js(f'{R}/contact_retarget.json') or {}).get('rest_settle') for a, R in (('P', RP), ('O', RO))}
lift = max([abs(x) for x in tab['O'].get('support_fallback_lift_cm', [])] or [float('nan')])
f0 = max((o.get('f0_centre_vs_perception_cm') or {'?': float('nan')}).values())
checks = dict(O_ref_vs_mocap=bool(ref['O'] and ref['O']['AUC'] >= gmin), support_check=bool(o.get('support_check_ok') and lift == 0),
              f0_within_3cm=bool(f0 <= 3))
g = dict(episode=ep, passed=all(checks.values()), rule=f'O reference vs mocap >= {gmin}, support check without fallback lift, '
         'frame-0 centres within 3 cm of perception', checks=checks, ref_vs_mocap=ref, f0_centre_max_cm=f0,
         O_support_fallback_lift_cm=lift, table={a: {k: t.get(k) for k in ('bottoms_cm', 'shifts_cm', 'inlier_frac')} for a, t in tab.items()},
         rest_settle=crs, oracle={k: o.get(k) for k in ('up_vs_table_normal_deg', 'mesh_frame_offset', 'expected_snap_cm',
                                                        'perception_vs_mocap', 'raw_vs_mocap', 'after_snap_vs_mocap')})
json.dump(g, open(f'{d}/g0.json', 'w'), indent=1)
a = lambda x: f"{x['AUC']} {x['per_obj_AUC']}" if x else 'none'
print(('PASS' if g['passed'] else 'FAIL ' + str([k for k, v in checks.items() if not v])) + f': O reference vs mocap {a(ref["O"])}; '
      f'P {a(ref["P"])}; frame-0 centres <= {f0} cm; fallback lift {lift} cm; oracle raw {(o.get("raw_vs_mocap") or {}).get("AUC")}, '
      f'after the expected snap {(o.get("after_snap_vs_mocap") or {}).get("AUC")}')
EOF
}

build() {  # $1 episode: P reference, then O reference on P's perception and hands, then G0
  local ep=$1 A=${ROOT[$1]} d=$OT/ep$1 RP=/content/refs/perc2mck/ep$1 RO=/content/refs/oraclemck/ep$1 g
  mkdir -p $d
  timeout 1200 bash $OPS/store.sh pull-depth $ep public > /dev/null 2>&1 || log "oracle_twins ep$ep: no stored depth (computed here)" >> $J
  ( export VARIANT=mck MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1 CR_ARGS="--rest_settle 1" STEPS=0 STOP_AFTER=reference \
      PERC=perc2 ASSETS=$A; bash $P/pipeline_ep.sh $ep ) > /content/ref_ep$ep.log 2>&1 \
    || { log "oracle_twins ep$ep: P reference FAILED ($(tail -3 /content/ref_ep$ep.log | tr '\n' ' ' | cut -c1-300))" >> $J; return 1; }
  log "oracle_twins ep$ep: P reference built ($(grep -a 'perception:\|qa_ref\|contact_retarget:' /content/ref_ep$ep.log | cut -c1-160 | tr '\n' ' ' | cut -c1-500))" >> $J
  touch $d/P_REF_OK
  mkdir -p $RO && cp $RP/hands.npz $RO/ && { [ ! -s $RP/hands_refined.npz ] || cp $RP/hands_refined.npz $RO/; } \
    || { log "oracle_twins ep$ep: hands copy FAILED" >> $J; return 1; }        # the same hands in both arms
  ( export VARIANT=mck MKREF_ARGS="--wrist_cost 3.0" CONTACT_RETARGET=1 CR_ARGS="--rest_settle 1" STEPS=0 STOP_AFTER=reference \
      PERC=oracle ASSETS=$A ORACLE_ARGS="${ORACLE_ARGS:-}"; bash $P/pipeline_ep.sh $ep ) > /content/oracle_ref_ep$ep.log 2>&1 \
    || { log "oracle_twins ep$ep: O reference FAILED ($(tail -3 /content/oracle_ref_ep$ep.log | tr '\n' ' ' | cut -c1-300))" >> $J; return 1; }
  cp /content/oracle/ep$ep/oracle.json $d/
  log "oracle_twins ep$ep: O reference built ($(grep -a 'qa_ref\|contact_retarget:' /content/oracle_ref_ep$ep.log | cut -c1-160 | tr '\n' ' ' | cut -c1-400))" >> $J
  for x in P:$RP O:$RO; do
    python $T/ref_vs_mocap.py $ep $(ls ${x#*:}/processed/*/*/*.parquet | head -1) --meshes $MESH_DIR --out $d/ref_vs_mocap_${x%%:*}.json \
      > $d/ref_vs_mocap_${x%%:*}.log 2>&1 || log "oracle_twins ep$ep: ref_vs_mocap ${x%%:*} FAILED ($(tail -1 $d/ref_vs_mocap_${x%%:*}.log | cut -c1-200))" >> $J
  done
  g=$(g0 $ep 2>&1 | tail -1); log "oracle_twins ep$ep: G0 $g" >> $J
}

label "oracle twins: references $EPS"
pids=()
for e in $EPS; do build $e & pids+=($!); sleep 60; done             # concurrent perception, staggered
wait "${pids[@]}"
PAIRS=""
for e in $EPS; do
  [ -f $OT/ep$e/P_REF_OK ] || continue
  PAIRS="$PAIRS $e:local:mck"
  if python -c "import json, sys; sys.exit(0 if json.load(open('$OT/ep$e/g0.json'))['passed'] else 1)" 2> /dev/null; then
    PAIRS="$PAIRS $e:local:mck:oracle"
  else
    log "oracle_twins ep$e: G0 not passed (or O reference missing): arm O is not trained" >> $J
  fi
done
PAIRS=${PAIRS# }; log "oracle_twins: learner $LEARNER on [$PAIRS]" >> $J
[ -n "$PAIRS" ] || { log "oracle_twins: no reference was built" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }

label "oracle twins: $LEARNER $PAIRS"
if [ $LEARNER = glock ]; then
  PAIRS="$PAIRS" TRAIN_SLOTS=${TRAIN_SLOTS:-2} bash $REPO_DIR/ops/jobs/glock_public.sh
else
  ( export FC_FDR_OBJ=1 FC_FDR_TIPS=1 FC_VOC_INERTIA=1 FC_IMMEDIATE_FIRST_FRAME=0.25 TRAIN_ARGS="$FDR_TRAIN_ARGS"   # as std_learner.sh
    PDIR_ROOT=/content/perc2 SUF=s CR=0 BASE_EVAL=0 NREP=${NREP:-6} PAIRS="$PAIRS" bash $REPO_DIR/ops/jobs/hard_ab.sh )
fi

# the reference each arm was trained on, vs mocap (after the learner's own reference stages: support fill, grasp lock,
# ILC, re-plan for glock; the copy refs/<perc>mcks for std), then the summary with the pre-registered readings
for e in $EPS; do
  for a in P O; do
    case $LEARNER:$a in
      glock:P) f=$(ls /content/refs/glockt/ep$e/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1) ;;
      glock:O) f=$(ls /content/refs/oracle_glockt/ep$e/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1) ;;
      std:P) f=$(ls /content/refs/perc2mcks/ep$e/processed/*/*/*.parquet 2> /dev/null | head -1) ;;
      std:O) f=$(ls /content/refs/oraclemcks/ep$e/processed/*/*/*.parquet 2> /dev/null | head -1) ;;
    esac
    [ -s "$f" ] && python $T/ref_vs_mocap.py $e $f --meshes $MESH_DIR --out $OT/ep$e/trained_ref_vs_mocap_$a.json > /dev/null 2>&1
  done
done
python - $OT $LEARNER $SEED "$EPS" << 'EOF' > $OT/summary.json
import json, os, sys
import numpy as np
OT, learner, seed, eps = sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4].split()]
def js(f):
    try:
        return json.load(open(f))
    except Exception:
        return None
res = {'P': '/content/results/glock_public/ep{e}/best/summary.json', 'O': '/content/results/oracle_glock_public/ep{e}/best/summary.json'} \
    if learner == 'glock' else {'P': '/content/results/hard_ab/ep{e}/mcks-s' + seed + '/summary.json',
                                'O': '/content/results/hard_ab/ep{e}/oracle_mcks-s' + seed + '/summary.json'}
out = dict(learner=learner, seed=int(seed), rule='docs/research/work/oracle-twins-20261030/PREREG.md', episodes={})
for e in eps:
    g = js(f'{OT}/ep{e}/g0.json') or {}; row = dict(g0_passed=g.get('passed'), g0_ref_vs_mocap={a: (x or {}).get('AUC') for a, x in (g.get('ref_vs_mocap') or {}).items()})
    for a in 'PO':
        s = js(res[a].format(e=e)); t = js(f'{OT}/ep{e}/trained_ref_vs_mocap_{a}.json')
        arm = dict(trained_ref_vs_mocap=(t or {}).get('ref_vs_mocap', {}).get('AUC'))
        if s:
            r = [x for x in s.get('rollouts', []) if 'auc' in x]; v = np.array([x['auc'] for x in r], float)
            arm.update(checkpoint=s.get('checkpoint'), n=len(r), sim_vs_ref=s.get('sim_vs_ref'), ref_auc=s.get('ref_auc'), floor_auc=s.get('floor_auc'))
            if len(v):
                arm.update(auc=dict(mean=round(float(v.mean()), 4), sd=round(float(v.std(ddof=1)) if len(v) > 1 else 0.0, 4),
                                    min=round(float(v.min()), 4), below_0_70=int((v < 0.70).sum())))
        row[a] = arm
    po, pp = (row['O'].get('auc') or {}).get('mean'), (row['P'].get('auc') or {}).get('mean')
    if po is not None:                                              # R1 / R2 exactly as pre-registered (PREREG.md)
        row['R1'] = 'yes (>= 0.90)' if po >= 0.90 else 'no (<= 0.75)' if po <= 0.75 else 'partial (0.75-0.90)'
    if po is not None and pp is not None:
        dl = round(po - pp, 4); row['delta_O_minus_P'] = dl
        row['R2'] = 'reference is the main loss (>= +0.12)' if dl >= 0.12 else 'not the reference (|d| <= 0.05)' if abs(dl) <= 0.05 \
            else 'oracle worse than perception (<= -0.05): check the construction' if dl <= -0.05 else 'inconclusive at one seed'
        row['class'] = 'C1 physics/learner-limited' if po <= 0.75 else 'C2 perception-limited' if dl >= 0.12 and po >= 0.90 \
            else 'C3 both' if dl >= 0.12 else 'C4 not the reference' if abs(dl) <= 0.05 else 'C5 inconclusive'
        so, sp = [(row[a].get('sim_vs_ref') or {}).get('mean') for a in 'OP']
        if so is not None and sp is not None:                       # R3 (secondary): how copyable each reference is
            d3 = round(so - sp, 4); row['sim_vs_ref_O_minus_P'] = d3
            row['R3'] = 'perceived reference harder to track (>= +0.15)' if d3 >= 0.15 else 'equally trackable (|d| <= 0.05)' \
                if abs(d3) <= 0.05 else 'inconclusive'
    out['episodes'][f'ep{e}'] = row
print(json.dumps(out, indent=1))
EOF
for e in $EPS; do
  log "oracle_twins RESULT ep$e: $(python -c "
import json; r = json.load(open('$OT/summary.json'))['episodes']['ep$e']
f = lambda a: (lambda x: f\"auc {x.get('auc')} sim_vs_ref {(x.get('sim_vs_ref') or {}).get('mean')} trained ref vs mocap {x.get('trained_ref_vs_mocap')}\")(r.get(a, {}))
print('G0', r.get('g0_passed'), r.get('g0_ref_vs_mocap'), '| P', f('P'), '| O', f('O'), '| delta', r.get('delta_O_minus_P'), '| R1', r.get('R1'), '| R2', r.get('R2'), '|', r.get('class'), '| R3', r.get('R3'))" 2>&1 | tail -1 | cut -c1-900)" >> $J
done
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
