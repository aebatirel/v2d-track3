#!/bin/bash
# H5 (robustness review §7, 2026-10-29): N official evaluations of every pack-6 checkpoint, scored sim_vs_ref against
# our own reference (qa.py policy; no ground truth). Measures how much of the packed score was a lucky draw and which
# episodes are high-variance. It never packs or uploads a best-of-N rollout: the output is information for the
# pre-registered choice rules (work log 2026-10-29).
#   1) pack_eval.sh with pack 6's exact choices (pack 5's RUNS / PICK / ASSET_PIECES, EP_LIB 8 only), no KEEP_RESULTS
#      unless the caller sets it (below):
#      pulls every reference / asset / checkpoint and runs draw 1 (results/submission, summary.txt);
#   2) draws 2..N: the same pristine kit evaluator on the same checkpoints JSON, each into results/h5/r<i>;
#   3) results/h5/h5_summary.json: per episode n, mean, sd, min, p20 and the packed draw (pack 6 summary.txt).
# As a job: ops/vast.sh ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run_id> 'N=10 bash ops/jobs/h5_reeval.sh'
# Candidate confirmation (2026-10-30): PICK_EXTRA="EP:RUN ..." is appended to pack 6's PICK (later entries win, so it
# replaces those episodes' checkpoints) and EPS_ONLY="EP ..." limits draws 2..N to those episodes (draw 1 stays the full
# pack). E.g. PICK_EXTRA=33:20261029-rcB-34bf6ae EPS_ONLY=33: 10 fresh draws of a candidate eval-33 checkpoint.
# Carved candidate (2026-10-30, eval-1 carve s43): KEEP_RESULTS="<pack run> ..." (pack_eval.sh) keeps the earlier
# official rollouts of unchanged checkpoints, so draw 1 is a pack candidate in which only the changed episodes are fresh
# (r1 then holds only those). ASSET_PIECES_EXTRA="DIR ..." adds the candidate's collision pieces to the ONE shared
# /content/assets (e.g. meshes/carve/ev01: carved white_pot / white_pot_lid, objects that evals 3/5/6/8/28 also have).
# That is safe only if no other episode is evaluated, so it needs KEEP_RESULTS and EVAL_ONLY="EP ..." (pack_eval.sh
# stops before the evaluator if any other episode would get a fresh rollout).
# Masses candidates (2026-10-31, docs/research/work/masses-eval-20261031/BUILD.md): RUNS_EXTRA="RUN@sub,... ..." is
# appended to pack 6's RUNS (pack_eval.sh: the FIRST run listed wins a file path, so pack 6's files stay as they are and
# the extra runs add only their own folders, e.g. RUN@refs/mass1_sf/ep20,refs/mass1s42_glockt/ep20); MASS_EPS / MA_ARGS
# reach pack_eval.sh (tools/mass_pack_check.py before draw 1) and the same check runs before draws 2..N; PACKED_TXT is the
# summary.txt of the pack on the board (default pack 6's, as before) for the packed column of h5_summary.json.
. /content/v2d-track3/ops/box/lib.sh
J=${J:-/content/job.log}; N=${N:-10}; H=/content/results/h5; mkdir -p $H
python $REPO_DIR/tools/no_oracle.py ${PICK_EXTRA:-} ${KEEP_RESULTS:-} ${ASSET_PIECES_EXTRA:-} ${RUNS_EXTRA:-} >> $J 2>&1 \
  || { log "h5: REFUSED: an input is an oracle twin (mocap-derived; tools/no_oracle.py)" >> $J; exit 1; }
C=/content/v2d-track3/meshes/carve
[ -n "${ASSET_PIECES_EXTRA:-}" ] && { [ -z "${KEEP_RESULTS:-}" ] || [ -z "${EVAL_ONLY:-}" ]; } \
  && { log "h5: ASSET_PIECES_EXTRA needs KEEP_RESULTS and EVAL_ONLY (shared /content/assets)" >> $J; exit 1; }
case " ${MA_ARGS:-}" in *--physics*)                              # (2026-10-31) masses in the shared /content/assets: the
  [ -n "${KEEP_RESULTS:-}" ] && [ -n "${EVAL_ONLY:-}" ] && [ -n "${MASS_EPS:-}" ] \
    || { log "h5: MA_ARGS --physics needs KEEP_RESULTS, EVAL_ONLY and MASS_EPS (shared /content/assets)" >> $J; exit 1; } ;;   # same rule
esac
export RUNS="20261026-fr32s46b-5e0e100@refs/glockt/ep32,refs/sf/ep32 20261026-gl10A2-5e0e100@refs/glockt/ep10,refs/glock/ep10 20261026-c25s42-feb0407@refs/perc2mcks 20261026-fr3233s43-6a8a0e2@refs/glockt/ep33,refs/sf/ep33 20261025-evb0810-ee7ba8e@refs/glockt/ep8,refs/sf/ep8 20261025-evb1420-ee7ba8e@refs/glockt/ep14,refs/sf/ep14,refs/glockt/ep20,refs/sf/ep20 20261025-fr3233-043275f@refs/glockt/ep32,refs/sf/ep32 20261025-std0116-ee7ba8e@refs/perc2mcks 20261025-std1928-ee7ba8e@refs/perc2mcks 20261025-std30-ee7ba8e@refs/perc2mcks 20261024-pack-31ef267${RUNS_EXTRA:+ $RUNS_EXTRA}"
export PICK="3:20261024-seed43-61101f5 5:20261024-seed43-61101f5 15:20261024-seed43-61101f5 16:20261024-seed43-61101f5 1:20261025-std0116-ee7ba8e:final 8:20261025-evb0810-ee7ba8e:final 14:20261025-evb1420-ee7ba8e:final 20:20261025-evb1420-ee7ba8e:final 19:20261025-std1928-ee7ba8e:final 28:20261025-std1928-ee7ba8e:final 25:20261026-c25s42-feb0407:ck=runs/perc2mcks/ep25-s42/policy_250003456.safetensors 30:20261025-std30-ee7ba8e:final 32:20261026-fr32s46b-5e0e100 33:20261026-fr3233s43-6a8a0e2 10:20261026-gl10A2-5e0e100 ${PICK_EXTRA:-}"
export EP_LIB="8:/content/v2d-track3/meshes/library_v3x" ASSET_PIECES="$C/ev25 $C/ev10${ASSET_PIECES_EXTRA:+ $ASSET_PIECES_EXTRA}"
export COMMIT_URL=https://github.com/aebatirel/v2d-track3/commit/$(git -C $REPO_DIR rev-parse HEAD)
label "H5: draw 1 (pack-6 environment)"
bash $REPO_DIR/ops/jobs/pack_eval.sh || { log "h5: pack_eval FAILED" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }
CK=/content/results/final_eval/checkpoints.json; CLEAN=/content/v2d_clean; KIT=/content/kit/v2d_submission_kit
FCV=/content/v2d/robotic_grounding/flash_chord/.venv/bin/python
if [ -n "${KEEP_RESULTS:-}" ]; then                                # a kept rollout is an earlier draw, not a new one:
  mkdir -p $H/r1                                                   # r1 = the episodes evaluated afresh in draw 1
  for e in $(python -c "import json, sys; print(' '.join(json.load(open(sys.argv[1]))))" $(dirname $CK)/checkpoints_eval.json); do
    cp -r /content/results/submission/qa/ep$e $H/r1/
  done
  log "h5: draw 1 fresh episodes: $(ls $H/r1 | tr '\n' ' ')" >> $J
else
  cp -r /content/results/submission/qa $H/r1
fi
if [ -n "${EPS_ONLY:-}" ]; then
  python -c "import json, sys; m = json.load(open(sys.argv[1])); json.dump({e: m[e] for e in sys.argv[3:]}, open(sys.argv[2], 'w'), indent=1)" \
    $CK $H/checkpoints_only.json $EPS_ONLY || exit 1
  CK=$H/checkpoints_only.json; log "h5: draws 2..$N only for episodes $EPS_ONLY ($(tr -d '\n ' < $CK | cut -c1-300))" >> $J
fi
if [ -n "${MASS_EPS:-}" ]; then                                    # draws 2..N load what draw 1's check saw (an episode
  python $REPO_DIR/tools/mass_pack_check.py --checkpoints $CK --all /content/results/final_eval/checkpoints.json \
    --props ${MASS_PROPS:-$REPO_DIR/docs/research/physics-2026-10-30/props_masses_only.json} --mass-eps "$MASS_EPS" \
    --table $REPO_DIR/docs/research/work/masses-eval-20261031/packed_refs.json --out $H/mass_pack_check.json > $H/mass_pack_check.txt 2>&1 \
    || { log "h5: REFUSED before draws 2..$N: $(cut -c1-600 $H/mass_pack_check.txt)" >> $J; bash $OPS/store.sh push-run > /dev/null 2>&1; exit 1; }
  log "h5: draws 2..$N $(cut -c1-600 $H/mass_pack_check.txt)" >> $J   # kept in draw 1 is checked here first)
fi
for i in $(seq 2 $N); do
  label "H5: draw $i of $N"
  O=$H/r$i; mkdir -p $O/results
  ( cd $CLEAN/robotic_grounding/flash_chord && PYTHONPATH=$CLEAN/robotic_grounding/flash_chord/src MUJOCO_GL=egl \
      XLA_PYTHON_CLIENT_PREALLOCATE=false $FCV $KIT/examples/run_policy_evaluation.py --checkpoints $CK \
      --results $O/results --runtime-root $CLEAN/robotic_grounding/flash_chord ) > $O/eval.log 2>&1 \
    || { log "h5: draw $i evaluation FAILED ($(tail -2 $O/eval.log | tr '\n' ' ' | cut -c1-200))" >> $J; continue; }
  for p in $O/results/episode_*.parquet; do
    e=$((10#$(basename $p .parquet | cut -d_ -f2))); mkdir -p $O/ep$e; cp ${p%.parquet}.* $O/ep$e/
    python $REPO_DIR/pipeline/qa.py policy $O/ep$e $e > /dev/null 2>&1 || true
    # rollouts kept by default (31 Oct, Prof. Inceoglu's good-vs-failed draw comparison: where draws of one checkpoint part
    # ways, GT-free on CPU; ~50-100 kB per episode); KEEP_ROLLOUTS=0 keeps only the scores, as before
    [ "${KEEP_ROLLOUTS:-1}" = 1 ] || rm -f $O/ep$e/*.parquet
  done
  rm -rf $O/results
  log "h5: draw $i done" >> $J
  bash $OPS/store.sh push-run > /dev/null 2>&1 || true            # partial results survive a crash
done
python - $H $N ${PACKED_TXT:-$REPO_DIR/results/submissions/20261026-track3f/summary.txt} << 'PYEOF' > $H/h5_summary.txt 2>&1
import glob, json, sys
import numpy as np
H, N, packed_txt = sys.argv[1], int(sys.argv[2]), sys.argv[3]
packed = json.loads(open(packed_txt).readline())
draws = {}
for f in glob.glob(f'{H}/r*/ep*/qa_policy.json'):
    ep = f.split('/ep')[-1].split('/')[0]
    draws.setdefault(ep, []).append(json.load(open(f))['sim_vs_ref'])
out = {}
for ep in sorted(draws, key=int):
    v = np.array(draws[ep])
    out[ep] = dict(n=len(v), mean=round(float(v.mean()), 4), sd=round(float(v.std(ddof=1)) if len(v) > 1 else 0.0, 4),
                   min=round(float(v.min()), 4), p20=round(float(np.percentile(v, 20)), 4), packed=packed.get(ep))
json.dump(out, open(f'{H}/h5_summary.json', 'w'), indent=1)
means = [d['mean'] for d in out.values()]
print(json.dumps(out))
print(f'episodes {len(out)}  mean of means {np.mean(means):.4f}  packed mean {np.mean([float(x) for x in packed.values()]):.4f}')
PYEOF
log "h5: $(tail -1 $H/h5_summary.txt)" >> $J
bash $OPS/store.sh push-run > /dev/null 2>&1 || true
exit 0
