#!/bin/bash
# Physics solver G2 + G3 on one box (2026-10-30; owner approved both, cap ~$14.5). Pre-registered readings, settings and
# expected time: docs/research/physics-2026-10-30/physics-solver.md section 5.2 (written before any G2/G3 result).
# No ground truth until G3's final scoring (registered AUC vs mocap of public episodes, after inference, as round 1).
#
# G2 (episodes G2_EPS, run concurrently): Do-as-I-Do-scale solve of the S1 grasp-lock + ILC reference (the same input
#   as G1; store run SRC, fallback ALT, then a rebuild, as ops/jobs/physics_solve.sh), with the 64-copy jitter check
#   (seed 0, common random numbers) of the input, of G1's solved reference (store run G1RUN) and of G2's output, all on
#   this box. Settings G2_ARGS; per-frame hard deadline DLPF2 s/frame and pacing PACE2 s/frame (behind schedule ->
#   MIN_ITERS iterations), so G2 ends within DLPF2 x frames whatever the throughput.
# G3: RL with the frozen recipe of the physics round 1 (ops/jobs/physics_arms.sh ARM=S1: LIB=/content/scanlib, S1 props,
#   SF=0, FDR + VOC fix, 70M steps, seed 42, CURVE_REP 3, NREP 5) through ops/jobs/glock_public.sh in REUSE_REF=1 mode on
#   the solved references, placed as /content/refs/glockt/ep<N>/<hive>/ref_gl_ilc.parquet (the only parquet there) with
#   their reconstructed_stage and a rest_check.json from their zero-action replay. robot_<side>_frames stay the INTENDED
#   hand (the solver only edits the wrist / finger targets; the wrist_ilc.py convention). Reference per episode:
#   G2_EPS: G3_PICK=best (default) -> G2's output if it exists and its jittered mean >= G1's on this box, else G1's;
#   G3_PICK=g2 -> G2's output if it exists, else G1's. Other episodes: G1's output.
# Summary: /content/results/physics_solve_rl/summary.json (G2 and G3 readings with their pre-registered verdicts).
#   ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'bash ops/jobs/physics_solve_rl.sh'
# Knobs: G2_EPS RL_EPS SRC ALT G1RUN JK DLPF2 PACE2 G2_ARGS G3_PICK SKIP_G2=1 SKIP_G3=1.
. /content/v2d-track3/ops/box/lib.sh
R=$REPO_DIR; T=$R/tools; P=$R/pipeline; J=${J:-/content/job.log}
FC=/content/v2d/robotic_grounding/flash_chord; O=/content/results/physics_solve_rl; mkdir -p $O
G2_EPS=${G2_EPS:-"2 12"}; RL_EPS=${RL_EPS:-"2 12 18 24"}
SRC=${SRC:-20261030-physS1-6a814df}; ALT=${ALT:-20261030-physS0-6a814df}; G1RUN=${G1RUN:-20261030-psolve-eecd18a}
JK=${JK:-64}; DLPF2=${DLPF2:-18}; PACE2=${PACE2:-14.4}; G3_PICK=${G3_PICK:-best}
G2_ARGS=${G2_ARGS:-"--worlds 4096 --robust 4 --horizon 60 --knot 4 --ctrl 10 --iters 32 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.9518 --retries 3 --retry 0.05 --back 1 --rob_pos 0.0005 --rob_fin 0.005 --early_rel 0.02 --early_n 2 --min_iters 6 --seed 0"}
GL_ARGS="--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15 --onset_anchor 1"
declare -A BASE=([2]="20261024-ev3-2c1e4dd:mck" [12]="20261024-ev2-2c1e4dd:mc" [18]="20261024-ev3-2c1e4dd:mc" [24]="20261024-ev3-2c1e4dd:mc")
export EMB=sharpa_hands_mid OMP_NUM_THREADS=1
log "physics_solve_rl code $(git -C $R rev-parse --short HEAD), G2 eps [$G2_EPS], RL eps [$RL_EPS], src $SRC (alt $ALT), G1 $G1RUN, JK $JK, DLPF2 $DLPF2, PACE2 $PACE2, G3_PICK $G3_PICK, G2_ARGS [$G2_ARGS]" >> $J
label "psolve_rl: assets"

# ---- objects: NVIDIA's public scans + S1 plausible masses (as physics_arms.sh ARM=S1 and physics_solve.sh)
mkdir -p /content/scanlib
for d in /content/t3/mesh/*/; do
  n=$(basename $d); f=$d/$n.glb; [ -f $f ] || f=$d/${n}_collision.glb
  [ -f $f ] && [ "$n" != wooden_spoon ] && ln -sf $f /content/scanlib/$n.glb
done
python $P/make_assets.py /content/scanlib /content/assets --physics $R/docs/research/physics-2026-10-30/props_public_scans.json >> $J 2>&1 \
  || { log "make_assets FAILED" >> $J; exit 1; }
E=$FC/src/flash_chord/configs/embodiment/sharpa_hands_mid.yaml
[ -s $E ] || cp $R/flashchord_conf/embodiment/sharpa_hands_mid.yaml $E || { log "embodiment copy FAILED" >> $J; exit 1; }

fix_assets() {  # as glock_public.sh: a reference names the absolute asset root of the box that built it
  python - "$1" << 'EOF'
import os, sys, pyarrow.parquet as pq
t = pq.read_table(sys.argv[1])
for r in sorted({os.path.dirname(os.path.dirname(p)) for p in t.column('object_urdf_paths')[0].as_py() if not os.path.exists(p)}):
    if r.startswith('/content/') and not os.path.lexists(r):
        os.symlink('/content/assets', r); print('linked', r, '-> /content/assets')
    else:
        print('MISSING assets under', r); sys.exit(1)
EOF
}
in_of() { ls /content/refs/glockt/ep$1/processed/*/*/ref_gl_ilc.parquet 2> /dev/null | head -1; }   # G2 input
g1_of() { ls /content/refs/psolve/ep$1/processed/*/*/ref_ps.parquet 2> /dev/null | head -1; }        # G1 output
g2_of() { ls /content/refs/psolve2/ep$1/processed/*/*/ref_ps.parquet 2> /dev/null | head -1; }       # G2 output
nframes() { python -c "import pyarrow.parquet as pq; print(len(pq.read_table('$1').column('robot_left_wrist_position')[0].as_py()))"; }
jitter() {  # $1 episode $2 reference $3 tag: 64-copy jitter check on the GPU
  ( cd $FC && DEV=cuda .venv/bin/python $T/physics_solve/jitter_check.py $2 --device cuda --k $JK --seed 0 \
      --json $O/ep$1/jitter_$3.json ) >> $O/ep$1/jitter_$3.log 2>&1
}
jmean() { python -c "import json; d=json.load(open('$1')); print(d['mean'])" 2> /dev/null; }

# ---- inputs: G2 inputs (SRC -> ALT -> rebuild, as physics_solve.sh) and G1's outputs
label "psolve_rl: inputs"
for e in $RL_EPS; do mkdir -p $O/ep$e; done
PULL_SUB="$(for e in $RL_EPS; do echo -n "refs/psolve/ep$e "; done)" bash $OPS/store.sh pull-run $G1RUN >> $J 2>&1 || log "pull-run $G1RUN: error (checking per episode)" >> $J
declare -A SRCOF
if [ "${SKIP_G2:-0}" != 1 ]; then
  PULL_SUB="$(for e in $G2_EPS; do echo -n "refs/glockt/ep$e "; done)" bash $OPS/store.sh pull-run $SRC >> $J 2>&1 || log "pull-run $SRC: error" >> $J
  for e in $G2_EPS; do [ -n "$(in_of $e)" ] && SRCOF[$e]=$SRC; done
  miss=$(for e in $G2_EPS; do [ -z "${SRCOF[$e]:-}" ] && echo -n "$e "; done)
  if [ -n "$miss" ]; then
    log "psolve_rl: not in $SRC: ep [$miss]; trying $ALT" >> $J
    PULL_SUB="$(for e in $miss; do echo -n "refs/glockt/ep$e "; done)" bash $OPS/store.sh pull-run $ALT >> $J 2>&1 || true
    for e in $miss; do [ -n "$(in_of $e)" ] && SRCOF[$e]=$ALT; done
  fi
  for e in $G2_EPS; do
    [ -n "${SRCOF[$e]:-}" ] && continue
    ( IFS=: read -r run base <<< "${BASE[$e]}"; R0=/content/refs/perc2$base/ep$e; LG=/content/rebuild_ep$e.log
      PULL_SUB="refs/perc2$base/ep$e" bash $OPS/store.sh pull-run $run >> $LG 2>&1 || true
      P0=$(ls $R0/processed/*/*/*.parquet 2> /dev/null | head -1); [ -s "$P0" ] && fix_assets $P0 >> $LG 2>&1 || exit 1
      hive=$(dirname ${P0#$R0/}); G=/content/refs/glockt/ep$e; mkdir -p $G/$hive /content/refs/glock_rb/ep$e/$hive; cp -r $R0/reconstructed_stage $G/
      ( cd $FC && FC=$FC GL_WRIST_KP=400 .venv/bin/python $P/grasp_lock.py $P0 /content/refs/glock_rb/ep$e/$hive/ref_gl.parquet $GL_ARGS ) >> $LG 2>&1 || exit 1
      ( cd $FC && .venv/bin/python $P/wrist_ilc.py /content/refs/glock_rb/ep$e/$hive/ref_gl.parquet $G/$hive/ref_gl_ilc.parquet --iters 4 --device cuda ) >> $LG 2>&1 ) \
      && SRCOF[$e]="rebuilt:${BASE[$e]}" || log "psolve_rl ep$e: no G2 input reference" >> $J
  done
fi
for e in $RL_EPS; do log "psolve_rl ep$e: G2 input ${SRCOF[$e]:-none} $(in_of $e); G1 output $(g1_of $e)" >> $J; done

# ---- G2
g2() {
  local ep=$1 P0 hive W N DL PC t0
  P0=$(in_of $ep); fix_assets $P0 >> $O/ep$ep/prep.log 2>&1 || { log "psolve_rl ep$ep: assets missing" >> $J; return 1; }
  hive=$(dirname ${P0#/content/refs/glockt/ep$ep/}); W=/content/refs/psolve2/ep$ep/$hive
  mkdir -p $W; cp -r /content/refs/glockt/ep$ep/reconstructed_stage /content/refs/psolve2/ep$ep/; cp $P0 $W/ref_in.parquet
  N=$(nframes $W/ref_in.parquet); DL=$(python -c "print(int($N * $DLPF2))")
  [ -s $O/ep$ep/jitter_glock.json ] || jitter $ep $W/ref_in.parquet glock
  [ -n "$(g1_of $ep)" ] && { fix_assets $(g1_of $ep) >> $O/ep$ep/prep.log 2>&1; jitter $ep $(g1_of $ep) g1; }
  log "psolve_rl ep$ep: jittered GL+ILC $(jmean $O/ep$ep/jitter_glock.json), G1 $(jmean $O/ep$ep/jitter_g1.json); G2 deadline $DL s" >> $J
  t0=$(date +%s)
  ( cd $FC && .venv/bin/python $T/physics_solve/solve.py $W/ref_in.parquet $W/ref_ps.parquet --device cuda $G2_ARGS \
      --deadline_s $DL --pace_s $PACE2 ) > $O/ep$ep/solve.out 2>&1 \
    || { log "psolve_rl ep$ep: G2 solve FAILED ($(tail -2 $O/ep$ep/solve.out | tr '\n' ' ' | cut -c1-300))" >> $J; return 1; }
  cp $W/ref_ps_solve.json $W/ref_ps_solve.log $O/ep$ep/ 2> /dev/null
  log "psolve_rl ep$ep: G2 solved in $(( $(date +%s) - t0 )) s; $(python -c "import json; d=json.load(open('$W/ref_ps_solve.json')); print('deadline_t', d['deadline_t'], 'rollbacks', d['rollbacks'], 'paced', d.get('paced_replans'), 'mean iterations', d.get('mean_iters'))" 2>&1 | tail -1)" >> $J
  ( cd $FC && DEV=cuda .venv/bin/python $T/trace_rollout.py zero $O/ep$ep/zero_g2.npz $W/ref_ps.parquet $N ) > $O/ep$ep/zero_g2.log 2>&1
  ( cd $R && python $T/trace_score.py $W/ref_ps.parquet $O/ep$ep/zero_g2.npz:zero_g2 $W/ref_ps_solve.npz:truth ) > $O/ep$ep/zero_score_g2.txt 2>&1
  jitter $ep $W/ref_ps.parquet g2
  log "psolve_rl ep$ep: G2 jittered $(jmean $O/ep$ep/jitter_g2.json) (GL+ILC $(jmean $O/ep$ep/jitter_glock.json), G1 $(jmean $O/ep$ep/jitter_g1.json)); $(tr '\n' ' ' < $O/ep$ep/zero_score_g2.txt)" >> $J
}
if [ "${SKIP_G2:-0}" != 1 ]; then
  label "psolve_rl: G2 [$G2_EPS]"
  first=$(for e in $G2_EPS; do [ -n "$(in_of $e)" ] && echo $e && break; done)
  if [ -n "$first" ]; then                          # one jitter run alone first: Warp compiles the CUDA kernels once
    P0=$(in_of $first); fix_assets $P0 >> $O/ep$first/prep.log 2>&1; jitter $first $P0 glock
  fi
  pids=()
  for e in $G2_EPS; do [ -n "$(in_of $e)" ] || continue; g2 $e & pids+=($!); sleep 20; done
  [ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
fi

# ---- G3 references: choose, place as refs/glockt/ep<N>/<hive>/ref_gl_ilc.parquet (alone), rest check
label "psolve_rl: G3 references"
GP=/content/results/glock_public; declare -A G3REF; rl_pairs=
for e in $RL_EPS; do
  pick=; src=
  if [[ " $G2_EPS " == *" $e "* ]] && [ -n "$(g2_of $e)" ]; then
    if [ "$G3_PICK" = g2 ] || python -c "import sys; sys.exit(0 if float('$(jmean $O/ep$e/jitter_g2.json)' or -1) >= float('$(jmean $O/ep$e/jitter_g1.json)' or -1) else 1)" 2> /dev/null; then
      pick=$(g2_of $e); src=G2
    fi
  fi
  [ -z "$pick" ] && [ -n "$(g1_of $e)" ] && { pick=$(g1_of $e); src=G1; }
  [ -n "$pick" ] || { log "psolve_rl ep$e: no solved reference for G3 (skipped)" >> $J; continue; }
  fix_assets $pick >> $O/ep$e/prep.log 2>&1 || { log "psolve_rl ep$e: assets missing for $pick" >> $J; continue; }
  sdir=$(dirname $pick); hive=processed/$(basename $(dirname $sdir))/$(basename $sdir); stage=${pick%%/processed/*}/reconstructed_stage
  RD=/content/refs/glockt/ep$e
  [ -d $RD ] && [ ! -d /content/refs/glockt_input/ep$e ] && { mkdir -p /content/refs/glockt_input; cp -r $RD /content/refs/glockt_input/ep$e; }
  rm -rf $RD/$hive; mkdir -p $RD/$hive; cp $pick $RD/$hive/ref_gl_ilc.parquet; rm -rf $RD/reconstructed_stage; cp -r $stage $RD/
  N=$(nframes $RD/$hive/ref_gl_ilc.parquet); mkdir -p $GP/ep$e
  ( cd $FC && DEV=cuda .venv/bin/python $T/trace_rollout.py zero $GP/ep$e/zero.npz $RD/$hive/ref_gl_ilc.parquet $N ) > $O/ep$e/g3_zero.log 2>&1
  ( cd $R && python $T/trace_score.py $RD/$hive/ref_gl_ilc.parquet $GP/ep$e/zero.npz:zero_action ) > $GP/ep$e/zero_score.txt 2>&1
  python $T/rest_check.py $GP/ep$e/zero.npz $RD/$hive/ref_gl_ilc.parquet > $GP/ep$e/rest_check.json 2>&1
  G3REF[$e]="$src $pick"; rl_pairs="$rl_pairs $e:${BASE[$e]}"
  log "psolve_rl ep$e: G3 reference = $src ($pick); zero action $(grep -a zero_action $GP/ep$e/zero_score.txt | awk '{print $NF}'); files in task dir: $(ls $RD/$hive | tr '\n' ' ')" >> $J
done
for e in $RL_EPS; do echo "$e ${G3REF[$e]:-none}"; done > $O/g3_references.txt

# ---- G3: the frozen round-1 recipe (physics_arms.sh ARM=S1) in REUSE_REF mode, seed 42
if [ "${SKIP_G3:-0}" != 1 ] && [ -n "$rl_pairs" ]; then
  label "psolve_rl: G3 RL [$rl_pairs]"
  export LIB=/content/scanlib SF=0 REPLAN=0 EVOLVE=0 CURVE_REP=3 NREP=5 SEED=42 REUSE_REF=1 HUMAN=0 GL_ARGS
  export MA_ARGS="--physics $R/docs/research/physics-2026-10-30/props_public_scans.json"
  export PULL_SUB="refs/perc2mck/ep2 refs/perc2mc/ep12 refs/perc2mc/ep18 refs/perc2mc/ep24" PAIRS="${rl_pairs# }"
  log "psolve_rl: G3 glock_public PAIRS [$PAIRS] REUSE_REF 1 seed 42" >> $J
  bash $R/ops/jobs/glock_public.sh
fi

# ---- summary with the pre-registered readings (physics-solver.md section 5.2)
python - $O $GP "$G2_EPS" "$RL_EPS" << 'EOF' > $O/summary.json
import json, os, re, sys
O, GP, g2eps, rleps = sys.argv[1], sys.argv[2], sys.argv[3].split(), sys.argv[4].split()
S1_AUC = {'2': 0.7362, '12': 0.8847, '18': 0.6245, '24': 0.2324}          # round 1, S1, seed 42 (gpu/S1_summary.json)
S1_30M = {'2': 0.483, '12': 0.549, '18': 0.529, '24': 0.112}              # round 1 curves (gpu/S1_ep*_curve.txt)
EP2_R2 = {'s43': 0.979, 's44': 0.9799}                                     # round 2, S1, ep2 (gpu/p2s1_ep2_s4*.json)
jl = lambda f: json.load(open(f)) if os.path.exists(f) else None
out = {'G2': {}, 'G3': {}}
d_scale, d_gl = {}, {}
for e in g2eps:
    r = {t: (lambda d: {k: d[k] for k in ('nominal', 'mean', 'sd', 'min', 'max', 'k')} if d else None)(jl(f'{O}/ep{e}/jitter_{t}.json'))
         for t in ('glock', 'g1', 'g2')}
    s = jl(f'{O}/ep{e}/ref_ps_solve.json')
    if s:
        r['solve'] = {k: s.get(k) for k in ('wall_s', 'deadline_t', 'rollbacks', 'paced_replans', 'mean_iters')}
    if r['g2'] and r['g1']:
        d_scale[e] = r['delta_vs_g1'] = round(r['g2']['mean'] - r['g1']['mean'], 4)
    if r['g2'] and r['glock']:
        d_gl[e] = r['delta_vs_glock'] = round(r['g2']['mean'] - r['glock']['mean'], 4)
    out['G2']['ep' + e] = r
v = list(d_scale.values()); m = sum(v) / len(v) if v else None
out['G2']['reading'] = dict(
    rule='scale helps iff mean(G2 - G1 jittered) over the G2 episodes >= +0.03 and none <= -0.05; hurts iff mean <= -0.03 '
         'or any <= -0.10; else no scale effect (an episode without a G2 result is left out and flagged)',
    mean_delta_vs_g1=None if m is None else round(m, 4), n=len(v), missing=[e for e in g2eps if e not in d_scale],
    verdict='no result' if m is None else ('scale helps' if m >= 0.03 and min(v) > -0.05 else
                                            'scale hurts' if m <= -0.03 or min(v) <= -0.10 else 'no scale effect'),
    g1_bar_kept_vs_glock={e: d >= 0.03 for e, d in d_gl.items()})
refs = dict(l.split(None, 1) for l in open(f'{O}/g3_references.txt').read().splitlines() if l.strip()) if os.path.exists(f'{O}/g3_references.txt') else {}
c30, dauc = {}, {}
for e in rleps:
    r = dict(reference=refs.get(e))
    f = f'{GP}/ep{e}/curve.txt'
    if os.path.exists(f):
        r['curve'] = open(f).read().splitlines()
        for line in r['curve']:
            mm = re.match(r'\s*30M\s+sim_vs_ref\s+([0-9.]+)', line)
            if mm:
                c30[e] = float(mm.group(1)); r['curve_30M'] = c30[e]; r['delta_30M_vs_S1'] = round(c30[e] - S1_30M[e], 4)
    b = jl(f'{GP}/ep{e}/best/summary.json')
    if b:
        r['best'] = {k: b.get(k) for k in ('checkpoint', 'n', 'sim_vs_ref', 'auc')}
        if b.get('auc'):
            dauc[e] = r['delta_auc_vs_S1'] = round(b['auc']['mean'] - S1_AUC[e], 4)
    r['S1_round1'] = dict(auc=S1_AUC[e], curve_30M=S1_30M[e])
    if e == '2':
        r['S1_round2_ep2_auc'] = EP2_R2
    out['G3']['ep' + e] = r
n30 = sum(1 for e in rleps if e in c30 and c30[e] - S1_30M[e] >= 0.03)
out['G3']['H_RL'] = dict(rule='supported iff curve sim_vs_ref at 30M (3 official evaluations) >= round-1 S1 seed 42 + 0.03 on >= 2 of 4 '
                              'episodes (no 30M result = not)', episodes=n30, verdict='supported' if n30 >= 2 else 'falsified')
va = list(dauc.values()); ma = sum(va) / len(va) if va else None
out['G3']['final_auc'] = dict(
    rule='registered AUC vs mocap (NREP 5, checkpoint chosen by sim_vs_ref) minus round-1 S1 seed 42: signal iff mean >= +0.03 and '
         'none <= -0.05; harm iff mean <= -0.03 or any <= -0.10; else inconclusive (one seed: a signal buys a second seed)',
    mean_delta=None if ma is None else round(ma, 4), n=len(va), missing=[e for e in rleps if e not in dauc],
    verdict='no result' if ma is None else ('signal' if ma >= 0.03 and min(va) > -0.05 else
                                             'harm' if ma <= -0.03 or min(va) <= -0.10 else 'inconclusive'))
print(json.dumps(out, indent=1))
EOF
log "psolve_rl summary: $(tr -d '\n ' < $O/summary.json | cut -c1-2000)" >> $J
label "psolve_rl: done $(python -c "import json; d=json.load(open('$O/summary.json')); print('G2', d['G2']['reading']['verdict'], '| H-RL', d['G3']['H_RL']['verdict'], '| AUC', d['G3']['final_auc']['verdict'])" 2>/dev/null)"
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
